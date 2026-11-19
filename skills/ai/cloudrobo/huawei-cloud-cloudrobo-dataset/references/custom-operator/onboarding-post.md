> Part of the custom-operator guide. Index: [custom-operator-workflow.md](custom-operator-workflow.md)

### Resume & Recovery 恢复与重试

#### Resume from Failed Phase 从失败阶段恢复

```bash
# Phase 1 completed, Phase 2 failed — resume:
# 命令编排见 ../../SKILL.md §Custom Operator Onboarding（组合 client 真实命令）
# ⚠️ 代码放 OBS 并直接挂载: Phase 3 is skipped — resume goes straight to Phase 4
```

The `--reuse-workdir` flag skips work copy creation and reuses all Phase 1
artifacts. This avoids re-copying user code and re-validating config.

#### Re-run Full Onboarding 重新执行完整上架

If the work copy is stale or config changed significantly:

```bash
# 命令编排见 ../../SKILL.md §Custom Operator Onboarding（组合 client 真实命令）
```

This creates a new work copy with a fresh timestamp.

### Interaction Rules 交互规则

The onboarding command follows these interaction rules:

1. **One user-facing question round per turn** — parallel read-only queries may prepare it, but each phase step reports before the next mutating action
2. **Display results before asking** — show build output, then ask to proceed
3. **Mutation confirmation** — Phases 2 (push) and 3 (asset creation) are
   mutating operations and require explicit user confirmation
4. **Dry-run first** — for new operators, recommend `--dry-run` before full run
5. **Error handling** — on failure, display the error, suggest fix from
   [onboarding-post.md](onboarding-post.md), offer retry or abort

### Full Onboarding Example 完整上架示例

```bash
# 1. Dry-run validation
# 命令编排见 ../../SKILL.md §Custom Operator Onboarding（组合 client 真实命令）
```

### Post-Onboarding 上架后操作

After successful onboarding, the custom operator algorithm is available in the
workspace's asset catalog. It can now be used in proc-tasks:

```bash
# List workspace assets to find the new algorithm
cloudrobo asset list-assets --type algorithm --catalog-id {workspace_catalog_id}

# Create a proc-task using the custom operator
cloudrobo dataset proc create-task \
  --name "test-custom-operator" \
  --algo-type WORKSPACE_ASSETS \
  --task-config '{"algo_entrance":"algo-xyz789ghi012", ...}'
```

See the parent skill (`huawei-cloud-cloudrobo-dataset`) for task creation details.

### Work Copy Cleanup 工作副本清理

The work copy (`/tmp/custom-operator-work-{timestamp}/`) is a **temporary directory**.
Cleanup policy:

- **Success** (Phase 4 verified): auto-clean by default after the run
- **Failure**: retained for `--reuse-workdir` resume; ask the user whether to clean now
  or keep for debugging
- `--keep-workdir` / `--clean-workdir`: retain / force-clean explicitly
- Old copies beyond `max_workdir_count` (default 10) are swept oldest-first every
  `workdir_cleanup_interval`

Cleanup only removes the work-copy directory — the user's original source directory is
never touched. With `workdir_retention: false` in `~/.cloudrobo/config.yaml`, work
copies are auto-cleaned immediately after every run (production hardening).

### Server-Side Local Junk Cleanup 服务器本机垃圾清理（必做）

After the verification ends (success or final failure), **always clean the build
host's local artifacts** — this is not optional (a single verification can leave
3–6 GB of throwaway images). **⚠️ Cleanup scope = ONLY this run's artifacts** — on a
shared Docker daemon the host may also hold the customer's own images/containers:

1. Throwaway/probe/test docker images and the local duplicate of a 代码放 OBS、运行时挂载 preset
   image (after SWR push): `docker rmi <probe>:<tag>` — digest-checked, this run's only
2. This run's exited containers + proven dangling images + build cache:
   `docker rm <recorded-id>` (or label-filtered prune) + per-ID `docker rmi` on
   proven dangling images + `docker builder prune -f` — **never** an unfiltered
   `docker container prune -f` / `docker image prune -af` / `docker system prune`
3. `/tmp` build scratch dirs & logs (`/tmp/preset-image-build/`, `/tmp/build-probe/`,
   `/tmp/preset-build.log`, `/tmp/preset-push.log`, `/tmp/current_workdir_ts`)
4. Work copy: auto-clean on success (see above); keep after a FAILED run for
   `--reuse-workdir`

Guardrails: never remove the SWR-tagged image referenced by the algorithm asset, the
base image, any image/tag/container this run did NOT create, or any file outside
`/tmp`/the work copy. These local-only artifacts need **no customer confirmation**
(unlike platform junk — see [garbage-cleanup-report.md](garbage-cleanup-report.md) §Part 1A/1B).

### Phase Boundary Summary 阶段边界速览

Every phase validates its inputs before starting; missing required information is
**asked from the user**, and every mutating operation requires **explicit confirmation**:

| Phase | Key Inputs | Must Ask When Missing | Mutation Confirmation |
|-------|-----------|------------------------|-----------------------|
| 0 Image decision | workspace_id, catalog_id, image assets list | workspace/catalog_id; docker login command only when auto-generation (from AK/SK) or login fails | — |
| 1 Code adaptation | source dir, operator_config.yaml, src/, requirements.txt | source path, config file, missing fields | — |
| 2 Build & push | work copy, docker daemon, SWR URL, login cmd | base image (pull fail), login cmd (auto-login fail) | docker push |
| 3 Asset creation | image_url, catalog_id, ext_metadata | catalog_id, image_url (do Phase 2 first) | both create-asset calls |
| 4 Runtime verification | algorithm_asset_id, input-dataset source, dataset(s), output_name | dataset source (① 空间资产-数据-新建 / ② 空间资产-数据-复用 / ③ OBS存储 direct path), dataset selection, unique output_name | create-task; Source ①: create-asset `type=dataset` + create-version + update-version RELEASE; Source ③ (OBS存储): **no dataset asset created or referenced** (direct `UDF_OBS_ASSET` entry) |

See [phase-boundaries.md](phase-boundaries.md) for the full boundary matrix.

---