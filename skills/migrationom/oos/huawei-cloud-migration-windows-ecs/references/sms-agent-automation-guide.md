# SMS-Agent AutoIt 自动化配置技术详解

> 本文档记录通过 WinRM + AutoIt v3 远程自动化配置华为云 SMS-Agent 的完整技术实现细节。
> 基于 `scripts/windows_migration/scripts/py3/` 中的实际代码（configure_sms_agent.au3 v5、configure_sms_agent.exe）分析整理。
> 注：早期版本的外层编排器 `deploy_and_run.py` 已归档移除，其职责现由 `phases/configure_phase.py` 承担；本指南的核心（au3 GUI 自动化）仍适用。

> **适用范围**: 本文档描述的 AutoIt GUI 自动化方案仅适用于 **Python3 GUI Agent**（Windows Server 2012+）。
> 对于 **Python2 CLI Agent**（Windows Server 2008/2008R2/Windows 7），请使用 MSI/Service 静默安装方式，
> 无需 AutoIt 和 GUI 交互，详见 `sms-agent-guide.md` 的 2.2 节。

## 1. 整体架构：三层调用链

```
configure_phase.py (Linux 执行机, 通过 WinRM 远程操控)
  └→ schtasks 计划任务 (Windows, 跳出 session 0 进入 session 1)
       └→ AutoIt3.exe configure_sms_agent.au3 (Windows session 1, GUI 交互)
```

### 为什么要三层？

WinRM 运行在 Windows 的 **session 0**（服务会话）。从 Windows Vista/Server 2008 起，
session 0 被隔离用于服务进程，**看不到也操作不了 GUI**。但 SMS-Agent 是 GUI 程序，
必须有人在界面上填 AK/SK/Domain 并点击按钮。

解决方案：用 `schtasks /create /it` 创建计划任务——`/it` 标志让任务在
**交互式会话（session 1，即 RDP/console 登录的桌面）**中运行，
AutoIt 就能看到并操作窗口了。

**前提条件**：目标 Windows 机器必须有活跃的 console/RDP 会话（有人登录着桌面）。

## 2. configure_phase.py 技术细节

### 2.1 WinRM 连接与编码

```python
s = winrm.Session(WINRM_URL, auth=(WIN_USER, WIN_PASS), transport='ntlm')

def run(cmd):
    r = s.run_cmd(cmd)
    out = r.std_out.decode('gbk', 'replace').strip()  # GBK 解码
    ...
```

- **NTLM 认证**：Windows 默认认证方式
- **GBK 解码**：Windows 中文版 cmd 输出是 GBK 编码，不用 GBK 会乱码
- **run_ps()**：PowerShell 脚本编码为 UTF-16-LE base64，通过 `powershell -EncodedCommand` 执行
  - 解决两个问题：① cmd shell 会吃掉 `$` 变量符号；② 避免引号转义地狱

### 2.2 文件传输：base64 分块

WinRM 单条命令有 **~8KB 长度限制**，.au3 脚本 11-15KB 直接传不了。

**v3 方案**（certutil decode）：
1. 读文件二进制 → base64 编码 → 切成 1500 字符/块
2. 第一块 `Set-Content` 覆盖写入 .b64 文件
3. 后续块 `Add-Content` 追加到 .b64 文件
4. `certutil -decode xxx.b64 xxx.au3` 解码为二进制文件
5. 删除临时 .b64 文件

**v2 方案**（[IO.File]::WriteAllBytes，旧版）：
1. 读文件 → 加 UTF-8 BOM（`\xef\xbb\xbf`）→ base64 编码 → 切成 500 字符/块
2. 第一块 `[IO.File]::WriteAllBytes` 覆盖写入
3. 后续每块：`ReadAllBytes` 读回 → 拼接字节数组 → `WriteAllBytes` 写回
4. BOM 的作用：让 Windows 上 AutoIt 能正确识别 UTF-8 编码读取中文

### 2.3 计划任务执行 AutoIt

```python
def run_au3_via_task(au3_path, task_name, args=""):
    # 1. 生成 .bat：@echo off + 调用 AutoIt3.exe 运行 .au3
    bat = f'@echo off\r\n"{AUTOIT_EXE}" "{au3_path}" {args}\r\n'
    # 2. .bat 通过 base64 写到远程 C:\opt\xxx.bat
    # 3. schtasks /delete 先删旧任务（/f 强制）
    # 4. schtasks /create 创建新任务：
    #    /sc once（只跑一次）、/rl highest（最高权限）、
    #    /it（交互式会话）、/ru /rp 指定运行用户密码
    # 5. schtasks /run 立即触发
```

关键参数：
- `/it` — 在交互式会话中运行（核心！）
- `/rl highest` — 最高权限运行
- `/ru {user} /rp {password}` — 指定运行身份

### 2.4 主流程 7 步

1. `taskkill` 杀 SMS-Agent.exe 和 SMS-Agent-cmd.exe，等 3 秒确认
2. 删旧日志，建 `C:\opt` 目录
3. `transfer_file` 上传 configure_sms_agent.au3，验证远程文件大小
4. `run_au3_via_task` 启动配置，AK/SK/Domain 作为命令行参数传入
5. **轮询 60×5s=5分钟**，读 `configure_log.txt` 最后 3 行，看"配置完成"或"错误+步骤"退出
6. 读完整日志输出
7. 检查进程 + 读 SMS-Agent 日志最后 10 行，判断注册成功

### 2.5 成功判定标志

检查 `SmsAgent_Info.log` 内容：
- `upload os info` / `upload system info` → **注册成功**
- `check ak/sk info success` → AK/SK 验证通过（注册进行中）
- `SMS-Agent-cmd.exe` 进程存在 → Agent 工作进程中（真正的成功标志）

> **注意**：SMS-Agent.exe 只是 GUI 壳，SMS-Agent-cmd.exe 存在才说明真正注册成功。

## 3. configure_sms_agent.au3 技术细节

### 3.1 凭据传入

脚本默认值置空（v5 安全改进），必须从命令行参数传入：
```autoit
Global $g_AK = ""
Global $g_SK = ""
Global $g_Domain = ""
If $CmdLine[0] >= 1 Then $g_AK = $CmdLine[1]
If $CmdLine[0] >= 2 Then $g_SK = $CmdLine[2]
If $CmdLine[0] >= 3 Then $g_Domain = $CmdLine[3]
If $g_AK = "" Or $g_SK = "" Or $g_Domain = "" Then Exit(1)
```

### 3.2 主窗口坐标常量

相对于 SMS-Agent 窗口左上角的偏移量（不是屏幕绝对坐标）：

| 元素 | 常量 | X | Y |
|------|------|---|---|
| AK 输入框 | $REL_AK_X/Y | 221 | 60 |
| SK 输入框 | $REL_SK_X/Y | 219 | 99 |
| Domain 输入框 | $REL_DOMAIN_X/Y | 222 | 139 |
| 启动按钮 | $REL_START_X/Y | 181 | 553 |
| "是"按钮(备用) | $REL_YES_X/Y | 385 | 393 |

### 3.3 核心函数

#### _Log($msg)
写 `C:\opt\configure_log.txt`（模式 1 = 追加），同时 ConsoleWrite。
configure_phase.py 轮询此文件判断进度。

#### _ClientToScreen($hWnd, $clientX, $clientY)
调用 Win32 API `ClientToScreen`，客户区坐标 → 屏幕绝对坐标。
**用于 Tkinter 窗口**，因为 Tkinter 的 `ControlGetPos` 返回客户区坐标，
直接加 `WinGetPos` 偏移会差一个标题栏高度（~31px）。

```autoit
Func _ClientToScreen($hWnd, $clientX, $clientY)
    Local $tPoint = DllStructCreate("int X;int Y")
    DllStructSetData($tPoint, "X", $clientX)
    DllStructSetData($tPoint, "Y", $clientY)
    _WinAPI_ClientToScreen($hWnd, $tPoint)
    Local $aResult[2]
    $aResult[0] = DllStructGetData($tPoint, "X")
    $aResult[1] = DllStructGetData($tPoint, "Y")
    Return $aResult
EndFunc
```

#### _ClickRelative($hWin, $relX, $relY)
SMS-Agent 主窗口用这个。`WinGetPos` + 偏移 → `MouseClick`。
**不用 ClientToScreen**，因为 SMS-Agent 是标准 Win32 窗口，WinGetPos + 偏移已验证可用。

#### _InputRelative($hWin, $relX, $relY, $text)
凭据输入核心逻辑：
1. `_ClickRelative` 点击输入框获焦
2. `Ctrl+A` 全选 → `DELETE` 清空
3. `ClipPut($text)` 放剪贴板 → `Ctrl+V` 粘贴
4. **验证**：`Ctrl+A` → `Ctrl+C` → `ClipGet()` 读回，与原始文本比较
5. 不匹配则重试一次

**为什么不用 Send($text) 逐字符？**
- AutoIt 的 `Send()` 首字符可能丢失
- 特殊字符（`@`、`/`等）会被解释为按键修饰符
- 剪贴板粘贴绕过这些问题

### 3.4 步骤 8："注意"弹窗处理

尝试匹配 5 种标题（注意/Warning/Confirm/提示/Message），每个等 15 秒。
找到后 4 级降级点击：
1. `ControlClick` 按 TEXT 匹配"是"
2. `ControlClick` 按 TEXT 匹配"Yes"
3. `ControlClick` 按 INSTANCE 匹配第一个按钮
4. `Send("{ENTER}")` 直接回车

无弹窗则用坐标 (385, 393) 点击"是"按钮位置作为备用。

### 3.5 步骤 9："选择企业项目"窗口（最复杂）

#### 问题：Tkinter 窗口特性
- 下拉框是 `TkChild` 而非 `ComboBox`，`ControlCommand SelectString` 不适用
- 按钮的 `text` 为空，`ControlClick by TEXT` 无法匹配
- 弹出菜单是 override-redirect 窗口，Win32 API 检测不到

#### v5 解决方案

**1. 关闭 cmd.exe 窗口**
```autoit
Local $aCmds = WinList("[CLASS:ConsoleWindowClass]")
For $i = 1 To $aCmds[0][0]
    WinClose($aCmds[$i][1])
Next
```
计划任务的 .bat 会留下 cmd 窗口，可能遮挡企业项目窗口。

**2. 查找窗口**：4 种标题轮询 30 秒（WinGetHandle + 检查可见性）

**3. 窗口置顶**：WinActivate + WinSetOnTop + WinActivate（多次确保最前）

**4. 自动扫描下拉框控件**（INSTANCE 1-5）
```autoit
For $inst = 1 To 5
    Local $tryPos = ControlGetPos($hEp, "", "[CLASS:TkChild; INSTANCE:" & $inst & "]")
    If IsArray($tryPos) And $tryPos[2] > 50 Then  ; 宽度>50才是下拉框
        $dropPos = $tryPos
        ExitLoop
    EndIf
Next
```
TkChild 找不到再尝试 ComboBox。

**5. ClientToScreen 坐标转换**
取控件中心点（`pos + size/2`），转成屏幕绝对坐标。

**6. 三重兜底 + 重试 3 轮**

每轮尝试：
- **方法 1**：鼠标点击下拉框展开 → 尝试多个 Y 偏移（10/15/20/25px）点击菜单第一项 → 点确定
- **方法 2**：键盘方式 — 点击下拉框 → `Send("{DOWN}")` → `Send("{ENTER}")` → 点确定
- **方法 3**：`ControlClick` 直接点确定按钮（default 可能已预选）

**7. 失败截图**
```autoit
_ScreenCapture_Capture("C:\opt\ep_window.png", ...)
```
3 轮全失败则截图保存供调试。

### 3.6 步骤 10：验证

- 检查 `SMS-Agent.exe` 进程存活
- 等 5 秒后检查 `SMS-Agent-cmd.exe`（fork 出来的命令行版本，存在=注册成功）
- 读 `SmsAgent_Info.log` 最后 500 字符写入配置日志

## 4. install_sms_agent.au3 技术细节

静默安装脚本，**可在 WinRM session 0 直接运行**（不需要计划任务）：

1. 检查 `C:\SMS-Agent-Py3\SMS-Agent.exe` 是否已存在 → 跳过
2. 检查安装包 `C:\SMS-Agent-Py3.exe` → 不存在报错
3. `RunWait("C:\\SMS-Agent-Py3.exe /S", ..., @SW_HIDE)` — `/S` 是 NSIS 静默参数
4. 等 3 秒，验证 SMS-Agent.exe 出现
5. 额外检查 SMS-Agent-cmd.exe 和 config\auth.cfg

## 5. autoit-v3-setup.exe

AutoIt v3 安装包（12.6MB）。目标 Windows 机器需要先装 AutoIt 才能运行 .au3 脚本。
通过 WinRM 静默安装：`autoit-v3-setup.exe /S`（NSIS 静默模式）。

安装后 AutoIt3.exe 路径：`C:\Program Files (x86)\AutoIt3\AutoIt3.exe`

## 6. 远程环境参考

| 项目 | 值 |
|------|-----|
| 操作系统 | Windows Server 2019 |
| WinRM 端口 | 5985 (HTTP) |
| 分辨率 | 1024×768 |
| AutoIt 路径 | C:\Program Files (x86)\AutoIt3\AutoIt3.exe |
| SMS-Agent 路径 | C:\SMS-Agent-Py3\ |
| 配置日志 | C:\opt\configure_log.txt |
| Agent 日志 | C:\SMS-Agent-Py3\Logs\SmsAgent_Info.log |
| Domain | sms.cn-north-4.myhuaweicloud.com |

> **注意**：Domain 是 `sms.cn-north-4`（SMS 服务 endpoint），
> 与 OBS 的 region（如 cn-north-1）不同，不要混淆。

## 7. 窗口坐标参考

### SMS-Agent 主窗口（标准 Win32）

| 元素 | 相对坐标 | 计算方式 |
|------|----------|----------|
| AK 输入框 | (221, 60) | WinGetPos + 偏移 |
| SK 输入框 | (219, 99) | WinGetPos + 偏移 |
| Domain 输入框 | (222, 139) | WinGetPos + 偏移 |
| 启动按钮 | (181, 553) | WinGetPos + 偏移 |

### "选择企业项目"窗口（Tkinter）

| 元素 | 控件类 | 坐标转换方式 |
|------|--------|-------------|
| 下拉框 | TkChild (INSTANCE 1-5) | ClientToScreen（标题栏偏移 ~31px） |
| 确定按钮 | Button (INSTANCE 1-3) | ClientToScreen |

> **关键区别**：主窗口用 `WinGetPos + 偏移`（已验证可用）；
> 企业项目窗口必须用 `ClientToScreen`（Tkinter 标题栏偏移 ~31px）。

## 8. 验证成功日志

配置成功后，`SmsAgent_Info.log` 应包含：

```
check ak/sk info success                    # AK/SK 验证通过
enterprise projects count: 19               # 查询到企业项目
successfully upload os info, source_id: ... # 源端信息上传成功
Success to upload system info               # 系统信息上传成功
start schedule task which gets command from SMS  # 开始接收 SMS 指令
start heart beat monitor thread             # 心跳监控启动
```

## 9. 版本演进

| 版本 | 文件 | 关键改进 |
|------|------|----------|
| v4 FINAL | configure_sms_agent.au3 | 剪贴板粘贴 + ClientToScreen + 4级降级 |
| v5 | configure_sms_agent.au3 | 多重兜底下拉框（扫描INSTANCE 1-5、多Y偏移、三重兜底、重试3轮、失败截图、凭据置空） |
| v2 | configure_phase.py | [IO.File]::WriteAllBytes 分块、硬编码凭据 |
| v3 | configure_phase.py | argparse+环境变量、certutil decode、chunk_size=1500、凭据不硬编码 |
