# Enterprise Project EPS Python Script Usage Guide

> EPS is a global service that uses GlobalCredentials for authentication. The --project_id parameter is not required.

---

## Enterprise Projects

### list_enterprise_projects.py — List Enterprise Projects

Purpose: List enterprise projects authorized for the current user, including ID, name, status, type, description, creation time, and update time.
Supports filtering by ID/name/status/type, sorting, and pagination.
Usage: python scripts/eps/list_enterprise_projects.py -h

---

### show_enterprise_project.py — Show Enterprise Project Details

Purpose: Show details of a specified enterprise project, including ID, name, status, type, description, creation time, update time, and deletion marker.
Usage: python scripts/eps/show_enterprise_project.py -h

---

### show_enterprise_project_quota.py — Show Enterprise Project Quota

Purpose: Show quota information for enterprise projects, including usage, quota, and limit for each resource type.
Usage: python scripts/eps/show_enterprise_project_quota.py -h

---

## Cloud Services and Resources

### list_providers.py — List Cloud Service Providers

Purpose: List cloud service providers supported by enterprise projects, including cloud service name, display name, and supported resource types. Supports filtering by cloud service name and pagination.
Usage: python scripts/eps/list_providers.py -h

---

### show_resource_bind_enterprise_project.py — List Resources Bound to an Enterprise Project

Purpose: List resources bound to a specified enterprise project, including resource ID, name, type, and owning project.
Supports filtering by resource type and project ID, searching by resource name, and pagination.
Usage: python scripts/eps/show_resource_bind_enterprise_project.py -h

---

### show_associated_resources.py — Show Associated Resources

Purpose: Show associated enterprise project resource information for a specified resource, including resource ID, name, type, and associated resource list.
Usage: python scripts/eps/show_associated_resources.py -h

---

### list_resource_mapping.py — List Resource Type Mappings

Purpose: List resource type mappings, returning key-value pair mappings of resource types.
Usage: python scripts/eps/list_resource_mapping.py -h

---

## Migration Records

### list_migration_records.py — List Migration Records

Purpose: List enterprise project migration records, including resource ID, name, type, operation type, source/target enterprise project, event time, and status.
Supports filtering by time range and resource ID.
Usage: python scripts/eps/list_migration_records.py -h

---

## Service Configuration

### show_ep_configs.py — Show Service Configuration

Purpose: Show enterprise project service configuration information.
Usage: python scripts/eps/show_ep_configs.py -h

---

## API Versions

### list_api_versions.py — List API Versions

Purpose: List API versions for enterprise projects, including version ID, status, and update time.
Usage: python scripts/eps/list_api_versions.py -h

---

### show_api_version.py — Show API Version Details

Purpose: Show details of a specified enterprise project API version, including version ID, status, update time, and links.
Usage: python scripts/eps/show_api_version.py -h
