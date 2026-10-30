; compile_au3.au3 — 用 AutoIt3.exe 调 Aut2Exe (绕过 GUI 挂起)
; CmdLine[1] = aut2exe 路径
; CmdLine[2] = 输入 au3 路径
; CmdLine[3] = 输出 exe 路径
; CmdLine[4] = 标记文件路径 (编译完成后创建)

If $CmdLine[0] < 4 Then
    ConsoleWrite("Usage: compile_au3.au3 <aut2exe> <in.au3> <out.exe> <done_marker>" & @CRLF)
    Exit(1)
EndIf

Local $sAut2Exe = $CmdLine[1]
Local $sIn = $CmdLine[2]
Local $sOut = $CmdLine[3]
Local $sDone = $CmdLine[4]

; 删除旧 exe
FileDelete($sOut)

; 用 RunWait 调 Aut2Exe (AutoIt 的 RunWait 能正确处理 GUI 程序)
Local $sCmd = '"' & $sAut2Exe & '" /in "' & $sIn & '" /out "' & $sOut & '" /nopack'
ConsoleWrite("Running: " & $sCmd & @CRLF)

Local $iRet = RunWait($sCmd, "", @SW_HIDE)
ConsoleWrite("Aut2Exe returned: " & $iRet & @CRLF)

; 检查 exe 是否生成
If FileExists($sOut) Then
    ; 写标记文件
    Local $hFile = FileOpen($sDone, 2)
    FileWriteLine($hFile, "COMPILE_OK")
    FileClose($hFile)
    ConsoleWrite("Compile OK: " & $sOut & @CRLF)
    Exit(0)
Else
    ConsoleWrite("Compile FAIL: exe not found" & @CRLF)
    Exit(1)
EndIf
