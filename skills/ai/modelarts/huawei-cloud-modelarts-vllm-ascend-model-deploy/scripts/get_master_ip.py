#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从全局 rank table 获取 master IP、DP start rank 与 DP size(节点数)。

从 GLOBAL_RANK_TABLE_FILE_PATH 指向的 rank table JSON 读取:
  - 默认: 输出 master IP(与 POD_IP 比较判定角色)
  - --dp-rank: 输出当前节点 DP start rank
  - --dp-size: 输出 DP 总数 = rank table 节点数(动态推导,禁硬编码)

环境变量: GLOBAL_RANK_TABLE_FILE_PATH(rank table 路径)、POD_IP(当前节点 IP)
"""

import json
import os
import sys
import time

GLOBAL_RANK_TABLE_ENV = "GLOBAL_RANK_TABLE_FILE_PATH"


def wait_and_get_completed_global_rank_table():
    """轮询等待 rank table 文件 status 变为 completed,返回解析后的 dict。"""
    global_rank_table_path = os.getenv(GLOBAL_RANK_TABLE_ENV)
    if not global_rank_table_path:
        print('read env "{}" failed'.format(GLOBAL_RANK_TABLE_ENV), file=sys.stderr)
        return None
    while True:
        try:
            rank_table = get_rank_table(global_rank_table_path)
            if rank_table is not None:
                return rank_table
        except Exception as e:
            print(e, file=sys.stderr)
        time.sleep(1)


def get_rank_table(global_rank_table_path=None):
    """读取 rank table JSON 文件,status 为 completed 时返回,否则返回 None。"""
    if global_rank_table_path is None:
        global_rank_table_path = os.getenv(GLOBAL_RANK_TABLE_ENV)
    with open(global_rank_table_path, "r") as file:
        buf = file.read()
    rank_table = json.loads(buf)
    if rank_table["status"] == "completed":
        return rank_table
    else:
        return None


def get_master_ip():
    """从 rank table 的第一个 server_group 的第一个 server 取 master IP。"""
    try:
        rank_table = wait_and_get_completed_global_rank_table()
        if rank_table is None:
            return None
        master = rank_table["server_group_list"][0]["server_list"][0]
        return master["server_ip"]
    except Exception as e:
        print(e, file=sys.stderr)


def get_dp_start_rank():
    """根据 POD_IP 在 rank table 中匹配当前节点的 data-parallel start rank。

    遍历所有 server_group 的 server_list,匹配 server_ip / server_id / container_ip
    等于 POD_IP 的条目,返回其在全局遍历顺序中的序号(rank)。
    未匹配时回退为 0(master 节点)。
    """
    try:
        rank_table = wait_and_get_completed_global_rank_table()
        if rank_table is None:
            return 0
        pod_ip = os.getenv("POD_IP")
        if not pod_ip:
            print("read env POD_IP failed", file=sys.stderr)
            return 0
        rank = 0
        for group in rank_table.get("server_group_list", []):
            for server in group.get("server_list", []):
                if (
                    server.get("server_ip") == pod_ip
                    or server.get("server_id") == pod_ip
                    or server.get("container_ip") == pod_ip
                ):
                    return rank
                rank += 1
        print(
            f"Warning: POD_IP {pod_ip} not found in rank table, fallback to rank 0",
            file=sys.stderr,
        )
        return 0
    except Exception as e:
        print(f"get_dp_start_rank error: {e}", file=sys.stderr)
        return 0


def get_dp_size():
    """统计 rank table 中全部 server 数(节点总数)。

    单引擎 DP 形态(multinode / pd_colocate)下,每个节点运行 1 个实例,
    数据并行总数(DATA_PARALLEL_SIZE)= rank table 中全部 server_list 条目数。
    硬编码默认值(如 1/2)在节点数变化时会与 --data-parallel-size 不符,
    导致跨节点通信失败,因此由 rank table 动态推导。
    """
    try:
        rank_table = wait_and_get_completed_global_rank_table()
        if rank_table is None:
            return 1
        total = 0
        for group in rank_table.get("server_group_list", []):
            total += len(group.get("server_list", []))
        if total <= 0:
            print("Warning: rank table contains no server, fallback to 1", file=sys.stderr)
            return 1
        return total
    except Exception as e:
        print(f"get_dp_size error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--dp-rank":
        print(get_dp_start_rank())
    elif len(sys.argv) > 1 and sys.argv[1] == "--dp-size":
        print(get_dp_size())
    else:
        print(get_master_ip())
