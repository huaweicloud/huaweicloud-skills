#!/usr/bin/env python3
"""Step 0.5: non-blocking KooCLI (hcloud) availability & version check.

Three outcomes (never blocks the flow; ALWAYS exits 0):
  1. hcloud not installed  -> prints an install reminder
  2. hcloud too old        -> prints an upgrade reminder
  3. hcloud installed & OK -> silent pass (no output)

Run via: python scripts/check-koocli.py
"""

import re
import shutil
import subprocess
import sys

# KooCLI versions below this are considered too old (3.x is the modern line;
# current releases are 7.x). Raise this when the ecosystem moves on.
MIN_SUPPORTED = (3, 0, 0)

VERSION_RE = re.compile(r"(\d+)\.(\d+)\.(\d+)")

INSTALL_HINT = (
    "hcloud (KooCLI) not found in PATH. Some skills you install may depend on "
    "KooCLI. Install it first: https://support.huaweicloud.com/qs-hcli/hcli_02_003.html"
)
UPGRADE_HINT = (
    "hcloud (KooCLI) version {cur} is older than the supported minimum {min}. "
    "Upgrade to the latest version: hcloud update -y"
)


def parse_version(text):
    m = VERSION_RE.search(text or "")
    if not m:
        return None
    return tuple(int(x) for x in m.groups())


def check_koocli():
    if shutil.which("hcloud") is None:
        print("[Step 0.5] " + INSTALL_HINT)
        return 0

    try:
        proc = subprocess.run(
            ["hcloud", "version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        text = (proc.stdout or "") + (proc.stderr or "")
    except (OSError, subprocess.TimeoutExpired) as e:
        print("[Step 0.5] hcloud found but its version could not be checked: {0}".format(e))
        print("[Step 0.5] If unsure, run 'hcloud version' / 'hcloud update -y' manually.")
        return 0

    ver = parse_version(text)
    if ver is None:
        print("[Step 0.5] hcloud found; version output: {0!r}".format(text.strip()[:80]))
        print("[Step 0.5] If the version is too old, upgrade: hcloud update -y")
        return 0

    if ver < MIN_SUPPORTED:
        cur = ".".join(str(x) for x in ver)
        minimum = ".".join(str(x) for x in MIN_SUPPORTED)
        print("[Step 0.5] " + UPGRADE_HINT.format(cur=cur, min=minimum))
        return 0

    # hcloud installed and version OK -> silent pass
    return 0


if __name__ == "__main__":
    sys.exit(check_koocli())