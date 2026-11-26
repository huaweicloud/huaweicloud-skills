#!/usr/bin/env python3
"""DevBox async example: the Sandbox/commands/files flow with AsyncSandbox."""
import asyncio
import os

from devbox import AsyncSandbox


async def main() -> None:
    template = os.getenv("DEVBOX_TEST_TEMPLATE", "default")
    async with await AsyncSandbox.create(template, timeout=300) as sandbox:
        print(f"sandbox created: {sandbox.sandbox_id}")

        result = await sandbox.commands.run("printf 'hello from DevBox'")
        print(f"command output: {result.stdout}")

        path = "/tmp/hello.txt"
        await sandbox.files.write(path, "hello from the async SDK")
        print(f"file content: {await sandbox.files.read(path)}")


if __name__ == "__main__":
    asyncio.run(main())
