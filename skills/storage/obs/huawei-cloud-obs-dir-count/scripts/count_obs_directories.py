#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Count directories (folders) in a Huawei Cloud OBS bucket or under a prefix.

Read-only operation only. This script NEVER creates, modifies, deletes or
uploads any bucket or object. It lists directories with the hcloud OBS module
(obsutil behind the scenes) and prints an integer count.

Security properties:
  - Inputs are validated with strict allow-list regexes (no shell metacharacters
    can reach the subprocess), so a malicious --bucket / --prefix cannot inject.
  - Commands are executed with a plain argv list via subprocess.run(...) with
    shell=False -- no shell, no eval, no exec, no dynamic import.
  - hcloud is located with shutil.which(), never spawned through a shell.
  - Credentials are read only from the user's own obsutil configuration; this
    script never reads, prints, or forwards AK/SK values.

Exit codes:
  0  success (count printed)
  2  usage / input validation error
  3  runtime error (CLI missing, config missing, network/API/permission error)
"""

import argparse
import json
import re
import shutil
import subprocess
import sys

# Strict allow-list validation. These regexes reject spaces, quotes, semicolons,
# backticks, dollar signs, pipes, newlines and any other shell/URL metacharacters.
BUCKET_RE = re.compile(r"^[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]$")
PREFIX_RE = re.compile(r"^[A-Za-z0-9._/-]*$")
CLOUD_URL_RE = re.compile(r"^obs://[A-Za-z0-9][A-Za-z0-9.-]{1,61}[a-z0-9](?:/[A-Za-z0-9._/-]*)?$")

PAGE_LIMIT = 1000  # obsutil default page size; paginate beyond this via -marker


def err(msg_en, msg_zh=None):
    """Write a bilingual error to stderr (English primary + Chinese hint)."""
    out = "[ERROR] {0}".format(msg_en)
    if msg_zh:
        out += "\n{0}".format(msg_zh)
    sys.stderr.write(out + "\n")


def check_bucket(value):
    if not BUCKET_RE.match(value or ""):
        err(
            "Invalid bucket name {0!r}. Bucket names must be 3-63 characters, "
            "start and end with a lowercase letter or digit, and contain only "
            "lowercase letters, digits, hyphens (-) and periods (.).".format(value),
            "[提示] 桶名不合法：请使用小写字母、数字、点(.)和短横线(-)，长度3-63字符，以字母或数字开头结尾。",
        )
        return False
    return True


def check_prefix(value):
    if value is None:
        return True
    if not PREFIX_RE.match(value):
        err(
            "Invalid prefix {0!r}. Prefix may contain only letters, digits, "
            "dot (.), underscore (_), slash (/) and hyphen (-). Spaces and shell "
            "metacharacters are not allowed.".format(value),
            "[提示] 前缀不合法：仅允许字母、数字、点(.)、下划线(_)、斜杠(/)和短横线(-)，不允许空格或特殊字符。",
        )
        return False
    if value.startswith("/") or value.endswith("/") or "//" in value:
        err(
            "Invalid prefix {0!r}. Prefix must not start or end with '/' and must "
            "not contain consecutive slashes.".format(value),
            "[提示] 前缀不能以/开头或结尾，也不能包含连续的//。",
        )
        return False
    return True


def find_hcloud():
    path = shutil.which("hcloud")
    if not path:
        err(
            "hcloud (KooCLI) was not found on PATH. Install it first; see the "
            "skill references/cli-installation-guide.md for a signed, user-level install.",
            "[提示] 未找到 hcloud(KooCLI) 命令，请先安装；安装与校验方法见技能 references/cli-installation-guide.md。",
        )
        return None
    return path


def run_obs_list(hcloud, url, extra=None):
    """Run `hcloud OBS ls <url> -d [-limit=N] [-marker=X]` (no shell).

    Returns (exit_code, stdout, stderr, error_kind). error_kind is one of
    'cli-missing'/'config'/'auth'/'notfound'/'other' or None.
    """
    cmd = [hcloud, "OBS", "ls", url, "-d", "-limit={0}".format(PAGE_LIMIT)]
    if extra:
        cmd.extend(extra)
    try:
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=120,
        )
    except FileNotFoundError:
        return 1, "", str(cmd), "cli-missing"
    except subprocess.TimeoutExpired:
        return 1, "", "timeout", "other"

    out = (proc.stdout or "") + "\n" + (proc.stderr or "")
    kind = classify_error(out)
    return proc.returncode, proc.stdout or "", proc.stderr or "", kind


def classify_error(output):
    low = output.lower()
    if "please set ak, sk and endpoint" in low or "configuration file" in low:
        return "config"
    if (
        "invalidaccesskeyid" in low
        or "signaturedoesnotmatch" in low
        or "accessdenied" in low
        or "forbidden" in low
        or "unauthorized" in low
    ):
        return "auth"
    if "nosuchbucket" in low or "bucket not found" in low or "404" in low:
        return "notfound"
    return "other"


def parse_level(output):
    """Parse one `obsutil ls -d` output page.

    Returns (dirs, next_marker) where dirs is the set of immediate directory
    paths (already stripped of 'obs://' and trailing '/') and next_marker is a
    continuation marker string or None.
    """
    dirs = set()
    next_marker = None
    in_folder_list = False
    for raw in output.splitlines():
        line = raw.rstrip("\r\n")
        stripped = line.strip()
        if stripped.startswith("Folder list:"):
            in_folder_list = True
            continue
        if stripped.startswith("Object list:"):
            in_folder_list = False
            continue
        if stripped.startswith("Next marker:"):
            next_marker = stripped[len("Next marker:"):].strip()
            continue
        if in_folder_list and stripped.startswith("obs://"):
            path = stripped[len("obs://"):].rstrip("/")
            if path:
                dirs.add(path)
    return dirs, next_marker


def fetch_all_dirs(hcloud, url):
    """Fetch every immediate directory under `url`, following -marker pages.

    Returns (dirs, error_kind) or (None, error_kind) on fatal error.
    """
    all_dirs = set()
    marker = None
    while True:
        extra = ["-marker={0}".format(marker)] if marker else None
        code, out, _serr, kind = run_obs_list(hcloud, url, extra)
        if (code != 0 and kind != "other") or (code != 0 and not out):
            # 'other' kinds with a non-zero code but no parseable markers may be
            # transient; treat as fatal only when we could not parse a page.
            return None, kind
        dirs, next_marker = parse_level(out)
        all_dirs.update(dirs)
        if not next_marker or next_marker == marker:
            break
        marker = next_marker
    return all_dirs, None


def expected_query_path(bucket, prefix):
    """Normalized 'bucket/prefix' used to detect obsutil's self-folder entry."""
    if prefix:
        return "{0}/{1}".format(bucket, prefix.rstrip("/"))
    return bucket


def count_immediate(hcloud, bucket, prefix):
    url = "obs://{0}".format("/".join(p for p in (bucket, prefix) if p))
    dirs, kind = fetch_all_dirs(hcloud, url)
    if dirs is None:
        return None, kind
    self_path = expected_query_path(bucket, prefix)
    # Exclude the query prefix itself (obsutil lists it as a folder only when
    # the prefix contains direct objects/files, so it is not a sub-directory).
    return len([d for d in dirs if d != self_path]), None


def count_recursive(hcloud, bucket, prefix, max_depth):
    """Breadth-first count of every sub-directory under bucket[/prefix]."""
    root = prefix.rstrip("/") if prefix else ""
    self_path = expected_query_path(bucket, root)
    queue = [(root, 0)]  # (relative_prefix, depth_so_far)
    total = 0
    visited = {self_path}
    while queue:
        rel, depth = queue.pop(0)
        depth_children = depth + 1
        if max_depth > 0 and depth_children > max_depth:
            continue
        path_key = "{0}/{1}".format(bucket, rel).rstrip("/") if rel else bucket
        url = "obs://{0}".format("/".join(p for p in (bucket, rel) if p))
        if rel:
            # do not descend into the self entry polluting children; handled below
            pass
        dirs, kind = fetch_all_dirs(hcloud, url)
        if dirs is None:
            return None, kind
        for d in sorted(dirs):
            if d == self_path or d in visited:
                continue
            visited.add(d)
            total += 1
            rel_child = d[len(bucket):].lstrip("/")
            queue.append((rel_child, depth_children))
    return total, None


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="count_obs_directories.py",
        description="Count directories (folders) in a Huawei Cloud OBS bucket or prefix. "
                    "Read-only; never creates/modifies/deletes anything.",
    )
    parser.add_argument("--bucket", required=True,
                        help="OBS bucket name (lowercase letters, digits, . and -).")
    parser.add_argument("--prefix", default="",
                        help="Optional prefix (folder path) inside the bucket. "
                             "Letters, digits, . _ / - only.")
    parser.add_argument("-r", "--recursive", action="store_true",
                        help="Count directories at every level under the prefix instead "
                             "of only the immediate sub-directories.")
    parser.add_argument("--max-depth", type=int, default=0,
                        help="With --recursive, limit traversal depth (0 = unlimited).")
    parser.add_argument("--json", action="store_true",
                        help="Emit a JSON object instead of a bare integer.")
    args = parser.parse_args(argv)

    if not check_bucket(args.bucket):
        return 2
    if not check_prefix(args.prefix):
        return 2
    if args.max_depth < 0:
        err("--max-depth must be >= 0.",
            "[提示] --max-depth 必须大于等于0。")
        return 2

    hcloud = find_hcloud()
    if not hcloud:
        return 3

    if args.recursive:
        count, kind = count_recursive(hcloud, args.bucket, args.prefix, args.max_depth)
    else:
        count, kind = count_immediate(hcloud, args.bucket, args.prefix)

    if count is None:
        emit_error_for_kind(kind)
        return 3

    if args.json:
        print(json.dumps({
            "bucket": args.bucket,
            "prefix": args.prefix,
            "recursive": bool(args.recursive),
            "directory_count": count,
        }))
    else:
        print(count)
    return 0


def emit_error_for_kind(kind):
    if kind == "config":
        err(
            "OBS credentials are not configured. Run these commands yourself in your "
            "own terminal (never paste AK/SK into chat):\n"
            "  hcloud obs config -i=<YourAK> -k=<YourSK> -e=obs.<region>.myhuaweicloud.com\n"
            "Then retry.",
            "[提示] 未配置 obsutil 凭证。请在您自己的终端执行上述配置命令（请勿在对话中粘贴AK/SK），完成后再重试。",
        )
    elif kind == "auth":
        err(
            "Authentication or permission was denied. The AK/SK may be invalid or the "
            "IAM user lacks OBS read permission (obs:bucket:ListBucket). See "
            "references/iam-policies.md.",
            "[提示] 认证或权限校验失败：请检查AK/SK是否正确，或IAM用户是否缺少OBS只读权限(obs:bucket:ListBucket)。",
        )
    elif kind == "notfound":
        err(
            "The bucket or prefix does not exist (404). Confirm the bucket name and "
            "prefix, then retry.",
            "[提示] 未找到指定的桶或前缀(404)，请确认桶名与前缀是否正确。",
        )
    elif kind == "cli-missing":
        err(
            "hcloud CLI could not be executed. Check that it is installed on PATH.",
            "[提示] 无法执行 hcloud 命令，请检查是否已安装，或是否在PATH中。",
        )
    else:
        err(
            "Failed to list directories. Check the bucket and prefix, your network "
            "connectivity, and the obsutil endpoint configuration.",
            "[提示] 目录列举失败：请检查桶名/前缀、网络连通性以及 obsutil endpoint 配置。",
        )


if __name__ == "__main__":
    sys.exit(main())