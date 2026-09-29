#!/usr/bin/env python3
"""
ownership_utils.py — 目标端 ECS 所属权管理工具

通过 ECS 标签（Tag）实现所属权管理：
  - 创建目标 ECS 时自动打标签，标识由本 skill 创建
  - 通过标签精确查找已存在的目标 ECS（防重复创建）
  - 操作 ECS 前校验所属权（权限范围控制）

标签体系:
  - migration-skill: vmware-ecs-private  (标识由本 skill 创建)
  - source-ip: 192.168.0.186             (源端主机 IP)
  - source-name: xxx                     (源端主机名)
  - migration-time: 2026-08-26T12:00:00  (迁移时间戳)
"""

import re
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

# 本 skill 的标识标签
SKILL_TAG_KEY = "migration-skill"
SKILL_TAG_VALUE = "vmware-ecs-private"


def build_ownership_tags(source_ip: str, source_name: str = "") -> Dict[str, str]:
    """构建所属权标签

    Args:
        source_ip: 源端主机 IP
        source_name: 源端主机名 (可选)

    Returns:
        标签 dict, 如:
        {
            "migration-skill": "vmware-ecs-private",
            "source-ip": "192.168.0.186",
            "source-name": "xxx",
            "migration-time": "2026-08-26T12:00:00"
        }
    """
    tags = {
        SKILL_TAG_KEY: SKILL_TAG_VALUE,
        "source-ip": source_ip,
        "migration-time": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
    }
    if source_name:
        tags["source-name"] = source_name
    return tags


def check_ownership(ecs_info: Dict[str, Any], source_ip: str = "") -> bool:
    """校验 ECS 是否属于本 skill 的所属权

    通过检查 ECS 的标签判断：
      1. 必须有 migration-skill=vmware-ecs-private 标签 (由本 skill 创建)
      2. 如果指定了 source_ip，还需匹配 source-ip 标签

    Args:
        ecs_info: ECS 实例信息 (hcloud ShowServer 返回)
        source_ip: 源端 IP (可选，用于精确匹配)

    Returns:
        True=属于本 skill 所属权, False=不属于
    """
    if not ecs_info:
        return False

    # 从 ECS 信息中提取标签
    tags = _extract_tags(ecs_info)
    if not tags:
        return False

    # 检查 skill 标识标签
    if tags.get(SKILL_TAG_KEY) != SKILL_TAG_VALUE:
        return False

    # 如果指定了 source_ip，检查是否匹配
    if source_ip:
        tagged_ip = tags.get("source-ip", "")
        if tagged_ip and tagged_ip != source_ip:
            return False

    return True


def _extract_tags(ecs_info: Dict[str, Any]) -> Dict[str, str]:
    """从 ECS 信息中提取标签 dict

    华为云 ECS ShowServer 返回的标签格式可能为:
      - {"tags": [{"key": "k", "value": "v"}, ...]}
      - {"server": {"tags": [{"key": "k", "value": "v"}, ...]}}
      - {"tags": {"k": "v", ...}}  (部分 API 版本)
    """
    server = ecs_info.get("server", ecs_info)
    tags_raw = server.get("tags", ecs_info.get("tags", []))

    if not tags_raw:
        return {}

    result = {}
    if isinstance(tags_raw, list):
        for tag in tags_raw:
            if isinstance(tag, dict):
                k = tag.get("key", "")
                v = tag.get("value", "")
                if k:
                    result[k] = v
    elif isinstance(tags_raw, dict):
        result = dict(tags_raw)

    return result


def find_owned_target(ecs_ops, source_ip: str) -> Optional[Dict[str, Any]]:
    """按所属权标签查找已存在的目标 ECS

    遍历 ECS 列表，查找带有本 skill 标签且 source-ip 匹配的 ECS。

    Args:
        ecs_ops: ECSOps 实例
        source_ip: 源端主机 IP

    Returns:
        匹配的 ECS 信息 dict, 或 None (未找到)
    """
    if not source_ip:
        return None

    logger.info(f"Searching for owned target ECS by source_ip={source_ip}")
    servers = ecs_ops.hcloud.ecs_list_servers()
    server_list = servers.get("servers", []) if isinstance(servers, dict) else []

    for srv in server_list:
        if check_ownership(srv, source_ip=source_ip):
            srv_id = srv.get("id", "")
            srv_name = srv.get("name", "")
            logger.info(f"Found owned target ECS: id={srv_id}, name={srv_name}")
            return srv

    logger.info(f"No owned target ECS found for source_ip={source_ip}")
    return None


def validate_ecs_name(name: str) -> str:
    """校验目标端 ECS 主机名是否符合命名规则

    规则: 只能由中文字符、英文字母、数字及 _、-、. 组成
          长度 [1-128] 英文字符或 [1-64] 中文字符

    Args:
        name: 待校验的 ECS 主机名

    Returns:
        校验通过后的名称

    Raises:
        ValueError: 名称不符合规则
    """
    if not name or not str(name).strip():
        raise ValueError("ECS 名称不能为空")

    name = str(name).strip()

    # 字符校验: 允许中文、英文、数字、_、-、.
    valid_pattern = re.compile(r'^[a-zA-Z0-9\u4e00-\u9fff_\-\.]+$')
    if not valid_pattern.match(name):
        raise ValueError(
            f"ECS 名称 '{name}' 包含非法字符。"
            f"只允许中文字符、英文字母、数字及 _、-、. 组成"
        )

    # 长度校验
    has_chinese = bool(re.search(r'[\u4e00-\u9fff]', name))
    if has_chinese:
        # 含中文: 最多 64 个字符
        if len(name) > 64:
            raise ValueError(
                f"ECS 名称 '{name}' 长度 {len(name)} 超过限制。"
                f"含中文名称最多 64 个字符"
            )
    else:
        # 纯英文: 最多 128 个字符
        if len(name) > 128:
            raise ValueError(
                f"ECS 名称 '{name}' 长度 {len(name)} 超过限制。"
                f"英文名称最多 128 个字符"
            )

    if len(name) < 1:
        raise ValueError("ECS 名称长度至少 1 个字符")

    return name


def generate_target_name(source_name: str) -> str:
    """根据源端主机名生成目标端 ECS 名称

    策略: target_name = f"migrated-{source_name}"
    前缀 'migrated-' 标识由本 skill 创建。

    Args:
        source_name: 源端主机名

    Returns:
        校验通过的目标端 ECS 名称

    Raises:
        ValueError: 生成的名称不符合命名规则
    """
    if not source_name:
        source_name = "unknown-source"
    target_name = f"migrated-{source_name}"
    return validate_ecs_name(target_name)
