"""評測報告：report.md（給人讀，先設定、再總表、再逐題）與 report.html（可篩選的單檔頁面）。"""

import html
import json
from pathlib import Path

from .agent import MODES
from .evaluate import OUTCOMES, load_results, summarize

MODE_LABELS = {"baseline": "baseline｜平鋪資料字典", "context": "context｜角色 context 包",
               "plan": "plan｜語意計畫＋本體檢查", "tools": "tools｜工具查詢＋本體檢查",
               "workflow": "workflow｜LLM 填範本＋本體執行＋檢查"}
MODE_HOW = {"baseline": "全部 44 項指標平鋪成資料字典放進 system prompt；沒有類別階層、權限、待定範圍與規則（模擬寬表 agent）。",
            "context": "依角色過濾後的 context 包整包放進 system prompt；一次呼叫，回答＋JSON 結果。本體檢查只記錄、不擋。",
            "plan": "同一份 context 包；先交語意計畫 → 本體檢查（不過就帶錯誤重試）→ 通過後只帶已驗證的指標卡片作答。",
            "tools": "只給類別骨架與規則；指標細節用 6 個本體工具查詢；最後的 JSON 結果一樣要通過本體檢查。",
            "workflow": "只給類別骨架與 3 個本體型別化範本；LLM 只填欄位或拆成多個呼叫，由本體執行，結果經本體檢查（有質疑就把執行結果退回一次）後才作答。"}
OUTCOME_LABELS = {"correct": "正確", "safe_miss": "保守未答", "silent_wrong": "默默答錯", "format_error": "格式錯誤"}
DECISION_LABELS = {"answer": "回答", "clarify": "澄清", "out_of_scope": "不在範圍", "blocked": "系統擋下",
                   "unparsed": "無法解析", "error": "呼叫失敗", None: "—"}


def write(run_dir):
    run_dir = Path(run_dir)
    results = load_results(run_dir)
    meta_path = run_dir / "run.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
    summary = summarize(results)
    (run_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (run_dir / "report.md").write_text(render_markdown(meta, summary, results), encoding="utf-8")
    (run_dir / "report.html").write_text(render_html(meta, summary, results), encoding="utf-8")
    return summary


# ---------------------------------------------------------------------- Markdown


def render_markdown(meta, summary, results):
    modes = [m for m in MODES if m in summary["modes"]]
    md = [f"# 單 agent CoT 評測報告（{meta.get('started', '')}）", ""]
    if meta.get("dry_run") or meta.get("backend") not in (None, "openai"):
        md += [f"> ⚠️ 這次用的是 `{meta.get('backend')}` 後端（{meta.get('backend_note', '')}），"
               "結果只用來檢查流程，不代表模型能力。", ""]
    md += ["## 1. 實驗設定", "",
           "| 項目 | 內容 |", "|---|---|",
           f"| 模型 | `{meta.get('model', '—')}` |",
           f"| 端點 | `{meta.get('base_url', '—')}` |",
           f"| 工具呼叫 | {meta.get('tool_calling', '—')} |",
           f"| 溫度／max_tokens | {meta.get('temperature', '—')}／{meta.get('max_tokens', '—')} |",
           f"| 本體 | v{meta.get('ontology_version', '—')}（{meta.get('ontology_state', '')}）|",
           f"| 知識指紋 | `{meta.get('knowledge_fingerprint', '')[:16]}` |",
           f"| 題庫 | {meta.get('question_count', len({r['question_id'] for r in results}))} 題，"
           f"重複 {meta.get('repeat', 1)} 次 |", ""]
    md += ["### 本體怎麼進入 CoT（四種模式）", "", "| 模式 | 做法 | context 大小（估計 token） |", "|---|---|---|"]
    for mode in modes:
        md.append(f"| {MODE_LABELS[mode]} | {MODE_HOW[mode]} | {summary['modes'][mode]['pack_tokens_est']} |")
    if meta.get("packs"):
        md += ["", "### 角色 context 包", "", "| 檔案 | 角色 | 層級 | 指標數 | 估計 token | 實測 token |", "|---|---|---|---|---|---|"]
        for p in meta["packs"]:
            md.append(f"| {p['file']} | {p['role']} | {p['level']} | {p['metrics']} | {p['tokens_est']} | "
                      f"{p.get('tokens_exact') or '—'} |")
    md += ["", "## 2. 結果總表", "",
           "- **正確**：決策可接受，指標／類別／必要說明都對，沒有越權或自編 ID。",
           "- **保守未答**：沒答對，但選了澄清、不在範圍，或被系統擋下；不會誤導使用者。",
           "- **默默答錯**：給了回答但內容錯（最需要避免）。", "",
           "| 模式 | 正確 | 默默答錯 | 保守未答 | 格式錯誤 | 越權 | 自編 ID | 檢查首次通過 | 被擋下 | 若有檢查會擋 | 平均輸入 token | 平均輸出 token | 平均秒數 | 平均呼叫 | 平均工具 |",
           "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for mode in modes:
        s = summary["modes"][mode]
        md.append("| " + " | ".join([
            mode, f"{s['correct']}/{s['n']}（{_pct(s['accuracy'])}）", f"{s['silent_wrong']}（{_pct(s['silent_wrong_rate'])}）",
            str(s["safe_miss"]), str(s["format_error"]), str(s["leaks"]), str(s["invalid_ids"]),
            _pct(s["gate_first_pass"]) if s["gate_first_pass"] is not None else "—", str(s["blocked"]),
            str(s["would_block"]) if mode in ("baseline", "context") else "—",
            _num(s["avg_prompt_tokens"]), _num(s["avg_completion_tokens"]), _num(s["avg_latency"]),
            _num(s["avg_llm_calls"]), _num(s["avg_tool_calls"])]) + " |")
    md += ["", "### 依題型", "", "| 題型 | " + " | ".join(modes) + " |", "|---|" + "---|" * len(modes)]
    for cat, per in summary["categories"].items():
        md.append(f"| {cat} | " + " | ".join(f"{per[m]['correct']}/{per[m]['n']}" if m in per else "—" for m in modes) + " |")
    md += ["", "## 3. 逐題紀錄", ""]
    by_q = {}
    for r in results:
        by_q.setdefault(r["question_id"], []).append(r)
    for qid, items in by_q.items():
        first = items[0]
        e = first["expect"]
        md += [f"### {qid}｜{first['category']}｜角色 {first['role']}", "", f"> {first['question']}", "",
               f"期望：決策 {'／'.join(DECISION_LABELS.get(d, d) for d in e['decision'])}"
               + (f"；指標（{e['match']}）{_ids(e['metrics'])}" if e.get("metrics") else "")
               + (f"；類別 {_ids(e['classes'])}" if e.get("classes") else "")
               + (f"；禁止 {_ids(e['forbidden'])}" if e.get("forbidden") else "")
               + (f"；需提到 {'／'.join(e['mention_any'])}" if e.get("mention_any") else "")]
        if first.get("note"):
            md.append(f"說明：{first['note']}")
        md.append("")
        for r in sorted(items, key=lambda r: (MODES.index(r["mode"]) if r["mode"] in MODES else 9, r["repeat"])):
            t = r["transcript"]
            tag = f"**{r['mode']}**" + (f"（第 {r['repeat'] + 1} 次）" if r["repeat"] else "")
            md += [f"#### {tag}：{OUTCOME_LABELS[r['outcome']]}｜{DECISION_LABELS.get(t.get('decision'), t.get('decision'))}"
                   f"｜{_ids(t.get('metrics') or [])}", ""]
            if r["problems"]:
                md += ["問題：" + "；".join(r["problems"]), ""]
            for i, g in enumerate(t.get("gate") or [], 1):
                state = "通過" if g["passed"] else "未通過"
                label = "本體檢查" if g.get("enforced") else "本體檢查（只記錄）"
                line = f"- {label}第 {i} 次：{state}"
                if g["errors"]:
                    line += "；" + "；".join(f"[{x['code']}] {x['message']}" for x in g["errors"])
                if g.get("challenges"):
                    line += "；質疑：" + "；".join(f"[{x['code']}] {x['message']}" for x in g["challenges"])
                if g["warnings"]:
                    line += "；提醒：" + "；".join(x["message"] for x in g["warnings"])
                md.append(line)
            tool_lines = []
            for call in t.get("calls") or []:
                for c, res in zip(call["tool_calls"], call["tool_results"] or [None] * len(call["tool_calls"])):
                    tool_lines.append(f"- 工具 `{c['name']}({_short(c['arguments'], 120)})` → {_short(json.dumps(res, ensure_ascii=False), 160)}")
            if tool_lines:
                md += [""] + tool_lines
            md += ["", "回答：", "", _quote(t.get("answer") or t.get("error") or "（無）"), ""]
            md.append(f"<sub>呼叫 {t.get('llm_calls', 0)} 次、工具 {t.get('tool_calls', 0)} 次、"
                      f"token {t.get('usage', {}).get('prompt_tokens', 0)}＋{t.get('usage', {}).get('completion_tokens', 0)}、"
                      f"{t.get('latency', 0)} 秒</sub>")
            md.append("")
    return "\n".join(md) + "\n"


def _pct(x):
    return "—" if x is None else f"{x * 100:.0f}%"


def _num(x):
    return "—" if x is None else (f"{x:.0f}" if x >= 100 else f"{x}")


def _ids(ids):
    return "、".join(f"`{i}`" for i in ids) if ids else "（無）"


def _short(text, n):
    text = text if isinstance(text, str) else json.dumps(text, ensure_ascii=False)
    return text if len(text) <= n else text[:n] + "…"


def _quote(text):
    return "\n".join("> " + line if line.strip() else ">" for line in text.strip().splitlines())


# ---------------------------------------------------------------------- HTML


def render_html(meta, summary, results):
    data = {"meta": meta, "summary": summary, "modes": [m for m in MODES if m in summary["modes"]],
            "modeLabels": MODE_LABELS, "modeHow": MODE_HOW, "outcomeLabels": OUTCOME_LABELS,
            "decisionLabels": {str(k): v for k, v in DECISION_LABELS.items()},
            "results": [{k: v for k, v in r.items()} for r in results]}
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    return HTML_TEMPLATE.replace("__DATA__", payload).replace("__TITLE__", html.escape(
        f"單 agent CoT 評測報告 {meta.get('started', '')}"))


HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
<style>
:root{--bg:#f6f7f9;--card:#fff;--ink:#1d2330;--muted:#667085;--line:#e4e7ec;--accent:#2f5bd3;
--ok:#1a7f4b;--okbg:#e7f6ee;--warn:#9a6700;--warnbg:#fff4d6;--bad:#b42318;--badbg:#fdecea;--grey:#475467;--greybg:#eef0f3}
*{box-sizing:border-box}body{margin:0;font:14px/1.6 -apple-system,BlinkMacSystemFont,"PingFang TC","Noto Sans TC","Microsoft JhengHei",sans-serif;background:var(--bg);color:var(--ink)}
header{background:var(--card);border-bottom:1px solid var(--line);padding:18px 28px}
h1{font-size:20px;margin:0 0 4px}h2{font-size:16px;margin:28px 0 10px}h3{font-size:15px;margin:0}
main{max-width:1280px;margin:0 auto;padding:8px 28px 60px}
.banner{background:var(--warnbg);color:var(--warn);padding:8px 12px;border-radius:8px;margin-top:10px}
.muted{color:var(--muted)}.mono{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:12.5px}
table{border-collapse:collapse;width:100%;background:var(--card);border:1px solid var(--line);border-radius:10px;overflow:hidden}
th,td{padding:7px 10px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}th{background:#fafbfc;font-weight:600;color:var(--grey);font-size:13px}
tr:last-child td{border-bottom:none}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:12px}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px}
.big{font-size:26px;font-weight:700}.bar{height:8px;border-radius:4px;background:var(--greybg);overflow:hidden;display:flex;margin:6px 0}
.bar span{display:block;height:100%}
.pill{display:inline-block;padding:1px 8px;border-radius:999px;font-size:12px;font-weight:600;white-space:nowrap}
.o-correct{background:var(--okbg);color:var(--ok)}.o-safe_miss{background:var(--warnbg);color:var(--warn)}
.o-silent_wrong{background:var(--badbg);color:var(--bad)}.o-format_error{background:var(--greybg);color:var(--grey)}
.filters{display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin:12px 0;position:sticky;top:0;background:var(--bg);padding:8px 0;z-index:2}
select,input{font:inherit;padding:5px 8px;border:1px solid var(--line);border-radius:6px;background:#fff}
.q{background:var(--card);border:1px solid var(--line);border-radius:10px;margin:10px 0}
.q>summary{list-style:none;cursor:pointer;padding:12px 14px;display:flex;gap:10px;align-items:center;flex-wrap:wrap}
.q>summary::-webkit-details-marker{display:none}.q .qtext{flex:1;min-width:260px}
.dots{display:flex;gap:4px}.dot{width:12px;height:12px;border-radius:3px}
.d-correct{background:var(--ok)}.d-safe_miss{background:#e0a100}.d-silent_wrong{background:var(--bad)}.d-format_error{background:#98a2b3}
.body{padding:0 14px 14px;border-top:1px solid var(--line)}
.exp{background:#fafbfc;border-radius:8px;padding:8px 10px;margin:10px 0}
.run{border:1px solid var(--line);border-radius:8px;margin:10px 0;padding:10px 12px}
.run h4{margin:0 0 6px;font-size:14px;display:flex;gap:8px;align-items:center;flex-wrap:wrap}
.answer{white-space:pre-wrap;background:#fbfbfd;border-left:3px solid var(--accent);padding:8px 10px;border-radius:4px;margin:8px 0}
.gate{font-size:13px;margin:2px 0}.gate.fail{color:var(--bad)}.gate.pass{color:var(--ok)}
.tool{font-size:12.5px;margin:2px 0;color:var(--grey)}
details.raw summary{cursor:pointer;color:var(--muted);font-size:12.5px}pre{white-space:pre-wrap;word-break:break-word;background:#f3f4f6;padding:8px;border-radius:6px;font-size:12px;max-height:420px;overflow:auto}
</style></head><body>
<header><h1 id="title"></h1><div class="muted" id="sub"></div><div id="banner"></div></header>
<main>
<h2>1. 實驗設定</h2><div id="setup"></div>
<h2>2. 結果總表</h2><div class="grid" id="cards"></div><div style="margin-top:12px" id="table"></div>
<h2>依題型</h2><div id="cats"></div>
<h2>3. 逐題紀錄</h2>
<div class="filters">
 <label>模式 <select id="f-mode"><option value="">全部</option></select></label>
 <label>結果 <select id="f-outcome"><option value="">全部</option></select></label>
 <label>題型 <select id="f-cat"><option value="">全部</option></select></label>
 <input id="f-text" placeholder="搜尋題目或指標 ID" size="24">
 <span class="muted" id="f-count"></span>
 <span class="muted" id="f-legend"></span>
</div>
<div id="questions"></div>
</main>
<script>
const D = __DATA__;
const $ = s => document.querySelector(s);
const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const pct = x => x == null ? '—' : Math.round(x * 100) + '%';
const ids = a => (a && a.length) ? a.map(x => `<span class="mono">${esc(x)}</span>`).join('、') : '（無）';
const m = D.meta;
$('#title').textContent = '單 agent CoT 評測報告';
$('#sub').textContent = `${m.started || ''}｜模型 ${m.model || '—'}｜本體 v${m.ontology_version || '—'}`;
if (m.backend && m.backend !== 'openai') $('#banner').innerHTML = `<div class="banner">這次用的是 <b>${esc(m.backend)}</b> 後端（${esc(m.backend_note || '')}），結果只用來檢查流程，不代表模型能力。</div>`;
const rows = [['模型', m.model], ['端點', m.base_url], ['工具呼叫', m.tool_calling], ['溫度／max_tokens', `${m.temperature ?? '—'}／${m.max_tokens ?? '—'}`],
  ['本體', `v${m.ontology_version || '—'}（${m.ontology_state || ''}）`], ['知識指紋', (m.knowledge_fingerprint || '').slice(0, 16)],
  ['題庫', `${m.question_count ?? '—'} 題，重複 ${m.repeat ?? 1} 次`]];
let setup = '<table>' + rows.map(r => `<tr><th style="width:160px">${r[0]}</th><td class="mono">${esc(r[1] ?? '—')}</td></tr>`).join('') + '</table>';
setup += '<h3 style="margin:16px 0 8px">本體怎麼進入 CoT</h3><table><tr><th>模式</th><th>做法</th><th>context（估計 token）</th></tr>' +
  D.modes.map(x => `<tr><td><b>${esc(D.modeLabels[x])}</b></td><td>${esc(D.modeHow[x])}</td><td>${D.summary.modes[x].pack_tokens_est ?? '—'}</td></tr>`).join('') + '</table>';
if (m.packs) setup += '<h3 style="margin:16px 0 8px">角色 context 包</h3><table><tr><th>檔案</th><th>角色</th><th>層級</th><th>指標數</th><th>估計 token</th><th>實測 token</th></tr>' +
  m.packs.map(p => `<tr><td class="mono">${esc(p.file)}</td><td>${esc(p.role)}</td><td>${esc(p.level)}</td><td>${p.metrics}</td><td>${p.tokens_est}</td><td>${p.tokens_exact ?? '—'}</td></tr>`).join('') + '</table>';
$('#setup').innerHTML = setup;
const colors = {correct:'var(--ok)', safe_miss:'#e0a100', silent_wrong:'var(--bad)', format_error:'#98a2b3'};
$('#cards').innerHTML = D.modes.map(x => { const s = D.summary.modes[x];
  const bar = ['correct','safe_miss','silent_wrong','format_error'].map(o => `<span style="width:${s.n ? s[o] / s.n * 100 : 0}%;background:${colors[o]}"></span>`).join('');
  return `<div class="card"><div class="muted">${esc(D.modeLabels[x])}</div><div class="big">${pct(s.accuracy)}</div><div class="bar">${bar}</div>
  <div class="muted">正確 ${s.correct}／默默答錯 ${s.silent_wrong}／保守 ${s.safe_miss}／格式 ${s.format_error}</div></div>`; }).join('');
$('#table').innerHTML = '<table><tr><th>模式</th><th>正確</th><th>默默答錯</th><th>保守未答</th><th>越權</th><th>自編 ID</th><th>檢查首過</th><th>被擋下</th><th>若有檢查會擋</th><th>平均 token（入＋出）</th><th>平均秒數</th><th>平均呼叫／工具</th></tr>' +
  D.modes.map(x => { const s = D.summary.modes[x]; return `<tr><td><b>${x}</b></td><td>${s.correct}/${s.n}</td><td>${s.silent_wrong}</td><td>${s.safe_miss}</td><td>${s.leaks}</td><td>${s.invalid_ids}</td>
  <td>${s.gate_first_pass == null ? '—' : pct(s.gate_first_pass)}</td><td>${s.blocked}</td><td>${['baseline','context'].includes(x) ? s.would_block : '—'}</td>
  <td>${s.avg_prompt_tokens ?? '—'}＋${s.avg_completion_tokens ?? '—'}</td><td>${s.avg_latency ?? '—'}</td><td>${s.avg_llm_calls ?? '—'}／${s.avg_tool_calls ?? '—'}</td></tr>`; }).join('') + '</table>';
$('#cats').innerHTML = '<table><tr><th>題型</th>' + D.modes.map(x => `<th>${x}</th>`).join('') + '</tr>' +
  Object.entries(D.summary.categories).map(([c, per]) => `<tr><td>${esc(c)}</td>` + D.modes.map(x => `<td>${per[x] ? per[x].correct + '/' + per[x].n : '—'}</td>`).join('') + '</tr>').join('') + '</table>';
$('#f-legend').innerHTML = '右側方塊依序為 ' + D.modes.join('／') + '：<span class="dot d-correct" style="display:inline-block"></span> 正確 <span class="dot d-safe_miss" style="display:inline-block"></span> 保守 <span class="dot d-silent_wrong" style="display:inline-block"></span> 默默答錯';
for (const x of D.modes) $('#f-mode').insertAdjacentHTML('beforeend', `<option value="${x}">${x}</option>`);
for (const [k, v] of Object.entries(D.outcomeLabels)) $('#f-outcome').insertAdjacentHTML('beforeend', `<option value="${k}">${v}</option>`);
for (const c of Object.keys(D.summary.categories)) $('#f-cat').insertAdjacentHTML('beforeend', `<option value="${esc(c)}">${esc(c)}</option>`);
const groups = []; const index = {};
for (const r of D.results) { if (!(r.question_id in index)) { index[r.question_id] = groups.length; groups.push([]); } groups[index[r.question_id]].push(r); }
function runHtml(r) {
  const t = r.transcript;
  let h = `<div class="run"><h4><b>${esc(r.mode)}</b>${r.repeat ? `（第 ${r.repeat + 1} 次）` : ''}<span class="pill o-${r.outcome}">${esc(D.outcomeLabels[r.outcome])}</span>
    <span>${esc(D.decisionLabels[String(t.decision)] || t.decision)}</span><span>${ids(t.metrics)}</span></h4>`;
  if (r.problems.length) h += `<div class="gate fail">問題：${esc(r.problems.join('；'))}</div>`;
  (t.gate || []).forEach((g, i) => { h += `<div class="gate ${g.passed ? 'pass' : 'fail'}">${g.enforced ? '本體檢查' : '本體檢查（只記錄）'}第 ${i + 1} 次：${g.passed ? '通過' : '未通過'}` +
    (g.errors.length ? '；' + esc(g.errors.map(e => `[${e.code}] ${e.message}`).join('；')) : '') +
    ((g.challenges || []).length ? '；質疑：' + esc(g.challenges.map(e => `[${e.code}] ${e.message}`).join('；')) : '') +
    (g.warnings.length ? '；提醒：' + esc(g.warnings.map(w => w.message).join('；')) : '') + '</div>'; });
  for (const c of t.calls || []) (c.tool_calls || []).forEach((tc, i) => { h += `<div class="tool">🔧 <span class="mono">${esc(tc.name)}(${esc(tc.arguments)})</span> → <span class="mono">${esc(JSON.stringify((c.tool_results || [])[i] ?? null).slice(0, 220))}</span></div>`; });
  h += `<div class="answer">${esc(t.answer || t.error || '（無）')}</div>`;
  h += `<div class="muted" style="font-size:12px">呼叫 ${t.llm_calls ?? 0} 次、工具 ${t.tool_calls ?? 0} 次、token ${t.usage?.prompt_tokens ?? 0}＋${t.usage?.completion_tokens ?? 0}、${t.latency ?? 0} 秒</div>`;
  h += `<details class="raw"><summary>原始呼叫紀錄（含思考內容）</summary><pre>${esc(JSON.stringify(t.calls, null, 1))}</pre></details></div>`;
  return h;
}
function render() {
  const fm = $('#f-mode').value, fo = $('#f-outcome').value, fc = $('#f-cat').value, ft = $('#f-text').value.trim();
  let shown = 0; let out = '';
  for (const g of groups) {
    const q = g[0];
    if (fc && q.category !== fc) continue;
    let runs = g.filter(r => (!fm || r.mode === fm) && (!fo || r.outcome === fo));
    if (ft) { const hit = q.question.includes(ft) || q.question_id.includes(ft) || g.some(r => (r.transcript.metrics || []).some(x => x.includes(ft))); if (!hit) continue; }
    if (!runs.length) continue;
    shown++;
    const e = q.expect;
    const dots = g.map(r => `<span class="dot d-${r.outcome}" title="${esc(r.mode)}：${esc(D.outcomeLabels[r.outcome])}"></span>`).join('');
    out += `<details class="q"><summary><span class="mono">${esc(q.question_id)}</span><span class="pill" style="background:var(--greybg)">${esc(q.category)}</span>
      <span class="muted">${esc(q.role)}</span><span class="qtext">${esc(q.question)}</span><span class="dots">${dots}</span></summary><div class="body">
      <div class="exp">期望：決策 ${e.decision.map(d => esc(D.decisionLabels[d] || d)).join('／')}${e.metrics && e.metrics.length ? `；指標（${e.match}）${ids(e.metrics)}` : ''}${e.classes.length ? '；類別 ' + ids(e.classes) : ''}${e.forbidden.length ? '；禁止 ' + ids(e.forbidden) : ''}${e.mention_any.length ? '；需提到 ' + esc(e.mention_any.join('／')) : ''}${q.note ? `<br><span class="muted">${esc(q.note)}</span>` : ''}</div>
      ${runs.map(runHtml).join('')}</div></details>`;
  }
  $('#questions').innerHTML = out || '<p class="muted">沒有符合條件的紀錄。</p>';
  $('#f-count').textContent = `${shown} 題`;
}
for (const id of ['#f-mode', '#f-outcome', '#f-cat']) $(id).addEventListener('change', render);
$('#f-text').addEventListener('input', render);
render();
</script></body></html>
"""
