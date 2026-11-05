# Getting Started with Huawei Cloud KooCLI

## Overview

This is the **pre-guide** for first-time KooCLI users. It walks through the complete onboarding flow that comes *before* any cloud resource operation:

1. Environment preparation
2. KooCLI installation
3. First-time authentication
4. Basic usage flow

Follow the steps in order. First-time users **must** complete this guide before constructing any `hcloud` command. If KooCLI is already installed and authenticated, skip ahead to `../SKILL.md` (Core Commands / Scenario Routing).

> **STOP - Do not answer from general knowledge.** Follow the procedure below and verify each step with the actual command output.

## 1. Environment Preparation

Confirm the following before installing KooCLI:

| Item | Requirement | Verification |
|------|-------------|--------------|
| Operating System | Linux (x86_64 / aarch64), macOS (Intel / Apple Silicon), or Windows (PowerShell, WSL supported) | `uname -a` / `echo $HOSTTYPE` |
| Huawei Cloud Account | Valid account with the required access permissions | Sign in to https://console.huaweicloud.com |
| Credentials | AK/SK pair or IAM user credentials, created in the IAM console (see `iam-policies.md`) | IAM console |
| Network | Reachable Huawei Cloud service endpoints | `curl -s https://ecs.cn-north-4.myhuaweicloud.com` |
| KooCLI Version | 7.2.2 or higher (this skill is verified against 7.2.12) | `hcloud version` |

> **Region note**: a default region applies to every command unless it is overridden per command with `--cli-region=<region>`. Not all services are available in all regions - confirm that the target service supports the target region before executing.

## 2. KooCLI Installation

KooCLI (`hcloud`) is the official Huawei Cloud command-line tool covering 100+ cloud services. Install it with the one-click installer or the per-OS package for your platform:

- Official download page (per-OS packages, checksum files, privacy statement): https://support.huaweicloud.com/qs-hcli/hcli_02_003.html
- Detailed steps for script install, package install, arm64 variants, Docker, auto-completion, PATH setup, update and uninstall: `installation-guide.md`

After installation, confirm the binary is on `PATH` and record the version:

```bash
hcloud version
```

## 3. First-Time Authentication

### 3.1 Accept the Privacy Statement (first run only)

KooCLI asks you to read and accept the privacy statement on first use, and remembers the decision in the `agreePrivacy` field of the configuration file (`~/.hcloud/config.json`; `C:\Users\<user>\.hcloud\config.json` on Windows).

```bash
# A harmless first command; read the statement when it is printed, then confirm interactively
hcloud version
```

- **Do not pipe `echo "y" |` into the command** - the statement must be reviewed before it is accepted.
- Where no interactive terminal exists, the equivalent non-interactive switch is `hcloud configure set --cli-agree-privacy-statement=true`, to be used only after the statement has actually been read.
- Privacy statement: https://www.huaweicloud.com/declaration/sa_prp.html

### 3.2 Configure Credentials (interactive)

Use the interactive wizard, which prompts for each value and masks the secret key:

```bash
# Default configuration item (interactive: AK, SK, region)
hcloud configure init

# Named configuration item for a dedicated environment/agent profile
hcloud configure init --cli-profile=<profile-name>
```

`--cli-profile` is a global option; `hcloud configure init` itself documents no other options. For non-interactive creation or modification of a named profile, use:

```bash
hcloud configure set --cli-profile=<profile-name> --cli-region=cn-north-4
```

The authentication modes (AKSK / Profile / ecsAgency / SSO / AssumeRole) and their options are documented in `../SKILL.md` (section "2. Configure koocli"); permissions and least-privilege policies are in `iam-policies.md`.

### 3.3 Non-Interactive Setup (Agent / CI Environments)

The interactive wizard needs a terminal, which agent chats and CI jobs usually do not provide. In those environments the credentials are provisioned **outside the agent conversation**, never typed into it:

```bash
# User runs this in their own terminal or CI secret step (NOT in agent chat):
hcloud configure init --cli-profile=<profile-name>

# Agent then verifies credential status only, without revealing any value:
hcloud configure list
```

Rules for non-interactive setup:

- The agent must never ask the user to paste AK/SK, and must never echo a credential value.
- Credential values must be injected by the platform, a secret manager, or the user's own terminal - not from chat. See `credential-security.md` for the approved carriers and their caveats.
- Verify with `hcloud configure list` (or `hcloud configure show --cli-profile=<name>`), which masks secret values.
- Use a temporary profile per session and remove it afterwards (`hcloud configure delete`).

### 3.4 Credential Security Rules [MUST]

- **Never pass AK/SK as command-line arguments** in chat or in an interactive shell - secrets would enter shell history.
- **Never let users input AK/SK directly in a conversation**, and never expose an AK/SK value in output or reports.
- **Only use `hcloud configure list` / `hcloud configure show` to check credential status** - both mask secret values.
- Keep the configuration file encrypted (`--cli-auth-encrypt` defaults to `true`; never set it to `false`) and restrict its file permissions.
- Prefer IAM users over the main account, and enable MFA for sensitive operations.

The full best practices (secret handling, shell history, rotation, least privilege) are in `credential-security.md` - follow that file instead of improvising.

## 4. Basic Usage Flow

After installation and authentication, verify the setup and run a first read-only command:

```bash
# 1. Verify installation and version -> prints the installed version (7.2.12 verified)
hcloud version

# 2. Confirm the configured credential status (secret values stay masked)
hcloud configure list

# 3. List the services supported by this KooCLI build
hcloud --help

# 4. List the operations of one service (help output is the authoritative source)
hcloud ECS --help

# 5. Read the parameters of the chosen operation before using it
hcloud ECS ListServersDetails --help

# 6. Run a first read-only command
hcloud ECS ListServersDetails --cli-region=cn-north-4

# 7. Format the output (json / table / tsv) and filter it with JMESPath
hcloud ECS ListServersDetails --cli-region=cn-north-4 \
  --cli-output=json --cli-query="servers[].{ID:id,Name:name,Status:status}"
```

General command format:

```bash
hcloud <service> <operation> [parameters] [options]
```

- `<service>`: cloud service name (ECS, VPC, OBS, IAM, ...)
- `<operation>`: API operation name (e.g. `ListServersDetails`, `CreateVpc`), discoverable with `hcloud <service> --help`
- `[parameters]`: operation parameters (e.g. `--server_id=i-12345678`), listed by `hcloud <service> <operation> --help`
- `[options]`: global options (`--cli-region`, `--cli-output`, `--cli-query`, `--cli-profile`, ...), listed by `hcloud --help`

> **Parameter format**: every option must be written as `--param=value`. The space-separated form (`--cli-region cn-north-4`) is rejected with a `[USE_ERROR]` whose message ends in `正确格式为:--param=value` ("the correct format is `--param=value`"), and the space-separated value is not treated as a parameter value at all - verified on KooCLI 7.2.12.

Notes on step 6-7:

- `--cli-region` and `--project_id` are required for `ListServersDetails`, but `--project_id` is derived automatically from the configured credentials and region, so it usually needs no explicit value.
- The response of `ListServersDetails` is a `servers` array, which is why the JMESPath expression starts with `servers[]`.
- These two commands query live resources and therefore require valid credentials; the skill itself never executes them on the user's behalf.

## Critical Warnings

| Trap | Why |
|------|-----|
| AK/SK must be kept secret | Never commit them to git or share them; never pass them as command-line arguments (see `credential-security.md`) |
| Default region applies to all commands | Override per command with `--cli-region=<region>` |
| Options are not space-separated | Always write `--param=value`; a space-separated `--cli-region cn-north-4` fails with `[USE_ERROR] ... 正确格式为:--param=value` |
| Some services are region-specific | Not all services are available in all regions |
| Privacy statement blocks first run | Accept it once after reading it; do not auto-answer `y` |
| Help output is authoritative | Always run `hcloud <service> <operation> --help` before constructing a command - a plausible-looking operation name may not exist (verified counter-example: `hcloud ECS ListInstances/v3` fails with a `[USE_ERROR]` "unsupported operation" message - `不支持的operation:ListInstances/v3` on a Chinese-locale build - while `hcloud ECS ListServersDetails` is valid) |
| Agent must not run setup for the user | Credential provisioning happens outside the agent conversation; the agent only guides and verifies |

## Related References

- `../SKILL.md` - Full KooCLI guidance (command construction, authentication modes, troubleshooting)
- `installation-guide.md` - Installation, update, uninstall and Docker usage
- `credential-security.md` - Credential security best practices (required reading before authentication)
- `iam-policies.md` - IAM permissions and policy configuration
- `core-commands.md` - Core command reference
- `common-workflows.md` - End-to-end operation workflows
- `cli-troubleshooting.md` - Error classification and troubleshooting
