# Verification Method（验证方法）

> 本文件给出**真实可跑**的验证命令，用于回归本 skill 的脚本契约（退出码 / stdout JSON / 权限判定 / 并发 / wrapper 桩测试 / PowerShell 5.1）。
> 所有用例都在**一次性临时目录**下运行：`HOME` 指向临时目录，**绝不触碰真实的 `~/.bashrc`**；PowerShell 用例通过 `CODEARTS_CLI_ENV_SCOPE=Process` 强制进程作用域，**绝不写真实的 User 级环境变量**。

统一前置（除 PowerShell 章节外都用 bash）：

```bash
cd skills/devtools/cli/huawei-cloud-codearts-code-gen
export CODEARTS_SETUP_MAX_RETRY=1      # 测试钩子：把重试压到 1 次，避免等 3×5s
export CODEARTS_SETUP_RETRY_DELAY=0    # 测试钩子：重试间隔 0s
```

---

## 1. 静态检查：语法、行尾、编码、文件名

```bash
# 1.1 全部 shell 脚本语法检查
for f in scripts/*.sh; do bash -n "$f" && echo "bash -n OK  $f" || echo "bash -n FAIL $f"; done

# 1.2 bash 3.2（macOS 自带）不兼容语法排查：应输出 OK
#     先过滤掉「仅在注释里提到这些关键字」的行（脚本注释里会说明它兼容 bash 3.2）
grep -nE 'mapfile|declare -A|\$\{[A-Za-z_]+,,|\$\{[A-Za-z_]+^^' scripts/*.sh | grep -vE ':[0-9]+:[[:space:]]*#' \
  && echo "FAIL: bash4-only syntax" || echo "OK: bash 3.2 compatible"

# 1.3 行尾必须是 LF、不得有 BOM、文件名必须是 kebab-case
python3 - <<'PY'
import pathlib, re, sys
root = pathlib.Path(".")
bad = []
files = sorted([p for p in root.rglob("*") if p.is_file()])
for p in files:
    b = p.read_bytes()
    if b.startswith(b"\xef\xbb\xbf"):
        bad.append(f"{p}: BOM")
    if b"\r\n" in b:
        bad.append(f"{p}: CRLF")
for p in files:
    if p.parent.name == "references" and not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*\.md", p.name):
        bad.append(f"{p}: not kebab-case .md")
allowed = {".md", ".sh", ".ps1"}
for p in files:
    if p.suffix not in allowed:
        bad.append(f"{p}: extension {p.suffix!r} outside allowlist subset")
print("files:", len(files))
print("BAD:", bad if bad else "none")
sys.exit(1 if bad else 0)
PY
```

预期：1.1 全部 `OK`；1.2 输出 `OK`；1.3 输出 `BAD: none` 且退出码 `0`。

---

## 2. `setup.sh` 状态与退出码矩阵（0 / 2 / 10 / 20 / 30 / 40 / 50）

一次性搭建临时 HOME 与**假 CLI**（假 CLI 只打印一行 JSONL 并退出 0，用于让 Step 4 连通性检查通过）：

```bash
T=$(mktemp -d)
mkdir -p "$T/.codeartsdoer/installers"
cat > "$T/.codeartsdoer/installers/codearts" <<'EOF'
#!/bin/sh
printf '%s\n' '{"type":"text","content":"ok"}'
exit 0
EOF
chmod +x "$T/.codeartsdoer/installers/codearts"

run() { # run <label> <command...>
  label="$1"; shift
  out=$("$@" 2>/dev/null); rc=$?
  printf '%-26s rc=%-3s stdout=%s\n' "$label" "$rc" "$out"
}
```

### 2.1 用例

```bash
# (a) --save-aksk 缺 SK -> 2 invalid_arguments
run "a save-aksk-only-ak(2)"  env HOME="$T" bash scripts/setup.sh --save-aksk ONLYAK

# (b) 空 AK/SK -> 2 empty_credentials
run "b save-aksk-empty(2)"    env HOME="$T" bash scripts/setup.sh --save-aksk "" ""

# (c) --ak 缺值 -> 2 invalid_arguments
run "c ak-without-value(2)"   env HOME="$T" bash scripts/setup.sh --ak

# (d) 取不到目录锁 -> 2 lock_timeout（人为放一个新鲜锁目录，并把陈旧阈值调大）
mkdir -p "$T/.bashrc.lock"
run "d lock-timeout(2)"       env HOME="$T" CODEARTS_SETUP_LOCK_RETRY=2 CODEARTS_SETUP_LOCK_SLEEP=0.1 \
                                  CODEARTS_SETUP_LOCK_STALE=3600 bash scripts/setup.sh --save-aksk AK SK
rmdir "$T/.bashrc.lock"

# (e) 无凭据 -> 10 need_input（假 CLI 已就位，避免走安装分支）
run "e need-input(10)"        env -u CODEARTS_CLI_AK -u CODEARTS_CLI_SK HOME="$T" bash scripts/setup.sh

# (f) 有凭据但没有权限配置 -> 20 need_consent
run "f need-consent(20)"      env HOME="$T" CODEARTS_CLI_AK=AK CODEARTS_CLI_SK=SK bash scripts/setup.sh

# (g) 有凭据 + 权限配制齐 -> 0 ready
mkdir -p "$T/.codeartsdoer/cli-data/storage/permission"
printf '[{"permission":"edit","pattern":"%s","action":"allow"},{"permission":"write","pattern":"%s","action":"allow"}]\n' "$T" "$T" \
  > "$T/.codeartsdoer/cli-data/storage/permission/global.json"
run "g ready(0)"              env HOME="$T" CODEARTS_CLI_AK=AK CODEARTS_CLI_SK=SK bash scripts/setup.sh

# (h) CLI 输出无认证字样的失败 -> 40 network_failed
cat > "$T/.codeartsdoer/installers/codearts" <<'EOF'
#!/bin/sh
printf '%s\n' 'boom' >&2
exit 1
EOF
run "h network-failed(40)"    env HOME="$T" CODEARTS_CLI_AK=AK CODEARTS_CLI_SK=SK bash scripts/setup.sh

# (i) CLI 明说 unauthorized -> 50 auth_failed
cat > "$T/.codeartsdoer/installers/codearts" <<'EOF'
#!/bin/sh
printf '%s\n' 'unauthorized: invalid AK/SK'
exit 0
EOF
run "i auth-failed(50)"       env HOME="$T" CODEARTS_CLI_AK=AK CODEARTS_CLI_SK=SK bash scripts/setup.sh

# (j) CLI 不存在且下载失败（离线：把 curl/wget 影子成失败桩）-> 30
#     注意 type 依平台：Linux/macOS = download_failed；Windows Git Bash 的 uname 是 MINGW*，
#     OS 被识别为 Windows，于是走 unsupported_os —— 两者都必须是 exit 30
mkdir -p "$T/bin"
printf '#!/bin/sh\nexit 127\n' > "$T/bin/curl"
cp "$T/bin/curl" "$T/bin/wget"
chmod +x "$T/bin/curl" "$T/bin/wget"
rm -f "$T/.codeartsdoer/installers/codearts"
run "j install-branch(30)"    env HOME="$T" PATH="$T/bin:$PATH" CODEARTS_CLI_AK=AK CODEARTS_CLI_SK=SK bash scripts/setup.sh

# (k) --clear-aksk -> 0 cleared（先写一份带凭据的 .bashrc）
printf 'export CODEARTS_CLI_AK=AK\nexport CODEARTS_CLI_SK=SK\n' > "$T/.bashrc"
run "k cleared(0)"            env HOME="$T" bash scripts/setup.sh --clear-aksk
grep -cE '^export CODEARTS_CLI_(AK|SK)=' "$T/.bashrc" || echo "OK: credentials removed"
```

### 2.2 结果判读

| 用例 | 期望 rc | 期望 stdout |
|------|--------|------------|
| a / b / c | `2` | 单个 JSON，`"type"` 为 `invalid_arguments` / `empty_credentials` |
| d | `2` | 单个 JSON，`"type":"lock_timeout"` |
| e | `10` | 单个 JSON，`"status":"need_input"` |
| f | `20` | 单个 JSON，`"status":"need_consent"` |
| g | `0` | `{"status":"ready","code":0,...}` |
| h | `40` | `{"status":"error","code":40,"type":"network_failed",...}` |
| i | `50` | `{"status":"error","code":50,"type":"auth_failed",...}` |
| j | `30` | `{"status":"error","code":30,...}`，`type` 为 `download_failed`（Linux/macOS）或 `unsupported_os`（Windows Git Bash） |
| k | `0` | `{"status":"cleared","code":0,...}`，且 `.bashrc` 不再含两行导出 |

### 2.3 stdout 契约（#113-5：stdout 只允许出现约定 JSON）

```bash
# 每个非 0 用例都必须能在 stdout 上解析出「恰好一个」JSON 对象，日志全部在 stderr
HOME="$T" bash scripts/setup.sh --save-aksk ONLYAK 2>"$T/err.txt" > "$T/out.json"; echo "rc=$?"
python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); print("stdout JSON OK:", d["status"], d["code"])' "$T/out.json"
echo "stdout lines = $(wc -l < "$T/out.json")   stderr lines = $(wc -l < "$T/err.txt")"
```

预期：`rc=2`；`stdout JSON OK: error 2`；`stdout lines = 1`（严格只有一个 JSON 对象），`stderr lines >= 1`（面向人的可读提示走 stderr，不污染 stdout 契约）。

---

## 3. 权限判定：#113-7 紧凑 JSON 与 pretty JSON 必须一致

```bash
P="$T/.codeartsdoer/cli-data/storage/permission/global.json"
mkdir -p "$(dirname "$P")"

# 3.1 紧凑写法
printf '[{"permission":"edit","pattern":"/workspace","action":"allow"},{"permission":"write","pattern":"/workspace","action":"allow"}]\n' > "$P"
run "compact"        env HOME="$T" CODEARTS_CLI_AK=AK CODEARTS_CLI_SK=SK bash scripts/setup.sh

# 3.2 语义等价的 pretty 写法（仅缩进/换行不同）—— 结果必须与 3.1 完全一致
python3 - "$P" <<'PY'
import json, sys
p = sys.argv[1]
raw = json.load(open(p))
open(p, "w").write(json.dumps(raw, indent=2) + "\n")
PY
run "pretty"         env HOME="$T" CODEARTS_CLI_AK=AK CODEARTS_CLI_SK=SK bash scripts/setup.sh

# 3.3 键顺序被打乱也必须一致
python3 - "$P" <<'PY'
import json, sys
p = sys.argv[1]
raw = json.load(open(p))
open(p, "w").write(json.dumps(raw, indent=2, sort_keys=True) + "\n")
PY
run "pretty-reordered" env HOME="$T" CODEARTS_CLI_AK=AK CODEARTS_CLI_SK=SK bash scripts/setup.sh

# 3.4 负例：只有 write 允许、缺 edit -> 必须回到 20
printf '[{"permission":"write","action":"allow"}]\n' > "$P"
run "only-write(20)" env HOME="$T" CODEARTS_CLI_AK=AK CODEARTS_CLI_SK=SK bash scripts/setup.sh

# 3.5 回退分支：影子掉 python3/python/jq，强制走 tr/awk 回退实现，结果必须与 3.1/3.2 一致
printf '[{"permission":"edit","pattern":"/workspace","action":"allow"},{"permission":"write","pattern":"/workspace","action":"allow"}]\n' > "$P"
mkdir -p "$T/shadows"
for n in python3 python jq; do printf '#!/bin/sh\nexit 127\n' > "$T/shadows/$n"; chmod +x "$T/shadows/$n"; done
run "pretty-fallback" env HOME="$T" PATH="$T/shadows:$PATH" CODEARTS_CLI_AK=AK CODEARTS_CLI_SK=SK bash scripts/setup.sh
```

预期：`compact` / `pretty` / `pretty-reordered` / `pretty-fallback` 全部 `rc=0`；`only-write(20)` 为 `rc=20`。
（HEAD 版本用 `grep -A1` 判定，`pretty` 会误判为「未配置」——这正是 #113-7 的复现点。）

---

## 4. 并发 `--save-aksk`：#113-10 不丢行、不撕裂

```bash
CT=$(mktemp -d)
: > "$CT/.bashrc"

# 前置：假 CLI 必须先就位。否则每个并发进程都会卡在「自动安装 CLI」这一步（甚至尝试联网下载），
#       根本走不到保存凭据的 load_aksk()，结果会是 0 行而不是 1 行。
mkdir -p "$CT/.codeartsdoer/installers"
cat > "$CT/.codeartsdoer/installers/codearts" <<'EOF'
#!/bin/sh
printf '%s\n' '{"type":"text","content":"ok"}'
exit 0
EOF
chmod +x "$CT/.codeartsdoer/installers/codearts"

for i in $(seq 1 20); do
  for tag in a b; do
    HOME="$CT" CODEARTS_SETUP_LOCK_RETRY=50 CODEARTS_SETUP_LOCK_SLEEP=0.1 \
      bash scripts/setup.sh --save-aksk "AK${i}${tag}" "SK${i}${tag}" >/dev/null 2>&1 &
  done
done
wait

echo "AK lines: $(grep -cE '^export CODEARTS_CLI_AK=' "$CT/.bashrc")"
echo "SK lines: $(grep -cE '^export CODEARTS_CLI_SK=' "$CT/.bashrc")"
echo "total lines: $(wc -l < "$CT/.bashrc")"
# 允许值被双引号包裹（脚本写入形式是 export CODEARTS_CLI_AK="..."），否则会把正常行误判为残片
grep -vE '^(export CODEARTS_CLI_(AK|SK)="?[A-Za-z0-9]+"?)?$' "$CT/.bashrc" && echo "FAIL: torn line" || echo "OK: no torn line"
cat "$CT/.bashrc"
```

预期：`AK lines: 1`、`SK lines: 1`、`total lines: 2`、`OK: no torn line`。
（两个字段必须配对来自同一次写入；HEAD 版本无锁，并发时会出现丢行或半个写。）

---

## 5. wrapper 桩测试：`scripts/codearts_run.sh`（#113-3/4/5/8/14）

可编程假 CLI（行为由 `STUB_MODE` 控制，argv 记录到 `STUB_ARGV_LOG`）：

```bash
W=$(mktemp -d)
cat > "$W/codearts" <<'EOF'
#!/bin/sh
[ -n "$STUB_ARGV_LOG" ] && printf '%s\n' "$@" >> "$STUB_ARGV_LOG"
case "$STUB_MODE" in
  jsonl)   printf '%s\n' '{"type":"step_start","sessionId":"s1"}' \
                       '{"type":"text","content":"```python\nprint(1)\n```"}' \
                       '{"type":"step_finish","status":"ok"}'; exit 0 ;;
  empty)   exit 0 ;;
  nonjson) printf '%s\n' 'Unexpected error, exit 0'; exit 0 ;;
  auth)    printf '%s\n' 'unauthorized: invalid AK/SK' >&2; exit 1 ;;
  net)     printf '%s\n' 'connection timed out' >&2; exit 1 ;;
  fail)    printf '%s\n' 'boom' >&2; exit 3 ;;
esac
EOF
chmod +x "$W/codearts"
```

### 5.1 用例

```bash
# (a) 无凭据 -> 10 need_input，且 CLI 根本没被调用（argv 日志为空/不存在）
STUB_ARGV_LOG="$W/argv-a" env -u CODEARTS_CLI_AK -u CODEARTS_CLI_SK HOME="$W" \
  CODEARTS_CLI_BIN="$W/codearts" bash scripts/codearts_run.sh models >"$W/o" 2>/dev/null
echo "a) rc=$? out=$(cat "$W/o")"
[ -s "$W/argv-a" ] && echo "FAIL: CLI was invoked" || echo "OK: CLI not invoked"

# (b) CLI 不存在 -> 30 cli_not_installed
env HOME="$W" CODEARTS_CLI_AK=AK CODEARTS_CLI_SK=SK CODEARTS_CLI_BIN="$W/absent/codearts" \
  bash scripts/codearts_run.sh models >"$W/o" 2>/dev/null
echo "b) rc=$? out=$(cat "$W/o")"

# (c) 正常 JSONL -> 0，stdout 原样透传
env HOME="$W" CODEARTS_CLI_AK=AK CODEARTS_CLI_SK=SK CODEARTS_CLI_BIN="$W/codearts" STUB_MODE=jsonl \
  bash scripts/codearts_run.sh run --format json -m "provider/model" "task" >"$W/o" 2>/dev/null
echo "c) rc=$? lines=$(wc -l <"$W/o")"

# (d) CLI 退出 0 但 stdout 为空 -> 60 output_contract_violation
env HOME="$W" CODEARTS_CLI_AK=AK CODEARTS_CLI_SK=SK CODEARTS_CLI_BIN="$W/codearts" STUB_MODE=empty \
  bash scripts/codearts_run.sh run --format json "task" >"$W/o" 2>/dev/null
echo "d) rc=$? out=$(cat "$W/o")"

# (e) 退出 0 但 stdout 不是合法 JSONL -> 60（#113-5 的真实形态）
env HOME="$W" CODEARTS_CLI_AK=AK CODEARTS_CLI_SK=SK CODEARTS_CLI_BIN="$W/codearts" STUB_MODE=nonjson \
  bash scripts/codearts_run.sh run --format json "task" >"$W/o" 2>/dev/null
echo "e) rc=$? out=$(cat "$W/o")"

# (f) 非零退出 + unauthorized -> 50 auth_failed（#113-8：消息不统一也要归类）
env HOME="$W" CODEARTS_CLI_AK=AK CODEARTS_CLI_SK=SK CODEARTS_CLI_BIN="$W/codearts" STUB_MODE=auth \
  bash scripts/codearts_run.sh models >"$W/o" 2>/dev/null
echo "f) rc=$? out=$(cat "$W/o")"

# (g) 非零退出 + timeout -> 40 network_failed
env HOME="$W" CODEARTS_CLI_AK=AK CODEARTS_CLI_SK=SK CODEARTS_CLI_BIN="$W/codearts" STUB_MODE=net \
  bash scripts/codearts_run.sh models >"$W/o" 2>/dev/null
echo "g) rc=$? out=$(cat "$W/o")"

# (h) 其它非零退出 -> 1 cli_failed
env HOME="$W" CODEARTS_CLI_AK=AK CODEARTS_CLI_SK=SK CODEARTS_CLI_BIN="$W/codearts" STUB_MODE=fail \
  bash scripts/codearts_run.sh models >"$W/o" 2>/dev/null
echo "h) rc=$? out=$(cat "$W/o")"
```

### 5.2 `-f` 附件（#113-14）

```bash
# (i) -f 被 wrapper 吃掉：附件内容以 fenced block 追加到任务描述，CLI 的 argv 里不得出现 -f 或文件名
printf 'def f():\n    return 1\n' > "$W/att.py"
STUB_ARGV_LOG="$W/argv-f" STUB_MODE=jsonl env HOME="$W" CODEARTS_CLI_AK=AK CODEARTS_CLI_SK=SK \
  CODEARTS_CLI_BIN="$W/codearts" bash scripts/codearts_run.sh run --format json \
  -m "provider/model" -f "$W/att.py" "add docstrings" >"$W/o" 2>/dev/null
echo "i) rc=$? lines=$(wc -l <"$W/o")"
grep -qx -- '-f' "$W/argv-f"       && echo "FAIL: -f leaked to CLI"        || echo "OK: -f consumed by wrapper"
grep -qx -- '--file' "$W/argv-f"   && echo "FAIL: --file leaked to CLI"    || echo "OK: --file consumed"
grep -qx -- "$W/att.py" "$W/argv-f" && echo "FAIL: file path is a standalone argv" || echo "OK: file path consumed"
grep -q -- '----- Attached file:' "$W/argv-f" && echo "OK: attachment block appended to the task argument"
echo "--- CLI argv as seen by the stub ---"; cat "$W/argv-f"
```
（末尾那条 `cat` 会显示最后一个位置参数已被拼成「任务描述 + 附件 fenced block」，而 `-f` 与文件路径都没有作为独立 argv 传下去。）

# (j) 不存在的文件 / 空文件 -> 60 attachment_failed
env HOME="$W" CODEARTS_CLI_AK=AK CODEARTS_CLI_SK=SK CODEARTS_CLI_BIN="$W/codearts" \
  bash scripts/codearts_run.sh run --format json -f "$W/nope.py" "task" >"$W/o" 2>/dev/null
echo "j1) rc=$? out=$(cat "$W/o")"
: > "$W/empty.py"
env HOME="$W" CODEARTS_CLI_AK=AK CODEARTS_CLI_SK=SK CODEARTS_CLI_BIN="$W/codearts" \
  bash scripts/codearts_run.sh run --format json -f "$W/empty.py" "task" >"$W/o" 2>/dev/null
echo "j2) rc=$? out=$(cat "$W/o")"
```

### 5.3 结果判读

| 用例 | 期望 rc | 期望 stdout |
|------|--------|------------|
| a | `10` | `{"status":"need_input","code":10,"type":"aksk_required","message":"..."}` |
| b | `30` | `{"status":"error","code":30,"type":"cli_not_installed",...}` |
| c | `0` | CLI 的 3 行 JSONL 原样透传 |
| d / e / j1 / j2 | `60` | `code:60`，`type` 分别是 `output_contract_violation` / `attachment_failed` |
| f | `50` | `{"status":"error","code":50,"type":"auth_failed",...}` |
| g | `40` | `{"status":"error","code":40,"type":"network_failed",...}` |
| h | `1` | `{"status":"error","code":1,"type":"cli_failed",...}` |
| i | `0` | 正常 JSONL；且 CLI argv 中无 `-f` / 附件路径 |

**核心不变量**：任何失败路径都**不得** `exit 0`；失败时 stdout **有且只有一个** JSON 对象，其余日志全部在 stderr 且带 `[codearts_run]` 前缀。

---

## 6. Windows PowerShell 5.1 验证

```powershell
Set-Location skills\devtools\cli\huawei-cloud-codearts-code-gen

# 6.1 语法解析（Windows PowerShell 5.1 与 PowerShell 7 都适用）
Get-ChildItem .\scripts\*.ps1 | ForEach-Object {
  $errs = $null
  [void][System.Management.Automation.Language.Parser]::ParseFile($_.FullName, [ref]$null, [ref]$errs)
  if ($errs.Count) { "PARSE-FAIL $($_.Name): $($errs[0].Message)" } else { "PARSE-OK   $($_.Name)" }
}

# 6.2 测试前先记录真实 User 作用域的值，测试后必须保持不变
$beforeAk = [Environment]::GetEnvironmentVariable("CODEARTS_CLI_AK", "User")
$beforeSk = [Environment]::GetEnvironmentVariable("CODEARTS_CLI_SK", "User")

# 6.3 -ClearAksk：强制 Process 作用域，绝不写真实 User 作用域
#     ⚠️ 下面这行 $env:CODEARTS_CLI_ENV_SCOPE = "Process" 是本用例成立的前提，不可省略
$env:CODEARTS_CLI_ENV_SCOPE = "Process"
$env:CODEARTS_BASHRC_PATH   = Join-Path $env:TEMP "cg-probe-bashrc"
$env:CODEARTS_CLI_AK        = "PROBE_AK"
$env:CODEARTS_CLI_SK        = "PROBE_SK"
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup.ps1 -ClearAksk
"clear-aksk rc=$LASTEXITCODE"

# ❌ 反面写法（禁止照抄）：没有先钉 Process 作用域就执行下面的命令，会清掉本机真实的
#    用户级 CODEARTS_CLI_AK/SK，且无法恢复：
#       powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup.ps1 -ClearAksk
#    同理，直接照抄本节任何一行到「干净」的新会话前，必须确认 CODEARTS_CLI_ENV_SCOPE=Process 已生效。

# 6.4 --save-aksk 参数校验：缺 SK / 空值必须是 exit 2 + 单个 JSON
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup.ps1 --save-aksk ONLYAK
"missing-sk rc=$LASTEXITCODE"
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup.ps1 --save-aksk "" ""
"empty-aksk rc=$LASTEXITCODE"

# 6.5 断言真实 User 作用域未被改动
$afterAk = [Environment]::GetEnvironmentVariable("CODEARTS_CLI_AK", "User")
$afterSk = [Environment]::GetEnvironmentVariable("CODEARTS_CLI_SK", "User")
if ($beforeAk -eq $afterAk -and $beforeSk -eq $afterSk) { "OK: real User scope untouched" } else { "FAIL: real User scope changed" }
```

预期：6.1 全部 `PARSE-OK`；6.3 `rc=0` 且 stdout 为 `{"status":"cleared","code":0,...}`；6.4 两次都是 `rc=2`；6.5 输出 `OK: real User scope untouched`。

> ⚠️ 禁止把 `-ClearAksk` 直接跑在默认的 `User` 作用域：那会清掉本机真实的 `CODEARTS_CLI_AK/SK`。测试必须通过 `CODEARTS_CLI_ENV_SCOPE=Process` 隔离。

---

## 7. 结果判读与常见假阳性

| 现象 | 判读 |
|------|------|
| 日志里出现 `[codearts_run]` 行 | 正常，日志只走 stderr |
| `permission.sh --agree` 的 stdout 是 `PERMISSION_CONFIGURED` + 路径而不是 JSON | 正常且有意保留：它不是 `--format json` 的契约对象，改为 JSON 属于无收益的接口破坏 |
| `setup.sh` 走了下载安装分支并耗时 | 测试必须先把假 CLI 放到 `$HOME/.codeartsdoer/installers/codearts`，或设 `CODEARTS_SETUP_MAX_RETRY=1` |
| 控制台中文乱码 | 与文件本身无关：核对文件内容请用编辑器/`read` 类工具，不要以控制台渲染为准；必要时设 `PYTHONIOENCODING=utf-8` |
| `bash -n` 报 `$'\n'` 之类语法错 | 说明用了 `sh`/旧 bash 解析：`.sh` 脚本必须用 bash 解析（`bash -n`），不要用 `sh -n` |

## 8. 一次性回归清单

1. 第 1 节静态检查全绿；
2. 第 2 节 11 个退出码用例全部符合 2.2 表；
3. 第 3 节紧凑 / pretty / 乱序 / 回退四条路径结果一致，负例回到 `20`；
4. 第 4 节并发后 AK / SK 各恰好 1 行、无残片；
5. 第 5 节 wrapper 的 11 个用例全部符合 5.3 表；
6. 第 6 节 PowerShell 解析与 `-ClearAksk` 通过，且真实 User 作用域未被改动。
