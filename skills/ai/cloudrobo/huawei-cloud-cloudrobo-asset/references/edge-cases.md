# Edge Cases 边界情况

| Scenario | Handling |
|----------|---------|
| Missing `catalog_id` | Execute "Prerequisite: Get catalog_id" workflow — prefer `cloudrobo workspace current` → `asset_catalog_id`; fallback to list-repositories → list-catalogs |
| `show-asset`/`show-catalog`/`show-version` non-existent ID | `ResourceNotFoundError` raised by SDK when asset/catalog/version does not exist |
| `create-asset` duplicate name in same catalog | `ResourceConflictError` raised by SDK when asset name already exists |
| `import-asset` OBS upload fails | `RuntimeError` raised; asset and version already created (Mode 1/2) but file not uploaded; version stays in `CREATING` status; reuse `--asset-id --version-id` to retry upload (uploads directly, same-name OBS objects are overwritten idempotently; transitions to `DRAFT` once upload succeeds) |
| `export-asset` no versions | RuntimeError "No versions found for asset {asset_id}" |
| `export-asset` local_path not found | FileNotFoundError "Local path does not exist: {local_path}" — export-asset requires the target directory to exist (it creates a subdirectory `{local_path}/{asset_id}/` inside it) |
| `export-asset` local_path is a file | ValueError "Local path must be a directory, not a file: {local_path}" |
| `export-asset` no `data_read` permission | Export not allowed; inform user |
| `export-asset` with `type=image` | Client raises ValueError "does not support image assets" — image is a SWR reference, no downloadable files |
| `export-asset` with `type=algorithm` | Downloads code from version detail's `ext_metadata.code_dir` OBS path (not from `url` field which is null). If `code_dir` is missing or invalid, raises RuntimeError with recovery guidance: "Algorithm asset ... has no code_dir in ext_metadata. This usually means the algorithm was created but code upload failed or was skipped. Use import-asset with --asset-id and --version-id to upload code first." |
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
| `import-asset` with `type=image` | CLI raises UsageError "image assets are not supported by import-asset. Use cloudrobo asset create-asset instead." — image is a SWR reference, no local code upload semantics |
| `import-asset` with `type=algorithm` (new asset) | CLI requires `--tags` (allowed: Data Processing/Train); creates asset with placeholder code_dir `{catalog.url}/pending`, uploads code to `{catalog.url}/{asset_id}/{version_id}/`, then updates both asset-level and version-level ext_metadata code_dir to actual path (clears placeholder `pending`); user must NOT provide code_dir/boot_file |
| `create-asset` algorithm/image without tags | Client raises ValidationError "tags is required for type 'algorithm'/'image'" (task scenario tag constraint, aligns with backend checkTags) |
| `import-asset` new version without ext_metadata (non-algorithm) | Client raises ValueError "ext_metadata is required to create a new version for type 'X' asset" — backend requires ext_metadata on version creation for model/dataset/image/simulation |
| `create-asset`/`import-asset` with `type=algorithm`\|`image` and sub_type | Client actively drops sub_type for algorithm/image (backend no longer uses it); no error raised, sub_type not sent to backend |
| `create-asset` algorithm tags not subset of referenced image tags | Client raises ValidationError "tags mismatch: algorithm tags ... must be a subset of ..." — algorithm tags must be a subset of referenced image (engine.asset_id) tags |
| `update-asset` algorithm/image tags to empty | Client raises ValidationError "tags cannot be empty for type 'algorithm'/'image'" |
| `import-asset` algorithm upload fails | Asset created with placeholder code_dir; code not uploaded; version stays in `CREATING`; retry with `--asset-id --version-id` (reuse version, uploads directly) then code_dir updated on success |
| `import-asset` algorithm Mode 2 (asset_id only) | Gets catalog_id from asset detail (user does NOT pass --catalog-id); creates new version, uploads code to `{catalog.url}/{asset_id}/{version_id}/`, updates code_dir. **ext_metadata is required**: not passing ext_metadata raises ValueError "ext_metadata is required to create a new version for algorithm asset"; passing invalid ext_metadata (missing engine/command) raises ValidationError |
| `import-asset` algorithm Mode 3 (asset_id + version_id) | Raises ValueError "Reuse version (asset_id + version_id) is not supported for algorithm assets" — algorithm supports Mode 1 (new asset) and Mode 2 (new version) only |
| `import-asset` Mode 3 ignores frontmatter | When `--asset-id` and `--version-id` are both provided, description/status/tags/version/ext_metadata/parent_asset_version_id/generation_method from frontmatter are ignored (version already exists). Mode 3 uploads files directly (same-name OBS objects are overwritten idempotently). After upload, if version status is `CREATING`, auto-updates to `DRAFT` |
| `import-asset` Mode 3 SDK layer rejects image | SDK layer (not just CLI) rejects image assets with ValueError "import_asset does not support image assets. Image assets are SWR references with no local code upload semantics." — protects SDK callers bypassing CLI |
| `export-asset` README.md already exists | Preserves existing body content, replaces frontmatter only |
| Algorithm info | Dynamically fetched; do not hardcode algorithm lists or asset_ids |
| `capabilities` filter | Only effective for `type=model`; maps to actions: `training`→[PRETRAINING,FFT,LORA], `inference`→[ONLINE_DEPLOYMENT], `reinforcement_learning`→[LIBERO_*] |
| Cross-skill invocation | This skill does not call other skills by name; does not handle training, inference, or dispatch |
| Mutating operations | create/update/delete/import/export/batch-delete should be confirmed by the user |
