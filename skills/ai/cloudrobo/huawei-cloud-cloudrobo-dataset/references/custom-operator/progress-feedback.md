> Part of the custom-operator guide. Index: [custom-operator-workflow.md](custom-operator-workflow.md)

## Progress Feedback for Long-Running Steps 长等待步骤进度反馈

### Contents 目录

- Overview 概述
- Principle 原则
- Long-Running Steps Checklist 长等待步骤清单
- Task Creation: Create-Then-Poll (NOT `--wait`) 任务创建：创建后轮询
- Docker Push Progress 镜像推送进度
- Cleanup & Image Housekeeping 清理与镜像整理

### Overview 概述

Several steps in this skill take **minutes to tens of minutes**: `docker build`,
`docker push` (large images), OBS code upload, and the Phase-4 proc-task run. The
customer cannot see the terminal, so the skill **MUST** keep them informed with
periodic, timestamped progress messages — otherwise they will think the run is stuck
(deadlocked). **Never leave the customer with a silent gap longer than ~60 s.**

### Principle 原则

Every long-running step follows the same pattern:

1. **Before starting** — tell the customer what will run, how long it typically takes,
   and what the next step is.
   - 对话话术：「接下来会构建并推送算子镜像。构建约需 X 分钟，推送视镜像大小约需 Y 分钟，我会定期同步进度，请稍候。」
2. **During** — emit a progress heartbeat at least every 30–60 s: current timestamp,
   elapsed time, current phase/sub-step, and (when available) numeric progress.
3. **On completion** — report the concrete result (image digest + tag, task id +
   status, output path), then proceed to the next step.
4. **On failure/timeout** — report exactly where it stopped, what was tried, and the
   next action (see [failure-analysis-guide.md](failure-analysis-guide.md)).

### Long-Running Steps Checklist 长等待步骤清单

| Step | Typical duration | Progress signal to report |
|------|------------------|---------------------------|
| `docker build` (把代码打进镜像) | 2–10 min (heavy deps: longer) | Step N / total (docker prints `Step 1/6 ...`), per-step name; every completed step |
| `docker push` (把代码打进镜像) | 5–60+ min for 5–10 GB images | Image size first (`docker images`); then layer push progress (docker prints `layer: Pushed` per layer); estimate remaining by pushed/total layers |
| OBS code upload (代码放 OBS、运行时挂载) | seconds–minutes | File count + bytes uploaded, target OBS path |
| `create-task` + poll (Phase 4) | 2–60 min | After create: `task_id` + status `PENDING`; then every poll: status (`PENDING` / `POD_PENDING` / `RUNNING` / `SUCCEEDED` / `FAILED`) + elapsed |
| preset-image push (代码放 OBS、运行时挂载, one-off) | same as `docker push` above | same as `docker push` |

### Task Creation: Create-Then-Poll (NOT `--wait`) 任务创建：创建后轮询

**Do NOT use `--wait --timeout`.** It blocks the whole pipeline and gives the
customer no progress; worse, the agent tool may time out and abort while the task is
still running. Instead:

1. **Create without `--wait`**:
   ```bash
   cloudrobo dataset proc create-task --name <task-name> --algo-type OBS_ASSETS \
     --task-config "$(cat /tmp/task_config.json)"
   # task_id is returned in payload.id (not top-level id)
   ```
2. **Poll `show-task` with a progress heartbeat**, e.g. every 20–30 s, max ~2 h. The
   loop is extracted to **`../../scripts/poll-task.sh`**:
   ```bash
   bash scripts/poll-task.sh <task-id> [max-polls 120] [sleep-secs 30]
   # e.g. bash scripts/poll-task.sh $TASK_ID 120 30
   ```
   - Report each poll result to the customer: **对话话术**「任务 `{task_name}` 当前状态 `{status}`，已等待 {elapsed} 分钟。状态含义：PENDING=排队中，POD_PENDING=创建计算节点/拉取镜像中，RUNNING=算子运行中（转换类任务可能持续 10–40 分钟）。」
   - On `RUNNING` for a known-slow operator, extend the poll budget and reassure the
     customer (this is normal, not a hang).
3. **Verify** after `SUCCEEDED` (log + frames) — see [Phase 4](onboarding-phase-4.md) Step 4.3.

> **Alternative: `wait-task` (platform-native progress output).** `cloudrobo dataset
> proc wait-task --task-id <id> --timeout <sec> --interval <sec>` waits and prints
> every status change in real time (a built-in heartbeat). Prefer it when the
> execution tool can stream output without a hard timeout; fall back to the manual
> poll loop above when the tool may abort long-running blocking calls (which is why
> `create-task --wait` is avoided).

### Docker Push Progress 镜像推送进度

Large images (torch/lerobot ≈ 10 GB) push for a long time. Keep the customer informed:

1. **Before push** — report the local image size and the SWR target:
   ```bash
   docker images --format "{{.Repository}}:{{.Tag}} {{.Size}}" <operator-name>:<tag>
   # 对话话术：「镜像大小约 {size}，开始推送到 SWR ...。若大部分层已存在于仓库，推送会很快；全新大镜像可能需要 10–60 分钟。我会持续同步进度。」
   ```
2. **During push** — `docker push` prints per-layer lines. Because the command may be
   captured/buffered, prefer streaming it and reporting at intervals:
   ```bash
   # stream push output to a log, then tail-progress it
   docker push swr.{region}.myhuaweicloud.com/{ns}/{operator}:{tag} > /tmp/push.log 2>&1 &
   PUSH_PID=$!
   # every 30s: count Pushed layers vs total, report to customer
   #   grep -c "Pushed" /tmp/push.log ; tail -1 /tmp/push.log
   wait $PUSH_PID
   ```
   - **对话话术**：「推送中：已推送 {pushed}/{total} 个层。当前耗时 {elapsed} 分钟。`Layer already exists` 表示该层与仓库一致，无需重传（会显著缩短时间）。」
   - Many layers are usually `Layer already exists` on re-push — the delta is tiny.
3. **After push** — report the digest + tag:
   ```
   digest: sha256:...  tag: 20260924154534
   ```
   and proceed to asset registration.

### Cleanup & Image Housekeeping 清理与镜像整理

**This is a MUST-DO step after the verification ends (success or final failure)**, not
an optional extra: a single verification can leave 3–6 GB of throwaway images plus
build scratch dirs on the build host. These are local-only artifacts (no platform
impact), so **run them without waiting for customer confirmation** — except skip
anything the customer explicitly wants to keep.

The authoritative full procedure (keep the final SWR-tagged image, remove THIS run's
throwaway / probe / test images, remove THIS run's exited containers + proven dangling
images + build cache, clean THIS run's `/tmp` scratch dirs, work-copy lifecycle) lives
in [garbage-cleanup-report.md](garbage-cleanup-report.md) §Part 1A — this section only keeps the progress-related
reminders:

- **Image size/progress during cleanup** — report freed space (`docker system df`) and
  which images were removed; never go silent on long `docker image prune`.
- **Keep the final SWR-tagged image** (referenced by the algorithm asset) and the base
  image; the pushed preset-image tag is a **timestamp**
  (`{YYYYMMDDHHMMSS}`, e.g. `...:20260924154534`) — never the base-image version
  string.
- ⚠️ **Never `docker rmi` an image this run did not build** — not the algorithm-asset
  image, not the base image, and NOT any customer idle image (tagged or dangling) on a
  shared host. Every removal is digest-checked against this run's build record.
- ⚠️ Never `docker rmi` an image tag that the algorithm asset still references. If
  cleanup would remove the only local copy of a needed preset image, skip it and warn
  the customer instead. After a **FAILED** run, keep the work copy for
  `--reuse-workdir` debugging (work-copy lifecycle: [phase-boundaries.md](phase-boundaries.md) §Work Copy Lifecycle).

---