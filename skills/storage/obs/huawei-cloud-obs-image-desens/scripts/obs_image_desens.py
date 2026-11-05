#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
huawei-cloud-obs-image-desens — one-click OBS image desensitization (blur/mosaic) skill.

Batch-list, desensitize images and write the results back to OBS. Uses:
  - obsutil (hcloud obs) for OBS object list / download / upload
  - Pillow (PIL) for local image desensitization processing
  - huaweicloudsdkfunctiongraph (optional) for creating an automatic
    desensitization FunctionGraph function + OBS event trigger

Subcommands:
  list             List image objects (jpg/jpeg/png/bmp/webp/gif) under a bucket/prefix
  process          List, download, desensitize and upload results back to OBS in one run
  setup-trigger    (Advanced) Create a FunctionGraph function + OBS trigger for auto desensitization
"""

import argparse
import base64
import json
import os
import re
import subprocess
import sys
import tempfile

try:
    from PIL import Image, ImageFilter, ImageDraw
except ImportError:
    Image = None

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".gif", ".tif", ".tiff"}

DEFAULT_RESULT_PREFIX = "desensitized/"

OBS_EVENT_MAP = {
    "ObjectCreated": ["ObjectCreated"],
    "Put": ["Put"],
    "Post": ["Post"],
    "Copy": ["Copy"],
    "CompleteMultipartUpload": ["CompleteMultipartUpload"],
}


def log(msg):
    sys.stderr.write("[obs-image-desens] %s\n" % msg)


def run_cmd(cmd, capture=True):
    log("run: %s" % " ".join(str(c) for c in cmd))
    proc = subprocess.run([str(c) for c in cmd], capture_output=capture, text=True)
    if proc.returncode != 0:
        raise RuntimeError("command failed (%s): %s" % (proc.returncode, (proc.stderr or "").strip()[:500]))
    return (proc.stdout or "")


def list_objects(bucket, prefix=""):
    """Use obsutil to list object keys under bucket/prefix."""
    obs_url = "obs://%s/%s" % (bucket, prefix) if prefix else "obs://%s" % bucket
    out = run_cmd(["hcloud", "obs", "ls", obs_url, "-s"])
    keys = []
    for line in out.splitlines():
        line = line.strip()
        m = re.match(r"^obs://[^/]+/(.+)$", line)
        if m:
            key = m.group(1).strip()
            if key:
                keys.append(key)
    seen = []
    for k in keys:
        if k not in seen:
            seen.append(k)
    return seen


def is_image(key):
    return os.path.splitext(key)[1].lower() in IMAGE_EXTS


def filter_images(keys):
    return [k for k in keys if is_image(k)]


def do_list(bucket, prefix, show_all):
    keys = list_objects(bucket, prefix)
    images = filter_images(keys)
    log("total objects: %d, image candidates: %d" % (len(keys), len(images)))
    output = {"bucket": bucket, "prefix": prefix, "objects": len(keys), "images": []}
    for k in keys:
        if is_image(k) or show_all:
            output["images"].append(k)
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return output


# ---------------------------------------------------------------------------
# PIL desensitization rules
# ---------------------------------------------------------------------------

def _check_pil():
    if Image is None:
        raise RuntimeError("Pillow is required. Install it with: pip install Pillow")


def apply_rule_pil(img, rule, rule_params):
    """Apply a desensitization rule to a PIL image. Returns the processed image."""
    _check_pil()
    rule = rule or "whole"
    rule_params = rule_params or {}

    if rule == "whole":
        block = int(rule_params.get("block_size", 12))
        return _pixelate(img, block)
    elif rule == "blur":
        radius = int(rule_params.get("radius", 8))
        return img.filter(ImageFilter.GaussianBlur(radius))
    elif rule == "region":
        boxes = _parse_regions(rule_params.get("regions"), img.size)
        block = int(rule_params.get("block_size", 12))
        return _apply_region(img, boxes, lambda _im: _pixelate(_im, block))
    elif rule == "region-blur":
        boxes = _parse_regions(rule_params.get("regions"), img.size)
        radius = int(rule_params.get("radius", 8))
        return _apply_region(img, boxes, lambda _im: _im.filter(ImageFilter.GaussianBlur(radius)))
    elif rule == "region-block":
        boxes = _parse_regions(rule_params.get("regions"), img.size)
        fill = rule_params.get("fill", "black")
        return _apply_region(img, boxes, lambda _im: _solid(_im, fill))
    elif rule == "edges":
        # Edge/corner darkening is intentionally not exposed (security constraint);
        # unknown rules are rejected explicitly.
        raise ValueError("unknown desensitization rule: %s" % rule)
    else:
        raise ValueError(
            "unsupported rule: %s (supported: whole, blur, region, region-blur, region-block)" % rule)


def _pixelate(img, block):
    w, h = img.size
    block = max(2, int(block))
    small = img.resize((max(1, w // block), max(1, h // block)), Image.BILINEAR)
    return small.resize((w, h), Image.NEAREST)


def _solid(img, color):
    return Image.new(img.mode, img.size, color=color)


def _parse_regions(regions, size):
    """Parse regions into PIL boxes. Support:
      - "100,50,300,200"      (absolute x0,y0,x1,y1)
      - JSON list form passed as string
    """
    if not regions:
        raise ValueError("region rules require --regions (e.g. 100,50,300,200)")
    if isinstance(regions, str):
        regions = regions.split(";")
    boxes = []
    for item in regions:
        item = item.strip()
        if not item:
            continue
        coords = [int(v.strip()) for v in re.split(r"[,x\s]+", item) if v.strip() != ""]
        if len(coords) != 4:
            raise ValueError("invalid region: %s (expected x0,y0,x1,y1)" % item)
        x0, y0, x1, y1 = coords
        if x0 < 0 or y0 < 0 or x1 > size[0] or y1 > size[1] or x1 <= x0 or y1 <= y0:
            raise ValueError("region %s out of image bounds %s" % (item, size))
        boxes.append((x0, y0, x1, y1))
    return boxes


def _apply_region(img, boxes, op):
    out = img.copy()
    for (x0, y0, x1, y1) in boxes:
        region = out.crop((x0, y0, x1, y1))
        out.paste(op(region), (x0, y0))
    return out


# ---------------------------------------------------------------------------
# process subcommand
# ---------------------------------------------------------------------------

def do_process(args):
    """One-run: list -> download -> desensitize -> upload."""
    source_bucket = args.source_bucket
    source_prefix = args.source_prefix or ""
    target_bucket = args.target_bucket or source_bucket
    target_prefix = args.target_prefix or DEFAULT_RESULT_PREFIX

    keys = list_objects(source_bucket, source_prefix)
    images = filter_images(keys)
    if not images:
        log("no image candidates found under obs://%s/%s" % (source_bucket, source_prefix))
        print(json.dumps({"status": "no_images", "images": []}, ensure_ascii=False))
        return {"status": "no_images"}

    if not getattr(args, "yes", False):
        # interactive confirmation
        log("candidate images (%d):" % len(images))
        for k in images:
            log("  %s" % k)
        ans = input("Proceed with desensitization for all candidates above? (yes/no): ").strip().lower()
        if ans not in ("yes", "y", ""):
            print(json.dumps({"status": "cancelled"}, ensure_ascii=False))
            return {"status": "cancelled"}

    results = []
    with tempfile.TemporaryDirectory(prefix="obs_desens_") as tmpdir:
        for key in images:
            res = _process_one(key, source_bucket, target_bucket, target_prefix, args, tmpdir)
            results.append(res)
        successful = [r for r in results if r["status"] == "success"]
        failed = [r for r in results if r["status"] != "success"]

    summary = {
        "status": "done" if not failed else "partial",
        "source_bucket": source_bucket,
        "target_bucket": target_bucket,
        "target_prefix": target_prefix,
        "total": len(results),
        "successful": len(successful),
        "failed": len(failed),
        "results": results,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return summary


def _process_one(key, source_bucket, target_bucket, target_prefix, args, tmpdir):
    basename = os.path.basename(key)
    local_src = os.path.join(tmpdir, "src_" + basename)
    local_dst = os.path.join(tmpdir, "dst_" + basename)
    try:
        src_url = "obs://%s/%s" % (source_bucket, key)
        run_cmd(["hcloud", "obs", "cp", src_url, local_src])
        if not os.path.exists(local_src):
            return {"key": key, "status": "failed", "error": "download produced no file"}
        img = Image.open(local_src)
        img.load()
        rule = args.rule
        rule_params = {}
        if rule in ("whole", "blur"):
            rule_params = {"block_size": args.block_size, "radius": args.radius}
        if rule.startswith("region"):
            rule_params = {"regions": args.regions, "block_size": args.block_size,
                           "radius": args.radius, "fill": args.fill}
        processed = apply_rule_pil(img, rule, rule_params)
        # Preserve original format; fallback to PNG if the format cannot be saved as-is
        fmt = img.format or "PNG"
        try:
            processed.save(local_dst, format=fmt)
        except Exception:
            local_dst = os.path.splitext(local_dst)[0] + ".png"
            processed.save(local_dst, format="PNG")
        target_key = target_prefix.rstrip("/") + "/" + basename if target_prefix else basename
        dst_url = "obs://%s/%s" % (target_bucket, target_key)
        run_cmd(["hcloud", "obs", "cp", local_dst, dst_url])
        return {"key": key, "target": target_key, "status": "success"}
    except Exception as exc:
        return {"key": key, "status": "failed", "error": str(exc)[:300]}


# ---------------------------------------------------------------------------
# setup-trigger subcommand (FunctionGraph + OBS trigger)
# ---------------------------------------------------------------------------

def do_setup_trigger(args):
    """Create a FunctionGraph function with embedded auto-desensitization code
    plus an OBS trigger. Requires huaweicloudsdkfunctiongraph + environment
    credentials (HUAWEICLOUD_SDK_AK / HUAWEICLOUD_SDK_SK)."""
    try:
        from huaweicloudsdkcore.auth.credentials import BasicCredentials
        from huaweicloudsdkfunctiongraph.v2 import (
            FunctionGraphClient,
            CreateFunctionRequest,
            CreateFunctionRequestBody,
            FuncCode,
            CreateFunctionTriggerRequest,
            CreateFunctionTriggerRequestBody,
            TriggerEventDataRequestBody,
        )
        from huaweicloudsdkfunctiongraph.v2.region.functiongraph_region import FunctionGraphRegion
        from huaweicloudsdkcore.exceptions.exceptions import ClientRequestException
    except ImportError:
        raise RuntimeError("huaweicloudsdkfunctiongraph is required for setup-trigger. "
                           "Install with: pip install huaweicloudsdkfunctiongraph")

    ak = args.ak or os.environ.get("HUAWEICLOUD_SDK_AK") or os.environ.get("HUAWEI_AK")
    sk = args.sk or os.environ.get("HUAWEICLOUD_SDK_SK") or os.environ.get("HUAWEI_SK")
    project_id = args.project_id or os.environ.get("HUAWEI_PROJECT_ID")
    region = args.region or os.environ.get("HUAWEI_REGION") or "cn-north-4"
    if not ak or not sk:
        raise RuntimeError("AK/SK required (--ak/--sk or HUAWEICLOUD_SDK_AK/HUAWEICLOUD_SDK_SK)")

    credentials = BasicCredentials(ak=ak, sk=sk, project_id=project_id)
    client = FunctionGraphClient.new_builder().with_credentials(credentials) \
        .with_region(FunctionGraphRegion.value_of(region)).build()

    function_name = args.function_name
    func_code = _build_auto_func_code(args)

    body = CreateFunctionRequestBody(
        func_name=function_name,
        package=args.package or "default",
        runtime=args.runtime or "Python3.9",
        handler=args.handler or "index.handler",
        memory_size=args.memory or 256,
        timeout=args.timeout or 60,
        description="Auto OBS image desensitization generated by huawei-cloud-obs-image-desens",
        code_type="inline",
        func_code=FuncCode(file=func_code),
    )
    function = client.create_function(CreateFunctionRequest(body=body))
    function_urn = function.func_urn
    log("function created: %s" % function_urn)

    if not args.no_trigger:
        event_data = TriggerEventDataRequestBody(
            name=args.trigger_name or function_name + "-obs",
            bucket=args.trigger_bucket,
            events=OBS_EVENT_MAP.get(args.event_type or "ObjectCreated") or [args.event_type],
            prefix=args.trigger_prefix or args.source_prefix or "",
            suffix=args.trigger_suffix or "",
        )
        trigger_body = CreateFunctionTriggerRequestBody(
            trigger_type_code="OBS",
            trigger_status=args.trigger_status or "ACTIVE",
            event_type_code="OBS",
            event_data=event_data,
        )
        try:
            trigger = client.create_function_trigger(
                CreateFunctionTriggerRequest(function_urn=function_urn, body=trigger_body))
            log("OBS trigger created on %s" % args.trigger_bucket)
            trigger_id = trigger.trigger_id
        except ClientRequestException as exc:
            log("trigger create failed: %s (function remains)" % str(exc)[:300])
            trigger_id = None
    else:
        trigger_id = None

    out = {
        "status": "success",
        "function_name": function_name,
        "function_urn": function_urn,
        "trigger_id": trigger_id,
        "trigger_bucket": args.trigger_bucket if not args.no_trigger else None,
        "region": region,
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return out


def _build_auto_func_code(args):
    """Inline FunctionGraph handler code that reads OBS event, downloads the object,
    applies the rule and uploads the result back to OBS."""
    rule = args.rule
    block_size = args.block_size
    radius = args.radius
    fill = args.fill
    if args.trigger_prefix or args.source_prefix:
        src_prefix = (args.trigger_prefix or args.source_prefix or "").rstrip("/")
    else:
        src_prefix = ""
    code = '''# -*- coding: utf-8 -*-
import base64
import json
import os

import boto3

RULE = "%(rule)s"
RADIUS = int(%(radius)d)
BLOCK = int(%(block_size)d)
FILL = "%(fill)s"
SRC_PREFIX = "%(src_prefix)s"


def _pixelate(img):
    w, h = img.size
    small = img.resize((max(1, w // BLOCK), max(1, h // BLOCK)))
    return small.resize((w, h))


def handler(event, context):
    records = event.get("Records") or event.get("records") or []
    desens = []
    for rec in records:
        try:
            bucket = rec["obs"]["bucket"]["name"]
            key = rec["obs"]["object"]["key"]
        except Exception:
            continue
        if SRC_PREFIX and not key.startswith(SRC_PREFIX):
            continue
        if not key.lower().endswith((".jpg", ".jpeg", ".png", ".bmp", ".webp", ".gif")):
            continue
        s3 = boto3.client("s3", endpoint_url=os.environ.get("OBS_ENDPOINT"),
                          aws_access_key_id=os.environ.get("OBS_AK"),
                          aws_secret_access_key=os.environ.get("OBS_SK"))
        data = s3.get_object(Bucket=bucket, Key=key)["Body"].read()
        from io import BytesIO
        from PIL import Image
        img = Image.open(BytesIO(data))
        if RULE == "blur":
            from PIL import ImageFilter
            img = img.filter(ImageFilter.GaussianBlur(RADIUS))
        else:
            img = _pixelate(img)
        buf = BytesIO()
        img.save(buf, format=img.format or "PNG")
        s3.put_object(Bucket=bucket, Key=key, Body=buf.getvalue())
        desens.append({"bucket": bucket, "key": key})
    return {"desensitized": desens}
''' % {
        "rule": rule, "radius": radius, "block_size": block_size,
        "fill": fill, "src_prefix": src_prefix,
    }
    return base64.b64encode(code.encode("utf-8")).decode("utf-8")


def build_parser():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="command", required=True)

    p_list = sub.add_parser("list", help="List image objects under a bucket/prefix")
    p_list.add_argument("--bucket", required=True)
    p_list.add_argument("--prefix", default="")
    p_list.add_argument("--show-all", action="store_true",
                        help="show all objects including non-image files")
    p_list.set_defaults(command="list")

    p_proc = sub.add_parser("process", help="One-run desensitization: list+download+process+upload")
    p_proc.add_argument("--source-bucket", required=True)
    p_proc.add_argument("--source-prefix", default="")
    p_proc.add_argument("--target-bucket", default="")
    p_proc.add_argument("--target-prefix", default=DEFAULT_RESULT_PREFIX)
    p_proc.add_argument("--rule", default="whole",
                        choices=["whole", "blur", "region", "region-blur", "region-block"],
                        help="desensitization rule")
    p_proc.add_argument("--block-size", type=int, default=12, help="mosaic block size (px)")
    p_proc.add_argument("--radius", type=int, default=8, help="Gaussian blur radius")
    p_proc.add_argument("--regions", default="", help="regions 'x0,y0,x1,y1[;x0,y0,x1,y1]'")
    p_proc.add_argument("--fill", default="black", help="region-block fill color")
    p_proc.add_argument("--yes", action="store_true", help="skip confirmation")
    p_proc.set_defaults(command="process")

    p_trig = sub.add_parser("setup-trigger",
                            help="(Advanced) create FunctionGraph function + OBS trigger")
    p_trig.add_argument("--function-name", required=True)
    p_trig.add_argument("--trigger-bucket", required=False)
    p_trig.add_argument("--trigger-prefix", default="")
    p_trig.add_argument("--trigger-suffix", default="")
    p_trig.add_argument("--event-type", default="ObjectCreated",
                        choices=list(OBS_EVENT_MAP.keys()) + ["ObjectRemoved"])
    p_trig.add_argument("--region", default="")
    p_trig.add_argument("--project-id", default="")
    p_trig.add_argument("--ak", default="")
    p_trig.add_argument("--sk", default="")
    p_trig.add_argument("--runtime", default="Python3.9")
    p_trig.add_argument("--handler", default="index.handler")
    p_trig.add_argument("--package", default="default")
    p_trig.add_argument("--memory", type=int, default=256)
    p_trig.add_argument("--timeout", type=int, default=60)
    p_trig.add_argument("--rule", default="whole",
                        choices=["whole", "blur", "region", "region-blur", "region-block"])
    p_trig.add_argument("--block-size", type=int, default=12)
    p_trig.add_argument("--radius", type=int, default=8)
    p_trig.add_argument("--regions", default="")
    p_trig.add_argument("--fill", default="black")
    p_trig.add_argument("--source-prefix", default="", help="in-function prefix filter")
    p_trig.add_argument("--trigger-name", default="")
    p_trig.add_argument("--trigger-status", default="ACTIVE")
    p_trig.add_argument("--no-trigger", action="store_true",
                        help="create function only, skip the OBS trigger")
    p_trig.set_defaults(command="setup-trigger")

    return p


def main():
    p = build_parser()
    args = p.parse_args()

    try:
        if args.command == "list":
            do_list(args.bucket, args.prefix, args.show_all)
        elif args.command == "process":
            do_process(args)
        elif args.command == "setup-trigger":
            do_setup_trigger(args)
        else:
            p.print_help()
    except KeyboardInterrupt:
        sys.exit(130)
    except Exception as exc:
        sys.stderr.write("ERROR: %s\n" % exc)
        sys.exit(1)


if __name__ == "__main__":
    main()