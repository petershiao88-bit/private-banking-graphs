"""Seed the initial reviewed product AUM metadata; not a generic SQL analyzer.

Refuses to overwrite the active JSON; subsequent edits belong in that JSON.
"""

import copy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PG = ROOT / "department-pg"
FH = "https://example.org/ontology/holding#"
BANK = "https://example.org/ontology/bank#"


def seed():
    target = PG / "product-aum.json"
    if target.exists():
        raise SystemExit("product-aum.json exists; refusing overwrite")
    deposit = json.loads((PG / "deposits.json").read_text(encoding="utf-8"))
    template = json.loads((PG / "advisory-income.json").read_text(encoding="utf-8"))
    fields = {key: copy.deepcopy(template["field_definitions"][key]) for key in (
        "customerId", "productId", "amount", "currency", "snapshotDate")}
    fields["amount"].update(name="AUM 金額", definition="依指定快照日與核定管理、認列及估值口徑形成的資產規模金額。")
    fields["customerId"]["definition"] = "AUM 所衡量客戶的來源識別欄位。"
    fields["productId"]["definition"] = "AUM 所對應金融商品的來源識別欄位。"
    fields["currency"]["definition"] = "AUM 金額的計價或報表幣別。"
    fields["snapshotDate"]["definition"] = "AUM 所衡量的資產規模之資料基準日期。"
    model = {
        "schema_version": "1.0.0", "ontology_version": template["ontology_version"], "status": "active",
        "scope": "metadata_only", "inference": False, "instance_mapping": False,
        "access_policy_status": "deferred_by_user", "field_definitions": fields,
        "execution": {key: None for key in ("sql", "join_rules", "filter_rules", "aggregation_rules",
                      "row_grain", "valuation_rules", "deduplication_rules", "snapshot_selection", "currency_conversion")},
        "evidence": copy.deepcopy(deposit["evidence"]), "sources": copy.deepcopy(deposit["sources"]),
        "concepts": [], "relation_definitions": [],
    }
    sql_path = "Ontology/私銀智能問答/sources/sql/1.AUM_DETAIL.sql"
    model["evidence"].update({
        "sql_bank_investment_aum": {"file": sql_path, "lines": [211, 230], "encoding": "cp950"},
        "sql_bank_bond_proprietary_aum": {"file": sql_path, "lines": [232, 251], "encoding": "cp950"},
    })
    for table, evidence in (("DSFND.PB_FUND_MONTH", "sql_bank_investment_aum"),
                             ("DSWTR.BOND_POS_DAY", "sql_bank_bond_proprietary_aum")):
        model["sources"].append({"table": table, "status": "observed_in_files", "database_verified": False,
                                  "evidence": [evidence]})

    def add(cid, name, product_classes, observations, basis=None):
        mappings = [{"field": field, "status": "pending_product_identity" if field == "productId" else
                     "pending_currency" if field == "currency" else "pending_time_semantics" if field == "snapshotDate"
                     else "observed_raw_candidate" if field == "customerId" else "pending_aum_recognition",
                     "table": None, "column": None, "candidates": []} for field in fields]
        concept = {"id": cid, "name": name, "definition": name + "所描述的客戶資產規模指標。",
                   "subsidiary": "bank", "department_owner": None, "class_uri": BANK + "BankAUM",
                   "specific_product_class_uri": None, "product_class_uris": [BANK + p for p in product_classes],
                   "basis_concept": basis, "fields": mappings, "observations": observations}
        model["concepts"].append(concept)
        model["relation_definitions"].append({"id": cid + ".product", "name": name + "衡量金融商品",
            "source_concept": cid, "property_uri": FH + "measuresProduct", "domain_uri": FH + "AUM",
            "target_class_uri": FH + "FinancialProduct", "fields": []})
        return {m["field"]: m for m in mappings}

    for source_id, cid, name in (
        ("bank.twd_deposit", "bank.twd_deposit_aum", "台幣存款 AUM"),
        ("bank.foreign_currency_deposit", "bank.foreign_currency_deposit_aum", "外幣存款 AUM"),
        ("bank.structured_deposit", "bank.structured_deposit_aum", "結構型存款 AUM"),
    ):
        source = next(c for c in deposit["concepts"] if c["id"] == source_id)
        mappings = add(cid, name, [uri.split("#")[-1] for uri in source["class_uris"]], {
            "coverage": "沿用已盤點存款來源候選，不承諾完整業務覆蓋；原始餘額與正式 AUM 的認列仍待確認。",
            "classification_evidence": copy.deepcopy(source["classification_evidence"]),
            "valuation_observation": "既有 SQL 依來源日期、客戶、PCC、分類碼彙總原始 BAL_AMT／AVAIL_BAL。",
            "date_observation": "DATA_DT、LST_MTN_DT 或 YYYYMM 的適用語意仍待確認，未選定快照日。",
            "gaps": ["原始餘額不直接等同核定 AUM。", "來源幣別、去重、跨表識別與聚合未定案。",
                     "分類碼及歷史時間門檻只作來源觀察，不自動轉成新版篩選規則。",
                     "台幣／外幣／結構型分類可能重疊，銀行 AUM 不自動將本清單相加。"],
            "evidence": sorted({e for item in source["classification_evidence"] for e in item["evidence"]}),
        }, basis=source_id)
        for field, original_field in (("customerId", "customerId"), ("amount", "balance"), ("snapshotDate", "snapshotDate")):
            original = next(m for m in source["fields"] if m["field"] == original_field)
            mappings[field]["candidates"] = copy.deepcopy(original["candidates"])

    table = "DSFND.PB_FUND_MONTH"
    evidence = ["sql_bank_investment_aum"]
    for cid, name, products, codes, mapped in (
        ("bank.overseas_stock_aum", "海外股票 AUM", ("StockProduct", "OverseasFinancialProduct"),
         ["其他-國外有價證券", "其他-國外股票", "股票"], "海外股票"),
        ("bank.overseas_bond_trust_aum", "海外債券（信託）AUM", ("BondProduct", "OverseasFinancialProduct"),
         ["海外債券"], "海外債券(信託)"),
        ("bank.offshore_structured_aum", "境外結構型商品 AUM", ("StructuredFinancialProduct", "OverseasFinancialProduct"),
         ["結構型商品"], "境外結構型商品"),
    ):
        mappings = add(cid, name, products, {
            "coverage": "僅依既有銀行投資 AUM 分支建立來源候選。",
            "sql_output": "AUM_013_015_015_016_017_018",
            "sql_group_by": ["IDNO", "TO_CHAR(EXEDATE,'YYYYMMDD')", "PCCCODE", "normalized TRUSTPRD"],
            "valuation_observation": "SUM(CurrentTWDValue)",
            "classification_evidence": [{"table": table, "column": "TRUSTPRD", "values": codes,
                                         "mapped_label": mapped, "status": "evidence_only", "evidence": evidence}],
            "date_observation": "SQL 將 EXEDATE 轉成 YYYYMMDD；來源日期業務定義與統一快照口徑尚未選定。",
            "gaps": ["CurrentTWDValue 的台幣語意目前僅見欄位名稱與 SQL；未獨立核對 metadata，currency 不填常數。",
                     "TRUSTPRD 是業務分類，不當作單一商品 ID；來源聚合未保留商品識別。",
                     "既有 SQL 的股票分類包含『其他-國外有價證券』，分類範圍需覆核。" if "stock" in cid
                     else "業務通路與商品細分類只保留為部門情境，不新增組合 OWL Class。"],
            "evidence": evidence,
        })
        for field, column, meaning in (("customerId", "IDNO", "SQL 客戶識別欄位。"),
                                       ("amount", "CurrentTWDValue", "SQL 投資 AUM 加總欄位，正式估值與認列待確認。"),
                                       ("snapshotDate", "EXEDATE", "SQL 使用日期候選，尚未核定統一快照日。")):
            mappings[field]["candidates"] = [{"table": table, "column": column, "meaning": meaning, "evidence": evidence}]

    table = "DSWTR.BOND_POS_DAY"
    evidence = ["sql_bank_bond_proprietary_aum"]
    mappings = add("bank.overseas_bond_proprietary_aum", "海外債券（自營）AUM", ("BondProduct", "OverseasFinancialProduct"), {
        "coverage": "既有自營平台外國債券 AUM 分支；不與信託分支自動合併。",
        "sql_output": "AUM_019", "sql_group_by": ["CIF_ID", "DATA_DT"],
        "valuation_observation": "SUM(STO_AMT * MKT_PRI / 100 * EXC_RATE)",
        "sql_filter_observation": "PCC_CODE LIKE '2E%'",
        "date_observation": "先日彙總，再取全體資料每月最大日期；不是每位客戶各自最後交易日。",
        "classification_evidence": [],
        "gaps": ["amount 的三個來源欄位為同一估值公式的輸入，不是可任選的三種金額。",
                 "來源日期、幣別、估值、跨來源去重與統一快照規則仍待核定。",
                 "既有全體每月最大日期只作觀察，不轉成新版預設選日規則。"],
        "evidence": evidence,
    })
    for field, columns in (("customerId", ["CIF_ID"]), ("amount", ["STO_AMT", "MKT_PRI", "EXC_RATE"]),
                            ("snapshotDate", ["DATA_DT"])):
        mappings[field]["candidates"] = [{"table": table, "column": column,
            "meaning": "估值公式輸入。" if field == "amount" else "既有 SQL 的來源識別／日期欄位候選。",
            "evidence": evidence} for column in columns]
    target.write_text(json.dumps(model, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print("Seeded seven product AUM concepts (metadata candidates only)")


if __name__ == "__main__":
    seed()
