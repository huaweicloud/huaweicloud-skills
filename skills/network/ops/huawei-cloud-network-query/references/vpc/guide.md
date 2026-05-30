# VPC Python Script Usage Guide

---

## v3 List Queries

### list_vpcs.py — Query VPC List

Purpose: Query the VPC list, including name, ID, CIDR, status, description.
Usage: python scripts/vpc/list_vpcs.py -h

---

### list_virsubnets.py — Query Subnet List

Purpose: Query the subnet list, including name, ID, VPC ID, status, CIDR range, availability zone ID, description.
Usage: python scripts/vpc/list_virsubnets.py -h

---

### list_security_groups.py — Query Security Group List

Purpose: Query the security group list, including name, ID, description.
Usage: python scripts/vpc/list_security_groups.py -h

---

### list_security_group_rules.py — Query Security Group Rule List

Purpose: Query the security group rule list, including ID, direction, protocol, action, remote IP prefix, remote security group ID, security group ID, priority.
Usage: python scripts/vpc/list_security_group_rules.py -h

---

### list_ports.py — Query Port List

Purpose: Query the port list, including ID, name, device ID, device owner, MAC address, status, admin state, VPC ID, subnet ID.
Usage: python scripts/vpc/list_ports.py -h

---

### list_firewall.py — Query Firewall List

Purpose: Query the firewall list, including ID, name, status, admin state, description, enterprise project ID.
Usage: python scripts/vpc/list_firewall.py -h

---

### list_address_group.py — Query Address Group List

Purpose: Query the address group list, including ID, name, IP version, max capacity, description.
Usage: python scripts/vpc/list_address_group.py -h

---

### list_sub_network_interfaces.py — Query Sub Network Interface List

Purpose: Query the sub network interface list, including ID, subnet ID, private IP address, MAC address, VPC ID, parent ID.
Usage: python scripts/vpc/list_sub_network_interfaces.py -h

---

### list_traffic_mirror_filters.py — Query Traffic Mirror Filter List

Purpose: Query the traffic mirror filter list, including ID, name, description, created at, updated at.
Usage: python scripts/vpc/list_traffic_mirror_filters.py -h

---

### list_traffic_mirror_filter_rules.py — Query Traffic Mirror Filter Rule List

Purpose: Query the traffic mirror filter rule list, including ID, traffic mirror filter ID, direction, protocol, source CIDR, destination CIDR, action, priority.
Usage: python scripts/vpc/list_traffic_mirror_filter_rules.py -h

---

### list_traffic_mirror_sessions.py — Query Traffic Mirror Session List

Purpose: Query the traffic mirror session list, including ID, name, traffic mirror filter ID, traffic mirror target ID, virtual network ID, priority, enabled.
Usage: python scripts/vpc/list_traffic_mirror_sessions.py -h

---

### list_virsubnet_cidr_reservations.py — Query Subnet CIDR Reservation List

Purpose: Query the subnet CIDR reservation list, including ID, subnet ID, CIDR, IP version, name, description.
Usage: python scripts/vpc/list_virsubnet_cidr_reservations.py -h

### list_address_groups_dependency.py — Query Address Group Dependencies

Purpose: Query address group dependencies, including ID, name, IP version, max capacity, description.
Usage: python scripts/vpc/list_address_groups_dependency.py -h

### show_vpc.py — Query VPC Details

Purpose: Query VPC details, including ID, name, CIDR, status, description, enterprise project ID, created at, updated at.
Usage: python scripts/vpc/show_vpc.py -h

---

### show_virsubnet.py — Query Subnet Details

Purpose: Query subnet details, including ID, name, VPC ID, status, CIDR range, availability zone ID, description, created at, updated at.
Usage: python scripts/vpc/show_virsubnet.py -h

---

### show_security_group.py — Query Security Group Details

Purpose: Query security group details, including ID, name, description, enterprise project ID, created at, updated at.
Usage: python scripts/vpc/show_security_group.py -h

---

### show_security_group_rule.py — Query Security Group Rule Details

Purpose: Query security group rule details, including ID, direction, protocol, action, remote IP prefix, remote security group ID, security group ID, priority, IP protocol type, port range min, port range max.
Usage: python scripts/vpc/show_security_group_rule.py -h

---

### show_port.py — Query Port Details

Purpose: Query port details, including ID, name, device ID, device owner, MAC address, status, admin state, VPC ID, subnet ID.
Usage: python scripts/vpc/show_port.py -h

---

### show_firewall.py — Query Firewall Details

Purpose: Query firewall details, including ID, name, status, admin state, description, enterprise project ID, created at, updated at.
Usage: python scripts/vpc/show_firewall.py -h

---

### show_address_group.py — Query Address Group Details

Purpose: Query address group details, including ID, name, IP version, max capacity, description, created at, updated at.
Usage: python scripts/vpc/show_address_group.py -h

---

### show_sub_network_interface.py — Query Sub Network Interface Details

Purpose: Query sub network interface details, including ID, subnet ID, private IP address, MAC address, VPC ID, parent ID, description.
Usage: python scripts/vpc/show_sub_network_interface.py -h

---

### show_virsubnet_cidr_reservation.py — Query Subnet CIDR Reservation Details

Purpose: Query subnet CIDR reservation details, including ID, subnet ID, CIDR, IP version, name, description.
Usage: python scripts/vpc/show_virsubnet_cidr_reservation.py -h

---

### show_traffic_mirror_filter.py — Query Traffic Mirror Filter Details

Purpose: Query traffic mirror filter details, including ID, name, description, created at, updated at.
Usage: python scripts/vpc/show_traffic_mirror_filter.py -h

---

### show_traffic_mirror_filter_rule.py — Query Traffic Mirror Filter Rule Details

Purpose: Query traffic mirror filter rule details, including ID, traffic mirror filter ID, direction, protocol, source CIDR, destination CIDR, action, priority.
Usage: python scripts/vpc/show_traffic_mirror_filter_rule.py -h

---

### show_traffic_mirror_session.py — Query Traffic Mirror Session Details

Purpose: Query traffic mirror session details, including ID, name, traffic mirror filter ID, traffic mirror target ID, virtual network ID, priority, enabled, description.
Usage: python scripts/vpc/show_traffic_mirror_session.py -h

---

### show_quota.py — Query Quota

Purpose: Query quota, including key, value.
Usage: python scripts/vpc/show_quota.py -h

---

### show_sub_network_interfaces_quantity.py — Query Sub Network Interface Count

Purpose: Query the count of sub network interfaces.
Usage: python scripts/vpc/show_sub_network_interfaces_quantity.py -h

### list_subnets.py — Query Subnet List (v2)

Purpose: Query the subnet list (v2), including name, ID, CIDR, gateway IP, VPC ID, status, availability zone.
Usage: python scripts/vpc/list_subnets.py -h

---

### list_flow_logs.py — Query VPC Flow Log List

Purpose: Query the VPC flow log list, including ID, name, resource type, resource ID, traffic type, log group ID, log topic ID, status.
Usage: python scripts/vpc/list_flow_logs.py -h

---

### list_route_tables.py — Query Route Table List

Purpose: Query the route table list, including ID, VPC ID, name.
Usage: python scripts/vpc/list_route_tables.py -h

---

### list_vpc_peerings.py — Query VPC Peering List

Purpose: Query the VPC peering list, including ID, name, status, requester VPC ID, requester tenant ID, accepter VPC ID, accepter tenant ID.
Usage: python scripts/vpc/list_vpc_peerings.py -h

---

### list_vpc_routes.py — Query VPC Route List

Purpose: Query the VPC route list, including ID, type, destination, VPC ID, next hop.
Usage: python scripts/vpc/list_vpc_routes.py -h

---

### list_privateips.py — Query Private IP List

Purpose: Query the private IP list, including ID, subnet ID, IP address, status, device owner.
Usage: python scripts/vpc/list_privateips.py -h

### show_subnet.py — Query Subnet Details (v2)

Purpose: Query subnet details (v2), including ID, name, CIDR, gateway IP, VPC ID, status, availability zone, DHCP enabled, primary DNS, secondary DNS, description.
Usage: python scripts/vpc/show_subnet.py -h

---

### show_flow_log.py — Query VPC Flow Log Details

Purpose: Query VPC flow log details, including ID, name, resource type, resource ID, traffic type, log group ID, log topic ID, status, description.
Usage: python scripts/vpc/show_flow_log.py -h

---

### show_route_table.py — Query Route Table Details

Purpose: Query route table details, including ID, name, VPC ID, description.
Usage: python scripts/vpc/show_route_table.py -h

---

### show_vpc_peering.py — Query VPC Peering Details

Purpose: Query VPC peering details, including ID, name, status.
Usage: python scripts/vpc/show_vpc_peering.py -h

---

### show_vpc_route.py — Query VPC Route Details

Purpose: Query VPC route details, including ID, type, destination, VPC ID, next hop.
Usage: python scripts/vpc/show_vpc_route.py -h

---

### show_privateip.py — Query Private IP Details

Purpose: Query private IP details, including ID, subnet ID, IP address, status, device owner.
Usage: python scripts/vpc/show_privateip.py -h

---

### show_network_ip_availabilities.py — Query Network IP Availability

Purpose: Query the number of available network IPs.
Usage: python scripts/vpc/show_network_ip_availabilities.py -h

---
