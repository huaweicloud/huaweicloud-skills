"""
迁移主机信息来源：环境变量 Host_Information（JSON 数组模板）。

批量迁移不再要求 CSV 主机列表，改为从环境变量读取:

  export Host_Information='[
    {
      "主机名": "win-src-1", "公网IP": "1.2.3.4", "内网IP": "192.168.1.10",
      "端口号": "5985", "用户名": "Administrator", "密码": "xxx",
      "region_id": "cn-north-4", "region_name": "华北-北京四",
      "project_id": "proj_01", "project_name": "migrate",
      "os_type": "WINDOWS", "use_public_ip": "false"
    },
    {
      "代理主机名": "jump-1", "公网IP": "203.0.113.10", "内网IP": "10.0.0.1",
      "端口号": "22", "用户名": "root", "密码": "yyy",
      "region_id": "cn-north-4", "region_name": "华北-北京四"
    }
  ]'

中文键与英文键均可识别；兼容单对象（dict）或数组（list）。
CSV（config/hosts.csv）保留为向后兼容回退，不改变迁移基本逻辑。
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

ENV_NAME = "Host_Information"

# 旧版嵌套格式标记键（早期 Host_Information 结构）
_NESTED_MARKER_KEYS = ("source_server", "proxy_server", "migration_ak_sk", "sms_agent_config")


def _expand_nested_env(data: dict) -> list[dict]:
    """兼容旧版嵌套 Host_Information → 数组项（源端 + 代理）。

    旧格式:
      {
        "migration_ak_sk": {"ak": "...", "sk": "..."},
        "proxy_server": {"host": "203.0.113.10", "internal_ip": "192.168.1.75",
                         "ssh_port": 22, "ssh_username": "root", "ssh_password": "..."},
        "source_server": {"internal_ip": "192.168.1.252", "username": "Administrator",
                          "password": "..."},
        "sms_agent_config": {"ak": "...", "sk": "...", "sms_domain": "...",
                             "enterprise_project": "..."}
      }

    云侧 AK/SK/Domain/企业项目仍由 config/migrate.yaml 的 sms_agent 段提供，
    此处只导出主机/代理结构，绝不回传任何密钥字段。
    """
    items: list[dict] = []
    src = data.get("source_server") or {}
    if src:
        items.append({
            "主机名": str(src.get("hostname") or src.get("name") or "win-source"),
            "公网IP": str(src.get("public_ip") or ""),
            "内网IP": str(src.get("internal_ip") or src.get("private_ip") or src.get("ip") or ""),
            "端口号": str(src.get("winrm_port") or src.get("port") or 5985),
            "用户名": str(src.get("username") or "Administrator"),
            "密码": str(src.get("password") or ""),
            "os_type": str(src.get("os_type") or "WINDOWS"),
            "use_public_ip": str(src.get("use_public_ip") or "false"),
            "region_id": str(src.get("region_id") or ""),
            "region_name": str(src.get("region_name") or ""),
        })
    proxy = data.get("proxy_server") or {}
    if proxy:
        items.append({
            "代理主机名": str(proxy.get("hostname") or proxy.get("name") or "jump-proxy"),
            "公网IP": str(proxy.get("host") or proxy.get("public_ip") or ""),
            "内网IP": str(proxy.get("internal_ip") or proxy.get("private_ip") or ""),
            "端口号": str(proxy.get("ssh_port") or proxy.get("port") or 22),
            "用户名": str(proxy.get("ssh_username") or "root"),
            "密码": str(proxy.get("ssh_password") or ""),
            "region_id": str(proxy.get("region_id") or ""),
            "region_name": str(proxy.get("region_name") or ""),
        })
    return items


# 中英文键 → 标准键（源端主机）
_SOURCE_ALIASES = {
    "主机名": "hostname", "hostname": "hostname", "name": "hostname",
    "公网IP": "public_ip", "公网ip": "public_ip", "public_ip": "public_ip",
    "publicip": "public_ip", "外网IP": "public_ip",
    "内网IP": "private_ip", "内网ip": "private_ip", "private_ip": "private_ip",
    "privateip": "private_ip", "inner_ip": "private_ip", "内网地址": "private_ip",
    "端口号": "winrm_port", "port": "winrm_port", "winrm_port": "winrm_port",
    "端口": "winrm_port",
    "用户名": "username", "username": "username", "user": "username",
    "密码": "password", "password": "password", "pwd": "password",
    "region_id": "region_id", "region": "region_id",
    "region_name": "region_name",
    "project_id": "project_id", "project": "project_id",
    "project_name": "project_name",
    "os_type": "os_type", "ostype": "os_type", "系统类型": "os_type",
    "use_public_ip": "use_public_ip", "usepublicip": "use_public_ip",
}

# 代理主机专用别名 → 标准键
_PROXY_ALIASES = {
    "代理主机名": "proxy_hostname", "proxy_hostname": "proxy_hostname",
    "公网IP": "proxy_public_ip", "公网ip": "proxy_public_ip",
    "proxy_public_ip": "proxy_public_ip",
    "内网IP": "proxy_private_ip", "内网ip": "proxy_private_ip",
    "proxy_private_ip": "proxy_private_ip",
    "端口号": "proxy_ssh_port", "端口": "proxy_ssh_port",
    "port": "proxy_ssh_port", "proxy_ssh_port": "proxy_ssh_port",
    "ssh_port": "proxy_ssh_port",
    "用户名": "proxy_username", "username": "proxy_username",
    "proxy_username": "proxy_username",
    "密码": "proxy_password", "password": "proxy_password",
    "proxy_password": "proxy_password",
    "region_id": "proxy_region_id", "proxy_region_id": "proxy_region_id",
    "region_name": "proxy_region_name", "proxy_region_name": "proxy_region_name",
}


def _strip_comment_lines(text: str) -> str:
    """去掉 JSON 中常见的 // 与 # 注释行，便于 shell 环境变量粘贴。"""
    lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("//") or stripped.startswith("#"):
            continue
        lines.append(line)
    return "\n".join(lines)


def _normalize_item(item: dict) -> dict:
    """将中英文键归一化为标准键（先判定代理对象，再按对应别名表映射）。"""
    keys = [str(k) for k in item.keys()]
    is_proxy_like = (
        any("代理" in k for k in keys)
        or any(k.startswith("proxy_") for k in keys)
        or any(k in keys for k in (
            "proxy_hostname", "proxy_public_ip", "proxy_private_ip",
            "proxy_ssh_port", "proxy_username", "proxy_password",
        ))
    )
    alias_map = _PROXY_ALIASES if is_proxy_like else _SOURCE_ALIASES

    norm: dict[str, Any] = {}
    for raw_key, value in item.items():
        if not isinstance(raw_key, str):
            norm[str(raw_key)] = value
            continue
        key = raw_key.strip()
        std = alias_map.get(key)
        if std:
            if isinstance(value, str):
                value = value.strip()
            if value not in (None, ""):
                norm.setdefault(std, value)
        else:
            norm.setdefault(key, value)
    # 兜底字段：代理主机（含“代理”字样键）标记
    if is_proxy_like:
        norm["is_proxy"] = True
    return norm


def _looks_like_proxy(item: dict) -> bool:
    if item.get("is_proxy"):
        return True
    if item.get("proxy_hostname") or item.get("proxy_public_ip"):
        return True
    # 源端主机必须有可登录的用户名；代理对象没有 os_type/project 等源端特征
    if item.get("os_type") or item.get("project_id") or item.get("use_public_ip"):
        return False
    raw_keys = [str(k).lower() for k in item.keys()]
    if any("代理" in k for k in item.keys()):
        return True
    return bool(item.get("proxy_username") or ("proxy" in " ".join(raw_keys)))


def _split_sources_and_proxies(items: list[dict]) -> tuple[list[dict], list[dict]]:
    """分离源端主机与代理主机。返回 (sources, proxies)。"""
    sources: list[dict] = []
    proxies: list[dict] = []
    for item in items:
        norm = _normalize_item(item)
        if _looks_like_proxy(norm):
            proxies.append(norm)
        else:
            sources.append(norm)
    return sources, proxies


def load_host_information(env_name: str = ENV_NAME) -> list[dict]:
    """从环境变量读取 Host_Information JSON，返回原始 dict 列表（未归一化）。

    支持：数组、单对象、空值。解析失败返回 [] 并记录 warning。
    """
    raw = os.environ.get(env_name, "")
    if not raw or not raw.strip():
        return []
    text = _strip_comment_lines(raw)
    try:
        data = json.loads(text)
    except Exception as e:
        logger.warning("环境变量 %s JSON 解析失败: %s", env_name, e)
        return []
    if isinstance(data, dict):
        # 旧版嵌套格式（含 source_server/proxy_server 等标记键）→ 展开为数组项
        if any(k in data for k in _NESTED_MARKER_KEYS):
            expanded = _expand_nested_env(data)
            if expanded:
                return expanded
        return [data]
    if isinstance(data, list):
        return data
    logger.warning("环境变量 %s 不是 JSON 数组或对象", env_name)
    return []


def load_sources_and_proxies(env_name: str = ENV_NAME) -> tuple[list[dict], list[dict]]:
    """解析环境变量 → (源端主机列表, 代理主机列表)，均为归一化标准键 dict。"""
    items = load_host_information(env_name)
    return _split_sources_and_proxies(items)


def to_host_states(sources: list[dict], prefer_inner_ip: bool = False) -> list[dict]:
    """源端主机 dict → 批量编排器可直接构建 HostState 的 dict 列表。

    - host 字段：公网模式取公网IP（优先），私网模式取内网IP（prefer_inner_ip=True）。
    - 保持与 batch_base._load_hosts 相同的字段语义，并附加 region/project/os 信息。
    """
    states: list[dict] = []
    for src in sources:
        hostname = str(src.get("hostname") or "").strip()
        public_ip = str(src.get("public_ip") or "").strip()
        private_ip = str(src.get("private_ip") or "").strip()

        if prefer_inner_ip:
            host = private_ip or public_ip or hostname
        else:
            host = public_ip or private_ip or hostname
        if not host:
            logger.warning("跳过缺少主机标识的源端记录: %s", src)
            continue

        try:
            winrm_port = int(src.get("winrm_port") or 5985)
        except (TypeError, ValueError):
            winrm_port = 5985

        states.append({
            "host": host,
            "hostname": hostname,
            "public_ip": public_ip,
            "private_ip": private_ip,
            "username": str(src.get("username") or "Administrator").strip(),
            "password": str(src.get("password") or ""),
            "winrm_port": winrm_port,
            "region_id": str(src.get("region_id") or "").strip(),
            "region_name": str(src.get("region_name") or "").strip(),
            "project_id": str(src.get("project_id") or "").strip(),
            "project_name": str(src.get("project_name") or "").strip(),
            "os_type": str(src.get("os_type") or "").strip(),
            "use_public_ip": str(src.get("use_public_ip") or "").strip(),
        })
    return states


def first_proxy_config(proxies: list[dict]) -> dict | None:
    """取第一个可用代理 → (host, ssh_port, username, password) 配置 dict；无则 None。"""
    for p in proxies:
        host = str(p.get("proxy_public_ip") or p.get("proxy_private_ip") or p.get("proxy_hostname") or "").strip()
        if not host:
            continue
        try:
            ssh_port = int(p.get("proxy_ssh_port") or 22)
        except (TypeError, ValueError):
            ssh_port = 22
        return {
            "host": host,
            "ssh_port": ssh_port,
            "username": str(p.get("proxy_username") or "root").strip(),
            "password": str(p.get("proxy_password") or ""),
            "region_id": str(p.get("proxy_region_id") or "").strip(),
            "region_name": str(p.get("proxy_region_name") or "").strip(),
        }
    return None