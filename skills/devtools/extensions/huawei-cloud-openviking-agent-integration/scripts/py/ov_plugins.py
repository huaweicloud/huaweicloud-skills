#!/usr/bin/env python3
"""ov_plugins.py — Plugin provisioning helpers CLI.

Replaces heredoc Python in lib/plugins.sh.

Subcommands:
    validate-source <url> <host> <path>   exit 0 if URL points at official repo
    diff-blobs <old-tree.json> <new-tree.json> <exdir>   print A/M/D diff lines
    blob-map <tree.json> <exdir>          print path<TAB>sha lines
    sha1-verify <file> <expected-sha>     exit 0 if git-blob SHA-1 matches
    parse-sha <json-response>             print commit SHA from GitHub API JSON
"""
import hashlib
import json
import sys
import os
from urllib.parse import urlparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def cmd_validate_source(args):
    url, host, path = args[0], args[1], args[2]
    u = urlparse(url)
    ok_host = u.hostname in (host, f"www.{host}")
    p = u.path.rstrip("/").lstrip("/")
    if p.endswith(".git"):
        p = p[: -len(".git")]
    ok_path = p == path or p.endswith("/" + path)
    sys.exit(0 if (ok_host and ok_path and u.scheme in ("http", "https")) else 1)


def _blob_map(tree_json_path, exdir):
    with open(tree_json_path) as f:
        d = json.load(f)
    result = {}
    for e in d.get("tree", []):
        if e.get("type") == "blob" and e.get("path", "").startswith(exdir + "/"):
            result[e["path"]] = e["sha"]
    return result


def cmd_diff_blobs(args):
    old, new, exdir = args[0], args[1], args[2]
    o = _blob_map(old, exdir)
    n = _blob_map(new, exdir)
    for p in sorted(set(o) | set(n)):
        if p not in o:
            print("A", p)
        elif p not in n:
            print("D", p)
        elif o[p] != n[p]:
            print("M", p)


def cmd_blob_map(args):
    tree_path, exdir = args[0], args[1]
    m = _blob_map(tree_path, exdir)
    for path, sha in m.items():
        print(f"{path}\t{sha}")


def cmd_sha1_verify(args):
    file_path, expected = args[0], args[1]
    with open(file_path, "rb") as f:
        data = f.read()
    actual = hashlib.sha1(b"blob %d\x00" % len(data) + data).hexdigest()
    sys.exit(0 if actual == expected else 1)


def cmd_parse_sha(args):
    """Print the SHA from a GitHub commits/HEAD API response (stdin or arg)."""
    raw = args[0] if args else sys.stdin.read()
    try:
        d = json.loads(raw)
        print(d.get("sha", ""))
    except Exception:
        print("")


def main():
    cmd = sys.argv[1]
    args = sys.argv[2:]
    dispatch = {
        "validate-source": cmd_validate_source,
        "diff-blobs": cmd_diff_blobs,
        "blob-map": cmd_blob_map,
        "sha1-verify": cmd_sha1_verify,
        "parse-sha": cmd_parse_sha,
    }
    fn = dispatch.get(cmd)
    if not fn:
        print(f"Unknown subcommand: {cmd}", file=sys.stderr)
        sys.exit(2)
    fn(args)


if __name__ == "__main__":
    main()
