# Acceptance Criteria: Correct/Error Pattern Comparison

## CLI Command Patterns

### Service Name

**Correct:** Use uppercase `SWR`
```bash
hcloud SWR ShowNamespace --namespace=pancake --cli-region=cn-north-4
```

**Error:** Use lowercase or mixed case
```bash
hcloud swr ShowNamespace ...   # Wrong: service name must be uppercase
hcloud Swr ShowNamespace ...   # Wrong: service name must be uppercase
```

### Operation Name

**Correct:** Use PascalCase
```bash
hcloud SWR ShowNamespace ...
hcloud SWR CreateRepo ...
hcloud SWR ListRepositoryTags ...
```

**Error:** Use snake_case or lowercase
```bash
hcloud SWR ShowNamespace ...  # Wrong: must be PascalCase
hcloud SWR CreateRepo ...     # Wrong: must be PascalCase
```

### Region Parameter

**Correct:** Include `--cli-region` in every command
```bash
hcloud SWR ShowNamespace --namespace=pancake --cli-region=cn-north-4
```

**Error:** Omit region parameter
```bash
hcloud SWR ShowNamespace --namespace=pancake  # Wrong: missing --cli-region
```

## Parameter Patterns

### Namespace Name

**Correct:** Lowercase letters, digits, hyphens; 1-64 characters
```bash
hcloud SWR CreateNamespace --namespace=my-project --cli-region=cn-north-4
```

**Error:** Uppercase, underscores, or invalid length
```bash
hcloud SWR CreateNamespace --namespace=MyProject  # Wrong: uppercase not allowed
hcloud SWR CreateNamespace --namespace=my_project  # Wrong: underscore not allowed
```

### Repository Visibility

**Correct:** Use boolean `true` or `false`
```bash
hcloud SWR CreateRepo --namespace=pancake --repository=my-app --is_public=false --cli-region=cn-north-4
```

**Error:** Use string values
```bash
hcloud SWR CreateRepo --namespace=pancake --repository=my-app --is_public=yes  # Wrong: must be boolean
```

### Tag Operations

**Correct:** Use `--tag` parameter with exact tag name
```bash
hcloud SWR ShowRepoTag --namespace=pancake --repository=my-app --tag=v1.0 --cli-region=cn-north-4
```

**Error:** Use `--name` or `--version` instead of `--tag`
```bash
hcloud SWR ShowRepoTag --namespace=pancake --repository=my-app --name=v1.0  # Wrong: parameter is --tag
```

### Sort Order Column

**Correct:** Use valid `--order_column` values per command
```bash
hcloud SWR ListReposDetails --namespace=pancake --order_column=name --order_type=desc --cli-region=cn-north-4
hcloud SWR ListReposDetails --namespace=pancake --order_column=tag_count --order_type=desc --cli-region=cn-north-4
```

**Error:** Use invalid column names
```bash
hcloud SWR ListReposDetails --namespace=pancake --order_column=size  # Wrong: not a valid order_column
```

## Security Standards

### Credential Handling

**Correct:** Use environment variables
```bash
export HUAWEI_CLOUD_AK=<your-ak>
export HUAWEI_CLOUD_SK=<your-sk>
export HUAWEI_CLOUD_REGION=cn-north-4
hcloud SWR ShowNamespace --namespace=pancake --cli-region=cn-north-4
```

**Error:** Hardcode credentials in commands or ask users for AK/SK
```bash
hcloud SWR ShowNamespace --namespace=pancake --cli-region=cn-north-4 --ak=xxx --sk=xxx  # Wrong: never pass credentials as parameters
```

### Write Operation Confirmation

**Correct:** Prompt user confirmation before write operations
```

The following write operation will be executed:
  Command: hcloud SWR CreateNamespace --namespace=my-project
  Target: namespace 'my-project'
  Change: Create new SWR namespace
Do you want to proceed? (yes/no)
```

**Error:** Execute write operations without confirmation
```bash
# Directly executing Create/Update/Delete without user confirmation is prohibited
hcloud SWR DeleteNamespaces --namespace=pancake --cli-region=cn-north-4
```

## Output Format Standards

### Tag Field Name

**ListRepositoryTags** returns `Tag` (capital T):

```json
[
  {
    "Tag": "v1.0",
    "digest": "sha256:..."
  }
]
```

**ShowRepoTag** returns `tag` (lowercase):

```json
{
  "tag": "v1.0",
  "digest": "sha256:..."
}
```

**Error:** Expect same field name in both responses

```json
// ListRepositoryTags uses "Tag" (capital T)
// ShowRepoTag uses "tag" (lowercase)
```

### Repository Image Count

**Correct:** Response field is `num_images`

```json
{
  "num_images": 5
}
```

**Error:** Expect `tag_count` in response (note: `tag_count` is valid for `--order_column` but not in response)

```json
{
  "tag_count": 5  // Wrong: response field is "num_images"
}
```
