# Verification Method

## 1. Prerequisites verification

```bash
hcloud version                   # >= 3.2.0
obsutil version                  # >= 5.5.0
hcloud obs ls -limit=1           # credentials + endpoint OK
```

## 2. Read-only verification (R3 actions, live)

```bash
# TC-01: list lifecycle rules
hcloud obs lifecycle obs://{bucket} -method=get
# expect: {"Rules": [...]} JSON, exit 0

# TC-02: get rule by ID
hcloud obs lifecycle obs://{bucket} -method=get -localfile=/tmp/rules.json
python3 -c "import json;c=json.load(open('/tmp/rules.json'));print([r for r in c['Rules'] if r['ID']=='{rule_id}'])"
# expect: the rule object printed

# TC-03: list objects
hcloud obs ls obs://{bucket} -limit=10 -s
# expect: object keys + LastModified + size

# TC-04: bucket stat (for cost/diagnosis)
hcloud obs stat obs://{bucket}

# TC-05: diagnose
python3 scripts/obs_lifecycle_analyzer.py diagnose --bucket {bucket} --limit 100
# expect: structured findings (rule state, prefix match, age check, overlaps)

# TC-06: cost
python3 scripts/obs_lifecycle_analyzer.py cost --bucket {bucket} --limit 100
# expect: per-rule transition plan + monthly cost comparison

# TC-07: preview (dry-run)
python3 scripts/obs_lifecycle_analyzer.py preview --bucket {bucket} --prefix {prefix} --days 30
# expect: affected object list + count + total size; NO mutation performed
```

## 3. Mutation verification (R2/R1 actions — preview + user confirmation required)

```bash
# TC-08: create rule — dry-run first
python3 scripts/obs_lifecycle_analyzer.py preview --bucket {bucket} --prefix logs/ --days 30
# user confirms
python3 scripts/obs_lifecycle_analyzer.py create-rule \
  --bucket {bucket} --rule-id verify-create-01 --prefix logs/ --action expire --days 30
hcloud obs lifecycle obs://{bucket} -method=get   # verify rule present

# TC-09: update rule
python3 scripts/obs_lifecycle_analyzer.py update-rule \
  --bucket {bucket} --rule-id verify-create-01 --days 60
hcloud obs lifecycle obs://{bucket} -method=get   # verify days == 60

# TC-10: delete rule (single rule, restores prior state)
python3 scripts/obs_lifecycle_analyzer.py delete-rule --bucket {bucket} --rule-id verify-create-01
hcloud obs lifecycle obs://{bucket} -method=get   # verify rule gone, others intact
```

**Restore rule:** after mutation tests, restore the bucket's original lifecycle configuration captured before testing (get → save → put back), so no test residue remains.

## 4. Security verification

```bash
# No hardcoded credentials in the skill
grep -rniE "access[_-]?key[[:space:]]*=[[:space:]]*['\"]?[A-Z0-9]{8,}" skills/storage/obs/huawei-cloud-obs-lifecycle-management/ || echo "clean"
```

## 5. Structure compliance

```bash
bash scripts/validate-skill.sh skills/storage/obs/huawei-cloud-obs-lifecycle-management
```

Expected: no FAIL on Critical checks (SKILL.md exists, frontmatter, name match, description + triggers, no version, required sections, iam-policies.md, no hardcoded credentials, no cross-skill
references). Medium WARNs on obsutil-mode CLI style (lowercase service/operation, no `--cli-region`) are expected and documented in SKILL.md's KooCLI Command Format Standard.

## 6. Acceptance test cases (from acceptance-criteria.md)

| Case | Action | Expected |
|------|--------|----------|
| TC-01 | list rules | JSON Rules[] returned |
| TC-02 | get rule by id | matching rule object |
| TC-03 | list objects | keys/sizes returned |
| TC-04 | stat bucket | bucket metadata |
| TC-05 | diagnose | findings list |
| TC-06 | cost | cost comparison |
| TC-07 | preview | affected objects, no mutation |
| TC-08/09/10 | create/update/delete rule | applied + verified, config restored after test |