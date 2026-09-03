# Verification Method

## Specification Compliance Verification

```bash
# Validate skill structure manually (no auto-validator script in this skill)
[ -f SKILL.md ] && echo "SKILL.md exists"
```

Checks against the Huawei Cloud Skill Specification:
- SKILL.md exists with valid frontmatter
- Required sections present (Overview, Prerequisites, Workflow, Core Commands, etc.)
- No hardcoded credentials
- File naming conventions (kebab-case)
- Package size and file count limits

## Functional Testing

### CLI Priority (Default)

```bash
bash scripts/test-cli-commands.sh -s {absolute-or-relative-skill-path} -e cli
# e.g. bash scripts/test-cli-commands.sh -s /path/to/huawei-cloud-hss-query -e cli
```

### Test Flow

```
Each test case → Execute hcloud HSS command
  ├── ✅ Success → Record PASS
  └── ❌ Failure → Analyze error
       ├── Auth error → Check credentials
       ├── Param error → Fix and retry
       └── Service error → Record for investigation
```

## Manual Verification Checklist

| Check | Command | Expected |
|-------|---------|----------|
| CLI authenticated | `hcloud configure list` | Valid profile shown |
| HSS available | `hcloud HSS ListHostStatus --cli-region={region} --limit=1` | No service error |
| Host list works | `hcloud HSS ListHostStatus --cli-region={region} --limit=1` | JSON with host data |
| Vul list works | `hcloud HSS ListVulnerabilities --cli-region={region} --limit=1` | JSON with vul data |
| Baseline works | `hcloud HSS ShowBaselineOverview --cli-region={region}` | JSON with baseline stats |
| Events work | `hcloud HSS ListEventHandleHistory --cli-region={region} --limit=1 --offset=0` | JSON with event data |
| Login audit works | `hcloud HSS ListLoginCommonIp --cli-region={region}` | JSON with login IP data |
