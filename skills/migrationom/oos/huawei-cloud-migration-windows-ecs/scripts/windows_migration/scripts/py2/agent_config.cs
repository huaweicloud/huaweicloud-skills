using System;
using System.Diagnostics;
using System.IO;
using System.Runtime.InteropServices;
using System.Text;
using System.Collections.Generic;

class AgentConfig {
    [StructLayout(LayoutKind.Sequential)]
    struct KEY_EVENT_RECORD {
        public int bKeyDown; public ushort wRepeatCount;
        public ushort wVirtualKeyCode; public ushort wVirtualScanCode;
        public char UnicodeChar; public uint dwControlKeyState;
    }
    [StructLayout(LayoutKind.Explicit)]
    struct INPUT_RECORD {
        [FieldOffset(0)] public ushort EventType;
        [FieldOffset(4)] public KEY_EVENT_RECORD KeyEvent;
    }
    [StructLayout(LayoutKind.Sequential)]
    struct COORD { public short X; public short Y; }
    [StructLayout(LayoutKind.Sequential)]
    struct SMALL_RECT { public short Left; public short Top; public short Right; public short Bottom; }
    [StructLayout(LayoutKind.Sequential)]
    struct CONSOLE_SCREEN_BUFFER_INFO {
        public COORD dwSize; public COORD dwCursorPosition;
        public ushort wAttributes; public SMALL_RECT srWindow;
        public COORD dwMaximumWindowSize;
    }
    [DllImport("kernel32.dll")] static extern bool FreeConsole();
    [DllImport("kernel32.dll")] static extern bool AttachConsole(uint dwProcessId);
    [DllImport("kernel32.dll")] static extern IntPtr GetStdHandle(uint nStdHandle);
    [DllImport("kernel32.dll", SetLastError=true)]
    static extern bool WriteConsoleInput(IntPtr h, INPUT_RECORD[] buf, uint n, out uint written);
    [DllImport("kernel32.dll")] static extern bool GetConsoleScreenBufferInfo(IntPtr h, out CONSOLE_SCREEN_BUFFER_INFO info);
    [DllImport("kernel32.dll", SetLastError=true, CharSet=CharSet.Unicode)]
    static extern bool ReadConsoleOutputCharacterW(IntPtr h, StringBuilder buf, uint n, COORD coord, out uint read);
    [DllImport("kernel32.dll")] static extern bool SetConsoleOutputCP(uint cp);
    [DllImport("kernel32.dll")] static extern bool SetConsoleCP(uint cp);
    [DllImport("kernel32.dll")] static extern uint GetConsoleOutputCP();
    [DllImport("kernel32.dll")] static extern IntPtr GetConsoleWindow();
    [DllImport("user32.dll")] static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);

    // ===== Parameters set from command-line args =====
    static string ak = "";
    static string sk = "";
    static string domain = "";
    static string targetEp = "";
    static string agentExe = "";
    static string logFile = "";
    static string agentLog = "";
    static string certPath = "";

    static void Log(string msg) {
        File.AppendAllText(logFile, DateTime.Now.ToString("HH:mm:ss") + " - " + msg + "\r\n", Encoding.UTF8);
    }

    static Dictionary<string, string> ParseArgs(string[] args) {
        Dictionary<string, string> dict = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
        for (int i = 0; i < args.Length - 1; i++) {
            string key = args[i];
            if (key.StartsWith("--") || key.StartsWith("-")) {
                string val = args[i + 1];
                if (!val.StartsWith("--") && !val.StartsWith("-")) {
                    dict[key.TrimStart('-').ToLower()] = val;
                    i++;
                }
            }
        }
        return dict;
    }

    static void PrintUsage() {
        Console.Error.WriteLine("agent_config.exe - SMS-Agent-Py2 interactive configurator");
        Console.Error.WriteLine("Usage: agent_config.exe --ak <AK> --sk <SK> --domain <sms_domain>");
        Console.Error.WriteLine("  --ep <enterprise_project>");
        Console.Error.WriteLine("  --agent-exe <path_to_agent-start.exe>");
        Console.Error.WriteLine("  --log <configure_log.txt_path>");
        Console.Error.WriteLine("  --agent-log <SmsAgent_Info.log_path>");
        Console.Error.WriteLine("  --cert <cacert.pem_path> (optional)");
    }

    static bool InitArgs(string[] args) {
        Dictionary<string, string> p = ParseArgs(args);

        if (!p.ContainsKey("ak") || !p.ContainsKey("sk") || !p.ContainsKey("domain")
            || !p.ContainsKey("ep") || !p.ContainsKey("agent-exe")
            || !p.ContainsKey("log") || !p.ContainsKey("agent-log")) {
            PrintUsage();
            return false;
        }

        ak = p["ak"];
        sk = p["sk"];
        domain = p["domain"];
        targetEp = p["ep"];
        agentExe = p["agent-exe"];
        logFile = p["log"];
        agentLog = p["agent-log"];
        certPath = p.ContainsKey("cert") ? p["cert"] : "";

        // Defensive check: on non-Chinese OS, if EP name contains non-ASCII
        // (Chinese) characters, the SMS Agent's internal Python 2 cannot parse
        // Chinese EP names from API JSON responses — it silently falls back to
        // EP ID 0 (default) anyway. So we proactively set EP to "default" to
        // avoid encoding corruption downstream. On Chinese OS, no change.
        bool isChineseOS = false;
        try {
            int lcid = System.Globalization.CultureInfo.InstalledUICulture.LCID;
            isChineseOS = (lcid == 2052 || lcid == 3076 || lcid == 1028);
        } catch { }

        if (!isChineseOS) {
            bool hasNonAscii = false;
            foreach (char c in targetEp) {
                if (c > 127) { hasNonAscii = true; break; }
            }
            if (hasNonAscii) {
                Log("WARNING: Non-Chinese OS + non-ASCII EP name '" + targetEp
                    + "' -> falling back to 'default'. Change EP via console/API after registration.");
                targetEp = "default";
            }
        }

        return true;
    }

    static INPUT_RECORD[] MakeInput(string text) {
        INPUT_RECORD[] r = new INPUT_RECORD[text.Length * 2 + 2];
        int i = 0;
        foreach (char c in text) { r[i++] = K(c, 1, 0); r[i++] = K(c, 0, 0); }
        r[i++] = K('\r', 1, 0x0D); r[i++] = K('\r', 0, 0x0D);
        return r;
    }
    static INPUT_RECORD K(char c, int d, ushort v) {
        INPUT_RECORD ir = new INPUT_RECORD();
        ir.EventType = 1; ir.KeyEvent.bKeyDown = d; ir.KeyEvent.wRepeatCount = 1;
        ir.KeyEvent.wVirtualKeyCode = v; ir.KeyEvent.wVirtualScanCode = 0;
        ir.KeyEvent.UnicodeChar = c; ir.KeyEvent.dwControlKeyState = 0;
        return ir;
    }
    static void WriteInput(IntPtr handle, string val) {
        // 安全: 不记录写入内容（可能含 AK/SK），仅记录长度
        Log("Writing value: (len=" + val.Length + ")");
        INPUT_RECORD[] records = MakeInput(val);
        uint written = 0;
        bool ok = WriteConsoleInput(handle, records, (uint)records.Length, out written);
        Log("Result: ok=" + ok + " written=" + written);
    }

    static string lastBufInfo = "";
    static string ReadConsoleText(IntPtr handle) {
        CONSOLE_SCREEN_BUFFER_INFO info;
        if (!GetConsoleScreenBufferInfo(handle, out info)) return "";
        short width = info.dwSize.X;
        // Log buffer info once or when it changes
        string bufInfo = "size=" + width + "x" + info.dwSize.Y
            + " cursor=(" + info.dwCursorPosition.X + "," + info.dwCursorPosition.Y + ")"
            + " win=L" + info.srWindow.Left + " T" + info.srWindow.Top
            + " R" + info.srWindow.Right + " B" + info.srWindow.Bottom;
        if (bufInfo != lastBufInfo) {
            Log("BufInfo: " + bufInfo);
            lastBufInfo = bufInfo;
        }
        // Read from buffer top (0) to cursor/visible bottom, skip leading empty lines
        short left = info.srWindow.Left;
        short winWidth = (short)(info.srWindow.Right - left + 1);
        short bottom = (short)Math.Max((int)info.srWindow.Bottom, (int)info.dwCursorPosition.Y);
        List<string> rawLines = new List<string>();
        for (short row = 0; row <= bottom; row++) {
            StringBuilder line = new StringBuilder(winWidth);
            COORD coord; coord.X = left; coord.Y = row;
            uint read;
            if (ReadConsoleOutputCharacterW(handle, line, (uint)winWidth, coord, out read) && read > 0)
                rawLines.Add(line.ToString().TrimEnd());
            else
                rawLines.Add("");
        }
        // Trim leading empty lines, keep trailing context
        int firstNonEmpty = 0;
        for (int i = 0; i < rawLines.Count; i++) {
            if (rawLines[i].Trim().Length > 0) { firstNonEmpty = i; break; }
        }
        StringBuilder sb = new StringBuilder();
        for (int i = firstNonEmpty; i < rawLines.Count; i++)
            sb.AppendLine(rawLines[i]);
        return sb.ToString();
    }

    static void TaskKill(string name) {
        try {
            ProcessStartInfo psi = new ProcessStartInfo("taskkill", "/f /t /im " + name);
            psi.UseShellExecute = false;
            psi.RedirectStandardOutput = true;
            psi.RedirectStandardError = true;
            psi.CreateNoWindow = true;
            Process p = Process.Start(psi);
            p.WaitForExit(10000);
            string output = (p.StandardOutput.ReadToEnd() + p.StandardError.ReadToEnd()).Trim();
            Log("taskkill " + name + ": " + (output.Length > 100 ? output.Substring(0, 100) : output));
        } catch (Exception ex) { Log("taskkill " + name + ": " + ex.Message); }
    }

    static void KillExisting() {
        int myPid = Process.GetCurrentProcess().Id;

        // 1. Kill agent processes (tree kill across all sessions)
        TaskKill("SMSAgentDeploy.exe");
        TaskKill("agent-start.exe");

        // Verify agent-start processes are gone (retry up to 3x)
        for (int k = 0; k < 3; k++) {
            Process[] remain = Process.GetProcessesByName("agent-start");
            if (remain.Length == 0) break;
            Log("agent-start still alive: " + remain.Length + ", retry kill...");
            TaskKill("agent-start.exe");
            System.Threading.Thread.Sleep(2000);
        }
        Process[] finalCheck = Process.GetProcessesByName("agent-start");
        Log("After kill: " + finalCheck.Length + " agent-start procs remaining");

        // 2. Kill previous agent_config.exe instances (not ourselves)
        try {
            Process[] prevConfigs = Process.GetProcessesByName("agent_config");
            int killed = 0;
            foreach (Process p in prevConfigs) {
                if (p.Id != myPid) { try { p.Kill(); p.WaitForExit(5000); killed++; } catch { } }
            }
            if (killed > 0) Log("Killed " + killed + " previous agent_config instances");
        } catch (Exception ex) { Log("Kill prev agent_config: " + ex.Message); }

        System.Threading.Thread.Sleep(1000);

        // 3. Kill residual cmd.exe windows (cross-session, from previous schtasks runs)
        //    On migration target servers, no interactive cmd sessions expected.
        //    Use taskkill /f /t to kill process tree. Safe: only targets cmd.exe
        //    spawned by Task Scheduler in Session 1, not Session 0 (WinRM).
        TaskKill("cmd.exe");
        System.Threading.Thread.Sleep(500);

        // 4. Kill residual conhost.exe (console window hosts from previous runs)
        TaskKill("conhost.exe");
        System.Threading.Thread.Sleep(2000);
    }

    static void BackupOldLogs() {
        try {
            string logDir = Path.GetDirectoryName(agentLog);
            if (!Directory.Exists(logDir)) return;
            string ts = DateTime.Now.ToString("yyyyMMdd_HHmmss");
            foreach (string f in Directory.GetFiles(logDir, "*.log")) {
                string newName = Path.GetFileNameWithoutExtension(f) + "_" + ts + ".log";
                File.Move(f, Path.Combine(logDir, newName));
                Log("Backup: " + Path.GetFileName(f) + " -> " + newName);
            }
        } catch (Exception ex) { Log("BackupOldLogs: " + ex.Message); }
    }

    static int CheckMarkers() {
        if (!File.Exists(agentLog)) return 0;
        try {
            string content = File.ReadAllText(agentLog, System.Text.Encoding.Default).ToLower();
            int count = 0;
            if (content.Contains("as/sk")) count++;
            if (content.Contains("upload os info")) count++;
            if (content.Contains("upload source info")) count++;
            if (content.Contains("schedule task")) count++;
            if (content.Contains("heart beat")) count++;
            return count;
        } catch { return 0; }
    }

    static void Main(string[] args) {
        if (!InitArgs(args)) {
            return;
        }

        File.WriteAllText(logFile, "");
        Log("===== START =====");
        Log("Params: agent-exe=" + agentExe + " cert=" + certPath + " ep=" + targetEp);
        try {
            KillExisting();
            BackupOldLogs();

            // === Launch + Attach with retry (max 3 rounds) ===
            IntPtr inHandle = IntPtr.Zero;
            IntPtr outHandle = IntPtr.Zero;
            bool attached = false;
            for (int round = 0; round < 3 && !attached; round++) {
                if (round > 0) {
                    Log("=== Retry round " + (round+1) + "/3: killing residuals and re-launching ===");
                    KillExisting();
                    System.Threading.Thread.Sleep(3000);
                }
                Log("Starting agent (round " + (round+1) + "/3)...");
                ProcessStartInfo psi = new ProcessStartInfo();
                psi.FileName = "cmd.exe";
                psi.Arguments = "/c \"" + agentExe + "\"";
                psi.WorkingDirectory = Path.GetDirectoryName(agentExe);
                psi.UseShellExecute = false;
                if (certPath.Length > 0) {
                    psi.EnvironmentVariables["REQUESTS_CA_BUNDLE"] = certPath;
                }
                Process proc = Process.Start(psi);
                Log("Agent PID: " + proc.Id + " (cmd wrapper)");

                Log("Waiting 8s for agent init...");
                System.Threading.Thread.Sleep(8000);

                for (int attempt = 0; attempt < 10; attempt++) {
                    Process[] agents = Process.GetProcessesByName("agent-start");
                    Log("Attach attempt " + (attempt+1) + ": " + agents.Length + " agent-start procs");
                    int bestPid = 0;
                    int bestNonEmpty = 0;
                    int bestCursorY = -1;
                    foreach (Process a in agents) {
                        FreeConsole();
                        try {
                            if (AttachConsole((uint)a.Id)) {
                                IntPtr tOut = GetStdHandle(0xFFFFFFF5u);
                                CONSOLE_SCREEN_BUFFER_INFO bi;
                                int curY = 0;
                                if (GetConsoleScreenBufferInfo(tOut, out bi)) curY = bi.dwCursorPosition.Y;
                                string ct = ReadConsoleText(tOut);
                                int nonEmpty = 0;
                                foreach (string ln in ct.Split(new string[] { "\r\n", "\n" }, StringSplitOptions.None))
                                    if (ln.Trim().Length > 0) nonEmpty++;
                                Log("  PID=" + a.Id + " curY=" + curY + " nonEmpty=" + nonEmpty + " last=" + (ct.Trim().Length > 0 ? ct.Trim().Substring(Math.Max(0, ct.Trim().Length-20)) : "(empty)"));
                                if (nonEmpty > 0 && curY > bestCursorY) {
                                    bestPid = a.Id;
                                    bestNonEmpty = nonEmpty;
                                    bestCursorY = curY;
                                }
                                FreeConsole();
                            }
                        } catch { }
                    }
                    if (bestPid > 0) {
                        FreeConsole();
                        if (AttachConsole((uint)bestPid)) {
                            inHandle = GetStdHandle(0xFFFFFFF6u);
                            outHandle = GetStdHandle(0xFFFFFFF5u);
                            Log("Attached to best PID=" + bestPid + " nonEmpty=" + bestNonEmpty);
                            attached = true;
                            break;
                        }
                    }
                    System.Threading.Thread.Sleep(2000);
                }
                if (!attached) {
                    Log("Round " + (round+1) + " failed: could not attach to any console");
                }
            }
            if (!attached) {
                Log("ERROR: Could not attach to any console after 3 rounds");
                Log("===== DONE =====");
                return;
            }

            // State machine: console-buffer-driven interaction
            int state = 0;
            int maxCycles = 300; // 300 * 2s = 10min max
            for (int cycle = 0; cycle < maxCycles; cycle++) {
                string consoleText = ReadConsoleText(outHandle);
                string lower = consoleText.ToLower();

                switch (state) {
                    case 0: // Wait for pre-check success, or skip if y/n already showing
                        if (lower.Contains("pre-check successfully") || lower.Contains("pre check successfully")
                            || lower.Contains("pre-check") || lower.Contains("check success")) {
                            Log("State 0->1: pre-check detected");
                            state = 1;
                        } else if (lower.Contains("(y/n)") || lower.Contains("do you agree") || lower.Contains("agree")) {
                            Log("State 0->1: skipping pre-check, y/n already visible");
                            state = 1;
                        }
                        break;

                    case 1: // Detect y/n prompt
                        if (lower.Contains("do you agree") || lower.Contains("(y/n)") || lower.Contains("agree") || lower.Contains("y/n")) {
                            Log("State 1->2: y/n prompt detected, sending y");
                            WriteInput(inHandle, "y");
                            state = 2;
                        }
                        break;

                    case 2: // Detect AK prompt
                        if (lower.Contains("input ak") || lower.Contains("please input ak")) {
                            Log("State 2->3: AK prompt detected, sending AK");
                            WriteInput(inHandle, ak);
                            state = 3;
                        }
                        break;

                    case 3: // Detect SK prompt
                        if (lower.Contains("input sk") || lower.Contains("please input sk")) {
                            Log("State 3->4: SK prompt detected, sending SK");
                            WriteInput(inHandle, sk);
                            state = 4;
                        }
                        break;

                    case 4: // Detect "use last time" Y/N or direct smsdomain input
                        if (lower.Contains("last time") && (lower.Contains("y/y") || lower.Contains("n/n") || lower.Contains("y/n"))) {
                            Log("State 4->8: 'use last time' prompt, sending N");
                            WriteInput(inHandle, "N");
                            state = 8;
                        } else if (lower.Contains("sms_domain") || lower.Contains("smsdomain") || lower.Contains("sms domain")) {
                            if (!lower.Contains("last time")) {
                                Log("State 4->5: smsdomain input prompt detected, sending domain");
                                WriteInput(inHandle, domain);
                                state = 5;
                            }
                        }
                        break;

                    case 8: // Wait for actual smsdomain input (after answering N to "use last time")
                        // Search full text for "new sms_domain" prompt (not last-line only)
                        if (lower.Contains("new sms_domain") || lower.Contains("new smsdomain") || lower.Contains("a new sms")) {
                            Log("State 8->5: 'Please enter a new sms_domain' detected");
                            WriteInput(inHandle, domain);
                            state = 5;
                        }
                        break;

                    case 5: // Detect EP selection prompt (after EP list fully printed)
                        if (lower.Contains("select an enterprise project") || lower.Contains("input index")) {
                            Log("State 5: EP selection prompt detected");
                            // Parse EP list from console text
                            int epIndex = ParseEPList(consoleText);
                            string epInput = epIndex.ToString();
                            Log("State 5->6: sending EP index: " + epInput);
                            WriteInput(inHandle, epInput);
                            state = 6;
                        }
                        break;

                    case 6: // Poll for registration markers
                        int markers = CheckMarkers();
                        Log("State 6: markers=" + markers + "/5");
                        if (markers >= 5) {
                            Log("All 5 markers found! Registration successful.");
                            // Minimize the console window so it does not block the desktop
                            try {
                                IntPtr hWnd = GetConsoleWindow();
                                if (hWnd != IntPtr.Zero) {
                                    ShowWindow(hWnd, 6); // SW_MINIMIZE
                                    Log("Console window minimized.");
                                }
                            } catch (Exception exw) { Log("Minimize window error: " + exw.Message); }
                            Log("===== DONE =====");
                            return;
                        }
                        break;
                }

                // Log debug info every 5 cycles
                if (cycle % 5 == 0) {
                    // Count non-empty lines and show last few
                    string[] allLines = consoleText.Split(new string[] { "\r\n", "\n" }, StringSplitOptions.None);
                    int nonEmpty = 0;
                    string lastNonEmpty = "";
                    foreach (string ln in allLines) {
                        if (ln.Trim().Length > 0) { nonEmpty++; lastNonEmpty = ln.Trim(); }
                    }
                    Log("Cycle " + cycle + " State=" + state + " lines=" + allLines.Length + " nonEmpty=" + nonEmpty + " last='" + (lastNonEmpty.Length > 80 ? lastNonEmpty.Substring(0, 80) : lastNonEmpty) + "'");
                }

                System.Threading.Thread.Sleep(2000);
            }

            // Timeout
            int finalMarkers = CheckMarkers();
            Log("TIMEOUT after " + maxCycles + " cycles. Final markers=" + finalMarkers + "/5");
            Log("===== DONE =====");

        } catch (Exception ex) {
            Log("FATAL: " + ex.Message + "\r\n" + ex.StackTrace);
            Log("===== DONE =====");
        }
    }

    static int ParseEPList(string consoleText) {
        Log("ParseEPList: target='" + targetEp + "'");

        // Extract ASCII prefix (chars before first non-ASCII) for matching
        string asciiTarget = "";
        foreach (char c in targetEp) {
            if (c < 128) asciiTarget += c;
            else break;
        }
        asciiTarget = asciiTarget.TrimEnd('(', '-', ' ', ')', ':');
        Log("ParseEPList: asciiTarget='" + asciiTarget + "'");

        string[] lines = consoleText.Split(new string[] { "\r\n", "\n" }, StringSplitOptions.None);

        // Find EP list region: between "current user in enterprise projects below:"
        // and "Select an enterprise project" / "input index"
        int listStart = -1;
        int listEnd = lines.Length;
        for (int i = 0; i < lines.Length; i++) {
            string l = lines[i].Trim().ToLower();
            if (listStart < 0 && l.Contains("current user") && l.Contains("enterprise project")) {
                listStart = i + 1;
                Log("  EP list start at line " + i + ": " + lines[i].Trim());
            }
            if (listStart >= 0 && (l.Contains("select an enterprise project") || l.Contains("input index"))) {
                listEnd = i;
                Log("  EP list end at line " + i);
                break;
            }
        }

        if (listStart < 0) {
            Log("  EP list start marker not found, dumping all non-empty lines:");
            for (int i = 0; i < lines.Length; i++) {
                string t = lines[i].Trim();
                if (t.Length > 0) Log("  L" + i + ": " + (t.Length > 100 ? t.Substring(0, 100) : t));
            }
            return 0;
        }

        // Enumerate EP entries between markers, skip header, match by full name then prefix
        // EP entry lines start with a digit (the actual EP index the user must input).
        // Continuation lines (wrapped EP names) do NOT start with a digit - skip them.
        for (int i = listStart; i < listEnd; i++) {
            string trimmed = lines[i].Trim();
            if (trimmed.Length == 0) continue;
            // Skip header line like "index id name"
            string tl = trimmed.ToLower();
            if (tl.Contains("index") && tl.Contains("name") && !char.IsDigit(trimmed[0])) continue;
            // Skip continuation lines (wrapped names) - only process lines starting with a digit
            if (!char.IsDigit(trimmed[0])) continue;

            // Parse the actual EP number from the start of the line
            string numStr = "";
            for (int j = 0; j < trimmed.Length && char.IsDigit(trimmed[j]); j++) {
                numStr += trimmed[j];
            }
            int epNum = 0;
            int.TryParse(numStr, out epNum);

            string display = trimmed.Length > 100 ? trimmed.Substring(0, 100) : trimmed;
            Log("  EP[" + epNum + "]: " + display);

            // 1. Try exact full name match (target and console garbling pattern is the same)
            if (tl.Contains(targetEp.ToLower())) {
                Log("  EXACT MATCH at epNum=" + epNum);
                return epNum;
            }
            // 2. Fallback: ASCII prefix match
            if (asciiTarget.Length > 3 && tl.Contains(asciiTarget.ToLower())) {
                Log("  PREFIX MATCH at epNum=" + epNum);
                return epNum;
            }
        }

        Log("  No match found, using default 0");
        return 0;
    }
}
