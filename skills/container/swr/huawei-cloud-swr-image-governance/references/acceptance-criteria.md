# Acceptance Criteria: Correct/Error Pattern Comparison

## CLI Command Patterns

### Service Name

**Correct:** Use uppercase `SWR`
```bash
hcloud SWR ShowNamespaceAuth --namespace=pancake --cli-region=cn-north-4
```

**Error:** Use lowercase or mixed case
```bash
hcloud swr ShowNamespaceAuth ...   # Wrong: service name must be uppercase
hcloud Swr ShowNamespaceAuth ...   # Wrong: service name must be uppercase
```

### Operation Name

**Correct:** Use PascalCase
```bash
hcloud SWR ShowNamespaceAuth ...
hcloud SWR CreateRetention ...
hcloud SWR ListRepoDomains ...
```

**Error:** Use snake_case or lowercase
```bash
hcloud SWR show_namespace_auth ...  # Wrong: must be PascalCase
hcloud SWR create_retention ...     # Wrong: must be PascalCase
```

### Region Parameter

**Correct:** Include `--cli-region` in every command
```bash
hcloud SWR ShowNamespaceAuth --namespace=pancake --cli-region=cn-north-4
```

**Error:** Omit region parameter
```bash
hcloud SWR ShowNamespaceAuth --namespace=pancake  # Wrong: missing --cli-region
```

## Parameter Patterns

### Array-Style Permission Parameters

**Correct:** Index starts from 1
```bash
hcloud SWR CreateNamespaceAuth --namespace=pancake --1.auth=7 --1.user_id=xxx --1.user_name=xxx --cli-region=cn-north-4
```

**Error:** Index starts from 0
```bash
hcloud SWR CreateNamespaceAuth --namespace=pancake --0.auth=7 --0.user_id=xxx --0.user_name=xxx  # Wrong: index starts from 1
```

### Auth Values

**Correct:** Use numeric values 7, 3, 1
```bash
--1.auth=7  # manage (full control)
--1.auth=3  # edit (push/pull)
--1.auth=1  # read (pull only)
```

**Error:** Use arbitrary numbers or strings
```bash
--1.auth=2   # Wrong: 2 is not a valid auth level
--1.auth=admin  # Wrong: must be numeric
```

### Shared Domain Parameters

**Correct:** Use `--access_domain` with IAM domain name, include `--deadline` and `--permit`
```bash
hcloud SWR CreateRepoDomains --namespace=pancake --repository=my-app --access_domain=<iam-domain-name> --deadline=forever --permit=read --cli-region=cn-north-4
```

**Error:** Use `--domain` or omit required parameters
```bash
hcloud SWR CreateRepoDomains --namespace=pancake --repository=my-app --domain=xxx  # Wrong: parameter is --access_domain
hcloud SWR CreateRepoDomains --namespace=pancake --repository=my-app --access_domain=xxx  # Wrong: missing --deadline and --permit
```

### Retention Rule Parameters

**Correct:** Use nested array format with proper template and params
```bash
hcloud SWR CreateRetention --namespace=pancake --repository=my-app \
  --algorithm=or \
  --rules.1.template=tag_rule --rules.1.params='{"num":"10"}' \
  --rules.1.tag_selectors.1.kind=label --rules.1.tag_selectors.1.pattern=latest \
  --cli-region=cn-north-4
```

**Error:** Flat parameter format or missing nested structure
```bash
hcloud SWR CreateRetention --namespace=pancake --repository=my-app --template=tag_rule --num=10  # Wrong: must use nested array format
```

## Security Standards

### Credential Handling

**Correct:** Use environment variables
```bash
export HUAWEI_CLOUD_AK=<your-ak>
export HUAWEI_CLOUD_SK=<your-sk>
export HUAWEI_CLOUD_REGION=cn-north-4
hcloud SWR ShowNamespaceAuth --namespace=pancake --cli-region=cn-north-4
```

**Error:** Hardcode credentials in commands or ask users for AK/SK
```bash
hcloud SWR ShowNamespaceAuth --namespace=pancake --cli-region=cn-north-4 --ak=xxx --sk=xxx  # Wrong: never pass credentials as parameters
```

### Write Operation Confirmation

**Correct:** Prompt user confirmation before write operations
```
The following write operation will be executed:
  Command: hcloud SWR CreateNamespaceAuth --namespace=pancake --1.auth=7 --1.user_id=xxx --1.user_name=xxx
  Target: namespace 'pancake'
  Change: Grant manage (7) permission to user 'xxx'
Do you want to proceed? (yes/no)
```

**Error:** Execute write operations without confirmation
```bash
# Directly executing Create/Update/Delete without user confirmation is prohibited
hcloud SWR DeleteNamespaceAuth --namespace=pancake --1.user_id=xxx --1.user_name=xxx --cli-region=cn-north-4
```

## Output Format Standards

### Domain Timestamp Fields

**Correct:** Use `created` and `updated` fields
```json
{
  "created": "2025-01-15T10:30:00Z",
  "updated": "2025-01-15T10:30:00Z"
}
```

**Error:** Expect `created_at` and `updated_at` fields
```json
{
  "created_at": "2025-01-15T10:30:00Z"  // Wrong: field is "created", not "created_at"
}
```

### Permission Audit

**Correct:** Check both `self_auth` and `others_auths`
```python
# Check self_auth for owner permissions
# Check others_auths for granted user permissions
```

**Error:** Only check one field
```python
# Only checking self_auth misses granted users
# Only checking others_auths misses owner permissions
```
