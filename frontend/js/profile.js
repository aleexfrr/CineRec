// ===== CONFIGURACIÓN =====
const BASE_API = 'http://localhost:8000/api';

const GENRE_COLORS = {
  'Action':['#7f0000','#b71c1c'],'Adventure':['#bf360c','#e64a19'],
  'Animation':['#1b5e20','#388e3c'],'Children':['#f57f17','#fbc02d'],
  'Comedy':['#e65100','#ff8f00'],'Crime':['#212121','#424242'],
  'Documentary':['#1a237e','#283593'],'Drama':['#0d47a1','#1565c0'],
  'Fantasy':['#4a148c','#7b1fa2'],'Film-Noir':['#111','#333'],
  'Horror':['#3d0000','#6d0a0a'],'Musical':['#880e4f','#c2185b'],
  'Mystery':['#263238','#455a64'],'Romance':['#880e4f','#ad1457'],
  'Sci-Fi':['#006064','#00838f'],'Thriller':['#1a237e','#311b92'],
  'War':['#3e2723','#5d4037'],'Western':['#4e342e','#6d4c41'],
};

function colorPelicula(genres) {
  const c = GENRE_COLORS[genres?.[0]] || ['#1a1a2e','#2a2a4a'];
  return `linear-gradient(160deg, ${c[0]}, ${c[1]})`;
}

function posterCardHtml(p) {
  const bg = `background:${colorPelicula(p.genres)}`;
  const img = p.poster_url
    ? `<img src="${p.poster_url}" alt="${p.title}" class="nf-poster-img" onerror="this.style.display='none'" loading="lazy">`
    : '';
  const titleFallback = p.poster_url ? '' : `<div class="profile-movie-poster-title">${p.title}</div>`;
  return `<div class="profile-movie-poster" style="${bg}">${img}${titleFallback}</div>`;
}

// ===== UTILIDADES =====
function obtenerToken() { return localStorage.getItem('cinrec_token'); }

function obtenerUsuario() {
  try { return JSON.parse(localStorage.getItem('cinrec_user')); }
  catch { return null; }
}

function guardarUsuarioLocal(datos) {
  localStorage.setItem('cinrec_user', JSON.stringify(datos));
}

function cerrarSesion() {
  localStorage.clear();
  window.location.href = 'index.html?logout=1';
}

function mostrarAviso(mensaje, tipo = 'success') {
  const contenedor = document.getElementById('toast-container');
  const aviso = document.createElement('div');
  aviso.className = `toast ${tipo}`;
  aviso.innerHTML = `<span class="toast-icon">${tipo === 'success' ? '✅' : '❌'}</span> ${mensaje}`;
  contenedor.appendChild(aviso);
  setTimeout(() => aviso.remove(), 3500);
}

function mostrarAlertaPanel(idPanel, mensaje, tipo = 'error') {
  const elemento = document.getElementById(`${idPanel}-alert`);
  if (!elemento) return;
  elemento.className = `alert alert-${tipo}`;
  elemento.textContent = mensaje;
  elemento.style.display = 'flex';
}

function ocultarAlertaPanel(idPanel) {
  const elemento = document.getElementById(`${idPanel}-alert`);
  if (elemento) elemento.style.display = 'none';
}

function establecerErrorCampo(id, mensaje) {
  const elemento = document.getElementById(id);
  if (elemento) elemento.textContent = mensaje;
}

function limpiarErrores(...ids) {
  ids.forEach(id => establecerErrorCampo(id, ''));
}

function alternarContrasena(idEntrada, boton) {
  const entrada = document.getElementById(idEntrada);
  const visible = entrada.type === 'text';
  entrada.type = visible ? 'password' : 'text';
  boton.textContent = visible ? '👁️' : '🙈';
}

// ===== PANELES =====
const panelesCargados = new Set();

function mostrarPanel(nombre) {
  ['info', 'watchlist', 'ratings', 'security', 'danger'].forEach(p => {
    document.getElementById(`panel-${p}`).classList.toggle('active', p === nombre);
    document.getElementById(`nav-${p}`).classList.toggle('active', p === nombre);
  });

  if (nombre === 'watchlist' && !panelesCargados.has('watchlist')) {
    panelesCargados.add('watchlist');
    cargarMiLista();
  }
  if (nombre === 'ratings' && !panelesCargados.has('ratings')) {
    panelesCargados.add('ratings');
    cargarMisValoraciones();
  }
}

// ===== INICIALIZAR =====
(function inicializar() {
  if (!obtenerToken()) {
    window.location.href = 'index.html';
    return;
  }
  cargarPerfil();
})();

async function cargarPerfil() {
  const usuario = obtenerUsuario();
  if (!usuario) { cerrarSesion(); return; }

  // Rellenar sidebar con datos locales
  const inicial = (usuario.name || usuario.email || 'U')[0].toUpperCase();
  document.getElementById('user-avatar').textContent = inicial;
  document.getElementById('user-name').textContent = usuario.name || usuario.email;
  document.getElementById('sidebar-avatar').textContent = inicial;
  document.getElementById('sidebar-name').textContent = usuario.name || '—';
  document.getElementById('sidebar-email').textContent = usuario.email || '—';
  document.getElementById('detail-id').textContent = usuario.id || '—';
  document.getElementById('detail-role').textContent = usuario.role || 'usuario';

  const desde = usuario.created_at
    ? new Date(usuario.created_at).toLocaleDateString('es-ES', { year: 'numeric', month: 'long' })
    : 'desconocida';
  document.getElementById('sidebar-since').textContent = `Miembro desde ${desde}`;
  document.getElementById('detail-date').textContent = desde;

  // Prefill edición
  document.getElementById('edit-name').value = usuario.name || '';
  document.getElementById('edit-email').value = usuario.email || '';

  // Intentar cargar datos frescos del backend
  try {
    const respuesta = await fetch(`${BASE_API}/auth/me`, {
      headers: { 'Authorization': `Bearer ${obtenerToken()}` },
    });
    if (respuesta.ok) {
      const datos = await respuesta.json();
      const fusionado = { ...usuario, ...datos };
      guardarUsuarioLocal(fusionado);
      actualizarBarraLateral(fusionado);

      document.getElementById('stat-rated').textContent = datos.stats?.rated ?? 0;
      document.getElementById('stat-watchlist').textContent = datos.stats?.watchlist ?? 0;


    }
  } catch {
    // sin backend: mostrar datos locales sin estadísticas
  }
}

function actualizarBarraLateral(usuario) {
  const inicial = (usuario.name || usuario.email || 'U')[0].toUpperCase();
  document.getElementById('sidebar-avatar').textContent = inicial;
  document.getElementById('sidebar-name').textContent = usuario.name || '—';
  document.getElementById('sidebar-email').textContent = usuario.email || '—';
  document.getElementById('edit-name').value = usuario.name || '';
  document.getElementById('edit-email').value = usuario.email || '';
}

// ===== GUARDAR INFORMACIÓN =====
async function guardarInfo() {
  limpiarErrores('edit-name-error', 'edit-email-error');
  ocultarAlertaPanel('info');

  const nombre = document.getElementById('edit-name').value.trim();
  const correo = document.getElementById('edit-email').value.trim();

  let valido = true;
  if (!nombre || nombre.length < 2) { establecerErrorCampo('edit-name-error', 'Mínimo 2 caracteres'); valido = false; }
  if (!correo || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(correo)) { establecerErrorCampo('edit-email-error', 'Correo no válido'); valido = false; }
  if (!valido) return;

  try {
    const respuesta = await fetch(`${BASE_API}/auth/profile`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${obtenerToken()}`,
      },
      body: JSON.stringify({ name: nombre, email: correo }),
    });
    const datos = await respuesta.json();
    if (!respuesta.ok) throw new Error(datos.message || 'Error al guardar');
    const usuario = { ...obtenerUsuario(), name: nombre, email: correo };
    guardarUsuarioLocal(usuario);
    actualizarBarraLateral(usuario);
    mostrarAviso('Información actualizada ✅');
  } catch (error) {
    // Modo demo: guardar localmente
    const usuario = { ...obtenerUsuario(), name: nombre, email: correo };
    guardarUsuarioLocal(usuario);
    actualizarBarraLateral(usuario);
    mostrarAviso('Información actualizada (modo demo)');
  }
}

function reiniciarInfo() {
  const usuario = obtenerUsuario();
  document.getElementById('edit-name').value = usuario?.name || '';
  document.getElementById('edit-email').value = usuario?.email || '';
  limpiarErrores('edit-name-error', 'edit-email-error');
  ocultarAlertaPanel('info');
}

// ===== CAMBIAR CONTRASEÑA =====
async function cambiarContrasena() {
  limpiarErrores('pwd-current-error', 'pwd-new-error', 'pwd-confirm-error');
  ocultarAlertaPanel('security');

  const actual = document.getElementById('pwd-current').value;
  const nuevaContrasena = document.getElementById('pwd-new').value;
  const confirmacion = document.getElementById('pwd-confirm').value;

  let valido = true;
  if (!actual) { establecerErrorCampo('pwd-current-error', 'Introduce tu contraseña actual'); valido = false; }
  if (!nuevaContrasena || nuevaContrasena.length < 6) { establecerErrorCampo('pwd-new-error', 'Mínimo 6 caracteres'); valido = false; }
  if (nuevaContrasena !== confirmacion) { establecerErrorCampo('pwd-confirm-error', 'Las contraseñas no coinciden'); valido = false; }
  if (!valido) return;

  try {
    const respuesta = await fetch(`${BASE_API}/auth/change-password`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${obtenerToken()}`,
      },
      body: JSON.stringify({ current_password: actual, new_password: nuevaContrasena }),
    });
    const datos = await respuesta.json();
    if (!respuesta.ok) throw new Error(datos.message || 'Error');
    document.getElementById('pwd-current').value = '';
    document.getElementById('pwd-new').value = '';
    document.getElementById('pwd-confirm').value = '';
    mostrarAviso('Contraseña actualizada ✅');
  } catch (error) {
    if (error.message === 'Failed to fetch') {
      // Demo: simular éxito
      document.getElementById('pwd-current').value = '';
      document.getElementById('pwd-new').value = '';
      document.getElementById('pwd-confirm').value = '';
      mostrarAviso('Contraseña actualizada (modo demo)');
    } else {
      mostrarAlertaPanel('security', error.message, 'error');
    }
  }
}

// ===== MI LISTA =====
let _watchlistMovies = [];

async function cargarMiLista() {
  const contenedor = document.getElementById('watchlist-content');
  contenedor.innerHTML = '<p style="color:var(--text-muted);font-size:.875rem;">Cargando...</p>';
  try {
    const res = await fetch(`${BASE_API}/movies/watchlist`, {
      headers: { 'Authorization': `Bearer ${obtenerToken()}` },
    });
    const data = await res.json();
    _watchlistMovies = data.movies || [];
    document.getElementById('stat-watchlist').textContent = _watchlistMovies.length;
    renderizarLista('');
  } catch {
    contenedor.innerHTML = '<p style="color:var(--text-muted);font-size:.875rem;">Error al cargar la lista.</p>';
  }
}

function renderizarLista(generoFiltro) {
  const contenedor = document.getElementById('watchlist-content');
  const filtradas = generoFiltro
    ? _watchlistMovies.filter(p => p.genres?.includes(generoFiltro))
    : _watchlistMovies;

  const generosUnicos = [...new Set(_watchlistMovies.flatMap(p => p.genres || []))].sort();

  const barra = document.createElement('div');
  barra.className = 'profile-filter-bar';
  barra.innerHTML = ['', ...generosUnicos].map(g =>
    `<button class="profile-filter-btn${g === generoFiltro ? ' active' : ''}"
      onclick="renderizarLista('${g}')">${g || 'Todos'}</button>`
  ).join('');

  if (!filtradas.length) {
    contenedor.innerHTML = '';
    contenedor.appendChild(barra);
    contenedor.insertAdjacentHTML('beforeend', `
      <div class="profile-empty">
        <div class="empty-icon">📋</div>
        <div>${_watchlistMovies.length ? 'Ninguna película coincide con el filtro.' : 'Tu lista está vacía. Añade películas desde el catálogo.'}</div>
      </div>`);
    return;
  }

  const grid = document.createElement('div');
  grid.className = 'profile-movies-grid';
  filtradas.forEach(p => {
    const card = document.createElement('div');
    card.className = 'profile-movie-card';
    card.innerHTML = `
      ${posterCardHtml(p)}
      <div class="profile-movie-info">
        <div class="profile-movie-title">${p.title}</div>
        <div class="profile-movie-meta">${p.year || '—'} · ⭐ ${p.rating}</div>
        <button class="btn-remove-list" onclick="quitarDeLista(${p.id}, this)">Quitar de la lista</button>
      </div>`;
    grid.appendChild(card);
  });

  contenedor.innerHTML = '';
  contenedor.appendChild(barra);
  contenedor.appendChild(grid);
}

async function quitarDeLista(movieId, boton) {
  boton.disabled = true;
  boton.textContent = 'Quitando...';
  try {
    await fetch(`${BASE_API}/movies/${movieId}/watchlist`, {
      method: 'DELETE',
      headers: { 'Authorization': `Bearer ${obtenerToken()}` },
    });
    _watchlistMovies = _watchlistMovies.filter(p => p.id !== movieId);
    document.getElementById('stat-watchlist').textContent = _watchlistMovies.length;
    renderizarLista('');
    mostrarAviso('Película eliminada de tu lista');
  } catch {
    boton.disabled = false;
    boton.textContent = 'Quitar de la lista';
    mostrarAviso('Error al quitar la película', 'error');
  }
}

// ===== MIS VALORACIONES =====
let _ratingsMovies = [];

async function cargarMisValoraciones() {
  const contenedor = document.getElementById('ratings-content');
  contenedor.innerHTML = '<p style="color:var(--text-muted);font-size:.875rem;">Cargando...</p>';
  try {
    const res = await fetch(`${BASE_API}/movies/my-ratings`, {
      headers: { 'Authorization': `Bearer ${obtenerToken()}` },
    });
    const data = await res.json();
    _ratingsMovies = data.ratings || [];
    document.getElementById('stat-rated').textContent = _ratingsMovies.length;
    renderizarValoraciones('');
  } catch {
    contenedor.innerHTML = '<p style="color:var(--text-muted);font-size:.875rem;">Error al cargar las valoraciones.</p>';
  }
}

function renderizarValoraciones(generoFiltro) {
  const contenedor = document.getElementById('ratings-content');
  const filtradas = generoFiltro
    ? _ratingsMovies.filter(p => p.genres?.includes(generoFiltro))
    : _ratingsMovies;

  const generosUnicos = [...new Set(_ratingsMovies.flatMap(p => p.genres || []))].sort();

  const barra = document.createElement('div');
  barra.className = 'profile-filter-bar';
  barra.innerHTML = ['', ...generosUnicos].map(g =>
    `<button class="profile-filter-btn${g === generoFiltro ? ' active' : ''}"
      onclick="renderizarValoraciones('${g}')">${g || 'Todos'}</button>`
  ).join('');

  if (!filtradas.length) {
    contenedor.innerHTML = '';
    contenedor.appendChild(barra);
    contenedor.insertAdjacentHTML('beforeend', `
      <div class="profile-empty">
        <div class="empty-icon">⭐</div>
        <div>${_ratingsMovies.length ? 'Ninguna película coincide con el filtro.' : 'Todavía no has valorado ninguna película.'}</div>
      </div>`);
    return;
  }

  const grid = document.createElement('div');
  grid.className = 'profile-movies-grid';
  filtradas.forEach(p => {
    const card = document.createElement('div');
    card.className = 'profile-movie-card';
    const starsId = `stars-r-${p.id}`;
    card.innerHTML = `
      ${posterCardHtml(p)}
      <div class="profile-movie-info">
        <div class="profile-movie-title">${p.title}</div>
        <div class="profile-movie-meta">${p.year || '—'} · ⭐ ${p.rating}</div>
        <div class="profile-movie-user-rating" id="${starsId}">
          ${estrellasBotones(p.id, p.user_rating)}
        </div>
      </div>`;
    grid.appendChild(card);
  });

  contenedor.innerHTML = '';
  contenedor.appendChild(barra);
  contenedor.appendChild(grid);
}

function estrellasBotones(movieId, valorActual) {
  return Array.from({ length: 5 }, (_, i) => {
    const v = i + 1;
    return `<button class="star-edit${v <= valorActual ? ' on' : ''}"
      data-movie="${movieId}" data-v="${v}"
      onclick="cambiarValoracion(${movieId}, ${v})">★</button>`;
  }).join('') + `<span class="rating-label-inline" id="rl-${movieId}" style="font-size:.72rem;color:var(--text-muted);margin-left:.3rem;">${valorActual}/5</span>`;
}

async function cambiarValoracion(movieId, nuevaPuntuacion) {
  const contenedor = document.getElementById(`stars-r-${movieId}`);
  if (!contenedor) return;

  contenedor.querySelectorAll('.star-edit').forEach(b => {
    b.classList.toggle('on', Number(b.dataset.v) <= nuevaPuntuacion);
  });
  const label = document.getElementById(`rl-${movieId}`);
  if (label) label.textContent = `${nuevaPuntuacion}/5`;

  const movie = _ratingsMovies.find(p => p.id === movieId);
  if (movie) movie.user_rating = nuevaPuntuacion;

  try {
    await fetch(`${BASE_API}/movies/${movieId}/rate`, {
      method: 'POST',
      headers: { ...{ 'Authorization': `Bearer ${obtenerToken()}` }, 'Content-Type': 'application/json' },
      body: JSON.stringify({ score: nuevaPuntuacion }),
    });
    mostrarAviso(`Valoración actualizada: ${nuevaPuntuacion} ${'★'.repeat(nuevaPuntuacion)}`);
  } catch {
    mostrarAviso('Error al guardar la valoración', 'error');
  }
}

// ===== ZONA PELIGROSA =====
function cerrarTodasLasSesiones() {
  if (!confirm('¿Cerrar sesión en todos los dispositivos?')) return;
  fetch(`${BASE_API}/auth/logout-all`, {
    method: 'POST',
    headers: { 'Authorization': `Bearer ${obtenerToken()}` },
  }).catch(() => {});
  cerrarSesion();
}

function confirmarEliminarCuenta() {
  document.getElementById('delete-modal').classList.add('open');
  document.body.style.overflow = 'hidden';
}

function cerrarModalEliminar() {
  document.getElementById('delete-modal').classList.remove('open');
  document.body.style.overflow = '';
  document.getElementById('delete-confirm-input').value = '';
}

async function eliminarCuenta() {
  const entrada = document.getElementById('delete-confirm-input').value.trim();
  if (entrada !== 'ELIMINAR') {
    mostrarAviso('Escribe ELIMINAR para confirmar', 'error');
    return;
  }
  try {
    await fetch(`${BASE_API}/auth/account`, {
      method: 'DELETE',
      headers: { 'Authorization': `Bearer ${obtenerToken()}` },
    });
  } catch { /* demo */ }
  localStorage.clear();
  window.location.href = 'index.html';
}
