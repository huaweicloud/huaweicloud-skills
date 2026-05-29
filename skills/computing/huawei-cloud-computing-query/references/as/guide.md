# Huawei Cloud Auto Scaling (AS) Query Guide

## Scaling Groups

### list_scaling_groups.py — Query Auto Scaling Group List

Purpose: Query all scaling groups, returning scaling group ID, name, status, current/desired/min/max instance count, VPC ID, creation time, etc.
Usage: python scripts/as/list_scaling_groups.py -h

### show_scaling_group.py — Query Auto Scaling Group Details

Purpose: Query the complete details of a single scaling group, including network, security group, availability zone, load balancer listener, tags, etc.
Usage: python scripts/as/show_scaling_group.py -h

---

## Scaling Configurations

### list_scaling_configs.py — Query Auto Scaling Configuration List

Purpose: Query all scaling configurations, returning configuration ID, name, associated scaling group ID, creation time, etc.
Usage: python scripts/as/list_scaling_configs.py -h

### show_scaling_config.py — Query Auto Scaling Configuration Details

Purpose: Query the complete details of a single scaling configuration, including flavor, image, disk, keypair, public IP, security group, etc.
Usage: python scripts/as/show_scaling_config.py -h

---

## Scaling Group Instances

### list_scaling_instances.py — Query Scaling Group Instance List

Purpose: Query instances within a specified scaling group, returning instance ID, name, lifecycle state, health status, protection status, etc.
Usage: python scripts/as/list_scaling_instances.py -h

---

## Scaling Policies (v1)

### list_scaling_policies.py — Query Scaling Policy List (v1)

Purpose: Query the policy list of a specified scaling group (v1), returning policy ID, name, status, type, alarm ID, etc.
Usage: python scripts/as/list_scaling_policies.py -h

### show_scaling_policy.py — Query Scaling Policy Details (v1)

Purpose: Query details of a single policy (v1), including policy action, scheduled policy, etc.
Usage: python scripts/as/show_scaling_policy.py -h

---

## Scaling Policies (v2)

### list_scaling_v2_policies.py — Query Scaling Policy List (v2)

Purpose: Query the policy list of a specified scaling group (v2), supporting step interval alarm policies.
Usage: python scripts/as/list_scaling_v2_policies.py -h

### show_scaling_v2_policy.py — Query Scaling Policy Details (v2)

Purpose: Query details of a single policy (v2), including step interval alarm actions, metadata, etc.
Usage: python scripts/as/show_scaling_v2_policy.py -h

### list_all_scaling_v2_policies.py — Query All Scaling Policy List (v2)

Purpose: Query the policy list for all scaling groups and bandwidth (v2), supporting sorting, enterprise project filtering, etc.
Usage: python scripts/as/list_all_scaling_v2_policies.py -h

---

## Scaling Activity Logs

### list_scaling_activity_logs.py — Query Scaling Activity Log List (v1)

Purpose: Query the activity logs of a specified scaling group, returning activity ID, status, time, scaling value, description, etc.
Usage: python scripts/as/list_scaling_activity_logs.py -h

### list_scaling_activity_v2_logs.py — Query Scaling Activity Log List (v2)

Purpose: Query the activity logs of a specified scaling group (v2), supporting filtering by type and status, returning more detailed instance change information.
Usage: python scripts/as/list_scaling_activity_v2_logs.py -h

---

## Policy Execution Logs

### list_scaling_policy_execute_logs.py — Query Policy Execution Log List

Purpose: Query the execution logs of a specified policy, returning execution status, type, time, old value/desired value/limit value, etc.
Usage: python scripts/as/list_scaling_policy_execute_logs.py -h

---

## Notifications

### list_scaling_notifications.py — Query Scaling Group Notification List

Purpose: Query the SMN notification configuration of a specified scaling group, returning Topic URN, name, scenario, etc.
Usage: python scripts/as/list_scaling_notifications.py -h

---

## Lifecycle Hooks

### list_life_cycle_hooks.py — Query Lifecycle Hook List

Purpose: Query the lifecycle hooks of a specified scaling group, returning hook name, type, default result, timeout, etc.
Usage: python scripts/as/list_life_cycle_hooks.py -h

### show_life_cycle_hook.py — Query Lifecycle Hook Details

Purpose: Query details of a single lifecycle hook, including SMN notification configuration, etc.
Usage: python scripts/as/show_life_cycle_hook.py -h

### list_hook_instances.py — Query Scaling Group Hook Instance List

Purpose: Query instances in lifecycle hook waiting state, returning instance ID, hook name, status, timeout, etc.
Usage: python scripts/as/list_hook_instances.py -h

---

## Scheduled Tasks

### list_group_scheduled_tasks.py — Query Scaling Group Scheduled Task List

Purpose: Query the scheduled tasks of a specified scaling group, returning task ID, name, creation/update time, etc.
Usage: python scripts/as/list_group_scheduled_tasks.py -h

---

## Warm Pool

### list_warm_pool_instances.py — Query Warm Pool Instance List

Purpose: Query the warm pool instances of a specified scaling group, returning instance ID, name, status, etc.
Usage: python scripts/as/list_warm_pool_instances.py -h

### list_warm_pool_instances_new.py — Query Warm Pool Instance List (New)

Purpose: Query the warm pool instances of a specified scaling group (new API), returning instance ID, name, status, etc.
Usage: python scripts/as/list_warm_pool_instances_new.py -h

### show_warm_pool.py — Query Warm Pool Information

Purpose: Query the warm pool configuration of a specified scaling group, returning min/max capacity, initialization wait time, status, etc.
Usage: python scripts/as/show_warm_pool.py -h

### show_warm_pool_new.py — Query Warm Pool Information (New)

Purpose: Query the warm pool configuration of a specified scaling group (new API), returning min/max capacity, initialization wait time, status, etc.
Usage: python scripts/as/show_warm_pool_new.py -h

---

## Quotas

### show_resource_quota.py — Query AS Resource Quota

Purpose: Query the resource quota of the AS service, returning used/quota/max/min values for each resource type.
Usage: python scripts/as/show_resource_quota.py -h

### show_policy_and_instance_quota.py — Query Scaling Group Policy and Instance Quota

Purpose: Query the policy and instance quota of a specified scaling group, returning used/quota/max/min values for each type.
Usage: python scripts/as/show_policy_and_instance_quota.py -h

---

## Tags

### list_scaling_tag_infos_by_resource_id.py — Query Tags by Resource ID

Purpose: Query the tag list of a specified resource, returning user tags and system tags.
Usage: python scripts/as/list_scaling_tag_infos_by_resource_id.py -h

### list_scaling_tag_infos_by_tenant_id.py — Query Tags by Tenant ID

Purpose: Query tags for all resources under a tenant, returning tag key and value list.
Usage: python scripts/as/list_scaling_tag_infos_by_tenant_id.py -h

### list_resource_instances.py — Query Resource Instances by Tag

Purpose: Query resource instances filtered by tag, returning resource ID, name, details, and tags.
Usage: python scripts/as/list_resource_instances.py -h

---

## API Versions

### list_api_versions.py — Query AS API Version List

Purpose: Query the list of API versions supported by the AS service.
Usage: python scripts/as/list_api_versions.py -h

### show_api_version.py — Query AS API Version Details

Purpose: Query the details of a specified API version, including version ID, status, links, etc.
Usage: python scripts/as/show_api_version.py -h
