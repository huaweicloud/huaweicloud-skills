# Acceptance Criteria 验收标准

## Functional Criteria 功能标准

### Quota Query 配额查询

| # | Criterion | Verification | Status |
|---|-----------|--------------|--------|
| AC-01 | `list-quotas` returns domain_quotas + quotas + page_info | Run `cloudrobo resource list-quotas` | ☐ |
| AC-02 | `list-quotas` supports workspace_id filter | Run with `--workspace-id <id>` | ☐ |
| AC-03 | `list-quotas` supports resource_type filter | Run with `--resource-type CCE` | ☐ |
| AC-04 | CCE quota returns npu=0 | Run `--resource-type CCE`, check domain_quotas.npu=0 | ☐ |
| AC-05 | ModelArts quota returns cpu/memory/gpu=0 | Run `--resource-type MODELARTS`, check domain_quotas | ☐ |
| AC-06 | `list-quotas` supports pagination | Run with `--limit 20 --offset 0` | ☐ |
| AC-07 | `list-quotas` supports pool_type filter | Run with `--pool-type DEDICATED` | ☐ |

### Resource Pool Query 资源池查询

| # | Criterion | Verification | Status |
|---|-----------|--------------|--------|
| AC-08 | `list-pools` returns resources + page_info | Run `cloudrobo resource list-pools` | ☐ |
| AC-09 | `list-pools` supports resource_type filter | Run with `--resource-type MODELARTS` | ☐ |
| AC-10 | `list-pools` supports usages filter | Run with `--usages TRAINING,INFERENCE` | ☐ |
| AC-11 | `list-pools` supports pagination | Run with `--limit 10 --offset 0` | ☐ |
| AC-12 | `show-pool` returns pool detail with nodes | Run with `--pool-id <id>` | ☐ |
| AC-13 | `show-pool` returns node labels | Check nodes[].labels in response | ☐ |

### SDK Coverage SDK覆盖

| # | Criterion | Verification | Status |
|---|-----------|--------------|--------|
| AC-14 | SDK `list_quotas` works | Call `client.list_quotas()` | ☐ |
| AC-15 | SDK `list_pools` works | Call `client.list_pools()` | ☐ |
| AC-16 | SDK `show_pool` works | Call `client.show_pool(id)` | ☐ |

## Non-Functional Criteria 非功能标准

### Security 安全

| # | Criterion | Verification | Status |
|---|-----------|--------------|--------|
| AC-17 | No hardcoded AK/SK in SKILL.md or scripts | `grep -r "AK\|SK\|ACCESS_KEY\|SECRET" skills/ai/cloudrobo/huawei-cloud-cloudrobo-resource/` | ☐ |
| AC-18 | Credentials read from environment variables | Check docs reference `HUAWEI_CLOUD_AK`/`HUAWEI_CLOUD_SK` | ☐ |

### Documentation 文档

| # | Criterion | Verification | Status |
|---|-----------|--------------|--------|
| AC-19 | SKILL.md has valid frontmatter | `grep '^---$' skills/ai/cloudrobo/huawei-cloud-cloudrobo-resource/SKILL.md` | ☐ |
| AC-20 | Frontmatter has name + description + tags | Check frontmatter fields | ☐ |
| AC-21 | Description includes `Triggers include:` | `grep 'Triggers include:' skills/ai/cloudrobo/huawei-cloud-cloudrobo-resource/SKILL.md` | ☐ |
| AC-22 | All required sections present | Check Overview/Prerequisites/Workflow/Core Commands/Reference Documents | ☐ |
| AC-23 | Bilingual section headers | `grep '##.*概述'`, `grep '##.*前置条件'`, etc. | ☐ |
| AC-24 | references/ directory exists with 7 files | `ls skills/ai/cloudrobo/huawei-cloud-cloudrobo-resource/references/` | ☐ |
| AC-25 | scripts/test-cli-commands.sh exists | `ls skills/ai/cloudrobo/huawei-cloud-cloudrobo-resource/scripts/` | ☐ |
| AC-26 | templates/test-vars.json exists | `ls skills/ai/cloudrobo/huawei-cloud-cloudrobo-resource/templates/` | ☐ |

### Constraints 约束

| # | Criterion | Verification | Status |
|---|-----------|--------------|--------|
| AC-27 | Directory size ≤ 40 MB | `du -sh skills/ai/cloudrobo/huawei-cloud-cloudrobo-resource/` | ☐ |
| AC-28 | File count ≤ 30 | `find skills/ai/cloudrobo/huawei-cloud-cloudrobo-resource/ -type f \| wc -l` | ☐ |
| AC-29 | All files have allowed extensions | Check for .md/.sh/.json only | ☐ |
| AC-30 | No fabricated API paths | All paths match SDK source `_url()` calls | ☐ |

## Sign-off 签收

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Skill Author | | | |
| Reviewer | | | |
| Approver | | | |
