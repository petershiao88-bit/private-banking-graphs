import { S, actions, idx, onState, roleLabel, ui } from './store.js';
import { $, COLORS, esc } from './util.js';

/* RDF 圖譜：Cytoscape 繪圖、篩選、權限著色、搜尋與節點導覽。 */
export let cy = null;


export function renderControls() {
  const box = $('#layer-toggles');
  box.innerHTML = S.layers.map((l) => `<label><input type="checkbox" data-layer="${l.key}" ${ui.layers.has(l.key) ? 'checked' : ''}>
    <span class="swatch" style="background:${COLORS[l.key] || '#868e96'}"></span>${esc(l.title)}</label>`).join('');
  const sel = $('#role-view');
  sel.innerHTML = `<option value="">（不著色）</option>` + S.policy.roles.map((r) =>
    `<option value="${esc(r.id)}" ${ui.role === r.id ? 'selected' : ''}>${esc(r.label)}</option>`).join('');
  $('#legend').innerHTML = `<div class="field-label">圖例</div>
    ${S.layers.map((l) => `<div class="lg-item"><span class="swatch" style="background:${COLORS[l.key]}"></span>${esc(l.title)}類別</div>`).join('')}
    <div class="lg-item"><span class="swatch" style="background:#fff;border:2px dashed #adb5bd;opacity:.6"></span>淡色：未勾選層的上層類別</div>
    <div class="lg-item"><span class="swatch" style="background:#fff;border:2px solid #7048e8;border-radius:50%"></span>業務字典詞條（虛線框＝PG 既有）</div>
    <div class="lg-item"><span class="swatch line" style="border-color:#495057"></span>rdfs:subClassOf（宣告）</div>
    <div class="lg-item"><span class="swatch dash" style="border-color:#f59f00"></span>OWL 推理出的上層</div>
    <div class="lg-item"><span class="swatch dash" style="border-color:#9775fa"></span>詞條 → 類別對應</div>
    <div class="lg-item"><span class="swatch" style="background:#fa5252;transform:rotate(45deg);width:11px;height:11px"></span>SHACL shape（連到違規節點）</div>
    ${ui.role ? `<div class="lg-item"><span class="swatch" style="background:#fff5f5;border:3px solid #e03131"></span>${esc(roleLabel(ui.role))}不可看</div>
    <div class="lg-item"><span class="swatch" style="border:3px solid #2b8a3e"></span>${esc(roleLabel(ui.role))}可看</div>` : ''}`;
}

$('#layer-toggles').addEventListener('change', (e) => {
  const key = e.target.dataset.layer;
  if (!key) return;
  e.target.checked ? ui.layers.add(key) : ui.layers.delete(key);
  renderGraph();
});
[['#opt-inferred', 'inferred'], ['#opt-new', 'showNew'], ['#opt-pg', 'showPg'], ['#opt-objprop', 'objprop'],
  ['#opt-dataprop', 'dataprop'], ['#opt-shacl', 'shacl']].forEach(([sel, key]) => {
  $(sel).checked = ui[key];
  $(sel).addEventListener('change', (e) => { ui[key] = e.target.checked; renderGraph(); });
});
$('#role-view').addEventListener('change', (e) => { ui.role = e.target.value; renderControls(); applyOverlay(); if (ui.selected) actions.showDetail(ui.selected, false); });
$('#layout').addEventListener('change', (e) => { ui.layout = e.target.value; runLayout(); });
$('#relayout').addEventListener('click', () => runLayout());
$('#search').addEventListener('input', (e) => highlight(e.target.value.trim()));

export function buildElements() {
  const els = [];
  const visible = new Set();
  for (const c of S.classes) {
    if (!ui.layers.has(c.layer)) continue;
    visible.add(c.uri);
    els.push({ data: { id: c.uri, label: c.label + (c.deprecated ? '（下架）' : ''), kind: 'class', layer: c.layer, color: COLORS[c.layer] || '#868e96' } });
  }
  // 沒勾選的層裡、但是勾選類別的上層（例如子公司類別的金控層父類別）→ 以淡色背景節點補上，階層才不會斷成孤點
  const ghosts = new Set();
  const queue = [...visible];
  while (queue.length) {
    for (const p of idx.classByUri.get(queue.pop())?.parents || []) {
      const parent = idx.classByUri.get(p);
      if (!parent || visible.has(p) || ghosts.has(p)) continue;
      ghosts.add(p);
      queue.push(p);
      els.push({ data: { id: p, label: parent.label, kind: 'class', ghost: 1, layer: parent.layer, color: COLORS[parent.layer] || '#868e96' } });
    }
  }
  for (const c of S.classes) {
    for (const p of c.parents) {
      const shown = (u) => visible.has(u) || ghosts.has(u);
      if (shown(c.uri) && shown(p)) els.push({ data: { id: `sc|${c.uri}|${p}`, source: c.uri, target: p, kind: 'subclass' } });
    }
  }
  if (ui.inferred) {
    for (const e of S.inferred) {
      if (visible.has(e.source) && visible.has(e.target)) els.push({ data: { id: `inf|${e.source}|${e.target}`, source: e.source, target: e.target, kind: 'inferred', label: '推理' } });
    }
  }
  for (const p of S.properties) {
    if (p.kind === 'object' && ui.objprop) {
      for (const d of p.domain) for (const r of p.range) {
        if ((visible.has(d) || ghosts.has(d)) && (visible.has(r) || ghosts.has(r))) els.push({ data: { id: `op|${p.uri}|${d}|${r}`, source: d, target: r, kind: 'objprop', label: p.label } });
      }
    }
    if (p.kind === 'datatype' && ui.dataprop) {
      const domains = p.domain.filter((d) => visible.has(d));
      if (!domains.length) continue;
      els.push({ data: { id: p.uri, label: `${p.label}\n${p.range.join(', ')}`, kind: 'dataprop' } });
      for (const d of domains) els.push({ data: { id: `dp|${d}|${p.uri}`, source: d, target: p.uri, kind: 'dataprop-edge' } });
    }
  }
  for (const t of S.terms) {
    if ((t.origin === 'pg' && !ui.showPg) || (t.origin !== 'pg' && !ui.showNew)) continue;
    // 對應的類別都在沒勾選的層 → 不畫，避免浮出孤立節點；完全沒對應的詞條仍顯示（連到 SHACL 違規）
    if (t.mappings.length && !t.mappings.some((m) => visible.has(m.uri))) continue;
    const id = 'term:' + t.id;
    visible.add(id);
    els.push({ data: { id, label: t.name, kind: 'term', origin: t.origin } });
    t.mappings.forEach((m, i) => {
      if (visible.has(m.uri)) els.push({ data: { id: `map|${t.id}|${i}`, source: id, target: m.uri, kind: 'maps', label: S.mapping_roles[m.role] || m.role } });
    });
  }
  if (ui.shacl) {
    const shapesUsed = new Map();
    for (const r of S.validation.results) {
      if (!visible.has(r.node)) continue;
      const key = 'shape:' + r.shape;
      if (!shapesUsed.has(key)) shapesUsed.set(key, new Set());
      shapesUsed.get(key).add(r.node);
    }
    for (const [key, nodes] of shapesUsed) {
      const shape = S.shapes.find((s) => 'shape:' + s.id === key);
      els.push({ data: { id: key, label: shape ? shape.label : 'SHACL', kind: 'shape' } });
      for (const n of nodes) els.push({ data: { id: `${key}|${n}`, source: key, target: n, kind: 'shacl' } });
    }
  }
  return els;
}

export const CY_STYLE = [
  { selector: 'node', style: { label: 'data(label)', 'font-size': 11, 'text-valign': 'center', 'text-halign': 'center', color: '#fff', 'text-wrap': 'wrap', 'text-max-width': 110, width: 'label', height: 'label', padding: '8px', shape: 'round-rectangle', 'background-color': '#868e96', 'font-family': 'Noto Sans TC, PingFang TC, Microsoft JhengHei, sans-serif' } },
  { selector: 'node[kind="class"]', style: { 'background-color': 'data(color)' } },
  { selector: 'node[kind="class"][ghost]', style: { opacity: 0.4, 'border-width': 2, 'border-style': 'dashed', 'border-color': 'data(color)', 'background-color': '#fff', color: '#495057' } },
  { selector: 'node[kind="term"]', style: { shape: 'round-rectangle', 'background-color': '#fff', color: '#5f3dc4', 'border-width': 2, 'border-color': '#7048e8', 'corner-radius': 14 } },
  { selector: 'node[kind="term"][origin="pg"]', style: { 'border-style': 'dashed', 'border-color': '#9775fa', color: '#495057' } },
  { selector: 'node[kind="dataprop"]', style: { shape: 'tag', 'background-color': '#f1f3f5', color: '#495057', 'font-size': 10 } },
  { selector: 'node[kind="shape"]', style: { shape: 'diamond', 'background-color': '#fa5252', width: 26, height: 26, padding: 0, color: '#c92a2a', 'text-valign': 'bottom', 'text-margin-y': 4, 'font-size': 10 } },
  { selector: 'edge', style: { width: 1.5, 'curve-style': 'bezier', 'target-arrow-shape': 'triangle', 'arrow-scale': 0.8, 'line-color': '#adb5bd', 'target-arrow-color': '#adb5bd', 'font-size': 9, 'text-rotation': 'autorotate', 'text-background-color': '#fff', 'text-background-opacity': 0.85, 'text-background-padding': 1 } },
  { selector: 'edge[kind="subclass"]', style: { 'line-color': '#495057', 'target-arrow-color': '#495057', 'target-arrow-shape': 'triangle-backcurve' } },
  { selector: 'edge[kind="inferred"]', style: { 'line-style': 'dashed', 'line-color': '#fab005', 'target-arrow-color': '#fab005', label: 'data(label)', color: '#e67700' } },
  { selector: 'edge[kind="objprop"]', style: { 'line-color': '#74c0fc', 'target-arrow-color': '#74c0fc', label: 'data(label)', color: '#1971c2' } },
  { selector: 'edge[kind="dataprop-edge"]', style: { 'line-color': '#dee2e6', 'target-arrow-shape': 'none' } },
  { selector: 'edge[kind="maps"]', style: { 'line-style': 'dashed', 'line-color': '#b197fc', 'target-arrow-color': '#9775fa', width: 2, label: 'data(label)', color: '#7048e8' } },
  { selector: 'edge[kind="shacl"]', style: { 'line-style': 'dotted', 'line-color': '#ff8787', 'target-arrow-color': '#ff8787' } },
  { selector: 'node.violation', style: { 'border-width': 3, 'border-color': '#e03131', 'border-style': 'solid' } },
  { selector: 'node.warning', style: { 'border-width': 3, 'border-color': '#f59f00', 'border-style': 'solid' } },
  { selector: 'node.allow', style: { 'border-width': 4, 'border-color': '#2b8a3e', 'border-style': 'solid' } },
  { selector: 'node.deny', style: { 'background-color': '#fff5f5', color: '#c92a2a', 'border-width': 4, 'border-color': '#e03131', 'border-style': 'double' } },
  { selector: 'node.unmapped', style: { 'border-width': 3, 'border-color': '#f59f00', 'border-style': 'dashed' } },
  { selector: '.faded', style: { opacity: 0.12 } },
  { selector: 'node:selected', style: { 'overlay-color': '#ffd43b', 'overlay-opacity': 0.45, 'overlay-padding': 6 } },
];

export function renderGraph() {
  const els = buildElements();
  if (!cy) {
    cy = cytoscape({ container: $('#cy'), elements: els, style: CY_STYLE, wheelSensitivity: 0.25, minZoom: 0.15, maxZoom: 3 });
    cy.on('tap', 'node', (e) => actions.showDetail(e.target.id()));
    cy.on('tap', (e) => { if (e.target === cy) { cy.elements().removeClass('faded'); } });
  } else {
    cy.elements().remove();
    cy.add(els);
  }
  applyOverlay();
  runLayout();
  if (ui.selected && cy.getElementById(ui.selected).length) cy.getElementById(ui.selected).select();
}

export function applyOverlay() {
  if (!cy) return;
  cy.nodes().removeClass('violation warning allow deny unmapped');
  if (ui.shacl) {
    cy.nodes().forEach((n) => {
      const rs = idx.resultsByNode.get(n.id());
      if (rs) n.addClass(rs.some((r) => r.severity === 'Violation') ? 'violation' : 'warning');
    });
  }
  if (!ui.role) return;
  cy.nodes().forEach((n) => {
    let perm = null;
    if (n.data('kind') === 'class') perm = idx.classByUri.get(n.id())?.permissions[ui.role];
    if (n.data('kind') === 'term') perm = idx.termById.get(n.id().slice(5))?.permissions[ui.role];
    if (perm) n.removeClass('violation warning').addClass(perm.effect);
  });
}

export function runLayout() {
  if (!cy || !cy.nodes().length) return;
  const options = {
    cose: { name: 'cose', animate: false, nodeRepulsion: 5000, idealEdgeLength: 55, nodeOverlap: 12, padding: 30, randomize: false, componentSpacing: 30, gravity: 1.6, nestingFactor: 1.2 },
    breadthfirst: { name: 'breadthfirst', directed: false, spacingFactor: 1.1, padding: 30,
      roots: cy.nodes().filter((n) => n.data('kind') === 'class' && !n.outgoers('edge[kind="subclass"]').length) },
    concentric: { name: 'concentric', padding: 30, minNodeSpacing: 18,
      concentric: (n) => ({ class: n.outgoers('edge[kind="subclass"]').length ? 2 : 3, term: 1, shape: 0 }[n.data('kind')] ?? 1), levelWidth: () => 1 },
    grid: { name: 'grid', padding: 30, avoidOverlap: true },
  }[ui.layout];
  cy.layout(options).run();
  cy.fit(undefined, 30);
}

export function highlight(text) {
  if (!cy) return;
  cy.elements().removeClass('faded');
  if (!text) return;
  const q = text.toLowerCase();
  const hits = cy.nodes().filter((n) => n.data('label').toLowerCase().includes(q) || n.id().toLowerCase().includes(q)
    || (idx.classByUri.get(n.id())?.id || '').toLowerCase().includes(q));
  if (!hits.length) return;
  const keep = hits.union(hits.neighborhood());
  cy.elements().difference(keep).addClass('faded');
  cy.animate({ fit: { eles: keep, padding: 60 }, duration: 250 });
}

export function goToNode(id) {
  if (!$('#tab-graph').classList.contains('active')) actions.switchTab('graph');
  if (id.startsWith('term:')) {
    const t = idx.termById.get(id.slice(5));
    if (t && t.origin === 'pg' && !ui.showPg) { ui.showPg = true; $('#opt-pg').checked = true; renderGraph(); }
    if (t && t.origin !== 'pg' && !ui.showNew) { ui.showNew = true; $('#opt-new').checked = true; renderGraph(); }
    // 詞條對應的類別都在沒勾選的層時，把那些層打開，詞條才看得到
    const layers = t ? t.mappings.map((m) => idx.classByUri.get(m.uri)?.layer).filter(Boolean) : [];
    if (layers.length && !layers.some((l) => ui.layers.has(l))) { layers.forEach((l) => ui.layers.add(l)); renderControls(); renderGraph(); }
  } else {
    const c = idx.classByUri.get(id);
    if (c && !ui.layers.has(c.layer)) { ui.layers.add(c.layer); renderControls(); renderGraph(); }
  }
  const node = cy.getElementById(id);
  if (node.length) {
    cy.nodes().unselect();
    node.select();
    cy.animate({ center: { eles: node }, zoom: Math.max(cy.zoom(), 1), duration: 250 });
  }
  actions.showDetail(id);
}


actions.goToNode = goToNode;
onState(() => { renderControls(); renderGraph(); if (ui.selected) actions.showDetail(ui.selected, false); });
