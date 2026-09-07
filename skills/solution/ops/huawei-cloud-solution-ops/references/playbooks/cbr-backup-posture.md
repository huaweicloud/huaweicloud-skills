# CBR Backup Posture

Use this playbook when the user asks whether backup, recovery, vault capacity, or protection policy is healthy.

## Inputs

- Target region and protected resource type.
- Optional vault ID, backup ID, policy ID, or protected instance ID.
- Recovery point objective and retention expectations if the user has them.

## Read-Only Flow

1. Run CBR `ListVault` and `ShowSummary` to understand vault count, used capacity, and high-level posture.
2. Run CBR `ListBackups` to inspect backup status, age, size, and associated vaults.
3. Run CBR `ListPolicies` and `ShowPolicy` before judging whether schedule and retention match user expectations.
4. Run CBR `ShowVault` and `ShowBackup` for target-scoped readback.
5. Run CBR `ListProtectable` for the relevant protectable type before suggesting protection coverage changes.

## Guardrails

- Backup deletion, restore, replication, and vault changes are high-risk and must not be submitted from this playbook.
- Do not claim recovery readiness from backup existence alone; verify restore point, policy, vault status, and target resource compatibility.
- Treat backup metadata as sensitive because it can expose resource names, IDs, and topology.

## Promotion Gaps

- Collect live read-only smoke evidence for `ListVault`, `ListBackups`, and one target-scoped backup or vault query.
- Add restore-readiness checks after non-mutating verification paths are proven.
