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
    total_other = len(metrics) - total_aum - total_fee
    version = json.loads((ROOT / "build-config.json").read_text(encoding="utf-8"))["version"]
    rows = []
    for model, c in sorted(metrics, key=lambda item: (item[1]["subsidiary"],
                                                    not item[1]["class_uri"].endswith("AUM"), item[1]["id"])):
        mapping = c["table_sources"]
        primary = []
        support = []
        refs = set()
        for row in sorted(mapping["tables"], key=lambda item: (item["role"], item["table"])):
            text = "`" + row["table"] + "`"
            if row["role"] == "primary":
                primary.append(text)
            else:
                text += "（" + {"valuation_support": "估值輔助", "date_lookup_only": "僅日期查詢"}[row["role"]] + "）"
                support.append(text)
            refs.update(cite(model["evidence"][eid]) for eid in sorted(row["evidence"]))
        status = "部分範圍" if mapping["status"] == "partial_scope" else "有表級證據"
        label = "<br>".join(sorted(refs, key=lambda ref: int(ref[1:])))
        rows.append("| " + " | ".join((c["name"], "<br>".join(primary), "<br>".join(support) or "—", status, label)) + " |")
    lines = [
        "# AUM／手收與其他收益指標底表對照", "",
        f"2026-10-24，RDF v{version}。共 {len(metrics)} 項指標：{total_aum} 項 AUM、{total_fee} 項手收、{total_other} 項其他收益／損益。",
        "",
        "對應主體為指標，範圍參照金融商品或金融服務。此表只列底表及其角色，不新增欄位映射、公式或執行規則；所有來源均為檔案觀察，未查驗資料庫。",
        "",
        "| 指標 | 金額來源底表 | 輔助／查詢表 | 對應狀態 | 證據 |",
        "|---|---|---|---|---|", *rows, "",
        "## 覆蓋範圍與來源疑點", "",
        "- 新增規劃型信託與信託保管各自的 AUM／手收、開狀手收、外匯／黃金交易損益及放款利收。信託、保管、外匯與開狀屬金融服務；黃金及放款屬金融商品，來源仍接在指標上。",
        "- 外匯／黃金交易損益與放款利收參照一般 fh:Metric，未歸為 FeeIncome；HAS_BUSINESS_SCOPE 是 PG metadata 範圍參照，非新增 RDF Object Property。其收入期間元素留在 PG，不使用手收專屬屬性。",
        "- 規劃型信託的員工持股費用原文註記累計；與一般信託及保管分列，不核定差分、加總或去重。",
        "- FX 保留現貨 current／HS 分行條件差異及 TMU 排除 DCD／Cash Bond 的觀察，不將完整 FO108_W 視為外匯來源；不含 DCI TMU。開狀的攤提與換算疑點維持待定。",
        "- 放款來源台幣 GROSS_INCM 的 metadata 為毛利，外幣為利息收入減聯行息收入；保留來源業務收益口徑，非直接認定純客戶利息。本輪沒有放款或黃金 AUM。",
        "- 通用商品手收只對應已盤點的 SI、SN、銀行基金、ETF、海外股票、ELI、FCI、DCI 純手續費及保險日報手收來源，非完整銀行總手收清冊，也不代表這些來源可直接相加。",
        "- 新增四項銀行手收只建立指標與底表，欄位候選為空；DCI 不含 TMU 損益，ELI／FCI 與 SI 各自獨立，沒有新增 AUM 或自動合計規則。",
        "- 銀行保險 AUM 的來源意義保留為原始投資金額，不直接視為保單市值或現金價值。保險手收目前僅涵蓋日報；兩項月檔的客戶貢獻度未併入，仍為部分範圍。保單／契約及欄位映射保持暫緩。",
        "- 共用底表可能服務多項指標，表級對應不表示整張表只屬於某個商品，也沒有新增分類條件。",
        "- 銀行 ETF 直接繼承金控金融商品；PG 基金與 ETF 指標分列且不自動合計。ETF AUM 的實際分類取值仍待確認，手收保留來源 SQL 的 ETF 分支觀察；新欄位均 pending／null、候選為空。",
        "- 集合管理帳戶 AUM 參照銀行集合管理投資商品，直接繼承金控金融商品；來源 SQL 有集合分類，僅記表級來源。手收業務定義空白且原 CASE 順序有疑點，列為待確認，沒有新增手收指標、來源關係或欄位映射。",
        "- 證券股票設質 AUM 依需求表及彙總 SQL 歸入證券台股，衡量設質股票估值，非借款或可融資金額；僅建立 DSCSD.PBCMS_REPORTA03 表級來源。與台股庫存的重疊及日期意義待定，不新增自動加總／去重規則。台股手收仍缺來源定義。",
        "- 證券基金手收的債券交易表只出現在最大日期子查詢，保留為日期查詢來源。",
        "- 證券外股手收的 AM_SEC 僅供日期子查詢；原金額來源仍為 AM_SEC_M，不新增 current AM 金額來源。",
        "- 四項證券手收另引用 T_LAST_TWO_WORKDAYS。現有來源沒有其 schema／底層定義，保留為待釐清的期間輔助關係，未列成已辨識底表。",
        "- 理專、通聯及存款商品概念不在本次新增表級對應範圍。原有欄位候選與尚待確認事項維持。",
        "",
        "## 原始證據位置", "", *references, "",
        "維護來源：五份 active 指標 JSON 內各 concept 的 table_sources。執行 tools/export_metric_tables.py 可重建本表；本表不作為模型輸入。", "",
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
