#!/usr/bin/env python3
"""Normalize Terraform provider sources for HuaweiCloud SAC templates."""

import argparse
import json
import os
import pathlib
import re
import sys
from typing import Any, Tuple

HUAWEICLOUD_PATTERNS = [
    re.compile(r'source\s*=\s*"[^"]*huaweicloud[^"]*"', re.IGNORECASE),
]

KUBERNETES_PATTERNS = [
    re.compile(r'source\s*=\s*"[^"]*kubernetes[^"]*"', re.IGNORECASE),
]


def normalize_source_text(content: str) -> Tuple[str, bool]:
    updated = content

    for pattern in HUAWEICLOUD_PATTERNS:
        updated = pattern.sub('source = "huaweicloud/huaweicloud"', updated)

    for pattern in KUBERNETES_PATTERNS:
        updated = pattern.sub('source = "hashicorp/kubernetes"', updated)

    return updated, updated != content


def find_block_end(text: str, open_brace_idx: int) -> int:
    depth = 0
    for i in range(open_brace_idx, len(text)):
        ch = text[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return i
    return -1


def patch_huaweicloud_provider_block(block_body: str, include_token: bool = False) -> tuple[str, bool]:
    changed = False
    updated = block_body

    replacements = {
        "access_key": "var.access_key",
        "secret_key": "var.secret_key",
        "region": "var.region",
    }
    if include_token:
        replacements["security_token"] = "var.security_token"

    for key, expr in replacements.items():
        pattern = re.compile(rf"(?m)^(\s*{key}\s*=\s*)(.+?)\s*$")
        match = pattern.search(updated)
        if match:
            current_value = match.group(2).strip()
            if current_value != expr:
                updated = pattern.sub(rf"\1{expr}", updated, count=1)
                changed = True
        else:
            # Default 2-space indentation for provider body attributes.
            line = f"  {key} = {expr}"
            if updated.strip():
                updated = updated.rstrip() + "\n" + line + "\n"
            else:
                updated = line + "\n"
            changed = True

    return updated, changed


def ensure_hcl_variables(content: str, include_token: bool = False) -> tuple[str, bool]:
    changed = False
    updated = content.rstrip() + "\n"
    required_vars = ["access_key", "secret_key", "region"]
    if include_token:
        required_vars.append("security_token")

    for name in required_vars:
        if re.search(rf'(?m)\bvariable\s+"{re.escape(name)}"\s*\{{', updated):
            continue
        block = f'\nvariable "{name}" {{\n  type = string\n  sensitive = true\n}}\n'
        updated += block
        changed = True

    return updated, changed


def patch_hcl_provider_credentials(content: str, include_token: bool = False) -> tuple[str, bool]:
    changed = False
    updated = content

    pattern = re.compile(r'(?is)provider\s+"huaweicloud"\s*\{')
    cursor = 0
    chunks: list[str] = []

    while True:
        match = pattern.search(updated, cursor)
        if not match:
            chunks.append(updated[cursor:])
            break

        block_start = match.start()
        open_brace_idx = updated.find("{", match.start(), match.end())
        if open_brace_idx < 0:
            chunks.append(updated[cursor:])
            break
        close_brace_idx = find_block_end(updated, open_brace_idx)
        if close_brace_idx < 0:
            chunks.append(updated[cursor:])
            break

        chunks.append(updated[cursor : open_brace_idx + 1])
        body = updated[open_brace_idx + 1 : close_brace_idx]
        patched_body, body_changed = patch_huaweicloud_provider_block(body, include_token)
        chunks.append(patched_body)
        chunks.append("}")
        changed = changed or body_changed
        cursor = close_brace_idx + 1

    merged = "".join(chunks)
    merged, var_changed = ensure_hcl_variables(merged, include_token)
    return merged, changed or var_changed


def normalize_tf_json(content: str, include_token: bool = False) -> Tuple[str, bool]:
    data = json.loads(content)
    changed = False

    def normalize_required_providers(obj: Any) -> None:
        nonlocal changed
        if not isinstance(obj, dict):
            return

        terraform_block = obj.get("terraform")
        if not isinstance(terraform_block, dict):
            return

        required = terraform_block.get("required_providers")
        provider_maps = []
        if isinstance(required, dict):
            provider_maps = [required]
        elif isinstance(required, list):
            provider_maps = [entry for entry in required if isinstance(entry, dict)]
        else:
            return

        for provider_map in provider_maps:
            for provider_name, provider_cfg in provider_map.items():
                if not isinstance(provider_cfg, dict):
                    continue

                source_value = str(provider_cfg.get("source", "")).lower()
                provider_name_l = str(provider_name).lower()

                if "huaweicloud" in provider_name_l or "huaweicloud" in source_value:
                    if provider_cfg.get("source") != "huaweicloud/huaweicloud":
                        provider_cfg["source"] = "huaweicloud/huaweicloud"
                        changed = True
                    continue

                if "kubernetes" in provider_name_l or "kubernetes" in source_value:
                    if provider_cfg.get("source") != "hashicorp/kubernetes":
                        provider_cfg["source"] = "hashicorp/kubernetes"
                        changed = True

    if isinstance(data, dict):
        normalize_required_providers(data)

    def patch_provider_cfg(provider_cfg: dict) -> None:
        nonlocal changed
        mapping = {
            "access_key": "${var.access_key}",
            "secret_key": "${var.secret_key}",
            "region": "${var.region}",
        }
        if include_token:
            mapping["security_token"] = "${var.security_token}"
        for key, expr in mapping.items():
            if provider_cfg.get(key) != expr:
                provider_cfg[key] = expr
                changed = True

    def normalize_provider_blocks(obj: Any) -> None:
        if not isinstance(obj, dict):
            return
        provider = obj.get("provider")
        if isinstance(provider, dict):
            for name, cfg in provider.items():
                if "huaweicloud" not in str(name).lower():
                    continue
                if isinstance(cfg, dict):
                    patch_provider_cfg(cfg)
                elif isinstance(cfg, list):
                    for item in cfg:
                        if isinstance(item, dict):
                            patch_provider_cfg(item)
        elif isinstance(provider, list):
            for entry in provider:
                if not isinstance(entry, dict):
                    continue
                for name, cfg in entry.items():
                    if "huaweicloud" not in str(name).lower():
                        continue
                    if isinstance(cfg, dict):
                        patch_provider_cfg(cfg)
                    elif isinstance(cfg, list):
                        for item in cfg:
                            if isinstance(item, dict):
                                patch_provider_cfg(item)

    def ensure_json_variables(obj: Any) -> None:
        nonlocal changed
        if not isinstance(obj, dict):
            return
        var_block = obj.get("variable")
        if not isinstance(var_block, dict):
            var_block = {}
            obj["variable"] = var_block
            changed = True
        names = ["access_key", "secret_key", "region"]
        if include_token:
            names.append("security_token")
        for name in names:
            if name not in var_block:
                var_block[name] = {"type": "string", "sensitive": True}
                changed = True

    if isinstance(data, dict):
        normalize_provider_blocks(data)
        ensure_json_variables(data)

    updated = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    return updated, changed


def process_file(tf_file: pathlib.Path, dry_run: bool, include_token: bool = False) -> bool:
    original = tf_file.read_text(encoding="utf-8")

    if tf_file.name.endswith(".tf.json"):
        updated, changed = normalize_tf_json(original, include_token)
    else:
        updated_sources, changed_sources = normalize_source_text(original)
        updated, changed_provider = patch_hcl_provider_credentials(updated_sources, include_token)
        changed = changed_sources or changed_provider

    if changed and not dry_run:
        tf_file.write_text(updated, encoding="utf-8")

    return changed


def write_credentials_tfvars(
    root: pathlib.Path,
    ak: str,
    sk: str,
    region: str,
    out_file: str,
    token: str = "",
) -> pathlib.Path:
    out_path = (root / out_file).resolve()
    tfvars = {
        "access_key": ak,
        "secret_key": sk,
        "region": region,
    }
    if token:
        tfvars["security_token"] = token
    out_path.write_text(json.dumps(tfvars, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.chmod(out_path, 0o600)
    return out_path


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Normalize Terraform provider source for huaweicloud and kubernetes providers. "
            "Optionally write AK/SK/region into terraform.auto.tfvars.json."
        )
    )
    parser.add_argument("directory", help="Directory containing Terraform files")
    parser.add_argument("--dry-run", action="store_true", help="Show changes without writing")
    parser.add_argument("--ak", default="", help="HuaweiCloud Access Key (fallback: env HW_ACCESS_KEY)")
    parser.add_argument("--sk", default="", help="HuaweiCloud Secret Key (fallback: env HW_SECRET_KEY)")
    parser.add_argument("--region", default="", help="HuaweiCloud region, e.g. cn-north-4 (fallback: env HW_REGION)")
    parser.add_argument("--token", default="", help="REQUIRED SecurityToken for temporary federated credentials (fallback: env HW_SECURITY_TOKEN). Long-term keys without a token are refused.")
    parser.add_argument(
        "--tfvars-file",
        default="terraform.auto.tfvars.json",
        help="tfvars filename written under directory when --ak/--sk/--region are provided",
    )
    args = parser.parse_args()
    if not args.ak:
        args.ak = os.environ.get("HW_ACCESS_KEY", "")
    if not args.sk:
        args.sk = os.environ.get("HW_SECRET_KEY", "")
    if not args.region:
        args.region = os.environ.get("HW_REGION", "")
    if not args.token:
        args.token = os.environ.get("HW_SECURITY_TOKEN", "")

    root = pathlib.Path(args.directory).expanduser().resolve()
    if not root.exists() or not root.is_dir():
        print(f"Directory does not exist: {root}", file=sys.stderr)
        return 1

    has_any_cred = bool(args.ak or args.sk or args.region or args.token)
    has_all_cred = bool(args.ak and args.sk and args.region)
    if has_any_cred and not has_all_cred:
        print("When providing credentials, --ak --sk --region must all be set.", file=sys.stderr)
        return 3
    if has_all_cred and not args.token:
        print(
            "Refused: only temporary credentials are accepted. "
            "Provide --token (or env HW_SECURITY_TOKEN); long-term keys without a SecurityToken are not allowed.",
            file=sys.stderr,
        )
        return 3

    tf_files = sorted(root.rglob("*.tf")) + sorted(root.rglob("*.tf.json"))
    if not tf_files:
        print(f"No Terraform files found in: {root}")
        return 2

    changed_files = []
    include_token = bool(args.token)
    for tf_file in tf_files:
        if process_file(tf_file, args.dry_run, include_token):
            changed_files.append(tf_file)

    print(f"Scanned {len(tf_files)} .tf files in {root}")
    print(f"Changed {len(changed_files)} files")
    for path in changed_files:
        print(f" - {path}")

    tfvars_path = (root / args.tfvars_file).resolve()
    if has_all_cred:
        if args.dry_run:
            print("Dry-run enabled: skip writing credentials tfvars file.")
        else:
            out_path = write_credentials_tfvars(root, args.ak, args.sk, args.region, args.tfvars_file, args.token)
            print(f"Wrote credentials tfvars: {out_path}")
            print("Keep this file local and do not commit it to git.")
    else:
        if tfvars_path.exists():
            print(f"Using existing credentials tfvars: {tfvars_path}")
        else:
            print(
                "No credentials provided and no tfvars file found. "
                "Set --ak --sk --region --token or env HW_ACCESS_KEY/HW_SECRET_KEY/HW_REGION/HW_SECURITY_TOKEN "
                "(temporary credentials with SecurityToken only).",
                file=sys.stderr,
            )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
