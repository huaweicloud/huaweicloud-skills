# DevBox JavaScript / TypeScript SDK Reference

Package `devbox-js-sdk`, version 0.1.x. Requires **Node.js >= 20.18.1**. ESM-only (`"type": "module"`), ships its own TypeScript types, bundles `undici`.

```bash
npm install devbox-js-sdk     # published on npm (0.1.0)
```

```js
import { Sandbox, DevBox, DevBoxError, RateLimitError } from "devbox-js-sdk";
```

## Public API (`import { ... } from "devbox-js-sdk"`)

| Export | Kind | Purpose |
|--------|------|---------|
| `Sandbox` | class | Main entry point for one sandbox |
| `Envd` | class | EnvD runtime metrics/envs/health |
| `DevBox` | class | Reusable client managing multiple sandboxes |
| `CommandHandle` | class | Running background process / PTY session |
| `CommandResult` | type | `{ exitCode, stdout, stderr, pid }` |
| `SandboxInfo` | type | `{ sandboxId, templateId, state, startedAt, endAt, cpuCount, memoryMb, diskSizeMb, metadata, lifecycle }` |
| `TemplateInfo` | type | `{ templateId, name, aliases, buildId, cpuCount, memoryMb, diskSizeMb }` |
| `SandboxLifecycle` | type | `{ onTimeout: "kill"\|"pause", autoResume: boolean }` |
| `SandboxState` | enum | `Running/Paused/Stopped` (transient states trimmed in 0.1.x dev) |
| `FileInfo` | type | `{ name, path, type, size, mode?, permissions?, owner?, group?, modifiedAt?, symlinkTarget? }` |
| `FileType` | enum | `File/Directory/Symlink` |
| `FileWatchEvent` | type | `{ name, type, path?, entry? }` |
| `ProcessInfo` | type | `{ pid, command, running, startedAt }` |
| `PtySize` | type | `{ rows, cols }` |
| `Page` | type | `{ items, nextToken?, total? }` |
| `GitCredentials` | type | `{ username, password }` |
| `RunOptions` / `WaitOptions` | types | see Commands |
| `CreateSandboxOptions` | type | `{ timeout?, envs?, metadata?, buildId?, lifecycle? }` |
| `DevBoxOptions` | type | `{ apiKey?, apiUrl?, gatewayUrl?, requestTimeoutMs?, headers?, dispatcher? }` |
| `DevBoxError` + subclasses | classes | see [Errors](#errors) |

## Configuration

| Setting | Env var | Default | Notes |
|---------|---------|---------|-------|
| API Key | `DEVBOX_API_KEY` or `E2B_API_KEY` | required | also `apiKey` option |
| Manager URL | `DEVBOX_API_URL` or `E2B_API_URL` | `https://devbox.developer.myhuaweicloud.com` | https only (http for localhost only) |
| Gateway URL override | `DEVBOX_GATEWAY_URL` | Manager-returned address | may contain `{tunnel_id}` / `{port}` |
| Request timeout | `requestTimeoutMs` | Manager 150000 ms, data plane 30000 ms | one value overrides both |

Constructor options take precedence over environment variables. All time values in **milliseconds** except sandbox lifetime `timeout`/`duration` (seconds).

## Sandbox

### Creation & Connection

```js
const sandbox = await Sandbox.create(
  "default",                       // template ID, name, or alias
  {
    timeout: 300,                  // seconds, 10..86400
    envs: { NODE_ENV: "test" },    // Record<string, string>
    metadata: { team: "infra" },
    buildId: "...",                // pin a template build
    lifecycle: { onTimeout: "pause", autoResume: true },
  },
);

const sandbox2 = await Sandbox.connect(sandboxId, { timeout: 300 });
// Fetches Gateway credentials (resumes a paused sandbox);
// does NOT itself open a data-plane connection. Deleted sandboxes cannot be reconnected.
```

No context manager — always clean up explicitly:

```js
try { /* work */ } finally {
  try { await sandbox.kill(); } finally { await sandbox.close(); }
}
```

### Lifecycle

| Method | Behavior |
|--------|----------|
| `sandboxId` | getter — sandbox ID |
| `info` | cached `SandboxInfo` |
| `getInfo()` | refresh state from Manager |
| `isRunning()` | Manager-reported state is Running; `NotFoundError` → false |
| `setTimeout(timeout)` | **reset** remaining lifetime (can shorten); 10–86400 s |
| `refresh(duration = 300)` | extend to **at least** `duration` remaining; never shortens |
| `pause()` | memory+disk snapshot; retained 24 h |
| `resume({ timeout: 300 })` | resume the same sandbox; returns `this` with a new connect token |
| `kill()` | delete sandbox; `false` if already deleted/expired (idempotent cleanup) |
| `close()` | release local connections only |

### Runtime facets

`sandbox.commands` → `Commands`; `sandbox.files` → `Filesystem`; `sandbox.pty` → `Pty`; `sandbox.git` → `Git`; `sandbox.envd` → `Envd`.

## Envd (runtime diagnostics)

```js
const metrics = await sandbox.envd.getMetrics(); // { timestamp, cpuCount, cpuUsedPct,
                                                 //   memTotal/memUsed/memCache,
                                                 //   diskTotal/diskUsed, oomKills?,
                                                 //   cpuPossible?/cpuTarget?/
                                                 //   cpuTargetAttempts?/cpuWritePendingMs? }
const envs = await sandbox.envd.getEnvs();       // Record<string, string>
const health = await sandbox.envd.health();      // { envdVersion } via X-Envd-Version
```

Direct probes of EnvD's own REST endpoints (`/metrics`, `/envs`, `/health`) — useful for monitoring and diagnostics. Wire keys are snake_case; returned objects are camelCase.

## Commands

```ts
// RunOptions (exported type) — background: true returns a CommandHandle;
// user is unsupported (ConfigurationError); stdin allocates stdin;
// timeoutMs defaults to 60000 and is also enforced server-side;
// onStdout/onStderr are foreground-only callbacks;
// check defaults to true (CommandExitError on non-zero exit).
interface RunOptions {
  background?: boolean;
  envs?: Record<string, string>;
  cwd?: string;
  user?: string;
  stdin?: boolean;
  timeoutMs?: number | null;
  onStdout?: (value: string) => void | Promise<void>;
  onStderr?: (value: string) => void | Promise<void>;
  check?: boolean;
}
```

```js
const result = await sandbox.commands.run("python --version");
console.log(result.exitCode, result.stdout, result.stderr);

await sandbox.commands.run("build.sh", {
  onStdout: (chunk) => process.stdout.write(chunk),
  timeoutMs: 300000,
});

const proc = await sandbox.commands.run("cat", { background: true, stdin: true });
await proc.sendStdin("hello\n");
await proc.closeStdin();
const result2 = await proc.wait();          // WaitOptions: onStdout/onStderr/check

const handle = await sandbox.commands.connect(proc.pid);   // re-attach by PID
const procs = await sandbox.commands.list();               // ProcessInfo[]
await sandbox.commands.sendStdin(pid, "data");
await sandbox.commands.closeStdin(pid);
await sandbox.commands.sendSignal(pid, "SIGTERM");         // or "SIGKILL"
```

`CommandHandle`: `.pid`, `wait()`, `sendStdin()`, `closeStdin()`, `sendSignal(signal)`, `kill()`, `disconnect()` (detach local stream only — remote process keeps running). Reconnect receives only new output — no replay. Commands execute as `/bin/bash -l -c <command>` under the sandbox's default user.

## Filesystem

| Method | Notes |
|--------|-------|
| `read(path, encoding?) -> Promise<string>` | default utf8 |
| `readBytes(path) -> Promise<Uint8Array>` | binary |
| `write(path, data, options?) -> Promise<FileInfo>` | string or Uint8Array |
| `writeBatch(files) -> Promise<FileInfo[]>` | sequential writes |
| `list(path, { depth? }) -> Promise<FileInfo[]>` | depth >= 1, default 1 |
| `stat(path) -> Promise<FileInfo>` | metadata |
| `exists(path) -> Promise<boolean>` | via stat |
| `makeDir(path)` | create directory |
| `move(source, destination)` | move/rename |
| `remove(path)` | delete file or directory |
| `upload(localPath, remotePath) -> Promise<FileInfo>` | local → sandbox |
| `download(remotePath, localPath) -> Promise<string>` | sandbox → local |
| `watch(path, { recursive?, includeEntry? }) -> AsyncIterable<FileWatchEvent>` | break/return ends the stream and closes the connection |

> **Watch timing**: start the watcher BEFORE the change happens — events produced before the subscription exists are not replayed. Official pattern: start a background command `sleep 1; printf done > /dir/done.txt`, then iterate the watcher; the 1 s buffer lets the subscription establish first.

```js
const writer = await sandbox.commands.run(
  "sleep 1; printf done > /tmp/workspace/done.txt",
  { background: true },
);
for await (const event of sandbox.files.watch("/tmp/workspace")) {
  console.log(event.name, event.type);
  if (event.name === "done.txt") break;
}
await writer.wait({ check: false });
```

All sandbox paths must be **absolute** (`/...`).

## PTY

```js
const session = await sandbox.pty.start("/bin/bash", {
  size: { rows: 30, cols: 100 },
  envs: { LANG: "en_US.UTF-8" },   // optional
  cwd: "/root",                    // optional
});

await session.sendStdin("pwd\n");
await sandbox.pty.resize(session.pid, { rows: 40, cols: 120 });
await session.sendStdin("exit\n");
const result = await session.wait({ check: false });
console.log(result.stdout);
```

- `TERM=xterm-256color` by default.
- `exit` ends the remote shell; `disconnect()` only detaches the output stream.

## Git

```js
sandbox.git.clone(url, path, { branch, depth, credentials, timeoutMs });
sandbox.git.status(repository);                                  // --short --branch
sandbox.git.checkout(repository, reference, { create });
sandbox.git.add(repository, paths /* string | string[] */);
sandbox.git.commit(repository, message);
sandbox.git.pull(repository, { remote, branch, credentials, timeoutMs });
sandbox.git.push(repository, { remote, branch, credentials, timeoutMs });
sandbox.git.setConfig(repository, key, value);
```

`GitCredentials = { username, password }` — injected as `DEVBOX_GIT_USERNAME` / `DEVBOX_GIT_PASSWORD` env vars with `GIT_TERMINAL_PROMPT=0`. Not persisted in the sandbox. Default `timeoutMs` for clone/pull/push: 300000.

## DevBox client (multi-sandbox)

```js
import { DevBox } from "devbox-js-sdk";

const client = new DevBox({ apiKey, apiUrl, requestTimeoutMs, headers, dispatcher });
try {
  const templates = await client.templates.list();
  const page = await client.sandboxes.list({
    states: [SandboxState.Running],
    limit: 50,                     // 0..1000 (0 = no limit)
    nextToken: undefined,          // from previous Page.nextToken
    metadata: undefined,           // optional server-side business-tag filter string
  });
  const sandbox = await client.sandboxes.create(templates[0].templateId, { timeout: 600 });
  console.log(sandbox.sandboxId, page.total);
  await sandbox.kill();
} finally {
  await client.close();           // closes control connection only
}
```

## Errors

`DevBoxError` exposes `code`, `statusCode`, `requestId`, `message`; subclasses: `AuthenticationError` (401), `PermissionDeniedError` (403), `ValidationError` (400/422), `NotFoundError` (404), `ConflictError` (409), `RateLimitError` (429, with `retryAfter`), `RequestTimeoutError` (408), `ServiceUnavailableError` (5xx), `ProtocolError`, `ConfigurationError`, `CommandExitError` (carries `.result`).

```js
import { DevBoxError, CommandExitError, RateLimitError, Sandbox } from "devbox-js-sdk";

try {
  await Sandbox.create("default").then((s) => s.commands.run("false"));
} catch (error) {
  if (error instanceof CommandExitError) console.log(error.result.exitCode);
  if (error instanceof RateLimitError) console.log(error.retryAfter);
  if (error instanceof DevBoxError)
    console.log(error.code, error.statusCode, error.requestId, error.message);
}
```

## Timeout & Retry Semantics (summary)

- Manager requests 150000 ms, data-plane HTTP 30000 ms defaults; `requestTimeoutMs` overrides both.
- `timeoutMs` (commands, default 60000) is enforced server-side too; per network phase, not a wall-clock cap.
- Sandbox lifetime `timeout`/`duration` are **seconds** (10–86400).
- Request timeouts never change sandbox lifetime.
- Transport retries: connection-establishment failures only, two short-interval retries. Rate limits, server errors, and possibly-delivered writes are never retried.

## Install & Verify

```bash
cd /path/to/your-project && npm install devbox-js-sdk   # published on npm
node -e "import('devbox-js-sdk').then((m) => console.log(m.VERSION))"
```

Source-build fallback (pin a `dev`-branch commit): `git clone -b dev https://github.com/huaweicloud/devspace-devbox.git`, then `cd devspace-devbox/js-sdk && npm ci && npm run build` and `npm install /path/to/devspace-devbox/js-sdk` — the published tarball already ships `dist/`. See [sdk-installation-guide.md](sdk-installation-guide.md).
