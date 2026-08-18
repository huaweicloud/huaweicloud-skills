# Agent Protocol — 凭证请求协议

> 本文件由 SKILL.md 拆分而来, 记录 AK/SK 凭证缺失时的处理协议。
> 核心规则: 禁止向用户索要 AK/SK 明文, 引导用户带外配置环境变量后重跑。

## Agent Protocol — Credential Request

When Phase 4 or Phase 6 needs to call live Huawei Cloud APIs but cannot find
credentials in the environment, the framework does **not** silently skip. It
emits a structured request and exits with a sentinel code so the calling
agent is forced to surface the need to the user — **but the agent must not
ask the user to type or paste AK/SK in chat**. The user must set the
variables in their shell profile out-of-band.

**Sentinel string** (emitted to stderr, one line):
```
__HUAWEI_SKILL_TESTER_CRED_REQUEST_v1__
```

**Exit code**: `77`

**Agent response protocol** (MUST follow):

1. **Detect**: When running the test framework (directly or via
   `run-test-pipeline.sh`), catch exit code `77` OR the sentinel line in stderr.
2. **Pause**: Stop further pipeline execution. Do not skip ahead to Phase 5/7 —
   that would silently produce a "passing" report without live API coverage.
3. **Output the template**: Read the env-var setup template that the framework
   already emitted to stderr (the block beginning with
   `===== copy from here =====`) and output it to the user **verbatim**. Tell
   the user to fill in `<your-access-key-id>` and `<your-secret-access-key>`
   in their shell profile / PowerShell `$PROFILE` (out-of-band, NOT in chat).
4. **Never ask for AK/SK in chat**: Forbidden actions include
   `ask_user`, `read -p`, any web form, any clipboard paste back to the agent,
   any inline `read` loop, or any path through `~/.hcloud/config.json` /
   `~/.aliyun/config.json` / `~/.aws/credentials` that the user might
   silently trust.
5. **Re-run**: Once the user confirms they have set env vars out-of-band, the
   agent simply re-runs the failing phase:
   `HUAWEI_ACCESS_KEY=<your-access-key> bash run-test-pipeline.sh --skills <name> --phase 4`
   (the user is expected to have `export`-ed the vars in the shell where the
   agent executes the command).
6. **If the user declines**: Surface the decline to the human, do NOT mark
   Phase 4/6 as `pass`. You may abort the whole test, or report a partial run
   explicitly tagged "live phases skipped — no credentials".

**Direct-terminal mode (no agent)**: If a human runs the script directly from
a real terminal (`[ -t 0 ]` is true), the framework still emits the template
to stderr and exits 77 — the user runs the same `export HUAWEI_ACCESS_KEY=<your-access-key>`
in their shell and re-invokes the script. **There is no inline `read`
prompt path any more.** The TTY prompt used to exist for human convenience
but was removed because (a) it can leak values through terminal scrollback
and clipboard, (b) it is inconsistent with the agent protocol, and (c) it
violates the "no in-session secret entry" rule used elsewhere in the
Huawei Cloud skill ecosystem.

**Example agent behavior**:

```text
> bash run-test-pipeline.sh --skills rds-query
... Phase 0-3 pass ...
[Phase 4] __HUAWEI_SKILL_TESTER_CRED_REQUEST_v1__
[Phase 4] HUAWEI_CREDENTIALS_REQUIRED
[Phase 4] exit code: 77
<agent detects 77, pauses run>
<agent outputs the env-var template verbatim to the user, with a one-line instruction>
<user opens their shell, pastes the export HUAWEI_ACCESS_KEY=<your-access-key> lines, re-runs>
<agent re-runs: bash run-test-pipeline.sh --skills rds-query --phase 4>
```

**Rationale**: The test framework's job is to actually verify the skill
against the real cloud, not to produce green checkmarks from offline analysis
alone. Silently skipping live tests would let a broken skill pass. The
sentinel + exit code is a hard "stop and ask" signal so the human is always
in the loop for live-credential decisions — but the only safe way to handle
credentials is to keep them out of the in-session channel entirely.

