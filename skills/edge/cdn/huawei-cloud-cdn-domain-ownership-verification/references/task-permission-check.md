# Step 1: Credential Validation

Check hcloud credential availability. The domain permission check is performed in Step 2 via `ShowVerifyDomainOwnerInfo` (a successful query confirms the domain belongs to the current account; 404/CDN.0171 means the domain is not under this account, 403 means insufficient permission).

## 1.1 Credential Validation

**Command**:
```bash
hcloud configure list
```

**Decision logic**:

| Output | Action |
|--------|--------|
| mode=AKSK + accessKeyId present | Credentials valid, continue to Step 2 |
| No AK/SK configuration | Abort, return "Credentials not configured. Run 'hcloud configure' to configure AK/SK first." |

**Security rules**:
- Do not read/echo/print AK/SK values
- Do not require users to input credentials directly in the conversation
- If the user provides AK/SK in the conversation, stop immediately and guide secure configuration

## Exception Handling

| Exception Scenario | Handling |
|--------------------|----------|
| hcloud command not found | Prompt to install hcloud CLI, see cli-installation-guide.md |
| Network connection failure | Prompt to check network connection |
| Credentials expired | Prompt to reconfigure credentials |

## Example

```bash
# Credential validation
hcloud configure list
# Output contains mode=AKSK + accessKeyId → continue to Step 2
```
