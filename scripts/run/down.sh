#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

patterns=(
  "uv run --project ${ROOT_DIR}/apps/qwen_tts_api python -m apps.qwen_tts_api.main"
  "uv run --project ${ROOT_DIR}/apps/qwen_tts_api python -m apps.qwen_tts_api.tts_clone_server"
  "uv run --project ${ROOT_DIR}/apps/qwen_asr_api python -m apps.qwen_asr_api.main"
  "uv run --project ${ROOT_DIR}/apps/ocr_deepseek_api python -m apps.ocr_deepseek_api.main"
  "uv run --project ${ROOT_DIR}/apps/ocr_glm_api python -m apps.ocr_glm_api.main"
  "uv run --project ${ROOT_DIR}/apps/ocr_gateway python -m apps.ocr_gateway.main"
  "${ROOT_DIR}/apps/qwen_tts_api/.venv/bin/python3 -m apps.qwen_tts_api.main"
  "${ROOT_DIR}/apps/qwen_tts_api/.venv/bin/python3 -m apps.qwen_tts_api.tts_clone_server"
  "${ROOT_DIR}/apps/qwen_asr_api/.venv/bin/python3 -m apps.qwen_asr_api.main"
  "${ROOT_DIR}/apps/ocr_deepseek_api/.venv/bin/python3 -m apps.ocr_deepseek_api.main"
  "${ROOT_DIR}/apps/ocr_glm_api/.venv/bin/python3 -m apps.ocr_glm_api.main"
  "${ROOT_DIR}/apps/ocr_gateway/.venv/bin/python3 -m apps.ocr_gateway.main"
)

declare -A seen=()
pids=()

for pattern in "${patterns[@]}"; do
  while IFS= read -r pid; do
    [[ -n "${pid}" ]] || continue
    if [[ -z "${seen[$pid]+x}" ]]; then
      seen["$pid"]=1
      pids+=("$pid")
    fi
  done < <(pgrep -f "$pattern" || true)
done

if [[ ${#pids[@]} -eq 0 ]]; then
  echo "No hay procesos activos del stack actual."
  exit 0
fi

echo "Deteniendo servicios: ${pids[*]}"
kill "${pids[@]}"
