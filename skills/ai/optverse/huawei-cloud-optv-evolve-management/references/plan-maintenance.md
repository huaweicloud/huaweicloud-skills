# Plan tool maintenance experience

> ⚠️ **Reading gate**: this document covers agent-side `plan` / `scratchpad` tool maintenance (task state machines).
> - If your agent **does NOT have** `plan` / `scratchpad` tools (no task-state-machine capability): skip this document entirely.
> - If your agent **has** `plan` / `scratchpad` tools: read this once on the first multi-step task you encounter (e.g. create algorithm project → upload → start evolve), then refer back to it for later tasks.

> The main document `SKILL.md` covers hcloud / OptVerse / IAM and does not touch agent-side `plan` / `scratchpad` maintenance. This document records hands-on experience maintaining plan across multi-step tasks, for reuse in later runs.

## 1. `plan` tool semantics quick reference

`plan` is the agent-side "task-step state machine"; there is exactly one active plan per session.

| Action | Behavior |
|---|---|
| `replace_active` | Replace the whole plan (use when creating a new task / when the task direction changes significantly) |
| `update_steps` | Partially update a single step's status / title / description |
| `advance` | Mark `completed_step_id` as completed, and automatically mark the **next pending** step as in_progress |
| `get_active` | Read the current active plan |
| `clear_active` | Explicitly clear the plan |

> ⚠️ Auto-clear rule: when **all steps are `completed`**, the active plan is automatically cleared and `get_active` returns `null`. This is not a bug — by design. The plan is a "what to do next" board, not a finished log.

## 2. Recommended workflows

### 2.1 Multi-step creation tasks (e.g. create algorithm project → upload → start evolve)

1. `replace_active` to build the full step map at once (4–8 steps is appropriate);
2. After completing each step → `advance`;
3. Once all steps complete → the plan is auto-cleared → the user no longer sees history;
4. **Remediation**: `scratchpad save key=done_steps` to persist the step list; then `replace_active` to build a new plan reflecting current real state (e.g. "waiting for user trigger to query").

### 2.2 Long-running dormant tasks (e.g. only act when the user asks for progress)

Use a very small plan (1–2 steps):

- `await-user-trigger` (in_progress)
- `cleanup-tmp` (pending)

Do not artificially `advance` to make the plan "look like it's moving".

### 2.3 Failure / rollback tasks

Do **not** `clear_active` to wipe a failed plan — keep the failure state for post-mortem. Use `update_steps` to mark the failed step as `failed` with the reason in the description; after fixing it, `advance` again to resume.

## 3. Division of labor with `scratchpad` / `memory`

| Tool | Purpose | Lifetime |
|---|---|---|
| `plan` | Steps to take next (goal + step status) | active → all completed → clear |
| `scratchpad` | In-session transient state, IDs, decisions, next step | current task |
| `memory` | Long-term stable preferences / project context / general knowledge | across tasks / across sessions |

> Rule of thumb: `plan` watches the road, `scratchpad` watches the pack, `memory` watches the map.

## 4. Anti-patterns

| ❌ Anti-pattern | Why it's bad |
|---|---|
| Using plan as a log (update_steps on every action) | State becomes chaotic; everything disappears on completion |
| Advancing all steps at once to mark them completed | User can't see history, and this triggers auto-clear |
| Forcing `advance` when the task direction has changed | Use `replace_active` instead — when the goal changes, the plan must be rewritten |
| Writing AID / TID / credentials into plan steps | Plan is structured steps, not an identifier carrier; use `scratchpad` or `memory` |
| Calling `clear_active` to "reset" the plan | Loses context; `replace_active` is safer |

## 5. Failure case: recovering from a disappeared plan

**Trigger**: after several consecutive `advance` calls, the user asks "why can't I see the plan?"

**Recovery steps**:

1. `scratchpad save key=done_steps` to persist the completed step list;
2. `plan replace_active` with a new title + 1–2 steps to rebuild a plan reflecting "current real state" (task already started / waiting for user / clean up temp);
3. Briefly explain to the user: "the plan is not lost — it was auto-cleared; the completion record has been persisted".

> Don't try to "restore" the original plan — once all steps are completed it has already run its course; the new plan should face "what's next", not "what was".