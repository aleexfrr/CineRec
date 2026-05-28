# CineRec — Sistema de Recomendación de Películas

CineRec es una plataforma web completa de recomendación de películas construida sobre el dataset **MovieLens 1M** (1.000.209 valoraciones reales). Combina un backend en Python/FastAPI, tres motores de Machine Learning, streaming de eventos en tiempo real con Apache Kafka, una base de datos MongoDB y un dashboard de analíticas con Node-RED. Todo el sistema se despliega con un único comando gracias a Docker Compose.

---

## Índice

1. [Características](#características)
2. [Arquitectura](#arquitectura)
3. [Stack tecnológico](#stack-tecnológico)
4. [Instalación](#instalación)
   - [Requisitos](#requisitos)
   - [Método 1 — Script automático (recomendado)](#método-1--script-automático-recomendado)
   - [Método 2 — Manual paso a paso](#método-2--manual-paso-a-paso)
5. [Primer uso](#primer-uso)
6. [Acceso a los servicios](#acceso-a-los-servicios)
7. [Estructura del proyecto](#estructura-del-proyecto)
8. [Base de datos](#base-de-datos)
9. [API REST](#api-rest)
10. [Motor de recomendación](#motor-de-recomendación)
11. [Modelos de Machine Learning](#modelos-de-machine-learning)
12. [Pipeline de streaming Kafka](#pipeline-de-streaming-kafka)
13. [Dashboard Node-RED](#dashboard-node-red)
14. [Desarrollo local sin Docker](#desarrollo-local-sin-docker)
15. [Variables de entorno](#variables-de-entorno)
16. [Comandos útiles](#comandos-útiles)
17. [Solución de problemas](#solución-de-problemas)

---

## Características

- **Recomendaciones personalizadas** basadas en el historial de valoraciones del usuario, ponderando géneros preferidos y calidad media del dataset.
- **Tres motores de ML independientes**: filtrado colaborativo (SVD), filtrado por contenido (TF-IDF + coseno) y clasificación (Random Forest).
- **Streaming en tiempo real**: cada valoración se publica en Kafka y se procesa en vivo.
- **Interfaz web estilo Netflix** con tema oscuro, carruseles por género, búsqueda con filtros y modal de detalle de película.
- **Sistema completo de usuarios**: registro, login con JWT, onboarding de preferencias, perfil, historial, watchlist y cambio de contraseña.
- **Dashboard de analíticas** con Node-RED: estadísticas globales, top películas, métricas de modelos y eventos Kafka en vivo.
- **Dataset MovieLens 1M** precargado: 3.883 películas, 6.040 usuarios, 1.000.209 valoraciones.
- **Despliegue con un comando** mediante Docker Compose.

---

## Arquitectura

```
┌────────────────────────────────────────────────────────────────┐
│                        Docker Compose                          │
│                                                                │
│   Navegador                                                    │
│      │                                                         │
│      ▼                                                         │
│  ┌──────────┐   /api/*   ┌──────────┐        ┌──────────────┐  │
│  │ Frontend │──────────▶ │ Backend  │◀─────▶│   MongoDB    │  │
│  │  nginx   │            │ FastAPI  │        │              │  │
│  │  :80     │            │  :8000   │        │  cinerec     │  │
│  └──────────┘            └────┬─────┘        │  (app web)   │  │
│                               │              │              │  │
│  ┌──────────┐                 │ publish      │  movie_      |  │
│  │ Node-RED │◀────────────────┤              │  recommender |  │
│  │ :1881/ui │   MongoDB query │              │  (ML + ETL)  │  │
│  └──────────┘                 ▼              └──────────────┘  │
│                         ┌──────────┐                ▲          │
│                         │  Kafka   │                │          │
│                         │  :9092   │        ┌───────┴──────┐   │
│                         └──────────┘        │   Consumer   │   │
│                               │             │   (Python)   │   │
│                               └────────────▶└──────────────┘   │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

### Flujo de una valoración

```
Usuario valora película en la web
  → Frontend envía POST /api/movies/{id}/rate
  → Backend guarda en cinerec.valoraciones (MongoDB)
  → Backend publica evento en Kafka (topic: movie_ratings)  [async]
  → Consumer recibe el evento
  → Consumer guarda en movie_recommender.ratings_realtime (MongoDB)
  → Dashboard Node-RED muestra el evento en tiempo real
```

### Servicios

| Servicio   | Imagen                        | Puerto | Descripción                              |
|------------|-------------------------------|--------|------------------------------------------|
| frontend   | nginx:alpine (custom)         | 80     | Interfaz web HTML/CSS/JS                 |
| backend    | python:3.11-slim (custom)     | 8000   | API REST con FastAPI                     |
| mongodb    | mongo:7                       | 27017  | Base de datos principal                  |
| kafka      | confluentinc/cp-kafka:7.5.0   | 9092   | Bus de eventos para streaming            |
| zookeeper  | confluentinc/cp-zookeeper:7.5.0 | 2181 | Coordinador de Kafka                     |
| consumer   | python:3.11-slim (custom)     | —      | Consumidor Kafka → MongoDB               |
| nodered    | nodered/node-red (custom)     | 1881   | Dashboard de analíticas en tiempo real   |

---

## Stack tecnológico

| Capa | Tecnología |
|---|---|
| **Backend** | Python 3.11, FastAPI, Uvicorn, Motor (async MongoDB driver) |
| **Base de datos** | MongoDB 7 (NoSQL documental) |
| **Autenticación** | JWT (python-jose, HS256), bcrypt |
| **Streaming** | Apache Kafka 7.5 + Zookeeper, kafka-python |
| **Machine Learning** | scikit-learn, scikit-surprise (SVD) |
| **Frontend** | HTML5, CSS3, JavaScript ES6+ (sin frameworks) |
| **Servidor web** | nginx:alpine |
| **Dashboard** | Node-RED 3 |
| **Orquestación** | Docker Compose v2 |
| **Dataset** | MovieLens 1M (GroupLens, Universidad de Minnesota) |

---

## Instalación

### Requisitos

Lo único necesario es tener **Docker** instalado y corriendo.

#### Linux (Ubuntu / Debian)

```bash
sudo apt update && sudo apt install -y ca-certificates curl gnupg

sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | \
  sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

echo "deb [arch=$(dpkg --print-architecture) \
  signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Usar Docker sin sudo (requiere cerrar sesión y volver a entrar)
sudo usermod -aG docker $USER && newgrp docker
```

#### Windows / macOS

Instala **Docker Desktop** desde https://docs.docker.com/get-docker/ e inícialo.

#### Verificar instalación

```bash
docker --version          # Docker version 24.x o superior
docker compose version    # Docker Compose version v2.x o superior
```

---

### Método 1 — Script automático (recomendado)

El script `setup.sh` hace todo en un solo paso: construye las imágenes, levanta los servicios y restaura todos los datos de MongoDB.

```bash
# 1. Descomprimir el proyecto
unzip CineRec.zip
cd CineRec

# 2. Ejecutar el instalador
bash setup.sh
```

El script:
1. Verifica que Docker esté instalado y corriendo.
2. Crea `.env` desde `.env.example` si no existe.
3. Construye e inicia todos los contenedores (`docker compose up --build -d`).
4. Espera a que MongoDB esté listo (health check).
5. Restaura la base de datos completa desde `mongodump/` usando `mongorestore`.
6. Muestra las URLs de acceso.

> La primera vez tarda 3-5 minutos descargando imágenes base de Docker.

---

### Método 2 — Manual paso a paso

```bash
cd CineRec

# 1. Crear el archivo de variables de entorno
cp .env.example .env

# 2. Construir e iniciar todos los servicios
docker compose up --build -d

# 3. Esperar a que MongoDB esté healthy (~30 segundos)
docker compose ps   # espera a ver "healthy" en mongodb

# 4. Restaurar la base de datos
docker cp mongodump/. movie_mongodb:/tmp/restore
docker exec movie_mongodb mongorestore --dir /tmp/restore --drop --quiet
docker exec movie_mongodb rm -rf /tmp/restore

# 5. Verificar que todo está corriendo
docker compose ps
```

#### Parar el sistema

```bash
docker compose down        # Para los contenedores (los datos de MongoDB se conservan)
docker compose down -v     # Para los contenedores Y borra todos los datos
```

---

## Primer uso

1. Abre **http://localhost** en el navegador.
2. Haz clic en **Registrarse** y crea tu cuenta.
3. Completa el **onboarding**: distribuye 5 puntos entre los grupos de géneros que más te gustan. Esto alimenta las recomendaciones iniciales antes de que tengas historial.
4. Explora el catálogo, busca películas por título, género o año y **valóralas**.
5. Cuantas más películas valores, más personalizadas serán las recomendaciones.

---

## Acceso a los servicios

| URL | Descripción |
|---|---|
| http://localhost | Aplicación web (login, catálogo, perfil) |
| http://localhost:8000/docs | Swagger UI — documentación interactiva de la API |
| http://localhost:8000/redoc | ReDoc — documentación alternativa de la API |
| http://localhost:1881/ui | Dashboard Node-RED (analíticas en tiempo real) |
| http://localhost:1881 | Editor de flujos Node-RED |
| localhost:27017 | MongoDB (conéctate con MongoDB Compass) |

---

## Estructura del proyecto

```
CineRec/
│
├── backend/                        # API REST
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py                     # Punto de entrada FastAPI (CORS, lifespan, routers)
│   └── app/
│       ├── config.py               # Carga de variables de entorno (.env)
│       ├── database.py             # Conexión async a MongoDB con Motor
│       ├── auth_utils.py           # Hash bcrypt + generación/validación JWT
│       ├── kafka_producer.py       # Publica eventos de valoración en Kafka
│       ├── ml_sync.py              # Sincroniza valoraciones al dataset ML
│       ├── setup_db.py             # Crea índices de MongoDB (ejecutar una vez)
│       ├── models/
│       │   ├── usuario.py          # Esquema Pydantic: UsuarioDB y subclases
│       │   ├── pelicula.py         # Esquema Pydantic: PeliculaDB y filtros
│       │   └── valoracion.py       # Esquema Pydantic: Valoracion
│       └── routers/
│           ├── auth.py             # Endpoints: registro, login, perfil, contraseña
│           └── peliculas.py        # Endpoints: búsqueda, recomendaciones, valorar, watchlist
│
├── frontend/                       # Interfaz web
│   ├── Dockerfile
│   ├── nginx.conf                  # Proxy /api/ → backend:8000
│   ├── index.html                  # Login y registro
│   ├── onboarding.html             # Selección de géneros favoritos (5 puntos)
│   ├── movies.html                 # Catálogo principal (estilo Netflix)
│   ├── profile.html                # Perfil, historial de valoraciones y watchlist
│   ├── dashboard.html              # Embed del dashboard Node-RED
│   ├── css/style.css               # Tema oscuro (#0a0a1a + dorado #f5c518)
│   └── js/
│       ├── auth.js                 # Login/registro, JWT en localStorage
│       ├── onboarding.js           # Selector de géneros con 5 puntos distribuibles
│       ├── movies.js               # Carruseles, búsqueda, modal de película, valoraciones
│       ├── profile.js              # Perfil de usuario, historial, watchlist
│       └── dashboard.js            # Configuración y embed de Node-RED
│
├── recommender/                    # Motores de Machine Learning
│   ├── model_store.py              # Guardar/cargar modelos en MongoDB GridFS
│   ├── collaborative/
│   │   └── collaborative_filtering.py   # SVD — filtrado colaborativo
│   ├── content_based/
│   │   └── content_based.py             # TF-IDF + coseno — filtrado por contenido
│   ├── classification/
│   │   └── classification_recommender.py # Random Forest — clasificación binaria
│   ├── popularity/
│   │   └── popularity_recommender.py    # Recomendador por popularidad (fallback)
│   └── evaluation/
│       └── evaluation.py                # Evaluación y métricas de los modelos
│
├── streaming/                      # Pipeline de eventos Kafka
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── producer/
│   │   └── ratings_producer.py     # Envía valoraciones históricas a Kafka (simulación)
│   └── consumer/
│       └── ratings_consumer.py     # Consume eventos y los guarda en MongoDB
│
├── nodered/                        # Dashboard de analíticas
│   ├── Dockerfile
│   ├── flows.json                  # Flujos preconstruidos (consultas MongoDB + widgets)
│   └── settings.js                 # Configuración de Node-RED
│
├── etl/                            # Carga inicial del dataset MovieLens
│   ├── pipeline.py                 # Orquesta: extract → transform → load
│   ├── extract.py                  # Lee los .dat de MovieLens 1M
│   ├── transform.py                # Limpieza, normalización, tipado
│   └── load_mongodb.py             # Inserción masiva en MongoDB + índices
│
├── mongodump/                      # Backup binario de MongoDB (mongorestore)
│   ├── cinerec/                    # DB de la app web (usuarios, películas, valoraciones)
│   └── movie_recommender/          # DB de ML (ratings 1M, movies, users, métricas)
│
├── notebooks/                      # Análisis exploratorio (Jupyter)
│   ├── 01_eda.ipynb                # Análisis del dataset MovieLens
│   ├── 02_modelos.ipynb            # Experimentación con los modelos ML
│   └── 03_recomendaciones.ipynb    # Evaluación de recomendaciones
│
├── docker-compose.yml              # Orquestación de todos los servicios
├── config.py                       # Config compartida para ETL y recommenders
├── requirements.txt                # Dependencias Python (ETL + ML + notebooks)
├── setup.sh                        # Script de instalación automática
├── .env                            # Variables de entorno (no subir a git)
└── .env.example                    # Plantilla de variables de entorno
```

---

## Base de datos

CineRec utiliza **dos bases de datos MongoDB** separadas:

### `cinerec` — Aplicación web

| Colección | Documentos | Descripción |
|---|---|---|
| `usuarios` | ~6 | Cuentas registradas en la web |
| `peliculas` | 3.883 | Catálogo enriquecido (rating_avg, rating_count, poster_url) |
| `valoraciones` | variable | Valoraciones reales hechas desde la web |

**Esquema `usuarios`:**
```json
{
  "_id": ObjectId,
  "nombre": "string",
  "apellidos": "string",
  "email": "string (único)",
  "password_hash": "string (bcrypt)",
  "edad": 25,
  "genero": "string",
  "onboarding_done": true,
  "preferred_groups": { "action_adventure": 2, "drama_romance": 1, "comedy_animation": 2 },
  "watchlist": [1, 42, 318],
  "ml_user_id": 1234,
  "created_at": ISODate
}
```

**Esquema `peliculas`:**
```json
{
  "_id": 1,
  "title": "Toy Story (1995)",
  "genres": ["Animation", "Children", "Comedy"],
  "rating_avg": 3.87,
  "rating_count": 2077,
  "poster_url": "https://...",
  "imdb_id": "tt0114709"
}
```

**Esquema `valoraciones`:**
```json
{
  "_id": ObjectId,
  "user_id": "string",
  "movie_id": 1,
  "rating": 4.5,
  "timestamp": ISODate
}
```

---

### `movie_recommender` — Machine Learning y streaming

| Colección | Documentos | Descripción |
|---|---|---|
| `movies` | 3.883 | Películas del dataset MovieLens original |
| `ratings` | 1.000.209 | Valoraciones históricas MovieLens |
| `users` | 6.040 | Usuarios demográficos MovieLens |
| `ratings_realtime` | variable | Eventos Kafka recibidos en tiempo real |
| `recommendations` | variable | Recomendaciones generadas por los modelos ML |
| `model_metrics` | 3 | Métricas de evaluación (RMSE, F1, Accuracy) |
| `evaluation_results` | variable | Resultados detallados de evaluación |
| `fs.files` / `fs.chunks` | variable | Modelos ML serializados en GridFS |

---

## API REST

La API corre en `http://localhost:8000`. Documentación interactiva en `/docs` (Swagger UI).

Todos los endpoints excepto `/api/auth/login` y `/api/auth/register` requieren el header:
```
Authorization: Bearer <token_jwt>
```

### Autenticación

| Método | Endpoint | Descripción |
|---|---|---|
| `POST` | `/api/auth/register` | Registrar nuevo usuario |
| `POST` | `/api/auth/login` | Login — devuelve JWT |
| `GET` | `/api/auth/me` | Datos del usuario autenticado |
| `PUT` | `/api/auth/me` | Actualizar nombre / email |
| `POST` | `/api/auth/change-password` | Cambiar contraseña |
| `POST` | `/api/auth/onboarding` | Guardar preferencias de géneros |

**Ejemplo — Registro:**
```bash
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"nombre": "Ana", "email": "ana@example.com", "password": "secret123"}'
```

**Ejemplo — Login:**
```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "ana@example.com", "password": "secret123"}'
# Respuesta: { "access_token": "eyJ...", "token_type": "bearer", "user": {...} }
```

### Películas

| Método | Endpoint | Descripción |
|---|---|---|
| `GET` | `/api/movies/search` | Buscar películas con filtros |
| `GET` | `/api/movies/trending` | Top películas por popularidad |
| `GET` | `/api/movies/recommendations` | Recomendaciones personalizadas |
| `POST` | `/api/movies/recommendations/refresh` | Forzar regeneración de recomendaciones |
| `GET` | `/api/movies/genre/{genre}` | Películas por género |
| `GET` | `/api/movies/watchlist` | Watchlist del usuario |
| `GET` | `/api/movies/my-ratings` | Historial de valoraciones del usuario |
| `POST` | `/api/movies/{id}/rate` | Valorar una película |
| `POST` | `/api/movies/{id}/watchlist` | Añadir a watchlist |
| `DELETE` | `/api/movies/{id}/watchlist` | Eliminar de watchlist |

**Parámetros de búsqueda** (`GET /api/movies/search`):

| Parámetro | Tipo | Descripción |
|---|---|---|
| `q` | string | Texto libre en el título |
| `genre` | string | Filtrar por género (ej: `Action`) |
| `year` | integer | Filtrar por año |
| `min_rating` | float | Rating mínimo (0.5 – 5.0) |
| `limit` | integer | Número de resultados (1-100, default 20) |

**Ejemplo — Buscar películas de acción de los 90 con rating alto:**
```bash
curl "http://localhost:8000/api/movies/search?genre=Action&year=1994&min_rating=4.0" \
  -H "Authorization: Bearer <token>"
```

**Ejemplo — Valorar una película:**
```bash
curl -X POST http://localhost:8000/api/movies/1/rate \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"score": 4.5}'
```

---

## Motor de recomendación

El endpoint `GET /api/movies/recommendations` aplica el siguiente algoritmo:

```
1. Obtener todas las valoraciones del usuario desde MongoDB

   ┌─ Sin valoraciones ──▶ usar preferred_groups del onboarding
   │                        → buscar películas de esos géneros con rating_avg ≥ 3.8
   │
   └─ Con valoraciones ──▶ calcular perfil de géneros ponderado:
        para cada película valorada positivamente (≥ 3★):
            peso[género] += rating_dado

        top_genres = 5 géneros con mayor peso acumulado

        candidatos = películas NO vistas con esos géneros
                     y rating_count ≥ 30 y rating_avg ≥ 3.0

        puntuación = afinidad_género × rating_avg_dataset

        devolver top 20 ordenados por puntuación
```

La respuesta incluye el campo `source` que indica qué algoritmo se aplicó:
- `"onboarding"` — recomendaciones basadas en preferencias iniciales
- `"content_based"` — recomendaciones basadas en historial
- `"trending"` — fallback si no hay candidatos válidos

---

## Modelos de Machine Learning

Los modelos se entrenan fuera de Docker (requieren Python 3.11 local) y guardan su estado en MongoDB GridFS. Una vez entrenados, sus métricas aparecen automáticamente en el dashboard.

### Preparar el entorno

```bash
python3 -m venv venv
source venv/bin/activate        # Linux/Mac
# venv\Scripts\activate         # Windows
pip install -r requirements.txt
```

### Filtrado Colaborativo — SVD

Predice la puntuación que daría el usuario a películas no vistas, basándose en patrones de usuarios con gustos similares (descomposición SVD sobre la matriz usuario-película).

```bash
# Entrenar (tarda ~3 min — entrena sobre 1M de ratings)
python -m recommender.collaborative --train

# Generar recomendaciones para el usuario con ml_user_id = 1
python -m recommender.collaborative --predict 1

# Ver las 20 mejores recomendaciones
python -m recommender.collaborative --predict 1 --top 20
```

- **Librería**: `scikit-surprise`
- **Métrica**: RMSE ≈ 0.87 (escala 1–5)
- **Evaluación**: split 80/20, entrenamiento final sobre dataset completo

### Filtrado por Contenido — TF-IDF + Coseno

Construye un perfil del usuario a partir de los géneros de las películas valoradas positivamente y busca películas similares mediante similitud coseno.

```bash
python -m recommender.content_based --train
python -m recommender.content_based --predict 1
```

- **Librería**: `scikit-learn`
- **Features**: géneros de las películas (18 categorías MovieLens)
- **Métrica**: similitud coseno (0 a 1)

### Clasificación — Random Forest

Predice si una película le gustará al usuario (rating ≥ 3.5) como problema de clasificación binaria.

```bash
python -m recommender.classification --train
python -m recommender.classification --predict 1
```

- **Librería**: `scikit-learn`
- **Métrica**: F1-Score ≈ 0.73 / Accuracy ≈ 73%
- **Features**: preferencias de género del usuario + historial de valoraciones

### Recomendador de Popularidad (fallback)

Sin entrenamiento previo. Devuelve las películas con más valoraciones y mejor rating medio. Se usa como fallback para usuarios sin historial.

### Dónde se guardan los modelos

Los modelos se serializan con `pickle` y se guardan en **MongoDB GridFS** (colección `movie_recommender.fs.files`). Esto permite cargarlos en cualquier momento sin reentrenamiento.

---

## Pipeline de streaming Kafka

### Flujo automático (en producción)

Cuando un usuario valora una película desde la web, el backend publica el evento en Kafka **de forma asíncrona** sin bloquear la respuesta:

```
POST /api/movies/{id}/rate
  → MongoDB: guarda valoración en cinerec.valoraciones
  → Kafka: publica en topic "movie_ratings" [asyncio.create_task]
  → Consumer: recibe el evento y guarda en movie_recommender.ratings_realtime
  → Node-RED: muestra el evento en el dashboard
```

No se necesita ninguna acción adicional. Funciona automáticamente con `docker compose up`.

### Simulación con datos históricos (opcional)

Para generar un flujo continuo de eventos de prueba a partir del dataset histórico:

```bash
source venv/bin/activate
python streaming/producer/ratings_producer.py
```

Envía 1 valoración por segundo al topic `movie_ratings`. Útil para ver el dashboard en acción sin esperar valoraciones reales.

### Estructura de un evento Kafka

```json
{
  "user":     "Ana",
  "movie_id": 318,
  "rating":   5.0,
  "timestamp": "2025-06-15T10:30:00"
}
```

---

## Dashboard Node-RED

Accede en **http://localhost:1881/ui**

El dashboard muestra en tiempo real:

| Widget | Descripción |
|---|---|
| Estadísticas globales | Nº películas, usuarios, valoraciones totales y eventos en streaming |
| Top 10 películas | Ordenadas por rating medio del dataset MovieLens |
| Recomendaciones SVD | Últimas predicciones del modelo colaborativo por usuario |
| Recomendaciones TF-IDF | Últimas predicciones del modelo por contenido |
| Recomendaciones RF | Últimas predicciones del modelo de clasificación |
| Métricas de modelos | RMSE, F1, Accuracy de cada modelo entrenado |
| Valoraciones en vivo | Eventos Kafka llegando en tiempo real desde la web |

Los flujos se actualizan automáticamente cada 10 segundos consultando MongoDB. También puedes forzar una actualización desde el editor de flujos (`http://localhost:1881`) pulsando el botón **Inject** de cualquier nodo.

---

## Desarrollo local sin Docker

Si prefieres hacer cambios en el código sin reconstruir imágenes, levanta solo la infraestructura en Docker y el backend/frontend en local:

```bash
# 1. Levantar solo la infraestructura (MongoDB, Kafka, Node-RED)
docker compose up mongodb zookeeper kafka nodered -d

# 2. Preparar entorno Python
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Terminal 1 — Backend con recarga automática
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# Terminal 2 — Consumidor Kafka
source venv/bin/activate
python streaming/consumer/ratings_consumer.py

# Terminal 3 — Frontend (servidor estático)
python3 -m http.server 3000 --directory frontend
# Accede a http://localhost:3000
```

> En modo local el frontend hace llamadas a `http://localhost:8000/api` directamente (sin el proxy nginx).

---

## Variables de entorno

El archivo `.env` (raíz del proyecto) configura todos los servicios:

| Variable | Default | Descripción |
|---|---|---|
| `MONGO_URL` | `mongodb://localhost:27017` | URL de MongoDB para el backend |
| `DB_NAME` | `cinerec` | Nombre de la BD de la aplicación web |
| `MONGO_URI` | `mongodb://localhost:27017` | URL de MongoDB para ETL y ML |
| `DATABASE_NAME` | `movie_recommender` | Nombre de la BD de ML |
| `SECRET_KEY` | `cinerec-dev-secret-...` | Clave para firmar los JWT — **¡cámbiala en producción!** |
| `KAFKA_TOPIC` | `movie_ratings` | Nombre del topic de Kafka |
| `KAFKA_SERVER` | `localhost:9092` | Dirección del broker Kafka |

> Dentro de Docker Compose, las URLs de MongoDB y Kafka usan los nombres de servicio (`mongodb:27017`, `kafka:29092`) en lugar de `localhost`. Esto se configura automáticamente en `docker-compose.yml`.

---

## Comandos útiles

### Docker Compose

```bash
# Iniciar todos los servicios
docker compose up -d

# Iniciar y reconstruir imágenes (tras cambios en código)
docker compose up --build -d

# Ver estado de todos los servicios
docker compose ps

# Ver logs en tiempo real
docker compose logs -f
docker compose logs backend -f
docker compose logs consumer -f

# Parar (conserva datos de MongoDB)
docker compose down

# Parar y borrar todos los datos
docker compose down -v

# Reiniciar un servicio concreto
docker compose restart backend
```

### MongoDB

```bash
# Abrir consola de MongoDB
docker exec -it movie_mongodb mongosh

# Ver bases de datos y colecciones
docker exec movie_mongodb mongosh --eval "show dbs"
docker exec movie_mongodb mongosh --eval "use cinerec; show collections"

# Contar documentos
docker exec movie_mongodb mongosh --eval "db.getSiblingDB('cinerec').peliculas.countDocuments()"

# Hacer un backup manual
docker exec movie_mongodb mongodump --out /tmp/backup
docker cp movie_mongodb:/tmp/backup ./mi_backup
```

### Reconstruir servicios individuales

```bash
docker compose up --build backend -d     # Solo backend
docker compose up --build frontend -d    # Solo frontend
docker compose up --build consumer -d    # Solo consumidor Kafka
```

---

## Solución de problemas

### El backend no arranca — "Application startup failed"

MongoDB no estaba listo cuando arrancó el backend. Solución:

```bash
docker compose logs mongodb --tail=20    # ¿Está healthy?
docker compose restart backend           # Reiniciar cuando MongoDB esté listo
```

### El consumer Kafka se reinicia en bucle al arrancar

Es normal los primeros 30-60 segundos mientras Kafka inicializa. Se conecta automáticamente en cuanto Kafka está listo.

```bash
docker compose logs consumer --follow    # Verás "Connected to Kafka" cuando esté listo
```

### El puerto 80 ya está en uso

Otro servicio usa el puerto 80. Cambia el puerto del frontend en `docker-compose.yml`:

```yaml
frontend:
  ports:
    - "3000:80"   # Accede desde http://localhost:3000
```

### El puerto 8000 ya está en uso

Hay un proceso local usando el puerto 8000 (por ejemplo, uvicorn corriendo fuera de Docker):

```bash
ss -tlnp | grep 8000          # Identificar el proceso
kill <PID>                     # Matarlo
docker compose up backend -d   # Volver a levantar el backend
```

### Node-RED no muestra datos en el dashboard

1. Asegúrate de que MongoDB tiene datos: `docker exec movie_mongodb mongosh --eval "db.getSiblingDB('movie_recommender').movies.countDocuments()"`
2. En el editor de flujos (`http://localhost:1881`), pulsa el botón **Inject** de cualquier nodo para forzar una consulta.
3. Si los datos siguen sin aparecer, reinicia Node-RED: `docker compose restart nodered`

### Conflicto de nombres de contenedores al arrancar

Si tienes contenedores de otro proyecto con el mismo nombre (`movie_mongodb`, `movie_kafka`...):

```bash
docker ps -a                         # Ver todos los contenedores
docker stop <nombre> && docker rm <nombre>   # Eliminar el conflictivo
docker compose up -d                 # Volver a arrancar
```

### Los datos de MongoDB desaparecen tras reiniciar

Esto ocurre solo si usas `docker compose down -v` (borra los volúmenes). Con `docker compose down` a secas los datos se conservan en el volumen `cinerec_mongo_data`. Si los pierdes, restaura desde el backup:

```bash
docker cp mongodump/. movie_mongodb:/tmp/restore
docker exec movie_mongodb mongorestore --dir /tmp/restore --drop --quiet
docker exec movie_mongodb rm -rf /tmp/restore
```
