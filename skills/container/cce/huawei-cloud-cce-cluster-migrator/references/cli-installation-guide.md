# CLI and Tooling Installation Guide

This guide details the prerequisites, CLI tools, and client utilities required for executing Kubernetes cluster migrations to Huawei Cloud CCE.

---

## 1. Huawei Cloud KooCLI (`hcloud`)

The Huawei Cloud Command Line Interface (KooCLI) interacts with the CCE API for cluster discovery, flavor checks, kubeconfig generation, and add-on inspection.

### Installation

#### Linux (x86_64)

```bash
curl -LO "https://ap-southeast-1-hwc-clis.obs.ap-southeast-1.myhuaweicloud.com/cli/latest/hcloud_linux_amd64.tar.gz"
tar -zxvf hcloud_linux_amd64.tar.gz
sudo mv hcloud /usr/local/bin/
sudo chmod +x /usr/local/bin/hcloud
```

#### macOS (ARM64)

```bash
curl -LO "https://ap-southeast-1-hwc-clis.obs.ap-southeast-1.myhuaweicloud.com/cli/latest/hcloud_darwin_arm64.tar.gz"
tar -zxvf hcloud_darwin_arm64.tar.gz
sudo mv hcloud /usr/local/bin/
sudo chmod +x /usr/local/bin/hcloud
```

#### Windows (PowerShell)

```powershell
Invoke-WebRequest -Uri "https://ap-southeast-1-hwc-clis.obs.ap-southeast-1.myhuaweicloud.com/cli/latest/hcloud_windows_amd64.zip" -OutFile "hcloud.zip"
Expand-Archive -Path "hcloud.zip" -DestinationPath "$env:USERPROFILE\bin"
$env:PATH += ";$env:USERPROFILE\bin"
```

### Authentication Setup

Authenticate out-of-band using environment variables or `hcloud configure`:

```bash
# Set Huawei Cloud credentials in environment
export HUAWEI_ACCESS_KEY="<your-access-key-id>"
export HUAWEI_SECRET_KEY="<your-secret-access-key>"
export HUAWEI_REGION="cn-north-4"

# Verify credentials (read-only verification)
hcloud configure list
```

> [!WARNING]
> Never print or log AK/SK strings in terminal transcripts or commit them to version control.

---

## 2. Kubernetes CLI (`kubectl`)

`kubectl` controls both the source cluster and the target CCE cluster.

### Installation

Ensure `kubectl` version matches within one minor version difference of the target CCE cluster (e.g., v1.28.x or v1.30.x):

```bash
# Linux
curl -LO "https://dl.k8s.io/release/v1.28.9/bin/linux/amd64/kubectl"
sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl
kubectl version --client --output=yaml
```

### CCE Kubeconfig Synchronization & Centralized Management

In accordance with the **Centralized Management Architecture**, target CCE cluster credentials must remain strictly on the central operator/bastion machine.

#### Option A: Central Operator Local Authentication (`update-kubeconfig`)

Use KooCLI to generate an interactive `client-exec` kubeconfig on the operator host:

```bash
hcloud CCE update-kubeconfig --cluster-id=<cce-cluster-id> --region=cn-north-4 --output=~/.kube/cce-config
```

> [!WARNING]
> Kubeconfigs generated via `update-kubeconfig` embed local system binary paths (e.g. `C:\Windows\hcloud.exe` on Windows). Never copy this configuration to remote source hosts or machines running a different operating system. Target deployments and restore verifications must be executed centrally from the operator machine.

#### Option B: Standalone Cross-Platform X.509 Certificate (`CreateKubernetesClusterCert`)

If an automated CI/CD pipeline or remote agent strictly requires headless access to the CCE API server without a local KooCLI binary:

```bash
hcloud CCE CreateKubernetesClusterCert --cli-region=<region_id> --cluster_id=<cce-cluster-id> --duration=30
```

This API returns self-contained Base64-encoded client certificate and private key data (`client-certificate-data` and `client-key-data`), which can be embedded directly into a static kubeconfig that operates universally across Linux, Windows, and containerized runners without binary dependencies.

#### Verification

Verify cluster access from the operator host:

```bash
kubectl --kubeconfig=~/.kube/cce-config cluster-info
kubectl --kubeconfig=~/.kube/cce-config get nodes
```

---

## 3. Velero CLI

Velero is the standard tool for backing up and restoring Kubernetes cluster resources and persistent volumes.

### Installation

```bash
VELERO_VERSION="v1.13.2"
curl -LO "https://github.com/vmware-tanzu/velero/releases/download/${VELERO_VERSION}/velero-${VELERO_VERSION}-linux-amd64.tar.gz"
tar -xvf "velero-${VELERO_VERSION}-linux-amd64.tar.gz"
sudo mv "velero-${VELERO_VERSION}-linux-amd64/velero" /usr/local/bin/
velero version --client-only
```

---

## 4. Huawei Cloud Object Storage Utility (`obsutil`)

`obsutil` synchronizes file data, large PV exports, and backup repositories to Huawei Cloud OBS.

### Installation

```bash
# Linux
wget https://obs-community.obs.cn-north-1.myhuaweicloud.com/obsutil/current/obsutil_linux_amd64.tar.gz
tar -xzvf obsutil_linux_amd64.tar.gz
cd obsutil_linux_amd64_*
chmod 755 obsutil
sudo mv obsutil /usr/local/bin/

# Configure interactively out-of-band (prompts silently for AK/SK)
obsutil config -e=obs.cn-north-4.myhuaweicloud.com
```

---

## 5. Container Image Migration Tool (`skopeo`)

`skopeo` inspects and copies container images between registries without requiring a local Docker daemon.

```bash
# Debian / Ubuntu
sudo apt-get update && sudo apt-get install -y skopeo

# RHEL / CentOS / EulerOS
sudo yum install -y skopeo
```

---

## 6. Huawei Cloud Image Migrator (`image-migrator`)

`image-migrator` is Huawei Cloud's dedicated automated tool for bulk container image migration to SWR.

### Installation

- **Linux x86_64**:
  ```bash
  curl -LO "https://ucs-migration.obs.cn-north-4.myhuaweicloud.com/toolkits/image-migrator-linux-amd64"
  chmod +x image-migrator-linux-amd64
  sudo mv image-migrator-linux-amd64 /usr/local/bin/image-migrator
  ```
- **Linux ARM64**:
  ```bash
  curl -LO "https://ucs-migration.obs.cn-north-4.myhuaweicloud.com/toolkits/image-migrator-linux-arm64"
  chmod +x image-migrator-linux-arm64
  sudo mv image-migrator-linux-arm64 /usr/local/bin/image-migrator
  ```
- **Windows x86_64**:
  Download executable: `https://ucs-migration.obs.cn-north-4.myhuaweicloud.com/toolkits/image-migrator-windows-amd64.exe`

---

## 7. Huawei Cloud Metadata Cloner (`k8clone`)

`k8clone` is Huawei Cloud's official zero-overhead Kubernetes metadata cloning and restoration tool.

### Installation

- **Linux x86_64**:
  ```bash
  curl -LO "https://ucs-migration.obs.cn-north-4.myhuaweicloud.com/toolkits/k8clone-linux-amd64"
  chmod +x k8clone-linux-amd64
  sudo mv k8clone-linux-amd64 /usr/local/bin/k8clone
  ```
- **Linux ARM64**:
  ```bash
  curl -LO "https://ucs-migration.obs.cn-north-4.myhuaweicloud.com/toolkits/k8clone-linux-arm64"
  chmod +x k8clone-linux-arm64
  sudo mv k8clone-linux-arm64 /usr/local/bin/k8clone
  ```
