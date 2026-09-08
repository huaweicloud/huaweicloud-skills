# Acceptance Criteria 验收标准

## Functional Criteria 功能标准

### Workspace Management 工作空间管理

| # | Criterion | Verification | Status |
|---|-----------|--------------|--------|
| AC-01 | `create` creates a workspace and returns workspace_id + asset_catalog_id | Run `cloudrobo workspace create --name test --default-obs-path obs://bucket/test` | ☐ |
| AC-02 | `list` returns all workspaces for the domain | Run `cloudrobo workspace list` | ☐ |
| AC-03 | `list` supports pagination | Run `cloudrobo workspace list --limit 10 --offset 0` | ☐ |
| AC-04 | `list` returns `last_count` (remaining quota) | Check response has `last_count` field | ☐ |
| AC-05 | `show` returns workspace detail with asset_catalog_id | Run `cloudrobo workspace show --workspace-id <id>` | ☐ |
| AC-06 | `update` modifies workspace name | Run `cloudrobo workspace update --workspace-id <id> --name new-name` | ☐ |
| AC-07 | `update` modifies workspace description and tags | Run with `--description` and `--tags` | ☐ |
| AC-08 | `update` transfers ownership | Run with `--owner-id <new-owner>` | ☐ |
| AC-09 | `delete` removes a workspace | Run `cloudrobo workspace delete --workspace-id <id>` | ☐ |
| AC-10 | `create --dry-run` previews without executing | Run with `--dry-run` flag | ☐ |

### Member Management 成员管理

| # | Criterion | Verification | Status |
|---|-----------|--------------|--------|
| AC-11 | `list-members` returns member list | Run `cloudrobo workspace list-members --workspace-id <id>` | ☐ |
| AC-12 | `add-members` adds new members | Run `cloudrobo workspace add-members --workspace-id <id> --member-list '<json>'` | ☐ |
| AC-13 | `update-member` changes member roles | Run `cloudrobo workspace update-member --workspace-id <id> --user-id <uid> --role-ids <r1>` | ☐ |
| AC-14 | `delete-members` removes members | Run `cloudrobo workspace delete-members --workspace-id <id> --user-ids <u1>` | ☐ |
| AC-15 | Root user cannot be added as member | Attempt to add root user, expect error | ☐ |
| AC-16 | Owner cannot be deleted | Attempt to delete owner, expect error | ☐ |
| AC-17 | Duplicate member rejected | Attempt to add existing member, expect error | ☐ |

### Overview & Statistics 概览统计

| # | Criterion | Verification | Status |
|---|-----------|--------------|--------|
| AC-18 | `overview` returns capacity and usage | Run `cloudrobo workspace overview` | ☐ |
| AC-19 | `overview` returns member count | Check response has `member_count` field | ☐ |
| AC-20 | `workspace_used` matches list count | Compare overview `workspace_used` with list total | ☐ |

### Context Switching 工作空间切换

| # | Criterion | Verification | Status |
|---|-----------|--------------|--------|
| AC-21 | `use` switches active workspace | Run `cloudrobo workspace use --workspace-id <id>` | ☐ |
| AC-22 | `use` saves to workspace.json | Check `~/.cloudrobo/workspace.json` after `use` | ☐ |
| AC-23 | `use` on invalid ID fails gracefully | Run with invalid ID, expect error exit | ☐ |
| AC-24 | `current` displays saved config | Run `cloudrobo workspace current` | ☐ |
| AC-25 | `current` with no config shows "未配置工作空间" | Run after removing workspace.json | ☐ |

### Default Workspace 默认工作空间

| # | Criterion | Verification | Status |
|---|-----------|--------------|--------|
| AC-26 | Default workspace auto-created on first list | Run `list` on new account, check "default" appears | ☐ |
| AC-27 | Default workspace cannot be deleted | Attempt delete, expect error | ☐ |
| AC-28 | Default workspace does not support member operations | Attempt add/update/delete members, expect error | ☐ |
| AC-29 | Default workspace supports first-time obs path set | Run update with `--default-obs-path` | ☐ |

### SDK Coverage SDK覆盖

| # | Criterion | Verification | Status |
|---|-----------|--------------|--------|
| AC-30 | SDK `create_workspace` works | Call `client.create_workspace({...})` | ☐ |
| AC-31 | SDK `list_workspaces` works | Call `client.list_workspaces()` | ☐ |
| AC-32 | SDK `show_workspace` works | Call `client.show_workspace(id)` | ☐ |
| AC-33 | SDK `update_workspace` works | Call `client.update_workspace(id, {...})` | ☐ |
| AC-34 | SDK `delete_workspace` works | Call `client.delete_workspace(id)` | ☐ |
| AC-35 | SDK `add_workspace_members` works | Call `client.add_workspace_members(id, {...})` | ☐ |
| AC-36 | SDK `list_workspace_members` works | Call `client.list_workspace_members(id)` | ☐ |
| AC-37 | SDK `update_workspace_member` works | Call `client.update_workspace_member(id, {...})` | ☐ |
| AC-38 | SDK `delete_workspace_members` works | Call `client.delete_workspace_members(id, [uids])` | ☐ |
| AC-39 | SDK `get_workspace_overview` works | Call `client.get_workspace_overview()` | ☐ |

## Non-Functional Criteria 非功能标准

### Security 安全

| # | Criterion | Verification | Status |
|---|-----------|--------------|--------|
| AC-40 | No hardcoded AK/SK in SKILL.md or scripts | `grep -r "AK\|SK\|ACCESS_KEY\|SECRET" skills/ai/cloudrobo/huawei-cloud-cloudrobo-workspace/` | ☐ |
| AC-41 | Credentials read from environment variables | Check docs reference `HUAWEI_CLOUD_AK`/`HUAWEI_CLOUD_SK` | ☐ |
| AC-42 | Mutating operations require user confirmation | Check SKILL.md Edge Cases section | ☐ |
| AC-43 | workspace.json has 0o600 permissions | Check file permissions after `workspace use` | ☐ |

### Documentation 文档

| # | Criterion | Verification | Status |
|---|-----------|--------------|--------|
| AC-44 | SKILL.md has valid frontmatter | `grep '^---$' skills/ai/cloudrobo/huawei-cloud-cloudrobo-workspace/SKILL.md` | ☐ |
| AC-45 | Frontmatter has name + description + tags | Check frontmatter fields | ☐ |
| AC-46 | Description includes `Triggers include:` | `grep 'Triggers include:' skills/ai/cloudrobo/huawei-cloud-cloudrobo-workspace/SKILL.md` | ☐ |
| AC-47 | All required sections present | Check Overview/Prerequisites/Workflow/Core Commands/Reference Documents | ☐ |
| AC-48 | Bilingual section headers | `grep '##.*概述'`, `grep '##.*前置条件'`, etc. | ☐ |
| AC-49 | references/ directory exists with required files | `ls skills/ai/cloudrobo/huawei-cloud-cloudrobo-workspace/references/` | ☐ |
| AC-50 | scripts/test-cli-commands.sh exists | `ls skills/ai/cloudrobo/huawei-cloud-cloudrobo-workspace/scripts/` | ☐ |
| AC-51 | templates/test-vars.json exists | `ls skills/ai/cloudrobo/huawei-cloud-cloudrobo-workspace/templates/` | ☐ |

### Constraints 约束

| # | Criterion | Verification | Status |
|---|-----------|--------------|--------|
| AC-52 | Directory size ≤ 40 MB | `du -sh skills/ai/cloudrobo/huawei-cloud-cloudrobo-workspace/` | ☐ |
| AC-53 | File count ≤ 30 | `find skills/ai/cloudrobo/huawei-cloud-cloudrobo-workspace/ -type f \| wc -l` | ☐ |
| AC-54 | All files have allowed extensions | Check for .md/.sh/.json/.yaml/.py only | ☐ |
| AC-55 | No fabricated API paths | All paths match SDK source `_url()` calls | ☐ |

## Sign-off 签收

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Skill Author | | | |
| Reviewer | | | |
| Approver | | | |
