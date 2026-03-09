#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
UNIT_SRC_DIR="${ROOT_DIR}/systemd/user"
UNIT_DST_DIR="${XDG_CONFIG_HOME:-${HOME}/.config}/systemd/user"

mkdir -p "${UNIT_DST_DIR}"

for template in "${UNIT_SRC_DIR}"/*.service; do
  unit_name="$(basename "${template}")"
  sed "s|@ROOT_DIR@|${ROOT_DIR}|g" "${template}" > "${UNIT_DST_DIR}/${unit_name}"
  chmod 0644 "${UNIT_DST_DIR}/${unit_name}"
done

systemctl --user daemon-reload

cat <<'EOF'
Unidades instaladas en ~/.config/systemd/user

Para habilitarlas:
  systemctl --user enable --now qwen-tts.service qwen-tts-clone.service qwen-asr.service deepseek-ocr.service glm-ocr.service ocr-gateway.service
EOF
