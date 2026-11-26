# KooCLI readiness and setup

Users install/configure hcloud locally. Read `gotchas.md` G01–G02 before checks; handle credentials per G12.

## Readiness

1. `hcloud version` confirms only the local CLI version.
2. For connection checks, read `IAM KeystoneListAuthProjects --help`, then query with `--cli-region=cn-north-1 --cli-output=json`. Success verifies only that IAM call's connectivity, authentication and read authorization; BSS pricing/create permissions need separate evidence. Select quote projects per G02, not from the endpoint region.
3. Only if the IAM call reports missing configuration, inspect `hcloud configure list`; otherwise skip.

Report version, IAM outcome and unverified scope; omit project lists and domain/project IDs. Do not infer credential type.

## User setup

Choose the OS/architecture package from the [official guide](https://support.huaweicloud.com/qs-hcli/hcli_02_003.md); reuse an existing profile. For missing configuration, the user runs `hcloud configure set` with credentials entered locally.

Check PATH for missing commands, official links for download failures, and network/proxy evidence for connection errors.
