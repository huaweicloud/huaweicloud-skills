# CBR Python Script Usage Guide

---

## Vaults

### list_vault.py — List Vaults

Purpose: List CBR vaults, supports filtering by name, object type, protection type, status, policy ID, enterprise project, etc. Output fields: id, name, status, object type, protection type, capacity (GB), used (MB), creation time, availability zone. Required: --project_id; Optional: --region, --limit, --name, --offset, --cloud_type, --protect_type, --object_type, --enterprise_project_id, --id, --policy_id, --status, --resource_ids.
Usage: python scripts/cbr/list_vault.py -h

---

### show_vault.py — Show Specified Vault Details

Purpose: Show CBR vault details, including basic info (id, name, description, project ID, availability zone, auto-bind, auto-expand, SMN notification, threshold, etc.), billing info (billing mode, cloud type, consistency level, object type, protection type, capacity, used, allocated, status, spec code, etc.), binding rules, bound resource list (id, name, type, protection status, size, backup size, backup count, excluded/included volumes), tag list. Required: --project_id, --vault_id; Optional: --region.
Usage: python scripts/cbr/show_vault.py -h

---

### list_external_vault.py — List Vaults in Other Regions

Purpose: List CBR external vaults in other regions, supports filtering by protection type, region ID, resource type, cloud type, vault ID. Output fields: id, name, status, object type, protection type, capacity (GB), used (MB), creation time, availability zone. Required: --project_id, --external_project_id; Optional: --region, --limit, --offset, --protect_type, --region_id, --objcet_type, --cloud_type, --vault_id.
Usage: python scripts/cbr/list_external_vault.py -h

---

### show_summary.py — Vault Capacity Summary

Purpose: Show CBR vault capacity summary, including total capacity (GB) and used capacity (GB). Required: --project_id; Optional: --region.
Usage: python scripts/cbr/show_summary.py -h

---

## Checkpoints

### show_checkpoint.py — Show Backup Checkpoint Details

Purpose: Show specified backup checkpoint details, including checkpoint id, status, project ID, creation time, extended info (name, description, retention duration), associated vault info (id, name, resource list with protection status/resource size/backup size/backup count, skipped resource list with reason). Required: --project_id, --checkpoint_id; Optional: --region.
Usage: python scripts/cbr/show_checkpoint.py -h

---

## Backups

### list_backups.py — List All Backups

Purpose: List CBR backups, supports filtering by checkpoint ID, backup type, name, resource ID/name/type/availability zone, status, vault ID, enterprise project, time range, etc. Output fields: id, name, status, resource type, resource name, resource size (GB), vault ID, backup type, creation time, incremental. Required: --project_id; Optional: --region, --checkpoint_id, --dec, --end_time, --image_type, --limit, --marker, --name, --offset, --resource_az, --resource_id, --resource_name, --resource_type, --sort, --start_time, --status, --vault_id, --enterprise_project_id, --own_type, --member_status, --parent_id, --used_percent, --show_replication, --incremental.
Usage: python scripts/cbr/list_backups.py -h

---

### show_backup.py — Show Specified Backup Details

Purpose: Show CBR backup details, including id, name, description, status, resource ID, resource name, resource type, resource size, vault ID, backup type, incremental, creation time, expiration time, protection time, checkpoint ID, enterprise project ID, provider ID. Required: --project_id, --backup_id; Optional: --region.
Usage: python scripts/cbr/show_backup.py -h

---

### show_metadata.py — Show Backup Metadata

Purpose: Show CBR backup metadata, including backup ID, backups, flavor, floatingips, interface, ports, server, volumes. Required: --project_id, --backup_id; Optional: --region.
Usage: python scripts/cbr/show_metadata.py -h

---

## Policies

### list_policies.py — List Policies

Purpose: List CBR policies, supports filtering by policy type (backup/replication) and vault ID. Output fields: id, name, enabled, policy type, associated vault count. Required: --project_id; Optional: --region, --operation_type, --vault_id.
Usage: python scripts/cbr/list_policies.py -h

---

### show_policy.py — Show Specified Policy Details

Purpose: Show CBR policy details, including id, name, enabled, operation type (backup/replication), policy type. Required: --project_id, --policy_id; Optional: --region.
Usage: python scripts/cbr/show_policy.py -h

---

## Organization Policies

### list_organization_policies.py — List Organization Policies

Purpose: List CBR organization policies. Output fields: id, name, policy type, enabled, status. Required: --project_id, --operation_type (backup/replication); Optional: --region, --limit, --offset.
Usage: python scripts/cbr/list_organization_policies.py -h

---

### list_organization_policy_detail.py — List Organization Policy Deployment Status

Purpose: List CBR organization policy deployment status. Output fields: policy ID, domain ID, project ID, status. Required: --project_id, --organization_policy_id; Optional: --region.
Usage: python scripts/cbr/list_organization_policy_detail.py -h

---

### show_organization_policy.py — Show Specified Organization Policy Details

Purpose: Show CBR organization policy details, including id, name, description, operation type, domain ID, domain name, enabled, status, scope. Required: --project_id, --organization_policy_id; Optional: --region.
Usage: python scripts/cbr/show_organization_policy.py -h

---

## Tasks

### list_op_logs.py — List Tasks

Purpose: List CBR tasks, supports filtering by task type, status, time range, vault ID/name, resource ID/name, enterprise project, etc. Output fields: id, task type, status, backup provider ID, vault ID, vault name, creation time. Required: --project_id; Optional: --region, --end_time, --limit, --offset, --operation_type, --provider_id, --resource_id, --resource_name, --start_time, --status, --vault_id, --vault_name, --enterprise_project_id.
Usage: python scripts/cbr/list_op_logs.py -h

---

### show_op_log.py — Show Single Task Details

Purpose: Show CBR task details, including id, task type, status, provider ID, vault ID, vault name, project ID, policy ID, checkpoint ID, creation time, start time, end time, update time. Required: --project_id, --operation_log_id; Optional: --region.
Usage: python scripts/cbr/show_op_log.py -h

---

## Protectables

### list_protectable.py — List Protectable Resources

Purpose: List CBR protectable resources, supports filtering by name, status, resource ID, cloud server ID. Output fields: id, name, type, size (GB), status. Required: --project_id, --protectable_type (e.g., OS::Nova::Server, OS::Cinder::Volume, OS::Sfs::Turbo, OS::Workspace::DesktopV2); Optional: --region, --limit, --marker, --name, --offset, --status, --id, --server_id.
Usage: python scripts/cbr/list_protectable.py -h

---

### show_protectable.py — Show Specified Protectable Resource Details

Purpose: Show CBR specified protectable resource details, including id, name, type, size, status. Required: --project_id, --protectable_type, --instance_id; Optional: --region.
Usage: python scripts/cbr/show_protectable.py -h

---

### check_agent.py — Check Agent Status

Purpose: Check CBR resource client agent status, supports batch query. Output fields: resource ID, installed, version, status code, message. Required: --project_id, --resource_ids (comma-separated), --resource_types (comma-separated, one-to-one with resource_ids); Optional: --region, --resource_names.
Usage: python scripts/cbr/check_agent.py -h

---

### show_replication_capabilities.py — Show Replication Capabilities

Purpose: Show CBR cross-region replication capabilities, output includes each region name and its supported replication target regions. Required: --project_id; Optional: --region.
Usage: python scripts/cbr/show_replication_capabilities.py -h

---

## File Backup Agents

### list_agent.py — List Agents

Purpose: List CBR file backup agents, supports filtering by status and agent ID. Output fields: agent_id, version, type, hostname, host IP, OS, status, last activation time. Required: --project_id; Optional: --region, --limit, --offset, --status, --agent_id.
Usage: python scripts/cbr/list_agent.py -h

---

### show_agent.py — Show Specified Agent Details

Purpose: Show CBR file backup agent details, including agent_id, version, type, hostname, host nickname, host IP, OS, status, last activation time, creation time, update time, backup path list (path ID, directory path, status, exclude paths). Required: --project_id, --agent_id; Optional: --region.
Usage: python scripts/cbr/show_agent.py -h

---

## Feature Query

### list_features.py — List Supported Features

Purpose: List CBR service supported features, returns complete feature information. Required: --project_id; Optional: --region, --limit, --offset.
Usage: python scripts/cbr/list_features.py -h

---

### show_feature.py — Show Specified Feature Details

Purpose: Show CBR specified feature details, returns complete feature information. Required: --project_id, --feature_key; Optional: --region, --limit, --offset.
Usage: python scripts/cbr/show_feature.py -h

---

## Backup Sharing

### show_members_detail.py — List Backup Members

Purpose: List CBR backup sharing members, supports filtering by target project ID, image ID, status, vault ID, etc. Output fields: member ID, status, backup ID, target project ID, vault ID, creation time. Required: --project_id, --backup_id; Optional: --region, --dest_project_id, --image_id, --status, --vault_id, --limit, --marker, --offset, --sort.
Usage: python scripts/cbr/show_members_detail.py -h

---

### show_member_detail.py — Show Backup Member Details

Purpose: Show CBR backup sharing member details, including id, status, backup ID, image ID, target project ID, vault ID, creation time, update time. Required: --project_id, --backup_id, --member_id; Optional: --region.
Usage: python scripts/cbr/show_member_detail.py -h

---

## Projects and Domains

### list_projects.py — List Tenant Projects

Purpose: List CBR tenant projects. Output fields: project ID, name, domain ID, enabled. Optional: --project_id, --region.
Usage: python scripts/cbr/list_projects.py -h

---

### show_domain.py — Show Tenant Information

Purpose: Show CBR domain information, including project name, project ID, domain ID, domain name. Required: --source_project_id; Optional: --project_id, --region.
Usage: python scripts/cbr/show_domain.py -h

---

### list_domain_projects.py — List Domain Projects

Purpose: List CBR projects under a domain. Output fields: project ID, project name. Required: --domain_name; Optional: --project_id, --region.
Usage: python scripts/cbr/list_domain_projects.py -h

---

### show_migrate_status.py — Show Migration Status

Purpose: Show CBR migration status, including overall status and per-project migration status list. Optional: --project_id, --region, --all_regions.
Usage: python scripts/cbr/show_migrate_status.py -h

---

## Metering

### show_storage_usage.py — Show Storage Usage Statistics

Purpose: Show CBR storage usage statistics, including resource count and per-resource resource ID, resource name, resource type, backup count, backup size (GB), multi-AZ backup size. Required: --project_id; Optional: --region, --limit, --offset, --resource_id, --resource_type.
Usage: python scripts/cbr/show_storage_usage.py -h

---

## Tags

### show_vault_tag.py — Show Vault Resource Tags

Purpose: Show CBR tags for a specified vault, including user tags (key/value) and system tags (key/value). Required: --project_id, --vault_id; Optional: --region.
Usage: python scripts/cbr/show_vault_tag.py -h

---

### show_vault_project_tag.py — Show Vault Project Tags

Purpose: Show CBR tags for all vaults in a project. Required: --project_id; Optional: --region.
Usage: python scripts/cbr/show_vault_project_tag.py -h

---

### show_vault_resource_instances.py — Query Vault Resource Instances by Tag

Purpose: Query CBR vault resource instances by tag filtering, supports AND/OR/exclude tag conditions, field matching, filtering by cloud type/object type, supports filter and count operations. Output: total count, resource ID, resource name, vault info (id, name, status, object type, protection type, capacity, used). Required: --project_id; Optional: --region, --action, --limit, --offset, --tags, --tags_any, --not_tags, --not_tags_any, --without_any_tag, --cloud_type, --object_type, --matches, --render_offset.
Usage: python scripts/cbr/show_vault_resource_instances.py -h
