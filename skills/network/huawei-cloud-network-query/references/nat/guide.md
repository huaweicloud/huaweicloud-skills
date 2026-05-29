# NAT Gateway Python Script Usage Guide

---

## Public NAT Gateway

### list_nat_gateways.py — Query NAT Gateway List

Purpose: Query the NAT gateway list, including ID, name, status, spec, router_id, internal_network_id, description, enterprise project ID.
Usage: python scripts/nat/list_nat_gateways.py -h

---

### list_nat_gateway_dnat_rules.py — Query DNAT Rule List

Purpose: Query the NAT gateway DNAT rule list, including ID, status, protocol, floating_ip_address, internal_service_port, private_ip, external_service_port, nat_gateway_id, description.
Usage: python scripts/nat/list_nat_gateway_dnat_rules.py -h

---

### list_nat_gateway_snat_rules.py — Query SNAT Rule List

Purpose: Query the NAT gateway SNAT rule list, including ID, status, floating_ip_address, CIDR, source_type, nat_gateway_id, network ID, description.
Usage: python scripts/nat/list_nat_gateway_snat_rules.py -h

---

### list_nat_gateway_specs.py — Query Public NAT Gateway Specification List

Purpose: Query the NAT gateway specification list, including spec.
Usage: python scripts/nat/list_nat_gateway_specs.py -h

---

### show_nat_gateway.py — Query NAT Gateway Details

Purpose: Query NAT gateway details, including ID, name, description, spec, status, admin state, router_id, internal_network_id, enterprise project ID, created at, dnat_rules_limit, snat_rule_public_ip_limit.
Usage: python scripts/nat/show_nat_gateway.py -h

---

### show_nat_gateway_dnat_rule.py — Query DNAT Rule Details

Purpose: Query NAT gateway DNAT rule details, including ID, nat_gateway_id, protocol, floating_ip_address, floating_ip_id, external_service_port, internal_service_port, private_ip, port ID, status, admin state, description, created at, global_eip_id, global_eip_address.
Usage: python scripts/nat/show_nat_gateway_dnat_rule.py -h

---

### show_nat_gateway_snat_rule.py — Query SNAT Rule Details

Purpose: Query NAT gateway SNAT rule details, including ID, nat_gateway_id, CIDR, source_type, floating_ip_id, floating_ip_address, network ID, status, admin state, description, created at, global_eip_id, global_eip_address.
Usage: python scripts/nat/show_nat_gateway_snat_rule.py -h

### list_private_nats.py — Query Private NAT Gateway List

Purpose: Query the private NAT gateway list, including ID, name, status, spec, description, enterprise project ID.
Usage: python scripts/nat/list_private_nats.py -h

---

### list_private_dnats.py — Query Private DNAT Rule List

Purpose: Query the private NAT gateway DNAT rule list, including ID, gateway_id, protocol, private IP address, internal_service_port, transit_service_port, transit_ip_id, status, description.
Usage: python scripts/nat/list_private_dnats.py -h

---

### list_private_snats.py — Query Private SNAT Rule List

Purpose: Query the private NAT gateway SNAT rule list, including ID, gateway_id, CIDR, subnet ID, description, status.
Usage: python scripts/nat/list_private_snats.py -h

---

### list_specs.py — Query Private NAT Gateway Specification List

Purpose: Query the private NAT gateway specification list, including name, code, rule_max, sess_max, bps_max, pps_max, qps_max.
Usage: python scripts/nat/list_specs.py -h

---

### show_private_nat.py — Query Private NAT Gateway Details

Purpose: Query private NAT gateway details, including ID, name, description, spec, status, enterprise project ID, created at, updated at, rule_max.
Usage: python scripts/nat/show_private_nat.py -h

---

### show_private_dnat.py — Query Private DNAT Rule Details

Purpose: Query private NAT gateway DNAT rule details, including ID, gateway_id, transit_ip_id, network_interface_id, type, protocol, private IP address, internal_service_port, transit_service_port, status, description, enterprise project ID, created at, updated at.
Usage: python scripts/nat/show_private_dnat.py -h

---

### show_private_snat.py — Query Private SNAT Rule Details

Purpose: Query private NAT gateway SNAT rule details, including ID, gateway_id, CIDR, subnet ID, description, status, enterprise project ID, created at, updated at.
Usage: python scripts/nat/show_private_snat.py -h

### list_transit_ip.py — Query Transit IP List

Purpose: Query the transit IP list, including ID, IP address, network_interface_id, gateway_id, subnet ID, status, enterprise project ID.
Usage: python scripts/nat/list_transit_ip.py -h

---

### show_transit_ip.py — Query Transit IP Details

Purpose: Query transit IP details, including ID, IP address, network_interface_id, gateway_id, subnet ID, status, enterprise project ID, created at, updated at.
Usage: python scripts/nat/show_transit_ip.py -h

### list_transit_subnet.py — Query Transit Subnet List

Purpose: Query the transit subnet list, including ID, name, VPC ID, subnet ID, CIDR, type, status, ip_count, description.
Usage: python scripts/nat/list_transit_subnet.py -h

---

### show_transit_subnet.py — Query Transit Subnet Details

Purpose: Query transit subnet details, including ID, name, description, VPC ID, subnet ID, CIDR, type, status, ip_count, created at, updated at.
Usage: python scripts/nat/show_transit_subnet.py -h

---

### list_nat_gateway_tag.py — Query Public NAT Gateway Project Tags

Purpose: Query public NAT gateway project tags, including key, values.
Usage: python scripts/nat/list_nat_gateway_tag.py -h

---

### list_nat_gateway_by_tag.py — Query Public NAT Gateway Instances by Tag

Purpose: Query public NAT gateway instances filtered by tag, including resource_id, resource_name, tags.
Usage: python scripts/nat/list_nat_gateway_by_tag.py -h

---

### show_nat_gateway_tag.py — Query Tags of a Specific Public NAT Gateway

Purpose: Query tags of a specific public NAT gateway, including key, value.
Usage: python scripts/nat/show_nat_gateway_tag.py -h

---

### list_private_nat_tags.py — Query Private NAT Gateway Project Tags

Purpose: Query private NAT gateway project tags, including key, values.
Usage: python scripts/nat/list_private_nat_tags.py -h

---

### list_private_nats_by_tags.py — Query Private NAT Gateway Instances by Tag

Purpose: Query private NAT gateway instances filtered by tag, including resource_id, resource_name, tags.
Usage: python scripts/nat/list_private_nats_by_tags.py -h

---

### show_private_nat_tags.py — Query Tags of a Specific Private NAT Gateway

Purpose: Query tags of a specific private NAT gateway, including key, value.
Usage: python scripts/nat/show_private_nat_tags.py -h

---

### list_transit_ip_tags.py — Query Transit IP Project Tags

Purpose: Query transit IP project tags, including key, values.
Usage: python scripts/nat/list_transit_ip_tags.py -h

---

### list_transit_ips_by_tags.py — Query Transit IP Instances by Tag

Purpose: Query transit IP instances filtered by tag, including resource_id, resource_name, tags.
Usage: python scripts/nat/list_transit_ips_by_tags.py -h

---

### show_transit_ip_tags.py — Query Tags of a Specific Transit IP

Purpose: Query tags of a specific transit IP, including key, value.
Usage: python scripts/nat/show_transit_ip_tags.py -h

---

### list_transit_subnet_tags.py — Query Transit Subnet Project Tags

Purpose: Query transit subnet project tags, including key, values.
Usage: python scripts/nat/list_transit_subnet_tags.py -h

---

### list_transit_subnets_by_tags.py — Query Transit Subnet Instances by Tag

Purpose: Query transit subnet instances filtered by tag, including resource_id, resource_name, tags.
Usage: python scripts/nat/list_transit_subnets_by_tags.py -h

---

### show_transit_subnet_tags.py — Query Tags of a Specific Transit Subnet

Purpose: Query tags of a specific transit subnet, including key, value.
Usage: python scripts/nat/show_transit_subnet_tags.py -h
