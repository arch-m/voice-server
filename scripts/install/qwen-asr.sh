#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

# shellcheck source=./load_env.sh
source "${ROOT_DIR}/scripts/load_env.sh"

MODELS_DIR="$(resolve_repo_path "${MODELS_DIR:-./models}")"
MODEL_PATH="$(resolve_repo_path "${QWEN_ASR_MODEL:-${MODELS_DIR}/qwen-asr-model}")"

echo "=== Instalacion de Qwen3-ASR con uv ==="

echo "[1/5] Instalando dependencias del sistema..."
sudo pacman -S --noconfirm ffmpeg sox uv

if ! command -v python3.11 >/dev/null 2>&1; then
  echo "python3.11 no esta disponible en PATH." >&2
  echo "Instalalo antes de continuar; este proyecto fija Python 3.11." >&2
  exit 1
fi

# shellcheck source=./scripts/ensure_uv.sh
source "${ROOT_DIR}/scripts/ensure_uv.sh"

echo "[2/5] Sincronizando proyecto uv para ASR..."
"${ROOT_DIR}/scripts/sync-project.sh" apps/qwen_asr_api

echo "[3/5] Descargando modelo Qwen3-ASR-0.6B..."
mkdir -p "$(dirname "${MODEL_PATH}")"
cd "${ROOT_DIR}/apps/qwen_asr_api"
"${UV_BIN}" run hf download Qwen/Qwen3-ASR-0.6B --local-dir "${MODEL_PATH}"
rm -rf "${MODEL_PATH}/.cache"
echo "Modelo descargado en: ${MODEL_PATH}"

echo "[4/5] Verificando imports criticos..."
cd "${ROOT_DIR}"
export PYTHONPATH="${ROOT_DIR}${PYTHONPATH:+:${PYTHONPATH}}"
"${UV_BIN}" run --project "${ROOT_DIR}/apps/qwen_asr_api" python -c "import apps.qwen_asr_api.main; print('qwen_asr_api ok')"

echo "[5/5] Listo."
echo ""
echo "Entorno uv: ${ROOT_DIR}/apps/qwen_asr_api/.venv"
echo "Servidor ASR: ${ROOT_DIR}/scripts/run/qwen-asr.sh"
echo "Endpoint: POST http://localhost:8003/asr"
