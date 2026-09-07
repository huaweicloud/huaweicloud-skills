#!/usr/bin/env python3
"""Generate or edit images through Huawei Cloud MaaS image generation APIs."""

from __future__ import annotations

import argparse
import base64
import json
import mimetypes
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import hcloud_common
import maas_common

IMAGE_GENERATIONS_PATH = "/v1/images/generations"
DEFAULT_MODEL = "qwen-image"
DEFAULT_SIZE = "1024x1024"
DEFAULT_SEED = 1


@dataclass(frozen=True)
class ImageItem:
    """One MaaS image generation or editing request."""

    file: str
    prompt: str
    size: str | None
    seed: int | None
    image: str | None
    watermark: bool | None


class MaasImageError(RuntimeError):
    """Raised when a MaaS image request cannot be planned or executed."""


def ensure_suffix(file_name: str, image_format: str) -> str:
    """Return a safe output filename with the requested suffix."""
    path = Path(file_name)
    suffix = "." + image_format
    if path.name != file_name:
        raise MaasImageError(f"Unsafe output file name: {file_name}")
    if path.suffix.lower() == suffix:
        return file_name
    return path.with_suffix(suffix).name


def load_image_list(raw: Any, *, max_bytes: int) -> str | None:
    """Return a MaaS image field from one or more references."""
    if raw in (None, "", []):
        return None
    refs = raw if isinstance(raw, list) else [raw]
    urls = [maas_common.image_reference_to_url(str(ref), max_bytes=max_bytes) for ref in refs]
    return ", ".join(urls)


def load_items(args: argparse.Namespace) -> list[ImageItem]:
    """Load image generation items from CLI args or prompt JSON."""
    if args.prompt_file and args.prompt:
        raise MaasImageError("Use either --prompt-file or --prompt, not both.")
    if args.prompt:
        if not args.file:
            raise MaasImageError("--file is required with --prompt.")
        raw_items: list[dict[str, Any]] = [
            {
                "file": args.file,
                "prompt": args.prompt,
                "size": args.size,
                "seed": args.seed,
                "image": args.image,
                "watermark": args.watermark,
            }
        ]
    elif args.prompt_file:
        data = maas_common.load_json_file(args.prompt_file)
        if isinstance(data, dict) and isinstance(data.get("items"), list):
            raw_items = data["items"]
        elif isinstance(data, list):
            raw_items = data
        else:
            raise MaasImageError("Prompt file must be a list or an object with an items list.")
    else:
        raise MaasImageError("Either --prompt-file or --prompt is required.")

    items: list[ImageItem] = []
    for index, raw in enumerate(raw_items, start=1):
        if not isinstance(raw, dict):
            raise MaasImageError(f"Prompt item {index} must be an object.")
        file_name = str(raw.get("file") or "").strip()
        prompt = str(raw.get("prompt") or "").strip()
        if not file_name:
            raise MaasImageError(f"Prompt item {index} is missing file.")
        if not prompt:
            raise MaasImageError(f"Prompt item {index} is missing prompt.")
        size = raw.get("size", args.size)
        seed = raw.get("seed", args.seed)
        watermark = raw.get("watermark", args.watermark)
        items.append(
            ImageItem(
                file=ensure_suffix(file_name, args.format),
                prompt=prompt,
                size=maas_common.normalize_size(str(size), separator="x") if size else None,
                seed=maas_common.normalize_seed(int(seed)) if seed is not None else None,
                image=load_image_list(raw.get("image") or raw.get("images"), max_bytes=args.max_image_bytes),
                watermark=bool(watermark) if watermark is not None else None,
            )
        )
    return items


def build_payload(model: str, item: ImageItem) -> dict[str, Any]:
    """Build one MaaS image generation request body."""
    payload: dict[str, Any] = {
        "model": model,
        "prompt": item.prompt,
        "response_format": "b64_json",
    }
    if item.size:
        payload["size"] = item.size
    if item.seed is not None:
        payload["seed"] = item.seed
    if item.image:
        payload["image"] = item.image
    if item.watermark is not None:
        payload["watermark"] = item.watermark
    return payload


def extract_b64_json(response: dict[str, Any]) -> str:
    """Extract generated image b64_json from a MaaS response."""
    data = response.get("data")
    if isinstance(data, list) and data:
        item = data[0]
        if isinstance(item, dict) and isinstance(item.get("b64_json"), str):
            return item["b64_json"]
    if isinstance(response.get("b64_json"), str):
        return response["b64_json"]
    raise MaasImageError("MaaS image response did not contain data[0].b64_json.")


def decode_b64_image(value: str) -> tuple[bytes, str | None]:
    """Decode raw base64 or data URI image content."""
    media_type = None
    encoded = value
    if value.startswith("data:") and "," in value:
        header, encoded = value.split(",", 1)
        media_type = header[5:].split(";", 1)[0] or None
    return base64.b64decode(encoded), media_type


def write_image(raw: bytes, media_type: str | None, target: Path, image_format: str) -> None:
    """Write image bytes in the requested local format."""
    if image_format == "png" and media_type == "image/png":
        target.write_bytes(raw)
        return
    try:
        from io import BytesIO

        from PIL import Image

        with Image.open(BytesIO(raw)) as image:
            if image_format == "webp":
                image.save(target, "WEBP", quality=88, method=6)
            elif image_format in {"jpg", "jpeg"}:
                image.convert("RGB").save(target, "JPEG", quality=92)
            else:
                image.save(target, "PNG")
    except ImportError as exc:
        guessed = mimetypes.guess_extension(media_type or "") or ".img"
        raise MaasImageError(f"Pillow is required to convert generated image bytes to {image_format}; source looked like {guessed}.") from exc


def generate_item(
    *,
    api_key: str,
    model: str,
    item: ImageItem,
    out_dir: Path,
    image_format: str,
    overwrite: bool,
    timeout: int,
    base_url: str,
) -> dict[str, Any]:
    """Generate one image item and return manifest metadata."""
    target = out_dir / item.file
    if target.exists() and target.stat().st_size > 0 and not overwrite:
        return {"file": item.file, "prompt": item.prompt, "size": item.size, "seed": item.seed, "status": "existing"}

    response = maas_common.request_json(
        "POST",
        IMAGE_GENERATIONS_PATH,
        api_key=api_key,
        body=build_payload(model, item),
        timeout=timeout,
        base_url=base_url,
    )
    raw, media_type = decode_b64_image(extract_b64_json(response["body"]))
    write_image(raw, media_type, target, image_format)
    body = response["body"] if isinstance(response["body"], dict) else {}
    return {
        "file": item.file,
        "prompt": item.prompt,
        "size": item.size,
        "seed": item.seed,
        "status": "generated",
        "model": body.get("model") or model,
        "endpoint_host": maas_common.response_metadata(response)["endpoint_host"],
        "created": body.get("created"),
        "usage": body.get("usage"),
    }


def build_plan(args: argparse.Namespace) -> dict[str, Any]:
    """Build a non-executing MaaS image generation plan."""
    items = load_items(args)
    return {
        "success": True,
        "dry_run": True,
        "provider": "Huawei Cloud MaaS image generation",
        "endpoint": maas_common.endpoint_url(IMAGE_GENERATIONS_PATH, args.base_url),
        "model": args.model,
        "out_dir": str(args.out_dir),
        "items": [maas_common.summarize_payload(build_payload(args.model, item) | {"file": item.file}) for item in items],
        "requires_api_key_env": list(maas_common.MAAS_API_KEY_ENV_NAMES),
        "api_key_presence": maas_common.api_key_presence(),
        "boundary": "Dry-run only; no MaaS API call was made.",
    }


def execute(args: argparse.Namespace) -> dict[str, Any]:
    """Execute MaaS image generation requests."""
    items = load_items(args)
    out_dir = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = args.manifest or out_dir / "maas_image_manifest.json"
    api_key = maas_common.get_api_key()
    manifest = {
        "generated_at": maas_common.now_utc_iso(),
        "provider": "Huawei Cloud MaaS image generation",
        "endpoint_host": maas_common.endpoint_url(IMAGE_GENERATIONS_PATH, args.base_url).split("/", 3)[2],
        "model": args.model,
        "items": [],
    }
    for item in items:
        manifest["items"].append(
            generate_item(
                api_key=api_key,
                model=args.model,
                item=item,
                out_dir=out_dir,
                image_format=args.format,
                overwrite=args.overwrite,
                timeout=args.timeout,
                base_url=args.base_url,
            )
        )
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"success": True, "manifest": str(manifest_path), "count": len(items), "items": manifest["items"]}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prompt-file", type=Path, help="JSON file with image generation items.")
    parser.add_argument("--prompt", help="Single prompt text.")
    parser.add_argument("--file", help="Output file name for --prompt mode.")
    parser.add_argument("--image", action="append", help="Input image path, data URI, or public URL for image edit models.")
    parser.add_argument("--out-dir", type=Path, required=True, help="Directory for generated local images.")
    parser.add_argument("--manifest", type=Path, help="Manifest path. Defaults to <out-dir>/maas_image_manifest.json.")
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"MaaS image model. Default: {DEFAULT_MODEL}.")
    parser.add_argument("--size", default=DEFAULT_SIZE, help=f"Default output size. Default: {DEFAULT_SIZE}.")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED, help=f"Default random seed. Default: {DEFAULT_SEED}.")
    parser.add_argument("--watermark", action=argparse.BooleanOptionalAction, default=None, help="Set MaaS watermark parameter.")
    parser.add_argument("--format", choices=["webp", "png", "jpg"], default="webp", help="Final local image format.")
    parser.add_argument("--max-image-bytes", type=int, default=20 * 1024 * 1024, help="Maximum local input image size before base64 encoding.")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--base-url", default=maas_common.DEFAULT_MAAS_BASE_URL)
    parser.add_argument("--timeout", type=int, default=240)
    parser.add_argument("--pretty", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Run MaaS image generation."""
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
