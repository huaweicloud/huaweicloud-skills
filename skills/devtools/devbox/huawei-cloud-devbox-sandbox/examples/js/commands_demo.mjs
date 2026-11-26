import { Sandbox } from "devbox-js-sdk";

const sandbox = await Sandbox.create("default", { timeout: 300 });

try {
  console.log(`sandbox: ${sandbox.sandboxId}`);

  const version = await sandbox.commands.run("python3 --version");
  console.log(`foreground: exit=${version.exitCode} stdout=${version.stdout.trim()}`);

  console.log("streaming:");
  await sandbox.commands.run("for i in 1 2 3; do echo line-$i; done", {
    onStdout: (chunk) => console.log(`  [stdout] ${chunk.trim()}`),
  });

  const process = await sandbox.commands.run("cat", { background: true, stdin: true });
  await process.sendStdin("hello-stdin\n");
  await process.closeStdin();
  const waited = await process.wait();
  console.log(`background+stdin: ${waited.stdout.trim()}`);

  // Signal a running process, then read its termination status on the same handle.
  const sleeper = await sandbox.commands.run("sleep 60", { background: true });
  console.log(`started pid ${sleeper.pid}`);
  await sleeper.sendSignal("SIGTERM");
  const terminated = await sleeper.wait({ check: false });
  console.log(`terminated: exit=${terminated.exitCode} (non-zero = killed by signal)`);

  // Reconnect to a STILL-RUNNING process: disconnect keeps the remote process alive,
  // connect(pid) re-attaches (no replay of output produced while disconnected).
  const reader = await sandbox.commands.run("read line; printf reconnected:$line", {
    background: true,
    stdin: true,
  });
  await reader.disconnect();
  const handle = await sandbox.commands.connect(reader.pid, { timeoutMs: 30000 });
  await handle.sendStdin("proof\n");
  const reconnected = await handle.wait();
  console.log(`reconnected: ${reconnected.stdout.trim()}`);

  for (const info of await sandbox.commands.list()) {
    console.log(`process: pid=${info.pid} running=${info.running} cmd=${info.command}`);
  }
} finally {
  try {
    await sandbox.kill();
  } finally {
    await sandbox.close();
  }
}
