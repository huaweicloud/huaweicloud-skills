#!/usr/bin/env python3
"""
源端数据盘准备工具（独立脚本，不触碰 Agent 配置/启动脚本）。

用途：给源端 Windows 主机新挂载的 EVS 裸盘建分区、分配盘符、格式化为 NTFS，
     并（可选）以正确工作目录干净重启 SMS Agent 以触发重新采集磁盘拓扑。

设计：
  - 连接参数从 config/migrate.yaml 的 source 段读取（零硬编码）
  - 只操作指定/自动发现的"新数据盘"，绝不触碰现有系统盘
  - 不修改 Agent 的任何配置/计划任务；Agent 重启使用 Start-Process + WorkingDirectory
  - 本操作与正常迁移流程解耦，属独立运维脚本（源端测试数据盘不在迁移范围内）

用法:
  python3 scripts/source_data_disk.py --config config/migrate.yaml \
      --disk 1 --letter D --size-gb 40 --restart-agent
  # --disk 省略时按 size-gb 自动发现"无分区且容量匹配"的盘
  # 不加 --restart-agent 则只建分区，不重启 Agent
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import winrm

PROJECT_ROOT = Path(__file__).parent.parent
DEFAULT_CONFIG = PROJECT_ROOT / "config" / "migrate.yaml"


def load_source(config_path: str) -> dict:
    import yaml
    with open(config_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}
    src = cfg.get("source", {}) or {}
    need = ["host", "username", "password"]
    missing = [k for k in need if not src.get(k)]
    if missing:
        raise SystemExit(f"配置缺少 source 字段: {missing}")
    return src


def ps(session, script: str) -> str:
    r = session.run_ps(script)
    return ((r.std_out or b"") + (r.std_err or b"")).decode("gbk", errors="replace")


def find_target_disk(session, size_gb: int) -> int:
    """自动发现目标盘：无分区且容量 <= size_gb+1GB 的物理盘。"""
    out = ps(session, """
$target = Get-Disk | Where-Object {
    ($_.Size -gt 1GB) -and
    (-not (Get-Partition -DiskNumber $_.Number -ErrorAction SilentlyContinue))
} | Select-Object -First 1
if ($target) { Write-Output ('DISK=' + $target.Number) } else { Write-Output 'DISK=NONE' }
""")
    for line in out.splitlines():
        line = line.strip()
        if line.startswith("DISK="):
            v = line.split("=", 1)[1]
            return int(v) if v != "NONE" else -1
    return -1


def prepare_data_disk(session, disk_number: int, letter: str, size_gb: int) -> str:
    script = f"""
$n = {disk_number}
$d = Get-Disk -Number $n
if (-not $d) {{ Write-Output 'ERR: disk not found'; exit 1 }}
Write-Output ('DISK_INFO: ' + $d.FriendlyName + ' ' + $d.Size + ' ' + $d.PartitionStyle + ' ' + $d.OperationalStatus)
Set-Disk -Number $n -IsOffline $false -ErrorAction SilentlyContinue
if ($d.PartitionStyle -eq 'RAW') {{ Initialize-Disk -Number $n -PartitionStyle MBR }}
$existing = Get-Partition -DiskNumber $n -ErrorAction SilentlyContinue
if (-not $existing) {{
    $p = New-Partition -DiskNumber $n -UseMaximumSize
    # 如果指定盘符被占用，取下一个空闲盘符
    $wanted = '{letter}'
    if (Get-Volume -DriveLetter $wanted -ErrorAction SilentlyContinue) {{
        $used = (Get-Volume | Where-Object {{ $_.DriveLetter }}).DriveLetter
        $wanted = ((65..90) | ForEach-Object {{ [char]$_ }} | Where-Object {{ $_ -notin $used }} | Select-Object -First 1)
    }}
    Set-Partition -PartitionNumber $p.PartitionNumber -NewDriveLetter $wanted
    Format-Volume -Partition $p -FileSystem NTFS -NewFileSystemLabel DATA -Confirm:$false | Out-Null
    Write-Output ('PARTITION_READY: ' + $wanted + ': NTFS')
}} else {{
    $e = $existing | Select-Object -First 1
    $vol = Get-Volume -Partition $e -ErrorAction SilentlyContinue
    if ($vol -and $vol.FileSystem -ne 'NTFS') {{
        Format-Volume -Partition $e -FileSystem NTFS -NewFileSystemLabel DATA -Confirm:$false | Out-Null
        Write-Output ('PARTITION_REFORMATED: ' + $e.DriveLetter + ': NTFS')
    }} else {{
        Write-Output ('PARTITION_EXISTS: letter=' + $e.DriveLetter)
    }}
}}
Get-Partition -DiskNumber $n | Format-Table -AutoSize | Out-String
"""
    out = ps(session, script)
    return out


def restart_agent(session, install_dir: str, agent_exe: str) -> str:
    """干净重启 SMS Agent：正确 WorkingDirectory，不碰配置与计划任务。

    install_dir / agent_exe 由命令行注入（--install-dir / --agent-exe），
    不再硬编码 C:\SMS-Agent-Py3，支持自定义安装目录。
    """
    exe_path = f"{install_dir}\\{agent_exe}"
    script = f"""
$exe = '{exe_path}'
if (-not (Test-Path $exe)) {{ Write-Output 'ERR: agent exe not found'; exit 1 }}
$running = Get-Process -Name 'SMS-Agent' -ErrorAction SilentlyContinue
if ($running) {{ $running | Stop-Process -Force; Start-Sleep -Seconds 3 }}
Start-Process -FilePath $exe -WorkingDirectory '{install_dir}' -WindowStyle Hidden
Start-Sleep -Seconds 5
$alive = Get-Process -Name 'SMS-Agent' -ErrorAction SilentlyContinue
if ($alive) {{ Write-Output ('AGENT_STARTED pid=' + $alive.Id) }} else {{ Write-Output 'AGENT_START_FAILED' }}
"""
    return ps(session, script)


def main():
    ap = argparse.ArgumentParser(description="源端数据盘准备（独立脚本，不碰 Agent 配置）")
    ap.add_argument("--config", default=str(DEFAULT_CONFIG), help="migrate.yaml 路径")
    ap.add_argument("--disk", type=int, default=-1, help="磁盘编号（如 1）；缺省自动发现")
    ap.add_argument("--letter", default="D", help="盘符（默认 D）")
    ap.add_argument("--size-gb", type=int, default=40, help="数据盘容量 GB（自动发现用，默认 40）")
    ap.add_argument("--restart-agent", action="store_true", help="分区后干净重启 Agent 触发重新采集")
    ap.add_argument("--install-dir", default=r"C:\SMS-Agent-Py3", help="SMS-Agent 安装目录（默认 C:\\SMS-Agent-Py3）")
    ap.add_argument("--agent-exe", default="SMS-Agent.exe", help="Agent 主程序名（默认 SMS-Agent.exe）")
    args = ap.parse_args()

    src = load_source(args.config)
    session = winrm.Session(
        f"http://{src['host']}:{src.get('winrm_port', 5985)}/wsman",
        auth=(src["username"], src["password"]),
        transport=src.get("winrm_transport", "ntlm"),
    )

    disk = args.disk
    if disk < 0:
        disk = find_target_disk(session, args.size_gb)
        if disk < 0:
            print("自动发现失败：未找到无分区的数据盘（请用 --disk 显式指定）")
            return 2

    print(f"[1/2] 准备数据盘 Disk {disk} ...")
    for line in prepare_data_disk(session, disk, args.letter, args.size_gb).splitlines():
        if line.strip():
            print("  " + line.strip()[:140])

    if args.restart_agent:
        print("[2/2] 干净重启 SMS Agent（正确工作目录）...")
        for line in restart_agent(session, args.install_dir, args.agent_exe).splitlines():
            if line.strip():
                print("  " + line.strip()[:140])
        print("提示：等待 1~3 分钟后用 ShowServer 复查磁盘拓扑（应出现 2 块盘）")
    else:
        print("未重启 Agent（未加 --restart-agent）")

    return 0


if __name__ == "__main__":
    sys.exit(main())