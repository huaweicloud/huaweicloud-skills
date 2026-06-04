#!/bin/bash
# e2e_compile_run.sh - Compile and RunOperator (Baseline Version) 
# Usage: bash scripts/e2e_compile_run.sh <operator_dir> [batch_size] [num_class]
# accordingdepend: compile_run.sh bitin operator_dir under

set -e

OPERATOR_DIR="${1:?Error: operator_dir is required}"
BATCH_SIZE="${2:-128}"
NUM_CLASS="${3:-1024}"

cd "$OPERATOR_DIR"

echo "===== Steps 1: CompileOperator ====="
bash compile_run.sh "$BATCH_SIZE" "$NUM_CLASS"

echo ""
echo "===== Steps 2: VerificationRun Results ====="
echo "CheckOutputmiddleiswhetherPackagecontain 'precision pass'..."
