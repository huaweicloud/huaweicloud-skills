#!/bin/bash
# Compare Terraform plan resources against original RMS inventory
# Usage: ./scripts/compare_resources.sh <plan_file> <rms_json_file>
#
# Identifies gaps between what Terraform manages and what exists in the cloud.

PLAN_FILE="${1:-/tmp/tf_plan.txt}"
RMS_FILE="${2:-/tmp/rms_all_resources.json}"

if [ ! -f "$PLAN_FILE" ] || [ ! -f "$RMS_FILE" ]; then
  echo "ERROR: Plan file or RMS file not found"
  exit 1
fi

python3 -c "
import json, re

# Parse Terraform plan — extract 'will be created' resources
tf_resources = []
with open('$PLAN_FILE') as f:
    for line in f:
        m = re.match(r'\s*# (\S+) will be created', line)
        if m:
            tf_resources.append(m.group(1))

# Parse RMS inventory
with open('$RMS_FILE') as f:
    data = json.load(f)
rms_resources = data.get('resources', [])

from collections import Counter
rms_counts = Counter()
for r in rms_resources:
    key = f'{r[\"provider\"]}.{r[\"type\"]}'
    rms_counts[key] += 1

tf_counts = Counter()
for r in tf_resources:
    # Extract resource type (e.g., huaweicloud_vpc from huaweicloud_vpc.poc)
    parts = r.split('.')
    if len(parts) >= 2:
        tf_counts[parts[0]] += 1

print('=== Original Resources (RMS) ===')
total_rms = sum(rms_counts.values())
for k, v in sorted(rms_counts.items()):
    print(f'  {k}: {v}')
print(f'  TOTAL: {total_rms}')

print()
print('=== Terraform Resources (Plan) ===')
total_tf = sum(tf_counts.values())
for k, v in sorted(tf_counts.items()):
    print(f'  {k}: {v}')
print(f'  TOTAL: {total_tf}')

print()
print('=== Auto-created (correctly excluded) ===')
auto_created = {
    'cce.nodes': 'Managed by CCE node pool',
    'gaussdb.nodes': 'Auto-created by GaussDB instance',
    'dcs.node': 'Auto-created by DCS instance',
    'dms.kafka_nodes': 'Auto-created by Kafka instance',
    'dms.rabbitmq_nodes': 'Auto-created by RabbitMQ instance',
    'evs.volumes': 'Managed by ECS/CCE parent',
    'hss.agents': 'Runtime component, not infrastructure',
}
for k, v in auto_created.items():
    if k in rms_counts:
        print(f'  {k}: {rms_counts[k]} ({v})')

print()
print('=== Summary ===')
auto_count = sum(rms_counts.get(k, 0) for k in auto_created)
print(f'  Original: {total_rms}')
print(f'  TF managed: {total_tf}')
print(f'  Auto-created (excluded): {auto_count}')
print(f'  Coverage: {(total_tf + auto_count) / total_rms * 100:.1f}%')
"
