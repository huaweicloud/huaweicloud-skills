# IAM Policies

## Summary

This skill does **not** require any IAM credentials or policies.

## Reason

The skill discovers and installs Huawei Cloud agent skills by fetching a
**public, read-only** skill index. It does not require:

- AK/SK (Access Key / Secret Key)
- IAM tokens or session credentials
- Any form of authentication or authorization

All data sources are public endpoints:

| Endpoint | Protocol | Purpose |
|----------|----------|---------|
| `gitcode.com/api/v5/.../skills-index/index.json` | HTTPS (443) | Skill index (public, base64-decoded) |
| `gitcode.com/api/v5/.../skills-index/cn-en-map.json` | HTTPS (443) | CN↔EN keyword mapping (public) |
| `raw.githubusercontent.com/huaweicloud/huaweicloud-skills` | HTTPS (443) | Full SKILL.md detail of a matched skill |
| `devdata2.huaweicloud.com/.../findcounts/increment` | HTTPS (443) | Fire-and-forget install-count record (non-blocking) |

## Permissions Needed

- **None.** No IAM policy, agency, or role needs to be attached to the agent
  runtime for this skill to work.

## Security Notes

- The script only performs HTTP GET requests to public endpoints (plus one
  non-blocking POST for install counting)
- No cloud resources are created, modified, or deleted
- No credentials are stored, transmitted, or logged
- The script does not reference any environment variables prefixed with
  `HUAWEI_`, `HW_`, or `HWC_` (except `SKILL_QUALITY_*` used to configure
  non-blocking quality reporting, which is optional)

## Network Requirements

Ensure the Agent runtime has network access to the endpoints listed above.
If the runtime is behind a firewall, allow HTTPS (443) egress to
`gitcode.com`, `raw.githubusercontent.com`, and `devdata2.huaweicloud.com`.