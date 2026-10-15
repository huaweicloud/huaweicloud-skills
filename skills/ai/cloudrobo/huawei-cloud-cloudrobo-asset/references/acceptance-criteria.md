# Acceptance Criteria 验收标准

## Functional Criteria 功能标准

### Repository & Catalog 仓库与目录

| # | Criterion | Verification | Status |
|---|-----------|--------------|--------|
| AC-01 | `list-repositories` returns repository list | Run `cloudrobo asset list-repositories` | ☐ |
| AC-02 | `list-repositories` filters by name | Run `cloudrobo asset list-repositories --name my-repo` | ☐ |
| AC-03 | `list-catalogs` returns catalogs for a repository | Run `cloudrobo asset list-catalogs --repository-id <id>` | ☐ |
| AC-04 | `show-catalog` returns catalog detail | Run `cloudrobo asset show-catalog --catalog-id <id>` | ☐ |

### Asset Management 资产管理

| # | Criterion | Verification | Status |
|---|-----------|--------------|--------|
| AC-05 | `create-asset` creates an asset and returns asset_id | Run `cloudrobo asset create-asset --catalog-id <id> --name test --type model --ext-metadata '{"model_type":"planning"}'` | ☐ |
| AC-06 | `create-asset --dry-run` previews without executing | Run with `--dry-run`, verify no asset created | ☐ |
| AC-07 | `list-assets` returns assets for a catalog | Run `cloudrobo asset list-assets --catalog-id <id>` | ☐ |
| AC-08 | `list-assets` filters by type and status | Run `cloudrobo asset list-assets --catalog-id <id> --type model --status RELEASE` | ☐ |
| AC-09 | `list-assets` requires repository-id or catalog-id | Run without either, expect UsageError | ☐ |
| AC-10 | `show-asset` returns asset detail | Run `cloudrobo asset show-asset --asset-id <id>` | ☐ |
| AC-11 | `update-asset` modifies asset properties | Run `cloudrobo asset update-asset --asset-id <id> --name new-name` | ☐ |
| AC-12 | `update-asset` rejects immutable fields at CLI level | Run `cloudrobo asset update-asset --asset-id <id> --type dataset`; expect Click "no such option" error (immutable fields: catalog_id/type/sub_type/url/parent_asset_version_id/generation_method not exposed as CLI options) | ☐ |
| AC-12b | `update-asset` SDK exposes no immutable-field parameters | Inspect `client.update_asset` signature / `validate_update_asset()` — only `type`/`sub_type` (create-consistency) are validated; immutable fields (`catalog_id`/`url`/`parent_asset_version_id`/`generation_method`) are not accepted as parameters at all | ☐ |
| AC-13 | `delete-asset` removes an asset | Run `cloudrobo asset delete-asset --asset-id <id>` | ☐ |
| AC-14 | `batch-delete-assets` removes multiple assets | Run `cloudrobo asset batch-delete-assets --asset-ids "id1,id2"` | ☐ |

### Version Management 版本管理

| # | Criterion | Verification | Status |
|---|-----------|--------------|--------|
| AC-15 | `create-version` creates a version | Run `cloudrobo asset create-version --asset-id <id> --version 1.0.0` | ☐ |
| AC-16 | `list-versions` returns versions for an asset | Run `cloudrobo asset list-versions --asset-id <id>` | ☐ |
| AC-17 | `show-version` returns version detail | Run `cloudrobo asset show-version --asset-id <id> --version-id <vid>` | ☐ |
| AC-18 | `update-version` modifies version properties | Run `cloudrobo asset update-version --asset-id <id> --version-id <vid> --description new` | ☐ |
| AC-19 | `delete-version` removes a version | Run `cloudrobo asset delete-version --asset-id <id> --version-id <vid>` | ☐ |
| AC-20 | `batch-delete-versions` removes multiple versions | Run `cloudrobo asset batch-delete-versions --asset-id <id> --version-ids "v1,v2"` | ☐ |

### Tag Management 标签管理

| # | Criterion | Verification | Status |
|---|-----------|--------------|--------|
| AC-21 | `add-tags` adds tags to an asset | Run `cloudrobo asset add-tags --asset-id <id> --tags "tag1,tag2"` | ☐ |
| AC-22 | `delete-tag` removes a tag | Run `cloudrobo asset delete-tag --asset-id <id> --tag tag1` | ☐ |
| AC-23 | `list-tags` returns predefined tags | Run `cloudrobo asset list-tags --language zh` | ☐ |
| AC-24 | `list-tags` filters by type | Run `cloudrobo asset list-tags --language zh --type model` | ☐ |

### Action Management Action管理

| # | Criterion | Verification | Status |
|---|-----------|--------------|--------|
| AC-25 | `list-actions` returns actions for a version | Run `cloudrobo asset list-actions --asset-id <id> --version-id <vid>` | ☐ |
| AC-26 | `create-action` creates an action | Run `cloudrobo asset create-action --asset-id <id> --version-id <vid> --action-info '{"action":"FFT",...}'` | ☐ |
| AC-27 | `show-action` returns action detail | Run `cloudrobo asset show-action --asset-id <id> --version-id <vid> --action FFT` | ☐ |
| AC-28 | `update-action` modifies an action | Run `cloudrobo asset update-action --asset-id <id> --version-id <vid> --action FFT --action-info '{"status":"DISABLE"}'` | ☐ |
| AC-29 | `delete-action` removes an action | Run `cloudrobo asset delete-action --asset-id <id> --version-id <vid> --action FFT` | ☐ |

### Permission & Lineage 权限与血缘

| # | Criterion | Verification | Status |
|---|-----------|--------------|--------|
| AC-30 | `check-permission` returns permission verdict | Run `cloudrobo asset check-permission --asset-id <id> --version-id <vid> --permissions "meta_read,data_read"` | ☐ |
| AC-31 | `show-lineage` returns parent-child tree | Run `cloudrobo asset show-lineage --asset-id <id> --version-id <vid> --type children` | ☐ |
| AC-32 | `show-lineage` with no lineage returns friendly message | Run on asset with no lineage, verify message | ☐ |

### Marketplace 广场

| # | Criterion | Verification | Status |
|---|-----------|--------------|--------|
| AC-33 | `search-assets` returns search results | Run `cloudrobo asset search-assets --keyword robot` | ☐ |
| AC-34 | `search-assets` filters by type | Run `cloudrobo asset search-assets --keyword robot --type model` | ☐ |
| AC-35 | `list-publication-assets` returns official/community assets | Run `cloudrobo asset list-publication-assets --type model` | ☐ |
| AC-36 | `list-publication-assets` filters by capabilities | Run `cloudrobo asset list-publication-assets --type model --capabilities training` | ☐ |

### Import & Export 导入导出

| # | Criterion | Verification | Status |
|---|-----------|--------------|--------|
| AC-37 | `import-asset` creates asset + version + uploads to OBS | Run `cloudrobo asset import-asset --catalog-id <id> --name test --type model --ext-metadata '{"model_type":"planning"}' --local-path ./model` | ☐ |
| AC-38 | `import-asset --dry-run` previews without executing | Run with `--dry-run`, verify no asset created | ☐ |
| AC-39 | `import-asset` with `--asset-id` creates new version | Run with `--asset-id <existing>`, verify new version created | ☐ |
| AC-40 | `import-asset` with `--asset-id --version-id` reuses version | Run with both, verify no new version created | ☐ |
| AC-41 | `import-asset` non-existent path raises FileNotFoundError | Run with `--local-path /nonexistent`, verify error | ☐ |
| AC-42 | `export-asset` downloads asset version to local + writes README.md | Run `cloudrobo asset export-asset --asset-id <id> --local-path ./out`; verify README.md with frontmatter exists in output | ☐ |
| AC-43 | `export-asset` with `--version-id` exports specific version | Run with `--version-id <vid>`, verify correct version | ☐ |
| AC-44 | `export-asset` no versions raises RuntimeError | Run on asset with no versions, verify error | ☐ |
| AC-45 | `import-asset` reads frontmatter from README.md | Export an asset, then import with only `--catalog-id --local-path`; verify metadata read from frontmatter | ☐ |
| AC-46 | `import-asset` ext_metadata missing for model raises UsageError | Run `import-asset --catalog-id <id> --name test --type model --local-path ./dir` without ext_metadata or frontmatter; verify UsageError | ☐ |
| AC-47 | `import-asset` frontmatter overrides CLI args | Create README.md with `type: model`, run with `--type dataset`; verify model type used | ☐ |
| AC-48 | `export-asset` preserves existing README.md body | Export to folder with existing README.md; verify body preserved, frontmatter replaced | ☐ |
| AC-49 | `import-asset` with invalid frontmatter YAML falls back silently | Create README.md with invalid YAML frontmatter, run import-asset; verify import proceeds with CLI args, no crash | ☐ |
| AC-49a | `import-asset` Mode 3 reuses version and uploads files | Run `import-asset --asset-id <id> --version-id <vid> --local-path ./dir`; verify files uploaded to OBS (same-name objects are overwritten idempotently) | ☐ |
| AC-49c | `import-asset` updates CREATING→DRAFT after upload | Run import without `--status`; verify version status is `CREATING` during upload, then `DRAFT` after upload succeeds | ☐ |
| AC-49d | `import-asset` preserves user-specified status | Run import with `status: RELEASE` in frontmatter; verify version status remains `RELEASE` after upload (no auto-update) | ☐ |
| AC-49e | `import-asset` rejects image type | Run `import-asset --catalog-id <id> --type image --local-path ./img`; verify UsageError "image assets are not supported by import-asset" | ☐ |
| AC-49f | `import-asset` imports algorithm with code upload | Run `import-asset --catalog-id <id> --type algorithm --tags Train --local-path ./algo`; verify code uploaded to `{catalog.url}/{asset_id}/{version_id}/` and version code_dir updated to actual path | ☐ |
| AC-49g | `create-asset` algorithm/image requires tags | Run `create-asset --type algorithm --ext-metadata '{"engine":...,"command":...}'` without tags; verify ValidationError "tags is required" | ☐ |
| AC-49h | `create-asset` algorithm tags subset of image tags | Create image with tags `["Train","Data Processing"]`, create algorithm referencing it with `--tags Train`; verify success; with `--tags Notebook` verify ValidationError "must be a subset of" | ☐ |
| AC-49i | `create-asset` algorithm sub_type is dropped | Run `create-asset --catalog-id <id> --type algorithm --sub-type training --tags Train --ext-metadata '{"engine":...,"command":...}'`; verify asset created and returned asset has no sub_type (client drops it) | ☐ |
| AC-49j | `create-asset` image sub_type is ignored | Run `create-asset --catalog-id <id> --type image --sub-type inference --tags "Data Processing" --ext-metadata '{"arch":"x86_64","device_type":["CPU"]}'`; verify no error and asset has no sub_type | ☐ |
| AC-49k | `import-asset` algorithm Mode 2 creates new version | Run `import-asset --asset-id <algo-id> --type algorithm --tags Train --local-path ./algo` (no --catalog-id); verify new version created, code uploaded to `{catalog.url}/{asset_id}/{version_id}/`, code_dir updated | ☐ |
| AC-49l | `import-asset` algorithm Mode 3 rejected | Run `import-asset --asset-id <algo-id> --version-id <vid> --type algorithm --local-path ./algo`; verify ValueError "not supported for algorithm assets" | ☐ |
| AC-49m | `import-asset` new version requires ext_metadata | Run `import-asset --asset-id <model-id> --local-path ./dir` without --ext-metadata; verify ValueError "ext_metadata is required to create a new version" | ☐ |
| AC-49n | `export-asset` algorithm downloads from code_dir | Run `export-asset --asset-id <algo-id> --local-path ./out`; verify files downloaded from `ext_metadata.code_dir` OBS path | ☐ |
| AC-49o | `export-asset` image type rejected | Run `export-asset --asset-id <image-id> --local-path ./out`; verify ValueError "does not support image assets" | ☐ |
| AC-49p | `import-asset` algorithm Mode 2 requires ext_metadata | Run `import-asset --asset-id <algo-id> --local-path ./algo` without --ext-metadata; verify ValueError "ext_metadata is required to create a new version for algorithm asset" | ☐ |
| AC-49q | `import-asset` Mode 3 SDK layer rejects image | Call SDK `import_asset(asset_id=<img-id>, version_id=<vid>, ...)` directly (bypass CLI); verify ValueError "import_asset does not support image assets" | ☐ |
| AC-49r | `export-asset` algorithm missing code_dir error | Run `export-asset --asset-id <algo-id-no-code> --local-path ./out` on algorithm with empty ext_metadata; verify RuntimeError contains "code_dir" and recovery guidance | ☐ |
| AC-49s | `export-asset` local_path not found raises FileNotFoundError | Run `export-asset --asset-id <id> --local-path /nonexistent`; verify FileNotFoundError "Local path does not exist" | ☐ |

## Non-Functional Criteria 非功能标准

### Security 安全

| # | Criterion | Verification | Status |
|---|-----------|--------------|--------|
| AC-50 | No hardcoded AK/SK in SKILL.md or scripts | `grep -r "AK\|SK\|ACCESS_KEY\|SECRET" skills/ai/cloudrobo/huawei-cloud-cloudrobo-asset/` | ☐ |
| AC-51 | Credentials read from environment variables | Check docs reference `HUAWEI_CLOUD_AK`/`HUAWEI_CLOUD_SK` | ☐ |
| AC-52 | Mutating operations require user confirmation | Check SKILL.md Parameter Confirmation section | ☐ |

### Documentation 文档

| # | Criterion | Verification | Status |
|---|-----------|--------------|--------|
| AC-53 | SKILL.md has valid frontmatter | `grep '^---$' skills/ai/cloudrobo/huawei-cloud-cloudrobo-asset/SKILL.md` | ☐ |
| AC-54 | Frontmatter has name + description + tags | Check frontmatter fields | ☐ |
| AC-55 | Description includes `Triggers include:` | `grep 'Triggers include:' skills/ai/cloudrobo/huawei-cloud-cloudrobo-asset/SKILL.md` | ☐ |
| AC-56 | All required sections present | Check Overview/Prerequisites/Workflow/Core Commands/Parameter Confirmation/Reference Documents | ☐ |
| AC-57 | Bilingual section headers | `grep '##.*概述'`, `grep '##.*前置条件'`, etc. | ☐ |
| AC-58 | references/ directory exists with required files | `ls skills/ai/cloudrobo/huawei-cloud-cloudrobo-asset/references/` | ☐ |
| AC-59 | scripts/test-cli-commands.sh exists | `ls skills/ai/cloudrobo/huawei-cloud-cloudrobo-asset/scripts/` | ☐ |
| AC-60 | templates/test-vars.json exists | `ls skills/ai/cloudrobo/huawei-cloud-cloudrobo-asset/templates/` | ☐ |

### Constraints 约束

| # | Criterion | Verification | Status |
|---|-----------|--------------|--------|
| AC-61 | Directory size ≤ 40 MB | `du -sh skills/ai/cloudrobo/huawei-cloud-cloudrobo-asset/` | ☐ |
| AC-62 | File count ≤ 30 | `find skills/ai/cloudrobo/huawei-cloud-cloudrobo-asset/ -type f \| wc -l` | ☐ |
| AC-63 | All files have allowed extensions | Check for .md/.sh/.json/.yaml/.py only | ☐ |
| AC-64 | No fabricated API paths | All paths match SDK source `_url()` calls | ☐ |

## Sign-off 签收

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Skill Author | | | |
| Reviewer | | | |
| Approver | | | |
