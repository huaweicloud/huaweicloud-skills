#!/usr/bin/env python3
"""Plan or fetch one bounded Huawei Cloud provider pricing quote."""

from __future__ import annotations

import argparse
import shlex
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import hcloud_billing_live_read
import hcloud_billing_readonly
import hcloud_common

SERVICE_DEFAULT_PRESETS = {
    "BMS": "bms",
    "ECS": "ecs",
    "ELB": "elb",
    "EVS": "evs",
    "NAT": "nat",
    "OBS": "obs",
    "SFS": "sfs",
    "VPC": "vpc",
}
EIP_PRESETS = ("eip-bw", "eip-flow", "eip-ip")
COMPONENT_LABELS = {
    "bms": "BMS compute",
    "ecs": "ECS compute",
    "elb": "ELB instance",
    "evs": "EVS volume",
    "eip-bw": "EIP bandwidth",
    "eip-flow": "EIP traffic",
    "eip-ip": "EIP address",
    "nat": "NAT gateway",
    "obs": "OBS storage",
    "sfs": "SFS Turbo storage",
    "vpc": "VPC endpoint",
}
SERVICE_EXCLUDED_COMPONENTS = {
    "ECS": [
        "EVS root volume",
        "EVS data volumes",
        "EIP address and bandwidth",
        "traffic and other attached services",
    ],
    "EIP": [
        "EIP components not selected by pricing_preset",
        "downstream traffic or service charges outside the selected usage input",
    ],
}


def unknown_cost_estimate(
    *,
    service: str,
    operation: str | None = None,
    region: str | None = None,
    reason: str,
    reason_code: str = "PRICING_INPUTS_UNAVAILABLE",
    quantity: int | None = None,
    resource_spec: list[str] | None = None,
    components_included: list[str] | None = None,
    components_excluded: list[str] | None = None,
    next_action_command: str | None = None,
) -> dict[str, Any]:
    """Return an explicit unknown estimate without inventing an amount."""

    return {
        "contract": "huaweicloud_single_change_cost_estimate_v1",
        "status": "unknown",
        "amount": None,
        "currency": None,
        "reason_code": reason_code,
        "reason": reason,
        "basis": "provider_point_in_time_quote",
        "scope": {
            "service": service.upper(),
            "operation": operation,
            "region": region,
            "quantity": quantity,
            "resource_spec": list(resource_spec or []),
            "components_included": list(components_included or []),
            "components_excluded": list(components_excluded or []),
        },
        "quote_time": None,
        "discount_basis": "unknown_until_provider_quote",
        "historical_billing_fact": False,
        "purchase_commitment": False,
        "confidence": "unknown",
        "next_action_command": next_action_command,
    }


def supported_presets(charge_mode: str) -> dict[str, dict[str, Any]]:
    """Return pricing presets supported by the selected BSS quote operation."""

    return (
        hcloud_billing_readonly.ON_DEMAND_PRICING_PRESETS
        if charge_mode == "on_demand"
        else hcloud_billing_readonly.PERIOD_PRICING_PRESETS
    )


def selected_preset(args: argparse.Namespace) -> tuple[str | None, list[str]]:
    """Return an unambiguous BSS pricing preset and validation errors."""

    service = str(args.service).strip().upper()
    explicit = str(getattr(args, "pricing_preset", None) or "").strip().lower()
    if service == "EIP" and not explicit:
        return None, [
            "EIP pricing is component-specific; choose eip-bw, eip-flow, or eip-ip explicitly."
        ]
    preset = explicit or SERVICE_DEFAULT_PRESETS.get(service)
    if not preset:
        return None, [
            f"No default BSS pricing preset is registered for service {service}."
        ]
    available = supported_presets(args.charge_mode)
    if preset not in available:
        return None, [
            f"Pricing preset {preset} is unavailable for {args.charge_mode}; supported presets: {', '.join(sorted(available))}."
        ]
    return preset, []


def estimate_scope(
    args: argparse.Namespace,
    preset: str | None,
) -> dict[str, Any]:
    """Return the exact components and usage dimensions covered by a quote."""

    service = str(args.service).strip().upper()
    included = [COMPONENT_LABELS[preset]] if preset in COMPONENT_LABELS else []
    return {
        "service": service,
        "region": args.region,
        "charge_mode": args.charge_mode,
        "quantity": args.quantity,
        "resource_spec": list(args.resource_spec or []),
        "resource_size": list(getattr(args, "resource_size", None) or []),
        "usage_value": list(getattr(args, "usage_value", None) or []),
        "period_type": list(getattr(args, "period_type", None) or []),
        "period_num": list(getattr(args, "period_num", None) or []),
        "pricing_preset": preset,
        "components_included": included,
        "components_excluded": list(
            SERVICE_EXCLUDED_COMPONENTS.get(service, [])
        ),
    }


def live_read_args(args: argparse.Namespace, preset: str) -> SimpleNamespace:
    """Map the single-change contract to the existing BSS live-read contract."""

    operation = (
        "on-demand-pricing"
        if args.charge_mode == "on_demand"
        else "period-pricing"
    )
    return SimpleNamespace(
        operation=operation,
        entry_point="pricing_inquiry",
        endpoint_base=hcloud_billing_readonly.DEFAULT_ENDPOINT_BASE,
        language="zh_CN",
        bill_cycle=None,
        shared_month=None,
        begin_time=None,
        end_time=None,
        time_measure_id=1,
        group_by=["CLOUD_SERVICE_TYPE"],
        filter=[],
        cost_type="ORIGINAL_COST",
        amount_type="PAYMENT_AMOUNT",
        project_id=args.project_id,
        service_type_code=None,
        resource_type=None,
        resource_spec=list(args.resource_spec or []),
        usage_type=None,
        region_code=None,
        pricing_region=args.region,
        available_zone=getattr(args, "available_zone", None),
        pricing_preset=preset,
        resource_size=list(getattr(args, "resource_size", None) or []),
        size_measure_id=list(getattr(args, "size_measure_id", None) or []),
        usage_value=list(getattr(args, "usage_value", None) or []),
        subscription_num=[args.quantity],
        inquiry_precision=1,
        period_type=list(getattr(args, "period_type", None) or []),
        period_num=list(getattr(args, "period_num", None) or []),
        fee_installment_mode=getattr(args, "fee_installment_mode", None),
        resource_id=None,
        enterprise_project_id=None,
        charge_mode=None,
        bill_type=None,
        method=None,
        sub_customer_id=None,
        customer_id=None,
        order_id=None,
        balance_type=None,
        status=None,
        free_resource_id=None,
        quota_id=None,
        include_zero_record=None,
        statistic_type=None,
        offset=0,
        limit=50,
        query=[],
        body_json_file=None,
        body_json_text=None,
        execute=bool(args.execute),
        confirm_live_billing_read=getattr(
            args,
            "confirm_live_billing_read",
            None,
        ),
        include_redacted_records=False,
        timeout=args.timeout,
        time_budget=None,
        max_output_chars=args.max_output_chars,
        checkpoint_file=None,
        resume=False,
        output_file=None,
        pretty=False,
    )


def quote_cli_command(args: argparse.Namespace, preset: str) -> str:
    """Return the explicit command that can obtain the reviewed provider quote."""

    command = [
        "python3",
        "scripts/hcloud_cost_estimate.py",
        "--service",
        str(args.service).upper(),
        "--region",
        args.region,
        "--project-id",
        args.project_id,
        "--charge-mode",
        args.charge_mode,
        "--pricing-preset",
        preset,
        "--quantity",
        str(args.quantity),
    ]
    for value in args.resource_spec:
        command.extend(["--resource-spec", str(value)])
    for option, values in (
        ("--resource-size", getattr(args, "resource_size", None) or []),
        ("--size-measure-id", getattr(args, "size_measure_id", None) or []),
        ("--usage-value", getattr(args, "usage_value", None) or []),
        ("--period-type", getattr(args, "period_type", None) or []),
        ("--period-num", getattr(args, "period_num", None) or []),
    ):
        for value in values:
            command.extend([option, str(value)])
    if getattr(args, "available_zone", None):
        command.extend(["--available-zone", args.available_zone])
    if getattr(args, "fee_installment_mode", None):
        command.extend(
            ["--fee-installment-mode", args.fee_installment_mode]
        )
    command.extend(
        [
            "--execute",
            "--confirm-live-billing-read",
            hcloud_billing_live_read.CONFIRM_TOKEN,
        ]
    )
    return shlex.join(command)


def build_cost_estimate(args: argparse.Namespace) -> dict[str, Any]:
    """Build or execute one point-in-time provider quote workflow."""

    service = str(args.service).strip().upper()
    preset, errors = selected_preset(args)
    if args.quantity < 1:
        errors.append("quantity must be at least 1.")
    if len(args.resource_spec or []) != 1:
        errors.append(
            "A single-change estimate requires exactly one resource_spec."
        )
    scope = estimate_scope(args, preset)
    if errors:
        reason_code = (
            "AMBIGUOUS_PRICING_PRESET"
            if service == "EIP" and not getattr(args, "pricing_preset", None)
            else "INVALID_PRICING_INPUT"
        )
        return {
            "success": False,
            "mode": "execute" if args.execute else "plan",
            "service": service,
            "error_code": reason_code,
            "errors": errors,
            "allowed_pricing_presets": sorted(
                supported_presets(args.charge_mode)
            ),
            "cost_estimate": unknown_cost_estimate(
                service=service,
                region=args.region,
                reason=" ".join(errors),
                reason_code=reason_code,
                quantity=args.quantity,
                resource_spec=list(args.resource_spec or []),
                components_included=scope["components_included"],
                components_excluded=scope["components_excluded"],
            ),
        }

    assert preset is not None
    pricing_read = hcloud_billing_live_read.build_live_read(
        live_read_args(args, preset)
    )
    next_action = quote_cli_command(args, preset)
    if not args.execute:
        estimate = unknown_cost_estimate(
            service=service,
            region=args.region,
            reason="The provider pricing inquiry is planned but has not been executed.",
            reason_code="PROVIDER_QUOTE_NOT_EXECUTED",
            quantity=args.quantity,
            resource_spec=list(args.resource_spec),
            components_included=scope["components_included"],
            components_excluded=scope["components_excluded"],
            next_action_command=next_action,
        )
        estimate["scope"].update(
            {
                key: value
                for key, value in scope.items()
                if key not in estimate["scope"]
            }
        )
        return {
            "success": bool(pricing_read.get("success")),
            "mode": "plan",
            "planning_only": True,
            "service": service,
            "pricing_preset": preset,
            "cost_estimate": estimate,
            "pricing_read": pricing_read,
        }

    execution = pricing_read.get("execution")
    execution_result = execution.get("result") if isinstance(execution, dict) else None
    summary = execution_result.get("summary") if isinstance(execution_result, dict) else None
    quote = summary.get("pricing_quote") if isinstance(summary, dict) else None
    if not pricing_read.get("success") or not isinstance(quote, dict):
        estimate = unknown_cost_estimate(
            service=service,
            region=args.region,
            reason="The provider pricing inquiry did not return a usable aggregate quote.",
            reason_code="PROVIDER_QUOTE_UNAVAILABLE",
            quantity=args.quantity,
            resource_spec=list(args.resource_spec),
            components_included=scope["components_included"],
            components_excluded=scope["components_excluded"],
            next_action_command=next_action,
        )
        estimate["scope"].update(
            {
                key: value
                for key, value in scope.items()
                if key not in estimate["scope"]
            }
        )
        return {
            "success": False,
            "mode": "execute",
            "service": service,
            "pricing_preset": preset,
            "cost_estimate": estimate,
            "pricing_read": pricing_read,
        }

    estimate = {
        "contract": "huaweicloud_single_change_cost_estimate_v1",
        "status": "quoted",
        "amount": quote.get("quoted_amount"),
        "currency": quote.get("currency"),
        "reason_code": None,
        "reason": None,
        "basis": "provider_point_in_time_quote",
        "scope": scope,
        "quote_time": quote.get("observed_at"),
        "official_website_amount": quote.get("official_website_amount"),
        "discount_amount": quote.get("discount_amount"),
        "discount_basis": quote.get("discount_selection"),
        "optional_discount_alternative_count": quote.get(
            "optional_discount_alternative_count"
        ),
        "historical_billing_fact": False,
        "purchase_commitment": False,
        "confidence": "provider_quote",
        "next_action_command": None,
    }
    return {
        "success": estimate["amount"] is not None,
        "mode": "execute",
        "planning_only": False,
        "service": service,
        "pricing_preset": preset,
        "cost_estimate": estimate,
        "pricing_read": pricing_read,
    }


def parse_args() -> argparse.Namespace:
    """Parse single-change cost-estimate arguments."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--service", required=True)
    parser.add_argument("--region", required=True)
    parser.add_argument("--project-id", required=True)
    parser.add_argument(
        "--charge-mode",
        choices=("on_demand", "period"),
        default="on_demand",
    )
    parser.add_argument("--pricing-preset")
    parser.add_argument("--resource-spec", action="append", required=True)
    parser.add_argument("--quantity", type=int, default=1)
    parser.add_argument("--resource-size", type=int, action="append", default=[])
    parser.add_argument("--size-measure-id", type=int, action="append", default=[])
    parser.add_argument("--usage-value", type=float, action="append", default=[])
    parser.add_argument("--available-zone")
    parser.add_argument("--period-type", action="append", default=[])
    parser.add_argument("--period-num", type=int, action="append", default=[])
    parser.add_argument(
        "--fee-installment-mode",
        choices=("HALF_PAY", "ZERO_PAY", "NA"),
    )
    parser.add_argument("--execute", action="store_true")
    parser.add_argument(
        "--confirm-live-billing-read",
        help=(
            "Required in execute mode and must equal "
            f"{hcloud_billing_live_read.CONFIRM_TOKEN}."
        ),
    )
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--max-output-chars", type=int, default=20000)
    parser.add_argument("--output-file")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()
    if args.timeout < 1:
        parser.error("--timeout must be greater than 0.")
    if args.max_output_chars < 1:
        parser.error("--max-output-chars must be greater than 0.")
    return args


def main() -> int:
    """Build or execute the quote and emit a stable public result."""

    args = parse_args()
    result = build_cost_estimate(args)
    hcloud_common.emit_public_result(
        result,
        output_file=Path(args.output_file) if args.output_file else None,
        pretty=args.pretty,
        default_mode="plan",
        receipt_extra={"cost_estimate": result.get("cost_estimate")},
    )
    return 0 if result["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
