# Step-by-Step Verification Process for CCI Skill Functionality

## 1. Environment Verification

```bash
hcloud version  # >= 7.2.2
hcloud configure list  # valid profile exists
```

## 2. Namespace Verification

```bash
hcloud CCI listCoreV1Namespace --cli-region=cn-north-4 --cli-output=json
```

Expected: list of namespaces with `metadata.name` and `status.phase`.

## 3. Network Verification

```bash
hcloud CCI readNetworkingCciIoV1beta1NamespacedNetworkStatus \
  --name=<network-name> --namespace=<ns-name> \
  --cli-region=cn-north-4 --cli-output=json
```

Expected: `status.state=Active`.

## 4. Deployment Verification

```bash
hcloud CCI readAppsV1NamespacedDeploymentStatus \
  --name=<deploy-name> --namespace=<ns-name> \
  --cli-region=cn-north-4 --cli-output=json
```

Expected: `status.readyReplicas > 0`, `status.availableReplicas > 0`.

## 5. Pod Verification

```bash
hcloud CCI readCoreV1NamespacedPodStatus \
  --name=<pod-name> --namespace=<ns-name> \
  --cli-region=cn-north-4 --cli-output=json
```

Expected: `status.phase=Running`.

## 6. Log Verification

```bash
hcloud CCI readCoreV1NamespacedPodLog \
  --name=<pod-name> --namespace=<ns-name> \
  --container=<container-name> \
  --cli-region=cn-north-4
```

Expected: application log output.

## 7. Delete Operation Verification

Two-step confirmation process:

1. **Test without confirmation:** show preview and warning only, do not execute deletion.
2. **Test with confirmation:** verify the resource is actually deleted by attempting to read it (should return 404 or empty result).

## 8. Complete Verification Checklist

| Step | Verification Item | Expected Result | Verification Command |
|---|---|---|---|
| 1 | hcloud CLI installed | version >= 7.2.2 | `hcloud version` |
| 2 | CLI profile configured | valid profile listed | `hcloud configure list` |
| 3 | Namespace created | status.phase=Active | `listCoreV1Namespace` |
| 4 | Network created | status.state=Active | `readNetworkingCciIoV1beta1NamespacedNetworkStatus` |
| 5 | Deployment created | readyReplicas > 0 | `readAppsV1NamespacedDeploymentStatus` |
| 6 | Pod running | status.phase=Running | `readCoreV1NamespacedPodStatus` |
| 7 | Logs accessible | application log output | `readCoreV1NamespacedPodLog` |
| 8 | Delete requires confirmation | preview shown, no deletion | test delete without confirm |
| 9 | Delete with confirmation | resource removed | test delete with confirm, then read returns 404 |
| 10 | Permission errors handled | policy shown, execution paused | test with insufficient permissions |