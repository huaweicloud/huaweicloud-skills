# ELB Python Script Usage Guide

---

## List Query APIs

### list_load_balancers.py — Query Load Balancer List

Purpose: Query the ELB load balancer list, including name, ID, vip_address, provisioning_status, operating_status, VPC ID.
Usage: python scripts/elb/list_load_balancers.py -h

---

### list_listeners.py — Query Listener List

Purpose: Query the ELB listener list, including name, ID, protocol, protocol_port, loadbalancer_id, default_pool_id, admin state.
Usage: python scripts/elb/list_listeners.py -h

---

### list_pools.py — Query Backend Server Group List

Purpose: Query the ELB backend server group list, including name, ID, protocol, lb_algorithm, healthmonitor_id, VPC ID.
Usage: python scripts/elb/list_pools.py -h

---

### list_members.py — Query Backend Server List

Purpose: Query the ELB backend server list, including name, ID, address, protocol_port, weight, operating_status, admin state.
Usage: python scripts/elb/list_members.py -h

---

### list_health_monitors.py — Query Health Check List

Purpose: Query the ELB health check list, including name, ID, type, delay, timeout, max_retries, admin state.
Usage: python scripts/elb/list_health_monitors.py -h

---

### list_certificates.py — Query Certificate List

Purpose: Query the ELB certificate list, including name, ID, type, domain, expiration time, admin state.
Usage: python scripts/elb/list_certificates.py -h

---

### list_l7_policies.py — Query L7 Policy List

Purpose: Query the ELB L7 policy list, including name, ID, action, position, priority, listener_id, provisioning_status.
Usage: python scripts/elb/list_l7_policies.py -h

---

### list_l7_rules.py — Query L7 Rule List

Purpose: Query the ELB L7 rule list, including ID, type, compare_type, value, key, admin state, provisioning_status.
Usage: python scripts/elb/list_l7_rules.py -h

---

### list_flavors.py — Query Flavor List

Purpose: Query the ELB flavor list, including ID, name, type, shared, flavor_sold_out.
Usage: python scripts/elb/list_flavors.py -h

---

### list_logtanks.py — Query Cloud Log List

Purpose: Query the ELB cloud log list, including ID, loadbalancer_id, log group ID, log topic ID.
Usage: python scripts/elb/list_logtanks.py -h

---

### list_security_policies.py — Query Security Policy List

Purpose: Query the ELB security policy list, including ID, name, description, protocols, ciphers.
Usage: python scripts/elb/list_security_policies.py -h

---

### list_ip_groups.py — Query IP Address Group List

Purpose: Query the ELB IP address group list, including ID, name, description, project ID.
Usage: python scripts/elb/list_ip_groups.py -h

---

### list_jobs.py — Query Job List

Purpose: Query the ELB job list, including job ID, job type, status, resource ID, begin_time, end time.
Usage: python scripts/elb/list_jobs.py -h

---

### list_master_slave_pools.py — Query Master-Backup Backend Server Group List

Purpose: Query the ELB master-backup backend server group list, including ID, name, protocol, lb_algorithm, VPC ID, type.
Usage: python scripts/elb/list_master_slave_pools.py -h

---

### list_all_l7_rules.py — Query All L7 Rule List

Purpose: Query the ELB all L7 rule list, including ID, type, compare_type, value, key, admin state, provisioning_status.
Usage: python scripts/elb/list_all_l7_rules.py -h

---

### list_all_members.py — Query All Backend Server List

Purpose: Query the ELB all backend server list, including ID, name, address, protocol_port, weight, pool ID, operating_status.
Usage: python scripts/elb/list_all_members.py -h

---

### list_availability_zones.py — Query Availability Zone List

Purpose: Query the ELB availability zone list, including code, state, protocol, common border group, category.
Usage: python scripts/elb/list_availability_zones.py -h

---

### list_system_security_policies.py — Query System Security Policy List

Purpose: Query the ELB system security policy list, including name, protocols, ciphers, project ID.
Usage: python scripts/elb/list_system_security_policies.py -h

---

### list_loadbalancer_tags.py — Query Load Balancer Tags

Purpose: Query the ELB load balancer tag list, including key, values.
Usage: python scripts/elb/list_loadbalancer_tags.py -h

---

### list_listener_tags.py — Query Listener Tags

Purpose: Query the ELB listener tag list, including key, values.
Usage: python scripts/elb/list_listener_tags.py -h

---

### list_api_versions.py — Query API Version List

Purpose: Query the ELB API version list, including ID, status.
Usage: python scripts/elb/list_api_versions.py -h

---

### list_domain_i_ps.py — Query Domain IP List

Purpose: Query the ELB domain IP list, including ID, IP address, type, domain name, enabled.
Usage: python scripts/elb/list_domain_i_ps.py -h

---

### list_feature_configs.py — Query Feature Configuration List

Purpose: Query the ELB feature configuration list, including ID, feature, type, value, enabled, description.
Usage: python scripts/elb/list_feature_configs.py -h

---

### list_quota_details.py — Query Quota Detail List

Purpose: Query the ELB quota detail list, including quota_key, quota_limit, used, unit.
Usage: python scripts/elb/list_quota_details.py -h

---

### list_recycle_bin_load_balancers.py — Query Recycle Bin Load Balancer List

Purpose: Query the ELB recycle bin load balancer list, including ID, name, vip_address, provisioning_status, operating_status, VPC ID.
Usage: python scripts/elb/list_recycle_bin_load_balancers.py -h

---

### list_loadbalancer_feature.py — Query Load Balancer Feature List

Purpose: Query the ELB load balancer feature list, including feature, type, value.
Usage: python scripts/elb/list_loadbalancer_feature.py -h

### show_load_balancer.py — Query Load Balancer Details

Purpose: Query ELB load balancer details, including ID, name, description, vip_address, provisioning_status, operating_status, VPC ID, admin state, guaranteed, created at, updated at.
Usage: python scripts/elb/show_load_balancer.py -h

---

### show_listener.py — Query Listener Details

Purpose: Query ELB listener details, including ID, name, protocol, protocol_port, loadbalancer_id, default_pool_id, admin state, connection_limit, created at, updated at.
Usage: python scripts/elb/show_listener.py -h

---

### show_pool.py — Query Backend Server Group Details

Purpose: Query ELB backend server group details, including ID, name, protocol, lb_algorithm, healthmonitor_id, VPC ID, admin state, description, type, created at, updated at.
Usage: python scripts/elb/show_pool.py -h

---

### show_member.py — Query Backend Server Details

Purpose: Query ELB backend server details, including ID, name, address, protocol_port, weight, admin state, operating_status, subnet_cidr_id, IP version.
Usage: python scripts/elb/show_member.py -h

---

### show_health_monitor.py — Query Health Check Details

Purpose: Query ELB health check details, including ID, name, type, delay, timeout, max_retries, max_retries_down, admin state, monitor_port, domain name, url_path, http_method, expected_codes.
Usage: python scripts/elb/show_health_monitor.py -h

---

### show_certificate.py — Query Certificate Details

Purpose: Query ELB certificate details, including ID, name, type, domain, description, admin state, expiration time, common_name, fingerprint, source, created at, updated at.
Usage: python scripts/elb/show_certificate.py -h

---

### show_l7_policy.py — Query L7 Policy Details

Purpose: Query ELB forwarding policy details, including ID, name, action, position, priority, listener_id, redirect_pool_id, redirect_listener_id, redirect_url, provisioning_status, admin state, description.
Usage: python scripts/elb/show_l7_policy.py -h

---

### show_l7_rule.py — Query L7 Rule Details

Purpose: Query ELB forwarding rule details, including ID, type, compare_type, value, key, admin state, provisioning_status, invert.
Usage: python scripts/elb/show_l7_rule.py -h

---

### show_flavor.py — Query Flavor Details

Purpose: Query ELB flavor details, including ID, name, type, shared, flavor_sold_out, common border group, category.
Usage: python scripts/elb/show_flavor.py -h

---

### show_logtank.py — Query Cloud Log Details

Purpose: Query ELB cloud log details, including ID, loadbalancer_id, log group ID, log topic ID, project ID.
Usage: python scripts/elb/show_logtank.py -h

---

### show_security_policy.py — Query Security Policy Details

Purpose: Query ELB security policy details, including ID, name, description, protocols, ciphers, enterprise project ID, created at, updated at.
Usage: python scripts/elb/show_security_policy.py -h

---

### show_job.py — Query Job Details

Purpose: Query ELB job details, including job ID, job type, status, resource ID, error code, error message, begin_time, end time.
Usage: python scripts/elb/show_job.py -h

---

### show_master_slave_pool.py — Query Master-Backup Backend Server Group Details

Purpose: Query ELB master-backup backend server group details, including ID, name, protocol, lb_algorithm, VPC ID, type, description, IP version, enterprise project ID.
Usage: python scripts/elb/show_master_slave_pool.py -h

---

### show_load_balancer_status.py — Query Load Balancer Status Tree

Purpose: Query the ELB load balancer status tree.
Usage: python scripts/elb/show_load_balancer_status.py -h

---

### show_load_balancer_topology.py — Query Load Balancer Topology

Purpose: Query the ELB load balancer topology.
Usage: python scripts/elb/show_load_balancer_topology.py -h

---

### show_load_balancer_ports.py — Query Load Balancer Port List

Purpose: Query the ELB load balancer port list, including port ID, IP address, ipv6_address, type, subnet ID.
Usage: python scripts/elb/show_load_balancer_ports.py -h

---

### show_member_health_check_job.py — Query Member Health Check Job

Purpose: Query ELB member health check job details, including job ID, status, listener_id, member_id, check_item_total_num, check_item_finished_num, created at, updated at.
Usage: python scripts/elb/show_member_health_check_job.py -h

---

### show_ip_group.py — Query IP Address Group Details

Purpose: Query ELB IP address group details, including ID, name, description, project ID, enterprise project ID, created at, updated at.
Usage: python scripts/elb/show_ip_group.py -h

---

### show_ip_group_related_listeners.py — Query IP Address Group Related Listeners

Purpose: Query the list of listeners associated with an ELB IP address group, including ID.
Usage: python scripts/elb/show_ip_group_related_listeners.py -h

---

### show_listener_tags.py — Query Listener Tags

Purpose: Query the ELB listener tag list, including key, value.
Usage: python scripts/elb/show_listener_tags.py -h

---

### show_loadbalancer_tags.py — Query Load Balancer Tags

Purpose: Query the ELB load balancer tag list, including key, value.
Usage: python scripts/elb/show_loadbalancer_tags.py -h

---

### show_quota.py — Query Quota

Purpose: Query ELB quota, including project ID, loadbalancer, listener, pool, member, healthmonitor, l7policy, certificate, ipgroup, security_policy.
Usage: python scripts/elb/show_quota.py -h

---

### show_recycle_bin.py — Query Recycle Bin Configuration

Purpose: Query ELB recycle bin configuration, including project ID, enable, policy.
Usage: python scripts/elb/show_recycle_bin.py -h

---

### show_certificate_private_key_echo.py — Query Certificate Private Key Echo Switch

Purpose: Query the ELB certificate private key echo switch.
Usage: python scripts/elb/show_certificate_private_key_echo.py -h

### count_preoccupy_ip_num.py — Calculate Pre-occupied IP Count

Purpose: Calculate the number of pre-occupied IPs for LB.
Usage: python scripts/elb/count_preoccupy_ip_num.py -h
