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

PLACEHOLDER_AK = "PLEASE_SET_ACCESS_KEY"
PLACEHOLDER_SK = "PLEASE_SET_SECRET_KEY"
PLACEHOLDER_REGION = "PLEASE_SET_REGION"

# Allowed Huawei Cloud regions. Kept in sync with the region validation used by the
# Dify template's region_id variable and SKILL.md's region_id allowed list.
ALLOWED_REGIONS = [
    "cn-north-4",
    "cn-southwest-2",
    "cn-north-12",
    "ap-southeast-3",
    "cn-east-3",
    "cn-north-9",
    "cn-south-2",
    "cn-south-1",
    "tr-west-1",
    "cn-south-4",
    "ap-southeast-1",
    "cn-north-2",
    "cn-north-1",
    "cn-east-4",
]

REGION_VALIDATION_HCL = (
    "  validation {{\n"
    "    condition     = contains({allowed}, var.{name})\n"
    '    error_message = "Invalid input, please re-enter."\n'
    "  }}\n"
)


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


def patch_huaweicloud_provider_block(block_body: str) -> tuple[str, bool]:
    changed = False
    updated = block_body

    replacements = {
        "access_key": "var.access_key",
        "secret_key": "var.secret_key",
        "region": "var.region",
    }

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


def region_variable_block_hcl(name: str = "region") -> str:
    """HCL block for the region variable, including an allow-list validation.

    Mirrors the validation already present on the template's region_id variable so
    an invalid region cannot bypass region_id by passing the provider `region`
    variable directly.
    """
    allowed = ", ".join(f'"{r}"' for r in ALLOWED_REGIONS)
    return (
        f'\nvariable "{name}" {{\n'
        f"  type = string\n"
        f"{REGION_VALIDATION_HCL.format(allowed='[' + allowed + ']', name=name)}"
        f"}}\n"
    )


def ensure_hcl_variables(content: str) -> tuple[str, bool]:
    changed = False
    updated = content.rstrip() + "\n"
    required_vars = ["access_key", "secret_key", "region"]

    for name in required_vars:
        # If a variable block already exists, ensure region carries the validation.
        existing = re.search(rf'(?m)\bvariable\s+"{re.escape(name)}"\s*\{{', updated)
        if existing:
            if name == "region":
                block_start = updated.find("{", existing.start(), existing.end())
                block_end = find_block_end(updated, block_start)
                if block_start >= 0 and block_end >= 0:
                    body = updated[block_start + 1 : block_end]
                    if not re.search(r"(?is)\bvalidation\s*\{", body):
                        updated, did_change = add_hcl_validation(updated, name, existing)
                        changed = changed or did_change
            continue
        block = region_variable_block_hcl(name) if name == "region" else f'\nvariable "{name}" {{\n  type = string\n}}\n'
        updated += block
        changed = True

    return updated, changed


def add_hcl_validation(content: str, name: str, match) -> tuple[str, bool]:
    """Inject an allow-list validation into an existing HCL variable block."""
    open_idx = content.find("{", match.start(), match.end())
    if open_idx < 0:
        return content, False
    close_idx = find_block_end(content, open_idx)
    if close_idx < 0:
        return content, False
    allowed = ", ".join(f'"{r}"' for r in ALLOWED_REGIONS)
    validation = REGION_VALIDATION_HCL.format(allowed="[" + allowed + "]", name=name)
    updated = content[: open_idx + 1] + "\n" + validation + content[open_idx + 1 :]
    return updated, True


def patch_hcl_provider_credentials(content: str) -> tuple[str, bool]:
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
        patched_body, body_changed = patch_huaweicloud_provider_block(body)
        chunks.append(patched_body)
        chunks.append("}")
        changed = changed or body_changed
        cursor = close_brace_idx + 1

    merged = "".join(chunks)
    merged, var_changed = ensure_hcl_variables(merged)
    return merged, changed or var_changed


def normalize_tf_json(content: str) -> Tuple[str, bool]:
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
        for name in ("access_key", "secret_key", "region"):
            if name not in var_block:
                var_block[name] = {"type": "string"}
                changed = True
        # Ensure the provider region variable carries the allow-list validation.
        region_cfg = var_block.get("region")
        if isinstance(region_cfg, dict) and not region_cfg.get("validation"):
            region_cfg["validation"] = [
                {
                    "condition": "${contains([" + ", ".join(f'"{r}"' for r in ALLOWED_REGIONS) + "], var.region)}",
                    "error_message": "Invalid input, please re-enter.",
                }
            ]
            changed = True

    if isinstance(data, dict):
        normalize_provider_blocks(data)
        ensure_json_variables(data)

    updated = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    return updated, changed


def process_file(tf_file: pathlib.Path, dry_run: bool) -> bool:
    original = tf_file.read_text(encoding="utf-8")

    if tf_file.name.endswith(".tf.json"):
        updated, changed = normalize_tf_json(original)
    else:
        updated_sources, changed_sources = normalize_source_text(original)
        updated, changed_provider = patch_hcl_provider_credentials(updated_sources)
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
) -> pathlib.Path:
    out_path = (root / out_file).resolve()
    tfvars = {
        "access_key": ak,
        "secret_key": sk,
        "region": region,
    }
    out_path.write_text(json.dumps(tfvars, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return out_path


def load_credential_env_values() -> tuple[str, str, str]:
    def pick(names: list[str]) -> str:
        for name in names:
            value = str(os.getenv(name, "")).strip()
            if value:
                return value
        return ""

    ak = pick(["HW_ACCESS_KEY", "HUAWEICLOUD_ACCESS_KEY", "HWC_ACCESS_KEY"])
    sk = pick(["HW_SECRET_KEY", "HUAWEICLOUD_SECRET_KEY", "HWC_SECRET_KEY"])
    region = pick(["HW_REGION_NAME", "HUAWEICLOUD_REGION", "HWC_REGION"])
    return ak, sk, region


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Normalize Terraform provider source for huaweicloud and kubernetes providers. "
            "Write credentials into terraform.auto.tfvars.json without printing secrets."
        )
    )
    parser.add_argument("directory", help="Directory containing Terraform files")
    parser.add_argument("--dry-run", action="store_true", help="Show changes without writing")
    parser.add_argument("--region", default="", help="HuaweiCloud region, e.g. cn-north-4")
    parser.add_argument(
        "--tfvars-file",
        default="terraform.auto.tfvars.json",
        help="tfvars filename written under directory",
    )
    args = parser.parse_args()

    root = pathlib.Path(args.directory).expanduser().resolve()
    if not root.exists() or not root.is_dir():
        print(f"Directory does not exist: {root}", file=sys.stderr)
        return 1

    tf_files = sorted(root.rglob("*.tf")) + sorted(root.rglob("*.tf.json"))
    if not tf_files:
        print(f"No Terraform files found in: {root}")
        return 2

    changed_files = []
    for tf_file in tf_files:
        if process_file(tf_file, args.dry_run):
            changed_files.append(tf_file)

    print(f"Scanned {len(tf_files)} .tf files in {root}")
    print(f"Changed {len(changed_files)} files")
    for path in changed_files:
        print(f" - {path}")

    env_ak, env_sk, env_region = load_credential_env_values()
    resolved_ak = env_ak
    resolved_sk = env_sk
    resolved_region = args.region.strip() or env_region

    has_ak = bool(resolved_ak)
    has_sk = bool(resolved_sk)
    has_credentials = has_ak and has_sk
    has_partial_credentials = has_ak ^ has_sk

    if has_partial_credentials:
        print(
            "Incomplete credentials detected (only AK or SK). "
            "Provide both values via environment variables or local tfvars.",
            file=sys.stderr,
        )
        return 3

    tfvars_path = (root / args.tfvars_file).resolve()

    if has_credentials:
        region_value = resolved_region or PLACEHOLDER_REGION
        if args.dry_run:
            print(f"Dry-run enabled: would write local tfvars at {tfvars_path}")
        else:
            out_path = write_credentials_tfvars(
                root,
                resolved_ak,
                resolved_sk,
                region_value,
                args.tfvars_file,
            )
            print(f"Wrote credentials tfvars: {out_path}")
            if region_value == PLACEHOLDER_REGION:
                print("Region is missing and left as placeholder. Edit tfvars before terraform apply.")
            print("Keep this file local and do not commit it to git.")
        return 0

    if tfvars_path.exists():
        print(f"No AK/SK detected. Reuse local tfvars file: {tfvars_path}")
        print("Verify access_key/secret_key/region in this file before terraform apply.")
        return 0

    region_value = resolved_region or PLACEHOLDER_REGION
    if args.dry_run:
        print(f"Dry-run enabled: would create placeholder tfvars at {tfvars_path}")
    else:
        placeholder_path = write_credentials_tfvars(
            root,
            PLACEHOLDER_AK,
            PLACEHOLDER_SK,
            region_value,
            args.tfvars_file,
        )
        print(f"Created placeholder tfvars: {placeholder_path}")
    print("No AK/SK detected in environment or arguments.")
    print("Edit this local file and fill access_key/secret_key before terraform apply.")
    print("Do not paste or echo credentials in chat.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
