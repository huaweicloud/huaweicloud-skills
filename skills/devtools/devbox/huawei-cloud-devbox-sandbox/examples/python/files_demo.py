#!/usr/bin/env python3
"""DevBox files example: write/read, directories, metadata, transfer and directory watch."""
import tempfile
from contextlib import closing
from pathlib import Path

from devbox import Sandbox


def main() -> None:
    with Sandbox.create("default", timeout=300) as sandbox:
        print(f"sandbox: {sandbox.sandbox_id}")

        sandbox.files.make_dir("/tmp/demo")
        sandbox.files.write("/tmp/demo/message.txt", "hello")
        assert sandbox.files.read("/tmp/demo/message.txt") == "hello"
        assert sandbox.files.read_bytes("/tmp/demo/message.txt") == b"hello"
        print("write/read round-trip ok")

        info = sandbox.files.stat("/tmp/demo/message.txt")
        print(f"stat: name={info.name} type={info.type} size={info.size}")

        sandbox.files.make_dir("/tmp/demo/nested")
        sandbox.files.move("/tmp/demo/message.txt", "/tmp/demo/nested/message.txt")
        entries = sandbox.files.list("/tmp/demo", depth=2)
        for entry in entries:
            print(f"entry: {entry.path} ({entry.type})")

        with tempfile.TemporaryDirectory() as tmp:
            local_in = Path(tmp) / "upload.bin"
            local_in.write_bytes(b"\x00\x01\x02devbox")
            sandbox.files.upload(str(local_in), "/tmp/demo/upload.bin")
            local_out = Path(tmp) / "download.bin"
            sandbox.files.download("/tmp/demo/upload.bin", str(local_out))
            assert local_out.read_bytes() == local_in.read_bytes()
            print("upload/download round-trip ok")

        # Directory watch: start the watcher BEFORE the change happens.
        # The background command sleeps 1s first so the watch subscription is
        # established by the time the file is created (official pattern).
        writer = sandbox.commands.run(
            "sleep 1; printf done > /tmp/demo/nested/done.txt", background=True
        )
        with closing(sandbox.files.watch("/tmp/demo/nested", include_entry=False)) as events:
            for event in events:
                print(f"watch: {event.type} {event.name}")
                if event.name == "done.txt":
                    break
        writer.wait(check=False)

        sandbox.files.remove("/tmp/demo")
        assert not sandbox.files.exists("/tmp/demo")
        print("cleanup ok")


if __name__ == "__main__":
    main()
