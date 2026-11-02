"""Export the reviewed metric-to-table inventory without exposing field mappings."""
import argparse
import importlib.util
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
                                                builder.investment_metrics, builder.advisory_income)]
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
        "# AUM／手收指標底表對照", "",
        f"2026-10-22，RDF v0.10.0。共 {len(metrics)} 項指標：{total_aum} 項 AUM、{len(metrics)-total_aum} 項手收。",
        "",
        "對應主體為 AUM／手收指標。商品分類維持既有語意參照。此表只列底表及其角色，不新增欄位映射、公式或執行規則；所有來源均為檔案觀察，未查驗資料庫。",
        "",
        "| AUM／手收指標 | 金額來源底表 | 輔助／查詢表 | 對應狀態 | 證據 |",
        "|---|---|---|---|---|", *rows, "",
        "## 覆蓋範圍與來源疑點", "",
        "- 通用商品手收只對應已盤點的 SI、SN、銀行基金、海外股票、ELI、FCI 與 DCI 純手續費來源，非完整銀行總手收清冊，也不代表這些來源可直接相加。",
        "- 新增四項銀行手收只建立指標與底表，欄位候選為空；DCI 不含 TMU 損益，ELI／FCI 與 SI 各自獨立，沒有新增 AUM 或自動合計規則。",
        "- 共用底表可能服務多項指標，表級對應不表示整張表只屬於某個商品，也沒有新增分類條件。",
        "- 證券基金手收的債券交易表只出現在最大日期子查詢，保留為日期查詢來源。",
        "- 證券外股手收的 AM_SEC 僅供日期子查詢；原金額來源仍為 AM_SEC_M，不新增 current AM 金額來源。",
        "- 四項證券手收另引用 T_LAST_TWO_WORKDAYS。現有來源沒有其 schema／底層定義，保留為待釐清的期間輔助關係，未列成已辨識底表。",
        "- 理專、通聯及存款商品概念不在本次新增表級對應範圍。原有欄位候選與尚待確認事項維持。",
        "",
        "## 原始證據位置", "", *references, "",
        "維護來源：四份 active 指標 JSON 內各 concept 的 table_sources。執行 tools/export_metric_tables.py 可重建本表；本表不作為模型輸入。", "",
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
