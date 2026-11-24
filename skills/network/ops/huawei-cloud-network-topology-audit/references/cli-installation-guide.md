# CLI Installation Guide

## Installing hcloud (KooCLI)

```bash
# Download and install (inspect the script before running it)
curl -sSL https://cn-north-4-hdn-koocli.obs.cn-north-4.myhuaweicloud.com/cli/latest/hcloud_install.sh -o ./hcloud_install.sh
bash ./hcloud_install.sh

# Verify installation
hcloud version
```

## KooCLI Command Format (Standard)

Every KooCLI call uses the same standard form, with an explicit `--cli-region`:

```
hcloud <Service> <Operation> --cli-region=<region> [--key=value ...]
```

- `<Service>` — KooCLI service name in PascalCase, e.g. `VPC`, `ELB`, `NAT`, `ECS`, `RDS`, `CCE`.
- `<Operation>` — KooCLI operation in PascalCase, e.g. `ListVpcs`, `ListClusters`.
- `--cli-region=<region>` — **required** on every call, e.g. `--cli-region=cn-north-4`.
- `--key=value` — optional request parameters in `=` form, e.g. `--limit=1`.

## Configuring Authentication

Configure the profile interactively so the AK/SK is not written into shell history or a command line:

```bash
hcloud configure set --cli-region=cn-north-4
# Enter the access key and secret key at the prompts.
```

Or export environment variables (never commit real values to the repository):

```bash
export HUAWEICLOUD_SDK_AK="<your-ak>"
export HUAWEICLOUD_SDK_SK="<your-sk>"
```

This skill also accepts `HUAWEI_ACCESS_KEY`/`HUAWEI_SECRET_KEY`, `HW_ACCESS_KEY`/`HW_SECRET_KEY`,
`HWC_AK`/`HWC_SK`, and `HWC_ACCESS_KEY`/`HWC_SECRET_KEY` — the same order used by
`scripts/precheck.sh` and `scripts/query-dcs-instances.py`.

## Verifying Authentication

```bash
# Test with a simple VPC query (note the required --cli-region)
hcloud VPC ListVpcs --cli-region=cn-north-4 --limit=1
```

## Notes

- This skill primarily relies on query skills (path A) and Python SDK scripts (path B). The
  hcloud CLI is only needed for CCE queries via the CCE cluster management skill.
- For most resource types (VPC, ELB, EIP, NAT, ECS, RDS), the Python SDK is used via query
  skills, not the CLI directly.
- When running inside the skill pipeline, wrap KooCLI calls as
  `skill-quality-cli run --skill-name huawei-cloud-network-topology-audit -- hcloud ...`.