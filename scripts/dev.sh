#!/usr/bin/env bash

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"
BACKEND_HOST="${BACKEND_HOST:-127.0.0.1}"
BACKEND_PORT="${BACKEND_PORT:-8000}"
CONDA_ENV_NAME="${CONDA_ENV_NAME:-route_minds}"

find_conda() {
  local candidate

  if [[ -n "${CONDA_EXE:-}" && -x "${CONDA_EXE}" ]]; then
    printf '%s\n' "${CONDA_EXE}"
    return 0
  fi

  for candidate in \
    "conda" \
    "/opt/homebrew/Caskroom/miniconda/base/bin/conda" \
    "${HOME}/miniconda3/bin/conda" \
    "${HOME}/anaconda3/bin/conda"
  do
    if command -v "${candidate}" >/dev/null 2>&1; then
      command -v "${candidate}"
      return 0
    fi

    if [[ -x "${candidate}" ]]; then
      printf '%s\n' "${candidate}"
      return 0
    fi
  done

  return 1
}

CONDA_BIN="$(find_conda || true)"

if [[ -z "${CONDA_BIN}" ]]; then
  echo "Unable to find Conda. Install it or set CONDA_EXE before running this script." >&2
  exit 1
fi

if ! "${CONDA_BIN}" env list | awk '{print $1}' | grep -qx "${CONDA_ENV_NAME}"; then
  echo "Conda environment '${CONDA_ENV_NAME}' is not available." >&2
  echo "Create it with: ${CONDA_BIN} env create -f environment.yml" >&2
  exit 1
fi

frontend_pid=""
backend_pid=""

cleanup() {
  trap - EXIT INT TERM

  if [[ -n "${frontend_pid}" ]] && kill -0 "${frontend_pid}" >/dev/null 2>&1; then
    kill "${frontend_pid}" >/dev/null 2>&1 || true
  fi

  if [[ -n "${backend_pid}" ]] && kill -0 "${backend_pid}" >/dev/null 2>&1; then
    kill "${backend_pid}" >/dev/null 2>&1 || true
  fi

  wait "${frontend_pid}" "${backend_pid}" 2>/dev/null || true
}

trap cleanup EXIT INT TERM

echo "Starting frontend on http://127.0.0.1:${FRONTEND_PORT}"
(cd "${REPO_ROOT}" && bun --cwd apps/web dev --host 127.0.0.1 --port "${FRONTEND_PORT}") &
frontend_pid=$!

echo "Starting backend on http://${BACKEND_HOST}:${BACKEND_PORT}"
(
  cd "${REPO_ROOT}"
  "${CONDA_BIN}" run -n "${CONDA_ENV_NAME}" \
    uvicorn api.app.main:app --reload --host "${BACKEND_HOST}" --port "${BACKEND_PORT}"
) &
backend_pid=$!

wait -n "${frontend_pid}" "${backend_pid}"
