"""Build an evidence-backed Income business dictionary and normalized graph plan.

The source ontology and SQL are read only. This script does not execute Oracle SQL.
Python 3 and openpyxl are used to read the accompanying metadata workbook.
"""

from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path
import re

import openpyxl


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "ontology"
DOMAIN = "income"


def key(kind: str, value: str) -> str:
    return f"{DOMAIN}:{kind}:{value}"


def clean_sql(text: str) -> str:
    """Blank SQL comments while preserving literals and line numbers."""
    return re.sub(
        r"'(?:(?:'')|[^'])*'|/\*[\s\S]*?\*/|--[^\n]*",
        lambda match: match[0] if match[0].startswith("'") else re.sub(r"[^\n]", " ", match[0]),
        text,
    )


def sql_inventory() -> tuple[list[dict], dict[str, str]]:
    records = []
    contents = {}
    for name in ("8.INCOME_DETAIL.sql", "9.INCOME_SMY.sql", "X-INCOME_MOTHLY.sql"):
        text = (ROOT / "sources" / "sql" / name).read_bytes().decode("cp950").replace("\r\n", "\n")
        contents[name] = text
        active = clean_sql(text)
        for match in re.finditer(r"\b(?:CREATE\s+TABLE|INSERT\s+INTO)\s+(INCOME_[A-Z0-9_]+)\b", active, re.I):
            end = active.find(";", match.start())
            if end < 0:
                raise ValueError(f"No SQL terminator after {name}:{match.start()}")
            code = active[match.start():end + 1]
            refs = sorted(set(re.findall(r"\b(?:FROM|JOIN)\s+([A-Z][A-Z0-9_]*(?:\.[A-Z][A-Z0-9_]*)?)", code, re.I)))
            refs = [ref.upper() for ref in refs]
            line_start = text.count("\n", 0, match.start()) + 1
            line_end = text.count("\n", 0, end) + 1
            records.append({
                "id": f"{name}:L{line_start}", "file": f"sources/sql/{name}",
                "output": match[1].upper(),
                "operation": "insert_refresh" if match[0].upper().startswith("INSERT") else "create",
                "lineStart": line_start, "lineEnd": line_end,
                "sql": text[match.start():end + 1], "references": refs,
                "setOperation": "UNION ALL" if re.search(r"\bUNION\s+ALL\b", code, re.I) else "UNION" if re.search(r"\bUNION\b", code, re.I) else "none",
                "status": "observed_in_sql",
            })
    return records, contents


def dictionary() -> dict:
    metrics = [
        {"code": "income_total_customer_month", "name": "每客戶每月總收入", "definition": "10._INCOME_ROA.sql 的收入子查詢按 CUST_ID 與 SUBSTR(YYYYMMDD,1,6) 加總 INCOME_TMP02.AMT；涵蓋 SQL 歸類的手收及利收。", "grain": "CUST_ID × YYYYMM", "implementation": "INCOME_TMP02", "formula": "SUM(AMT) GROUP BY CUST_ID, SUBSTR(YYYYMMDD,1,6)", "status": "observed_in_sql"},
        {"code": "fee_income", "name": "手收（SQL分類）", "definition": "TYP='手收' 的收入；其中包含手續費、貢獻度及部分損益欄位。", "filter": "TYP='手收'", "status": "inferred"},
        {"code": "bank_fee_income", "name": "銀行手收", "definition": "TYP='手收' 且 PROD_TYPE='銀行' 的 AMT。", "filter": "TYP='手收' AND PROD_TYPE='銀行'", "status": "inferred"},
        {"code": "securities_fee_income", "name": "證券手收", "definition": "TYP='手收' 且 PROD_TYPE='證券' 的 AMT。", "filter": "TYP='手收' AND PROD_TYPE='證券'", "status": "inferred"},
        {"code": "interest_income", "name": "利息收入", "definition": "TYP='利收' 的存款與放款 AMT。", "filter": "TYP='利收'", "status": "inferred"},
        {"code": "deposit_interest_income", "name": "存款利收", "definition": "INCOME_066 以 GROSS_INCM 彙總存款利收；現況來源僅使用外幣存款表。", "filter": "TYP='利收' AND SUB_TYPE='存款'", "status": "observed_in_sql"},
        {"code": "loan_interest_income", "name": "放款利收", "definition": "INCOME_067 以台幣 GROSS_INCM 及外幣 INT_INCM-CB_INT_AMT 彙總；現況來源僅使用外幣放款表。", "filter": "TYP='利收' AND SUB_TYPE='放款'", "status": "observed_in_sql"},
        {"code": "report_income_amount", "name": "組織收入報表金額", "definition": "INCOME_REPORT 排除 PRFT_CNTR_CD 為 NULL 的列，再按日期、收入類型、機構、產品與組織加總 AMT。", "implementation": "INCOME_REPORT", "formula": "SUM(AMT)", "grain": "YYYYMMDD × TYP × PROD_TYPE × SUB_TYPE × 組織", "status": "observed_in_sql"},
        {"code": "report_row_count", "name": "組織收入報表列數", "definition": "INCOME_REPORT 的 COUNT(*) 是各組的來源列數，不能直接當成不重複客戶數或交易數。", "implementation": "INCOME_REPORT", "formula": "COUNT(*)", "status": "observed_in_sql"},
    ]
    products = []

    def product(code, name, parent, stages, classification, basis, **extra):
        products.append({"code": code, "name": name, "parentMetric": parent, "stages": stages,
                         "classification": classification, "amountBasis": basis,
                         "includedByCurrentSql": True, "status": "inferred", **extra})

    product("bank_insurance", "銀行保險", "bank_fee_income", ["INCOME_028", "INCOME_029", "INCOME_030"], "手收／銀行／保險", "COMM_AMT 或 PS（metadata 定義為客戶貢獻度）", overlapRisk=True)
    product("bank_bond_trust", "海外債券（信託）", "bank_fee_income", ["INCOME_031"], "手收／銀行／海外債券_信託", "SUM(BRHREBATEAMT + WKR028/100)")
    product("bank_bond_proprietary", "外國債券（自營）", "bank_fee_income", ["INCOME_032"], "手收／銀行／外國債券_自營", "SUM(ABS(INC_AMT_NT))", signRule="absolute_value")
    for code, name, value in [("bank_fund", "銀行基金", "基金"), ("bank_etf", "銀行ETF", "ETF"), ("bank_overseas_stock", "銀行海外股票", "海外股票")]:
        product(code, name, "bank_fee_income", ["INCOME_033_034_035_036"], f"手收／銀行／{value}", "SUM(BRHREBATEAMT)", stageFilter=f"FH_TYP='{value}'")
    product("bank_collective_account", "集合管理帳戶（定義存在，SQL分支被遮蔽）", "bank_fee_income", ["INCOME_033_034_035_036"], "預期：手收／銀行／集合管理帳戶", "SUM(BRHREBATEAMT)", includedByCurrentSql=False, status="metadata_sql_conflict", stageFilter="FHID starts TA/TB/TD/TE", reason="CASE 第一個 NOT IN 條件先把這些代碼歸到基金。")
    product("bank_dci", "銀行DCI", "bank_fee_income", ["INCOME_037", "INCOME_038"], "手收／銀行／DCI", "FEE_AMOUNT_TWD + DCD 的 TMUPROFIT（來源以 UNION 匯集）")
    product("bank_structured_domestic", "境內結構型商品", "bank_fee_income", ["INCOME_039", "INCOME_040", "INCOME_041"], "手收／銀行／結構型_境內", "SI/FCI FEE_AMOUNT_TWD；ELI FEE_AMOUNT")
    product("bank_structured_offshore", "境外結構型商品", "bank_fee_income", ["INCOME_042"], "手收／銀行／結構型_境外", "SN 的 SUM(BRHREBATEAMT)")
    product("bank_fx", "銀行FX收入", "bank_fee_income", ["INCOME_043", "INCOME_044"], "手收／銀行／FX", "BAL_AMT_TWD（兌換損益）與 TMUPROFIT")
    product("bank_lc", "銀行開狀", "bank_fee_income", ["INCOME_045"], "手收／銀行／開狀", "SUM(FEE_AMT)；SQL未做 ÷12 或匯率換算", definitionConflict=True)
    product("bank_planned_trust", "規劃型信託／保管", "bank_fee_income", ["INCOME_046", "INCOME_047", "INCOME_048"], "手收／銀行／規劃型信託", "借券、管理、成立費；Fee+CreateFee；保管FEE", cumulativeRisk=True)
    product("bank_gold", "銀行黃金", "bank_fee_income", ["INCOME_049"], "手收／銀行／黃金", "SUM(PLAMT_TWD)")
    for code, name, value in [("securities_bond", "證券複委託債券", "債券"), ("securities_structured", "證券複委託結構型商品", "結構型商品")]:
        product(code, name, "securities_fee_income", ["INCOME_051_054"], f"手收／證券／{value}", "SUM(CFEE*FXRATE)", stageFilter=f"FLG='{value}'")
    product("securities_fund", "證券複委託基金", "securities_fee_income", ["INCOME_052"], "手收／證券／基金", "SUM(WKA31)", snapshotReferenceRisk=True)
    product("securities_foreign_stock", "證券複委託外國股票", "securities_fee_income", ["INCOME_053"], "手收／證券／外國股票", "SUM((CFEE-ABFEE)*FXRATE)", signRule="preserve_source_sign", sourceSelectionRisk=True)
    product("deposit_interest", "存款利息", "deposit_interest_income", ["INCOME_066"], "利收／銀行／存款", "SUM(GROSS_INCM)")
    product("loan_interest", "放款利息", "loan_interest_income", ["INCOME_067"], "利收／銀行／放款", "台幣 SUM(GROSS_INCM) + 外幣 SUM(INT_INCM-CB_INT_AMT)")

    rules = []

    def rule(code, name, description, stages=(), metrics=(), products=(), status="observed_in_sql", **extra):
        rules.append({"code": code, "name": name, "description": description,
                      "stages": list(stages), "metrics": list(metrics), "products": list(products),
                      "status": status, **extra})

    rule("final_union_distinct", "24條收入來源整列去重", "INCOME_TMP01 使用 UNION，對 TYP、PROD_TYPE、SUB_TYPE、NM、CUST_ID、YYYYMMDD、AMT 完全相同的輸出列去重；不按保單或交易ID去重。", stages=["INCOME_TMP01"])
    rule("customer_month_sum", "依收入認列月份加總", "ROA收入子查詢對 INCOME_TMP02 依 CUST_ID × SUBSTR(YYYYMMDD,1,6) 執行 SUM(AMT)，沒有取每月最後一日或最新一筆；YYYYMMDD 的來源口徑依產品而異。", metrics=["income_total_customer_month"])
    rule("insurance_next_month", "保險PS認列次月", "INCOME_029/030 將 LST_MTN_DT ADD_MONTHS(...,1) 後轉成 YYYYMMDD；029 排除空 PS，030 篩 OPEN_ACCOUNT='Y'。028 則使用 APPLY_DT。", stages=["INCOME_028", "INCOME_029", "INCOME_030"])
    rule("insurance_overlap", "保險日月來源重疊待確認", "metadata 建議調整版本第28-30列將028定為日檔保險手收、029定為月批保險手收、030定為月批保險續期手收。三者在SQL都納入；028的NM為部門名稱，029/030為空，UNION不能依保單去重。文件未證明日檔與月批來源互斥。", products=["bank_insurance"], status="requires_business_confirmation", issue=True)
    rule("insurance_ps_meaning", "保險PS與COMM_AMT口徑待確認", "業務參考表第29/30列明確指定保險／續期手收取PS，與SQL一致。欄位metadata則將PS稱為客戶貢獻度，並另有BRANCH_FEE手續費欄位。保留取值PS，但不能單憑欄位名稱證明PS與COMM_AMT完全等價。", stages=["INCOME_029", "INCOME_030"], status="requires_business_confirmation", issue=True)
    rule("securities_recognition_month", "證券月底認列次月", "依 T_LAST_TWO_WORKDAYS.LAST2_WD 判斷交易／清算日；日期 >= LAST2_WD 時歸入次月，其他歸當月，輸出日期均為該月01日。行事曆缺漏時比較為NULL，CASE會落入當月ELSE。", stages=["INCOME_051_054_TMP01", "INCOME_051_054_TMP02", "INCOME_052_TMP01", "INCOME_052_TMP02", "INCOME_053_TMP01", "INCOME_053_TMP02"])
    rule("bond_absolute_value", "自營債券金額取絕對值", "INCOME_032 先對 INC_AMT_NT 取 ABS 再 SUM，因此此來源的負值也轉成正值。", stages=["INCOME_032"])
    rule("stock_negative_preserved", "外國股票保留來源正負號", "INCOME_053 使用 (CFEE-ABFEE)*FXRATE，沒有截負為0；metadata 也提到報表可能將負手收調成0，而儀表盤可依DW資料。這份圖保留現行SQL口徑。", products=["securities_foreign_stock"])
    rule("fund_case_shadow", "集合管理帳戶分支被基金遮蔽", "TA/TB/TD/TE 開頭不在 PS/CB/YB/SN 清單內，因此先命中 CASE 第一條 NOT IN 並輸出基金，後面的集合管理帳戶 WHEN 無法命中。未修改來源SQL。", stages=["INCOME_033_034_035_036"], products=["bank_collective_account", "bank_fund"], status="metadata_sql_conflict", issue=True)
    rule("lc_formula_gap", "開狀攤提與匯率口徑差異", "metadata 建議調整版本第45列描述 FEE_AMT ÷12 * 前日清算匯率；SQL實作 SUM(FEE_AMT)，只篩有效 FEE_END_DATE，未攤提或換匯。", stages=["INCOME_045"], status="metadata_sql_conflict", issue=True)
    rule("deposit_refresh_union", "存款月更新使用UNION", "存款歷史TMP02用 UNION ALL；上月更新TMP_DETAIL_04卻用 UNION。不同存款來源若 CUST_ID、YYYYMMDD、AMT 恰好相同，月更新可能先去掉其中一列再SUM。放款月更新使用 UNION ALL。", stages=["INCOME_066_TMP02", "INCOME_066_TMP_DETAIL_04", "INCOME_067_TMP_DETAIL_03"], status="observed_in_sql", issue=True)
    rule("monthly_refresh_scope", "上月重載與篩選範圍", "月更新先DELETE上一月份再INSERT；月更新來源只有月份條件，沒有歷史初始化的私銀 PRFT_CNTR_CD 篩選。X-INCOME_MOTHLY.sql 註明已放回每日項目，不能當作額外可加總收入。", stages=["INCOME_066", "INCOME_067"], issue=True)
    rule("current_foreign_only", "存放款現況只讀外幣", "存款 TMP03 只讀 DEP_FN_ACCT.GROSS_INCM；放款 TMP03 只讀 LN_FN_ACCT 的 INT_INCM-CB_INT_AMT。SQL註解說台幣現況表無 GROSS_INCM；台幣當期涵蓋範圍需核對。", stages=["INCOME_066_TMP03", "INCOME_067_TMP03"], status="requires_business_confirmation", issue=True)
    rule("customer_org_join", "按客戶與月份串聯組織", "INCOME_TMP02 LEFT JOIN PB_CUST_005，連接 CUST_ID 與收入月份=YYYYMM；若客戶月份在PB_CUST_005不唯一，收入列可能被放大。目前未取得資料驗證唯一性。", stages=["INCOME_TMP02"], issue=True)
    rule("report_scope", "報表排除無組織收入", "INCOME_REPORT 只保留 PRFT_CNTR_CD IS NOT NULL；ROA的收入子查詢對INCOME_TMP02未加這個條件，再LEFT JOIN PB_CUST_TMP06的客戶月份母體。兩個輸出的收入涵蓋範圍需分開理解。", metrics=["report_income_amount", "income_total_customer_month"])
    rule("report_count", "CNT是列數", "INCOME_REPORT 使用 COUNT(*)，沒有 COUNT(DISTINCT CUST_ID)，也沒有依交易ID計數。", metrics=["report_row_count"])
    rule("fund_snapshot_reference", "基金現況引用債券最大快照日", "INCOME_052_TMP02 的 MAX(YYYYMMDD) 子查詢取自 PB_BONDTRADM_SEC，不是 PB_FUNDTRADM_SEC；是否共用快照日需確認。", stages=["INCOME_052_TMP02"], status="requires_business_confirmation", issue=True)
    rule("stock_am_source", "股票AM現況來源待確認", "INCOME_053_TMP02 的PM分支讀 PB_STOCKTRADM_PM_SEC，但AM分支仍讀 PB_STOCKTRADM_AM_SEC_M，並與非_M的最大快照日比較。保留實際來源以供核對。", stages=["INCOME_053_TMP02"], status="requires_business_confirmation", issue=True)
    rule("historical_precondition", "歷史TMP01需要既有表", "INCOME_066/067 初始化仍FROM TMP01，但同檔的TMP01建表區塊被 /*...*/ 註解。將TMP01標為外部前置依賴，保留註解定義，不能宣稱整份SQL可從空庫獨立執行。", stages=["INCOME_066", "INCOME_067", "INCOME_066_TMP01", "INCOME_067_TMP01"], issue=True)
    rule("trust_cumulative", "員工持股費用期間待確認", "INCOME_047 註解標示累計，實際按 BALDATE SUM(FEE+CREATEFEE)；metadata 將FEE稱管理費（每月）、CREATEFEE稱成立費（一次性）。若每日重複累計值，直接月SUM可能重複認列，需依資料確認。", stages=["INCOME_047"], status="requires_business_confirmation", issue=True)

    return {
        "id": DOMAIN, "version": "0.1", "status": "inferred_business_dictionary",
        "scope": "現有Income JSON、staging SQL與metadata的定義及血緣；沒有客戶收入實際資料。",
        "sourceFiles": ["ontology/Income Ontology.json", "sources/sql/8.INCOME_DETAIL.sql", "sources/sql/9.INCOME_SMY.sql", "sources/sql/10._INCOME_ROA.sql", "sources/sql/X-INCOME_MOTHLY.sql", "sources/metadata/收入_metadata.xlsx", "sources/metadata/收入_20250527.xlsx"],
        "metrics": metrics,
        "metricHierarchy": [["income_total_customer_month", "fee_income"], ["income_total_customer_month", "interest_income"], ["fee_income", "bank_fee_income"], ["fee_income", "securities_fee_income"], ["interest_income", "deposit_interest_income"], ["interest_income", "loan_interest_income"]],
        "products": products, "rules": rules,
        "dimensions": [
            {"code": "customer", "name": "客戶", "field": "CUST_ID", "definition": "各來源ID由SQL映射為CUST_ID；沒有額外的身分合併規則。"},
            {"code": "recognition_date", "name": "收入認列日／月份", "field": "YYYYMMDD / SUBSTR(YYYYMMDD,1,6)", "definition": "各來源日期不同，包含交易日、寫入日次月與月份01日。"},
            {"code": "income_type", "name": "收入類型", "field": "TYP", "definition": "手收或利收，依9.INCOME_SMY.sql常數分類。"},
            {"code": "institution", "name": "機構別", "field": "PROD_TYPE", "definition": "銀行或證券。"},
            {"code": "product", "name": "產品分類", "field": "SUB_TYPE", "definition": "來源產品分類、FH_TYP或FLG。"},
            {"code": "organization", "name": "組織歸屬", "field": "PRFT_CNTR_CD / SHT_NM", "definition": "依PB_CUST_005的客戶月份取得，與來源NM/PCCODE不同。"},
            {"code": "source_nm", "name": "來源識別NM", "field": "NM", "definition": "保險028為DEPT_EASY_NM，部分來源為PCCODE，其他為空；不是統一的組織鍵。"},
        ],
        "pendingBusinessQuestions": ["保險028/029/030是否互斥且可加總？PS是否等同收入？", "集合管理帳戶分類與開狀計價應以哪份定義為準？", "每日累計／月更新的收入是否會重複認列？", "各來源是否皆已採一致的新台幣收入口徑？"],
        "insuranceSources": [
            {"stage": "INCOME_028", "name": "保險手收（日檔）", "basis": "COMM_AMT", "date": "APPLY_DT", "reference": "建議調整版本第28列"},
            {"stage": "INCOME_029", "name": "保險手收（月批）", "basis": "PS", "date": "LST_MTN_DT次月", "reference": "建議調整版本第29列"},
            {"stage": "INCOME_030", "name": "保險續期手收（月批）", "basis": "PS", "date": "LST_MTN_DT次月", "reference": "建議調整版本第30列"},
        ],
    }


class Graph:
    def __init__(self):
        self.nodes = {}
        self.edges = {}

    def node(self, label, node_key, **props):
        props = {name: value for name, value in props.items() if value is not None}
        if node_key in self.nodes and self.nodes[node_key]["label"] != label:
            raise ValueError(f"Conflicting labels for {node_key}")
        self.nodes.setdefault(node_key, {"label": label, "key": node_key, "properties": {}})["properties"].update(props)
        return node_key

    def edge(self, source, kind, target, **props):
        self.edges[(source, kind, target)] = {"from": source, "to": target, "type": kind, "properties": props}


def main():
    source = OUT / "Income Ontology.json"
    ontology = json.loads(source.read_text(encoding="utf-8-sig"))
    if ontology["domain"]["id"] != DOMAIN:
        raise ValueError("Expected income ontology")
    doc = dictionary()
    records, contents = sql_inventory()
    graph = Graph()
    root = key("metric", "income_total_customer_month")
    ontology_key = graph.node("Ontology", key("ontology", DOMAIN), name="收入Ontology", sourceFile=source.name, sourceSha256=hashlib.sha256(source.read_bytes()).hexdigest(), termCount=len(ontology["terms"]), sourceJson=json.dumps({name: value for name, value in ontology.items() if name != "terms"}, ensure_ascii=False))
    graph.edge(root, "DESCRIBED_BY_ONTOLOGY", ontology_key)

    stages = set(record["output"] for record in records)
    stages.update(t["term"].split(".", 1)[0] for t in ontology["terms"])
    stages.update(ref for record in records for ref in record["references"] if ref.startswith("INCOME_"))
    evidence_by_stage = {}
    for stage in sorted(stages):
        graph.node("StagingOutput", key("stage", stage), name=stage, outputObject=stage, status="observed_in_sql" if any(r["output"] == stage for r in records) else "external_precondition", lineageMethod="SQL reference inventory, manually reviewed")
    for item in doc["insuranceSources"]:
        graph.node("StagingOutput", key("stage", item["stage"]), name=item["name"], amountBasis=item["basis"], recognitionDate=item["date"], businessReference=item["reference"])
    for record in records:
        stage = key("stage", record["output"])
        sql_key = graph.node("SqlEvidence", key("sql", record["id"]), name=f"{record['output']} ({record['operation']})", **record)
        graph.edge(stage, "SUPPORTED_BY_SQL", sql_key)
        source_key = graph.node("SourceDocument", key("source", record["file"]), name=Path(record["file"]).name, path=record["file"], encoding="cp950")
        graph.edge(sql_key, "FROM_DOCUMENT", source_key)
        evidence_by_stage.setdefault(record["output"], []).append(sql_key)
        for ref in record["references"]:
            if ref.startswith("INCOME_"):
                graph.edge(stage, "REFRESHED_FROM" if record["operation"] == "insert_refresh" else "DEPENDS_ON", key("stage", ref))
            else:
                table_key = graph.node("PhysicalTable", key("table", ref), name=ref, physicalTable=ref, status="observed_in_sql")
                graph.edge(stage, "READS_FROM", table_key)
                graph.edge(sql_key, "READS_FROM", table_key)

    # These two active reads depend on preexisting historical tables. Their local
    # definitions are commented out, and are retained with that exact status.
    for stage in ("INCOME_066_TMP01", "INCOME_067_TMP01"):
        text = contents["8.INCOME_DETAIL.sql"]
        start = re.search(rf"create table {stage}\b", text, re.I).start()
        end = text.index(";", start) + 1
        snippet = text[start:end]
        sql_key = graph.node("SqlEvidence", key("sql", stage + ":commented"), name=stage + "（註解定義）", sql=snippet, file="sources/sql/8.INCOME_DETAIL.sql", lineStart=text.count("\n", 0, start) + 1, status="commented_out_sql")
        graph.edge(key("stage", stage), "DOCUMENTED_BY_SQL", sql_key)
        graph.edge(sql_key, "FROM_DOCUMENT", key("source", "sources/sql/8.INCOME_DETAIL.sql"))
        for ref in sorted(set(re.findall(r"\bFROM\s+([A-Z][A-Z0-9_]*\.[A-Z][A-Z0-9_]*)", clean_sql(snippet), re.I))):
            table_key = graph.node("PhysicalTable", key("table", ref.upper()), name=ref.upper(), physicalTable=ref.upper())
            graph.edge(sql_key, "READS_FROM", table_key)

    metadata = {}
    workbook = openpyxl.load_workbook(ROOT / "sources" / "metadata" / "收入_metadata.xlsx", read_only=True, data_only=True)
    for sheet in workbook:
        for row in sheet.iter_rows(min_row=2, values_only=True):
            if len(row) >= 5 and row[1]:
                metadata[(sheet.title.upper(), str(row[1]).upper())] = {"description": str(row[4]) if row[4] else "", "dataType": str(row[2]) if row[2] else "", "metadataSheet": sheet.title}
    workbook.close()
    metadata_source = graph.node("SourceDocument", key("source", "sources/metadata/收入_metadata.xlsx"), name="收入_metadata.xlsx", path="sources/metadata/收入_metadata.xlsx")
    graph.edge(ontology_key, "HAS_SOURCE", metadata_source)

    for term in ontology["terms"]:
        stage_name = term["term"].split(".", 1)[0]
        term_key = graph.node("Term", key("term", term["id"]), name=term["displayName"], term=term["term"], id=term["id"], status=term.get("status"), formula=term.get("formula"), formulas=term.get("formulas", []), grain=term.get("grain", []), dimensionCandidates=term.get("dimensionCandidates", []), aliases=term.get("aliases", []), branchIndex=term.get("evidence", {}).get("branchIndex"), queryEnabled=term.get("queryEnabled", False), sourceJson=json.dumps(term, ensure_ascii=False))
        graph.edge(ontology_key, "HAS_TERM", term_key)
        graph.edge(key("stage", stage_name), "DESCRIBED_BY", term_key)
        for sql_key in evidence_by_stage.get(stage_name, []):
            graph.edge(term_key, "SUPPORTED_BY_SQL", sql_key)
        for prop in term.get("evidence", {}).get("sourceProperties", []):
            physical = prop.get("physicalTable")
            column = prop.get("column")
            if not physical or not column:
                continue
            physical, column = physical.upper(), column.upper()
            table_key = graph.node("PhysicalTable", key("table", physical), name=physical, physicalTable=physical)
            exact = metadata.get((physical, column))
            template = metadata.get((physical.removesuffix("_HS"), column)) if not exact else None
            column_key = graph.node("PhysicalColumn", key("column", physical + "." + column), name=column, physicalTable=physical, column=column, mappingStatus=prop.get("mappingStatus"), metadataStatus="exact" if exact else "history_table_template" if template else "not_found", **(exact or template or {}))
            graph.edge(table_key, "HAS_COLUMN", column_key)
            graph.edge(term_key, "USES_SOURCE_COLUMN", column_key)
            if exact or template:
                graph.edge(column_key, "DESCRIBED_BY_METADATA", metadata_source)

    for metric in doc["metrics"]:
        props = {name: value for name, value in metric.items() if name != "implementation"}
        graph.node("BusinessMetric", key("metric", metric["code"]), **props)
        if metric.get("implementation"):
            graph.edge(key("metric", metric["code"]), "IMPLEMENTED_BY", key("stage", metric["implementation"]))
    for parent, child in doc["metricHierarchy"]:
        graph.edge(key("metric", parent), "HAS_COMPONENT", key("metric", child))
    for report in ["report_income_amount", "report_row_count"]:
        graph.edge(root, "HAS_REPORT_METRIC", key("metric", report))
    for product in doc["products"]:
        product_key = graph.node("ProductCategory", key("product", product["code"]), **{name: value for name, value in product.items() if name not in {"stages", "parentMetric"}})
        graph.edge(key("metric", product["parentMetric"]), "INCLUDES_PRODUCT" if product["includedByCurrentSql"] else "DECLARES_PRODUCT", product_key)
        for stage in product["stages"]:
            graph.edge(product_key, "IMPLEMENTED_BY" if product["includedByCurrentSql"] else "DECLARED_IMPLEMENTATION", key("stage", stage), filter=product.get("stageFilter", "all rows"))
    for dimension in doc["dimensions"]:
        dimension_key = graph.node("BusinessDimension", key("dimension", dimension["code"]), status="inferred", **dimension)
        graph.edge(root, "HAS_DIMENSION", dimension_key)
    for rule in doc["rules"]:
        rule_key = graph.node("CalculationRule", key("rule", rule["code"]), **{name: value for name, value in rule.items() if name not in {"stages", "metrics", "products"}})
        for kind, field in [("stage", "stages"), ("metric", "metrics"), ("product", "products")]:
            for code in rule[field]:
                graph.edge(key(kind, code), "USES_CALCULATION_RULE", rule_key)
    roa_path = ROOT / "sources" / "sql" / "10._INCOME_ROA.sql"
    roa_text = roa_path.read_bytes().decode("cp950").replace("\r\n", "\n")
    roa_sql = graph.node("SqlEvidence", key("sql", "customer_month_aggregate"), name="ROA收入子查詢", sql="SELECT CUST_ID, SUBSTR(YYYYMMDD,1,6) YYYYMM, SUM(AMT) AMT FROM INCOME_TMP02 GROUP BY CUST_ID, SUBSTR(YYYYMMDD,1,6)", sourceSql=roa_text, status="observed_in_sql", note="完整ROA檔案產出收入、AUM及放款彙總欄位；註解提到ROA/ROBA，但SQL未執行除法計算比率。")
    roa_source = graph.node("SourceDocument", key("source", "sources/sql/10._INCOME_ROA.sql"), name=roa_path.name, path="sources/sql/10._INCOME_ROA.sql", encoding="cp950")
    graph.edge(root, "SUPPORTED_BY_SQL", roa_sql)
    graph.edge(roa_sql, "FROM_DOCUMENT", roa_source)
    population = graph.node("PhysicalTable", key("table", "PB_CUST_TMP06"), name="PB_CUST_TMP06", physicalTable="PB_CUST_TMP06", definition="ROA客戶月份母體")
    graph.edge(roa_sql, "READS_FROM", population)
    business_source = graph.node("SourceDocument", key("source", "sources/metadata/收入_20250527.xlsx"), name="收入_20250527.xlsx", path="sources/metadata/收入_20250527.xlsx", evidenceSheet="建議調整版本", status="historical_business_reference")
    graph.edge(ontology_key, "HAS_SOURCE", business_source)
    for item in doc["insuranceSources"]:
        graph.edge(key("stage", item["stage"]), "SUPPORTED_BY_METADATA", business_source, reference=item["reference"])
    graph.edge(key("rule", "insurance_overlap"), "SUPPORTED_BY_METADATA", business_source, reference="建議調整版本第28-30列")
    for code, row in [("insurance_ps_meaning", "收入_metadata.xlsx:兩張KPI表.PS/BRANCH_FEE"), ("fund_case_shadow", "建議調整版本:33/36"), ("lc_formula_gap", "建議調整版本:45"), ("stock_negative_preserved", "建議調整版本:53"), ("trust_cumulative", "收入_metadata.xlsx:DSEBS.EBTS_ACT_CntAUMBal_PB.FEE/CREATEFEE")]:
        graph.edge(key("rule", code), "SUPPORTED_BY_METADATA", metadata_source if row.startswith("收入_metadata") else business_source, reference=row)

    plan = {"ontologyId": DOMAIN, "rootKey": root, "nodes": list(graph.nodes.values()), "relationships": list(graph.edges.values())}
    doc["ontologySummary"] = {"termCount": len(ontology["terms"]), "branchTermCount": sum(t.get("evidence", {}).get("branchIndex") is not None for t in ontology["terms"]), "reviewedTermCount": sum(bool(t.get("review", {}).get("confirmedBy")) for t in ontology["terms"]), "stageCount": len(stages), "sqlStatementCount": len(records)}
    doc["stagingRegistry"] = [{name: value for name, value in record.items() if name != "sql"} for record in records]
    for name, data in [("Income_business_dictionary.json", doc), ("Income_graph_plan.json", plan)]:
        (OUT / name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"nodes": len(graph.nodes), "relationships": len(graph.edges), "labels": dict(Counter(node["label"] for node in graph.nodes.values())), "dictionary": doc["ontologySummary"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
