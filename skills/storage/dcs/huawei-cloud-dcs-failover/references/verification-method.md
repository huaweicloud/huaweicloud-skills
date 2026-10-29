# Verification Method

## Environment Verification

### 1. hcloud Availability

```bash
hcloud version
```

Expected: outputs KooCLI version number.

### 2. Target Instance Availability

```bash
hcloud DCS ListInstances --cli-region=cn-south-1
```

Expected: target instance is in the list with status RUNNING.

### 3. Master-Slave Structure Verification

```bash
hcloud DCS ShowNodesInformation --cli-region=cn-south-1 --instance_id=<id>
```

Expected: output contains master and slave nodes with different `az_code` (cross-AZ).

## End-to-End Functional Verification

### Full Pipeline Drill (invocation performs real failover)

```bash
# One-click full pipeline (prepare -> execute -> report, execute is real failover)
python3 scripts/run.py

# Or phase-by-phase
python3 scripts/run.py --phase prepare
python3 scripts/run.py --phase execute [--force]
python3 scripts/run.py --phase report
```

Expected:
- prepare outputs instance info, IAM permissions, risk assessment overview
- execute outputs pre-check, risk hints, real-time recheck, and calls ChangeMasterStandby for real failover
- Cloud resource master-slave roles are swapped

> ⚠️ **Before executing a real failover**:
> - Confirm the target instance is a test environment instance, not production
> - Notify relevant business teams of the drill time window
> - Assess and accept risks (if prepare reports critical risks, a second confirmation with --force is required)

### Real Failover Drill

```bash
python3 scripts/run.py
```

Expected:
1. prepare phase completes architecture hard-gate and risk assessment
2. execute phase calls ChangeMasterStandby, polls for failover completion
3. Report generated at `templates/failover_report_*.html`

## Key Path Verification Points

| Check point | Verification method | Pass criteria |
|-------------|---------------------|---------------|
| Architecture hard-gate | Run prepare on a single-AZ or non-ha instance | Should be rejected |
| Status gate | Run prepare on a CLOSED instance | Should warn and execute should reject |
| Risk blocking | Fake a critical item in risk_assessment.json | execute without --force should exit |
| Instance consistency | Modify config.json instance_id then run execute | Should report risk assessment mismatch and block |
| Failover detection | Check execution_result.json after real failover | result=success, after_master.az=original slave AZ |
| Scoring | Check scores field | Three-dimensional scoring + weighted total present and reasonable |
