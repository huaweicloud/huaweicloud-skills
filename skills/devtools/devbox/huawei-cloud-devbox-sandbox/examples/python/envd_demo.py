#!/usr/bin/env python3
"""DevBox envd example: realtime metrics, sandbox env vars and health probe.

`sandbox.envd` is the runtime facet for EnvD's own REST endpoints
(/metrics, /envs, /health) — useful for monitoring and diagnostics.
"""
from devbox import Sandbox


def main() -> None:
    with Sandbox.create("default", timeout=300) as sandbox:
        print(f"sandbox: {sandbox.sandbox_id}")

        metrics = sandbox.envd.get_metrics()
        print(f"metrics: cpu={metrics.cpu_used_pct}% of {metrics.cpu_count} "
              f"mem={metrics.mem_used}/{metrics.mem_total}MB "
              f"disk={metrics.disk_used}/{metrics.disk_total}MB")

        envs = sandbox.envd.get_envs()
        print(f"envs: PATH={envs.get('PATH', '')!r}")

        health = sandbox.envd.health()
        print(f"envd version: {health.envd_version!r}")


if __name__ == "__main__":
    main()
