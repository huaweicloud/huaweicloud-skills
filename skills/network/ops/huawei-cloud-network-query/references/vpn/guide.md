# VPN Python Script Usage Guide

---

## Availability Zone Queries

### list_availability_zones.py — Query VPN Availability Zone List

Purpose: Query the VPN availability zone list, including category, type, availability zone list.
Usage: python scripts/vpn/list_availability_zones.py -h

---

### list_extended_availability_zones.py — Query Extended Availability Zone List

Purpose: Query the VPN extended availability zone list, including name, common border group, available specifications.
Usage: python scripts/vpn/list_extended_availability_zones.py -h

---

### list_p2c_vgw_availability_zones.py — Query P2C VPN Gateway Availability Zone List

Purpose: Query the P2C VPN gateway availability zone list.
Usage: python scripts/vpn/list_p2c_vgw_availability_zones.py -h

### list_cgws.py — Query Peer Gateway List

Purpose: Query the peer gateway list, including ID, name, BGP AS number, identifier type, identifier value, created at.
Usage: python scripts/vpn/list_cgws.py -h

---

### show_cgw.py — Query Peer Gateway Details

Purpose: Query peer gateway details, including ID, name, BGP AS number, identifier type, identifier value, CA certificate, created at, updated at.
Usage: python scripts/vpn/show_cgw.py -h

### list_vgws.py — Query VPN Gateway List

Purpose: Query the VPN gateway list, including ID, name, status, association type, VPC ID, specification, connection count, used connection count, enterprise project ID.
Usage: python scripts/vpn/list_vgws.py -h

---

### show_vgw.py — Query VPN Gateway Details

Purpose: Query VPN gateway details, including ID, name, status, association type, IP version, VPC ID, specification, connection count, used connection count, enterprise project ID, HA mode, created at, updated at.
Usage: python scripts/vpn/show_vgw.py -h

---

### show_vpn_gateway_certificate.py — Query VPN Gateway Certificate

Purpose: Query VPN gateway certificate details, including ID, name, VPN gateway ID, status, issuer, signature algorithm, certificate serial number, certificate subject, certificate expiration time, created at, updated at.
Usage: python scripts/vpn/show_vpn_gateway_certificate.py -h

---

### show_vpn_gateway_routing_table.py — Query VPN Gateway Routing Table

Purpose: Query the VPN gateway routing table, including destination, next hop, outgoing interface IP, source, AS path, MED value.
Usage: python scripts/vpn/show_vpn_gateway_routing_table.py -h

### list_vpn_connections.py — Query VPN Connection List

Purpose: Query the VPN connection list, including ID, name, status, VPN gateway ID, peer gateway ID, connection mode, enterprise project ID.
Usage: python scripts/vpn/list_vpn_connections.py -h

---

### show_vpn_connection.py — Query VPN Connection Details

Purpose: Query VPN connection details, including ID, name, status, VPN gateway ID, VPN gateway IP, connection mode, peer gateway ID, tunnel local address, tunnel peer address, NQA switch, Hub switch, created at, updated at, enterprise project ID.
Usage: python scripts/vpn/show_vpn_connection.py -h

---

### show_vpn_connection_log.py — Query VPN Connection Log

Purpose: Query VPN connection log, including time, raw message.
Usage: python scripts/vpn/show_vpn_connection_log.py -h

### list_connection_monitors.py — Query Connection Monitor List

Purpose: Query the VPN connection monitor list, including ID, status, VPN connection ID, type, source IP, destination IP.
Usage: python scripts/vpn/list_connection_monitors.py -h

---

### show_connection_monitor.py — Query Connection Monitor Details

Purpose: Query VPN connection monitor details, including ID, status, VPN connection ID, type, source IP, destination IP, protocol type.
Usage: python scripts/vpn/show_connection_monitor.py -h

### list_vpn_gateway_jobs.py — Query VPN Gateway Job List

Purpose: Query the VPN gateway job list, including ID, resource ID, job type, status, created at.
Usage: python scripts/vpn/list_vpn_gateway_jobs.py -h

---

### list_p2c_vpn_gateway_jobs.py — Query P2C VPN Gateway Job List

Purpose: Query the P2C VPN gateway job list, including ID, resource ID, job type, status, created at.
Usage: python scripts/vpn/list_p2c_vpn_gateway_jobs.py -h

### list_p2c_vgws.py — Query P2C VPN Gateway List

Purpose: Query the P2C VPN gateway list, including ID, name, status, VPC ID, specification, max connection count, current connection count, enterprise project ID.
Usage: python scripts/vpn/list_p2c_vgws.py -h

---

### show_p2c_vgw.py — Query P2C VPN Gateway Details

Purpose: Query P2C VPN gateway details, including ID, name, status, VPC ID, connection subnet, specification, max connection count, current connection count, enterprise project ID, created at, updated at.
Usage: python scripts/vpn/show_p2c_vgw.py -h

---

### list_p2c_vgw_connections.py — Query P2C VPN Gateway Connection List

Purpose: Query the P2C VPN gateway connection list, including connection ID, client IP, client username, inbound packets, outbound packets.
Usage: python scripts/vpn/list_p2c_vgw_connections.py -h

---

### show_vpn_connections_log_config.py — Query VPN Connection Log Configuration

Purpose: Query VPN connection log configuration, including log group ID, log stream ID.
Usage: python scripts/vpn/show_vpn_connections_log_config.py -h

### list_vpn_servers_by_project.py — Query VPN Server List Under Project

Purpose: Query the VPN server list under a project, including ID, P2C VPN gateway ID, client authentication type, tunnel protocol, status.
Usage: python scripts/vpn/list_vpn_servers_by_project.py -h

---

### list_vpn_servers_by_vgw.py — Query VPN Server List Under Gateway

Purpose: Query the VPN server list under a VPN gateway, including ID, P2C VPN gateway ID, client authentication type, tunnel protocol, status.
Usage: python scripts/vpn/list_vpn_servers_by_vgw.py -h

---

### show_client_ca.py — Query Client CA Certificate

Purpose: Query client CA certificate details, including ID, name, issuer, subject, serial number, expiration time, signature algorithm, created at, updated at.
Usage: python scripts/vpn/show_client_ca.py -h

### list_vpn_access_policies.py — Query VPN Access Policy List

Purpose: Query the VPN access policy list, including ID, name, type, user group ID, user group name, description.
Usage: python scripts/vpn/list_vpn_access_policies.py -h

---

### show_vpn_access_policy.py — Query VPN Access Policy Details

Purpose: Query VPN access policy details, including ID, name, type, user group ID, user group name, description, created at, updated at.
Usage: python scripts/vpn/show_vpn_access_policy.py -h

### list_vpn_user_groups.py — Query VPN User Group List

Purpose: Query the VPN user group list, including ID, name, description, type, user count.
Usage: python scripts/vpn/list_vpn_user_groups.py -h

---

### show_vpn_user_group.py — Query VPN User Group Details

Purpose: Query VPN user group details, including ID, name, description, type, user count, created at, updated at.
Usage: python scripts/vpn/show_vpn_user_group.py -h

### list_vpn_users.py — Query VPN User List

Purpose: Query the VPN user list, including ID, name, description, user group ID, user group name.
Usage: python scripts/vpn/list_vpn_users.py -h

---

### show_vpn_user.py — Query VPN User Details

Purpose: Query VPN user details, including ID, name, description, user group ID, user group name, created at, updated at.
Usage: python scripts/vpn/show_vpn_user.py -h

---

### list_vpn_users_in_group.py — Query User List Within User Group

Purpose: Query the VPN user list within a user group, including ID, name, description.
Usage: python scripts/vpn/list_vpn_users_in_group.py -h

### show_quotas_info.py — Query Quota Information

Purpose: Query VPN quota information, including type, used, quota, unit.
Usage: python scripts/vpn/show_quotas_info.py -h

---

### list_project_tags.py — Query Project Tags

Purpose: Query VPN project tags, including key, values.
Usage: python scripts/vpn/list_project_tags.py -h

---

### list_resources_by_tags.py — Query Resource Instance List by Tag

Purpose: Query VPN resource instance list by tag, including resource_id, resource_name, tags.
Usage: python scripts/vpn/list_resources_by_tags.py -h

---

### show_resource_tags.py — Query Resource Tags

Purpose: Query VPN resource tags, including key, value.
Usage: python scripts/vpn/show_resource_tags.py -h
