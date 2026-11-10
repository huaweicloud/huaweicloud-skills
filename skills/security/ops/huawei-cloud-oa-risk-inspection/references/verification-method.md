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

# Smoke test: query OA service API connectivity (OA is only available in cn-southwest-2)
hcloud OA ShowCheckItemList --cli-region=cn-southwest-2 --limit=1
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
python3 scripts/oa_risk_inspection.py
```

The OA region is the script constant `cn-southwest-2`; the script has no region option.

**Verify:**
- Output JSON file exists at `oa_risk_inspection_results_<ts>.json`
- JSON contains `meta` and `results` arrays
- No error messages in stdout/stderr

### Step 3: Fetch Config Resource Compliance Results

```bash
python3 scripts/config_compliance_inspection.py
```

The hcloud region is the script constant `cn-north-4`; the script has no region option.

**Verify:**
- Output JSON file exists at `config_compliance_inspection_results_<ts>.json`
- JSON contains `meta`, `assignments`, `statistics`, and `failures` arrays
- No error messages in stdout/stderr

### Step 4: Fetch SecMaster Baseline Check Results

```bash
python3 scripts/secmaster_baseline_inspection.py
```

No region parameter: the script scans the region list built into it.

**Verify:**
- Output JSON file exists at `secmaster_baseline_inspection_results_<ts>.json`
- Stats file exists at `secmaster_baseline_inspection_stats_<ts>.json`
- The full-results JSON contains `meta`, `workspaces`, and `data`; `meta.regions` has one entry per built-in region and `meta.instances` records every instance with its status
- The log states the scanned region count and the verified / unverified split at startup
- Exit code is `0` when at least one instance was inspected, `1` when every verified region was reachable and the account holds no instance, `2` when the scan is incomplete

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
- `meta.sources` lists all three sources with status `ok` when every input was provided
- Omitting one `--*-file` option still produces a merged file, with that source's `meta.sources` status `missing`

**Scoped run — check the support set first, then add the whitelist to both Step 2 and Step 5:**

```bash
python3 scripts/cloud_service_filter.py --cloud-services "ECS,CCE"
```

**Verify (support-set probe):**
- The command prints JSON with `requested` / `supported` / `unsupported` / `services` / `available`
- `--cloud-services "ECS,XYZ"` reports `ecs` under `supported` and `XYZ` under `unsupported`, exit code `0`
- `--cloud-services "XYZ"` reports an empty `supported` and lists every inspectable code under `available`
- Pass only the `supported` services on to Step 2 and Step 5

```bash
python3 scripts/oa_risk_inspection.py --cloud-services "ECS,CCE"
python3 scripts/merge_inspection_results.py \
  --oa-file oa_risk_inspection_results_<ts>.json \
  --config-file config_compliance_inspection_results_<ts>.json \
  --secmaster-file secmaster_baseline_inspection_results_<ts>.json \
  --cloud-services "ECS,CCE"
```

**Verify:**
- OA log reports fewer triggered check items than the full list, and `meta.cloud_service_filter` records `requested` / `resolved` / `services`
- `meta.cloud_service_filter.excluded_by_service` and `excluded_unclassified` carry per-source counts
- `meta.counts.converted_total` equals the length of `results`
- `results` contains only the requested services; Config / SecMaster records without any service value are absent and counted under `excluded_unclassified`
- `--cloud-services zzz` exits non-zero, writes no merged file, and logs the service codes present in the input — an unlisted service no longer falls back to its own literal code
- A record whose service value is a historical spelling (e.g. `hecs`, `fgs`, `vpnaas`) is matched by the alias of its canonical service (`ecs`, `functiongraph`, `vpn`)
- Omitting `--cloud-services` from the merge while the OA input records one adopts the recorded scope and logs a WARNING

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
- Full-tenant run: the directory holds exactly the two files above, and the subdirectory name matches both file names
- Scoped run: `analysis/<ts>/merge_inspection_report_<ts>_risk_items.json` also exists; its `items` match the HTML risk table and Excel overview, `totals.items` equals the item count, `totals.resources` equals the total resource entries, and it contains no report path, archive path or account ID

### Step 7: Archive Deliverables and Clean Up Temporary Files

```bash
python3 scripts/archive_artifacts.py --report-dir analysis/<ts>
```

**Verify:**
- HTML report and XLSX report exist under
  `~/.hcloud-oa-risk/<ts>/`
- Scoped run: `merge_inspection_report_<ts>_risk_items.json` is archived alongside them
- `archive_manifest.json` in that directory lists exactly the archived files under `archived`
- The merged JSON is not present in the archive directory, and no other JSON is archived
- The 5 temporary JSON files from Steps 2-5 (including the merged JSON) are deleted; the
  risk-item JSON is never in that deletion list
- `analysis/<ts>/` is removed only when it held no other file
- Exit code is 0; when a file fails to archive, exit code is 1 and the source file remains

### Step 8: Workflow Summary

**Verify:**
- Completion table shows No./Step/Status/Remarks for all 8 steps
- The archive directory and archived artifact absolute paths are listed
- Unarchived deliverables are marked "not archived" with the local path and reason
- Blacklist-filtered items appear as one line with the Config and SecMaster counts
- A source with no data is marked "无数据" in Remarks, never as "0 risks"
- No per-source breakdown section and no list of deleted temporary files
- Scoped run: the risk-item JSON is presented (item-level table, resource details expanded
  while `totals.items` <= 20 and `totals.resources` <= 50, otherwise the JSON path is given),
  the covered `services` are stated, services that matched no record are called out, the
  "已匹配 N 条检查记录，未发现风险项" wording is used when `totals.items` is 0, and the
  unclassified exclusion count appears in one line
- Full-tenant run: no risk-item table is presented

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
