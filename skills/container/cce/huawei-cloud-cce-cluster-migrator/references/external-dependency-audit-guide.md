# External Connection Dependency Audit and Connectivity Probing Guide

This document outlines the end-to-end methodology for discovering, auditing, and validating external connection dependencies when migrating Kubernetes workloads to Huawei Cloud CCE.

## Why External Dependency Auditing is Critical

In Kubernetes migrations, workloads transition to a new VPC network CIDR, new node subnets, and new egress IP addresses. Even if container workloads deploy cleanly, production outages will occur immediately upon cutover if:

1. **Egress IP Whitelists**: Upstream APIs (payment gateways, SMS providers, financial interfaces, partner webhooks) reject outbound requests because the new egress IP (Huawei Cloud NAT Gateway EIP) has not been whitelisted.
2. **Private Network Routing**: Internal dependencies (on-premises databases, LDAP/AD, ERP, MQ) are unreachable due to missing Direct Connect (DC) or VPN routes from the target CCE VPC.
3. **Internal DNS Resolution**: Private internal domain names (`*.corp.internal`, `*.idc.local`) fail to resolve because target CCE CoreDNS lacks upstream forwarding rules.
4. **Security Group Egress Filters**: CCE node security groups block required outbound ports.

---

## Phase 1: Discovery & Dependency Inventory

Execute the following extraction procedures on the source cluster prior to migration.

### 1. ExternalName Services Discovery

Inspect all Kubernetes Services that route in-cluster traffic to external FQDNs:

```bash
kubectl get svc -A --field-selector spec.type=ExternalName \
  -o custom-columns=NAMESPACE:.metadata.namespace,NAME:.metadata.name,EXTERNAL_NAME:.spec.externalName
```

### 2. Headless Services and Manual Endpoints

Identify headless Services configured with manual Endpoints (typically pointing to static external database IPs or legacy hosts without Pod selectors):

```bash
kubectl get endpoints -A -o jsonpath='{range .items[?(!@.metadata.labels.kubernetes\.io/service-name)]}{.metadata.namespace}{"\t"}{.metadata.name}{"\t"}{range .subsets[*].addresses[*]}{.ip}{" "}{end}{"\n"}{end}'
```

Or query all services without selectors:

```bash
kubectl get svc -A -o jsonpath='{range .items[?!@.spec.selector]}{.metadata.namespace}{"\t"}{.metadata.name}{"\t"}{.spec.type}{"\n"}{end}'
```

### 3. ConfigMap & Secret Scanning for External Endpoints

Scan ConfigMaps and Secrets across application namespaces for external IP addresses, database connection strings, and domain names:

```bash
# Scan ConfigMaps for external hosts and URLs
kubectl get cm -A -o jsonpath='{range .items[*]}{.metadata.namespace}{"/"}{.metadata.name}{"\n"}{range $k,$v in .data}{"  "}{$k}{": "}{$v}{"\n"}{end}{end}' | \
  grep -E "(http://|https://|jdbc:|mongodb://|redis://|amqp://|[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3})"
```

### 4. Pod Spec Static Host Aliases

Audit workloads using `spec.hostAliases` for hardcoded `/etc/hosts` mappings:

```bash
kubectl get pods,deployments,statefulsets,daemonsets -A \
  -o jsonpath='{range .items[*]}{.kind}{"/"}{.metadata.namespace}{"/"}{.metadata.name}{range .spec.template.spec.hostAliases[*]}{"\n  "}{.ip}{" -> "}{.hostnames}{end}{"\n"}{end}' | \
  grep -v "^[A-Za-z]*/[^/]*$"
```

---

## Phase 2: Huawei Cloud Egress Architecture & IP Whitelisting

### 1. Egress Architecture Overview

```
CCE Pods (VPC Subnet) ──> CCE Node ──> NAT Gateway (SNAT Rule) ──> Elastic IP (EIP) ──> Internet / Partner APIs
```

All outbound internet traffic from CCE cluster nodes and pods traverses the Huawei Cloud NAT Gateway SNAT rule associated with the cluster subnet.

### 2. Pre-Migration Customer Egress Requirement Gate

During migration planning, explicitly audit and confirm with the customer:

1. **Workload Public Egress**: Does the application call external internet endpoints (e.g. payment gateways, OAuth providers, SMS services, partner webhooks)?
2. **Container Image Source**: Will container images be pulled directly from public registries (`docker.io`, `quay.io`), or will 100% of images be mirrored to Huawei Cloud SWR?

#### NAT Gateway Decision Matrix:

|Scenario|Customer Workload Internet Egress|Image Registry Strategy|NAT Gateway + SNAT Required?|Notes|
|-|-|-|-|-|
|**A (Recommended)**|None (Strictly Internal)|100% Mirrored to SWR|**No (Cost-Optimized)**|SWR traffic routes via internal VPC endpoints without NAT.|
|**B (Hybrid)**|Yes (Calls External APIs)|Mirrored to SWR|**Yes**|NAT Gateway required for workload egress; whitelisting required.|
|**C (Direct Pull)**|Any|Direct `docker.io` Pulls|**Yes (Mandatory)**|CCE nodes cannot reach `docker.io` without outbound SNAT.|

### 3. Inspect Target NAT Gateway and SNAT Rules

Verify active NAT Gateways in the target region:

```bash
hcloud NAT ListNatGateways --cli-region=<region_id>
```

Verify SNAT rules and retrieve the public egress EIP(s):

```bash
hcloud NAT ListNatGatewaySnatRules --cli-region=<region_id>
```

Filter SNAT rules by the target CCE cluster's VPC router ID or subnet network ID:

```bash
hcloud NAT ListNatGatewaySnatRules --cli-region=<region_id> --floating_ip_address="{target_eip}"
```

### 4. Partner API Whitelisting Action Plan

Before initiating workload cutover:

1. Collate all discovered upstream endpoints (payment gateways, bank APIs, SMS gateways, government systems).
2. Submit the target CCE NAT Gateway EIP (`floating_ip_address`) to partner security teams for firewall/WAF allowlisting.
3. Establish a dual-whitelist window: keep both source cluster egress IP and target CCE egress IP active simultaneously during migration.

---

## Phase 3: Hybrid Cloud & On-Premises Connectivity

For dependencies hosted in on-premises IDCs or dedicated VPCs:

1. **Direct Connect (DC) / Virtual Private Network (VPN)**:
   - Ensure target CCE VPC has active route table entries pointing on-premises CIDRs (e.g., `10.0.0.0/8` or `172.16.0.0/12`) to the Virtual Gateway (VGW) or VPN Gateway.
2. **Security Group Egress Rules**:
   - Verify the CCE node security group allows egress TCP/UDP traffic to the destination on-premises subnets:
     ```bash
     hcloud VPC ListSecurityGroupRules/v3 --cli-region=<region_id> --security_group_id.1={cce_node_sg_id}
     ```

---

## Phase 4: CoreDNS Private Domain Forwarding

If workloads resolve private enterprise domains (e.g., `db.corp.internal`, `auth.idc.local`), configure CoreDNS upstream forwarding in the target CCE cluster.

Inspect the target CCE CoreDNS ConfigMap:

```bash
kubectl get cm coredns -n kube-system -o yaml
```

Add upstream forward blocks to the Corefile data:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: coredns
  namespace: kube-system
data:
  Corefile: |
    .:53 {
        errors
        health
        kubernetes cluster.local in-addr.arpa ip6.arpa {
           pods insecure
           fallthrough in-addr.arpa ip6.arpa
        }
        forward . /etc/resolv.conf
        cache 30
        loop
        reload
        loadbalance
    }
    corp.internal:53 {
        errors
        cache 30
        forward . 192.168.10.10 192.168.10.11
    }
```

Apply and restart CoreDNS:

```bash
kubectl apply -f coredns-custom.yaml -n kube-system
kubectl rollout restart deployment coredns -n kube-system
```

---

## Phase 5: In-Cluster Pre-Cutover Connectivity Probing

Never execute traffic cutover without verifying end-to-end network reachability from within the target CCE cluster.

### 1. Cloud Management Plane Egress Verification

Verify that the target CCE cluster subnet has an active SNAT rule on the NAT Gateway:

```bash
hcloud NAT ListNatGatewaySnatRules --cli-region=<region_id>
```

### 2. Ad-Hoc Ephemeral Pod Probing (Optional)

For quick interactive troubleshooting of a specific external dependency:

```bash
kubectl run net-troubleshoot --rm -it --image=alpine --restart=Never -- \
  wget -qO- --timeout=5 https://www.huaweicloud.com
```

For TCP port reachability to private dependencies:

```bash
kubectl run nc-troubleshoot --rm -it --image=alpine --restart=Never -- \
  nc -zv 192.168.10.50 3306
```

> [!NOTE] > **Image Pull Failures (401 Unauthorized / ErrImagePull)**:
> If the target CCE cluster does not have an active NAT Gateway (SNAT rule), worker nodes cannot reach `docker.io` or public registries over the internet. Additionally, CCE's default containerd mirror may intercept and reject unauthenticated requests.
> Always use images already mirrored to your SWR namespace (e.g., `--image=swr.<region>.myhuaweicloud.com/<org>/alpine`) with `default-secret` bound, or ensure a NAT Gateway is provisioned before testing public image pulls.

---

## Acceptance Verification Gate

Migration cannot proceed to Phase 6 (Traffic Cutover) until:

- [ ] All `ExternalName` and headless endpoints are documented and validated.
- [ ] Upstream third-party APIs have whitelisted the target CCE NAT Gateway EIP.
- [ ] Direct Connect / VPN routes to on-premise dependencies are verified.
- [ ] CoreDNS resolves enterprise private domain names from within CCE pods.
- [ ] Target CCE cluster subnet SNAT rule is active.
