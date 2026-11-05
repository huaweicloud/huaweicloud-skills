# Namespace Lifecycle Management

Namespaces are the foundational isolation boundary in CCI. All workload operations (Deployments, Pods, Networks) require a namespace.

## Create Namespace

The flavor annotation is **MANDATORY**. Accepted values:

| Flavor | Description |
|--------|-------------|
| `general-computing` | Standard compute instances (default) |
| `gpu-accelerated` | GPU instances — requires additional GPU quota approval |

The annotation key is `namespace.kubernetes.io/flavor` (dotted form). **hcloud CLI cannot pass dotted annotation keys**: hcloud treats dots as nested object delimiters and rejects the parameter outright.

```bash
# REJECTED — the dotted key is not a valid hcloud parameter name
hcloud CCI createCoreV1Namespace \
  --metadata.name=<ns-name> \
  --metadata.annotations.namespace.kubernetes.io/flavor=gpu-accelerated \
  --cli-region=<region>
# [USE_ERROR]不正确的参数:metadata.annotations.namespace.kubernetes.io/flavor
```

The hyphenated form is accepted by the parser, but hcloud transmits it **verbatim** as the annotation key `namespace-kubernetes-io/flavor` (verified with `--dryrun`). CCI does not treat that key as the flavor annotation, so it only appears to work for `general-computing` — because `general-computing` is the default flavor:

```bash
# Safe only because general-computing is the default flavor
hcloud CCI createCoreV1Namespace \
  --metadata.name=<ns-name> \
  --metadata.annotations.namespace-kubernetes-io/flavor=general-computing \
  --cli-region=<region> \
  --cli-output=json
```

> **⚠️ `gpu-accelerated` requires the dotted key.** Creating a namespace with
> `--metadata.annotations.namespace-kubernetes-io/flavor=gpu-accelerated` does **not** create a GPU
> namespace. The request body carries the unrecognized hyphenated key, so CCI falls back to
> `general-computing` (and the namespace is created without error, which makes the failure easy to
> miss).

To request `gpu-accelerated` (or to set the flavor annotation explicitly for any flavor), create the namespace with the skill's Python helper — it signs the request directly and sends the dotted annotation, using the same technique as Network creation:

```bash
python scripts/cci_network_helper.py create-namespace \
  --name=<ns-name> \
  --flavor=gpu-accelerated \
  --region=<region> \
  [--project-id=<project-id>]
```

- `--name` = CCI namespace name
- `--flavor` = `general-computing` or `gpu-accelerated`
- `--region` = Huawei Cloud region (must match `[a-z0-9-]+`, e.g. `cn-north-4`; any invalid value is rejected with `ERROR: invalid region`)
- `--project-id` = optional; when the project ID is already known, pass it to skip the automatic `hcloud IAM KeystoneListProjects` detection

The helper sends `POST https://cci.<region>.myhuaweicloud.com/api/v1/namespaces` with the dotted annotation in the body:

```json
{
  "apiVersion": "v1",
  "kind": "Namespace",
  "metadata": {
    "name": "<ns-name>",
    "annotations": {
      "namespace.kubernetes.io/flavor": "gpu-accelerated"
    }
  }
}
```

The helper reports the annotation the API echoed back (`Applied annotation namespace.kubernetes.io/flavor: ...`) and warns when it does not match the requested flavor. Always verify the result afterwards with `readCoreV1Namespace` and confirm that the returned `metadata.annotations` contains `namespace.kubernetes.io/flavor` with the expected value — do not assume the request succeeded.

> GPU-accelerated namespaces require GPU quota to be approved before workloads can be created.

## List Namespaces

```bash
hcloud CCI listCoreV1Namespace --cli-region=<region> --cli-output=json
```

Filter output with JMESPath:

```bash
hcloud CCI listCoreV1Namespace --cli-region=<region> --cli-output=json \
  --cli-query="items[].{Name:metadata.name,Status:status.phase,Flavor:metadata.annotations.namespace\.kubernetes\.io/flavor}"
```

## Read Namespace

```bash
hcloud CCI readCoreV1Namespace --name=<ns-name> --cli-region=<region> --cli-output=json
```

## Delete Namespace

**TWO-STEP CONFIRMATION REQUIRED — this operation is irreversible and cascading.**

### Step 1: Confirm the namespace exists, then preview it

```bash
hcloud CCI readCoreV1Namespace --name=<ns-name> --cli-region=<region> --cli-output=json
```

- **Existence pre-check (mandatory)**: if this read reports that the namespace does not exist (not found), tell the user `Namespace '<ns-name>' does not exist` and **STOP**. Do **not** run the delete command — never issue a delete for a resource you have not confirmed exists.
- If the read succeeds, show the details and warn the user:

> **WARNING**: Deleting a namespace cascades to ALL resources under it — Networks, Deployments, Pods, ConfigMaps, Secrets, etc. This cannot be undone.

### Step 2: Execute (only after explicit user confirmation)

```bash
hcloud CCI deleteCoreV1Namespace --name=<ns-name> --cli-region=<region>
```

- This is **irreversible** — no undo, no recovery
- This is **cascading** — all child resources are destroyed
- Always run `readCoreV1Namespace` first so the user can review what will be lost; only delete a namespace that Step 1 confirmed exists

## Namespace Naming Rules

- Must follow DNS_LABEL format: lowercase alphanumeric and hyphens only
- Must start with a lowercase letter or digit
- Maximum 63 characters
- Examples: `my-app`, `test-ns-01`, `production`

## Namespace Status Phases

| Phase | Meaning |
|-------|---------|
| `Active` | Namespace is ready for use |
| `Terminating` | Namespace is being deleted — all resources are being cleaned up |