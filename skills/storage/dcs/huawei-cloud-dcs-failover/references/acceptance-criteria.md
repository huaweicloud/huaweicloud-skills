# Acceptance Criteria

## Functional Acceptance

### prepare Phase

| Item | Expected result | Verification |
|------|-----------------|--------------|
| Read config.json | Correctly loads region and instance_id | `python3 scripts/prepare.py` outputs config info |
| Query DCS instance | Locates target instance and fills in details (cache_mode, etc.) | Outputs instance name/status/cache_mode/AZ |
| Check IAM permissions | Outputs auth readiness / DCS permission status | Outputs permission check results |
| Generate experiment.json | File exists and format is correct | `cat experiments/experiment.json` |
| Generate iam_policy.json | File exists and format is correct | `cat experiments/iam_policy.json` |
| Generate monitoring.json | File exists and format is correct (8 CES metrics) | `cat experiments/monitoring.json` |
| Generate readiness report | HTML + Markdown report generated | `ls experiments/readiness_report.*` |
| Architecture hard-gate | ha + RUNNING + cross-AZ required items all pass | Outputs "准备就绪" |
| Risk detection | Read-only probe of nodes/load/backups and output results | prepare outputs "风险评估总览" |
| Risk assessment | Each item graded (info/unknown/warning/critical) and overall level correct | risk_assessment.json overall_level/items valid |
| Risk warning | Console + report + risk_assessment.json all present | Readiness report contains risk section |

### execute Phase

| Item | Expected result | Verification |
|------|-----------------|--------------|
| Load config | Correctly reads 3 config files | Outputs experiment name and instance info |
| Pre-check | Instance exists, ha type, RUNNING | Outputs "安全检查: 全部通过" |
| IAM permission recheck | Reads iam_policy.json, rechecks DCS read and failover permissions | Outputs `iam_dcs_access: ✓` and `iam_failover_capable: ✓` |
| Risk warning display | Reads risk_assessment.json and outputs risk hints | Outputs "[风险提示] 总体风险等级: ..." |
| Risk blocking | Blocks failover by default when critical items exist | With faked critical items, execute without `--force` should exit with prompt |
| Forced drill | `--force` skips blocking | `execute --force` proceeds (manual confirmation semantics) |
| Instance consistency check | Blocks when risk_assessment.json doesn't match current instance | With faked instance_id, execute should exit without triggering failover |
| Real-time recheck before failover | Rechecks instance status and node health before failover | execute outputs `[实时复核]` and blocks on critical anomaly |
| Execute failover | ChangeMasterStandby call succeeds | Outputs failover command submitted successfully |
| Poll for completion | Master-slave role swap completes | Outputs "倒换完成" and duration |
| Consistency check | Master node moved to slave AZ / key count | execution_result.json contains consistency_check |
| Three-dimensional scoring | failover/data/business -> weighted total | execution_result.json contains scores |
| Save result | execution_result.json generated | File exists and format is correct |

### report Phase

| Item | Expected result | Verification |
|------|-----------------|--------------|
| Read execution result | Correctly loads execution_result.json | No ERROR output |
| Generate HTML report | Report file generated | `ls templates/failover_report_*.html` |
| Report content complete | Contains all sections | Open in browser to check |
| Report standalone | Inline CSS, no external dependencies | Browser displays correctly offline |
| HTML encoding | External data escaped via html.escape | Check report.py / prepare.py esc()/_esc() covers all external data insertion points |

### Unified Entry run.py

| Item | Expected result | Verification |
|------|-----------------|--------------|
| One-click full pipeline | prepare->execute->report runs in order | `python3 scripts/run.py` |
| Phase-by-phase | Only runs specified phase | `python3 scripts/run.py --phase prepare` |
| Forced drill | --force skips critical risk blocking | `python3 scripts/run.py --force` |

## Report Content Acceptance

The generated HTML report must contain the following sections:

- [ ] Result banner (success/timeout status, failover duration)
- [ ] Instance info (name, ID, engine, capacity, time)
- [ ] Safety checks (5 items: instance exists / RUNNING / ha type / IAM read / IAM failover)
- [ ] Master-slave topology change (before/after comparison)
- [ ] Failover timeline (polling records)
- [ ] Data consistency check

## Security Acceptance

- [ ] config.json contains no plaintext AK/SK
- [ ] Instance status must be RUNNING before failover
- [ ] Instance must be ha (master-slave) type before failover
- [ ] execute phase performs real failover (no dry-run mode)
- [ ] Critical risks block failover by default; --force is explicit override after manual confirmation
- [ ] Report does not leak sensitive credentials
- [ ] All external data from cloud APIs in HTML report is HTML-entity-encoded (html.escape) to prevent stored XSS
