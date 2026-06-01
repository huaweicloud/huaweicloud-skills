# CCI Operation Catalog

Complete quick reference of all `hcloud CCI` operations organized by category.

## Namespace (Core)

| Operation | Description |
|---|---|
| `createCoreV1Namespace` | Create namespace |
| `listCoreV1Namespace` | List namespaces |
| `readCoreV1Namespace` | Read namespace details |
| `deleteCoreV1Namespace` | Delete namespace |

## Network (CCI-specific CRD)

| Operation | Description |
|---|---|
| `createNetworkingCciIoV1beta1NamespacedNetwork` | Create Network |
| `listNetworkingCciIoV1beta1NamespacedNetwork` | List Networks |
| `readNetworkingCciIoV1beta1NamespacedNetwork` | Read Network |
| `readNetworkingCciIoV1beta1NamespacedNetworkStatus` | Read Network status |
| `deleteNetworkingCciIoV1beta1NamespacedNetwork` | Delete Network |
| `deleteNetworkingCciIoV1beta1CollectionNamespacedNetwork` | Delete all Networks in namespace |

## Deployment (Apps)

| Operation | Description |
|---|---|
| `createAppsV1NamespacedDeployment` | Create Deployment |
| `listAppsV1NamespacedDeployment` | List Deployments in namespace |
| `listAppsV1DeploymentForAllNamespaces` | List Deployments across namespaces |
| `readAppsV1NamespacedDeployment` | Read Deployment |
| `readAppsV1NamespacedDeploymentStatus` | Read Deployment status |
| `readAppsV1NamespacedDeploymentScale` | Read Deployment scale |
| `patchAppsV1NamespacedDeployment` | Update Deployment (patch) |
| `patchAppsV1NamespacedDeploymentScale` | Scale Deployment |
| `replaceAppsV1NamespacedDeployment` | Replace Deployment |
| `replaceAppsV1NamespacedDeploymentScale` | Replace Deployment scale |
| `deleteAppsV1NamespacedDeployment` | Delete Deployment |
| `deleteAppsV1CollectionNamespacedDeployment` | Delete all Deployments in namespace |

## StatefulSet (Apps)

| Operation | Description |
|---|---|
| `createAppsV1NamespacedStatefulSet` | Create StatefulSet |
| `listAppsV1NamespacedStatefulSet` | List StatefulSets |
| `listAppsV1StatefulSetForAllNamespaces` | List StatefulSets across namespaces |
| `readAppsV1NamespacedStatefulSet` | Read StatefulSet |
| `readAppsV1NamespacedStatefulSetStatus` | Read StatefulSet status |
| `patchAppsV1NamespacedStatefulSet` | Update StatefulSet |
| `replaceAppsV1NamespacedStatefulSet` | Replace StatefulSet |
| `deleteAppsV1NamespacedStatefulSet` | Delete StatefulSet |
| `deleteAppsV1CollectionNamespacedStatefulSet` | Delete all StatefulSets in namespace |

## Pod (Core)

| Operation | Description |
|---|---|
| `createCoreV1NamespacedPod` | Create Pod |
| `listCoreV1NamespacedPod` | List Pods in namespace |
| `listCoreV1PodForAllNamespaces` | List Pods across namespaces |
| `readCoreV1NamespacedPod` | Read Pod details |
| `readCoreV1NamespacedPodStatus` | Read Pod status |
| `readCoreV1NamespacedPodLog` | Read Pod logs |
| `patchCoreV1NamespacedPod` | Update Pod |
| `replaceCoreV1NamespacedPod` | Replace Pod |
| `deleteCoreV1NamespacedPod` | Delete Pod |
| `deleteCoreV1CollectionNamespacedPod` | Delete all Pods in namespace |
| `connectCoreV1GetNamespacedPodExec` | Exec into Pod (GET) |
| `connectCoreV1PostNamespacedPodExec` | Exec into Pod (POST) |

## EIPPool (CCI-specific CRD)

| Operation | Description |
|---|---|
| `createCrdYangtseCniV1NamespacedEIPPool` | Create EIPPool |
| `listCrdYangtseCniV1NamespacedEIPPool` | List EIPPools |
| `readCrdYangtseCniV1NamespacedEIPPool` | Read EIPPool |
| `readCrdYangtseCniV1NamespacedEIPPoolStatus` | Read EIPPool status |
| `patchCrdYangtseCniV1NamespacedEIPPool` | Update EIPPool |
| `replaceCrdYangtseCniV1NamespacedEIPPool` | Replace EIPPool |
| `deleteCrdYangtseCniV1NamespacedEIPPool` | Delete EIPPool |

## Service (Core)

| Operation | Description |
|---|---|
| `createCoreV1NamespacedService` | Create Service |
| `listCoreV1NamespacedService` | List Services |
| `readCoreV1NamespacedService` | Read Service |
| `readCoreV1NamespacedServiceStatus` | Read Service status |
| `patchCoreV1NamespacedService` | Update Service |
| `replaceCoreV1NamespacedService` | Replace Service |
| `deleteCoreV1NamespacedService` | Delete Service |

## Ingress (Extensions)

| Operation | Description |
|---|---|
| `createExtensionsV1beta1NamespacedIngress` | Create Ingress |
| `listExtensionsV1beta1NamespacedIngress` | List Ingresses |
| `readExtensionsV1beta1NamespacedIngress` | Read Ingress |
| `readExtensionsV1beta1NamespacedIngressStatus` | Read Ingress status |
| `patchExtensionsV1beta1NamespacedIngress` | Update Ingress |
| `replaceExtensionsV1beta1NamespacedIngress` | Replace Ingress |
| `deleteExtensionsV1beta1NamespacedIngress` | Delete Ingress |
| `deleteExtensionsV1beta1CollectionNamespacedIngress` | Delete all Ingresses |

## ConfigMap

| Operation | Description |
|---|---|
| `createCoreV1NamespacedConfigMap` | Create ConfigMap |
| `listCoreV1NamespacedConfigMap` | List ConfigMaps |
| `readCoreV1NamespacedConfigMap` | Read ConfigMap |
| `patchCoreV1NamespacedConfigMap` | Update ConfigMap |
| `replaceCoreV1NamespacedConfigMap` | Replace ConfigMap |
| `deleteCoreV1NamespacedConfigMap` | Delete ConfigMap |
| `deleteCoreV1CollectionNamespacedConfigMap` | Delete all ConfigMaps |

## Secret

| Operation | Description |
|---|---|
| `createCoreV1NamespacedSecret` | Create Secret |
| `listCoreV1NamespacedSecret` | List Secrets |
| `readCoreV1NamespacedSecret` | Read Secret |
| `patchCoreV1NamespacedSecret` | Update Secret |
| `replaceCoreV1NamespacedSecret` | Replace Secret |
| `deleteCoreV1NamespacedSecret` | Delete Secret |
| `deleteCoreV1CollectionNamespacedSecret` | Delete all Secrets |

## PersistentVolumeClaim

| Operation | Description |
|---|---|
| `createCoreV1NamespacedPersistentVolumeClaim` | Create PVC |
| `listCoreV1NamespacedPersistentVolumeClaim` | List PVCs |
| `readCoreV1NamespacedPersistentVolumeClaim` | Read PVC |
| `replaceCoreV1NamespacedPersistentVolumeClaim` | Replace PVC |
| `deleteCoreV1NamespacedPersistentVolumeClaim` | Delete PVC |

## Job (Batch v1)

| Operation | Description |
|---|---|
| `createBatchV1NamespacedJob` | Create Job |
| `listBatchV1NamespacedJob` | List Jobs |
| `readBatchV1NamespacedJob` | Read Job |
| `readBatchV1NamespacedJobStatus` | Read Job status |
| `patchBatchV1NamespacedJob` | Update Job |
| `replaceBatchV1NamespacedJob` | Replace Job |
| `deleteBatchV1NamespacedJob` | Delete Job |
| `deleteBatchV1CollectionNamespacedJob` | Delete all Jobs |

## Job (Volcano)

| Operation | Description |
|---|---|
| `createBatchVolcanoShV1alpha1NamespacedJob` | Create Volcano Job |
| `listBatchVolcanoShV1alpha1NamespacedJob` | List Volcano Jobs |
| `readBatchVolcanoShV1alpha1NamespacedJob` | Read Volcano Job |
| `patchBatchVolcanoShV1alpha1NamespacedJob` | Update Volcano Job |
| `replaceBatchVolcanoShV1alpha1NamespacedJob` | Replace Volcano Job |
| `deleteBatchVolcanoShV1alpha1NamespacedJob` | Delete Volcano Job |
| `deleteBatchVolcanoShV1alpha1CollectionNamespacedJob` | Delete all Volcano Jobs |

## RBAC

| Operation | Description |
|---|---|
| `createRbacAuthorizationV1NamespacedRoleBinding` | Create RoleBinding |
| `listRbacAuthorizationV1NamespacedRoleBinding` | List RoleBindings |
| `listRbacAuthorizationV1RoleBindingForAllNamespaces` | List RoleBindings across namespaces |
| `readRbacAuthorizationV1NamespacedRoleBinding` | Read RoleBinding |
| `listRbacAuthorizationV1ClusterRole` | List ClusterRoles |
| `readRbacAuthorizationV1ClusterRole` | Read ClusterRole |
| `patchRbacAuthorizationV1NamespacedRoleBinding` | Update RoleBinding |
| `replaceRbacAuthorizationV1NamespacedRoleBinding` | Replace RoleBinding |
| `deleteRbacAuthorizationV1NamespacedRoleBinding` | Delete RoleBinding |

## Events / ResourceQuota / Metrics

| Operation | Description |
|---|---|
| `listCoreV1NamespacedEvent` | List Events |
| `readCoreV1NamespacedEvent` | Read Event |
| `listCoreV1NamespacedResourceQuota` | List ResourceQuotas |
| `listMetricsV1beta1NamespacedPodMetrics` | List Pod metrics |
| `readMetricsV1beta1NamespacedPodMetrics` | Read Pod metrics |

## StorageClass

| Operation | Description |
|---|---|
| `listStorageV1StorageClass` | List StorageClasses |
| `readStorageV1StorageClass` | Read StorageClass |

## ReplicaSet

| Operation | Description |
|---|---|
| `listAppsV1NamespacedReplicaSet` | List ReplicaSets |
| `readAppsV1NamespacedReplicaSet` | Read ReplicaSet |

## Endpoints

| Operation | Description |
|---|---|
| `createCoreV1NamespacedEndpoints` | Create Endpoints |
| `listCoreV1NamespacedEndpoints` | List Endpoints |
| `readCoreV1NamespacedEndpoints` | Read Endpoints |
| `patchCoreV1NamespacedEndpoints` | Update Endpoints |
| `replaceCoreV1NamespacedEndpoints` | Replace Endpoints |
| `deleteCoreV1NamespacedEndpoints` | Delete Endpoints |

## API Discovery

| Operation | Description |
|---|---|
| `GetOpenAPIv2` | Get OpenAPI v2 schema |
| `getAPIVersions` | Get API versions |
| `getCoreAPIVersions` | Get core API versions |
| `getCoreV1APIResources` | Get core v1 API resources |
| `getAppsAPIGroup` | Get apps API group |
| `getAppsV1APIResources` | Get apps v1 API resources |
| `getBatchAPIGroup` | Get batch API group |
| `getBatchV1APIResources` | Get batch v1 API resources |
| `getBatchV1beta1APIResources` | Get batch v1beta1 API resources |
| `getBatchVolcanoShAPIGroup` | Get Volcano API group |
| `getBatchVolcanoShV1alpha1APIResources` | Get Volcano v1alpha1 API resources |
| `getCrdYangtseCniAPIGroup` | Get Yangtse CNI CRD API group |
| `getCrdYangtseCniV1APIResources` | Get Yangtse CNI v1 API resources |
| `getExtensionsAPIGroup` | Get extensions API group |
| `getExtensionsV1beta1APIResources` | Get extensions v1beta1 API resources |
| `getMetricsAPIGroup` | Get metrics API group |
| `getMetricsV1beta1APIResources` | Get metrics v1beta1 API resources |
| `getNetworkingCciIoAPIGroup` | Get networking CCI API group |
| `getNetworkingCciIoV1beta1APIResources` | Get networking v1beta1 API resources |
| `getRbacAuthorizationAPIGroup` | Get RBAC API group |
| `getRbacAuthorizationV1APIResources` | Get RBAC v1 API resources |

---

All operations use the format:

```
hcloud CCI <Operation> --param=value --cli-region=<region> --cli-output=json
```

Namespaced operations require `--namespace=<ns-name>`.