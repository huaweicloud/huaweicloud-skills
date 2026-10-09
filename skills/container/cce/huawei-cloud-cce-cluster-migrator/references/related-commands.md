# Related Commands Quick Reference

This document provides a consolidated quick-reference table of verified Huawei Cloud KooCLI (`hcloud`) and Kubernetes commands used in CCE migrations. All `hcloud` commands require `--cli-region` (or `--region` for `update-kubeconfig`).

---

## 1. Huawei Cloud Infrastructure Commands

|Service|Operation / Command|Key Parameters|Purpose|
|-|-|-|-|
|**CCE**|`hcloud CCE ListClusters`|`--cli-region=<region>`|Discover target CCE clusters|
|**CCE**|`hcloud CCE ShowCluster`|`--cluster_id=<id> --detail=true`|Inspect cluster status and add-ons|
|**CCE**|`hcloud CCE GetClusterFlavorSpecs`|`--clusterType=VirtualMachine`|Query cluster flavors and capacity|
|**CCE**|`hcloud CCE update-kubeconfig`|`--cluster-id=<id> --region=<region> --output=<path> [--external]`|Sync authenticated CCE kubeconfig|
|**CCE**|`hcloud CCE ListAddonInstances`|`--cluster_id=<id>`|Verify Everest CSI & CoreDNS add-ons|
|**CCE**|`hcloud CCE ListNodePools`|`--cluster_id=<id> --showDefaultNodePool=true`|List cluster node pools|
|**CCE**|`hcloud CCE ListNodes`|`--cluster_id=<id> --limit=100`|List cluster worker nodes|
|**SWR**|`hcloud SWR CreateSecret`|`--cli-region=<region>`|Generate temporary SWR Docker login auth|
|**SWR**|`hcloud SWR ListNamespaces`|`--cli-region=<region>`|List SWR organizations/namespaces|
|**SWR**|`hcloud SWR ListReposDetails`|`--namespace=<org>`|Inspect repositories in an organization|
|**NAT**|`hcloud NAT ListNatGateways`|`--cli-region=<region>`|List NAT Gateways in target VPC|
|**NAT**|`hcloud NAT ListNatGatewaySnatRules`|`--cli-region=<region> [--floating_ip_address=<eip>]`|Inspect SNAT rules for egress whitelisting|
|**VPC**|`hcloud VPC ListVpcs`|`--cli-region=<region>`|List VPCs in target region|
|**VPC**|`hcloud VPC ShowSubnet`|`--subnet_id=<id> --cli-region=<region>`|Query subnet CIDR and available IPs|
|**VPC**|`hcloud VPC ListSecurityGroupRules/v3`|`--security_group_id.1=<sg_id>`|Inspect node security group rules|
|**VPC**|`hcloud VPC CreateSecurityGroupRule/v3`|`--security_group_rule.security_group_id=<id> --security_group_rule.direction=ingress --security_group_rule.protocol=tcp --security_group_rule.multiport=30000-32767 --security_group_rule.remote_ip_prefix=<cidr>`|Open NodePort 30000-32767 for Ingress|
|**ELB**|`hcloud ELB ListLoadBalancers/v3`|`--cli-region=<region>`|List Dedicated ELB instances|
|**ELB**|`hcloud ELB ShowLoadBalancer/v3`|`--loadbalancer_id=<id>`|Inspect ELB VIP, status, and bound EIPs|
|**EIP**|`hcloud EIP ListPublicips/v3`|`--associate_instance_type.1=ELB`|List public EIPs associated with ELBs|
|**EIP**|`hcloud EIP ShowPublicip/v3`|`--publicip_id=<id>`|Query public EIP bandwidth and status|
|**SFSTurbo**|`hcloud SFSTurbo ListShares`|`--cli-region=<region>`|List pre-created SFS Turbo file systems|
|**SFSTurbo**|`hcloud SFSTurbo ShowShare`|`--share_id=<id> --cli-region=<region>`|Query SFS Turbo status, export location, and capacity|

---

## 2. Kubernetes & Migration Tooling Commands

|Tool|Command|Purpose|Reference Guide|
|-|-|-|-|
|**kubectl**|`kubectl get pods -A -o jsonpath='{range .items[*]}{range .spec.containers[*]}{.image}{"\n"}{end}{end}' \| sort -u`|Extract container image inventory|`references/swr-image-sync-guide.md`|
|**kubectl**|`kubectl get svc -A --field-selector spec.type=ExternalName`|Discover external DNS dependencies|`references/external-dependency-audit-guide.md`|
|**kubectl**|`kubectl get pvc,pv -A -o wide`|Inventory source storage volumes|`references/storage-pv-migration-guide.md`|
|**kubectl**|`kubectl apply -f templates/velero-sc-mapping.yaml -n velero`|Apply StorageClass remapping|`references/storage-pv-migration-guide.md`|
|**velero**|`velero backup create <name> --include-namespaces=<ns> --exclude-namespaces=kube-system,velero --wait`|Execute source cluster backup|`references/velero-migration-guide.md`|
|**velero**|`velero restore create <name> --from-backup <backup> --wait`|Restore workloads & volumes on CCE|`references/velero-migration-guide.md`|
|**skopeo**|`skopeo copy --dest-creds="${SWR_AUTH}" --insecure-policy docker://<src> docker://<target-swr>`|Mirror container image to SWR|`references/swr-image-sync-guide.md`|
|**curl**|`curl -Iv https://<domain> --resolve <domain>:443:<cce-elb-eip>`|Pre-cutover Ingress smoke test|`references/traffic-cutover-guide.md`|
