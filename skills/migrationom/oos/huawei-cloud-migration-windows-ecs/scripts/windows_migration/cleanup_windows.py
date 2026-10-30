"""
清理源端 Windows 环境上的迁移残留程序和文件。
通过 WinRM 连接源端，依次清理：
  1. 计划任务 ConfigureSMSAgent / ConfigureSMSAgentPy2 / SMSAgentWatchdog
  2. SMS-Agent 进程 + 安装目录（Py3: C:\SMS-Agent-Py3, Py2: C:\SMS-Agent-Py2）
  3. AutoIt 进程 + 安装目录 C:\Program Files (x86)\AutoIt3 [仅 Py3]
  4. 源端工作目录（从 source_base_dir 配置读取）
  5. 相关注册表项（卸载入口、Run/RunOnce 自启动、SMSAgentDeploy 服务注册）

为什么必须先清理：残留的 `sms_domain.txt` 会让 Py2 Agent 交互错位（注册时被问 “use last time?” 而非直接要 domain）；残留的计划任务/进程/安装目录会干扰新一轮注册，造成 `invalid AK or SK` 或“假成功未注册”。本工具幂等，源端干净时重跑也无副作用。

连接地址和路径从 config/migrate.yaml 读取（零硬编码）：
  公网: source.host + source.winrm_port
  私网: proxy_server.host + proxy_server.gost_listen_port

清理目标根据 sms_agent.agent_version 动态选择：
  py3: 清理 SMS-Agent.exe 进程 + C:\SMS-Agent-Py3 + AutoIt
  py2: 清理 agent-start.exe 进程 + C:\SMS-Agent-Py2（无 AutoIt）
"""
import argparse
import sys
import time
from pathlib import Path

import yaml
import winrm

# 项目根目录
PROJECT_ROOT = Path(__file__).parent
DEFAULT_CONFIG = PROJECT_ROOT / "config" / "migrate.yaml"


def build_cleanup_commands(agent_version: str = "py3",
                           install_dir: str = "C:\\SMS-Agent-Py3",
                           agent_exe_name: str = "SMS-Agent.exe",
                           source_base_dir: str = "C:\\auto_agent_opt",
                           source_download_dir: str = "C:\\auto_agent_opt\\downloads") -> list:
    """
    根据 agent_version 构建清理命令列表。

    Py3: 清理 SMS-Agent.exe + AutoIt + C:\SMS-Agent-Py3
    Py2: 清理 agent-start.exe + C:\SMS-Agent-Py2（无 AutoIt）
    """
    is_py2 = agent_version == "py2"

    # 从安装目录名推导卸载注册表项名（如 C:\SMS-Agent-Py2 -> SMS-Agent-Py2）
    # 同时作为服务名和注册表搜索关键词
    uninstall_key = install_dir.split("\\")[-1] if "\\" in install_dir else install_dir

    commands = [
        ("删除计划任务 ConfigureSMSAgent",
         'schtasks /delete /tn ConfigureSMSAgent /f 2>nul & echo DONE'),

        ("删除计划任务 ConfigureSMSAgentPy2",
         'schtasks /delete /tn ConfigureSMSAgentPy2 /f 2>nul & echo DONE'),

        ("删除计划任务 SMSAgentWatchdog",
         'schtasks /delete /tn SMSAgentWatchdog /f 2>nul & echo DONE'),

        (f"终止 SMS-Agent 进程 ({agent_exe_name})",
         f'taskkill /f /im {agent_exe_name} 2>nul & taskkill /f /im SmsAgent.exe 2>nul & taskkill /f /im SMSAgentDeploy.exe 2>nul & echo DONE'),

        ("终止 agent-start.exe 残留进程",
         "wmic process where \"name='cmd.exe' and commandline like '%%agent-start%%'\" call terminate 2>nul & echo DONE"),

        ("终止 Console session 残留 cmd.exe 窗口",
         'taskkill /f /im cmd.exe /fi "SESSION eq 1" 2>nul & echo DONE'),

        (f"删除 SMS-Agent 安装目录 {install_dir}",
         f'if exist "{install_dir}" (rmdir /s /q "{install_dir}" & echo DELETED) else (echo NOT_FOUND)'),
    ]

    if not is_py2:
        # Py3 独有: AutoIt 清理
        commands.extend([
            ("终止 AutoIt 进程",
             'taskkill /f /im AutoIt3.exe 2>nul & taskkill /f /im Au3Info.exe 2>nul & echo DONE'),

            ("删除 AutoIt 安装目录",
             'if exist "C:\\Program Files (x86)\\AutoIt3" (rmdir /s /q "C:\\Program Files (x86)\\AutoIt3" & echo DELETED) else (echo NOT_FOUND)'),

            ("删除 AutoIt 卸载注册表项 (WOW64)",
             'reg delete "HKLM\\SOFTWARE\\WOW6432Node\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\AutoItv3" /f 2>nul & echo DONE'),

            ("删除 AutoIt 卸载注册表项 (64-bit)",
             'reg delete "HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\AutoItv3" /f 2>nul & echo DONE'),

            ("清除 AutoIt 用户级卸载注册表项",
             'reg delete "HKCU\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\AutoItv3" /f 2>nul & echo DONE'),
        ])

    commands.extend([
        (f"删除源端工作目录 {source_base_dir}",
         f'if exist "{source_base_dir}" (rmdir /s /q "{source_base_dir}" & echo DELETED) else (echo NOT_FOUND)'),

        (f"删除源端下载目录 {source_download_dir} (安装包缓存)",
         f'if exist "{source_download_dir}" (rmdir /s /q "{source_download_dir}" & echo DELETED) else (echo NOT_FOUND)'),

        ("清理 SMS-Agent 相关临时文件",
         'del /f /q "%USERPROFILE%\\Desktop\\SMS-Agent*" 2>nul & del /f /q "%TEMP%\\SMS-Agent*" 2>nul & echo DONE'),

        ("删除 SMS-Agent 卸载注册表项 (WOW6432Node)",
         f'reg delete "HKLM\\SOFTWARE\\WOW6432Node\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\{uninstall_key}" /f 2>nul & echo DONE'),

        ("删除 SMS-Agent 卸载注册表项 (64-bit)",
         f'reg delete "HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\{uninstall_key}" /f 2>nul & echo DONE'),

        ("清理 REQUESTS_CA_BUNDLE 系统环境变量 (Py2 TLS 残留)",
         'reg delete "HKLM\\SYSTEM\\CurrentControlSet\\Control\\Session Manager\\Environment" /v REQUESTS_CA_BUNDLE /f 2>nul & echo DONE'),

        ("清理 REQUESTS_CA_BUNDLE 用户环境变量 (Py2 TLS 残留)",
         'reg delete "HKCU\\Environment" /v REQUESTS_CA_BUNDLE /f 2>nul & echo DONE'),

        ("清理 Run/RunOnce 自启动项 (HKLM)",
         'reg delete "HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Run" /v SMSAgentDeploy /f 2>nul '
         '& reg delete "HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Run" /v SMS-Agent /f 2>nul '
         '& reg delete "HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\RunOnce" /v SMSAgentDeploy /f 2>nul '
         '& reg delete "HKLM\\SOFTWARE\\WOW6432Node\\Microsoft\\Windows\\CurrentVersion\\Run" /v SMSAgentDeploy /f 2>nul '
         '& reg delete "HKLM\\SOFTWARE\\WOW6432Node\\Microsoft\\Windows\\CurrentVersion\\RunOnce" /v SMSAgentDeploy /f 2>nul '
         '& echo DONE'),

        ("删除 SMSAgentDeploy Windows 服务注册",
         'sc delete SMSAgentDeploy 2>nul & sc query SMSAgentDeploy 2>nul & echo DONE'),

        ("清理 HKLM\\SOFTWARE 下 SMS-Agent 相关注册表键",
         f'reg delete "HKLM\\SOFTWARE\\{uninstall_key}" /f 2>nul '
         f'& reg delete "HKLM\\SOFTWARE\\WOW6432Node\\{uninstall_key}" /f 2>nul '
         '& echo DONE'),

        ("验证清理结果",
         f'if exist "{install_dir}" (echo SMS_AGENT_DIR_STILL_EXISTS) else (echo SMS_AGENT_DIR_CLEAN) '
         f'& if exist "{source_base_dir}" (echo WORKDIR_STILL_EXISTS) else (echo WORKDIR_CLEAN) '
         f'& reg query "HKLM\\SOFTWARE\\WOW6432Node\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\{uninstall_key}" 2>nul && (echo REG_UNINSTALL_STILL_EXISTS) || (echo REG_UNINSTALL_CLEAN)'),
    ])

    return commands





def load_connection_config(config_path: Path) -> tuple:
    """从 migrate.yaml 读取 WinRM 连接参数 + agent 版本信息。

    返回: (host, port, username, password, agent_version, install_dir, agent_exe_name)
    """
    with open(config_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    scenario = cfg.get("scenario", "public")
    source = cfg.get("source", {})
    username = source.get("username", "Administrator")
    password = source.get("password", "")

    if scenario == "private":
        proxy = cfg.get("proxy_server", {})
        host = proxy.get("host", "")
        port = proxy.get("gost_listen_port", 15985)
    else:
        host = source.get("host", "")
        port = source.get("winrm_port", 5985)

    sa = cfg.get("sms_agent", {})
    agent_version = sa.get("agent_version", "py3")
    install_dir = sa.get("install_dir", "C:\\SMS-Agent-Py3")
    agent_exe_name = sa.get("agent_exe_name", "SMS-Agent.exe")

    source_base_dir = cfg.get("source_base_dir", "C:\\auto_agent_opt")

    source_download_dir = (
        cfg.get("download", {}).get("source_download_dir", "")
        or f"{source_base_dir}\\downloads"
    )

    return (host, port, username, password, agent_version, install_dir,
            agent_exe_name, source_base_dir, source_download_dir)


def cleanup_source_winrm(config_path: Path) -> int:
    """通过 WinRM 清理源端迁移残留（连接参数来自 migrate.yaml，零硬编码）。

    供 cleanup_environment.py 编排复用；独立 CLI 入口保持等价（见 main）。
    """
    (host, port, username, password, agent_version, install_dir, agent_exe_name,
     source_base_dir, source_download_dir) = load_connection_config(config_path)

    print(f"配置: {config_path}")
    print(f"连接源端 Windows: {host}:{port}")
    print(f"Agent 版本: {agent_version} (exe={agent_exe_name}, dir={install_dir})")
    endpoint = f"http://{host}:{port}/wsman"
    session = winrm.Session(
        target=endpoint,
        auth=(username, password),
        transport="ntlm",
    )

    # 测试连接
    try:
        r = session.run_cmd("echo CONNECTION_OK")
        if r.status_code != 0 or b"CONNECTION_OK" not in r.std_out:
            print("ERROR: WinRM 连接失败")
            return 1
        print(f"✅ WinRM 连接成功: {host}:{port}")
    except Exception as e:
        print(f"ERROR: 无法连接 WinRM: {e}")
        return 1

    # 根据版本构建清理命令
    cleanup_commands = build_cleanup_commands(
        agent_version, install_dir, agent_exe_name, source_base_dir, source_download_dir)

    print(f"\n{'=' * 60}")
    print(f"开始清理源端 Windows 环境 (Agent 版本: {agent_version})")
    print(f"{'=' * 60}\n")

    all_ok = True
    for desc, cmd in cleanup_commands:
        print(f"▶ {desc}")
        try:
            r = session.run_cmd(cmd)
            stdout = r.std_out.decode("gbk", errors="replace").strip() if r.std_out else ""
            stderr = r.std_err.decode("gbk", errors="replace").strip() if r.std_err else ""
            if r.status_code == 0:
                print(f"  → {stdout if stdout else 'OK'}")
            else:
                print(f"  → 警告: {stderr if stderr else stdout}")
                # 非致命错误，继续
        except Exception as e:
            print(f"  → 错误: {e}")
            all_ok = False
        time.sleep(0.5)

    print(f"\n{'=' * 60}")
    print("清理完成" + (" (全部成功)" if all_ok else " (有警告，可继续)"))
    print(f"{'=' * 60}")
    # 清理脚本不阻断后续迁移，恒返回 0；all_ok 仅用于日志汇总
    return 0


def main():
    ap = argparse.ArgumentParser(description="源端残留清理（WinRM 远程执行，幂等可重复）")
    ap.add_argument("config", nargs="?", default=None, help="migrate.yaml 路径")
    ap.add_argument("--config", dest="config_flag", default="", help="migrate.yaml 路径（与位置参数等价）")
    args = ap.parse_args()
    config_path = Path(args.config_flag or args.config or DEFAULT_CONFIG)
    if not config_path.is_absolute():
        config_path = PROJECT_ROOT / config_path
    return cleanup_source_winrm(config_path)


if __name__ == "__main__":
    sys.exit(main())
