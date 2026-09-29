# Kubectl And Kubectl-CCE Installation

Use this reference only when `kubectl` or `kubectl-cce` is unavailable, or when the user explicitly asks to install, repair, or replace a local binary.

## Prerequisites

- Linux and macOS require Bash, `curl`, `tar`, `cp`, and `chmod`.
- Source-build fallback additionally requires `git` and Go.
- The selected `--bin-dir` must be writable. `/usr/local/bin` commonly requires elevated local permission.
- Network operations use these defaults: 10-second connection timeout, 300-second download timeout, 600-second source-clone timeout, and 900-second build timeout.
- Installation does not need Huawei Cloud credentials. Never print or store credentials, tokens, or kubeconfig content.

## Installer Commands

All installation operations use the bundled script:

```bash
bash scripts/install_kubectl_cce.sh [--check] [--execute] [--reinstall] [--bin-dir <directory>]
```

| Command | Risk | Behavior |
| --- | --- | --- |
| `bash scripts/install_kubectl_cce.sh --check` | R3 | Shows platform, architecture, executable state, client version, and plugin discovery. |
| `bash scripts/install_kubectl_cce.sh --bin-dir <directory>` | R3 | Shows the no-change installation plan. |
| `bash scripts/install_kubectl_cce.sh --execute --bin-dir <directory>` | R1 | Installs missing binaries after explicit confirmation. |
| `bash scripts/install_kubectl_cce.sh --reinstall --execute --bin-dir <directory>` | R1 | Replaces only `kubectl-cce` after explicit confirmation. |

Never infer a target directory, use `sudo` automatically, or install missing build dependencies without user confirmation.

## Installation Sources And Fallback

- On Linux, the script selects the latest public Huawei Cloud OBS `kubectl` package matching the local `amd64` or `arm64` architecture.
- If OBS lookup, download, or extraction fails, it downloads the Kubernetes stable binary. If that also fails, it builds the same stable source tag.
- For Linux, `kubectl-cce` v0.2.1 is downloaded from the Gitee Release. An unavailable asset or failed download falls back to building the pinned source tag.
- On macOS, the plugin is built from the fixed v0.2.1 source tag because the Release has no macOS asset.
- If `git` or Go is missing for the source fallback, report the missing dependency; do not install it automatically.

## Confirmation And Verification

Before an R1 action, show the no-change plan and confirm the installation directory, the binaries to change, and any explicit plugin replacement. After an
installation succeeds, verify:

```bash
kubectl version --client
kubectl plugin list
```

The plugin is ready when `kubectl plugin list` contains `kubectl-cce`. Do not rely on `kubectl cce --version`; the pinned source tag does not expose a stable
version flag.

## Windows

Do not run the bundled script on Windows. Download `kubectl.exe` from the [official Kubernetes release site](https://kubernetes.io/releases/download/) and the
matching `kubectl-cce` v0.2.1 ZIP from the [Gitee Release](https://gitee.com/pancake0001/kubectl-cce-plugin/releases/tag/v0.2.1). Extract both into a
user-selected directory on `PATH`, then run `kubectl plugin list`.

## Troubleshooting

| Symptom | Action |
| --- | --- |
| Required local command is missing | Install it through the user-approved system method, then rerun the plan. |
| Download fails or times out | Check connectivity; use the script's documented fallback or approved timeout override. |
| Source build fails | Install the reported `git` or Go prerequisite through an approved method, then rerun the plan. |
| Permission denied | Choose a writable target directory or request explicit approval for elevated execution. |
| Plugin not listed | Ensure the selected `--bin-dir` is on `PATH`, then rerun `kubectl plugin list`. |
