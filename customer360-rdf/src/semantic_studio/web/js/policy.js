import { S, actions, classChip, classOptions, idx, onState, resolveClass, setState, termChip, ui } from './store.js';
import { $, $$, EFFECT_LABEL, api, esc, toast } from './util.js';

/* 權限：角色、規則、類別 × 角色矩陣。 */

export function policyDraft() {
  if (!ui.policyDraft) ui.policyDraft = JSON.parse(JSON.stringify(S.policy));
  return ui.policyDraft;
}

export function renderPolicy() {
  const box = $('#policy-panel');
  const d = policyDraft();
  const roleOpts = (sel) => d.roles.map((r) => `<option value="${esc(r.id)}" ${r.id === sel ? 'selected' : ''}>${esc(r.label)}</option>`).join('');
  const matrixRoles = S.policy.roles;
  const deniedTerms = matrixRoles.map((r) => ({ role: r, terms: S.terms.filter((t) => t.permissions[r.id].effect === 'deny') }));
  box.innerHTML = `
    <h2>類別權限</h2>
    <p class="muted">單一類別的規則會沿 rdfs:subClassOf（含 OWL 推理）套用到所有子類別；多個類別的「組合規則」只套用到同時涵蓋這些類別的字典詞條。同一角色只要有任何拒絕就不可看（取最嚴格）。</p>
    <div class="policy-grid">
      <div>
        <h3>角色</h3>
        <table><thead><tr><th>ID</th><th>名稱</th><th></th></tr></thead><tbody>
        ${d.roles.map((r, i) => `<tr data-i="${i}"><td><input class="r-id" value="${esc(r.id)}"></td><td><input class="r-label" value="${esc(r.label)}"></td><td><button class="ghost small r-del">✕</button></td></tr>`).join('')}
        </tbody></table>
        <div class="row" style="margin-top:8px"><button class="small" id="r-add">＋ 角色</button>
          <label class="small-text muted">沒有命中規則時：</label>
          <select id="p-default"><option value="allow" ${d.default_effect === 'allow' ? 'selected' : ''}>可看</option><option value="deny" ${d.default_effect === 'deny' ? 'selected' : ''}>不可看</option></select></div>
      </div>
      <div>
        <h3>目前被拒絕的詞條（已儲存的規則）</h3>
        ${deniedTerms.map(({ role, terms }) => `<div class="small-text" style="margin-bottom:6px"><b>${esc(role.label)}</b>（${terms.length}）：${terms.map((t) => termChip(t.id)).join('') || '<span class="muted">無</span>'}</div>`).join('')}
      </div>
    </div>
    <h3>規則</h3>
    <datalist id="policy-class-options">${classOptions()}</datalist>
    <table><thead><tr><th style="width:170px">規則 ID</th><th style="width:120px">角色</th><th style="width:100px">效果</th><th>類別（多個＝組合規則）</th><th>說明</th><th style="width:40px"></th></tr></thead><tbody>
    ${d.rules.map((r, i) => `<tr data-i="${i}">
      <td><input class="p-id" value="${esc(r.id)}"></td>
      <td><select class="p-role">${roleOpts(r.role)}</select></td>
      <td><select class="p-effect"><option value="deny" ${r.effect === 'deny' ? 'selected' : ''}>拒絕</option><option value="allow" ${r.effect === 'allow' ? 'selected' : ''}>允許</option></select></td>
      <td><div class="classes-cell">${r.classes.map((c, j) => `<span class="chip ${idx.classById.get(c)?.layer || ''}">${esc(idx.classById.get(c)?.label || c)} <a href="#" class="p-cdel" data-j="${j}">✕</a></span>`).join(r.classes.length > 1 ? ' × ' : '')}
        <input class="p-cadd" list="policy-class-options" placeholder="加入類別"></div></td>
      <td><input class="p-note" value="${esc(r.note)}"></td>
      <td><button class="ghost small p-del">✕</button></td></tr>`).join('')}
    </tbody></table>
    <div class="actions"><button class="small" id="p-add">＋ 規則</button><button class="primary" id="p-save">儲存權限</button><button class="ghost" id="p-reset">放棄變更</button></div>
    <h3>類別 × 角色（已儲存的規則）</h3>
    <table class="matrix"><thead><tr><th>類別</th>${matrixRoles.map((r) => `<th>${esc(r.label)}</th>`).join('')}</tr></thead><tbody>
    ${S.layers.map((l) => S.classes.filter((c) => c.layer === l.key).map((c) => `<tr><td>${classChip(c.uri)}<span class="mono muted small-text">${esc(c.id)}</span></td>
      ${matrixRoles.map((r) => { const p = c.permissions[r.id]; return `<td class="eff-${p.effect}" title="${esc(p.matches.map((m) => m.note || m.rule).join('；'))}">${EFFECT_LABEL[p.effect]}${p.matches.some((m) => m.via[0].inherited) ? '（繼承）' : ''}</td>`; }).join('')}</tr>`).join('')).join('')}
    </tbody></table>`;
  const rows = (sel) => $$(sel, box);
  rows('.r-id').forEach((el) => el.addEventListener('change', (e) => {
    const i = +e.target.closest('tr').dataset.i; const old = d.roles[i].id; d.roles[i].id = e.target.value.trim();
    d.rules.forEach((r) => { if (r.role === old) r.role = d.roles[i].id; });
  }));
  rows('.r-label').forEach((el) => el.addEventListener('change', (e) => { d.roles[+e.target.closest('tr').dataset.i].label = e.target.value; }));
  rows('.r-del').forEach((el) => el.addEventListener('click', (e) => {
    const i = +e.target.closest('tr').dataset.i; const id = d.roles[i].id;
    if (d.rules.some((r) => r.role === id)) { toast('這個角色還有規則，請先刪除規則', true); return; }
    d.roles.splice(i, 1); renderPolicy();
  }));
  $('#r-add').addEventListener('click', () => { d.roles.push({ id: 'role' + (d.roles.length + 1), label: '新角色' }); renderPolicy(); });
  $('#p-default').addEventListener('change', (e) => { d.default_effect = e.target.value; });
  rows('.p-id').forEach((el) => el.addEventListener('change', (e) => { d.rules[+e.target.closest('tr').dataset.i].id = e.target.value.trim(); }));
  rows('.p-role').forEach((el) => el.addEventListener('change', (e) => { d.rules[+e.target.closest('tr').dataset.i].role = e.target.value; }));
  rows('.p-effect').forEach((el) => el.addEventListener('change', (e) => { d.rules[+e.target.closest('tr').dataset.i].effect = e.target.value; }));
  rows('.p-note').forEach((el) => el.addEventListener('change', (e) => { d.rules[+e.target.closest('tr').dataset.i].note = e.target.value; }));
  rows('.p-del').forEach((el) => el.addEventListener('click', (e) => { d.rules.splice(+e.target.closest('tr').dataset.i, 1); renderPolicy(); }));
  rows('.p-cdel').forEach((el) => el.addEventListener('click', (e) => { e.preventDefault(); d.rules[+e.target.closest('tr').dataset.i].classes.splice(+el.dataset.j, 1); renderPolicy(); }));
  rows('.p-cadd').forEach((el) => el.addEventListener('change', (e) => {
    const id = resolveClass(e.target.value);
    if (!idx.classById.has(id)) { toast('本體中沒有這個類別', true); return; }
    const rule = d.rules[+e.target.closest('tr').dataset.i];
    if (!rule.classes.includes(id)) rule.classes.push(id);
    renderPolicy();
  }));
  $('#p-add').addEventListener('click', () => { d.rules.push({ id: 'rule-' + (d.rules.length + 1), role: d.roles[0]?.id || '', effect: 'deny', classes: [], note: '' }); renderPolicy(); });
  $('#p-reset').addEventListener('click', () => { ui.policyDraft = null; renderPolicy(); });
  $('#p-save').addEventListener('click', async () => {
    try { setState(await api('/api/policy/save', { policy: d })); toast('權限已儲存，所有詞條已重新計算'); } catch (err) { toast(err.message, true); }
  });
}


onState(renderPolicy);
