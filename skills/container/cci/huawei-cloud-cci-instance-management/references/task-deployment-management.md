# Deployment Lifecycle Management

Deployments in CCI are serverless — no node management is needed. CCI automatically provisions compute resources based on container specifications.

## Prerequisites

Before creating a Deployment, the following must already exist:

1. **Namespace** — created via `createCoreV1Namespace`
2. **Network** — created via `createNetworkingCciIoV1beta1NamespacedNetwork` and in `Active` state

## Create Deployment

### Single Container

```bash
hcloud CCI createAppsV1NamespacedDeployment \
  --namespace=<ns-name> \
  --metadata.name=<deploy-name> \
  --spec.replicas=1 \
  --spec.selector.matchLabels.app=<deploy-name> \
  --spec.template.metadata.labels.app=<deploy-name> \
  --spec.template.spec.containers.1.name=<container-name> \
  --spec.template.spec.containers.1.image=<image> \
  --spec.template.spec.containers.1.resources.limits.cpu=500m \
  --spec.template.spec.containers.1.resources.limits.memory=1Gi \
  --spec.template.spec.containers.1.resources.requests.cpu=500m \
  --spec.template.spec.containers.1.resources.requests.memory=1Gi \
  --cli-region=<region> \
  --cli-output=json
```

Key constraints:

- `--spec.selector.matchLabels` **MUST match** `--spec.template.metadata.labels` — mismatched labels prevent the Deployment from managing its Pods
- Resource limits and requests are **MANDATORY** for CCI — omitting them causes creation failure
- `resources.requests` **MUST equal** `resources.limits` for every container (same CPU value and same memory value) — CCI rejects mismatches with `limit and request doesn't equal`
- Array indices are 1-based in hcloud dot notation: `containers.1` is the first container, `containers.2` is the second (JSON Patch paths in the scale/update sections below are 0-based instead)

### Multi-Container Example

```bash
hcloud CCI createAppsV1NamespacedDeployment \
  --namespace=<ns-name> \
  --metadata.name=<deploy-name> \
  --spec.replicas=1 \
  --spec.selector.matchLabels.app=<deploy-name> \
  --spec.template.metadata.labels.app=<deploy-name> \
  --spec.template.spec.containers.1.name=main \
  --spec.template.spec.containers.1.image=nginx \
  --spec.template.spec.containers.1.resources.limits.cpu=500m \
  --spec.template.spec.containers.1.resources.limits.memory=1Gi \
  --spec.template.spec.containers.1.resources.requests.cpu=500m \
  --spec.template.spec.containers.1.resources.requests.memory=1Gi \
  --spec.template.spec.containers.2.name=sidecar \
  --spec.template.spec.containers.2.image=busybox \
  --spec.template.spec.containers.2.resources.limits.cpu=100m \
  --spec.template.spec.containers.2.resources.limits.memory=256Mi \
  --spec.template.spec.containers.2.resources.requests.cpu=100m \
  --spec.template.spec.containers.2.resources.requests.memory=256Mi \
  --cli-region=<region> \
  --cli-output=json
```

### Port Specification Example

```bash
hcloud CCI createAppsV1NamespacedDeployment \
  --namespace=<ns-name> \
  --metadata.name=<deploy-name> \
  --spec.replicas=1 \
  --spec.selector.matchLabels.app=<deploy-name> \
  --spec.template.metadata.labels.app=<deploy-name> \
  --spec.template.spec.containers.1.name=<container-name> \
  --spec.template.spec.containers.1.image=<image> \
  --spec.template.spec.containers.1.ports.1.containerPort=80 \
  --spec.template.spec.containers.1.resources.limits.cpu=500m \
  --spec.template.spec.containers.1.resources.limits.memory=1Gi \
  --spec.template.spec.containers.1.resources.requests.cpu=500m \
  --spec.template.spec.containers.1.resources.requests.memory=1Gi \
  --cli-region=<region> \
  --cli-output=json
```

## List Deployments

### Within a namespace

```bash
hcloud CCI listAppsV1NamespacedDeployment \
  --namespace=<ns-name> \
  --cli-region=<region> --cli-output=json
```

### Across all namespaces

```bash
hcloud CCI listAppsV1DeploymentForAllNamespaces \
  --cli-region=<region> --cli-output=json
```

## Read Deployment

```bash
hcloud CCI readAppsV1NamespacedDeployment \
  --name=<deploy-name> --namespace=<ns-name> \
  --cli-region=<region> --cli-output=json
```

## Read Deployment Status

```bash
hcloud CCI readAppsV1NamespacedDeploymentStatus \
  --name=<deploy-name> --namespace=<ns-name> \
  --cli-region=<region> --cli-output=json
```

Check `readyReplicas` vs `replicas` to determine rollout progress.

## Scale Deployment

`patchAppsV1NamespacedDeploymentScale` has **no** `--spec.replicas` parameter (its only body parameter is `--io.k8s.apimachinery.pkg.apis.meta.v1.Patch`). Scaling is done with a JSON Patch body:

```bash
hcloud CCI patchAppsV1NamespacedDeploymentScale \
  --name=<deploy-name> --namespace=<ns-name> \
  --io.k8s.apimachinery.pkg.apis.meta.v1.Patch='[{"op":"replace","path":"/spec/replicas","value":<new-count>}]' \
  --cli-region=<region>
```

> The old form `--spec.replicas=<new-count>` fails with `[USE_ERROR]不正确的参数:spec.replicas`.

## Update Deployment (Patch)

`patchAppsV1NamespacedDeployment` accepts only `--io.k8s.apimachinery.pkg.apis.meta.v1.Patch` as its body parameter — there is no `--spec.template...` parameter. Pass a JSON Patch body instead.

### Update container image

```bash
hcloud CCI patchAppsV1NamespacedDeployment \
  --name=<deploy-name> --namespace=<ns-name> \
  --io.k8s.apimachinery.pkg.apis.meta.v1.Patch='[{"op":"replace","path":"/spec/template/spec/containers/0/image","value":"<new-image>"}]' \
  --cli-region=<region>
```

`containers/0` is the **first** container: JSON Patch array indices are 0-based, while hcloud dot-notation parameters are 1-based (`--spec.template.spec.containers.1.image`).

This triggers a rolling update — Pods are replaced incrementally.

### Other patchable fields

`--io.k8s.apimachinery.pkg.apis.meta.v1.Patch` is a JSON Patch array, so several changes can be sent in one request, and paths other than `/spec/replicas` and container images are allowed as long as they are in the supported update list (`metadata.labels`, `metadata.annotations`, `spec.template`, `spec.replicas`, `spec.revisionHistoryLimit`, `spec.progressDeadlineSeconds`):

```bash
hcloud CCI patchAppsV1NamespacedDeployment \
  --name=<deploy-name> --namespace=<ns-name> \
  --io.k8s.apimachinery.pkg.apis.meta.v1.Patch='[{"op":"replace","path":"/spec/replicas","value":3},{"op":"replace","path":"/spec/template/spec/containers/0/image","value":"nginx:1.27"}]' \
  --cli-region=<region>
```

## Delete Deployment

**TWO-STEP CONFIRMATION REQUIRED.**

### Step 1: Warn the user

> **WARNING**: Deleting a Deployment terminates all Pod replicas managed by it. This is irreversible.

### Step 2: Execute (only after explicit user confirmation)

```bash
hcloud CCI deleteAppsV1NamespacedDeployment \
  --name=<deploy-name> --namespace=<ns-name> \
  --cli-region=<region>
```