import { Sandbox } from "devbox-js-sdk";

const sandbox = await Sandbox.create("default", { timeout: 300 });

try {
  console.log(`sandbox: ${sandbox.sandboxId}`);

  const metrics = await sandbox.envd.getMetrics();
  console.log(
    `metrics: cpu=${metrics.cpuUsedPct}% of ${metrics.cpuCount} ` +
      `mem=${metrics.memUsed}/${metrics.memTotal}MB ` +
      `disk=${metrics.diskUsed}/${metrics.diskTotal}MB`,
  );

  const envs = await sandbox.envd.getEnvs();
  console.log(`envs: PATH=${JSON.stringify(envs.PATH ?? "")}`);

  const health = await sandbox.envd.health();
  console.log(`envd version: ${JSON.stringify(health.envdVersion)}`);
} finally {
  try {
    await sandbox.kill();
  } finally {
    await sandbox.close();
  }
}
