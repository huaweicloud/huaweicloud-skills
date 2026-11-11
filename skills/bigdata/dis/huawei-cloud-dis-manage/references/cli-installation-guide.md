# KooCLI Installation and Configuration Guide

DIS operations in this skill use Huawei Cloud KooCLI (`hcloud`).

## 1. Install KooCLI

Supported platforms: Linux, macOS, Windows. KooCLI 3.x or later is required.

> The `hcloud version`, `hcloud update`, and `hcloud configure` commands in this
> section are KooCLI lifecycle/setup steps, not DIS business operations, so they
> are intentionally left unwrapped. Every `hcloud dis <Operation>` business
> command must use the `skill-quality-cli run ... --` wrapper (see SKILL.md).

| Platform | Installation |
|----------|--------------|
| Linux / macOS | Download the KooCLI package from the Huawei Cloud CLI page and add the binary to `PATH` |
| Windows | Run the installer and open a new terminal |

Verify:

```bash
hcloud version
```

Upgrade an existing installation:

```bash
hcloud update -y
```

## 2. Configure credentials

Use the interactive initializer so AK/SK are stored in the local profile and
never echoed on the command line:

```bash
hcloud configure init
```

Provide the AK, SK, region (for example `cn-north-4`), and project ID when
prompted. The profile is written to `~/.hcloud/config.json` with restricted
permissions. Do not paste credentials into scripts, documents, or chat.

Inspect the active profile (secrets are masked):

```bash
hcloud configure list
```

Show the details of a specific profile (secrets are masked):

```bash
hcloud configure show --cli-profile={profile_name}
```

Switch the active profile:

```bash
hcloud configure set --cli-profile={profile_name}
```

`configure set` switches to an existing profile. If the profile does not
exist, it starts the profile creation flow and prompts for the AK/SK, region,
and project ID.

Environment-variable credentials are supported by the Huawei Cloud SDKs; for
KooCLI prefer the encrypted local profile. In automation, inject credentials at
runtime through the platform secret store rather than committing them.

## 3. Region and project

DIS is regional. Set a default region in the profile and/or pass
`--cli-region={region}` explicitly on every command. `--project_id` is
auto-filled from the profile's parent project for the selected region; pass it
explicitly only when operating on a different project.

Common regions: `cn-north-4` (Beijing 4), `cn-north-1` (Beijing 1),
`cn-east-3` (Shanghai 3), `cn-south-1` (Guangzhou 1),
`ap-southeast-1` (Hong Kong).

## 4. Verify DIS access

```bash
skill-quality-cli run --skill-name huawei-cloud-dis-manage -- hcloud dis ListStreams --cli-region={region} --limit=5
```

Expected result: a JSON list of stream names (empty list is valid when the
tenant has no streams).

If the response is `DIS.4107 Invalid AccessKey header`:

1. Confirm the active profile is the intended account with
   `hcloud configure list`.
2. Confirm the AK/SK pair is valid (for example by calling another regional
   service such as ECS).
3. Confirm DIS is enabled for the account in that region and that the IAM user
   has the DIS permissions from `iam-policies.md`.
4. Retry with an explicitly passed `--cli-region`.

## 5. Quality telemetry

This skill relies on `skill-quality-cli`, ensured by `scripts/ensure_cli.sh`
(idempotent). Manual upgrade: `skill-quality-cli upgrade`. To disable telemetry
reporting, set `SKILL_QUALITY_REPORT=0`. DIS business operations never fail
because telemetry is unavailable.