#!/usr/bin/env python3
"""DevBox lifecycle example: timeout, refresh, pause/resume and reconnect by sandbox ID."""
from devbox import DevBox, Sandbox


def main() -> None:
    sandbox = Sandbox.create("default", timeout=300)
    sandbox_id = sandbox.sandbox_id
    print(f"created: {sandbox_id} (state={sandbox.get_info().state})")

    sandbox.commands.run("echo before-pause > /tmp/state.txt")

    sandbox.set_timeout(600)
    print(f"set_timeout(600): end_at={sandbox.get_info().end_at}")

    sandbox.refresh(900)
    print(f"refresh(900): end_at={sandbox.get_info().end_at}")

    sandbox.pause()
    print(f"paused: state={sandbox.get_info().state} (retained up to 24h)")

    sandbox.close()
    print("closed local connection (sandbox kept)")

    resumed = Sandbox.connect(sandbox_id, timeout=300)
    print(f"resumed: {resumed.sandbox_id} (state={resumed.get_info().state})")
    print(f"file survived: {resumed.files.read('/tmp/state.txt').strip()!r}")

    print("running sandboxes:")
    with DevBox() as client:
        page = client.sandboxes.list(states=["running"])
        print(f"  total={page.total}")
        for info in page.items:
            print(f"  {info.sandbox_id} {info.state} {dict(info.metadata)}")

    resumed.kill()
    print(f"killed: {sandbox_id}")


if __name__ == "__main__":
    main()
