#!/usr/bin/env python3
"""
SMS 主机迁移 - 迁移前检查脚本

读取迁移主机列表 JSON，执行以下检查：
1. 网络连通性（ping + 端口 22/8900/8899）
2. 源端资源水位（CPU < 80%，可用内存 > 256MB）
3. 磁盘合规性（数量 ≤ 23，Linux 单盘 ≤ 16TB）
4. OS 兼容性及源端 OS/目的端镜像版本一致性
5. 高危操作扫描（并发数、源端数量等）

用法:
    python3 pre_migration_check.py --input migration_hosts.json 
"""

import argparse
import json
import os
import socket
import subprocess
import sys
from datetime import datetime

# ──────────────────────────────────────────────
# SMS 支持的操作系统列表（简化版，基于官方兼容性列表）
# ──────────────────────────────────────────────
SUPPORTED_OS = {
    "linux": [
        "centos 6", "centos 7", "centos 8", "centos stream",
        "red hat enterprise linux 6", "red hat enterprise linux 7",
        "red hat enterprise linux 8", "red hat enterprise linux 9",
        "oracle linux 6", "oracle linux 7", "oracle linux 8", "oracle linux 9",
        "suse linux enterprise server 11", "suse linux enterprise server 12",
        "suse linux enterprise server 15",
        "ubuntu server 12", "ubuntu server 14", "ubuntu server 16",
        "ubuntu server 18", "ubuntu server 20", "ubuntu server 22",
        "ubuntu server 23", "ubuntu server 24",
        "debian gnu/linux 8", "debian gnu/linux 9", "debian gnu/linux 10",
        "debian gnu/linux 11", "debian gnu/linux 12",
        "fedora 23", "fedora 24", "fedora 25", "fedora 26", "fedora 27",
        "fedora 28", "fedora 29", "fedora 30", "fedora 31", "fedora 32",
        "fedora 33", "fedora 34", "fedora 35", "fedora 36", "fedora 37",
        "fedora 38", "fedora 39",
        "euleros 2",
        "amazon linux 2", "amazon linux 2018", "amazon linux 2023",
        "alibaba cloud linux 3",
        "openeuler", "hce",
    ],
    "windows": [
        "windows server 2008", "windows server 2008 r2",
        "windows 7", "windows 8.1", "windows 10", "windows 11",
        "windows server 2012", "windows server 2012 r2",
        "windows server 2016", "windows server 2019",
        "windows server 2022", "windows server 2025",
    ],
}

# SMS 迁移限制常量
MAX_SOURCE_SERVERS = 1000       # 单用户源端服务器上限
MAX_CONCURRENT_MIGRATIONS = 200  # 最大并发迁移数
MAX_DISK_COUNT = 23             # 最大磁盘数量（ECS 24 - 1 代理磁盘）
MAX_DISK_SIZE_TB = 16           # Linux 最大单盘容量
CPU_USAGE_THRESHOLD = 80        # CPU 占用率阈值 (%)
MIN_AVAILABLE_MEMORY_MB = 256   # 最小可用内存
SMS_DEFAULT_PORT = 443          # SMS 服务端点 HTTPS 端口


# ──────────────────────────────────────────────
# 检查结果数据结构
# ──────────────────────────────────────────────
class CheckResult:
    def __init__(self, name, passed, detail="", severity="info"):
        self.name = name
        self.passed = passed
        self.detail = detail
        self.severity = severity  # info / warning / error

    def __str__(self):
        icon = "✅" if self.passed else ("🔴" if self.severity == "error" else "🟡")
        return f"  {icon} {self.name}: {self.detail}"


def check_network_connectivity(ip, ports, timeout=3):
    """检查 IP 可达性和端口连通性"""
    results = []

    # ping 检查
    try:
        ping_cmd = ["ping", "-c", "1", "-W", str(timeout), ip]
        ret = subprocess.run(ping_cmd, capture_output=True, timeout=timeout + 2)
        if ret.returncode == 0:
            results.append(CheckResult("Ping 可达性", True, f"{ip} 可达"))
        else:
            results.append(CheckResult("Ping 可达性", False, f"{ip} 不可达", "error"))
    except Exception as e:
        results.append(CheckResult("Ping 可达性", False, f"ping 异常: {e}", "error"))

    # 端口检查
    for port in ports:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((ip, port))
            sock.close()
            if result == 0:
                results.append(CheckResult(f"端口 {port}", True, f"{ip}:{port} 开放"))
            else:
                results.append(CheckResult(
                    f"端口 {port}", False,
                    f"{ip}:{port} 未开放 (返回码 {result})",
                    "error"
                ))
        except Exception as e:
            results.append(CheckResult(
                f"端口 {port}", False, f"端口检查异常: {e}", "error"
            ))

    return results



def check_sms_endpoint(endpoint, timeout=3):
    """检查源端是否能连接 SMS 服务端点。"""
    if not endpoint:
        return CheckResult("SMS 服务端点", False, "未提供 SMS 服务端点，无法验证源端到 SMS 的访问能力", "warning")
    host, port = endpoint, SMS_DEFAULT_PORT
    if isinstance(endpoint, dict):
        host = endpoint.get("host") or endpoint.get("address") or endpoint.get("domain")
        port = endpoint.get("port", SMS_DEFAULT_PORT)
    if not host:
        return CheckResult("SMS 服务端点", False, "SMS 服务端点为空", "warning")
    try:
        with socket.create_connection((host, int(port)), timeout=timeout):
            return CheckResult("SMS 服务端点", True, f"{host}:{port} 可连接")
    except Exception as e:
        return CheckResult("SMS 服务端点", False, f"{host}:{port} 不可连接: {e}", "error")


def check_disk_inventory(host, disks):
    """核对磁盘数量、挂载/初始化状态及分区信息。"""
    results = []
    source = host.get("source", {})
    expected = source.get("expected_disk_count") or source.get("excel_disk_count") or host.get("expected_disk_count")
    actual = len(disks)
    if expected is None:
        results.append(CheckResult("Excel 磁盘数量核对", False, f"已发现 {actual} 块，但输入未提供 Excel 中的源端磁盘数量", "warning"))
    elif actual == int(expected):
        results.append(CheckResult("Excel 磁盘数量核对", True, f"现场 {actual} 块 = Excel {expected} 块"))
    else:
        results.append(CheckResult("Excel 磁盘数量核对", False, f"现场 {actual} 块 ≠ Excel {expected} 块", "error"))
    for i, disk in enumerate(disks, 1):
        name = disk.get("name") or disk.get("device") or f"磁盘 {i}"
        mounted, initialized = disk.get("mounted"), disk.get("initialized")
        if mounted is False or initialized is False:
            results.append(CheckResult(f"{name} 挂载/初始化", False, "磁盘未挂载或未初始化，可能不会被迁移", "error"))
        elif mounted is True and initialized is True:
            results.append(CheckResult(f"{name} 挂载/初始化", True, "已挂载且已初始化"))
        else:
            results.append(CheckResult(f"{name} 挂载/初始化", False, "未提供 mounted/initialized 状态，请在源端通过 lsblk 或 fdisk -l 确认", "warning"))
        if "partitions" not in disk:
            results.append(CheckResult(f"{name} 分区信息", False, "未提供分区信息，请在源端通过 lsblk 或 fdisk -l 记录", "warning"))
        else:
            results.append(CheckResult(f"{name} 分区信息", True, f"已记录 {len(disk.get('partitions') or [])} 个分区"))
    return results


def check_runtime_resources(host):
    """检查 CPU、可用内存，并记录源端规格。"""
    results = []
    source = host.get("source", {})
    cpu = source.get("cpu_usage_percent")
    if cpu is None:
        results.append(CheckResult("CPU 占用率", False, "未提供实时 CPU 占用率，请在源端确认 < 80%", "warning"))
    elif float(cpu) < CPU_USAGE_THRESHOLD:
        results.append(CheckResult("CPU 占用率", True, f"{cpu}% < {CPU_USAGE_THRESHOLD}%"))
    else:
        results.append(CheckResult("CPU 占用率", False, f"{cpu}% ≥ {CPU_USAGE_THRESHOLD}%", "error"))
    memory = source.get("available_memory_mb")
    if memory is None:
        results.append(CheckResult("可用内存", False, "未提供实时可用内存，请在源端确认 > 256MB", "warning"))
    elif float(memory) > MIN_AVAILABLE_MEMORY_MB:
        results.append(CheckResult("可用内存", True, f"{memory}MB > {MIN_AVAILABLE_MEMORY_MB}MB"))
    else:
        results.append(CheckResult("可用内存", False, f"{memory}MB ≤ {MIN_AVAILABLE_MEMORY_MB}MB", "error"))
    cores, size, os_name = source.get("cpu_cores"), source.get("memory_gb"), source.get("os", "unknown")
    if cores is not None and size is not None:
        results.append(CheckResult("源端规格记录", True, f"CPU {cores} 核，内存 {size}GB，OS {os_name}"))
    else:
        results.append(CheckResult("源端规格记录", False, "未完整提供 CPU 核数、内存大小或 OS 版本，请在源端记录", "warning"))
    return results


def check_os_target_match(host):
    """检查源端 OS 与目的端镜像版本是否一致。"""
    source, target = host.get("source", {}), host.get("target", {})
    source_os = source.get("os")
    target_os = target.get("image_os") or target.get("os") or target.get("image_version") or host.get("target_image_os")
    if not source_os or not target_os:
        return CheckResult("源端 OS/目的端镜像", False, "未同时提供源端 OS 和目的端镜像版本，无法确认一致", "warning")
    normalize = lambda v: " ".join(str(v).lower().replace("-", " ").split())
    if normalize(source_os) == normalize(target_os):
        return CheckResult("源端 OS/目的端镜像", True, f"{source_os} = {target_os}")
    return CheckResult("源端 OS/目的端镜像", False, f"源端 {source_os} ≠ 目的端 {target_os}", "error")


def check_network_type(host):
    """检查 VPN/专线/EIP 网络类型及公网迁移配置。"""
    network_type = host.get("network_type") or host.get("network", {}).get("type")
    sms, normalized = host.get("sms", {}), str(network_type or "").strip().lower()
    if normalized in {"vpn", "专线", "dedicated line", "dedicated_line", "vpn或者专线"}:
        configured = sms.get("network_type") or sms.get("template_network_type")
        if configured and str(configured).lower() not in {"private", "私网"}:
            return CheckResult("网络类型", False, f"{network_type} 应配置为私网，当前为 {configured}", "error")
        return CheckResult("网络类型", True, f"{network_type} → 私网")
    if normalized in {"eip", "公网", "public", "public_ip"}:
        if sms.get("use_public_ip") is not True:
            return CheckResult("网络类型", False, "EIP 网络必须配置 use_public_ip=true", "error")
        eip = sms.get("existing_eip") or host.get("existing_eip")
        if not eip:
            return CheckResult("网络类型", False, "未提供已有 EIP；需通知用户准备，禁止 Agent 新建 EIP", "warning")
        return CheckResult("网络类型", True, f"EIP → 公网，使用已有 EIP {eip}")
    return CheckResult("网络类型", False, "网络类型未明确，必须为 VPN/专线或 EIP", "error")
def check_disk_compliance(disks, os_type):
    """检查磁盘合规性"""
    results = []

    # 磁盘数量
    disk_count = len(disks)
    if disk_count <= MAX_DISK_COUNT:
        results.append(CheckResult(
            "磁盘数量", True,
            f"{disk_count} 块 (限制 ≤ {MAX_DISK_COUNT})"
        ))
    else:
        results.append(CheckResult(
            "磁盘数量", False,
            f"{disk_count} 块超过限制 {MAX_DISK_COUNT}，无法迁移",
            "error"
        ))

    # 磁盘大小（仅 Linux 有 16TB 限制）
    if os_type == "linux":
        for i, disk in enumerate(disks):
            size_gb = disk.get("size_gb", 0)
            size_tb = size_gb / 1024
            if size_tb > MAX_DISK_SIZE_TB:
                results.append(CheckResult(
                    f"磁盘 {i} 容量", False,
                    f"{size_tb:.1f}TB 超过 Linux 限制 {MAX_DISK_SIZE_TB}TB",
                    "error"
                ))
            else:
                results.append(CheckResult(
                    f"磁盘 {i} 容量", True,
                    f"{size_gb}GB ({size_tb:.1f}TB ≤ {MAX_DISK_SIZE_TB}TB)"
                ))

    return results


def check_os_compatibility(os_name, os_type):
    """检查操作系统是否在 SMS 支持列表内"""
    os_lower = os_name.lower()
    supported_list = SUPPORTED_OS.get(os_type, [])

    for supported in supported_list:
        if supported in os_lower:
            return CheckResult(
                "OS 兼容性", True,
                f"{os_name} 在 SMS 支持列表内"
            )

    return CheckResult(
        "OS 兼容性", False,
        f"{os_name} 不在 SMS 已知支持列表内，请手动确认兼容性",
        "warning"
    )


def check_resource_limits(host):
    """检查源端资源水位（基于输入中声明的规格）"""
    results = []

    # CPU 核数检查（迁移要求 > 1U）
    cpu_cores = host.get("source", {}).get("cpu_cores", 0)
    if cpu_cores >= 1:
        results.append(CheckResult(
            "CPU 核数", True,
            f"{cpu_cores} 核 (要求 ≥ 1)"
        ))
    else:
        results.append(CheckResult(
            "CPU 核数", False,
            f"{cpu_cores} 核不满足最低要求 1 核",
            "error"
        ))

    # 内存检查（迁移要求 > 1G）
    memory_gb = host.get("source", {}).get("memory_gb", 0)
    if memory_gb >= 1:
        results.append(CheckResult(
            "内存大小", True,
            f"{memory_gb}GB (要求 ≥ 1GB)"
        ))
    else:
        results.append(CheckResult(
            "内存大小", False,
            f"{memory_gb}GB 不满足最低要求 1GB",
            "error"
        ))

    return results


def check_high_risk_conditions(hosts):
    """扫描整个输入列表中是否触发高危操作条件"""
    results = []

    # H-16: 并发迁移数检查
    total_hosts = len(hosts)
    if total_hosts > MAX_CONCURRENT_MIGRATIONS:
        results.append(CheckResult(
            "H-16 并发迁移数", False,
            f"{total_hosts} 台超过并发限制 {MAX_CONCURRENT_MIGRATIONS} 台",
            "error"
        ))
    else:
        results.append(CheckResult(
            "H-16 并发迁移数", True,
            f"{total_hosts} 台 (限制 ≤ {MAX_CONCURRENT_MIGRATIONS} 台)"
        ))

    # H-17: 源端服务器总数检查
    if total_hosts > MAX_SOURCE_SERVERS:
        results.append(CheckResult(
            "H-17 源端服务器总数", False,
            f"{total_hosts} 台超过源端数量限制 {MAX_SOURCE_SERVERS} 台",
            "error"
        ))
    else:
        results.append(CheckResult(
            "H-17 源端服务器总数", True,
            f"{total_hosts} 台 (限制 ≤ {MAX_SOURCE_SERVERS} 台)"
        ))

    return results


def run_pre_check(input_file):
    """执行迁移前检查主流程"""
    # 读取输入
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            hosts = json.load(f)
    except FileNotFoundError:
        print(f"❌ 输入文件不存在: {input_file}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"❌ JSON 解析失败: {e}")
        sys.exit(1)

    if not isinstance(hosts, list) or len(hosts) == 0:
        print("❌ 输入文件应为非空的迁移主机数组")
        sys.exit(1)

    print("=" * 70)
    print(f"  SMS 主机迁移 - 迁移前检查报告")
    print(f"  生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  输入文件: {input_file}")
    print(f"  主机数量: {len(hosts)}")
    print("=" * 70)

    all_passed = True
    has_errors = False

    # 全局高危操作检查
    print("\n📋 全局高危操作扫描:")
    print("-" * 50)
    for r in check_high_risk_conditions(hosts):
        print(r)
        if not r.passed:
            all_passed = False
            if r.severity == "error":
                has_errors = True

    # 逐主机检查
    for host in hosts:
        host_id = host.get("id", "unknown")
        source = host.get("source", {})
        os_type = source.get("os_type", "linux")
        os_name = source.get("os", "unknown")
        source_ip = source.get("ip", "")
        disks = source.get("disks", [])

        # 网络端口配置
        net = host.get("network", {})
        ssh_port = net.get("source_ssh_port", source.get("ssh_port", 22))
        ports = [ssh_port]

        print(f"\n🖥️  主机 {host_id} ({source.get('hostname', 'N/A')}):")
        print(f"    源端 IP: {source_ip} | OS: {os_name} | 类型: {os_type}")
        print("-" * 50)

        # 1. 网络连通性
        print("  📡 网络连通性检查:")
        for r in check_network_connectivity(source_ip, ports):
            print(r)
            if not r.passed:
                all_passed = False
                if r.severity == "error":
                    has_errors = True

        # 2. SMS 服务端点与网络类型
        endpoint = host.get("sms", {}).get("endpoint") or host.get("sms_endpoint")
        for r in [check_sms_endpoint(endpoint), check_network_type(host)]:
            print(r)
            if not r.passed:
                all_passed = False
                if r.severity == "error":
                    has_errors = True

        # 3. 资源水位
        print("  💻 资源规格检查:")
        for r in check_runtime_resources(host):
            print(r)
            if not r.passed:
                all_passed = False
                if r.severity == "error":
                    has_errors = True

        # 4. 磁盘清单与挂载状态
        print("  📋 磁盘清单检查:")
        for r in check_disk_inventory(host, disks):
            print(r)
            if not r.passed:
                all_passed = False
                if r.severity == "error":
                    has_errors = True

        # 5. 磁盘合规性
        print("  💽 磁盘合规性检查:")
        for r in check_disk_compliance(disks, os_type):
            print(r)
            if not r.passed:
                all_passed = False
                if r.severity == "error":
                    has_errors = True

        # 6. OS 兼容性
        print("  🐧 操作系统兼容性检查:")
        r = check_os_compatibility(os_name, os_type)
        print(r)
        if not r.passed:
            all_passed = False
            if r.severity == "error":
                has_errors = True

        # 7. 源端 OS 与目的端镜像一致性
        r = check_os_target_match(host)
        print(r)
        if not r.passed:
            all_passed = False
            if r.severity == "error":
                has_errors = True

    # 总结
    print("\n" + "=" * 70)
    if has_errors:
        print("  ❌ 检查未通过 — 存在 error 级别问题，请修复后再执行迁移")
        print("  ⚠️  请同时遵守 SKILL.md 中的「禁止执行的高危操作列表」")
        print("  📌 特别提醒 H-06: 迁移过程中源端只允许读操作，禁止任何增删改")
    elif not all_passed:
        print("  🟡 检查通过但有警告 — 请确认 warning 项后再执行迁移")
    else:
        print("  ✅ 检查全部通过 — 可以执行迁移")
        print("  ⚠️  迁移过程中请遵守 SKILL.md 中的「禁止执行的高危操作列表」")
        print("  📌 特别提醒 H-06: 迁移过程中源端只允许读操作，禁止任何增删改")
    print("=" * 70)

    return 0 if all_passed else 1


def main():
    parser = argparse.ArgumentParser(
        description="SMS 主机迁移 - 迁移前检查"
    )
    parser.add_argument(
        "--input", "-i", required=True,
        help="迁移主机列表 JSON 文件路径"
    )
    args = parser.parse_args()
    sys.exit(run_pre_check(args.input))


if __name__ == "__main__":
    main()
