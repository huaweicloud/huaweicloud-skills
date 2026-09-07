#!/usr/bin/env python3
"""Build lifecycle closure plans for common Huawei Cloud service tasks."""

from __future__ import annotations

import argparse
from types import SimpleNamespace
from typing import Any

import hcloud_common
import hcloud_lts_readonly
import hcloud_security_policy
import hcloud_service_change_plan
import hcloud_service_readiness

CLOSURE_SERVICES = ("VPC", "EIP", "EVS", "ELB", "RDS", "OBS", "DNS", "SCM", "CDN", "CES_LTS")
SERVICE_ALIASES = {
    "CES": "CES_LTS",
    "LTS": "CES_LTS",
    "CES+LTS": "CES_LTS",
    "CES_LTS": "CES_LTS",
}

SERVICE_CLOSURE_PROFILES: dict[str, dict[str, Any]] = {
    "VPC": {
        "task": "security-group-rule",
        "tenant_goals": ["上好云", "用好云"],
        "default_operation": "CreateSecurityGroupRule",
        "maturity": "p0-closure",
        "summary": (
            "Close the network and security-group loop before exposing an ECS, EIP, or ELB entry point."
        ),
        "recommended_inputs": [
            "vpc_id",
            "subnet_id",
            "security_group_id",
            "direction",
            "protocol",
            "remote_ip_prefix",
            "port_range_min",
            "port_range_max",
        ],
        "target_params": ["vpc_id", "subnet_id", "security_group_id", "security_group_rule_id"],
        "dependency_checks": [
            "Confirm region/project and the canonical VPC/subnet/security group before changing rules.",
            "List VPCs, subnets, security groups, and security group rules before choosing a target.",
            "Check whether the target security group is already attached to ECS, ELB backend members, or other resources.",
        ],
        "parameter_checks": [
            "Security group rule changes must state direction, protocol, source CIDR, and port range.",
            "CIDR and port intent must match the workload entry path: admin, web, ELB backend, or private-only.",
            "Do not infer a missing source CIDR from the user's goal; ask for a fixed admin, office, VPN, bastion, ELB, or private CIDR.",
        ],
        "risk_gates": [
            {
                "code": "sensitive_ingress",
                "severity": "hard",
                "message": (
                    "Block unrestricted IPv4 ingress for SSH 22 and development ports 3000/5000/8000/8080. "
                    "Exact TCP 80/443 requires an explicit public Web plan."
                ),
            },
            {
                "code": "connection_tracking",
                "severity": "medium",
                "message": "Changing ingress priority, policy, protocol, port, or source can affect existing instance traffic.",
            },
        ],
        "verification_checks": [
            "Read back ShowSecurityGroup and ShowSecurityGroupRule when target IDs are known.",
            "For public access tasks, verify the EIP or ELB entry path plus backend ECS security group.",
            "For admin access, verify only from the approved source CIDR and record temporary-rule cleanup needs.",
        ],
        "governance_checks": [
            "Record owner, workload, expiry, and approved source CIDR for each non-default ingress rule.",
            "Create cleanup or review tasks for temporary SSH or test Web rules.",
        ],
        "official_docs": [
            {
                "title": "Huawei Cloud VPC security group and rule overview",
                "url": "https://support.huaweicloud.com/usermanual-vpc/zh-cn_topic_0073379079.html",
            }
        ],
    },
    "EIP": {
        "task": "public-entry-binding",
        "tenant_goals": ["上好云", "用好云", "管好云"],
        "default_operation": "UpdatePublicip",
        "maturity": "p0-closure",
        "summary": "Treat EIP create/bind/unbind/release as public exposure and cost-impacting changes.",
        "recommended_inputs": [
            "publicip_id",
            "target_resource_id",
            "target_port_id",
            "bandwidth_id",
            "bandwidth_size",
            "billing_mode",
        ],
        "target_params": ["publicip_id", "bandwidth_id"],
        "dependency_checks": [
            "Confirm the EIP, target ECS/port/ELB/NAT resource, region, and project before binding.",
            "Check whether the EIP is already bound, idle, shared-bandwidth backed, or billed independently.",
            "Check the target security group before assuming the public IP is reachable.",
        ],
        "parameter_checks": [
            "Binding must identify the exact EIP and target resource/port.",
            "Creation or bandwidth updates must include line/type, bandwidth size, and billing posture.",
            "Unbind/release tasks must distinguish keeping the IP from releasing the paid resource.",
        ],
        "risk_gates": [
            {
                "code": "public_exposure",
                "severity": "high",
                "message": "Binding EIP creates a public entry path; verify security group source CIDRs and exposed ports first.",
            },
            {
                "code": "cost_retention",
                "severity": "medium",
                "message": "Unbound pay-per-use EIPs can still incur retention and bandwidth charges until released or adjusted.",
            },
            {
                "code": "single_binding_region",
                "severity": "medium",
                "message": "An EIP can bind only one cloud resource and must be in the same region as the target.",
            },
        ],
        "verification_checks": [
            "Read back ShowPublicip and verify status, public address, bandwidth, and binding target.",
            "For ECS access, verify ECS status, security group ingress, and protocol reachability.",
            "For release/unbind, verify the EIP is absent or no longer bound and document cost follow-up.",
        ],
        "governance_checks": [
            "Tag the EIP with owner, workload, environment, and expiry when it is temporary.",
            "Include EIP in idle audit after unbind or test workloads.",
        ],
        "official_docs": [
            {
                "title": "Huawei Cloud EIP overview and binding boundaries",
                "url": "https://support.huaweicloud.com/productdesc-eip/overview_0001.html",
            },
            {
                "title": "Huawei Cloud EIP unbind and release difference",
                "url": "https://support.huaweicloud.com/intl/zh-cn/eip_faq/faq_eip_0034.html",
            },
        ],
    },
    "EVS": {
        "task": "data-disk-readiness",
        "tenant_goals": ["上好云", "用好云", "管好云"],
        "default_operation": "CreateVolume",
        "maturity": "p0-closure",
        "summary": "Separate cloud-side volume state from guest OS filesystem and mount readiness.",
        "recommended_inputs": [
            "volume_id",
            "server_id",
            "availability_zone",
            "size",
            "volume_type",
            "device",
            "mountpoint",
            "filesystem",
            "snapshot_id",
        ],
        "target_params": ["volume_id", "snapshot_id"],
        "dependency_checks": [
            "Confirm AZ compatibility, volume status, ECS target, disk mode, and whether the volume is shared.",
            "For attach, ensure the target ECS state and attach mode meet EVS/ECS constraints.",
            "For resize/delete/detach, check snapshots, backups, mount state, and application dependency.",
        ],
        "parameter_checks": [
            "Creation requires volume type, size, AZ, and project/region context.",
            "Attach/readiness tasks should state target ECS, expected device, mountpoint, filesystem, and persistence requirement.",
            "Resize tasks must distinguish control-plane capacity from guest partition/filesystem expansion.",
        ],
        "risk_gates": [
            {
                "code": "data_loss",
                "severity": "high",
                "message": "Format, repartition, delete, detach, or MBR-to-GPT conversion can destroy or interrupt data.",
            },
            {
                "code": "guest_readiness_gap",
                "severity": "medium",
                "message": "EVS in-use only means cloud attachment; the guest OS still needs device, filesystem, mount, fstab, and write-test evidence.",
            },
        ],
        "verification_checks": [
            "Read back ShowVolume or ShowJob and verify status, size, volume type, and attachments.",
            "Inside the ECS, verify device discovery, partition/filesystem, mountpoint, fstab-by-UUID, df, and write test.",
            "For resize, verify both cloud-side size and guest partition/filesystem expansion.",
        ],
        "governance_checks": [
            "Require snapshot or backup posture before destructive storage changes.",
            "Tag data disks with owner, workload, environment, data classification, and retention expectation.",
        ],
        "official_docs": [
            {
                "title": "Huawei Cloud EVS attach non-shared disk",
                "url": "https://support.huaweicloud.com/usermanual-evs/evs_01_0036.html",
            },
            {
                "title": "Huawei Cloud EVS Linux data disk initialization",
                "url": "https://support.huaweicloud.com/usermanual-evs/evs_01_0033.html",
            },
            {
                "title": "Huawei Cloud EVS Linux resize partition and filesystem",
                "url": "https://support.huaweicloud.com/intl/zh-cn/usermanual-evs/evs_01_0109.html",
            },
        ],
    },
    "ELB": {
        "task": "web-backend-routing",
        "tenant_goals": ["上好云", "用好云", "管好云"],
        "default_operation": "CreateListener",
        "maturity": "p0-closure",
        "summary": "Treat ELB as listener, pool, member, health-monitor, backend security group, and protocol readiness.",
        "recommended_inputs": [
            "loadbalancer_id",
            "listener_id",
            "pool_id",
            "member_id",
            "backend_server_id",
            "backend_address",
            "listener_protocol",
            "listener_port",
            "backend_protocol",
            "backend_port",
            "health_check_path",
        ],
        "target_params": ["loadbalancer_id", "listener_id", "pool_id", "member_id"],
        "dependency_checks": [
            "Confirm load balancer, VPC/subnet, listener protocol/port, pool protocol, backend ECS, and backend address.",
            "Confirm backend ECS security group allows traffic from the ELB backend subnet and health check protocol/port.",
            "Check whether health monitor settings match the application protocol, port, path, and expected status code.",
        ],
        "parameter_checks": [
            "Plan listener, pool, member, and health monitor as staged resources instead of one opaque command.",
            "Member planning must specify backend address, protocol port, subnet, weight, and ECS identity when available.",
            "HTTP/HTTPS tasks should state Host/path/status expectations for protocol verification.",
        ],
        "risk_gates": [
            {
                "code": "backend_unreachable",
                "severity": "high",
                "message": "Do not declare ELB ready until member health and backend protocol probe succeed.",
            },
            {
                "code": "security_group_dependency",
                "severity": "high",
                "message": "Backend ECS security groups must allow ELB subnet health-check and service traffic.",
            },
        ],
        "verification_checks": [
            "Read back ShowLoadBalancer/ShowListener/ShowPool/ListMembers or ShowMember.",
            "Verify member operating_status is ONLINE before claiming traffic is routed.",
            "Run HTTP/TCP protocol probes through the ELB entry point after cloud-side resources are ACTIVE.",
        ],
        "governance_checks": [
            "Record owner, domain, certificate, health-check policy, backend pool, and rollback target.",
            "Include unhealthy or empty backend pools in idle/governance review.",
        ],
        "official_docs": [
            {
                "title": "Huawei Cloud ELB backend server security group configuration",
                "url": "https://support.huaweicloud.com/intl/zh-cn/usermanual-elb/elb_ug_hd_0007.html",
            },
            {
                "title": "Huawei Cloud ELB health check troubleshooting",
                "url": "https://support.huaweicloud.com/intl/zh-cn/elb_faq/zh-cn_topic_0018127975.html",
            },
            {
                "title": "Huawei Cloud ELB ShowLoadBalancerStatus API",
                "url": "https://support.huaweicloud.com/api-elb/ShowLoadBalancerStatus.html",
            },
        ],
    },
    "RDS": {
        "task": "database-readiness-and-change",
        "tenant_goals": ["上好云", "用好云", "管好云"],
        "default_operation": "UpdateConfiguration",
        "maturity": "p0-closure",
        "summary": "Treat RDS work as database availability, backup, connection, parameter, restart, and rollback planning.",
        "recommended_inputs": [
            "instance_id",
            "config_id",
            "engine",
            "version",
            "database_port",
            "vpc_id",
            "subnet_id",
            "security_group_id",
            "backup_retention_days",
            "maintenance_window",
            "rollback_plan",
        ],
        "target_params": ["instance_id", "config_id"],
        "dependency_checks": [
            "Discover instances, backups, configurations, datastores, flavors, and subnet/security-group dependencies before planning changes.",
            "Check backup policy and latest backup posture before parameter, resize, restart, or destructive database work.",
            "Confirm client network path, DNS/endpoint, port, security group, and credential handling before claiming connection readiness.",
        ],
        "parameter_checks": [
            "Parameter and specification changes must state instance ID, config/parameter target, maintenance window, restart impact, and rollback path.",
            "Database/user changes must distinguish schema/user intent from instance-level infrastructure changes.",
            "Connection checks need endpoint/DNS, port, source CIDR, SSL requirement, and least-privilege credential handling.",
        ],
        "risk_gates": [
            {
                "code": "backup_required",
                "severity": "high",
                "message": "Do not proceed with risky RDS changes until backup posture and restore boundary are reviewed.",
            },
            {
                "code": "restart_or_connection_impact",
                "severity": "high",
                "message": "Parameter, resize, reboot, security group, and endpoint changes can interrupt database connections.",
            },
        ],
        "verification_checks": [
            "Read back ListInstances plus ShowBackupPolicy, ShowConfiguration or ShowInstanceConfiguration when target IDs are known.",
            "Verify instance status, endpoint/DNS, port, backup policy, parameter status, and pending restart state.",
            "Only declare database readiness after a bounded connection probe from the intended client network succeeds.",
        ],
        "governance_checks": [
            "Record owner, workload, environment, backup retention, maintenance window, and rollback owner.",
            "Include stopped, abnormal, or weak-backup RDS instances in lifecycle governance review.",
        ],
        "official_docs": [
            {
                "title": "Huawei Cloud RDS documentation",
                "url": "https://support.huaweicloud.com/rds/index.html",
            }
        ],
    },
    "OBS": {
        "task": "bucket-policy-lifecycle-readiness",
        "tenant_goals": ["上好云", "用好云", "管好云"],
        "default_operation": "PutBucketLifecycle",
        "maturity": "p0-closure",
        "summary": "Treat OBS as an obsutil-backed bucket, policy, lifecycle, static-site, and public-access boundary.",
        "recommended_inputs": [
            "bucket",
            "endpoint",
            "policy_file",
            "lifecycle_file",
            "static_website",
            "public_access_intent",
            "owner",
            "retention_policy",
        ],
        "target_params": ["bucket"],
        "dependency_checks": [
            "Use the OBS adapter path, not ordinary OpenAPI-style hcloud OBS operations.",
            "List buckets and stat the target bucket before policy, lifecycle, or static website planning.",
            "Read existing bucket policy and lifecycle configuration before generating replacement plans.",
        ],
        "parameter_checks": [
            "Policy/lifecycle changes must identify the exact bucket and local policy/lifecycle file.",
            "Static site work must state index/error document, CDN/DNS boundary, HTTPS path, and public access intent.",
            "Public access must be explicit and reviewed; do not infer public-read from the phrase static site alone.",
        ],
        "risk_gates": [
            {
                "code": "public_bucket_exposure",
                "severity": "high",
                "message": "Bucket ACL or policy can expose object data publicly; wildcard principals/actions/resources require review.",
            },
            {
                "code": "lifecycle_data_loss",
                "severity": "high",
                "message": "Lifecycle rules can expire, transition, or delete objects; retention and recovery expectations must be reviewed.",
            },
        ],
        "verification_checks": [
            "Read back StatBucket, GetBucketPolicy, and GetBucketLifecycle after planned changes.",
            "For static sites, verify object presence, index/error documents, CDN/DNS linkage, and HTTP/HTTPS response.",
            "Summarize object/bucket evidence without dumping sensitive object listings or policy secrets into chat.",
        ],
        "governance_checks": [
            "Record owner, data classification, public access justification, lifecycle retention, and review date.",
            "Include public or wildcard policy findings in security/governance review.",
        ],
        "official_docs": [
            {
                "title": "Huawei Cloud OBS documentation",
                "url": "https://support.huaweicloud.com/obs/index.html",
            }
        ],
    },
    "DNS": {
        "task": "record-change-readiness",
        "tenant_goals": ["上好云", "用好云"],
        "default_operation": "UpdateRecordSet",
        "maturity": "p0-closure",
        "summary": "Treat DNS record changes as traffic-routing changes with TTL, conflict, rollback, and resolution checks.",
        "recommended_inputs": [
            "zone_id",
            "recordset_id",
            "record_name",
            "record_type",
            "records",
            "ttl",
            "rollback_records",
        ],
        "target_params": ["zone_id", "recordset_id"],
        "dependency_checks": [
            "Discover public zones and existing record sets before planning record changes.",
            "Check conflicting records, record type compatibility, TTL, and whether the name is controlled by CDN/ELB/OBS static-site flows.",
            "Capture current records before any update so rollback values are explicit.",
        ],
        "parameter_checks": [
            "Record changes must state zone ID, record name, type, values, TTL, and rollback values.",
            "A/AAAA/CNAME/TXT/MX records have different validation and propagation expectations.",
            "Low TTL changes should be planned before cutover when the current TTL is high.",
        ],
        "risk_gates": [
            {
                "code": "traffic_cutover",
                "severity": "high",
                "message": "DNS changes can redirect or break production traffic until caches expire.",
            },
            {
                "code": "record_conflict",
                "severity": "medium",
                "message": "Conflicting CNAME/A/AAAA or duplicate records require explicit resolution before submit.",
            },
        ],
        "verification_checks": [
            "Read back ShowPublicZone and ShowRecordSet after planned changes.",
            "Verify DNS resolution from at least one resolver and explain TTL/cache propagation delay.",
            "For application cutover, pair DNS resolution evidence with HTTP/HTTPS protocol probes.",
        ],
        "governance_checks": [
            "Record owner, domain purpose, rollback record, TTL, and change window.",
            "Include stale or orphaned records in later governance review.",
        ],
        "official_docs": [
            {
                "title": "Huawei Cloud DNS documentation",
                "url": "https://support.huaweicloud.com/dns/index.html",
            }
        ],
    },
    "SCM": {
        "task": "certificate-https-readiness",
        "tenant_goals": ["上好云", "用好云", "管好云"],
        "default_operation": "PushCertificate",
        "maturity": "p0-closure",
        "summary": "Treat certificate work as domain, validity, deployment-target, replacement, and HTTPS verification planning.",
        "recommended_inputs": [
            "certificate_id",
            "domain_name",
            "target_service",
            "target_resource_id",
            "replace_certificate_id",
            "expiry_window_days",
        ],
        "target_params": ["certificate_id"],
        "dependency_checks": [
            "List certificates and read target certificate detail before push, replacement, or delete planning.",
            "Confirm domain/SAN match, certificate status, expiration, issuer, and intended deployment target.",
            "Check CDN/ELB/other HTTPS dependency before replacing or deleting certificates.",
        ],
        "parameter_checks": [
            "Certificate deployment must state certificate ID, target service, target resource, and domain name.",
            "Replacement plans must include old/new certificate IDs and rollback target.",
            "Private key or sensitive certificate material reads remain outside the normal read path unless explicitly approved.",
        ],
        "risk_gates": [
            {
                "code": "https_outage",
                "severity": "high",
                "message": "Certificate mismatch, expiry, or failed deployment can break HTTPS traffic.",
            },
            {
                "code": "sensitive_material",
                "severity": "high",
                "message": "Certificate private key and secret material must not be read or displayed by default.",
            },
        ],
        "verification_checks": [
            "Read back ShowCertificate and verify domain, SAN, status, expiration, and deployment target.",
            "Verify HTTPS handshake and certificate chain from the public endpoint after deployment.",
            "Check CDN/ELB listener/domain references when SCM is only the certificate source.",
        ],
        "governance_checks": [
            "Record owner, domain, expiry date, renewal path, deployment targets, and rollback certificate.",
            "Create expiry review tasks for certificates inside the warning window.",
        ],
        "official_docs": [
            {
                "title": "Huawei Cloud SCM documentation",
                "url": "https://support.huaweicloud.com/scm/index.html",
            }
        ],
    },
    "CDN": {
        "task": "cdn-domain-origin-https-readiness",
        "tenant_goals": ["上好云", "用好云", "管好云"],
        "default_operation": "UpdateDomainFullConfig",
        "maturity": "p0-closure",
        "summary": "Treat CDN work as domain, origin, cache, certificate, refresh/preheat, and HTTP verification planning.",
        "recommended_inputs": [
            "domain_id",
            "domain_name",
            "origin",
            "origin_protocol",
            "certificate_id",
            "cache_rules",
            "refresh_paths",
            "rollback_origin",
        ],
        "target_params": ["domain_id"],
        "dependency_checks": [
            "List domains and show target domain detail before origin, HTTPS, cache, or deletion planning.",
            "Check origin reachability, DNS/SCM certificate dependency, cache rules, and whether OBS/ELB/ECS is the origin.",
            "Confirm KooCLI supported region resolution for CDN commands before planning execution.",
        ],
        "parameter_checks": [
            "Domain changes must state domain name/ID, origin, protocol, HTTPS/certificate intent, and rollback origin.",
            "Cache changes must identify affected paths, TTL behavior, refresh/preheat scope, and expected propagation.",
            "Origin updates must include health and direct-origin validation before traffic is routed through CDN.",
        ],
        "risk_gates": [
            {
                "code": "origin_or_cache_outage",
                "severity": "high",
                "message": "Wrong origin, protocol, certificate, or cache rules can break or stale production content.",
            },
            {
                "code": "refresh_preheat_scope",
                "severity": "medium",
                "message": "Large refresh/preheat scopes can affect quota, cost, and origin load.",
            },
        ],
        "verification_checks": [
            "Read back ShowDomainDetail and verify domain status, origin, HTTPS, and cache configuration.",
            "Probe HTTP/HTTPS through CDN and, when needed, direct origin to separate CDN and origin faults.",
            "After cache changes, verify representative URLs and record expected propagation delay.",
        ],
        "governance_checks": [
            "Record owner, domain, origin, certificate, cache policy, rollback origin, and change window.",
            "Include disabled/stale domains and risky origins in governance review.",
        ],
        "official_docs": [
            {
                "title": "Huawei Cloud CDN documentation",
                "url": "https://support.huaweicloud.com/cdn/index.html",
            }
        ],
    },
    "CES_LTS": {
        "task": "health-evidence-readiness",
        "tenant_goals": ["用好云", "管好云"],
        "default_operation": None,
        "change_planner": "none",
        "readiness_service": "CES",
        "maturity": "p0-closure",
        "summary": "Combine resource state, CES metric discovery, bounded LTS log queries, and application probes before declaring health.",
        "recommended_inputs": [
            "target_service",
            "target_id",
            "namespace",
            "metric_name",
            "dimension",
            "start_time",
            "end_time",
            "log_group_id",
            "log_stream_id",
            "keyword",
            "probe_url",
        ],
        "target_params": [],
        "dependency_checks": [
            "Discover CES metrics before choosing namespace, metric_name, dimensions, period, and time window.",
            "Discover LTS log groups/streams before querying logs, and keep time windows and keywords narrow.",
            "Pair metrics/logs with resource state and application protocol probes instead of relying on one status field.",
        ],
        "parameter_checks": [
            "Metric queries need explicit namespace, metric, dimension, period, and bounded time range.",
            "Log queries need explicit log group, stream, start/end time, keyword, and sensitivity handling.",
            "Health conclusions must separate observed facts, missing evidence, and recommended next checks.",
        ],
        "risk_gates": [
            {
                "code": "evidence_gap",
                "severity": "medium",
                "message": "Do not declare healthy, idle, or failed when only one evidence source has been checked.",
            },
            {
                "code": "sensitive_logs",
                "severity": "high",
                "message": "LTS logs may contain sensitive application data; narrow queries and summarize results.",
            },
        ],
        "verification_checks": [
            "Use CES ListMetrics to discover namespace, metric, dimension, and period before datapoint interpretation.",
            "Use LTS log group/stream/log query plans for bounded log evidence, not broad log dumps.",
            "Combine resource state, CES metrics, LTS logs, and protocol probe evidence in the final health conclusion.",
        ],
        "governance_checks": [
            "Record metric/log evidence windows, missing evidence, alarm coverage, and owner follow-up.",
            "Keep CES alarm creation planner-only and require review for notification policy changes.",
        ],
        "official_docs": [
            {
                "title": "Huawei Cloud CES documentation",
                "url": "https://support.huaweicloud.com/ces/index.html",
            },
            {
                "title": "Huawei Cloud LTS documentation",
                "url": "https://support.huaweicloud.com/lts/index.html",
            },
        ],
    },
}

SERVICE_ACCEPTANCE_EVIDENCE: dict[str, dict[str, Any]] = {
    "VPC": {
        "completion_rule": "Network changes are accepted only after rule readback and an entry-path probe from the approved source are both accounted for.",
        "claim_boundaries": [
            "A security group rule readback does not prove the application is reachable.",
            "Do not claim public readiness when the approved source CIDR or target entry path is missing.",
        ],
        "items": [
            {
                "id": "security_group_rule_readback",
                "layer": "cloud_control_plane",
                "description": "Read back the target security group and rule, including direction, protocol, ports, source CIDR, and attached workloads.",
                "required_inputs": ["security_group_id"],
                "any_of_inputs": ["security_group_rule_id", "direction"],
            },
            {
                "id": "entry_path_probe",
                "layer": "protocol_or_network",
                "description": "Verify the intended ECS, EIP, or ELB entry path from the approved source CIDR and expected protocol/port.",
                "required_inputs": ["remote_ip_prefix", "port_range_min"],
                "any_of_inputs": ["target_resource_id", "vpc_id", "subnet_id"],
            },
        ],
    },
    "EIP": {
        "completion_rule": "Public entry changes are accepted only after EIP readback, target binding evidence, and the relevant protocol path are checked.",
        "claim_boundaries": [
            "ShowPublicip success does not prove SSH, HTTP, or application reachability.",
            "Unbound EIPs may still carry cost until release or bandwidth policy is reviewed.",
        ],
        "items": [
            {
                "id": "publicip_readback",
                "layer": "cloud_control_plane",
                "description": "Read back public IP status, address, bandwidth, billing mode, and current binding target.",
                "required_inputs": ["publicip_id"],
            },
            {
                "id": "binding_target_readback",
                "layer": "cloud_control_plane",
                "description": "Verify the exact ECS port, ELB, NAT, or other target resource that should own the EIP binding.",
                "any_of_inputs": ["target_resource_id", "target_port_id"],
            },
            {
                "id": "public_protocol_probe",
                "layer": "protocol_or_network",
                "description": "Probe the expected public protocol through the EIP after ECS/ELB and security group evidence is collected.",
                "any_of_inputs": ["probe_url", "target_resource_id", "target_port_id"],
            },
        ],
    },
    "EVS": {
        "completion_rule": "Storage work is accepted only after cloud attachment and guest filesystem readiness are both evidenced.",
        "claim_boundaries": [
            "An EVS volume in-use state does not prove the guest OS can read and write it.",
            "Formatting, repartitioning, detach, delete, and resize remain data-risk actions until explicitly approved.",
        ],
        "items": [
            {
                "id": "volume_readback",
                "layer": "cloud_control_plane",
                "description": "Read back volume status, size, type, AZ, attachment target, and recent job state when applicable.",
                "required_inputs": ["volume_id"],
            },
            {
                "id": "guest_device_filesystem",
                "layer": "guest_runtime",
                "description": "Inside the ECS, collect device discovery, partition/filesystem, mountpoint, fstab-by-UUID, df, and write-test evidence.",
                "required_inputs": ["server_id", "mountpoint"],
                "any_of_inputs": ["device", "filesystem"],
            },
        ],
    },
    "ELB": {
        "completion_rule": "Load-balancing work is accepted only after ELB topology, backend health, security-group reachability, and protocol probes are covered.",
        "claim_boundaries": [
            "Listener or pool creation does not prove backend service readiness.",
            "Member ONLINE evidence should be paired with an application protocol probe before declaring user-path success.",
        ],
        "items": [
            {
                "id": "elb_topology_readback",
                "layer": "cloud_control_plane",
                "description": "Read back load balancer, listener, pool, member, and health monitor topology.",
                "required_inputs": ["loadbalancer_id"],
                "any_of_inputs": ["listener_id", "pool_id", "member_id"],
            },
            {
                "id": "backend_health",
                "layer": "service_readiness",
                "description": "Verify backend member health, backend ECS status, and security group allowance from the ELB subnet.",
                "any_of_inputs": ["member_id", "backend_server_id", "backend_address"],
            },
            {
                "id": "elb_protocol_probe",
                "layer": "protocol_or_network",
                "description": "Probe HTTP/TCP through the ELB entry point with expected host, path, port, and status behavior.",
                "any_of_inputs": ["probe_url", "listener_port", "backend_port"],
            },
        ],
    },
    "RDS": {
        "completion_rule": "Database work is accepted only after instance, backup, parameter, network, and bounded client connection evidence are covered.",
        "claim_boundaries": [
            "An available RDS instance state does not prove application connection readiness.",
            "Parameter, resize, reboot, restore, and delete actions remain high risk until backup and rollback evidence are reviewed.",
        ],
        "items": [
            {
                "id": "instance_backup_parameter_readback",
                "layer": "cloud_control_plane",
                "description": "Read back instance state, backup policy, configuration/parameter state, endpoint, and pending restart state.",
                "required_inputs": ["instance_id"],
            },
            {
                "id": "client_connection_probe",
                "layer": "application_runtime",
                "description": "Run a bounded connection probe from the intended client network with least-privilege credentials.",
                "required_inputs": ["database_port"],
                "any_of_inputs": ["vpc_id", "subnet_id", "security_group_id", "probe_source"],
            },
            {
                "id": "rollback_boundary",
                "layer": "governance",
                "description": "Record latest backup posture, maintenance window, restart impact, and rollback owner before risky changes.",
                "any_of_inputs": ["rollback_plan", "backup_retention_days", "maintenance_window"],
            },
        ],
    },
    "OBS": {
        "completion_rule": "Bucket work is accepted only after bucket readback, policy/lifecycle evidence, and user-path evidence for static sites or public access.",
        "claim_boundaries": [
            "Bucket existence does not prove object availability or safe public access.",
            "Lifecycle rules can delete data and must not be accepted without retention evidence.",
        ],
        "items": [
            {
                "id": "bucket_stat_policy_lifecycle",
                "layer": "cloud_control_plane",
                "description": "Read back bucket stat, policy, lifecycle configuration, and public-access posture through the OBS adapter.",
                "required_inputs": ["bucket"],
            },
            {
                "id": "static_site_or_object_probe",
                "layer": "protocol_or_network",
                "description": "For static sites or published objects, verify index/error documents, CDN/DNS linkage, and HTTP/HTTPS response.",
                "required_inputs": ["bucket"],
                "any_of_inputs": ["static_website", "probe_url", "domain_name"],
            },
            {
                "id": "retention_review",
                "layer": "governance",
                "description": "Record owner, data classification, lifecycle retention, and public access justification.",
                "any_of_inputs": ["retention_policy", "owner", "public_access_intent"],
            },
        ],
    },
    "DNS": {
        "completion_rule": "DNS work is accepted only after record readback, resolver evidence, and rollback values are documented.",
        "claim_boundaries": [
            "API update success does not prove global DNS propagation.",
            "Application cutover should not be accepted without protocol probes on representative URLs.",
        ],
        "items": [
            {
                "id": "recordset_readback",
                "layer": "cloud_control_plane",
                "description": "Read back zone and recordset values, type, TTL, and conflict state.",
                "required_inputs": ["zone_id", "recordset_id"],
            },
            {
                "id": "dns_resolution_probe",
                "layer": "protocol_or_network",
                "description": "Verify resolution from at least one resolver and record TTL/cache expectations.",
                "required_inputs": ["record_name"],
                "any_of_inputs": ["records", "ttl"],
            },
            {
                "id": "cutover_rollback",
                "layer": "governance",
                "description": "Record rollback records and pair application cutover with HTTP/HTTPS probes when applicable.",
                "any_of_inputs": ["rollback_records", "probe_url"],
            },
        ],
    },
    "SCM": {
        "completion_rule": "Certificate work is accepted only after certificate detail, deployment target, and public HTTPS chain evidence are covered.",
        "claim_boundaries": [
            "Certificate upload success does not prove HTTPS is served by the target entry point.",
            "Private key or secret material must not be collected as normal acceptance evidence.",
        ],
        "items": [
            {
                "id": "certificate_detail_readback",
                "layer": "cloud_control_plane",
                "description": "Read back certificate domain/SAN, status, issuer, expiration, and deployment target reference.",
                "required_inputs": ["certificate_id"],
            },
            {
                "id": "https_chain_probe",
                "layer": "protocol_or_network",
                "description": "Verify HTTPS handshake and certificate chain from the public endpoint.",
                "required_inputs": ["domain_name"],
                "any_of_inputs": ["target_service", "target_resource_id"],
            },
        ],
    },
    "CDN": {
        "completion_rule": "CDN work is accepted only after domain/origin/cache readback and representative CDN-vs-origin protocol evidence.",
        "claim_boundaries": [
            "CDN configuration success does not prove cache propagation or origin health.",
            "Refresh/preheat scope should be reviewed before broad cache operations.",
        ],
        "items": [
            {
                "id": "cdn_domain_config_readback",
                "layer": "cloud_control_plane",
                "description": "Read back domain status, origin, HTTPS, certificate, and cache configuration.",
                "required_inputs": ["domain_id"],
            },
            {
                "id": "cdn_and_origin_probe",
                "layer": "protocol_or_network",
                "description": "Probe representative URLs through CDN and, when needed, directly against the origin.",
                "required_inputs": ["domain_name"],
                "any_of_inputs": ["origin", "probe_url"],
            },
            {
                "id": "cache_change_review",
                "layer": "governance",
                "description": "Record affected paths, expected propagation delay, refresh/preheat scope, and rollback origin.",
                "any_of_inputs": ["cache_rules", "refresh_paths", "rollback_origin"],
            },
        ],
    },
    "CES_LTS": {
        "completion_rule": "Health conclusions are accepted only after resource state, metrics, logs, and user-path probes are separated into observed facts and missing evidence.",
        "claim_boundaries": [
            "A single metric, log query, or status field is not enough to declare healthy, idle, or failed.",
            "LTS evidence must stay bounded by time, stream, and keyword to avoid sensitive broad dumps.",
        ],
        "items": [
            {
                "id": "metric_window",
                "layer": "observability",
                "description": "Discover CES metric namespace/dimension/period and collect a bounded metric window.",
                "required_inputs": ["start_time", "end_time"],
                "any_of_inputs": ["namespace", "metric_name", "dimension"],
            },
            {
                "id": "bounded_log_window",
                "layer": "observability",
                "description": "Collect bounded LTS log evidence by group, stream, time window, and keyword when logs are needed.",
                "required_inputs": ["log_group_id", "log_stream_id", "start_time", "end_time"],
                "any_of_inputs": ["keyword", "target_id"],
            },
            {
                "id": "user_path_probe",
                "layer": "protocol_or_network",
                "description": "Pair resource state, metrics, and logs with a protocol or application probe where user impact matters.",
                "any_of_inputs": ["probe_url", "target_id", "target_service"],
            },
        ],
    },
}


def parse_key_values(values: list[str]) -> dict[str, str]:
    """Parse repeated KEY=VALUE inputs."""
    result: dict[str, str] = {}
    for item in values:
        if "=" not in item:
            raise ValueError(f"Expected KEY=VALUE but got: {item}")
        key, value = item.split("=", 1)
        key = key.strip().lstrip("-").replace("-", "_")
        if not key:
            raise ValueError(f"Expected non-empty key in: {item}")
        result[key] = value.strip()
    return result


def param_tokens(params: dict[str, str]) -> list[str]:
    """Return hcloud-style CLI argument tokens for planner policy scans."""
    return [f"--{key}={value}" for key, value in sorted(params.items())]


def missing_inputs(profile: dict[str, Any], params: dict[str, str]) -> list[str]:
    """Return recommended input names that were not supplied."""
    return [name for name in profile["recommended_inputs"] if name not in params]


def evidence_item_status(item: dict[str, Any], params: dict[str, str]) -> dict[str, Any]:
    """Return one acceptance evidence item with input-gap status."""
    required = list(item.get("required_inputs", []))
    any_of = list(item.get("any_of_inputs", []))
    missing_required = [name for name in required if name not in params]
    missing_any_of = any_of if any_of and not any(name in params for name in any_of) else []
    status = "ready_to_collect" if not missing_required and not missing_any_of else "missing_inputs"
    return {
        "id": item["id"],
        "layer": item["layer"],
        "description": item["description"],
        "required_inputs": required,
        "any_of_inputs": any_of,
        "missing_required_inputs": missing_required,
        "missing_any_of_inputs": missing_any_of,
        "status": status,
    }


def build_acceptance_evidence_plan(
    service: str,
    params: dict[str, str],
    readiness_plan: dict[str, Any],
    extra_evidence_plans: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return a structured service-specific acceptance evidence plan."""
    spec = SERVICE_ACCEPTANCE_EVIDENCE.get(service, {})
    items = [evidence_item_status(item, params) for item in spec.get("items", [])]
    missing_inputs_by_item = {
        item["id"]: sorted(set(item["missing_required_inputs"] + item["missing_any_of_inputs"]))
        for item in items
        if item["status"] == "missing_inputs"
    }
    readiness_checks = sum(len(entry.get("checks", [])) for entry in readiness_plan.get("services", []))
    return {
        "service": service,
        "acceptance_level": "task_level_acceptance_evidence_plan",
        "execution_boundary": "planner_only_no_live_probe",
        "completion_rule": spec.get(
            "completion_rule",
            "Accept the task only after applicable cloud, runtime, protocol, and governance evidence is collected.",
        ),
        "evidence_items": items,
        "summary": {
            "total_item_count": len(items),
            "ready_item_count": sum(1 for item in items if item["status"] == "ready_to_collect"),
            "missing_input_item_count": sum(1 for item in items if item["status"] == "missing_inputs"),
            "planned_readiness_check_count": readiness_checks,
            "extra_evidence_plan_count": len(extra_evidence_plans or {}),
        },
        "missing_inputs_by_item": missing_inputs_by_item,
        "claim_boundaries": spec.get(
            "claim_boundaries",
            ["Do not treat API success as task completion without service-specific acceptance evidence."],
        ),
    }


def readiness_targets(profile: dict[str, Any], params: dict[str, str]) -> list[str]:
    """Return target parameters relevant to service readiness checks."""
    return [f"{name}={params[name]}" for name in profile["target_params"] if name in params]


def canonical_service(value: str) -> str:
    """Return the canonical lifecycle closure service key."""
    service = value.upper().replace("-", "_")
    return SERVICE_ALIASES.get(service, service)


def change_plan_args(
    args: argparse.Namespace,
    service: str,
    operation: str,
    params: dict[str, str],
) -> SimpleNamespace:
    """Build arguments for the existing service-aware change planner."""
    return SimpleNamespace(
        service=service,
        operation=operation,
        region=args.region,
        project_id=args.project_id,
        profile=args.profile,
        json_input_file=args.json_input_file,
        arg=[*args.arg, *param_tokens(params)],
        no_dryrun=args.no_dryrun,
        allow_public_web=bool(getattr(args, "allow_public_web", False)),
        allow_unregistered=args.allow_unregistered,
    )


def readiness_args(args: argparse.Namespace, service: str, profile: dict[str, Any], params: dict[str, str]) -> SimpleNamespace:
    """Build arguments for service-level readiness planning."""
    return SimpleNamespace(
        service=[profile.get("readiness_service", service)],
        target=readiness_targets(profile, params),
        region=args.region,
        project_id=args.project_id,
        profile=args.profile,
        limit=args.limit,
        obs_endpoint=None,
        obs_config=None,
        obs_payer=None,
        execute=False,
        timeout=args.timeout,
        strict=False,
        require_all=False,
    )


def lts_plan_args(args: argparse.Namespace, params: dict[str, str]) -> SimpleNamespace:
    """Build arguments for bounded LTS read-only planning."""
    return SimpleNamespace(
        region=args.region,
        project_id=args.project_id,
        profile=args.profile,
        limit=args.limit,
        log_group_id=params.get("log_group_id"),
        log_stream_id=params.get("log_stream_id"),
        start_time=params.get("start_time"),
        end_time=params.get("end_time"),
        keyword=params.get("keyword"),
        execute=False,
        timeout=args.timeout,
    )


def build_extra_evidence_plans(service: str, args: argparse.Namespace, params: dict[str, str]) -> dict[str, Any]:
    """Return supplemental planner-only evidence plans for composite closures."""
    if service != "CES_LTS":
        return {}
    return {
        "lts_readonly_plan": hcloud_lts_readonly.build_plan(lts_plan_args(args, params)),
        "note": "CES readiness discovers metrics through the normal service readiness plan; LTS remains metadata-backed/read-only evidence planning.",
    }


def build_change_plan(
    args: argparse.Namespace,
    service: str,
    profile: dict[str, Any],
    params: dict[str, str],
) -> dict[str, Any]:
    """Build a non-executing change plan for the selected service."""
    if profile.get("change_planner") == "none":
        return {
            "success": True,
            "service": service,
            "operation": None,
            "planning_only": True,
            "change_planner": "none",
            "submit_requires_confirmation": False,
            "submit_is_not_executed_by_this_planner": True,
            "reason": "This closure profile is read-only/planner-only and has no default mutating operation.",
        }
    operation = args.operation or profile["default_operation"]
    return hcloud_service_change_plan.build_service_plan(change_plan_args(args, service, operation, params))


def service_policy_scan(
    args: argparse.Namespace,
    service: str,
    params: dict[str, str],
) -> dict[str, Any]:
    """Run local service-specific policy scans."""
    if service != "VPC":
        return {"violations": [], "scan_error": None}
    return hcloud_security_policy.check_change_inputs(
        [*args.arg, *param_tokens(params)],
        args.json_input_file,
        allow_public_web=bool(getattr(args, "allow_public_web", False)),
    )


def build_risk_section(
    args: argparse.Namespace,
    service: str,
    profile: dict[str, Any],
    params: dict[str, str],
    change_plan: dict[str, Any],
) -> dict[str, Any]:
    """Return service risk gates plus hard blockers from policy and planner output."""
    policy_scan = service_policy_scan(args, service, params)
    hard_blockers: list[dict[str, Any]] = []
    seen_blockers: set[tuple[Any, ...]] = set()

    def add_blocker(source: str, violation: dict[str, Any]) -> None:
        key = (
            violation.get("code"),
            violation.get("path"),
            violation.get("cidr_field"),
            violation.get("cidr"),
            tuple(violation.get("ports", [])),
        )
        if key in seen_blockers:
            return
        seen_blockers.add(key)
        hard_blockers.append(
            {
                "code": violation.get("code", "policy_violation"),
                "message": violation.get("message"),
                "source": source,
                "details": violation,
            }
        )

    for violation in policy_scan.get("violations", []):
        add_blocker("hcloud_security_policy.py", violation)
    for violation in change_plan.get("policy_violations", []):
        add_blocker("hcloud_service_change_plan.py", violation)

    return {
        "gates": profile["risk_gates"],
        "policy_scan": policy_scan,
        "hard_blockers": hard_blockers,
        "hard_blocked": bool(hard_blockers),
        "change_plan_risk": change_plan.get("risk", {}),
    }


def execution_summary(change_plan: dict[str, Any]) -> dict[str, Any]:
    """Return the controlled execution summary from a lower-level change plan."""
    commands = change_plan.get("commands", {})
    return {
        "planning_only": True,
        "submit_is_not_executed": True,
        "submit_requires_explicit_confirmation": True,
        "dryrun_or_plan_command": commands.get("dryrun_or_plan"),
        "submit_command": commands.get("submit"),
        "lower_level_planner_success": change_plan.get("success", False),
        "lower_level_planner": "scripts/hcloud_service_change_plan.py",
        "error_handling": [
            "Run real hcloud calls through scripts/hcloud_safe_exec.py so auth, permission, region/project, parameter, quota, not-found, timeout, and network errors are classified.",
            "Do not retry the same failing submit blindly; update the plan after each distinct failure.",
            "Record redacted run-journal evidence for approved dry-run, submit, and verification steps.",
        ],
    }


def build_stage_plan(
    args: argparse.Namespace,
    service: str,
    profile: dict[str, Any],
    params: dict[str, str],
    change_plan: dict[str, Any],
    readiness_plan: dict[str, Any],
    risk_section: dict[str, Any],
    extra_evidence_plans: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Return the six-stage lifecycle closure plan."""
    gaps = missing_inputs(profile, params)
    return [
        {
            "id": "context_dependency_discovery",
            "title": "Context and dependency discovery",
            "checks": profile["dependency_checks"],
            "readiness_plan": readiness_plan,
            "extra_evidence_plans": extra_evidence_plans or {},
        },
        {
            "id": "operation_parameter_planning",
            "title": "Operation and parameter planning",
            "operation": args.operation or profile["default_operation"],
            "recommended_inputs": profile["recommended_inputs"],
            "provided_inputs": sorted(params),
            "missing_recommended_inputs": gaps,
            "parameter_checks": profile["parameter_checks"],
            "change_plan": change_plan,
        },
        {
            "id": "risk_security_gate",
            "title": "Risk and security gate",
            **risk_section,
        },
        {
            "id": "controlled_execution_error_handling",
            "title": "Controlled execution and error handling",
            **execution_summary(change_plan),
        },
        {
            "id": "post_change_verification",
            "title": "Post-change verification",
            "checks": profile["verification_checks"],
            "readiness_targets": readiness_targets(profile, params),
            "resource_verifier": "scripts/hcloud_resource_verify.py",
            "acceptance_evidence_plan": build_acceptance_evidence_plan(
                service,
                params,
                readiness_plan,
                extra_evidence_plans,
            ),
            "evidence_rule": "Do not treat API submit success as service readiness; verify resource, binding, health, guest, or protocol state as applicable.",
        },
        {
            "id": "governance_audit",
            "title": "Governance and audit",
            "checks": profile["governance_checks"],
            "journal": "Use redacted run-journal entries for approved execution and verification evidence.",
            "tenant_goals": profile["tenant_goals"],
        },
    ]


def build_service_closure(args: argparse.Namespace, service: str, params: dict[str, str]) -> dict[str, Any]:
    """Build one service lifecycle closure plan."""
    service = canonical_service(service)
    profile = SERVICE_CLOSURE_PROFILES[service]
    change_plan = build_change_plan(args, service, profile, params)
    readiness_plan = hcloud_service_readiness.build_readiness(readiness_args(args, service, profile, params))
    risk_section = build_risk_section(args, service, profile, params, change_plan)
    extra_evidence_plans = build_extra_evidence_plans(service, args, params)
    stages = build_stage_plan(args, service, profile, params, change_plan, readiness_plan, risk_section, extra_evidence_plans)
    success = bool(change_plan.get("success")) and not risk_section["hard_blocked"]
    return {
        "service": service,
        "success": success,
        "task": args.task or profile["task"],
        "default_task": profile["task"],
        "maturity": profile["maturity"],
        "summary": profile["summary"],
        "tenant_goals": profile["tenant_goals"],
        "planning_only": True,
        "official_docs": profile["official_docs"],
        "missing_recommended_inputs": missing_inputs(profile, params),
        "hard_blocked": risk_section["hard_blocked"],
        "hard_blockers": risk_section["hard_blockers"],
        "stages": stages,
    }


def build_lifecycle_plan(args: argparse.Namespace) -> dict[str, Any]:
    """Build lifecycle closure plans for selected services."""
    params = parse_key_values(args.param)
    selected_services = [canonical_service(service) for service in (args.service or CLOSURE_SERVICES)]
    unsupported = [service for service in selected_services if service not in SERVICE_CLOSURE_PROFILES]
    if unsupported:
        return {
            "success": False,
            "mode": "plan",
            "planning_only": True,
            "error": "Unsupported lifecycle closure service.",
            "unsupported_services": unsupported,
            "supported_services": list(CLOSURE_SERVICES),
        }

    services = [build_service_closure(args, service, params) for service in selected_services]
    return {
        "success": all(item["success"] for item in services),
        "mode": "plan",
        "planning_only": True,
        "version": "0.3.2",
        "scope": "P0 lifecycle closure for core cloud onboarding, usage, and governance services",
        "service_count": len(services),
        "supported_services": list(CLOSURE_SERVICES),
        "services": services,
    }


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--service", action="append", help="Closure service. Defaults to all P0 closure services.")
    parser.add_argument("--task", help="Human task label for the closure plan.")
    parser.add_argument("--operation", help="Optional change operation to pass to the service planner.")
    parser.add_argument("--param", action="append", default=[], help="Task parameter as KEY=VALUE.")
    parser.add_argument("--region", help="Explicit cli-region for generated lower-level plans.")
    parser.add_argument("--project-id", help="Optional project_id for generated lower-level plans.")
    parser.add_argument("--profile", help="Optional cli-profile for generated lower-level plans.")
    parser.add_argument("--json-input-file", help="Optional JSON input file for the lower-level change planner.")
    parser.add_argument("--arg", action="append", default=[], help="Additional raw hcloud argument token.")
    parser.add_argument("--no-dryrun", action="store_true", help="Do not add --dryrun in lower-level plans.")
    parser.add_argument(
        "--allow-public-web",
        action="store_true",
        help=(
            "Allow exact TCP 80/443 ingress from 0.0.0.0/0 for a user-confirmed public website plan. "
            "This does not authorize submit."
        ),
    )
    parser.add_argument("--allow-unregistered", action="store_true", help="Pass through to hcloud_service_change_plan.py.")
    parser.add_argument("--limit", type=int, default=20, help="Optional read-only readiness discovery limit.")
    parser.add_argument("--timeout", type=int, default=120, help="Timeout used only if nested plans are later executed.")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")
    args = parser.parse_args()
    if args.limit < 1:
        parser.error("--limit must be greater than 0.")
    if args.timeout < 1:
        parser.error("--timeout must be greater than 0.")
    return args


def main() -> int:
    """Build and print lifecycle closure plans."""
    args = parse_args()
    try:
        result = build_lifecycle_plan(args)
    except ValueError as exc:
        result = {"success": False, "error": str(exc)}
    hcloud_common.emit_json(result, pretty=args.pretty)
    return 0 if result.get("success") else 1


if __name__ == "__main__":
    raise SystemExit(main())
