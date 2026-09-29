#!/usr/bin/env python3
"""
task_name_utils.py — SMS 迁移任务名称清理工具

华为云 SMS 创建迁移任务时，任务名称规则：
  - 只能由中文字符、英文字母、数字、下划线、短横线组成
  - 最小长度：1
  - 最大长度：20

本模块提供 sanitize_task_name() 函数，确保任意输入都符合上述规则。
"""

import re
import logging

logger = logging.getLogger(__name__)

# SMS 任务名称规则常量
SMS_TASK_NAME_MIN_LENGTH = 1
SMS_TASK_NAME_MAX_LENGTH = 20

# 允许的字符: 中文字符(\u4e00-\u9fff)、英文字母、数字、下划线、短横线
# 正则: 匹配不在允许范围内的字符
_INVALID_CHARS_PATTERN = re.compile(r'[^\u4e00-\u9fffa-zA-Z0-9_-]')


def sanitize_task_name(name: str, fallback_prefix: str = "migrate") -> str:
    """清理并验证 SMS 迁移任务名称，确保符合华为云 SMS API 规则。

    规则:
      - 只能由中文字符、英文字母、数字、下划线、短横线组成
      - 最小长度: 1, 最大长度: 20

    处理步骤:
      1. 若输入为空或 None，使用 fallback_prefix 作为基础
      2. 去除首尾空白
      3. 移除所有不允许的字符 (如点号、空格、冒号等)
      4. 若清理后为空，使用 fallback_prefix
      5. 截断到最大长度 20

    Args:
        name: 原始任务名称
        fallback_prefix: 当 name 为空或清理后为空时的回退前缀

    Returns:
        符合 SMS API 规则的任务名称 (1-20 字符)
    """
    # Step 1: 处理空输入
    if not name or not isinstance(name, str):
        name = fallback_prefix
    else:
        name = name.strip()

    # Step 2: 移除不允许的字符
    cleaned = _INVALID_CHARS_PATTERN.sub('', name)

    # Step 3: 若清理后为空，使用 fallback_prefix
    if not cleaned:
        cleaned = fallback_prefix

    # Step 4: 截断到最大长度
    if len(cleaned) > SMS_TASK_NAME_MAX_LENGTH:
        original = cleaned
        cleaned = cleaned[:SMS_TASK_NAME_MAX_LENGTH]
        logger.warning(
            f"Task name truncated from {len(original)} to "
            f"{SMS_TASK_NAME_MAX_LENGTH} chars: '{original}' -> '{cleaned}'"
        )

    # Step 5: 确保最小长度 (此时 cleaned 至少有 fallback_prefix 的长度)
    if len(cleaned) < SMS_TASK_NAME_MIN_LENGTH:
        cleaned = fallback_prefix[:SMS_TASK_NAME_MAX_LENGTH]

    return cleaned


def generate_task_name_from_ip(source_ip: str) -> str:
    """从源端 IP 生成符合 SMS 规则的迁移任务名称。

    策略: 使用 IP 各段拼接，确保总长度 <= 20。
    例如: 192.168.0.230 -> "m-192-168-0-230" (16 chars)

    Args:
        source_ip: 源端 IP 地址 (如 "192.168.0.230")

    Returns:
        符合 SMS API 规则的任务名称
    """
    if not source_ip:
        return sanitize_task_name("migrate-unknown")

    # 将 IP 中的点替换为短横线
    ip_part = source_ip.replace('.', '-')

    # 尝试不同的前缀，确保总长度 <= 20
    # 优先使用 "migrate-" (8 chars)，若超长则缩短前缀
    for prefix in ["migrate-", "mig-", "m-"]:
        candidate = f"{prefix}{ip_part}"
        if len(candidate) <= SMS_TASK_NAME_MAX_LENGTH:
            return sanitize_task_name(candidate)

    # 如果 IP 本身就很长（极端情况），直接截断
    return sanitize_task_name(f"m-{ip_part}")


def generate_task_name_from_id(source_id: str) -> str:
    """从源端 ID 生成符合 SMS 规则的迁移任务名称。

    策略: 使用 source_id 的前 8 位 + 短时间戳，确保总长度 <= 20。
    例如: "abcd1234-1234" (12 chars)

    Args:
        source_id: 源端服务器 ID

    Returns:
        符合 SMS API 规则的任务名称
    """
    if not source_id:
        return sanitize_task_name("migrate-task")

    # 取 source_id 前 8 位
    id_part = source_id[:8]

    # 使用 "t-" 前缀 + id_part，确保 <= 20
    # "t-" (2) + 8 = 10 chars，远在限制内
    candidate = f"t-{id_part}"

    return sanitize_task_name(candidate)
