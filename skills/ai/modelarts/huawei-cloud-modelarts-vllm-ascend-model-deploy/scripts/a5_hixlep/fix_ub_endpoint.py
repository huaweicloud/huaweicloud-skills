#!/usr/bin/env python3
"""根据 npu-smi info -m 的 NPU ID <-> Chip Phy-ID 对应关系，修正 /etc/hixlep/ 下的
ub_endpoint_npu_*.json 文件：仅保留 Chip Phy-ID 存在的文件，并重命名为对应 NPU ID。

用法（目标机器，需 root）：
    sudo python3 fix_ub_endpoint.py        # 先预览计划
    sudo python3 fix_ub_endpoint.py -y     # 确认执行
"""
import os
import re
import subprocess
import sys

HIXLEP_DIR = os.environ.get("HIXLEP_DIR", "/etc/hixlep")
PATTERN = re.compile(r"^ub_endpoint_npu_(\d+)\.json$")


def get_phy_to_npu_map():
    out = subprocess.run(
        ["npu-smi", "info", "-m"], capture_output=True, text=True
    ).stdout
    mapping = {}
    header = False
    for line in out.splitlines():
        cols = line.split()
        if cols[:2] == ["NPU", "ID"]:
            header = True
            continue
        if header and len(cols) >= 4 and cols[0].isdigit():
            mapping[int(cols[3])] = int(cols[0])
    return mapping


def plan_changes(phy_to_npu, dirpath):
    to_delete, to_rename = [], []
    for name in os.listdir(dirpath):
        m = PATTERN.match(name)
        if not m:
            continue
        idx = int(m.group(1))
        if idx not in phy_to_npu:
            to_delete.append(name)
        else:
            to_rename.append((name, f"ub_endpoint_npu_{phy_to_npu[idx]}.json"))
    return to_delete, to_rename


def main():
    phy_to_npu = get_phy_to_npu_map()
    if not phy_to_npu:
        print("错误：未解析到 NPU ID / Chip Phy-ID 映射，请检查 npu-smi info -m 输出",
              file=sys.stderr)
        sys.exit(1)
    print(f"Chip Phy-ID <-> NPU ID 映射: {phy_to_npu}")

    to_delete, to_rename = plan_changes(phy_to_npu, HIXLEP_DIR)
    print("计划删除:")
    for n in to_delete:
        print(f"  rm {os.path.join(HIXLEP_DIR, n)}")
    print("计划重命名:")
    for old, new in to_rename:
        print(f"  {os.path.join(HIXLEP_DIR, old)} -> {os.path.join(HIXLEP_DIR, new)}")

    if not to_delete and not to_rename:
        print("无变更")
        return
    if "-y" not in sys.argv and "--yes" not in sys.argv:
        print("以上为预览。确认执行请加 -y/--yes")
        return

    for n in to_delete:
        os.remove(os.path.join(HIXLEP_DIR, n))
        print(f"已删除 {n}")
    for old, new in to_rename:
        src, dst = os.path.join(HIXLEP_DIR, old), os.path.join(HIXLEP_DIR, new)
        if os.path.exists(dst):
            print(f"警告: 目标 {new} 已存在，跳过 {old}")
            continue
        os.rename(src, dst)
        print(f"已重命名 {old} -> {new}")


if __name__ == "__main__":
    main()
