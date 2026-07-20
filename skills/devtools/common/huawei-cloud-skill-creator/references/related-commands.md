# Related Commands — Huawei Cloud Skill Creator v2

## CLI Commands

```bash
# Validate generated skill
bash scripts/validate-skill.sh {skill-path}

# Test generated skill commands
bash scripts/test-cli-commands.sh {skill-path} --executor cli
bash scripts/test-cli-commands.sh {skill-path} --executor sdk
bash scripts/test-cli-commands.sh {skill-path} --executor api
```

## SDK Methods

```python
# Check SDK availability
from huaweicloudsdkbss.v2 import BssClient

# Generate dataflow diagram
bash scripts/generate-dataflow-diagram.sh {skill-path}
```

## Phase Summary Helpers

```bash
# Check all phase summaries
for i in 1 2 3 4 5 6; do
  if [ -f "phase-${i}-summary.json" ]; then
    echo "✅ Phase $i: $(cat phase-${i}-summary.json | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('summary',''))" 2>/dev/null)"
  else
    echo "❌ Phase $i: not completed"
  fi
done
```

## hcloud CLI Service Check

```bash
# Check if a service is supported
hcloud --help | grep -i "{service_name}"

# List all available services
python3 -c "
import json, os
with open(os.path.expanduser('~/.hcloud/metaRepo/services_en.json')) as f:
    data = json.load(f)
for item in data.get('items', []):
    s = item.get('Service', {})
    print(f\"{s.get('Text',''):20} {s.get('Description','')}\")
"
```
