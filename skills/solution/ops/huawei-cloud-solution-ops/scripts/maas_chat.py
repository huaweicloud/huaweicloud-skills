#!/usr/bin/env python3
"""Call Huawei Cloud MaaS chat APIs for text generation and image understanding."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import hcloud_common
import maas_common

TEXT_V2_PATH = "/v2/chat/completions"
VISION_V1_PATH = "/v1/chat/completions"
OPENAI_COMPAT_PATH = "/openai/v1/chat/completions"
DEFAULT_TEXT_MODEL = "deepseek-v3.2"
DEFAULT_VISION_MODEL = "qwen2.5-vl-72b"


def load_messages(args: argparse.Namespace) -> list[dict[str, Any]]:
    """Load or build MaaS chat messages."""
    if args.messages_file and (args.prompt or args.image):
        raise maas_common.MaasAPIError("Use either --messages-file or prompt/image arguments, not both.")
    if args.messages_file:
        data = maas_common.load_json_file(args.messages_file)
        if isinstance(data, dict):
            data = data.get("messages")
        if not isinstance(data, list):
            raise maas_common.MaasAPIError("--messages-file must be a list or an object containing a messages list.")
        if not all(isinstance(item, dict) for item in data):
            raise maas_common.MaasAPIError("Every message must be a JSON object.")
        return data

    if not args.prompt:
        raise maas_common.MaasAPIError("--prompt is required when --messages-file is not used.")
    messages: list[dict[str, Any]] = []
    if args.system:
        messages.append({"role": "system", "content": args.system})
    if args.image:
        content: list[dict[str, Any]] = [{"type": "text", "text": args.prompt}]
        for image in args.image:
            content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": maas_common.image_reference_to_url(image, max_bytes=args.max_image_bytes)},
                }
            )
        messages.append({"role": "user", "content": content})
    else:
        messages.append({"role": "user", "content": args.prompt})
    if args.assistant_prefix:
        messages.append({"role": "assistant", "content": args.assistant_prefix, "prefix": True})
    return messages


def load_extra_body(args: argparse.Namespace) -> dict[str, Any]:
    """Load optional extra request body fields."""
    if args.extra_body_file and args.extra_body_json:
        raise maas_common.MaasAPIError("Use either --extra-body-file or --extra-body-json, not both.")
    if args.extra_body_file:
        return maas_common.require_json_object(maas_common.load_json_file(args.extra_body_file), "--extra-body-file")
    if args.extra_body_json:
        return maas_common.require_json_object(maas_common.load_json_text(args.extra_body_json), "--extra-body-json")
    return {}


def endpoint_path(args: argparse.Namespace) -> str:
    """Return the MaaS chat endpoint path for the requested API style."""
    if args.image and args.api == "standard-v2":
        return VISION_V1_PATH
    if args.api == "standard-v2":
        return TEXT_V2_PATH
    if args.api == "vision-v1":
        return VISION_V1_PATH
    return OPENAI_COMPAT_PATH


def build_payload(args: argparse.Namespace) -> dict[str, Any]:
    """Build a MaaS chat completion payload."""
    messages = load_messages(args)
    model = args.model or (DEFAULT_VISION_MODEL if args.api == "vision-v1" or args.image else DEFAULT_TEXT_MODEL)
    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
    }
    for key in ("temperature", "top_p", "max_tokens", "max_completion_tokens", "reasoning_effort"):
        value = getattr(args, key)
        if value is not None:
            payload[key] = value
    if args.stream:
        payload["stream"] = True
        payload["stream_options"] = {"include_usage": True}
    payload.update(load_extra_body(args))
    return payload


def summarize_chat_response(response: dict[str, Any]) -> dict[str, Any]:
    """Return a compact chat response without hiding the generated answer."""
    body = response.get("body")
    if not isinstance(body, dict):
        return {"raw": body}
    choices = body.get("choices") if isinstance(body.get("choices"), list) else []
    first = choices[0] if choices and isinstance(choices[0], dict) else {}
    message = first.get("message") if isinstance(first.get("message"), dict) else {}
    return {
        "id": body.get("id"),
        "model": body.get("model"),
        "content": message.get("content"),
        "reasoning_content_present": bool(message.get("reasoning_content")),
        "tool_calls": message.get("tool_calls") or [],
        "finish_reason": first.get("finish_reason"),
        "usage": body.get("usage"),
        "raw_response": body,
    }


def build_plan(args: argparse.Namespace) -> dict[str, Any]:
    """Build a non-executing MaaS chat call plan."""
    payload = build_payload(args)
    return {
        "success": True,
        "dry_run": True,
        "endpoint": maas_common.endpoint_url(endpoint_path(args), args.base_url),
        "method": "POST",
        "payload": maas_common.summarize_payload(payload),
        "requires_api_key_env": list(maas_common.MAAS_API_KEY_ENV_NAMES),
        "api_key_presence": maas_common.api_key_presence(),
        "boundary": "Dry-run only; no MaaS API call was made.",
    }


def execute(args: argparse.Namespace) -> dict[str, Any]:
    """Execute a MaaS chat completion request."""
    payload = build_payload(args)
    if payload.get("stream"):
        raise maas_common.MaasAPIError("This helper can plan stream=true payloads, but does not execute streaming responses yet.")
    api_key = maas_common.get_api_key()
    response = maas_common.request_json("POST", endpoint_path(args), api_key=api_key, body=payload, timeout=args.timeout, base_url=args.base_url)
    return {
        "success": True,
        "dry_run": False,
        **maas_common.response_metadata(response),
        "chat": summarize_chat_response(response),
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api", choices=["standard-v2", "vision-v1", "openai-compatible"], default="standard-v2")
    parser.add_argument("--model", help="MaaS model parameter. Defaults to deepseek-v3.2 or qwen2.5-vl-72b for vision.")
    parser.add_argument("--system", help="Optional system message.")
    parser.add_argument("--prompt", help="User prompt text.")
    parser.add_argument("--assistant-prefix", help="Assistant prefix for continuation mode.")
    parser.add_argument("--messages-file", type=Path, help="JSON messages file.")
    parser.add_argument("--image", action="append", help="Local image path, data URI, or public URL for image understanding.")
    parser.add_argument("--max-image-bytes", type=int, default=10 * 1024 * 1024, help="Maximum local image size before base64 encoding.")
    parser.add_argument("--temperature", type=float)
    parser.add_argument("--top-p", type=float, dest="top_p")
    parser.add_argument("--max-tokens", type=int, dest="max_tokens")
    parser.add_argument("--max-completion-tokens", type=int, dest="max_completion_tokens")
    parser.add_argument("--reasoning-effort", choices=["high", "max"], dest="reasoning_effort")
    parser.add_argument("--stream", action="store_true", help="Set stream=true in the payload. The helper still reads the raw response as JSON.")
    parser.add_argument("--extra-body-file", type=Path, help="JSON object merged into the request body.")
    parser.add_argument("--extra-body-json", help="JSON object merged into the request body.")
    parser.add_argument("--base-url", default=maas_common.DEFAULT_MAAS_BASE_URL)
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--pretty", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Run a MaaS chat helper."""
    try:
        args = parse_args(argv)
        result = build_plan(args) if args.dry_run else execute(args)
        hcloud_common.emit_json(result, pretty=args.pretty)
        return 0
    except Exception as exc:
        hcloud_common.emit_json({"success": False, "error": str(exc)})
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
