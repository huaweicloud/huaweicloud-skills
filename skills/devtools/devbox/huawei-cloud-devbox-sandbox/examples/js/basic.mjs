import { Sandbox } from "devbox-js-sdk";

const template = process.env.DEVBOX_TEST_TEMPLATE ?? "default";
const sandbox = await Sandbox.create(template, { timeout: 300 });

try {
  console.log(`sandbox created: ${sandbox.sandboxId}`);

  const result = await sandbox.commands.run("printf 'hello from DevBox'");
  console.log(`command output: ${result.stdout}`);

  await sandbox.files.write("/tmp/message.txt", "hello from the SDK");
  console.log(`file content: ${await sandbox.files.read("/tmp/message.txt")}`);
} finally {
  try {
    await sandbox.kill();
  } finally {
    await sandbox.close();
  }
}
