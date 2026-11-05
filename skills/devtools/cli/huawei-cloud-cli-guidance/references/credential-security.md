# Credential Security Best Practices

This document collects the security best practices for handling Huawei Cloud
credentials (Access Key / Secret Key, tokens, passwords, and profile files)
when working with KooCLI (`hcloud`). Follow these rules on every run — leaking
a credential is far more costly than any convenience gained by an inline
parameter.

**Applicable scope and capability boundary:**
- Scope: credential handling around KooCLI — how credentials are obtained,
  carried, stored, checked, rotated, and cleaned up.
- This document is **guidance only**. The skill does not execute commands on the
  user's behalf, does not request, store or print credential values, and adds
  **no new action or operation** — it only states the rules the guidance follows
  while helping with authentication configuration.
- Every `hcloud` command and option quoted below was checked against the `--help`
  output of KooCLI 7.2.12. Statements that could not be verified locally are
  marked as such.

## 1. Never Paste AK/SK in Plaintext

- **Never ask users to paste AK/SK, SK, tokens, passwords, or credential files
  into a conversation.** Credentials must be configured by the user themselves,
  outside the chat, using an interactive flow.
- **Never echo credential values in commands or command output.** When writing
  example commands that need authentication parameters, use placeholders only:
  ```bash
  hcloud <service> <operation> \
    --cli-access-key=<AccessKeyId> \
    --cli-secret-key=<SecretAccessKey> \
    --cli-region=cn-north-4
  ```
- Never run commands that dump credentials, for example `echo $ACCESS_KEY`,
  `cat ~/.hcloud/config.json`, or any secret-value read. Use
  `hcloud configure list` to check credential *status* only — it does not
  reveal secret values.
- Do **not** use `hcloud configure show` to print secrets. Its documented usage
  allows querying `secretAccessKey`, which would output the SK in plaintext:
  ```bash
  # DO NOT DO THIS - the query below can return the plaintext SK
  # hcloud configure show --cli-profile <name> --cli-output=table \
  #   --cli-query=[name,mode,accessKeyId,secretAccessKey]
  ```
- Treat debug output as sensitive. KooCLI signs requests with the AK, so
  `--debug` / `--dryrun` output can contain credential-derived material and
  must not be pasted into shared channels, reports or issue comments. (KooCLI
  7.2.12 accepts `--debug`; `--cli-debug` is **not** a valid option — it is
  rejected with `[USE_ERROR]` "incorrect parameter: cli-debug".)
- Sensitive information (AK/SK, passwords, tokens) must never appear in report
  output, logs, or issue comments.
- If a secret has already been exposed, treat it as compromised: scrub the text
  **and rotate the credential immediately** (section 4). Deleting the message or
  editing the document is not remediation.

## 2. Keep Credentials Out of Shell History

Leaking credentials into shell history is the **#1 credential leak vector**.
A command line is copied beyond the tool that consumes it: into
`~/.bash_history` (bash), `~/.zsh_history` (zsh) or the PSReadLine history file
(PowerShell), into the process argument list (readable by other local
processes), into terminal scrollback, and into CI/CD job logs.

- **Do not use inline credential parameters in interactive shells**, because
  the full command line — including the secret values — is written to shell
  history:
  ```bash
  # ❌ NEVER do this — AK/SK lands in shell history
  hcloud configure set --cli-access-key=<AccessKeyId> --cli-secret-key=<SecretAccessKey>   # prohibited
  ```
- **Use the interactive configuration wizard instead** — `hcloud configure init`
  prompts for each value and does not put the secret into shell history:
  ```bash
  hcloud configure init --cli-profile=agent-profile
  ```
- If a command needs a password or secret field (for example `adminPass` when
  creating resources), do **not** pass the plaintext value on the command line.
  Prefer local-only input or runtime injection so the value never touches shell
  history.
- In scripts, read credential values from files, environment variables, or
  `read -s` prompts instead of hard-coding them in the command line.
- When you must use inline values in a script, prefix the command with a space
  (`HISTCONTROL=ignorespace` in bash) or run it with history disabled, and make
  sure the secrets are not echoed anywhere.
- **Disposal if a secret has already been typed:**
  1. Remove the entry from the current session and from the history file: bash
     `history -d <n>` plus scrubbing `~/.bash_history`; zsh cleanup of
     `~/.zsh_history`; PowerShell `Clear-History` plus removal of the offending
     line in `(Get-PSReadLineOption).HistorySavePath`.
  2. Stop recording before a sensitive command if the tool cannot avoid a
     command line: bash `set +o history`, or rely on `HISTCONTROL=ignorespace`
     with a leading space.
  3. Treat the cleanup as best-effort only — backups, synced dotfiles,
     scrollback and CI logs may still hold the value. **Rotate the credential
     immediately** and revoke the old one (section 4).

## 3. Prefer `hcloud` Profiles or Environment Variables

KooCLI stores configured credentials in `~/.hcloud/config.json` (per profile)
rather than reading them from individual command lines. Prefer one of the
following managed ways:

### Profile Mode (recommended for KooCLI)

Create a dedicated profile once, then reference it by name — secret values never
appear in daily commands:

```bash
# Create a profile (interactive, prompts for AK/SK/region)
hcloud configure init --cli-profile=agent-profile

# Check credential status (never reveals secret values)
hcloud configure list

# Use the profile in commands
hcloud <service> <operation> \
  --cli-profile=agent-profile \
  --cli-region=cn-north-4 \
  --cli-output=json
```

- `--cli-profile` is a global KooCLI option (listed in `hcloud --help`).
  `hcloud configure init --help` itself documents no options and its default
  target is the configuration item `default`; to add or modify a **named**
  profile non-interactively you can also use
  `hcloud configure set --cli-profile=<name>` (verified option).
- Keep the configuration file encrypted: `--cli-auth-encrypt` defaults to
  `true`; never set it to `false`. Restrict the file permissions (for example
  `chmod 600 ~/.hcloud/config.json`) and never copy it to a shared location.
- Use one independent profile per environment (`dev`, `test`, `prod`) and clean up
  temporary profiles after an agent session finishes (see section 4).

### Environment Variables (platform / CI pipelines)

Environment variables (`HW_ACCESS_KEY` / `HW_SECRET_KEY`, or the equivalents
provided by your platform) are a convenient option in agent platforms,
devspaces, and CI pipelines, where the values are injected by the platform
instead of being typed into the command line. The Huawei Cloud SDK convention
for the same purpose is `HUAWEICLOUD_SDK_AK`, `HUAWEICLOUD_SDK_SK`, and
`HUAWEICLOUD_SDK_SECURITY_TOKEN` (the last one accompanies temporary AK/SK).

> **Note for KooCLI 7.x:** KooCLI itself reads credentials from
> `~/.hcloud/config.json` profiles. `HCLOUD_ACCESS_KEY` / `HCLOUD_SECRET_KEY`
> environment variables are **not** read by KooCLI 7.x. Environment-variable
> injection only works when your platform/tooling (for example
> `huaweicloud-devkit` or the CI runner) picks the variables up and forwards
> them to KooCLI. When in doubt, configure a profile instead.
>
> The same caution applies to `HUAWEICLOUD_SDK_AK` / `HUAWEICLOUD_SDK_SK` /
> `HUAWEICLOUD_SDK_SECURITY_TOKEN`: they are consumed by Huawei Cloud
> SDK-based tooling, not by the KooCLI binary (verified: `hcloud --help` does not
> document them, and KooCLI 7.2.12 contains no such environment-variable name).
> Use them only where the tooling that runs your command actually reads them,
> inject them at runtime instead of exporting literals in an interactive shell,
> and unset them when the job finishes.

### Explicit Parameter Mode (one-off commands only)

Passing `--cli-access-key` / `--cli-secret-key` inline is acceptable only for
one-time commands outside an interactive shell (for example in CI), and the
values must come from a secure source — never from chat, and never typed into an
interactive terminal where they would enter shell history.

### Other approved authentication carriers

Use exactly one authentication method per call; prefer these over a long-lived
AK/SK whenever they fit the scenario.

| Method | Command / option (verified) | Applicable scenario |
|--------|-----------------------------|---------------------|
| SSO login | `hcloud configure sso` (`--cli-operate` accepts `login` or `logout`; `--cli-profile` selects the target) | Human access through IAM Identity Center; no long-lived AK/SK kept on disk |
| ECS agency | `--cli-mode=ecsAgency` | Workloads on an ECS instance that has a delegation configured; temporary AK/SK and SecurityToken are obtained automatically |
| AssumeRole | `--cli-mode=AssumeRole` with `--cli-agency-domain-id` / `--cli-agency-domain-name`, `--cli-agency-name`, `--cli-source-profile` | Cross-account delegation with short-lived access; the source profile must already exist and must differ from the current profile |
| Temporary credentials | `--cli-security-token` together with temporary AK/SK | Sessions issued by STS/agency; the token expires, so re-issue it instead of extending it |

Keep `--cli-skip-secure-verify` disabled (documented as not recommended), and do
not disable HTTPS certificate verification to work around a credential problem.

## 4. Credential Rotation and Least Privilege

- **Use IAM users instead of the main account** for daily operations. Create
  AK/SK pairs under IAM users only.
- **Grant the minimum permissions required** for the task (least privilege).
  See `./iam-policies.md` for least-privilege IAM policy examples.
- **Enable MFA (Multi-Factor Authentication)** for sensitive operations and for
  IAM users that hold AK/SK.
- **Rotate AK/SK regularly** (for example every 90 days, or the interval your
  security policy requires) and immediately when a credential may have been
  leaked. Delete unused or old keys in the console
  (`My Credentials -> Access Keys`, or IAM -> Users -> Access Keys).
  When rotating: create the new key, store it through an approved method
  (section 3), verify it with a read-only call, then delete the old key — never
  leave the old key behind "just in case".
- **Use one AK/SK pair per person or service**, so a leaked key can be revoked
  without affecting everything else. Never share one credential between
  environments, accounts, or team members.
- **Prefer temporary credentials for short-lived tasks**: use an ECS agency
  (`--cli-mode=ecsAgency`), SSO login, or AssumeRole instead of a long-lived
  AK/SK where applicable.
- **Isolate environments with profiles** and always select the intended one
  explicitly (`--cli-profile dev|test|prod`). Never leave a production profile as
  the default on a shared or agent workstation.
- **Clean up temporary profiles and credentials** when the task is over, then
  verify what is left without printing secrets:
  ```bash
  # Delete one configuration item (profile) - --cli-profile is required
  hcloud configure delete --cli-profile=<name>

  # Delete all local configuration (profiles, credentials, custom parameters)
  hcloud configure clear

  # Check the remaining profiles (does not reveal secret values)
  hcloud configure list
  ```
- **Protect credential files**: keep `~/.hcloud/config.json` permissions
  restrictive (for example `chmod 600`) and never place credentials in shared
  or world-readable locations.
- **Do not store credentials in plaintext scripts or documents.** If a
  credential is suspected of leaking, rotate it immediately and remove it from
  any console, file, or history it may have appeared in.
