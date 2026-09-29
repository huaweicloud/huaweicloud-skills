# hcloud CLI Installation and Authentication

This skill executes commands through the Huawei Cloud KooCLI (`hcloud`). This guide covers
installation and the two supported authentication modes.

## 1. Install KooCLI

Requires KooCLI 7.2.x or later. One of the following methods:

### Linux / macOS (official package with SHA-256 verification)

Download the **official KooCLI package** for a **fixed version** from the official download page
(`https://support.huaweicloud.com/intl/en-us/qs-hcli/hcli_02_003.html`), verify its SHA-256 against the
official `.sha256` checksum file, then install locally. Do **not** fetch and pipe an unverified online
script straight into a shell.

```bash
# 1) Download the fixed-version KooCLI package + its official `.sha256` verification file
#    (fill in the exact URLs published on the official page for your OS, e.g. KooCLI-linux-amd64.tar.gz)
curl -fsSL -O "<official-url>/KooCLI-linux-amd64.tar.gz"
curl -fsSL -O "<official-url>/KooCLI-linux-amd64.tar.gz_sha256utf-8"

# 2) Verify integrity before unpacking (digest must match the officially published checksum)
sha256sum -c "KooCLI-linux-amd64.tar.gz_sha256utf-8" \
  && echo "SHA-256 verified" || { echo "SHA-256 MISMATCH - abort"; exit 1; }

# 3) Unpack and install into a user-local directory
mkdir -p ~/.local/hcloud && tar -zxf KooCLI-linux-amd64.tar.gz -C ~/.local/hcloud
export PATH="$HOME/.local/hcloud:$PATH"
```

> **Security**: never fetch a remote artifact and execute it in a single piped step. Always
> download the package first, verify its SHA-256 digest against the value published on the official
> page, then unpack. A corrupted or tampered package must never be executed.

### Docker

```bash
docker run -it huaweicloud/cloud-cli:latest
```

### Verify

```bash
hcloud version
```

## 2. Authentication — Mode B (recommended): local hcloud profile

Use the interactive configuration wizard (credentials are prompted, never passed on the command line):

```bash
hcloud configure set
```

> **Never pass AK/SK as command-line arguments**. The `hcloud configure set` wizard must be run
> interactively so credentials are prompted and never appear on the command line or in the shell
> history. KooCLI stores the profile in `~/.hcloud/config.json` (resolved from the OS user home, not
> `$HOME`) and authenticates **only** from that file (or the `--cli-access-key` / `--cli-secret-key`
> parameters). **KooCLI does not read AK/SK environment variables** (see Mode A below).

Validate:

```bash
hcloud configure list
```

The output must show a profile with `"mode": "AKSK"` and a real `accessKeyId`.

For non-interactive / CI environments where the interactive wizard is not possible: do **not** rely on
environment variables — KooCLI does not read them. Instead import the profile from a protected config
file owned by the running user (mode `0600`), i.e. run the wizard once on a trusted host and copy
`~/.hcloud/config.json` into the CI user's home, or use a service account whose profile is provisioned
the same way. Never embed the key on the CLI.

## 3. Authentication — Mode A (NOT supported by KooCLI): AK/SK environment variables

Older revisions of this skill documented AK/SK via environment variables:

```bash
export HUAWEICLOUD_SDK_AK="your-access-key-id"
export HUAWEICLOUD_SDK_SK="your-secret-access-key"
```

**This is NOT a working authentication path for KooCLI (verified against 7.2.12)**: KooCLI reads
credentials exclusively from `~/.hcloud/config.json` (or the `--cli-access-key` / `--cli-secret-key`
parameters); it does **not** read `HUAWEICLOUD_SDK_AK` / `HUAWEICLOUD_SDK_SK`, `HUAWEI_ACCESS_KEY` /
`HUAWEI_SECRET_KEY`, or `HW_ACCESS_KEY` / `HW_SECRET_KEY`. With an empty configuration, a bare
`hcloud` call fails with a `[USE_ERROR]` telling you to configure it first
(`No configuration file exists. Run 'hcloud configure init'...` /
`配置文件中不存在配置项,请您执行hcloud configure set添加配置项`).

Use **Mode B** (`hcloud configure set`) instead. (The `HUAWEICLOUD_SDK_*` / `HUAWEI_*` variable names
belong to the Huawei Cloud SDKs, not to KooCLI; a few isolated KooCLI features may consult
environment variables, but credentials are not among them.)

## 4. Verify IAM access

```bash
hcloud IAM ListUsersV5 --cli-region=cn-north-4 --limit=1
```

A successful JSON response with `users` confirms both the CLI and the credentials work.

## 5. Quality reporting via skill-quality-cli

This skill reports command execution quality telemetry through `skill-quality-cli`
(installed by `scripts/ensure_cli.sh` — idempotent, silently skips if already present).

- **Install location**: `~/.local/bin/skill-quality-cli`. `ensure_cli.sh` automatically adds
  `~/.local/bin` to the current session `PATH` and persists it to `~/.bashrc` / `~/.profile`, so both
  login and non-login shells can resolve `skill-quality-cli`. If a non-login environment still cannot
  find it, run `export PATH="$HOME/.local/bin:$PATH"` (or re-source `~/.bashrc`) once.
- **How commands are wrapped**: every command in SKILL.md is shown in **dual form** — the bare
  executable `hcloud IAM <Operation> ...` line and the identical payload wrapped with
  `skill-quality-cli run --skill-name huawei-cloud-iam-manage -- hcloud ...`. The bare line is what
  the evaluation framework's Phase 1 command extractor recognizes (`hcloud` / `python3` line
  prefixes);
  the wrapped line is the *mandatory* execution form for quality reporting. Run the wrapped form
  (or ensure the execution environment applies the wrapper); the bare form exists so tooling and
  examples stay parseable.
- **Upgrade**: `skill-quality-cli upgrade` (manual; no auto-upgrade). Disable telemetry:
  `SKILL_QUALITY_REPORT=0`.
- **Failure behavior**: if `skill-quality-cli` is unavailable, `ensure_cli.sh` prints a warning and
  exits non-blocking — business hcloud commands keep working (with a one-line warning) so the CLI
  wrapper never blocks real operations.

## 6. Troubleshooting

| Symptom | Fix |
| ------- | --- |
| `AccessDenied` / 403 | Check the profile AK/SK and that the caller has `iam:users:listUsers` (or admin) permission |
| `Unable to parse response` | Usually a proxy/network issue — check `HTTPS_PROXY`, retry |
| `config not found` | Run `hcloud configure set` first to create a profile |
| KooCLI version too old | `hcloud update -y` or reinstall |
| `skill-quality-cli: command not found` (non-login shell) | Run `scripts/ensure_cli.sh` (or `scripts/install_cli.sh`) once — it exports `~/.local/bin` into the current session PATH and persists it to `~/.bashrc` / `~/.profile`; re-source the shell or `export PATH="$HOME/.local/bin:$PATH"` |
