# CLI Installation Guide (KooCLI)

## Prerequisites

| Dependency | Version | Purpose |
|------------|---------|---------|
| KooCLI (`hcloud`) | latest | Query RMS resources and service metadata |
| Terraform | >= 1.90.0 | Validate and plan the generated IaC |
| Python | 3.8+ | Inventory processing scripts |

## Install KooCLI

```bash
# Install (curl one-liner)
curl -sSL https://cn-north-4-hwc-cli.obs.cn-north-4.myhuaweicloud.com/cli/install.sh | bash

# Verify
hcloud version
```

## Configure Credentials

Credentials are read from environment variables (**never** written into files
or command lines):

```bash
export HUAWEI_ACCESS_KEY="your-ak"
export HUAWEI_SECRET_KEY="your-sk"
```

KooCLI automatically uses `HUAWEI_ACCESS_KEY` / `HUAWEI_SECRET_KEY` (or the
standard `HUAWEICLOUD_SDK_AK` / `HUAWEICLOUD_SDK_SK`) when calling services.

Verify authentication:

```bash
hcloud Config ListAllResources --cli-region={region} --limit=1
```

## Install Terraform

```bash
# Example (Linux x86_64); adjust URL for your architecture
wget https://releases.hashicorp.com/terraform/1.9.8/terraform_1.9.8_linux_amd64.zip
unzip terraform_1.9.8_linux_amd64.zip -d /usr/local/bin/
terraform version
```

Terraform uses the same `HUAWEI_ACCESS_KEY` / `HUAWEI_SECRET_KEY` environment
variables for the Huawei Cloud provider.