const NR_URL = 'http://localhost:1881/ui';

function token()  { return localStorage.getItem('cinrec_token'); }
function cerrarSesion() { localStorage.clear(); window.location.href = 'index.html?logout=1'; }

(function init() {
  if (!token()) { window.location.href = 'index.html'; return; }

  const u = JSON.parse(localStorage.getItem('cinrec_user') || '{}');
  document.getElementById('user-name').textContent   = u.name || u.email || '';
  document.getElementById('user-avatar').textContent = (u.name || u.email || 'U')[0].toUpperCase();

  renderIframe();
  verificarEstado();
})();

function renderIframe() {
  document.getElementById('nr-area').innerHTML = `
    <iframe
      id="nr-iframe"
      class="nr-frame"
      src="${NR_URL}"
      title="Node-RED Dashboard"
      allow="fullscreen"
    ></iframe>`;
}

function recargarDashboard() {
  const iframe = document.getElementById('nr-iframe');
  if (iframe) {
    iframe.src = iframe.src;
  } else {
    renderIframe();
  }
  verificarEstado();
}

async function verificarEstado() {
  const dot  = document.getElementById('nr-dot');
  const text = document.getElementById('nr-status-text');
  try {
    const ctrl = new AbortController();
    setTimeout(() => ctrl.abort(), 3000);
    const res = await fetch(NR_URL, { mode: 'no-cors', signal: ctrl.signal });
    // no-cors siempre devuelve opaque (type='opaque') si llega — eso indica que el servidor responde
    dot.className  = 'nr-dot online';
    text.textContent = 'Node-RED activo';
  } catch {
    dot.className  = 'nr-dot offline';
    text.textContent = 'No disponible';
    mostrarOffline();
  }
}

function mostrarOffline() {
  document.getElementById('nr-area').innerHTML = `
    <div class="nr-offline">
      <div class="icon">📡</div>
      <h2>Node-RED no está disponible</h2>
      <p>Asegúrate de que el contenedor Docker está en marcha:</p>
      <p><code>docker compose up -d nodered</code></p>
      <p>El dashboard estará disponible en <code>localhost:1881/ui</code> una vez iniciado.</p>
      <button class="btn btn-primary" onclick="recargarDashboard()">Reintentar</button>
    </div>`;
}
