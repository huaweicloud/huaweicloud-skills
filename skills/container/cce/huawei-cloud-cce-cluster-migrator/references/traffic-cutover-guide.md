# Ingress and Traffic Cutover Guide

This guide details the traffic switchover procedure from the source Kubernetes environment to Huawei Cloud CCE using Huawei Cloud Elastic Load Balance (ELB) and DNS cutover strategies.

---

## 1. CCE Ingress Configuration (Dedicated ELB + Public EIP)

Huawei Cloud CCE natively integrates with Elastic Load Balance (ELB) and Elastic IP (EIP) via annotations on Kubernetes Ingress resources. External internet traffic arrives at the public EIP, forwards to the Dedicated ELB instance, and is distributed across CCE worker nodes or directly to Pod ENIs.

### CCE Cluster Architecture & Backend Service Type Rules

> [!IMPORTANT] > **Cluster Type & Backend Service Compatibility**:
>
> - **CCE Turbo + Dedicated ELB (Recommended / Mandatory for New Deployments)**:
>   - Pods are assigned secondary IPs directly on Huawei Cloud Yangtse Elastic Network Interfaces (ENI).
>   - ELB routes traffic directly to Pod IPs without node-level port forwarding.
>   - Backend Kubernetes Services **support `ClusterIP` natively** (or `NodePort`).
> - **CCE Standard (Legacy / Maintenance Mode)**:
>   - ELB Ingress controller cannot route directly to Pod IPs. Traffic must traverse worker node ports.
>   - Backend Kubernetes Services **MUST be defined as `type: NodePort`**.
>   - **Critical Failure Mode**: If `ClusterIP` is used on CCE Standard, the Ingress controller will fail with:
>     `can not found protocol port of pod xxx, skip add member` and `GeneratePolicyFailed`.
>   - Worker node security groups must explicitly allow inbound traffic on the NodePort range (`30000-32767`).

### Dedicated ELB vs Shared ELB

- **Dedicated ELB** (`kubernetes.io/elb.class: performance`): Mandatory for production migrations, providing isolated compute instances, customizable SLA, high throughput, and direct public EIP binding.
- **Shared ELB** (`kubernetes.io/elb.class: union`): Multi-tenant shared infrastructure for cost-sensitive non-production workloads.

### 1.1 Ingress Specification Standard

In Kubernetes v1.23+ and CCE, Ingress manifests must follow these specifications:

- **Ingress Controller Class**: Specify `spec.ingressClassName: cce` to bind to the native Huawei Cloud CCE Ingress Controller.
- **Path Matching**: Set `pathType: ImplementationSpecific` combined with the CCE path property extension:
  ```yaml
  property:
    ingress.beta.kubernetes.io/url-match-mode: STARTS_WITH # or EQUAL_TO
  pathType: ImplementationSpecific
  ```
- **ELB Class & Listener Port**: Specify `kubernetes.io/elb.class: performance` (Dedicated ELB) and `kubernetes.io/elb.port: '80'` (or `'443'`).
- **Resource Tagging**: Pass tags via `kubernetes.io/elb.tags: key1=value1,key2=value2`.

### 1.2 Ingress with Pre-Provisioned Dedicated ELB (by ELB ID)

In production migrations, an existing Dedicated ELB with a pre-bound public EIP is recommended. Point the Ingress to the ELB via `kubernetes.io/elb.id`. If using HTTPS (port 443), also provide `kubernetes.io/elb.cert-id`. See `templates/ingress-elb-eip-template.yaml` (Option 2) for manifest examples.

### 1.3 Ingress with Auto-Created Dedicated ELB and Public EIP

CCE can dynamically provision a Dedicated ELB and bind an EIP automatically during Ingress creation via `kubernetes.io/elb.autocreate`.

> [!WARNING] > **`elb.autocreate` Syntax, ID Semantics, and Immutability Constraints**:
>
> 1. **Subnet ID Fields**:
>    - **`vip_subnet_cidr_id`**: The IPv4 Subnet CIDR ID (Neutron Subnet ID, e.g. `bf23419b-...`), retrieved from `neutron_subnet_id` via `hcloud VPC ListSubnets --cli-region=<region_id>`.
>    - **`elb_virsubnet_ids`**: Plural array of VPC Subnet IDs (Network IDs, e.g. `["f2e3f433-..."]`), retrieved from the `id` field of the subnet.
>    - **`vip_address`**: Optional internal VIP address for the load balancer.
> 2. **Bandwidth & Public IP Fields**:
>    - `bandwidth_name`, `bandwidth_chargemode` (`bandwidth` or `traffic`), `bandwidth_size` (Mbit/s), `bandwidth_sharetype` (`PER` or `WHOLE`), and `eip_type` (`5_bgp`).
> 3. **Mandatory ELB Fields**: Dedicated ELB requires `available_zone` (array of AZ strings) and `l7_flavor_name` (e.g. `L7_flavor.elb.s1.small` or `L7_flavor.elb.pro.max`).
> 4. **Strict Immutability**: The `kubernetes.io/elb.autocreate` annotation **cannot be modified** on an existing Ingress. Modifying fields in-place triggers webhook rejection. To change ELB parameters, delete and re-create the Ingress:
>    ```bash
>    kubectl delete ingress <ingress-name> -n <namespace>
>    kubectl apply -f <ingress-manifest>.yaml
>    ```

See `templates/ingress-elb-eip-template.yaml` (Option 1) for the full autocreate manifest configuration.

### 1.4 CCE Node Security Group for Inbound Traffic

When ELB forwards traffic to worker nodes on Kubernetes `NodePort` ranges (`30000-32767`), verify that the CCE node security group allows ingress traffic:

```bash
# Inspect active security group rules on the node security group
hcloud VPC ListSecurityGroupRules/v3 --cli-region=<region_id> --security_group_id.1=<cce-node-sg-id>

# Allow NodePort ingress from the VPC or client CIDR
hcloud VPC CreateSecurityGroupRule/v3 --cli-region=<region_id> --security_group_rule.security_group_id=<cce-node-sg-id> --security_group_rule.direction=ingress --security_group_rule.protocol=tcp --security_group_rule.multiport=30000-32767 --security_group_rule.remote_ip_prefix=<client_or_vpc_cidr> --security_group_rule.description="Allow CCE NodePort ingress"
```

---

## 2. Pre-Cutover Validation (Smoke Testing)

Before updating public DNS records, validate that the target CCE cluster and ingress respond correctly:

1. Retrieve the public EIP and operational status of the target ELB instance:

   ```bash
   hcloud ELB ShowLoadBalancer/v3 --cli-region=<region_id> --loadbalancer_id=<elb-id>
   ```

2. Query EIP details associated with ELB instances:

   ```bash
   hcloud EIP ListPublicips/v3 --cli-region=<region_id> --associate_instance_type.1=ELB
   ```

3. Test target endpoints using `curl` with the `--resolve` flag:
   ```bash
   curl -Iv https://app.example.com \
     --resolve app.example.com:443:<target-elb-eip>
   ```
4. Verify TLS handshake, HTTP status code (e.g. 200 OK), and backend service response headers.

---

## 3. DNS Switchover Strategy

### Option A: Weighted DNS Migration (Recommended for High-Traffic Services)

1. Lower DNS Time-to-Live (TTL) on the source domain to `60` seconds at least 24 hours in advance.
2. In Huawei Cloud DNS (or current DNS provider), configure weighted records:
   - Initial Canary: `90%` Source IP / `10%` Target CCE ELB IP.
   - Monitor error rates (HTTP 5xx) and latency in Huawei Cloud Cloud Eye (AOM).
   - Mid Stage: `50%` Source IP / `50%` Target CCE ELB IP.
   - Final Stage: `0%` Source IP / `100%` Target CCE ELB IP.

### Option B: Immediate Cutover (Maintenance Window)

1. Announce scheduled maintenance window.
2. Scale down non-essential source workloads or set them to read-only mode to stop writes.
3. Perform final incremental storage sync (see `storage-pv-migration-guide.md`).
4. Repoint DNS A/CNAME record to target CCE ELB IP/domain.
5. Verify live traffic arrival on CCE.

---

## 4. Rollback Playbook

If unexpected failures occur during cutover:

1. Immediately revert DNS records to the source cluster IP address.
2. If stateful writes occurred on CCE, reverse-sync delta data back to the source storage before restoring traffic.
3. Keep the target CCE cluster running for root-cause diagnosis.
