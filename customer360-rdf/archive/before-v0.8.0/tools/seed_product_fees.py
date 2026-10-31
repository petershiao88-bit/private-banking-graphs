"""Seed the initial reviewed, file-evidenced PG fee candidates; not a SQL parser.

Refuses to overwrite the active JSON. Maintain subsequent edits in that JSON.
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PG = ROOT / "department-pg"
FH = "https://example.org/ontology/holding#"
BANK = "https://example.org/ontology/bank#"


def seed():
    target = PG / "product-fees.json"
    if target.exists():
        raise SystemExit("product-fees.json already exists; refusing to overwrite")
    template = json.loads((PG / "advisory-income.json").read_text(encoding="utf-8"))
    model = {key: template[key] for key in (
        "schema_version", "ontology_version", "status", "scope", "inference", "instance_mapping",
        "access_policy_status", "execution", "field_definitions")}
    model["evidence"] = {
        "sql_si": {"file": "Ontology/私銀智能問答/sources/sql/8.INCOME_DETAIL.sql", "lines": [131, 148], "encoding": "cp950"},
        "sql_offshore": {"file": "Ontology/私銀智能問答/sources/sql/8.INCOME_DETAIL.sql", "lines": [191, 202], "encoding": "cp950"},
        "sql_si_summary": {"file": "Ontology/私銀智能問答/sources/sql/9.INCOME_SMY.sql", "lines": [92, 100], "encoding": "cp950"},
        "sql_offshore_summary": {"file": "Ontology/私銀智能問答/sources/sql/9.INCOME_SMY.sql", "lines": [122, 130], "encoding": "cp950"},
        "metadata_si": {"file": "Ontology/私銀智能問答/sources/metadata/收入_metadata.xlsx", "sheet": "DSDEP.SI_PERFO_RPT", "rows": [2, 3, 8, 13, 21, 23, 29]},
        "metadata_offshore": {"file": "Ontology/私銀智能問答/sources/metadata/收入_metadata.xlsx", "sheet": "DSFND.PB_FUND_SPREAD_DAILY", "rows": [7, 8, 9, 13, 14, 18, 20, 31, 32]},
        "private_product_domestic": {"file": "Ontology/私銀智能問答/ontology/independent_concepts/concept_graph.json", "product_code": "bank_structured_domestic"},
        "private_product_offshore": {"file": "Ontology/私銀智能問答/ontology/independent_concepts/concept_graph.json", "product_code": "bank_structured_offshore"},
    }
    si_tables = ["DSDEP.SI_PERFO_RPT", "DSDEP.SI_PERFO_RPT_HS"]
    offshore_table = "DSFND.PB_FUND_SPREAD_DAILY"
    model["sources"] = [{"table": table, "status": "observed_in_files", "database_verified": False,
                         "evidence": ["sql_si"] if table.endswith("_HS") else ["sql_si", "metadata_si"]}
                        for table in si_tables]
    model["sources"].append({"table": offshore_table, "status": "observed_in_files",
                             "database_verified": False, "evidence": ["sql_offshore", "metadata_offshore"]})
    model["concepts"] = []
    model["relation_definitions"] = []
    for cid, name, product_code in (
        ("bank.domestic_structured_si_fee_income", "境內結構型商品手收（SI）", "bank_structured_domestic"),
        ("bank.offshore_structured_fee_income", "境外結構型商品手收", "bank_structured_offshore"),
    ):
        fields = [{"field": field, "status": "pending", "table": None, "column": None, "candidates": []}
                  for field in model["field_definitions"]]
        mappings = {item["field"]: item for item in fields}

        def candidate(field, table, column, meaning, evidence, applicability):
            mappings[field]["candidates"].append({"table": table, "column": column, "meaning": meaning,
                                                   "evidence": evidence, "applicability": applicability})

        if product_code == "bank_structured_domestic":
            for table in si_tables:
                candidate("customerId", table, "CUSTOMER_ID", "SQL 作為 cust_id 的客戶欄位。", ["sql_si"], "observed_in_sql")
                candidate("amount", table, "FEE_AMOUNT_TWD", "SQL 彙總的原始手續費欄位。", ["sql_si"], "observed_in_sql")
            for column, meaning in (("RM_ID", "所屬員編"), ("USER_ID", "員編")):
                candidate("employeeId", si_tables[0], column, meaning, ["metadata_si"], "pending_advisor_attribution")
            observations = {
                "coverage": "僅納入 INCOME_039 的 SI 分支；尚未納入 INCOME_040 ELI 與 INCOME_041 FCI，不宣稱完整境內手收。",
                "sql_output": "INCOME_039",
                "sql_group_by": ["CUSTOMER_ID", "TRADE_DATE", "S_PCC_CODE"],
                "sql_aggregation": "SUM(FEE_AMOUNT_TWD)",
                "sql_combination": "current／HS 各自聚合後 UNION（非 UNION ALL）",
                "sql_filters": [],
                "event_date": {"column": "TRADE_DATE", "meaning": "交易日", "evidence": ["sql_si", "metadata_si"]},
                "fee_currency": {"current_column": "FEE_AMOUNT_TWD", "current_unit": "TWD", "historical_unit": None,
                                 "note": "current metadata 說明為手續費換算台幣；歷史表欄位語意未獨立核對，selected currency 保持 null。", "evidence": ["metadata_si"]},
                "gaps": ["S_PCC_CODE 在 SQL 中使用，但提供的 current metadata 未列此欄位。",
                         "DEALNO 是交易單號，不當作商品 ID。",
                         "current metadata 的專員欄位不自動套用到 HS；來源也未證明哪些行員具有理專角色。",
                         "既有 SQL 已彙總並移除員編與商品識別，不直接用該彙總還原理專／單一商品手收。"],
                "evidence": ["sql_si", "metadata_si", "sql_si_summary", "private_product_domestic"],
            }
        else:
            candidate("customerId", offshore_table, "IDNO", "客戶 ID；SQL 作為 cust_id。", ["sql_offshore", "metadata_offshore"], "observed_in_sql")
            candidate("amount", offshore_table, "BRHREBATEAMT", "分行手續費；SQL 彙總欄位。", ["sql_offshore", "metadata_offshore"], "observed_in_sql")
            for column, meaning in (("BAOEMPID", "所屬專員編號"), ("SAOEMPID", "服務專員編號")):
                candidate("employeeId", offshore_table, column, meaning, ["metadata_offshore"], "pending_advisor_attribution")
            candidate("productId", offshore_table, "FUNDID", "metadata 定義為基金代碼，對 SN 商品的適用性待確認。", ["metadata_offshore"], "pending_sn_product_identifier")
            observations = {
                "coverage": "僅觀察 INCOME_042 的 SN 分行手續費範圍。",
                "sql_output": "INCOME_042",
                "sql_group_by": ["FEEDATE", "IDNO", "BAOPCCCODE"],
                "sql_aggregation": "SUM(BRHREBATEAMT)",
                "sql_combination": None,
                "sql_filters": ["FHID='SN'", "BAOPCCCODE LIKE '2E%'"],
                "event_date": {"column": "FEEDATE", "meaning": "手續費發生日", "sql_conversion": "TO_DATE(FEEDATE+19110000,'YYYYMMDD')", "evidence": ["sql_offshore", "metadata_offshore"]},
                "fee_currency": {"current_column": "BRHREBATEAMT", "current_unit": None, "historical_unit": None,
                                 "note": "分行手續費欄位未標明計價幣別，不從其他台幣金額欄位推定。", "evidence": ["metadata_offshore"]},
                "gaps": ["BAOPCCCODE 是所屬專員 PCC，不是行員編號。",
                         "所屬與服務專員的收入歸屬方式待確認，均不直接選定 employeeId。",
                         "FHID metadata 名稱為基金公司代碼；SN 商品分類依 SQL 條件與私銀產品語意辨識。",
                         "FUNDID 對 SN 的適用性待確認；SQL 彙總也未保留該欄位。"],
                "evidence": ["sql_offshore", "metadata_offshore", "sql_offshore_summary", "private_product_offshore"],
            }
        for field in ("customerId", "amount"):
            mappings[field]["status"] = "observed_raw_candidate"
        for field in ("employeeId", "productId"):
            if mappings[field]["candidates"]:
                mappings[field]["status"] = "pending_attribution" if field == "employeeId" else "pending_product_identity"
        model["concepts"].append({
            "id": cid, "name": name,
            "definition": "銀行境內 SI 結構型商品業務的手續費收入。" if product_code.endswith("domestic") else "銀行境外結構型商品業務的分行手續費收入。",
            "subsidiary": "bank", "department_owner": None, "class_uri": BANK + "BankFeeIncome",
            "specific_product_class_uri": BANK + "StructuredFinancialProduct",
            "private_product_code": product_code, "fields": fields, "observations": observations,
        })
        model["relation_definitions"].append({
            "id": cid + ".product", "name": name + "對應金融商品", "source_concept": cid,
            "property_uri": FH + "measuresProduct", "domain_uri": FH + "Metric",
            "range_uri": FH + "FinancialProduct", "target_class_uri": BANK + "StructuredFinancialProduct",
            "fields": [],
        })
        model["relation_definitions"].append({
            "id": cid + ".advisor", "name": name + "歸屬理專", "source_concept": cid,
            "property_uri": BANK + "attributedToAdvisor", "domain_uri": BANK + "BankFeeIncome",
            "range_uri": BANK + "FinancialAdvisor", "target_class_uri": BANK + "FinancialAdvisor",
            "fields": [],
        })
    target.write_text(json.dumps(model, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print("Created initial department-pg/product-fees.json (metadata candidates only)")


if __name__ == "__main__":
    seed()
