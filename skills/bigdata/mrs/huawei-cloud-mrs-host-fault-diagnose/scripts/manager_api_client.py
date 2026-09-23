#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MRS Manager REST API 调用脚本
通过参数和YAML配置文件拼接URL请求，访问MRS Manager服务
支持 HTTP Basic Auth 和 Cookie（JSESSIONID）两种认证方式、密码加密存储、接口可扩展
"""

import argparse
import base64
import getpass
import json
import os
import secrets
import platform
import re
import ssl
import stat
import subprocess
import tempfile
import time
import urllib.parse
import urllib.request
from http.cookiejar import CookieJar, LWPCookieJar
from typing import Any, Optional

import yaml


CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "manager_api_config.yaml")
APIS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "manager_api_apis")
IS_WINDOWS = platform.system() == "Windows"


def load_config() -> dict:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    if "apis" not in config or not config["apis"]:
        config["apis"] = {}
    if os.path.isdir(APIS_DIR):
        for fname in sorted(os.listdir(APIS_DIR)):
            if fname.endswith((".yaml", ".yml")):
                fpath = os.path.join(APIS_DIR, fname)
                with open(fpath, "r", encoding="utf-8") as f:
                    api_defs = yaml.safe_load(f)
                if api_defs and isinstance(api_defs, dict):
                    config["apis"].update(api_defs)
    return config


def _get_default_session_cache_dir() -> str:
    tmp = os.environ.get("TEMP") or os.environ.get("TMP") or os.environ.get("TMPDIR", "/tmp")
    return os.path.join(tmp, "manager_session")


def _aes_key_path(config: dict) -> str:
    key_file = config.get("crypto", {}).get("aes_key_file", "")
    if key_file:
        return key_file
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), ".aes_key")


def _ensure_aes_key(config: dict) -> bytes:
    key_path = _aes_key_path(config)
    if os.path.exists(key_path):
        with open(key_path, "r", encoding="utf-8") as f:
            return bytes.fromhex(f.read().strip())
    key = secrets.token_bytes(32)
    fd, tmp_path = tempfile.mkstemp(dir=os.path.dirname(key_path), suffix=".tmp")
    try:
        os.write(fd, key.hex().encode("utf-8"))
        os.close(fd)
        os.chmod(tmp_path, stat.S_IRUSR | stat.S_IWUSR)
        os.replace(tmp_path, key_path)
    except OSError:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise
    return key


def _aes_encrypt(plain_text: str, config: dict) -> str:
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    from cryptography.hazmat.primitives import padding as sym_padding
    key = _ensure_aes_key(config)
    iv = secrets.token_bytes(16)
    padder = sym_padding.PKCS7(128).padder()
    padded = padder.update(plain_text.encode("utf-8")) + padder.finalize()
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
    encryptor = cipher.encryptor()
    ct = encryptor.update(padded) + encryptor.finalize()
    return base64.b64encode(iv + ct).decode("utf-8")


def _aes_decrypt(cipher_text: str, config: dict) -> str:
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    from cryptography.hazmat.primitives import padding as sym_padding
    key = _ensure_aes_key(config)
    raw = base64.b64decode(cipher_text)
    iv = raw[:16]
    ct = raw[16:]
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
    decryptor = cipher.decryptor()
    padded = decryptor.update(ct) + decryptor.finalize()
    unpadder = sym_padding.PKCS7(128).unpadder()
    data = unpadder.update(padded) + unpadder.finalize()
    return data.decode("utf-8")


def _call_crypto_api(data: str, crypto_type: str, config: dict) -> str:
    scc_conf = config.get("crypto", {}).get("scc_conf") or os.getenv("SCC_CONF")
    if not scc_conf:
        raise RuntimeError("scc_conf not set in config or env SCC_CONF")
    bin_path = config.get("crypto", {}).get("bin_path", "/usr/local/seccomponent/bin/CryptoAPI")
    if not os.path.isfile(bin_path):
        raise RuntimeError(f"CryptoAPI not found: {bin_path}")
    proc = subprocess.run(
        [bin_path, "-f", scc_conf, f"-{crypto_type}"],
        input=data,
        capture_output=True,
        text=True,
        timeout=60,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"CryptoAPI failed (exit={proc.returncode}): {proc.stderr}")
    output = proc.stdout.strip()
    if ":" in output:
        output = output.split(":", 1)[1]
    return output


def _crypto_engine(config: dict) -> str:
    """选择加密引擎：auto | aes | cryptoapi

    auto: Windows 用 Python AES，Linux 用 CryptoAPI
    aes: 强制使用 Python AES-256-CBC（Windows/Linux 均可）
    cryptoapi: 强制使用 CryptoAPI
    """
    engine = config.get("crypto", {}).get("engine", "auto")
    if isinstance(engine, str):
        engine = engine.strip().lower()
    if engine in ("aes", "cryptoapi"):
        return engine
    return "aes" if IS_WINDOWS else "cryptoapi"


def encrypt(plain_text: str, config: dict) -> str:
    """加密：按 crypto.engine 选择 AES 或 CryptoAPI"""
    if _crypto_engine(config) == "aes":
        return _aes_encrypt(plain_text, config)
    return _call_crypto_api(plain_text, "e", config)


def decrypt(cipher_text: str, config: dict) -> str:
    """解密：按 crypto.engine 选择 AES 或 CryptoAPI"""
    if _crypto_engine(config) == "aes":
        return _aes_decrypt(cipher_text, config)
    return _call_crypto_api(cipher_text, "d", config)


def _build_ssl_context(config: dict) -> ssl.SSLContext:
    ctx = ssl.create_default_context()
    verify_ssl = config.get("crypto", {}).get("verify_ssl", True)
    if not verify_ssl:
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    else:
        ca_cert = config.get("crypto", {}).get("ca_cert", "")
        if ca_cert and os.path.isfile(ca_cert):
            ctx.load_verify_locations(ca_cert)
    return ctx


class SessionManager:
    """Manager Session 管理：通过 login_check 获取 JSESSIONID Cookie 并缓存"""

    def __init__(self, config: dict):
        self.config = config
        cache_dir = config.get("session", {}).get("cache_dir", "")
        if not cache_dir:
            cache_dir = _get_default_session_cache_dir()
        os.makedirs(cache_dir, exist_ok=True)
        if not IS_WINDOWS:
            os.chmod(cache_dir, stat.S_IRWXU)
        self.cookie_file = os.path.join(cache_dir, "cookies.txt")
        self.cookie_jar = LWPCookieJar(self.cookie_file)
        # 加载已有 Cookie
        if os.path.exists(self.cookie_file):
            try:
                self.cookie_jar.load(ignore_discard=True, ignore_expires=True)
            # Cookie 文件损坏或格式不兼容时忽略，后续会重新登录获取新 Cookie
            except OSError:
                pass

    def _is_session_valid(self) -> bool:
        """检查缓存的 JSESSIONID Cookie 是否仍在有效期内"""
        if not os.path.exists(self.cookie_file):
            return False
        file_mtime = os.path.getmtime(self.cookie_file)
        ttl = self.config.get("session", {}).get("ttl", 7200)
        return (time.time() - file_mtime) < ttl

    def _has_jsessionid(self) -> bool:
        """检查 Cookie Jar 中是否有 JSESSIONID"""
        for cookie in self.cookie_jar:
            if cookie.name == "JSESSIONID":
                return True
        return False

    def get_session(self, force_refresh: bool = False) -> LWPCookieJar:
        """获取有效的 Cookie Jar，优先用缓存，过期或强制刷新则重新登录"""
        if not force_refresh and self._is_session_valid() and self._has_jsessionid():
            return self.cookie_jar

        server = self.config["server"]
        scheme = server.get("scheme", "https")
        host = server["host"]
        port = server["port"]
        base_path = server.get("base_path", "/web")

        auth = self.config["auth"]
        username = auth["username"]
        encrypted_password = auth["encrypted_password"]
        if not encrypted_password:
            raise RuntimeError("encrypted_password not set in config")
        password = decrypt(encrypted_password, self.config)

        url = f"{scheme}://{host}:{port}{base_path}/api/v2/login_check"

        ctx = _build_ssl_context(self.config)

        # 构造带 Basic Auth 和 Cookie 处理的 opener
        cookie_jar = LWPCookieJar()
        opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(cookie_jar),
            urllib.request.HTTPSHandler(context=ctx),
        )

        # login_check 使用 Basic Auth 认证
        # Basic Auth 认证：使用 bytes 操作避免凭据明文字符串残留
        _cred_bytes = b":".join([username.encode("utf-8"), password.encode("utf-8")])
        credentials = base64.b64encode(_cred_bytes).decode("utf-8")
        del _cred_bytes
        req = urllib.request.Request(
            url=url,
            data=b"",
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Authorization": f"Basic {credentials}",
            },
            method="POST",
        )

        try:
            res = opener.open(req, timeout=30)
            res.read()
            res.close()
        except urllib.error.HTTPError as e:
            # 某些 Manager 版本 login_check 返回 302/401 但仍设置 Cookie
            if e.code not in (302, 401):
                raise RuntimeError(f"Login failed: HTTP {e.code}")
        except Exception as e:
            raise RuntimeError(f"Login failed: {e}")

        # 保存 Cookie 到文件
        self.cookie_jar = cookie_jar
        try:
            cookie_jar.save(self.cookie_file, ignore_discard=True, ignore_expires=True)
        # Cookie 持久化失败不影响本次请求，下次会重新登录获取新 Cookie
        except OSError:
            pass

        return self.cookie_jar

    def get_basic_auth_header(self) -> str:
        """获取 Basic Auth 头（某些接口直接用 Basic Auth 更方便）"""
        auth = self.config["auth"]
        username = auth["username"]
        encrypted_password = auth["encrypted_password"]
        if not encrypted_password:
            raise RuntimeError("encrypted_password not set in config")
        password = decrypt(encrypted_password, self.config)
        # Basic Auth 认证：使用 bytes 操作避免凭据明文字符串残留
        _cred_bytes = b":".join([username.encode("utf-8"), password.encode("utf-8")])
        credentials = base64.b64encode(_cred_bytes).decode("utf-8")
        del _cred_bytes
        return f"Basic {credentials}"


def _build_url(config: dict, api_name: str, params: dict) -> str:
    """拼接完整请求 URL，替换路径中的 {param} 占位符"""
    server = config["server"]
    scheme = server.get("scheme", "https")
    host = server["host"]
    port = server["port"]
    base_path = server.get("base_path", "/web")
    api_def = config["apis"][api_name]
    path = api_def["path"]
    for key in params:
        placeholder = "{" + key + "}"
        if placeholder in path:
            path = path.replace(placeholder, str(params[key]))
    return f"{scheme}://{host}:{port}{base_path}{path}"


_MISSING = object()


def _resolve_template_value(value, params: dict):
    if isinstance(value, str):
        m = re.match(r"^\{(\w+)(?::([^}]*))?\}$", value)
        if m:
            param_name = m.group(1)
            default = m.group(2)
            if param_name in params and params[param_name] is not None:
                v = params[param_name]
                if isinstance(v, str):
                    try:
                        v = json.loads(v)
                    except (json.JSONDecodeError, TypeError):
                        bracket_match = re.match(r"^\[(.+)\]$", v.strip())
                        if bracket_match:
                            v = [item.strip() for item in bracket_match.group(1).split(",")]
                return v
            elif default is not None:
                try:
                    return json.loads(default)
                except (json.JSONDecodeError, TypeError):
                    return default
            else:
                return _MISSING
        if re.search(r"\{(\w+)(?::[^}]*)?\}", value):
            def replacer(m):
                param_name = m.group(1)
                default = m.group(2)
                if param_name in params and params[param_name] is not None:
                    return str(params[param_name])
                elif default is not None:
                    return default
                return ""
            return re.sub(r"\{(\w+)(?::([^}]*))?\}", replacer, value)
        return value
    elif isinstance(value, list):
        result = []
        for item in value:
            resolved = _resolve_template_value(item, params)
            if resolved is not _MISSING:
                result.append(resolved)
        return result if result else _MISSING
    elif isinstance(value, dict):
        result = {}
        for k, v in value.items():
            resolved = _resolve_template_value(v, params)
            if resolved is not _MISSING:
                result[k] = resolved
        return result if result else _MISSING
    return value


def _build_request_body(api_def: dict, params: dict) -> Optional[bytes]:
    template = api_def.get("request_body_template")
    if not template:
        return None
    if isinstance(template, str):
        m = re.match(r"^\{(\w+)(?::([^}]*))?\}$", template)
        if m:
            param_name = m.group(1)
            default = m.group(2)
            if param_name in params and params[param_name] is not None:
                v = params[param_name]
                if isinstance(v, str):
                    try:
                        json.loads(v)
                        return v.encode("utf-8")
                    except (json.JSONDecodeError, TypeError):
                        return json.dumps(v).encode("utf-8")
                return json.dumps(v).encode("utf-8")
            elif default is not None:
                return default.encode("utf-8")
            return None
    result = _resolve_template_value(template, params)
    if result is _MISSING:
        return None
    return json.dumps(result).encode("utf-8")


def _apply_response_filter(data: Any, response_filter: dict) -> Any:
    if not response_filter:
        return data
    if isinstance(data, list):
        first_key = next(iter(response_filter))
        return _apply_response_filter({first_key: data}, response_filter).get(first_key, data)
    if not isinstance(data, dict):
        return data
    result = dict(data)
    for array_key, fields in response_filter.items():
        if array_key not in result:
            continue
        arr = result[array_key]
        if not isinstance(arr, list):
            continue
        filtered = []
        for item in arr:
            if not isinstance(item, dict):
                filtered.append(item)
                continue
            new_item = {}
            for f in fields:
                if isinstance(f, str):
                    if f in item:
                        new_item[f] = item[f]
                elif isinstance(f, dict):
                    for parent_key, child_fields in f.items():
                        if parent_key in item and isinstance(item[parent_key], dict):
                            child = item[parent_key]
                            if isinstance(child_fields, str):
                                if child_fields in child:
                                    new_item[parent_key] = {child_fields: child[child_fields]}
                            elif isinstance(child_fields, list):
                                sub = {}
                                for cf in child_fields:
                                    if cf in child:
                                        sub[cf] = child[cf]
                                if sub:
                                    new_item[parent_key] = sub
            filtered.append(new_item)
        result[array_key] = filtered
    return result


def _validate_param(name: str, value: str, rules: dict):
    ptype = rules.get("type", "str")
    if ptype == "int":
        try:
            iv = int(value)
        except (ValueError, TypeError):
            raise ValueError(f"参数 {name} 必须为整数，当前值: {value}")
        if "min" in rules and iv < rules["min"]:
            raise ValueError(f"参数 {name} 不能小于 {rules['min']}，当前值: {iv}")
        if "max" in rules and iv > rules["max"]:
            raise ValueError(f"参数 {name} 不能大于 {rules['max']}，当前值: {iv}")
    elif ptype == "enum":
        allowed = rules.get("values", [])
        if value not in allowed:
            raise ValueError(f"参数 {name} 必须为 {allowed} 之一，当前值: {value}")
    elif ptype == "path":
        if "/.." in value or "\\.." in value:
            raise ValueError(f"参数 {name} 路径不允许包含 '..'，当前值: {value}")
        if "//" in value or "\\\\" in value:
            raise ValueError(f"参数 {name} 路径不允许包含连续分隔符，当前值: {value}")
        prefix = rules.get("prefix", "")
        if prefix and not value.startswith(prefix):
            raise ValueError(f"参数 {name} 路径必须以 '{prefix}' 开头，当前值: {value}")
    elif ptype == "str":
        pattern = rules.get("pattern", "")
        if pattern and not re.match(pattern, value):
            err = rules.get("error", f"参数 {name} 格式不匹配正则: {pattern}")
            raise ValueError(err)


def _validate_params(api_def: dict, params: dict):
    param_rules = api_def.get("param_rules", {})
    all_params = list(api_def.get("required_params", [])) + list(api_def.get("optional_params", []))
    for pname in all_params:
        if pname not in params or params[pname] is None:
            continue
        rules = param_rules.get(pname, {})
        if not rules:
            continue
        _validate_param(pname, params[pname], rules)


_default_cluster_id = None


def _get_default_cluster_id(config: dict, auth_mode: str = "basic") -> int:
    global _default_cluster_id
    if _default_cluster_id is not None:
        return _default_cluster_id
    result = call_api(config, "get_clusters", {}, auth_mode=auth_mode)
    if isinstance(result, list) and len(result) > 0:
        _default_cluster_id = result[0].get("id", 1)
    else:
        _default_cluster_id = 1
    return _default_cluster_id


def call_api(
    config: dict,
    api_name: str,
    params: dict,
    output_file: str = None,
    auth_mode: str = "basic",
    _is_retry: bool = False,
) -> Any:
    """通用接口调用

    auth_mode:
      - "basic": 使用 HTTP Basic Auth（默认，适合一次性调用）
      - "cookie": 使用 JSESSIONID Cookie（适合多次调用，减少认证开销）
    """
    if api_name not in config.get("apis", {}):
        raise ValueError(f"Unknown API: {api_name}. Available: {list(config.get('apis', {}).keys())}")

    api_def = config["apis"][api_name]
    method = api_def.get("method", "GET").upper()

    if "cluster_id" in api_def.get("required_params", []) and "cluster_id" not in params:
        params = dict(params)
        params["cluster_id"] = str(_get_default_cluster_id(config, auth_mode))

    for rp in api_def.get("required_params", []):
        if rp not in params or params[rp] is None:
            raise ValueError(f"Missing required param: {rp}")

    _validate_params(api_def, params)

    url = _build_url(config, api_name, params)
    ctx = _build_ssl_context(config)

    headers = {"Accept": "application/json"}

    # 根据认证模式设置请求头
    session_mgr = SessionManager(config)
    if auth_mode == "cookie":
        cookie_jar = session_mgr.get_session(force_refresh=_is_retry)
        # 将 Cookie 添加到请求头
        cookie_header = ""
        for cookie in cookie_jar:
            if cookie.name == "JSESSIONID":
                cookie_header = f"JSESSIONID={cookie.value}"
                break
        if cookie_header:
            headers["Cookie"] = cookie_header
    else:
        headers["Authorization"] = session_mgr.get_basic_auth_header()

    is_download = api_def.get("is_download", False)
    req_data = None

    if method in ("POST", "PUT", "DELETE"):
        headers["Content-Type"] = "application/json"
        body = _build_request_body(api_def, params)
        req_data = body if body else b"{}"

    if method == "GET" and not is_download:
        query_params = {}
        path_params = set()
        for key in params:
            placeholder = "{" + key + "}"
            if placeholder in api_def["path"]:
                path_params.add(key)
        all_get_params = list(api_def.get("required_params", [])) + list(api_def.get("optional_params", []))
        for p in all_get_params:
            if p in params and params[p] is not None and p not in path_params:
                query_params[p] = params[p]
        if query_params:
            url += "?" + urllib.parse.urlencode(query_params)

    req = urllib.request.Request(url=url, data=req_data, headers=headers, method=method)

    default_timeout = config.get("server", {}).get("timeout", 60)
    timeout = api_def.get("timeout", default_timeout)

    try:
        if auth_mode == "cookie":
            # Cookie 模式使用 opener 处理重定向和 Cookie
            cookie_jar = session_mgr.get_session()
            opener = urllib.request.build_opener(
                urllib.request.HTTPCookieProcessor(cookie_jar),
                urllib.request.HTTPSHandler(context=ctx),
            )
            res = opener.open(req, timeout=timeout)
        else:
            res = urllib.request.urlopen(req, context=ctx, timeout=timeout)

        if is_download:
            filename = api_def.get("output_filename", "download_output")
            if output_file:
                filename = output_file
            with open(filename, "wb") as f:
                while True:
                    chunk = res.read(8192)
                    if not chunk:
                        break
                    f.write(chunk)
            res.close()
            return {"status": "success", "file": os.path.abspath(filename)}

        # 检查 Content-Type，非 JSON 直接返回原始文本
        content_type = res.headers.get("Content-Type", "")
        raw_body = res.read()
        res.close()

        if "application/json" in content_type:
            try:
                return json.loads(raw_body.decode("utf-8"))
            except json.JSONDecodeError:
                return {"raw": raw_body.decode("utf-8", errors="replace")}
        else:
            return {"raw": raw_body.decode("utf-8", errors="replace")}

    except urllib.error.HTTPError as e:
        # Session 过期时自动刷新重试一次
        if e.code in (401, 403) and not _is_retry:
            if auth_mode == "cookie":
                return call_api(config, api_name, params, output_file=output_file,
                                auth_mode=auth_mode, _is_retry=True)
        try:
            error_body = json.loads(e.read().decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            error_body = {"http_status": e.code, "message": str(e)}
        return {"error": f"HTTP {e.code}", "detail": error_body}
    except Exception as e:
        return {"error": "EXCEPTION", "message": str(e)}


def main():
    parser = argparse.ArgumentParser(
        description="MRS Manager REST API 调用工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 列出所有可用接口
  python manager_api_client.py --list-apis

  # 查询OMS基本信息（Basic Auth）
  python manager_api_client.py -a get_oms_info

  # 查询集群告警（Basic Auth）
  python manager_api_client.py -a get_alarms -p 'cluster_id=1'

  # 查询主机列表（Cookie 认证，适合多次调用）
  python manager_api_client.py -a get_hosts --auth cookie

  # 查询服务监控指标
  python manager_api_client.py -a get_service_metrics -p 'cluster_id=1' -p 'service_name=HDFS' -p 'metric_names=dn_cpu_usage_allhost'

  # 加密密码（首次配置时使用，交互式输入）
  python manager_api_client.py --encrypt-password
        """,
    )

    parser.add_argument("-a", "--api", help="要调用的API名称")
    parser.add_argument("-p", "--param", action="append", default=[], help="接口参数，格式: key=value（可多次使用）")
    parser.add_argument("-o", "--output", help="下载文件保存路径（仅下载接口）")
    parser.add_argument("--auth", choices=["basic", "cookie"], default="basic",
                        help="认证方式: basic(HTTP Basic Auth) 或 cookie(JSESSIONID)，默认 basic")
    parser.add_argument("--list-apis", action="store_true", help="列出所有可用接口")
    parser.add_argument("--encrypt-password", action="store_true", help="加密密码并输出密文（用于配置文件），密码通过交互式输入")
    parser.add_argument("--json", action="store_true", help="JSON格式输出")
    parser.add_argument("--raw", action="store_true", help="输出原始响应（不格式化）")
    parser.add_argument("--full", action="store_true", help="输出完整返回值（默认精简，仅保留关键字段）")

    args = parser.parse_args()

    config = load_config()

    if args.encrypt_password:
        plain_password = getpass.getpass("请输入要加密的密码: ")
        if not plain_password:
            print("密码不能为空")
            return
        encrypted = encrypt(plain_password, config)
        print(f"加密后的密码: {encrypted}")
        print(f"请将此值填入配置文件 auth.encrypted_password 字段")
        return

    if args.list_apis:
        apis = config.get("apis", {})
        if args.json:
            print(json.dumps(apis, ensure_ascii=False, indent=2))
        else:
            print("可用接口列表:")
            print("-" * 80)
            for name, api_def in apis.items():
                method = api_def.get("method", "GET")
                path = api_def.get("path", "")
                desc = api_def.get("desc", "")
                required = ", ".join(api_def.get("required_params", []))
                optional = ", ".join(api_def.get("optional_params", []))
                print(f"  {name}")
                if desc:
                    print(f"    说明: {desc}")
                print(f"    方法: {method}  路径: {path}")
                print(f"    必填: {required or '无'}")
                print(f"    可选: {optional or '无'}")
                print()
        return

    if not args.api:
        parser.error("请指定 --api 参数或使用 --list-apis 查看可用接口")

    params = {}
    for p in args.param:
        if "=" not in p:
            parser.error(f"参数格式错误: {p}，应为 key=value")
        key, value = p.split("=", 1)
        params[key.strip()] = value.strip()

    result = call_api(config, args.api, params, output_file=args.output, auth_mode=args.auth)

    if not args.full and isinstance(result, (dict, list)):
        api_def = config.get("apis", {}).get(args.api, {})
        rf = api_def.get("response_filter")
        if rf:
            result = _apply_response_filter(result, rf)

    if args.raw and isinstance(result, dict) and "raw" in result:
        print(result["raw"])
    elif args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        if isinstance(result, dict) and "error" in result:
            print(f"错误: {result['error']}")
            if "detail" in result:
                print(json.dumps(result["detail"], ensure_ascii=False, indent=2))
            elif "message" in result:
                print(result["message"])
        else:
            print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
