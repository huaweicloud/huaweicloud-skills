# kubectl-cce Usage

`huawei_get_cce_events` uses `kubectl` to read Events. It first uses a temporary kubeconfig through the cluster external endpoint. When no external endpoint is available, it falls back to the `kubectl cce` plugin.

## Install

Install `kubectl` with the system package manager and verify it:

```bash
kubectl version --client
```

Install `kubectl-cce` v0.1.0 from the GitHub release that matches the local OS and architecture:

```bash
curl -LO https://github.com/pancake0001/kubectl-cce-plugin/releases/download/v0.1.0/kubectl-cce_0.1.0_linux_amd64.tar.gz
tar -xzf kubectl-cce_0.1.0_linux_amd64.tar.gz
chmod +x kubectl-cce && mv kubectl-cce /usr/local/bin/
kubectl plugin list
```

The executable must be named `kubectl-cce` so that kubectl discovers it as `kubectl cce`.

## Plugin Credentials

The plugin requires AK, SK, and the target cluster's project ID. The skill supplies compatible credential environment variables internally and passes the project ID explicitly with `--project-id`. Temporary credentials also require a security token.

Set these values through an approved local credential provider before invoking the plugin. Never place credential values in this document, shell history, source control, or command output.

## Example

```bash
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get events -A
```
