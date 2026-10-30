#!/usr/bin/env python3
"""
通用配置加载模块 — 面向接口，不硬编码任何 IP/端口/路径。
从 YAML 配置文件加载所有参数，提供统一的 get 接口。
"""

import os
import sys

try:
    import yaml
except ImportError:
    print("PyYAML not installed. Install with: pip3 install pyyaml", file=sys.stderr)
    sys.exit(1)


class ConfigError(Exception):
    """配置相关异常"""
    pass


class Config:
    """
    配置管理器：加载 YAML 配置文件，提供分层 get 接口。
    所有脚本通过此模块获取参数，不硬编码任何值。
    """

    def __init__(self, config_path=None):
        self._data = {}
        self._config_path = self._resolve_config_path(config_path)
        self.load()

    @staticmethod
    def _resolve_config_path(config_path):
        """智能解析配置文件路径"""
        # 按优先级查找配置
        candidates = [
            config_path,
            os.environ.get("PROXYOPT_CONFIG"),
            os.path.join(os.getcwd(), "config", "config.yaml"),
            os.path.join(os.path.dirname(__file__), "..", "config", "config.yaml"),
        ]
        for c in candidates:
            if c and os.path.isfile(c):
                return os.path.abspath(c)

        raise ConfigError(
            f"Config file not found. Searched: {candidates}. "
            f"Set PROXYOPT_CONFIG env var or pass --config path."
        )

    def load(self):
        """加载并解析 YAML 配置文件"""
        try:
            with open(self._config_path, "r", encoding="utf-8") as f:
                self._data = yaml.safe_load(f) or {}
        except yaml.YAMLError as e:
            raise ConfigError(f"YAML parse error in {self._config_path}: {e}")
        except IOError as e:
            raise ConfigError(f"Cannot read config file {self._config_path}: {e}")

    def get(self, dotted_key, default=None):
        """
        通过点分路径获取配置值，例如 get('squid.port', 3128)
        支持嵌套字典层级访问。
        """
        keys = dotted_key.split(".")
        val = self._data
        for k in keys:
            if isinstance(val, dict) and k in val:
                val = val[k]
            else:
                return default
        return val

    def get_required(self, dotted_key):
        """获取必需配置项，不存在则抛异常"""
        val = self.get(dotted_key)
        if val is None:
            raise ConfigError(f"Required config key '{dotted_key}' not found in {self._config_path}")
        return val

    def get_section(self, section_name):
        """获取整个配置段（返回字典）"""
        return self.get(section_name, {})

    @property
    def config_path(self):
        return self._config_path

    def dump(self):
        """返回当前配置的字符串表示（用于日志）"""
        return yaml.dump(self._data, default_flow_style=False, allow_unicode=True)


# ── 便捷访问器 ──────────────────────────────────────────────

class SandboxConfig:
    """沙箱角色配置便捷访问"""
    def __init__(self, config: Config):
        self.http_host = config.get("sandbox.http_host", "0.0.0.0")
        self.http_port = config.get("sandbox.http_port", 8080)
        self.serve_dir = config.get("sandbox.serve_dir", "./downloads")
        self.precache_host = config.get("sandbox.precache_host", "127.0.0.1")
        self.obs_bucket = config.get("sandbox.obs_bucket", "")
        self.obs_prefix = config.get("sandbox.obs_prefix", "")
        self.obs_endpoint = config.get("sandbox.obs_endpoint", "")
        self.obsutil_path = config.get("sandbox.obsutil_path", "obsutil")
        self.download_dir = config.get("sandbox.download_dir", "./downloads")
        self.max_retries = config.get("sandbox.max_retries", 3)
        self.retry_interval = config.get("sandbox.retry_interval", 5)
        self.max_connections = config.get("sandbox.max_connections", 64)
        self.auth_token = config.get("sandbox.auth_token", None)


class SquidConfig:
    """Squid 代理配置便捷访问"""
    def __init__(self, config: Config):
        self.host = config.get("squid.host", "")
        self.port = config.get("squid.port", 3128)
        self.cache_dir = config.get("squid.cache_dir", "/var/spool/squid")
        self.cache_size_mb = config.get("squid.cache_size_mb", 4096)
        self.max_object_size = config.get("squid.max_object_size", "512 MB")
        self.refresh_pattern_hours = config.get("squid.refresh_pattern_hours", 24)
        # 默认不放开代理来源：留空 = 仅放行 RFC1918 内网；
        # 显式配置 0.0.0.0/0 / all 需用户确认（开放代理红线，勿默认）
        self.allowed_src_cidr = config.get("squid.allowed_src_cidr", "")
        self.collapsed_forwarding = config.get("squid.collapsed_forwarding", True)


class GostConfig:
    """gost 端口转发配置便捷访问"""
    def __init__(self, config: Config):
        self.host = config.get("gost.host", "")
        self.listen_port = config.get("gost.listen_port", 0)
        self.target_port = config.get("gost.target_port", 5985)
        self.forward_rules = config.get("gost.forward_rules", [])
        self.install_url = config.get("gost.install_url", "")
        self.version = config.get("gost.version", "3.2.6")
        # keepalive
        self.ka_enabled = config.get("gost.keepalive.enabled", True)
        self.ka_idle = config.get("gost.keepalive.idle", "15s")
        self.ka_interval = config.get("gost.keepalive.interval", "5s")
        self.ka_count = config.get("gost.keepalive.count", 3)
        # autolink
        self.al_enabled = config.get("gost.autolink.enabled", True)
        self.al_delay = config.get("gost.autolink.delay", "5s")


class SourceConfig:
    """源端主机配置便捷访问"""
    def __init__(self, config: Config):
        self.concurrent = config.get("source.concurrent", 10)
        self.retry_count = config.get("source.retry_count", 3)
        self.retry_delay_sec = config.get("source.retry_delay_sec", 5)
        self.timeout_sec = config.get("source.timeout_sec", 300)
        self.download_dir = config.get("source.download_dir", "C:\\auto_agent_opt\\downloads")
        self.hosts_file = config.get("source.hosts_file", "")
        self.verify_ssl = config.get("source.verify_ssl", False)


def load_config(config_path=None):
    """工厂函数：加载配置并返回 Config 实例"""
    return Config(config_path)
