#!/usr/bin/env python3
"""Start the bag2manifest workbench on loopback by default."""

import os
import sys

from bag2manifest.webapp import main


def _allow_loopback() -> None:
    for key in ("NO_PROXY", "no_proxy"):
        entries = [s.strip() for s in os.environ.get(key, "").split(",") if s.strip()]
        for host in ("127.0.0.1", "localhost"):
            if host not in entries:
                entries.append(host)
        os.environ[key] = ",".join(entries)


if __name__ == "__main__":
    _allow_loopback()
    if not any(arg == "--host" or arg.startswith("--host=") for arg in sys.argv[1:]):
        sys.argv.extend(("--host", "127.0.0.1"))
    main()
