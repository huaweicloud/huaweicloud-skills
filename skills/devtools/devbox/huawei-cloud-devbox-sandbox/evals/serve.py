#!/usr/bin/env python3
"""DevBox mock service launcher.

Runs the mock Manager + Gateway as a standalone service (for client/server
and cross-architecture verification).

Environment:
    MOCK_BIND          bind address (default 127.0.0.1; use 0.0.0.0 for containers)
    MOCK_GATEWAY_HOST  host returned to clients as the Gateway domain
                       (default 127.0.0.1; use the service hostname/container name)

Usage:
    python3 evals/serve.py        # blocks; Ctrl+C to stop
"""
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import mock_devbox  # noqa: E402


def main() -> None:
    mgr = mock_devbox.ThreadingHTTPServer(
        (mock_devbox.BIND_HOST, mock_devbox.MGR_PORT), mock_devbox.ManagerHandler)
    gw = mock_devbox.ThreadingHTTPServer(
        (mock_devbox.BIND_HOST, mock_devbox.GW_PORT), mock_devbox.GatewayHandler)
    print(f"SERVICE UP manager={mock_devbox.BIND_HOST}:{mock_devbox.MGR_PORT} "
          f"gateway={mock_devbox.GW_HOST}:{mock_devbox.GW_PORT}", flush=True)
    threading.Thread(target=mgr.serve_forever, daemon=True).start()
    threading.Thread(target=gw.serve_forever, daemon=True).start()
    while True:
        time.sleep(60)


if __name__ == "__main__":
    main()
