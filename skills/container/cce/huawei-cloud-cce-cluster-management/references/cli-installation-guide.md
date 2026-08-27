# CLI Installation Guide

## Overview

This skill depends on two CLI tools. Install them via the corresponding skills before use.

## Required CLIs

| CLI | Purpose | Installation |
| --- | --- | --- |
| `hcloud` (KooCLI) | Huawei Cloud API calls (CCE, EIP, IAM) | [huawei-cloud-cli-guidance](../huawei-cloud-cli-guidance/SKILL.md) skill |
| `kubectl` + `kubectl-cce` | Kubernetes node operations (cordon/uncordon/drain/status) | [huawei-cloud-kubectl-cce-installer](../huawei-cloud-kubectl-cce-installer/SKILL.md) skill |

## Verification

```bash
hcloud version
kubectl cce --help
```
