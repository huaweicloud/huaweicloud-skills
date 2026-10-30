; ============================================================================
; install_sms_agent.au3
; 功能：静默安装 SMS-Agent-Py3.exe
; 说明：使用静默模式安装，无需 GUI 交互，可在 WinRM session 0 中运行
; 命令行参数:
;   CmdLine[1] = 安装包路径 (默认: C:\SMS-Agent-Py3.exe)
;   CmdLine[2] = 安装目录   (默认: C:\SMS-Agent-Py3)
;   CmdLine[3] = 日志路径   (默认: C:\auto_agent_opt\install_log.txt)
; ============================================================================

#include <File.au3>

; ---- 解析命令行参数 ----
Global $g_Installer = "C:\SMS-Agent-Py3.exe"
Global $g_InstallDir = "C:\SMS-Agent-Py3"
Global $g_LogPath = "C:\auto_agent_opt\install_log.txt"

If $CmdLine[0] >= 1 Then $g_Installer = $CmdLine[1]
If $CmdLine[0] >= 2 Then $g_InstallDir = $CmdLine[2]
If $CmdLine[0] >= 3 Then $g_LogPath = $CmdLine[3]

; 日志函数
Func _Log($msg)
    Local $hFile = FileOpen($g_LogPath, 1)
    FileWriteLine($hFile, @YEAR & "/" & @MON & "/" & @MDAY & " " & @HOUR & ":" & @MIN & ":" & @SEC & " - " & $msg)
    FileClose($hFile)
    ConsoleWrite($msg & @CRLF)
EndFunc

_Log("===== 开始安装 SMS-Agent-Py3 =====")
_Log("安装包: " & $g_Installer)
_Log("安装目录: " & $g_InstallDir)
_Log("日志路径: " & $g_LogPath)

; 检查是否已安装
If FileExists($g_InstallDir & "\SMS-Agent.exe") Then
    _Log("SMS-Agent-Py3 已安装，跳过安装步骤")
    Exit(0)
EndIf

; 检查安装包是否存在
If Not FileExists($g_Installer) Then
    _Log("错误：安装包不存在: " & $g_Installer)
    Exit(1)
EndIf

; 静默安装
_Log("正在静默安装 ...")
Local $iPid = RunWait('"' & $g_Installer & '" /S', "", @SW_HIDE)
_Log("安装进程返回码: " & $iPid)

; 等待安装完成
Sleep(3000)

; 验证安装
If FileExists($g_InstallDir & "\SMS-Agent.exe") Then
    _Log("安装成功！SMS-Agent.exe 已就绪")
    _Log("安装路径: " & $g_InstallDir)

    ; 列出关键文件
    If FileExists($g_InstallDir & "\SMS-Agent-cmd.exe") Then
        _Log("SMS-Agent-cmd.exe 存在")
    EndIf
    If FileExists($g_InstallDir & "\config\auth.cfg") Then
        _Log("配置文件 auth.cfg 存在")
    EndIf

    Exit(0)
Else
    _Log("错误：安装后未找到 SMS-Agent.exe，安装可能失败")
    Exit(1)
EndIf
