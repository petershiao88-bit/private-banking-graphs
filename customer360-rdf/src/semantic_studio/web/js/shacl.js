import { S, classChip, onState, termChip } from './store.js';
import { $, esc } from './util.js';

/* SHACL：驗證結果與 shapes。 */

export function renderShacl() {
  const box = $('#shacl-panel');
  const v = S.validation;
  const viol = v.results.filter((r) => r.severity === 'Violation').length;
  box.innerHTML = `
    <h2>SHACL 驗證</h2>
    <p class="muted">資料圖＝本體＋OWL 推理出的 subClassOf 閉包＋所有業務字典對應（PG 既有與新詞條）。shape 檔案放在 config 的 paths.shapes_dir。</p>
    <div class="cards">
      <div class="card"><div class="num" style="color:${v.conforms ? '#2b8a3e' : '#e03131'}">${v.conforms ? '通過' : '未通過'}</div><div class="lbl">整體結果</div></div>
      <div class="card"><div class="num">${viol}</div><div class="lbl">違規</div></div>
      <div class="card"><div class="num">${v.results.length - viol}</div><div class="lbl">警告</div></div>
      <div class="card"><div class="num">${S.shapes.length}</div><div class="lbl">shapes</div></div>
    </div>
    <h3>驗證結果</h3>
    ${v.results.length ? `<table><thead><tr><th>等級</th><th>節點</th><th>shape</th><th>訊息</th><th>路徑／值</th></tr></thead><tbody>
      ${v.results.map((r) => `<tr><td>${r.severity === 'Violation' ? '<span class="chip deny">違規</span>' : '<span class="chip warn">警告</span>'}</td>
        <td>${r.node.startsWith('term:') ? termChip(r.node.slice(5)) : classChip(r.node)}</td>
        <td class="small-text">${esc(S.shapes.find((s) => s.id === r.shape)?.label || r.shape)}</td>
        <td>${esc(r.message)}${r.mapping_index !== null && r.mapping_index !== undefined ? `（第 ${r.mapping_index + 1} 筆對應）` : ''}</td>
        <td class="mono small-text">${esc(r.path || '')}${r.value && !String(r.value).startsWith('dict:') ? ' = ' + esc(r.value) : ''}</td></tr>`).join('')}
    </tbody></table>` : '<div class="result Info">所有節點都通過 SHACL。</div>'}
    <h3>Shapes</h3>
    ${S.shapes.map((s) => `<div class="perm"><div class="head"><b>${esc(s.label)}</b><span>${s.targets.map((t) => `<span class="chip">${esc(t)}</span>`).join('')}${s.severity === 'Warning' ? '<span class="chip warn">警告等級</span>' : ''}</span></div>
      <div class="small-text muted">${esc(s.comment)}</div>
      <table style="margin-top:6px"><tbody>${s.constraints.map((c) => `<tr><td class="mono small-text" style="width:200px">${esc(c.path || (c.kind === 'sparql' ? 'SPARQL' : c.kind))}</td>
        <td class="small-text">${esc(c.message)}${c.kind === 'sparql' ? `<details><summary class="muted">查詢</summary><pre class="code">${esc(c.rule)}</pre></details>` : `<div class="muted mono">${esc(c.rule)}</div>`}</td></tr>`).join('')}</tbody></table></div>`).join('')}`;
}


onState(renderShacl);
