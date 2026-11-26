#!/usr/bin/env python3
"""DevBox commands example: streaming, background processes, stdin, signals and reconnection."""
from devbox import Sandbox


def main() -> None:
    with Sandbox.create("default", timeout=300) as sandbox:
        print(f"sandbox: {sandbox.sandbox_id}")

        result = sandbox.commands.run("python3 --version")
        print(f"foreground: exit={result.exit_code} stdout={result.stdout.strip()!r}")

        print("streaming:")
        sandbox.commands.run(
            "for i in 1 2 3; do echo line-$i; done",
            on_stdout=lambda chunk: print(f"  [stdout] {chunk.strip()}"),
        )

        process = sandbox.commands.run("cat", background=True, stdin=True)
        process.send_stdin("hello-stdin\n")
        process.close_stdin()
        waited = process.wait()
        print(f"background+stdin: {waited.stdout.strip()!r}")

        # Signal a running process, then read its termination status on the same handle.
        sleeper = sandbox.commands.run("sleep 60", background=True)
        print(f"started pid {sleeper.pid}")
        sleeper.send_signal("SIGTERM")
        terminated = sleeper.wait(check=False)
        print(f"terminated: exit={terminated.exit_code} (non-zero = killed by signal)")

        # Reconnect to a STILL-RUNNING process: disconnect keeps the remote process alive,
        # connect(pid) re-attaches (no replay of output produced while disconnected).
        reader = sandbox.commands.run(
            "read line; printf reconnected:$line", background=True, stdin=True
        )
        reader.disconnect()
        handle = sandbox.commands.connect(reader.pid, timeout=30)
        handle.send_stdin("proof\n")
        reconnected = handle.wait()
        print(f"reconnected: {reconnected.stdout.strip()!r}")

        for info in sandbox.commands.list():
            print(f"process: pid={info.pid} running={info.running} cmd={info.command}")


if __name__ == "__main__":
    main()
