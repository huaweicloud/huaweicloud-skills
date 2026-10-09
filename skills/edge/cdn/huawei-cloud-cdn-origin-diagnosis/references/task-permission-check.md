# Step 1: Credential Check and Domain Permission Validation

Check hcloud credential availability, and validate that the domain belongs to the current account via ShowDomainDetailByName.

## 1.1 Credential Check

**Command**:
```bash
hcloud configure list
```

**Decision Logic**:

| Output | Action |
|--------|--------|
| mode=AKSK + accessKeyId present | Credentials valid; continue to 1.2 |
| No AK/SK configured | Abort; return "Credentials not configured. Run `hcloud configure` to configure AK/SK first." |

## 1.1b Python Library Availability Check

Before any probe step runs, confirm the `requests` library required by `scripts/origin_probe.py` is importable and meets the minimum version.

**Command**:
```bash
python -c "import requests; assert requests.__version__ >= '2.25'; print('ok')"
```

**Decision Logic**:

| Output | Action |
|--------|--------|
| Prints `ok` | Library available; continue to 1.2 |
| ImportError / version too low | Abort; return "Missing Python library: requests. Install with: pip install requests>=2.25" |

**Security Rules**:
- Prohibited from reading/echoing/printing AK/SK values
- Prohibited from asking the user to input credentials directly in the conversation
- If the user provides AK/SK in the conversation, stop immediately and guide secure configuration

## 1.2 Domain Permission Validation

**Command**:
```bash
hcloud CDN ShowDomainDetailByName --cli-region=<region> --domain_name=<domain>
```

**Decision Logic**:

| Return Code | Action |
|-------------|--------|
| 200 + domain_id | Domain validation passed; record domain_id and cname; continue to Step 2 |
| 404 / CDN.0171 | Abort; return "Domain not found under the current account. Please confirm the domain ownership." |
| 403 | Abort; return "No permission to diagnose this domain. Please contact the administrator to grant CDN domain query permission." |
| Other errors | Abort; return "Domain query failed: <error message>" |

**Output Records**:
- domain_id: used for the subsequent report
- domain_name: confirms the target domain
- cname: CNAME address (optional record)
- domain_status: domain status (online/offline/configuring)

## Exception Handling

| Exception Scenario | Handling |
|--------------------|----------|
| hcloud command not found | Prompt to install hcloud CLI; see cli-installation-guide.md |
| Network connection failure | Prompt to check network connectivity |
| Credentials expired | Prompt to reconfigure credentials |
| Domain status is configuring | Prompt "Domain is being configured; onboarding may not be complete, but origin configuration query can continue." |

## Example

```bash
# Credential check
hcloud configure list
# Output contains mode=AKSK + accessKeyId → continue

# Domain permission validation
hcloud CDN ShowDomainDetailByName --cli-region=<region> --domain_name=www.example.com
# Returns 200 + domain_id → continue
# Returns 404 → abort
# Returns 403 → abort
```
