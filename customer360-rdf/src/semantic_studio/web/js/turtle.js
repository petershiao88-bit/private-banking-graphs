import { onState } from './store.js';
import { $, api, toast } from './util.js';

/* Turtle 原文檢視。 */

export let turtleCache = { what: null, text: '' };
export async function loadTurtle() {
  const what = $('#turtle-what').value;
  $('#turtle-download').href = '/api/turtle?what=' + what;
  $('#turtle-download').setAttribute('download', `${what}.ttl`);
  try {
    if (turtleCache.what !== what) turtleCache = { what, text: await api('/api/turtle?what=' + what) };
    const q = $('#turtle-filter').value.trim();
    const blocks = turtleCache.text.split(/\n\n+/);
    $('#turtle-text').textContent = q ? blocks.filter((b) => b.includes(q)).join('\n\n') : turtleCache.text;
  } catch (err) { toast(err.message, true); }
}
$('#turtle-what').addEventListener('change', loadTurtle);
$('#turtle-filter').addEventListener('input', loadTurtle);


onState(() => { turtleCache = { what: null, text: '' }; });
