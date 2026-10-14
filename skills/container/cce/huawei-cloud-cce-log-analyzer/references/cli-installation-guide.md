# CLI Installation Guide

## KooCLI (hcloud)

KooCLI is required for all LTS and CCE CLI operations. Install or update using:

```bash
# Install or update to the latest version
curl -sSL https://cn-north-4-hdn-koocli.obs.cn-north-4.myhuaweicloud.com/cli/latest/hcloud_install.sh -o /tmp/hcloud_install.sh
bash /tmp/hcloud_install.sh -y

# Verify installation
hcloud version
```

### Configure Profile

```bash
hcloud configure set --cli-profile=default \
  --cli-access-key=<AK> \
  --cli-secret-key=<SK> \
  --cli-region=cn-north-4
```

## kubectl

`kubectl` is required for Pod stdout log retrieval and LogConfig custom resource management.

```bash
# Install kubectl
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
chmod +x kubectl
mv kubectl /usr/local/bin/
```

## kubectl cce Plugin

The `kubectl cce` plugin provides CCE cluster access for `kubectl`. Use the [huawei-cloud-kubectl-cce-installer](../../huawei-cloud-kubectl-cce-installer/SKILL.md) skill for installation and credentials.

## Cloud Native Logging Add-on

For CCE LogConfig tools, install the Cloud Native Logging add-on in the target cluster via the CCE console or CLI. See the [CCE Cloud Native Logging documentation](https://support.huaweicloud.com/usermanual-cce/cce_10_0416.html).

## Python Dependencies

```bash
pip install huaweicloudsdkcore huaweicloudsdklts
```

The LTS SDK (`huaweicloudsdklts`) is required only for `K8S_CCE` type LTS Access Config creation.