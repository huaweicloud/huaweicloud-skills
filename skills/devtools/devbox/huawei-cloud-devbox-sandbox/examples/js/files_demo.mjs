import { mkdtemp, readFile, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { Sandbox } from "devbox-js-sdk";

const sandbox = await Sandbox.create("default", { timeout: 300 });

try {
  console.log(`sandbox: ${sandbox.sandboxId}`);

  await sandbox.files.makeDir("/tmp/demo");
  await sandbox.files.write("/tmp/demo/message.txt", "hello");
  if ((await sandbox.files.read("/tmp/demo/message.txt")) !== "hello") throw new Error("mismatch");
  console.log("write/read round-trip ok");

  const info = await sandbox.files.stat("/tmp/demo/message.txt");
  console.log(`stat: name=${info.name} type=${info.type} size=${info.size}`);

  await sandbox.files.makeDir("/tmp/demo/nested");
  await sandbox.files.move("/tmp/demo/message.txt", "/tmp/demo/nested/message.txt");
  for (const entry of await sandbox.files.list("/tmp/demo", { depth: 2 })) {
    console.log(`entry: ${entry.path} (${entry.type})`);
  }

  const tmp = await mkdtemp(join(tmpdir(), "devbox-"));
  const localIn = join(tmp, "upload.bin");
  await writeFile(localIn, Buffer.from([0x00, 0x01, 0x02, 0x64, 0x65, 0x76, 0x62, 0x6f, 0x78]));
  await sandbox.files.upload(localIn, "/tmp/demo/upload.bin");
  const localOut = join(tmp, "download.bin");
  await sandbox.files.download("/tmp/demo/upload.bin", localOut);
  if (Buffer.compare(await readFile(localOut), await readFile(localIn)) !== 0) {
    throw new Error("upload/download mismatch");
  }
  console.log("upload/download round-trip ok");

  // Directory watch: start the watcher BEFORE the change happens.
  // The background command sleeps 1s first so the watch subscription is
  // established by the time the file is created (official pattern).
  const writer = await sandbox.commands.run(
    "sleep 1; printf done > /tmp/demo/nested/done.txt",
    { background: true },
  );
  for await (const event of sandbox.files.watch("/tmp/demo/nested", { includeEntry: false })) {
    console.log(`watch: ${event.type} ${event.name}`);
    if (event.name === "done.txt") break;
  }
  await writer.wait({ check: false });

  await sandbox.files.remove("/tmp/demo");
  if (await sandbox.files.exists("/tmp/demo")) throw new Error("remove failed");
  console.log("cleanup ok");
} finally {
  try {
    await sandbox.kill();
  } finally {
    await sandbox.close();
  }
}
