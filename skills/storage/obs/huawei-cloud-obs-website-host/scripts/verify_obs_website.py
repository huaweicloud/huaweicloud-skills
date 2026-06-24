#!/usr/bin/env python3
import argparse
import json
import os
from pathlib import Path
import socket
import sys
from datetime import datetime, timezone
import urllib.error
import urllib.parse
import urllib.request


def fetch(url: str) -> tuple[int | None, str, str]:
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.getcode(), "", resp.geturl()
    except urllib.error.HTTPError as exc:
        return exc.code, f"HTTPError: {exc.reason}", exc.url or url
    except Exception as exc:  # noqa: BLE001
        return None, str(exc), url


def resolve_domain(hostname: str) -> tuple[list[str], str]:
    try:
        _, _, ips = socket.gethostbyname_ex(hostname)
        if not ips:
            return [], "no A record resolved"
        return sorted(set(ips)), ""
    except Exception as exc:  # noqa: BLE001
        return [], str(exc)


def remediation_for_check(name: str, status: int | None, error: str) -> str:
    error_l = (error or "").lower()
    if "certificate_verify_failed" in error_l or "hostname mismatch" in error_l:
        return (
            "TLS certificate mismatch. Bind a valid certificate for this custom domain "
            "or front OBS with CDN/ELB and terminate TLS there."
        )
    if status == 403:
        return (
            "HTTP 403 has two common causes in this workflow: "
            "the bucket/object policy does not allow anonymous public read for website access, "
            "or the AK/SK used for OBS SDK checks/configuration lacks required IAM permissions. "
            "Verify both the website public-read policy/ACL and IAM actions such as "
            "obs:bucket:HeadBucket, obs:bucket:GetBucketLocation, and obs:bucket:PutBucketWebsite."
        )
    if status == 404:
        if name in {"root_path", "index_document"}:
            return "Verify index document key/path and confirm website configuration points to the right index."
        return "If a custom error page is configured, 404 can be expected; otherwise verify missing-path behavior."
    if status == 301 or status == 302:
        return "Check whether endpoint/domain is redirecting unexpectedly; use the OBS website endpoint."
    if status is None:
        return f"Network or DNS error: {error}. Verify domain resolution and endpoint reachability."
    if status >= 500:
        return "Server-side failure. Retry and check OBS service health/endpoint correctness."
    return "Review endpoint, website config, and object paths."


def read_obsutil_config(path: str) -> dict[str, str]:
    cfg: dict[str, str] = {}
    p = Path(path).expanduser()
    if not p.exists():
        return cfg
    try:
        text = p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return cfg
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("#") or "=" not in s:
            continue
        key, value = s.split("=", 1)
        cfg[key.strip().lower()] = value.strip()
    return cfg


def pick_credential(
    cli_val: str, env_val: str, cfg: dict[str, str], cfg_keys: tuple[str, ...]
) -> str:
    if cli_val:
        return cli_val
    if env_val:
        return env_val
    for key in cfg_keys:
        val = cfg.get(key, "")
        if val:
            return val
    return ""


def run_bucket_region_check(
    bucket_name: str,
    obs_endpoint: str,
    expected_region: str,
    access_key: str,
    secret_key: str,
    security_token: str,
) -> dict[str, object]:
    result: dict[str, object] = {
        "enabled": True,
        "bucket_name": bucket_name,
        "obs_endpoint": obs_endpoint,
        "expected_region": expected_region,
        "actual_region": "",
        "head_bucket_status": None,
        "get_bucket_location_status": None,
        "passed": False,
        "error": "",
    }

    if not access_key or not secret_key:
        result["error"] = "missing AK/SK. Set HW_ACCESS_KEY and HW_SECRET_KEY (or pass --access-key/--secret-key)."
        return result

    try:
        from obs import ObsClient  # type: ignore
    except Exception as exc:  # noqa: BLE001
        result["error"] = f"OBS SDK not available: {exc}. Install with: pip install esdk-obs-python"
        return result

    client = ObsClient(
        access_key_id=access_key,
        secret_access_key=secret_key,
        security_token=security_token or None,
        server=obs_endpoint,
    )
    try:
        head = client.headBucket(bucket_name)
        head_status = int(getattr(head, "status", 0) or 0)
        result["head_bucket_status"] = head_status
        if not (200 <= head_status < 300):
            result["error"] = f"headBucket returned non-2xx status: {head_status}"
            return result

        location = client.getBucketLocation(bucket_name)
        location_status = int(getattr(location, "status", 0) or 0)
        result["get_bucket_location_status"] = location_status
        if not (200 <= location_status < 300):
            result["error"] = f"getBucketLocation returned non-2xx status: {location_status}"
            return result

        actual_region = str(getattr(getattr(location, "body", None), "location", "") or "")
        result["actual_region"] = actual_region
        if expected_region and actual_region and actual_region != expected_region:
            result["error"] = f"region mismatch: expected={expected_region}, actual={actual_region}"
            return result

        result["passed"] = True
        return result
    except Exception as exc:  # noqa: BLE001
        result["error"] = str(exc)
        return result
    finally:
        client.close()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify Huawei OBS static website endpoint"
    )
    parser.add_argument(
        "--bucket-name",
        required=True,
        help="OBS bucket name",
    )
    parser.add_argument(
        "--region",
        required=True,
        help="OBS region, for example cn-north-4",
    )
    parser.add_argument(
        "--domain",
        default="",
        help=(
            "Custom domain to verify instead of the default OBS website endpoint "
            "(optional; host or URL)"
        ),
    )
    parser.add_argument(
        "--index-document",
        default="index.html",
        help="Index document key (default: index.html)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output machine-readable JSON report",
    )
    parser.add_argument(
        "--access-key",
        default="",
        help="AK for optional bucket SDK check (defaults to HW_ACCESS_KEY)",
    )
    parser.add_argument(
        "--secret-key",
        default="",
        help="SK for optional bucket SDK check (defaults to HW_SECRET_KEY)",
    )
    parser.add_argument(
        "--security-token",
        default="",
        help="Security token for optional bucket SDK check (defaults to HW_SECURITY_TOKEN or ~/.obsutilconfig)",
    )
    parser.add_argument(
        "--obsutil-config",
        default=str(Path.home() / ".obsutilconfig"),
        help="obsutil config file path for optional bucket SDK check (default: ~/.obsutilconfig)",
    )
    args = parser.parse_args()

    raw_domain = args.domain.strip()
    if raw_domain:
        if "://" in raw_domain:
            parsed = urllib.parse.urlparse(raw_domain)
        else:
            parsed = urllib.parse.urlparse(f"http://{raw_domain}")
    else:
        parsed = urllib.parse.urlparse(
            f"http://{args.bucket_name}.obs.{args.region}.myhuaweicloud.com"
        )

    if not parsed.netloc and parsed.path:
        # Handle plain host input like "example.com" parsed into path.
        parsed = urllib.parse.urlparse(f"http://{parsed.path}")

    host_port = parsed.netloc
    if not host_port:
        print(f"invalid domain: {args.domain}", file=sys.stderr)
        return 2

    path_prefix = parsed.path.rstrip("/")
    scheme_bases = [("http", f"http://{host_port}{path_prefix}")]
    raw_site = scheme_bases[0][1]

    checks: list[dict[str, object]] = []
    verification_target = "custom_domain" if raw_domain else "default_obs_domain"
    for scheme, base in scheme_bases:
        checks.extend(
            [
                {
                    "scheme": scheme,
                    "name": "root_path",
                    "url": f"{base}/",
                    "expected": "HTTP 200",
                    "pass_statuses": {200},
                },
                {
                    "scheme": scheme,
                    "name": "index_document",
                    "url": f"{base}/{args.index_document}",
                    "expected": "HTTP 200",
                    "pass_statuses": {200},
                },
                {
                    "scheme": scheme,
                    "name": "missing_path",
                    "url": f"{base}/nonexistent-path",
                    "expected": "HTTP 404 or configured custom error page behavior",
                    "pass_statuses": {404, 200},
                    "advisory_only": True,
                },
            ]
        )

    domain = parsed.hostname or ""
    dns_ips, dns_error = ([], "")
    if domain:
        dns_ips, dns_error = resolve_domain(domain)

    results: list[dict[str, object]] = []
    dns_passed = bool(dns_ips) if domain else True
    all_passed = dns_passed
    remediation_steps: list[str] = []
    bucket_check: dict[str, object] = {"enabled": False}

    if not dns_passed:
        remediation_steps.append(
            f"DNS resolution failed for {domain}: {dns_error}. Verify A/CNAME record and propagation."
        )

    actions_performed = ["DNS resolution check for endpoint domain"]
    obs_endpoint = f"https://obs.{args.region}.myhuaweicloud.com"
    cfg = read_obsutil_config(args.obsutil_config)
    access_key = pick_credential(
        args.access_key,
        os.getenv("HW_ACCESS_KEY", ""),
        cfg,
        ("ak", "access_key_id"),
    )
    secret_key = pick_credential(
        args.secret_key,
        os.getenv("HW_SECRET_KEY", ""),
        cfg,
        ("sk", "secret_access_key"),
    )
    security_token = pick_credential(
        args.security_token,
        os.getenv("HW_SECURITY_TOKEN", ""),
        cfg,
        ("securitytoken", "security_token", "token"),
    )
    bucket_check = run_bucket_region_check(
        bucket_name=args.bucket_name,
        obs_endpoint=obs_endpoint,
        expected_region=args.region,
        access_key=access_key,
        secret_key=secret_key,
        security_token=security_token,
    )
    actions_performed.append("OBS SDK read-only check: headBucket + getBucketLocation")
    if not bool(bucket_check.get("passed", False)):
        all_passed = False
        error = str(bucket_check.get("error", "") or "bucket/region check failed")
        if "403" in error:
            remediation = (
                f"Bucket/region check failed: {error}. "
                "When troubleshooting 403, tell the user both common possibilities: "
                "the bucket/object is not public-read for website access, or the AK/SK lacks "
                "required IAM permissions. Verify bucket public-read policy/ACL and IAM actions "
                "such as obs:bucket:HeadBucket and obs:bucket:GetBucketLocation."
            )
        else:
            remediation = (
                f"Bucket/region check failed: {error}. "
                "Verify bucket name, OBS endpoint, region, and IAM permissions."
            )
        remediation_steps.append(remediation)

    for scheme, _base in scheme_bases:
        actions_performed.extend(
            [
                f"HTTP GET root path over {scheme.upper()}",
                f"HTTP GET index document over {scheme.upper()}",
                f"HTTP GET missing path over {scheme.upper()}",
            ]
        )

    for check in checks:
        status, error, final_url = fetch(check["url"])
        passed = status in check["pass_statuses"]
        advisory_only = bool(check.get("advisory_only", False))
        if not passed and not advisory_only:
            all_passed = False
            remediation = remediation_for_check(check["name"], status, error)
            if remediation not in remediation_steps:
                remediation_steps.append(remediation)
        else:
            remediation = ""
        results.append(
            {
                "name": check["name"],
                "scheme": check["scheme"],
                "url": check["url"],
                "expected": check["expected"],
                "status": status,
                "final_url": final_url,
                "passed": passed,
                "advisory_only": advisory_only,
                "error": error,
                "remediation": remediation,
            }
        )

    report = {
        "input_summary": {
            "site_url": raw_site,
            "bucket_name": args.bucket_name,
            "region": args.region,
            "domain_override": raw_domain,
            "verification_target": verification_target,
            "target_host": host_port,
            "checked_schemes": [scheme for scheme, _base in scheme_bases],
            "index_document": args.index_document,
            "checked_at_utc": datetime.now(timezone.utc).isoformat(),
            "domain": domain,
        },
        "actions_performed": actions_performed,
        "verification_results": {
            "bucket_region": bucket_check,
            "dns": {
                "domain": domain,
                "resolved_ips": dns_ips,
                "passed": dns_passed,
                "error": dns_error,
            },
            "http_checks": results,
            "overall_passed": all_passed,
        },
        "remediation_steps": remediation_steps,
    }

    if args.json:
        print(json.dumps(report, ensure_ascii=True, indent=2))
    else:
        print("Input summary:")
        print(f"- site_url: {report['input_summary']['site_url']}")
        print(f"- bucket_name: {report['input_summary']['bucket_name']}")
        print(f"- region: {report['input_summary']['region']}")
        print(f"- domain_override: {report['input_summary']['domain_override'] or 'none'}")
        print(f"- verification_target: {report['input_summary']['verification_target']}")
        print(f"- target_host: {report['input_summary']['target_host']}")
        print(f"- checked_schemes: {','.join(report['input_summary']['checked_schemes'])}")
        print(f"- index_document: {report['input_summary']['index_document']}")
        print(f"- checked_at_utc: {report['input_summary']['checked_at_utc']}")
        print(f"- domain: {report['input_summary']['domain']}")
        print()
        print("Actions performed:")
        for action in report["actions_performed"]:
            print(f"- {action}")
        print()
        print("Verification results:")
        bucket_region_report = report["verification_results"]["bucket_region"]
        if bucket_region_report.get("enabled"):
            if bucket_region_report.get("passed"):
                print(
                    "- bucket_region: PASS "
                    f"(bucket={bucket_region_report['bucket_name']}; "
                    f"expected_region={bucket_region_report['expected_region'] or 'n/a'}; "
                    f"actual_region={bucket_region_report['actual_region'] or 'unknown'})"
                )
            else:
                print(
                    "- bucket_region: FAIL "
                    f"({bucket_region_report.get('error', 'unknown error')})"
                )
        dns_report = report["verification_results"]["dns"]
        if dns_report["passed"]:
            print(f"- dns: PASS (resolved_ips={','.join(dns_report['resolved_ips'])})")
        else:
            print(f"- dns: FAIL ({dns_report['error']})")
        for item in report["verification_results"]["http_checks"]:
            status_text = "PASS" if item["passed"] else "FAIL"
            observed = item["status"] if item["status"] is not None else f"ERROR ({item['error']})"
            print(
                f"- {item['scheme']} {item['name']}: {status_text} "
                f"(expected: {item['expected']}; observed: {observed}; url: {item['url']})"
            )
        print(f"- overall: {'PASS' if report['verification_results']['overall_passed'] else 'FAIL'}")
        print()
        if remediation_steps:
            print("Remediation steps:")
            for step in remediation_steps:
                print(f"- {step}")
        else:
            print("Remediation steps:")
            print("- none")

    return 0 if all_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
