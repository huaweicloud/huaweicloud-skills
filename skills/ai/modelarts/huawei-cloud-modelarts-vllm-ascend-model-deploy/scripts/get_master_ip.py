#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从全局 rank table 获取 master IP。

从 GLOBAL_RANK_TABLE_FILE_PATH 指向的 rank table JSON 读取:
  - 默认(group_idx=0): 输出 group 0 第一个 server IP(多机部署 master / PD 分离 proxy)
  - group_idx=1: 输出 group 1 第一个 server IP(PD 分离 prefill 组 master)
  - group_idx=2: 输出 group 2 第一个 server IP(PD 分离 decode 组 master)

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


def get_master_ip(group_idx=0):
    """从 rank table 的指定 server_group 的第一个 server 取 master IP。

    部署形态对应 group_idx:
    - 单机部署: 不调用此文件
    - 多机部署: group_idx=0(server_group_list[0]['server_list'][0] = master IP)
      master 推理单元实例数只能为 1,group 0 只有 1 个 server
    - PD 分离部署:
      - proxy(group 0): 实例数只能为 1,通过源码获取 masterIp(group_idx=0)
      - prefill(group 1): 多实例场景下需要主从结构
        server_group_list[1]['server_list'][0] = master,其余为 worker
      - decode(group 2): 多实例场景下需要主从结构
        server_group_list[2]['server_list'][0] = D 组自己的 master,其余 = worker
      (官网 V2: D 组的 --dp-address 指向 D 组自己的第一个 server,不是 prefill 组的 master;
       内网证据: 8机 3P1D 部署 D 组 master 在 rank table 位置 6,独立于 P 组位置 0/2/4)
    """
    try:
        rank_table = wait_and_get_completed_global_rank_table()
        if rank_table is None:
            return None
        master = rank_table["server_group_list"][group_idx]["server_list"][0]
        return master["server_ip"]
    except Exception as e:
        print(e, file=sys.stderr)


def get_dp_start_rank():
    """根据 POD_IP 在 rank table 中匹配当前节点的 data-parallel start rank。

    multi_node 形态每节点 1 个实例,按 rank table 全局遍历序号取 rank
    (master=0, worker=1/2/...)。ModelArts multi_node 不注入 DP_START_RANK
    envs(与 PD 分离不同),必须从 rank table 动态推导;硬编码 0 会导致 worker
    也启动 engine rank 0,与 master 冲突,vLLM 报 "HELLO message from remote
    engine 0, expected it to be local"。未匹配时回退为 0(master 节点)。
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
    """统计 rank table 中全部 server 数(multi_node DP 总数 = 节点数)。

    multi_node 形态每节点运行 1 个实例,DP 总数 = rank table 全部 server_list
    条目数。硬编码(如 2)在节点数变化时与 --data-parallel-size 不符导致跨
    节点通信失败,因此动态推导。PD 分离由 envs/脚本固定填入 PREFILL_DP_SIZE
    /DECODE_DP_SIZE,不调用此函数。
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
        group_idx = 0
        if len(sys.argv) > 1:
            try:
                group_idx = int(sys.argv[1])
            except ValueError:
                pass
        result = get_master_ip(group_idx)
        if result is not None:
            print(result)
