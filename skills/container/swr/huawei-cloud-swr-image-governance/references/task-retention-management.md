# Task: Retention Management

## Overview

SWR retention rules automate the cleanup of old image tags, helping manage storage and maintain a clean repository. This task covers creating, listing, updating, deleting retention rules, and viewing execution histories.

## Operations Catalog

| Operation          | Method | Description              | Key Parameters                                  |
| ------------------ | ------ | ------------------------ | ----------------------------------------------- |
| `ListRetentions`  | GET    | 获取镜像老化规则列表     | `--namespace`, `--repository`                   |
| `CreateRetention` | POST   | 创建镜像老化规则         | `--namespace`, `--repository`, `--algorithm`, `--rules.[N].template`, `--rules.[N].params`, `--rules.[N].tag_selectors` |
| `ShowRetention`   | GET    | 获取镜像老化规则详情     | `--namespace`, `--repository`, `--retention_id` |
| `UpdateRetention` | PUT    | 修改镜像老化规则         | Same as CreateRetention + `--retention_id`      |
| `DeleteRetention` | DELETE | 删除镜像老化规则         | `--namespace`, `--repository`, `--retention_id` |
| `ListRetentionHistories` | GET | 获取镜像老化执行记录 | `--namespace`, `--repository`, `--retention_id` |

## Workflows

### W1: List Retention Rules

```bash
# List all retention rules for a repository
hcloud SWR ListRetentions --namespace=pancake --repository=openclaw-sandbox --cli-region=cn-north-4
```

**Output**: Returns a flat JSON array. When no rules exist, returns `[]`.

### W2: Create a Retention Rule

Retention rules define which tags to keep. Tags NOT matching any rule condition will be deleted during execution.

**Rule Templates**:
- `tag_rule`: Keep a specified number of the most recent tags (by `num`)
- `date_rule`: Keep tags created within a specified number of days (by `days`)

**Tag Selector Kinds**:
- `label`: Exact tag name match (e.g., `latest`, `v1.0`)
- `regexp`: Regular expression pattern match (e.g., `v\d+\.\d+`)

**Algorithm**: `or` — a tag is retained if it matches ANY rule (OR logic)

```bash
# Keep last 10 tags (regardless of age)
hcloud SWR CreateRetention --namespace=pancake --repository=openclaw-sandbox \
  --algorithm=or \
  --rules.1.template=tag_rule \
  --rules.1.params.num=10 \
  --rules.1.tag_selectors.1.kind=label \
  --rules.1.tag_selectors.1.pattern=latest \
  --cli-region=cn-north-4

# Keep tags from last 30 days
hcloud SWR CreateRetention --namespace=pancake --repository=openclaw-sandbox \
  --algorithm=or \
  --rules.1.template=date_rule \
  --rules.1.params.days=30 \
  --rules.1.tag_selectors.1.kind=label \
  --rules.1.tag_selectors.1.pattern=latest \
  --cli-region=cn-north-4

# Multiple rules: keep last 5 tags OR keep tags from last 30 days
hcloud SWR CreateRetention --namespace=pancake --repository=openclaw-sandbox \
  --algorithm=or \
  --rules.1.template=tag_rule \
  --rules.1.params.num=5 \
  --rules.1.tag_selectors.1.kind=label \
  --rules.1.tag_selectors.1.pattern=latest \
  --rules.2.template=date_rule \
  --rules.2.params.days=30 \
  --rules.2.tag_selectors.1.kind=regexp \
  --rules.2.tag_selectors.1.pattern=v\d+ \
  --cli-region=cn-north-4

# Protect specific tags with label selector (these will always be kept)
hcloud SWR CreateRetention --namespace=pancake --repository=openclaw-sandbox \
  --algorithm=or \
  --rules.1.template=tag_rule \
  --rules.1.params.num=10 \
  --rules.1.tag_selectors.1.kind=label \
  --rules.1.tag_selectors.1.pattern=latest \
  --rules.1.tag_selectors.2.kind=label \
  --rules.1.tag_selectors.2.pattern=stable \
  --cli-region=cn-north-4
```

**⚠️ Nested Array Format**: Rules use deeply nested arrays:
- `--rules.1.template` (outer array, 1-based)
- `--rules.1.tag_selectors.1.kind` (inner array, 1-based)
- Index starts from 1 (not 0)

**Tag Selector Purpose**: Tag selectors define WHICH tags the rule applies to. Use `label` kind with important tag names (like `latest`, `stable`) to protect them from cleanup, or use `regexp` to match version patterns.

**Post-creation Verification**:

```bash
hcloud SWR ListRetentions --namespace=pancake --repository=openclaw-sandbox --cli-region=cn-north-4
```

### W3: View Retention Rule Details

```bash
hcloud SWR ShowRetention --namespace=pancake --repository=openclaw-sandbox --retention_id=<id> --cli-region=cn-north-4
```

Response format to be verified with actual API call.

### W4: Update a Retention Rule

```bash
# Change retention to keep only last 5 tags
hcloud SWR UpdateRetention --namespace=pancake --repository=openclaw-sandbox \
  --retention_id=<id> \
  --algorithm=or \
  --rules.1.template=tag_rule \
  --rules.1.params.num=5 \
  --rules.1.tag_selectors.1.kind=label \
  --rules.1.tag_selectors.1.pattern=latest \
  --cli-region=cn-north-4
```

**Parameters**: Same as CreateRetention, plus `--retention_id`.

### W5: Delete a Retention Rule

⚠️ **CAUTION**: Deleting a retention rule stops automated cleanup. Old tags will accumulate indefinitely.

```bash
hcloud SWR DeleteRetention --namespace=pancake --repository=openclaw-sandbox --retention_id=<id> --cli-region=cn-north-4
```

**Post-deletion Verification**:

```bash
hcloud SWR ListRetentions --namespace=pancake --repository=openclaw-sandbox --cli-region=cn-north-4
```

### W6: View Retention Execution History

```bash
hcloud SWR ListRetentionHistories --namespace=pancake --repository=openclaw-sandbox --retention_id=<id> --cli-region=cn-north-4
```

Response format to be verified with actual API call.

## Common Scenarios

### S1: Standard Cleanup Policy for Development Repository

Keep a reasonable number of recent tags:

```bash
# Keep last 10 tags to manage storage
hcloud SWR CreateRetention --namespace=dev-team --repository=my-app \
  --algorithm=or \
  --rules.1.template=tag_rule \
  --rules.1.params.num=10 \
  --rules.1.tag_selectors.1.kind=label \
  --rules.1.tag_selectors.1.pattern=latest \
  --cli-region=cn-north-4
```

### S2: Production Repository with Strict Retention

Keep production images for a longer period:

```bash
# Keep all tags from last 90 days in production repo
hcloud SWR CreateRetention --namespace=prod-team --repository=my-app \
  --algorithm=or \
  --rules.1.template=date_rule \
  --rules.1.params.days=90 \
  --rules.1.tag_selectors.1.kind=regexp \
  --rules.1.tag_selectors.1.pattern=v\d+\.\d+\.\d+ \
  --cli-region=cn-north-4
```

### S3: Protect Important Tags While Cleaning Old Ones

Use tag selectors to protect critical tags:

```bash
# Keep last 3 tags, but always protect latest and stable
hcloud SWR CreateRetention --namespace=team-backend --repository=gateway \
  --algorithm=or \
  --rules.1.template=tag_rule \
  --rules.1.params.num=3 \
  --rules.1.tag_selectors.1.kind=label \
  --rules.1.tag_selectors.1.pattern=latest \
  --rules.1.tag_selectors.2.kind=label \
  --rules.1.tag_selectors.2.pattern=stable \
  --cli-region=cn-north-4
```

### S4: Batch Apply Retention to All Repositories

Apply retention rules to all repositories in a namespace:

```bash
# 1. List all repositories in the namespace
hcloud SWR ListReposDetails --namespace=team-backend --cli-region=cn-north-4

# 2. For each repository, create a retention rule
hcloud SWR CreateRetention --namespace=team-backend --repository=<repo-name> \
  --algorithm=or \
  --rules.1.template=tag_rule \
  --rules.1.params.num=10 \
  --rules.1.tag_selectors.1.kind=label \
  --rules.1.tag_selectors.1.pattern=latest \
  --cli-region=cn-north-4
```

## Retention Rule Design Guide

| Repository Type   | Recommended Rule          | Params          | Tag Selector              |
| ----------------- | ------------------------- | --------------- | ------------------------- |
| Development       | `tag_rule` (keep N)       | `num=10`        | `label:latest`            |
| Staging           | `date_rule` (keep N days) | `days=30`       | `regexp:v\d+\.\d+`       |
| Production        | `date_rule` (keep N days) | `days=90`       | `regexp:v\d+\.\d+\.\d+`  |
| Base images       | `tag_rule` (keep N)       | `num=5`         | `label:latest,stable`    |