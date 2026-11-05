# Verification Method

## Prerequisite Check

```bash
hcloud version                     # expect >= 7.2
hcloud configure list                # expect a valid AK/SK profile with region
```

## Quick Verification

Check the WAF operations used by this skill are available in the CLI metadata:

```bash
hcloud WAF ListHost --cli-region=cn-north-4 --help
hcloud WAF ListCompositeHosts --cli-region=cn-north-4 --help
hcloud WAF ListEvent --cli-region=cn-north-4 --help
hcloud WAF ListIgnoreRule --cli-region=cn-north-4 --help
hcloud WAF ListWhiteblackipRule --cli-region=cn-north-4 --help
hcloud WAF ListGeoipRule --cli-region=cn-north-4 --help
hcloud WAF ListCustomRules --cli-region=cn-north-4 --help
hcloud WAF ListPunishmentRules --cli-region=cn-north-4 --help
hcloud WAF ListAnticrawlerRules --cli-region=cn-north-4 --help
hcloud WAF ListCcRules --cli-region=cn-north-4 --help
hcloud WAF ListPolicyProtectRules --cli-region=cn-north-4 --help
hcloud WAF ListWebBasicProtectionRules --cli-region=cn-north-4 --help
hcloud WAF ListPolicy --cli-region=cn-north-4 --help
```

Each `--help` should print the operation's `Description`/`Params` (i.e. the command exists and the parameter names match the ones used in SKILL.md).

## Live Operability Check

| Step | Command | Expected Outcome |
|------|---------|------------------|
| 1. List protected domains | `hcloud WAF ListCompositeHosts --cli-region={region} --pagesize=10` | JSON list of hosts (may be empty) |
| 2. List a host's events | `hcloud WAF ListEvent --cli-region={region} --recent=today --pagesize=1` | JSON event structure (may be empty) — query itself succeeds |
| 3. Block-event filter | `hcloud WAF ListEvent --cli-region={region} --recent=3days --actions.1=block --pagesize=10` | Filtered block events |
| 4. Rule chain queries | `hcloud WAF ListIgnoreRule --cli-region={region} --policy_id={policy_id}` | rule JSON (may be empty) |

> Note: if the account returns `WAF.00012006 ... not authorized`, the CLI commands are correctly formed but the IAM account lacks WAF read permission — grant the policy in `references/iam-policies.md` and retry.

## Testing the Diagnosis Flow (dry run)

1. Pick a real (or user-provided) `hostname`.
2. Run Step 1 → get `host_id` / `policy_id`.
3. Run Step 2 with a recent window (`--recent=1week` or `--from/--to`) → collect events.
4. Run Step 3 (local analysis) and Step 4 (rule chain) against `policy_id`.
5. Optionally re-run Step 2 after a user-applied change to compare.

## Rollback-Verify Command

```bash
hcloud WAF ListEvent --cli-region={region} --domains.1={hostname} --from={from_ms} --to={to_ms} --sip={source_ip} --actions.1=block
```
