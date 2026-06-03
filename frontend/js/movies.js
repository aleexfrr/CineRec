const API = 'http://localhost:8000/api';
let idPeliculaActual = null;
let heroMovie        = null;

// Caché local: movieId → puntuación del usuario (se carga al inicio)
const misValoraciones = new Map();

async function cargarMisValoraciones() {
  try {
    const res  = await fetch(`${API}/movies/my-ratings`, { headers: cabeceras() });
    const data = await res.json();
    (data.ratings || []).forEach(r => misValoraciones.set(r.id, r.user_rating));
  } catch {}
}

// colores de fondo por género (actúan de póster)
const GENRE_COLORS = {
  'Action':      ['#7f0000','#b71c1c'], 'Adventure':   ['#bf360c','#e64a19'],
  'Animation':   ['#1b5e20','#388e3c'], 'Children':    ['#f57f17','#fbc02d'],
  'Comedy':      ['#e65100','#ff8f00'], 'Crime':       ['#212121','#424242'],
  'Documentary': ['#1a237e','#283593'], 'Drama':       ['#0d47a1','#1565c0'],
  'Fantasy':     ['#4a148c','#7b1fa2'], 'Film-Noir':   ['#111','#333'],
  'Horror':      ['#3d0000','#6d0a0a'], 'Musical':     ['#880e4f','#c2185b'],
  'Mystery':     ['#263238','#455a64'], 'Romance':     ['#880e4f','#ad1457'],
  'Sci-Fi':      ['#006064','#00838f'], 'Thriller':    ['#1a237e','#311b92'],
  'War':         ['#3e2723','#5d4037'], 'Western':     ['#4e342e','#6d4c41'],
};

function colorPelicula(genres) {
  const c = GENRE_COLORS[genres?.[0]] || ['#1a1a2e','#2a2a4a'];
  return `linear-gradient(160deg, ${c[0]}, ${c[1]})`;
}

function posterStyle(p) {
  if (p.poster_url) return `background:${colorPelicula(p.genres)}`;
  return `background:${colorPelicula(p.genres)}`;
}

function posterInner(p, extraClass = '') {
  if (p.poster_url) {
    return `<img src="${p.poster_url}" alt="${p.title}"
      class="nf-poster-img${extraClass ? ' ' + extraClass : ''}"
      onerror="this.style.display='none'"
      loading="lazy">`;
  }
  return '';
}

function token() { return localStorage.getItem('cinrec_token'); }
function cabeceras() { return { 'Authorization': `Bearer ${token()}` }; }

function cerrarSesion() {
  localStorage.clear();
  window.location.href = 'index.html?logout=1';
}


function mostrarAviso(msg, tipo = 'success') {
  const c = document.getElementById('toast-container');
  const t = document.createElement('div');
  t.className = `toast ${tipo}`;
  t.innerHTML = `<span class="toast-icon">${tipo === 'success' ? '✅' : '❌'}</span> ${msg}`;
  c.appendChild(t);
  setTimeout(() => t.remove(), 3000);
}

// ── INICIO ────────────────────────────────────────────────────────────────────
(function init() {
  if (!token()) { window.location.href = 'index.html'; return; }

  const u = JSON.parse(localStorage.getItem('cinrec_user') || '{}');
  document.getElementById('user-name').textContent   = u.name || u.email || '';
  document.getElementById('user-avatar').textContent = (u.name || u.email || 'U')[0].toUpperCase();

  cargarMisValoraciones();
  cargarTodo();
})();

// Sombra en la navbar al hacer scroll
window.addEventListener('scroll', () => {
  document.getElementById('nf-nav').classList.toggle('scrolled', window.scrollY > 50);
});

// ── CARGA PRINCIPAL ───────────────────────────────────────────────────────────
async function cargarTodo() {
  // primero trending para el hero (no espera a las demás)
  cargarFila('scroll-trending', `${API}/movies/trending`, 'count-trending').then(movies => {
    if (movies.length) configurarHero(movies[0]);
  });

  cargarRecomendaciones();
  cargarFila('scroll-action',      `${API}/movies/genre/Action?limit=20`,  'count-action');
  cargarFila('scroll-drama',       `${API}/movies/genre/Drama?limit=20`,   'count-drama');
  cargarFila('scroll-comedy',      `${API}/movies/genre/Comedy?limit=20`,  'count-comedy');
  cargarFila('scroll-scifi',       `${API}/movies/genre/Sci-Fi?limit=20`,  'count-scifi');
  cargarFila('scroll-horror',      `${API}/movies/genre/Horror?limit=20`,  'count-horror');
  cargarFila('scroll-romance',     `${API}/movies/genre/Romance?limit=20`, 'count-romance');
  cargarFila('scroll-animation',   `${API}/movies/genre/Animation?limit=20`,'count-animation');
  cargarFila('scroll-documentary', `${API}/movies/genre/Documentary?limit=20`,'count-documentary');
}

async function cargarRecomendaciones() {
  const contenedor = document.getElementById('scroll-recs');
  const label      = document.getElementById('recs-label');
  contenedor.innerHTML = esqueleto(10);

  try {
    const res  = await fetch(`${API}/movies/recommendations`, { headers: cabeceras() });
    const data = await res.json();
    const movies = data.movies || [];

    contenedor.innerHTML = '';
    movies.forEach((p, i) => contenedor.appendChild(crearTarjeta(p, i)));

    if (document.getElementById('count-recs'))
      document.getElementById('count-recs').textContent = `${movies.length} películas`;

    // Mostrar origen de las recomendaciones
    if (label) {
      const textos = {
        collaborative:     'Recomendado por IA (filtrado colaborativo)',
        content_based_ml:  'Recomendado por IA (basado en contenido)',
        content_based:     'Basado en tus valoraciones',
        onboarding:        'Basado en tus preferencias',
        trending:          'Las más populares',
      };
      label.textContent = textos[data.source] || '';
      label.style.display = data.source ? 'inline' : 'none';
    }
  } catch {
    contenedor.innerHTML = '<p style="color:var(--text-muted);padding:1rem 0">No disponible</p>';
  }
}

async function cargarFila(scrollId, url, countId) {
  const contenedor = document.getElementById(scrollId);
  contenedor.innerHTML = esqueleto(10);
  try {
    const res    = await fetch(url, { headers: cabeceras() });
    const data   = await res.json();
    const movies = data.movies || [];
    contenedor.innerHTML = '';
    movies.forEach((p, i) => contenedor.appendChild(crearTarjeta(p, i)));
    if (countId) {
      const el = document.getElementById(countId);
      if (el) el.textContent = `${movies.length} películas`;
    }
    return movies;
  } catch {
    contenedor.innerHTML = '<p style="color:var(--text-muted);padding:1rem 0">No disponible</p>';
    return [];
  }
}

// ── HERO ──────────────────────────────────────────────────────────────────────
function configurarHero(movie) {
  heroMovie = movie;
  document.getElementById('hero-title').textContent   = movie.title;
  document.getElementById('hero-rating').textContent  = `⭐ ${movie.rating}`;
  document.getElementById('hero-year').textContent    = movie.year || '';
  document.getElementById('hero-genres').textContent  = movie.genre || '';
  document.getElementById('hero-votes').textContent   = movie.rating_count ? `🗳️ ${movie.rating_count.toLocaleString()} votos` : '';
  const heroBg = document.getElementById('hero-bg');
  heroBg.style.background = colorPelicula(movie.genres);
  if (movie.poster_url) {
    heroBg.style.backgroundImage = `url('${movie.poster_url}')`;
    heroBg.style.backgroundSize  = 'cover';
    heroBg.style.backgroundPosition = 'center top';
  }
}

function abrirModalHero() { if (heroMovie) abrirModal(heroMovie); }

// ── TARJETA ───────────────────────────────────────────────────────────────────
function crearTarjeta(p, indice = -1) {
  const div = document.createElement('div');
  div.className = 'nf-card';
  div.onclick   = () => abrirModal(p);

  const rankHtml = (indice >= 0 && indice < 10)
    ? `<div class="nf-card-rank">${indice + 1}</div>` : '';

  div.innerHTML = `
    <div class="nf-card-poster" style="background:${colorPelicula(p.genres)}">
      ${posterInner(p)}
      <div class="nf-card-rating-badge">⭐ ${p.rating}</div>
      ${rankHtml}
      ${!p.poster_url ? `<div class="nf-card-poster-title">${p.title}</div>` : ''}
      <div class="nf-card-overlay">
        <div class="nf-overlay-rating">⭐ ${p.rating}</div>
        <div class="nf-overlay-votes">${formatearNumero(p.rating_count)} votos</div>
        <button class="nf-overlay-btn" onclick="event.stopPropagation();abrirModal(p)">Ver detalles</button>
      </div>
    </div>
    <div class="nf-card-info">
      <div class="nf-card-titulo">${p.title}</div>
      <div class="nf-card-meta">
        <span class="nf-card-year">${p.year || '—'}</span>
        <span class="nf-card-stars">⭐ ${p.rating}</span>
      </div>
    </div>`;
  return div;
}

function esqueleto(n) {
  return Array(n).fill('<div class="nf-card-skeleton"></div>').join('');
}


function formatearNumero(n) {
  if (!n) return '0';
  if (n >= 1000) return (n / 1000).toFixed(0) + 'k';
  return n;
}

// ── BÚSQUEDA ──────────────────────────────────────────────────────────────────
let searchDebounce = null;
let generoActivo   = '';

function toggleBusqueda() {
  const overlay = document.getElementById('search-overlay');
  const estaAbierto = overlay.classList.contains('open');
  if (estaAbierto) {
    cerrarBusqueda();
  } else {
    overlay.classList.add('open');
    document.body.style.overflow = 'hidden';
    document.getElementById('search-input').focus();
  }
}

function cerrarBusqueda() {
  document.getElementById('search-overlay').classList.remove('open');
  document.body.style.overflow = '';
}

function cerrarBusquedaOverlay(e) {
  if (e.target === document.getElementById('search-overlay')) cerrarBusqueda();
}

function limpiarBusqueda() {
  const input = document.getElementById('search-input');
  input.value = '';
  input.focus();
  document.getElementById('search-clear').style.display = 'none';
  document.getElementById('search-results').innerHTML = '';
  document.getElementById('search-results-header').style.display = 'none';
  // si hay género activo, lanza búsqueda solo por género
  if (generoActivo) disparaBusqueda();
}

// chips de género
document.getElementById('genre-chips').addEventListener('click', e => {
  const chip = e.target.closest('.search-chip');
  if (!chip) return;
  document.querySelectorAll('.search-chip').forEach(c => c.classList.remove('active'));
  chip.classList.add('active');
  generoActivo = chip.dataset.genre;
  disparaBusqueda();
});

// cambio en selects de rating/año
['filter-rating', 'filter-year'].forEach(id => {
  document.getElementById(id).addEventListener('change', disparaBusqueda);
});

// input con debounce
document.getElementById('search-input').addEventListener('input', e => {
  const val = e.target.value;
  document.getElementById('search-clear').style.display = val ? 'inline' : 'none';
  clearTimeout(searchDebounce);
  searchDebounce = setTimeout(disparaBusqueda, 380);
});

function disparaBusqueda() {
  const q      = document.getElementById('search-input').value.trim();
  const genre  = generoActivo;
  const year   = document.getElementById('filter-year').value;
  const rating = document.getElementById('filter-rating').value;
  if (!q && !genre && !year && !rating) return;
  buscarPeliculas(q, genre, year, rating);
}

async function buscarPeliculas(q, genre, year, rating) {
  const res    = document.getElementById('search-results');
  const header = document.getElementById('search-results-header');

  // skeleton mientras carga
  res.innerHTML = Array(10).fill('<div class="search-skeleton"></div>').join('');
  header.style.display = 'none';

  const params = new URLSearchParams({ limit: 40 });
  if (q)      params.append('q', q);
  if (genre)  params.append('genre', genre);
  if (year)   params.append('year', year);
  if (rating) params.append('min_rating', rating);

  try {
    const data   = await fetch(`${API}/movies/search?${params}`, { headers: cabeceras() }).then(r => r.json());
    const movies = data.movies || [];

    header.style.display = 'block';
    document.getElementById('search-count').textContent =
      movies.length ? `${movies.length} película${movies.length !== 1 ? 's' : ''} encontrada${movies.length !== 1 ? 's' : ''}` : '';

    res.innerHTML = '';
    if (!movies.length) {
      res.innerHTML = `
        <div class="search-empty">
          <div class="search-empty-icon">🎬</div>
          <p>No encontramos nada con esos filtros.<br>Prueba con otro título o cambia el género.</p>
        </div>`;
      return;
    }
    movies.forEach(p => res.appendChild(crearTarjetaBusqueda(p)));
  } catch {
    res.innerHTML = '<div class="search-empty"><p>Error al buscar. Comprueba que el backend está activo.</p></div>';
  }
}

function crearTarjetaBusqueda(p) {
  const div = document.createElement('div');
  div.className = 'search-result-card';
  div.onclick   = () => { cerrarBusqueda(); abrirModal(p); };
  div.innerHTML = `
    <div class="search-result-poster" style="background:${colorPelicula(p.genres)}">
      ${p.poster_url ? `<img src="${p.poster_url}" alt="${p.title}" onerror="this.remove()" loading="lazy">` : ''}
      ${!p.poster_url ? `<div class="search-result-poster-title">${p.title}</div>` : ''}
      <div class="search-result-badge">⭐ ${p.rating}</div>
    </div>
    <div class="search-result-info">
      <div class="search-result-title" title="${p.title}">${p.title}</div>
      <div class="search-result-meta">${p.year || '—'} · ${p.genre || ''}</div>
    </div>`;
  return div;
}

// Atajo de teclado: / o Ctrl+K abre el buscador; ESC lo cierra
document.addEventListener('keydown', e => {
  if (e.key === 'Escape') {
    const overlay = document.getElementById('search-overlay');
    if (overlay.classList.contains('open')) { cerrarBusqueda(); return; }
  }
  if ((e.key === '/' || (e.ctrlKey && e.key === 'k')) && !['INPUT','TEXTAREA','SELECT'].includes(document.activeElement.tagName)) {
    e.preventDefault();
    toggleBusqueda();
  }
});

// ── MODAL ─────────────────────────────────────────────────────────────────────
function abrirModal(p) {
  idPeliculaActual = p.id;
  document.getElementById('modal-title').textContent  = p.title;
  document.getElementById('modal-year').textContent   = p.year || '';
  document.getElementById('modal-rating').textContent = `⭐ ${p.rating}`;
  document.getElementById('modal-genre').textContent  = p.genre || '';
  document.getElementById('modal-description').textContent = p.description || 'Descripción no disponible en el dataset.';
  const wrap = document.getElementById('modal-poster-wrap');
  wrap.style.background = colorPelicula(p.genres);
  wrap.innerHTML = p.poster_url
    ? `<img src="${p.poster_url}" alt="${p.title}" class="modal-poster-img" onerror="this.remove()">`
    : '';
  document.getElementById('modal-stats').innerHTML = p.rating_count
    ? `<span class="modal-stat">🗳️ ${p.rating_count.toLocaleString()} valoraciones</span>`
    : '';

  // Mostrar valoración existente del usuario (o limpiar si no ha valorado)
  const valoracionPrevia = misValoraciones.get(p.id) ?? p.user_rating ?? null;
  const LABELS = ['', 'Muy mala', 'Mala', 'Regular', 'Buena', 'Excelente'];
  const estrellas = valoracionPrevia ? Math.round(valoracionPrevia) : 0;
  document.querySelectorAll('#stars .star').forEach(s => {
    s.classList.toggle('active', Number(s.dataset.v) <= estrellas);
  });
  const sv = document.getElementById('star-value');
  if (sv) sv.textContent = estrellas ? `${estrellas}/5 — ${LABELS[estrellas]}` : '';

  document.getElementById('movie-modal').classList.add('open');
  document.body.style.overflow = 'hidden';
}

function cerrarModal() {
  document.getElementById('movie-modal').classList.remove('open');
  document.body.style.overflow = '';
  idPeliculaActual = null;
}

function cerrarModalEnOverlay(e) {
  if (e.target === document.getElementById('movie-modal')) cerrarModal();
}

document.addEventListener('keydown', e => { if (e.key === 'Escape') cerrarModal(); });

// ── ACCIONES ──────────────────────────────────────────────────────────────────
async function valorarPelicula(id, puntuacion) {
  // actualizar UI de estrellas
  document.querySelectorAll('#stars .star').forEach(s => {
    s.classList.toggle('active', Number(s.dataset.v) <= puntuacion);
  });
  const labels = ['', 'Muy mala', 'Mala', 'Regular', 'Buena', 'Excelente'];
  const el = document.getElementById('star-value');
  if (el) el.textContent = `${puntuacion}/5 — ${labels[puntuacion]}`;

  const esNueva = !misValoraciones.has(id);
  try {
    await fetch(`${API}/movies/${id}/rate`, {
      method: 'POST',
      headers: { ...cabeceras(), 'Content-Type': 'application/json' },
      body: JSON.stringify({ score: puntuacion }),
    });
    misValoraciones.set(id, puntuacion);
    cargarRecomendaciones();
  } catch {}
  const msg = esNueva
    ? `Valorada con ${puntuacion} ${'★'.repeat(puntuacion)}`
    : `Valoración actualizada a ${puntuacion} ${'★'.repeat(puntuacion)}`;
  mostrarAviso(msg);
}

async function anadirAListaDeseos(id) {
  try {
    await fetch(`${API}/movies/${id}/watchlist`, { method: 'POST', headers: cabeceras() });
  } catch {}
  mostrarAviso('Añadido a tu lista 📋');
}
