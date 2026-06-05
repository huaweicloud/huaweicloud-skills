#!/usr/bin/env python
"""Normalize Terraform provider sources for HuaweiCloud SAC templates."""

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

# Ensure sibling modules are importable regardless of CWD.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from sensitive_mask import mask_dict

HUAWEICLOUD_PATTERNS = [
    re.compile(r'source\s*=\s*"[^"]*huaweicloud[^"]*"', re.IGNORECASE),
]

KUBERNETES_PATTERNS = [
    re.compile(r'source\s*=\s*"[^"]*kubernetes[^"]*"', re.IGNORECASE),
]


def normalize_source_text(content: str) -> tuple[str, bool]:
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


def ensure_hcl_variables(content: str) -> tuple[str, bool]:
    changed = False
    updated = content.rstrip() + "\n"
    required_vars = ["access_key", "secret_key", "region"]

    for name in required_vars:
        if re.search(rf'(?m)\bvariable\s+"{re.escape(name)}"\s*\{{', updated):
            continue
        block = f'\nvariable "{name}" {{\n  type = string\n}}\n'
        updated += block
        changed = True

    return updated, changed


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
        patched_body, body_changed = patch_huaweicloud_provider_block(body)
        chunks.append(patched_body)
        chunks.append("}")
        changed = changed or body_changed
        cursor = close_brace_idx + 1

    merged = "".join(chunks)
    merged, var_changed = ensure_hcl_variables(merged)
    return merged, changed or var_changed


def normalize_tf_json(content: str) -> tuple[str, bool]:
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

    if isinstance(data, dict):
        normalize_provider_blocks(data)
        ensure_json_variables(data)

    updated = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    return updated, changed


def process_file(tf_file: Path, dry_run: bool) -> bool:
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
    root: Path,
    ak: str,
    sk: str,
    region: str,
    out_file: str,
) -> Path:
    out_path = (root / out_file).resolve()
    tfvars = {
        "access_key": ak,
        "secret_key": sk,
        "region": region,
    }
    out_path.write_text(json.dumps(tfvars, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
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
    parser.add_argument("--region", default="", help="HuaweiCloud region, e.g. cn-north-4")
    args = parser.parse_args()

    root = Path(args.directory).expanduser().resolve()
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

    # Resolve credentials: ak/sk from env vars, region from CLI arg
    ak = os.environ.get("HW_ACCESS_KEY", "")
    sk = os.environ.get("HW_SECRET_KEY", "")
    region = args.region
    tfvars_path = (root / "terraform.auto.tfvars.json").resolve()

    if ak and sk:
        print("Loaded AK/SK from environment variables.")
    else:
        print(
            f"AK/SK not found in environment variables. "
            f"Please manually edit {tfvars_path} to add access_key and secret_key.",
            file=sys.stderr,
        )

    if args.dry_run:
        print("Dry-run enabled: skip writing credentials tfvars file.")
    else:
        out_path = write_credentials_tfvars(root, ak, sk, region, "terraform.auto.tfvars.json")
        # Mask sensitive values in summary output.
        masked = mask_dict({"access_key": ak, "secret_key": sk, "region": region})
        print(f"Wrote credentials tfvars: {out_path}")
        print(f"  Contents: {json.dumps(masked, ensure_ascii=False)}")
        print("Keep this file local and do not commit it to git.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
