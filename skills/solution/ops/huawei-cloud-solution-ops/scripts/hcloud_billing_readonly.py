#!/usr/bin/env python3
"""Build planner-only Huawei Cloud billing and cost specs plus hcloud command plans."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

import hcloud_common

DEFAULT_ENDPOINT_BASE = "https://bss-intl.myhuaweicloud.com"
BILL_CYCLE_RE = re.compile(r"^\d{4}-\d{2}$")
SEMANTIC_CATALOG_PATH = hcloud_common.REFERENCES_DIR / "billing" / "semantic-catalog.json"
BSS_CLI_REGION = "cn-north-1"
BSS_X_LANGUAGE = "zh_CN"
SUPPORTED_X_LANGUAGES = {"zh_CN", "en_US"}
PRICING_REGION_DEFAULT = "cn-north-4"
PERIOD_TYPE_ALIASES = {
    "0": 0,
    "day": 0,
    "days": 0,
    "天": 0,
    "2": 2,
    "month": 2,
    "months": 2,
    "月": 2,
    "3": 3,
    "year": 3,
    "years": 3,
    "年": 3,
    "4": 4,
    "hour": 4,
    "hours": 4,
    "小时": 4,
}
ON_DEMAND_PRICING_PRESETS: dict[str, dict[str, Any]] = {
    "ecs": {
        "cloud_service_type": "hws.service.type.ec2",
        "resource_type": "hws.resource.type.vm",
        "usage_measure_id": 4,
        "usage_factor": "Duration",
        "spec_suffix": ".linux",
        "help": "ECS on-demand VM pricing; append .win explicitly for Windows specs.",
    },
    "evs": {
        "cloud_service_type": "hws.service.type.ebs",
        "resource_type": "hws.resource.type.volume",
        "usage_measure_id": 4,
        "usage_factor": "Duration",
        "need_resource_size": True,
        "default_size": 10,
        "default_size_measure_id": 17,
        "help": "EVS volume pricing; size defaults to 10 GB.",
    },
    "eip-bw": {
        "cloud_service_type": "hws.service.type.vpc",
        "resource_type": "hws.resource.type.bandwidth",
        "usage_measure_id": 4,
        "usage_factor": "Duration",
        "need_resource_size": True,
        "default_size": 1,
        "default_size_measure_id": 15,
        "help": "EIP bandwidth pricing; size defaults to 1 Mbps.",
    },
    "eip-flow": {
        "cloud_service_type": "hws.service.type.vpc",
        "resource_type": "hws.resource.type.bandwidth",
        "usage_measure_id": 10,
        "usage_factor": "upflow",
        "help": "EIP traffic pricing; usage unit is GB.",
    },
    "eip-ip": {
        "cloud_service_type": "hws.service.type.vpc",
        "resource_type": "hws.resource.type.ip",
        "usage_measure_id": 4,
        "usage_factor": "Duration",
        "help": "Public EIP address pricing.",
    },
    "vpc": {
        "cloud_service_type": "hws.service.type.vpc",
        "resource_type": "hws.resource.type.vpcep",
        "usage_measure_id": 4,
        "usage_factor": "Duration",
        "help": "VPC endpoint pricing.",
    },
    "elb": {
        "cloud_service_type": "hws.service.type.elb",
        "resource_type": "hws.resource.type.elbv2",
        "usage_measure_id": 4,
        "usage_factor": "Duration",
        "help": "ELB pricing code from the official reference script; confirm current ELB SKU support.",
    },
    "nat": {
        "cloud_service_type": "hws.service.type.natgateway",
        "resource_type": "hws.resource.type.natgateway",
        "usage_measure_id": 4,
        "usage_factor": "Duration",
        "help": "Public NAT gateway pricing.",
    },
    "obs": {
        "cloud_service_type": "hws.service.type.obs",
        "resource_type": "hws.resource.type.obs",
        "usage_measure_id": 4,
        "usage_factor": "Duration",
        "help": "OBS storage pricing.",
    },
    "sfs": {
        "cloud_service_type": "hws.service.type.sfsturbo",
        "resource_type": "hws.resource.type.sfsturbo",
        "usage_measure_id": 4,
        "usage_factor": "Duration",
        "need_resource_size": True,
        "default_size": 500,
        "default_size_measure_id": 17,
        "help": "SFS Turbo pricing; size defaults to 500 GB.",
    },
}
PERIOD_PRICING_PRESETS: dict[str, dict[str, Any]] = {
    "ecs": {
        "cloud_service_type": "hws.service.type.ec2",
        "resource_type": "hws.resource.type.vm",
        "spec_suffix": ".linux",
        "help": "ECS yearly/monthly VM pricing; append .win explicitly for Windows specs.",
    },
    "evs": {
        "cloud_service_type": "hws.service.type.ebs",
        "resource_type": "hws.resource.type.volume",
        "need_resource_size": True,
        "default_size": 10,
        "default_size_measure_id": 17,
        "help": "EVS yearly/monthly volume pricing; size defaults to 10 GB.",
    },
    "eip-bw": {
        "cloud_service_type": "hws.service.type.vpc",
        "resource_type": "hws.resource.type.bandwidth",
        "need_resource_size": True,
        "default_size": 1,
        "default_size_measure_id": 15,
        "help": "EIP yearly/monthly bandwidth pricing; size defaults to 1 Mbps.",
    },
    "eip-ip": {
        "cloud_service_type": "hws.service.type.vpc",
        "resource_type": "hws.resource.type.ip",
        "help": "Public EIP address yearly/monthly pricing.",
    },
    "elb": {
        "cloud_service_type": "hws.service.type.elb",
        "resource_type": "hws.resource.type.elbv3",
        "help": "Dedicated ELB yearly/monthly pricing; confirm current SKU support.",
    },
    "nat": {
        "cloud_service_type": "hws.service.type.natgateway",
        "resource_type": "hws.resource.type.natgateway",
        "help": "NAT gateway yearly/monthly pricing.",
    },
    "obs": {
        "cloud_service_type": "hws.service.type.obs",
        "resource_type": "hws.resource.type.obs",
        "help": "OBS yearly/monthly pricing.",
    },
    "sfs": {
        "cloud_service_type": "hws.service.type.sfsturbo",
        "resource_type": "hws.resource.type.sfsturbo",
        "need_resource_size": True,
        "default_size": 500,
        "default_size_measure_id": 17,
        "help": "SFS Turbo yearly/monthly pricing; size defaults to 500 GB.",
    },
    "bms": {
        "cloud_service_type": "hws.service.type.baremetal",
        "resource_type": "hws.resource.type.pm",
        "spec_suffix": ".linux",
        "help": "BMS yearly/monthly pricing.",
    },
}

OPERATIONS: dict[str, dict[str, Any]] = {
    "account-balances": {
        "title": "ShowCustomerAccountBalances",
        "method": "GET",
        "path": "/v2/accounts/customer-accounts/balances",
        "doc_url": "https://support.huaweicloud.com/api-bss/",
        "permission": "bss:account:get",
        "query_fields": {},
        "freshness": "Point-in-time account balance and debt snapshot; it does not explain resource-level charge causes.",
    },
    "monthly-sum": {
        "title": "ShowCustomerMonthlySum",
        "method": "GET",
        "path": "/v2/bills/customer-bills/monthly-sum",
        "doc_url": "https://support.huaweicloud.com/intl/zh-cn/api-oce/mbc_00008.html",
        "permission": "billing:bill:view",
        "required_query": ["bill_cycle"],
        "freshness": "Summary bill data contains consumption up to 24:00 of the previous day and supports recent 3 years.",
    },
    "billing-statements": {
        "title": "ListCustomerBillsFeeRecords",
        "supports_x_language": True,
        "method": "GET",
        "path": "/v2/bills/customer-bills/fee-records",
        "doc_url": "https://support.huaweicloud.com/api-bss/",
        "permission": "bss:bill:list",
        "required_query": ["bill_cycle"],
        "query_fields": {
            "bill_cycle": "bill_cycle",
            "method": "method",
            "sub_customer_id": "sub_customer_id",
            "offset": "offset",
            "limit": "limit",
        },
        "freshness": "Billing statement rows are transaction evidence for one billing cycle; do not substitute them with monthly summary totals.",
    },
    "cost-data": {
        "title": "ListCosts",
        "supports_x_language": True,
        "method": "POST",
        "path": "/v4/costs/cost-analysed-bills/query",
        "doc_url": "https://support.huaweicloud.com/intl/zh-cn/api-oce/costm_00014.html",
        "permission": "costCenter:costAnalysis:listCosts",
        "required_body": ["time_condition", "groupby", "cost_type", "amount_type"],
        "freshness": "Original costs have about one-hour delay; amortized costs refresh every 24 hours and may lag 24-48 hours.",
    },
    "monthly-breakdown": {
        "title": "ListCustomerBillsMonthlyBreakDown",
        "supports_x_language": True,
        "method": "GET",
        "path": "/v2/bills/customer-bills/monthly-break-down",
        "doc_url": "https://support.huaweicloud.com/api-bss/",
        "permission": "bss:bill:list",
        "required_query": ["shared_month"],
        "query_fields": {
            "shared_month": "shared_month",
            "service_type_code": "service_type_code",
            "resource_type_code": "resource_type",
            "resource_id": "resource_id",
            "enterprise_project_id": "enterprise_project_id",
            "method": "method",
            "sub_customer_id": "sub_customer_id",
            "offset": "offset",
            "limit": "limit",
        },
        "freshness": "Monthly amortization evidence is available only for a bounded recent history; do not mix it with cash transaction totals.",
    },
    "resource-records": {
        "title": "ListCustomerselfResourceRecordDetails",
        "supports_x_language": True,
        "method": "POST",
        "path": "/v2/bills/customer-bills/res-records/query",
        "doc_url": "https://support.huaweicloud.com/intl/zh-cn/api-oce/mbc_00003.html",
        "permission": "billing:billDetail:view",
        "required_body": ["cycle"],
        "freshness": "Resource detail data can be delayed by up to 24 hours.",
    },
    "resource-fee-records": {
        "title": "ListCustomerselfResourceRecords",
        "supports_x_language": True,
        "method": "GET",
        "path": "/v2/bills/customer-bills/res-fee-records",
        "doc_url": "https://support.huaweicloud.com/intl/zh-cn/api-oce/mbc_00004.html",
        "permission": "billing:billDetail:view",
        "required_query": ["cycle"],
        "freshness": "Resource fee records are billing-period data; date filters must stay within the same cycle.",
    },
    "usage-summary": {
        "title": "ListResourceUsageSummary",
        "supports_x_language": True,
        "method": "GET",
        "path": "/v2/bills/customer-bills/resources/usage/summary",
        "doc_url": "https://support.huaweicloud.com/api-bss/",
        "permission": "bss:bill:list",
        "required_query": ["bill_cycle", "service_type_code", "resource_type_code", "usage_type"],
        "query_fields": {
            "bill_cycle": "bill_cycle",
            "service_type_code": "service_type_code",
            "resource_type_code": "resource_type",
            "usage_type": "usage_type",
            "offset": "offset",
            "limit": "limit",
        },
        "freshness": "95th-percentile usage summary for CDN, OBS, IEC, and VPC bandwidth-style products; use usage detail before attributing a spike to one resource.",
    },
    "usage-detail": {
        "title": "ListResourceUsage",
        "supports_x_language": True,
        "method": "GET",
        "path": "/v2/bills/customer-bills/resources/usage/details",
        "doc_url": "https://support.huaweicloud.com/api-bss/",
        "permission": "bss:bill:list",
        "required_query": ["bill_cycle", "service_type_code", "resource_type_code", "usage_type", "resource_id"],
        "query_fields": {
            "bill_cycle": "bill_cycle",
            "service_type_code": "service_type_code",
            "resource_type_code": "resource_type",
            "usage_type": "usage_type",
            "resource_id": "resource_id",
            "offset": "offset",
            "limit": "limit",
        },
        "freshness": "95th-percentile usage detail for one resource; resource_id stays protected in summaries and one page remains partial evidence.",
    },
    "on-demand-pricing": {
        "title": "ListOnDemandResourceRatings",
        "method": "POST",
        "path": "/v2/bills/ratings/on-demand-resources",
        "doc_url": "https://support.huaweicloud.com/api-bss/",
        "permission": "bss:pricing:inquire",
        "required_body": ["project_id", "product_infos"],
        "freshness": "On-demand inquiry is a point-in-time quote for the provided SKU dimensions; it is not a historical bill or a purchase order.",
    },
    "period-pricing": {
        "title": "ListRateOnPeriodDetail",
        "method": "POST",
        "path": "/v2/bills/ratings/period-resources/subscribe-rate",
        "doc_url": "https://support.huaweicloud.com/api-bss/",
        "permission": "bss:pricing:inquire",
        "required_body": ["project_id", "product_infos"],
        "freshness": "Yearly/monthly inquiry is a point-in-time subscribe quote for the provided SKU dimensions; renewal and existing-order discounts require separate evidence.",
    },
    "account-change-records": {
        "title": "ListCustomerAccountChangeRecords",
        "method": "GET",
        "path": "/v2/accounts/customer-accounts/account-change-records",
        "doc_url": "https://support.huaweicloud.com/api-bss/",
        "permission": "bss:account:list",
        "required_query": ["balance_type"],
        "query_fields": {
            "balance_type": "balance_type",
            "bill_cycle": "bill_cycle",
            "offset": "offset",
            "limit": "limit",
        },
        "freshness": "Read-only account transaction ledger; the word Change in the operation name does not imply mutation.",
    },
    "stored-value-cards": {
        "title": "ListStoredValueCards",
        "method": "GET",
        "path": "/v2/promotions/benefits/stored-value-cards",
        "doc_url": "https://support.huaweicloud.com/api-bss/",
        "permission": "bss:storedValueCard:list",
        "required_query": ["status"],
        "query_fields": {
            "status": "status",
            "offset": "offset",
            "limit": "limit",
        },
        "freshness": "Stored-value card status evidence; it is not a single transaction or resource-charge explanation.",
    },
    "free-resource-infos": {
        "title": "ListFreeResourceInfos",
        "supports_x_language": True,
        "method": "GET",
        "path": "/v3/payments/free-resources/query",
        "doc_url": "https://support.huaweicloud.com/api-bss/",
        "permission": "bss:freeResource:list",
        "query_fields": {
            "service_type_code_list.1": "service_type_code",
            "offset": "offset",
            "limit": "limit",
        },
        "freshness": "Resource package inventory and entitlement evidence; link to usage records before explaining deductions.",
    },
    "free-resource-usages": {
        "title": "ListFreeResourceUsages",
        "supports_x_language": True,
        "method": "GET",
        "path": "/v3/payments/free-resources/usages/query",
        "doc_url": "https://support.huaweicloud.com/api-bss/",
        "permission": "bss:freeResource:list",
        "required_query": ["free_resource_ids.1"],
        "query_fields": {
            "free_resource_ids.1": "free_resource_id",
        },
        "freshness": "Remaining quota evidence for a specific resource package.",
    },
    "free-resource-usage-records": {
        "title": "ListFreeResourcesUsageRecords",
        "method": "GET",
        "path": "/v3/payments/free-resources/usage-records/query",
        "doc_url": "https://support.huaweicloud.com/api-bss/",
        "permission": "bss:freeResource:list",
        "required_query": ["free_resource_ids.1"],
        "query_fields": {
            "free_resource_ids.1": "free_resource_id",
            "begin_time": "begin_time",
            "end_time": "end_time",
            "offset": "offset",
            "limit": "limit",
        },
        "freshness": "Deduction record windows should stay bounded; do not treat a partial window as lifetime usage.",
    },
    "coupon-change-records": {
        "title": "ListCustomerCouponChangeRecords",
        "method": "GET",
        "path": "/v2/promotions/benefits/coupon-change-records",
        "doc_url": "https://support.huaweicloud.com/api-bss/",
        "permission": "bss:coupon:list",
        "required_query": ["balance_type"],
        "query_fields": {
            "balance_type": "balance_type",
            "bill_cycle": "bill_cycle",
            "offset": "offset",
            "limit": "limit",
        },
        "freshness": "Read-only coupon ledger; it explains coupon movement, not order-level discount eligibility by itself.",
    },
    "quota-coupons": {
        "title": "ListQuotaCoupons",
        "method": "GET",
        "path": "/v2/promotions/benefits/quota-coupons",
        "doc_url": "https://support.huaweicloud.com/api-bss/",
        "permission": "bss:coupon:list",
        "query_fields": {
            "quota_ids.1": "quota_id",
            "quota_status_list.1": "status",
            "offset": "offset",
            "limit": "limit",
        },
        "freshness": "Partner coupon quota evidence; do not execute coupon issuance or recovery from this planner.",
    },
    "order-list": {
        "title": "ListCustomerOrders",
        "method": "GET",
        "path": "/v2/orders/customer-orders",
        "doc_url": "https://support.huaweicloud.com/api-bss/",
        "permission": "bss:order:list",
        "query_fields": {
            "order_id": "order_id",
            "customer_id": "customer_id",
            "service_type_code": "service_type_code",
            "offset": "offset",
            "limit": "limit",
        },
        "freshness": "Order evidence can explain purchase or refund context; it does not replace bill or cost facts.",
    },
    "order-details": {
        "title": "ShowCustomerOrderDetails",
        "supports_x_language": True,
        "method": "GET",
        "path": "/v2/orders/customer-orders/details",
        "doc_url": "https://support.huaweicloud.com/api-bss/",
        "permission": "bss:order:get",
        "required_query": ["order_id"],
        "query_fields": {
            "order_id": "order_id",
            "customer_id": "customer_id",
        },
        "freshness": "Order detail evidence; protected order and customer identifiers must stay redacted in summaries.",
    },
    "refund-order-details": {
        "title": "ShowRefundOrderDetails",
        "method": "GET",
        "path": "/v2/orders/customer-orders/refund-orders",
        "doc_url": "https://support.huaweicloud.com/api-bss/",
        "permission": "bss:order:get",
        "required_query": ["order_id"],
        "query_fields": {
            "order_id": "order_id",
            "customer_id": "customer_id",
        },
        "freshness": "Refund order evidence is read-only; do not execute unsubscribe or refund actions.",
    },
    "order-coupons": {
        "title": "ListOrderCouponsByOrderId",
        "method": "GET",
        "path": "/v2/orders/customer-orders/order-coupons",
        "doc_url": "https://support.huaweicloud.com/api-bss/",
        "permission": "bss:coupon:list",
        "required_query": ["order_id"],
        "query_fields": {"order_id": "order_id"},
        "freshness": "Available coupon evidence near an order; do not guide payment from this planner.",
    },
    "order-discounts": {
        "title": "ListOrderDiscounts",
        "method": "GET",
        "path": "/v2/orders/customer-orders/order-discounts",
        "doc_url": "https://support.huaweicloud.com/api-bss/",
        "permission": "bss:discount:list",
        "required_query": ["order_id"],
        "query_fields": {"order_id": "order_id"},
        "freshness": "Available discount evidence near an order; pricing strategy remains outside historical billing facts.",
    },
    "enterprise-organizations": {
        "title": "ListEnterpriseOrganizations",
        "method": "GET",
        "path": "/v2/enterprises/organizations",
        "doc_url": "https://support.huaweicloud.com/api-bss/",
        "permission": "bss:enterprise:list",
        "query_fields": {"offset": "offset", "limit": "limit"},
        "freshness": "Enterprise organization scope evidence; permission failure is not proof that no billing scope exists.",
    },
    "enterprise-sub-customers": {
        "title": "ListEnterpriseSubCustomers",
        "method": "GET",
        "path": "/v2/enterprises/sub-customers",
        "doc_url": "https://support.huaweicloud.com/api-bss/",
        "permission": "bss:enterprise:list",
        "query_fields": {"offset": "offset", "limit": "limit"},
        "freshness": "Enterprise sub-customer scope evidence; identifiers are protected by default.",
    },
    "subcustomer-monthly-bills": {
        "title": "ListSubcustomerMonthlyBills",
        "method": "GET",
        "path": "/v2/bills/subcustomer-bills/monthly-bills",
        "doc_url": "https://support.huaweicloud.com/api-bss/",
        "permission": "bss:subCustomerBill:list",
        "required_query": ["cycle"],
        "query_fields": {
            "cycle": "bill_cycle",
            "charge_mode": "charge_mode",
            "customer_id": "customer_id",
            "offset": "offset",
            "limit": "limit",
        },
        "freshness": "Sub-customer billing summary; confirm enterprise/partner authorization before querying.",
    },
    "subcustomer-bill-detail": {
        "title": "ListSubCustomerBillDetail",
        "supports_x_language": True,
        "method": "GET",
        "path": "/v2/bills/subcustomer-bills/detail",
        "doc_url": "https://support.huaweicloud.com/api-bss/",
        "permission": "bss:subCustomerBill:list",
        "required_query": ["bill_cycle", "customer_id"],
        "query_fields": {
            "bill_cycle": "bill_cycle",
            "customer_id": "customer_id",
            "offset": "offset",
            "limit": "limit",
        },
        "freshness": "Sub-customer detail rows require confirmed authorization and narrow output handling.",
    },
    "partner-balances": {
        "title": "ListPartnerBalances",
        "method": "GET",
        "path": "/v2/accounts/partner-accounts/balances",
        "doc_url": "https://support.huaweicloud.com/api-bss/",
        "permission": "bss:partnerAccount:list",
        "query_fields": {"offset": "offset", "limit": "limit"},
        "freshness": "Partner balance evidence; do not expand to customer data without explicit scope.",
    },
    "partner-account-change-records": {
        "title": "ListPartnerAccountChangeRecords",
        "method": "GET",
        "path": "/v2/accounts/partner-accounts/account-change-records",
        "doc_url": "https://support.huaweicloud.com/api-bss/",
        "permission": "bss:partnerAccount:list",
        "required_query": ["balance_type"],
        "query_fields": {
            "balance_type": "balance_type",
            "offset": "offset",
            "limit": "limit",
        },
        "freshness": "Partner transaction ledger; read-only and sensitive.",
    },
    "reference-service-types": {
        "title": "ListServiceTypes",
        "supports_x_language": True,
        "method": "GET",
        "path": "/v2/products/service-types",
        "doc_url": "https://support.huaweicloud.com/api-bss/",
        "permission": "bss:dictionary:list",
        "query_fields": {"offset": "offset", "limit": "limit"},
        "freshness": "Service type dictionary for translating billing service codes.",
    },
    "reference-resource-types": {
        "title": "ListResourceTypes",
        "supports_x_language": True,
        "method": "GET",
        "path": "/v2/products/resource-types",
        "doc_url": "https://support.huaweicloud.com/api-bss/",
        "permission": "bss:dictionary:list",
        "query_fields": {
            "service_type_code": "service_type_code",
            "offset": "offset",
            "limit": "limit",
        },
        "freshness": "Resource type dictionary for translating billing resource codes.",
    },
    "reference-usage-types": {
        "title": "ListUsageTypes",
        "supports_x_language": True,
        "method": "GET",
        "path": "/v2/products/usage-types",
        "doc_url": "https://support.huaweicloud.com/api-bss/",
        "permission": "bss:dictionary:list",
        "query_fields": {
            "service_type_code": "service_type_code",
            "resource_type_code": "resource_type",
            "offset": "offset",
            "limit": "limit",
        },
        "freshness": "Usage type dictionary for interpreting usage records.",
    },
    "reference-measure-units": {
        "title": "ListMeasureUnits",
        "supports_x_language": True,
        "method": "GET",
        "path": "/v2/products/measure-units",
        "doc_url": "https://support.huaweicloud.com/api-bss/",
        "permission": "bss:dictionary:list",
        "query_fields": {"offset": "offset", "limit": "limit"},
        "freshness": "Measurement unit dictionary for billing and usage displays.",
    },
    "reference-service-resources": {
        "title": "ListServiceResources",
        "supports_x_language": True,
        "method": "GET",
        "path": "/v2/products/service-resources",
        "doc_url": "https://support.huaweicloud.com/api-bss/",
        "permission": "bss:dictionary:list",
        "required_query": ["service_type_code"],
        "query_fields": {
            "service_type_code": "service_type_code",
            "offset": "offset",
            "limit": "limit",
        },
        "freshness": "Service-to-resource mapping dictionary for resolving billing dimensions.",
    },
}

OPERATION_ALIASES = {
    "balance": "account-balances",
    "balances": "account-balances",
    "account-balance": "account-balances",
    "monthly-summary": "monthly-sum",
    "statement": "billing-statements",
    "statements": "billing-statements",
    "fee-records": "billing-statements",
    "amortized-cost": "monthly-breakdown",
    "amortization": "monthly-breakdown",
    "resource-details": "resource-records",
    "resource-detail": "resource-records",
    "resource-consumption": "resource-fee-records",
    "resource-fees": "resource-fee-records",
    "resource-usage-summary": "usage-summary",
    "resource-usage": "usage-detail",
    "usage": "usage-detail",
    "on-demand-price": "on-demand-pricing",
    "ondemand-pricing": "on-demand-pricing",
    "pricing-on-demand": "on-demand-pricing",
    "period-price": "period-pricing",
    "yearly-monthly-pricing": "period-pricing",
    "pricing-period": "period-pricing",
    "free-resources": "free-resource-infos",
    "free-resource-usage": "free-resource-usages",
    "coupon-records": "coupon-change-records",
    "orders": "order-list",
    "order": "order-details",
    "refund": "refund-order-details",
    "service-types": "reference-service-types",
    "resource-types": "reference-resource-types",
    "usage-types": "reference-usage-types",
    "measure-units": "reference-measure-units",
    "service-resources": "reference-service-resources",
}
SOURCE_OPERATION_TO_PLANNER = {f"BSS/{metadata['title']}": operation for operation, metadata in OPERATIONS.items()}


def operation_supports_x_language(operation: str) -> bool:
    """Return whether a planner key or KooCLI operation accepts X-Language."""
    planner_operation = SOURCE_OPERATION_TO_PLANNER.get(
        f"BSS/{operation}",
        operation,
    )
    metadata = OPERATIONS.get(planner_operation, {})
    return bool(metadata.get("supports_x_language"))


def load_semantic_catalog(path: Path = SEMANTIC_CATALOG_PATH) -> dict[str, Any]:
    """Load the local billing semantic catalog."""
    if not path.exists():
        return {"entry_points": {}, "entities": {}}
    return hcloud_common.load_json(path)


def semantic_entry_point_names() -> list[str]:
    """Return known billing semantic entry point names."""
    return sorted(load_semantic_catalog().get("entry_points", {}))


def build_semantic_route(entry_point: str | None, catalog: dict[str, Any] | None = None) -> dict[str, Any] | None:
    """Return semantic billing route metadata for an entry point."""
    if not entry_point:
        return None
    catalog = catalog or load_semantic_catalog()
    entry = catalog.get("entry_points", {}).get(entry_point)
    if not isinstance(entry, dict):
        return {
            "entry_point": entry_point,
            "found": False,
            "error": "Unknown billing semantic entry point.",
        }

    entities = catalog.get("entities", {})
    entity_details = {name: entities.get(name, {}) for name in entry.get("ontology_entities", [])}
    source_operations = sorted({operation for details in entity_details.values() for operation in details.get("source_operations", [])})
    supported_operations = sorted(
        set(entry.get("supported_planner_operations", []))
        | {SOURCE_OPERATION_TO_PLANNER[operation] for operation in source_operations if operation in SOURCE_OPERATION_TO_PLANNER}
    )
    supported_source_operations = sorted(operation for operation in source_operations if operation in SOURCE_OPERATION_TO_PLANNER)
    return {
        "entry_point": entry_point,
        "found": True,
        "required_context": entry.get("required_context", {}),
        "triggers": entry.get("triggers", []),
        "money_basis": entry.get("required_context", {}).get("money_basis", []),
        "ontology_entities": entry.get("ontology_entities", []),
        "entity_details": entity_details,
        "source_operations": source_operations,
        "supported_planner_operations": supported_operations,
        "supported_source_operations": supported_source_operations,
        "unsupported_source_operations": [
            operation for operation in source_operations if operation not in set(supported_source_operations)
        ],
    }


def parse_key_values(values: list[str]) -> dict[str, str]:
    """Parse repeated key=value CLI values into a dictionary."""
    parsed: dict[str, str] = {}
    for item in values:
        if "=" not in item:
            raise ValueError(f"Expected key=value, got {item!r}.")
        key, value = item.split("=", 1)
        if not key:
            raise ValueError(f"Expected non-empty key in {item!r}.")
        parsed[key] = value
    return parsed


def parse_filters(values: list[str]) -> list[dict[str, Any]]:
    """Parse cost-data filters in KEY=value1,value2 form."""
    filters: list[dict[str, Any]] = []
    for item in values:
        if "=" not in item:
            raise ValueError(f"Expected KEY=value1,value2 filter, got {item!r}.")
        key, raw_values = item.split("=", 1)
        if key == "ENTERPRISE_PROJECT":
            raise ValueError("Use ENTERPRISE_PROJECT_ID for ListCosts enterprise-project filtering, not ENTERPRISE_PROJECT.")
        entries = [entry.strip() for entry in raw_values.split(",") if entry.strip()]
        if not key or not entries:
            raise ValueError(f"Expected non-empty key and value list in filter {item!r}.")
        filters.append(
            {
                "operator": 0,
                "filter_factor": {
                    "key": key,
                    "value": entries,
                },
            }
        )
    return filters


def optional_fields(**values: Any) -> dict[str, Any]:
    """Return fields whose values are not empty."""
    return {key: value for key, value in values.items() if value not in (None, "", [])}


def validate_required_fields(operation: str, fields: list[str], values: dict[str, Any]) -> list[str]:
    """Return validation errors for missing required query or body fields."""
    return [f"Missing required {operation} field: {field}." for field in fields if values.get(field) in (None, "", [])]


def build_generic_query(args: argparse.Namespace, metadata: dict[str, Any], operation: str) -> tuple[dict[str, Any], list[str]]:
    """Build query parameters for reviewed read-only BSS List*/Show* operations."""
    query_fields = metadata.get("query_fields", {})
    query = optional_fields(
        **{param_name: getattr(args, attr_name) for param_name, attr_name in query_fields.items() if hasattr(args, attr_name)}
    )
    return query, []


def load_body_override(args: argparse.Namespace) -> tuple[dict[str, Any] | None, str | None, list[str]]:
    """Return an explicit JSON body override when supplied."""
    if args.body_json_file and args.body_json_text:
        return None, None, ["Use either --body-json-file or --body-json-text, not both."]
    if args.body_json_text:
        try:
            body = json.loads(args.body_json_text)
        except json.JSONDecodeError as exc:
            return None, "body-json-text", [f"Invalid --body-json-text: {exc}"]
        if not isinstance(body, dict):
            return None, "body-json-text", ["--body-json-text must decode to a JSON object."]
        return body, "body-json-text", []
    if args.body_json_file:
        try:
            body = json.loads(Path(args.body_json_file).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            return None, "body-json-file", [f"Cannot read --body-json-file as JSON object: {exc}"]
        if not isinstance(body, dict):
            return None, "body-json-file", ["--body-json-file must decode to a JSON object."]
        return body, "body-json-file", []
    return None, None, []


def validate_cycle(field: str, value: str | None) -> list[str]:
    """Return validation errors for a YYYY-MM billing cycle field."""
    if not value:
        return [f"Missing required {field}."]
    if not BILL_CYCLE_RE.match(value):
        return [f"{field} must use YYYY-MM format."]
    return []


def build_monthly_sum_query(args: argparse.Namespace) -> tuple[dict[str, Any], list[str]]:
    """Build ShowCustomerMonthlySum query parameters."""
    errors = validate_cycle("bill_cycle", args.bill_cycle)
    if args.enterprise_project_id:
        errors.append(
            "ShowCustomerMonthlySum cannot filter by enterprise_project_id; use operation=cost-data with filter ENTERPRISE_PROJECT_ID=<id>."
        )
    query = optional_fields(
        bill_cycle=args.bill_cycle,
        service_type_code=args.service_type_code,
        method=args.method,
        sub_customer_id=args.sub_customer_id,
        offset=args.offset,
        limit=args.limit,
    )
    return query, errors


def build_cost_data_body(args: argparse.Namespace) -> tuple[dict[str, Any] | None, str, list[str]]:
    """Build or load a ListCosts request body."""
    body, source, errors = load_body_override(args)
    if body is not None or errors:
        return body, source or "generated", errors

    missing = [name for name in ("begin_time", "end_time") if not getattr(args, name)]
    if missing:
        return None, "generated", [f"Missing required cost-data field: {', '.join(missing)}."]

    body = {
        "amount_type": args.amount_type,
        "offset": args.offset,
        "cost_type": args.cost_type,
        "limit": args.limit,
        "groupby": [{"type": "dimension", "key": item} for item in args.group_by],
        "time_condition": {
            "time_measure_id": args.time_measure_id,
            "begin_time": args.begin_time,
            "end_time": args.end_time,
        },
    }
    try:
        filters = parse_filters(args.filter)
    except ValueError as exc:
        return None, "generated", [str(exc)]
    if args.region_code:
        existing_region_filters = [
            item
            for item in filters
            if item.get("filter_factor", {}).get("key") == "REGION_CODE"
        ]
        if existing_region_filters:
            values = existing_region_filters[0]["filter_factor"].get("value", [])
            if values != [args.region_code]:
                return None, "generated", [
                    "region_code conflicts with the explicit REGION_CODE cost-data filter."
                ]
        else:
            filters.append(
                {
                    "operator": 0,
                    "filter_factor": {
                        "key": "REGION_CODE",
                        "value": [args.region_code],
                    },
                }
            )
    if filters:
        body["filters"] = filters
    return body, "generated", []


def build_resource_records_body(args: argparse.Namespace) -> tuple[dict[str, Any] | None, str, list[str]]:
    """Build or load a resource detail request body."""
    body, source, errors = load_body_override(args)
    if body is not None or errors:
        return body, source or "generated", errors

    errors = validate_cycle("cycle", args.bill_cycle)
    body = optional_fields(
        cycle=args.bill_cycle,
        cloud_service_type=args.service_type_code,
        resource_type=args.resource_type,
        region=args.region_code,
        res_instance_id=args.resource_id,
        charge_mode=args.charge_mode,
        bill_type=args.bill_type,
        enterprise_project_id=args.enterprise_project_id,
        include_zero_record=args.include_zero_record,
        method=args.method,
        sub_customer_id=args.sub_customer_id,
        offset=args.offset,
        limit=args.limit,
    )
    return body, "generated", errors


def build_resource_fee_query(args: argparse.Namespace) -> tuple[dict[str, Any], list[str]]:
    """Build ListCustomerselfResourceRecords query parameters."""
    errors = validate_cycle("cycle", args.bill_cycle)
    query = optional_fields(
        cycle=args.bill_cycle,
        charge_mode=args.charge_mode,
        cloud_service_type=args.service_type_code,
        region=args.region_code,
        bill_type=args.bill_type,
        res_instance_id=args.resource_id,
        enterprise_project_id=args.enterprise_project_id,
        method=args.method,
        sub_customer_id=args.sub_customer_id,
        bill_date_begin=args.begin_time,
        bill_date_end=args.end_time,
        statistic_type=args.statistic_type,
        offset=args.offset,
        limit=args.limit,
    )
    return query, errors


def value_list(value: Any) -> list[Any]:
    """Return a CLI or namespace scalar as a list."""
    if value in (None, "", []):
        return []
    if isinstance(value, list):
        return value
    return [value]


def expand_counted_values(values: list[Any], count: int, field_name: str, errors: list[str]) -> list[Any]:
    """Expand one value to match product count or report a count mismatch."""
    if not values:
        return [None] * count
    if len(values) == 1:
        return values * count
    if len(values) != count:
        errors.append(f"--{field_name} count must be 1 or match --resource-spec count ({count}).")
        return values[:count] + [None] * max(count - len(values), 0)
    return values


def pricing_spec_with_suffix(spec: str, suffix: str | None) -> str:
    """Return a pricing resource spec with a safe default OS suffix when needed."""
    if not suffix:
        return spec
    if suffix == ".linux" and spec.endswith((".linux", ".win")):
        return spec
    if spec.endswith(suffix):
        return spec
    return f"{spec}{suffix}"


def normalize_period_type(value: Any) -> int | None:
    """Return the BSS period_type integer for a CLI value."""
    key = str(value).strip().lower()
    return PERIOD_TYPE_ALIASES.get(key)


def pricing_body_override(args: argparse.Namespace) -> tuple[dict[str, Any] | None, str | None, list[str]]:
    """Return an explicit pricing JSON body override when supplied."""
    return load_body_override(args)


def pricing_common_product_values(
    args: argparse.Namespace,
    presets: dict[str, dict[str, Any]],
    operation: str,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[str]]:
    """Build common pricing product fields from a reviewed preset."""
    errors: list[str] = []
    project_id = getattr(args, "project_id", None)
    preset_name = getattr(args, "pricing_preset", None)
    if not project_id:
        errors.append(f"Missing required {operation} field: project_id.")
    if not preset_name:
        errors.append(f"Missing required {operation} field: pricing_preset.")
        return {}, [], errors
    preset = presets.get(preset_name)
    if preset is None:
        errors.append(f"Unsupported {operation} pricing preset: {preset_name}. Supported presets: {', '.join(sorted(presets))}.")
        return {}, [], errors

    raw_specs = [str(item) for item in value_list(getattr(args, "resource_spec", None)) if str(item)]
    if not raw_specs:
        errors.append(f"Missing required {operation} field: resource_spec.")
        return {"project_id": project_id, "preset": preset}, [], errors

    specs = [pricing_spec_with_suffix(spec, preset.get("spec_suffix")) for spec in raw_specs]
    count = len(specs)
    resource_sizes = value_list(getattr(args, "resource_size", None))
    size_measure_ids = value_list(getattr(args, "size_measure_id", None))
    if not resource_sizes and preset.get("need_resource_size"):
        resource_sizes = [preset["default_size"]]
    if not size_measure_ids and preset.get("need_resource_size"):
        size_measure_ids = [preset["default_size_measure_id"]]
    if resource_sizes and not size_measure_ids:
        errors.append(f"{operation} requires --size-measure-id when --resource-size is provided.")
    if size_measure_ids and not resource_sizes:
        errors.append(f"{operation} requires --resource-size when --size-measure-id is provided.")

    expanded_sizes = expand_counted_values(resource_sizes, count, "resource-size", errors)
    expanded_size_measure_ids = expand_counted_values(size_measure_ids, count, "size-measure-id", errors)
    subscription_nums = expand_counted_values(
        value_list(getattr(args, "subscription_num", None)) or [1],
        count,
        "subscription-num",
        errors,
    )
    region = getattr(args, "pricing_region", None) or getattr(args, "region_code", None) or PRICING_REGION_DEFAULT
    available_zone = getattr(args, "available_zone", None)

    products = []
    for index, spec in enumerate(specs, start=1):
        product = optional_fields(
            id=str(index),
            cloud_service_type=preset["cloud_service_type"],
            resource_type=preset["resource_type"],
            resource_spec=spec,
            region=region,
            available_zone=available_zone,
            resource_size=expanded_sizes[index - 1],
            size_measure_id=expanded_size_measure_ids[index - 1],
            subscription_num=subscription_nums[index - 1],
        )
        products.append(product)
    context = {
        "project_id": project_id,
        "preset": preset,
        "preset_name": preset_name,
        "product_count": count,
    }
    return context, products, errors


def build_on_demand_pricing_body(args: argparse.Namespace) -> tuple[dict[str, Any] | None, str, list[str]]:
    """Build or load a ListOnDemandResourceRatings request body."""
    body, source, errors = pricing_body_override(args)
    if body is not None or errors:
        return body, source or "generated", errors

    context, products, errors = pricing_common_product_values(args, ON_DEMAND_PRICING_PRESETS, "on-demand-pricing")
    if products:
        usage_values = expand_counted_values(
            value_list(getattr(args, "usage_value", None)) or [1],
            len(products),
            "usage-value",
            errors,
        )
        preset = context["preset"]
        for index, product in enumerate(products):
            product["usage_factor"] = preset.get("usage_factor", "Duration")
            product["usage_value"] = usage_values[index]
            product["usage_measure_id"] = preset["usage_measure_id"]

    return (
        {
            "project_id": context.get("project_id"),
            "inquiry_precision": getattr(args, "inquiry_precision", None) if getattr(args, "inquiry_precision", None) is not None else 1,
            "product_infos": products,
        },
        "generated",
        errors,
    )


def build_period_pricing_body(args: argparse.Namespace) -> tuple[dict[str, Any] | None, str, list[str]]:
    """Build or load a ListRateOnPeriodDetail request body."""
    body, source, errors = pricing_body_override(args)
    if body is not None or errors:
        return body, source or "generated", errors

    context, products, errors = pricing_common_product_values(args, PERIOD_PRICING_PRESETS, "period-pricing")
    if products:
        period_types = value_list(getattr(args, "period_type", None)) or ["month"]
        normalized_period_types: list[int] = []
        for item in period_types:
            normalized = normalize_period_type(item)
            if normalized is None:
                errors.append("Invalid --period-type; supported values are day/month/year/hour, 天/月/年/小时, or 0/2/3/4.")
            else:
                normalized_period_types.append(normalized)
        expanded_period_types = expand_counted_values(normalized_period_types, len(products), "period-type", errors)
        period_nums = expand_counted_values(
            value_list(getattr(args, "period_num", None)) or [1],
            len(products),
            "period-num",
            errors,
        )
        fee_installment_mode = getattr(args, "fee_installment_mode", None)
        for index, product in enumerate(products):
            product["period_type"] = expanded_period_types[index]
            product["period_num"] = period_nums[index]
            if fee_installment_mode:
                product["fee_installment_mode"] = fee_installment_mode

    return (
        {
            "project_id": context.get("project_id"),
            "product_infos": products,
        },
        "generated",
        errors,
    )


def build_url(endpoint_base: str, path: str, query: dict[str, Any]) -> str:
    """Return a request URL with encoded query parameters when present."""
    base = endpoint_base.rstrip("/")
    if not query:
        return f"{base}{path}"
    return f"{base}{path}?{urlencode(query)}"


def cli_defaults(catalog: dict[str, Any]) -> dict[str, str]:
    """Return fixed BSS KooCLI defaults."""
    defaults = catalog.get("bss_cli_defaults", {})
    legacy_language = str(defaults.get("cli_lang") or "")
    x_language = str(defaults.get("x_language") or "")
    if not x_language and legacy_language:
        x_language = {"cn": "zh_CN", "en": "en_US"}.get(legacy_language, legacy_language)
    return {
        "cli_region": str(defaults.get("cli_region") or BSS_CLI_REGION),
        "x_language": x_language or BSS_X_LANGUAGE,
    }


def operation_name(raw_operation: str) -> str:
    """Resolve a user-facing operation name or alias."""
    return OPERATION_ALIASES.get(raw_operation, raw_operation)


def scalar_cli_value(value: Any) -> str:
    """Return a stable KooCLI scalar argument value."""
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def flatten_cli_args(prefix: str, value: Any) -> list[str]:
    """Flatten a JSON-like body into KooCLI dot-notation arguments."""
    if value in (None, "", []):
        return []
    if isinstance(value, dict):
        args: list[str] = []
        for key, child in value.items():
            args.extend(flatten_cli_args(f"{prefix}.{key}", child))
        return args
    if isinstance(value, list):
        args = []
        for index, child in enumerate(value, start=1):
            args.extend(flatten_cli_args(f"{prefix}.{index}", child))
        return args
    return [f"--{prefix}={scalar_cli_value(value)}"]


def hcloud_safe_exec_command(
    operation: str,
    args: list[str],
    defaults: dict[str, str],
    *,
    x_language: str | None,
) -> list[str]:
    """Return a safe_exec wrapped read-only BSS command."""
    command = hcloud_common.safe_exec_command_prefix() + [
        "--service",
        "BSS",
        "--operation",
        operation,
        "--arg=--cli-output=json",
        "--expect-json",
    ]
    command.append(f"--arg=--cli-region={defaults['cli_region']}")
    if x_language:
        command.append(f"--arg=--X-Language={x_language}")
    command.extend(f"--arg={item}" for item in args)
    return command


def build_hcloud_command_plan(
    operation: str,
    metadata: dict[str, Any],
    request_spec: dict[str, Any],
    body_source: str | None,
    defaults: dict[str, str],
) -> dict[str, Any]:
    """Return a reviewed hcloud read-only command plan or a blocked reason."""
    blocked_reasons: list[str] = []
    cli_args: list[str] = []

    if metadata["method"] == "POST" and body_source != "generated":
        blocked_reasons.append(
            "Explicit JSON bodies are kept as request specs; this planner only maps generated safe fields to KooCLI dot notation."
        )

    for key, value in request_spec.get("query", {}).items():
        if value not in (None, "", []):
            cli_args.append(f"--{key}={scalar_cli_value(value)}")
    body = request_spec.get("body")
    if body and not blocked_reasons:
        for key, value in body.items():
            cli_args.extend(flatten_cli_args(key, value))

    headers = request_spec.get("headers", {})
    x_language = headers.get("X-Language") if isinstance(headers, dict) else None
    safe_exec_command = (
        hcloud_safe_exec_command(metadata["title"], cli_args, defaults, x_language=x_language) if not blocked_reasons else None
    )
    return {
        "supported": not blocked_reasons,
        "blocked_reasons": blocked_reasons,
        "read_only": True,
        "service": "BSS",
        "operation": metadata["title"],
        "operation_capabilities": {
            "x_language_header": operation_supports_x_language(operation),
        },
        "cli_defaults": defaults,
        "hcloud_args": cli_args,
        "safe_exec_command": safe_exec_command,
        "execution_requires_user_approval": True,
        "sensitivity": {
            "level": "high",
            "reason": "Billing data can expose account identifiers, resource identifiers, order data, and spend.",
        },
        "output_boundary": {
            "summarize_by_default": True,
            "raw_output_allowed_only_after_scope_confirmation": True,
            "protected_identifiers": load_semantic_catalog().get("protected_identifiers", []),
        },
    }


def pagination_scope(query: dict[str, Any], body: dict[str, Any] | None) -> dict[str, Any]:
    """Return pagination completeness metadata for billing queries."""
    source = body if body is not None else query
    offset = source.get("offset") if isinstance(source, dict) else None
    limit = source.get("limit") if isinstance(source, dict) else None
    return {
        "offset": offset,
        "limit": limit,
        "complete_result_claim_allowed": False,
        "reason": "A single billing page is partial until total_count and all intended pages are reviewed.",
    }


def billing_period_fields(query: dict[str, Any], body: dict[str, Any] | None) -> list[str]:
    """Return fields that define the billing period or time window."""
    fields: list[str] = []
    for key in ("bill_cycle", "cycle", "shared_month", "begin_time", "end_time", "bill_date_begin", "bill_date_end"):
        if query.get(key) not in (None, "", []):
            fields.append(key)
    if isinstance(body, dict):
        for key in ("cycle", "bill_date_begin", "bill_date_end"):
            if body.get(key) not in (None, "", []):
                fields.append(key)
        time_condition = body.get("time_condition")
        if isinstance(time_condition, dict):
            for key in ("begin_time", "end_time", "time_measure_id"):
                if time_condition.get(key) not in (None, "", []):
                    fields.append(f"time_condition.{key}")
    return sorted(set(fields))


def scope_fields(query: dict[str, Any], body: dict[str, Any] | None) -> list[str]:
    """Return fields that narrow the account, service, region, or resource scope."""
    known_scope_keys = {
        "method",
        "sub_customer_id",
        "enterprise_project_id",
        "service_type_code",
        "cloud_service_type",
        "resource_type",
        "resource_type_code",
        "region",
        "region_code",
        "res_instance_id",
        "resource_id",
        "usage_type",
        "order_id",
        "customer_id",
        "balance_type",
        "status",
        "free_resource_ids.1",
        "quota_ids.1",
        "quota_status_list.1",
        "service_type_code_list.1",
        "charge_mode",
        "bill_type",
        "project_id",
        "resource_spec",
        "available_zone",
        "usage_factor",
        "period_type",
    }
    fields = [key for key, value in query.items() if key in known_scope_keys and value not in (None, "", [])]
    if isinstance(body, dict):
        fields.extend(key for key, value in body.items() if key in known_scope_keys and value not in (None, "", []))
        for product in body.get("product_infos", []) if isinstance(body.get("product_infos"), list) else []:
            if not isinstance(product, dict):
                continue
            for key in (
                "cloud_service_type",
                "resource_type",
                "resource_spec",
                "region",
                "available_zone",
                "usage_factor",
                "period_type",
            ):
                if product.get(key) not in (None, "", []):
                    fields.append(f"product_infos:{key}")
        for group in body.get("groupby", []) if isinstance(body.get("groupby"), list) else []:
            if isinstance(group, dict) and group.get("key"):
                fields.append(f"groupby:{group['key']}")
        for item in body.get("filters", []) if isinstance(body.get("filters"), list) else []:
            factor = item.get("filter_factor") if isinstance(item, dict) else None
            if isinstance(factor, dict) and factor.get("key"):
                fields.append(f"filter:{factor['key']}")
    return sorted(set(fields))


def semantic_grains(semantic_route: dict[str, Any] | None) -> list[str]:
    """Return grain descriptions from the selected semantic route."""
    if not semantic_route or not semantic_route.get("found"):
        return []
    grains = [str(details.get("grain")) for details in semantic_route.get("entity_details", {}).values() if details.get("grain")]
    return sorted(set(grains))


def billing_semantic_discipline(
    metadata: dict[str, Any],
    semantic_route: dict[str, Any] | None,
    query: dict[str, Any],
    body: dict[str, Any] | None,
) -> dict[str, Any]:
    """Return the billing answer discipline tuple required before summaries."""
    route_context = semantic_route.get("required_context", {}) if semantic_route and semantic_route.get("found") else {}
    return {
        "required_tuple": ["fact", "grain", "money_basis", "scope", "billing_period"],
        "selected_fact": metadata["title"],
        "semantic_entry_point": semantic_route.get("entry_point") if semantic_route else None,
        "grain_candidates": semantic_grains(semantic_route),
        "money_basis": route_context.get("money_basis", []),
        "scope_fields": scope_fields(query, body),
        "billing_period_fields": billing_period_fields(query, body),
        "non_additive_rule": (
            "Do not add or compare billing outputs unless fact, grain, money_basis, scope, and billing_period are compatible."
        ),
        "separate_fact_examples": [
            "monthly_summary",
            "resource_fee_record",
            "resource_detail",
            "cost_analysis",
            "order_or_refund",
            "coupon_or_stored_value",
        ],
    }


def build_request_spec(args: argparse.Namespace) -> dict[str, Any]:
    """Build a planner-only billing/cost API request specification."""
    operation = operation_name(args.operation or "monthly-sum")
    metadata = OPERATIONS[operation]
    semantic_catalog = load_semantic_catalog()
    defaults = cli_defaults(semantic_catalog)
    semantic_route = build_semantic_route(getattr(args, "entry_point", None), semantic_catalog)
    supports_x_language = operation_supports_x_language(operation)
    query: dict[str, Any] = {}
    body: dict[str, Any] | None = None
    body_source: str | None = None
    errors: list[str] = []

    try:
        raw_query = parse_key_values(args.query)
        if operation == "monthly-sum":
            query, errors = build_monthly_sum_query(args)
        elif operation == "cost-data":
            body, body_source, errors = build_cost_data_body(args)
        elif operation == "resource-records":
            body, body_source, errors = build_resource_records_body(args)
        elif operation == "resource-fee-records":
            query, errors = build_resource_fee_query(args)
        elif operation == "on-demand-pricing":
            body, body_source, errors = build_on_demand_pricing_body(args)
        elif operation == "period-pricing":
            body, body_source, errors = build_period_pricing_body(args)
        else:
            query, errors = build_generic_query(args, metadata, operation)
        query.update(raw_query)
        if query and metadata.get("required_query"):
            errors.extend(
                error for error in validate_required_fields(operation, metadata.get("required_query", []), query) if error not in errors
            )
    except ValueError as exc:
        errors = [str(exc)]

    if supports_x_language and args.language not in SUPPORTED_X_LANGUAGES:
        errors.append(f"Unsupported X-Language value {args.language!r}; expected one of {sorted(SUPPORTED_X_LANGUAGES)}.")

    request_spec = {
        "method": metadata["method"],
        "endpoint_base": args.endpoint_base.rstrip("/"),
        "path": metadata["path"],
        "url": build_url(args.endpoint_base, metadata["path"], query),
        "headers": optional_fields(
            **{
                "Content-Type": "application/json",
                "X-Language": args.language if supports_x_language else None,
            }
        ),
        "query": query,
        "body": hcloud_common.redact_json(body, set()) if body is not None else None,
        "body_source": body_source,
        "requires_auth": "customer AK/SK signature or customer token; credentials are intentionally not accepted by this planner.",
    }
    command_plan = build_hcloud_command_plan(operation, metadata, request_spec, body_source, defaults)

    warnings = [
        "This script does not sign or send HTTP requests.",
        "Billing and cost data can contain account, resource, and spend-sensitive information; keep output scope narrow.",
        "Do not infer spend from resource inventory when billing APIs are unavailable.",
        "BSS hcloud templates must use --cli-region=cn-north-1. Add --X-Language only when operation_capabilities.x_language_header is true; --cli-lang is profile-only and is never an operation argument.",
        "Do not claim full-account totals from one page unless pagination has been completed and checked.",
    ]
    if semantic_route and semantic_route.get("found") and operation not in semantic_route.get("supported_planner_operations", []):
        warnings.append(
            "The selected operation is not the first-fit planner operation for the semantic entry point; review semantic_route.supported_planner_operations."
        )

    return {
        "success": not errors,
        "mode": "plan",
        "planning_only": True,
        "operation": operation,
        "title": metadata["title"],
        "semantic_route": semantic_route,
        "billing_semantic_discipline": billing_semantic_discipline(metadata, semantic_route, query, body),
        "bss_cli_defaults": defaults,
        "request_spec": request_spec,
        "hcloud_command_plan": command_plan,
        "pagination_scope": pagination_scope(query, body),
        "validation": {
            "errors": errors,
            "warnings": warnings,
        },
        "execution_supported": bool(command_plan.get("supported")) and not errors,
        "official_docs": {
            "url": metadata["doc_url"],
            "permission": metadata["permission"],
            "freshness": metadata["freshness"],
        },
        "next_steps": [
            "Confirm the account scope, enterprise project scope, time range, and permission boundary with the user.",
            "If live billing access is approved, run only the generated hcloud_command_plan.safe_exec_command and summarize the redacted result.",
            "Summarize billing output instead of pasting full raw records unless the user explicitly asks for the raw data scope.",
        ],
    }


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--operation", choices=sorted(list(OPERATIONS) + list(OPERATION_ALIASES)))
    parser.add_argument("--entry-point", choices=semantic_entry_point_names(), help="Optional billing semantic entry point.")
    parser.add_argument("--endpoint-base", default=DEFAULT_ENDPOINT_BASE, help="Billing endpoint base URL.")
    parser.add_argument(
        "--language",
        default="zh_CN",
        help="X-Language value for operations that support the header.",
    )
    parser.add_argument("--bill-cycle", help="Billing cycle in YYYY-MM format.")
    parser.add_argument("--shared-month", help="Shared month for monthly amortization in YYYY-MM format.")
    parser.add_argument("--begin-time", help="Cost begin_time or fee bill_date_begin.")
    parser.add_argument("--end-time", help="Cost end_time or fee bill_date_end.")
    parser.add_argument("--time-measure-id", type=int, default=1, choices=[1, 2], help="Cost time unit: 1 day, 2 month.")
    parser.add_argument("--group-by", action="append", default=None, help="Cost groupby dimension key.")
    parser.add_argument("--filter", action="append", default=[], help="Cost filter as KEY=value1,value2. Can be repeated.")
    parser.add_argument("--cost-type", default="ORIGINAL_COST", choices=["ORIGINAL_COST", "AMORTIZED_COST"])
    parser.add_argument("--amount-type", default="PAYMENT_AMOUNT", choices=["PAYMENT_AMOUNT", "NET_AMOUNT"])
    parser.add_argument("--project-id", help="Project ID for BSS pricing inquiries.")
    parser.add_argument("--service-type-code", help="Cloud service type code.")
    parser.add_argument("--resource-type", help="Resource type code.")
    parser.add_argument("--resource-spec", action="append", help="Pricing resource spec. Can be repeated.")
    parser.add_argument("--usage-type", help="Usage type code, for example 95Peak or bandwidth95peak.")
    parser.add_argument("--region-code", help="Billing region code filter, for example ap-southeast-1.")
    parser.add_argument("--pricing-region", help=f"Pricing SKU region, default {PRICING_REGION_DEFAULT}.")
    parser.add_argument("--available-zone", help="Pricing available zone filter.")
    parser.add_argument("--pricing-preset", help="Pricing preset such as ecs, evs, eip-bw, eip-flow, eip-ip, obs, sfs, nat, elb, or bms.")
    parser.add_argument("--resource-size", type=int, action="append", help="Pricing resource size. Can be repeated.")
    parser.add_argument(
        "--size-measure-id", type=int, action="append", help="Pricing size measure ID, for example 15 Mbps or 17 GB. Can be repeated."
    )
    parser.add_argument("--usage-value", type=float, action="append", help="On-demand pricing usage value. Defaults to 1.")
    parser.add_argument("--subscription-num", type=int, action="append", help="Pricing subscription quantity. Defaults to 1.")
    parser.add_argument("--inquiry-precision", type=int, default=1, choices=[0, 1], help="On-demand pricing precision mode.")
    parser.add_argument("--period-type", action="append", help="Period pricing type: day/month/year/hour, 天/月/年/小时, or 0/2/3/4.")
    parser.add_argument("--period-num", type=int, action="append", help="Period pricing duration count. Defaults to 1.")
    parser.add_argument(
        "--fee-installment-mode", choices=["HALF_PAY", "ZERO_PAY", "NA"], help="CloudPond-style fee installment mode when supported."
    )
    parser.add_argument("--resource-id", help="Resource instance ID filter.")
    parser.add_argument("--enterprise-project-id", help="Enterprise project ID filter.")
    parser.add_argument("--charge-mode", help="Charging mode filter.")
    parser.add_argument("--bill-type", type=int, help="Bill type filter.")
    parser.add_argument("--method", help="Query scope, for example oneself, sub_customer, or all.")
    parser.add_argument("--sub-customer-id", help="Sub-customer account ID for enterprise master-account queries.")
    parser.add_argument("--customer-id", help="Customer or sub-customer ID for explicitly scoped BSS queries.")
    parser.add_argument("--order-id", help="Order ID for read-only order evidence queries.")
    parser.add_argument("--balance-type", help="Balance type for account, partner, or coupon transaction records.")
    parser.add_argument("--status", help="Status filter for stored-value cards or coupon quotas.")
    parser.add_argument("--free-resource-id", help="Free resource package ID for usage and deduction queries.")
    parser.add_argument("--quota-id", help="Coupon quota ID for quota coupon queries.")
    parser.add_argument("--include-zero-record", help="Whether to include zero records for resource detail queries.")
    parser.add_argument("--statistic-type", type=int, help="Resource fee record statistic type.")
    parser.add_argument("--offset", type=int, default=0, help="Pagination offset.")
    parser.add_argument("--limit", type=int, default=10, help="Pagination limit.")
    parser.add_argument("--query", action="append", default=[], help="Additional raw query key=value. Can be repeated.")
    parser.add_argument("--body-json-file", help="Explicit JSON request body file for POST operations.")
    parser.add_argument("--body-json-text", help="Explicit JSON request body text for POST operations.")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")
    args = parser.parse_args()
    if args.operation is None and args.entry_point:
        route = build_semantic_route(args.entry_point)
        supported = route.get("supported_planner_operations", []) if route else []
        args.operation = supported[0] if supported else "monthly-sum"
    args.operation = operation_name(args.operation or "monthly-sum")
    if args.offset < 0:
        parser.error("--offset must be greater than or equal to 0.")
    if args.limit < 1:
        parser.error("--limit must be greater than 0.")
    args.group_by = args.group_by or ["CLOUD_SERVICE_TYPE"]
    return args


def main() -> int:
    """Build the billing/cost request spec."""
    args = parse_args()
    result = build_request_spec(args)
    hcloud_common.emit_json(result, pretty=args.pretty)
    return 0 if result["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
