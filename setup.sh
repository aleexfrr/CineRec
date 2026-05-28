#!/bin/bash
# ============================================================
#  CineRec — Script de instalación automática
#  Uso: bash setup.sh
# ============================================================
set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

ok()   { echo -e "${GREEN}[OK]${NC} $1"; }
info() { echo -e "${YELLOW}[..] $1${NC}"; }
err()  { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

echo ""
echo "=============================================="
echo "   CineRec — Sistema de Recomendación"
echo "=============================================="
echo ""

# ── 1. Comprobar Docker ───────────────────────────────────────
info "Comprobando Docker..."
command -v docker &>/dev/null   || err "Docker no está instalado. Instálalo desde https://docs.docker.com/get-docker/"
docker info &>/dev/null         || err "El servicio Docker no está corriendo. Arráncalo antes de ejecutar este script."
docker compose version &>/dev/null || err "Docker Compose v2 no está instalado."
ok "Docker $(docker --version | awk '{print $3}' | tr -d ',')"

# ── 2. Copiar .env si no existe ───────────────────────────────
if [ ! -f .env ]; then
    cp .env.example .env
    info "Creado .env desde .env.example (revisa la SECRET_KEY antes de producción)"
fi

# ── 3. Levantar servicios ─────────────────────────────────────
info "Construyendo e iniciando servicios Docker (puede tardar varios minutos la primera vez)..."
docker compose up --build -d
ok "Servicios levantados"

# ── 4. Esperar a que MongoDB esté healthy ─────────────────────
info "Esperando a que MongoDB esté listo..."
MAX=60
COUNT=0
until docker inspect --format='{{.State.Health.Status}}' movie_mongodb 2>/dev/null | grep -q "healthy"; do
    sleep 2
    COUNT=$((COUNT + 2))
    if [ $COUNT -ge $MAX ]; then
        err "MongoDB no respondió en ${MAX}s. Revisa: docker compose logs mongodb"
    fi
    echo -n "."
done
echo ""
ok "MongoDB listo"

# ── 5. Restaurar datos ────────────────────────────────────────
if [ -d "mongodump" ]; then
    info "Restaurando datos de MongoDB..."
    docker cp mongodump/. movie_mongodb:/tmp/mongodump_restore
    docker exec movie_mongodb mongorestore \
        --dir /tmp/mongodump_restore \
        --drop \
        --quiet
    docker exec movie_mongodb rm -rf /tmp/mongodump_restore
    ok "Datos restaurados"
else
    echo -e "${YELLOW}[AVISO]${NC} No se encontró la carpeta mongodump/. Si quieres datos de ejemplo, ejecuta:"
    echo "        python3 etl/pipeline.py"
fi

# ── 6. Resumen ────────────────────────────────────────────────
echo ""
echo "=============================================="
echo -e "${GREEN}  Instalación completada${NC}"
echo "=============================================="
echo ""
echo "  Web principal   →  http://localhost"
echo "  API (Swagger)   →  http://localhost:8000/docs"
echo "  Dashboard       →  http://localhost:1881/ui"
echo ""
echo "  Para parar:     docker compose down"
echo "  Para ver logs:  docker compose logs -f"
echo ""
