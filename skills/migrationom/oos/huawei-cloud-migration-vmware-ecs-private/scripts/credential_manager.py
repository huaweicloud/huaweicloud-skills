#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
credential_manager.py — 凭证管理器 (v2.9.0)

安全规范:
  1. AK/SK 从环境变量读取 (migration_Access_Key / migration_Secret_Access_Key)
  2. 主机密码从环境变量读取 (migration_password)
  3. 加密缓存使用 AES-256-GCM，密钥由机器指纹派生
  4. 拒绝临时 AK/SK，不通过 IAM 创建/删除任何凭证
  5. AK/SK 变更时提示用户确认 (yes/no)
  6. 显示时脱敏 (如 HPUA****YPQY)，永不显示明文
  7. 环境变量仅在进程内使用，不写入磁盘配置文件

  v2.9.0 变更: 移除 RSA-4096 加密流程，改为环境变量直接读取。
  旧版 RSA 相关代码已移除。

Author: Migration Skill v2.9.0
"""

import os
import sys
import json
import hashlib
import base64
import getpass
import subprocess
import platform
import uuid
import time
import re
import logging
from pathlib import Path
from typing import Optional, Tuple, Dict, Any

# 加密库
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.backends import default_backend

logger = logging.getLogger(__name__)

# ── 常量 ──────────────────────────────────────────────
CACHE_DIR = Path.home() / ".migration_skill"
CACHE_FILE = CACHE_DIR / ".cred_cache"

AES_KEY_SIZE = 32  # 256-bit
AES_NONCE_SIZE = 12
SALT_SIZE = 16
PBKDF2_ITERATIONS = 100000

# 脱敏: 保留前4后4字符
MASK_KEEP_PREFIX = 4
MASK_KEEP_SUFFIX = 4

# ── 环境变量名 ──────────────────────────────────────
ENV_AK = "migration_Access_Key"
ENV_SK = "migration_Secret_Access_Key"
ENV_PWD = "migration_password"


class CredentialManager:
    """凭证管理器 — 环境变量读取 + AES 缓存 + 脱敏 + 变更检测"""

    def __init__(self):
        self._ensure_dirs()

    # ── 目录初始化 ─────────────────────────────────────
    def _ensure_dirs(self):
        """创建缓存目录，权限 700"""
        CACHE_DIR.mkdir(mode=0o700, exist_ok=True)

    # ── 机器指纹 ───────────────────────────────────────
    @staticmethod
    def _machine_fingerprint() -> bytes:
        """
        生成机器指纹 (用于派生 AES 缓存密钥)
        组合: hostname + machine-id + MAC + CPU
        """
        parts = []

        # hostname
        parts.append(platform.node())

        # /etc/machine-id 或 /var/lib/dbus/machine-id
        for mid_path in ["/etc/machine-id", "/var/lib/dbus/machine-id"]:
            try:
                with open(mid_path) as f:
                    parts.append(f.read().strip())
                    break
            except (IOError, OSError):
                continue

        # MAC 地址
        try:
            mac = uuid.getnode()
            parts.append(f"{mac:012x}")
        except Exception:
            pass

        # CPU 信息
        parts.append(platform.processor() or platform.machine())

        fp_str = "|".join(parts)
        return hashlib.sha256(fp_str.encode("utf-8")).digest()

    # ── AES 缓存密钥派生 ───────────────────────────────
    def _derive_cache_key(self, salt: bytes) -> bytes:
        """从机器指纹 + salt 派生 AES-256 密钥"""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=AES_KEY_SIZE,
            salt=salt,
            iterations=PBKDF2_ITERATIONS,
            backend=default_backend(),
        )
        return kdf.derive(self._machine_fingerprint())

    # ── 环境变量读取 AK/SK ─────────────────────────────
    @staticmethod
    def get_credentials_from_env() -> Tuple[Optional[str], Optional[str]]:
        """
        从环境变量读取 AK/SK

        环境变量:
          migration_Access_Key         — AK
          migration_Secret_Access_Key  — SK

        Returns: (ak, sk) 或 (None, None) 如果环境变量未设置
        """
        ak = os.environ.get(ENV_AK)
        sk = os.environ.get(ENV_SK)
        return ak, sk

    # ── 环境变量读取主机密码 ───────────────────────────
    @staticmethod
    def get_password_from_env() -> Optional[str]:
        """
        从环境变量读取主机密码

        环境变量:
          migration_password — 主机密码

        Returns: 密码字符串 或 None 如果环境变量未设置
        """
        return os.environ.get(ENV_PWD)

    # ── 检查环境变量是否已配置 ─────────────────────────
    @staticmethod
    def check_env_credentials() -> Tuple[bool, str]:
        """
        检查环境变量 AK/SK 是否已配置

        Returns: (True, "") 已配置; (False, msg) 未配置或缺失
        """
        ak = os.environ.get(ENV_AK)
        sk = os.environ.get(ENV_SK)

        if not ak and not sk:
            return False, (
                f"环境变量未配置。请设置以下环境变量:\n"
                f"  export {ENV_AK}='你的AK'\n"
                f"  export {ENV_SK}='你的SK'\n"
                f"  (主机密码等占位符环境变量请按 Excel 中 ${{...}} 引用配置)"
            )
        if not ak:
            return False, f"环境变量 {ENV_AK} 未设置"
        if not sk:
            return False, f"环境变量 {ENV_SK} 未设置"

        return True, ""

    # ── 多环境变量校验 (v2.9.1) ───────────────────────
    @staticmethod
    def validate_env_vars(required_vars: set) -> Tuple[bool, list, list]:
        """校验多个环境变量是否已配置

        Args:
            required_vars: 需要校验的环境变量名集合

        Returns:
            (all_set, missing, configured)
            - all_set: True 全部已配置
            - missing: 未配置的环境变量名列表
            - configured: 已配置的环境变量名列表
        """
        missing = []
        configured = []
        for var_name in sorted(required_vars):
            if os.environ.get(var_name):
                configured.append(var_name)
            else:
                missing.append(var_name)
        all_set = len(missing) == 0
        return all_set, missing, configured

    # ── 脱敏 ───────────────────────────────────────────
    @staticmethod
    def mask_credential(value: str) -> str:
        """
        脱敏显示: 保留前4后4，中间用 **** 替代
        例: HPUAYPQY... -> HPUA****YPQY
        短于 8 字符则全掩码
        """
        if not value:
            return "****"
        if len(value) <= MASK_KEEP_PREFIX + MASK_KEEP_SUFFIX:
            return "****"
        return (
            value[:MASK_KEEP_PREFIX]
            + "****"
            + value[-MASK_KEEP_SUFFIX:]
        )

    # ── AES 缓存写入 ───────────────────────────────────
    def save_to_cache(self, credentials: Dict[str, str]) -> None:
        """
        将凭证加密缓存到本地文件 (AES-256-GCM)
        文件权限 600

        credentials: {"ak": "...", "sk": "...", "region": "..."}
        """
        salt = os.urandom(SALT_SIZE)
        key = self._derive_cache_key(salt)
        nonce = os.urandom(AES_NONCE_SIZE)

        aesgcm = AESGCM(key)
        plaintext = json.dumps(credentials).encode("utf-8")
        ciphertext = aesgcm.encrypt(nonce, plaintext, None)

        # 格式: salt(16) + nonce(12) + ciphertext
        blob = salt + nonce + ciphertext
        CACHE_FILE.write_bytes(blob)
        os.chmod(str(CACHE_FILE), 0o600)
        logger.info("凭证已加密缓存: %s", CACHE_FILE)

    # ── AES 缓存读取 ───────────────────────────────────
    def load_from_cache(self) -> Optional[Dict[str, str]]:
        """
        从缓存读取并解密凭证
        Returns: {"ak": "...", "sk": "...", "region": "..."} 或 None
        """
        if not CACHE_FILE.exists():
            return None

        try:
            blob = CACHE_FILE.read_bytes()
            salt = blob[:SALT_SIZE]
            nonce = blob[SALT_SIZE : SALT_SIZE + AES_NONCE_SIZE]
            ciphertext = blob[SALT_SIZE + AES_NONCE_SIZE :]

            key = self._derive_cache_key(salt)
            aesgcm = AESGCM(key)
            plaintext = aesgcm.decrypt(nonce, ciphertext, None)
            return json.loads(plaintext.decode("utf-8"))
        except Exception as e:
            logger.warning("缓存读取失败: %s", e)
            return None

    # ── 缓存清除 ───────────────────────────────────────
    @staticmethod
    def clear_cache() -> None:
        """安全清除缓存文件"""
        if CACHE_FILE.exists():
            # 覆写后删除
            size = CACHE_FILE.stat().st_size
            with open(str(CACHE_FILE), "wb") as f:
                f.write(os.urandom(size))
            CACHE_FILE.unlink()
            logger.info("缓存已安全清除")

    # ── 变更检测 ───────────────────────────────────────
    def detect_change(self, new_ak: str, new_sk: str) -> bool:
        """
        检测 AK/SK 是否与缓存中的不同
        Returns: True 表示有变更
        """
        cached = self.load_from_cache()
        if not cached:
            return True

        return (new_ak != cached.get("ak")) or (new_sk != cached.get("sk"))

    # ── 确认变更 ───────────────────────────────────────
    @staticmethod
    def confirm_change(old_masked: str, new_masked: str) -> bool:
        """
        提示用户确认 AK/SK 变更
        显示脱敏值，要求 yes/no 确认
        """
        print(f"\n⚠️  您的 AK/SK 已经修改:")
        print(f"   旧 AK: {old_masked}")
        print(f"   新 AK: {new_masked}")
        print(f"   修改会重新配置使用 AK/SK 的进程、权限等")
        print()

        while True:
            answer = input("请确认是否修改 (yes/no): ").strip().lower()
            if answer in ("yes", "y"):
                return True
            if answer in ("no", "n"):
                return False
            print("请输入 yes 或 no")

    # ── 拒绝临时凭证 ───────────────────────────────────
    @staticmethod
    def reject_temporary() -> None:
        """
        拒绝临时 AK/SK — 永不通过 IAM 创建/删除凭证
        此方法仅为规范标记，调用时抛出异常
        """
        raise ValueError(
            "安全规范禁止: 不允许使用临时 AK/SK。"
            "请使用用户已有的永久 AK/SK。"
        )

    # ── 临时凭证检测 ───────────────────────────────────
    @staticmethod
    def is_temporary_ak(ak: str) -> bool:
        """
        检测 AK 是否为临时凭证

        华为云 AK 前缀规则:
          - HST  开头 → 临时凭证 (SecurityToken 方式获取)
          - HPUA 开头 → 永久凭证 (IAM 用户长期 AK)
          - 其他前缀也视为永久凭证 (兼容未来格式)

        Returns: True 表示临时凭证, False 表示永久凭证
        """
        if not ak or len(ak) < 3:
            return False
        return ak.startswith("HST")

    # ── 检查临时凭证 (只检测，禁止任何操作) ─────────────
    def check_temporary_credentials(self) -> Tuple[bool, str]:
        """
        检查缓存中的凭证是否为临时凭证 (只检测，禁止任何操作)

        Returns:
            (is_temporary, message)
            - (False, "") : 缓存为空或凭证为永久凭证，可正常使用
            - (True, msg) : 检测到临时凭证，禁止任何操作
        """
        cached = self.load_from_cache()
        if not cached:
            return False, ""

        ak = cached.get("ak", "")
        if self.is_temporary_ak(ak):
            masked_ak = self.mask_credential(ak)
            msg = (
                f"检测到临时凭证 (AK: {masked_ak}, HST前缀)。"
                "禁止使用临时 AK/SK 进行任何操作。"
                "原因: 迁移任务耗时较长，临时凭证一旦过期，"
                "导致后续任务停止，无法访问操作。"
                "请通过环境变量配置永久 AK/SK (HPUA前缀)。"
            )
            logger.warning(msg)
            return True, msg

        return False, ""

    # ── 永久凭证确认后作废临时凭证 ─────────────────────
    def invalidate_temporary_after_permanent(self, permanent_ak: str) -> bool:
        """
        在永久 AK/SK 验证通过并缓存后，作废临时凭证

        Args:
            permanent_ak: 已验证的永久 AK (用于确认确实是永久凭证)

        Returns:
            True 表示已作废临时凭证, False 表示无需作废
        """
        if self.is_temporary_ak(permanent_ak):
            logger.error("invalidate_temporary_after_permanent: 传入的 AK 仍是临时凭证，拒绝执行")
            return False

        self.clear_temporary_env_vars()
        logger.info("永久凭证已确认并缓存，临时凭证已作废")
        logger.info("永久 AK: %s (HPUA前缀)", self.mask_credential(permanent_ak))
        return True

    # ── 清除临时 AK/SK 环境变量 ───────────────────────
    @staticmethod
    def clear_temporary_env_vars() -> None:
        """
        清除所有临时 AK/SK 相关环境变量
        永久 AK/SK 验证通过后调用，确保临时凭证不再可用。
        """
        temp_env_keys = [
            "HUAWEICLOUD_SDK_AK",
            "HUAWEICLOUD_SDK_SK",
            "HUAWEICLOUD_SDK_SECURITY_TOKEN",
            "HWCloud_SDK_AK",
            "HWCloud_SDK_SK",
            "HWCloud_SDK_SecurityToken",
            "HW_ACCESS_KEY",
            "HW_SECRET_KEY",
            "HW_SECURITY_TOKEN",
        ]
        cleared = []
        for key in temp_env_keys:
            if key in os.environ:
                cleared.append(key)
                del os.environ[key]
        if cleared:
            logger.info("已清除临时环境变量: %s", ", ".join(cleared))

    # ── hcloud CLI 配置 ────────────────────────────────
    def configure_hcloud(self, ak: str, sk: str, region: str, security_token: str = None) -> bool:
        """
        配置 hcloud CLI 凭证 (通过环境变量，不写入 config 文件)
        显示脱敏 AK
        """
        logger.info("配置 hcloud CLI (AK: %s, region: %s)",
                     self.mask_credential(ak), region)

        env_vars = {
            "HWCloud_SDK_AK": ak,
            "HWCloud_SDK_SK": sk,
            "HWCloud_SDK_Region": region,
        }
        if security_token:
            env_vars["HWCloud_SDK_SecurityToken"] = security_token

        for key, val in env_vars.items():
            os.environ[key] = val

        return True

    # ── obsutil 配置 ──────────────────────────────────
    def configure_obsutil(self, ak: str, sk: str, region: str) -> bool:
        """
        配置 obsutil CLI 凭证 (联动更新)。
        obsutil 是华为云 OBS 命令行工具，用于文件上传/下载。
        配置方式: obsutil config -i=AK -k=SK -e=endpoint

        Returns: True 配置成功, False 失败 (非致命，仅警告)
        """
        logger.info("配置 obsutil (AK: %s, region: %s)",
                     self.mask_credential(ak), region)

        # 查找 obsutil
        obsutil_path = None
        for candidate in ["/usr/local/bin/obsutil", os.path.expanduser("~/.local/bin/obsutil"), "/usr/bin/obsutil"]:
            if os.path.exists(candidate) and os.access(candidate, os.X_OK):
                obsutil_path = candidate
                break
        if not obsutil_path:
            try:
                r = subprocess.run(["which", "obsutil"], capture_output=True, text=True, timeout=5)
                if r.returncode == 0 and r.stdout.strip():
                    obsutil_path = r.stdout.strip()
            except Exception:
                pass

        if not obsutil_path:
            logger.warning("obsutil 未安装，跳过 obsutil 配置 (非致命)")
            return False

        # 构建 OBS endpoint
        obs_endpoint = f"obs.{region}.myhuaweicloud.com"

        try:
            result = subprocess.run(
                [obsutil_path, "config", f"-i={ak}", f"-k={sk}", f"-e={obs_endpoint}"],
                capture_output=True, text=True, timeout=30,
            )
            if result.returncode == 0:
                logger.info("obsutil 配置成功 (endpoint=%s)", obs_endpoint)
                return True
            else:
                logger.warning("obsutil 配置失败 (code=%d): %s", result.returncode, result.stderr[:200])
                return False
        except Exception as e:
            logger.warning("obsutil 配置异常: %s", e)
            return False

    # ── SMS Agent 配置 ────────────────────────────────
    def configure_sms_agent(self, ak: str, sk: str, region: str) -> bool:
        """
        配置 SMS Agent 凭证 (联动更新)。
        SMS Agent 通过 hcloud CLI 间接使用 AK/SK (环境变量)。

        Returns: True 配置成功, False 失败 (非致命，仅警告)
        """
        logger.info("配置 SMS Agent 凭证 (AK: %s, region: %s)",
                     self.mask_credential(ak), region)

        env_ak = os.environ.get("HWCloud_SDK_AK", "")
        if env_ak != ak:
            os.environ["HWCloud_SDK_AK"] = ak
            os.environ["HWCloud_SDK_SK"] = sk
            os.environ["HWCloud_SDK_Region"] = region
            logger.info("SMS Agent: 环境变量已同步更新")
        else:
            logger.info("SMS Agent: 环境变量已一致，无需更新")

        # 检查 SMS Agent 配置文件 (如果存在)
        sms_agent_conf_paths = [
            "/usr/local/sms-agent/conf/agent.conf",
            "/tmp/sms-agent-*/conf/agent.conf",
        ]
        import glob
        for pattern in sms_agent_conf_paths:
            for conf_path in glob.glob(pattern):
                if os.path.exists(conf_path):
                    logger.info("SMS Agent 配置文件存在: %s (AK/SK 通过 hcloud 环境变量传递)", conf_path)

        return True

    # ── 凭证验证 ───────────────────────────────────────
    @staticmethod
    def verify_credentials(ak: str, sk: str, region: str = "cn-north-1") -> Tuple[bool, str]:
        """
        验证 AK/SK 是否可用 (通过 hcloud CLI 发起只读 API 调用)
        Returns: (True, "") 验证通过; (False, error_msg) 验证失败
        """
        env = os.environ.copy()
        env["HUAWEICLOUD_SDK_AK"] = ak
        env["HUAWEICLOUD_SDK_SK"] = sk
        env["HUAWEICLOUD_SDK_REGION"] = region

        try:
            proc = subprocess.run(
                ["hcloud", "IAM", "KeystoneListAuthDomains", f"--cli-region={region}"],
                capture_output=True,
                text=True,
                timeout=30,
                env=env,
            )
            if proc.returncode == 0:
                if "error_code" in proc.stdout or "error_code" in proc.stderr:
                    err = "API 返回错误"
                    if "error_msg" in proc.stdout:
                        err = proc.stdout.strip()
                    return False, err
                logger.info("凭证验证通过 (AK: %s, region: %s)",
                            CredentialManager.mask_credential(ak), region)
                return True, ""
            else:
                err_msg = proc.stderr.strip() or proc.stdout.strip() or f"退出码 {proc.returncode}"
                logger.warning("凭证验证失败: %s", err_msg)
                return False, err_msg
        except FileNotFoundError:
            return False, "hcloud CLI 未安装或不在 PATH 中"
        except subprocess.TimeoutExpired:
            return False, "验证请求超时 (30s)"
        except Exception as e:
            return False, f"验证异常: {e}"

    # ── 验证并重试 (环境变量方式) ──────────────────────
    def verify_and_retry(
        self,
        region: str = "cn-north-1",
        max_retries: int = 3,
    ) -> Tuple[str, str]:
        """
        从环境变量读取 AK/SK 并验证，验证不通过则提示用户重新设置环境变量
        Returns: (ak, sk) 验证通过的明文凭证
        Raises: ValueError 超过最大重试次数或环境变量未设置
        """
        for attempt in range(1, max_retries + 1):
            # 1. 从环境变量读取
            ak, sk = self.get_credentials_from_env()
            if not ak or not sk:
                msg = (
                    f"环境变量未设置。请先设置:\n"
                    f"  export {ENV_AK}='你的AK'\n"
                    f"  export {ENV_SK}='你的SK'"
                )
                logger.error("第 %d 次尝试 — %s", attempt, msg)
                if attempt < max_retries:
                    print(f"\n❌ {msg}")
                    print("设置后按回车继续...")
                    input()
                    continue
                else:
                    raise ValueError(msg)

            # 2. 验证
            ok, err = self.verify_credentials(ak, sk, region)
            if ok:
                logger.info("凭证验证通过 (第 %d 次尝试)", attempt)
                return ak, sk

            # 3. 验证失败
            logger.error("第 %d 次尝试 — 凭证验证失败: %s", attempt, err)
            if attempt < max_retries:
                print(f"\n❌ 凭证验证失败: {err}")
                print(f"   当前 AK (脱敏): {self.mask_credential(ak)}")
                print(f"   请检查环境变量 {ENV_AK} 和 {ENV_SK} 是否正确。")
                print("   修正后按回车继续...")
                input()
            else:
                raise ValueError(
                    f"凭证验证失败，已重试 {max_retries} 次。最后错误: {err}"
                )

    # ── 完整凭证获取流程 (环境变量方式) ─────────────────
    def get_credentials(
        self,
        region: str = "cn-north-1",
        force_update: bool = False,
    ) -> Dict[str, str]:
        """
        完整凭证获取流程 (v2.9.0 环境变量方式):
        1. 从环境变量读取 AK/SK
        2. 变更检测 — 如有变更提示用户确认 (force_update=True 时跳过)
        3. 加密缓存 (AES)
        4. 配置 hcloud CLI + obsutil + SMS Agent (联动更新)
        5. 返回凭证字典 (脱敏)

        Args:
            region: 华为云区域
            force_update: 强制使用新读取的 AK/SK，跳过变更检测

        Returns: {"ak_masked": "HPUA****YPQY", "sk_masked": "****",
                  "region": "cn-north-1", "configured": True}
        """
        # 1. 从环境变量读取
        ak, sk = self.get_credentials_from_env()
        if not ak or not sk:
            raise ValueError(
                f"环境变量未设置。请先设置:\n"
                f"  export {ENV_AK}='你的AK'\n"
                f"  export {ENV_SK}='你的SK'\n"
                f"  export {ENV_PWD}='主机密码'"
            )

        # 2. 变更检测 (force_update=True 时跳过)
        if not force_update:
            cached = self.load_from_cache()
            if cached:
                old_ak_masked = self.mask_credential(cached.get("ak", ""))
                new_ak_masked = self.mask_credential(ak)

                if cached.get("ak") != ak or cached.get("sk") != sk:
                    if not self.confirm_change(old_ak_masked, new_ak_masked):
                        logger.info("用户取消变更，使用缓存凭证")
                        ak = cached["ak"]
                        sk = cached["sk"]
                        region = cached.get("region", region)
        else:
            logger.info("force_update=True，跳过变更检测，强制使用环境变量中的 AK/SK")

        # 3. 缓存
        creds = {"ak": ak, "sk": sk, "region": region}
        self.save_to_cache(creds)

        # 4. 联动配置 hcloud CLI + obsutil + SMS Agent
        self.configure_hcloud(ak, sk, region)
        self.configure_obsutil(ak, sk, region)
        self.configure_sms_agent(ak, sk, region)

        # 5. 返回脱敏信息
        return {
            "ak_masked": self.mask_credential(ak),
            "sk_masked": self.mask_credential(sk),
            "region": region,
            "configured": True,
        }

    # ── v2.9.0: 信息安全防护 ────────────────────────────
    @staticmethod
    def guard_aksk_leak(filepath: str, content: str = None) -> bool:
        """
        防止 AK/SK 明文泄露到非业务存储

        检测目标路径是否为非业务相关存储 (如公网可达目录、临时目录)，
        如果写入内容包含 AK/SK 明文特征，拦截并告警。

        Args:
            filepath: 目标文件路径
            content: 待写入内容 (可选)

        Returns:
            True 表示安全可写入, False 表示检测到风险已拦截
        """
        risky_paths = ["/tmp/", "/var/tmp/", "/dev/shm/", "public", "download"]
        is_risky = any(p in filepath for p in risky_paths)

        if content and is_risky:
            aksk_pattern = re.compile(r'(HPUA|HST)[A-Z0-9]{20,}')
            if aksk_pattern.search(content):
                logger.error(
                    "信息安全违规: 检测到 AK/SK 明文写入非业务存储路径 %s，已拦截",
                    filepath
                )
                return False

        return True

    # ── batch_migrate 适配方法 ──────────────────────────
    def get_cached_credentials(self) -> Optional[Dict[str, str]]:
        """获取缓存的凭证 (适配 batch_migrate 调用)"""
        return self.load_from_cache()

    def has_cached_credentials(self) -> bool:
        """检查是否存在已缓存的凭证"""
        return self.load_from_cache() is not None

    def cache_credentials(self, ak: str, sk: str) -> None:
        """缓存凭证 (适配 batch_migrate 调用)"""
        self.save_to_cache({"ak": ak, "sk": sk})

    @staticmethod
    def mask_ak(ak: str) -> str:
        """脱敏 AK (适配 batch_migrate 调用)"""
        return CredentialManager.mask_credential(ak)


# ── CLI 入口 ──────────────────────────────────────────
def main():
    """命令行入口"""
    import argparse

    parser = argparse.ArgumentParser(
        description="凭证管理器 v2.9.0 — 环境变量读取 + AES 缓存"
    )
    sub = parser.add_subparsers(dest="command")

    # check-env: 检查环境变量是否已配置
    sub.add_parser("check-env", help="检查环境变量 AK/SK 是否已配置")

    # get-creds: 从环境变量读取并验证
    p_get = sub.add_parser("get-creds", help="从环境变量读取 AK/SK 并验证")
    p_get.add_argument("--region", default="cn-north-1", help="华为云区域")

    # mask: 脱敏显示
    p_mask = sub.add_parser("mask", help="脱敏显示")
    p_mask.add_argument("value", help="要脱敏的值")

    # clear-cache: 安全清除缓存
    sub.add_parser("clear-cache", help="安全清除缓存")

    args = parser.parse_args()
    mgr = CredentialManager()

    if args.command == "check-env":
        ok, msg = mgr.check_env_credentials()
        if ok:
            ak, sk = mgr.get_credentials_from_env()
            print("✅ 环境变量已配置")
            print(f"   AK (脱敏): {mgr.mask_credential(ak)}")
            print(f"   SK (脱敏): {mgr.mask_credential(sk)}")
        else:
            print(f"❌ {msg}")
            sys.exit(1)

    elif args.command == "get-creds":
        try:
            result = mgr.get_credentials(region=args.region)
            print("✅ 凭证获取并配置成功")
            print(f"   AK (脱敏): {result['ak_masked']}")
            print(f"   SK (脱敏): {result['sk_masked']}")
            print(f"   Region: {result['region']}")
        except ValueError as e:
            print(f"❌ {e}")
            sys.exit(1)

    elif args.command == "mask":
        print(mgr.mask_credential(args.value))

    elif args.command == "clear-cache":
        mgr.clear_cache()
        print("✅ 缓存已安全清除")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
