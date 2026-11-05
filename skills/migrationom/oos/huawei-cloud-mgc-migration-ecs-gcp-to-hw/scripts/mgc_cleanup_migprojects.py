#!/usr/bin/env python3
"""List and delete Huawei Cloud SMS/MgC migration projects.

The SMS.8115 error (migration project count limit reached) is resolved by
deleting obsolete ``mgc*`` projects created by this workflow. This helper
lists the projects of the destination account and, when ``--apply`` is
given, deletes the selected ones.

The account's default migration project (``isdefault=true``) cannot be
deleted through the API: DELETE returns ``HTTP 400 ... SMS.7303``. To remove
it, first create or promote another project as the default in the SMS/MgC
console, then rerun this script.

Usage (dry-run by default):

  python3 scripts/mgc_cleanup_migprojects.py
  python3 scripts/mgc_cleanup_migprojects.py --apply
  python3 scripts/mgc_cleanup_migprojects.py --apply --name-prefix "" --keep <id>
"""

import argparse
import json
import os
import sys

from mgc_migrate import HcApiClient, env_default, write_json_file

DEFAULT_MIGPROJECT_ERROR_HINT = (
    "Default migration project cannot be deleted (SMS.7303). In the SMS/MgC "
    "console, set another migration project as the account default first, "
    "then delete this one."
)


def list_migprojects(client: HcApiClient, endpoint: str) -> list:
    rsp = client.request_json("GET", f"{endpoint}/v3/migprojects")
    projects = rsp.get("migprojects")
    if projects is None:
        projects = rsp.get("migration_projects") or []
    return [p for p in projects if isinstance(p, dict)]


def delete_migproject(client: HcApiClient, endpoint: str, project_id: str) -> None:
    client.request_json("DELETE", f"{endpoint}/v3/migprojects/{project_id}")


def parse_args(argv: list) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="List and delete SMS/MgC migration projects (dry-run by default)."
    )
    parser.add_argument(
        "--endpoint",
        default=env_default("SMS_ENDPOINT", "https://sms.ap-southeast-3.myhuaweicloud.com").rstrip("/"),
        help="SMS endpoint (default: SMS_ENDPOINT env or ap-southeast-3).",
    )
    parser.add_argument(
        "--access-key",
        default=env_default("DESTINATION_ACCESS_KEY", ""),
        help="Destination account AK (default: DESTINATION_ACCESS_KEY).",
    )
    parser.add_argument(
        "--secret-key",
        default=env_default("DESTINATION_SECRET_KEY", ""),
        help="Destination account SK (default: DESTINATION_SECRET_KEY).",
    )
    parser.add_argument(
        "--name-prefix",
        default="mgc",
        help="Only consider projects whose name starts with this prefix; pass '' for all.",
    )
    parser.add_argument(
        "--keep",
        action="append",
        default=[],
        help="Project ID to keep (repeatable).",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually delete the matched projects (default is dry-run).",
    )
    parser.add_argument(
        "--result-path",
        default=env_default("MIGPROJECT_CLEANUP_RESULT", "./out/migproject_cleanup.json"),
        help="Where to write the cleanup summary JSON.",
    )
    return parser.parse_args(argv)


def main(argv: list) -> int:
    args = parse_args(argv)
    if not args.access_key or not args.secret_key:
        raise RuntimeError(
            "Destination AK/SK are required: pass --access-key/--secret-key or set "
            "DESTINATION_ACCESS_KEY/DESTINATION_SECRET_KEY."
        )

    client = HcApiClient(args.access_key, args.secret_key)
    projects = list_migprojects(client, args.endpoint)
    keep = {str(item).strip() for item in args.keep if str(item).strip()}
    prefix = str(args.name_prefix or "")

    considered = []
    for project in projects:
        project_id = str(project.get("id") or "").strip()
        name = str(project.get("name") or "").strip()
        if not project_id:
            continue
        if prefix and not name.startswith(prefix):
            continue
        considered.append(project)

    results = []
    for project in considered:
        project_id = str(project.get("id") or "").strip()
        name = str(project.get("name") or "").strip()
        is_default = bool(project.get("isdefault"))
        entry = {
            "id": project_id,
            "name": name,
            "isdefault": is_default,
            "action": "kept",
            "reason": "",
        }
        if project_id in keep:
            entry["reason"] = "listed in --keep"
        elif is_default:
            entry["reason"] = "default project: cannot be deleted via API"
            print(f"[MGC-CLEANUP] SKIP default project {name} ({project_id})")
            print(f"[MGC-CLEANUP]   {DEFAULT_MIGPROJECT_ERROR_HINT}")
        elif not args.apply:
            entry["action"] = "would_delete"
            print(f"[MGC-CLEANUP] WOULD DELETE {name} ({project_id})")
        else:
            try:
                delete_migproject(client, args.endpoint, project_id)
                entry["action"] = "deleted"
                print(f"[MGC-CLEANUP] DELETED {name} ({project_id})")
            except RuntimeError as exc:
                detail = str(exc)
                entry["action"] = "delete_failed"
                entry["reason"] = detail
                print(f"[MGC-CLEANUP] FAILED to delete {name} ({project_id}): {detail}")
                if "SMS.7303" in detail:
                    print(f"[MGC-CLEANUP]   {DEFAULT_MIGPROJECT_ERROR_HINT}")
        results.append(entry)

    summary = {
        "endpoint": args.endpoint,
        "dry_run": not args.apply,
        "name_prefix": prefix,
        "total_projects": len(projects),
        "considered_projects": len(considered),
        "deleted": [r["id"] for r in results if r["action"] == "deleted"],
        "would_delete": [r["id"] for r in results if r["action"] == "would_delete"],
        "skipped_default": [r["id"] for r in results if r["isdefault"]],
        "failed": [r for r in results if r["action"] == "delete_failed"],
        "results": results,
        "total_after": len(projects)
        - len([r for r in results if r["action"] == "deleted"]),
    }
    write_json_file(args.result_path, summary)
    print(f"[MGC-CLEANUP] summary written to {os.path.abspath(args.result_path)}")
    return 1 if summary["failed"] else 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except RuntimeError as exc:
        print(f"[MGC-CLEANUP] ERROR: {exc}", file=sys.stderr)
        sys.exit(2)