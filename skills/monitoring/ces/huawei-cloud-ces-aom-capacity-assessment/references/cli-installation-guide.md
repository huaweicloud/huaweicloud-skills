# hcloud (KooCLI) Installation and Configuration Guide

All monitoring-data collection in this skill runs through Huawei Cloud CLI **hcloud (KooCLI)**; install it and configure credentials before use.

## 1. Installation

KooCLI supports multiple installation methods (see the official KooCLI user guide on Huawei Cloud):

- **Linux/macOS install script**: run the curl install script per the official docs
- **pip install**: `pip install huaweicloudcli`
- **apt/yum/rpm**: on systems with the official Huawei Cloud repo enabled, install via the package manager

Confirm the version after installation:

```bash
hcloud version
```

## 2. Configure credentials (AK/SK)

Log in with the AK/SK of the Huawei Cloud account used for collection (with CES read-only permission, see `iam-policies.md`):

```bash
hcloud configure set --cli-access-key=<AK> --cli-secret-key=<SK> --cli-region=cn-east-3
```

> The keys are stored encrypted under `~/.hcloud/`; follow the account's security policies before deploying to a production environment.
> For environment-variable mode, set `HW_ACCESS_KEY` and `HW_SECRET_KEY`.

## 3. Region

The skill automatically resolves Chinese region names in the Excel template (e.g. "华北-北京四") to `--cli-region` codes (see `region-map.md`).
The account must have permissions in the target region; otherwise an IAM error is returned, as explained in `troubleshooting-dns.md`.

## 4. Connectivity self-check

```bash
python3 <SKILL_DIR>/scripts/capacity_cli.py smoke --region cn-east-3
```

`{"ok": true}` means the environment is ready. On network/timeout errors, follow `troubleshooting-dns.md` to diagnose DNS intranet-IP issues.