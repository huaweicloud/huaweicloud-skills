# Acceptance Criteria

## Overview
This document defines the quality standards and acceptance criteria for the alarm-reduce-noise skill. All criteria must be met before the skill is considered production-ready.

## Functional Acceptance Criteria

### 1. Environment & Dependencies

| Criterion | Description | Verification |
|-----------|-------------|--------------|
| AC-1.1 | Python version >= 3.10 | `check_env.py` outputs `[OK] Python version` |
| AC-1.2 | All Python dependencies installed | `check_env.py` outputs `[OK] All dependencies installed` |
| AC-1.3 | hcloud CLI available | `check_env.py` outputs `[OK] hcloud CLI found` |
| AC-1.4 | AK/SK configured via environment variables | `alarm.py` runs without auth errors |

### 2. Alarm Data Collection

| Criterion | Description | Verification |
|-----------|-------------|--------------|
| AC-2.1 | CES alarm histories fetched for all regions | `alarm_result.json` contains entries for each region in 关键资源标记表 |
| AC-2.2 | CES alarm rules fetched | `ces_alarm_rules.json` contains rule list per region |
| AC-2.3 | AOM alarm rules fetched | `ces_alarm_rules.json` includes AOM rules (merged with CES) |
| AC-2.4 | Multi-region format used | `alarm_result.json` has `{"alarms": {region_name: {...}}}` structure |
| AC-2.5 | Time range parameter respected | `--days 7` collects alarms from last 7 days only |
| AC-2.6 | Project ID auto-fetched per region | No manual Project ID configuration required |

### 3. Alarm Analysis

| Criterion | Description | Verification |
|-----------|-------------|--------------|
| AC-3.1 | Core resource filtering works | Only alarms for resources with 是否核心业务="是" are analyzed |
| AC-3.2 | Health score calculated (0-100) | Report shows health score for each region |
| AC-3.3 | 告警治理 dimension analyzed | Report includes routing, dedup, suppression, silence sections |
| AC-3.4 | 告警收敛 dimension analyzed | Report includes alarm storm, temporal correlation sections |
| AC-3.5 | 告警关联 dimension analyzed | Report includes root cause, derived alarm sections |
| AC-3.6 | 长久未恢复告警 analyzed | Report includes 7/14/30/90 day unresolved alarm levels |
| AC-3.7 | TOP10 high-frequency alarms listed | Only core resource alarms included |
| AC-3.8 | Daily alarm trend present | Report shows per-day alarm count trend |

### 4. Report Generation

| Criterion | Description | Verification |
|-----------|-------------|--------------|
| AC-4.1 | HTML report generated | `alarm-noise-report.html` exists and opens in browser |
| AC-4.2 | Region switcher works | Dropdown at report top, switching updates all sections |
| AC-4.3 | 降噪建议 included | Suggestions sorted by priority (高/中/长期) |
| AC-4.4 | Report is self-contained | No external dependencies (CSS/JS inline) |

## Technical Acceptance Criteria

### 1. Multi-region Support

| Criterion | Description |
|-----------|-------------|
| AC-T1.1 | Regions auto-extracted from 关键资源标记表.xlsx "Region" column |
| AC-T1.2 | hcloud CLI uses `--cli-region` for region-specific API calls |
| AC-T1.3 | Project ID fetched per region via `hcloud IAM KeystoneListProjects` |
| AC-T1.4 | HTML report provides searchable region switcher dropdown |

### 2. Authentication

| Criterion | Description |
|-----------|-------------|
| AC-T2.1 | AK/SK read from `HW_ACCESS_KEY` / `HW_SECRET_KEY` env vars |
| AC-T2.2 | Security token supported via `HW_SECURITY_TOKEN` |
| AC-T2.3 | Project ID override via `HW_PROJECT_ID` env var |
| AC-T2.4 | No credentials hardcoded in source code |

### 3. Error Handling

| Criterion | Description |
|-----------|-------------|
| AC-T3.1 | Missing Excel file produces clear error message |
| AC-T3.2 | API failures (CES/AOM) are logged and don't crash the pipeline |
| AC-T3.3 | Empty alarm histories result in valid report (0 alarms), not a crash |
| AC-T3.4 | Region with no alarms handled gracefully in multi-region report |

### 4. Workspace Management

| Criterion | Description |
|-----------|-------------|
| AC-T4.1 | Timestamped workspace directory created automatically |
| AC-T4.2 | `ALARM_REDUCE_NOISE_WORKSPACE_DIR` env var enables shared directory across scripts |
| AC-T4.3 | Multiple runs don't overwrite (timestamped dirs) |

## Output Quality Acceptance Criteria

### 1. HTML Report Quality
- Region switcher with search filter at the top
- Health score displayed prominently with 5-dimension breakdown
- Alarm overview statistics (total, by level, by service)
- TOP10 high-frequency alarms table (core resources only)
- Daily alarm trend visualization
- Four analysis dimension sections with detailed findings
- 降噪建议 sorted by priority (高/中/长期) with actionable recommendations
- All sections update when switching regions

### 2. Data Accuracy
- Health score = weighted sum of 5 dimensions (告警总量, 严重告警占比, 告警收敛率, 长久未恢复告警, 趋势)
- Only core resource alarms counted in analysis (filtered by 关键资源标记表)
- Alarm storm threshold: >30 times = high risk, >100 times = severe
- Unresolved alarm levels: >7d (info), >14d (info), >30d (warning), >90d (danger)

### 3. Analysis Depth
- 告警治理: covers AOM降噪链 4环节 (路由分组, 去重, 抑制, 静默)
- 告警收敛: alarm storm identification with frequency threshold
- 告警关联: root cause analysis with derived alarm suppression suggestions
- 长久未恢复: time-tiered classification with actionable remediation

## Compliance Acceptance Criteria

### 1. Huawei Cloud Standards
- Uses official hcloud CLI for CES and AOM API calls
- Follows Huawei Cloud region naming conventions (cn-north-4, cn-east-3, etc.)
- Supports multi-region collection from 关键资源标记表

### 2. Security Standards
- Read-only operations only — no resource creation, modification, or deletion
- AK/SK never logged or written to output files
- `.env` file gitignored, credentials via environment variables preferred
- No sensitive data in generated reports

## Acceptance Testing Process

### Pre-Acceptance Checklist
- [ ] Python 3.10+ installed
- [ ] hcloud CLI installed and configured
- [ ] AK/SK with required IAM permissions configured (see iam-policies.md)
- [ ] `assets/关键资源标记表.xlsx` with valid "Region" and "是否核心业务" columns
- [ ] `requirements.txt` dependencies installed

### Acceptance Test Execution
1. Run `python3 scripts/check_env.py` — verify all prerequisites met
2. Run `python3 scripts/alarm.py --days 7` — verify alarm data collected
3. Run `python3 scripts/analyze_alarm.py` — verify HTML report generated
4. Open report in browser — verify all sections render correctly
5. Switch regions in report — verify data updates
6. Verify all functional criteria (AC-1.x through AC-4.x)
7. Verify all technical criteria (AC-T1.x through AC-T4.x)
8. Confirm no cloud resources were modified (read-only)

## References

- verification-method.md: Step-by-step verification procedures
- iam-policies.md: Required permissions for acceptance testing
- cli-installation-guide.md: hcloud CLI installation guide
- alarm-analysis.md: Detailed analysis methodology
