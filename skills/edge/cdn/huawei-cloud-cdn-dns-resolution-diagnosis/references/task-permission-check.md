# Step 1: Credential Validation and Domain Permission Check

Check hcloud credential availability, and validate the domain belongs to the current account via ShowDomainDetailByName while obtaining the expected CNAME.

## 1.1 Credential Validation

**Command**:
```bash
hcloud configure list
```

**Decision Logic**:

| Output | Handling |
|--------|----------|
| mode=AKSK + accessKeyId present | Credentials valid, continue to 1.2 |
| No AK/SK configuration | Abort, return "Credentials not configured. Run `hcloud configure` first to configure AK/SK" |

**Security Rules**:
- Prohibited from reading/echoing/printing AK/SK values
- Prohibited from asking the user to input credentials directly in the conversation
- If the user provides AK/SK in the conversation, stop immediately and guide secure configuration

## 1.2 Domain Permission Validation and CNAME Retrieval

**Command**:
```bash
hcloud CDN ShowDomainDetailByName --cli-region=<region> --domain_name=<domain>
```

**Decision Logic**:

| Return Code | Handling |
|-------------|----------|
| 200 + id | Domain validation passed, record domain_id and **cname**, continue to Step 2 |
| 404 / CDN.0171 | Abort, return "Domain not under the current account. Please confirm the domain ownership" |
| 403 | Abort, return "No permission to diagnose this domain. Please contact the administrator to grant CDN domain query permission" |
| Other errors | Abort, return "Domain query failed: <error message>" |

**Output Records**:
- `domain_id`: Used for subsequent report
- `domain_name`: Confirm the target domain
- **`cname`**: CDN expected CNAME address, used for report and remediation suggestions (key field)
- `domain_status`: Domain status (online/offline/configuring)

## Exception Handling

| Exception Scenario | Handling |
|--------------------|----------|
| hcloud command not found | Prompt to install hcloud CLI, see cli-installation-guide.md |
| Network connection failed | Prompt to check network connection |
| Credentials expired | Prompt to reconfigure credentials |
| Domain status is configuring | Prompt "Domain is being configured, onboarding may not be complete" |
| Domain status is offline | Prompt "Domain is disabled, resolution may be abnormal" |

## Example

```bash
# Credential validation
hcloud configure list
# Output contains mode=AKSK + accessKeyId → continue

# Domain permission validation and CNAME retrieval
hcloud CDN ShowDomainDetailByName --cli-region=<region> --domain_name=www.example.com
# Returns 200 + id + cname=www.example.com.cdn.net → record cname, continue to Step 2
# Returns 404 → abort
# Returns 403 → abort
```

## Output Forwarding

After this step is complete, the following information is forwarded to subsequent steps and report generation:
- `domain_id`
- `domain_name`
- **`cname` (expected CNAME, used for Step 2 comparison and report)**
- `domain_status`
