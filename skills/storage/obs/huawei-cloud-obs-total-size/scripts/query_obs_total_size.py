#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Query the total size of Huawei Cloud OBS buckets.

Prints ONLY the size value (a number, in bytes by default) — nothing else.

Primary executor : KooCLI obsutil-backed `hcloud OBS ls obs://<bucket>/ -du -bf=raw`
                   (returns the exact bucket size in bytes; `hcloud OBS ls` lists buckets).
Fallback executor: huaweicloudsdkobs Python SDK
                   (lists buckets, lists objects per bucket and sums their sizes).

Multi-region handling: when summing across all buckets, each bucket is queried
with its own regional endpoint (`-e=obs.<region>.myhuaweicloud.com` for CLI, a
client bound to the bucket's location for the SDK). A single bucket that cannot
be queried (NoSuchBucket / NoSuchKey / permission denied) is skipped with a
warning to stderr instead of aborting the whole summation.

Security note: external commands are always invoked as an argv list
(`subprocess.run([...])`, never `shell=True`, never a shell string), so bucket
names and other arguments are never interpreted by a shell and there is no
command-injection surface. Bucket names are additionally validated with a
strict whitelist regex before being passed to any tool.

Usage:
  python3 query_obs_total_size.py [--bucket <name>] [--all]
      [--unit bytes|kb|mb|gb] [--human] [--region <region>] [--executor auto|cli|sdk]

Examples:
  python3 query_obs_total_size.py --bucket my-bucket          # single bucket size in bytes
  python3 query_obs_total_size.py --all                       # total across all buckets
  python3 query_obs_total_size.py --all --unit mb             # total in MB
  python3 query_obs_total_size.py --all --human               # human readable
"""

import argparse
import os
import re
import subprocess
import sys

_REGION_RE = re.compile(r"([a-z]{2}-[a-z0-9]+-\d)")
# Bucket names: 3-63 chars, lowercase letters/digits/hyphens/dots, no spaces,
# quotes, semicolons or other shell-significant characters. Rejects every
# character that could carry a command-injection payload.
_BUCKET_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]$")
_CRED_ENV_HINTS = (
    "HUAWEI_ACCESS_KEY / HUAWEI_SECRET_KEY "
    "(or HUAWEICLOUD_SDK_AK / HUAWEICLOUD_SDK_SK)"
)


def _resolve_credentials():
    """Resolve AK/SK from common Huawei Cloud environment variables."""
    a_key = (
        os.environ.get("HUAWEI_ACCESS_KEY")
        or os.environ.get("HUAWEICLOUD_SDK_AK")
        or os.environ.get("HUAWEI_CLOUD_ACCESS_KEY")
        or os.environ.get("HW_ACCESS_KEY")
    )
    s_key = (
        os.environ.get("HUAWEI_SECRET_KEY")
        or os.environ.get("HUAWEICLOUD_SDK_SK")
        or os.environ.get("HUAWEI_CLOUD_SECRET_KEY")
        or os.environ.get("HW_SECRET_KEY")
    )
    return a_key, s_key


def _build_sdk_client(region):
    from huaweicloudsdkobs.v1.obs_client import ObsClient
    from huaweicloudsdkobs.v1.obs_credentials import ObsCredentials
    from huaweicloudsdkobs.v1.region.obs_region import ObsRegion

    a_key, s_key = _resolve_credentials()
    if not a_key or not s_key:
        raise RuntimeError(
            "No AK/SK environment variables detected. Set %s and retry.\n"
            "提示：未检测到 AK/SK 环境变量，请设置 %s 后重试（AK/SK 可在华为云控制台「我的凭证」页面获取）。"
            % (_CRED_ENV_HINTS, _CRED_ENV_HINTS)
        )
    credentials = ObsCredentials(a_key, s_key)
    return ObsClient.new_builder().with_credentials(credentials).with_region(ObsRegion.value_of(region)).build()


def _validate_bucket_name(name):
    """Reject bucket names that do not match the OBS bucket-name whitelist.

    Called before any external command or SDK call so that bucket names can
    never be used as a command-injection vector. OBS bucket names may only
    contain lowercase letters, digits, hyphens and dots (3-63 chars).
    """
    if not name:
        return
    if not _BUCKET_NAME_RE.match(name):
        raise RuntimeError(
            "Invalid OBS bucket name: %r. Bucket names may only contain "
            "lowercase letters, digits, hyphens and dots (3-63 chars). "
            "Refusing to continue to avoid malformed/shell-injected arguments. "
            "(桶名称不合法：仅允许小写字母、数字、连字符和点，长度 3-63。)" % name
        )


def _run_cli(cmd):
    # Command injection safety: `cmd` is always an argv list and never goes
    # through a shell (no `shell=True`, no shell string concatenation). Every
    # argument that reaches this function from user input (--bucket) has been
    # validated by _validate_bucket_name above.
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if proc.returncode != 0:
        raise RuntimeError((proc.stderr or proc.stdout or "").strip())
    return proc.stdout


def list_buckets_cli():
    """List (name, region) pairs via `hcloud OBS ls`.

    Handles obsutil's wrapped-line output where a long bucket name spills onto
    the next line together with the creation date and region.
    """
    out = _run_cli(["hcloud", "OBS", "ls"])
    buckets = []
    current = None
    pending = False
    for line in out.splitlines():
        line = line.rstrip()
        m = re.match(r"obs://([^\s/]+)", line)
        if m:
            if current:
                buckets.append(current)
            current = {"name": m.group(1), "region": "", "pending": False}
            rest = line[m.end():]
            dm = re.search(r"\d{4}-\d{2}-\d{2}T[\d:]+Z", rest)
            if dm:
                rm = _REGION_RE.search(rest[dm.end():])
                if rm:
                    current["region"] = rm.group(1)
                else:
                    current["pending"] = True
            else:
                current["pending"] = True
        elif current and current.get("pending") and line.strip():
            dm = re.search(r"\d{4}-\d{2}-\d{2}T[\d:]+Z", line)
            if dm:
                rm = _REGION_RE.search(line[dm.end():])
                if rm:
                    current["region"] = rm.group(1)
            current["pending"] = False
    if current:
        buckets.append(current)
    return [(b["name"], b["region"]) for b in buckets]


def _parse_cli_size(text):
    """Parse the '[DU] Total bucket size: N[unit]' line into bytes.

    Tolerant of obsutil output variations: a bare integer (e.g. `5002295`),
    an integer with a 'B' suffix (`5002295B`), or a human-readable value with
    a unit suffix (`4.77MB`). Returns None if the line cannot be parsed.
    """
    m = re.search(r"Total bucket size:\s*([\d.]+)\s*([KMGTP]?B?)\b", text, re.IGNORECASE)
    if m is None:
        return None
    num = float(m.group(1))
    unit = (m.group(2) or "B").upper()
    factors = {
        "B": 1,
        "KB": 1024,
        "MB": 1024 ** 2,
        "GB": 1024 ** 3,
        "TB": 1024 ** 4,
        "PB": 1024 ** 5,
    }
    return int(num * factors.get(unit, 1))


def _friendly_error(bucket, raw):
    """Map common obsutil error patterns to a friendly bilingual message."""
    if "NoSuchBucket" in raw or "NoSuchKey" in raw or "404" in raw or "does not exist" in raw:
        return (
            "Cannot query bucket %s: the bucket does not exist (NoSuchBucket). "
            "Please check the bucket name. (查询桶 %s 失败：该桶不存在，请检查桶名称是否正确。)" % (bucket, bucket)
        )
    if "AccessDenied" in raw or "403" in raw or "Forbidden" in raw:
        return (
            "Cannot query bucket %s: the current credentials have no access to this bucket (AccessDenied). "
            "(查询桶 %s 失败：当前凭证无权限访问该桶。)" % (bucket, bucket)
        )
    if "InvalidAccessKeyId" in raw or "Please set ak" in raw:
        return (
            "Cannot query bucket %s: obsutil credentials are not configured or are invalid. "
            "Run `hcloud obs config` to set AK/SK/endpoint. "
            "(查询桶 %s 失败：obsutil 凭证未配置或无效，请先执行 hcloud obs config 配置 AK/SK/endpoint。)" % (bucket, bucket)
        )
    return "Cannot query bucket %s: %s (查询桶 %s 失败：%s)" % (bucket, raw[:300], bucket, raw[:300])


def bucket_size_cli(bucket, region=""):
    """Get exact bucket size in bytes via `hcloud OBS ls obs://<bucket>/ -du -bf=raw`.

    When a region is known, binds the bucket's regional endpoint with `-e=...`
    so cross-region buckets can be measured from any default endpoint.
    """
    _validate_bucket_name(bucket)
    cmd = ["hcloud", "OBS", "ls", "obs://%s" % bucket, "-du", "-bf=raw"]
    if region:
        cmd.append("-e=obs.%s.myhuaweicloud.com" % region)
    try:
        out = _run_cli(cmd)
    except RuntimeError as exc:
        raise RuntimeError(_friendly_error(bucket, str(exc)))
    size = _parse_cli_size(out)
    if size is None:
        raise RuntimeError(
            "Cannot query bucket %s: unable to parse the total bucket size from the obsutil output. "
            "(查询桶 %s 失败：无法解析 obsutil 输出中的总大小。)" % (bucket, bucket)
        )
    return size


def total_size_cli(buckets):
    """Sum bucket sizes via CLI. Per-bucket failures are skipped with a warning
    (stderr) so a single inaccessible bucket never aborts the whole sum. When
    only one bucket was requested, its error propagates directly."""
    total = 0
    failed = 0
    errors = []
    for name, region in buckets:
        try:
            total += bucket_size_cli(name, region)
        except Exception as exc:
            failed += 1
            errors.append(str(exc))
            if len(buckets) > 1:
                print("Warning: %s (警告：%s)" % (exc, exc), file=sys.stderr)
    if failed == len(buckets) and total == 0:
        if len(buckets) == 1:
            raise RuntimeError(errors[0] if errors else "Query bucket failed / 查询桶失败")
        raise RuntimeError(
            "All buckets failed to be queried, cannot compute the total size. "
            "Please check the credentials and bucket permissions. "
            "(所有桶均查询失败，无法汇总总大小。请检查凭证配置与桶权限。)"
        )
    return total


def list_buckets_sdk(client):
    from huaweicloudsdkobs.v1.model import ListBucketsRequest

    res = client.list_buckets(ListBucketsRequest()).to_dict()
    buckets = (res.get("buckets") or {}).get("bucket") or []
    return [(b.get("name"), b.get("location") or "") for b in buckets]


def bucket_size_sdk(client, bucket):
    """Sum sizes of all objects in a bucket via the SDK (paginated)."""
    from huaweicloudsdkobs.v1.model import ListObjectsRequest

    total = 0
    marker = None
    while True:
        req = ListObjectsRequest(bucket_name=bucket, max_keys=1000, marker=marker)
        d = client.list_objects(req).to_dict()
        for c in d.get("contents") or []:
            total += int(c.get("size") or 0)
        marker = d.get("next_marker")
        if not d.get("is_truncated") or not marker:
            break
    return total


def total_size_sdk(client, buckets, default_region):
    """Sum sizes of buckets via the SDK. Buckets may live in different regions;
    a client bound to the bucket's own location is used when known. Per-bucket
    failures are skipped with a warning (friendly mapped, no raw traceback)."""
    total = 0
    failed = 0
    errors = []
    for entry in buckets:
        if isinstance(entry, tuple):
            name, loc = entry
        else:
            name, loc = entry, ""
        region = loc or default_region
        region = region.replace("-oss-", "-").split(".")[0]
        if not region:
            region = default_region
        _validate_bucket_name(name)
        try:
            c = _build_sdk_client(region)
            total += bucket_size_sdk(c, name)
        except Exception as exc:
            failed += 1
            errors.append(str(exc))
            if len(buckets) > 1:
                friendly = _friendly_error(name, str(exc))
                print("Warning: %s (警告：%s)" % (friendly, friendly), file=sys.stderr)
    if failed == len(buckets) and total == 0:
        if len(buckets) == 1:
            raise RuntimeError(_friendly_error(buckets[0][0] if isinstance(buckets[0], tuple) else buckets[0],
                                              errors[0] if errors else "Query bucket failed / 查询桶失败"))
        raise RuntimeError(
            "All buckets failed to be queried, cannot compute the total size. "
            "Please check the credentials and bucket permissions. "
            "(所有桶均查询失败，无法汇总总大小。请检查凭证配置与桶权限。)"
        )
    return total


def format_size(value, unit, human):
    if human:
        size = float(value)
        for u in ("B", "KB", "MB", "GB", "TB"):
            if size < 1024 or u == "TB":
                return "%.2f%s" % (size, u)
            size /= 1024
        return str(int(value))
    if unit == "bytes":
        return str(int(value))
    factors = {"kb": 1024.0, "mb": 1024.0 * 1024.0, "gb": 1024.0 ** 3}
    if unit in factors:
        return "%.2f" % (value / factors[unit])
    return str(int(value))


def main():
    parser = argparse.ArgumentParser(
        description="Query total size of Huawei Cloud OBS buckets. Prints a single size value (bytes by default)."
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--bucket", default="", help="OBS bucket name; total size of this bucket only")
    group.add_argument(
        "--all", action="store_true",
        help="Total size across all buckets (default when --bucket is not given)",
    )
    parser.add_argument(
        "--unit", default="bytes", choices=["bytes", "kb", "mb", "gb"],
        help="Output unit (default bytes)",
    )
    parser.add_argument("--human", action="store_true", help="Human readable size (e.g. 4.77MB)")
    parser.add_argument("--region", default="cn-north-4", help="Huawei Cloud region (default cn-north-4)")
    parser.add_argument(
        "--executor", default="auto", choices=["auto", "cli", "sdk"],
        help="Execution method: cli (hcloud obsutil), sdk (python SDK), auto (try cli first, fallback to sdk)",
    )
    args = parser.parse_args()

    _validate_bucket_name(args.bucket)

    buckets = None
    try:
        if args.executor == "cli":
            names = [(args.bucket, "")] if args.bucket else list_buckets_cli()
            total = total_size_cli(names)
        elif args.executor == "sdk":
            client = _build_sdk_client(args.region)
            all_buckets = list_buckets_sdk(client)
            if args.bucket:
                loc_map = {n: (n, loc) for n, loc in all_buckets}
                names = [loc_map.get(args.bucket, (args.bucket, ""))]
            else:
                names = all_buckets
            total = total_size_sdk(client, names, args.region)
        else:  # auto
            try:
                names = [(args.bucket, "")] if args.bucket else list_buckets_cli()
                total = total_size_cli(names)
            except RuntimeError as cli_err:
                # Single-bucket requests propagate the CLI's friendly error
                # (no double traceback). For --all, fall back to the SDK only
                # when the CLI path failed as a whole (e.g. obsutil not
                # configured); per-bucket skips already emit warnings.
                if args.bucket:
                    raise cli_err
                client = _build_sdk_client(args.region)
                all_buckets = list_buckets_sdk(client)
                names = all_buckets
                total = total_size_sdk(client, names, args.region)
    except RuntimeError as exc:
        print("Error: %s (错误：%s)" % (exc, exc), file=sys.stderr)
        sys.exit(1)

    print(format_size(total, args.unit, args.human))


if __name__ == "__main__":
    main()