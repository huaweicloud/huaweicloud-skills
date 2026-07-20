# Verification Method — Huawei Cloud Skill Creator v2

## Phase-by-Phase Verification

### Phase 1 Verification
```bash
# Verify phase-1-summary.json exists and contains confirmed requirements
test -f phase-1-summary.json && echo "✅ Phase 1 complete" || echo "❌ Phase 1 not done"
```

### Phase 2 Verification
```bash
# Verify CLI availability
hcloud ECS ListFlavors --cli-region=cn-north-4 --limit=1

# Verify SDK availability
python3 -c "from huaweicloudsdkbss.v2 import BssClient; print('SDK OK')"

# Verify phase-2-summary.json
test -f phase-2-summary.json && echo "✅ Phase 2 complete" || echo "❌ Phase 2 not done"
```

### Phase 3 Verification
```bash
# Validate generated skill structure
bash scripts/validate-skill.sh {skill-path}

# Verify required files exist
for f in SKILL.md references/iam-policies.md; do
  test -f "{skill-path}/$f" && echo "✅ $f" || echo "❌ $f"
done
```

### Phase 4 Verification
```bash
# Run test cases
bash scripts/test-cli-commands.sh {skill-path} --executor {cli|sdk|api}
```

### Phase 5 Verification
```bash
# Resource lifecycle test
# Create → Verify → Query → Destroy → Confirm
```

### Phase 6 Verification
```bash
# Six-phase completeness check
for i in 1 2 3 4 5 6; do
  test -f "phase-${i}-summary.json" && echo "✅ Phase ${i}" || echo "❌ Phase ${i} MISSING"
done
```

## CLI→SDK→API Fallback

| Level | Method | Command |
|-------|--------|---------|
| 1st | CLI | `hcloud {Service} {Operation} --cli-region={region}` |
| 2nd | SDK | `python3 -c "from huaweicloudsdk... import ..."` |
| 3rd | API | `curl -X {METHOD} {user-provided-endpoint}` |

## Environment Variables for AK/SK

Priority order:
1. `HUAWEI_ACCESS_KEY` / `HUAWEI_SECRET_KEY`
2. `HWC_AK` / `HWC_SK`
3. Prompt user for input
