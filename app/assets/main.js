// app/assets/main.js
const el = (id) => document.getElementById(id);
let lastResult = null;

function codeNode(text) {
  const c = document.createElement('code');
  c.textContent = text ?? '';
  return c;
}
function replaceWithCode(selector, text, root) {
  const target = (root || document).querySelector(selector);
  if (!target) return;
  const holder = document.createElement('span');
  holder.appendChild(codeNode(text));
  target.replaceWith(holder);
}

async function runQuery() {
  const url = (el('url').value || '').trim();
  const query = (el('query').value || '').trim();
  const html = el('html').value || '';
  const useChrome = !!el('useChrome')?.checked;
  const waitSelector = (el('waitSelector')?.value || '').trim();

  el('status').textContent = 'Running…';
  el('exportBtn').disabled = true;
  el('runBtn').disabled = true;

  try {
    const body = {
      url,
      html,
      query,
      render: useChrome ? 'chrome' : 'requests',
      wait_selector: useChrome && waitSelector ? waitSelector : null,
      wait_ms: useChrome ? 1500 : null,
      reuse: true
    };

    const resp = await fetch('/api/locate', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify(body),
      // IMPORTANT: do NOT set window.location; just fetch JSON
    });
    const data = await resp.json();
    if (!resp.ok) throw new Error(data.error || resp.statusText);

    lastResult = data;
    el('exportBtn').disabled = false;

    renderBest(data.best);
    renderCandidates(data.candidates || []);

    const preview = document.getElementById('preview');
    if (useChrome) {
      document.getElementById('previewNote').textContent =
        'Live highlight applied in the persistent Chrome window (same tab reused).';
      preview.srcdoc = '<!-- live in Chrome -->';
    } else {
      document.getElementById('previewNote').textContent =
        'Embedded preview below (static HTML).';
      preview.srcdoc = data.previewHtml || '';
    }

    el('status').textContent = `Candidates: ${data.totalCandidates}`;
  } catch (e) {
    el('status').textContent = 'Error: ' + e.message;
    console.error(e);
  } finally {
    el('runBtn').disabled = false;
  }
}

// Click handlers (buttons are type="button", so no submit)
el('runBtn').addEventListener('click', (ev) => {
  ev.preventDefault();  // extra safety
  runQuery();
});
el('exportBtn').addEventListener('click', (ev) => {
  ev.preventDefault();
  if (!lastResult) return;
  const name = makeFileName(lastResult.query || 'nl-locator');
  const blob = new Blob([JSON.stringify(lastResult, null, 2)], {type: 'application/json'});
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = name + '.json';
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
});

// Press Enter in the query input to run (without reload)
['query','url','waitSelector'].forEach(id => {
  const input = el(id);
  if (!input) return;
  input.addEventListener('keydown', (ev) => {
    if (ev.key === 'Enter') {
      ev.preventDefault(); // stop form-like submission
      runQuery();
    }
  });
});

function makeFileName(q){
  return (q || 'nl-locator').toLowerCase()
    .replace(/[^a-z0-9]+/g,'-')
    .replace(/(^-|-$)/g,'');
}

function renderBest(best) {
  const container = document.getElementById('best');

  if (!best) {
    container.innerHTML = `<div class="muted">No strong match found.</div>`;
    return;
  }

  // Use <pre> to preserve newlines
  container.innerHTML = `
    <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">
      <span class="badge">score ${best.score}</span>
      <strong>${best.tag}</strong>
    </div>
    <div class="muted small">${best.text || '(no text)'}</div>
    <pre class="block-code" id="bestLoc"></pre>
  `;

  // Use textContent (not innerHTML) to avoid escaping issues
  const loc = container.querySelector('#bestLoc');
  loc.textContent = `CSS: ${best.css || ''}\nXPath: ${best.xpath || ''}`;
}


function renderCandidates(list) {
  const tb = document.querySelector('#candidates tbody');
  tb.innerHTML = '';

  list.forEach((c, i) => {
    const tr = document.createElement('tr');

    const tdScore = document.createElement('td');
    tdScore.textContent = String(c.score);

    const tdTag = document.createElement('td');
    tdTag.textContent = c.tag || '';

    const tdText = document.createElement('td');
    tdText.textContent = c.text || '';

    // Locator block (multi-line)
    const tdLoc = document.createElement('td');
    const pre = document.createElement('pre');
    pre.className = 'block-code';
    pre.textContent = `#${i + 1}\nCSS: ${c.css || ''}\nXPath: ${c.xpath || ''}`;
    tdLoc.appendChild(pre);

    tr.append(tdScore, tdTag, tdText, tdLoc);
    tb.appendChild(tr);
  });
}
