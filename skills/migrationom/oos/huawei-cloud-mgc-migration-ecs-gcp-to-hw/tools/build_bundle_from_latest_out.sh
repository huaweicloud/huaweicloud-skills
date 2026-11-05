#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
REPO_DIR="$(cd "${SKILL_DIR}/../.." && pwd)"
OUT_DIR="${REPO_DIR}/out"
BUNDLES_DIR="${SKILL_DIR}/bundles"

if [[ $# -ge 1 ]]; then
  BUNDLE_NAME="$1"
else
  BUNDLE_NAME="$(date +%Y-%m-%d)-migration-bundle"
fi

TARGET_DIR="${BUNDLES_DIR}/${BUNDLE_NAME}"
mkdir -p "${TARGET_DIR}"

required_files=(
  "migration_result.json"
  "precheck_task_cleanup.json"
  "postcheck_network.json"
  "task_poll_latest.json"
)

for f in "${required_files[@]}"; do
  src="${OUT_DIR}/${f}"
  if [[ -f "${src}" ]]; then
    cp -f "${src}" "${TARGET_DIR}/${f}"
  else
    echo "[WARN] missing artifact: ${src}" >&2
  fi
done

cp -f "${SKILL_DIR}/SKILL.md" "${TARGET_DIR}/SKILL.md"
cp -f "${SKILL_DIR}/references/runbook.md" "${TARGET_DIR}/runbook.md"
cp -f "${SKILL_DIR}/references/lessons-learned.md" "${TARGET_DIR}/lessons-learned.md"
cp -f "${SKILL_DIR}/references/reuse-bundle.md" "${TARGET_DIR}/reuse-bundle.md"

cat > "${TARGET_DIR}/README.md" <<EOT
# Migration Bundle: ${BUNDLE_NAME}

This bundle was generated from latest artifacts under:
- ${OUT_DIR}

Included files:
- migration_result.json
- precheck_task_cleanup.json
- postcheck_network.json
- task_poll_latest.json
- SKILL.md
- runbook.md
- lessons-learned.md
- reuse-bundle.md

Generated at: $(date '+%Y-%m-%d %H:%M:%S %z')
EOT

(
  cd "${BUNDLES_DIR}"
  tar -czf "${BUNDLE_NAME}.tar.gz" "${BUNDLE_NAME}"
)

echo "Bundle directory: ${TARGET_DIR}"
echo "Bundle archive: ${BUNDLES_DIR}/${BUNDLE_NAME}.tar.gz"
