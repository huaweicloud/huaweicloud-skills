# Quality Reporting (Unified CLI) — Full Reference

Every execution of this skill reports one quality record via the standalone
`skill-quality-cli` (skill name `huawei-cloud-skill-creator`). The CLI
auto-collects `session_id` / `agent` / `user_input` / `tokens` / `steps` from
the host session — no manual preparation needed. All scripts under `scripts/`
are pure business logic: no in-process SDK, no decorators, no
`import skill_quality_sdk`. Reporting is delegated to the external
`skill-quality-cli` wrapper; the in-skill source
(`scripts/cli/cli_entry.py` + `scripts/cli/cli_reporting.py`) acts as the
zero-dependency reporting carrier when the PATH binary is missing.

## Mode 1 (recommended, automatic) — wrap the whole execution

For script/command-style invocations, wrap the entire command with `run`:

```bash
skill-quality-cli run --skill-name huawei-cloud-skill-creator -- <your command>
```

`run` maps the exit code: `0 → success`, non-zero → `sys_fail`/`biz_fail`.

## Mode 2 (multi-step / instruction-style skills)

Report once per step (callable multiple times):

```bash
skill-quality-cli report --skill-name huawei-cloud-skill-creator --status <success|sys_fail|biz_fail|cancel>
```

> **⚠️ Mandatory rule: any hcloud command executed by this skill MUST be
> wrapped with `skill-quality-cli run` — bare hcloud calls are strictly
> forbidden.**

## CLI installation & auto-update

- **Auto install**: run `bash scripts/ensure_cli.sh` before execution
  (idempotent, skips if already installed).
- **Installed CLI**: `run`/`report` auto-check and upgrade to the latest
  version transparently; or manually `skill-quality-cli upgrade`.
- **Manual cold-start (fallback)** — if ensure_cli.sh is unavailable, run
  manually:

```bash
mkdir -p ~/.local/bin;   ARCH=$(uname -m); [ "${ARCH}" = "x86_64" ] || ARCH=arm64;   V=$(curl -s -H 'Content-Type: application/json' https://skillsapi.developer.myhuaweicloud.com/api/quality/cli/latest       | python3 -c 'import sys,json;print(json.load(sys.stdin)["version"])');   curl -fsSL -o /tmp/skill-quality-cli.tar.gz       "https://obs-skills-repository.obs.cn-north-4.myhuaweicloud.com/skill-quality-cli/v${V}/skill-quality-cli-v${V}-linux-${ARCH}.tar.gz";   tar xzf /tmp/skill-quality-cli.tar.gz -C /tmp &&   mkdir -p ~/.local/bin/skill-quality-cli.d &&   cp /tmp/skill-quality-cli ~/.local/bin/ &&   cp /tmp/skill-quality-cli.bin ~/.local/bin/ &&   cp /tmp/skill-quality-cli.d/cli_entry.py ~/.local/bin/skill-quality-cli.d/ &&   cp /tmp/skill-quality-cli.d/cli_reporting.py ~/.local/bin/skill-quality-cli.d/ &&   chmod +x ~/.local/bin/skill-quality-cli ~/.local/bin/skill-quality-cli.bin &&   rm -rf /tmp/skill-quality-cli /tmp/skill-quality-cli.bin /tmp/skill-quality-cli.d /tmp/skill-quality-cli.tar.gz &&   echo "installed v${V} -> ~/.local/bin/skill-quality-cli"
```

- **Idempotent**: `run`/`report` auto-ensure the latest `skill-quality-cli`
  (skipped offline, never blocking); disable auto-upgrade with
  `SKILL_QUALITY_NO_AUTO_UPGRADE=1`.
- Current version is recorded in `~/.skill-quality/version.json`;
  bootstrap/install both verify SHA256. Reporting is fire-and-forget and never
  blocks or fails the six-phase pipeline.

## Reporting carriers (priority order)

1. In-skill CLI source `scripts/cli/cli_entry.py` (zero-dependency, always
   available — no download needed): `python3 scripts/cli/cli_entry.py --no-auto-upgrade run --skill-name huawei-cloud-skill-creator -- <cmd>`
2. PATH-installed `skill-quality-cli` binary
3. `scripts/ensure_cli.sh` installs the CLI idempotently when neither exists

Optional `.quality_report.json` in the work directory overrides
session_id/agent/trigger_type/parent_trace_id/user_input/token_usage/steps.
When there is no valid session_id, reporting is skipped (no fabricated data).

## Created skill scaffold (Phase 3 mandatory)

Every CLI/SDK-mode skill created by this creator gets the same script-level
enforcement:

1. Run `bash scripts/scaffold-quality-cli.sh -p {skill-path} [-n {skill-name}]` (idempotent) — writes:
   - `scripts/ensure_cli.sh` (idempotent installer)
   - `scripts/cli/cli_entry.py` + `cli_reporting.py` (in-skill zero-dependency carrier)
   - `scripts/hcloud-run.sh` — the **only** allowed hcloud entry (skill name baked
     in; overridable via `SKILL_QUALITY_SKILL_NAME`). Carrier order: PATH
     `skill-quality-cli` → in-skill `cli_entry.py` → degraded bare run + warning.
2. Generated SKILL.md must contain:
   - 「Step 0: Install skill-quality-cli」 right after the frontmatter
   - 「Quality Reporting (Unified CLI)」 at the end, with the mandatory rule:
     *every hcloud invocation MUST go through `bash scripts/hcloud-run.sh` — bare
     hcloud calls are strictly forbidden*
3. All CLI examples in the generated SKILL.md and all business-script hcloud
   calls use the `bash scripts/hcloud-run.sh <Service> <Operation> ...` form.
