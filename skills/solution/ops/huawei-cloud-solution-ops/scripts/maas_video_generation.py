#!/usr/bin/env python3
"""Create, query, and wait for Huawei Cloud MaaS video generation tasks."""

from __future__ import annotations

import argparse
import time
from pathlib import Path
from typing import Any

import hcloud_common
import maas_common

VIDEO_GENERATIONS_PATH = "/v1/video/generations"
DEFAULT_TEXT_TO_VIDEO_MODEL = "Wan2.2-T2V-A14B"
DEFAULT_IMAGE_TO_VIDEO_MODEL = "Wan2.2-I2V-A14B"
TERMINAL_STATUSES = {"succeeded", "failed"}


def parse_key_values(values: list[str]) -> dict[str, Any]:
    """Parse repeated key=value pairs into a dictionary."""
    parsed: dict[str, Any] = {}
    for item in values:
        if "=" not in item:
            raise maas_common.MaasAPIError(f"Expected key=value, got {item!r}.")
        key, value = item.split("=", 1)
        if not key:
            raise maas_common.MaasAPIError(f"Expected non-empty key in {item!r}.")
        if value.lower() == "true":
            parsed[key] = True
        elif value.lower() == "false":
            parsed[key] = False
        elif value.isdigit():
            parsed[key] = int(value)
        else:
            parsed[key] = value
    return parsed


def parse_media(values: list[str], *, max_bytes: int) -> list[dict[str, Any]]:
    """Parse media entries in type=image_url,url=... form."""
    media: list[dict[str, Any]] = []
    for item in values:
        fields = parse_key_values([part.strip() for part in item.split(",") if part.strip()])
        if "type" not in fields or "url" not in fields:
            raise maas_common.MaasAPIError("--media entries must include type=... and url=....")
        fields["url"] = maas_common.image_reference_to_url(str(fields["url"]), max_bytes=max_bytes)
        media.append(fields)
    return media


def load_json_body(args: argparse.Namespace) -> dict[str, Any] | None:
    """Load a raw video request body override."""
    if args.body_json_file and args.body_json_text:
        raise maas_common.MaasAPIError("Use either --body-json-file or --body-json-text, not both.")
    if args.body_json_file:
        return maas_common.require_json_object(maas_common.load_json_file(args.body_json_file), "--body-json-file")
    if args.body_json_text:
        return maas_common.require_json_object(maas_common.load_json_text(args.body_json_text), "--body-json-text")
    return None


def default_model(args: argparse.Namespace) -> str:
    """Return a default video model for CLI-built payloads."""
    if args.model:
        return args.model
    if args.image or args.first_frame or args.last_frame or args.media:
        return DEFAULT_IMAGE_TO_VIDEO_MODEL
    return DEFAULT_TEXT_TO_VIDEO_MODEL


def build_input(args: argparse.Namespace) -> dict[str, Any]:
    """Build the MaaS video input object."""
    if not args.prompt:
        raise maas_common.MaasAPIError("--prompt is required unless --body-json-file/--body-json-text is used.")
    data: dict[str, Any] = {"prompt": args.prompt}
    if args.media:
        data["media"] = parse_media(args.media, max_bytes=args.max_image_bytes)
    elif args.first_frame or args.last_frame:
        media = []
        if args.first_frame:
            media.append({"type": "first_frame", "url": maas_common.image_reference_to_url(args.first_frame, max_bytes=args.max_image_bytes)})
        if args.last_frame:
            media.append({"type": "last_frame", "url": maas_common.image_reference_to_url(args.last_frame, max_bytes=args.max_image_bytes)})
        data["media"] = media
    elif args.image:
        if len(args.image) > 1:
            data["media"] = [
                {"type": "image_url", "url": maas_common.image_reference_to_url(image, max_bytes=args.max_image_bytes)}
                for image in args.image
            ]
        else:
            data["img_url"] = maas_common.image_reference_to_url(args.image[0], max_bytes=args.max_image_bytes)
    return data


def build_parameters(args: argparse.Namespace) -> dict[str, Any]:
    """Build the MaaS video parameters object."""
    params: dict[str, Any] = {}
    if args.size:
        params["size"] = maas_common.normalize_size(args.size, separator=args.size_separator)
    if args.resolution:
        params["resolution"] = args.resolution
    if args.ratio:
        params["ratio"] = args.ratio
    if args.fps is not None:
        params["fps"] = args.fps
    if args.duration is not None:
        params["duration"] = args.duration
    if args.seed is not None:
        params["seed"] = maas_common.normalize_seed(args.seed)
    if args.audio is not None:
        params["audio"] = args.audio
    if args.shot_type:
        params["shot_type"] = args.shot_type
    params.update(parse_key_values(args.parameter))
    if not params:
        raise maas_common.MaasAPIError("At least one video parameter is required; pass --size or --resolution/--ratio/duration fields.")
    return params


def build_create_payload(args: argparse.Namespace) -> dict[str, Any]:
    """Build a MaaS video generation request body."""
    raw = load_json_body(args)
    if raw is not None:
        return raw
    return {
        "model": default_model(args),
        "input": build_input(args),
        "parameters": build_parameters(args),
    }


def query_path(task_id: str) -> str:
    """Return the video query path for a task ID."""
    if not task_id.strip():
        raise maas_common.MaasAPIError("--task-id cannot be empty.")
    return f"{VIDEO_GENERATIONS_PATH}/{task_id.strip()}"


def create_task(args: argparse.Namespace) -> dict[str, Any]:
    """Create a MaaS video generation task."""
    payload = build_create_payload(args)
    api_key = maas_common.get_api_key()
    response = maas_common.request_json("POST", VIDEO_GENERATIONS_PATH, api_key=api_key, body=payload, timeout=args.timeout, base_url=args.base_url)
    body = response["body"]
    return {
        "success": True,
        "action": "create",
        **maas_common.response_metadata(response),
        "task_id": body.get("task_id") if isinstance(body, dict) else None,
        "response": body,
        "next_step": "Use --action query --task-id <task_id> or --action wait --task-id <task_id>.",
    }


def query_task(args: argparse.Namespace) -> dict[str, Any]:
    """Query one MaaS video generation task."""
    api_key = maas_common.get_api_key()
    response = maas_common.request_json("GET", query_path(args.task_id), api_key=api_key, timeout=args.timeout, base_url=args.base_url)
    body = response["body"]
    status = body.get("status") if isinstance(body, dict) else None
    return {
        "success": True,
        "action": "query",
        **maas_common.response_metadata(response),
        "task_id": body.get("task_id") if isinstance(body, dict) else args.task_id,
        "status": status,
        "terminal": status in TERMINAL_STATUSES,
        "result_url": body.get("content", {}).get("result_url") if isinstance(body, dict) and isinstance(body.get("content"), dict) else None,
        "response": body,
    }


def wait_task(args: argparse.Namespace) -> dict[str, Any]:
    """Poll a MaaS video task until it reaches a terminal status or max attempts."""
    attempts = []
    for attempt in range(1, args.max_attempts + 1):
        result = query_task(args)
        attempts.append({"attempt": attempt, "status": result.get("status"), "result_url": result.get("result_url")})
        if result.get("terminal"):
            result["action"] = "wait"
            result["attempts"] = attempts
            return result
        if attempt < args.max_attempts:
            time.sleep(args.interval)
    return {
        "success": False,
        "action": "wait",
        "task_id": args.task_id,
        "status": attempts[-1]["status"] if attempts else None,
        "attempts": attempts,
        "error": "Video task did not reach a terminal status within max attempts.",
    }


def build_plan(args: argparse.Namespace) -> dict[str, Any]:
    """Build a non-executing MaaS video action plan."""
    payload = build_create_payload(args) if args.action == "create" else None
    path = VIDEO_GENERATIONS_PATH if args.action == "create" else query_path(args.task_id)
    return {
        "success": True,
        "dry_run": True,
        "action": args.action,
        "endpoint": maas_common.endpoint_url(path, args.base_url),
        "method": "POST" if args.action == "create" else "GET",
        "payload": maas_common.summarize_payload(payload),
        "requires_api_key_env": list(maas_common.MAAS_API_KEY_ENV_NAMES),
        "api_key_presence": maas_common.api_key_presence(),
        "boundary": "Dry-run only; no MaaS API call was made and no video was downloaded.",
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--action", choices=["create", "query", "wait"], default="create")
    parser.add_argument("--model", help="MaaS video model parameter.")
    parser.add_argument("--prompt", help="Prompt for create action.")
    parser.add_argument("--image", action="append", help="Input image path, data URI, or public URL.")
    parser.add_argument("--first-frame", help="First-frame image for keyframe video models.")
    parser.add_argument("--last-frame", help="Last-frame image for keyframe video models.")
    parser.add_argument("--media", action="append", default=[], help="Media entry like type=image_url,url=https://...,ref_name=name.")
    parser.add_argument("--size", help="Video size, for example 720x1280 or 720*1280.")
    parser.add_argument("--size-separator", choices=["x", "*"], default="x", help="Separator used in generated size field.")
    parser.add_argument("--resolution", help="Resolution tier such as 720p for PixVerse models.")
    parser.add_argument("--ratio", help="Video ratio such as 16:9.")
    parser.add_argument("--fps", type=int)
    parser.add_argument("--duration", type=int)
    parser.add_argument("--seed", type=int)
    parser.add_argument("--audio", action=argparse.BooleanOptionalAction, default=None)
    parser.add_argument("--shot-type", choices=["single", "multi"])
    parser.add_argument("--parameter", action="append", default=[], help="Extra parameters as key=value. Can be repeated.")
    parser.add_argument("--body-json-file", type=Path, help="Raw JSON request body for create action.")
    parser.add_argument("--body-json-text", help="Raw JSON request body for create action.")
    parser.add_argument("--task-id", help="Task ID for query/wait actions.")
    parser.add_argument("--max-image-bytes", type=int, default=50 * 1024 * 1024)
    parser.add_argument("--max-attempts", type=int, default=20)
    parser.add_argument("--interval", type=float, default=15.0)
    parser.add_argument("--base-url", default=maas_common.DEFAULT_MAAS_BASE_URL)
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)
    if args.action in {"query", "wait"} and not args.task_id:
        parser.error("--task-id is required for query/wait.")
    if args.max_attempts < 1:
        parser.error("--max-attempts must be greater than 0.")
    if args.interval < 0:
        parser.error("--interval must be non-negative.")
    return args


def main(argv: list[str] | None = None) -> int:
    """Run a MaaS video generation helper."""
    try:
        args = parse_args(argv)
        if args.dry_run:
            result = build_plan(args)
        elif args.action == "create":
            result = create_task(args)
        elif args.action == "query":
            result = query_task(args)
        else:
            result = wait_task(args)
        hcloud_common.emit_json(result, pretty=args.pretty)
        return 0 if result.get("success") else 1
    except Exception as exc:
        hcloud_common.emit_json({"success": False, "error": str(exc)})
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
