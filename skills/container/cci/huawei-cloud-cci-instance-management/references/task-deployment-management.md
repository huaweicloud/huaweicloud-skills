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
  --spec.template.spec.containers.1.resources.requests.cpu=250m \
  --spec.template.spec.containers.1.resources.requests.memory=512Mi \
  --cli-region=<region> \
  --cli-output=json
```

Key constraints:

- `--spec.selector.matchLabels` **MUST match** `--spec.template.metadata.labels` — mismatched labels prevent the Deployment from managing its Pods
- Resource limits and requests are **MANDATORY** for CCI — omitting them causes creation failure
- Array indices are 1-based: `containers.1` is the first container, `containers.2` is the second

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
  --spec.template.spec.containers.1.resources.requests.cpu=250m \
  --spec.template.spec.containers.1.resources.requests.memory=512Mi \
  --spec.template.spec.containers.2.name=sidecar \
  --spec.template.spec.containers.2.image=busybox \
  --spec.template.spec.containers.2.resources.limits.cpu=100m \
  --spec.template.spec.containers.2.resources.limits.memory=256Mi \
  --spec.template.spec.containers.2.resources.requests.cpu=50m \
  --spec.template.spec.containers.2.resources.requests.memory=128Mi \
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
  --spec.template.spec.containers.1.resources.requests.cpu=250m \
  --spec.template.spec.containers.1.resources.requests.memory=512Mi \
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

```bash
hcloud CCI patchAppsV1NamespacedDeploymentScale \
  --name=<deploy-name> --namespace=<ns-name> \
  --spec.replicas=<new-count> \
  --cli-region=<region>
```

## Update Deployment (Patch)

### Update container image

```bash
hcloud CCI patchAppsV1NamespacedDeployment \
  --name=<deploy-name> --namespace=<ns-name> \
  --spec.template.spec.containers.1.image=<new-image> \
  --cli-region=<region>
```

This triggers a rolling update — Pods are replaced incrementally.

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