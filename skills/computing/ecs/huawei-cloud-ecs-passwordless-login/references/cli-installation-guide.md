# CLI Installation Guide — huawei-cloud-ecs-passwordless-login

Required tooling for configuring passwordless SSH login via COC.

## hcloud CLI (KooCLI)

Required for all COC and IAM operations.

### Install

Download from [Huawei Cloud KooCLI](https://support.huaweicloud.com/intl/en-us/usermanual-hcli/hcli_01_001.html) or install via pip:

```bash
pip install huaweicloudsdkcore huaweicloudsdkiotda
```

For the standalone binary:

```bash
curl -fsSL -o /usr/local/bin/hcloud https://hwcloudcli.obs.cn-north-1.myhuaweicloud.com/cli/latest/hcloud_linux_amd64
chmod +x /usr/local/bin/hcloud
```

### Configure

```bash
hcloud configure init
```

Or set via environment variables:

```bash
export HW_ACCESS_KEY=<AK>
export HW_SECRET_KEY=<SK>
```

### Verify

```bash
hcloud version
hcloud configure show
```

Test connectivity:

```bash
hcloud IAM KeystoneListAuthDomains/v3
```

### Authentication Modes

| Mode | Description |
|------|-------------|
| AK/SK | Standard key-based auth via `hcloud configure init` |
| ecsAgency | ECS-mounted agency (only applicable when running on Huawei Cloud ECS) |

## SSH Client

### Verify

```bash
ssh -V
```

SSH is typically pre-installed on Linux and macOS. Windows users can use the built-in OpenSSH client (Windows 10+) or Git Bash.

## Additional Tools

| Tool | Purpose |
|------|---------|
| `ssh-keygen` | Generate SSH key pairs (bundled with SSH) |
| `base64` | Encode/decode script content for COC (bundled with Linux/macOS) |
| `jq` | Parse JSON responses from hcloud (optional, recommended) |
