#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LakeWatch API 调用脚本
通过参数和YAML配置文件拼接URL请求，访问LakeWatch服务
支持Token自动管理（缓存+过期刷新）、密码加密存储、接口可扩展
"""

import argparse
import base64
import hashlib
import getpass
import json
import os
import platform
import re
import ssl
import stat
import subprocess
import tempfile
import time
import urllib.parse
import urllib.request
from typing import Any, Optional

import yaml


CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lakewatch_api_config.yaml")
# Windows 用 AES 加密，Linux 用 CryptoAPI
IS_WINDOWS = platform.system() == "Windows"


def load_config() -> dict:
    """加载 YAML 配置文件"""
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _get_default_token_cache_dir() -> str:
    """获取系统临时目录下的 Token 缓存路径"""
    tmp = os.environ.get("TEMP") or os.environ.get("TMP") or os.environ.get("TMPDIR", "/tmp")
    return os.path.join(tmp, "lakewatch_token")


def _aes_key_path(config: dict) -> str:
    """获取 AES 密钥文件路径"""
    key_file = config.get("crypto", {}).get("aes_key_file", "")
    if key_file:
        return key_file
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), ".aes_key")


def _ensure_aes_key(config: dict) -> bytes:
    """确保 AES 密钥存在，不存在则原子写入生成"""
    # 密钥文件不存在时自动生成 32 字节随机密钥，使用原子写入防止竞态
    key_path = _aes_key_path(config)
    if os.path.exists(key_path):
        with open(key_path, "r", encoding="utf-8") as f:
            return bytes.fromhex(f.read().strip())
    key = os.urandom(32)
    fd, tmp_path = tempfile.mkstemp(dir=os.path.dirname(key_path), suffix=".tmp")
    try:
        os.write(fd, key.hex().encode("utf-8"))
        os.close(fd)
        os.chmod(tmp_path, stat.S_IRUSR | stat.S_IWUSR)
        os.replace(tmp_path, key_path)
    except Exception:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise
    return key


def _aes_encrypt(plain_text: str, config: dict) -> str:
    """AES-256-CBC 加密，输出 Base64(IV + 密文)"""
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    from cryptography.hazmat.primitives import padding as sym_padding
    key = _ensure_aes_key(config)
    iv = os.urandom(16)
    padder = sym_padding.PKCS7(128).padder()
    padded = padder.update(plain_text.encode("utf-8")) + padder.finalize()
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
    encryptor = cipher.encryptor()
    ct = encryptor.update(padded) + encryptor.finalize()
    return base64.b64encode(iv + ct).decode("utf-8")


def _aes_decrypt(cipher_text: str, config: dict) -> str:
    """AES-256-CBC 解密"""
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
    """调用华为 CryptoAPI 二进制进行加解密，crypto_type: e=加密 d=解密"""
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
    # 输出格式为 "prefix:value"，取冒号后部分
    output = proc.stdout.strip()
    if ":" in output:
        output = output.split(":", 1)[1]
    return output


def encrypt(plain_text: str, config: dict) -> str:
    """加密：Windows 用 AES，Linux 用 CryptoAPI"""
    if IS_WINDOWS:
        return _aes_encrypt(plain_text, config)
    return _call_crypto_api(plain_text, "e", config)


def decrypt(cipher_text: str, config: dict) -> str:
    """解密：Windows 用 AES，Linux 用 CryptoAPI"""
    if IS_WINDOWS:
        return _aes_decrypt(cipher_text, config)
    return _call_crypto_api(cipher_text, "d", config)


def _build_ssl_context(config: dict) -> ssl.SSLContext:
    """根据配置构建 SSL 上下文，支持跳过验证和自定义 CA 证书"""
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


class TokenManager:
    # Token 缓存至本地文件（加密存储），过期自动刷新（默认1天）
    def __init__(self, config: dict):
        self.config = config
        cache_dir = config.get("token", {}).get("cache_dir", "")
        if not cache_dir:
            cache_dir = _get_default_token_cache_dir()
        os.makedirs(cache_dir, exist_ok=True)
        # Linux 设置目录权限仅所有者可访问
        if not IS_WINDOWS:
            os.chmod(cache_dir, stat.S_IRWXU)
        self.token_file = os.path.join(cache_dir, "token.json")

    def _is_token_valid(self, token_data: dict) -> bool:
        """检查缓存 Token 是否仍在有效期内"""
        if "token" not in token_data or "timestamp" not in token_data:
            return False
        # 以收到 Token 时的本地时间为基准 + ttl 判断过期
        ttl = self.config.get("token", {}).get("ttl", 86400)
        return (time.time() - token_data["timestamp"]) < ttl

    def get_token(self, force_refresh: bool = False) -> str:
        """获取 Token，优先用缓存，过期或强制刷新则重新请求"""
        if not force_refresh:
            cached = self._load_cached_token()
            if cached and self._is_token_valid(cached):
                return cached["token"]

        server = self.config["server"]
        scheme = server.get("scheme", "https")
        host = server["host"]
        port = server["port"]

        auth = self.config["auth"]
        username = auth["username"]
        encrypted_password = auth["encrypted_password"]
        if not encrypted_password:
            raise RuntimeError("encrypted_password not set in config")
        password = decrypt(encrypted_password, self.config)

        url = f"{scheme}://{host}:{port}/lakewatch/v1/system/get-token"
        payload = json.dumps({"username": username, "password": password}).encode("utf-8")

        ctx = _build_ssl_context(self.config)

        req = urllib.request.Request(
            url=url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            res = urllib.request.urlopen(req, context=ctx)
            body = json.loads(res.read().decode("utf-8"))
            res.close()
        except Exception as e:
            raise RuntimeError(f"Failed to get token: {e}")

        # 接口返回格式: {"code": "200", "data": {"token": "xxx", "expireTime": "..."}}
        data = body.get("data") or body
        if isinstance(data, dict):
            token = data.get("token") or data.get("access_token", "")
        else:
            token = str(data)

        if not token:
            raise RuntimeError(f"Token not found in response: {body}")

        self._save_token(token)
        return token

    def _load_cached_token(self) -> Optional[dict]:
        """从缓存文件加载并解密 Token"""
        if not os.path.exists(self.token_file):
            return None
        try:
            with open(self.token_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            # Token 加密存储，需解密
            if "encrypted_token" in data:
                data["token"] = decrypt(data["encrypted_token"], self.config)
            return data
        except (json.JSONDecodeError, IOError):
            return None

    def _save_token(self, token: str):
        """加密 Token 后原子写入缓存文件"""
        encrypted_token = encrypt(token, self.config)
        content = json.dumps({
            "encrypted_token": encrypted_token,
            "timestamp": time.time(),
        })
        # 原子写入：先写临时文件再 rename，防止写到一半损坏
        fd, tmp_path = tempfile.mkstemp(dir=os.path.dirname(self.token_file), suffix=".tmp")
        try:
            os.write(fd, content.encode("utf-8"))
            os.close(fd)
            if not IS_WINDOWS:
                os.chmod(tmp_path, stat.S_IRUSR | stat.S_IWUSR)
            os.replace(tmp_path, self.token_file)
        except Exception:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            raise


def _build_url(config: dict, api_name: str, params: dict) -> str:
    """拼接完整请求 URL，替换路径中的 {param} 占位符"""
    server = config["server"]
    scheme = server.get("scheme", "https")
    host = server["host"]
    port = server["port"]
    api_def = config["apis"][api_name]
    path = api_def["path"]
    for key in params:
        val = str(params[key])
        placeholder = "{" + key + "}"
        if placeholder in path:
            path = path.replace(placeholder, urllib.parse.quote(val, safe=""))
        wildcard = "{*" + key + "}"
        if wildcard in path:
            path = path.replace(wildcard, urllib.parse.quote(val, safe="/?=&"))
    return f"{scheme}://{host}:{port}{path}"


def _build_request_body(api_def: dict, params: dict) -> Optional[dict]:
    """根据配置的 request_body 映射构建 POST 请求体"""
    body_map = api_def.get("request_body", {})
    if not body_map:
        return None
    body = {}
    for param_name, json_key in body_map.items():
        if param_name in params and params[param_name] is not None:
            value = params[param_name]
            if isinstance(value, str):
                try:
                    value = json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    pass
            body[json_key] = value
    return body if body else None


def _validate_param(name: str, value: str, rules: dict):
    """根据 YAML 中配置的校验规则验证参数值"""
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
    """校验所有传入参数（必填+可选），根据 YAML 中的 param_rules 配置"""
    param_rules = api_def.get("param_rules", {})
    all_params = list(api_def.get("required_params", [])) + list(api_def.get("optional_params", []))
    for pname in all_params:
        if pname not in params or params[pname] is None:
            continue
        rules = param_rules.get(pname, {})
        if not rules:
            continue
        _validate_param(pname, params[pname], rules)


def call_api(config: dict, api_name: str, params: dict, output_file: str = None, _is_retry: bool = False) -> Any:
    """通用接口调用：自动获取 Token、构建请求、处理响应，401 时自动重试"""
    if api_name not in config.get("apis", {}):
        raise ValueError(f"Unknown API: {api_name}. Available: {list(config.get('apis', {}).keys())}")

    api_def = config["apis"][api_name]
    method = api_def.get("method", "GET").upper()

    for rp in api_def.get("required_params", []):
        if rp not in params or params[rp] is None:
            raise ValueError(f"Missing required param: {rp}")

    _validate_params(api_def, params)

    token_manager = TokenManager(config)
    token = token_manager.get_token()

    url = _build_url(config, api_name, params)

    ctx = _build_ssl_context(config)

    headers = {"X-LW-Token": token}

    is_download = api_def.get("is_download", False)
    req_data = None

    if method == "POST":
        headers["Content-Type"] = "application/json"
        body = _build_request_body(api_def, params)
        req_data = json.dumps(body).encode("utf-8") if body else b"{}"

    if method == "GET" and not is_download:
        query_params = {}
        for p in api_def.get("optional_params", []):
            if p in params and params[p] is not None:
                query_params[p] = params[p]
        if query_params:
            url += "?" + urllib.parse.urlencode(query_params)

    req = urllib.request.Request(url=url, data=req_data, headers=headers, method=method)

    default_timeout = config.get("server", {}).get("timeout", 60)
    timeout = api_def.get("timeout", default_timeout)

    try:
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

        body = json.loads(res.read().decode("utf-8"))
        res.close()
        return body
    except urllib.error.HTTPError as e:
        # Token 过期时自动刷新重试一次
        if e.code == 401 and not _is_retry:
            token_manager = TokenManager(config)
            new_token = token_manager.get_token(force_refresh=True)
            headers["X-LW-Token"] = new_token
            req = urllib.request.Request(url=url, data=req_data, headers=headers, method=method)
            return call_api(config, api_name, params, output_file=output_file, _is_retry=True)
        try:
            error_body = json.loads(e.read().decode("utf-8"))
        except Exception:
            error_body = {"http_status": e.code, "message": str(e)}
        return {"error": f"HTTP {e.code}", "detail": error_body}
    except Exception as e:
        return {"error": "EXCEPTION", "message": str(e)}


def main():
    """命令行入口：解析参数并执行对应操作"""
    parser = argparse.ArgumentParser(
        description="LakeWatch API 调用工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 列出所有可用接口
  python lakewatch_api_client.py --list-apis

  # 收集节点资源数据
  python lakewatch_api_client.py -a collect_alarm_node_res_data -p cluster_id=xxx -p resource_type=system-load

  # 收集告警日志数据
  python lakewatch_api_client.py -a collect_alarm_log_data -p cluster_id=xxx -p alarm_time="2026/06/11 16:00:32" -p log_directory=/var/log -p log_file_name=xxx -p keywords='["ERROR"]'

  # 加密密码（首次配置时使用，交互式输入）
  python lakewatch_api_client.py --encrypt-password
        """,
    )

    parser.add_argument("-a", "--api", help="要调用的API名称")
    parser.add_argument("-p", "--param", action="append", default=[], help="接口参数，格式: key=value（可多次使用）")
    parser.add_argument("-o", "--output", help="下载文件保存路径（仅下载接口）")
    parser.add_argument("--list-apis", action="store_true", help="列出所有可用接口")
    parser.add_argument("--encrypt-password", action="store_true", help="加密密码并输出密文（用于配置文件），密码通过交互式输入")
    parser.add_argument("--json", action="store_true", help="JSON格式输出")

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

    if args.api == "get_token":
        tm = TokenManager(config)
        token = tm.get_token()
        fingerprint = hashlib.md5(token.encode()).hexdigest()[:8]
        if args.json:
            print(json.dumps({"status": "ok", "len": len(token), "md5": fingerprint}, ensure_ascii=False, indent=2))
        else:
            print(f"Token获取成功 (len={len(token)}, md5={fingerprint})")
        return

    result = call_api(config, args.api, params, output_file=args.output)
    if args.json:
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
