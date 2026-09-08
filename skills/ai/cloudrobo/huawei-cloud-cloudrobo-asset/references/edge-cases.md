# Edge Cases 边界情况

| Scenario | Handling |
|----------|---------|
| Missing `catalog_id` | Execute "Prerequisite: Get catalog_id" workflow — prefer `cloudrobo workspace current` → `asset_catalog_id`; fallback to list-repositories → list-catalogs |
| `show-asset`/`show-catalog`/`show-version` non-existent ID | `ResourceNotFoundError` raised by SDK when asset/catalog/version does not exist |
| `create-asset` duplicate name in same catalog | `ResourceConflictError` raised by SDK when asset name already exists |
| `import-asset` OBS upload fails | `RuntimeError` raised; asset and version already created (Mode 1/2) but file not uploaded; version stays in `CREATING` status; reuse `--asset-id --version-id` to retry upload (incremental by default — only uploads missing files; transitions to `DRAFT` once upload succeeds) |
| `export-asset` no versions | RuntimeError "No versions found for asset {asset_id}" |
| `export-asset` no `data_read` permission | Export not allowed; inform user |
| `list-assets` no repository-id or catalog-id | CLI raises UsageError |
| `show-lineage` no lineage | Returns friendly message "该资产版本没有血缘关系" |
| `create-asset` simulation without sub_type | sub_type is required for simulation type |
| `update-asset` immutable fields | Only `name`/`description`/`status`/`tags`/`ext_metadata` are modifiable — `catalog_id`/`type`/`sub_type`/`url`/`parent_asset_version_id`/`generation_method` are not exposed as CLI options or SDK parameters (fields are immutable, not client-rejected) |
| `update-version` immutable fields | Only `version`/`description`/`status`/`ext_metadata` are modifiable — `url`/`parent_asset_version_id`/`generation_method` are not exposed as CLI options or SDK parameters (fields are immutable, not client-rejected) |
| `list-publication-assets` vs `list-assets` | Built-in/official assets use `list-publication-assets` (public); workspace assets use `list-assets` (private) |
| `search-assets` type filter | Supports `simulation`/`model`/`dataset`; without type, searches all three |
| Object storage paths | Must use `obs://` protocol; `s3://` is prohibited |
| `asset_id` and `version_id` format | UUID format |
| `import-asset` README.md frontmatter | Auto-reads metadata (name, type, sub_type, description, status, tags, version, ext_metadata, parent_asset_version_id, generation_method) from `local-path/README.md` YAML frontmatter; frontmatter overrides CLI parameters (except catalog_id, CLI only); falls back to CLI if frontmatter missing or invalid |
| `import-asset` ext_metadata missing for type | model/dataset/algorithm/image/simulation require ext_metadata with specific fields (robot is sub_type of simulation); CLI raises `UsageError` before API call if missing from both frontmatter and `--ext-metadata` |
| `import-asset` frontmatter invalid YAML | If README.md exists but frontmatter is invalid YAML, `_safe_parse_frontmatter` returns `{}` silently; falls back to CLI parameters |
| `import-asset` Mode 3 ignores frontmatter | When `--asset-id` and `--version-id` are both provided, description/status/tags/version/ext_metadata/parent_asset_version_id/generation_method from frontmatter are ignored (version already exists). Mode 3 defaults to incremental upload (`overwrite=False` — skips existing OBS objects); use `--overwrite` to force re-upload all files. After upload, if version status is `CREATING`, auto-updates to `DRAFT` |
| `export-asset` README.md already exists | Preserves existing body content, replaces frontmatter only |
| Algorithm info | Dynamically fetched; do not hardcode algorithm lists or asset_ids |
| `capabilities` filter | Only effective for `type=model`; maps to actions: `training`→[PRETRAINING,FFT,LORA], `inference`→[ONLINE_DEPLOYMENT], `reinforcement_learning`→[LIBERO_*] |
| Cross-skill invocation | This skill does not call other skills by name; does not handle training, inference, or dispatch |
| Mutating operations | create/update/delete/import/export/batch-delete should be confirmed by the user |
