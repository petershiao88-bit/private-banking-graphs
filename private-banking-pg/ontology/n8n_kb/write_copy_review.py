import json
from pathlib import Path
from html import escape

H=Path(__file__).resolve().parent
w=json.loads((H/'main.copy.deployed.json').read_text(encoding='utf-8'))
audit=json.loads((H/'main_node_audit.json').read_text(encoding='utf-8'))
retained={
 'Router Input':'將聊天內容與 sessionId 整理成 user_query、session_id；後續完整問題由分類器與 metric router 傳遞。',
 'Get row(s)':'讀取既有 AUM Metric Registry；目前六種 AUM 類別，未配置 Income registry。',
 'Merge':'合併使用者問題與 registry，提供入口分類器。',
 'Router Model':'保留已使用的模型，負責 metric 分類。',
 'Structured Output Parser1':'保留入口分類結果 route、resolved_query、missing_fields 等欄位；完整性檢查仍只在主流程。',
 'Postgres Chat Memory':'沿用既有聊天記憶連線；副本測試使用新 session，不以舊 SQL 覆蓋本次 KB 證據。',
 'Response Model':'保留回答模型，由 Response 的新狀態規則產生自然中文。',
 '整理追問回覆':'保留原問題、上一輪追問與本次補充的整合，再交回入口分類器；已實測補年份流程。',
 '知識分支 Metric 清單':'獨立讀取原 registry，供知識問題的範圍檢查。',
 '是否可回答':'保留知識分支的原有範圍分流；未新增任何 IF。',
 'AUM 知識回答 Agent':'保留原知識解釋用途；此次只替換 SQL Reasoning Agent 的 KB。',
 '知識回答 Model':'保留知識回答模型與既有設定。',
 'AUM Knowledge Lookup':'仍服務獨立的知識回答分支。此分支沒有 metric router，不直接接需要 metricCodes 的新 KB。',
 '整理知識回答':'將知識 Agent 的 output/text 整理成最終聊天文字。',
}
for a in audit:
 if a['node'] in ['SQL KB','If']: a['action']='removed'
 elif a['node'] in retained and a['action']=='retained': a['reason']=retained[a['node']]
 nxt=[]
 for kind,groups in w['connections'].get(a['node'],{}).items():
  for group in groups:
   for edge in group: nxt.append(edge['node']+('（工具／模型連線）' if kind!='main' else ''))
 a['next']=nxt
(H/'main_node_audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2),encoding='utf-8')
tests=json.loads((H/'main_copy_live_tests.json').read_text(encoding='utf-8')) if (H/'main_copy_live_tests.json').exists() else []
labels={'changed':'已調整','retained':'保留','added':'新增','removed':'移除'}
rows=''.join('<tr><td>'+escape(a['node'])+'</td><td>'+labels[a['action']]+'</td><td>'+escape(a['reason'])+'</td><td>'+escape('、'.join(a['next']) or '—')+'</td></tr>' for a in audit)
test_rows=''.join('<tr><td>'+escape(t['name'])+'</td><td><pre>'+escape(t['observed'])+'</pre></td></tr>' for t in tests)
live=json.loads((H/'jev_main_live_single.json').read_text(encoding='utf-8'))
test_rows='<tr><td>原生 Jev：完整主流程</td><td><pre>'+escape(live['text'])+'</pre></td></tr>'+test_rows
html='''<!doctype html><html lang="zh-Hant"><meta charset="utf-8"><title>主流程副本逐節點檢查</title><style>body{font:16px/1.7 system-ui,sans-serif;max-width:1320px;margin:42px auto;padding:0 24px;color:#192a3b}h1{font-size:30px}table{border-collapse:collapse;width:100%;margin:24px 0}td,th{padding:12px;border:1px solid #d8e1e8;text-align:left;vertical-align:top}th{background:#eff4f8}td:first-child{min-width:150px}pre{white-space:pre-wrap;font:inherit;font-size:14px}.note{background:#fff4dc;padding:18px;border-radius:8px}a{color:#0761ac}</style><h1>智能查詢 — 概念圖 KB 測試版</h1>
<p>檢查日期：2026-10-07。副本已保存，保留為未發布的測試流程。原版的節點參數與連線已還原並比對整合前備份。</p>
<p><a href="https://chiang4901.app.n8n.cloud/workflow/nBrzHm3pNsVcOpeu">開啟副本</a> · <a href="https://chiang4901.app.n8n.cloud/workflow/glxRvnXZ1bCtknVi">開啟原版</a></p>
<p>資料查詢路徑：入口分類／必要追問 → metric router → 實際來源欄位清單 → 固定執行 Product Concept KB（原生 Jev Decisions API）→ SQL Chain → SQL 查詢 → 結果整理 → 回覆 → 保留全部候選機率。</p>
<p>KB v3 已發布，使用 typesafe/jev-1.13，實際回傳版本 typesafe/jev-1.13-20260917。每個產品與領域獨立保留 included／uncertain／excluded 分布，probability 為原始 included 機率；confidence 分開保留。沒有跨候選正規化、top-1 截斷或數值門檻；分流使用原生 choice 與歧義攔截，數值門檻尚未校準。詳細證據：<a href="jev_deployment_validation.json">本次驗證報告</a>。</p>
<div class="note">KB 的圖譜映射與執行資料庫的實際資料分開看待。目前 ds 業務 schema 可見五張存款來源表；基金所需來源尚未具備。測試確認缺來源時不虛構金額，並不表示基金 AUM 金額已驗證。主流程目前僅配置 AUM registry；KB 本身可接受 Income，但本副本會清楚回覆 Income 路由尚未配置。SQL 節點的來源比對支援目前的明確 FROM/JOIN 與簡單 CTE；它不是完整 SQL parser，複雜 SQL 語法仍需獨立測試。</div>
<h2>逐節點檢查</h2><p>目前副本有 35 個節點。審查表包含之前移除的 SQL KB／If，以及本次新增的保留候選機率節點。</p>
<table><thead><tr><th>節點</th><th>處理</th><th>檢查結果／理由</th><th>下一步</th></tr></thead><tbody>'''+rows+'''</tbody></table><h2>實際執行驗證</h2><p>第一列是此次端到端測試，後續列保留先前的基線紀錄。此次另測明確多產品、產品歧義與候選不相關，並對線上匯出通過 56 項契約檢查及 19 項實際機率證據檢查。測試固定資料已移除。</p><table><tr><th>案例</th><th>觀察結果</th></tr>'''+test_rows+'''</table></html>'''
(H/'main-copy-review.html').write_text(html,encoding='utf-8')
print('Wrote per-node review for',len(audit),'nodes.')
