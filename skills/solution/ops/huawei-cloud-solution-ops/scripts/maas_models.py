#!/usr/bin/env python3
"""Inspect Huawei Cloud MaaS model support from local catalog or MaaS API."""

from __future__ import annotations

import argparse
from typing import Any

import hcloud_common
import maas_common

CATALOG_PATH = hcloud_common.REFERENCES_DIR / "maas-model-catalog.json"
MODELS_PATH = "/v2/models"


def load_catalog() -> dict[str, Any]:
    """Load the curated local MaaS model catalog."""
    if not CATALOG_PATH.exists():
        return {"schema_version": 1, "models": []}
    return hcloud_common.load_json(CATALOG_PATH)


def filter_models(catalog: dict[str, Any], capability: str | None = None, model: str | None = None) -> list[dict[str, Any]]:
    """Filter local model entries by capability or model id/name."""
    models = [item for item in catalog.get("models", []) if isinstance(item, dict)]
    if capability:
        needle = capability.lower()
        models = [
            item
            for item in models
            if needle in {str(value).lower() for value in item.get("capabilities", [])}
            or needle == str(item.get("model_type", "")).lower()
        ]
    if model:
        needle = model.lower()
        models = [
            item
            for item in models
            if needle in {str(item.get("model", "")).lower(), str(item.get("name", "")).lower()}
        ]
    return models


def build_local_result(args: argparse.Namespace) -> dict[str, Any]:
    """Build a local catalog lookup result."""
    catalog = load_catalog()
    matches = filter_models(catalog, capability=args.capability, model=args.model)
    return {
        "success": True,
        "source": "local_catalog",
        "catalog_version": catalog.get("schema_version"),
        "doc_version": catalog.get("doc_version"),
        "filters": {"capability": args.capability, "model": args.model},
        "count": len(matches),
        "models": matches,
        "boundary": "Local catalog is a curated aid. Check MaaS console or --online for live availability before production use.",
    }


def build_online_plan(args: argparse.Namespace) -> dict[str, Any]:
    """Build a non-executing online model-list request plan."""
    return {
        "success": True,
        "source": "online_plan",
        "endpoint": maas_common.endpoint_url(MODELS_PATH, args.base_url),
        "method": "GET",
        "requires_api_key_env": list(maas_common.MAAS_API_KEY_ENV_NAMES),
        "api_key_presence": maas_common.api_key_presence(),
        "execute_hint": "Pass --online --execute to call GET /v2/models.",
        "boundary": "This plan does not call MaaS or reveal API keys.",
    }


def execute_online(args: argparse.Namespace) -> dict[str, Any]:
    """Call MaaS GET /v2/models."""
    api_key = maas_common.get_api_key()
    response = maas_common.request_json("GET", MODELS_PATH, api_key=api_key, timeout=args.timeout, base_url=args.base_url)
    return {
        "success": True,
        "source": "online",
        **maas_common.response_metadata(response),
        "response": response["body"],
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capability", help="Filter local catalog by capability, such as text, vision, image_generation, or video_generation.")
    parser.add_argument("--model", help="Filter local catalog by exact model parameter or display name.")
    parser.add_argument("--online", action="store_true", help="Plan or execute live GET /v2/models instead of local catalog only.")
    parser.add_argument("--execute", action="store_true", help="Actually call MaaS when --online is set.")
    parser.add_argument("--base-url", default=maas_common.DEFAULT_MAAS_BASE_URL, help="MaaS API base URL.")
    parser.add_argument("--timeout", type=int, default=60, help="HTTP timeout in seconds.")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Run MaaS model lookup."""
    try:
        args = parse_args(argv)
        if args.online:
            result = execute_online(args) if args.execute else build_online_plan(args)
        else:
            result = build_local_result(args)
        hcloud_common.emit_json(result, pretty=args.pretty)
        return 0
    except Exception as exc:
        hcloud_common.emit_json({"success": False, "error": str(exc)})
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
