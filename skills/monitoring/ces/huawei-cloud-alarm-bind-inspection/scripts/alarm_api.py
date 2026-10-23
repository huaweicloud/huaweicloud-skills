#!/usr/bin/env python3
"""
CES (Cloud Eye Service) API wrapper.
Replaces the former CloudScope OA API with standard Huawei Cloud CES SDK calls.
Authentication is via AK/SK (environment variables), not browser cookie/CFTK.
"""

import logging
from config import build_ces_client

from huaweicloudsdkces.v2.model.list_alarm_rules_request import ListAlarmRulesRequest
from huaweicloudsdkces.v2.model.list_alarm_rule_policies_request import ListAlarmRulePoliciesRequest
from huaweicloudsdkces.v2.model.list_alarm_rule_resources_request import ListAlarmRuleResourcesRequest
from huaweicloudsdkces.v2.model.show_alarm_template_request import ShowAlarmTemplateRequest
from huaweicloudsdkces.v2.model.show_resource_group_request import ShowResourceGroupRequest
from huaweicloudsdkces.v2.model.list_resource_groups_request import ListResourceGroupsRequest
from huaweicloudsdkces.v2.model.list_resource_groups_services_resources_request import (
    ListResourceGroupsServicesResourcesRequest,
)

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger("ces-api")

YELLOW = "\033[33m"
RED = "\033[31m"
RESET = "\033[0m"


def _to_dict(obj):
    """Convert a CES SDK model object to a plain dict."""
    if obj is None:
        return None
    if hasattr(obj, "to_dict"):
        return obj.to_dict()
    return obj


# ---------------------------------------------------------------------------
# Alarm Rules
# ---------------------------------------------------------------------------

def fetch_all_alarm_rules(region: str = None):
    """
    Fetch all alarm rules from CES via ListAlarmRules (with pagination).

    Args:
        region: Huawei Cloud region ID. If None, uses default from env.

    Returns:
        List of alarm rule dicts. Each dict has keys:
        alarm_id, name, namespace, type, enabled, notification_enabled,
        policies, resources, alarm_notifications, enterprise_project_id, etc.
    """
    client = build_ces_client(region)
    result = []
    offset = 0
    limit = 100

    try:
        while True:
            request = ListAlarmRulesRequest()
            request.offset = offset
            request.limit = limit

            response = client.list_alarm_rules(request)
            alarms = getattr(response, "alarms", []) or []
            count = getattr(response, "count", 0)

            for alarm in alarms:
                result.append(_to_dict(alarm))

            offset += len(alarms)
            if offset >= count or len(alarms) == 0:
                break

        logger.info(f"Fetched {len(result)} alarm rules from CES")
        return result

    except Exception as e:
        logger.error(f"{RED}fetch_all_alarm_rules failed: {e}{RESET}")
        return result


def fetch_alarm_rule_policies(alarm_id: str, region: str = None):
    """
    Fetch alarm policies bound to a specific alarm rule.

    Args:
        alarm_id: Alarm rule ID (starts with 'al').
        region: Huawei Cloud region ID.

    Returns:
        List of policy dicts (metric_name, period, filter, comparison_operator,
        value, unit, count, level, namespace, dimension_name).
    """
    client = build_ces_client(region)
    result = []
    offset = 0
    limit = 100

    try:
        while True:
            request = ListAlarmRulePoliciesRequest()
            request.alarm_id = alarm_id
            request.offset = offset
            request.limit = limit

            response = client.list_alarm_rule_policies(request)
            policies = getattr(response, "policies", []) or []
            count = getattr(response, "count", 0)

            for policy in policies:
                result.append(_to_dict(policy))

            offset += len(policies)
            if offset >= count or len(policies) == 0:
                break

        return result

    except Exception as e:
        logger.error(f"{RED}fetch_alarm_rule_policies failed: alarm_id={alarm_id}, error={e}{RESET}")
        return result


def fetch_alarm_rule_resources(alarm_id: str, region: str = None):
    """
    Fetch resources associated with an alarm rule.

    Note: Resources are typically already embedded in the ListAlarmRules response.
    Use this only if you need a fresh fetch of resources for a specific rule.

    Args:
        alarm_id: Alarm rule ID.
        region: Huawei Cloud region ID.

    Returns:
        List of resource dicts.
    """
    client = build_ces_client(region)
    result = []
    offset = 0
    limit = 100

    try:
        while True:
            request = ListAlarmRuleResourcesRequest()
            request.alarm_id = alarm_id
            request.offset = offset
            request.limit = limit

            response = client.list_alarm_rule_resources(request)
            resources = getattr(response, "resources", []) or []
            count = getattr(response, "count", 0)

            for res in resources:
                result.append(_to_dict(res))

            offset += len(resources)
            if offset >= count or len(resources) == 0:
                break

        return result

    except Exception as e:
        logger.error(f"{RED}fetch_alarm_rule_resources failed: alarm_id={alarm_id}, error={e}{RESET}")
        return result


# ---------------------------------------------------------------------------
# Alarm Templates
# ---------------------------------------------------------------------------

def fetch_alarm_template(template_id: str, region: str = None):
    """
    Fetch alarm template details by template ID.

    Args:
        template_id: Alarm template ID.
        region: Huawei Cloud region ID.

    Returns:
        Template detail dict, or None on failure.
    """
    client = build_ces_client(region)

    try:
        request = ShowAlarmTemplateRequest()
        request.template_id = template_id

        response = client.show_alarm_template(request)
        return _to_dict(getattr(response, "alarm_template", None))

    except Exception as e:
        logger.error(f"{RED}fetch_alarm_template failed: template_id={template_id}, error={e}{RESET}")
        return None


# ---------------------------------------------------------------------------
# Resource Groups
# ---------------------------------------------------------------------------

def fetch_all_resource_groups(region: str = None, enterprise_project_id: str = None):
    """
    List all resource groups in CES.

    Args:
        region: Huawei Cloud region ID.
        enterprise_project_id: Optional enterprise project filter.

    Returns:
        List of resource group dicts.
    """
    client = build_ces_client(region)
    result = []
    offset = 0
    limit = 100

    try:
        while True:
            request = ListResourceGroupsRequest()
            request.offset = offset
            request.limit = limit
            if enterprise_project_id:
                request.enterprise_project_id = enterprise_project_id

            response = client.list_resource_groups(request)
            groups = getattr(response, "resource_groups", []) or []
            count = getattr(response, "count", 0)

            for group in groups:
                result.append(_to_dict(group))

            offset += len(groups)
            if offset >= count or len(groups) == 0:
                break

        return result

    except Exception as e:
        logger.error(f"{RED}fetch_all_resource_groups failed: {e}{RESET}")
        return result


def fetch_resource_group(group_id: str, region: str = None):
    """
    Show resource group details (including resources).

    Args:
        group_id: Resource group ID.
        region: Huawei Cloud region ID.

    Returns:
        Resource group detail dict, or None on failure.
    """
    client = build_ces_client(region)

    try:
        request = ShowResourceGroupRequest()
        request.group_id = group_id

        response = client.show_resource_group(request)
        return _to_dict(getattr(response, "resource_group", None))

    except Exception as e:
        logger.error(f"{RED}fetch_resource_group failed: group_id={group_id}, error={e}{RESET}")
        return None


def fetch_resource_group_services_resources(
    group_id: str,
    service: str = "",
    region: str = None,
    dim_name: str = "",
    limit: int = 100,
):
    """
    List resources in a resource group filtered by service.

    This replaces the former fetch_monitor_resources OA API.
    Used by enrich_metric_dimension to discover resources and their dimensions.

    Args:
        group_id: Resource group ID.
        service: Cloud service namespace (e.g., "SYS.ECS").
        region: Huawei Cloud region ID.
        dim_name: Optional dimension name filter.
        limit: Page size.

    Returns:
        List of resource dicts. Each resource has 'dimensions' (list of
        {name, value}) describing its metric dimensions.
    """
    client = build_ces_client(region)
    result = []
    offset = 0

    try:
        while True:
            request = ListResourceGroupsServicesResourcesRequest()
            request.group_id = group_id
            request.offset = offset
            request.limit = limit
            if service:
                request.service = service
            if dim_name:
                request.dim_name = dim_name

            response = client.list_resource_groups_services_resources(request)
            resources = getattr(response, "resources", []) or []
            count = getattr(response, "count", 0)

            for res in resources:
                result.append(_to_dict(res))

            offset += len(resources)
            if offset >= count or len(resources) == 0:
                break

        return result

    except Exception as e:
        logger.warning(
            f"{YELLOW}fetch_resource_group_services_resources failed: "
            f"group_id={group_id}, service={service}, error={e}{RESET}"
        )
        return result
