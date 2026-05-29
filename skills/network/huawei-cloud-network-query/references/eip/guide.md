# EIP Python Script Usage Guide

---

## List Queries

### list_publicips.py — Query Elastic Public IP List

Purpose: Query the elastic public IP list, including ID, public IP address, status, type, alias, bandwidth size.
Usage: python scripts/eip/list_publicips.py -h

---

### list_bandwidth.py — Query Bandwidth List

Purpose: Query the bandwidth list, including ID, name, size, type, billing mode, publicip_count.
Usage: python scripts/eip/list_bandwidth.py -h

---

### list_bandwidths_limit.py — Query Tenant Bandwidth Limits

Purpose: Query tenant bandwidth limits, including ID, billing mode, min_size, max_size.
Usage: python scripts/eip/list_bandwidths_limit.py -h

---

### list_common_pools.py — Query Common Pool List

Purpose: Query the common pool list, including common border group, publicip_pools.
Usage: python scripts/eip/list_common_pools.py -h

---

### list_publicip_pool.py — Query Public IP Pool List

Purpose: Query the public IP pool list, including ID, name, type, status, size, used, common border group.
Usage: python scripts/eip/list_publicip_pool.py -h

---

### list_share_bandwidth_types.py — Query Shared Bandwidth Type List

Purpose: Query the shared bandwidth type list, including ID, bandwidth type, name_zh, name_en, common border group.
Usage: python scripts/eip/list_share_bandwidth_types.py -h

---

### list_project_geip_bindings.py — Query GEIP Binding List

Purpose: Query the tenant list of GEIP and instance binding relationships, including geip_id, geip_ip_address, instance_type, instance_id.
Usage: python scripts/eip/list_project_geip_bindings.py -h

---

### list_tenant_vpc_igws.py — Query Virtual IGW List

Purpose: Query the virtual IGW list under a tenant, including ID, name, VPC ID, enable_ipv6.
Usage: python scripts/eip/list_tenant_vpc_igws.py -h

---

### show_publicip.py — Query Elastic Public IP Details

Purpose: Query elastic public IP details.
Usage: python scripts/eip/show_publicip.py -h

---

### show_publicip_pool.py — Query Public IP Pool Details

Purpose: Query public IP pool details.
Usage: python scripts/eip/show_publicip_pool.py -h

---

### show_publicip_pool_types.py — Query Public IP Pool Types

Purpose: Query public IP pool types.
Usage: python scripts/eip/show_publicip_pool_types.py -h

---

### show_internal_vpc_igw.py — Query Virtual IGW Details

Purpose: Query virtual IGW details.
Usage: python scripts/eip/show_internal_vpc_igw.py -h

---

### count_eip_available_resources.py — Query Available EIP Resource Count

Purpose: Query the number of available elastic public IP resources, including available count.
Usage: python scripts/eip/count_eip_available_resources.py -h

---

### list_eip_bandwidths.py — Query Bandwidth List (v3 API)

Purpose: Query the bandwidth list (v3 API, returns more detailed bandwidth information), including ID, name, size, type, bandwidth_type, admin_state, publicip_count.
Usage: python scripts/eip/list_eip_bandwidths.py -h
