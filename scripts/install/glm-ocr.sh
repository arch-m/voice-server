#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

echo "=== Instalacion de GLM-OCR con uv ==="

echo "[1/4] Instalando dependencias del sistema..."
sudo pacman -S --noconfirm uv

if ! command -v python3.11 >/dev/null 2>&1; then
  echo "python3.11 no esta disponible en PATH." >&2
  echo "Instalalo antes de continuar; este proyecto fija Python 3.11." >&2
  exit 1
fi

# shellcheck source=./scripts/ensure_uv.sh
source "${ROOT_DIR}/scripts/ensure_uv.sh"

echo "[2/4] Sincronizando proyecto uv para GLM-OCR..."
"${ROOT_DIR}/scripts/sync-project.sh" apps/ocr_glm_api

echo "[3/4] Verificando imports criticos..."
cd "${ROOT_DIR}"
export PYTHONPATH="${ROOT_DIR}${PYTHONPATH:+:${PYTHONPATH}}"
"${UV_BIN}" run --project "${ROOT_DIR}/apps/ocr_glm_api" python -c "import apps.ocr_glm_api.main; print('ocr_glm_api ok')"

echo "[4/4] Listo."
echo ""
echo "Entorno uv: ${ROOT_DIR}/apps/ocr_glm_api/.venv"
echo "Servidor: ${ROOT_DIR}/scripts/run/glm-ocr.sh"
