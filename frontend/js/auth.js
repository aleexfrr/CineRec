// ===== CONFIGURACIÓN =====
const BASE_API = 'http://localhost:8000/api'; // Cambia al puerto de tu backend Python

// ===== UTILIDADES =====
function mostrarAviso(mensaje, tipo = 'success') {
  const contenedor = document.getElementById('toast-container');
  const aviso = document.createElement('div');
  aviso.className = `toast ${tipo}`;
  aviso.innerHTML = `<span class="toast-icon">${tipo === 'success' ? '✅' : '❌'}</span> ${mensaje}`;
  contenedor.appendChild(aviso);
  setTimeout(() => aviso.remove(), 3500);
}

function mostrarAlerta(mensaje, tipo = 'error') {
  const elemento = document.getElementById('auth-alert');
  elemento.className = `alert alert-${tipo}`;
  elemento.textContent = mensaje;
  elemento.style.display = 'flex';
}

function ocultarAlerta() {
  document.getElementById('auth-alert').style.display = 'none';
}

function establecerErrorCampo(idCampo, mensaje) {
  document.getElementById(idCampo).textContent = mensaje;
}

function limpiarErrores(...ids) {
  ids.forEach(id => { document.getElementById(id).textContent = ''; });
}

function establecerCargando(idBoton, cargando, textoDefecto) {
  const boton = document.getElementById(idBoton);
  boton.disabled = cargando;
  boton.textContent = cargando ? 'Cargando...' : textoDefecto;
}

// ===== MOSTRAR/OCULTAR CONTRASEÑA =====
function alternarContrasena(idEntrada, boton) {
  const entrada = document.getElementById(idEntrada);
  const visible = entrada.type === 'text';
  entrada.type = visible ? 'password' : 'text';
  boton.textContent = visible ? '👁️' : '🙈';
}

// ===== PESTAÑAS =====
function cambiarPestana(pestana) {
  ocultarAlerta();
  ['login', 'register'].forEach(t => {
    document.getElementById(`tab-${t}`).classList.toggle('active', t === pestana);
    document.getElementById(`form-${t}`).classList.toggle('active', t === pestana);
  });
}

// ===== VALIDACIONES =====
function validarCorreo(correo) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(correo);
}

// ===== LOGIN =====
document.getElementById('form-login').addEventListener('submit', async (e) => {
  e.preventDefault();
  limpiarErrores('login-email-error', 'login-password-error');
  ocultarAlerta();

  const correo = document.getElementById('login-email').value.trim();
  const contrasena = document.getElementById('login-password').value;

  let valido = true;
  if (!correo || !validarCorreo(correo)) {
    establecerErrorCampo('login-email-error', 'Introduce un correo válido');
    valido = false;
  }
  if (!contrasena) {
    establecerErrorCampo('login-password-error', 'La contraseña es obligatoria');
    valido = false;
  }
  if (!valido) return;

  establecerCargando('btn-login', true, 'Iniciar sesión');

  try {
    const respuesta = await fetch(`${BASE_API}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email: correo, password: contrasena }),
    });

    const datos = await respuesta.json();

    if (respuesta.ok) {
      // Guardar token y datos de usuario
      localStorage.setItem('cinrec_token', datos.token);
      localStorage.setItem('cinrec_user', JSON.stringify({
        id: datos.user_id,
        name: datos.name,
        email: datos.email,
      }));
      mostrarAviso('¡Bienvenido de nuevo!');
      setTimeout(() => { window.location.href = 'movies.html'; }, 600);
    } else {
      mostrarAlerta(datos.detail || datos.message || 'Correo o contraseña incorrectos');
    }
  } catch (error) {
    mostrarAlerta('No se puede conectar con el servidor. ¿Está arrancado?');
  } finally {
    establecerCargando('btn-login', false, 'Iniciar sesión');
  }
});

// ===== REGISTRO =====
document.getElementById('form-register').addEventListener('submit', async (e) => {
  e.preventDefault();
  limpiarErrores('reg-name-error', 'reg-apellidos-error', 'reg-edad-error', 'reg-genero-error', 'reg-email-error', 'reg-password-error', 'reg-password2-error');
  ocultarAlerta();

  const nombre     = document.getElementById('reg-name').value.trim();
  const apellidos  = document.getElementById('reg-apellidos').value.trim();
  const edadVal    = document.getElementById('reg-edad').value.trim();
  const genero     = document.getElementById('reg-genero').value;
  const correo     = document.getElementById('reg-email').value.trim();
  const contrasena  = document.getElementById('reg-password').value;
  const contrasena2 = document.getElementById('reg-password2').value;
  const edad       = edadVal ? parseInt(edadVal, 10) : null;

  let valido = true;
  if (!nombre || nombre.length < 2) {
    establecerErrorCampo('reg-name-error', 'El nombre debe tener al menos 2 caracteres');
    valido = false;
  }
  if (!apellidos || apellidos.length < 2) {
    establecerErrorCampo('reg-apellidos-error', 'Los apellidos deben tener al menos 2 caracteres');
    valido = false;
  }
  if (!edadVal || isNaN(edad) || edad < 13 || edad > 120) {
    establecerErrorCampo('reg-edad-error', 'Introduce una edad válida (13–120)');
    valido = false;
  }
  if (!genero) {
    establecerErrorCampo('reg-genero-error', 'Selecciona un género');
    valido = false;
  }
  if (!correo || !validarCorreo(correo)) {
    establecerErrorCampo('reg-email-error', 'Introduce un correo válido');
    valido = false;
  }
  if (!contrasena || contrasena.length < 6) {
    establecerErrorCampo('reg-password-error', 'La contraseña debe tener al menos 6 caracteres');
    valido = false;
  }
  if (contrasena !== contrasena2) {
    establecerErrorCampo('reg-password2-error', 'Las contraseñas no coinciden');
    valido = false;
  }
  if (!valido) return;

  establecerCargando('btn-register', true, 'Crear cuenta');

  try {
    const respuesta = await fetch(`${BASE_API}/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: nombre, apellidos, edad, genero, email: correo, password: contrasena }),
    });

    const datos = await respuesta.json();

    if (respuesta.ok) {
      // Guardar sesión y redirigir al onboarding
      localStorage.setItem('cinrec_token', datos.token);
      localStorage.setItem('cinrec_user', JSON.stringify({
        id: datos.user_id,
        name: datos.name || nombre,
        email: datos.email || correo,
        created_at: new Date().toISOString(),
      }));
      mostrarAviso('¡Cuenta creada! Vamos a conocerte mejor 🎬');
      setTimeout(() => { window.location.href = 'onboarding.html'; }, 600);
    } else {
      mostrarAlerta(datos.detail || datos.message || 'Error al crear la cuenta. Inténtalo de nuevo.');
    }
  } catch (error) {
    mostrarAlerta('No se puede conectar con el servidor. ¿Está arrancado?');
  } finally {
    establecerCargando('btn-register', false, 'Crear cuenta');
  }
});

// ===== REDIRIGIR SI YA ESTÁ LOGADO =====
(function verificarAuth() {
  // ?logout=1 en la URL fuerza limpiar sesión (útil cuando el token es inválido)
  if (new URLSearchParams(window.location.search).get('logout') === '1') {
    localStorage.clear();
    return;
  }
  if (localStorage.getItem('cinrec_token')) {
    window.location.href = 'movies.html';
  }
})();
