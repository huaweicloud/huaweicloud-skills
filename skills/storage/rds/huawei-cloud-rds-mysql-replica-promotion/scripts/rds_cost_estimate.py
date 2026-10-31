#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Estimate the cost of Huawei Cloud RDS for MySQL resources via BSS.

Overview:
    This script estimates the price of creating a Huawei Cloud RDS for
    MySQL instance through the `hcloud` (KooCLI) command line tool. It
    quotes on-demand (hourly) and prepaid (month/year) prices through the
    BSS rating APIs without creating any resource. It is a standalone
    companion tool of the SKILL workflow, used by the Agent to present
    concrete cost figures during the risk disclosure step; it writes a
    structured JSON report instead of text tables.

Detailed Description:
    The region's project id is resolved automatically via
    KeystoneListAuthProjects (rds_common.resolve_project_id). BSS is a
    global service, so every BSS call pins --cli-region=cn-north-1 and
    carries the real region inside product_infos.N.region. Flavors are
    resolved either directly from --spec-code or by filtering
    ListFlavors on vcpus/ram/group_type with the instance_mode field
    (lowercase ha/single/replica); --deploy-type optionally keeps only
    one deployment type, otherwise both single and ha are listed.
    On-demand quotes use usage_measure_id=4 (hour) per the verified BSS
    billing unit; prepaid quotes default to 1 month + 1 year and support
    --period-type/--period-num overrides. --charge-mode optionally
    filters the quoting to the instance's actual charge mode (postPaid
    quotes only on-demand, prePaid only prepaid), while the default None
    keeps quoting both modes for backward compatibility. An optional
    storage volume quote (resource_type hws.resource.type.rds.volume) is
    appended as a second product in the same on-demand or prepaid call
    when --storage-size-gb is given; the prepaid call builds it with
    period_type/period_num, while the on-demand call uses the usage_*
    fields, and the volume line is then merged into the quoted total and
    a warning notes that no separate storage figure was quoted.
    Individual quote failures are isolated into warnings and never abort
    the whole run.

Workflow:
    1. Parse the command line arguments.
    2. Validate the spec input (spec-code or vcpus/ram).
    3. Resolve the project id of the region.
    4. Resolve the flavors to quote (spec-code path or ListFlavors path).
    5. Quote on-demand prices (compute, plus storage when requested),
       skipped when --charge-mode is prePaid.
    6. Quote prepaid prices for the configured periods, skipped when
       --charge-mode is postPaid.
    7. Write the structured JSON report.

Dependencies:
    - Python 3.9+ standard library only (argparse, json, logging, os,
      sys, datetime).
    - rds_common (same directory, shared helpers).
    - External: `hcloud` (KooCLI 7.2.2+) installed, configured and
      authenticated.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from datetime import datetime, timezone

import rds_common as common

LOGGER = logging.getLogger(__name__)

BSS_REGION = "cn-north-1"
RDS_SERVICE_TYPE = "hws.service.type.rds"
RESOURCE_TYPE_VM = "hws.resource.type.rds.vm"
RESOURCE_TYPE_VOLUME = "hws.resource.type.rds.volume"
SIZE_MEASURE_ID_GB = 17
# Verified (2026-10-22, cn-north-4): RDS MySQL on-demand rating requires
# usage_measure_id=4 (hour); value 1 fails with CBC.6050.
USAGE_MEASURE_ID_HOUR = 4
DEFAULT_PERIODS = [(2, 1), (3, 1)]
PERIOD_TYPES = {2: "month", 3: "year"}
DEFAULT_OUTPUT_PREFIX = "rds_cost_estimate_result_{ts}.json"

# Verified storage spec mapping (ListResourceSpecs, cn-north-4, 2026-10-22).
# volume.type -> {mode: resource_spec} for the single/ha modes the
# single-to-HA conversion needs. Unmapped volume types yield no spec.
STORAGE_SPEC_MAP = {
    "CLOUDSSD": {
        "single": "rds.mysql.volume.cloudssd",
        "ha": "rds.mysql.volume.cloudssd.ha",
    },
    "ESSD": {
        "single": "rds.mysql.volume.essd",
        "ha": "rds.mysql.volume.essd.ha",
    },
    "ESSD2": {
        "single": "rds.mysql.volume.essd2",
        "ha": "rds.mysql.volume.essd2.ha",
    },
    "GPSSD2": {
        "single": "rds.mysql.volume.gpssd2",
        "ha": "rds.mysql.volume.gpssd2.ha",
    },
}


def build_arg_parser() -> argparse.ArgumentParser:
    """Build the command line argument parser.

    1. Add the region, spec input, deploy type, period, storage and output
       options.

    Args:
        None

    Returns:
        argparse.ArgumentParser: Configured parser.

    Examples:
        >>> parser = build_arg_parser()
        >>> args = parser.parse_args(["--region", "cn-north-4", "--spec-code", "rds.mysql.x1.large.2.ha"])
        >>> args.region == "cn-north-4"
        True
    """
    parser = argparse.ArgumentParser(
        prog="rds_cost_estimate",
        description=(
            "Estimate the cost of Huawei Cloud RDS for MySQL resources "
            "via the hcloud CLI BSS rating APIs; quotes only, never "
            "creates resources."
        ),
    )
    parser.add_argument(
        "--region",
        required=True,
        help="Required. Cloud region (e.g. cn-north-4).",
    )
    parser.add_argument(
        "--spec-code",
        default=None,
        help=(
            "Optional. Exact flavor spec code to quote directly (e.g. "
            "rds.mysql.x1.large.2.ha); takes priority over vcpus/ram "
            "filtering."
        ),
    )
    parser.add_argument(
        "--vcpus",
        type=int,
        default=None,
        help="Optional. vCPU count used to filter ListFlavors.",
    )
    parser.add_argument(
        "--ram",
        type=int,
        default=None,
        help="Optional. Memory size in GB used to filter ListFlavors.",
    )
    parser.add_argument(
        "--group-type",
        default="dedicated",
        help="Optional. Flavor group type used to filter ListFlavors (default dedicated).",
    )
    parser.add_argument(
        "--db-version",
        default="8.0",
        help="Optional. MySQL version passed to ListFlavors (default 8.0).",
    )
    parser.add_argument(
        "--deploy-type",
        choices=["single", "ha"],
        default=None,
        help=(
            "Optional. Keep only one deployment type; when absent both "
            "single and ha flavors are listed. Ignored when --spec-code "
            "is given."
        ),
    )
    parser.add_argument(
        "--compare-single-ha",
        action="store_true",
        help=(
            "Optional. Quote both the single instance spec and its derived "
            "ha spec (x86 appends .ha; ARM replaces .single with .ha) and "
            "output a price comparison with delta and multiple. Requires "
            "--spec-code with the single instance spec."
        ),
    )
    parser.add_argument(
        "--period-type",
        type=int,
        choices=[0, 2, 3, 4],
        default=None,
        help=(
            "Optional. Prepaid period type: 2=month, 3=year; when absent "
            "both 1 month and 1 year are quoted."
        ),
    )
    parser.add_argument(
        "--period-num",
        type=int,
        default=1,
        help="Optional. Prepaid period count (default 1).",
    )
    parser.add_argument(
        "--storage-size-gb",
        type=int,
        default=None,
        help=(
            "Optional. Storage volume size in GB; when given the volume "
            "is quoted together with the compute flavor in one on-demand "
            "call and merged into the quoted total."
        ),
    )
    parser.add_argument(
        "--storage-type",
        default="GPSSD",
        help="Optional. Storage volume type used as the volume resource_spec (default GPSSD).",
    )
    parser.add_argument(
        "--charge-mode",
        choices=["postPaid", "prePaid"],
        default=None,
        help=(
            "Optional. Filter quotes by the instance's actual charge mode: "
            "postPaid quotes only on-demand (hourly) prices; prePaid quotes "
            "only prepaid (monthly/yearly) prices; when absent both modes "
            "are quoted (backward compatible)."
        ),
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Optional. Path to the output JSON report file.",
    )
    return parser


def validate_spec_input(
    parser: argparse.ArgumentParser, args: argparse.Namespace
) -> None:
    """Validate that at least one spec input path is present.

    1. Accept when --spec-code is given.
    2. Accept when both --vcpus and --ram are given.
    3. In compare mode require --spec-code (a single instance spec).
    4. Otherwise call parser.error which prints usage and exits with code 2.

    Args:
        parser: argparse.ArgumentParser — The configured parser.
        args: argparse.Namespace — Parsed command line arguments.

    Returns:
        None

    Examples:
        >>> parser = argparse.ArgumentParser()
        >>> # An invalid combination exits the process with code 2.
        # >>> validate_spec_input(parser, argparse.Namespace(spec_code=None, vcpus=None, ram=None, compare_single_ha=False))
        # SystemExit: 2
    """
    if args.compare_single_ha:
        if not args.spec_code:
            parser.error(
                "--compare-single-ha requires --spec-code with the single instance spec"
            )
        return
    if args.spec_code:
        return
    if args.vcpus is None or args.ram is None:
        parser.error("either --spec-code or both --vcpus and --ram must be provided")


def make_bss_prefix(project_id: str) -> list[str]:
    """Build the base BSS hcloud command prefix for a resolved project.

    1. Join the BSS service name, the pinned global region and the project
       id flag.

    Args:
        project_id: str — The resolved project id of the target region.

    Returns:
        list[str]: Command prefix for BSS rating operations.

    Examples:
        >>> make_bss_prefix("p1")
        ['BSS', '--cli-region=cn-north-1', '--project_id=p1']
    """
    return [
        "BSS",
        "--cli-region={}".format(BSS_REGION),
        "--project_id={}".format(project_id),
    ]


def build_compute_product(index: int, region: str, spec_code: str) -> list[str]:
    """Build the compute product_infos command arguments for one quote.

    1. Emit the cloud_service_type/resource_type/resource_spec/region and
       the on-demand usage fields for the compute product.

    Args:
        index: int — The 1-based product index in the request.
        region: str — The real cloud region of the resource.
        spec_code: str — The compute flavor spec code.

    Returns:
        list[str]: product_infos.<index> command arguments.

    Examples:
        >>> args = build_compute_product(1, "cn-north-4", "rds.mysql.x1.large.2.ha")
        >>> "--product_infos.1.cloud_service_type=hws.service.type.rds" in args
        True
        >>> "--product_infos.1.resource_spec=rds.mysql.x1.large.2.ha" in args
        True
    """
    return [
        "--product_infos.{}.cloud_service_type={}".format(index, RDS_SERVICE_TYPE),
        "--product_infos.{}.resource_type={}".format(index, RESOURCE_TYPE_VM),
        "--product_infos.{}.resource_spec={}".format(index, spec_code),
        "--product_infos.{}.region={}".format(index, region),
        "--product_infos.{}.id={}".format(index, index),
        "--product_infos.{}.subscription_num=1".format(index),
        "--product_infos.{}.usage_factor=Duration".format(index),
        "--product_infos.{}.usage_value=1".format(index),
        "--product_infos.{}.usage_measure_id={}".format(index, USAGE_MEASURE_ID_HOUR),
    ]


def resolve_storage_spec(volume_type: str, mode: str) -> str | None:
    """Resolve the storage resource_spec from a volume type and mode.

    1. Look up the volume type in the verified storage spec map.
    2. Return the mode-specific spec (single/ha) or None when unmapped.

    Args:
        volume_type: str — The instance volume type (e.g. CLOUDSSD).
        mode: str — The deployment mode (single or ha).

    Returns:
        str | None: The storage resource_spec, or None when the volume
            type is not in the mapping table.

    Examples:
        >>> resolve_storage_spec("CLOUDSSD", "ha")
        'rds.mysql.volume.cloudssd.ha'
        >>> resolve_storage_spec("ULTRAHIGH", "ha") is None
        True
    """
    by_mode = STORAGE_SPEC_MAP.get(volume_type.upper() if volume_type else "")
    if not by_mode:
        return None
    return by_mode.get(mode)


def build_storage_product(
    index: int, region: str, size_gb: int, resource_spec: str
) -> list[str]:
    """Build the storage volume product_infos command arguments.

    1. Emit the volume resource fields including resource_size and
       size_measure_id, plus the on-demand usage fields.

    Args:
        index: int — The 1-based product index in the request.
        region: str — The real cloud region of the resource.
        size_gb: int — The storage volume size in GB.
        resource_spec: str — The resolved storage resource_spec
            (e.g. rds.mysql.volume.cloudssd.ha).

    Returns:
        list[str]: product_infos.<index> command arguments.

    Examples:
        >>> args = build_storage_product(2, "cn-north-4", 40, "rds.mysql.volume.cloudssd.ha")
        >>> "--product_infos.2.resource_type=hws.resource.type.rds.volume" in args
        True
        >>> "--product_infos.2.resource_size=40" in args
        True
    """
    return [
        "--product_infos.{}.cloud_service_type={}".format(index, RDS_SERVICE_TYPE),
        "--product_infos.{}.resource_type={}".format(index, RESOURCE_TYPE_VOLUME),
        "--product_infos.{}.resource_spec={}".format(index, resource_spec),
        "--product_infos.{}.resource_size={}".format(index, size_gb),
        "--product_infos.{}.size_measure_id={}".format(index, SIZE_MEASURE_ID_GB),
        "--product_infos.{}.region={}".format(index, region),
        "--product_infos.{}.id={}".format(index, index),
        "--product_infos.{}.subscription_num=1".format(index),
        "--product_infos.{}.usage_factor=Duration".format(index),
        "--product_infos.{}.usage_value=1".format(index),
        "--product_infos.{}.usage_measure_id={}".format(index, USAGE_MEASURE_ID_HOUR),
    ]


def build_storage_product_for_period(
    index: int,
    region: str,
    size_gb: int,
    resource_spec: str,
    period_type: int,
    period_num: int,
) -> list[str]:
    """Build the storage volume product args for prepaid (period) quotes.

    1. Emit the volume resource fields including resource_size and
       size_measure_id, plus the prepaid period fields.
    2. Unlike build_storage_product, use period_type/period_num instead of
       usage_factor/usage_value/usage_measure_id, because
       ListRateOnPeriodDetail rejects the usage_* fields.

    Args:
        index: int — The 1-based product index in the request.
        region: str — The real cloud region of the resource.
        size_gb: int — The storage volume size in GB.
        resource_spec: str — The resolved storage resource_spec
            (e.g. rds.mysql.volume.cloudssd.ha).
        period_type: int — Prepaid period type (2=month, 3=year).
        period_num: int — Prepaid period count.

    Returns:
        list[str]: product_infos.<index> command arguments.

    Examples:
        >>> args = build_storage_product_for_period(2, "cn-north-4", 40,
        ...     "rds.mysql.volume.cloudssd.ha", 2, 1)
        >>> "--product_infos.2.period_type=2" in args
        True
        >>> "--product_infos.2.resource_size=40" in args
        True
    """
    return [
        "--product_infos.{}.cloud_service_type={}".format(index, RDS_SERVICE_TYPE),
        "--product_infos.{}.resource_type={}".format(index, RESOURCE_TYPE_VOLUME),
        "--product_infos.{}.resource_spec={}".format(index, resource_spec),
        "--product_infos.{}.resource_size={}".format(index, size_gb),
        "--product_infos.{}.size_measure_id={}".format(index, SIZE_MEASURE_ID_GB),
        "--product_infos.{}.region={}".format(index, region),
        "--product_infos.{}.id={}".format(index, index),
        "--product_infos.{}.subscription_num=1".format(index),
        "--product_infos.{}.period_type={}".format(index, period_type),
        "--product_infos.{}.period_num={}".format(index, period_num),
    ]


def parse_on_demand(payload: dict) -> dict | None:
    """Parse an on-demand rating payload into a result dict.

    1. Return None when the payload carries an error_code.
    2. Read amount/official_website_amount/discount_amount/currency.
    3. Split the product_rating_results into compute (id=1) and storage
       (id=2) component amounts so compare mode can report each line.

    Args:
        payload: dict — The parsed ListOnDemandResourceRatings payload.

    Returns:
        dict | None: On-demand result dict, or None on error.

    Examples:
        >>> result = parse_on_demand({"amount": "0.34", "currency": "CNY"})
        >>> result["hourly_price"] == "0.34"
        True
        >>> result["compute"]["hourly_price"] == "0.34"
        True
        >>> parse_on_demand({"error_code": "CBC.0000"}) is None
        True
    """
    if "error_code" in payload:
        return None
    compute = {}
    storage = None
    for product in payload.get("product_rating_results") or []:
        if str(product.get("id")) == "2":
            storage = {
                "hourly_price": product.get("amount"),
                "official_website_amount": product.get("official_website_amount"),
            }
        elif str(product.get("id")) == "1":
            compute = {
                "hourly_price": product.get("amount"),
                "official_website_amount": product.get("official_website_amount"),
            }
    return {
        "hourly_price": payload.get("amount"),
        "official_website_amount": payload.get("official_website_amount"),
        "discount_amount": payload.get("discount_amount"),
        "usage_measure_id": USAGE_MEASURE_ID_HOUR,
        "currency": payload.get("currency", "CNY"),
        "compute": compute,
        "storage": storage,
        "total": payload.get("amount"),
    }


def parse_period(
    payload: dict, period_type: int, period_num: int
) -> dict | None:
    """Parse a prepaid rating payload into a period result dict.

    1. Return None when the payload carries an error_code.
    2. Read official_website_amount/discount_amount from the official
       rating result.
    3. Use discount_rating_results[0].discount_amount_after_policy as the
       final amount when present; otherwise compute
       official_website_amount - discount_amount, and when no discount
       information exists fall back to official_website_amount itself.
    4. Split the product_rating_results into compute (id=1) and storage
       (id=2) component amounts so compare mode can report each line.

    Args:
        payload: dict — The parsed ListRateOnPeriodDetail payload.
        period_type: int — The quoted period type (2=month, 3=year).
        period_num: int — The quoted period count.

    Returns:
        dict | None: Period result dict, or None on error.

    Examples:
        >>> payload = {"official_website_rating_result": {"official_website_amount": "146.88",
        ...              "discount_amount": "0.00"}, "currency": "CNY"}
        >>> result = parse_period(payload, 2, 1)
        >>> result["period_type"] == 2
        True
        >>> result["final_amount"] == "146.88"
        True
        >>> parse_period({"error_code": "CBC.0000"}, 2, 1) is None
        True
        >>> no_discount = parse_period({"official_website_rating_result": {"official_website_amount": "550.0"}}, 2, 1)
        >>> no_discount["final_amount"] == "550.0"
        True
    """
    if "error_code" in payload:
        return None
    official_rating = payload.get("official_website_rating_result") or {}
    official = official_rating.get("official_website_amount")
    discount = official_rating.get("discount_amount")
    final_amount = None
    discount_results = payload.get("discount_rating_results") or []
    if discount_results:
        final_amount = discount_results[0].get("discount_amount_after_policy")
    elif official is not None and discount is not None:
        try:
            final_amount = "{:.2f}".format(
                float(official) - float(discount)
            )
        except (TypeError, ValueError):
            final_amount = None
    elif official is not None:
        # No discount information returned; fall back to the official
        # website amount as the final amount so the field stays usable.
        final_amount = official
    compute = {}
    storage = None
    for product in official_rating.get("product_rating_results") or []:
        if str(product.get("id")) == "2":
            storage = {
                "official_website_amount": product.get("official_website_amount"),
                "final_amount": product.get("official_website_amount"),
            }
        elif str(product.get("id")) == "1":
            compute = {
                "official_website_amount": product.get("official_website_amount"),
                "final_amount": product.get("official_website_amount"),
            }
    return {
        "period_type": period_type,
        "period_num": period_num,
        "official_website_amount": official,
        "discount_amount": discount,
        "final_amount": final_amount,
        "currency": payload.get("currency", "CNY"),
        "compute": compute,
        "storage": storage,
        "total": official,
    }


def quote_on_demand(
    bss_prefix: list[str],
    region: str,
    spec_code: str,
    storage: dict | None,
    timeout: int,
) -> tuple[dict | None, list[str]]:
    """Quote the on-demand price for a compute flavor plus optional storage.

    1. Build the compute product and, when storage is requested, append the
       storage volume product in the same call.
    2. Run ListOnDemandResourceRatings and parse the response.

    Args:
        bss_prefix: list[str] — Base BSS command prefix.
        region: str — The real cloud region of the resource.
        spec_code: str — The compute flavor spec code.
        storage: dict | None — Storage params (size_gb/storage_type) or None.
        timeout: int — Timeout in seconds for the subprocess call.

    Returns:
        tuple[dict | None, list[str]]: (on-demand result, warnings).

    Examples:
        # Requires hcloud credentials:
        # >>> quote_on_demand(["BSS"], "cn-north-4", "x", None, 5)
        # (None, [])
    """
    warnings: list[str] = []
    product_args = build_compute_product(1, region, spec_code)
    if storage is not None:
        product_args += build_storage_product(
            2, region, storage["size_gb"], storage["resource_spec"]
        )
    cmd = bss_prefix + ["ListOnDemandResourceRatings"] + product_args
    try:
        payload = common.run_hcloud(cmd, timeout)
    except common.HcloudError as exc:
        warnings.append(
            "on-demand quote failed for {} (BSS channel {}, instance region "
            "{}): {}".format(spec_code, BSS_REGION, region, exc)
        )
        return None, warnings
    result = parse_on_demand(payload)
    if result is None:
        warnings.append(
            "on-demand quote failed for {}: {}".format(
                spec_code, common.extract_error_message(payload)
            )
        )
        return None, warnings
    if storage is not None:
        result["includes_storage"] = True
    return result, warnings


def quote_period(
    bss_prefix: list[str],
    region: str,
    spec_code: str,
    period_type: int,
    period_num: int,
    timeout: int,
    storage: dict | None = None,
) -> tuple[dict | None, list[str]]:
    """Quote the prepaid price for one period of a compute flavor.

    1. Build the product args with the period type and count.
    2. Append the storage volume product when storage is requested.
    3. Run ListRateOnPeriodDetail and parse the response.

    Args:
        bss_prefix: list[str] — Base BSS command prefix.
        region: str — The real cloud region of the resource.
        spec_code: str — The compute flavor spec code.
        period_type: int — The quoted period type (2=month, 3=year).
        period_num: int — The quoted period count.
        timeout: int — Timeout in seconds for the subprocess call.
        storage: dict | None — Storage params (size_gb/resource_spec) or None.

    Returns:
        tuple[dict | None, list[str]]: (period result, warnings).

    Examples:
        # Requires hcloud credentials:
        # >>> quote_period(["BSS"], "cn-north-4", "x", 2, 1, 5)
        # (None, [])
    """
    warnings: list[str] = []
    product_args = [
        "--product_infos.1.cloud_service_type={}".format(RDS_SERVICE_TYPE),
        "--product_infos.1.resource_type={}".format(RESOURCE_TYPE_VM),
        "--product_infos.1.resource_spec={}".format(spec_code),
        "--product_infos.1.region={}".format(region),
        "--product_infos.1.id=1",
        "--product_infos.1.subscription_num=1",
        "--product_infos.1.period_type={}".format(period_type),
        "--product_infos.1.period_num={}".format(period_num),
    ]
    if storage is not None:
        product_args += build_storage_product_for_period(
            2,
            region,
            storage["size_gb"],
            storage["resource_spec"],
            period_type,
            period_num,
        )
    cmd = bss_prefix + ["ListRateOnPeriodDetail"] + product_args
    try:
        payload = common.run_hcloud(cmd, timeout)
    except common.HcloudError as exc:
        warnings.append(
            "prepaid quote failed for {} (period {}/{}, BSS channel {}, "
            "instance region {}): {}".format(
                spec_code, period_type, period_num, BSS_REGION, region, exc
            )
        )
        return None, warnings
    result = parse_period(payload, period_type, period_num)
    if result is None:
        warnings.append(
            "prepaid quote failed for {} (period {}/{}): {}".format(
                spec_code,
                period_type,
                period_num,
                common.extract_error_message(payload),
            )
        )
    return result, warnings


def resolve_specs(
    args: argparse.Namespace,
    cmd_prefix: list[str],
    timeout: int,
) -> tuple[list[dict], list[str]]:
    """Resolve the flavors to quote via the spec-code or ListFlavors path.

    1. Use --spec-code directly when provided.
    2. Otherwise filter ListFlavors on vcpus/ram/group_type.
    3. Apply the --deploy-type filter, defaulting to single and ha.

    Args:
        args: argparse.Namespace — Parsed command line arguments.
        cmd_prefix: list[str] — Base RDS hcloud command prefix.
        timeout: int — Timeout in seconds for the subprocess call.

    Returns:
        tuple[list[dict], list[str]]: (spec list, warnings).

    Examples:
        # Requires hcloud credentials:
        # >>> resolve_specs(argparse.Namespace(), ["RDS"], 5)
        # ([], [])
    """
    warnings: list[str] = []
    if args.spec_code:
        return (
            [
                {
                    "spec_code": args.spec_code,
                    "instance_mode": "",
                    "vcpus": None,
                    "ram": None,
                }
            ],
            warnings,
        )
    try:
        payload = common.run_hcloud(
            cmd_prefix
            + [
                common.CMD_LIST_FLAVORS,
                "--database_name=MySQL",
                "--version_name={}".format(args.db_version),
            ],
            timeout,
        )
    except common.HcloudError as exc:
        warnings.append("ListFlavors failed: {}".format(exc))
        return [], warnings
    flavors = payload.get("flavors") or []
    matched = []
    for flavor in flavors:
        if str(flavor.get("vcpus", "")) == str(args.vcpus) and str(
            flavor.get("ram", "")
        ) == str(args.ram) and flavor.get("group_type", "") == args.group_type:
            instance_mode = flavor.get("instance_mode", "")
            if args.deploy_type:
                if instance_mode == args.deploy_type:
                    matched.append(flavor)
            elif instance_mode in ("single", "ha"):
                matched.append(flavor)
    if not matched:
        warnings.append(
            "no flavor matched vcpus={} ram={} group_type={} deploy_type={}".format(
                args.vcpus, args.ram, args.group_type, args.deploy_type or "single,ha"
            )
        )
    return (
        [
            {
                "spec_code": flavor.get("spec_code", ""),
                "instance_mode": flavor.get("instance_mode", ""),
                "vcpus": flavor.get("vcpus"),
                "ram": flavor.get("ram"),
            }
            for flavor in matched
        ],
        warnings,
    )


def derive_ha_spec_code(spec_code: str) -> str:
    """Derive the ha spec code from a single instance spec code.

    1. Replace a trailing .single suffix with .ha for ARM flavors.
    2. Otherwise append .ha for x86 flavors.

    Args:
        spec_code: str — The single instance spec code.

    Returns:
        str: The derived ha spec code.

    Examples:
        >>> derive_ha_spec_code("rds.mysql.x1.large.2")
        'rds.mysql.x1.large.2.ha'
        >>> derive_ha_spec_code("rds.mysql.large.arm2.single")
        'rds.mysql.large.arm2.ha'
    """
    if spec_code.endswith(".single"):
        return spec_code[: -len(".single")] + ".ha"
    return spec_code + ".ha"


def resolve_periods(args: argparse.Namespace) -> list[tuple[int, int]]:
    """Resolve the prepaid periods to quote.

    1. Use the --period-type/--period-num pair when --period-type is given.
    2. Otherwise return the default 1 month + 1 year pair list.

    Args:
        args: argparse.Namespace — Parsed command line arguments.

    Returns:
        list[tuple[int, int]]: (period_type, period_num) pairs.

    Examples:
        >>> resolve_periods(argparse.Namespace(period_type=None, period_num=1))
        [(2, 1), (3, 1)]
        >>> resolve_periods(argparse.Namespace(period_type=3, period_num=2))
        [(3, 2)]
    """
    if args.period_type is not None:
        return [(args.period_type, args.period_num)]
    return list(DEFAULT_PERIODS)


def run_compare(args: argparse.Namespace) -> int:
    """Run the single vs ha price comparison mode.

    1. Resolve the project id and build the BSS prefix.
    2. Derive the ha spec code from the single spec code.
    3. Quote both specs for on-demand and monthly/yearly periods, each
       carrying the storage product when --storage-size-gb is given.
    4. Compute the price delta and ha multiple, write the report.

    Args:
        args: argparse.Namespace — Parsed command line arguments.

    Returns:
        int: Exit code (0 with at least one successful quote, 1 otherwise).

    Examples:
        # Requires hcloud credentials:
        # >>> run_compare(args)
        1
    """
    try:
        project_id = common.resolve_project_id(args.region, common.DEFAULT_TIMEOUT)
        bss_prefix = make_bss_prefix(project_id)
    except common.HcloudError as exc:
        LOGGER.error("hcloud error: %s", exc)
        return 1

    single_spec = args.spec_code
    ha_spec = derive_ha_spec_code(single_spec)
    warnings: list[str] = []
    periods = resolve_periods(args)
    any_success_ref: list[bool] = [False]

    def storage_for(mode: str) -> dict | None:
        """Build the storage params for a mode, or None when skipped."""
        if args.storage_size_gb is None:
            return None
        resource_spec = resolve_storage_spec(args.storage_type, mode)
        if not resource_spec:
            warnings.append(
                "storage volume type {} has no mapping for mode {}; "
                "storage skipped".format(args.storage_type, mode)
            )
            return None
        return {
            "size_gb": args.storage_size_gb,
            "resource_spec": resource_spec,
            "storage_type": args.storage_type,
            "mode": mode,
        }

    def quote_spec(spec_code: str, mode: str) -> dict:
        """Quote on-demand and/or prepaid periods for one spec.

        1. Quote on-demand when --charge-mode is absent or postPaid.
        2. Quote the configured prepaid periods when --charge-mode is
           absent or prePaid.
        3. Return the spec result with the quoted lines kept null/empty
           for the filtered-out mode.

        Args:
            spec_code: str — The spec code to quote.
            mode: str — Deployment mode (single or ha) for storage.

        Returns:
            dict: The spec result dict.
        """
        storage = storage_for(mode)
        on_demand = None
        if args.charge_mode in (None, common.CHARGE_MODE_POSTPAID):
            on_demand, on_warnings = quote_on_demand(
                bss_prefix, args.region, spec_code, storage, common.DEFAULT_TIMEOUT
            )
            warnings.extend(on_warnings)
            if on_demand is not None:
                any_success_ref[0] = True
        period_pricing = []
        if args.charge_mode in (None, common.CHARGE_MODE_PREPAID):
            for period_type, period_num in periods:
                period_result, period_warnings = quote_period(
                    bss_prefix,
                    args.region,
                    spec_code,
                    period_type,
                    period_num,
                    common.DEFAULT_TIMEOUT,
                    storage,
                )
                warnings.extend(period_warnings)
                if period_result is not None:
                    any_success_ref[0] = True
                period_pricing.append(period_result)
        return {
            "spec_code": spec_code,
            "on_demand": on_demand,
            "period_pricing": period_pricing,
        }

    single_result = quote_spec(single_spec, "single")
    ha_result = quote_spec(ha_spec, "ha")
    any_success = any_success_ref[0]

    # Compute the delta and multiple from the true on-demand amount first,
    # then the first successfully quoted period (monthly preferred, then
    # yearly), each using the spec total.
    price_delta = None
    ha_multiple = None
    if single_result["on_demand"] and ha_result["on_demand"]:
        single_amount = single_result["on_demand"].get("total")
        ha_amount = ha_result["on_demand"].get("total")
        if single_amount is not None and ha_amount is not None:
            price_delta, ha_multiple = compute_delta_multiple(
                single_amount, ha_amount
            )
    if price_delta is None:
        for period_type, period_num in periods:
            single_period = next(
                (p for p in single_result["period_pricing"]
                 if p and p.get("period_type") == period_type
                 and p.get("period_num") == period_num),
                None,
            )
            ha_period = next(
                (p for p in ha_result["period_pricing"]
                 if p and p.get("period_type") == period_type
                 and p.get("period_num") == period_num),
                None,
            )
            if single_period and ha_period:
                single_amount = single_period.get("total")
                ha_amount = ha_period.get("total")
                if single_amount is not None and ha_amount is not None:
                    price_delta, ha_multiple = compute_delta_multiple(
                        single_amount, ha_amount
                    )
                    if price_delta is not None:
                        break

    report = build_compare_report(args, single_spec, ha_spec, single_result,
                                  ha_result, price_delta, ha_multiple, warnings)
    write_result = common.write_report(report, args.output, common.timestamp_now())
    if write_result != 0:
        return 1
    if not any_success:
        LOGGER.error("all price quotes failed; no usable result.")
        return 1
    return 0


def compute_delta_multiple(
    single_amount: str | float | None,
    ha_amount: str | float | None,
) -> tuple[str | None, str | None]:
    """Format the ha/single price delta and multiple from two amounts.

    1. Parse both amounts as floats and format the delta and ratio.
    2. Return (None, None) when either amount is missing or unparsable.

    Args:
        single_amount: str | float | None — The single spec amount.
        ha_amount: str | float | None — The ha spec amount.

    Returns:
        tuple[str | None, str | None]: (price_delta, ha_multiple).

    Examples:
        >>> compute_delta_multiple("0.62", "1.168")
        ('0.55', '1.88')
        >>> compute_delta_multiple(None, "1.168")
        (None, None)
    """
    if single_amount is None or ha_amount is None:
        return None, None
    try:
        price_delta = "{:.2f}".format(float(ha_amount) - float(single_amount))
        ha_multiple = "{:.2f}".format(float(ha_amount) / float(single_amount))
    except (TypeError, ValueError, ZeroDivisionError):
        return None, None
    return price_delta, ha_multiple


def build_compare_report(
    args: argparse.Namespace,
    single_spec: str,
    ha_spec: str,
    single_result: dict,
    ha_result: dict,
    price_delta: str | None,
    ha_multiple: str | None,
    warnings: list[str],
) -> dict:
    """Build the compare-mode structured JSON report payload.

    1. Fill the metadata and query_params sections.
    2. Attach single/ha results, delta, multiple and scope note.

    Args:
        args: argparse.Namespace — Parsed command line arguments.
        single_spec: str — The single instance spec code.
        ha_spec: str — The derived ha spec code.
        single_result: dict — The single spec quote result.
        ha_result: dict — The ha spec quote result.
        price_delta: str | None — The formatted price delta.
        ha_multiple: str | None — The formatted ha/single multiple.
        warnings: list[str] — Collected warnings.

    Returns:
        dict: The compare report payload.

    Examples:
        >>> report = build_compare_report(argparse.Namespace(region="cn-north-4", db_version="8.0",
        ...     spec_code="x", deploy_type=None, period_type=None, period_num=1,
        ...     storage_size_gb=None, storage_type="GPSSD", charge_mode=None),
        ...     "x", "x.ha", {"spec_code": "x", "on_demand": {}, "period_pricing": []},
        ...     {"spec_code": "x.ha", "on_demand": {}, "period_pricing": []},
        ...     None, None, [])
        >>> report["query_params"]["compare_single_ha"] is True
        True
        >>> report["query_params"]["charge_mode"] is None
        True
    """
    storage_included = args.storage_size_gb is not None and any(
        (r.get("on_demand") and r["on_demand"].get("storage") is not None)
        or any(
            p and p.get("storage") is not None
            for p in (r.get("period_pricing") or [])
        )
        for r in (single_result, ha_result)
    )
    storage_specs = {}
    if args.storage_size_gb is not None:
        single_spec_resolved = resolve_storage_spec(args.storage_type, "single")
        ha_spec_resolved = resolve_storage_spec(args.storage_type, "ha")
        if single_spec_resolved:
            storage_specs["single"] = single_spec_resolved
        if ha_spec_resolved:
            storage_specs["ha"] = ha_spec_resolved
    return {
        "metadata": {
            "script": "rds_cost_estimate",
            "version": "1.0",
            "region": args.region,
            "db_version": args.db_version,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        },
        "query_params": {
            "compare_single_ha": True,
            "single_spec_code": single_spec,
            "ha_spec_code": ha_spec,
            "periods": resolve_periods(args),
            "storage_size_gb": args.storage_size_gb,
            "storage_type": args.storage_type,
            "storage_specs": storage_specs,
            "charge_mode": args.charge_mode,
        },
        "single_price": single_result,
        "ha_price": ha_result,
        "price_delta": price_delta,
        "ha_multiple": ha_multiple,
        "scope_note": (
            "prices cover the compute flavor and the instance storage "
            "volume; storage is quoted per spec (single and ha differ) and "
            "is included in the totals"
            if storage_included
            else "prices cover the compute flavor only; storage was not "
            "quoted because no --storage-size-gb was given or the volume "
            "type could not be mapped"
        ),
        "warnings": warnings,
    }


def run(args: argparse.Namespace) -> int:
    """Resolve the project id, quote all prices and write the report.

    1. Resolve the region project id via KeystoneListAuthProjects.
    2. Resolve the flavors to quote.
    3. Quote on-demand (and storage when requested) and prepaid prices.
    4. Write the structured JSON report and return the exit code.

    Args:
        args: argparse.Namespace — Parsed command line arguments.

    Returns:
        int: Exit code (0 with at least one successful quote, 1 otherwise).

    Examples:
        # Requires hcloud credentials:
        # >>> run(args)
        1
    """
    if args.compare_single_ha:
        return run_compare(args)

    try:
        project_id = common.resolve_project_id(args.region, common.DEFAULT_TIMEOUT)
        bss_prefix = make_bss_prefix(project_id)
        cmd_prefix = common.make_rds_prefix(args.region, project_id)
    except common.HcloudError as exc:
        LOGGER.error("hcloud error: %s", exc)
        return 1

    warnings: list[str] = []
    specs, resolve_warnings = resolve_specs(args, cmd_prefix, common.DEFAULT_TIMEOUT)
    warnings.extend(resolve_warnings)
    if not specs:
        report = build_report(args, [], warnings)
        return common.write_report(report, args.output, common.timestamp_now())

    storage = None
    if args.storage_size_gb is not None:
        resource_spec = resolve_storage_spec(args.storage_type, "single")
        if not resource_spec:
            warnings.append(
                "storage volume type {} has no mapping; storage skipped".format(
                    args.storage_type
                )
            )
        else:
            storage = {
                "size_gb": args.storage_size_gb,
                "resource_spec": resource_spec,
                "storage_type": args.storage_type,
                "mode": "single",
            }
            warnings.append(
                "storage volume ({} GB, resource_spec={}) was merged into the "
                "on-demand total; it was not quoted separately".format(
                    args.storage_size_gb, resource_spec
                )
            )

    periods = resolve_periods(args)
    results: list[dict] = []
    any_success = False
    for spec in specs:
        spec_code = spec["spec_code"]
        on_demand = None
        if args.charge_mode in (None, common.CHARGE_MODE_POSTPAID):
            on_demand, on_warnings = quote_on_demand(
                bss_prefix, args.region, spec_code, storage, common.DEFAULT_TIMEOUT
            )
            warnings.extend(on_warnings)
            if on_demand is not None:
                any_success = True
        period_pricing = []
        if args.charge_mode in (None, common.CHARGE_MODE_PREPAID):
            for period_type, period_num in periods:
                period_result, period_warnings = quote_period(
                    bss_prefix,
                    args.region,
                    spec_code,
                    period_type,
                    period_num,
                    common.DEFAULT_TIMEOUT,
                )
                warnings.extend(period_warnings)
                if period_result is not None:
                    any_success = True
                period_pricing.append(period_result)
        results.append(
            {
                "spec_code": spec_code,
                "instance_mode": spec["instance_mode"],
                "vcpus": spec["vcpus"],
                "ram": spec["ram"],
                "on_demand": on_demand,
                "period_pricing": period_pricing,
                "storage_pricing": None,
            }
        )

    report = build_report(args, results, warnings)
    write_result = common.write_report(report, args.output, common.timestamp_now())
    if write_result != 0:
        return 1
    if not any_success:
        LOGGER.error("all price quotes failed; no usable result.")
        return 1
    return 0


def build_report(
    args: argparse.Namespace, results: list[dict], warnings: list[str]
) -> dict:
    """Build the structured JSON report payload.

    1. Fill the metadata section from the run context.
    2. Fill the query_params section for reproducibility.
    3. Attach the results array and the warnings array.

    Args:
        args: argparse.Namespace — Parsed command line arguments.
        results: list[dict] — Per-spec quote results.
        warnings: list[str] — Collected warnings.

    Returns:
        dict: The report payload.

    Examples:
        >>> report = build_report(argparse.Namespace(region="cn-north-4", db_version="8.0",
        ...     spec_code="x", deploy_type=None, period_type=None, period_num=1,
        ...     storage_size_gb=None, storage_type="GPSSD", charge_mode=None), [], [])
        >>> report["query_params"]["spec_code"] == "x"
        True
        >>> report["query_params"]["charge_mode"] is None
        True
    """
    return {
        "metadata": {
            "script": "rds_cost_estimate",
            "version": "1.0",
            "region": args.region,
            "db_version": args.db_version,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        },
        "query_params": {
            "spec_code": args.spec_code,
            "deploy_type": args.deploy_type,
            "periods": resolve_periods(args),
            "storage_size_gb": args.storage_size_gb,
            "storage_type": args.storage_type,
            "charge_mode": args.charge_mode,
        },
        "results": results,
        "warnings": warnings,
    }


def resolve_default_output() -> str:
    """Resolve the default output path in the script directory.

    1. Join the script directory with the timestamped file name.

    Args:
        None

    Returns:
        str: Absolute default output file path.

    Examples:
        >>> resolve_default_output().endswith("rds_cost_estimate_result_")
        True
    """
    return os.path.join(
        common.SCRIPT_DIR,
        DEFAULT_OUTPUT_PREFIX.format(ts=common.timestamp_now()),
    )


def main() -> int:
    """Run the cost estimation workflow.

    1. Parse arguments and validate the spec input.
    2. Set up logging and delegate to run().

    Args:
        None

    Returns:
        int: Exit code (0 on success, 1 on failure, 2 on invalid arguments).

    Examples:
        # Running the script requires hcloud credentials:
        # >>> main()
        1
    """
    parser = build_arg_parser()
    args = parser.parse_args()
    validate_spec_input(parser, args)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        stream=sys.stderr,
    )
    return run(args)


if __name__ == "__main__":
    sys.exit(main())
