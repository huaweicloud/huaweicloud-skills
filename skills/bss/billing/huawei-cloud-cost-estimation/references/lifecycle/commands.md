# Provisioning operation allowlist

Evidence snapshot: KooCLI 7.2.2. This reference preserves operation identifiers and their exact meanings; obtain parameters at runtime with `hcloud <Service> <Operation> --help`. Prerequisite or configuration operations that are not independently billable are labeled explicitly. Unsubscribe is not allowlisted; follow the console guidance in `concepts.md`.

Dependencies indicate lookup directions, not parameter definitions: `P` project, `ORG` account, `EP` enterprise project, `N` network, `AZ` availability zone, `IMG` image, `DISK` disk type, `KEY` key pair, `SPEC` specification, `PRODUCT` product, `PARENT` parent resource, `STACK` IDE stack, and `H` runtime help only.

## Provisioning operations (74)

| Operation | Meaning | Billing | Dependencies |
| --- | --- | --- | --- |
| `APIG/CreateInstanceV2` | Create a pay-per-use dedicated API Gateway instance (V2). | Pay-per-use | P, EP, N |
| `APIG/CreateOrder` | Create an order for a yearly/monthly dedicated API Gateway instance (V2). | Yearly/monthly | P, EP, N, PRODUCT |
| `BMS/CreateBareMetalServers` | Create one or more Bare Metal Servers. | Pay-per-use or yearly/monthly | P, EP, N, AZ, IMG, DISK, KEY, SPEC |
| `CBH/CreateCbh` | Create a Cloud Bastion Host instance pending an order. | Order prerequisite; not independently billable | P, EP, N, AZ, SPEC |
| `CBH/CreateInstance` | Create a yearly/monthly Cloud Bastion Host instance. | Yearly/monthly | P, EP, N, AZ |
| `CBH/CreateInstanceOrder` | Create a yearly/monthly Cloud Bastion Host instance order. | Yearly/monthly | P, PRODUCT |
| `CBR/CreatePolicy` | Create a Cloud Backup and Recovery backup or replication policy. | Not independently billable | P |
| `CBR/CreatePostPaidVault` | Create a yearly/monthly Cloud Backup and Recovery vault. | Yearly/monthly | P, EP |
| `CBR/CreateVault` | Create a Cloud Backup and Recovery vault. | Determine from current help | P, EP, AZ |
| `CCE/CreateAutopilotCluster` | Create an empty pay-per-use CCE Autopilot cluster. | Pay-per-use | P, N, AZ, IMG, SPEC |
| `CCE/CreateCluster` | Create an empty CCE Standard or Turbo cluster. | Pay-per-use or yearly/monthly | H |
| `CCE/CreateNode` | Create a node in an existing CCE cluster. | Pay-per-use or yearly/monthly | P, N, AZ, IMG, DISK, SPEC, PARENT |
| `CCE/CreateNodePool` | Create a node pool in an existing CCE cluster, optionally with initial nodes. | Nodes: pay-per-use or yearly/monthly | H |
| `CCE/SubscribePackageProducts` | Subscribe to a CCE package. | Determine from current help | PRODUCT |
| `CDM/CreateCluster` | Create a Cloud Data Migration cluster. | Determine from current help | H |
| `CDN/CreateDomain/v1` | Create a CDN acceleration domain using the KooCLI V1 binding. | Determine from current help | H |
| `CDN/CreateDomain/v2` | Create a CDN acceleration domain using the KooCLI V2 binding. | Determine from current help | H |
| `CFW/CreateEastWestFirewall` | Create an east-west firewall for an existing Cloud Firewall instance. | Configuration; not independently billable | P, EP |
| `CFW/CreateFirewall` | Purchase a Cloud Firewall instance. | Pay-per-use or yearly/monthly | P, EP, N, SPEC |
| `CloudTable/CreateCloudTableCluster` | Create a CloudTable HBase, Doris, or ClickHouse cluster. | Determine from current help | H |
| `CloudTable/CreateCluster` | Create a CloudTable cluster using the deprecated V2 API. | Determine from current help | H |
| `CloudIDE/CreateInstance` | Create a CodeArts IDE Online cloud development environment. | Pay-per-use | ORG, STACK |
| `CodeArtsInspector/CreatePurchaseOrder` | Create a website vulnerability scanning package order for CodeArts Inspector, formerly VSS. | Paid subscription; determine from help | P, PRODUCT |
| `CSE/CreateEngine` | Create a dedicated ServiceComb engine, registry/configuration center, or application gateway in Cloud Service Engine. | Pay-per-use | P, N, SPEC |
| `CSS/CreateCluster/v1` | Create a single-node-role Elasticsearch cluster in Cloud Search Service using the deprecated V1 API. | Pay-per-use or yearly/monthly | P, EP, N, AZ, DISK, SPEC |
| `CSS/CreateCluster/v2` | Create a multi-node-role Cloud Search Service cluster (V2). | Pay-per-use or yearly/monthly | P, EP, N, AZ, DISK, SPEC |
| `DataArtsStudio/PayForDgcOneKey` | Purchase a DataArts Studio instance, formerly DGC, in one step. | Determine from current help | H |
| `DBSS/CreateDbEncryptInstancePeriod` | Purchase a yearly/monthly Database Security Service database-encryption instance. | Yearly/monthly | P, EP, N, AZ, IMG, SPEC |
| `DBSS/CreateDbOmInstancePeriod` | Purchase a yearly/monthly Database Security Service database-operations instance. | Yearly/monthly | P, EP, N, AZ, IMG, SPEC |
| `DBSS/CreateInstancesPeriodOrder` | Create a yearly/monthly Database Security Service audit instance using the API scheduled for retirement. | Yearly/monthly | P, EP, N, AZ, IMG, SPEC |
| `DBSS/CreateInstancesPeriodOrderNew` | Create a yearly/monthly Database Security Service audit instance using the current API. | Yearly/monthly | P, EP, N, AZ, IMG, SPEC |
| `DCS/CreateInstance` | Create a Distributed Cache Service instance using the recommended V2 API. | Pay-per-use or yearly/monthly | P, EP, N, SPEC |
| `DDM/CreateDdmInstance` | Purchase a Distributed Database Middleware instance (V3). | Determine from current help | H |
| `DDM/CreateInstance` | Purchase a Distributed Database Middleware instance (V1). | Determine from current help | H |
| `DDS/CreateInstance` | Create a Document Database Service cluster, replica set, or single-node instance (V3). | Pay-per-use or yearly/monthly | P, EP, N, AZ, SPEC |
| `DeH/CreateDedicatedHost` | Allocate one or more Dedicated Hosts. | Determine from current help | H |
| `DSC/CreateProductOrder` | Submit a Data Security Center instance order. | Determine from current help | P, PRODUCT |
| `DWS/CreateCluster` | Create a Data Warehouse Service cluster using the legacy V1.0 API, maintained for existing features only. | Determine from current help | P, EP, N, AZ, KEY, SPEC |
| `DWS/CreateClusterV2` | Create a Data Warehouse Service cluster using the recommended V2 API. | Determine from current help | P, EP, N, AZ, KEY, SPEC |
| `ECS/CreatePostPaidServers` | Create one or more pay-per-use Elastic Cloud Servers (V1). | Pay-per-use | P, EP, N, AZ, IMG, DISK, KEY, SPEC |
| `ECS/CreateServers` | Create one or more Elastic Cloud Servers (V1.1). | Pay-per-use or yearly/monthly | P, EP, N, AZ, IMG, DISK, KEY, SPEC |
| `EIP/CreatePrePaidPublicip` | Allocate a yearly/monthly Elastic IP. | Yearly/monthly | P, EP |
| `EIP/CreatePublicip` | Allocate a pay-per-use IPv4 or IPv6 Elastic IP. | Pay-per-use | P, EP |
| `EIP/CreateSharedBandwidth` | Create EIP shared bandwidth (V2.0). | Determine from current help | P, EP |
| `ELB/CreateLoadBalancer/v2` | Create a shared private Elastic Load Balance instance (V2). | Determine from current help | P, EP, N |
| `ELB/CreateLoadBalancer/v3` | Create a dedicated Elastic Load Balance instance (V3). | Pay-per-use or yearly/monthly | P, EP, N, AZ, SPEC |
| `EPS/CreateEnterpriseProject` | Create an enterprise project. | Free logical governance object; not a resource order | P |
| `ESW/CreateInstance` | Create an Enterprise Switch instance. | Pay-per-use | H |
| `EVS/CreateVolume` | Create an Elastic Volume Service disk (V2.1). | Pay-per-use or yearly/monthly | P, EP, AZ, IMG, DISK |
| `GaussDB/CreateGaussMySqlInstance` | Create a TaurusDB instance. | Pay-per-use or yearly/monthly | P, EP, N, AZ, SPEC |
| `GaussDB/CreateStarrocksInstance` | Create an HTAP standard StarRocks instance for a specified TaurusDB instance. | Pay-per-use or yearly/monthly | P, N, SPEC, PARENT |
| `GaussDBforNoSQL/CreateInstance` | Create a GeminiDB instance, including one restored from backup or a specified time. | Pay-per-use or yearly/monthly | P, EP, N, AZ, SPEC, PRODUCT |
| `GaussDBforopenGauss/CreateDatabaseInstance` | Create a GaussDB instance through API V3.2. | Pay-per-use or yearly/monthly | P, EP, N, AZ, SPEC |
| `GaussDBforopenGauss/CreateDbInstance` | Create a GaussDB instance through API V3.1. | Pay-per-use or yearly/monthly | P, EP, N, AZ, SPEC |
| `GaussDBforopenGauss/CreateGaussDbInstance` | Create a GaussDB instance through API V5 and the new IAM authentication plane. | Pay-per-use or yearly/monthly | P, EP, N, AZ, SPEC |
| `GaussDBforopenGauss/CreateInstance` | Create a GaussDB enterprise or centralized instance through the historical V3 API. | Pay-per-use or yearly/monthly | P, EP, N, AZ, SPEC |
| `HSS/CreateAntiVirusPaidTask` | Create a paid Host Security Service virus-scanning task. | Paid | P, EP |
| `HSS/CreateQuotasOrder` | Subscribe to yearly/monthly Host Security Service protection quotas. | Yearly/monthly | P, EP |
| `IEC/CreateInstance` | Create an Intelligent Edge Cloud instance. | Determine from current help | H |
| `Kafka/CreatePostPaidKafkaInstance` | Create a Distributed Message Service for Kafka instance. | Pay-per-use or yearly/monthly | P, EP, N, PRODUCT |
| `MetaStudio/CreateMetaStudioOrders` | Subscribe to yearly/monthly, one-time, or pay-per-use MetaStudio packages. | Yearly/monthly, one-time, or pay-per-use packages | H |
| `MRS/CreateCluster/v1` | Create a MapReduce Service cluster and submit a job through API V1.1. | Pay-per-use or yearly/monthly | P, EP, N, DISK |
| `MRS/CreateCluster/v2` | Create a MapReduce Service cluster through API V2. | Pay-per-use or yearly/monthly | P, EP, N, AZ, KEY |
| `NAT/CreateNatGateway` | Create a public NAT Gateway instance. | Pay-per-use or yearly/monthly | P, EP, N |
| `RabbitMQ/CreatePostPaidInstanceByEngine` | Create a Distributed Message Service for RabbitMQ instance. | Pay-per-use or yearly/monthly | P, EP, N, PRODUCT |
| `RDS/CreateInstance` | Create an RDS single, primary/standby, cluster, or read-replica instance (V3). | Pay-per-use or yearly/monthly | P, EP, N, AZ, SPEC |
| `RDS/CreateInstanceIam5` | Create an RDS instance through API V5, including yearly/monthly encryption with a RAM-shared KMS key. | Pay-per-use or yearly/monthly | P, EP, N, AZ, SPEC |
| `RocketMQ/CreateInstanceByEngine` | Create a Distributed Message Service for RocketMQ instance. | Pay-per-use or yearly/monthly | P, EP, N, PRODUCT |
| `SCM/SubscribeCertificate` | Purchase a public SSL certificate and create its pending certificate application. | Paid | H |
| `SecMaster/CreateSubscriptionOrder` | Subscribe to or configure SecMaster editions, quotas, and add-on packages. | Pay-per-use, yearly/monthly, or configuration | P, PRODUCT |
| `VPN/CreateVpnServer` | Create an SSL VPN server module in an existing Point-to-Cloud VPN gateway. | Configuration; not independently billable | P, N, PARENT |
| `WAF/CreateCloudWafPostPaidResource` | Provision pay-per-use cloud-mode Web Application Firewall resources. | Pay-per-use | P, EP |
| `WAF/CreateInstance` | Create a pay-per-use dedicated Web Application Firewall engine instance. | Pay-per-use | P, EP, N, SPEC |
| `WAF/CreatePrepaidCloudWaf` | Purchase a yearly/monthly cloud-mode Web Application Firewall edition and expansion packages. | Yearly/monthly | P, EP, PRODUCT |

## Dependency queries

Read current runtime help before read-only queries too. Parameters are not specified here.

| Label | Operations | Meaning |
| --- | --- | --- |
| P | `IAM/KeystoneListAuthProjects`, `IAM/KeystoneListProjects` | Project scope |
| ORG | `IAM/KeystoneListAuthDomains` | Current account/domain |
| EP | `EPS/ListEnterpriseProject` | Enterprise project |
| N | `VPC/ListVpcs/v3`, `VPC/ListSubnets`, `VPC/ListSecurityGroups/v3` | VPC, subnet, and security group |
| AZ | `ECS/NovaListAvailabilityZones`, `ECS/ListServerAzInfo` | Availability zone |
| IMG | `IMS/ListImages` | Image |
| DISK | `EVS/CinderListVolumeTypes` | Disk type |
| KEY | `ECS/NovaListKeypairs` | Key pair |
| SPEC | `ECS/ListFlavors`; optionally `ECS/ListFlavorSellPolicies`; each other service's own `ListFlavors` or equivalent | Preserve target-AZ status, billing support, and restrictions; follow `concepts.md`. A basic flavor list does not establish provisionability. |
| PRODUCT | `Kafka/ListEngineProducts`, `RabbitMQ/ListEngineProducts`, `RocketMQ/ListEngineProducts`, `SecMaster/ListSubscriptionProduct` | Products available for sale |
| PARENT | `CCE/ListClusters`, `GaussDB/ListGaussMySqlInstances`; service-specific `List*` operations | Parent cluster, instance, or gateway |
| STACK | `CloudIDE/ListStacks` | CodeArts IDE Online stacks and available specifications |
| H | `hcloud <Service> <Operation> --help` | Runtime discovery; stop if help fails |

## ECS, EVS, and EIP payment fields

KooCLI 7.2.12 snapshot, 2026-10-27. Recheck current help. Payment defaults, conditional fields and order pitfalls are in `../gotchas.md` G09–G11.

| Operation | Field prefix | Mode; period unit/count | Auto-pay / auto-renew |
| --- | --- | --- | --- |
| `ECS/CreateServers` | `server.extendparam` | `chargingMode`; `periodType` / `periodNum` | `isAutoPay` / `isAutoRenew` (strings) |
| `EVS/CreateVolume` | `bssParam` | `chargingMode`; `periodType` / `periodNum` | `isAutoPay` / `isAutoRenew` (strings) |
| `EIP/CreatePrePaidPublicip` | `extendParam` | `charge_mode`; `period_type` / `period_num` | `is_auto_pay` / `is_auto_renew` (booleans) |
