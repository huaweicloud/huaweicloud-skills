#!/bin/bash
# e2e_profile_simulator.sh - Compile + SimulationRun + msprof op simulator PerformanceCollection
# Usage: bash scripts/e2e_profile_simulator.sh <operator_dir> [batch_size] [num_class]
# accordingdepend: compile_simulator.sh bitin operator_dir under
# Notes: Simulation Requireslinkconnect simulator library, compile_simulator.sh Automatichandlemanage

set -e

OPERATOR_DIR="${1:?Error: operator_dir is required}"
BATCH_SIZE="${2:-128}"
NUM_CLASS="${3:-1024}"

cd "$OPERATOR_DIR"

echo "===== Steps 1: Clean Up Old msprof Output ====="
rm -rf OPPROF_*

echo "===== Steps 2: CompileSimulationVersion ====="
bash compile_simulator.sh "$BATCH_SIZE" "$NUM_CLASS"

echo ""
echo "===== Steps 3: Execute msprof op simulator SimulationPerformanceCollection ====="
echo "commandcommand: msprof op simulator --soc-version=Ascend910B1 ./run.fatbin $BATCH_SIZE $NUM_CLASS"
msprof op simulator --soc-version=Ascend910B1 ./run.fatbin "$BATCH_SIZE" "$NUM_CLASS"

echo ""
echo "===== Steps 4: searchfindGenerateofPerformanceDataDirectory ====="
PROFILE_DIR=$(ls -d OPPROF_* 2>/dev/null | head -1)
if [ -n "$PROFILE_DIR" ]; then
    echo "PerformanceDataDirectory: $OPERATOR_DIR/$PROFILE_DIR"
    echo "relatedkeyfilecolumntable: "
    ls "$PROFILE_DIR"/
else
    echo "errorerror: notfindto OPPROF_* Directory, PerformanceCollectioncanabilitylossfailure"
    exit 1
fi
