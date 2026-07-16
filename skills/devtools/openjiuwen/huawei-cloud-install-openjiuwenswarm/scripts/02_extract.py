#!/usr/bin/env python3
"""Phase 2: Extract archive. Run as: python3 scripts/02_extract.py"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *

if os.path.isfile(RUNTIME_PYTHON):
    print("[2/5] \u23ed\ufe0f Already done: mirror already extracted, skip extraction", flush=True)
    sys.exit(0)

ensure_base_dir()
print("[2/5] \U0001f4c2 Extracting mirror...", flush=True)

try:
    if MIRROR_FILE.endswith(".tar.gz") or MIRROR_FILE.endswith(".tgz"):
        subprocess.run(["tar", "xzf", MIRROR_FILE, "-C", BASE_DIR], check=True)
    elif MIRROR_FILE.endswith(".tar.bz2") or MIRROR_FILE.endswith(".tbz2"):
        subprocess.run(["tar", "xjf", MIRROR_FILE, "-C", BASE_DIR], check=True)
    elif MIRROR_FILE.endswith(".tar.xz") or MIRROR_FILE.endswith(".txz"):
        subprocess.run(["tar", "xJf", MIRROR_FILE, "-C", BASE_DIR], check=True)
    elif MIRROR_FILE.endswith(".zip"):
        import zipfile
        with zipfile.ZipFile(MIRROR_FILE, "r") as zf:
            zf.extractall(BASE_DIR)
    else:
        output_error("unknown_archive_format",
                     "Unrecognized archive format",
                     "Use .tar.gz, .tar.bz2, .tar.xz, or .zip")
except Exception as e:
    output_error("extraction_failed",
                 f"Failed to extract mirror: {str(e)}",
                 "Check archive integrity")

# Fix directory structure: tarball may have python/ directly under BASE_DIR
import shutil
direct_python = os.path.join(BASE_DIR, "python")
expected_python = os.path.join(EXTRACT_DIR, "python")
if os.path.isdir(direct_python) and not os.path.isdir(expected_python):
    os.makedirs(EXTRACT_DIR, exist_ok=True)
    shutil.move(direct_python, expected_python)

if not os.path.isfile(RUNTIME_PYTHON):
    output_error("extraction_failed",
                 f"Runtime Python not found: {RUNTIME_PYTHON}",
                 "Check mirror archive structure")

print("[2/5] \u2705 Mirror extraction completed", flush=True)