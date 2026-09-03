# CLI Installation Guide

## Install hcloud CLI (KooCLI)

KooCLI supports Linux AMD 64-bit and ARM 64-bit. Check your OS architecture:

```bash
echo $HOSTTYPE
```

- `x86_64` → use AMD 64-bit commands
- `aarch64` → use ARM 64-bit commands

### Method 1: One-line Install (Recommended)

```bash
curl -sSL https://cn-north-4-hdn-koocli.obs.cn-north-4.myhuaweicloud.com/cli/latest/hcloud_install.sh -o ./hcloud_install.sh && bash ./hcloud_install.sh
```

Default install path: `/usr/local/hcloud/`, symlinked to `/usr/local/bin/hcloud`.

To skip interactive prompts with defaults:

```bash
curl -sSL https://cn-north-4-hdn-koocli.obs.cn-north-4.myhuaweicloud.com/cli/latest/hcloud_install.sh -o ./hcloud_install.sh && bash ./hcloud_install.sh -y
```

### Method 2: Step-by-step Install

**Step 1 — Download:**

AMD 64-bit:
```bash
curl -LO "https://cn-north-4-hdn-koocli.obs.cn-north-4.myhuaweicloud.com/cli/latest/huaweicloud-cli-linux-amd64.tar.gz"
```

ARM 64-bit:
```bash
curl -LO "https://cn-north-4-hdn-koocli.obs.cn-north-4.myhuaweicloud.com/cli/latest/huaweicloud-cli-linux-arm64.tar.gz"
```

**Step 2 — Extract:**

AMD 64-bit:
```bash
tar -zxvf huaweicloud-cli-linux-amd64.tar.gz
```

ARM 64-bit:
```bash
tar -zxvf huaweicloud-cli-linux-arm64.tar.gz
```

**Step 3 — (Optional) Move to PATH:**

```bash
mv $(pwd)/hcloud /usr/local/bin/
```

**Step 4 — (Optional) Enable auto-completion:**

```bash
hcloud auto-complete on
```

### Verify Installation

```bash
hcloud version
```

Expected output:
```
当前KooCLI版本:3.2.8
```

## Configure Authentication

### Method 1: Interactive Configuration (Recommended)

```bash
hcloud configure init
```

Follow the prompts to enter:
- AK (Access Key ID)
- SK (Secret Access Key)
- Default region

### Method 2: Non-interactive Configuration

```bash
hcloud configure set --cli-access-key={your_ak} --cli-secret-key={your_sk} --cli-region={your_region}
```

### Verify Authentication

```bash
hcloud ModelArts ListNotebooks --cli-region=cn-north-4 --limit=1
```

## hcloud CLI Reference

- Documentation: https://support.huaweicloud.com/qs-hcli/hcli_02_003.html
- ModelArts API Explorer: https://console.huaweicloud.com/apiexplorer/#/openapi/ModelArts
