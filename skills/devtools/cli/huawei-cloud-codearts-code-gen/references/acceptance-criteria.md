# Acceptance Criteria（验收清单）

> 范围：本 PR 一次性解决 issue **#100**（frontmatter 缺失与跨平台兼容性）与 issue **#113**（aishell 评测 12 项：8 个 P1 + 4 个 P2）共 16 条问题，并修掉 `skills_bot` 对 PR 的审查意见（含 Critical #6）。
> 每条给出四件事：**原问题 → 复现方式（HEAD） → 修复后预期 → 判定命令**。
> 判定命令中 `$SKILL` 指本 skill 目录；`$HEAD` 指被审查版本 `37ee3c1`。不含任何需要写 git 的操作。

```bash
SKILL=skills/devtools/cli/huawei-cloud-codearts-code-gen
HEAD=37ee3c1
```

---

## A. issue #100 —— frontmatter 缺失及跨平台兼容性

### A-1 `#100-1` 清理命令使用就地编辑，macOS(BSD) 上不兼容

- **原问题**：`scripts/setup.sh` 的 `save_aksk()` 与 SKILL.md 的 4 处清理命令使用 `sed` 的原地编辑选项；BSD sed 要求额外给出备份后缀参数，所以同一行在 macOS 上必然失败。
- **复现方式（HEAD）**：
  ```bash
  git -C <worktree> show $HEAD:$SKILL/scripts/setup.sh | grep -cE 'sed[[:space:]]+-i'
  git -C <worktree> show $HEAD:$SKILL/SKILL.md        | grep -cE 'sed[[:space:]]+-i'
  ```
  两条计数都 > 0；在 macOS 上执行该清理命令会报 `sed: 1: "...": invalid command code`。
- **修复后预期**：
  1. 全目录（含 references）再也搜不到 `sed` 的原地编辑写法；
  2. `~/.bashrc` 改用「过滤到临时文件 + 原子 `mv` 替换」实现，新建文件 `chmod 600`，已存在则保留原权限位；
  3. 文档中所有清理命令统一为 `bash scripts/setup.sh --clear-aksk`（Windows：`setup.ps1 -ClearAksk`）。
- **判定命令**：
  ```bash
  # 注意：下面的模式写成正则，避免本文件自身包含被禁写法而产生假命中
  grep -rnE --include='*.sh' --include='*.ps1' --include='*.md' 'sed[[:space:]]+(-i|--in-place)' "$SKILL" \
    && echo "FAIL" || echo "PASS: no in-place edit literal in this skill"
  # 功能等价性：清理后 .bashrc 不再含凭据行，且不影响其它内容
  T=$(mktemp -d); printf 'KEEP=1\nexport CODEARTS_CLI_AK=AK\nexport CODEARTS_CLI_SK=SK\n' > "$T/.bashrc"
  HOME="$T" bash "$SKILL/scripts/setup.sh" --clear-aksk; echo "rc=$?"
  grep -c 'KEEP=1' "$T/.bashrc"                       # 期望 1
  grep -cE '^export CODEARTS_CLI_(AK|SK)=' "$T/.bashrc" # 期望 0
  ```

### A-2 `#100-2` frontmatter 元数据缺失（描述/触发词/标签/能力全空）

- **原问题**：tester Phase 1 特征提取异常——frontmatter 只有 `name` + `description`，无 `triggers` / `tags`；正文无能力清单，14 条命令被当作表格内容误提取。
- **复现方式（HEAD）**：
  ```bash
  git -C <worktree> show $HEAD:$SKILL/SKILL.md | head -12
  git -C <worktree> show $HEAD:$SKILL/SKILL.md | grep -c '^## Capabilities'
  ```
  第一条输出中无 `triggers:` / `tags:`；第二条为 `0`。
- **修复后预期**：
  - frontmatter 为合法 YAML，含 `name`、`description`（功能摘要 + 触发条件，含字面量 `Triggers include:`）、`triggers`、`tags`（≤5）；**无 `version` 字段**；`name` 与目录名一致；
  - 存在 `## Capabilities` 且内容为**列表**（非纯表格）。
- **判定命令**：
  ```bash
  python3 - <<PY
  import yaml, sys, pathlib, re
  p = pathlib.Path("$SKILL/SKILL.md"); t = p.read_text(encoding="utf-8")
  fm = yaml.safe_load(t.split("---", 2)[1])
  ok = (fm.get("name") == p.parent.name and fm.get("description")
        and len(fm.get("tags") or []) <= 5 and "version" not in fm
        and "Triggers include:" in fm["description"])
  body = t.split("---", 2)[2]
  cap = re.search(r"^## Capabilities\s*$", body, re.M) is not None
  print("frontmatter OK:", bool(ok), "| Capabilities:", cap)
  sys.exit(0 if ok and cap else 1)
  PY
  ```

### A-3 `#100-3` 跨平台兼容性

- **原问题**：`set -e` 与命令替换组合会提前退出；安装器日志灌入 stdout 破坏 JSON 契约；`grep` 的 BRE 分支写法在 BSD grep 上不生效；两个 `.ps1` 带 UTF-8 BOM。
- **复现方式（HEAD）**：
  ```bash
  git -C <worktree> show $HEAD:$SKILL/scripts/setup.ps1 | head -c 3 | xxd   # efbbbf = BOM
  git -C <worktree> show $HEAD:$SKILL/scripts/permission.ps1 | head -c 3 | xxd
  ```
- **修复后预期**：6 个脚本全部 **LF + UTF-8 无 BOM**；`bash -n` 全通过；`set -e` 下的命令替换写成 `if ! VAR=$(...)` 形式；安装器输出重定向到 stderr；`grep -E` 使用 ERE；`.sh` 不使用 bash 4 专有语法（兼容 macOS bash 3.2）。
- **判定命令**：见 `references/verification-method.md` 第 1 节（一次跑完语法 / 行尾 / BOM / 文件名检查）。

### A-4 `#100-4` 报 `references/` 目录缺失（**误报，不修**）

- **原问题**：Phase 0 报告 references 缺失；issue 自己标注为「误报，CLI 封装型技能不需要 references/」。
- **处理**：不把它当作缺陷修；但为满足 `skills_bot` 审查项 #12 / #23，本 PR **仍然新增** `references/` 7 个文件。
- **判定命令**：
  ```bash
  ls "$SKILL/references"   # 期望 7 个 .md：acceptance-criteria / cli-installation-guide /
                           # dataflow-diagram / iam-policies / json-output-parsing /
                           # status-handling / verification-method
  ```

---

## B. issue #113 —— P1（8 项）

### B-3 `#113-3` `codearts models` 无 AK/SK 仍返回 exit 0

- **原问题**：未配置 AK/SK 时 CLI 返回 exit 0，错误信息只写 stderr，调用方误判成功。
- **复现方式（HEAD）**：清空 `CODEARTS_CLI_AK/SK` 后直接调用裸 `codearts models` → `rc=0`，stdout 无有用内容或为错误文本。
- **修复后预期**：wrapper 在**调用 CLI 之前**做凭据预检查；缺凭据时 stdout 输出单个 `{"status":"need_input","code":10,"type":"aksk_required",...}`，`exit 10`，CLI 完全不被调用。
- **判定命令**：`references/verification-method.md` §5.1(a)：`rc=10` 且 `argv` 日志为空。

### B-4 `#113-4` `codearts run --format json` 失败仍返回 exit 0

- **原问题**：无效 AK/SK 或 API 失败时 CLI 仍 exit 0，脚本拿不到失败信号。
- **复现方式（HEAD）**：用无效凭据运行 → `rc=0`，错误只在 stderr。
- **修复后预期**：wrapper 三步守卫（退出码 == 0、stdout 非空、json 模式每行都是合法 JSONL 且无顶层 `{"type":"error"}`）；任一不满足即非 0 退出，**绝不 exit 0**。
- **判定命令**：§5.1(d)(e)(f)(g)(h)，期望 `60/60/50/40/1`。

### B-5 `#113-5` `--format json` 时 stdout 输出非 JSON 文本

- **原问题**：json 模式下 stdout 出现人类可读错误文本，破坏 JSON 契约。
- **复现方式（HEAD）**：桩 CLI 在 `--format json` 下打印 `Unexpected error` 并 exit 0 → 上层把它当成功。
- **修复后预期**：wrapper 逐行 JSONL 校验（优先 `python3`/`python`，无 python 时用 `grep -E` 回退），违规 → `{"code":60,"type":"output_contract_violation"}`，`exit 60`；日志一律 stderr + `[codearts_run]` 前缀。
- **判定命令**：§5.1(e) 与 §2.3（stdout 只允许一个 JSON）。

### B-6 `#113-6` `--save-aksk` 缺少 SK 参数时崩溃

- **原问题**：`setup.sh --save-aksk ONLYAK` → `exit 1`，无友好提示（`$2` 未设置时无参数数量校验）。
- **复现方式（HEAD）**：`HOME=$T bash scripts/setup.sh --save-aksk ONLYAK; echo $?` → `1`，stdout/stderr 均无结构化提示。
- **修复后预期**：解析阶段先校验参数个数与取值，缺值时 stdout 输出单个 `{"status":"error","code":2,"type":"invalid_arguments",...,"fix_hint":"Usage: setup.sh --save-aksk <AK> <SK>",...}`，`exit 2`；stderr 同时给一行人类可读提示。
- **判定命令**：§2.1(a) → `rc=2`，JSON 可 `json.load`。

### B-7 `#113-7` 权限检查依赖文本行格式（紧凑 vs pretty 判定不一致）

- **原问题**：用 `grep -A1` 检测权限配置，pretty-print 后误判为「未配置」。
- **复现方式（HEAD）**：写紧凑 `global.json` → `CONFIGURED`；同一份文件的 pretty 写法 → `NOT_CONFIGURED(rc=20)`；键顺序打乱 → 同样误判。
- **修复后预期**：改为真正的 JSON 解析（`python3` → `jq` → 无依赖回退），紧凑 / pretty / 键乱序三种写法判定**完全一致**，且必须同时存在 `edit` 与 `write` 的 `allow` 才视为已配置。
- **判定命令**：§3 的 `compact` / `pretty` / `pretty-reordered` / `pretty-fallback` 全部 `rc=0`，负例 `only-write(20)`。
- **对应实现**：`setup.sh` 的 `permission_json_ok_python` / `permission_json_ok_jq` / `permission_json_ok_fallback`。

### B-8 `#113-8` CLI 错误消息不匹配认证检测模式

- **原问题**：无效 AK/SK 时 CLI 输出 `Unexpected error`，`setup.sh` 的匹配模式识别不了，错误被归到网络类或直接漏判。
- **复现方式（HEAD）**：桩 CLI 打印 `Unexpected error` 且 exit 0 → 旧逻辑把它当成功。
- **修复后预期**：统一错误分类——认证类 → `50 auth_failed`，网络类 → `40 network_failed`，退出 0 但 stdout 是错误诊断 → 按内容归类，其它非零 → `1 cli_failed`；`setup.sh` 的 `AUTH_ERROR_PATTERN` 覆盖 `unexpected error`。
- **判定命令**：§5.1(f)(g)(h) + §2.1(h)(i)。

### B-11 `#113-11` 文档暗示模型可模糊匹配

- **原问题**：SKILL.md 的表述让人以为 `"GLM-5.1"` 这类短名可被 CLI 匹配，实际 `-m` 必须是 `codearts models` 输出的完整 `provider/model`。
- **复现方式（HEAD）**：`git show $HEAD:$SKILL/SKILL.md` 中模型选择段落未强调「完整 model_id」。
- **修复后预期**：明确写出 **`-m` 必须是从 `codearts models` 输出逐字复制的完整 `provider/model`**；短名会被原样转发并失败；并给出「用户口头说模型名时先映射、并展示解析结果」的流程。
- **判定命令**：
  ```bash
  grep -n 'provider/model' "$SKILL/SKILL.md" | head
  grep -nE 'does not perform fuzzy|NOT resolved to|verbatim' "$SKILL/SKILL.md"
  ```

### B-12 `#113-12` JSON 解析表与实际输出不符

- **原问题**：文档称 `tool_use` 事件含文件路径，实际生成的代码在 `text` 事件的 markdown 代码块里。
- **复现方式（HEAD）**：`git show $HEAD:$SKILL/SKILL.md | grep -n 'output.path'` → 出现在「Record `sessionId`」之外的肯定式描述中。
- **修复后预期**：事件表明确 **代码在 `text` 事件的 `.content` 的 markdown 代码块中**；`tool_use` **不携带生成的文件路径**，明确「不要读 `.output.path`，该字段不会被产生」。
- **判定命令**：
  ```bash
  grep -n 'output.path' "$SKILL/references/json-output-parsing.md"   # 只应出现在“不产生”的否定说明里
  grep -n 'step_start\|step_finish\|tool_use\|`text`' "$SKILL/references/json-output-parsing.md"
  ```

### B-13 `#113-13` CLI 不创建文件，任务里的 `Output:` 路径无效

- **原问题**：任务描述里写 `Output: /path` 但 CLI 不会创建目录或文件，代码只在 `text` 事件里；用户以为文件已生成。
- **复现方式（HEAD）**：运行一次生成任务，`Output:` 指向的目录不存在，CLI 也不报错。
- **修复后预期**：文档明确 **CLI 不创建/写入任何文件**；`Output:` 只是提示（hint）；解析后由 **agent 自己**把代码块落盘（按需创建父目录），并只报告**确实写过**的路径。
- **判定命令**：
  ```bash
  grep -n 'does NOT create or write any files' "$SKILL/references/json-output-parsing.md"
  grep -n 'hint' "$SKILL/references/json-output-parsing.md"
  ```

---

## C. issue #113 —— P2（4 项）

### C-9 `#113-9` 空 AK/SK 值未校验

- **原问题**：`setup.sh --save-aksk "" ""` 未拒绝，静默回退到旧值。
- **复现方式（HEAD）**：`HOME=$T bash scripts/setup.sh --save-aksk "" ""; echo $?` → 未报错且未写坏/未更新。
- **修复后预期**：空值（或仅空白）→ `{"code":2,"type":"empty_credentials"}`，`exit 2`，且**不触碰** `~/.bashrc`；同时对无法安全存储的字符（引号、反斜杠、`$`、反引号、换行）同样拒绝。
- **判定命令**：§2.1(b)；另加「拒绝前后 `.bashrc` 字节一致」断言：
  ```bash
  T=$(mktemp -d); printf 'KEEP=1\n' > "$T/.bashrc"; cp "$T/.bashrc" "$T/before"
  HOME="$T" bash "$SKILL/scripts/setup.sh" --save-aksk "" "" ; echo "rc=$?"
  cmp -s "$T/.bashrc" "$T/before" && echo "OK: .bashrc untouched" || echo "FAIL"
  ```

### C-10 `#113-10` 并发 `--save-aksk` 竞态

- **原问题**：两个进程同时改写 `~/.bashrc` 可能丢写或撕裂。
- **复现方式（HEAD）**：两个进程各写 20 次 → `grep -c` 出现 0 行 / 多行 / 半行。
- **修复后预期**：用 **`mkdir` 目录锁**（macOS 无 `flock`）+ 原子替换；超出预算 → `{"code":2,"type":"lock_timeout"}`；并发后 AK / SK **各恰好 1 行**、成对、无残片。
- **判定命令**：§4。

### C-13 `#113-13`（见 B-13）

见上文 B-13；同一问题在 issue 中按 P2 记录。

### C-14 `#113-14` `-f` 文件附加功能失败

- **原问题**：`codearts run -f /tmp/test.py "add docstring"` → exit 1 且无输出（外部 CLI 不支持该参数）。
- **复现方式（HEAD）**：对裸 `codearts` 执行上述命令。
- **修复后预期**：wrapper **吃掉** `-f` / `--file`（两者等价、可重复），把文件内容以 fenced markdown block 追加到最后一个位置参数（任务描述）；文件不存在 / 不是普通文件 / 不可读 / 为空 → `{"code":60,"type":"attachment_failed"}`，`exit 60`。
- **判定命令**：§5.2——`rc=0`，且 CLI argv 里既无 `-f` 也无附件路径；j1 / j2 → `rc=60`。

---

## D. `skills_bot` 对 PR 的审查项（合并门槛）

| 审查项 | 判据 | 判定命令 |
|--------|------|---------|
| #6 Markdown 章节（Critical） | `## Overview`、`## Prerequisites`、`## Workflow`、`## Core Commands`、`## Parameter Confirmation`、`## Reference Documents` 六个标题**逐字存在** | `for h in Overview Prerequisites Workflow "Core Commands" "Parameter Confirmation" "Reference Documents"; do printf '%-24s %s\n' "$h" "$(grep -cE "^## $h\$" "$SKILL/SKILL.md")"; done`（每项 ≥1） |
| #11 description 触发词 | frontmatter `description` 含字面量 `Triggers include:` | `grep -c 'Triggers include:' "$SKILL/SKILL.md"` |
| #12 references 检查 3/3 | `iam-policies.md`、`verification-method.md`、`cli-installation-guide.md` 存在；`references/` 下全为 kebab-case | `ls "$SKILL/references"`；`ls "$SKILL/references" \| grep -vE '^[a-z0-9]+(-[a-z0-9]+)*\.md$' \|\| echo PASS` |
| #15 含 `--cli-region` | SKILL.md 含 KooCLI 标准语法（含字面量 `--cli-region`）+ 如实说明本 skill 不调用 hcloud/KooCLI | `grep -n -- '--cli-region' "$SKILL/SKILL.md"` |
| #18 行数 ≤500 | `wc -l < "$SKILL/SKILL.md"` ≤ 500（目标 ≤480） | `wc -l < "$SKILL/SKILL.md"` |
| #23 acceptance-criteria | `references/acceptance-criteria.md` 存在 | `test -f "$SKILL/references/acceptance-criteria.md" && echo PASS` |
| #7 Skill 间直接调用 | 文件内不得出现其它 skill 的目录名 | `grep -rhoE 'huawei-cloud-[a-z0-9-]+' "$SKILL" \| sort -u \| grep -v '^huawei-cloud-codearts-code-gen$' \|\| echo PASS` |
| 包约束 | 文件数 ≤30、总量 ≤40MB、扩展名在白名单内 | `references/verification-method.md` §1.3 |
| 安全扫描 | 无硬编码凭据（`CODEARTS_CLI_AK=` / `CODEARTS_CLI_SK=` 只允许接文档占位或短测试值，不得接 20 字符以上的真实值） | `grep -rnE 'CODEARTS_CLI_[AS]K="?[A-Za-z0-9+/=]{20,}' "$SKILL" \|\| echo PASS`（用 `[AS]K` 同时覆盖 AK/SK，避免在正则里写竖线） |

---

## E. 回归基线（每次改动都要重跑）

1. `bash -n` 全部 `.sh` 通过；PowerShell 5.1 解析全部 `.ps1` 通过。
2. 全目录 LF + UTF-8 无 BOM；`references/` 全部 kebab-case `.md`。
3. `setup.sh` 退出码矩阵：`0 / 2 / 10 / 20 / 30 / 40 / 50` 各用例符合预期（`verification-method.md` §2）。
4. wrapper 退出码契约：`1 / 10 / 30 / 40 / 50 / 60`，失败路径永不 `exit 0`（§5）。
5. 文档与实现一致：文档里出现的每个脚本名、参数、退出码都能在脚本源码里找到对应实现。
6. 被移出 SKILL.md 的状态块与 JSON 解析段落**逐字**存在于 `references/status-handling.md` 与 `references/json-output-parsing.md`：

   ```bash
   for t in need_input need_consent invalid_arguments error ready cleared; do
     printf '%-20s %s\n' "$t" "$(grep -c "### Status: $t" "$SKILL/references/status-handling.md")"
   done
   grep -c '### Important: Load AK/SK and PATH' "$SKILL/references/status-handling.md"
   grep -c '^\*\*Parse JSON output:\*\*$'         "$SKILL/references/json-output-parsing.md"
   grep -c '^## Task Description Tips$'           "$SKILL/references/json-output-parsing.md"
   ```
