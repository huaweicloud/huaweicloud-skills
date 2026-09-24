#!/bin/bash
# Query all resources in a region via RMS (Config/配置审计)
# Usage: ./scripts/query_all_resources.sh {region}
#
# Prerequisites:
#   - hcloud CLI configured with AK/SK
#   - HUAWEI_ACCESS_KEY and HUAWEI_SECRET_KEY environment variables set

REGION="${1:-sa-brazil-1}"
OUTPUT_FILE="${2:-/tmp/rms_resources_${REGION}.json}"

if [ -z "$HUAWEI_ACCESS_KEY" ] || [ -z "$HUAWEI_SECRET_KEY" ]; then
  echo "ERROR: HUAWEI_ACCESS_KEY and HUAWEI_SECRET_KEY must be set"
  exit 1
fi

echo "Querying all resources in region: $REGION"

# RMS ListAllResources — paginated
hcloud Config ListAllResources \
  --cli-region="$REGION" \
  --limit=200 \
  > "$OUTPUT_FILE" 2>/dev/null

if [ $? -ne 0 ]; then
  echo "ERROR: Failed to query resources"
  exit 1
fi

# Count resources
COUNT=$(python3 -c "
import json
with open('$OUTPUT_FILE') as f:
    data = json.load(f)
resources = data.get('resources', [])
print(len(resources))
" 2>/dev/null)

echo "Found $COUNT resources in $REGION"
echo "Output saved to: $OUTPUT_FILE"

# Summary by type
python3 -c "
import json
from collections import Counter
with open('$OUTPUT_FILE') as f:
    data = json.load(f)
resources = data.get('resources', [])
type_counts = Counter()
for r in resources:
    key = f'{r[\"provider\"]}.{r[\"type\"]}'
    type_counts[key] += 1
print()
print('Resource summary:')
for k, v in sorted(type_counts.items()):
    print(f'  {k}: {v}')
" 2>/dev/null
