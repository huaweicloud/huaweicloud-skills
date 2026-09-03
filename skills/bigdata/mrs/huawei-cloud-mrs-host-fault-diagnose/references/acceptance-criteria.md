# Acceptance Criteria - MRS Fault Diagnosis

This document defines the pass/fail criteria for testing the MRS fault diagnosis skill. It covers SKILL.md format, command format, parameter validation, output format, error handling, and security.

## 1. SKILL.md Format Validation

| Criterion | Pass | Fail |
|-----------|------|------|
| YAML frontmatter present | `---`-wrapped block at file top with `name`, `description`, `tags` | Missing frontmatter or required fields |
| `name` matches directory | `name: huawei-cloud-mrs-host-fault-diagnose` equals the package directory name | Mismatch |
| `description` includes trigger words | Contains "故障诊断" / "fault diagnosis" and usage scenario | Missing trigger words or scenario |
| Required sections present | Overview, Prerequisites, Command Format Standard, Workflow, Core Commands, Parameter Confirmation, Output Format, Verification Method, References, Notes | Missing any required section |
| References use relative paths | All doc links are `references/*.md`, `fault_layer/*.md`, `scenarios/*.md`, `components/*.md`, or `propagation.md`; no external URLs | External URLs in references |
| File size | Single file <= 500 lines, package <= 5MB | Exceeds limits |

## 2. Command Format Validation

### 2.1 LakeWatch Client Command

| Criterion | Pass | Fail |
|-----------|------|------|
| Correct interpreter | `python3` on Linux, `python` on Windows | Wrong interpreter for platform |
| `-a` API name present | `-a <api_name>` from the config catalog | Missing `-a` or unknown API |
| `-p` values single-quoted | `-p 'key=value'` with single quotes | Unquoted values with special chars (`[] {} \| ()`) |
| Windows `"` escaping | `"` inside `-p` values replaced with `"""` on PowerShell | Unescaped `"` causing `code:500` |
| Placeholders substituted | `<cluster_id>`, `<alarm_time>`, `<node_name>`, `<service_name>` replaced with real values | Literal placeholders executed |

### 2.2 Correct vs Wrong Examples

```bash
# Correct (Linux)
python3 lakewatch_api_client.py -a collect_alarm_log_data \
  -p 'cluster_id=b46a9c34-c2b4-4208-9a3b-89581764bff6' \
  -p 'alarm_time=2026/06/11 16:00:32 GMT+08:00' \
  -p 'keywords=["ERROR","Exception"]' \
  -p 'log_type=local'

# Wrong (Linux): unquoted value with special chars
python3 lakewatch_api_client.py -a collect_alarm_log_data -p keywords=["ERROR","Exception"]

# Correct (Windows PowerShell)
python lakewatch_api_client.py -a collect_alarm_log_data -p 'keywords=["""ERROR"""]'

# Wrong (Windows): unescaped "
python lakewatch_api_client.py -a collect_alarm_log_data -p 'keywords=["ERROR"]'
```

## 3. Parameter Validation

| Parameter | Rule | Pass | Fail |
|-----------|------|------|------|
| `alarm_time` | `yyyy/MM/dd HH:mm:ss GMT+X:XX` | `2026/06/11 16:00:32 GMT+08:00` | `2026-06-11 16:00:32` |
| `log_directory` | Must start with `/var/log/` | `/var/log/Bigdata/controller` | `/tmp/logs` |
| `log_file_name` | No path separators | `exe.log*` | `dir/file.log` |
| `log_type` | Enum: `local` / `hdfs` | `local` | `syslog` |
| `keywords` | JSON array | `["ERROR"]` | `ERROR` |
| `target_url` | Must NOT start with `/` | `api/v2/clusters` | `/api/v2/clusters` |

## 4. Output Format Validation

| Criterion | Pass | Fail |
|-----------|------|------|
| Diagnosis result table present | Contains diagnosis time, cluster ID, faulty component, faulty node | Missing fields |
| Diagnosis process section present | Contains step-by-step results (instance status, quick log scan, host troubleshooting, detailed investigation) | Missing section |
| Propagation path present | Contains root cause -> propagation -> symptom | Missing propagation path |
| Root cause section present | Contains root cause layer + root cause type | Root cause missing |
| Repair suggestion table present | Contains priority, operation, description, needs-user-confirmation | Missing table |
| All repair actions flagged "Yes" | Every repair row has needs-user-confirmation = Yes | Any repair marked as auto-execute |
| No fabricated data | All conclusions cite actual command output | Invented metrics or log content |

## 5. Error Handling Validation

| Scenario | Pass | Fail |
|----------|------|------|
| Command fails | Skip current check, continue other checks | Abort entire diagnosis |
| Component config missing | Tell user to copy `_template.md` and create `<service_name>.md` | Fabricate component info |
| Missing cluster_id | Ask user to provide, stop execution | Proceed with guesses |
| Authentication error (401) | Read iam-policies.md, guide user, pause | Retry blindly or expose credentials |
| `code:500` on Windows | Detect quoting issue, escape `"` as `"""` | Report as server bug |
| Alarm skill not available | Inform user when alarm diagnosis is referenced but skill not present; offer generic flow | Silently skip |
| Cross-skill dependency declared | SKILL.md Prerequisites section 4 declares dependency on huawei-cloud-mrs-host-alarm-diagnose | No dependency declaration found |

## 6. Security Validation

| Criterion | Pass | Fail |
|-----------|------|------|
| No plaintext password | `grep -rn "password" scripts/lakewatch_api_config.yaml` shows only `encrypted_password` ciphertext | Plaintext password present |
| No AK/SK in files | `grep -rni "access-key\|secret-key\|AK.*SK" scripts/ references/ SKILL.md` returns no credentials | Credentials found |
| Password not in conversation | Skill uses `--encrypt-password` interactive flow | Skill asks user to paste plaintext password |
| Read-only operations | All commands are query/collect; no start/stop/modify/delete | Any mutating command |
| Repair requires confirmation | All repair rows marked needs-user-confirmation = Yes | Skill executes repair directly |

## 7. Diagnosis Flow Validation

| Criterion | Pass | Fail |
|-----------|------|------|
| Entry routing correct | service_name only -> service fault; node_name only -> host fault; both -> instance fault | Wrong entry selected |
| Progressive investigation | Quick log scan first, detailed investigation only when no conclusion | Always starts with detailed investigation |
| Component config loaded first | Reads `components/<service_name>.md` before running commands | Fabricates component info |
| No self-inferred log paths | Log paths come from component config or knowledge base | Invents log paths |
| Reflects on completeness | After checks, confirms root cause or re-checks missed steps | Stops without confirming |
| Variable placeholders substituted | Real values used | Hardcoded placeholders executed |
| Propagation chain traced | Outputs root cause -> propagation -> symptom when applicable | Skips propagation analysis |

## Test Summary

A skill release passes when ALL sections 1-7 pass. Any single Fail criterion blocks release.
