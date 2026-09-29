# Step 1: Credential Validation and Domain Permission Validation

Check hcloud credential availability, and validate via ShowDomainDetailByName that the domain belongs to the current account.

## 1.1 Credential Validation

**Command**:
```bash
hcloud configure list
```

**Decision Logic**:

| Output | Handling |
|--------|----------|
| mode=AKSK + accessKeyId present | Credentials valid; continue to 1.2 |
| No AK/SK configuration | Stop; return "Credentials not configured. Run `hcloud configure` first to configure AK/SK" |

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

| Return Code | Handling |
|-------------|----------|
| 200 + domain_id | Domain validation passed; record domain_id and cname; continue to Step 2 |
| 404 / CDN.0171 | Stop; return "Domain not found under current account. Please confirm domain ownership" |
| 403 | Stop; return "No permission to diagnose this domain. Contact the administrator to grant CDN domain query permission" |
| Other error | Stop; return "Domain query failed: <error message>" |

**Output Records**:
- domain_id: used in subsequent report
- domain_name: confirmed target domain
- cname: CNAME address (optional record)
- domain_status: domain status (online/offline/configuring)

## Exception Handling

| Exception Scenario | Handling |
|---------------------|----------|
| hcloud command not found | Prompt to install hcloud CLI; see cli-installation-guide.md |
| Network connection failed | Prompt to check the network connection |
| Credentials expired | Prompt to reconfigure credentials |
| Domain status is configuring | Prompt "Domain is configuring; onboarding may not have completed, and certificate configuration may also be incomplete" |

## Example

```bash
# Credential validation
hcloud configure list
# Output contains mode=AKSK + accessKeyId → continue

# Domain permission validation
hcloud CDN ShowDomainDetailByName --cli-region=<region> --domain_name=www.example.com
# Returns 200 + domain_id → continue
# Returns 404 → stop
# Returns 403 → stop
```

## Report Content

Record the following information in the diagnosis report:
- Diagnosis item name: Domain Permission Validation
- Status: ✅ Pass / ❌ Fail / ⚠️ Warning
- Detail: domain_id, domain status
