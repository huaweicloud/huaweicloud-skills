#!/usr/bin/env python3
"""DevBox Git example: clone a public repo, configure identity, commit locally, optional push."""
import os

from devbox import GitCredentials, Sandbox

REPO_URL = os.getenv("DEVBOX_DEMO_REPO", "https://github.com/octocat/Hello-World.git")
REPO_PATH = "/tmp/demo-repo"


def main() -> None:
    token = os.getenv("DEVBOX_DEMO_GIT_TOKEN", "")
    with Sandbox.create("default", timeout=600) as sandbox:
        print(f"sandbox: {sandbox.sandbox_id}")

        result = sandbox.git.clone(REPO_URL, REPO_PATH, depth=1, timeout=300)
        print(f"clone: exit={result.exit_code}")

        sandbox.git.set_config(REPO_PATH, "user.name", "devbox-demo")
        sandbox.git.set_config(REPO_PATH, "user.email", "devbox-demo@example.com")

        sandbox.commands.run(f"echo devbox > {REPO_PATH}/devbox.txt")
        sandbox.git.add(REPO_PATH, "devbox.txt")
        sandbox.git.commit(REPO_PATH, "add devbox marker")

        status = sandbox.git.status(REPO_PATH)
        print(f"status: exit={status.exit_code} out={status.stdout.strip()!r}")

        if token:
            credentials = GitCredentials(username="devbox-demo", password=token)
            push = sandbox.git.push(REPO_PATH, credentials=credentials, timeout=300)
            print(f"push: exit={push.exit_code}")
        else:
            print("push skipped (set DEVBOX_DEMO_GIT_TOKEN to enable)")


if __name__ == "__main__":
    main()
