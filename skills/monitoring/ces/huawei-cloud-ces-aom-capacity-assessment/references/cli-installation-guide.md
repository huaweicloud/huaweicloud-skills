# hcloud (KooCLI) Installation and Configuration Guide

All monitoring-data collection in this skill runs through Huawei Cloud CLI **hcloud (KooCLI)**; install it and configure credentials before use.

## 1. Installation

Install KooCLI **only from the official installation documentation** on the Huawei Cloud support site:

- Official KooCLI installation guide (download, install and verification):
  <https://support.huaweicloud.com/qs-hcli/hcli_02_003.html>

Follow the official steps there — download, checksum verification, and installation are all performed by the officially documented installer/package.

> **Supply-chain rule**: never install by piping a remote script directly into a shell, and never download-then-execute an installer fetched at runtime. Use only the official KooCLI binary package and its official checksum verification as described in the official guide above.

Confirm the version after installation:

```bash
hcloud version
```

Requirement: KooCLI **7.2.x or later** (all commands in this skill were verified against 7.3.12).

## 2. Configure credentials (AK/SK)

Provide the AK/SK of the Huawei Cloud account used for collection (with CES read-only permission, see `iam-policies.md`) through **environment variables**, so no secret is ever written into the shell history, a file, or the repository:

```bash
export HUAWEICLOUD_SDK_AK="$HW_AK"      # value supplied out of band, never echoed
export HUAWEICLOUD_SDK_SK="$HW_SK"
```

Check whether a usable credential source is already in place (read-only inspection):

```bash
hcloud configure list
```

> Credentials are supplied out of band (environment variables or an existing hcloud profile). Never paste AK/SK into a command line argument, a document, an issue/PR comment, or a script; rotate immediately if a key was ever exposed.
> Region can be given per call with `--cli-region` (see below), so it does not have to be stored in the credential profile.

## 3. Region

The skill automatically resolves Chinese region names in the Excel template (e.g. "华北-北京四") to `--cli-region` codes (see `region-map.md`).
The account must have permissions in the target region; otherwise an IAM error is returned, as explained in `troubleshooting-dns.md`.

## 4. Connectivity self-check

```bash
python3 <SKILL_DIR>/scripts/capacity_cli.py smoke --region cn-east-3
```

`{"ok": true}` means the environment is ready. On network/timeout errors, follow `troubleshooting-dns.md` to diagnose DNS intranet-IP issues.

## Reference

- KooCLI quickstart (official installation guide): <https://support.huaweicloud.com/qs-hcli/hcli_02_003.html>
- Huawei Cloud API Explorer (for `--help` verification): <https://console.huaweicloud.com/apiexplorer>
