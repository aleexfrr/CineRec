# CineRec — Sistema de Recomendación de Películas

Sistema de recomendación de películas en tiempo real desarrollado con Python, MongoDB, Kafka y NodeRED. Combina técnicas clásicas de Machine Learning con procesamiento de datos en streaming para generar recomendaciones personalizadas a partir del dataset MovieLens.

---

## Descripción del proyecto

CineRec es un proyecto de fin de curso del **Máster en Inteligencia Artificial y Big Data**. El objetivo es construir un sistema end-to-end que cubra todas las fases de un proyecto de datos real:

- **Ingesta** de datos en crudo desde ficheros `.dat`
- **Transformación y limpieza** mediante un pipeline ETL
- **Almacenamiento** en base de datos NoSQL (MongoDB)
- **Modelado** con cuatro algoritmos de recomendación e IA
- **Streaming** en tiempo real de eventos de ratings con Kafka
- **Visualización** de métricas y resultados en un dashboard con NodeRED

El dataset utilizado es **MovieLens 1M**, que contiene 1.000.209 ratings de 6.040 usuarios sobre 3.883 películas.

---

## Stack tecnológico

| Componente | Tecnología |
|---|---|
| Lenguaje | Python 3.11+ |
| Base de datos | MongoDB 7 |
| Streaming | Apache Kafka + Zookeeper |
| Dashboard | NodeRED |
| Orquestación | Docker Compose |
| ML — Colaborativo | Surprise (SVD) |
| ML — Contenido | scikit-learn (TF-IDF + Cosine Similarity) |
| ML — Clasificación | scikit-learn (Random Forest) |

---

## Arquitectura

```
datos raw (.dat)
      │
      ▼
┌──────────────┐
│ ETL Pipeline │  extract → transform → load
└──────┬───────┘
       │
       ▼
┌─────────────┐
│   MongoDB   │  movies · users · ratings · recommendations
└──────┬──────┘
       │
       ├────────────────────────────────────────┐
       ▼                                        ▼
┌───────────────────┐                  ┌───────────────────┐
│  Recomendadores   │                  │  Kafka Streaming  │
│  ─ Popularity     │                  │  Producer → Topic │
│  ─ Collaborative  │                  │  Consumer → Mongo │
│  ─ Content-Based  │                  └───────────────────┘
│  ─ Classification |                          │
└────────┬──────────┘                          │
         └────────────────┬────────────────────┘
                          ▼
                  ┌──────────────┐
                  │   NodeRED    │  Dashboard en tiempo real
                  └──────────────┘
```

---

## Modelos de IA

### 1. Popularity Recommender
Recomienda las películas con mayor rating medio, filtrando por un mínimo de votos para evitar sesgos. No es personalizado pero sirve como baseline para comparar con los demás modelos.

### 2. Collaborative Filtering — SVD
Modelo de **filtrado colaborativo** basado en la descomposición en valores singulares (SVD). Aprende patrones latentes de comportamiento entre usuarios y películas: si dos usuarios han valorado de forma similar las mismas películas, se asume que tienen gustos parecidos y se les recomiendan películas que el otro ha valorado bien pero el primero no ha visto.

- **Librería:** Surprise
- **Evaluación:** RMSE sobre el conjunto de test

### 3. Content-Based — TF-IDF + Cosine Similarity
Recomienda películas similares a una película dada basándose en sus géneros. Los géneros se vectorizan con TF-IDF y la similitud entre películas se calcula con la similitud del coseno entre sus vectores.

- **Librería:** scikit-learn
- **Input:** título de una película
- **Output:** top N películas más similares con su puntuación de similitud

### 4. Classification — Random Forest
Modelo de **clasificación binaria** que predice si a un usuario le gustará o no una película (liked = rating ≥ 4). Utiliza como features el perfil del usuario (edad, género, ocupación), características de la película (año, géneros en one-hot encoding) y el historial de interacciones.

- **Librería:** scikit-learn
- **Métricas:** Accuracy, Precision, Recall, F1-Score
- **Output:** probabilidad de que al usuario le guste cada película no vista

### Evaluación comparativa
Los cuatro modelos se comparan entre sí usando métricas estándar de sistemas de recomendación:

- **Precision@10** — de las 10 recomendadas, ¿cuántas le gustaron realmente al usuario?
- **Recall@10** — de todas las que le gustaron, ¿cuántas aparecen en el top 10?
- **NDCG@10** — mide la calidad del ranking, penalizando más los errores en las primeras posiciones

---

## Estructura del proyecto

```
CineRec/
├── .env                          # Variables de entorno (no subir a git)
├── .gitignore
├── config.py                     # Configuración centralizada
├── docker-compose.yml            # Orquestación de servicios
├── requirements.txt
│
├── data/
│   ├── raw/                      # Datos originales MovieLens (.dat)
│   └── processed/                # Datos limpios (.csv)
│
├── etl/
│   ├── extract.py                # Lectura de ficheros raw
│   ├── transform.py              # Limpieza y transformación
│   ├── load_mongodb.py           # Carga en MongoDB
│   └── pipeline.py               # Orquesta el ETL completo
│
├── recommender/
│   ├── popularity/
│   │   └── popularity_recommender.py
│   ├── collaborative/
│   │   └── collaborative_filtering.py
│   ├── content_based/
│   │   └── content_based.py
│   ├── classification/
│   │   └── classification_recommender.py
│   └── evaluation/
│       └── evaluation.py         # Comparativa de modelos
│
├── streaming/
│   ├── producer/
│   │   └── ratings_producer.py   # Envía ratings a Kafka
│   └── consumer/
│       └── ratings_consumer.py   # Consume eventos y guarda en MongoDB
│
├── nodered/
│   ├── flows.json                # Dashboard NodeRED
│   └── settings.js
│
└── notebooks/
    └── 01_eda.ipynb              # Análisis exploratorio de datos
```

---

## Instalación y uso

### Requisitos previos
- Docker y Docker Compose instalados
- Python 3.11+

### 1. Clonar el repositorio

```bash
git clone <url-del-repositorio>
cd CineRec
```

### 2. Configurar variables de entorno

El fichero `.env` ya incluye los valores por defecto para Docker Compose:

```
MONGO_URI=mongodb://localhost:27017
DATABASE_NAME=movie_recommender
KAFKA_TOPIC=movie_ratings
KAFKA_SERVER=localhost:9092
```

### 3. Levantar los servicios

```bash
docker compose up -d
```

Esto arranca MongoDB, Kafka, Zookeeper y NodeRED.

### 4. Instalar dependencias Python

```bash
pip install -r requirements.txt
```

### 5. Ejecutar el ETL

```bash
python etl/pipeline.py
```

### 6. Ejecutar los recomendadores

```bash
python recommender/popularity/popularity_recommender.py
python recommender/collaborative/collaborative_filtering.py
python recommender/content_based/content_based.py
python recommender/classification/classification_recommender.py
```

### 7. Evaluar los modelos

```bash
python recommender/evaluation/evaluation.py
```

### 8. Streaming en tiempo real

```bash
# Terminal 1 — Consumer
python streaming/consumer/ratings_consumer.py

# Terminal 2 — Producer
python streaming/producer/ratings_producer.py
```

### 9. Dashboard NodeRED

Instala los plugins en `http://localhost:1880` → Manage palette:
- `node-red-dashboard`
- `node-red-node-mongodb`

Dashboard disponible en:
```
http://localhost:1880/ui
```

---

## Dataset

**MovieLens 1M** — GroupLens Research

| Fichero | Contenido |
|---|---|
| `movies.dat` | 3.883 películas con título, géneros y año |
| `users.dat` | 6.040 usuarios con edad, género y ocupación |
| `ratings.dat` | 1.000.209 ratings (escala 1-5) con timestamp |