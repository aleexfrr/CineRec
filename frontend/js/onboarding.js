// ===== CONFIGURACIÓN =====
const BASE_API = 'http://localhost:8000/api';
const TOTAL_PUNTOS = 5;

// 6 grupos de 2 tipos de películas cada uno
const GRUPOS = [
  { id: 'action_adventure',    emoji: '💥', types: ['Acción',          'Aventura']      },
  { id: 'drama_romance',       emoji: '🎭', types: ['Drama',           'Romance']       },
  { id: 'horror_thriller',     emoji: '😱', types: ['Terror',          'Thriller']      },
  { id: 'comedy_animation',    emoji: '😂', types: ['Comedia',         'Animación']     },
  { id: 'scifi_fantasy',       emoji: '🚀', types: ['Ciencia Ficción', 'Fantasía']      },
  { id: 'documentary_history', emoji: '📰', types: ['Documental',      'Historia']      },
];

// ===== ESTADO =====
const puntos = Object.fromEntries(GRUPOS.map(g => [g.id, 0]));

// ===== UTILIDADES =====
function obtenerToken()   { return localStorage.getItem('cinrec_token'); }
function obtenerUsuario() { try { return JSON.parse(localStorage.getItem('cinrec_user')); } catch { return null; } }

function mostrarAviso(mensaje, tipo = 'success') {
  const contenedor = document.getElementById('toast-container');
  const aviso = document.createElement('div');
  aviso.className = `toast ${tipo}`;
  aviso.innerHTML = `<span class="toast-icon">${tipo === 'success' ? '✅' : '❌'}</span> ${mensaje}`;
  contenedor.appendChild(aviso);
  setTimeout(() => aviso.remove(), 3000);
}

function totalAsignados() {
  return Object.values(puntos).reduce((a, b) => a + b, 0);
}

function restantes() {
  return TOTAL_PUNTOS - totalAsignados();
}

// ===== RENDER INICIAL =====
(function inicializar() {
  if (!obtenerToken()) { window.location.href = 'index.html'; return; }
  construirPuntos();
  construirGrupos();
})();

function construirPuntos() {
  const contenedor = document.getElementById('points-dots');
  contenedor.innerHTML = '';
  for (let i = 0; i < TOTAL_PUNTOS; i++) {
    const punto = document.createElement('div');
    punto.className = 'points-dot';
    punto.id = `dot-${i}`;
    contenedor.appendChild(punto);
  }
}

function construirGrupos() {
  const cuadricula = document.getElementById('groups-grid');
  cuadricula.innerHTML = '';

  GRUPOS.forEach(grupo => {
    const tarjeta = document.createElement('div');
    tarjeta.className = 'group-card';
    tarjeta.id = `card-${grupo.id}`;
    tarjeta.innerHTML = `
      <div class="group-emoji">${grupo.emoji}</div>
      <div class="group-types">
        <span class="group-type-name">${grupo.types[0]}</span>
        <div class="group-type-sep">+</div>
        <span class="group-type-name">${grupo.types[1]}</span>
      </div>
      <div class="point-controls">
        <button class="point-btn" id="btn-minus-${grupo.id}" onclick="cambiarPunto('${grupo.id}', -1)" disabled>−</button>
        <span class="point-value" id="val-${grupo.id}">0</span>
        <button class="point-btn" id="btn-plus-${grupo.id}" onclick="cambiarPunto('${grupo.id}', +1)">+</button>
      </div>
      <div class="point-pips" id="pips-${grupo.id}"></div>`;
    cuadricula.appendChild(tarjeta);
  });
}

// ===== LÓGICA DE PUNTOS =====
function cambiarPunto(idGrupo, delta) {
  const nuevoValor = puntos[idGrupo] + delta;
  if (nuevoValor < 0) return;
  if (delta > 0 && restantes() <= 0) return;

  puntos[idGrupo] = nuevoValor;
  actualizarUI();
}

function actualizarUI() {
  const restante = restantes();
  const asignados = totalAsignados();

  // Contador principal
  document.getElementById('points-left').textContent = restante;

  // Dots indicadores
  for (let i = 0; i < TOTAL_PUNTOS; i++) {
    document.getElementById(`dot-${i}`).classList.toggle('filled', i < asignados);
  }

  // Actualizar cada tarjeta
  GRUPOS.forEach(grupo => {
    const valor = puntos[grupo.id];
    document.getElementById(`val-${grupo.id}`).textContent = valor;

    // Indicadores visuales
    const indicadores = document.getElementById(`pips-${grupo.id}`);
    indicadores.innerHTML = '';
    for (let i = 0; i < valor; i++) {
      const indicador = document.createElement('div');
      indicador.className = 'pip';
      indicadores.appendChild(indicador);
    }

    // Resaltar tarjeta si tiene puntos
    document.getElementById(`card-${grupo.id}`).classList.toggle('has-points', valor > 0);

    // Botón −
    document.getElementById(`btn-minus-${grupo.id}`).disabled = valor === 0;
    // Botón +
    document.getElementById(`btn-plus-${grupo.id}`).disabled = restante === 0;
  });

  // Botón continuar y pista
  const boton = document.getElementById('btn-continue');
  const pista = document.getElementById('footer-hint');

  if (restante === 0) {
    boton.disabled = false;
    pista.textContent = '¡Todos los puntos asignados! Pulsa continuar.';
    pista.style.color = 'var(--success)';
  } else {
    boton.disabled = true;
    pista.textContent = `Te ${restante === 1 ? 'queda' : 'quedan'} ${restante} punto${restante !== 1 ? 's' : ''} por asignar`;
    pista.style.color = 'var(--text-muted)';
  }
}

// ===== GUARDAR Y CONTINUAR =====
async function finalizarOnboarding() {
  const usuario = obtenerUsuario();
  if (!usuario) { window.location.href = 'index.html'; return; }

  const datosPerfil = construirPerfilJSON(usuario);

  // 1. Guardar en localStorage
  localStorage.setItem('cinrec_profile', JSON.stringify(datosPerfil));

  // 2. Actualizar objeto usuario con preferencias
  const usuarioActualizado = { ...usuario, preferred_groups: puntos, onboarding_done: true };
  localStorage.setItem('cinrec_user', JSON.stringify(usuarioActualizado));

  // 3. Intentar enviar al backend
  try {
    await fetch(`${BASE_API}/auth/preferences`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${obtenerToken()}`,
      },
      body: JSON.stringify(datosPerfil),
    });
  } catch {
    // sin backend: solo guardado local
  }

  mostrarAviso('¡Preferencias guardadas! Redirigiendo...');
  setTimeout(() => { window.location.href = 'movies.html'; }, 1200);
}

function construirPerfilJSON(usuario) {
  return {
    usuario: {
      id:       usuario.id       || null,
      nombre:   usuario.name     || null,
      correo:   usuario.email    || null,
      registro: usuario.created_at || new Date().toISOString(),
    },
    preferencias: {
      puntos_totales: TOTAL_PUNTOS,
      grupos: GRUPOS.map(g => ({
        id:     g.id,
        tipos:  g.types,
        puntos: puntos[g.id],
      })),
      fecha_encuesta: new Date().toISOString(),
    },
  };
}

// ===== SALTAR =====
function saltarOnboarding() {
  const usuario = obtenerUsuario();
  if (usuario) {
    const usuarioActualizado = { ...usuario, onboarding_done: false };
    localStorage.setItem('cinrec_user', JSON.stringify(usuarioActualizado));
  }
  window.location.href = 'movies.html';
}
