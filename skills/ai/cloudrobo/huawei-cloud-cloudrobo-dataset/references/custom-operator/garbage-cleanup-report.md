> Part of the custom-operator guide. Index: [custom-operator-workflow.md](custom-operator-workflow.md)

## Garbage Cleanup & Verification Report 垃圾清理与验证报告

### Contents 目录

- Overview 概述
- Part 1A: Server-Side Local Junk Cleanup 服务器本机垃圾清理（必做）
- Part 1B: Platform Garbage Cleanup 平台垃圾数据清理（询问制）
- Part 2: Verification Report 验证报告（Markdown）
- Relationship 与现有章节的关系

### Overview 概述

Every verification run leaves artifacts in two places: **on the CloudRobo platform**
and **on the build host (server)**. Both must be handled when the verification ends.

**Platform artifacts** (require customer confirmation to delete):

- **Failed proc-tasks** (`FAILED` status) — records of every failed attempt
- **Target dataset assets auto-created by failed tasks** — `create-task` pre-creates
  the output asset (`BUILD_IN_ASSET`) even when the task later fails; these stay as
  `DRAFT`/`CREATING` datasets
- **Historical output datasets** — each successful run also leaves an
  `{operator}-output-{timestamp}` dataset; repeated verifications accumulate them
- **Local work copies** — `/tmp/custom-operator-work-*` (see the work-copy lifecycle)

**Build-host (server) artifacts** (**MUST be cleaned automatically** — they are not
platform assets, only consume server disk):

- Throwaway local Docker images (network probe/test images, local duplicate of a Mode
  B preset image after SWR push, 把代码打进镜像 intermediate tags) — **only this run's**
- Exited containers + dangling images + build cache — **only this run's** (see Part 1A
  safe command set; never blanket `container prune` / `image prune -af` / `system prune`)
- `/tmp` build scratch dirs & logs, and the work copy (on success) — **only this run's**

After verification ends (success or final failure), the skill **MUST execute the
cleanup steps below — cleanup is a mandatory Phase 5 of the onboarding workflow,
NOT optional and never silently skipped**:

1. **Server-side local junk cleanup 服务器本机垃圾清理（必做，无需询问）** — always
   executed, no customer confirmation needed (safe local-only artifacts; see Part 1A)
2. **Platform garbage cleanup 平台垃圾清理（询问制，必问）** — delete this run's
   failed-task junk (and, if the customer wants, stale historical outputs); **the
   cleanup question MUST be asked at the end of every verification** — never finish a
   run without asking (see Part 1B)
3. **Verification report** — generate a concise `verification-report.md` documenting
   the verification result (**only useful information; trial-and-error attempts are
   NOT shown**); ask first

> **⚠️ Completion checklist — every verification run (success OR failure) must reach
> this state before the skill considers the task done:**
>
> | Step | Action | Trigger |
> |------|--------|---------|
> | 1 | Part 1A server-side local junk cleanup (this-run-only docker cleanup, `/tmp` scratch, work copy) | **Always** — no confirmation needed, never skip; scope = this run's artifacts only, customer images/containers untouched |
> | 2 | Part 1B platform junk cleanup question (failed tasks + stale output assets list, then delete on confirmation) | **Always ask** — never finish without asking |
> | 3 | Part 2 verification report (optional, ask first) | Ask |
>
> Missing any of the three means the onboarding workflow is **incomplete**. Failed
> task records (`FAILED` status) and their auto-created target dataset assets are
> platform junk and **must be listed + confirmed + deleted** per Part 1B.

### Part 1A: Server-Side Local Junk Cleanup 服务器本机垃圾清理（必做）

#### Principles 原则

- **Always run after the verification ends** (success or final failure) — this is NOT
  optional and does NOT need customer confirmation (these artifacts only consume build
  host disk; they are not platform assets and deleting them cannot affect the
  onboarded operator or its outputs).
- **Never remove:** the SWR-tagged image the algorithm asset references, the base
  image, the work copy after a **FAILED** run (keep for `--reuse-workdir`), or any
  file outside `/tmp` / the work copy. If the customer wants to keep a local copy of
  the built/preset image, skip its removal.
- **⚠️ Scope = ONLY this verification's artifacts.** On a shared Docker daemon the
  build host may hold the customer's own images, containers, and caches. Every
  cleanup below is limited to artifacts **proven to be produced by THIS run**:
  - **Never `docker rmi` / `docker image prune` a tagged image that this run did not
    build** (covers all customer idle images, tagged or untagged). Before deleting a
    throwaway tag, verify with `docker image inspect <tag> --format '{{.Id}}'` that
    its digest matches the build record; otherwise skip and warn.
  - **Never run an unfiltered `docker container prune -f`** — it removes EVERY exited
    container on the host, including the customer's. Remove only containers whose IDs
    were recorded by this run (`docker rm <id>`), or use
    `--filter label=cloudrobo-verification=<run-id>` when labels were set at `docker run`.
  - **Dangling-image precheck:** run `docker images --filter dangling=true` FIRST and
    inspect the list. Only delete dangling images whose ID/digest is provably from this
    run (usually none — every build product is tagged). Any dangling image of unknown
    origin is kept and reported to the customer — never blanket-pruned.
  - **`docker builder prune` is safe** for image data (it only clears build cache, no
    image is removed; rebuilds are slower afterwards but no data is lost). Note Docker
    has no "created after" filter for prune — `--filter until=<t>` removes OLDER
    entries, so it does NOT narrow cleanup to this run's cache; on a shared daemon the
    cache is expendable either way.

#### Commands 命令

```bash
RUN_ID=<workdir timestamp, e.g. custom-operator-work-20260924154534>

# 0. READ-ONLY precheck — list what exists BEFORE deleting anything
docker images --filter dangling=true --format '{{.ID}}  {{.CreatedSince}}  {{.Size}}'   # dangling-image inventory
docker ps -a --filter status=exited --format '{{.ID}}  {{.Image}}  {{.Names}}'          # exited-container inventory

# 1. throwaway / probe / test images + local preset duplicate (after SWR push) —
#    delete ONLY tags this run built; verify digest first
docker image inspect <probe-image>:<tag> --format '{{.Id}}'   # must equal the recorded build digest
docker rmi <probe-image>:<tag> 2>/dev/null || true
docker image inspect <operator>:fix --format '{{.Id}}'        # same digest check
docker rmi <operator>:fix <operator>:<tmp-tag> 2>/dev/null || true

# 2. exited containers — ONLY this run's containers (recorded IDs or label filter);
#    NEVER `docker container prune -f` without a filter
docker rm <recorded-container-id> 2>/dev/null || true
# or, if containers were started with --label cloudrobo-verification=$RUN_ID:
docker container prune -f --filter "label=cloudrobo-verification=$RUN_ID" 2>/dev/null || true

# 3. dangling images — delete ONLY dangling IDs whose digest matches a build record
#    from this run (per the precheck); unknown-origin dangling images are KEPT and
#    reported. NOTE: `docker image prune` (with or without --filter) targets ALL
#    dangling images on the host — prefer per-ID `docker rmi <id>` over blanket prune.
docker rmi <proven-dangling-image-id> 2>/dev/null || true   # only after digest match
# do NOT run `docker image prune -f` on a shared daemon unless the precheck list is
# empty or every entry is proven to belong to this run

# 4. build cache — SAFE: `docker builder prune` removes NO image, only rebuild cache;
#    rebuild cost is the only side effect, so it may run unfiltered
docker builder prune -f 2>/dev/null || true

# 5. /tmp — ONLY this run's named scratch dirs & logs; never rm anything else in /tmp
rm -rf /tmp/preset-image-build /tmp/build-probe 2>/dev/null || true
rm -f /tmp/preset-build.log /tmp/preset-push.log /tmp/current_workdir_ts 2>/dev/null || true
# work copy: success → auto-clean; FAILED → keep for --reuse-workdir
```

> **⚠️ Anti-mis-deletion rules (apply to every command above):**
> - **Never delete a tagged image this run did not build** — a customer's idle tagged
>   image is NEVER a cleanup target, even on a shared build host.
> - **Never run an unfiltered `docker container prune -f` / `docker image prune -af` /
>   `docker system prune`** — these delete customer artifacts wholesale.
> - **Dangling images of unknown origin are always kept**, never blanket-pruned; list
>   them for the customer instead.
> - When in doubt (shared daemon, can't prove ownership), **skip and warn** rather than
>   delete.

> Full command list & guardrails: [progress-feedback.md](progress-feedback.md) §Cleanup & Image Housekeeping
> Housekeeping.

### Part 1B: Platform Garbage Cleanup 平台垃圾数据清理（询问制）

#### Cleanup Principles 清理原则

- **Only delete what THIS skill's verification produced** — never delete:
  - the operator's **algorithm asset** and **image asset** (the onboarding deliverable)
  - the customer's own input datasets
  - the **current successful** output dataset (it is the verification deliverable;
    keep it unless the customer explicitly asks to remove it)
- **Every deletion is confirmed with the customer** (list exactly what will be
  deleted: names + IDs, then ask 确认)
- **⚠️ Verify BEFORE every delete** — `show-asset` / `show-task` must confirm ALL of:
  (a) the object was created **by this verification run** (name prefix
  `{operator}-proc-*` / `{operator}-output-*`, `algo_name` = operator, creation time
  within this run's window), (b) owner = current user, (c) name does **not** match the
  operator's algorithm/image asset names. Any mismatch → **skip and warn**, never
  delete an unverifiable object (a name-prefix match alone is NOT proof of ownership —
  a customer dataset could coincidentally be named `{operator}-output-*`).
- Cleanup targets, by category:

| Junk category | How to find it | 必做校验（任一不符 → 跳过并警告） | Delete command |
|---------------|----------------|-----------------------------------|----------------|
| Failed proc-tasks | `cloudrobo dataset proc list-tasks` → `status=FAILED` created by this verification (name `{operator}-proc-*`, `algo_name` = operator) | `show-task --task-id` → name = `{operator}-proc-*`, `algo_name` = operator, owner = current user, created within this run | `cloudrobo dataset proc delete-task --task-id <task_id>` |
| Target asset of a failed task | the failed task's `target_asset_id` / `target_asset_name` (from `show-task`) | `show-asset --asset-id` → name = the failed task's `target_asset_name`, owner = current user, created within this run, name ≠ operator's algorithm/image asset | `cloudrobo asset delete-asset --asset-id <asset_id>` |
| Stale historical output datasets | `cloudrobo asset list-assets --catalog-id <id> --type dataset` → name matches `{operator}-output-*`, older than the current run | 逐条 `show-asset` → name = `{operator}-output-*`, owner = current user, created before the current run (NOT the customer's own dataset) | `cloudrobo asset delete-asset --asset-id <asset_id>` |
| Local work copies | `/tmp/custom-operator-work-*` | 目录时间戳 = 本次验证的 workdir（绝不清理客户自建目录） | work-copy lifecycle (`--clean-workdir` / retention rules) |

> **Why failed tasks leave junk:** `create-task` pre-creates the output asset
> (`target_asset_id` / `target_asset_name`) at submission time. If the task fails, the
> asset stays as `DRAFT` (or `CREATING`) forever — delete it together with the failed
> task record.

#### Cleanup Flow 清理流程

**On failure (before fixing & re-running):** ask the customer whether to delete the
failed task + its target asset **now**:
- 对话话术：「本次任务失败。是否需要我先清理这条失败任务及其产生的目标数据集资产 `{target_asset_name}`？清理后我再根据日志修复并重新验证。是否清理？① 清理 ② 保留（先排查日志）」

**After the final verification (success or user gives up):**
1. **Server-side local junk cleanup (always, no confirmation)** — remove ONLY this
   run's throwaway docker images (probe/test images, local preset duplicate, 把代码打进镜像
   intermediate tags), this run's exited containers, proven dangling images / build
   cache, this run's `/tmp` scratch dirs & logs; on success also clean the work copy
   (safe command set — see §Part 1A §Commands):
   ```bash
   docker rmi <probe-image>:<tag> 2>/dev/null || true       # digest-checked, this run's only
   docker rm <recorded-container-id> 2>/dev/null || true    # NEVER unfiltered `docker container prune -f`
   docker rmi <proven-dangling-image-id> 2>/dev/null || true # only after precheck digest match
   docker builder prune -f 2>/dev/null || true               # cache only, no image removed
   rm -rf /tmp/preset-image-build /tmp/build-probe 2>/dev/null || true
   rm -f /tmp/preset-build.log /tmp/preset-push.log /tmp/current_workdir_ts 2>/dev/null || true
   ```
   (full list + guardrails: [progress-feedback.md](progress-feedback.md) §Cleanup & Image Housekeeping
   Housekeeping)
2. **Platform junk (confirmed)** — ask whether to clean up this run's failed attempts
   and stale outputs:
   - 对话话术：「验证流程结束。是否清理本次验证过程中产生的平台垃圾数据（失败的 N 条任务记录及其输出资产、历史的 M 个旧输出数据集 `{names}`）？清理不会删除算子的算法/镜像资产和本次成功验证的输出。① 全部清理 ② 只清理失败任务 ③ 保留」

**Verify the deletion** after each `delete-asset` / `delete-task`:
```bash
cloudrobo asset show-asset --asset-id <id>       # expect not found / 404
cloudrobo dataset proc show-task --task-id <id>  # expect not found / 404
```

#### Commands 命令

```bash
# delete a failed proc-task record
cloudrobo dataset proc delete-task --task-id <task_id>

# delete a stale/failed target dataset asset (and its versions)
cloudrobo asset delete-asset --asset-id <asset_id>

# delete a single asset version (when only the version, not the asset, is stale)
cloudrobo asset delete-version --asset-id <asset_id> --version-id <version_id>

# dry-run preview before real deletion
cloudrobo asset delete-asset --asset-id <asset_id> --dry-run
```

> **Safe-deletion guardrails:**
> - `delete-asset` removes the whole asset (all versions). Use `delete-version` when
>   only a version is stale (e.g. an intermediate image version on re-submission).
> - Never delete assets whose name matches the **operator name** (image/algorithm
>   assets) — only `{operator}-output-*` datasets and failed-task target assets.
> - Confirm again before any `delete-asset` that was auto-created by a **failed** task
>   if its `target_path` contains files the customer may want.
> - **⚠️ `show-asset` / `show-task` MUST pass before every delete** (see the table
>   above): name prefix + owner = current user + creation time within this run. A
>   name-prefix match alone is NOT proof — `{operator}-output-*` could be a customer
>   dataset. When verification fails, **skip and warn** instead of deleting.
> - **Never batch-delete** (`list-assets` → delete all matches). Confirm the exact
>   names + IDs one by one, then delete. `--dry-run` is your friend for previewing.

### Part 2: Verification Report 验证报告（Markdown）

#### Option & Prompt 选项与询问

After the final verification result is known, ask the customer (optional, default
no):
- 对话话术：「验证已结束（结果：{SUCCEEDED/FAILED}）。是否需要我生成一份《验证报告》Markdown 文档，记录本次验证的算子信息、资产信息和验证结果？报告只包含有用信息，不体现过程中的试错细节。① 生成 ② 不需要」

Only generate when the customer confirms. Report location: the work copy directory
(`/tmp/custom-operator-work-{timestamp}/verification-report.md`) — print the absolute
path and, if the customer wants, copy it next to the operator source directory
(**copying outside the work copy requires confirmation too**).

#### Content Rules 内容规范（只保留有用信息）

**MUST include (useful information):**
- Operator: name, deploy mode (把代码打进镜像 image-inbuilt / 代码放 OBS、运行时挂载 OBS-mounted), code
  location (image URL or OBS `code_dir`)
- Assets: image asset name/ID + SWR URL + version, algorithm asset name/ID +
  `engine.image_url` + `image_source`, `code_dir`
- Datasets: input dataset name/ID/obs path; output dataset name/ID + target OBS path
- Verification: task name + `task_id`, final status (`SUCCEEDED`), user-log success
  line, output frames summary, duration
- Conclusion: 通过 / 不通过 (and, on success, the output dataset as the deliverable)

**MUST NOT include (trial-and-error noise):**
- Failed attempts, error messages, fix iterations, intermediate images/tags that were
  discarded, deleted junk, or any debugging details
- Only the final, successful state (or, on failure, one final conclusion line)

#### Template 模板

Use [verification-report.md](verification-report.md) — fill every field from the actual
run; omit empty sections. Do not invent values.

### Relationship 与现有章节的关系

- Long-wait/progress heartbeat: [progress-feedback.md](progress-feedback.md) §Cleanup & Image Housekeeping
  Housekeeping (local Docker images) — this doc covers **platform** junk (tasks,
  assets)
- Work-copy lifecycle: ../../SKILL.md §Key Concepts (Work copy) & [phase-boundaries.md](phase-boundaries.md) §Work Copy Lifecycle
- Failure analysis before re-run: ../../SKILL.md §Failure Analysis & [failure-analysis-guide.md](failure-analysis-guide.md)

---