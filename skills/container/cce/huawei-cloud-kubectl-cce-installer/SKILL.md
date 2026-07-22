---
name: huawei-cloud-kubectl-cce-installer
description: Install, upgrade, verify, or troubleshoot local kubectl and the Huawei Cloud kubectl-cce plugin. Trigger when a user asks to install kubectl, install kubectl-cce, configure the CCE kubectl plugin, verify kubectl-cce availability, or repair local command prerequisites for CCE Kubernetes resource access.
tags: [kubectl, kubectl-cce, cce, huawei-cloud, kubernetes]
---

# Huawei Cloud CCE kubectl Installer

## Overview

Install and verify the local `kubectl` and `kubectl-cce` prerequisites used for Huawei Cloud CCE Kubernetes resource access. This skill changes only the local machine; it never creates, updates, or deletes cloud or Kubernetes resources.

**Architecture**: `scripts/install_kubectl_cce.sh` -> local OS package paths and official download/source repositories -> `kubectl` and `kubectl-cce` binaries -> `kubectl plugin list` verification.

**Execution Method**: Run the bundled shell script only. Do not replace its download URLs, build tags, installation paths, or verification steps with ad hoc commands unless the user explicitly asks for a different method.

**Capabilities**:
- Detect the local OS, architecture, executable availability, and plugin discovery state
- Show a no-change installation plan before execution
- Select the latest missing Linux `kubectl` package from Huawei Cloud OBS for the local architecture
- Fall back to the official Kubernetes stable release, then build the same stable tag when download fails
- Install `kubectl-cce` v0.1.0 from its Gitee Release on Linux when available
- Build the fixed `kubectl-cce` v0.1.0 source tag when a Release asset is unavailable or download fails
- Verify `kubectl` and `kubectl-cce` plugin discovery after installation

**Typical Use Cases**:
- "Install kubectl and kubectl-cce on this machine"
- "Check whether kubectl-cce is available"
- "Show the installation plan for CCE kubectl access"
- "Repair a missing kubectl-cce plugin"

## Prerequisites

### 1. Runtime Dependencies

- Bash, `curl`, `tar`, `cp`, and `chmod` for Linux/macOS installation
- `git` and Go only when source-build fallback is needed
- Write access to the selected `--bin-dir`; `/usr/local/bin` normally requires elevation
- Internet access to Kubernetes and Gitee release/source endpoints
- Network steps use timeouts by default: 10 seconds to connect, 300 seconds to download, 600 seconds to clone sources, and 900 seconds to build sources

### 2. Credential Configuration

Installation itself needs no Huawei Cloud credentials. Do not request, print, or save AK/SK, security tokens, IAM tokens, or kubeconfig content during installation.

After installation, `kubectl cce` requires credentials only when it accesses a CCE cluster. Read [plugin-usage.md](references/plugin-usage.md) before configuring that access.

### 3. Local Permission Requirements

| Permission | Purpose |
| ---------- | ------- |
| Read/execute access | Detect existing `kubectl` and `kubectl-cce` executables |
| Write access to `--bin-dir` | Install a missing executable |
| Elevated local permission when required | Write to protected directories such as `/usr/local/bin` |

**Permission Failure Handling**:

1. Report the target installation directory and the local permission error.
2. Ask the user to select a writable directory or explicitly authorize an elevated command.
3. Do not retry with `sudo` automatically.

## Core Commands

All commands use the bundled installer script:

```bash
bash scripts/install_kubectl_cce.sh [--check] [--execute] [--bin-dir <directory>]
```

### 1. Local State Check

```bash
bash scripts/install_kubectl_cce.sh --check
```

This is read-only. It reports the OS, architecture, installed binaries, `kubectl` client version, and `kubectl plugin list` output.

### 2. Installation Plan

```bash
bash scripts/install_kubectl_cce.sh --bin-dir /usr/local/bin
```

This is read-only. It shows which executables are missing and the exact download or source-build fallback without changing the machine.

### 3. Confirmed Installation

```bash
sudo bash scripts/install_kubectl_cce.sh --execute --bin-dir /usr/local/bin
```

Run only after the user confirms the previewed installation path and actions. The script does not overwrite existing `kubectl` or `kubectl-cce` executables.

### 4. Source-Build Fallback

- For Linux, list the public OBS package repository and select the latest package for the local `amd64` or `arm64` architecture. Package names determine release ordering.
- If OBS lookup, download, or extraction fails, download the official Kubernetes stable release; build the same stable tag only if that download fails.
- When the Linux `kubectl-cce` v0.1.0 asset is unavailable or download fails, build the fixed `v0.1.0` source tag.
- On macOS, build `kubectl-cce` v0.1.0 from source because the Release has no macOS asset.

The fallback requires `git` and Go. If either is absent, return the missing dependency rather than installing it automatically.

### 5. Windows Manual Installation

The bundled script does not run on Windows. Download the matching Windows `kubectl` binary from the [official Kubernetes release site](https://kubernetes.io/releases/download/) and the matching `kubectl-cce` ZIP from the [Gitee `v0.1.0` Release](https://gitee.com/pancake0001/kubectl-cce-plugin/releases/tag/v0.1.0). Extract the files, place them in a user-selected directory on `PATH`, and verify with `kubectl version --client` and `kubectl plugin list`. See [plugin-usage.md](references/plugin-usage.md) for the plugin-specific steps.

## Risk Levels

This skill modifies only local binaries and does not operate on cloud resources. It must still use a plan-and-confirm flow for system changes.

| Level | Meaning | Execution Guidance |
| ----- | ------- | ------------------ |
| R3 | Read-only local inspection | May run automatically |
| R1 | Local executable installation, replacement, or PATH-adjacent system change | Show the plan first and require explicit user confirmation before `--execute` |

| Operation | Risk Level | Description |
| --------- | ---------- | ----------- |
| `--check` | R3 | Inspect local tools and plugin discovery |
| Default script mode | R3 | Show installation plan without making changes |
| `--execute` | R1 | Install missing binaries into the selected directory |
| Source-build fallback | R1 | Clone fixed source tags and compile missing binaries |

## Parameter Reference

| Parameter | Required/Optional | Description | Default |
| --------- | ----------------- | ----------- | ------- |
| `--check` | Optional | Run only local inspection and verification | Disabled |
| `--execute` | Required for mutation | Install missing binaries after explicit confirmation | Disabled |
| `--bin-dir <directory>` | Optional | Target directory for newly installed executables | `/usr/local/bin` |
| `--help` | Optional | Display script usage | N/A |

Set `KUBECTL_CCE_CONNECT_TIMEOUT`, `KUBECTL_CCE_DOWNLOAD_TIMEOUT`, `KUBECTL_CCE_SOURCE_CLONE_TIMEOUT`, or `KUBECTL_CCE_SOURCE_BUILD_TIMEOUT` to positive integer seconds only when the default timeout is unsuitable.

## 参数确认

The installer may inspect the local machine without confirmation, but installation is an R1 local-system change. Confirm the following values with the user before running `--execute`.

| Parameter | Resolution | Confirmation Requirement |
| --------- | ---------- | ------------------------ |
| Installation mode | `--check` and the default plan are read-only; `--execute` installs missing binaries | Explicit confirmation required for `--execute` |
| `--bin-dir` | Defaults to `/usr/local/bin`; may be changed to a writable user-selected directory | Confirm the target directory before installation |
| Existing executables | Detected from `PATH`; the script does not overwrite them | Report the detected state; do not replace an executable without a separately approved workflow |
| Network timeouts | Use defaults unless the user provides positive integer overrides | Confirm non-default values when they materially extend the wait time |

Never infer a writable installation directory, use `sudo` automatically, or install a missing build dependency without the user's explicit approval.

## Output Format

The script writes human-readable output to standard output and exits nonzero when it cannot complete the requested operation.

**Key output fields**:
- `platform`: detected operating system
- `arch`: normalized CPU architecture
- `kubectl_present`: whether `kubectl` is in `PATH`
- `kubectl_cce_present`: whether `kubectl-cce` is in `PATH`
- `bin_dir`: selected installation directory
- `PLAN`: planned changes in no-change mode
- Error text: missing dependency, unsupported platform, download/build failure, or plugin discovery failure

## Workflow

1. Run `--check` and record the current local state.
2. Run the default plan command with the intended `--bin-dir`.
3. Present the planned downloads, source-build fallback, target directory, and R1 local-system impact to the user.
4. Wait for explicit confirmation.
5. Run the same command with `--execute`.
6. Verify `kubectl version --client` and `kubectl plugin list`.
7. For CCE access configuration, read [plugin-usage.md](references/plugin-usage.md) and perform only a read-only cluster request if the user asks to test connectivity.

## Verification

Run the read-only check first:

```bash
bash scripts/install_kubectl_cce.sh --check
```

After a confirmed installation, verify:

```bash
kubectl version --client
kubectl plugin list
```

The plugin is ready when `kubectl plugin list` contains `kubectl-cce`. Do not rely on `kubectl cce --version`: the source tag does not expose a stable version flag.

## Best Practices

1. **Inspect before installing** - always run `--check` and the no-change plan first.
2. **Use an explicit target directory** - show `--bin-dir` before asking for confirmation.
3. **Preserve existing binaries** - do not request `--execute` as an upgrade mechanism unless the user explicitly asks for replacement support.
4. **Use the local architecture** - select the latest amd64 or arm64 OBS package matching the host CPU.
5. **Separate installation from cluster access** - do not validate the plugin by mutating a cluster; use a read-only request only when requested.

## Notes

- Installation and source compilation are R1 local-system actions and require explicit confirmation.
- The script never writes Huawei Cloud credentials, tokens, or kubeconfig files.
- `kubectl-cce` must be named exactly `kubectl-cce` for Kubernetes plugin discovery.
- On Windows, do not run the bundled script; use the official Kubernetes download and matching Gitee Release ZIP as described in [plugin-usage.md](references/plugin-usage.md).

## Troubleshooting

| Symptom | Likely Cause | Action |
| ------- | ------------ | ------ |
| `curl`, `tar`, `cp`, or `chmod` is missing | Local prerequisite is absent | Install the missing local prerequisite through the user-approved system method, then retry |
| Download fails | Network restriction or unavailable Release asset | Allow the script to use its fixed-tag source-build fallback after confirmation |
| Network step times out | Endpoint, proxy, or connection is slow or unavailable | Check connectivity, then increase the relevant `KUBECTL_CCE_*_TIMEOUT` value if the user approves |
| Source build fails | `git`/Go missing or source build dependency failure | Install the reported build prerequisite, then rerun the plan and confirmed installation |
| Permission denied in `--bin-dir` | Protected target directory | Select a writable directory or run an explicitly approved elevated command |
| Plugin not listed | Target directory is not in `PATH` | Add the selected `--bin-dir` to `PATH`, then rerun `kubectl plugin list` |
| macOS plugin missing | v0.1.0 has no macOS Release asset | Use the fixed `v0.1.0` source-build fallback |

## Limitations

- The bundled script executes only on Linux and macOS. Windows uses manual downloads from the official Kubernetes release site and Gitee; the script must not be used.
- The script installs missing binaries only; it does not upgrade or replace existing binaries.
- The skill does not configure Huawei Cloud credentials or retrieve kubeconfig files.
- The skill does not test cluster connectivity unless the user explicitly requests a separate read-only CCE command.
- Source build depends on the availability of the pinned Git tags and a compatible local Go toolchain.

## References

| Document | Use |
| -------- | --- |
| [Plugin Usage](references/plugin-usage.md) | kubectl-cce credentials, read-only CCE connectivity test, and Windows installation |
| [Acceptance Criteria](references/acceptance-criteria.md) | Installation, verification, safety, and documentation acceptance gates |
