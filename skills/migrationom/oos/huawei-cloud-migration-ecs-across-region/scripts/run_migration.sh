#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODULE_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

mkdir -p "${MODULE_DIR}/out"
python3 "${SCRIPT_DIR}/mgc_migrate.py"
