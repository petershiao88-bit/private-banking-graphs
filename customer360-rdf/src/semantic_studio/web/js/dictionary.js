import { S, actions, classChip, classOptions, idx, onState, permissionBlock, resolveClass, resultHtml, setState, ui } from './store.js';
import { $, $$, api, esc, toast } from './util.js';

/* 業務字典對應：詞條清單、對應編輯器、即時預覽、匯入。 */

$('#term-filter').addEventListener('input', renderTermList);
$('#term-seg').addEventListener('click', (e) => {
  const b = e.target.closest('button');
  if (!b) return;
  ui.termFilter = b.dataset.f;
  $$('#term-seg button').forEach((x) => x.classList.toggle('on', x === b));
  renderTermList();
});
$('#new-term').addEventListener('click', () => openEditor(null));

export function renderTermList() {
  const q = $('#term-filter').value.trim().toLowerCase();
  const items = S.terms.filter((t) => {
    if (q && !(`${t.name} ${t.id} ${t.definition}`.toLowerCase().includes(q))) return false;
    if (ui.termFilter === 'dictionary') return t.origin !== 'pg';
    if (ui.termFilter === 'pg') return t.origin === 'pg';
    if (ui.termFilter === 'unmapped') return !t.mappings.length;
    if (ui.termFilter === 'issues') return idx.resultsByNode.has('term:' + t.id);
    return true;
  }).sort((a, b) => (a.origin === 'pg') - (b.origin === 'pg') || a.id.localeCompare(b.id));
  $('#term-items').innerHTML = items.map((t) => {
    const issues = (idx.resultsByNode.get('term:' + t.id) || []).length;
    return `<div class="item ${ui.editing && ui.editing.original_id === t.id ? 'active' : ''}" data-term="${esc(t.id)}">
      <div class="name">${esc(t.name)}</div>
      <div class="meta"><span class="mono">${esc(t.id)}</span> · ${t.origin === 'pg' ? 'PG' : esc(t.source)} · ${t.mappings.length} 個對應${issues ? ` · <span style="color:#e03131">${issues} 個 SHACL 問題</span>` : ''}</div>
    </div>`;
  }).join('') || '<div class="empty">沒有符合的詞條。</div>';
}
$('#term-items').addEventListener('click', (e) => {
  const item = e.target.closest('[data-term]');
  if (!item) return;
  const t = idx.termById.get(item.dataset.term);
  openEditor(t.editable ? t.id : null, t.editable ? null : t, !t.editable);
});

export function openEditor(termId, copyFrom = null, readonly = false) {
  if (termId) {
    const t = idx.termById.get(termId);
    ui.editing = { original_id: t.id, id: t.id, name: t.name, definition: t.definition, source: t.source, mappings: t.mappings.map((m) => ({ class: m.class, role: m.role })), readonly: false };
  } else if (copyFrom) {
    ui.editing = { original_id: readonly ? copyFrom.id : null, id: readonly ? copyFrom.id : 'new.' + copyFrom.id, name: copyFrom.name, definition: copyFrom.definition,
      source: readonly ? copyFrom.source : `複製自 ${copyFrom.id}`, mappings: copyFrom.mappings.map((m) => ({ class: m.class, role: m.role })), readonly };
  } else {
    ui.editing = { original_id: null, id: '', name: '', definition: '', source: '業務字典', mappings: [], readonly: false };
  }
  ui.editing.preview = null;
  ui.editing.suggestions = null;
  renderTermList();
  renderEditor();
  schedulePreview();
}

export function renderEditor() {
  const box = $('#term-editor');
  const e = ui.editing;
  if (!e) { box.innerHTML = '<div class="empty">從左邊選一個詞條，或建立新詞條。<br>新詞條對應到類別組合後，會自動繼承那些類別的權限，並以 SHACL 驗證對應是否合格。</div>'; return; }
  const ro = e.readonly;
  const roleOptions = (sel) => Object.entries(S.mapping_roles).map(([k, v]) => `<option value="${k}" ${k === sel ? 'selected' : ''}>${esc(v)}</option>`).join('');
  box.innerHTML = `
    ${ro ? `<div class="readonly-note">這是 department-pg 的既有詞條，在這裡唯讀。要調整對應請按「複製為新詞條」。</div>` : ''}
    <h2>${e.original_id ? esc(e.name || e.id) : '新業務字典詞條'}</h2>
    <div class="form" style="margin-top:12px">
      <label>ID</label><input id="f-id" value="${esc(e.id)}" placeholder="例如 wm.fund_subscription_fee" ${ro ? 'disabled' : ''}>
      <label>名稱</label><input id="f-name" value="${esc(e.name)}" ${ro ? 'disabled' : ''}>
      <label>定義</label><textarea id="f-def" rows="2" ${ro ? 'disabled' : ''} style="font-family:inherit;font-size:14px">${esc(e.definition)}</textarea>
      <label>來源</label><input id="f-src" value="${esc(e.source)}" ${ro ? 'disabled' : ''}>
    </div>
    <h3>對應到的類別組合</h3>
    <datalist id="class-options">${classOptions()}</datalist>
    <table class="map-table"><thead><tr><th style="width:130px">角色</th><th>類別（輸入中文名稱或 ID）</th><th>上層鏈</th><th style="width:60px"></th></tr></thead><tbody>
    ${e.mappings.map((m, i) => {
      const c = idx.classById.get(m.class);
      return `<tr data-i="${i}"><td><select class="m-role" ${ro ? 'disabled' : ''}>${roleOptions(m.role)}</select></td>
        <td><input class="m-class" list="class-options" value="${esc(m.class)}" ${ro ? 'disabled' : ''}>${c ? `<div class="small-text">${classChip(c.uri)}</div>` : m.class ? '<div class="small-text" style="color:#e03131">本體中沒有這個類別</div>' : ''}</td>
        <td class="small-text">${c ? esc(c.chain[0] || '頂層類別') : ''}</td>
        <td>${ro ? '' : '<button class="ghost small m-del" title="移除">✕</button>'}</td></tr>`;
    }).join('')}
    </tbody></table>
    ${ro ? '' : `<div class="row" style="margin-top:8px"><button class="small" id="m-add">＋ 加入類別</button><button class="small ghost" id="m-suggest">依名稱建議類別</button></div>
    <div class="suggestions" id="suggestions">${(e.suggestions || []).map((s, i) => e.mappings.some((m) => m.class === s.class) ? '' : `<button class="small ghost" data-sug="${i}">＋ ${esc(s.label)} <span class="mono muted">${esc(s.class)}</span>（${esc(S.mapping_roles[s.role])}）</button>`).join('')}</div>`}
    <div class="columns">
      <div><h3>繼承到的權限</h3><div id="pv-perm">${e.preview ? permissionBlock(e.preview.permissions) : '<div class="muted small-text">計算中…</div>'}</div></div>
      <div><h3>SHACL 驗證</h3><div id="pv-shacl">${e.preview ? (e.preview.validation.map(resultHtml).join('') || '<div class="result Info">通過所有 shape。</div>') : ''}</div>
        <details style="margin-top:10px"><summary class="small-text">這個詞條的 RDF</summary><pre class="code">${esc(e.preview ? e.preview.turtle.replace(/^@prefix[^\n]*\n/gm, '').trim() : '')}</pre></details>
        ${e.error ? `<div class="result">${esc(e.error)}</div>` : ''}</div>
    </div>
    <div class="actions">
      ${ro ? '<button class="primary" id="t-copy">複製為新詞條</button>' : `<button class="primary" id="t-save">儲存</button>
      ${e.original_id ? '<button class="danger" id="t-del">刪除詞條</button>' : ''}`}
      <button class="ghost" id="t-graph" ${e.original_id ? '' : 'disabled'}>在圖上查看</button>
    </div>`;
  if (ro) {
    $('#t-copy').addEventListener('click', () => openEditor(null, idx.termById.get(e.original_id)));
  } else {
    [['#f-id', 'id'], ['#f-name', 'name'], ['#f-def', 'definition'], ['#f-src', 'source']].forEach(([sel, key]) => {
      $(sel).addEventListener('input', (ev) => { e[key] = ev.target.value; schedulePreview(); });
    });
    $$('.m-role', box).forEach((el) => el.addEventListener('change', (ev) => { e.mappings[+ev.target.closest('tr').dataset.i].role = ev.target.value; schedulePreview(true); }));
    $$('.m-class', box).forEach((el) => el.addEventListener('change', (ev) => {
      const m = e.mappings[+ev.target.closest('tr').dataset.i];
      m.class = resolveClass(ev.target.value);
      if (idx.classById.has(m.class) && idx.classById.get(m.class).ancestors.includes(idx.classById.get('fh:FinancialProduct')?.uri)) m.role = m.role === 'primary' && e.mappings.length > 1 ? 'product' : m.role;
      schedulePreview(true);
    }));
    $$('.m-del', box).forEach((el) => el.addEventListener('click', (ev) => { e.mappings.splice(+ev.target.closest('tr').dataset.i, 1); schedulePreview(true); }));
    $('#m-add').addEventListener('click', () => { e.mappings.push({ class: '', role: e.mappings.length ? 'product' : 'primary' }); renderEditor(); $$('.m-class', box).pop().focus(); });
    $('#m-suggest').addEventListener('click', async () => {
      try { e.suggestions = await api('/api/suggest', { name: e.name, definition: e.definition }); if (!e.suggestions.length) toast('沒有找到名稱相近的類別'); renderEditor(); } catch (err) { toast(err.message, true); }
    });
    $$('[data-sug]', box).forEach((el) => el.addEventListener('click', () => {
      const s = e.suggestions[+el.dataset.sug];
      if (!e.mappings.some((m) => m.class === s.class)) e.mappings.push({ class: s.class, role: s.role });
      schedulePreview(true);
    }));
    $('#t-save').addEventListener('click', saveTerm);
    if (e.original_id) $('#t-del').addEventListener('click', deleteTerm);
  }
  if (e.original_id) $('#t-graph').addEventListener('click', () => actions.goToNode('term:' + e.original_id));
}

export function editorPayload() {
  const e = ui.editing;
  return { id: e.id.trim(), name: e.name.trim(), definition: e.definition.trim(), source: e.source.trim(),
    mappings: e.mappings.filter((m) => m.class).map((m) => ({ class: m.class, role: m.role })) };
}

export function schedulePreview(rerender = false) {
  if (rerender) renderEditor();
  clearTimeout(ui.previewTimer);
  ui.previewTimer = setTimeout(async () => {
    const e = ui.editing;
    if (!e) return;
    const payload = editorPayload();
    if (!payload.id) payload.id = 'preview.term';
    try {
      e.preview = await api('/api/term/preview', { term: payload });
      e.error = null;
    } catch (err) { e.preview = null; e.error = err.message; }
    if (ui.editing === e) {
      const keep = document.activeElement && document.activeElement.id;
      const pos = document.activeElement && document.activeElement.selectionStart;
      renderEditor();
      if (keep && $('#' + keep)) { $('#' + keep).focus(); try { $('#' + keep).setSelectionRange(pos, pos); } catch (_) { /* select 等元素 */ } }
    }
  }, 300);
}

export async function saveTerm() {
  const e = ui.editing;
  try {
    const state = await api('/api/term/save', { term: editorPayload(), original_id: e.original_id });
    const id = editorPayload().id;
    setState(state);
    openEditor(id);
    toast('已儲存到業務字典');
  } catch (err) { toast(err.message, true); }
}
export async function deleteTerm() {
  const e = ui.editing;
  if (!confirm(`確定刪除詞條「${e.name || e.id}」？`)) return;
  try { ui.editing = null; setState(await api('/api/term/delete', { id: e.original_id })); toast('已刪除'); } catch (err) { toast(err.message, true); }
}

export const IMPORT_EXAMPLES = {
  csv: 'id,name,definition,mappings\nwm.bond_coupon,海外債券配息,客戶持有海外債券收到的配息,\nwm.insurance_fee,保險佣金收入,銀行銷售保險商品的佣金收入,bank:BankFeeIncome@primary;bank:InsuranceProduct@product',
  json: '[\n  {"id": "wm.bond_coupon", "name": "海外債券配息", "definition": "客戶持有海外債券收到的配息"},\n  {"id": "wm.insurance_fee", "name": "保險佣金收入", "mappings": [{"class": "bank:BankFeeIncome", "role": "primary"}, {"class": "bank:InsuranceProduct", "role": "product"}]}\n]',
};
$('#import-text').placeholder = IMPORT_EXAMPLES.csv;
$('#import-format').addEventListener('change', (e) => { $('#import-text').placeholder = IMPORT_EXAMPLES[e.target.value]; });
$('#import-file').addEventListener('change', async (e) => {
  const file = e.target.files[0];
  if (!file) return;
  $('#import-text').value = await file.text();
  if (file.name.endsWith('.json')) $('#import-format').value = 'json';
});
$('#import-go').addEventListener('click', async () => {
  try {
    const res = await api('/api/import', { text: $('#import-text').value, format: $('#import-format').value, source: $('#import-source').value });
    $('#import-text').value = '';
    setState(res.state);
    toast(`已匯入 ${res.added.length} 個詞條，請逐一設定對應`);
    ui.termFilter = 'unmapped';
    $$('#term-seg button').forEach((x) => x.classList.toggle('on', x.dataset.f === 'unmapped'));
    renderTermList();
    if (res.added.length) openEditor(res.added[0]);
  } catch (err) { toast(err.message, true); }
});


actions.openEditor = openEditor;
onState(() => { renderTermList(); renderEditor(); });
