; configure_sms_agent.au3 (release — 安全增强: 敏感参数从临时文件读取, 不经命令行明文传递)
; DPI 自适应: _S() 缩放换算 + _DetectDpi() 检测 + _RefineScale() 窗口尺寸修正 + _WinStabilize() 渲染稳定
; EP选择: 展开→DOWN→Enter遍历 + 读EP文本框，匹配目标，找不到回default
; 测试验证: DPI 96/1024x768 ✓, DPI 96/1536x864 ✓, console/RDP 双会话 ✓, 5/5 标记全通过
;
; 命令行参数:
;   CmdLine[1] = 敏感参数文件路径 (base64编码, 读取后自动删除)
;   CmdLine[2] = Mode (direct/proxy)
;   CmdLine[3] = ProxyIP
;   CmdLine[4] = ProxyPort
;   CmdLine[5] = LogPath
;   CmdLine[6] = InstallDir (可选, 默认 C:\SMS-Agent-Py3)
;
; 敏感参数文件格式 (base64编码前):
;   AK=xxx
;   SK=xxx
;   Domain=xxx
;   EP=xxx
;   ProxyUser=xxx
;   ProxyPass=xxx

Global $g_AK = ""
Global $g_SK = ""
Global $g_Domain = ""
Global $g_EP = ""
Global $g_Mode = "direct"
Global $g_ProxyIP = ""
Global $g_ProxyPort = "3128"
Global $g_ProxyUser = ""
Global $g_ProxyPass = ""
Global $g_LogPath = "C:\auto_agent_opt\configure_log.txt"
; SMS-Agent-Py3 安装目录 (可通过 CmdLine[6] 覆盖, 默认 C:\SMS-Agent-Py3)
Global $g_InstallDir = "C:\SMS-Agent-Py3"

; ---- Base64 解码函数 (使用 MSXML COM 对象) ----
Func _Base64Decode($sB64)
    Local $oXML = ObjCreate("Msxml2.DOMDocument")
    Local $oNode = $oXML.createElement("b64")
    $oNode.dataType = "bin.base64"
    $oNode.text = $sB64
    Return BinaryToString($oNode.nodeTypedValue, 4)  ; 4 = UTF-8, 兼容中英文OS
EndFunc

; ---- 从临时文件读取敏感参数 (base64编码的 key=value 行) ----
Func _LoadSecrets($sFilePath)
    If Not FileExists($sFilePath) Then Return False
    Local $hFile = FileOpen($sFilePath, 0)
    If $hFile = -1 Then Return False
    Local $sB64 = FileRead($hFile)
    FileClose($hFile)
    ; 立即删除临时文件, 减少敏感数据在磁盘上的暴露窗口
    FileDelete($sFilePath)
    ; 解码 base64
    Local $sPlain = _Base64Decode($sB64)
    ; 逐行解析 key=value
    Local $aLines = StringSplit($sPlain, @CRLF)
    For $i = 1 To $aLines[0]
        Local $sLine = StringStripWS($aLines[$i], 3)
        If StringLen($sLine) = 0 Then ContinueLoop
        Local $iEq = StringInStr($sLine, "=")
        If $iEq = 0 Then ContinueLoop
        Local $sKey = StringLeft($sLine, $iEq - 1)
        Local $sVal = StringMid($sLine, $iEq + 1)
        Switch $sKey
            Case "AK"
                $g_AK = $sVal
            Case "SK"
                $g_SK = $sVal
            Case "Domain"
                $g_Domain = $sVal
            Case "EP"
                $g_EP = $sVal
            Case "ProxyUser"
                $g_ProxyUser = $sVal
            Case "ProxyPass"
                $g_ProxyPass = $sVal
        EndSwitch
    Next
    Return True
EndFunc

; ---- 解析命令行参数 ----
If $CmdLine[0] >= 1 Then _LoadSecrets($CmdLine[1])
If $CmdLine[0] >= 2 Then $g_Mode = $CmdLine[2]
If $CmdLine[0] >= 3 Then $g_ProxyIP = $CmdLine[3]
If $CmdLine[0] >= 4 Then $g_ProxyPort = $CmdLine[4]
If $CmdLine[0] >= 5 Then $g_LogPath = $CmdLine[5]
If $CmdLine[0] >= 6 Then $g_InstallDir = $CmdLine[6]

Global Const $REL_AK_X = 221, $REL_AK_Y = 60
Global Const $REL_SK_X = 219, $REL_SK_Y = 99
Global Const $REL_DOMAIN_X = 222, $REL_DOMAIN_Y = 139
Global Const $REL_START_X = 181, $REL_START_Y = 553
Global Const $REL_YES_X = 385, $REL_YES_Y = 393
Global Const $WIN_TITLE = "SMS-Agent"
Global Const $EP_ARROW_X = 241, $EP_ARROW_Y = 96
Global Const $EP_BTN_X = 174, $EP_BTN_Y = 154
Global Const $EP_TEXT_X = 50, $EP_TEXT_Y = 96
Global Const $EP_MAX_ITEMS = 15

Global Const $REL_DIRECT_RADIO_X = 143, $REL_DIRECT_RADIO_Y = 180
Global Const $REL_PROXY_RADIO_X = 342, $REL_PROXY_RADIO_Y = 180
Global Const $REL_PROXY_IP_X = 223, $REL_PROXY_IP_Y = 233
Global Const $REL_PROXY_PORT_X = 227, $REL_PROXY_PORT_Y = 268
Global Const $REL_PROXY_USER_X = 227, $REL_PROXY_USER_Y = 310
Global Const $REL_PROXY_PASS_X = 224, $REL_PROXY_PASS_Y = 347

; ============================================================================
; DPI 自适应缩放 — 自动适配不同分辨率/DPI 的坐标换算
; 原理: 所有坐标在 96 DPI (100%) 下标定，运行时按实际 DPI 等比缩放
;       找到窗口后用实际窗口尺寸二次修正，确保精准
; ============================================================================
Global $g_DpiScale = 1.0
Global Const $BASE_DPI = 96
Global Const $BASE_WIN_W = 616    ; 100% DPI 下主窗口宽度 (770/1.25)
Global Const $BASE_WIN_H = 589    ; 100% DPI 下主窗口高度 (736/1.25)

; _S: 坐标缩放换算函数 — 所有相对坐标经过此函数转换为当前 DPI 下的实际偏移
Func _S($val)
    Return Round($val * $g_DpiScale)
EndFunc

; _DetectDpi: 检测系统 DPI 并计算缩放因子
Func _DetectDpi()
    Local $dpi = 0
    ; 方法1: Win10 1607+ GetDpiForSystem
    Local $aRet = DllCall("user32.dll", "uint", "GetDpiForSystem")
    If Not @error And $aRet[0] > 0 Then
        $dpi = $aRet[0]
    EndIf
    ; 方法2: 注册表 AppliedDPI
    If $dpi = 0 Then
        $dpi = Number(RegRead("HKCU\Control Panel\Desktop\WindowMetrics", "AppliedDPI"))
    EndIf
    ; 方法3: 回退 96
    If $dpi = 0 Then $dpi = 96
    $g_DpiScale = $dpi / $BASE_DPI
    _Log(StringFormat("DPI 检测: %d, 缩放因子: %.2f", $dpi, $g_DpiScale))
    Return $dpi
EndFunc

; _RefineScale: 根据实际窗口尺寸修正缩放因子（覆盖 DPI 检测不准的场景）
Func _RefineScale($hWin)
    Local $aPos = WinGetPos($hWin)
    If Not IsArray($aPos) Or $aPos[2] <= 0 Or $aPos[3] <= 0 Then Return
    Local $scaleX = $aPos[2] / $BASE_WIN_W
    Local $scaleY = $aPos[3] / $BASE_WIN_H
    Local $avgScale = ($scaleX + $scaleY) / 2
    ; 仅在合理范围 (0.8~3.0) 内修正
    If $avgScale >= 0.8 And $avgScale <= 3.0 Then
        _Log(StringFormat("窗口尺寸修正: 实际 %dx%d, scaleX=%.3f scaleY=%.3f -> %.3f", _
            $aPos[2], $aPos[3], $scaleX, $scaleY, $avgScale))
        $g_DpiScale = $avgScale
    Else
        _Log(StringFormat("窗口尺寸异常 %dx%d, 保持 DPI 缩放 %.2f", $aPos[2], $aPos[3], $g_DpiScale))
    EndIf
EndFunc

; _WinStabilize: 等待窗口尺寸/位置稳定（渲染完成后返回最新位置）
; 解决: 高分辨率下 Tkinter 窗口先以小尺寸出现，再resize到最终尺寸的时序竞争
Func _WinStabilize($hWin, $maxWaitMs = 5000)
    Local $aPrev = WinGetPos($hWin)
    If Not IsArray($aPrev) Then Return 0
    Local $stable = 0
    Local $startTime = TimerInit()
    While TimerDiff($startTime) < $maxWaitMs
        Sleep(300)
        Local $aCurr = WinGetPos($hWin)
        If Not IsArray($aCurr) Then ContinueLoop
        If $aCurr[0] = $aPrev[0] And $aCurr[1] = $aPrev[1] And $aCurr[2] = $aPrev[2] And $aCurr[3] = $aPrev[3] Then
            $stable += 1
            If $stable >= 2 Then
                _Log(StringFormat("窗口已稳定: (%d,%d) %dx%d (等待%.0fms)", $aCurr[0], $aCurr[1], $aCurr[2], $aCurr[3], TimerDiff($startTime)))
                Return $aCurr
            EndIf
        Else
            $stable = 0
            _Log(StringFormat("窗口渲染中: (%d,%d) %dx%d -> (%d,%d) %dx%d", $aPrev[0], $aPrev[1], $aPrev[2], $aPrev[3], $aCurr[0], $aCurr[1], $aCurr[2], $aCurr[3]))
        EndIf
        $aPrev = $aCurr
    WEnd
    _Log("窗口稳定等待超时，使用最后已知位置")
    Local $aFinal = WinGetPos($hWin)
    If IsArray($aFinal) Then Return $aFinal
    Return $aPrev
EndFunc



Func _MatchEp($sText, $sTarget)
    If StringLen($sText) = 0 Or StringLen($sTarget) = 0 Then Return False
    If StringInStr($sText, $sTarget) Then Return True
    If StringInStr($sTarget, "(") Then
        Local $sEng = StringRegExpReplace($sTarget, "\(.*$", "")
        If $sEng <> "" And StringInStr($sText, $sEng) Then Return True
        Local $sChn = StringRegExpReplace($sTarget, "^.*\(", "")
        $sChn = StringRegExpReplace($sChn, "\)$", "")
        If $sChn <> "" And StringInStr($sText, $sChn) Then Return True
    EndIf
    Return False
EndFunc

Func _Log($msg)
    Local $hFile = FileOpen($g_LogPath, 1)
    FileWriteLine($hFile, @YEAR & "/" & @MON & "/" & @MDAY & " " & @HOUR & ":" & @MIN & ":" & @SEC & " - " & $msg)
    FileClose($hFile)
    ConsoleWrite($msg & @CRLF)
EndFunc

Func _ClickRelative($hWin, $relX, $relY, $desc = "")
    Local $aPos = WinGetPos($hWin)
    If @error Or Not IsArray($aPos) Then
        _Log("错误: 无法获取窗口位置 - " & $desc)
        Return False
    EndIf
    Local $absX = $aPos[0] + _S($relX)
    Local $absY = $aPos[1] + _S($relY)
    _Log(StringFormat("点击 [%s]: (%d,%d)", $desc, $absX, $absY))
    WinActivate($hWin)
    Sleep(500)
    MouseClick("left", $absX, $absY, 1, 3)
    Sleep(800)
    Return True
EndFunc

Func _InputRelative($hWin, $relX, $relY, $text, $desc = "")
    _ClickRelative($hWin, $relX, $relY, $desc & " (点击)")
    WinActivate($hWin)
    Sleep(300)
    Send("^a")
    Sleep(300)
    Send("{DELETE}")
    Sleep(500)
    ClipPut($text)
    Sleep(300)
    Send("^v")
    Sleep(1000)
    WinActivate($hWin)
    Sleep(200)
    Send("^a")
    Sleep(300)
    Send("^c")
    Sleep(300)
    Local $sReadBack = ClipGet()
    If StringStripWS($sReadBack, 3) = StringStripWS($text, 3) Then
        _Log("验证成功 [" & $desc & "]: 长度:" & StringLen($text))
    Else
        _Log("验证不匹配 [" & $desc & "]，重试...")
        WinActivate($hWin)
        Sleep(300)
        Send("^a")
        Sleep(300)
        Send("{DELETE}")
        Sleep(500)
        ClipPut($text)
        Sleep(300)
        Send("^v")
        Sleep(1000)
        _Log("重试完成 [" & $desc & "]: 长度:" & StringLen($text))
    EndIf
    Return True
EndFunc

Func _WinGetPosRetry($hWin, $maxRetries = 5)
    Local $epPos = 0
    For $i = 1 To $maxRetries
        $epPos = WinGetPos($hWin)
        If Not @error And IsArray($epPos) Then Return $epPos
        $epPos = WinGetPos(WinGetTitle($hWin))
        If Not @error And IsArray($epPos) Then Return $epPos
        Local $tRect = DllStructCreate("struct;long left;long top;long right;long bottom;endstruct")
        Local $aRet = DllCall("user32.dll", "bool", "GetWindowRect", "hwnd", $hWin, "struct*", $tRect)
        If $aRet[0] Then
            Local $aResult[4]
            $aResult[0] = DllStructGetData($tRect, "left")
            $aResult[1] = DllStructGetData($tRect, "top")
            $aResult[2] = DllStructGetData($tRect, "right") - $aResult[0]
            $aResult[3] = DllStructGetData($tRect, "bottom") - $aResult[1]
            If $aResult[2] > 0 And $aResult[3] > 0 Then Return $aResult
        EndIf
        WinActivate($hWin)
        _Log("WinGetPos 失败 (" & $i & "/" & $maxRetries & ")，重试...")
        Sleep(2000)
    Next
    Return 0
EndFunc

; ============================================================================
; 主流程
; ============================================================================
_DetectDpi()
_Log("===== 开始配置 SMS-Agent =====")
_Log("AK: (provided, 已打码)")
_Log("SK: (provided, 已打码)")
_Log("Domain: " & $g_Domain)
_Log("企业项目目标: " & $g_EP)

; 步骤 0: 切换英文键盘布局
_Log("步骤 0: 切换英文键盘布局")
DllCall("user32.dll", "long", "LoadKeyboardLayout", "str", "00000409", "uint", 1)
Sleep(500)
Send("{ESC}")
Sleep(300)
_Log("英文键盘已激活")

; 记录日志偏移
Local $sLogPath0 = $g_InstallDir & "\Logs\SmsAgent_Info.log"
Local $iLogOffset = 0
If FileExists($sLogPath0) Then
    $iLogOffset = FileGetSize($sLogPath0)
EndIf
_Log("日志偏移量: " & $iLogOffset & " 字节")

; 步骤 1: 清理旧进程并启动
_Log("步骤 1: 清理旧进程并启动 SMS-Agent.exe")
RunWait(@ComSpec & " /c taskkill /f /im SMS-Agent.exe 2>nul", "", @SW_HIDE)
RunWait(@ComSpec & " /c taskkill /f /im SMS-Agent-cmd.exe 2>nul", "", @SW_HIDE)
Sleep(2000)

If ProcessExists("SMS-Agent.exe") Then
    _Log("警告: SMS-Agent.exe 仍存在，再次尝试关闭")
    RunWait(@ComSpec & " /c taskkill /f /im SMS-Agent.exe", "", @SW_HIDE)
    Sleep(2000)
EndIf

Local $iPid = Run($g_InstallDir & "\SMS-Agent.exe", $g_InstallDir, @SW_SHOW)
_Log("已启动, PID: " & $iPid)
For $wPoll = 1 To 15
    $hWin = WinWait($WIN_TITLE, "", 3)
    If $hWin <> 0 Then
        $aPos = WinGetPos($hWin)
        If IsArray($aPos) And $aPos[2] > 300 And $aPos[3] > 300 Then
            _Log(StringFormat("找到主窗口: (%d,%d) %dx%d (轮询%d次)", $aPos[0], $aPos[1], $aPos[2], $aPos[3], $wPoll))
            ExitLoop
        EndIf
        _Log(StringFormat("窗口太小跳过: (%d,%d) %dx%d, 继续找...", $aPos[0], $aPos[1], $aPos[2], $aPos[3]))
        $hWin = 0
    EndIf
Next
If $hWin = 0 Then
    _Log("错误: 未找到主窗口(可能只有托盘小窗口)")
    Exit(1)
EndIf
WinSetState($hWin, "", @SW_SHOW)
WinMove($hWin, "", 50, 50)
Sleep(500)
WinActivate($hWin)
Sleep(1500)
$aPos = WinGetPos($hWin)
WinSetOnTop($hWin, "", 1)
_Log("主窗口已置顶（防止干扰）")
_Log(StringFormat("窗口就位: (%d,%d) %dx%d", $aPos[0], $aPos[1], $aPos[2], $aPos[3]))
    ; 等待主窗口渲染稳定
    Local $aMainStable = _WinStabilize($hWin)
    If IsArray($aMainStable) Then $aPos = $aMainStable
_RefineScale($hWin)

; 步骤 3-5: 输入 AK / SK / Domain
_Log("步骤 3: 输入 AK")
_InputRelative($hWin, $REL_AK_X, $REL_AK_Y, $g_AK, "AK")
_Log("步骤 4: 输入 SK")
_InputRelative($hWin, $REL_SK_X, $REL_SK_Y, $g_SK, "SK")
_Log("步骤 5: 输入 Domain")
_InputRelative($hWin, $REL_DOMAIN_X, $REL_DOMAIN_Y, $g_Domain, "Domain")

; 步骤 6: 选择启动方式
If $g_Mode = "proxy" Then
    _Log("步骤 6: 使用代理模式")
    _ClickRelative($hWin, $REL_PROXY_RADIO_X, $REL_PROXY_RADIO_Y, "使用代理 radio")
    Sleep(1000)
    _InputRelative($hWin, $REL_PROXY_IP_X, $REL_PROXY_IP_Y, $g_ProxyIP, "代理服务器IP")
    _InputRelative($hWin, $REL_PROXY_PORT_X, $REL_PROXY_PORT_Y, $g_ProxyPort, "代理端口")
    If $g_ProxyUser <> "" Then
        _InputRelative($hWin, $REL_PROXY_USER_X, $REL_PROXY_USER_Y, $g_ProxyUser, "代理用户名")
    Else
        _Log("代理用户名: 未填写（可选）")
    EndIf
    If $g_ProxyPass <> "" Then
        _InputRelative($hWin, $REL_PROXY_PASS_X, $REL_PROXY_PASS_Y, $g_ProxyPass, "代理密码")
    Else
        _Log("代理密码: 未填写（可选）")
    EndIf
Else
    _Log("步骤 6: 确认直连模式（默认选中）")
EndIf
Sleep(500)
; 记录点击Start前已有的TkTopLevel窗口(用于动态兜底检测EP窗口)
Local $aPreWins = WinList("[CLASS:TkTopLevel]")
_Log("步骤7前 TkTopLevel 窗口数: " & $aPreWins[0][0])
_Log("步骤 7: 点击启动按钮")
_ClickRelative($hWin, $REL_START_X, $REL_START_Y, "启动")

; 步骤 8: "注意"弹窗
_Log("步骤 8: 等待'注意'弹窗")
Local $hPopup = 0, $sPopupTitle = ""
Local $aTitles[6] = ["Attention", "注意", "Warning", "Confirm", "提示", "Message"]
For $i = 0 To UBound($aTitles) - 1
    $hPopup = WinWait($aTitles[$i], "", 15)
    If $hPopup <> 0 Then
        $sPopupTitle = $aTitles[$i]
        _Log("找到弹窗: '" & $sPopupTitle & "'")
        ExitLoop
    EndIf
Next
If $hPopup <> 0 Then
    WinSetOnTop($hPopup, "", 1)
    Sleep(300)
    WinActivate($hPopup)
    Sleep(800)
    Local $bClicked = False
    $bClicked = ControlClick($sPopupTitle, "", "[CLASS:Button; TEXT:是]")
    If Not $bClicked Then $bClicked = ControlClick($sPopupTitle, "", "[CLASS:Button; TEXT:Yes]")
    If Not $bClicked Then $bClicked = ControlClick($sPopupTitle, "", "[CLASS:Button; INSTANCE:1]")
    If Not $bClicked Then Send("{ENTER}")
    _Log("已点击确认按钮")
Else
    _Log("未检测到弹窗，用相对坐标兜底")
    _ClickRelative($hWin, $REL_YES_X, $REL_YES_Y, "是(兜底)")
EndIf
Sleep(2000)

; 步骤 9: "选择企业项目"弹窗
_Log("步骤 9: 处理企业项目弹窗（目标: " & $g_EP & "）")

; 关闭 cmd.exe 窗口
Local $aCmds = WinList("[CLASS:ConsoleWindowClass]")
For $i = 1 To $aCmds[0][0]
    WinClose($aCmds[$i][1])
Next
Sleep(1000)

; 方式1: 轮询找EP窗口
Local $hEp = 0, $epPos = 0, $sEpTitle = ""
Local $aEpTitles[6] = ["选择企业项目", "企业项目", "Select Enterprise Project", "选择项目", "Enterprise Project", "Select Project"]
Local $sLogPath = $g_InstallDir & "\Logs\SmsAgent_Info.log"

For $poll = 1 To 10
    Sleep(2000)
    For $ti = 0 To UBound($aEpTitles) - 1
        Local $aAllWins = WinList("[CLASS:TkTopLevel]")
        Local $bestArea = 999999
        For $ewi = 1 To $aAllWins[0][0]
            Local $sEW = $aAllWins[$ewi][0]
            Local $hEW = $aAllWins[$ewi][1]
            Local $aEP2 = WinGetPos($hEW)
            If IsArray($aEP2) Then
                Local $area = $aEP2[2] * $aEP2[3]
                If StringInStr($sEW, $aEpTitles[$ti]) And $area < $bestArea Then
                    $bestArea = $area
                    $epPos = $aEP2
                    $hEp = $hEW
                    $sEpTitle = $sEW
                EndIf
            EndIf
        Next
        If $hEp <> 0 Then ExitLoop
    Next
    If $hEp <> 0 Then
        _Log(StringFormat("方式1: 轮询%d次找到EP窗口 '%s' (%d,%d) %dx%d", $poll, $sEpTitle, $epPos[0], $epPos[1], $epPos[2], $epPos[3]))
        ExitLoop
    EndIf
    _Log("方式1: 轮询" & $poll & "/10, EP窗口未出现")
Next

; 方式2兜底: 查日志
If $hEp = 0 Then
    _Log("方式1未找到，尝试方式2: 查日志...")
    For $poll2 = 1 To 5
        Sleep(2000)
        If FileExists($sLogPath) Then
            Local $hLog = FileOpen($sLogPath, 0)
            Local $sAllLog = FileRead($hLog)
            FileClose($hLog)
            If StringInStr($sAllLog, "查询企业项目") Or StringInStr($sAllLog, "query enterprise") Or StringInStr($sAllLog, "Query enterprise") Or StringInStr($sAllLog, "querying enterprise") Then
                _Log("方式2: 日志中发现'查询企业项目'，等4s...")
                Sleep(4000)
                For $ti = 0 To UBound($aEpTitles) - 1
                    Local $aAllWins2 = WinList("[CLASS:TkTopLevel]")
                    Local $bestArea2 = 999999
                    For $ewi = 1 To $aAllWins2[0][0]
                        Local $sEW = $aAllWins2[$ewi][0]
                        Local $hEW = $aAllWins2[$ewi][1]
                        Local $aEP2 = WinGetPos($hEW)
                        If IsArray($aEP2) Then
                            Local $area = $aEP2[2] * $aEP2[3]
                            If StringInStr($sEW, $aEpTitles[$ti]) And $area < $bestArea2 Then
                                $bestArea2 = $area
                                $epPos = $aEP2
                                $hEp = $hEW
                                $sEpTitle = $sEW
                            EndIf
                        EndIf
                    Next
                    If $hEp <> 0 Then ExitLoop
                Next
                If $hEp <> 0 Then
                    _Log(StringFormat("方式2: 找到EP窗口 '%s' (%d,%d) %dx%d", $sEpTitle, $epPos[0], $epPos[1], $epPos[2], $epPos[3]))
                    ExitLoop
                EndIf
            EndIf
        EndIf
        _Log("方式2: 轮询" & $poll2 & "/5")
    Next
EndIf

; 方式3兜底: 动态检测新出现的TkTopLevel窗口(不依赖标题)
If $hEp = 0 Then
    _Log("方式1/2未找到，尝试方式3: 动态检测新窗口...")
    For $poll3 = 1 To 5
        Sleep(2000)
        Local $aAllWins3 = WinList("[CLASS:TkTopLevel]")
        For $ewi3 = 1 To $aAllWins3[0][0]
            Local $hEW3 = $aAllWins3[$ewi3][1]
            ; 排除主窗口
            If $hEW3 = $hWin Then ContinueLoop
            ; 排除弹窗
            If $hPopup <> 0 And $hEW3 = $hPopup Then ContinueLoop
            ; 排除之前已存在的窗口
            Local $bPreExists = False
            For $preI = 1 To $aPreWins[0][0]
                If $hEW3 = $aPreWins[$preI][1] Then
                    $bPreExists = True
                    ExitLoop
                EndIf
            Next
            If $bPreExists Then ContinueLoop
            ; 检查窗口尺寸(EP选择窗口通常 >200x150)
            Local $aEP3 = WinGetPos($hEW3)
            If IsArray($aEP3) And $aEP3[2] > 200 And $aEP3[3] > 150 Then
                $hEp = $hEW3
                $epPos = $aEP3
                $sEpTitle = $aAllWins3[$ewi3][0]
                ExitLoop
            EndIf
        Next
        If $hEp <> 0 Then
            _Log(StringFormat("方式3: 轮询%d次找到新窗口 '%s' (%d,%d) %dx%d", $poll3, $sEpTitle, $epPos[0], $epPos[1], $epPos[2], $epPos[3]))
            ExitLoop
        EndIf
        _Log("方式3: 轮询" & $poll3 & "/5, 无新窗口")
    Next
EndIf

If $hEp = 0 Then
    _Log("未找到企业项目窗口，跳过")
Else
    WinActivate($hEp)
    Sleep(1000)
    WinSetOnTop($hEp, "", 1)
    Sleep(500)
    WinActivate($hEp)
    Sleep(2000)
    ; 等待 EP 窗口渲染稳定（防止高分辨率下窗口尺寸未定型就取坐标）
    Local $aEpStable = _WinStabilize($hEp)
    If IsArray($aEpStable) Then $epPos = $aEpStable
    _Log(StringFormat("EP窗口: (%d,%d) %dx%d", $epPos[0], $epPos[1], $epPos[2], $epPos[3]))

    ; ============================================================
    ; 步骤 9a-9g: 展开下拉→DOWN→Enter遍历→读EP文本→匹配目标
    ; ============================================================

    ; 9a: 点击下拉箭头展开列表
    _Log("9a: 点击下拉箭头 rel=(" & $EP_ARROW_X & "," & $EP_ARROW_Y & ")")
    WinActivate($hEp)
    Sleep(500)
    MouseClick("left", $epPos[0] + _S($EP_ARROW_X), $epPos[1] + _S($EP_ARROW_Y), 1, 3)
    Sleep(2000)

    ; 9b: 找 popdown 窗口
    _Log("9b: 查找 popdown 窗口...")
    Local $hPop = 0, $popPos = 0
    Local $aWins2 = WinList("[CLASS:TkTopLevel]")
    _Log("TkTopLevel 窗口数: " & $aWins2[0][0])
    For $wi = 1 To $aWins2[0][0]
        Local $sWT = $aWins2[$wi][0]
        Local $hWT = $aWins2[$wi][1]
        Local $aWP = WinGetPos($hWT)
        If IsArray($aWP) Then
            _Log(StringFormat("  [%d] '%s' (%d,%d) %dx%d", $wi, $sWT, $aWP[0], $aWP[1], $aWP[2], $aWP[3]))
            If $sWT = "popdown" Then
                $hPop = $hWT
                $popPos = $aWP
                _Log("  -> 找到popdown (by title)")
                ExitLoop
            EndIf
        EndIf
    Next

    ; 没找到popdown标题的，找小窗口兜底(句柄排除优先, 标题排除兜底)
    If $hPop = 0 Then
        For $wi = 1 To $aWins2[0][0]
            Local $sWT = $aWins2[$wi][0]
            Local $hWT = $aWins2[$wi][1]
            ; 句柄排除: 跳过主窗口和EP窗口(不依赖标题)
            If $hWT = $hWin Or $hWT = $hEp Then ContinueLoop
            Local $aWP = WinGetPos($hWT)
            If IsArray($aWP) Then
                ; 尺寸筛选: popdown是小窗口(高度50~400)
                If $aWP[3] > 50 And $aWP[3] < 400 Then
                    $hPop = $hWT
                    $popPos = $aWP
                    _Log(StringFormat("  -> 选为popdown: '%s' (%d,%d) %dx%d", $sWT, $aWP[0], $aWP[1], $aWP[2], $aWP[3]))
                    ExitLoop
                EndIf
            EndIf
        Next
    EndIf

    ; 9c: 展开→DOWN→Enter 遍历 EP 列表
    Local $bEpSelected = False

    If $hPop = 0 Then
        _Log("WARNING: 未找到 popdown 窗口，将使用 default 企业项目")
    Else
        _Log(StringFormat("popdown: (%d,%d) %dx%d", $popPos[0], $popPos[1], $popPos[2], $popPos[3]))

        ; 9c: 展开→点击item[0]→读→展开→DOWN→Enter→读→...
        _Log("9c: 展开+DOWN+Enter 遍历...")
        Local $sLastRead = ""

        For $i = 0 To $EP_MAX_ITEMS - 1
            If $i = 0 Then
                ; 第一次: popdown已展开(9a/9b)，直接点击第一项
                _Log("  i=0: 点击第一项 (popdown已展开)")
                MouseClick("left", $popPos[0] + _S(10), $popPos[1] + _S(10), 1, 3)
                Sleep(500)
            Else
                ; 后续: 展开下拉 → DOWN → Enter
                _Log("  i=" & $i & ": 展开→DOWN→Enter")
                WinActivate($hEp)
                Sleep(300)
                MouseClick("left", $epPos[0] + _S($EP_ARROW_X), $epPos[1] + _S($EP_ARROW_Y), 1, 3)
                Sleep(2000)
                ; DOWN 到下一项（展开后 Listbox 自动获得焦点）
                Send("{DOWN}")
                Sleep(500)
                ; Enter 确认选中，popdown 关闭
                Send("{ENTER}")
                Sleep(500)
            EndIf

            ; 读 EP 文本框
            WinActivate($hEp)
            Sleep(300)
            MouseClick("left", $epPos[0] + _S($EP_TEXT_X), $epPos[1] + _S($EP_TEXT_Y), 1, 2)
            Sleep(300)
            Send("^a")
            Sleep(200)
            ClipPut("")
            Send("^c")
            Sleep(300)
            Local $sRead = ClipGet()
            $sRead = StringStripWS($sRead, 3)
            _Log(StringFormat("  item[%d] = [%s]", $i, $sRead))

            If StringLen($sRead) = 0 Then
                _Log("  读到空值，到底了")
                ExitLoop
            EndIf
            If $i > 0 And $sRead = $sLastRead Then
                _Log("  与上一项相同，到底了")
                ExitLoop
            EndIf
            $sLastRead = $sRead

            If _MatchEp($sRead, $g_EP) Then
                _Log("  [OK] 匹配目标企业项目: " & $sRead)
                $bEpSelected = True
                ExitLoop
            EndIf
        Next

        If Not $bEpSelected Then
            _Log("WARNING: 遍历全部项未找到匹配目标 '" & $g_EP & "'，回到 default")
            ; 展开 → UP回到最顶端(default) → Enter 选中
            WinActivate($hEp)
            Sleep(300)
            MouseClick("left", $epPos[0] + _S($EP_ARROW_X), $epPos[1] + _S($EP_ARROW_Y), 1, 3)
            Sleep(2000)
            ; UP 回到最顶端（多按几次确保到顶）
            For $upI = 1 To 15
                Send("{UP}")
                Sleep(100)
            Next
            Sleep(500)
            Send("{ENTER}")
            Sleep(500)
            _Log("  已回到 default (UP×15+Enter)")
        EndIf
    EndIf

    If $bEpSelected Then
        _Log("=== 企业项目选择成功 ===")
    Else
        _Log("=== 企业项目未选中目标，使用 default/当前项 ===")
    EndIf

    ; 9f: 点击确定
    Sleep(1000)
    If WinExists($hEp) Then
        WinActivate($hEp)
        Sleep(500)
    EndIf
    _Log("9f: 点击确定 rel=(" & $EP_BTN_X & "," & $EP_BTN_Y & ")")
    MouseClick("left", $epPos[0] + _S($EP_BTN_X), $epPos[1] + _S($EP_BTN_Y), 1, 3)
    Sleep(3000)

    If WinExists($hEp) Then
        _Log("窗口仍在，重试确定")
        WinActivate($hEp)
        Sleep(500)
        MouseClick("left", $epPos[0] + _S($EP_BTN_X), $epPos[1] + _S($EP_BTN_Y), 1, 3)
        Sleep(2000)
    EndIf

    If WinExists($hEp) Then
        _Log("EP窗口仍存在，按Enter")
        Send("{ENTER}")
        Sleep(2000)
    Else
        _Log("EP窗口已关闭")
    EndIf

    ; 9g: 校验 — 读 SmsAgent_Info.log 检查 "selected enterprise project:"
    Sleep(3000)
    Local $sEpLogPath = $g_InstallDir & "\Logs\SmsAgent_Info.log"
    If FileExists($sEpLogPath) Then
        Local $hEpLogFile = FileOpen($sEpLogPath, 0)
        FileSetPos($hEpLogFile, $iLogOffset, 0)
        Local $iEpNewBytes = FileGetSize($sEpLogPath) - $iLogOffset
        Local $sEpLogContent = FileRead($hEpLogFile, $iEpNewBytes)
        FileClose($hEpLogFile)
        Local $aEpLines = StringSplit($sEpLogContent, @CRLF)
        Local $sLastEp = ""
        For $eli = $aEpLines[0] To 1 Step -1
            If StringInStr($aEpLines[$eli], "selected enterprise project:") Then
                Local $sEpPart = StringRegExpReplace($aEpLines[$eli], "^.*selected enterprise project:\s*", "")
                $sLastEp = StringStripWS($sEpPart, 3)
            EndIf
        Next
        If StringLen($sLastEp) > 0 And _MatchEp($sLastEp, $g_EP) Then
            _Log("9g: [OK] 校验通过! 企业项目=" & $sLastEp & " (匹配目标: " & $g_EP & ")")
        ElseIf StringLen($sLastEp) > 0 Then
            _Log("9g: [X] 校验失败! 选中=" & $sLastEp & " 期望=" & $g_EP)
        Else
            _Log("9g: [X] 校验失败! 企业项目为空")
        EndIf
    Else
        _Log("9g: 日志不存在，无法校验")
    EndIf

EndIf

; 步骤 10: 验证状态
_Log("步骤 10: 验证启动状态")
If ProcessExists("SMS-Agent.exe") Then
    _Log("SMS-Agent.exe 进程正在运行")
Else
    _Log("警告: SMS-Agent.exe 未检测到")
EndIf
Sleep(5000)
If ProcessExists("SMS-Agent-cmd.exe") Then
    _Log("SMS-Agent-cmd.exe 已启动")
Else
    _Log("警告: SMS-Agent-cmd.exe 未检测到")
EndIf

; 步骤 11: 多标记日志检测注册成功
_Log("步骤 11: 等待注册成功（多标记检测，只看新增日志），最小化到托盘")
Local $bRegistered = False
Local $sLogPath11 = $g_InstallDir & "\Logs\SmsAgent_Info.log"

Local $aMarkers[5] = [ _
    "check ak/sk info success", _
    "successfully upload os info", _
    "Success to upload system info", _
    "start schedule task", _
    "start heart beat" _
]
Local $aMarkerFound[5] = [False, False, False, False, False]

For $iWait = 1 To 40
    Sleep(2000)
    If FileExists($sLogPath11) Then
        Local $iCurSize = FileGetSize($sLogPath11)
        Local $iNewBytes = $iCurSize - $iLogOffset
        If $iNewBytes > 0 Then
            Local $hLog11 = FileOpen($sLogPath11, 0)
            FileSetPos($hLog11, $iLogOffset, 0)
            Local $sNewLog = FileRead($hLog11, $iNewBytes)
            FileClose($hLog11)

            Local $iFoundCount = 0
            For $mi = 0 To 4
                If Not $aMarkerFound[$mi] And StringInStr($sNewLog, $aMarkers[$mi]) Then
                    $aMarkerFound[$mi] = True
                    _Log("  [OK] 检测到: " & $aMarkers[$mi])
                EndIf
                If $aMarkerFound[$mi] Then $iFoundCount += 1
            Next

            If $aMarkerFound[1] And $aMarkerFound[2] And $iFoundCount >= 3 Then
                _Log(StringFormat("注册成功! 命中 %d/5 标记 (新增日志 %d 字节)", $iFoundCount, $iNewBytes))
                $bRegistered = True
                ExitLoop
            EndIf

            If $aMarkerFound[0] And $aMarkerFound[4] Then
                _Log(StringFormat("注册成功(AK/SK+心跳)! 命中 %d/5 标记", $iFoundCount))
                $bRegistered = True
                ExitLoop
            EndIf
        EndIf
    EndIf
    _Log("等待注册... (" & ($iWait * 2) & "s)")
Next

_Log("--- 注册标记汇总 ---")
For $mi = 0 To 4
    If $aMarkerFound[$mi] Then
        _Log("  [OK] " & $aMarkers[$mi])
    Else
        _Log("  [X]  " & $aMarkers[$mi])
    EndIf
Next

; 步骤 11b: 检查错误日志
_Log("步骤 11b: 检查错误日志 SmsAgent_Error.log")
Local $sErrLogPath = $g_InstallDir & "\Logs\SmsAgent_Error.log"
Local $bHasError = False
If FileExists($sErrLogPath) Then
    Local $hErrLog = FileOpen($sErrLogPath, 0)
    Local $sErrContent = FileRead($hErrLog)
    FileClose($hErrLog)
    Local $iErrLen = StringLen($sErrContent)
    If $iErrLen > 10 Then
        _Log("  错误日志有内容, 长度: " & $iErrLen & " 字节")
        Local $aErrLines = StringSplit($sErrContent, @CRLF)
        Local $iErrTotal = $aErrLines[0]
        Local $iStart = $iErrTotal - 4
        If $iStart < 1 Then $iStart = 1
        For $ei = $iStart To $iErrTotal
            Local $sErrLine = StringStripWS($aErrLines[$ei], 3)
            If StringLen($sErrLine) > 0 Then
                _Log("  [ERROR] " & StringLeft($sErrLine, 200))
            EndIf
        Next
        $bHasError = True
    Else
        _Log("  错误日志为空或无有效内容")
    EndIf
Else
    _Log("  错误日志不存在（正常，表示无错误）")
EndIf

If $bHasError And Not $bRegistered Then
    _Log("  警告: 错误日志有内容且注册未成功，请检查错误日志")
ElseIf $bHasError And $bRegistered Then
    _Log("  注意: 注册已成功但错误日志有历史内容（可能是早期重试记录）")
EndIf

; 取消主窗口置顶
WinSetOnTop($hWin, "", 0)
_Log("主窗口已取消置顶")

; 步骤 12: 最小化到托盘
If $bRegistered Then
    _Log("步骤 12: 注册成功，开始最小化到托盘")
    Sleep(5000)

    ; 优先用步骤1的窗口句柄(标题可能已变但句柄不变)
    Local $hWinMin = 0
    If $hWin <> 0 And WinExists($hWin) Then
        $hWinMin = $hWin
        _Log("步骤12: 使用步骤1的窗口句柄(标题无关)")
    EndIf
    ; 回退: 按标题查找(中英文)
    If $hWinMin = 0 Then $hWinMin = WinGetHandle("运行中")
    If $hWinMin = 0 Then $hWinMin = WinGetHandle("Running")
    If $hWinMin = 0 Then $hWinMin = WinGetHandle("SMS-Agent")
    ; 最后回退: 按进程查找 TkTopLevel 大窗口
    If $hWinMin = 0 Then
        Local $aWins12 = WinList("[CLASS:TkTopLevel]")
        _Log("步骤12: 标题未匹配, TkTopLevel窗口数: " & $aWins12[0][0])
        For $wi12 = 1 To $aWins12[0][0]
            Local $hW12 = $aWins12[$wi12][1]
            Local $aP12 = WinGetPos($hW12)
            If IsArray($aP12) And $aP12[2] > 300 And $aP12[3] > 300 Then
                $hWinMin = $hW12
                _Log("步骤12: 通过TkTopLevel找到大窗口: '" & $aWins12[$wi12][0] & "' (" & $aP12[2] & "x" & $aP12[3] & ")")
                ExitLoop
            EndIf
        Next
    EndIf
    If $hWinMin <> 0 Then
        Local $aPos12 = WinGetPos($hWinMin)
        _Log(StringFormat("找到主窗口(句柄/标题): (%d,%d) %dx%d", $aPos12[0], $aPos12[1], $aPos12[2], $aPos12[3]))

        _Log("WinSetState @SW_MINIMIZE")
        WinActivate($hWinMin)
        Sleep(500)
        WinSetState($hWinMin, "", @SW_MINIMIZE)
        Sleep(2000)

        Local $iState12 = WinGetState($hWinMin)
        If BitAND($iState12, 16) Then
            _Log("窗口已最小化到任务栏")
        ElseIf BitAND($iState12, 2) Then
            _Log("SW_MINIMIZE 未生效，点击隐藏按钮")
            $aPos12 = WinGetPos($hWinMin)
            Local $iBtnX = $aPos12[0] + _S(418)
            Local $iBtnY = $aPos12[1] + _S(558)
            _Log(StringFormat("点击隐藏按钮: 绝对(%d,%d)", $iBtnX, $iBtnY))
            WinActivate($hWinMin)
            Sleep(500)
            MouseClick("left", $iBtnX, $iBtnY, 1, 3)
            Sleep(2000)
            _Log("已点击隐藏按钮")
        Else
            _Log("窗口已不可见")
        EndIf
    Else
        _Log("未找到主窗口(句柄/标题/TkTopLevel)，可能已在托盘状态")
    EndIf

    If ProcessExists("SMS-Agent.exe") Then
        _Log("SMS-Agent.exe 进程运行中（托盘状态正常）")
    Else
        _Log("警告: SMS-Agent.exe 进程未检测到")
    EndIf
Else
    _Log("警告: 80秒内未检测到足够的注册成功标记")
    _Log("请手动检查日志: " & $g_InstallDir & "\\Logs\\SmsAgent_Info.log")
EndIf

    _Log("CONFIG_COMPLETE")
_Log("===== 配置完成 =====")
Exit(0)
