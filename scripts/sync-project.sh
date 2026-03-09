#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "Uso: $0 <directorio-del-proyecto>" >&2
  exit 1
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROJECT_DIR="$1"
PYTHON_VERSION="${UV_PYTHON:-3.11}"

# shellcheck source=./ensure_uv.sh
source "${ROOT_DIR}/scripts/ensure_uv.sh"

cd "${ROOT_DIR}/${PROJECT_DIR}"
"${UV_BIN}" sync --python "${PYTHON_VERSION}"
