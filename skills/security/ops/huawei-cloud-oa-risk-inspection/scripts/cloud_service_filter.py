#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Shared cloud-service whitelist resolution for the inspection scripts.

Overview:
    This module resolves the user-supplied cloud-service whitelist used by
    `oa_risk_inspection.py`, `merge_inspection_results.py` and
    `merge_report_generator.py`, so that alias lookup, normalisation and
    record matching live in exactly one place instead of being duplicated
    across the three scripts.

Detailed Description:
    1. The alias table `references/cloud_services.json` maps each cloud
       service code to a list of aliases (Chinese name, English name,
       abbreviation and the code itself). A missing table degrades to
       literal code matching with a WARNING; a table that cannot be parsed,
       or one where a single alias resolves to two different codes, is a
       hard error because it would otherwise silently pick a wrong scope.
    2. Tokens are normalised with NFKC (full-width to half-width), whitespace
       collapse and case folding. The same normalisation is applied to the
       record side, because OA passes `service_type_code` through unchanged
       while Config and SecMaster lowercase it.
    3. The alias table is the single authority for the inspectable service
       scope: a token absent from it is reported as unsupported instead of
       being used as its own code. A newly launched cloud service therefore
       needs a table entry before it can be requested by name. The only
       exception is a missing table file, which degrades to literal code
       matching with a WARNING so a broken install still runs.
    4. Record matching prefers `service_type_code` and falls back to
       `summary.check_item_service`. A record with neither value is
       "unclassified": it is excluded under any whitelist and counted
       separately, never attached to a guessed service.
    5. A service is "matched" only when at least one record carries it; the
       caller uses that to decide between degrading (some services matched)
       and failing (no service matched).
    6. The same resolution also supplies the display name used by the report
       charts and the HTML service filter, so grouping, filtering and
       labelling can never disagree about what counts as one product.

Workflow:
    1. Load the alias table (optional path override) into a normalised
       alias -> code map plus a code -> display name map.
    2. Parse the comma-separated `--cloud-services` value into requested
       inputs, resolved pairs, the deduplicated service code list and the
       tokens the table does not cover.
    3. Classify a requested value as supported / unsupported for the
       pre-collection check, without touching any record.
    4. Match records against the resolved service set and accumulate the
       per-source matched / excluded / unclassified counters.

Dependencies:
    Python standard library only: json, logging, unicodedata, pathlib, typing.
    No third-party dependency; the module is purely local and never calls
    hcloud or accesses the network.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import unicodedata
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


logger = logging.getLogger(__name__)

# Alias table location: references/cloud_services.json of the project root
# (the parent of the scripts directory).
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
ALIAS_FILE_NAME = "cloud_services.json"
ALIAS_FILE_PATH = PROJECT_ROOT / "references" / ALIAS_FILE_NAME
# Record-level match outcomes returned by classify_record_service.
MATCH_MATCHED = "matched"
MATCH_EXCLUDED = "excluded"
MATCH_UNCLASSIFIED = "unclassified"


def normalize_token(value: str) -> str:
    """Normalise a cloud-service token or record value for comparison.

    1. Return an empty string for empty input.
    2. Apply NFKC so full-width characters become half-width.
    3. Collapse internal whitespace runs and strip the ends.
    4. Case-fold the result so `ECS`, `ecs` and `EcS` compare equal.

    Args:
        value: str — A user-supplied token or a record service value.

    Returns:
        str: The normalised token, or an empty string for empty input.

    Examples:
        >>> normalize_token("  ＥＣＳ ")
        'ecs'
        >>> normalize_token("Elastic  Cloud Server")
        'elastic cloud server'
    """
    if not value:
        return ""
    try:
        folded = unicodedata.normalize("NFKC", " ".join(str(value).split())).strip()
    except Exception:
        folded = str(value).strip()
    return folded.casefold()


def resolve_service_code(token: str, alias_map: Dict[str, str]) -> str:
    """Resolve one cloud-service token to its canonical code.

    1. Return an empty string for empty input.
    2. Normalise the token with `normalize_token`.
    3. Return the alias-table code, or an empty string when the table does
       not cover the token — the table is the authority on what can be
       inspected, so no token falls back to itself.

    Args:
        token: str — A user-supplied identifier or a record service value.
        alias_map: dict[str, str] — Normalised alias to code map.

    Returns:
        str: The canonical code, or an empty string when unsupported.

    Examples:
        >>> resolve_service_code("HECS", {"hecs": "ecs"})
        'ecs'
        >>> resolve_service_code("zzz", {"hecs": "ecs"})
        ''
    """
    normalized = normalize_token(token)
    if not normalized:
        return ""
    return alias_map.get(normalized, "")


def build_display_name_map(alias_map: Dict[str, str],
                           file_path: Optional[Path] = None) -> Dict[str, str]:
    """Build the code -> display name map used by the report and the filter.

    1. Read the alias table entries again to reach each entry's first name.
    2. Keep the first name verbatim, so `iDME` and `CloudTable` stay in their
       official spelling instead of becoming `IDME` / `CLOUDTABLE`.
    3. Return an empty map when the table is unavailable, letting the caller
       fall back to an upper-cased code.

    Args:
        alias_map: dict[str, str] — Normalised alias to code map; when empty
            the display map is empty too.
        file_path: Optional[Path] — Alias table path; defaults to the
            project table.

    Returns:
        dict[str, str]: Canonical code to its first alias name.

    Examples:
        # >>> build_display_name_map(load_alias_map())["ecs"]
        # 'ECS'
    """
    if not alias_map:
        return {}
    target = Path(file_path) if file_path else ALIAS_FILE_PATH
    try:
        entries = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    display: Dict[str, str] = {}
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        code = normalize_token(str(entry.get("code", "") or ""))
        names = entry.get("names") or []
        if not code or not isinstance(names, list):
            continue
        for name in names:
            text = str(name).strip()
            if text:
                display[code] = text
                break
    return display


def display_service_name(code: str, display_map: Dict[str, str]) -> str:
    """Derive the label shown for one canonical cloud-service code.

    1. Return an empty string for empty input.
    2. Return the alias table's first name for the code when it exists.
    3. Otherwise upper-case the normalised code, so an entry missing from the
       table still renders a stable label.

    Args:
        code: str — A canonical code or a raw service value.
        display_map: dict[str, str] — Map from build_display_name_map.

    Returns:
        str: The display label.

    Examples:
        >>> display_service_name("idme", {"idme": "iDME"})
        'iDME'
        >>> display_service_name("zzz", {})
        'ZZZ'
    """
    normalized = normalize_token(code)
    if not normalized:
        return ""
    return display_map.get(normalized) or normalized.upper()


def load_alias_map(file_path: Optional[Path] = None) -> Dict[str, str]:
    """Load the cloud-service alias table into a normalised token -> code map.

    1. Read and parse the JSON file; return an empty map with a WARNING when
       the file does not exist, so literal code matching still works.
    2. Raise a ValueError when the file cannot be read, is not valid JSON, or
       is not a list of objects carrying `code` and `names`.
    3. Register every alias and the code itself under its normalised form.
    4. Raise a ValueError when one normalised token maps to two different
       codes, because choosing either would silently narrow the scope.

    Args:
        file_path: Optional[Path] — Alias table path; defaults to
            references/cloud_services.json under the project root.

    Returns:
        dict[str, str]: Normalised alias token to cloud-service code.

    Raises:
        ValueError: The table is unreadable, malformed, or ambiguous.

    Examples:
        # >>> load_alias_map(Path("references/cloud_services.json"))["弹性云服务器"]
        # 'ecs'
    """
    target = Path(file_path) if file_path else ALIAS_FILE_PATH
    if not target.exists():
        logger.warning(
            "Cloud service alias table not found (%s); matching cloud services by literal code only.",
            target,
        )
        return {}
    try:
        raw_text = target.read_text(encoding="utf-8")
    except OSError as exc:
        raise ValueError(
            "Cloud service alias table cannot be read: {} ({})".format(target, exc)
        ) from exc
    try:
        entries = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise ValueError(
            "Cloud service alias table is not valid JSON: {} ({})".format(target, exc)
        ) from exc
    if not isinstance(entries, list):
        raise ValueError(
            "Cloud service alias table must contain a JSON list: {}".format(target)
        )
    alias_map: Dict[str, str] = {}
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError(
                "Cloud service alias table entry must be a JSON object: {}".format(target)
            )
        code = normalize_token(str(entry.get("code", "") or ""))
        if not code:
            raise ValueError(
                "Cloud service alias table entry has an empty code: {}".format(target)
            )
        names = entry.get("names", []) or []
        if not isinstance(names, list):
            raise ValueError(
                "Cloud service alias table entry 'names' must be a list: {}".format(target)
            )
        tokens = [code] + [str(name) for name in names]
        for token in tokens:
            normalized = normalize_token(token)
            if not normalized:
                continue
            existing = alias_map.get(normalized)
            if existing and existing != code:
                raise ValueError(
                    "Cloud service alias '{}' resolves to both '{}' and '{}': {}".format(
                        token, existing, code, target
                    )
                )
            alias_map[normalized] = code
    return alias_map


def classify_supported_services(raw_value: str,
                                alias_map: Dict[str, str]) -> Dict[str, Any]:
    """Classify a requested cloud-service list as supported or unsupported.

    1. Split the raw value on commas and drop blank segments, keeping the
       caller's wording untouched for reporting.
    2. Resolve each token through the alias table; a token the table does not
       cover is unsupported, never adopted as its own code.
    3. Collect the deduplicated codes of the supported tokens in first-seen
       order, plus every code the table can currently resolve so the caller
       can show what is inspectable.

    Args:
        raw_value: str — The raw comma-separated user wording.
        alias_map: dict[str, str] — Normalised alias to code map.

    Returns:
        dict[str, Any]: `supported` (`input` / `code` pairs), `unsupported`
            (the raw wordings), `requested` and `available` (all codes).

    Examples:
        >>> classify_supported_services("ECS,XYZ", {"ecs": "ecs"})["unsupported"]
        ['XYZ']
        >>> classify_supported_services("XYZ", {"ecs": "ecs"})["supported"]
        []
    """
    requested = [part.strip() for part in str(raw_value or "").split(",")]
    requested = [part for part in requested if part]
    supported: List[Dict[str, str]] = []
    unsupported: List[str] = []
    codes: List[str] = []
    for token in requested:
        code = resolve_service_code(token, alias_map)
        if not code:
            unsupported.append(token)
            continue
        supported.append({"input": token, "code": code})
        if code not in codes:
            codes.append(code)
    available: List[str] = []
    for code in alias_map.values():
        if code and code not in available:
            available.append(code)
    available.sort()
    return {
        "requested": requested,
        "supported": supported,
        "unsupported": unsupported,
        "services": codes,
        "available": available,
    }


def parse_cloud_services(raw_value: str, alias_map: Dict[str, str]) -> Dict[str, Any]:
    """Resolve a comma-separated `--cloud-services` value.

    1. Split on commas and drop blank segments.
    2. Normalise each token and look it up in the alias map; a token the
       table does not cover is unsupported and contributes no code.
    3. Deduplicate the resolved codes while keeping first-seen order.
    4. Raise a ValueError when nothing remains, so a typo never widens the
       run back to the whole tenant.

    Args:
        raw_value: str — The raw comma-separated command-line value.
        alias_map: dict[str, str] — Normalised alias to code map, possibly
            empty when the alias table is unavailable.

    Returns:
        dict[str, Any]: A dict with `requested` (raw segments), `resolved`
            (`input` / `code` pairs), `services` (deduplicated codes) and
            `unsupported` (tokens the table does not cover).

    Raises:
        ValueError: The value contains no usable token.

    Examples:
        >>> parse_cloud_services("ECS, 弹性云服务器", {"ecs": "ecs", "弹性云服务器": "ecs"})["services"]
        ['ecs']
        >>> parse_cloud_services("ECS,zzz", {"ecs": "ecs"})["unsupported"]
        ['zzz']
    """
    requested: List[str] = [part.strip() for part in str(raw_value or "").split(",")]
    requested = [part for part in requested if part]
    if not requested:
        raise ValueError(
            "The --cloud-services value contains no cloud service; "
            "refusing to fall back to a full-tenant inspection."
        )
    resolved: List[Dict[str, str]] = []
    services: List[str] = []
    unsupported: List[str] = []
    for token in requested:
        code = resolve_service_code(token, alias_map)
        if not code:
            unsupported.append(token)
            continue
        resolved.append({"input": token, "code": code})
        if code not in services:
            services.append(code)
    if not services:
        raise ValueError(
            "The --cloud-services value contains no cloud service; "
            "refusing to fall back to a full-tenant inspection."
        )
    return {
        "requested": requested,
        "resolved": resolved,
        "services": services,
        "unsupported": unsupported,
    }


def record_service_value(record: Dict[str, Any]) -> str:
    """Derive the cloud-service value of one record.

    1. Return the record `service_type_code` when non-empty.
    2. Fall back to `summary.check_item_service` when present.
    3. Return an empty string when neither is available.

    Args:
        record: dict[str, Any] — One OA-format inspection record.

    Returns:
        str: The raw (un-normalised) cloud-service value.

    Examples:
        >>> record_service_value({"service_type_code": "ecs"})
        'ecs'
        >>> record_service_value({"summary": {"check_item_service": "RDS"}})
        'RDS'
    """
    direct = record.get("service_type_code") or ""
    if direct:
        return str(direct)
    summary = record.get("summary") or {}
    fallback = summary.get("check_item_service") or ""
    return str(fallback)


def classify_record_service(record: Dict[str, Any], services: List[str]) -> str:
    """Classify one record against the resolved cloud-service whitelist.

    1. Derive the record service value; an empty value means the record is
       unclassified and cannot be attributed to any requested service.
    2. Resolve the value to its canonical code through the alias table, so a
       historical spelling the table folds onto a product (`hecs` -> `ecs`)
       matches a request for that product. This is the same resolution the
       report charts and the HTML filter use, keeping all three verdicts
       identical; a value the table does not cover falls back to its own
       normalised form, which is how an unmapped service still matches itself.
    3. Return matched / excluded / unclassified for the caller to count.

    Args:
        record: dict[str, Any] — One OA-format inspection record.
        services: list[str] — The resolved cloud-service code list.

    Returns:
        str: One of matched / excluded / unclassified.

    Examples:
        >>> classify_record_service({"service_type_code": "ECS"}, ["ecs"])
        'matched'
        >>> classify_record_service({"service_type_code": "hecs"}, ["ecs"])
        'matched'
        >>> classify_record_service({"service_type_code": "rds"}, ["ecs"])
        'excluded'
        >>> classify_record_service({}, ["ecs"])
        'unclassified'
    """
    raw_value = record_service_value(record)
    normalized = normalize_token(raw_value)
    if not normalized:
        return MATCH_UNCLASSIFIED
    alias_map = _cached_alias_map()
    record_code = resolve_service_code(raw_value, alias_map) or normalized
    allowed = {
        resolve_service_code(code, alias_map) or normalize_token(code)
        for code in services
    }
    return MATCH_MATCHED if record_code in allowed else MATCH_EXCLUDED


_CACHED_ALIAS_MAP: Optional[Dict[str, str]] = None


def _cached_alias_map() -> Dict[str, str]:
    """Return the default alias map, loading it at most once per process.

    1. Return the cached map when a previous call already loaded it.
    2. Otherwise load the project table and cache it, so per-record
       classification does not re-read the JSON file for every record.

    Args:
        None

    Returns:
        dict[str, str]: Normalised alias to canonical code.

    Examples:
        # >>> _cached_alias_map()["ecs"]
        # 'ecs'
    """
    global _CACHED_ALIAS_MAP
    if _CACHED_ALIAS_MAP is None:
        _CACHED_ALIAS_MAP = load_alias_map()
    return _CACHED_ALIAS_MAP


def new_match_counters() -> Dict[str, Any]:
    """Create the empty counter structure used while filtering.

    1. Seed the per-source excluded and unclassified maps for the three
       sources, so the merge metadata always carries every key.
    2. Track which requested services were seen at least once.

    Args:
        None

    Returns:
        dict[str, Any]: A dict with `excluded_by_service`,
            `excluded_unclassified`, `matched` and `seen_services`.

    Examples:
        >>> new_match_counters()["excluded_by_service"]
        {'oa': 0, 'config': 0, 'secmaster': 0}
    """
    return {
        "excluded_by_service": {"oa": 0, "config": 0, "secmaster": 0},
        "excluded_unclassified": {"config": 0, "secmaster": 0},
        "matched": 0,
        "seen_services": [],
    }


def accumulate_match(counters: Dict[str, Any], source_key: str,
                     outcome: str, record: Dict[str, Any]) -> None:
    """Accumulate one record's match outcome into the counter structure.

    1. Return immediately for a matched record, remembering its service so
       the caller can report which requested services were actually seen.
    2. Count an excluded record under its source.
    3. Count an unclassified record under its source when the source has an
       unclassified bucket (OA check items always carry a service code, so
       only Config and SecMaster are tracked).

    Args:
        counters: dict[str, Any] — The structure from new_match_counters.
        source_key: str — One of oa / config / secmaster.
        outcome: str — One of matched / excluded / unclassified.
        record: dict[str, Any] — The classified record.

    Returns:
        None

    Examples:
        >>> counters = new_match_counters()
        >>> accumulate_match(counters, "oa", "matched", {"service_type_code": "ecs"})
        >>> counters["seen_services"]
        ['ecs']
    """
    if outcome == MATCH_MATCHED:
        counters["matched"] = counters.get("matched", 0) + 1
        service = normalize_token(record_service_value(record))
        seen = counters.setdefault("seen_services", [])
        if service and service not in seen:
            seen.append(service)
        return
    if outcome == MATCH_EXCLUDED:
        buckets = counters.setdefault("excluded_by_service", {})
        buckets[source_key] = buckets.get(source_key, 0) + 1
        return
    buckets = counters.setdefault("excluded_unclassified", {})
    if source_key in buckets:
        buckets[source_key] = buckets.get(source_key, 0) + 1


def build_filter_metadata(parsed: Dict[str, Any],
                          counters: Dict[str, Any]) -> Dict[str, Any]:
    """Assemble the `meta.cloud_service_filter` block.

    1. Copy the requested inputs, resolved pairs and resolved service list.
    2. Compute the unmatched services as those never seen in any record.
    3. Attach the per-source exclusion counters.

    Args:
        parsed: dict[str, Any] — The structure from parse_cloud_services.
        counters: dict[str, Any] — The structure from new_match_counters.

    Returns:
        dict[str, Any]: The metadata block written to the merged output.

    Examples:
        # >>> build_filter_metadata({"requested": ["ECS"], "resolved": [], "services": ["ecs"]}, new_match_counters())["unmatched"]
        # ['ecs']
    """
    services = list(parsed.get("services", []))
    seen = set(counters.get("seen_services", []))
    unmatched = [code for code in services if normalize_token(code) not in seen]
    return {
        "requested": list(parsed.get("requested", [])),
        "resolved": list(parsed.get("resolved", [])),
        "services": services,
        "unmatched": unmatched,
        "excluded_by_service": dict(counters.get("excluded_by_service", {})),
        "excluded_unclassified": dict(counters.get("excluded_unclassified", {})),
    }


def build_probe_parser() -> argparse.ArgumentParser:
    """Build the command-line parser for the support-set probe.

    1. Register the same `--cloud-services` option the inspection scripts
       accept, so the probe sees the user's wording verbatim.
    2. Register an optional `--alias-file` so a test can point at a fixture
       table instead of the shipped one.

    Args:
        None

    Returns:
        argparse.ArgumentParser: The configured parser.

    Examples:
        >>> build_probe_parser().parse_args(["--cloud-services", "ECS"]).cloud_services
        'ECS'
    """
    parser = argparse.ArgumentParser(
        prog="cloud_service_filter",
        description="Report which requested cloud services can be inspected")
    parser.add_argument("--cloud-services", required=True,
                        help="Required. Comma-separated cloud service identifiers")
    parser.add_argument("--alias-file", default=None,
                        help="Optional. Alias table path override (default: the project table)")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    """Print the support-set verdict for the requested cloud services.

    1. Parse the arguments and load the alias table, reporting a table that
       cannot be loaded as a hard failure because the verdict would be wrong.
    2. Classify every requested token as supported or unsupported.
    3. Print the verdict as JSON on stdout so the caller can read it without
       parsing log lines, and return 0 even when some services are
       unsupported — the caller decides whether to continue.

    Args:
        argv: Optional[list[str]] — Argument list override; defaults to the
            process arguments.

    Returns:
        int: Process exit code: 0 on a completed verdict, 1 when the alias
            table cannot be loaded or no service was requested.

    Examples:
        # >>> main(["--cloud-services", "ECS,XYZ"])
        # 0
    """
    args = build_probe_parser().parse_args(argv)
    try:
        alias_map = load_alias_map(Path(args.alias_file) if args.alias_file else None)
    except ValueError as exc:
        logger.error("Cloud service alias table cannot be used: %s", exc)
        return 1
    verdict = classify_supported_services(args.cloud_services, alias_map)
    if not verdict["requested"]:
        logger.error("The --cloud-services value contains no cloud service.")
        return 1
    print(json.dumps(verdict, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
