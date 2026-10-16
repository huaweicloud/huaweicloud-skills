# Verification Method

## 1. Environment Verification

Before running the skill, verify that all prerequisites are met:

```bash
# Check Python version (>= 3.9 required)
python3 --version

# Check hcloud CLI availability
hcloud --version

# Check hcloud authentication
hcloud configure list

# Check Python dependencies
pip install --dry-run -r requirements.txt

# Smoke test: query OA service API connectivity
hcloud OA ShowCheckItemList --cli-region=cn-north-4 --limit=1
```

## 2. Feature Verification

### Step 1: Environment Check

| Check | Command | Expected |
|-------|---------|----------|
| Python >= 3.9 | `python3 --version` | Version >= 3.9.x |
| hcloud installed | `hcloud --version` | Version >= 7.2.2 |
| hcloud configured | `hcloud configure list` | Shows valid AK/SK profile |
| Dependencies | `pip install --dry-run -r requirements.txt` | All `already satisfied` |

### Step 2: Fetch OA Risk Inspection Results

```bash
python3 scripts/oa_risk_inspection.py \
  --region cn-north-4
```

**Verify:**
- Output JSON file exists at `oa_risk_inspection_results_<ts>.json`
- JSON contains `meta` and `results` arrays
- No error messages in stdout/stderr

### Step 3: Fetch Config Resource Compliance Results

```bash
python3 scripts/config_compliance_inspection.py \
  --cli-region cn-north-4
```

**Verify:**
- Output JSON file exists at `config_compliance_inspection_results_<ts>.json`
- JSON contains `meta`, `assignments`, `statistics`, and `failures` arrays
- No error messages in stdout/stderr

### Step 4: Fetch SecMaster Baseline Check Results

```bash
python3 scripts/secmaster_baseline_inspection.py \
  --region_id cn-north-4
```

**Verify:**
- Output JSON file exists at `secmaster_baseline_inspection_results_<ts>.json`
- Stats file exists at `secmaster_baseline_inspection_stats_<ts>.json`
- No error messages in stdout/stderr

### Step 5: Convert Raw Results

```bash
python3 scripts/merge_inspection_results.py \
  --oa-file oa_risk_inspection_results_<ts>.json \
  --config-file config_compliance_inspection_results_<ts>.json \
  --secmaster-file secmaster_baseline_inspection_results_<ts>.json
```

**Verify:**
- Merged JSON file exists at `merge_inspection_results_<ts>.json`
- Merged `results` contain OA / Config / SecMaster records with `source` field
- No error messages in stdout/stderr

### Step 6: Generate Report

```bash
python3 scripts/merge_report_generator.py \
  --input merge_inspection_results_<ts>.json \
  --output-dir analysis
```

**Verify:**
- HTML report exists at `analysis/<ts>/merge_inspection_report_<ts>.html`
- XLSX report exists at `analysis/<ts>/merge_inspection_report_<ts>.xlsx`
- HTML report opens in a browser and renders charts
- XLSX report opens in Excel and contains overview + detail sheets

### Step 7: Clean Up Temporary Files

**Verify:**
- The 5 temporary JSON files from Steps 2-5 are deleted
- Final report artifacts (HTML / XLSX) remain in place

### Step 8: Workflow Summary

**Verify:**
- Completion table shows step/status/notes for all 8 steps
- Final artifact absolute paths are listed

## 3. Report Content Validation

| Check | Method |
|-------|--------|
| Risk resource count accuracy | For each risk item, `resource_count` equals the resource detail list length (no `risk_resource_count` field dependency) |
| Hint classification | Quota placeholder items (e.g. "服务配额不足") appear in the hint block, not the risk table |
| Health score present | Open HTML, verify summary cards are displayed |
| Charts rendered | Verify 5 charts (status, product, source, dimension, trend) are visible |
| Risk item details | Click an item name, verify resource details expand |
| XLSX sheets | Verify overview sheet + one detail sheet per risk item |

## 4. Compliance Checks (Local, Offline)

| Check | Command |
|-------|---------|
| SKILL.md exists | `test -f SKILL.md && echo OK` |
| Frontmatter valid | `grep -E '^(name\|description\|tags):' SKILL.md` |
| No hardcoded credentials | `grep -rEn '(AK[A-Z]* *[:=] *[A-Z0-9]{16,}\|secret ?key *[:=])' .` |
| references/ has required files | `ls references/cli-installation-guide.md references/iam-authentication-guide.md references/verification-method.md references/acceptance-criteria.md` |

## 5. Acceptance Gate

Run the full workflow end-to-end against a non-production account:
1. Environment check passes — all prerequisites met
2. OA / Config / SecMaster data fetched — JSON outputs non-empty with valid structure
3. Raw results merged — merged JSON contains three sources
4. Report generated — both HTML and XLSX files created and valid
5. Risk count correct — every risk item count equals its resource list length
6. Cleanup — temporary JSON files removed after report generation
