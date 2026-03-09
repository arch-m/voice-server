#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

echo "=== Instalacion de OCR Gateway con uv ==="

echo "[1/3] Instalando dependencias del sistema..."
sudo pacman -S --noconfirm uv

if ! command -v python3.11 >/dev/null 2>&1; then
  echo "python3.11 no esta disponible en PATH." >&2
  echo "Instalalo antes de continuar; este proyecto fija Python 3.11." >&2
  exit 1
fi

# shellcheck source=./scripts/ensure_uv.sh
source "${ROOT_DIR}/scripts/ensure_uv.sh"

echo "[2/3] Sincronizando proyecto uv para OCR Gateway..."
"${ROOT_DIR}/scripts/sync-project.sh" apps/ocr_gateway

echo "[3/3] Verificando imports criticos..."
cd "${ROOT_DIR}"
export PYTHONPATH="${ROOT_DIR}${PYTHONPATH:+:${PYTHONPATH}}"
"${UV_BIN}" run --project "${ROOT_DIR}/apps/ocr_gateway" python -c "import apps.ocr_gateway.main; print('ocr_gateway ok')"

echo ""
echo "Entorno uv: ${ROOT_DIR}/apps/ocr_gateway/.venv"
echo "Servidor: ${ROOT_DIR}/scripts/run/ocr-gateway.sh"
echo "Endpoint: POST http://localhost:8012/ocr"
