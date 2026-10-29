# Risk Model (Threshold Business Semantics)

This document describes the threshold business rationale for **risk detection / assessment / warning** in `scripts/risk.py`.
The prepare phase automatically runs detection and assessment.

> 📌 **Single source of truth for thresholds**: all threshold values are authoritatively defined in the `THRESH` constant in `scripts/risk.py`.
> This document only describes the **business semantics and rationale** for each threshold; it does not duplicate threshold values.

## Four-Level Grading Definition

| Level | Meaning | Impact on flow |
|-------|---------|----------------|
| 🟢 info | Normal, no risk signal | No warning, no block |
| ⚪ unknown | Data missing (no permission / timeout / no CES data / API unsupported) | Overall level raised to "medium", prompts manual confirmation; **not auto-passed** |
| 🟠 warning | Risk signal present, recommend handling or confirmation | Overall level raised to "medium", console/report warning; no auto-block |
| 🔴 critical | Very likely to affect failover success or data safety | Overall level raised to "blocked", execute rejects by default (requires `--force`) |

**Overall level rule**: any critical item -> `blocked`; otherwise any warning or unknown item -> `medium`; otherwise -> `low`.

**Missing data rule (fail-safe design)**:
- **API unavailable / no permission / timeout / no CES data** -> marked "unknown" with explanation,
  **not downgraded to info, not auto-passed**. External data is treated as untrusted at boundaries; missing does not mean safe.
- **Never misjudge missing data as critical** — missing data is never fabricated into a critical item.

## Threshold Business Rationale

### Memory Usage (80 warning / 90 critical)
DCS is an in-memory database. After failover, the new master needs to rebuild data views; high memory pressure slows or fails recovery.
Sustained usage above 90% is a signal that "failover will very likely have problems".

### CPU Usage (70 warning / 90 critical)
During the failover window, all existing connections are dropped and business reconnects intensively; under high load, recovery performance is insufficient and interruption impact is amplified.

### Connection Usage (70% / 90%)
CES `connections_usage` directly provides connection usage. At the failover moment, all old connections become invalid;
application connection pools will instantly reconnect — when connections are near the limit, the reconnection storm can overwhelm the new master.
This is the most common "avalanche" source in failover drills.

### Max Latency (10ms warning / 50ms critical)
CES `command_max_rt` (microseconds) takes the last 1 hour max average. Sustained high latency indicates slow commands or hot keys, high risk during failover.

### Backup Freshness (48h / retention period)
Master-slave failover itself does not corrupt data (replicated data RPO≈0); backups are the recovery safety net for abnormal scenarios.
No successful backup beyond the retention period (`backup_strategy.keep_days`, capped at ≤7 days) is treated as critical.

### Master-Slave Structure
- Master-slave nodes incomplete (missing master or slave) -> critical, cannot failover
- Master-slave node status abnormal (not Active/Running/normal) -> critical
- Master-slave same AZ -> warning (AZ power-off drill cannot verify cross-AZ DR)
- Master-slave cross-AZ -> info

## Two Dynamic Defense Lines Before execute

The prepare risk assessment is a **snapshot** (the state at generation time); if hours pass between prepare and execute, load may have changed.
Therefore, execute has two additional dynamic defense lines before actual execution:

1. **Instance consistency check**: `risk_assessment.json` region/instance_id doesn't match current `config.json` -> block by default.
   Prevents "E "prepare instance A, switch config to B, use A's assessment to bypass B's failover" mismatches.
2. **Real-time recheck before failover** (`risk.realtime_safety_check`): immediately before calling ChangeMasterStandby, confirms
   instance status is RUNNING and master-slave nodes are healthy; blocks by default on critical anomaly (requires `--force`).

## Why "Block + --force" Instead of Always Allowing

The purpose of a failover drill is to verify HA, not to create incidents. When signals like instance abnormality, unhealthy nodes, or no backup
indicate "failover will definitely have problems", the drill would very likely turn into a real incident.
Therefore, execution is rejected by default, returning the final decision to a human: `execute --force` means
"I have assessed the risk and accept it" — a conscious choice, not the default path.

## Extension and Maintenance

- Add detection items: add probe logic in `risk.py` `detect_*` functions -> add an `_item(...)` in `assess_risks` -> add a line of business rationale in this file.
- Adjust thresholds: directly modify the `THRESH` constant in `risk.py` (single source of truth); this file does not need to sync values.
