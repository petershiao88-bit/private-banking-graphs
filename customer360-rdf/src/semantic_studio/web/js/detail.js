import { S, actions, classChip, idx, permissionBlock, resultHtml, termChip, ui } from './store.js';
import { $, api, esc } from './util.js';

/* 節點細節面板：類別、詞條、屬性、SHACL shape。 */
export async function showDetail(id, focusTab = true) {
  ui.selected = id;
  const box = $('#detail');
  if (id.startsWith('shape:')) {
    const shape = S.shapes.find((s) => 'shape:' + s.id === id);
    const rs = S.validation.results.filter((r) => 'shape:' + r.shape === id);
    box.innerHTML = shape ? `<h2>${esc(shape.label)}</h2><div class="muted small-text mono">${esc(shape.id)}</div>
      <p>${esc(shape.comment)}</p><h3>目標</h3>${shape.targets.map((t) => `<span class="chip">${esc(t)}</span>`).join('')}
      <h3>違規節點（${rs.length}）</h3>${rs.map((r) => `<div>${r.node.startsWith('term:') ? termChip(r.node.slice(5)) : classChip(r.node)}</div>${resultHtml(r)}`).join('')}` : '';
    return;
  }
  const c = idx.classByUri.get(id);
  const t = id.startsWith('term:') ? idx.termById.get(id.slice(5)) : null;
  const prop = !c && !t ? S.properties.find((p) => p.uri === id) : null;
  let detail = null;
  try { detail = await api('/api/node?id=' + encodeURIComponent(id)); } catch (err) { /* 屬性等非類別節點 */ }
  if (ui.selected !== id) return;
  const results = (idx.resultsByNode.get(id) || []).map(resultHtml).join('') || '<div class="muted small-text">沒有違規。</div>';
  if (c) {
    const children = S.classes.filter((x) => x.parents.includes(c.uri));
    const ancestors = new Set([c.uri, ...c.ancestors]);
    const own = S.properties.filter((p) => p.domain.includes(c.uri));
    const inherited = S.properties.filter((p) => !p.domain.includes(c.uri) && p.domain.some((d) => ancestors.has(d)));
    const propLine = (p, from) => `<div class="small-text">${esc(p.label)} <span class="mono muted">${esc(p.id)}</span> → ${p.range.map((r) => idx.classByUri.has(r) ? classChip(r) : `<span class="mono">${esc(r)}</span>`).join('')}${from ? `<span class="muted">（繼承自${esc(from)}）</span>` : ''}</div>`;
    box.innerHTML = `<h2>${esc(c.label)}</h2><div class="mono muted">${esc(c.id)}</div>
      <p>${esc(c.definition)}</p>
      <dl class="kv"><dt>層級</dt><dd>${classChip(c.uri, false)}</dd><dt>模組</dt><dd>${esc(c.module)}</dd><dt>成熟度</dt><dd>${esc(c.maturity)}${c.deprecated ? '，<b>已下架</b>' : ''}</dd></dl>
      <h3>上層鏈（OWL 推理）</h3>${c.chain.length ? c.chain.map((x) => `<div class="chain">${esc(x)}</div>`).join('') : '<div class="muted small-text">頂層類別</div>'}
      ${children.length ? `<h3>直接子類</h3>${children.map((x) => classChip(x.uri)).join('')}` : ''}
      <h3>權限（類別規則沿子類別繼承）</h3>${permissionBlock(c.permissions)}
      <h3>可用屬性</h3>${own.map((p) => propLine(p)).join('')}${inherited.map((p) => propLine(p, p.domain.map((d) => idx.classByUri.get(d)?.label).filter(Boolean).join('、'))).join('') || (own.length ? '' : '<div class="muted small-text">無</div>')}
      <h3>對應到此類別的詞條</h3>${detail && detail.terms.length ? detail.terms.map(termChip).join('') : '<div class="muted small-text">無</div>'}
      <h3>SHACL</h3><div class="small-text muted">適用 shape：${detail ? detail.shapes.map(esc).join('、') : ''}</div>${results}
      <h3>OWL（Turtle）</h3><pre class="code">${esc(detail ? detail.turtle.replace(/^@prefix[^\n]*\n/gm, '').trim() : '')}</pre>
      ${detail && detail.incoming.length ? `<h3>被引用</h3>${detail.incoming.map((i) => `<div class="small-text mono">${esc(i.subject)} ${esc(i.predicate)} 本類別</div>`).join('')}` : ''}`;
  } else if (t) {
    box.innerHTML = `<h2>${esc(t.name)}</h2><div class="mono muted">${esc(t.id)}</div>
      <p>${esc(t.definition) || '<span class="muted">（無定義）</span>'}</p>
      <dl class="kv"><dt>來源</dt><dd>${esc(t.source)}</dd><dt>類型</dt><dd>${t.origin === 'pg' ? 'PG 既有詞條（唯讀）' : '業務字典詞條'}</dd></dl>
      <h3>對應的類別組合</h3>${t.mappings.length ? t.mappings.map((m) => `<div><span class="chip role">${esc(S.mapping_roles[m.role] || m.role)}</span>${classChip(m.uri)}</div>`).join('') : '<div class="muted small-text">尚未對應</div>'}
      <h3>權限（繼承自對應的類別）</h3>${permissionBlock(t.permissions)}
      <h3>SHACL</h3>${results}
      <div class="actions"><button class="primary small" id="edit-term">${t.editable ? '編輯對應' : '複製為新詞條'}</button></div>
      <h3>RDF（Turtle）</h3><pre class="code">${esc(detail ? detail.turtle.replace(/^@prefix[^\n]*\n/gm, '').trim() : '')}</pre>`;
    $('#edit-term').addEventListener('click', () => { actions.openEditor(t.editable ? t.id : null, t.editable ? null : t); actions.switchTab('dictionary'); });
  } else if (prop) {
    box.innerHTML = `<h2>${esc(prop.label)}</h2><div class="mono muted">${esc(prop.id)}</div><p>${esc(prop.definition)}</p>
      <dl class="kv"><dt>種類</dt><dd>${prop.kind === 'object' ? '關係屬性' : '資料屬性'}</dd><dt>domain</dt><dd>${prop.domain.map((d) => classChip(d)).join('')}</dd><dt>range</dt><dd>${prop.range.map((r) => idx.classByUri.has(r) ? classChip(r) : `<span class="mono">${esc(r)}</span>`).join('')}</dd></dl>
      <h3>OWL（Turtle）</h3><pre class="code">${esc(detail ? detail.turtle.replace(/^@prefix[^\n]*\n/gm, '').trim() : '')}</pre>`;
  }
}


actions.showDetail = showDetail;
