import json
import os
import urllib3
from urllib.parse import urlparse

from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkcore.http.http_config import HttpConfig


def _ssl_verify_enabled():
    """是否启用 TLS 证书校验（默认启用）。

    仅当显式设置 HW_IGNORE_SSL_VERIFICATION=1/true 时才关闭校验，
    用于自签名证书/代理等特殊场景；关闭时保留 InsecureRequestWarning 输出。
    """
    val = os.getenv("HW_IGNORE_SSL_VERIFICATION", "").strip().lower()
    return val not in ("1", "true", "yes", "on")

HCLOUD_CONFIG = os.path.expanduser("~/.hcloud/config.json")


def _load_hcloud_profile():
    """从本地 hcloud CLI 配置文件读取 profile 凭据 (~/.hcloud/config.json)

    支持 'default' profile 与通过 HCLOUD_PROFILE 指定的其他 profile。
    返回 (ak, sk, region, security_token, domain_id) 或 (None,)*5。
    """
    try:
        with open(HCLOUD_CONFIG, "r", encoding="utf-8") as f:
            cfg = json.load(f)
    except (OSError, ValueError):
        return None, None, None, None, None

    profiles = cfg.get("profiles") or []
    profile_name = os.getenv("HCLOUD_PROFILE", "default")
    target = None
    for p in profiles:
        if isinstance(p, dict) and p.get("name") == profile_name:
            target = p
            break
    if target is None and profiles:
        target = profiles[0]
    if not isinstance(target, dict):
        return None, None, None, None, None

    return (
        target.get("accessKeyId", "") or "",
        target.get("secretAccessKey", "") or "",
        target.get("region", "") or "cn-north-4",
        target.get("securityToken", "") or "",
        target.get("domainId", "") or "",
    )


def load_credentials():
    """加载华为云凭据，优先级: 环境变量 HW_* > 本地 hcloud profile

    支持永久 AK/SK 与临时 AK/SK（含 SecurityToken）。
    环境变量: HW_ACCESS_KEY / HW_SECRET_KEY / HW_REGION_NAME / HW_SECURITY_TOKEN。
    本地 profile: ~/.hcloud/config.json（hcloud configure 生成的 default profile），
    可用 HCLOUD_PROFILE 指定其他 profile 名。
    """
    ak = os.getenv("HW_ACCESS_KEY", "")
    sk = os.getenv("HW_SECRET_KEY", "")
    region = os.getenv("HW_REGION_NAME", "cn-north-4")
    security_token = os.getenv("HW_SECURITY_TOKEN", "")
    domain_id = os.getenv("HW_DOMAIN_ID", "")

    if not ak or not sk:
        ak, sk, region, security_token, domain_id = _load_hcloud_profile()
        region = os.getenv("HW_REGION_NAME", region or "cn-north-4")

    if not ak or not sk:
        print("未配置 AK/SK，请设置环境变量 HW_ACCESS_KEY / HW_SECRET_KEY，或运行 `hcloud configure` 配置本地 profile")
        exit(-1)

    return ak, sk, region, security_token, domain_id


def _get_proxy_url():
    """获取代理 URL，优先级: HTTPS_PROXY > HTTP_PROXY"""
    proxy_url = os.getenv("HTTPS_PROXY", "")
    if proxy_url:
        return proxy_url
    proxy_url = os.getenv("HTTP_PROXY", "")
    if proxy_url:
        return proxy_url
    return ""


def build_http_config():
    """构建 HTTP 配置，代理支持环境变量

    代理 URL 来源（优先级从高到低）:
      1. HTTPS_PROXY
      2. HTTP_PROXY

    代理 URL 格式:
      - http://host:port
      - http://user:pass@host:port

    TLS: 默认启用证书校验；仅当 HW_IGNORE_SSL_VERIFICATION=1 时关闭。
    """
    http_config = HttpConfig.get_default_config()
    if _ssl_verify_enabled():
        http_config.ignore_ssl_verification = False
    else:
        http_config.ignore_ssl_verification = True
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    http_config.timeout = (30, 60)
    http_config.retry_times = 3

    proxy_url = _get_proxy_url()
    if proxy_url:
        parsed = urlparse(proxy_url)
        http_config.proxy_protocol = parsed.scheme or "http"
        http_config.proxy_host = parsed.hostname or ""
        http_config.proxy_port = parsed.port or 8080
        http_config.proxy_user = parsed.username or ""
        http_config.proxy_password = parsed.password or ""

    return http_config