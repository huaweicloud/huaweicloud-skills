# Troubleshooting Guide for CCI hcloud CLI Issues

## 1. Namespace Creation Fails

**Cause:** Missing `namespace.kubernetes.io/flavor` annotation.

**Fix:** Add the flavor annotation:
```
--metadata.annotations.namespace-kubernetes-io/flavor=general-computing
```

Without this annotation, CCI rejects namespace creation requests.

## 2. Network Creation Fails

**Cause:** Invalid subnet ID, VPC ID, or CIDR conflict.

**Fix:**
- Verify subnet ID with `hcloud VPC ListSubnets --vpc-id=<vpc-id>`
- Verify VPC ID with `hcloud VPC ShowVpc`
- Ensure Network CIDR does not overlap with `10.247.0.0/16` (reserved for CCI internal routing)
- Use a different CIDR range such as `10.0.0.0/24` or `172.16.0.0/24`

## 3. Pod Stays in Pending State

**Cause:** No Network in namespace, insufficient resources, or image pull failure.

**Fix:**
- Check events: `hcloud CCI listCoreV1NamespacedEvent --namespace=<ns-name>`
- Verify Network exists in the namespace
- Verify image name and credentials
- Check resource availability in the namespace

## 4. Deployment Pods Not Becoming Ready

**Cause:** Container crash, image pull error, or resource limits exceeded.

**Fix:**
- Read Pod status: `hcloud CCI readCoreV1NamespacedPodStatus --name=<pod> --namespace=<ns>`
- Check events: `hcloud CCI listCoreV1NamespacedEvent --namespace=<ns-name>`
- Read Pod logs: `hcloud CCI readCoreV1NamespacedPodLog --name=<pod> --namespace=<ns> --container=<container>`
- Check resource limits vs available namespace resources

## 5. Permission Denied (403)

**Cause:** IAM permissions insufficient for the requested operation.

**Fix:** Refer to iam-policies.md, identify the missing permission, and add it to the IAM policy.

## 6. Parameter Format Errors

**Common mistakes:**
- Using JSON objects instead of `{*}` format for nested parameters
- Using 0-based indexing instead of 1-based indexing
- Missing equals sign in `--key=value` format
- Using wrong parameter names

**Fix:** Refer to parameter-format.md for correct hcloud CLI parameter syntax.

## 7. EIPPool Creation Fails

**Cause:** No available EIPs in the project, or CIDR format error.

**Fix:**
- Verify EIP availability: `hcloud VPC ListPublicIps`
- Check CIDR format (must be valid IPv4 CIDR, e.g., `10.0.0.0/24`)
- Ensure sufficient EIPs exist for the pool size

## 8. Deep Nested Parameter Construction Is Complex

**Fix:**
- Always use `hcloud CCI <Operation> --help` first to see parameter structure
- Build parameters incrementally, adding one nested level at a time
- Use `--dryRun=All` to validate parameters before execution
- Refer to parameter-format.md for nested parameter syntax rules

## 9. hcloud CLI General Errors

| Error Type | Description | Resolution |
|---|---|---|
| `[NETWORK_ERROR]` | Network connectivity issue | Check network connection and proxy settings |
| `[USE_ERROR]` | Parameter format error | Check parameter format, refer to parameter-format.md |
| `[OPENAPI_ERROR]` | API version compatibility issue | Check API version, update hcloud CLI |
| Debug flag | `--cli-debug=true` | Add this flag to any command for detailed debug output |

## 10. Pod Exec Operations

The `connectCoreV1GetNamespacedPodExec` and `connectCoreV1PostNamespacedPodExec` operations are interactive WebSocket operations. They may not work well in hcloud CLI batch mode.

**Alternative:** Use Pod logs for diagnostics instead of exec:
```
hcloud CCI readCoreV1NamespacedPodLog --name=<pod> --namespace=<ns> --container=<container>
```

## 11. CCI Network "securitygroup can not be empty" Error

**Cause:** The annotation key `network.alpha.kubernetes.io/default-security-group` is not correctly passed.

**Common root causes:**
- Wrong annotation key used (e.g., `security-group-id` instead of `default-security-group`)
- hcloud CLI cannot pass annotation keys containing dots - it treats dots as nested levels
- hcloud `--cli-jsonInput` doesn't properly transmit annotations (see Section 13)

**Fix:** Use the Python helper script for Network creation instead of hcloud CLI. The Python SDK correctly handles annotation keys with dots.

## 12. hcloud CLI "Incorrect parameter" Error for Annotation Keys with Dots

**Cause:** When using `--metadata.annotations.network.alpha.kubernetes.io/key=value`, hcloud treats each dot as a nested object level delimiter. No escaping mechanism (backslash, quotes, etc.) works.

**Fix:** This is an hcloud CLI limitation. Use the Python helper script for any CCI resource creation that requires annotation keys with dots (especially Network). hcloud CLI is usable only for annotation keys without dots (e.g., hyphenated keys on Namespace).

## 13. hcloud `--cli-jsonInput` "Failed to parse cli-jsonInput parameter file" Error

**Cause:** Multiple possible causes for this JSON input parsing failure.

**Root causes and fixes:**
- **UTF-8 with BOM encoding:** hcloud cannot parse files with BOM. Use ASCII encoding (or UTF-8 without BOM) for the JSON input file.
- **Annotations with dots not transmitted:** This is a confirmed hcloud bug. Annotations with dots appear in `--dryrun` output but are not included in the actual API request body. Use the Python helper script instead.
- **Incorrect JSON structure:** The JSON structure must exactly match the skeleton format shown by `hcloud CCI <Operation> --help`. Verify field names, nesting, and required fields.

## 14. Network Creation "spec[networkID]: Required value" Error

**Cause:** The `networkID` field (neutron network ID) is missing from the Network spec. This field is required alongside `attachedVPC`, `subnetID`, and `networkType`.

**Fix:** Obtain the neutron network ID from `hcloud VPC ShowSubnet` output and include it in the Network spec as the `networkID` field.

## 15. CCI Annotation Key Auto-Normalization

**Behavior:** For Namespace resources, CCI automatically adds the canonical dotted annotation key (`namespace.kubernetes.io/flavor`) alongside the hyphenated version (`namespace-kubernetes-io/flavor`) when you provide only the hyphenated form. This auto-normalization only works for Namespace.

**Important:** This normalization does NOT apply to Network resources. For Network, you must provide the exact dotted annotation keys (`network.alpha.kubernetes.io/default-security-group`, etc.) yourself. Since hcloud CLI cannot handle dotted keys, use the Python helper script for Network creation.

## 16. Deployment "limit and request doesn't equal" Error

**Cause:** CCI requires container resource limits to equal requests. If limits != requests, CCI rejects the Deployment/Pod creation.

**Fix:** Set requests to the same values as limits:
```bash
--spec.template.spec.containers.1.resources.limits.cpu=500m
--spec.template.spec.containers.1.resources.limits.memory=1Gi
--spec.template.spec.containers.1.resources.requests.cpu=500m
--spec.template.spec.containers.1.resources.requests.memory=1Gi
```

## 17. EIPPool Creation Fails with "Object 'Kind' is missing"

**Cause:** Missing `--apiVersion=crd.yangtse.cni/v1` and `--kind=EIPPool` parameters.

**Fix:** Include both required fields:
```bash
--apiVersion=crd.yangtse.cni/v1 --kind=EIPPool
```

## 18. EIPPool Creation Fails with 422 "spec.eipAttributes.networkType: Required value"

**Cause:** Missing the required `--spec.eipAttributes.networkType` parameter.

**Fix:** Add `--spec.eipAttributes.networkType=5_bgp` (dynamic BGP) or `5_gray` (dedicated load balancing).

## 19. EIPPool Creation Fails with 403 "name, size, shareType and chargeMode are required"

**Cause:** Missing required bandwidth fields when auto-creating EIPs.

**Fix:** Include all bandwidth fields:
```bash
--spec.eipAttributes.bandwidth.shareType=PER
--spec.eipAttributes.bandwidth.size=5
--spec.eipAttributes.bandwidth.chargeMode=bandwidth
--spec.eipAttributes.bandwidth.name=<bandwidth-name>
```