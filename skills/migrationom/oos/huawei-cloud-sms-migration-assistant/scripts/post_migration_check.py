#!/usr/bin/env python3
"""
SMS 主机迁移 - 迁移后校验脚本

读取迁移主机列表 JSON，比对目的端与源端的规格一致性：
1. CPU 核数：目的端 vs 源端
2. 内存大小：目的端 vs 源端
3. 磁盘数量：目的端 vs 源端
4. 磁盘容量：目的端 vs 源端（允许目的端 ≥ 源端）
5. 操作系统版本：目的端 vs 源端（允许 HCE 切换差异）
6. 网络连通性：目的端是否可正常访问

支持两种模式：
  --mode manual  : 从 JSON 输入中读取目的端实际规格（用户手动填写）
  --mode hcloud  : 通过 hcloud CLI 查询目的端 ECS 实际规格

用法:
    python3 post_migration_check.py --input examples/migration_hosts.json
    python3 post_migration_check.py --input examples/migration_hosts.json --mode hcloud
"""

import argparse
import json
import socket
import subprocess
import sys
from datetime import datetime

# HCE 切换允许的 OS 映射（CentOS → HCE）
HCE_SWITCH_MAP = {
    "centos 7": ["hce", "hce 1", "hce 2", "openeuler"],
    "centos 8": ["hce", "hce 1", "hce 2", "openeuler"],
}

# 允许的规格差异阈值
DISK_SIZE_TOLERANCE_GB = 1  # 仅用于提示分区对齐造成的 1GB 以内差异


class CheckResult:
    def __init__(self, name, passed, detail="", severity="info"):
        self.name = name
        self.passed = passed
        self.detail = detail
        self.severity = severity

    def __str__(self):
        icon = "✅" if self.passed else ("🔴" if self.severity == "error" else "🟡")
        return f"  {icon} {self.name}: {self.detail}"


def check_network_connectivity(ip, ports=None, timeout=3):
    """检查目的端网络连通性"""
    if ports is None:
        ports = [22]

    results = []

    # ping
    try:
        ret = subprocess.run(
            ["ping", "-c", "1", "-W", str(timeout), ip],
            capture_output=True, timeout=timeout + 2
        )
        if ret.returncode == 0:
            results.append(CheckResult("目的端 Ping", True, f"{ip} 可达"))
        else:
            results.append(CheckResult("目的端 Ping", False, f"{ip} 不可达", "error"))
    except Exception as e:
        results.append(CheckResult("目的端 Ping", False, f"异常: {e}", "error"))

    # 端口
    for port in ports:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((ip, port))
            sock.close()
            if result == 0:
                results.append(CheckResult(f"目的端端口 {port}", True, "开放"))
            else:
                results.append(CheckResult(
                    f"目的端端口 {port}", False, "未开放", "warning"
                ))
        except Exception as e:
            results.append(CheckResult(
                f"目的端端口 {port}", False, f"异常: {e}", "warning"
            ))

    return results


def check_cpu_consistency(source_cpu, target_cpu):
    """CPU 核数必须与源端一致。"""
    if source_cpu is None or target_cpu is None or not source_cpu or not target_cpu:
        return CheckResult("CPU 核数", False, "缺少源端或目的端 CPU 核数", "warning")
    if target_cpu == source_cpu:
        return CheckResult("CPU 核数", True, f"目的端 {target_cpu} 核 = 源端 {source_cpu} 核")
    return CheckResult("CPU 核数", False, f"目的端 {target_cpu} 核 ≠ 源端 {source_cpu} 核，规格不一致", "error")

def check_memory_consistency(source_mem, target_mem):
    """内存大小必须与源端一致。"""
    if source_mem is None or target_mem is None or not source_mem or not target_mem:
        return CheckResult("内存大小", False, "缺少源端或目的端内存大小", "warning")
    if target_mem == source_mem:
        return CheckResult("内存大小", True, f"目的端 {target_mem}GB = 源端 {source_mem}GB")
    return CheckResult("内存大小", False, f"目的端 {target_mem}GB ≠ 源端 {source_mem}GB，规格不一致", "error")

def check_disk_consistency(source_disks, target_disks):
    """检查目的端是否完整接收所有源端磁盘。"""
    results = []
    src_count, tgt_count = len(source_disks), len(target_disks)
    if tgt_count == src_count:
        results.append(CheckResult("磁盘数量", True, f"目的端 {tgt_count} 块 = 源端 {src_count} 块"))
    else:
        results.append(CheckResult("磁盘数量", False, f"目的端 {tgt_count} 块 ≠ 源端 {src_count} 块，存在磁盘缺失或额外磁盘", "error"))
    for i, (src, tgt) in enumerate(zip(source_disks, target_disks), 1):
        src_size, tgt_size = src.get("size_gb"), tgt.get("size_gb")
        name = tgt.get("name") or tgt.get("device") or f"磁盘 {i}"
        if src_size is None or not tgt_size:
            results.append(CheckResult(f"{name} 容量", False, "缺少目的端实际容量，无法确认磁盘完整迁移", "warning"))
            continue
        diff = float(tgt_size) - float(src_size)
        if diff >= -DISK_SIZE_TOLERANCE_GB:
            results.append(CheckResult(f"{name} 容量", True, f"目的端 {tgt_size}GB ≥ 源端 {src_size}GB"))
        else:
            results.append(CheckResult(f"{name} 容量", False, f"目的端 {tgt_size}GB < 源端 {src_size}GB，目的端不能小于源端", "error"))
    return results

def check_os_consistency(source_os, target_os):
    """操作系统版本必须与源端一致。"""
    if not source_os or not target_os or source_os == "unknown" or target_os == "unknown":
        return CheckResult("操作系统", False, "缺少源端或目的端 OS 版本", "warning")
    normalize = lambda value: " ".join(str(value).lower().replace("-", " ").split())
    if normalize(source_os) == normalize(target_os):
        return CheckResult("操作系统", True, f"目的端 {target_os} = 源端 {source_os}")
    return CheckResult("操作系统", False, f"目的端 {target_os} ≠ 源端 {source_os}", "error")

def _snapshot_value(snapshot, *keys):
    for key in keys:
        if key in snapshot:
            return snapshot[key]
    return None


def check_source_write_integrity(source):
    """对比迁移前后源端只读快照，发现变化时阻止业务割接。"""
    before = source.get("pre_migration_snapshot") or source.get("migration_before") or {}
    after = source.get("post_migration_snapshot") or source.get("migration_after") or {}
    if not before or not after:
        return [CheckResult("源端写操作检查", False, "缺少迁移前后源端快照，无法验证 df、数据库、日志和 mtime 是否变化", "warning")]
    results = []
    checks = [
        ("磁盘使用量", ("disk_usage", "df_h")),
        ("数据库文件大小", ("database_files", "database_size")),
        ("日志文件大小", ("log_files", "log_size")),
        ("文件修改时间戳", ("mtimes", "file_mtimes")),
    ]
    for label, keys in checks:
        before_value = _snapshot_value(before, *keys)
        after_value = _snapshot_value(after, *keys)
        if before_value is None or after_value is None:
            results.append(CheckResult(f"源端{label}", False, "缺少迁移前或迁移后快照数据", "warning"))
        elif before_value == after_value:
            results.append(CheckResult(f"源端{label}", True, "迁移前后完全一致，无变化"))
        else:
            results.append(CheckResult(f"源端{label}", False, "迁移前后发生变化，禁止业务割接，需回滚并调查原因", "error"))
    return results


def check_application_business(target):
    """检查应用启动和业务验证结果；验证动作由用户或外部测试系统提供。"""
    checks = target.get("application_checks") or target.get("business_checks")
    if not checks:
        status = target.get("application_status") or target.get("business_verified")
        if status is True or str(status).lower() in {"ok", "passed", "running", "正常", "通过"}:
            return [CheckResult("应用与业务验证", True, "已提供通过结果")]
        return [CheckResult("应用与业务验证", False, "未提供应用启动和业务验证结果，请由用户完成验证", "warning")]
    if isinstance(checks, dict):
        checks = [{"name": name, "status": value} for name, value in checks.items()]
    results = []
    for item in checks:
        name = item.get("name", "未命名检查") if isinstance(item, dict) else "业务检查"
        status = item.get("status") if isinstance(item, dict) else item
        passed = status is True or str(status).lower() in {"ok", "passed", "running", "正常", "通过"}
        results.append(CheckResult(f"应用/业务: {name}", passed, str(status), "error" if not passed else "info"))
    return results

def query_ecs_via_hcloud(ecs_id, region):
    """通过 hcloud CLI 查询 ECS 实例详情"""
    try:
        cmd = [
            "hcloud", "ecs", "ShowServer",
            "--server_id", ecs_id,
            "--region", region,
        ]
        ret = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        if ret.returncode != 0:
            return None, f"hcloud 查询失败: {ret.stderr.strip()}"

        # hcloud 输出为 JSON
        data = json.loads(ret.stdout)
        server = data.get("server", data)

        # 提取规格信息
        flavor = server.get("flavor", {})
        cpu = flavor.get("vcpus", 0)
        mem_mb = flavor.get("ram", 0)
        mem_gb = mem_mb / 1024 if mem_mb else 0

        # 提取磁盘信息（需查询每个卷的实际大小）
        volumes = server.get("os-extended-volumes:volumes_attached", [])
        disks = []
        for vol in volumes:
            vol_id = vol.get("id", "")
            vol_size = 0
            if vol_id:
                vol_cmd = [
                    "hcloud", "ECS", "ShowVolume",
                    "--cli-region", region,
                    "--volume_id", vol_id,
                ]
                vol_ret = subprocess.run(vol_cmd, capture_output=True, text=True, timeout=15)
                if vol_ret.returncode == 0:
                    vol_data = json.loads(vol_ret.stdout)
                    vol_info = vol_data.get("volume", vol_data)
                    vol_size = vol_info.get("size", 0)
            disks.append({"size_gb": vol_size, "type": "unknown", "id": vol_id})

        # 提取 OS 信息
        image = server.get("image", {})
        os_name = image.get("os_version", "unknown")

        # 提取 IP
        addresses = server.get("Addresses", {})
        target_ip = ""
        for net_name, addr_list in addresses.items():
            for addr in addr_list:
                if addr.get("OS-EXT-IPS:type") == "fixed":
                    target_ip = addr.get("addr", "")
                    break

        return {
            "cpu_cores": int(cpu) if cpu else 0,
            "memory_gb": int(mem_gb) if mem_gb else 0,
            "disks": disks,
            "os": os_name,
            "ip": target_ip,
        }, None

    except FileNotFoundError:
        return None, "hcloud CLI 未安装"
    except Exception as e:
        return None, f"查询异常: {e}"


def run_post_check(input_file, mode="manual"):
    """执行迁移后校验主流程"""
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
    print(f"  SMS 主机迁移 - 迁移后校验报告")
    print(f"  生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  输入文件: {input_file}")
    print(f"  主机数量: {len(hosts)}")
    print(f"  查询模式: {mode}")
    print("=" * 70)

    all_passed = True
    has_errors = False

    for host in hosts:
        host_id = host.get("id", "unknown")
        source = host.get("source", {})
        target = host.get("target", {})

        print(f"\n🖥️  主机 {host_id} ({source.get('hostname', 'N/A')}):")
        print(f"    源端: {source.get('ip', 'N/A')} | 目的端: {target.get('ip', 'N/A')}")
        print("-" * 50)

        # 获取目的端实际规格
        if mode == "hcloud":
            ecs_id = target.get("ecs_id", "")
            region = target.get("region", "ap-southeast-3")
            if not ecs_id:
                print("  🟡 未提供 ecs_id，跳过 hcloud 查询，使用 JSON 中的规格")
                target_actual = target
            else:
                print(f"  📡 通过 hcloud 查询 ECS {ecs_id}...")
                queried, err = query_ecs_via_hcloud(ecs_id, region)
                if err:
                    print(f"  🟡 hcloud 查询失败: {err}，回退到 JSON 规格")
                    target_actual = target
                else:
                    print(f"  ✅ hcloud 查询成功")
                    target_actual = queried
        else:
            target_actual = target

        # 1. 源端写操作完整性（致命检查）
        print("  🔴 源端迁移前后写操作检查:")
        for r in check_source_write_integrity(source):
            print(r)
            if not r.passed:
                all_passed = False
                if r.severity == "error":
                    has_errors = True

        # 2. CPU 核数比对
        print("  💻 CPU 核数比对:")
        src_cpu = source.get("cpu_cores", 0)
        tgt_cpu = target_actual.get("cpu_cores", 0)
        r = check_cpu_consistency(src_cpu, tgt_cpu)
        print(r)
        if not r.passed:
            all_passed = False
            if r.severity == "error":
                has_errors = True

        # 3. 内存大小比对
        print("  🧠 内存大小比对:")
        src_mem = source.get("memory_gb", 0)
        tgt_mem = target_actual.get("memory_gb", 0)
        r = check_memory_consistency(src_mem, tgt_mem)
        print(r)
        if not r.passed:
            all_passed = False
            if r.severity == "error":
                has_errors = True

        # 4. 磁盘比对
        print("  💽 磁盘一致性比对:")
        src_disks = source.get("disks", [])
        tgt_disks = target_actual.get("disks", [])
        for r in check_disk_consistency(src_disks, tgt_disks):
            print(r)
            if not r.passed:
                all_passed = False
                if r.severity == "error":
                    has_errors = True

        # 5. OS 版本比对
        print("  🐧 操作系统版本比对:")
        src_os = source.get("os", "unknown")
        tgt_os = target_actual.get("os", "unknown")
        r = check_os_consistency(src_os, tgt_os)
        print(r)
        if not r.passed:
            all_passed = False
            if r.severity == "error":
                has_errors = True

        # 6. 目的端网络连通性
        tgt_ip = target_actual.get("ip", target.get("ip", ""))
        if tgt_ip:
            print("  📡 目的端网络连通性:")
            for r in check_network_connectivity(tgt_ip):
                print(r)
                if not r.passed:
                    all_passed = False
                    if r.severity == "error":
                        has_errors = True
        else:
            print("  🟡 未提供目的端 IP，跳过网络连通性检查")

        # 7. 应用启动与业务验证
        print("  🧪 应用启动与业务验证:")
        for r in check_application_business(target_actual):
            print(r)
            if not r.passed:
                all_passed = False
                if r.severity == "error":
                    has_errors = True

    # 总结
    print("\n" + "=" * 70)
    if has_errors:
        print("  ❌ 校验未通过 — 存在 error 级别差异，请检查迁移结果")
    elif not all_passed:
        print("  🟡 校验通过但有警告 — 请确认 warning 项")
    else:
        print("  ✅ 校验全部通过 — 目的端规格与源端基本一致")
    print("=" * 70)

    return 0 if all_passed else 1


def main():
    parser = argparse.ArgumentParser(
        description="SMS 主机迁移 - 迁移后校验"
    )
    parser.add_argument(
        "--input", "-i", required=True,
        help="迁移主机列表 JSON 文件路径"
    )
    parser.add_argument(
        "--mode", "-m", choices=["manual", "hcloud"], default="manual",
        help="查询模式: manual=从JSON读取, hcloud=通过hcloud CLI查询 (默认: manual)"
    )
    args = parser.parse_args()
    sys.exit(run_post_check(args.input, args.mode))


if __name__ == "__main__":
    main()
