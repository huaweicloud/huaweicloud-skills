#!/usr/bin/env bash

set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

for dir in "$script_dir"/*/; do
  if [[ ! -f "${dir}versions.tf" ]]; then
    continue
  fi

  echo "=== Validating ${dir} ==="
  terraform -chdir="$dir" fmt -check -recursive
  terraform -chdir="$dir" init -backend=false
  terraform -chdir="$dir" validate
done
