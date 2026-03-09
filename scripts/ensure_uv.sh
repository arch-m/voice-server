#!/usr/bin/env bash

if [[ -n "${UV_BIN:-}" && -x "${UV_BIN}" ]]; then
  return 0 2>/dev/null || exit 0
fi

if command -v uv >/dev/null 2>&1; then
  UV_BIN="$(command -v uv)"
elif [[ -x /usr/bin/uv ]]; then
  UV_BIN="/usr/bin/uv"
else
  cat >&2 <<'EOF'
uv is required but was not found.

Install it on Arch Linux with:
  sudo pacman -S uv
EOF
  return 1 2>/dev/null || exit 1
fi

export UV_BIN
