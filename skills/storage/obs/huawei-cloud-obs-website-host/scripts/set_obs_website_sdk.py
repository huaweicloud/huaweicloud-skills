#!/usr/bin/env python3
import argparse
import os
from pathlib import Path
import sys


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Set OBS static website hosting via Huawei OBS Python SDK"
    )
    p.add_argument("bucket_name", help="OBS bucket name")
    p.add_argument("endpoint", help="OBS endpoint, e.g. https://obs.<region>.myhuaweicloud.com")
    p.add_argument("--index-document", default="index.html", help="Index document key")
    p.add_argument("--error-document", default="", help="Error document key (optional)")
    p.add_argument(
        "--custom-domain",
        required=True,
        help="Custom domain to register on the bucket (required)",
    )
    p.add_argument(
        "--access-key",
        default="",
        help="AK (optional; defaults to HW_ACCESS_KEY or ~/.obsutilconfig)",
    )
    p.add_argument(
        "--secret-key",
        default="",
        help="SK (optional; defaults to HW_SECRET_KEY or ~/.obsutilconfig)",
    )
    p.add_argument(
        "--security-token",
        default="",
        help="Security token (optional; defaults to HW_SECURITY_TOKEN or ~/.obsutilconfig)",
    )
    p.add_argument(
        "--obsutil-config",
        default=str(Path.home() / ".obsutilconfig"),
        help="obsutil config file path (default: ~/.obsutilconfig)",
    )
    p.add_argument(
        "--certificate",
        default="",
        help="HTTPS certificate (PEM) to attach to the custom domain. Requires --private-key and --certificate-name.",
    )
    p.add_argument(
        "--private-key",
        default="",
        help="Private key (PEM) matching --certificate. Requires --certificate and --certificate-name.",
    )
    p.add_argument(
        "--certificate-name",
        default="",
        help="Certificate name (3-63 chars) for the custom domain HTTPS binding.",
    )
    p.add_argument(
        "--certificate-id",
        default="",
        help="CCM certificate ID (16 chars) from Cloud Certificate Manager, alternative to PEM direct upload.",
    )
    return p


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


def pick_credential(cli_val: str, env_val: str, cfg: dict[str, str], cfg_keys: tuple[str, ...]) -> str:
    if cli_val:
        return cli_val
    if env_val:
        return env_val
    for key in cfg_keys:
        val = cfg.get(key, "")
        if val:
            return val
    return ""


def build_cert_info(
    name: str, certificate: str, private_key: str, certificate_id: str
) -> dict[str, str]:
    cert_info: dict[str, str] = {"name": name}
    if certificate or private_key:
        if not certificate or not private_key:
            raise SystemExit(
                "--certificate and --private-key must be provided together "
                "when attaching a PEM certificate"
            )
        cert_info["certificate"] = certificate
        cert_info["privateKey"] = private_key
    elif certificate_id:
        cert_info["certificateId"] = certificate_id
    else:
        raise SystemExit(
            "--certificate-name requires either --certificate/--private-key "
            "or --certificate-id"
        )
    return cert_info


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    custom_domain = args.custom_domain.strip()
    if not custom_domain:
        parser.error("--custom-domain must not be blank")

    cert_info: dict[str, str] | None = None
    if args.certificate_name:
        if not (3 <= len(args.certificate_name) <= 63):
            parser.error("--certificate-name must be 3-63 characters long")
        if args.certificate_id and len(args.certificate_id) != 16:
            parser.error("--certificate-id must be a 16-character CCM certificate ID")
        cert_info = build_cert_info(
            args.certificate_name.strip(),
            args.certificate,
            args.private_key,
            args.certificate_id.strip(),
        )

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

    missing = []
    if not access_key:
        missing.append("ak")
    if not secret_key:
        missing.append("sk")
    if missing:
        print(
            "missing credentials: "
            + ", ".join(missing)
            + ". Fill them in ~/.obsutilconfig (or pass CLI args / env vars).",
            file=sys.stderr,
        )
        print(
            "checked sources: --access-key/--secret-key, HW_ACCESS_KEY/HW_SECRET_KEY, and obsutil config file.",
            file=sys.stderr,
        )
        return 2

    try:
        from obs import ObsClient, WebsiteConfiguration, IndexDocument, ErrorDocument  # type: ignore  # noqa: E501
    except Exception as exc:  # noqa: BLE001
        print(f"obs sdk not available: {exc}", file=sys.stderr)
        print("install with: pip install esdk-obs-python", file=sys.stderr)
        return 2

    client = ObsClient(
        access_key_id=access_key,
        secret_access_key=secret_key,
        security_token=security_token or None,
        server=args.endpoint,
    )

    try:
        # NOTE: esdk-obs-python >= 3.x requires WebsiteConfiguration model objects.
        # setBucketWebsite(bucketName, website, extensionHeaders=None)
        # where website is a WebsiteConfiguration with IndexDocument/ErrorDocument.
        index_doc = IndexDocument(suffix=args.index_document)
        if args.error_document:
            error_doc = ErrorDocument(key=args.error_document)
            website = WebsiteConfiguration(indexDocument=index_doc, errorDocument=error_doc)
        else:
            website = WebsiteConfiguration(indexDocument=index_doc)
        website_resp = client.setBucketWebsite(args.bucket_name, website)

        if cert_info:
            custom_domain_resp = client.setBucketCustomDomain(
                args.bucket_name, custom_domain, certificateInfo=cert_info
            )
        else:
            custom_domain_resp = client.setBucketCustomDomain(args.bucket_name, custom_domain)
    except Exception as exc:  # noqa: BLE001
        print(f"OBS configuration failed: {exc}", file=sys.stderr)
        return 1
    finally:
        client.close()

    website_status = getattr(website_resp, "status", None)
    if website_status is None or not (200 <= int(website_status) < 300):
        print(f"setBucketWebsite unexpected status: {website_status}", file=sys.stderr)
        return 1

    custom_domain_status = getattr(custom_domain_resp, "status", None)
    if custom_domain_status is None or not (200 <= int(custom_domain_status) < 300):
        print(
            f"setBucketCustomDomain unexpected status: {custom_domain_status}",
            file=sys.stderr,
        )
        return 1

    https_mode = " with HTTPS certificate" if cert_info else ""
    print(f"ok: website hosting configured, custom domain {custom_domain} registered{https_mode}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
