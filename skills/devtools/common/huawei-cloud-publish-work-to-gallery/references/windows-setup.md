# Windows 前置准备（PowerShell 5.1 / Git Bash）

本文件承接 SKILL.md 中的 Windows 专属一次性准备项，首次在 Windows 上发布前按此完成即可。

## 0. Start-Process 后台启动注意（Windows 上启动本地服务/隧道）

`Start-Process -RedirectStandardOutput X -RedirectStandardError X` **不能把 stdout 与 stderr 重定向到同一文件**（PS 5.1 抛 `InvalidOperationException`，且重定向到同一路径时不可见）。正确做法是拆成两个日志文件：

```powershell
$out = "<log-dir>\http-out.log"; $err = "<log-dir>\http-err.log"
Start-Process -FilePath "python" -ArgumentList "-m","http.server","8080","--bind","127.0.0.1" `
  -WorkingDirectory "<workDir>" -RedirectStandardOutput $out -RedirectStandardError $err -WindowStyle Hidden
# 注意：-WorkingDirectory 与 -RedirectStandardOutput 参数在较长命令行组合时可能触发外壳层的
# "ChildProcess.kill" 类异常，属于 opencode/PS 外壳与 Start-Process 的子进程生命周期问题——
# 命令被打断不代表服务没起来，重新执行应优先检查端口监听（netstat / Get-NetTCPConnection）再判断是否重试。
```

启动后**必须验证进程真实监听端口并返回本项目内容**（见 SKILL.md Step 2 健康检查要求），不要假设已成功。

## 1. 控制台编码（PowerShell 5.1）

PowerShell 5.1 控制台默认按系统代码页（GBK/CP936）解码 stdout，导致 Node/Python 脚本输出的中文显示为乱码。脚本内部已加 `setDefaultEncoding("utf8")` / `sys.stdout.reconfigure(encoding="utf-8")`（win32 条件），但作为双保险，首次进入发布流程时执行一次：

```powershell
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::InputEncoding  = [System.Text.Encoding]::UTF8
$env:PYTHONIOENCODING     = "utf-8"
chcp 65001 > $null
```

## 2. git 可用性

`git --version` 失败（未安装）时，不要跳过 Step 3，按以下引导用户安装：

```powershell
# 从清华镜像下载 Git for Windows
# 1. 打开 https://mirrors.tuna.tsinghua.edu.cn/github-release/git-for-windows/git/
# 2. 进入最新版本目录（如 Release-2.46.0/），下载 64-bit 安装包（如 Git-2.46.0-64-bit.exe）
# 3. 运行安装程序，保持默认选项（安装时自动配置 PATH）
# 4. 安装完成后重新打开终端，再次运行 git --version 验证
# 安装 Git for Windows 会附带 Git Bash（C:\Program Files\Git\bin\bash.exe）
```

## 3. 渲染门禁脚本选择（preflight.ps1 vs preflight.sh）

- `preflight.sh` 依赖 bash 执行。Windows 需安装 **Git Bash**（随 Git for Windows 附带）或 WSL 发行版。
- 若 bash 不可用，改用 PowerShell 原生版：`powershell -ExecutionPolicy Bypass -File <skill>/scripts/preflight.ps1`（与 preflight.sh 的 Windows 分支逻辑对齐，优先复用系统 Edge/Chrome，无需 bash）。

### bash 可用性判断（避免 WSL stub 误判）

Windows 10/11 默认在 `C:\Users\<user>\AppData\Local\Microsoft\WindowsApps\bash.exe` 放置 WSL stub，`Get-Command bash` 会找到它但无发行版时不可用。**禁止仅凭 `Get-Command bash` 判断，必须实际执行：**

```powershell
$bashOk = $false
try { $r = bash -c "echo ok" 2>&1; if ($r -match "ok") { $bashOk = $true } } catch {}
if (-not $bashOk) { Write-Host "bash 不可用（WSL stub 无发行版），改用 preflight.ps1" }
```

仅当 `$bashOk=true` 时方可使用 `preflight.sh`，否则走 `preflight.ps1`。

### preflight.ps1 编码自检（PowerShell 5.1）

`preflight.ps1` 必须以 **UTF-8 with BOM** 保存方可被 PowerShell 5.1 正确解析（无 BOM 时按 GBK 解码中文 → 语法错误）。运行前自动检测并修正：

```powershell
$f = "<skill>/scripts/preflight.ps1"
$b = [System.IO.File]::ReadAllBytes($f)
if (-not ($b.Length -ge 3 -and $b[0] -eq 0xEF -and $b[1] -eq 0xBB -and $b[2] -eq 0xBF)) {
  $c = [System.IO.File]::ReadAllText($f, [System.Text.Encoding]::UTF8)
  [System.IO.File]::WriteAllText($f, $c, [System.Text.UTF8Encoding]::new($true))
}
```

## 4. Playwright Python 包路径（跨平台通用）

Python Playwright 通过 `pip install playwright` 安装为 Python 包，模块解析走 `sys.path`（site-packages），无需 `node_modules` 目录：

- 自写截图脚本可放在任意目录运行（Python 包全局可见），无需像 Node 那样放 `scripts/` 下。内置脚本（`screenshot_guard.py`）直接 `python <skill>/scripts/screenshot_guard.py` 即可运行。
- `python -c "import playwright"` 可在任意 CWD 测试可用性（Python 包解析不依赖 CWD）：

```powershell
# 直接测试 Playwright Python 包是否可用（无需切换目录）
python -c "import playwright"
```

> 若 `preflight.ps1` / `preflight.sh` 检测到 Playwright 未装，会自动 `pip install playwright` + `python -m playwright install chromium`——优先复用系统 Edge/Chrome，无需下载 ~300MB Chromium。

## 5. 详情 zip 打包（首选 build-detail-zip.mjs，跨平台零依赖）

**首选：** `build-detail-zip.mjs` 内置正确目录结构（README.md@根 + `resources/` 前缀）并自动跑服务端同源校验，一步到位、无编码/平台坑：

```bash
node <skill>/scripts/build-detail-zip.mjs --readme <README.md> --resources <resources-dir> --out <workDetail.zip>
```

**备选（仅当 build-detail-zip.mjs 不可用时）：** `Compress-Archive` 在 PowerShell 5.1 会压平子目录，生成的 zip 只有 `README.md + arch.png`（丢失 `resources/` 前缀），平台校验返回 `GALLERY.PARAM.DETAIL_ZIP_INVALID`。必须用 .NET `ZipFile::CreateFromDirectory` 保留目录结构：

```powershell
Add-Type -AssemblyName System.IO.Compression.FileSystem
Remove-Item "$env:TEMP\workDetail.zip" -ErrorAction SilentlyContinue
[System.IO.Compression.ZipFile]::CreateFromDirectory("$staging", "$env:TEMP\workDetail.zip")
```

打包后可本地验证结构：`node <skill>/scripts/validate-detail-zip.mjs <zip>`（复用服务端 `parseDetailZip` 规则）。

## 6. 发布调用（Windows 用 publish-work.mjs）

PowerShell 直接向 `api.mjs` 传中文（`workName`/`introduction`）会被按系统代码页转码 → 400 参数错误。正确做法：把发布参数写入 UTF-8 JSON 文件，再经 Node 进程内 UTF-8 调 api.mjs（`publish-work.mjs` 内部还内置了门禁强制校验）：

```bash
node <skill>/scripts/publish-work.mjs --params <utf8-params.json> [--api <skill>/scripts/api.mjs] [--max-age <秒>]
```

## 7. Python 解释器选择（`python3` Store stub 陷阱）

Windows 上 `python3` 常指向 `WindowsApps` 的 Store stub（`Get-Command python3` 有结果但执行即失败，进程退出码 9009 / 无输出）。涉及 Python 的门禁命令（`verify-glyphs.py`、matplotlib 图表等）在 Windows 上**应先确认 `python3` 真实可用，不可用时改用 `python`**：

```powershell
python3 -c "print('py3 ok')" 2>$null   # 失败（Store stub）则改用 python
python <skill>/scripts/verify-glyphs.py <image.png>
```

`preflight.ps1` 已内置该回退（`@("python3","python") | Where-Object { Test-PyCmd $_ }`），但 SKILL.md / work-preparation.md 中的命令示例默认写 `python3`——Windows 实际执行时按本节替换为 `python` 即可。

## 7b. 多 Python 解释器补装（Windows）

Windows 可能同时存在 `python3.9` 与 `python`（3.11）等多个解释器，**site-packages 互不可见**。若 `preflight.ps1` 只装到主解释器，agent 用另一个解释器调门禁脚本会 `ModuleNotFoundError: playwright`。

`preflight.ps1` 已内置 `Add-OtherPythonDeps`：发现 `python3/python/python3.13~3.8` 候选（真实路径去重），为**主解释器之外**的每个解释器补装 `numpy/pillow/playwright`；补装失败**记录 `⚠️` 日志而非静默**（gate 不记录该解释器，避免误以为就绪）。gate 文件的 `python_bins=` 只含补装成功的解释器。