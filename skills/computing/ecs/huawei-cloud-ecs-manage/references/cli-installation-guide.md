# CLI Installation Guide

This guide covers installing and authenticating **KooCLI (hcloud CLI)** — the only execution
dependency of `huawei-cloud-ecs-manage`. No Python SDK is required for any business command.

## 1. Install KooCLI

Install KooCLI **only from the official installation documentation** on the Huawei Cloud
support site. Follow the official steps there — download, checksum verification, and
installation are all performed by the officially documented installer/package:

- Official KooCLI installation guide (download, install and verification):
  <https://support.huaweicloud.com/qs-hcli/hcli_02_003.html>

> **Supply-chain rule**: never install by piping a remote script directly into a shell, and
> never download-then-execute an installer fetched at runtime. Use only the official KooCLI
> binary package and its official checksum verification as described in the official guide
> above. This skill intentionally documents **no** download/install commands inline — the
> official guide is the single source of truth for obtaining the CLI (supply-chain safe).

### 1.1 Verify the installation

After completing the official installation steps, confirm the CLI is on `PATH`:

```bash
hcloud version
```

Requirement: KooCLI **7.2.x or later** (all commands in this skill were verified against 7.2.12).

## 2. Authentication

Two supported modes — the skill accepts either:

### Mode A: AK/SK environment variables (recommended for agents)

```bash
export HUAWEICLOUD_SDK_AK="<your-access-key-id>"
export HUAWEICLOUD_SDK_SK="<your-secret-access-key>"   # never echo this in chat/logs
export HUAWEI_ACCESS_KEY="$HUAWEICLOUD_SDK_AK"          # hcloud aliases
export HUAWEI_SECRET_KEY="$HUAWEICLOUD_SDK_SK"
```

> **Security**: secrets are read from the environment only. Never hardcode AK/SK in scripts,
> command lines, or skill files, and never print them in outputs.

### Mode B: hcloud interactive profile

```bash
hcloud configure    # follow the prompts (mode AKSK, region, project)
hcloud configure list   # verify: must show a profile with mode AKSK and a real accessKeyId
```

## 3. Verify authentication

```bash
hcloud configure list
```

A valid profile shows `"mode": "AKSK"` and a non-empty `accessKeyId`. If the command output is
empty or shows no profile, complete Mode A or B above before running any skill command.

## 4. Skill-quality-cli (quality telemetry)

Quality telemetry is collected automatically via `skill-quality-cli`:

```bash
bash scripts/ensure_cli.sh   # idempotent: installs only if absent (no auto-upgrade)
export PATH="$HOME/.local/bin:$PATH"
skill-quality-cli version    # verify it works
```

- `ensure_cli.sh` deploys the bundled `scripts/cli/` source locally — **no runtime download**,
  no network dependency beyond the business calls themselves (supply-chain safe).
- Upgrade manually: `skill-quality-cli upgrade` (no auto-upgrade).
- Disable telemetry: `export SKILL_QUALITY_REPORT=0`.
- If the local deploy fails, the skill degrades silently (business commands still run);
  re-run `ensure_cli.sh` once back online.

## 5. Region and project

- Always pass `--cli-region={region}` (e.g. `cn-north-4`) on every command.
- `--project_id` is auto-filled from the profile when omitted; if your account spans projects,
  pin it explicitly with `--project_id={project_id}` (or `hcloud configure set --cli-project-id`).
- Global services (IAM) are not used by this skill — all commands are regional.

## Reference

- KooCLI quickstart (official installation guide): <https://support.huaweicloud.com/qs-hcli/hcli_02_003.html>
- Huawei Cloud API Explorer (for `--help` verification): <https://console.huaweicloud.com/apiexplorer>