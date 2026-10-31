"""One-time path/documentation updates after the manifest moves."""
from pathlib import Path
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parents[2]
DEST = Path(__file__).resolve().parent
manifest = json.loads((DEST/'move-manifest.json').read_text(encoding='utf-8'))
for item in manifest:
    p = ROOT/item['destination']
    for record in item['files']:
        f = p/record['path'] if record['path'] else p
        assert hashlib.sha256(f.read_bytes()).hexdigest() == record['sha256'], f
    assert not (ROOT/item['source']).exists()
print('All 915 moved files match their original SHA-256 before path edits.')

for p in (ROOT/'tests/pg').glob('*.py'):
    s = p.read_text(encoding='utf-8-sig')
    s = re.sub(r'HERE\s*=\s*Path\(__file__\)\.resolve\(\)\.parent\b',
               'HERE = Path(__file__).resolve().parents[2] / "department-pg"', s)
    s = s.replace('Path(__file__).resolve().parent.parent', 'Path(__file__).resolve().parents[2]')
    s = re.sub(r'HERE\s*/\s*([\x27\x22])(history|drafts)(/[^\x27\x22]*)?\1',
               lambda m: 'HERE.parent / '+m[1]+'archive/department-pg/'+m[2]+(m[3] or '')+m[1], s)
    s = s.replace('discover -s department-pg', 'discover -s tests/pg')
    p.write_text(s, encoding='utf-8')

# Cross-test imports are existing contracts; register their new folder for discovery.
(ROOT/'tests/pg/__init__.py').write_text(
    '"""PG regression tests; model inputs remain in department-pg."""\n'
    'import sys\nfrom pathlib import Path\n'
    'sys.path.insert(0, str(Path(__file__).resolve().parent))\n', encoding='utf-8')

for rel in ('tools/export_metric_tables.py', 'department-pg/METRIC-TABLE-SOURCES.md'):
    p = ROOT/rel
    s = p.read_text(encoding='utf-8').replace('history/stock-pledge-aum-retired-v0.15.0.json',
                                          '../archive/department-pg/history/stock-pledge-aum-retired-v0.15.0.json')
    p.write_text(s, encoding='utf-8')

overview = '''## 先看這裡（2026-10-27 整理）

目前有效模型是 **v0.16.0**，模型最後更新為 2026-10-24。只要看私銀指標，先開 [44 項指標與來源表](department-pg/METRIC-TABLE-SOURCES.md)。

| 要找的內容 | 目前位置 |
|---|---|
| 完整 RDF／OWL | [customer360-ontology.ttl](customer360-ontology.ttl)、[customer360-ontology.owl](customer360-ontology.owl)，由來源模組產生 |
| 可編輯的 RDF 來源 | 根目錄五份 TTL：holding-core、bank-deposit、bank-common、bank-investment-products、securities-common |
| 最新 PG | [department-pg/](department-pg/) 內九份業務 JSON；model.json 只含通聯，不代表整份 PG |
| 圖譜、問答、推理與交接展示 | [semantica-poc/README.md](semantica-poc/README.md)；執行該資料夾的 launch.ps1 |
| 回歸測試 | tests/（RDF／Fabric）、tests/pg/（PG）；介面與推理測試留在 semantica-poc/ |
| 最新可選 Fabric 匯出 | outputs/fabric-v0.16.0/ 與同版 ZIP，屬完整技術 metadata 匯出 |
| 歷史版本、草稿與舊實作 | [archive/README.md](archive/README.md)，不是目前建置來源 |

本機圖譜：http://127.0.0.1:8866/；圖譜問答：http://127.0.0.1:8866/ask；交接示範：http://127.0.0.1:8866/handoff。需先啟動服務。
目前問答本體推理使用 **Semantica Reasoner**；舊 HermiT 已歸檔。畫布保持 146 節點／246 關係，只顯示一個 RDF 私銀部門，連到 44 項 PG 指標。以下建模紀錄的 PG metadata 數量與畫布顯示數量不同。

'''
p=ROOT/'README.md'
s=p.read_text(encoding='utf-8')
s=s.replace('department-pg/history/', 'archive/department-pg/history/')
s=s.replace('discover -s department-pg', 'discover -s tests/pg')
s=s.replace('history／drafts 不參與建置。', 'archive/department-pg/ 下的 history／drafts 不參與建置。')
s=s.replace('未執行來源 SQL、真實資料庫查核、完整 OWL reasoner、SHACL、GUI、Neo4j部署或Git提交。權限、帳戶、分行／數位、實體欄位映射與畫圖仍暫緩。',
    '上述為模型建置階段紀錄。後續圖譜、問答、規則推理及示範 SHACL 已於 semantica-poc 實作，詳見其 README；真實資料庫查核、SQL 執行與 Neo4j 部署仍未完成。')
s=s.replace('tools/legacy-v0.2.0', 'archive/cleanup-20261027/tools/legacy-v0.2.0')
s=s.replace('outputs/department-v0.16.0/apply.py', 'archive/cleanup-20261027/outputs/department-v0.16.0/apply.py')
head, rest = s.split('\n',1)
p.write_text(head+'\n\n'+overview+rest.lstrip(),encoding='utf-8')

p=ROOT/'department-pg/README.md'
s=p.read_text(encoding='utf-8').replace('department-pg/history/', '../archive/department-pg/history/')
s=s.replace('見 history/', '見 ../archive/department-pg/history/')
s='''# 最新 PG 檔案入口

先看 [44 項指標與來源表](METRIC-TABLE-SOURCES.md)，再依名稱開啟對應的九份業務 JSON。model.json 僅含通聯；model.cypher 是九份 JSON 的合併輸出。
測試與比對輔助程式已移至 ../tests/pg/；舊修訂紀錄與未採用草稿移至 ../archive/department-pg/。本資料夾保留有效模型、schema 與建置／驗證程式。

從專案根目錄執行測試：`.venv\\Scripts\\python.exe -X utf8 -B -m unittest discover -s tests/pg -v`。

'''+s
p.write_text(s,encoding='utf-8')

p=ROOT/'semantica-poc/README.md'
s=p.read_text(encoding='utf-8')
s=s.replace('沒有使用 LLM、付費 API、業務 SQL、Neo4j 或 Fabric 雲端服務。',
    '開啟圖譜本身不呼叫 LLM；問答送出問題時才透過 OpenRouter 呼叫模型。沒有執行業務 SQL、Neo4j 或 Fabric 雲端服務。')
s=s.replace('?????? link', '「圖譜問答」 link')
s+='''
## 檔案整理（2026-10-27）

目前使用 semantica_reasoner.py。舊 HermiT 程式、Java runtime、安裝下載檔、舊推理報告與服務日誌，已集中至 ../archive/cleanup-20261027/semantica-poc/；它們不是目前執行入口。舊程式保留供歷史查閱，若要重跑需恢復原相對路徑。
目前 .venv、.env、圖譜 data 快照、Semantica 推理快取及交接政策均留在原處。歷史與本次搬移清單見 ../archive/README.md。
'''
p.write_text(s,encoding='utf-8')

p=ROOT/'semantica-poc/UI-VERIFICATION.md'
s=p.read_text(encoding='utf-8')
# Retain current evidence for each feature; outdated Q&A/HermiT records remain in backup.
start=s.index('## Graph Q&A integration')
end=s.index('## Agent 交接驗證')
s=s[:start]+s[end:]
s=s.replace('舊HermiT程式、runtime、測試與歷史報告留作參考', '舊HermiT程式、runtime、測試與歷史報告已移至 ../archive/cleanup-20261027/semantica-poc/ 留作參考')
s+='\n整理前的完整歷史驗收紀錄：../archive/cleanup-20261027/before-edits/semantica-poc/UI-VERIFICATION.md。\n'
p.write_text(s,encoding='utf-8')

p=ROOT/'pyrightconfig.json'
cfg=json.loads(p.read_text(encoding='utf-8'))
cfg['exclude']=['.venv','archive','semantica-poc/.venv']
p.write_text(json.dumps(cfg,indent=2)+'\n',encoding='utf-8')

p=ROOT.parent/'README.md'
s=p.read_text(encoding='utf-8').replace('RDF／OWL v0.4.0', 'RDF／OWL v0.16.0')
s=s.replace('2. `customer360-rdf-owl/HANDOFF-ZED-RDF-PG-20261022.md`\n3. `customer360-rdf-owl/README.md`',
            '2. `customer360-rdf-owl/README.md`（最新版檔案入口）\n3. `customer360-rdf-owl/department-pg/METRIC-TABLE-SOURCES.md`（44 項私銀指標）')
p.write_text(s,encoding='utf-8')

(ROOT/'archive/README.md').write_text('''# 歷史檔案索引

最新版入口：[專案 README](../README.md)。此資料夾保存歷史版本；目前建置不以這裡的模型作為輸入。

| 位置 | 內容 |
|---|---|
| before-* | 原有各版模型快照，保留原名；目前回歸測試仍讀取其中的比對基準 |
| department-pg/history/ | 過往審閱決議、指標退場與修訂記錄；測試仍會驗證 |
| department-pg/drafts/ | 未採用的員工存款草稿；不參與建置 |
| cleanup-20261027/ | 本次搬入的舊文件、一次性工具與輸出、HermiT 舊實作及下載套件 |
| cleanup-20261027/before-edits/ | 本次修改前的文件、測試與輔助程式原文 |
| cleanup-20261027/move-manifest.json | 原路徑 → 新路徑、每個搬移檔案的大小與原始 SHA-256 |

沒有刪除模型歷史。歷史程式與文件保留當時內容，可能引用舊路徑，不能直接當目前的執行入口；需要重跑時請先在獨立副本恢復原目錄結構。最新 PG 測試已移至 ../tests/pg/ 並更新路徑。
''',encoding='utf-8')
print('Updated test paths and current documentation.')
