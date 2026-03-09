#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PROJECT_DIR="${ROOT_DIR}/apps/qwen_asr_api"

# shellcheck source=./ensure_uv.sh
source "${ROOT_DIR}/scripts/ensure_uv.sh"

cd "${ROOT_DIR}"
export PYTHONPATH="${ROOT_DIR}${PYTHONPATH:+:${PYTHONPATH}}"
exec "${UV_BIN}" run --project "${PROJECT_DIR}" python -m apps.qwen_asr_api.main
