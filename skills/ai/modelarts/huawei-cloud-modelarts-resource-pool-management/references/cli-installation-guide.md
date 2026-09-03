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

> **⚠️ CRITICAL: Follow these security rules strictly.**

### 🔒 Security Rules (for Agent)

- 🚫 **NEVER** read, echo, or print AK/SK values
- 🚫 **NEVER** read or cat credential files (`~/.hcloud/config.json`)
- 🚫 **NEVER** ask the user to input AK/SK directly in conversation
- 🚫 **NEVER** execute `hcloud configure set` — credential configuration is the **user's responsibility**
- ✅ **ALWAYS** use `hcloud configure list` to check credential status only (presence, not values)

### ✅ How the Agent Checks Credentials

```bash
# Only acceptable check — presence only, not values
hcloud configure list
```

- ✅ **Expected**: Shows a valid profile with `mode: AKSK`
- ❌ **If empty/invalid** → Guide the user to configure in their own terminal (see below)

### 🔧 How the User Configures (One-Time Setup)

Run these commands **in your terminal**, outside the agent session:

```bash
# Step 1: Prevent the configure command from being recorded in shell history
HISTCONTROL=ignorespace

# Step 2: Configure credentials (note the leading space to skip history)
 hcloud configure set --cli-access-key=<YOUR_AK> --cli-secret-key=<YOUR_SK>

# Step 3: (Optional) For temporary credentials, also set the security token
 hcloud configure set --cli-security-token=<YOUR_TOKEN>

# Step 4: (Optional) Set language
 hcloud configure set --cli-lang=cn
```

hcloud CLI stores credentials in `~/.hcloud/config.json`. It does **NOT** support `HW_ACCESS_KEY`/`HW_SECRET_KEY` environment variables (those are for Python SDK only).

### Verify Authentication

```bash
hcloud ModelArts ListNotebooks --cli-region=cn-north-4 --limit=1
```

## hcloud CLI Reference

- Documentation: https://support.huaweicloud.com/qs-hcli/hcli_02_003.html
- ModelArts API Explorer: https://console.huaweicloud.com/apiexplorer/#/openapi/ModelArts
