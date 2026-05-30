# DNS Python Script Usage Guide

---

## Public Zones

### list_public_zones.py — Query Public Zone List

Purpose: Query the public zone list, including ID, name, status, zone type, TTL, recordset count, enterprise project ID, created at. Supports filtering by name, ID, status, tags, enterprise project, etc. Supports fuzzy/exact search and sorting.
Usage: python scripts/dns/list_public_zones.py -h

---

### show_public_zone.py — Query Public Zone Details

Purpose: Query public zone details, including ID, name, description, email, zone type, TTL, serial, status, recordset count, pool_id, project ID, enterprise project ID, masters, etc.
Usage: python scripts/dns/show_public_zone.py -h

---

### show_public_zone_name_server.py — Query Public Zone Name Servers

Purpose: Query the name servers of a public zone, including hostname, priority.
Usage: python scripts/dns/show_public_zone_name_server.py -h

---

### list_public_zone_lines.py — Query Public Zone Line List

Purpose: Query the line list of a public zone, including line ID, name, IP segment, created at, updated at.
Usage: python scripts/dns/list_public_zone_lines.py -h

---

## Private Zones

### list_private_zones.py — Query Private Zone List

Purpose: Query the private zone list, including ID, name, status, zone type, TTL, recordset count, enterprise project ID, created at. Supports filtering by name, ID, status, tags, enterprise project, associated VPC, etc. Supports fuzzy/exact search and sorting.
Usage: python scripts/dns/list_private_zones.py -h

---

### show_private_zone.py — Query Private Zone Details

Purpose: Query private zone details, including ID, name, description, email, zone type, TTL, serial, status, recordset count, pool_id, project ID, enterprise project ID, proxy_pattern, masters, associated VPC routing information, etc.
Usage: python scripts/dns/show_private_zone.py -h

---

### show_private_zone_name_server.py — Query Private Zone Name Servers

Purpose: Query the name servers of a private zone, including hostname, priority, address.
Usage: python scripts/dns/show_private_zone_name_server.py -h

---

## Record Sets

### list_record_sets.py — Query Tenant Record Set List

Purpose: Query the tenant record set list, including ID, name, type, status, TTL, zone ID, zone name. Supports filtering by zone type, name, ID, type, status, tags, etc. Supports fuzzy/exact search and sorting.
Usage: python scripts/dns/list_record_sets.py -h

---

### list_record_sets_by_zone.py — Query Record Set List Under Zone

Purpose: Query the record set list under a specified zone, including ID, name, type, status, TTL, records. Supports filtering by name, ID, type, status, tags, etc. Supports fuzzy/exact search and sorting.
Usage: python scripts/dns/list_record_sets_by_zone.py -h

---

### list_record_sets_with_line.py — Query Tenant Record Set List (With Line Support)

Purpose: Query the tenant record set list (with line support), including ID, name, type, status, TTL, zone ID, zone name, line, weight. Supports filtering by zone type, zone ID, line ID, name, type, status, tags, health check ID, etc.
Usage: python scripts/dns/list_record_sets_with_line.py -h

---

### show_record_set.py — Query Record Set Details

Purpose: Query record set details, including ID, name, description, zone ID, zone name, type, TTL, status, default, project ID, bundle, records, etc.
Usage: python scripts/dns/show_record_set.py -h

---

### show_record_set_by_zone.py — Query Record Set Details Under Zone

Purpose: Query record set details under a specified zone, including ID, name, type, status, TTL, records. Supports filtering by line ID, name, type, status, tags, etc.
Usage: python scripts/dns/show_record_set_by_zone.py -h

---

### show_record_set_with_line.py — Query Record Set Details (With Line Support)

Purpose: Query record set details (with line support), including ID, name, description, zone ID, zone name, type, TTL, status, default, project ID, line, weight, health check ID, bundle, records, alias_target, etc.
Usage: python scripts/dns/show_record_set_with_line.py -h

---

## Reverse Resolution (PTR)

### list_ptr_records.py — Query PTR Record List

Purpose: Query the reverse resolution record list for elastic public IPs, including ID, IP address, PTR domain, status, TTL. Supports filtering by enterprise project ID, tags, status, etc.
Usage: python scripts/dns/list_ptr_records.py -h

---

### list_ptrs.py — Query PTR Record List

Purpose: Query the reverse resolution record list for elastic public IPs, including ID, IP address, PTR domain, status, TTL. Supports filtering by enterprise project ID, tags, status, resource type, etc.
Usage: python scripts/dns/list_ptrs.py -h

---

### show_ptr.py — Query PTR Record Details

Purpose: Query reverse resolution record details for an elastic public IP, including ID, PTR domain, description, TTL, status, enterprise project ID, public IP information (ID, address, type).
Usage: python scripts/dns/show_ptr.py -h

---

### show_ptr_record_set.py — Query Reverse Resolution Record for Elastic Public IP

Purpose: Query the reverse resolution record for a specified elastic public IP, including ID, PTR domain, description, TTL, IP address, status, action, enterprise project ID.
Usage: python scripts/dns/show_ptr_record_set.py -h

---

## Line Management

### list_line_groups.py — Query Line Group List

Purpose: Query the line group list, including line group ID, name, status, description, created at, updated at. Supports filtering by line group ID, name, etc.
Usage: python scripts/dns/list_line_groups.py -h

---

### show_line_group.py — Query Line Group Details

Purpose: Query line group details, including line group ID, name, status, description, included line list, created at, updated at.
Usage: python scripts/dns/show_line_group.py -h

---

### list_custom_line.py — Query Custom Line List

Purpose: Query the custom line list, including line ID, name, status, created at, updated at. Supports filtering by line ID, name, status, IP address, etc.
Usage: python scripts/dns/list_custom_line.py -h

---

### list_system_lines.py — Query System Line List

Purpose: Query the system line list, including line ID, name, created at, updated at. Supports filtering by language identifier.
Usage: python scripts/dns/list_system_lines.py -h

---

## Endpoints

### list_endpoints.py — Query Endpoint List

Purpose: Query the endpoint list, including ID, name, direction (inbound/outbound), status, created at, updated at. Supports filtering by VPC ID, name, etc.
Usage: python scripts/dns/list_endpoints.py -h

---

### show_endpoint.py — Query Endpoint Details

Purpose: Query endpoint details, including ID, name, direction, status, created at, updated at, IP address list.
Usage: python scripts/dns/show_endpoint.py -h

---

### list_endpoint_vpcs.py — Query Endpoint VPC List

Purpose: Query the endpoint VPC list, including VPC ID, VPC name, region. Supports filtering by VPC ID.
Usage: python scripts/dns/list_endpoint_vpcs.py -h

---

### list_endpoint_ipaddresses.py — Query Endpoint IP Address List

Purpose: Query the IP address list of a specified endpoint, including ID, IP address, status, created at, updated at.
Usage: python scripts/dns/list_endpoint_ipaddresses.py -h

---

## Resolver Forwarding Rules

### list_resolver_rules.py — Query Resolver Rule List

Purpose: Query the resolver forwarding rule list, including ID, name, domain, endpoint ID, status, created at, updated at. Supports filtering by domain, name, endpoint ID, forwarding rule ID, etc.
Usage: python scripts/dns/list_resolver_rules.py -h

---

### show_resolver_rule.py — Query Resolver Rule Details

Purpose: Query resolver forwarding rule details, including ID, name, domain, endpoint ID, status, created at, updated at, IP address list.
Usage: python scripts/dns/show_resolver_rule.py -h

---

## Resolver Access Logs

### list_resolver_query_log_configs.py — Query Resolver Query Log Config List

Purpose: Query the resolver query log configuration list, including ID, LTS log group ID, LTS log topic ID, associated VPC ID list. Supports filtering by VPC ID.
Usage: python scripts/dns/list_resolver_query_log_configs.py -h

---

### show_resolver_query_log_config.py — Query Resolver Query Log Config Details

Purpose: Query resolver query log configuration details, including ID, LTS log group ID, LTS log topic ID, associated VPC ID list.
Usage: python scripts/dns/show_resolver_query_log_config.py -h

---

## Name Servers

### list_name_servers.py — Query Name Server List

Purpose: Query the name server list, including zone type, region, name server records (hostname, priority, address). Supports filtering by zone type, region.
Usage: python scripts/dns/list_name_servers.py -h

---

### show_zone_name_server.py — Query DNS Server Addresses for Public Zone

Purpose: Query DNS server addresses for a public zone, including zone name, whether all Huawei Cloud DNS, whether includes Huawei Cloud DNS, actual DNS server list, expected DNS server list.
Usage: python scripts/dns/show_zone_name_server.py -h

---

## Tags

### list_tags.py — Query All Tag Sets for Specified Instance Type

Purpose: Query all tag sets for a specified instance type, including tag key, values list. resource_type supports: DNS-public_zone, DNS-private_zone, DNS-public_recordset, DNS-private_recordset, DNS-ptr_record.
Usage: python scripts/dns/list_tags.py -h

---

### show_resource_tag.py — Query Tags for Specified Instance

Purpose: Query tags for a specified instance, including tag key, value. resource_type supports: DNS-public_zone, DNS-private_zone, DNS-public_recordset, DNS-private_recordset, DNS-ptr_record.
Usage: python scripts/dns/show_resource_tag.py -h

---

## DNSSEC

### show_dnssec_config.py — Query DNSSEC Configuration

Purpose: Query DNSSEC configuration, including zone name, key_tag, flag, digest algorithm, digest type, digest, signature, signature type, KSK public key, DS record, status, created at, updated at.
Usage: python scripts/dns/show_dnssec_config.py -h

---

## Quotas and Diagnostics

### show_domain_quota.py — Query Tenant Quota

Purpose: Query tenant quota, including quota item, quota limit, used count, unit.
Usage: python scripts/dns/show_domain_quota.py -h

---

### show_domain_detection.py — Query Domain Diagnosis for Public Zone

Purpose: Query domain diagnosis for a public zone, including zone name, type, status. Supports filtering by recordset type (MX/CNAME/TXT) and zone name.
Usage: python scripts/dns/show_domain_detection.py -h

---

## Batch Operations

### show_batch_operation_task.py — Query Batch Operation Task

Purpose: Query batch operation task, including task ID, type, status, created at, success count, failure count, failure item list.
Usage: python scripts/dns/show_batch_operation_task.py -h

---

### show_batch_create_record_sets_task.py — Query Batch Create Record Sets Task

Purpose: Query batch create record sets task, including task ID, status, created at, updated at, total count, success count, failure count, failure item list.
Usage: python scripts/dns/show_batch_create_record_sets_task.py -h

---

## Domain Authorization and Retrieval

### show_authorize_txt_record.py — Query Public Subdomain Authorization

Purpose: Query public subdomain authorization, including ID, zone name, status, subdomain name, created at, updated at, TXT record (host, value).
Usage: python scripts/dns/show_authorize_txt_record.py -h

---

### show_retrieval.py — Query Public Domain Retrieval

Purpose: Query public domain retrieval, including ID, zone name, status, created at, updated at, TXT record (host, value).
Usage: python scripts/dns/show_retrieval.py -h

---

### show_retrieval_verification.py — Query Public Domain Retrieval Result

Purpose: Query public domain retrieval result, including task ID, status, updated at.
Usage: python scripts/dns/show_retrieval_verification.py -h

---

## Email and Website Domains

### show_email_record_set.py — Query Email Domain Record Set for Public Zone

Purpose: Query the email domain record set for a public zone, including ID, name, type, status, TTL, records.
Usage: python scripts/dns/show_email_record_set.py -h

---

### show_website_record_set.py — Query Website Domain Record Set for Public Zone

Purpose: Query the website domain record set for a public zone, including ID, name, type, status, TTL, records.
Usage: python scripts/dns/show_website_record_set.py -h

---

## DNS Resolution Statistics

### list_instances.py — Batch Query DNS Resolution Statistics Resources

Purpose: Batch query DNS resolution statistics resources, including ID, name, status, region, enterprise project ID. Supports filtering by zone ID, zone name, time range.
Usage: python scripts/dns/list_instances.py -h

---

## API Versions

### list_api_versions.py — Query API Version Information List

Purpose: Query the DNS API version information list, including version ID, status.
Usage: python scripts/dns/list_api_versions.py -h

---

### show_api_info.py — Query API Version Information for Specified Version

Purpose: Query API version information for a specified version, including version ID, status, version, min_version, updated, links.
Usage: python scripts/dns/show_api_info.py -h
