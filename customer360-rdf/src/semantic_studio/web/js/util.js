/* 共用小工具：DOM、跳脫、API、提示訊息。 */
export const $ = (sel, el = document) => el.querySelector(sel);
export const $$ = (sel, el = document) => [...el.querySelectorAll(sel)];
export const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
export const COLORS = { holding: '#3b5bdb', bank: '#0c8599', securities: '#d9480f' };
export const EFFECT_LABEL = { allow: '可看', deny: '不可看', unmapped: '未對應' };

export async function api(path, body) {
  const opts = body === undefined ? {} : {
    method: 'POST', headers: { 'Content-Type': 'application/json', 'X-Studio': '1' }, body: JSON.stringify(body),
  };
  const res = await fetch(path, opts);
  const isJson = (res.headers.get('content-type') || '').includes('json');
  const data = isJson ? await res.json() : await res.text();
  if (!res.ok) throw new Error((isJson && data.error) || data || res.statusText);
  return data;
}

export function toast(msg, error = false) {
  const el = $('#toast');
  el.textContent = msg;
  el.className = 'show' + (error ? ' error' : '');
  clearTimeout(toast.t);
  toast.t = setTimeout(() => { el.className = ''; }, error ? 5000 : 2200);
}

