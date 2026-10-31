"""Offline, synthetic A2A handoff: native Semantica rules + SHACL + gated delivery.

Only fixed demo scenarios are exposed over HTTP. No LLM, IAM, real client data,
remote agent, production approval, or original graph mutation is involved.
"""
from __future__ import annotations

import argparse
import asyncio
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import re
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, ConfigDict
from rdflib import Graph, Literal, Namespace, RDF, RDFS, URIRef

HERE = Path(__file__).resolve().parent
POLICY = HERE / "handoff-policy"
H = Namespace("urn:handoff-demo:")
BANK = "https://example.org/ontology/bank#"
HOLDING = "https://example.org/ontology/holding#"
SEC = "https://example.org/ontology/securities#"
POLICY_VERSION = "demo-policy-1"
LABELS = {
    "public": "公開資訊", "bank_view": "銀行視角", "internal_performance": "內部績效",
    "personal_data": "個資", "bank_subsidiary": "銀行子公司", "securities_subsidiary": "證券子公司",
}
TERMS = {
    "product_info": HOLDING + "FinancialProduct",
    "bank_fee": BANK + "BankFeeIncome",
    "recommendation": str(H.RecommendationAmount),
}
# A separate illustrative policy overlay. These tags are not asserted in the
# customer's original OWL; class membership alone does not make all fees secret.
CLASS_LABELS = {
    TERMS["product_info"]: ["public"],
    TERMS["bank_fee"]: ["bank_view", "internal_performance"],
}
SOURCES = {
    "product_catalog": {"labels": ["public"], "upstream": [], "description": "模擬公開商品說明"},
    "fee_staging": {"labels": ["internal_performance"], "upstream": [], "description": "模擬手收 staging 表"},
    "bank_holdings": {"labels": ["personal_data", "bank_subsidiary"], "upstream": [], "description": "模擬銀行持倉"},
    "securities_holdings": {"labels": ["personal_data", "securities_subsidiary"], "upstream": [], "description": "模擬證券持倉"},
    "combined_position": {"labels": [], "upstream": ["bank_holdings", "securities_holdings"], "description": "模擬上游銀行＋證券組合結果"},
}


def item(item_id, term_id, value, *sources):
    return {"id": item_id, "term_id": term_id, "value": value, "source_ids": list(sources)}


PUBLIC_ITEM = item("product", "product_info", "商品說明：申購前請閱讀公開說明書。", "product_catalog")
FEE_ITEM = item("fee", "bank_fee", "此檔手收 1.5%（模擬）", "fee_staging")
RECOMMENDATION = item("recommendation", "recommendation", "建議申購金額 100,000 元（模擬，非投資建議）", "combined_position")
# Mock server-side tool receipts stand in for a trusted tool adapter. Merely
# supplying a real receipt ID cannot authorize altered content or dropped sources.
RECEIPTS = {
    "public": [PUBLIC_ITEM], "fee": [PUBLIC_ITEM, FEE_ITEM],
    "combined": [RECOMMENDATION], "mixed": [PUBLIC_ITEM, FEE_ITEM, RECOMMENDATION],
    "missing_source": [item("fee", "bank_fee", "此檔手收 1.5%（模擬）")],
    "unknown_term": [item("unknown", "agent_invented_class", "未登記輸出", "product_catalog")],
}


def scenario_catalog():
    return [
        ("public", "公開資訊直接交接", "公開商品說明可以交給客戶報告 Agent。", "allowed"),
        ("fee_block", "手收未遮罩：阻擋", "銀行視角與內部績效不能進入客戶報告。", "blocked"),
        ("fee_mask", "手收移除後重驗", "註冊的遮罩工具移除整個手收項目，只傳公開說明。", "allowed_after_redaction"),
        ("combined_no_consent", "銀行＋證券：缺少同意", "組合答案繼承兩邊標籤，需要客戶同意。", "needs_consent"),
        ("combined_with_consent", "銀行＋證券：有效同意", "核對客戶、接收者、用途、效期後才傳送。", "allowed"),
        ("fake_consent", "Agent 自稱已取得同意", "沒有可信的同意紀錄，不接受 Agent 的文字聲明。", "needs_consent"),
        ("wrong_scope", "同意對象不符", "別的 Agent 的同意紀錄不能用於此次交接。", "needs_consent"),
        ("expired_consent", "同意已過期", "過期的同意紀錄不放行。", "needs_consent"),
        ("fake_public", "Agent 自稱答案公開", "忽略自報標籤，依已登記來源重新推導。", "needs_consent"),
        ("tampered_output", "竄改最後工具的 object", "內容與工具收據不符，進推理前即阻擋。", "blocked"),
        ("missing_source", "缺少來源", "即使格式正確，也不能把缺少來源當作沒有風險。", "blocked"),
        ("unknown_term", "Agent 自創 class", "詞條未登記，無法判定語義時阻擋。", "blocked"),
        ("fake_downgrade", "自稱已彙總可降級", "未註冊的降級處理不移除任何限制。", "blocked"),
        ("mixed_mask", "遮掉手收仍保留個資", "移除手收不會解除其他項目的客戶同意要求。", "needs_consent"),
    ]


def make_scenario(case_id):
    specs = {row[0]: row for row in scenario_catalog()}
    if case_id not in specs:
        raise ValueError("Unknown demo scenario")
    receipt = {
        "public": "public", "fee_block": "fee", "fee_mask": "fee",
        "missing_source": "missing_source", "unknown_term": "unknown_term",
        "mixed_mask": "mixed", "fake_downgrade": "combined",
    }.get(case_id, "combined")
    claim = {"receipt_id": receipt, "items": deepcopy(RECEIPTS[receipt]), "claimed_labels": [], "claimed_consent": False}
    request = {"sender": "advisor_agent", "recipient": "customer_report", "customer": "demo_customer_001", "purpose": "customer_report", "consent_id": None, "transform": None}
    if case_id in {"fee_mask", "mixed_mask"}:
        request["transform"] = "remove_bank_performance_v1"
    if case_id == "combined_with_consent":
        request["consent_id"] = "consent_valid"
    if case_id in {"wrong_scope", "expired_consent"}:
        request["consent_id"] = "consent_" + case_id
    if case_id == "fake_consent":
        claim["claimed_consent"] = True
    if case_id == "fake_public":
        claim["claimed_labels"] = ["public"]
    if case_id == "tampered_output":
        claim["items"][0]["value"] = "Agent 改成 9,999,999 元"
    if case_id == "fake_downgrade":
        request["transform"] = "agent_says_aggregated"
    return claim, request


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


class DemoReceiver:
    """Local stand-in for Agent B, capturing exactly what crosses the boundary."""
    def __init__(self):
        self.inbox = []

    def receive(self, payload):
        self.inbox.append(deepcopy(payload))
        return {"received": True, "payload_sha256": digest(payload)}


class HandoffHarness:
    def __init__(self):
        from semantica.context import ContextGraph
        from semantica.provenance import ProvenanceManager
        from semantica.provenance.storage import InMemoryStorage
        self.graph = ContextGraph(advanced_analytics=False, extract_entities=False, extract_relationships=False)
        self.provenance = ProvenanceManager(storage=InMemoryStorage())
        self.rules = [line.strip() for line in (POLICY / "rules.txt").read_text(encoding="utf-8").splitlines() if line.strip() and not line.startswith("#")]
        self.shapes = (POLICY / "customer-report.ttl").read_text(encoding="utf-8")
        self.ontology = Graph().parse(HERE.parent / "customer360-ontology.ttl", format="turtle")
        self.ontology.add((H.RecommendationAmount, RDFS.subClassOf, URIRef(HOLDING + "Metric")))
        self.policy_sha256 = digest({"rules": self.rules, "shapes": self.shapes, "terms": TERMS, "class_labels": CLASS_LABELS, "sources": SOURCES})
        self.now = datetime.now(timezone.utc)
        self.consents = {
            "consent_valid": {"customer": "demo_customer_001", "recipient": "customer_report", "purpose": "customer_report", "expires": self.now + timedelta(hours=1)},
            "consent_wrong_scope": {"customer": "demo_customer_001", "recipient": "different_agent", "purpose": "customer_report", "expires": self.now + timedelta(hours=1)},
            "consent_expired_consent": {"customer": "demo_customer_001", "recipient": "customer_report", "purpose": "customer_report", "expires": self.now - timedelta(seconds=1)},
        }

    def verify(self, claim, request):
        if request.get("sender") != "advisor_agent" or request.get("recipient") != "customer_report":
            raise ValueError("交接 Agent 尚未登記。")
        if request.get("customer") != "demo_customer_001" or request.get("purpose") != "customer_report":
            raise ValueError("交接客戶或用途不在本次工具收據的範圍。")
        expected = RECEIPTS.get(claim.get("receipt_id"))
        if expected is None or claim.get("items") != expected:
            raise ValueError("輸出內容或來源與可信工具收據不符。")
        if not expected or len({x["id"] for x in expected}) != len(expected):
            raise ValueError("工具輸出為空或項目 ID 重複。")
        for component in expected:
            if component["term_id"] not in TERMS:
                raise ValueError("輸出含有未登記詞條，不能推定它是安全內容。")
            if not component["source_ids"]:
                raise ValueError("輸出缺少來源，不能通過交接。")
            for source in component["source_ids"]:
                self.collect_sources(source, set(), set())
        if request.get("transform") not in {None, "remove_bank_performance_v1"}:
            raise ValueError("降級或彙總工具尚未註冊，不能解除標籤。")
        return deepcopy(expected)

    def collect_sources(self, source, found, active):
        if source not in SOURCES:
            raise ValueError("來源未登記，不能通過交接。")
        if source in active:
            raise ValueError("來源包含循環，無法確認完整血緣。")
        if source in found:
            return found
        record = SOURCES[source]
        if (not record["labels"] and not record["upstream"]) or any(label not in LABELS for label in record["labels"]):
            raise ValueError("來源缺少有效的風險分類。")
        active.add(source)
        found.add(source)
        for upstream in SOURCES[source]["upstream"]:
            self.collect_sources(upstream, found, active)
        active.remove(source)
        return found

    def consent_check(self, request):
        record = self.consents.get(request.get("consent_id"))
        verified = bool(record and all(record[key] == request[key] for key in ("customer", "recipient", "purpose")) and record["expires"] > datetime.now(timezone.utc))
        return {"verified": verified, "record_id": request.get("consent_id"), "checked_fields": ["customer", "recipient", "purpose", "expires"], "provider": "mock_consent_registry"}

    def infer(self, items, output_id):
        # Same native handler as Semantica's run_reasoning MCP tool. Only this
        # trusted adapter builds facts and loads the fixed policy rule set.
        from semantica.mcp_server import _tool_run_reasoning
        classes = set(TERMS.values())
        for child, parent in self.ontology.subject_objects(RDFS.subClassOf):
            classes.update((str(child), str(parent)))
        tokens = {uri: f"class_{i}" for i, uri in enumerate(sorted(classes))}
        facts = []
        for child, parent in self.ontology.subject_objects(RDFS.subClassOf):
            facts.append(f"Subclass({tokens[str(child)]}, {tokens[str(parent)]})")
        for uri, labels in CLASS_LABELS.items():
            facts += [f"ClassLabel({tokens[uri]}, {label})" for label in labels]
        all_sources = set()
        for component in items:
            cid = component["id"]
            facts += [f"Contains({output_id}, {cid})", f"IsA({cid}, {tokens[TERMS[component['term_id']]]})"]
            for source in component["source_ids"]:
                facts.append(f"DerivedFrom({cid}, {source})")
                self.collect_sources(source, all_sources, set())
        for source in sorted(all_sources):
            facts += [f"HasLabel({source}, {label})" for label in SOURCES[source]["labels"]]
            facts += [f"DerivedFrom({source}, {upstream})" for upstream in SOURCES[source]["upstream"]]
        facts = sorted(set(facts))
        response = _tool_run_reasoning({"facts": facts, "rules": self.rules})
        if "error" in response or not isinstance(response.get("derived_facts"), list):
            raise RuntimeError("Reasoning did not complete")
        derived = sorted(set(response["derived_facts"]))
        combined = facts + derived
        def labels_for(subject):
            pattern = re.compile(r"HasLabel\(" + re.escape(subject) + r",\s*([a-z_]+)\)")
            return sorted({m.group(1) for fact in combined if (m := pattern.fullmatch(fact))})
        labels = labels_for(output_id)
        if not labels or any(label not in LABELS for label in labels):
            raise RuntimeError("Unknown or missing policy labels")
        return {"engine": "Semantica MCP run_reasoning / Reasoner", "facts": facts, "rules": self.rules, "derived_facts": derived, "class_token_map": {token: uri for uri, token in tokens.items()}, "labels": labels, "item_labels": {component["id"]: labels_for(component["id"]) for component in items}, "sources": sorted(all_sources)}

    def validate(self, items, output_id, inference, consent):
        from semantica.ontology import run_shacl_validation
        graph = Graph()
        graph.bind("h", H)
        output = H[output_id]
        graph.add((output, RDF.type, H.Handoff))
        graph.add((output, H.recipient, H.customer_report))
        for prop in (H.receiptVerified, H.lineageComplete):
            graph.add((output, prop, Literal(True)))
        graph.add((output, H.consentVerified, Literal(consent["verified"])))
        for label in inference["labels"]:
            graph.add((output, H.label, H[label]))
        for component in items:
            node = H[component["id"]]
            graph.add((output, H.item, node))
            graph.add((node, H.value, Literal(component["value"])))
            graph.add((node, H["term"], URIRef(TERMS[component["term_id"]])))
            for source in component["source_ids"]:
                graph.add((node, H.source, H[source]))
        data = graph.serialize(format="turtle")
        report = run_shacl_validation(data, self.shapes)
        return {"engine": "Semantica run_shacl_validation / pySHACL", "conforms": report.conforms, "violations": [v.to_dict() for v in report.violations], "data_ttl": data, "shapes_ttl": self.shapes}

    def record_material(self, items, output_id, inference, original_id=None):
        for source in inference["sources"]:
            self.graph.add_nodes([{"id": source, "type": "DemoSource", "content": SOURCES[source]["description"]}])
            entry = self.provenance.track_entity(source, source="mock_tool_registry", used_entities=SOURCES[source]["upstream"], metadata={"demo_only": True})
            if entry is None:
                raise RuntimeError("Provenance storage failed")
        for component in items:
            cid = component["id"]
            class_uri = TERMS[component["term_id"]]
            self.graph.add_nodes([{"id": cid, "type": "AgentOutputItem", "content": component["value"]}, {"id": class_uri, "type": "OntologyClass"}])
            self.graph.add_edges([{"source": cid, "target": class_uri, "type": "INSTANCE_OF"}] + [{"source": cid, "target": source, "type": "DERIVED_FROM"} for source in component["source_ids"]])
            if self.provenance.track_entity(cid, source="mock_final_tool", used_entities=component["source_ids"], metadata={"term_id": component["term_id"]}) is None:
                raise RuntimeError("Provenance storage failed")
        self.graph.add_nodes([{"id": output_id, "type": "HandoffOutput", "content": "模擬交接輸出"}])
        self.graph.add_edges([{"source": output_id, "target": component["id"], "type": "CONTAINS"} for component in items])
        used = [component["id"] for component in items] + ([original_id] if original_id else [])
        if self.provenance.track_entity(output_id, source="mock_final_tool" if not original_id else "remove_bank_performance_v1", used_entities=used, metadata={"policy_version": POLICY_VERSION, "approved_projection": bool(original_id)}) is None:
            raise RuntimeError("Provenance storage failed")

    def decision(self, output_id, verdict, details, previous=None):
        decision_id = self.graph.record_decision(category="a2a_handoff", scenario=output_id, reasoning=details, outcome=verdict, confidence=1.0, decision_maker="local_demo_harness", entities=[output_id], metadata={"demo_only": True, "policy_version": POLICY_VERSION})
        if previous:
            self.graph.add_edges([{"source": previous, "target": decision_id, "type": "CAUSES"}])
        return decision_id

    def execute(self, claim, request, receiver):
        output_id = "answer_" + uuid4().hex[:12]
        base = {"demo_only": True, "policy_version": POLICY_VERSION, "policy_sha256": self.policy_sha256, "run_id": output_id, "used_llm": False, "used_hermit": False, "pg_included": False, "claim": deepcopy(claim), "request": deepcopy(request), "stages": [], "removed_items": [], "delivered": False, "receiver_inbox": [], "decision_ids": []}
        try:
            items = self.verify(claim, request)
        except ValueError as exc:
            base.update(verdict="blocked", explanation=str(exc), precheck={"verified": False})
            base["decision_ids"].append(self.decision(output_id, "blocked", str(exc)))
            return base
        base["precheck"] = {"verified": True, "receipt_sha256": digest(items), "agent_claims_used_as_evidence": False}
        consent = self.consent_check(request)
        base["consent"] = consent
        previous = None
        pending_payload = None
        for attempt in range(2):
            stage_id = output_id if attempt == 0 else output_id + "_redacted"
            inference = self.infer(items, stage_id)
            validation = self.validate(items, stage_id, inference, consent)
            self.record_material(items, stage_id, inference, output_id if attempt else None)
            decision_id = self.decision(stage_id, "allowed" if validation["conforms"] else "blocked", "SHACL conforms=" + str(validation["conforms"]), previous)
            base["decision_ids"].append(decision_id)
            base["stages"].append({"stage": "original" if attempt == 0 else "redacted", "items": deepcopy(items), "reasoning": inference, "validation": validation})
            if validation["conforms"]:
                verdict = "allowed_after_redaction" if attempt else "allowed"
                payload = {"handoff_id": stage_id, "sender": request["sender"], "recipient": request["recipient"], "customer": request["customer"], "purpose": request["purpose"], "items": deepcopy(items), "labels": inference["labels"], "policy_version": POLICY_VERSION, "decision_id": decision_id}
                pending_payload = payload
                base.update(verdict=verdict, explanation="已通過 SHACL，模擬接收 Agent 已收到驗證後的內容。")
                break
            if attempt == 0 and request.get("transform") == "remove_bank_performance_v1":
                # A registered deterministic projection, not an LLM deleting
                # labels. Drop whole independently structured components, then
                # regenerate facts and rerun SHACL before any receive() call.
                removed = [x for x in items if set(inference["item_labels"][x["id"]]) & {"bank_view", "internal_performance"}]
                if removed:
                    base["removed_items"] = deepcopy(removed)
                    projected = [x for x in items if x not in removed]
                    base["transformation"] = {"registered_tool": "remove_bank_performance_v1", "input_sha256": digest(items), "output_sha256": digest(projected), "removed_item_ids": [x["id"] for x in removed]}
                    items = projected
                    previous = decision_id
                    continue
            needs = "personal_data" in inference["labels"] and not consent["verified"]
            # Do not hide other violations behind a request for consent.
            forbidden = set(inference["labels"]) & {"bank_view", "internal_performance"}
            base.update(verdict="needs_consent" if needs and not forbidden else "blocked", explanation="缺少有效且範圍相符的客戶同意，尚未傳送。" if needs and not forbidden else "內容不符合接收 Agent 的 SHACL 條件，尚未傳送。")
            break
        base["lineage"] = self.provenance.get_lineage(stage_id)
        base["decision_trace"] = self.graph.trace_decision_chain(base["decision_ids"][-1])
        base["audit_graph"] = {"nodes": len(self.graph.find_nodes()), "edges": len(self.graph.find_edges())}
        # Audit and validation must finish before crossing even the mock boundary.
        if pending_payload is not None:
            receipt = receiver.receive(pending_payload)
            base.update(delivered=True, delivery_receipt=receipt, receiver_inbox=deepcopy(receiver.inbox))
        return base


def run_case(case_id):
    claim, request = make_scenario(case_id)
    result = HandoffHarness().execute(claim, request, DemoReceiver())
    spec = next(row for row in scenario_catalog() if row[0] == case_id)
    return {"case_id": case_id, "title": spec[1], "expected": spec[3], "passed": result["verdict"] == spec[3], **result}


def run_suite():
    results = [run_case(row[0]) for row in scenario_catalog()]
    return {"demo_only": True, "created_at": datetime.now(timezone.utc).isoformat(), "semantica_version": version("semantica"), "pyshacl_version": version("pyshacl"), "source_ontology_sha256": hashlib.sha256((HERE.parent / "customer360-ontology.ttl").read_bytes()).hexdigest(), "policy_version": POLICY_VERSION, "total": len(results), "passed": sum(result["passed"] for result in results), "results": results}


class DemoRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    case_id: str


def attach_handoff_demo(app, port=8866):
    router = APIRouter()
    gate = asyncio.Lock()
    allowed_origins = {"", f"http://127.0.0.1:{port}", f"http://localhost:{port}"}

    @router.get("/handoff", response_class=HTMLResponse, include_in_schema=False)
    async def page():
        return HTMLResponse((HERE / "handoff_demo.html").read_text(encoding="utf-8"), headers={"Cache-Control": "no-store"})

    @router.get("/api/handoff/scenarios")
    async def scenarios():
        return {"scenarios": [{"id": r[0], "title": r[1], "description": r[2], "expected": r[3]} for r in scenario_catalog()], "labels": LABELS}

    @router.post("/api/handoff/run")
    async def run(body: DemoRequest, request: Request):
        if request.headers.get("x-handoff-demo") != "1" or request.headers.get("origin", "") not in allowed_origins:
            raise HTTPException(403, "請由本機交接測試頁執行。")
        if body.case_id not in {r[0] for r in scenario_catalog()} | {"all"}:
            raise HTTPException(422, "未知的模擬案例。")
        if gate.locked():
            raise HTTPException(429, "測試正在執行，請稍後再試。")
        async with gate:
            try:
                return await asyncio.to_thread(run_suite if body.case_id == "all" else run_case, *([] if body.case_id == "all" else [body.case_id]))
            except Exception:
                # Engine / validation / audit failures never trigger delivery.
                raise HTTPException(503, "推理或驗證未完成；本次未交接。") from None

    old_count = len(app.router.routes)
    app.include_router(router)
    additions = app.router.routes[old_count:]
    del app.router.routes[old_count:]
    app.router.routes[0:0] = additions


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", default="all", choices=["all"] + [row[0] for row in scenario_catalog()])
    parser.add_argument("--report", action="store_true", help="Save the synthetic test report under data/handoff/")
    args = parser.parse_args()
    result = run_suite() if args.case == "all" else run_case(args.case)
    if args.report:
        folder = HERE / "data" / "handoff"
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "report.json").write_text(json.dumps(result, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    if args.case == "all":
        print(json.dumps({"passed": result["passed"], "total": result["total"], "cases": [{k: x[k] for k in ("case_id", "verdict", "passed", "delivered")} for x in result["results"]]}, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    raise SystemExit(0 if (result["passed"] == result["total"] if args.case == "all" else result["passed"]) else 1)
