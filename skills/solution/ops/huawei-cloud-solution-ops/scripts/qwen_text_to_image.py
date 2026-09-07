#!/usr/bin/env python3
"""Generate local site image assets with Huawei Cloud ModelArts MaaS.

This helper is intentionally provider-scoped and cloud-deployment friendly:
it uses Huawei Cloud's MaaS image generation API, reads the MaaS API key from
the environment, decodes b64_json images as local files, and writes a small
manifest without credentials.
"""

from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import maas_common

DEFAULT_MODEL = "qwen-image"
DEFAULT_ENDPOINT = "https://api.modelarts-maas.com/v1/images/generations"
DEFAULT_SIZE = "1024x1024"
DEFAULT_SEED = 1
MAX_SEED = 2_147_483_648
OUTPUT_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")
ACTION_PROGRESS_PREFIX = "__CLOUD_CLAW_ACTION_PROGRESS__"


@dataclass(frozen=True)
class PromptItem:
    """One Huawei Cloud MaaS image generation request."""

    file: str
    prompt: str
    size: str
    seed: int
    output_id: str = ""


class QwenImageError(RuntimeError):
    """Raised when Huawei Cloud MaaS image generation cannot complete."""


def emit_action_progress(
    *,
    phase: str,
    output_id: str,
    item_label: str,
    current: int,
    total: int,
    attempt: int | None = None,
    max_attempts: int | None = None,
    completed_count: int | None = None,
    failed_count: int | None = None,
) -> None:
    """Emit a backward-compatible, non-secret item progress marker."""

    payload: dict[str, object] = {
        "phase": phase,
        "output_id": output_id,
        "item_label": item_label,
        "current": current,
        "total": total,
    }
    for key, value in (
        ("attempt", attempt),
        ("max_attempts", max_attempts),
        ("completed_count", completed_count),
        ("failed_count", failed_count),
    ):
        if value is not None:
            payload[key] = value
    print(
        ACTION_PROGRESS_PREFIX + json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
        flush=True,
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate local image assets using Huawei Cloud ModelArts MaaS.")
    parser.add_argument("--prompt-file", help="JSON file containing prompt items.")
    parser.add_argument("--prompt", help="Single prompt text. Requires --file.")
    parser.add_argument("--file", help="Output file name for --prompt mode.")
    parser.add_argument(
        "--output-id",
        help="Stable checkpoint ID for --prompt mode. Defaults to the file stem.",
    )
    parser.add_argument("--out-dir", required=True, help="Directory where image assets are written.")
    parser.add_argument("--manifest", help="Manifest path. Defaults to <out-dir>/qwen_manifest.json for compatibility.")
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"Huawei Cloud MaaS image model. Default: {DEFAULT_MODEL}.")
    parser.add_argument("--size", default=DEFAULT_SIZE, help=f"Default image size. Default: {DEFAULT_SIZE}.")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED, help=f"Default random seed. Default: {DEFAULT_SEED}.")
    parser.add_argument("--format", choices=["webp", "png"], default="webp", help="Final local image format.")
    parser.add_argument("--overwrite", action="store_true", help="Regenerate even when target exists.")
    parser.add_argument("--dry-run", action="store_true", help="Validate inputs and print the resolved plan without network calls.")
    parser.add_argument("--timeout", type=int, default=240, help="HTTP timeout in seconds.")
    return parser.parse_args(argv)


def normalize_size(value: str) -> str:
    """Return a Huawei MaaS size string such as 1024x1024."""
    size = value.strip().lower().replace("*", "x")
    parts = size.split("x")
    if len(parts) != 2 or not all(part.isdigit() and int(part) > 0 for part in parts):
        raise QwenImageError(f"Invalid size for Huawei MaaS image generation: {value}")
    return f"{int(parts[0])}x{int(parts[1])}"


def normalize_seed(value: int) -> int:
    """Validate the Huawei MaaS seed range."""
    if value < 0 or value > MAX_SEED:
        raise QwenImageError(f"seed must be in [0, {MAX_SEED}]")
    return value


def load_prompt_items(args: argparse.Namespace) -> list[PromptItem]:
    if args.prompt:
        if not args.file:
            raise QwenImageError("--file is required when using --prompt")
        raw_items: list[dict[str, Any]] = [
            {
                "id": args.output_id,
                "file": args.file,
                "prompt": args.prompt,
                "size": args.size,
                "seed": args.seed,
            }
        ]
    elif args.prompt_file:
        try:
            data = json.loads(Path(args.prompt_file).read_text(encoding="utf-8"))
        except Exception as exc:
            raise QwenImageError(f"Could not read prompt file: {exc}") from exc
        if isinstance(data, list):
            raw_items = data
        elif isinstance(data, dict) and isinstance(data.get("items"), list):
            raw_items = data["items"]
        else:
            raise QwenImageError("Prompt file must be a list or an object with an items list")
    else:
        raise QwenImageError("Either --prompt-file or --prompt is required")

    items: list[PromptItem] = []
    for index, raw in enumerate(raw_items, start=1):
        if not isinstance(raw, dict):
            raise QwenImageError(f"Prompt item {index} must be an object")
        file_name = str(raw.get("file") or "").strip()
        prompt = str(raw.get("prompt") or "").strip()
        if not file_name or Path(file_name).name != file_name:
            raise QwenImageError(f"Prompt item {index} must have a safe file name")
        if not prompt:
            raise QwenImageError(f"Prompt item {index} is missing prompt")
        target_name = ensure_suffix(file_name, args.format)
        output_id = normalize_output_id(raw.get("id"), file_name=target_name)
        items.append(
            PromptItem(
                output_id=output_id,
                file=target_name,
                prompt=prompt,
                size=normalize_size(str(raw.get("size") or args.size)),
                seed=normalize_seed(int(raw.get("seed", args.seed))),
            )
        )
    return items


def normalize_output_id(value: object, *, file_name: str) -> str:
    """Return one stable progress/checkpoint ID for an output file."""

    explicit = str(value or "").strip()
    candidate = explicit or re.sub(r"[^A-Za-z0-9_.-]+", "-", Path(file_name).stem)
    candidate = candidate.strip("-.")
    if not OUTPUT_ID_RE.fullmatch(candidate):
        raise QwenImageError(f"Output {file_name} requires an id matching {OUTPUT_ID_RE.pattern}")
    return candidate


def ensure_suffix(file_name: str, image_format: str) -> str:
    suffix = "." + image_format
    path = Path(file_name)
    if path.suffix.lower() == suffix:
        return file_name
    return path.with_suffix(suffix).name


def build_payload(model: str, item: PromptItem) -> dict[str, Any]:
    """Build the Huawei Cloud MaaS image generation request body."""
    return {
        "model": model,
        "prompt": item.prompt,
        "size": item.size,
        "response_format": "b64_json",
        "seed": item.seed,
    }


def call_huawei_maas(api_key: str, model: str, item: PromptItem, timeout: int) -> dict[str, Any]:
    body = json.dumps(build_payload(model, item), ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        DEFAULT_ENDPOINT,
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        response_body = response.read().decode("utf-8")
    try:
        return json.loads(response_body)
    except json.JSONDecodeError as exc:
        raise QwenImageError("Huawei Cloud MaaS response was not JSON") from exc


def extract_b64_json(response: dict[str, Any]) -> str:
    """Extract b64_json from Huawei Cloud MaaS image generation response."""
    data = response.get("data")
    if isinstance(data, list) and data:
        item = data[0]
        if isinstance(item, dict) and isinstance(item.get("b64_json"), str):
            return item["b64_json"]
    if isinstance(response.get("b64_json"), str):
        return response["b64_json"]
    raise QwenImageError("Huawei Cloud MaaS response did not contain data[0].b64_json")


def decode_b64_image(value: str) -> tuple[bytes, str | None]:
    """Decode a raw or data-URI b64 image returned by Huawei Cloud MaaS."""
    media_type = None
    encoded = value
    if value.startswith("data:") and "," in value:
        header, encoded = value.split(",", 1)
        media_type = header[5:].split(";", 1)[0] or None
    return base64.b64decode(encoded), media_type


def write_image(raw: bytes, media_type: str | None, target: Path, image_format: str) -> None:
    if image_format == "png" and media_type == "image/png":
        target.write_bytes(raw)
        return

    try:
        from io import BytesIO

        from PIL import Image

        with Image.open(BytesIO(raw)) as image:
            if image_format == "webp":
                image.save(target, "WEBP", quality=88, method=6)
            else:
                image.save(target, "PNG")
    except ImportError as exc:
        guessed = mimetypes.guess_extension(media_type or "") or ".img"
        raise QwenImageError(
            f"Pillow is required to convert generated image bytes to {image_format}; source looked like {guessed}"
        ) from exc


def generate_item(
    api_key: str,
    model: str,
    item: PromptItem,
    out_dir: Path,
    image_format: str,
    overwrite: bool,
    timeout: int,
) -> dict[str, Any]:
    target = out_dir / item.file
    if target.exists() and target.stat().st_size > 0 and not overwrite:
        return {
            "file": item.file,
            "prompt": item.prompt,
            "size": item.size,
            "seed": item.seed,
            "status": "existing",
        }

    try:
        response = call_huawei_maas(api_key, model, item, timeout)
        raw, media_type = decode_b64_image(extract_b64_json(response))
        write_image(raw, media_type, target, image_format)
        return {
            "file": item.file,
            "prompt": item.prompt,
            "size": item.size,
            "seed": item.seed,
            "status": "generated",
            "model": response.get("model") or model,
            "endpoint_host": urllib.parse.urlparse(DEFAULT_ENDPOINT).netloc,
            "created": response.get("created"),
        }
    except urllib.error.HTTPError as exc:
        body = maas_common.redact_maas_text(
            exc.read().decode("utf-8", errors="replace"),
            api_key,
        )
        raise QwenImageError(f"Could not generate {item.file}: HTTP {exc.code}: {body[:300]}") from exc
    except Exception as exc:
        raise QwenImageError(f"Could not generate {item.file}: {exc}") from exc


def get_api_key() -> str:
    """Read the Huawei MaaS API key without logging it."""
    api_key = os.getenv("MAAS_API_KEY", "").strip() or os.getenv("MODELARTS_MAAS_API_KEY", "").strip()
    if not api_key:
        raise QwenImageError(
            "缺少华为云 ModelArts MaaS API Key。请先设置环境变量 MAAS_API_KEY "
            "或 MODELARTS_MAAS_API_KEY 后重试；不要把 API Key 写进代码、站点文件或 manifest。"
        )
    return api_key


def main(argv: list[str] | None = None) -> int:
    try:
        args = parse_args(argv)
        items = load_prompt_items(args)
        out_dir = Path(args.out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        manifest_path = Path(args.manifest) if args.manifest else out_dir / "qwen_manifest.json"

        plan = {
            "provider": "Huawei Cloud ModelArts MaaS",
            "endpoint": DEFAULT_ENDPOINT,
            "model": args.model,
            "out_dir": str(out_dir),
            "items": [
                {
                    "id": item.output_id,
                    "file": item.file,
                    "size": item.size,
                    "seed": item.seed,
                    "prompt": item.prompt,
                }
                for item in items
            ],
        }
        if args.dry_run:
            print(json.dumps({"success": True, "dry_run": True, "plan": plan}, ensure_ascii=False, indent=2))
            return 0

        api_key = get_api_key()
        manifest = {
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "provider": "Huawei Cloud ModelArts MaaS image generation",
            "endpoint_host": urllib.parse.urlparse(DEFAULT_ENDPOINT).netloc,
            "items": [],
        }
        for current, item in enumerate(items, start=1):
            emit_action_progress(
                phase="item_started",
                output_id=item.output_id,
                item_label=item.file,
                current=current,
                total=len(items),
                attempt=1,
                max_attempts=1,
            )
            try:
                result = generate_item(
                    api_key=api_key,
                    model=args.model,
                    item=item,
                    out_dir=out_dir,
                    image_format=args.format,
                    overwrite=args.overwrite,
                    timeout=args.timeout,
                )
                target = out_dir / item.file
                if not target.is_file() or target.stat().st_size <= 0:
                    raise QwenImageError(f"Generated output is missing or empty: {item.file}")
            except Exception:
                emit_action_progress(
                    phase="item_failed",
                    output_id=item.output_id,
                    item_label=item.file,
                    current=current,
                    total=len(items),
                    attempt=1,
                    max_attempts=1,
                    completed_count=current - 1,
                    failed_count=1,
                )
                raise
            manifest["items"].append(result)
            emit_action_progress(
                phase="item_succeeded",
                output_id=item.output_id,
                item_label=item.file,
                current=current,
                total=len(items),
                completed_count=current,
            )
            print(f"{result['status']}: {result['file']}", flush=True)

        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps({"success": True, "manifest": str(manifest_path), "count": len(items)}, ensure_ascii=False))
        return 0
    except Exception as exc:
        error = maas_common.redact_maas_text(str(exc))
        print(json.dumps({"success": False, "error": error}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
