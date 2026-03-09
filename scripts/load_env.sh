#!/usr/bin/env bash

if [[ -z "${ROOT_DIR:-}" ]]; then
  ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
fi

ENV_FILE="${ROOT_DIR}/.env"

if [[ -f "${ENV_FILE}" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "${ENV_FILE}"
  set +a
fi

resolve_repo_path() {
  local value="${1:-}"
  if [[ -z "${value}" ]]; then
    return 0
  fi
  if [[ "${value}" == "~" ]]; then
    printf '%s\n' "${HOME}"
  elif [[ "${value}" == ~/* ]]; then
    printf '%s\n' "${HOME}/${value#~/}"
  elif [[ "${value}" = /* ]]; then
    printf '%s\n' "${value}"
  else
    printf '%s\n' "${ROOT_DIR}/${value#./}"
  fi
}
