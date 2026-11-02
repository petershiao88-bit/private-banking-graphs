import './graph.js';
import './detail.js';
import './dictionary.js';
import './policy.js';
import './owl.js';
import './shacl.js';
import './turtle.js';
import { cy } from './graph.js';
import { S, actions, idx, setState } from './store.js';
import { loadTurtle } from './turtle.js';
import { $, $$, api, toast } from './util.js';

/* 進入點：分頁切換、全域點擊導覽、重新載入、啟動。 */
document.addEventListener('click', (e) => {
  const node = e.target.closest('[data-node]');
  if (node) { actions.goToNode(node.dataset.node); }
});


$('#tabs').addEventListener('click', (e) => {
  const btn = e.target.closest('button[data-tab]');
  if (btn) switchTab(btn.dataset.tab);
});
export function switchTab(tab) {
  $$('#tabs button').forEach((b) => b.classList.toggle('active', b.dataset.tab === tab));
  $$('.tab').forEach((s) => s.classList.toggle('active', s.id === 'tab-' + tab));
  if (tab === 'graph' && cy) { cy.resize(); }
  if (tab === 'turtle') loadTurtle();
}

$('#reload').addEventListener('click', async () => {
  try { setState(await api('/api/reload', {})); toast('已重新載入'); } catch (err) { toast(err.message, true); }
});


(async () => {
  try { setState(await api('/api/state')); } catch (err) { toast('載入失敗：' + err.message, true); }
})();

actions.switchTab = switchTab;

// 除錯與自動化測試用：在瀏覽器主控台可用 __studio.actions.goToNode(...)
window.__studio = { actions, idx, get S() { return S; } };
