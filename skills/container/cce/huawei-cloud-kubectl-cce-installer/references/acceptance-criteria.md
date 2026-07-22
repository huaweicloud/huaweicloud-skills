# Acceptance Criteria

## Installation Behavior

- `--check` completes without changing the local machine and reports the platform, architecture, executable presence, and plugin discovery state.
- The default invocation prints a plan and exits without installing or replacing executables.
- `--execute` installs only missing `kubectl` and `kubectl-cce` executables into the confirmed `--bin-dir`.
- Linux `kubectl-cce` downloads use the Gitee `v0.1.0` Release asset matching the local CPU architecture; an unavailable asset falls back to the pinned source tag.
- Existing `kubectl` and `kubectl-cce` executables are not overwritten.

## Verification

- The installer exits successfully only when `kubectl version --client` runs and `kubectl plugin list` contains `kubectl-cce` after a confirmed installation.
- Download, source-clone, and source-build operations use the documented timeout settings and return a clear nonzero error on failure.

## Safety and Documentation

- No cloud resources, Kubernetes resources, credentials, tokens, or kubeconfig files are created, changed, printed, or stored by the installer.
- R1 installation actions require a preview and explicit user confirmation before `--execute`.
- `SKILL.md` documents triggers, configurable parameters, confirmation requirements, fallback behavior, and verification commands.
