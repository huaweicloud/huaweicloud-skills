#!/usr/bin/env python3
"""Summarize and redact Huawei Cloud BSS/Billing query results."""

from __future__ import annotations

import argparse
import hashlib
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

import hcloud_common

SEMANTIC_CATALOG_PATH = hcloud_common.REFERENCES_DIR / "billing" / "semantic-catalog.json"
MONEY_FIELD_HINTS = (
    "amount",
    "cost",
    "debt",
    "cash",
    "credit",
    "coupon",
    "official",
    "discount",
)
DEFAULT_PROTECTED_KEYS = {
    "account_id",
    "account_name",
    "customer_id",
    "customer_name",
    "enterprise_project_id",
    "sub_customer_id",
    "indirect_partner_id",
    "associated_account",
    "payer_account_id",
    "resource_tag",
    "cost_unit",
    "resource_id",
    "res_instance_id",
    "resource_instance_id",
    "order_id",
    "trade_id",
    "coupon_id",
    "quota_id",
    "card_id",
}
MAX_DIMENSION_AGGREGATES = 50
MAX_DIMENSIONS_PER_AGGREGATE = 8
MAX_SUMMARY_SCALAR_CHARS = 256


def load_semantic_catalog(path: Path = SEMANTIC_CATALOG_PATH) -> dict[str, Any]:
    """Load billing semantic catalog metadata."""
    if not path.exists():
        return {"protected_identifiers": []}
    return hcloud_common.load_json(path)


def protected_keys(catalog: dict[str, Any] | None = None) -> set[str]:
    """Return field names that should be redacted in billing output."""
    catalog = catalog or load_semantic_catalog()
    return DEFAULT_PROTECTED_KEYS | {str(item) for item in catalog.get("protected_identifiers", [])}


def stable_redaction(value: Any) -> str:
    """Return a stable non-reversible redaction marker for one identifier."""
    text = str(value)
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:8]
    return f"***:{digest}"


def redact_protected_identifiers(value: Any, keys: set[str]) -> Any:
    """Recursively redact protected billing identifiers by key name."""
    if isinstance(value, dict):
        redacted = {}
        dimension_key = str(value.get("key") or "").strip().lower()
        for key, child in value.items():
            if (
                key in keys
                or (key == "value" and dimension_key in keys)
            ) and child not in (None, "", []):
                redacted[key] = stable_redaction(child)
            else:
                redacted[key] = redact_protected_identifiers(child, keys)
        return redacted
    if isinstance(value, list):
        return [redact_protected_identifiers(item, keys) for item in value]
    return value


def unwrap_safe_exec_result(value: Any) -> tuple[Any, dict[str, Any] | None]:
    """Return parsed BSS payload from a safe_exec result or direct JSON value."""
    if isinstance(value, dict) and "parsed_json" in value and ("service" in value or "operation" in value):
        return value.get("parsed_json"), value
    return value, None


def iter_record_lists(value: Any) -> list[tuple[str, list[Any]]]:
    """Return top-level list fields that look like result records."""
    if not isinstance(value, dict):
        return []
    lists = []
    for key, child in value.items():
        if isinstance(child, list):
            lists.append((key, child))
    return lists


def collect_field_names(records: list[Any]) -> list[str]:
    """Return stable field names seen in a record list."""
    names: set[str] = set()
    for record in records:
        if isinstance(record, dict):
            names.update(str(key) for key in record)
    return sorted(names)


def collect_money_fields(value: Any) -> list[str]:
    """Return top-level fields that appear to contain money amounts."""
    if not isinstance(value, dict):
        return []
    fields = []
    for key in value:
        lowered = str(key).lower()
        if any(hint in lowered for hint in MONEY_FIELD_HINTS):
            fields.append(str(key))
    return sorted(fields)


def bounded_summary_scalar(value: Any) -> Any | None:
    """Return one bounded scalar suitable for an agent-facing billing summary."""
    if value is None or isinstance(value, (dict, list)):
        return None
    if isinstance(value, (bool, int, float)):
        return value
    text = str(value)
    if len(text) > MAX_SUMMARY_SCALAR_CHARS:
        return text[:MAX_SUMMARY_SCALAR_CHARS] + "…"
    return text


def monetary_totals(payload: Any) -> dict[str, Any]:
    """Return bounded top-level monetary totals without exposing billing rows."""
    if not isinstance(payload, dict):
        return {}
    totals: dict[str, Any] = {}
    for key in collect_money_fields(payload):
        scalar = bounded_summary_scalar(payload.get(key))
        if scalar is not None:
            totals[key] = scalar
    return totals


def dimension_aggregates(payload: Any) -> list[dict[str, Any]]:
    """Return bounded cost-analysis dimension groups and their aggregate amounts."""
    aggregates: list[dict[str, Any]] = []
    for _, records in iter_record_lists(payload):
        for record in records:
            if not isinstance(record, dict) or not isinstance(record.get("dimensions"), list):
                continue
            dimensions: list[dict[str, Any]] = []
            for dimension in record["dimensions"][:MAX_DIMENSIONS_PER_AGGREGATE]:
                if not isinstance(dimension, dict):
                    continue
                key = bounded_summary_scalar(dimension.get("key"))
                value = bounded_summary_scalar(dimension.get("value"))
                if key is not None and value is not None:
                    dimensions.append({"key": key, "value": value})
            aggregate: dict[str, Any] = {"dimensions": dimensions}
            for field in collect_money_fields(record):
                scalar = bounded_summary_scalar(record.get(field))
                if scalar is not None:
                    aggregate[field] = scalar
            aggregates.append(aggregate)
            if len(aggregates) >= MAX_DIMENSION_AGGREGATES:
                return aggregates
    return aggregates


def verified_dimension_monetary_totals(payload: Any) -> dict[str, str]:
    """Sum monetary fields shared by every dimension aggregate using Decimal."""
    records = [
        record
        for _, items in iter_record_lists(payload)
        for record in items
        if isinstance(record, dict) and isinstance(record.get("dimensions"), list)
    ]
    if not records:
        return {}
    shared_fields = set(collect_money_fields(records[0]))
    for record in records[1:]:
        shared_fields.intersection_update(collect_money_fields(record))

    totals: dict[str, str] = {}
    for field in sorted(shared_fields):
        values = [record.get(field) for record in records]
        if any(value is None or isinstance(value, (bool, dict, list)) for value in values):
            continue
        try:
            total = sum((Decimal(str(value)) for value in values), Decimal("0"))
        except (InvalidOperation, ValueError):
            continue
        totals[field] = format(total, "f")
    return totals


def billing_scope_summary(
    operation: str | None,
    aggregates: list[dict[str, Any]],
    request_spec: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Describe whether the summarized fact is account-wide or region-scoped."""
    normalized_operation = str(operation or "").split("/", 1)[0].lower()
    if normalized_operation == "showcustomermonthlysum":
        query = request_spec.get("query") if isinstance(request_spec, dict) else None
        filtered = bool(
            isinstance(query, dict)
            and any(
                query.get(field) not in (None, "", [])
                for field in ("service_type_code", "method", "sub_customer_id")
            )
        )
        return {
            "scope_type": (
                "filtered_account_monthly_summary"
                if filtered
                else "all_account_monthly_summary"
            ),
            "region_filtered": False,
            "claim_boundary": (
                "ShowCustomerMonthlySum is not a region-specific fact and must not "
                "be presented as one region's exact cost."
            ),
        }
    if normalized_operation == "listcosts":
        region_values = {
            str(dimension["value"])
            for aggregate in aggregates
            for dimension in aggregate.get("dimensions", [])
            if str(dimension.get("key") or "").upper() == "REGION_CODE"
        }
        body = request_spec.get("body") if isinstance(request_spec, dict) else None
        filters = body.get("filters") if isinstance(body, dict) else None
        for item in filters if isinstance(filters, list) else []:
            factor = item.get("filter_factor") if isinstance(item, dict) else None
            if not isinstance(factor, dict) or factor.get("key") != "REGION_CODE":
                continue
            values = factor.get("value")
            if isinstance(values, list):
                region_values.update(str(value) for value in values)
        sorted_region_values = sorted(region_values)
        return {
            "scope_type": "cost_analysis_dimensions",
            "region_filtered": bool(sorted_region_values),
            "region_values": sorted_region_values,
            "claim_boundary": (
                "Region claims require a REGION_CODE filter or dimension and complete pagination."
            ),
        }
    return {
        "scope_type": "operation_specific",
        "region_filtered": False,
        "claim_boundary": "Use the reviewed request scope before making region-specific claims.",
    }


def pagination_summary(payload: Any, offset: int | None = None, limit: int | None = None) -> dict[str, Any]:
    """Return pagination completeness metadata."""
    total_count = payload.get("total_count") if isinstance(payload, dict) else None
    record_count = sum(len(records) for _, records in iter_record_lists(payload))
    reached_end = False
    complete = False
    if isinstance(total_count, int) and offset is not None:
        reached_end = offset + record_count >= total_count
        complete = offset == 0 and record_count >= total_count
    next_offset = None
    if not reached_end and offset is not None and record_count > 0:
        next_offset = offset + record_count
    return {
        "total_count": total_count,
        "record_count": record_count,
        "offset": offset,
        "limit": limit,
        "complete": bool(complete and total_count is not None),
        "next_offset": next_offset,
        "complete_result_claim_allowed": bool(complete and total_count is not None),
        "reason": "Totals and rankings require all intended pages; one page is partial when total_count exceeds offset + record_count.",
    }


def pricing_scope_summary(request_spec: dict[str, Any] | None) -> dict[str, Any]:
    """Return non-sensitive product dimensions from a pricing request."""

    body = request_spec.get("body") if isinstance(request_spec, dict) else None
    products = body.get("product_infos") if isinstance(body, dict) else None
    safe_products: list[dict[str, Any]] = []
    for product in products if isinstance(products, list) else []:
        if not isinstance(product, dict):
            continue
        safe_products.append(
            {
                key: product.get(key)
                for key in (
                    "cloud_service_type",
                    "resource_type",
                    "resource_spec",
                    "region",
                    "available_zone",
                    "resource_size",
                    "size_measure_id",
                    "subscription_num",
                    "usage_factor",
                    "usage_value",
                    "usage_measure_id",
                    "period_type",
                    "period_num",
                )
                if product.get(key) is not None
            }
        )
    return {
        "product_count": len(safe_products),
        "products": safe_products,
        "project_id_in_request": bool(
            isinstance(body, dict) and body.get("project_id")
        ),
        "project_id_included": False,
    }


def build_pricing_summary(
    raw_value: Any,
    *,
    request_spec: dict[str, Any] | None = None,
    observed_at: str | None = None,
) -> dict[str, Any]:
    """Build a bounded point-in-time BSS pricing quote summary.

    Pricing inquiry responses are not paginated billing record sets. This
    function intentionally reports only aggregate quote fields and counts; it
    never returns product identifiers or optional discount alternative amounts.
    """

    payload, safe_exec = unwrap_safe_exec_result(raw_value)
    operation = str(safe_exec.get("operation") or "") if isinstance(safe_exec, dict) else ""
    normalized_operation = operation.split("/", 1)[0]
    if not isinstance(payload, dict):
        return {
            "success": False,
            "source": "safe_exec" if safe_exec is not None else "direct_json",
            "operation": operation or None,
            "pricing_quote": None,
            "pagination": {"mode": "not_applicable", "complete": True},
            "error": "Pricing payload must be a JSON object.",
        }

    currency_value = bounded_summary_scalar(payload.get("currency"))
    currency_defaulted = currency_value in (None, "")
    currency = "CNY" if currency_defaulted else str(currency_value)
    if normalized_operation == "ListRateOnPeriodDetail":
        official = payload.get("official_website_rating_result")
        official = official if isinstance(official, dict) else {}
        quoted_amount = bounded_summary_scalar(
            official.get("official_website_amount")
        )
        component_results = official.get("product_rating_results")
        optional_discounts = payload.get("optional_discount_rating_results")
        quote = {
            "quote_kind": "period_subscription",
            "quoted_amount": quoted_amount,
            "official_website_amount": quoted_amount,
            "discount_amount": None,
            "currency": currency,
            "currency_defaulted_to_cny": currency_defaulted,
            "measure_id": bounded_summary_scalar(official.get("measure_id")),
            "component_count": len(component_results)
            if isinstance(component_results, list)
            else 0,
            "optional_discount_alternative_count": len(optional_discounts)
            if isinstance(optional_discounts, list)
            else 0,
            "discount_selection": "not_selected",
            "observed_at": observed_at,
        }
    else:
        component_results = payload.get("product_rating_results")
        quote = {
            "quote_kind": "on_demand_usage",
            "quoted_amount": bounded_summary_scalar(payload.get("amount")),
            "official_website_amount": bounded_summary_scalar(
                payload.get("official_website_amount")
            ),
            "discount_amount": bounded_summary_scalar(
                payload.get("discount_amount")
            ),
            "currency": currency,
            "currency_defaulted_to_cny": currency_defaulted,
            "measure_id": bounded_summary_scalar(payload.get("measure_id")),
            "component_count": len(component_results)
            if isinstance(component_results, list)
            else 0,
            "optional_discount_alternative_count": 0,
            "discount_selection": "provider_aggregate_result",
            "observed_at": observed_at,
        }
    return {
        "success": quote["quoted_amount"] not in (None, ""),
        "source": "safe_exec" if safe_exec is not None else "direct_json",
        "operation": operation or None,
        "pricing_quote": quote,
        "pricing_scope": pricing_scope_summary(request_spec),
        "pagination": {
            "mode": "not_applicable",
            "complete": True,
            "complete_result_claim_allowed": True,
        },
        "output_boundary": {
            "aggregate_quote_only": True,
            "raw_product_results_included": False,
            "optional_discount_amounts_included": False,
        },
    }


def build_summary(
    raw_value: Any,
    *,
    offset: int | None = None,
    limit: int | None = None,
    include_redacted_records: bool = False,
    request_spec: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a safe billing result summary."""
    payload, safe_exec = unwrap_safe_exec_result(raw_value)
    keys = protected_keys()
    redacted_payload = redact_protected_identifiers(payload, keys)
    record_lists = iter_record_lists(redacted_payload)
    aggregates = dimension_aggregates(redacted_payload)
    operation = safe_exec.get("operation") if isinstance(safe_exec, dict) else None
    pagination = pagination_summary(redacted_payload, offset=offset, limit=limit)
    summary: dict[str, Any] = {
        "top_level_fields": sorted(redacted_payload.keys()) if isinstance(redacted_payload, dict) else [],
        "money_fields_present": collect_money_fields(redacted_payload),
        "monetary_totals": monetary_totals(redacted_payload),
        "currency": (bounded_summary_scalar(redacted_payload.get("currency")) if isinstance(redacted_payload, dict) else None),
        "dimension_aggregates": aggregates,
        "billing_scope": billing_scope_summary(
            operation,
            aggregates,
            request_spec=request_spec,
        ),
        "record_lists": [
            {
                "field": field,
                "record_count": len(records),
                "field_names": collect_field_names(records),
            }
            for field, records in record_lists
        ],
    }
    if pagination["complete_result_claim_allowed"]:
        verified_totals = verified_dimension_monetary_totals(redacted_payload)
        if verified_totals:
            summary["verified_monetary_totals"] = verified_totals

    result: dict[str, Any] = {
        "success": payload is not None,
        "source": "safe_exec" if safe_exec is not None else "direct_json",
        "operation": operation,
        "redaction": {
            "protected_identifier_keys": sorted(keys),
            "strategy": "stable_hash_marker",
            "raw_identifiers_included": False,
        },
        "pagination": pagination,
        "summary": summary,
        "output_boundary": {
            "summarize_by_default": True,
            "raw_output_allowed_only_after_scope_confirmation": True,
        },
    }
    if include_redacted_records:
        result["redacted_records"] = redacted_payload
    return result


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json-file", type=Path, required=True, help="JSON file containing a safe_exec result or BSS JSON payload.")
    parser.add_argument("--offset", type=int, help="Known pagination offset from the command plan.")
    parser.add_argument("--limit", type=int, help="Known pagination limit from the command plan.")
    parser.add_argument("--include-redacted-records", action="store_true", help="Include redacted records in the output.")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")
    return parser.parse_args()


def main() -> int:
    """Summarize a billing result JSON file."""
    args = parse_args()
    raw_value = hcloud_common.load_json(args.json_file)
    result = build_summary(
        raw_value,
        offset=args.offset,
        limit=args.limit,
        include_redacted_records=args.include_redacted_records,
    )
    hcloud_common.emit_json(result, pretty=args.pretty)
    return 0 if result["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
