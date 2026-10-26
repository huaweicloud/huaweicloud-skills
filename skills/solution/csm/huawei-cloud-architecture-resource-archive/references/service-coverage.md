# Cloud Service Resource Query Coverage Analysis

> Updated: 2026-10-20

## Overview

This document describes the cloud service resource query capability of this skill. The code registers **43 service modules** that can produce **83 resource types** via KooCLI. Every resource type required by the marker table is covered by at least one registered module — there is no converter-level gap.

For actual test results and remaining gaps, see `gap-analysis.md`.

## 1. Registered Service Modules (43)

```
CCE VPC SUBNET ECS EIP GEIP ELB OBS RMS CDN CCAAS EPS ROUTETABLE SECURITYGROUP
NETWORKACL PEERING RDS DCS DDS DMS GAUSSDB GEMINIDB TAURUSDB LIVE NAT VPN VPCEP DNS
ER WAF CFW CNAD CC2 WORKSPACE DCAAS BMS CCI SFS CSS MRS DLI CloudTable BGP
```

Global services (queried once per account): GEIP / CDN / CCAAS / EPS / CC2 / RMS / OBS

## 2. Resource Types the Scripts Can Produce (83 types)

```
ECS BMS EIP GEIP ELB RDS DCS DDS DMS CCE CCI VPC VPC_Subnet VPC_RouteTable
VPC_SecurityGroup VPC_NetworkACL VPC_Peering WAF CDN_Domain
OBS RMS SFS_Turbo SFS3 EFS CSS MRS
DCAAS(5: DirectConnect / HostedDirectConnect / VirtualGateway / VirtualInterface / GlobalDcGateway)
GeminiDB GaussDB TaurusDB VPCEndpoint
CCAAS(4: CloudConnection / InterRegionBandwidth / BandwidthPackage / NetworkInstance)
CC2(3: CloudConnection / InterRegionBandwidth / BandwidthPackage)
ER(3: router / route table / attachment)
BGP CFW CNAD(2: Domain / DDoSStatus) NAT(3: gateway / SNAT / DNAT)
DNS(4: PublicZone / PrivateZone / Endpoint / ResolverRule)
VPN(4: gateway / connection / customer gateway / P2C gateway)
DLI(4: Queue / FlinkJob / Database / CrossSource) Workspace LIVE CloudTable
+ CCE K8s sub-types (Deployment/StatefulSet/Job/CronJob/PodGroup/DaemonSet/
  Service/Ingress/NetworkPolicy/NetworkPlane/ConfigMap/PVC/HPA/
  NodeAutoScaling/NamespacePermission — requires a cluster with a reachable K8s API endpoint)
```

## 3. Downstream Inference Support

The following service relationships are automatically inferred by `infer_downstream.py`:

| Source Resource | Inferred Downstream | Data Source |
|----------------|---------------------|-------------|
| GEIP | Bound instance (ECS/ELB/NAT) | `associate_instance_id` / `associate_instance_type` |
| ECS | Used image | `image.id` |
| ELB | Backend servers (ECS) | ListPools → ListMembers |
| CCE | Cluster nodes | ListNodes per cluster |
| VPC | Subnets, RouteTables | ListSubnets, ListRouteTables + cloud_resources |
| VPC_Peering | Connected VPCs (request + accept) | `request_vpc_info.vpc_id`, `accept_vpc_info.vpc_id` |
| VPCEndpoint | VPC, Subnet | `vpc_id`, `subnet_id` |
| VPN | VPC | `vpc_id` |
| VPN_Connection | VPN gateway, Customer gateway | `vgw_id`, `cgw_id` |
| EIP | Bound instance (ECS/ELB/VPN/PORT) | `associate_instance_id` / `instance_type` |
| CCAAS | Inter-region bandwidth | `cloud_connection_id` |

## 4. Capability Summary

- ✅ **43 service modules** registered, covering **83 resource types** — no converter-level gap.
- ✅ **11 downstream inference rules** covering all major resource relationships.
- ⚠️ CCE K8s sub-types (15+): require a cluster with a **reachable K8s API endpoint** (known limitation).
- ⚠️ DCAAS HostedDirectConnect: requires carrier-side provisioning, not self-service.
- ⚠️ Whether a given type is *actually returned* depends on the account owning that resource — see `gap-analysis.md` for test results.
