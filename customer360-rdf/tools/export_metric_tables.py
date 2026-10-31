"""Export the reviewed metric-to-table inventory without exposing field mappings."""
import argparse
import importlib.util
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PG = ROOT / "department-pg"
OUTPUT = PG / "METRIC-TABLE-SOURCES.md"


def render():
    spec = importlib.util.spec_from_file_location("metric_table_export", PG / "build_cypher.py")
    builder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(builder)
    models = [module.load_model() for module in (builder.product_aum, builder.product_fees,
                                                builder.investment_metrics, builder.advisory_income,
                                                builder.bank_business)]
    metrics = [(model, c) for model in models for c in model["concepts"] if "table_sources" in c]
    by_id = {c['id']: (model, c) for model, c in metrics}
    summary = builder.securities_summary.load_model()
    builder.securities_summary.validate_model(summary, {cid: c for cid, (_, c) in by_id.items()})
    metrics.extend((summary, c) for c in summary['concepts'])
    department = builder.departments.load_model()
    builder.departments.validate_model(department, {c['id']: c for _, c in metrics})
    records = {}
    references = []

    def cite(record):
        key = (record["file"], tuple(record.get("lines", [])), record.get("sheet"))
        if key not in records:
            number = len(records) + 1
            records[key] = number
            path = ROOT.parents[1].joinpath(*Path(record["file"]).parts[1:])
            relative = Path(os.path.relpath(path, PG)).as_posix()
            locator = ("，第 " + "–".join(map(str, record["lines"])) + " 行" if "lines" in record
                       else "，工作表 `" + record["sheet"] + "`")
            references.append(f"- E{number}：[{path.name}](<{relative}>){locator}。")
        return "E" + str(records[key])

    total_aum = sum(c["class_uri"].endswith("AUM") for _, c in metrics)
    total_fee = sum(c["class_uri"].endswith("FeeIncome") for _, c in metrics)
    total_lum = sum(c["class_uri"].endswith("LUM") for _, c in metrics)
    total_interest = sum(c["class_uri"].endswith("InterestIncome") for _, c in metrics)
    if len(metrics) != total_aum + total_fee + total_lum + total_interest:
        raise ValueError("Every active metric must have a reviewed AUM/LUM/fee/interest classification")
    version = json.loads((ROOT / "build-config.json").read_text(encoding="utf-8"))["version"]
    rows = []
    for model, c in sorted(metrics, key=lambda item: (item[1]["subsidiary"],
                                                    not item[1]["class_uri"].endswith("AUM"), item[1]["id"])):
        inherited = c.get('lineage_mode') == 'via_component_metrics'
        source_rows = []
        if inherited:
            for component_id in sorted(c['component_metric_ids']):
                component_model, component = by_id[component_id]
                source_rows.extend((component_model, row) for row in component['table_sources']['tables'])
        else:
            source_rows = [(model, row) for row in c['table_sources']['tables']]
        primary = []
        support = []
        refs = set()
        for source_model, row in sorted(source_rows, key=lambda item: (item[1]["role"], item[1]["table"])):
            text = "`" + row["table"] + "`"
            if row["role"] == "primary":
                if text not in primary:
                    primary.append(text)
            else:
                text += "（" + {"valuation_support": "估值輔助", "date_lookup_only": "僅日期查詢"}[row["role"]] + "）"
                if text not in support:
                    support.append(text)
            refs.update(cite(source_model["evidence"][eid]) for eid in sorted(row["evidence"]))
        status = ('沿分項追溯' if inherited else
                  '部分範圍' if c['table_sources']['status'] == 'partial_scope' else '有表級證據')
        label = "<br>".join(sorted(refs, key=lambda ref: int(ref[1:])))
        rows.append("| " + " | ".join((c["name"], "<br>".join(primary), "<br>".join(support) or "—", status, label)) + " |")
    lines = [
        "# AUM／LUM／手收／利收指標底表對照", "",
        f"2026-10-24，RDF v{version}。共 {len(metrics)} 項指標：{total_aum} 項 AUM、{total_lum} 項 LUM、{total_fee} 項手收、{total_interest} 項利收。",
        "",
        "對應主體為指標，範圍統一參照金融商品。此表只列底表及其角色，不新增欄位映射、公式或執行規則；所有來源均為檔案觀察，未查驗資料庫。",
        f"{len(metrics)} 項指標均由 PG 私銀（bank.private_banking）採用，顯示名稱統一加上私銀並保留銀行／證券來源。採用範圍來自 departments.json，不代表資料權責、理專歸屬或可自動加總；既有指標 ID 保留。",
        "證券總 AUM／總手收只涵蓋目前已納入的 5／4 項分項，列出的底表沿 HAS_COMPONENT_METRIC 追溯，不另建立總指標到底表的直接連線。兩項總指標的計算均待 Tool 定義；總指標及其分項不可再次一起加總。",
        "",
        "| 指標 | 金額來源底表 | 輔助／查詢表 | 對應狀態 | 證據 |",
        "|---|---|---|---|---|", *rows, "",
        "## 覆蓋範圍與來源疑點", "",
        "- 證券總 AUM 排除股票設質估值；舊 SQL 把 AUM_027／028 都標證券／台股，不能只篩 COMP／PROD 取得本輪口徑。各分類月內最新日期仍是草稿，AUM_TMP02／AUM_REPORT 完整產製邏輯未提供，不當正式月底或同日口徑。",
        "- 證券總手收不含缺來源的台股手收，外股保留淨手收與原跨次月觀察。沿分項保留 primary／valuation_support／date_lookup_only；同一債券交易表在不同分項可以是金額來源或日期查詢，本表分角色顯示。涵蓋關係不等於 SUM 或新 RDF Property。",
        "- 六類統一納為金融商品。規劃型信託／信託保管有 AUM 與手收；外匯、開狀、黃金只有手收；放款有 LUM 與利收。不新增外匯、開狀、黃金或放款 AUM。",
        "- 外匯／黃金依 SQL 歸手收，PG 保留兌換／TMU／黃金損益性質；放款依 SQL 歸利收，保留毛利及利息收入減聯行息的來源口徑。共通手收／利收不限定為純手續費／純客戶利息。",
        "- 本批使用／定義部門為私人銀行，承作子公司另列；資料權責部門仍待定。bank-business-metrics 的七項手收參照銀行理專歸屬，實際員編映射未定；存款與放款利收不新增理專歸屬。",
        "- 規劃型信託的員工持股費用原文註記累計；與一般信託及保管分列，不核定差分、加總或去重。",
        "- FX 保留現貨 current／HS 分行條件差異及 TMU 排除 DCD／Cash Bond 的觀察，不將完整 FO108_W 視為外匯來源；不含 DCI TMU。開狀的攤提與換算疑點維持待定。",
        "- 放款 LUM 取數來源為台外幣 current／歷史四表；來源 LN_BAL／BAL_AMT、分行條件、日期標記與彙總會科範圍只作觀察。利收另補外幣 current 分支，日期與歷史覆蓋仍待定，兩指標不混用金額。",
        "- 通用商品手收只對應已盤點的 SI、SN、銀行基金、ETF、海外股票、ELI、FCI、DCI 純手續費及保險日報手收來源，非完整銀行總手收清冊，也不代表這些來源可直接相加。",
        "- DCI 沿用原指標 ID，涵蓋 INCOME_037 純手續費及 INCOME_038 的 DCD／TMU 損益；FO108_W 只取 DCD 分支，與 FX 分支區分。ELI／FCI 與 SI 各自獨立，欄位候選為空，沒有新增 AUM 或自動合計規則。",
        "- 銀行保險 AUM 保留原始投資金額，不直接視為保單市值或現金價值。保險手收沿用原 ID，涵蓋 INCOME_028 日報及 INCOME_029／030 月檔；PS 的客戶貢獻度性質保留。月檔移至次月、日月重疊及 UNION 整列去重只作來源觀察，不認定可直接加總。",
        "- 存款利收新增 INCOME_066 的三項歷史與外幣 current 金額來源；不把台幣 current 表作利收來源。GROSS_INCM 保留為業務收益；歷史初建與上月替換的私銀條件、UNION ALL／UNION 及日期範圍差異待 Tool 承接。",
        "- 銀行海外債券信託手收取 INCOME_031 的 BRHREBATEAMT + WKR028/100；自營手收取 INCOME_032 的 SUM(ABS(INC_AMT_NT))。信託／自營留在 PG，均沿用債券及海外商品分類；來源性質、空值與正負號規則不擅改。",
        "- 共用底表可能服務多項指標，表級對應不表示整張表只屬於某個商品，也沒有新增分類條件。",
        "- 銀行 ETF 直接繼承金控金融商品；PG 基金與 ETF 指標分列且不自動合計。ETF AUM 的實際分類取值仍待確認，手收保留來源 SQL 的 ETF 分支觀察；新欄位均 pending／null、候選為空。",
        "- 集合管理帳戶 AUM 參照銀行集合管理投資商品，直接繼承金控金融商品；來源 SQL 有集合分類，僅記表級來源。手收業務定義空白且原 CASE 順序有疑點，列為待確認，沒有新增手收指標、來源關係或欄位映射。",
        "- 依使用者決議移出證券股票設質 AUM；DSCSD.PBCMS_REPORTA03 的股票估值證據存於 ../archive/department-pg/history/stock-pledge-aum-retired-v0.15.0.json，不接為 LUM 金額來源。股票設質 LUM 與台股手收均待可確認底表；原台股庫存 AUM 保留。",
        "- 證券基金手收的債券交易表只出現在最大日期子查詢，保留為日期查詢來源。",
        "- 證券外股手收的 AM_SEC 僅供日期子查詢；原金額來源仍為 AM_SEC_M，不新增 current AM 金額來源。",
        "- 四項證券手收另引用 T_LAST_TWO_WORKDAYS。現有來源沒有其 schema／底層定義，保留為待釐清的期間輔助關係，未列成已辨識底表。",
        "- 底表只對應指標，理專、通聯及商品概念不直接連底表。原有欄位候選維持；本批新增欄位皆空映射。SQL 執行及計算由 Tool 承接，Tool 綁定與實作尚未完成。",
        "",
        "## 原始證據位置", "", *references, "",
        "維護來源：五份原 active 指標 JSON 的 table_sources，加 securities-summary-metrics.json 的分項涵蓋；departments.json 驗證私銀採用範圍。執行 tools/export_metric_tables.py 可重建本表；本表不作為模型輸入。", "",
    ]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    payload = render().encode("utf-8")
    if args.check:
        if OUTPUT.read_bytes() != payload:
            raise ValueError("Metric table inventory is stale; run tools/export_metric_tables.py")
        print("PASS: metric table inventory matches active JSON")
    else:
        OUTPUT.write_bytes(payload)
        print("Generated department-pg/METRIC-TABLE-SOURCES.md")


if __name__ == "__main__":
    main()
