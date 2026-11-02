import { $, EFFECT_LABEL, esc } from './util.js';

/* 全域狀態：後端 state（S）、索引、UI 狀態、跨模組動作與重繪 hooks。 */
export let S = null;               // 後端 state（ES module live binding）
export const idx = { classByUri: new Map(), classById: new Map(), termById: new Map(), resultsByNode: new Map() };
export const ui = {
  layers: new Set(['holding', 'bank', 'securities']), inferred: true, showNew: true, showPg: false,
  objprop: true, dataprop: false, shacl: true, role: '', layout: 'cose', selected: null,
  termFilter: 'all', editing: null, policyDraft: null, previewTimer: null,
};


// 跨模組動作（由各模組註冊，避免循環 import）
export const actions = {};
// setState 後依序呼叫的重繪函式
export const stateHooks = [];
export const onState = (fn) => stateHooks.push(fn);

export function setState(state) {
  S = state;
  idx.classByUri = new Map(S.classes.map((c) => [c.uri, c]));
  idx.classById = new Map(S.classes.map((c) => [c.id, c]));
  idx.termById = new Map(S.terms.map((t) => [t.id, t]));
  idx.resultsByNode = new Map();
  for (const r of S.validation.results) {
    if (!idx.resultsByNode.has(r.node)) idx.resultsByNode.set(r.node, []);
    idx.resultsByNode.get(r.node).push(r);
  }
  const o = S.ontology;
  $('#onto-meta').textContent = `${o.label}｜v${o.version}（${o.status}，${o.date}）`;
  const v = S.validation.results.filter((r) => r.severity === 'Violation').length;
  const w = S.validation.results.length - v;
  const badge = $('#shacl-badge');
  badge.textContent = v || w ? `SHACL：${v} 違規、${w} 警告` : 'SHACL：全部通過';
  badge.className = 'badge' + (v ? ' bad' : '');
  ui.policyDraft = null;
  for (const hook of stateHooks) hook();
}

export function classChip(uriOrId, link = true) {
  const c = idx.classByUri.get(uriOrId) || idx.classById.get(uriOrId);
  if (!c) return `<span class="chip">${esc(uriOrId)}</span>`;
  return `<span class="chip ${c.layer}${link ? ' link' : ''}" data-node="${esc(c.uri)}" title="${esc(c.id)}">${esc(c.label)}</span>`;
}
export function termChip(id) {
  const t = idx.termById.get(id);
  return `<span class="chip term link" data-node="term:${esc(id)}">${esc(t ? t.name : id)}</span>`;
}
export function effectChip(effect) { return `<span class="chip ${effect}">${EFFECT_LABEL[effect] || effect}</span>`; }
export function roleLabel(id) { return (S.policy.roles.find((r) => r.id === id) || { label: id }).label; }
export function resultHtml(r) {
  const where = r.mapping_index !== null && r.mapping_index !== undefined ? `（第 ${r.mapping_index + 1} 筆對應）` : '';
  const value = r.value && !String(r.value).startsWith('dict:') ? `；值：<span class="mono">${esc(r.value)}</span>` : '';
  return `<div class="result ${esc(r.severity)}"><b>${r.severity === 'Violation' ? '違規' : r.severity === 'Warning' ? '警告' : '提示'}</b> ${esc(r.message)}${where}${value}</div>`;
}
export function permissionBlock(perms) {
  return S.policy.roles.map((r) => {
    const p = perms[r.id];
    const reasons = p.matches.map((m) => {
      const via = m.via.map((v) => v.mapped_class
        ? `${classChip(v.rule_class)}${v.inherited ? `（由對應的 ${classChip(v.mapped_class)} 繼承）` : '（直接對應）'}`
        : `${classChip(v.rule_class)}${v.inherited ? '（上層類別，繼承而來）' : '（本類別）'}`).join(' ＋ ');
      return `<li><b>${m.effect === 'deny' ? '拒絕' : '允許'}</b>｜${esc(m.note || m.rule)}${m.combination ? '（組合規則）' : ''}<br>${via}</li>`;
    }).join('');
    const why = p.effect === 'unmapped' ? '<ul><li>尚未對應任何類別，無法判定權限</li></ul>'
      : reasons ? `<ul>${reasons}</ul>` : `<ul><li>沒有命中規則，依預設：${EFFECT_LABEL[S.policy.default_effect]}</li></ul>`;
    return `<div class="perm"><div class="head"><span>${esc(r.label)}</span>${effectChip(p.effect)}</div>${why}</div>`;
  }).join('');
}

export function classOptions() {
  return S.classes.map((c) => `<option value="${esc(c.id)}">${esc(c.label)}｜${esc(c.chain[0] || c.label)}</option>`).join('');
}

export function resolveClass(value) {
  const v = value.trim();
  if (idx.classById.has(v)) return v;
  const byLabel = S.classes.filter((c) => c.label === v || `${c.label}｜${c.chain[0] || c.label}` === v);
  return byLabel.length === 1 ? byLabel[0].id : v;
}

