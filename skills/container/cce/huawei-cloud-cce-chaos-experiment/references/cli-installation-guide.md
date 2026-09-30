# CLI Installation Guide — hcloud KooCLI & kubectl

## Overview

This skill requires two CLI tools: **hcloud KooCLI** (for Huawei Cloud API calls) and **kubectl** (for CCE cluster interaction). Both must be installed and configured before running any phase.

## hcloud KooCLI

### Installation

#### Linux (x86_64 / ARM64)

```bash
curl -fsSL https://cn-north-4-hcloud-cli.obs.cn-north-4.myhuaweicloud.com/latest/hcloud_install.sh -o hcloud_install.sh
bash hcloud_install.sh
```

#### macOS

```bash
brew install hcloud-cli
```

#### Windows

Download the installer from the [KooCLI release page](https://support.huaweicloud.com/developer-hcli/hcli_02_0001.html).

### Configuration

```bash
# 1. Set AK/SK credentials
export HW_ACCESS_KEY="your_access_key"
export HW_SECRET_KEY="your_secret_key"

# 2. Set default region (optional — can also use --cli-region per command)
export HW_REGION_NAME="<region>"

# 3. Initialize the CLI (first time only)
hcloud configure set --cli-region=<region>
```

### Verification

```bash
hcloud version
hcloud ECS ListServersDetails --cli-region=<region> --cli-output=json
```

### Command Format Standard

All hcloud commands in this skill follow this format:

```bash
hcloud <Product> <API> [parameters] --cli-region=<region> --cli-output=json
```

- `--cli-region` is **always** specified explicitly (or via `HW_REGION_NAME` env var as fallback)
- `--cli-output=json` for all commands to ensure machine-parseable output
- For batch operations (BatchStopServers, BatchStartServers), flat parameter format is used:
  - `--os-stop.servers.1.id=<id1> --os-stop.servers.2.id=<id2> --os-stop.type=SOFT`
  - `--os-start.servers.1.id=<id1> --os-start.servers.2.id=<id2>`

## kubectl

### Installation

#### Option 1: Package Manager (Preferred)

```bash
# openEuler / RHEL / CentOS
dnf install -y kubernetes-client

# Ubuntu / Debian
apt-get install -y kubectl
```

#### Option 2: CDN Binary Download (Fallback)

```bash
ARCH=$(uname -m | sed 's/x86_64/amd64/;s/aarch64/arm64/')
curl -fsSL "https://dl.k8s.io/release/v1.28.0/bin/linux/${ARCH}/kubectl" -o /tmp/kubectl_download
sleep 1 && mv /tmp/kubectl_download /usr/local/bin/kubectl && chmod 755 /usr/local/bin/kubectl
```

> If `dl.k8s.io` is unreachable, try mirrors:
> - `https://mirrors.huaweicloud.com/kubernetes-release/release/v1.28.0/bin/linux/${ARCH}/kubectl`
> - `https://mirrors.aliyun.com/kubernetes-release/release/v1.28.0/bin/linux/${ARCH}/kubectl`

### Configuration

kubectl uses the kubeconfig file obtained from CCE:

```bash
# Obtain kubeconfig from CCE cluster
hcloud CCE CreateKubernetesClusterCert \
    --cluster_id=<cluster_id> \
    --cli-region=<region> \
    --duration=30 \
    --cli-output=json > /root/.kube/config
```

All kubectl commands in this skill use the `KUBECONFIG` environment variable:

```bash
KUBECONFIG=/root/.kube/config kubectl get nodes
```

### Verification

```bash
kubectl version --client
kubectl get nodes
```

## Common Issues

| Issue | Cause | Solution |
|---|---|---|
| `hcloud: command not found` | Not installed or not in PATH | Re-run installer or: `export PATH=$PATH:~/hcloud-cli` |
| `kubectl: command not found` | Not installed | Run `check_env.sh` for auto-install, or install manually |
| `InvalidAccessKey` | AK/SK not set or incorrect | Verify `HW_ACCESS_KEY` and `HW_SECRET_KEY` env vars |
| `Region not found` | Invalid region ID | Use a valid region (e.g., `cn-north-4`, `cn-east-3`) |
| `Unable to connect to server` | kubeconfig expired or invalid | Re-run `CreateKubernetesClusterCert` to obtain fresh kubeconfig |
| `Text file busy` | Corrupt kubectl binary | Remove and reinstall: `rm /usr/local/bin/kubectl && dnf install -y kubernetes-client` |
| Permission denied | IAM policy missing required actions | See `iam-policies.md` for required permissions |

## References

- [KooCLI Documentation](https://support.huaweicloud.com/developer-hcli/hcli_01_0001.html)
- [KooCLI Download](https://support.huaweicloud.com/developer-hcli/hcli_02_0001.html)
- [kubectl Documentation](https://kubernetes.io/docs/reference/kubectl/)
- [CCE Cluster Connectivity](https://support.huaweicloud.com/usermanual-cce/cce_01_0028.html)
