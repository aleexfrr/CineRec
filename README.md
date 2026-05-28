# CineRec — Sistema de Recomendación de Películas

CineRec es una plataforma completa de recomendación de películas construida con Python, FastAPI, MongoDB, Kafka y modelos de Machine Learning. Incluye una interfaz web estilo Netflix, un dashboard de analíticas en tiempo real y tres motores de recomendación distintos entrenados sobre el dataset MovieLens 1M.

---

## Índice

1. [Arquitectura](#arquitectura)
2. [Requisitos previos](#requisitos-previos)
3. [Inicio rápido con Docker](#inicio-rápido-con-docker)
4. [Primera vez: cargar datos](#primera-vez-cargar-datos)
5. [Entrenamiento de modelos ML](#entrenamiento-de-modelos-ml)
6. [Streaming en tiempo real](#streaming-en-tiempo-real)
7. [Acceso a los servicios](#acceso-a-los-servicios)
8. [Desarrollo local sin Docker](#desarrollo-local-sin-docker)
9. [Estructura del proyecto](#estructura-del-proyecto)
10. [Descripción de los modelos](#descripción-de-los-modelos)
11. [Solución de problemas](#solución-de-problemas)

---

## Arquitectura

```
┌──────────────────────────────────────────────────────────────┐
│                       Docker Compose                         │
│                                                              │
│  ┌──────────┐    ┌──────────┐    ┌──────────────────────┐    │
│  │ Frontend │    │ Backend  │    │       MongoDB        │    │
│  │  nginx   │    │ FastAPI  │    │  ┌────────────────┐  │    │
│  │  :80     │    │  :8000   │    │  │    cinerec     │  │    │
│  └──────────┘    └────┬─────┘    │  │  (app web DB)  │  │    │
│                       │          │  ├────────────────┤  │    │
│  ┌──────────┐         │          │  │ movie_recomm.. │  │    │
│  │ NodeRED  │─────────┼──────────┤  │ (ML + stream)  │  │    │
│  │  :1881   │         │          │  └────────────────┘  │    │
│  └──────────┘         │          └──────────────────────┘    │
│                       │                                      │
│  ┌──────────┐    ┌────┴─────┐                                │
│  │ Consumer │◄───│  Kafka   │                                │
│  │ (Python) │    │  :9092   │                                │
│  └──────────┘    └──────────┘                                │
└──────────────────────────────────────────────────────────────┘
```

| Servicio  | Descripción                                     | Puerto |
|-----------|-------------------------------------------------|--------|
| frontend  | Interfaz web (nginx sirviendo HTML/CSS/JS)      | 80     |
| backend   | API REST (FastAPI + Motor async)                | 8000   |
| mongodb   | Base de datos principal (MongoDB 7)             | 27017  |
| kafka     | Bus de eventos para streaming en tiempo real    | 9092   |
| zookeeper | Coordinador de Kafka                            | 2181   |
| consumer  | Consumidor Kafka → MongoDB (servicio Python)    | —      |
| nodered   | Dashboard de analíticas en tiempo real          | 1881   |

---

## Requisitos previos

### Docker y Docker Compose (obligatorio)

```bash
# Ubuntu / Debian
sudo apt update
sudo apt install -y ca-certificates curl gnupg

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
sudo usermod -aG docker $USER
newgrp docker
```

Verifica:

```bash
docker --version          # Docker version 24.x o superior
docker compose version    # Docker Compose version v2.x o superior
```

### Python 3.11+ (solo para ETL y modelos ML)

```bash
sudo apt install -y python3.11 python3.11-venv python3-pip

# En la raíz del proyecto
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

## Inicio rápido con Docker

```bash
# 1. Descomprimir o clonar el proyecto
cd CineRec

# 2. Construir e iniciar todos los servicios
docker compose up --build -d

# 3. Comprobar que todo está corriendo
docker compose ps
```

La primera vez tarda varios minutos (descarga de imágenes + build). Cuando todos los servicios muestren `running`, el sistema está listo.

> La base de datos arranca **vacía**. Continúa con la sección siguiente para cargar el dataset MovieLens.

Para parar los servicios:

```bash
docker compose down          # Para y elimina los contenedores (los datos se conservan)
docker compose down -v       # Para, elimina contenedores Y datos de MongoDB
```

---

## Primera vez: cargar datos

El dataset MovieLens 1M (6.040 usuarios · 3.883 películas · 1.000.209 valoraciones) está incluido en `data/raw/`. Hay que cargarlo en MongoDB ejecutando el ETL.

```bash
# Activar el entorno virtual
source venv/bin/activate

# Ejecutar el pipeline ETL completo (tarda ~2 minutos)
python etl/pipeline.py
```

El ETL realiza tres pasos:
1. **Extracción** — lee los archivos `.dat` de MovieLens
2. **Transformación** — limpia, normaliza y convierte tipos
3. **Carga** — inserta en la base de datos `movie_recommender` de MongoDB

### Cargar pósters (opcional)

Descarga automáticamente las portadas de las películas desde internet:

```bash
python scripts/fetch_posters_by_title.py
```

Requiere conexión a internet. Puede tardar varios minutos dependiendo de la velocidad de la red.

---

## Entrenamiento de modelos ML

CineRec incluye tres modelos de recomendación. Entrena los que quieras antes de que el dashboard muestre sus métricas.

### Filtrado Colaborativo — SVD

```bash
source venv/bin/activate

# Entrenar el modelo (guarda en MongoDB GridFS, tarda ~3 min)
python -m recommender.collaborative --train

# Generar recomendaciones para el usuario con ID 1
python -m recommender.collaborative --predict 1
```

### Filtrado por Contenido — TF-IDF

```bash
python -m recommender.content_based --train
python -m recommender.content_based --predict 1
```

### Clasificación — Random Forest

```bash
python -m recommender.classification --train
python -m recommender.classification --predict 1
```

Las métricas (RMSE, F1, Accuracy…) se guardan en `movie_recommender.model_metrics` y aparecen automáticamente en el dashboard de NodeRED.

---

## Streaming en tiempo real

### Valoraciones reales de la web (automático)

Cuando un usuario registrado valora una película en la web, el backend publica el evento en Kafka de forma automática. El servicio `consumer` lo recibe y lo guarda en `ratings_realtime`. **No se necesita ninguna acción adicional**, funciona solo con `docker compose up`.

### Simulación con datos históricos (opcional)

Para generar un flujo continuo de eventos de prueba:

```bash
source venv/bin/activate
python streaming/producer/ratings_producer.py
```

Envía una valoración por segundo al topic `movie_ratings`. El dashboard de NodeRED (`http://localhost:1881/ui`) los muestra en tiempo real.

---

## Acceso a los servicios

| Servicio               | URL                        | Descripción                      |
|------------------------|----------------------------|----------------------------------|
| Aplicación web         | http://localhost           | Interfaz principal               |
| Documentación API      | http://localhost:8000/docs | Swagger UI interactivo           |
| Dashboard analíticas   | http://localhost:1881/ui   | NodeRED — métricas en tiempo real|
| Editor de flujos       | http://localhost:1881      | NodeRED — editor de flujos       |
| MongoDB (cliente GUI)  | localhost:27017            | Conectar con MongoDB Compass     |

### Primer acceso

1. Abre **http://localhost**
2. Crea una cuenta con **Registrarse**
3. Completa el onboarding (selección de géneros favoritos)
4. Explora el catálogo y valora películas

Cuanto más valores, más personalizadas serán las recomendaciones.

---

## Desarrollo local sin Docker

Si prefieres desarrollar sin contenedores, solo levanta la infraestructura en Docker y el resto en local:

```bash
# 1. Levantar solo la infraestructura
docker compose up mongodb zookeeper kafka nodered -d

# 2. Activar entorno virtual
source venv/bin/activate

# 3. Backend (terminal 1)
cd backend
uvicorn main:app --reload --port 8000

# 4. Consumidor Kafka (terminal 2)
source venv/bin/activate
python streaming/consumer/ratings_consumer.py

# 5. Frontend — opción A: abrir el HTML directamente en el navegador
xdg-open frontend/index.html

# 5. Frontend — opción B: servidor local
python3 -m http.server 3000 --directory frontend
# Accede a http://localhost:3000
```

### Variables de entorno para desarrollo local

El archivo `.env` en la raíz ya tiene los valores correctos para local:

```env
MONGO_URL=mongodb://localhost:27017
DB_NAME=cinerec
MONGO_URI=mongodb://localhost:27017
DATABASE_NAME=movie_recommender
SECRET_KEY=cinerec-dev-secret-cambiar-en-produccion
KAFKA_TOPIC=movie_ratings
KAFKA_SERVER=localhost:9092
```

---

## Estructura del proyecto

```
CineRec/
│
├── backend/                     # API REST
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py                  # Punto de entrada de FastAPI
│   └── app/
│       ├── config.py            # Variables de entorno
│       ├── database.py          # Conexión MongoDB (Motor async)
│       ├── auth_utils.py        # JWT y contraseñas
│       ├── kafka_producer.py    # Publica valoraciones en Kafka
│       ├── ml_sync.py           # Sincroniza datos al dataset ML
│       ├── models/              # Esquemas Pydantic
│       │   ├── usuario.py
│       │   └── valoracion.py
│       └── routers/             # Endpoints de la API
│           ├── auth.py          # Registro, login, perfil
│           └── peliculas.py     # Búsqueda, recomendaciones, valoraciones
│
├── frontend/                    # Interfaz web
│   ├── Dockerfile
│   ├── nginx.conf
│   ├── index.html               # Login y registro
│   ├── movies.html              # Catálogo principal (estilo Netflix)
│   ├── onboarding.html          # Preferencias de géneros
│   ├── profile.html             # Perfil, historial y watchlist
│   ├── css/style.css
│   └── js/
│       ├── auth.js              # Login y registro
│       ├── movies.js            # Catálogo, búsqueda, modal de película
│       ├── onboarding.js        # Selección de géneros favoritos
│       └── profile.js           # Perfil de usuario
│
├── recommender/                 # Modelos de Machine Learning
│   ├── collaborative/           # SVD — Filtrado colaborativo
│   ├── content_based/           # TF-IDF — Filtrado por contenido
│   ├── classification/          # Random Forest — Clasificación
│   ├── popularity/              # Recomendador por popularidad global
│   ├── evaluation/              # Evaluación y métricas
│   └── model_store.py           # Guardar/cargar modelos en GridFS
│
├── streaming/                   # Pipeline Kafka
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── producer/
│   │   └── ratings_producer.py  # Envía eventos históricos a Kafka
│   └── consumer/
│       └── ratings_consumer.py  # Recibe eventos y los guarda en MongoDB
│
├── nodered/                     # Dashboard de analíticas
│   ├── Dockerfile
│   ├── flows.json               # Flujos preconstruidos (baked-in)
│   └── settings.js              # Configuración de NodeRED
│
├── etl/                         # Carga del dataset MovieLens
│   ├── extract.py
│   ├── transform.py
│   ├── load_mongodb.py
│   └── pipeline.py              # Ejecuta extract → transform → load
│
├── data/
│   ├── raw/                     # Dataset original MovieLens 1M (.dat)
│   │   ├── movies.dat
│   │   ├── ratings.dat
│   │   └── users.dat
│   └── processed/               # CSVs limpios generados por el ETL
│
├── scripts/
│   └── fetch_posters_by_title.py # Descarga pósters de películas
│
├── notebooks/                   # Análisis exploratorio (Jupyter)
│   ├── 01_eda.ipynb
│   ├── 02_modelos.ipynb
│   └── 03_recomendaciones.ipynb
│
├── docker-compose.yml           # Orquestación de todos los servicios
├── config.py                    # Config compartida para ETL y streaming
├── .env                         # Variables de entorno (no subir a git)
└── requirements.txt             # Todas las dependencias Python
```

---

## Descripción de los modelos

### Filtrado Colaborativo — SVD

Usa descomposición en valores singulares sobre la matriz usuario-película para predecir el rating que daría un usuario a una película que no ha visto, basándose en patrones de usuarios con gustos similares.

- **Librería**: `scikit-surprise`
- **Métrica**: RMSE ≈ 0.87 (escala 1-5)
- **Datos de entrenamiento**: 1.000.209 valoraciones

### Filtrado por Contenido — TF-IDF + Coseno

Construye un perfil del usuario a partir de los géneros de las películas que ha valorado positivamente y calcula similitud coseno con todo el catálogo para encontrar películas parecidas.

- **Librería**: `scikit-learn`
- **Métrica**: Similitud coseno (0 a 1)
- **Features**: Géneros de las películas

### Clasificación — Random Forest

Predice si a un usuario le gustará una película (rating ≥ 3.5) utilizando como features sus preferencias de género e historial de valoraciones.

- **Librería**: `scikit-learn`
- **Métrica**: F1-Score ≈ 0.73, Accuracy ≈ 73%

### Dashboard NodeRED (`http://localhost:1881/ui`)

Muestra en tiempo real:
- **Estadísticas globales**: número de películas, usuarios, valoraciones y eventos Kafka
- **Top 10 películas**: ordenadas por valoración media del dataset
- **Recomendaciones colaborativas**: últimas predicciones SVD por usuario
- **Recomendaciones por contenido**: últimas predicciones TF-IDF por usuario
- **Recomendaciones por clasificación**: últimas predicciones Random Forest
- **Métricas de modelos**: RMSE, F1, Accuracy de cada modelo entrenado
- **Valoraciones en tiempo real**: eventos Kafka llegando en vivo desde la web

---

## Solución de problemas

### El backend no arranca — "MongoDB no disponible"

```bash
# Ver el estado de MongoDB
docker compose ps mongodb

# Ver los logs
docker compose logs mongodb --tail=30
```

### El consumidor Kafka se reinicia en bucle

Es normal los primeros 30-60 segundos hasta que Kafka está listo. Se conectará solo.

```bash
docker compose logs consumer --follow
```

### NodeRED no muestra datos en el dashboard

1. Ejecuta el ETL: `python etl/pipeline.py`
2. Comprueba que MongoDB tiene datos en `movie_recommender`
3. En el editor de NodeRED (`http://localhost:1881`), pulsa el botón del nodo **Inject** para forzar una consulta

### Puerto 80 ocupado

Edita `docker-compose.yml` y cambia el puerto del frontend:

```yaml
frontend:
  ports:
    - "3000:80"   # Accede desde http://localhost:3000
```

### Reconstruir un servicio tras cambios en el código

```bash
docker compose up --build backend -d    # Solo el backend
docker compose up --build frontend -d   # Solo el frontend
docker compose up --build -d            # Todos
```

### Ver logs de cualquier servicio

```bash
docker compose logs backend --follow
docker compose logs consumer --follow
docker compose logs nodered --follow
```
