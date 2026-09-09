# Acceptance Criteria

## Functional Criteria

### Adapter Registry

| # | Criterion | Verification |
|---|-----------|-------------|
| AC-01 | All registered hardware adapter types are discoverable | `pyproject.toml` `[project.entry-points."r2c_sdk.adapters"]` lists dummy, a1z, flexiv, jaka, lerobot, moz1, playback, q25, q25_ros2, raw_sdk, ros2, tsd, ur5e_rtde, zenoh_ros1 |
| AC-02 | dummy adapter is registered | The `r2c_sdk.adapters` entry point includes `dummy` |
| AC-03 | Registered types are usable via `hardware.type` | Robot config `hardware.type: <type>` is accepted by the `RobotConfig` schema validator |

### Config Validation

| # | Criterion | Verification |
|---|-----------|-------------|
| AC-04 | A valid robot config is accepted | `r2c client` with a valid config starts and proceeds past `load_yaml` |
| AC-05 | An invalid robot config is rejected | `r2c client` with an invalid config exits 1 with "Invalid robot config in <path>" and details |
| AC-06 | Validation reports all errors at once | Invalid config with multiple errors reports all in one `ValidationError` message |
| AC-07 | Validation checks required top-level sections | Config missing `hardware`, `translator`, `device_to_r2c`, `r2c_to_device`, or `runtime` is rejected (`schema_version` is NOT required — it is an optional, extra-allowed key) |
| AC-08 | Validation checks hardware.type | Config with unknown `hardware.type` is rejected with the list of available types |

### Robot Edge Client

| # | Criterion | Verification |
|---|-----------|-------------|
| AC-09 | Can start client with credential bundle | `r2c client --bundle <zip> --robot-config <config> --duration 5` starts and logs connection |
| AC-10 | Can start client with client config | `r2c client --client-config <yaml> --project-id <id> --device-id <id> --duration 5` starts |
| AC-11 | Heartbeat auto-published by default | Log shows "Heartbeat auto publish started" |
| AC-12 | Heartbeat can be disabled | Set `runtime.heartbeat.enabled: false`; no heartbeat logs |
| AC-13 | Client stops after --duration | Process exits after specified duration |
| AC-14 | Client stops on Ctrl+C | Graceful shutdown: hardware disconnect → session close |
| AC-15 | dry_run mode publishes observations | Log shows observation publish events |
| AC-16 | dry_run mode does not execute actions | Received actions are logged but not sent to hardware |
| AC-17 | Can record observations | `--record ./obs.pkl` produces non-empty .pkl file |
| AC-18 | Can use custom hardware class | `--hardware-class my_pkg.MyAdapter` loads custom adapter |
| AC-19 | Can use custom translator class | `--translator-class my_pkg.MyTranslator` loads custom translator |
| AC-20 | Log file rotation works | `--log-file ./r2c.log` creates rotating log file |

### Private Key Password

| # | Criterion | Verification |
|---|-----------|-------------|
| AC-21 | Prompts for encrypted key password | Encrypted bundle triggers password prompt |
| AC-22 | --no-prompt-password fails on encrypted key | Error: "password prompting is disabled" |
| AC-23 | --private-key-password-env works | Env var provides password without prompt |
| AC-24 | Unencrypted key skips prompt | No prompt for unencrypted private key |

### Cloud Adapter (out of scope)

The cloud-side OpenPI inference adapter is **not** a `cloudrobo r2c` CLI subcommand. It is a
Python module/example in the `cloudrobo-r2c` package (`inference/r2c_cloud_adapter.py`,
`examples/*_cloud_adapter.py`). This skill covers only the robot-side edge client (`r2c client`).

| # | Criterion | Verification |
|---|-----------|-------------|
| AC-25 | Cloud adapter is documented as SDK-only | Skill docs do not present `r2c cloud-adapter` as an available CLI command |
| AC-26 | Round-trip verification path documented | `references/verification-method.md` explains how to validate observation→action round-trip using the dry-run client + a cloud adapter example script |

### Connection Priority

| # | Criterion | Verification |
|---|-----------|-------------|
| AC-30 | Bundle takes priority over client-config | With both `--bundle` and `--client-config`, bundle is used |
| AC-31 | client-config takes priority over CLI params | With `--client-config` and `--project-id`, config values used |
| AC-32 | CLI params require project-id and device-id | Without bundle or config, missing `--project-id` raises error |

## Non-Functional Criteria

| # | Criterion | Verification |
|---|-----------|-------------|
| NFR-01 | No hardcoded credentials | grep SKILL.md and references for AK/SK/password patterns |
| NFR-02 | Private key password treated as sensitive | grep for password masking; never echoed |
| NFR-03 | No cross-skill invocation | grep for other skill names (robot, workspace, etc.) |
| NFR-04 | Credential bundle is device-bound | Documented in iam-policies.md |
| NFR-05 | SKILL.md frontmatter has name + description + tags | YAML frontmatter check |
| NFR-06 | description includes `Triggers include:` | grep 'Triggers include:' |
| NFR-07 | references/ files use kebab-case | filename regex `^[a-z0-9-]+\.md$` |
| NFR-08 | Total files <= 30 | find -type f \| wc -l |
| NFR-09 | Total size <= 40MB | du -sh |
| NFR-10 | All file extensions in allowed list | .md/.sh/.json/.yaml/.yml/.py/.txt etc. |
| NFR-11 | Starting client/adapter requires user confirmation | SKILL.md documents confirmation requirement |
| NFR-12 | Zenoh topic isolation documented | iam-policies.md documents topic namespace |
| NFR-13 | dry_run mode documented | SKILL.md and verification-method.md cover dry_run |
| NFR-14 | Custom adapter guide provided | references/custom-adapter-guide.md exists |

## Test Cases Summary

| Case Type | Count | Coverage |
|-----------|-------|----------|
| Adapter registry | 3 | AC-01 ~ AC-03 |
| Config validation | 5 | AC-04 ~ AC-08 |
| Robot edge client | 12 | AC-09 ~ AC-20 |
| Private key password | 4 | AC-21 ~ AC-24 |
| Cloud adapter (out of scope) | 2 | AC-25 ~ AC-26 |
| Connection priority | 3 | AC-30 ~ AC-32 |
| **Total** | **29** | Full coverage |

> The authoritative machine-readable test list for execution lives in
> `templates/test-vars.json` (all `cloudrobo r2c client` commands).
