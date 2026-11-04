#!/usr/bin/env python3
"""CloudRobo custom-operator entrypoint (generated from templates/entrypoint.py).

This file is GENERATED into the work copy by the custom-operator skill; the user
does NOT write it. It reads the platform-injected ``SOURCE_DATASET_PATH`` env var,
resolves input/output directories, dynamically imports the user's ``process()``
function from ``src/`` (relative to this file), iterates every collected input item,
and writes the results to the output directory.

Generation rules (authoritative): references/custom-operator/custom-operator-workflow.md
Step 1.2. The placeholders below are patched in the work copy from
``operator_config.yaml`` (``entry.module`` / ``entry.function``).
"""
from __future__ import annotations

import importlib.util
import json
import os
import shutil
import sys
import tempfile
import traceback
from pathlib import Path

# --- patched from operator_config.yaml (entry.module / entry.function) -------------
MODULE = "user_operator"
FUNCTION = "process"
# ---------------------------------------------------------------------------------


def _redirect_tmpdir(output_dir: Path) -> Path | None:
    """Keep TMPDIR usable, preferring the system /tmp.

    The platform may mount /tmp read-only, in which case ray/opencv/... fail with
    "No usable temporary directory found in ['/tmp', ...]". Probe the system /tmp
    first and use it as-is when writable so OUTPUT_DIR stays clean; only when it is
    unusable fall back to a writable ``output_dir/.cloudrobo-tmp``. The fallback
    path is returned so the caller can remove it at exit (never leaving an empty
    junk folder in the output dataset). Never use SOURCE_DATASET_PATH (mounted
    read-only).
    """
    try:
        probe_fd, probe_path = tempfile.mkstemp(prefix=".cloudrobo-probe-")
        os.close(probe_fd)
        os.remove(probe_path)
        return None
    except OSError:  # noqa: BLE001
        tmp = output_dir / ".cloudrobo-tmp"
        try:
            tmp.mkdir(parents=True, exist_ok=True)
            os.environ["TMPDIR"] = str(tmp)
            tempfile.tempdir = str(tmp)
            return tmp
        except OSError:  # noqa: BLE001
            return None


def _output_dir() -> Path:
    # The platform mounts SOURCE_DATASET_PATH read-only; writing output/ inside it
    # fails with OSError: [Errno 30] Read-only file system.
    target = os.environ.get("TARGET_DATASET_PATH")
    out = Path(target) if target else Path("/output")
    out.mkdir(parents=True, exist_ok=True)
    return out


def _dataset_roots() -> list[Path]:
    """Input dataset roots from SOURCE_DATASET_PATH.

    SOURCE_DATASET_PATH is a JSON map which may hold MULTIPLE datasets (one task can
    process up to 10). Each value is a dataset path whose content lives under
    ``<path>/input/`` when present (dataset asset OBS roots also contain a
    ``<version_id>/`` subdirectory), otherwise at the root itself. Aggregate ALL
    datasets - do not take only the first.
    """
    raw = os.environ.get("SOURCE_DATASET_PATH", "")
    if not raw:
        return []
    try:
        mapping = json.loads(raw)
    except (ValueError, TypeError):
        raise SystemExit("SOURCE_DATASET_PATH is not a valid JSON map: %r" % (raw,))
    if not isinstance(mapping, dict):
        raise SystemExit("SOURCE_DATASET_PATH is not a JSON object: %r" % (raw,))
    roots: list[Path] = []
    for value in mapping.values():
        if not value:
            continue
        root = Path(str(value))
        candidate = root / "input"
        roots.append(candidate if candidate.is_dir() else root)
    return roots


def _collect_items(roots: list[Path]):
    """Yield ``(dataset_index, item_path)`` across ALL roots (recursive, files only).

    ``rglob("*")`` avoids ``IsADirectoryError`` on nested version-id directories.
    """
    for index, root in enumerate(roots):
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*")):
            if path.is_file():
                yield index, path


def _load_process():
    # src/ is resolved relative to __file__: Mode A bakes it at /app/src, Mode B
    # mounts it at {job_local_path}/src. Do NOT hardcode /app/src.
    src_dir = Path(__file__).resolve().parent / "src"
    module_path = src_dir / ("%s.py" % MODULE)
    if not module_path.is_file():
        raise SystemExit("Module %s not found in src/" % MODULE)
    sys.path.insert(0, str(src_dir.parent))
    spec = importlib.util.spec_from_file_location(MODULE, module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    func = getattr(module, FUNCTION, None)
    if func is None:
        raise SystemExit("Function %s not found in module" % FUNCTION)
    return func


def _write_output(out_dir: Path, stem: str, result) -> None:
    if isinstance(result, (bytes, bytearray)):
        (out_dir / ("%s.bin" % stem)).write_bytes(bytes(result))
    elif isinstance(result, str):
        (out_dir / ("%s.txt" % stem)).write_text(result, encoding="utf-8")
    elif result is not None:
        (out_dir / ("%s.txt" % stem)).write_text(str(result), encoding="utf-8")


def main() -> int:
    out_dir = _output_dir()
    tmp_fallback = _redirect_tmpdir(out_dir)
    process = _load_process()
    roots = _dataset_roots()
    multi = len(roots) > 1
    done = failed = 0
    for index, item in _collect_items(roots):
        # Single dataset keeps the original stem name; multiple datasets get a
        # {dataset_index}_ prefix to avoid output collisions.
        stem = "%s_%s" % (index, item.stem) if multi else item.stem
        try:
            _write_output(out_dir, stem, process(str(item)))
            done += 1
        except Exception:  # noqa: BLE001
            traceback.print_exc()
            failed += 1
    print("[DONE] Processed %d items, success %d, failed %d" % (done + failed, done, failed))
    if tmp_fallback is not None:
        shutil.rmtree(tmp_fallback, ignore_errors=True)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
