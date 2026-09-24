# CLI Installation Guide

## hcloud CLI (KooCLI)

### Installation

Download and install from: https://support.huaweicloud.com/qs-hcli/hcli_02_003.html

### Windows

```bash
# Via winget (if available)
winget install HuaweiCloud.KooCLI

# Or download the installer from the official page
```

### Linux/macOS

```bash
# Download the binary
curl -LO https://hwcloudcli.obs.cn-north-1.myhuaweicloud.com/cli/latest/hcloud_install.sh
bash hcloud_install.sh
```

### Configuration

Configure credentials interactively (never paste AK/SK in chat):

```bash
hcloud configure
```

Or set environment variables:

```bash
export HUAWEI_ACCESS_KEY="<your-access-key-id>"
read -rs HUAWEI_SECRET_KEY; export HUAWEI_SECRET_KEY
export HUAWEI_REGION="cn-southwest-301"
```

### Verify Installation

```bash
hcloud configure list
hcloud Apm --help
```

### APM CLI Reference

Official APM CLI reference: https://support.huaweicloud.com/clir-apm/APM-cli.html

Key commands for OTel ingestion:

```bash
# Create tracing business
hcloud APM CreateBusiness --cli-region={region}

# Get business token
hcloud APM ShowToken --cli-region={region} --business_id={id}
```

### AgentArts CLI

> As of current version, AgentArts CLI namespace is not confirmed in KooCLI.
> Use API (curl) mode for AgentArts observation operations.
