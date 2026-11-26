import { Sandbox } from "devbox-js-sdk";

const repoUrl = process.env.DEVBOX_DEMO_REPO ?? "https://github.com/octocat/Hello-World.git";
const repoPath = "/tmp/demo-repo";
const token = process.env.DEVBOX_DEMO_GIT_TOKEN ?? "";

const sandbox = await Sandbox.create("default", { timeout: 600 });

try {
  console.log(`sandbox: ${sandbox.sandboxId}`);

  const cloned = await sandbox.git.clone(repoUrl, repoPath, { depth: 1 });
  console.log(`clone: exit=${cloned.exitCode}`);

  await sandbox.git.setConfig(repoPath, "user.name", "devbox-demo");
  await sandbox.git.setConfig(repoPath, "user.email", "devbox-demo@example.com");

  await sandbox.commands.run(`echo devbox > ${repoPath}/devbox.txt`);
  await sandbox.git.add(repoPath, "devbox.txt");
  await sandbox.git.commit(repoPath, "add devbox marker");

  const status = await sandbox.git.status(repoPath);
  console.log(`status: exit=${status.exitCode} out=${JSON.stringify(status.stdout.trim())}`);

  if (token) {
    const pushed = await sandbox.git.push(repoPath, {
      credentials: { username: "devbox-demo", password: token },
    });
    console.log(`push: exit=${pushed.exitCode}`);
  } else {
    console.log("push skipped (set DEVBOX_DEMO_GIT_TOKEN to enable)");
  }
} finally {
  try {
    await sandbox.kill();
  } finally {
    await sandbox.close();
  }
}
