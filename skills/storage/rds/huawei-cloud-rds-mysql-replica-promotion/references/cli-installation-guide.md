# CLI Installation Guide

## hcloud (Huawei Cloud KooCLI)

The `hcloud` CLI is the primary command-line tool for interacting with Huawei Cloud services.
It is the only external dependency of this skill (>= 7.2.2); the Python scripts under
`scripts/` use only the standard library.

### Installation

Download and install from the official documentation:

> https://support.huaweicloud.com/qs-hcli/hcli_02.html

**Linux / macOS:**

```bash
# Download and run the official installation script
curl -O https://cn-north-4-hdn-koocli.obs.cn-north-4.myhuaweicloud.com/cli/latest/hcloud_install.sh
bash hcloud_install.sh
# Verify
hcloud --version
```

**Windows:**

Download the `.exe` from the KooCLI documentation page and add it to the system PATH,
then verify with `hcloud --version` in a new terminal.

### Configuration

Initialize the CLI with your AK/SK credentials:

```bash
hcloud configure set --cli-access-key=YOUR_AK --cli-secret-key=YOUR_SK --cli-region=cn-north-4
```

Verify the configuration:

```bash
hcloud configure list
```

A successful JSON response from a service smoke test means authentication is configured;
a DNS or authentication error means it is not. For example:

```bash
hcloud RDS ListApiVersionNew --cli-region=cn-north-4 --project_id=<your_project_id>
```

### Upgrade

```bash
hcloud version --upgrade
```

## Python Dependencies

This skill has **no third-party Python dependencies** — `scripts/rds_common.py`,
`list_instances.py`, `list_azs.py`, `pre_check.py`, `convert.py`, `resume.py`,
`rds_cost_estimate.py` and `rds_monitor.py` use only the Python standard library
(`argparse`, `json`, `logging`, `os`, `subprocess`, `sys`, `time`, `datetime`).

```bash
# Syntax check (no install needed)
python3 -m py_compile scripts/*.py
```

> Unlike some other Huawei Cloud skills (e.g. those depending on `openpyxl` to generate
> Excel files), this skill does not need `pip install` for any third-party package.
