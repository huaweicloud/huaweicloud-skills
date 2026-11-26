import { DevBox, Sandbox } from "devbox-js-sdk";

const sandbox = await Sandbox.create("default", { timeout: 300 });
const sandboxId = sandbox.sandboxId;
console.log(`created: ${sandboxId} (state=${(await sandbox.getInfo()).state})`);

await sandbox.commands.run("echo before-pause > /tmp/state.txt");

await sandbox.setTimeout(600);
console.log(`setTimeout(600): endAt=${(await sandbox.getInfo()).endAt}`);

await sandbox.refresh(900);
console.log(`refresh(900): endAt=${(await sandbox.getInfo()).endAt}`);

await sandbox.pause();
console.log(`paused: state=${(await sandbox.getInfo()).state} (retained up to 24h)`);

await sandbox.close();
console.log("closed local connection (sandbox kept)");

const resumed = await Sandbox.connect(sandboxId, { timeout: 300 });
try {
  console.log(`resumed: ${resumed.sandboxId} (state=${(await resumed.getInfo()).state})`);
  console.log(`file survived: ${JSON.stringify((await resumed.files.read("/tmp/state.txt")).trim())}`);

  console.log("running sandboxes:");
  const client = new DevBox();
  try {
    const page = await client.sandboxes.list({ states: ["running"] });
    console.log(`  total=${page.total}`);
    for (const info of page.items) {
      console.log(`  ${info.sandboxId} ${info.state} ${JSON.stringify(info.metadata)}`);
    }
  } finally {
    await client.close();
  }
} finally {
  await resumed.kill();
  console.log(`killed: ${sandboxId}`);
}
