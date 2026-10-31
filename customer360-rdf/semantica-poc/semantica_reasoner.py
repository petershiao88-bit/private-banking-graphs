"""Named-class inheritance tools executed by Semantica's symbolic Reasoner.

The adapter translates declared classes and named rdfs:subClassOf assertions to
facts. It does not implement an OWL DL consistency checker or use an LLM to infer.
"""

from datetime import datetime, timezone
import hashlib
from importlib.metadata import version
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import threading
from time import perf_counter

from rdflib import URIRef
from rdflib.namespace import OWL, RDF, RDFS

from ontology_tools import HERE, OntologySource, ToolPlan

RULES = [
    "IF DeclaredClass(?class) THEN SubClass(?class, ?class)",
    "IF SubClass(?child, ?middle) AND SubClass(?middle, ?parent) THEN SubClass(?child, ?parent)",
]
LIMITATIONS = ["僅執行已宣告類別的 rdfs:subClassOf 自反與遞移規則；未執行完整 OWL DL 一致性、可滿足性或資料型別驗證。"]


class UnsupportedAxioms(ValueError):
    pass


class SemanticaReasoner(OntologySource):
    engine = "Semantica Reasoner"
    scope = "holding_and_subsidiary_named_class_rules_only"

    def __init__(self, source=None):
        super().__init__(source)
        self.package_version = version("semantica")
        self.rules_sha = hashlib.sha256(json.dumps(RULES).encode()).hexdigest()
        code_hash = hashlib.sha256(Path(__file__).read_bytes() + (HERE / "ontology_tools.py").read_bytes()).hexdigest()
        self.cache_key = hashlib.sha256((self.source_sha + self.rules_sha + code_hash + self.package_version).encode()).hexdigest()
        self.folder = HERE / "data" / "semantica-reasoning" / self.cache_key
        self.lock = threading.Lock()
        self.tokens = {uri: f"class_{i:03}" for i, uri in enumerate(self.classes)}
        self.unsupported_axioms = self.find_unsupported_axioms()

    def find_unsupported_axioms(self):
        # Refuse to silently drop future OWL constructs. The current ontology's
        # property declarations/domain/range are metadata, not inference inputs.
        metadata = {OWL.versionIRI, OWL.versionInfo, OWL.priorVersion, OWL.backwardCompatibleWith, OWL.incompatibleWith}
        declarations = {OWL.Class, OWL.Ontology, OWL.AnnotationProperty, OWL.ObjectProperty, OWL.DatatypeProperty}
        issues = set()
        for subject, predicate, obj in self.graph:
            if str(predicate).startswith(str(OWL)) and predicate not in metadata:
                issues.add(str(predicate))
            if predicate == RDF.type and str(obj).startswith(str(OWL)) and obj not in declarations:
                issues.add(str(obj))
            if predicate == RDFS.subClassOf and (not isinstance(subject, URIRef) or not isinstance(obj, URIRef) or str(subject) not in self.tokens or str(obj) not in self.tokens):
                issues.add("rdfs:subClassOf with anonymous or undeclared endpoints")
            if predicate == RDFS.subPropertyOf:
                issues.add(str(predicate))
        return sorted(issues)

    def build_facts(self):
        facts = [f"DeclaredClass({token})" for token in self.tokens.values()]
        facts += [f"SubClass({self.tokens[str(child)]}, {self.tokens[str(parent)]})" for child, parent in self.graph.subject_objects(RDFS.subClassOf)]
        return sorted(set(facts))

    def classify(self, force=False):
        self.ensure_current()
        if self.unsupported_axioms:
            raise UnsupportedAxioms("Ontology contains axioms outside the supported rule subset")
        with self.lock:
            report_path = self.folder / "report.json"
            if report_path.exists() and not force:
                try:
                    report = json.loads(report_path.read_text(encoding="utf-8"))
                    if report.get("source_sha256") == self.source_sha and report.get("cache_key") == self.cache_key and report.get("engine") == self.engine and report.get("rules_sha256") == self.rules_sha:
                        return report, True
                except (ValueError, OSError):
                    pass
            from semantica.reasoning import Reasoner

            started = perf_counter()
            facts = self.build_facts()
            native = Reasoner(max_iterations=len(self.classes) + 2)
            results = native.infer_with_results(facts, RULES)
            # These are real native inference steps, not an rdflib closure or a
            # renamed HermiT report. Refuse an incomplete, non-fixpoint run.
            if native.forward_chain():
                raise RuntimeError("Semantica did not finish its closure")
            reverse = {token: uri for uri, token in self.tokens.items()}
            classes = {uri: set() for uri in self.classes}
            for fact in native.facts:
                match = re.fullmatch(r"SubClass\((class_\d+),\s*(class_\d+)\)", fact)
                if match:
                    child, parent = (reverse[token] for token in match.groups())
                    if child != parent:
                        classes[child].add(parent)
            report = {
                "engine": self.engine, "semantica_version": self.package_version, "cache_key": self.cache_key,
                "source_sha256": self.source_sha, "rules_sha256": self.rules_sha, "scope": self.scope,
                "executed_at": datetime.now(timezone.utc).isoformat(), "duration_seconds": round(perf_counter() - started, 4),
                "pg_included": False, "used_hermit": False, "consistency_complete": False, "consistency_checked": False,
                "limitations": LIMITATIONS, "classes": {uri: sorted(parents) for uri, parents in classes.items()},
                "input": {"facts": facts, "rules": RULES, "class_token_map": reverse},
                "derived_facts": sorted({result.conclusion for result in results}),
                "inference_trace": [{"conclusion": result.conclusion, "rule": "IF " + " AND ".join(map(str, result.rule_used.conditions)) + " THEN " + str(result.rule_used.conclusion), "premises": result.premises} for result in results],
            }
            self.ensure_current()
            self.folder.mkdir(parents=True, exist_ok=True)
            # Two local Explorer instances may warm the same cache concurrently.
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=self.folder, suffix=".tmp", delete=False) as handle:
                json.dump(report, handle, ensure_ascii=False, indent=2)
                temporary = Path(handle.name)
            os.replace(temporary, report_path)
            return report, False

    def execute(self, plan: ToolPlan):
        if plan.route != "ontology":
            raise ValueError("No ontology tool requested")
        for uri in (plan.class_uri, plan.parent_uri):
            if uri is not None and uri not in self.classes:
                raise ValueError("工具只接受金控與子公司本體中已宣告的類別 URI。")
        arguments = {key: value for key, value in {"class_uri": plan.class_uri, "parent_uri": plan.parent_uri}.items() if value is not None}
        base = {"id": "R1", "kind": "reasoning", "engine": self.engine, "tool": plan.tool, "arguments": arguments,
                "source_sha256": self.source_sha, "pg_included": False, "used_hermit": False, "scope": self.scope,
                "consistency_checked": False, "consistency_complete": False, "limitations": LIMITATIONS}
        try:
            self.ensure_current()
            if plan.tool == "check_consistency":
                return {**base, "status": "unsupported", "verdict": "unsupported_consistency", "summary": "目前使用 Semantica 類別繼承規則引擎，未執行完整 OWL 一致性檢查，因此無法判定整份本體是否一致。"}
            if self.unsupported_axioms:
                return {**base, "status": "unsupported", "verdict": "unsupported_axioms", "unsupported_axioms": self.unsupported_axioms, "summary": "本體含有目前繼承規則未支援的 OWL／RDFS 公理，已停止本次類別判定；需要相應的 OWL 推理器。"}
            report, cached = self.classify()
        except (RuntimeError, ValueError, OSError, KeyError, TypeError, ImportError):
            return {**base, "status": "error", "summary": "Semantica 規則推導未完成；目前不能提供類別判定。請檢查本機推理服務。"}
        base.update(cached=cached, executed_at=report["executed_at"], duration_seconds=report["duration_seconds"], rules=RULES,
                    input_fact_count=len(report["input"]["facts"]), derived_fact_count=len(report["derived_facts"]))
        ancestors = report["classes"][plan.class_uri]
        if plan.tool == "get_superclasses":
            parents = [{"uri": uri, "label": self.label(uri), "asserted_directly": (URIRef(plan.class_uri), RDFS.subClassOf, URIRef(uri)) in self.graph} for uri in ancestors]
            return {**base, "status": "completed", "verdict": "classified", "parents": parents, "summary": f"Semantica 規則推導：{self.label(plan.class_uri)}有 {len(parents)} 個上層類別（不含自身與 owl:Thing）。"}
        entailed = plan.class_uri == plan.parent_uri or plan.parent_uri in ancestors
        direct = (URIRef(plan.class_uri), RDFS.subClassOf, URIRef(plan.parent_uri)) in self.graph
        goal = f"SubClass({self.tokens[plan.class_uri]}, {self.tokens[plan.parent_uri]})"
        matching = next((step for step in report["inference_trace"] if step["conclusion"] == goal), None)
        return {**base, "status": "completed", "verdict": "entailed" if entailed else "not_entailed", "asserted_directly": direct,
                "supporting_asserted_path": self.asserted_path(plan.class_uri, plan.parent_uri) if entailed else [],
                "native_goal": goal, "native_inference": matching,
                "class_token_map": {token: uri for uri, token in self.tokens.items() if matching and any(token in fact for fact in [matching["conclusion"], *matching["premises"]])},
                "path_note": "佐證路徑由原始 rdfs:subClassOf 重建；native_inference 是 Semantica 原始匹配紀錄，可能包含同一結論的多組前提。",
                "summary": f"Semantica 規則推導：{self.label(plan.class_uri)}是{self.label(plan.parent_uri)}的子類別。" if entailed else f"目前的類別繼承規則與宣告無法證明{self.label(plan.class_uri)}是{self.label(plan.parent_uri)}的子類別；這不代表已證明兩者互斥。"}


if __name__ == "__main__":
    reasoner = SemanticaReasoner()
    report, cached = reasoner.classify(force="--force" in sys.argv)
    print(json.dumps({"engine": report["engine"], "classes": len(report["classes"]), "input_facts": len(report["input"]["facts"]), "derived_facts": len(report["derived_facts"]), "rules": RULES, "consistency_checked": False, "pg_included": False, "used_hermit": False, "cached": cached, "report": str(reasoner.folder / "report.json")}, ensure_ascii=False, indent=2))
