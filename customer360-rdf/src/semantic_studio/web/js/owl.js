import { S, classChip, idx, onState } from './store.js';
import { $, esc } from './util.js';

/* OWL 推理：統計、推理新增的關係、類別階層。 */

export function renderOwl() {
  const box = $('#owl-panel');
  const r = S.reasoning;
  if (!r) { box.innerHTML = `<h2>OWL 推理</h2><div class="result">${esc(S.reasoning_error || '推理未執行')}</div>`; return; }
  const children = new Map();
  for (const c of S.classes) for (const p of c.parents) { if (!children.has(p)) children.set(p, []); children.get(p).push(c); }
  const tree = (c) => `<li>${classChip(c.uri)}<span class="mono muted small-text">${esc(c.id)}</span>${children.has(c.uri) ? `<ul>${children.get(c.uri).sort((a, b) => a.layer.localeCompare(b.layer) || a.id.localeCompare(b.id)).map(tree).join('')}</ul>` : ''}</li>`;
  const roots = S.classes.filter((c) => !c.parents.length).sort((a, b) => a.id.localeCompare(b.id));
  box.innerHTML = `
    <h2>OWL 推理</h2><p class="muted">${esc(r.engine)}；對 ${(S.modules || []).length} 個模組合併後的 TBox 做閉包，並與獨立的 subClassOf 走訪交叉驗證（${esc(r.independent_check)}）。</p>
    <div class="cards">
      <div class="card"><div class="num">${r.input_triples}</div><div class="lbl">輸入 triples</div></div>
      <div class="card"><div class="num">${r.closure_triples}</div><div class="lbl">閉包 triples</div></div>
      <div class="card"><div class="num">${r.classes}</div><div class="lbl">類別</div></div>
      <div class="card"><div class="num">${r.asserted_subclass_axioms}</div><div class="lbl">宣告的 subClassOf</div></div>
      <div class="card"><div class="num">${r.entailed_pairs}</div><div class="lbl">蘊含的上下位關係</div></div>
      <div class="card"><div class="num">${r.inferred_only}</div><div class="lbl">推理新增</div></div>
      <div class="card"><div class="num">${r.cycles.length}／${r.unsatisfiable.length}</div><div class="lbl">循環／不可滿足</div></div>
    </div>
    <div class="columns">
      <div><h3>推理新增的關係</h3><table><thead><tr><th>類別</th><th>推出的上層</th><th>推理路徑</th></tr></thead><tbody>
      ${S.inferred.map((e) => `<tr><td>${classChip(e.source)}</td><td>${classChip(e.target)}</td><td class="small-text">${e.path.map((u) => esc(idx.classByUri.get(u)?.label || u)).join(' ⊑ ')}</td></tr>`).join('')}
      </tbody></table>
      <h3>限制</h3><ul class="small-text">${r.limitations.map((x) => `<li>${esc(x)}</li>`).join('')}</ul>
      <h3>類別組成元件檢查</h3>${S.component_issues.length ? S.component_issues.map((i) => `<div class="result ${i.level === 'warning' ? 'Warning' : ''}">${esc(i.id)}［${esc(i.rule)}］${esc(i.message)}</div>`).join('') : '<div class="result Info">43 個類別全部通過組成元件規則。</div>'}</div>
      <div><h3>類別階層（rdfs:subClassOf）</h3><div class="tree"><ul>${roots.map(tree).join('')}</ul></div></div>
    </div>`;
}


onState(renderOwl);
