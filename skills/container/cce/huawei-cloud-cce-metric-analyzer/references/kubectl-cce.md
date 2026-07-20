# kubectl-cce Usage

Use `kubectl` only when the metric analyzer must read Kubernetes resources that AOM and hcloud cannot derive, such as Pod label filtering, Ingress TLS Secrets, or LoadBalancer Services.

## Install

Install `kubectl` with the system package manager, then verify:

```bash
kubectl version --client
```

Install `kubectl-cce` v0.1.0 from GitHub Releases. Choose the archive that matches the target OS and architecture.

```bash
curl -LO https://github.com/pancake0001/kubectl-cce-plugin/releases/download/v0.1.0/kubectl-cce_0.1.0_linux_amd64.tar.gz
tar -xzf kubectl-cce_0.1.0_linux_amd64.tar.gz
chmod +x kubectl-cce && mv kubectl-cce /usr/local/bin/
kubectl plugin list
```

The executable must be named `kubectl-cce` so kubectl discovers it as the `kubectl cce` plugin.

## Configure

Use AK/SK credentials:

```bash
export HW_ACCESS_KEY="<your-ak>"
export HW_SECRET_KEY="<your-sk>"
export HW_PROJECT_ID="<your-project-id>"
export HW_REGION="cn-north-4"
```

For temporary AK/SK, also set:

```bash
export HW_SECURITY_TOKEN="<your-security-token>"
```

If AK/SK is not available, use an IAM token:

```bash
export HUAWEI_IAM_TOKEN="<your-iam-token>"
```

## Use

```bash
kubectl cce --cluster-id <cluster-id> --region cn-north-4 get pods -A
kubectl cce --cluster-id <cluster-id> --region cn-north-4 get svc,ingress -A
```
