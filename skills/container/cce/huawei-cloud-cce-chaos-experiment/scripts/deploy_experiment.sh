#!/bin/bash
# ============================================================
#  Deploy CCE AZ Power Outage Experiment
# ============================================================

set -e

# Parse arguments
EXPERIMENT_DIR=""
DRY_RUN=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --experiment-dir)
            EXPERIMENT_DIR="$2"
            shift 2
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        *)
            echo "Unknown argument: $1"
            exit 1
            ;;
    esac
done

if [ -z "$EXPERIMENT_DIR" ]; then
    echo "Error: --experiment-dir is required"
    exit 1
fi

EXPERIMENT_JSON="${EXPERIMENT_DIR}/experiment.json"

if [ ! -f "$EXPERIMENT_JSON" ]; then
    echo "Error: experiment.json not found in ${EXPERIMENT_DIR}"
    exit 1
fi

# Extract experiment info
EXPERIMENT_NAME=$(python3 -c "import json; d=json.load(open('${EXPERIMENT_JSON}')); print(d.get('experiment_name',''))")
REGION=$(python3 -c "import json; d=json.load(open('${EXPERIMENT_JSON}')); print(d.get('region','cn-north-4'))")
TARGET_AZ=$(python3 -c "import json; d=json.load(open('${EXPERIMENT_JSON}')); print(d.get('az',''))")
NODE_COUNT=$(python3 -c "import json; d=json.load(open('${EXPERIMENT_JSON}')); print(d.get('targets',{}).get('count',0))")
DURATION=$(python3 -c "import json; d=json.load(open('${EXPERIMENT_JSON}')); print(d.get('actions',{}).get('shutdown',{}).get('duration_seconds',300))")
INSTANCE_IDS=$(python3 -c "
import json
d=json.load(open('${EXPERIMENT_JSON}'))
nodes = d.get('targets',{}).get('nodes',[])
ids = [n['instance_id'] for n in nodes if n.get('instance_id')]
print(','.join(ids))
")

echo "=============================================="
echo "  Deploying CCE AZ Power Outage Experiment"
echo "=============================================="
echo "  Experiment dir: ${EXPERIMENT_DIR}"
echo "  Region:         ${REGION}"
echo "  Target AZ:      ${TARGET_AZ}"
echo "  Node count:     ${NODE_COUNT}"
echo "  Duration:       ${DURATION}s"
echo "  Dry run:        ${DRY_RUN}"
echo ""

if [ "$DRY_RUN" = "true" ]; then
    echo "  [DRY RUN] Skipping deployment."
    echo "  Experiment is prepared. To execute (built into this skill):"
    echo "    python3 scripts/execute_experiment.py --experiment-dir ${EXPERIMENT_DIR}"
    exit 0
fi

echo "[1/1] Generating emergency rollback script ..."

ROLLBACK_SCRIPT="${EXPERIMENT_DIR}/rollback_experiment.sh"

cat > "$ROLLBACK_SCRIPT" << 'ROLLBACK_HEADER'
#!/bin/bash
# ============================================================
#  Emergency Rollback: CCE AZ Power Outage Experiment
#  This script starts all target nodes to restore pre-experiment state.
# ============================================================
ROLLBACK_HEADER

cat >> "$ROLLBACK_SCRIPT" << ROLLBACK_BODY

REGION="${REGION}"
INSTANCE_IDS="${INSTANCE_IDS}"

echo "=============================================="
echo "  Emergency Rollback: Starting all target nodes"
echo "=============================================="
echo "  Region: \${REGION}"
echo "  Instances: \${INSTANCE_IDS}"
echo ""

# Build hcloud native parameter flags
SERVER_PARAMS=""
IFS=',' read -ra ID_ARRAY <<< "\${INSTANCE_IDS}"
IDX=1
for id in "\${ID_ARRAY[@]}"; do
    SERVER_PARAMS="\${SERVER_PARAMS} --os-start.servers.\${IDX}.id=\${id}"
    IDX=\$((IDX + 1))
done

echo "Executing BatchStartServers ..."
hcloud ECS BatchStartServers --cli-region="\${REGION}" --cli-output=json \${SERVER_PARAMS}

echo ""
echo "  Rollback command sent. Monitor node status with:"
echo "    kubectl get nodes -w"
echo ""
echo "=============================================="
echo "  Rollback initiated."
echo "=============================================="
ROLLBACK_BODY

chmod +x "$ROLLBACK_SCRIPT"
echo "  [✓] Generated: ${ROLLBACK_SCRIPT}"

echo ""
echo "  Experiment is prepared. To execute (built into this skill):"
echo "    python3 scripts/execute_experiment.py --experiment-dir ${EXPERIMENT_DIR}"
echo "    It reads experiment.json and performs the full execution flow:"
echo "      pre-check → shutdown → monitor → wait → rollback → verify → report"
echo ""
echo "  Emergency rollback:"
echo "    ${ROLLBACK_SCRIPT}"
echo ""
echo "=============================================="
echo "  Deployment SUCCESS (local mode)"
echo "=============================================="
echo ""
echo "  ⚠️  The experiment has NOT been started."
echo "  Review the files in ${EXPERIMENT_DIR} before executing."
