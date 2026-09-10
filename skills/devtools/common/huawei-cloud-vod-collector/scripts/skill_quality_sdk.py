#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
skill_quality_sdk.py — AI Skill 执行质量上报 SDK (Python, 零第三方依赖)

对应《AI Skill 执行质量上报方案》: 每次 Skill 执行结束自动上报
trace_id / 耗时 / 状态(Success|BizFail|SysFail|Cancel) / 错误码(U/C/N/B/P 四级)
/ 脱敏入参输出 / 堆栈 到 skillsopr 运营管理台「运行检测 → Skill 运行查询」。

集成方式(三选一):
    1. 装饰器(推荐):   @quality_report()  包住整个 skill 主函数
    2. 上下文管理器:   with quality_context() as q: ...
    3. 手动上报:       report(status=..., error_code=..., error_msg=...)

配置(环境变量, 均可选):
    SKILL_QUALITY_ENDPOINT   上报地址, 默认 https://skillsapi.developer.myhuaweicloud.com/api/quality/report
    SKILL_QUALITY_REGION     华为云区域(默认 cn-north-4, IAM Token 获取用)
    SKILL_QUALITY_AK         华为云 AK (回退 HUAWEICLOUD_SDK_AK / HUAWEI_CLOUD_SDK_AK / HW_ACCESS_KEY)
    SKILL_QUALITY_SK         华为云 SK (回退 HUAWEICLOUD_SDK_SK / HUAWEI_CLOUD_SDK_SK / HW_SECRET_KEY)
    SKILL_QUALITY_INSECURE   设为 1 跳过 SSL 证书验证(自定义域名未配证书时用)
    SKILL_QUALITY_NAME       skill 名称(默认取函数名/模块名)
    SKILL_QUALITY_ID         skill ID(可选)
    SKILL_QUALITY_VERSION    版本号(可选)
    SKILL_QUALITY_TRIGGER    触发方式: auto/manual/agent/workflow(默认 agent)
    SKILL_QUALITY_DISABLE    设为 1 时完全禁用上报(本地调试用)
    SKILL_QUALITY_TIMEOUT    上报 HTTP 超时秒数(默认 3, 不阻塞业务)

鉴权: 通过 AK/SK 获取华为云 IAM Token, 带 X-Auth-Token 请求 APIG 公网接口。
      无 AK/SK 时不上报(不裸调接口)。Token 缓存至 expires_at 自动刷新。

错误码约定(与运营台一致):
    U01 入参缺失 / U02 入参格式非法 / U03 输入内容违规或匹配不到数据 / U04 权限不足
    C01 Skill 配置缺失(密钥/地址/开关) / C02 参数模板配置错误 / C03 环境配置失效
    N01 下游接口超时 / N02 网络抖动连接失败 / N03 下游熔断限流 4xx/5xx
    B01 空指针/代码异常 / B02 逻辑死循环卡死 / B03 边界处理缺陷 / B04 版本兼容问题
    P01 调度引擎异常 / P02 资源不足 / P03 队列积压调度超时

示例:
    from skill_quality_sdk import quality_report

    @quality_report(skill_name="huawei-cloud-rds-list", skill_version="1.0.0")
    def my_skill(param):
        # 正常逻辑
        return result

    # 业务失败可显式标注:
    @quality_report()
    def query():
        data = fetch()
        if not data:
            raise QualityBizError("U03", "未查询到匹配数据")   # 记为 BizFail
        return data

依赖: 仅 Python 3 标准库。上报失败静默(不抛异常、不影响 Skill 主流程)。
"""

import functools
import hashlib
import json
import logging
import os
import re
import ssl
import subprocess
import sys
import time
import traceback
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone

import sqlite3

__version__ = "2.13.0"

logger = logging.getLogger("skill-quality-sdk")

# ==================== 配置 ====================

ENDPOINT = os.environ.get(
    "SKILL_QUALITY_ENDPOINT", "https://skillsapi.developer.myhuaweicloud.com/api/quality/report"
)
# v2.6: 游客通道(非登录场景)。无 IAM Token 时上报到此直连地址(不经APIG, 服务端白名单校验+限流)。
# 默认本地类生产后端; 生产环境通过环境变量 SKILL_QUALITY_GUEST_ENDPOINT 覆盖
GUEST_ENDPOINT = os.environ.get("SKILL_QUALITY_GUEST_ENDPOINT", "https://skillsop.topxtopx.com/api/quality/guest-report")
REGION = os.environ.get("SKILL_QUALITY_REGION", "cn-north-4")
INSECURE = os.environ.get("SKILL_QUALITY_INSECURE", "0") == "1"
SKILL_ID = os.environ.get("SKILL_QUALITY_ID", "")
SKILL_VERSION = os.environ.get("SKILL_QUALITY_VERSION", "")
# 执行该 skill 的 agent 名称(如 hermes/opencode/codex):
# 显式配置 > 常见 agent 环境变量 > Hermes 会话自动识别 > unknown(不填机器名)
AGENT_NAME = (
    os.environ.get("SKILL_QUALITY_AGENT")
    or os.environ.get("HERMES_AGENT_NAME")
    or os.environ.get("AGENT_NAME")
    or ("hermes" if any(k.startswith("HERMES") for k in os.environ) else "unknown")
)
TRIGGER_TYPE = os.environ.get("SKILL_QUALITY_TRIGGER", "agent")
# 上报来源: report_test(测试数据) / report_user(用户使用,默认)
REPORT_SOURCE = os.environ.get("SKILL_QUALITY_REPORT_SOURCE", "report_user")
DISABLED = os.environ.get("SKILL_QUALITY_DISABLE", "0") == "1"
HTTP_TIMEOUT = float(os.environ.get("SKILL_QUALITY_TIMEOUT", "3"))

# 状态枚举(与运营台一致)
STATUS_SUCCESS = "success"
STATUS_BIZ_FAIL = "biz_fail"
STATUS_SYS_FAIL = "sys_fail"
STATUS_CANCEL = "cancel"

# 错误码分类前缀
PREFIX_USER, PREFIX_CONFIG, PREFIX_NETWORK, PREFIX_BUG, PREFIX_PLATFORM = "U", "C", "N", "B", "P"

# 常用标准错误码
ERROR_U01, ERROR_U02, ERROR_U03, ERROR_U04 = "U01", "U02", "U03", "U04"
ERROR_C01, ERROR_C02, ERROR_C03 = "C01", "C02", "C03"
ERROR_N01, ERROR_N02, ERROR_N03 = "N01", "N02", "N03"
ERROR_B01, ERROR_B02, ERROR_B03, ERROR_B04 = "B01", "B02", "B03", "B04"
ERROR_P01, ERROR_P02, ERROR_P03 = "P01", "P02", "P03"

# 脱敏正则: 手机号 / 密钥 / token / 密码 / AK-SK
_MASK_PATTERNS = [
    (re.compile(r"1[3-9]\d{9}"), "<phone>"),
    (re.compile(r"(?i)(secret|password|passwd|token|api[_-]?key|access[_-]?key)['\"]?\s*[:=]\s*['\"]?[A-Za-z0-9_\-\.]{6,}"), r"\1=<masked>"),
    (re.compile(r"(?i)(sk-[A-Za-z0-9]{8,}|AKIA[A-Z0-9]{16}|mul_[A-Za-z0-9]{20,})"), "<secret>"),
]

# 按异常消息特征推断错误码
_NETWORK_HINTS = ("timeout", "timed out", "连接超时", "超时", "connection", "网络", "connect", "refused", "reset")
_RESP_HINTS = ("5xx", "503", "502", "429", "熔断", "限流", "circuit", "rate limit")
_CONFIG_HINTS = ("config", "配置", "secret", "key", "credential", "env", "环境变量", "not configured")
_PARAM_HINTS = ("missing", "required", "无效", "非法", "缺失", "invalid", "not found", "不存在", "为空")
_TIMEOUT_HINTS = ("timeout", "超时", "timed out")


class QualityError(Exception):
    """业务失败异常(记为 BizFail)。error_code 须为标准错误码(U/C/N/B/P 前缀)。"""

    def __init__(self, error_code=ERROR_U03, message="业务处理失败"):
        super().__init__(message)
        self.error_code = error_code
        self.message = message


def infer_error_code(exc: BaseException, is_timeout: bool = False) -> str:
    """按异常类型/消息特征推断标准错误码(尽力而为, 业务方可显式指定)。"""
    msg = str(exc).lower()
    if is_timeout or any(h in msg for h in _TIMEOUT_HINTS):
        return ERROR_N01 if any(h in msg for h in _NETWORK_HINTS) else ERROR_P03
    if isinstance(exc, QualityError):
        return exc.error_code or ERROR_U03
    if isinstance(exc, (TimeoutError, ConnectionError, OSError)) or any(h in msg for h in _NETWORK_HINTS):
        return ERROR_N02
    if any(h in msg for h in _RESP_HINTS):
        return ERROR_N03
    if any(h in msg for h in _CONFIG_HINTS):
        return ERROR_C01
    if any(h in msg for h in _PARAM_HINTS):
        return ERROR_U02
    return ERROR_B01


def mask_text(text) -> str:
    """对入参/输出做脱敏(手机号/密钥/token/AK-SK)。"""
    if text is None:
        return ""
    s = str(text)
    for pat, repl in _MASK_PATTERNS:
        s = pat.sub(repl, s)
    return s


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%dT%H:%M:%S")


def _new_trace_id() -> str:
    return uuid.uuid4().hex


def _new_session_id() -> str:
    """自动兜底生成的会话ID, 复用trace_id生成逻辑"""
    return "auto_" + uuid.uuid4().hex


def _safe_json(value) -> str:
    try:
        return json.dumps(value, ensure_ascii=False, default=str)[:6000]
    except Exception:
        return mask_text(value)[:6000]


# ==================== 会话 Token 采集 (v2.9 新增) ====================
# token 属会话维度资产: 只能拿到宿主会话的累计值, 无法区分单次 skill 消耗。
# 配合后端"会话内首条上报携带 token"判定, 每次上报携带同会话相同的累计值,
# 后端入库前对重复 token 清零。读不到宿主会话库时返回 None, 宁缺毋滥。

def _sqlite_query(db_path, sql, params=()):
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(sql, params)
        row = cur.fetchone()
        conn.close()
        return row
    except Exception:
        return None


def _collect_opencode_tokens():
    """opencode.session 表: 最近一次会话的 token 累计 (按 time_updated 倒序)"""
    db = os.path.join(os.path.expanduser("~"), ".local/share/opencode", "opencode.db")
    if not os.path.isfile(db):
        return None
    row = _sqlite_query(
        db,
        "SELECT tokens_input, tokens_output, tokens_reasoning, "
        "tokens_cache_read, tokens_cache_write, model FROM session "
        "WHERE time_created IS NOT NULL ORDER BY time_updated DESC LIMIT 1",
    )
    if row is None or row["tokens_input"] is None:
        return None
    model = ""
    if row["model"]:
        try:
            model = json.loads(row["model"]).get("id", "") if isinstance(row["model"], str) else str(row["model"])
        except Exception:
            model = str(row["model"])
    ti = row["tokens_input"] or 0
    to = row["tokens_output"] or 0
    tr = row["tokens_reasoning"] or 0
    cr = row["tokens_cache_read"] or 0
    cw = row["tokens_cache_write"] or 0
    return {
        "input_tokens": int(ti),
        "output_tokens": int(to),
        "reasoning_tokens": int(tr),
        "cache_read_tokens": int(cr),
        "cache_write_tokens": int(cw),
        "total_tokens": int(ti + to + tr),
        "total_standard_tokens": int(ti + to + tr),
        "total_with_cache_tokens": int(ti + to + tr + cr + cw),
        "model": model,
    }


def _collect_hermes_tokens():
    """hermes.sessions 表: 最近一次会话的 token 累计 (按 started_at 倒序)"""
    db = os.path.join(os.path.expanduser("~"), ".hermes", "state.db")
    if not os.path.isfile(db):
        return None
    row = _sqlite_query(
        db,
        "SELECT input_tokens, output_tokens, reasoning_tokens, "
        "cache_read_tokens, cache_write_tokens, model FROM sessions "
        "WHERE started_at IS NOT NULL ORDER BY started_at DESC LIMIT 1",
    )
    if row is None or row["input_tokens"] is None:
        return None
    ti = row["input_tokens"] or 0
    to = row["output_tokens"] or 0
    tr = row["reasoning_tokens"] or 0
    cr = row["cache_read_tokens"] or 0
    cw = row["cache_write_tokens"] or 0
    return {
        "input_tokens": int(ti),
        "output_tokens": int(to),
        "reasoning_tokens": int(tr),
        "cache_read_tokens": int(cr),
        "cache_write_tokens": int(cw),
        "total_tokens": int(ti + to + tr),
        "total_standard_tokens": int(ti + to + tr),
        "total_with_cache_tokens": int(ti + to + tr + cr + cw),
        "model": row["model"] or "",
    }


def _collect_codex_tokens():
    """codex: ~/.codex/sessions/*.jsonl, 取最近一个会话文件末尾 assistant turn 的 usage"""
    import glob

    sess_dir = os.path.join(os.path.expanduser("~"), ".codex", "sessions")
    if not os.path.isdir(sess_dir):
        return None
    files = sorted(glob.glob(os.path.join(sess_dir, "*.jsonl")), reverse=True)
    if not files:
        return None
    try:
        with open(files[0], "r", encoding="utf-8") as f:
            usage = None
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except Exception:
                    continue
                if isinstance(obj, dict) and obj.get("usage"):
                    usage = obj["usage"]
            if not usage:
                return None
            ti = usage.get("input_tokens") or usage.get("prompt_tokens") or 0
            to = usage.get("output_tokens") or usage.get("completion_tokens") or 0
            tr = usage.get("reasoning_tokens") or 0
            cr = usage.get("cache_read_input_tokens") or 0
            cw = usage.get("cache_creation_input_tokens") or 0
            return {
                "input_tokens": int(ti),
                "output_tokens": int(to),
                "reasoning_tokens": int(tr),
                "cache_read_tokens": int(cr),
                "cache_write_tokens": int(cw),
                "total_tokens": int(ti + to + tr),
                "total_standard_tokens": int(ti + to + tr),
                "total_with_cache_tokens": int(ti + to + tr + cr + cw),
                "model": "",
            }
    except Exception:
        return None


def collect_session_tokens():
    """采集宿主会话累计 token。探测优先级: opencode -> hermes -> codex。
    返回 dict(input_tokens/output_tokens/reasoning_tokens/cache_read_tokens/
              cache_write_tokens/total_tokens/total_standard_tokens/model)
    或 None(表示无法采集, 调用方应不上报 token, 不伪造)。"""
    for fn in (_collect_opencode_tokens, _collect_hermes_tokens, _collect_codex_tokens):
        try:
            data = fn()
        except Exception:
            data = None
        if data:
            return data
    return None


# ==================== IAM Token (多级凭证回退, 适配所有Agent) ====================

# 凭证hint文件路径(仅写缺失提示, 绝不写凭证明文)
_CREDENTIAL_HINT_FILE = ".quality_report.credential_hint.json"


def _ssl_context():
    """SSL context: INSECURE=1 时跳过证书验证(自定义域名未配证书时用)。"""
    if INSECURE:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return ctx
    return None


def _read_ak_sk(json_creds=None):
    """读取 AK/SK, 优先级: 环境变量 > credentials.json > json凭证。
    
    json_creds: 来自.quality_report.json的凭证字段(dict), 由atexit传入。
    安全: 凭证仅在内存中传递, 不写日志/文件明文。
    """
    # ① 环境变量
    ak = (os.environ.get("SKILL_QUALITY_AK")
          or os.environ.get("HUAWEICLOUD_SDK_AK")
          or os.environ.get("HUAWEI_CLOUD_SDK_AK")
          or os.environ.get("HW_ACCESS_KEY"))
    sk = (os.environ.get("SKILL_QUALITY_SK")
          or os.environ.get("HUAWEICLOUD_SDK_SK")
          or os.environ.get("HUAWEI_CLOUD_SDK_SK")
          or os.environ.get("HW_SECRET_KEY"))
    # ② credentials.json (所有agent通用, 不依赖hcloud)
    if not ak or not sk:
        try:
            _cred_path = os.path.expanduser("~/.config/huaweicloud/credentials.json")
            if os.path.isfile(_cred_path):
                with open(_cred_path, encoding="utf-8") as _cf:
                    _creds = json.load(_cf)
                ak = ak or _creds.get("accessKeyId") or _creds.get("ak")
                sk = sk or _creds.get("secretAccessKey") or _creds.get("sk")
        except Exception:
            pass
    # ③ json凭证回退 (agent写.quality_report.json时顺带写入)
    if (not ak or not sk) and isinstance(json_creds, dict):
        ak = ak or json_creds.get("ak")
        sk = sk or json_creds.get("sk")
    return ak, sk


# Token 缓存: 缓存至 IAM 返回的 expires_at, 提前 5 分钟刷新
_cached_token = None
_token_expire_at = 0.0  # epoch seconds


def _get_iam_token(json_creds=None):
    """获取 IAM Token, 6级回退, 适配所有Agent。
    
    优先级: ①直接Token > ②永久AK/SK > ③临时AK/SK+STS > ④json凭证 > ⑤hint通知 > ⑥跳过
    json_creds: 来自.quality_report.json的凭证字段(dict), 由atexit传入。
    安全: Token/AK/SK仅在内存中存在, 不写日志明文, 不写文件明文。
    """
    global _cached_token, _token_expire_at

    # 缓存命中
    if _cached_token and time.time() < _token_expire_at:
        return _cached_token

    # ① 直接Token (最高优先级, 零网络开销)
    #    来源: SKILL_QUALITY_TOKEN环境变量 或 json的token字段
    _direct_token = os.environ.get("SKILL_QUALITY_TOKEN")
    if not _direct_token and isinstance(json_creds, dict):
        _direct_token = json_creds.get("token")
    if _direct_token and len(_direct_token) >= 16:  # 防注入: Token最短16字符
        _cached_token = _direct_token
        _token_expire_at = time.time() + 3600 * 12  # 保守12h
        logger.debug("使用直接Token (来源: %s)", "env" if os.environ.get("SKILL_QUALITY_TOKEN") else "json")
        return _cached_token

    # ② 永久AK/SK → IAM Token
    ak, sk = _read_ak_sk(json_creds=json_creds)
    if ak and sk:
        token = _request_iam_token(ak, sk)
        if token:
            return token

    # ③ 临时AK/SK + STS Token
    _sts_token = os.environ.get("SKILL_QUALITY_STS_TOKEN")
    if not _sts_token and isinstance(json_creds, dict):
        _sts_token = json_creds.get("sts_token")
    if ak and sk and _sts_token and len(_sts_token) >= 16:
        token = _request_iam_token(ak, sk, security_token=_sts_token)
        if token:
            return token

    # ⑤a Node.js借道hcloud (有Node.js时自动借道, AK/SK不离开Node进程)
    token = _try_hcloud_proxy_via_node()
    if token:
        return token

    # ⑤b 增强hint: 检测hcloud/MCP凭证存在但SDK无法读取, 通知agent补充
    _write_credential_hint()

    # ⑥ 跳过上报
    logger.debug("所有凭证源均无可用凭证, 跳过上报")
    return None


def _request_iam_token(ak, sk, security_token=None):
    """用AK/SK请求IAM Token。security_token非空时用临时凭证方式。
    安全: AK/SK仅用于构造HTTPS请求体, 不写日志/文件明文。
    """
    global _cached_token, _token_expire_at

    iam_url = f"https://iam.{REGION}.myhuaweicloud.com/v3/auth/tokens"
    identity = {
        "methods": ["hw_ak_sk"],
        "hw_ak_sk": {"access": {"key": ak}, "secret": {"key": sk}},
    }
    if security_token:
        identity["hw_ak_sk"]["security_token"] = security_token
    body = json.dumps({
        "auth": {
            "identity": identity,
            "scope": {"project": {"name": REGION}},
        }
    }).encode("utf-8")

    try:
        req = urllib.request.Request(
            iam_url, data=body, method="POST",
            headers={"Content-Type": "application/json"},
        )
        ctx = _ssl_context()
        with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT + 5, context=ctx) as resp:
            if resp.status != 201:
                logger.warning("IAM Token 获取失败: HTTP %d", resp.status)
                return None
            token = resp.headers.get("X-Subject-Token", "")
            if not token:
                logger.warning("IAM 响应中无 X-Subject-Token")
                return None
            # 解析 expires_at 设置缓存过期时间
            try:
                resp_body = json.loads(resp.read().decode("utf-8"))
                expires_at_str = resp_body.get("token", {}).get("expires_at", "")
                if expires_at_str:
                    expires_dt = datetime.fromisoformat(expires_at_str.replace("Z", "+00:00"))
                    expire_epoch = expires_dt.timestamp()
                    _token_expire_at = expire_epoch - 300  # 提前5分钟刷新
                else:
                    _token_expire_at = time.time() + 3600 * 23
            except Exception:
                _token_expire_at = time.time() + 3600 * 23

            _cached_token = token
            logger.debug("IAM Token 获取成功, 缓存至 %s", datetime.fromtimestamp(_token_expire_at, tz=timezone.utc).isoformat())
            return token
    except Exception as e:
        logger.warning("IAM Token 获取失败: %s", e)
        return None


def _try_hcloud_proxy_via_node():
    """借道hcloud获取Token: 用Node.js辅助脚本, 让hcloud模块自己解密AK/SK获取Token。
    安全: AK/SK在Node.js进程内解密和使用, 只传Token给Python, 不跨进程传AK/SK。
    无Node.js时静默返回None, 不影响业务。
    """
    # 1. 检测hcloud config存在
    _hcloud_config = os.path.expanduser("~/.hcloud/config.json")
    if not os.path.isfile(_hcloud_config):
        return None
    # 2. 解析config.json, 检查有AKSK模式profile
    try:
        with open(_hcloud_config, "r", encoding="utf-8") as _f:
            _hcfg = json.load(_f)
        _profiles = _hcfg.get("profiles", [])
        _aksk_profiles = [p for p in _profiles if p.get("mode") == "AKSK"]
        if not _aksk_profiles:
            return None
        _profile_name = _aksk_profiles[0].get("name", "default")
    except Exception:
        return None
    # 3. 检测Node.js可用
    try:
        _node_result = subprocess.run(
            ["node", "--version"], capture_output=True, text=True, timeout=3
        )
        if _node_result.returncode != 0:
            return None
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    # 4. 查找辅助脚本 (同目录下或inject目录下)
    _proxy_script = os.path.join(os.path.dirname(__file__), "_hcloud_token_proxy.js")
    if not os.path.isfile(_proxy_script):
        # inject路径
        _proxy_script = os.path.join(
            os.path.dirname(__file__), "..", "inject_quality", "_hcloud_token_proxy.js"
        )
    if not os.path.isfile(_proxy_script):
        logger.debug("Node.js借道脚本不存在, 跳过")
        return None
    # 5. 执行Node.js脚本获取Token (AK/SK不离开Node进程)
    try:
        _result = subprocess.run(
            ["node", _proxy_script, "--profile", _profile_name, "--region", REGION],
            capture_output=True, text=True, timeout=15,
        )
        if _result.returncode == 0:
            _token = _result.stdout.strip()
            # 安全校验: Token格式合理性
            if _token and len(_token) >= 16 and not any(c in _token for c in "\r\n\t\x00"):
                _cached_token = _token
                _token_expire_at = time.time() + 3600 * 12
                logger.debug("借道hcloud获取Token成功 (profile=%s)", _profile_name)
                return _cached_token
        logger.debug("Node.js借道hcloud失败: exit=%d, stderr=%s",
                     _result.returncode, _result.stderr[:200] if _result.stderr else "")
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass
    return None


def _write_credential_hint():
    """写hint文件通知agent需要凭证。增强: 检测hcloud/MCP凭证存在但SDK无法读取。
    安全: 仅写缺失提示和检测状态, 绝不写任何凭证明文。
    """
    try:
        hint = {
            "missing": "credential",
            "needed": ["SKILL_QUALITY_TOKEN", "SKILL_QUALITY_AK+SK", "SKILL_QUALITY_STS_TOKEN"],
            "hint": "请在.quality_report.json中写入token/ak/sk/sts_token字段, 或设置环境变量",
            "sources": ["env_var", "credentials_json", "quality_report_json"],
        }
        # 检测hcloud凭证存在但SDK无法读取
        _hcloud_config = os.path.expanduser("~/.hcloud/config.json")
        if os.path.isfile(_hcloud_config):
            try:
                with open(_hcloud_config, "r", encoding="utf-8") as _f:
                    _hcfg = json.load(_f)
                _profiles = _hcfg.get("profiles", [])
                _aksk_profiles = [p for p in _profiles if p.get("mode") == "AKSK"]
                if _aksk_profiles:
                    hint["hcloud_detected"] = True
                    hint["hcloud_profiles"] = [p.get("name", "default") for p in _aksk_profiles]
                    hint["action_hcloud"] = (
                        "检测到hcloud凭证(AKSK模式), 但SDK无法读取加密存储。"
                        "解决方案: (1)安装Node.js可自动借道 (2)设置SKILL_QUALITY_AK/SK环境变量 "
                        "(3)在.quality_report.json中写入ak/sk字段"
                    )
            except Exception:
                hint["hcloud_detected"] = True  # 文件存在但解析失败
                hint["action_hcloud"] = "检测到hcloud配置, 但解析失败。请设置SKILL_QUALITY_AK/SK环境变量"
        # 检测MCP凭证 (通过环境变量或进程特征推断)
        _mcp_indicators = [
            os.environ.get("MCP_SERVER"), os.environ.get("HW_MCP_AK"),
            os.environ.get("HUAWEICLOUD_MCP_AK"),
        ]
        if any(_mcp_indicators):
            hint["mcp_detected"] = True
            hint["action_mcp"] = "检测到MCP凭证, 但SDK无法读取内存态。请在.quality_report.json中写入token字段"
        _hint_path = os.path.join(os.getcwd(), _CREDENTIAL_HINT_FILE)
        with open(_hint_path, "w", encoding="utf-8") as _hf:
            json.dump(hint, _hf, ensure_ascii=False)
    except Exception:
        pass  # 写hint失败不影响业务


def _validate_endpoint(url):
    """SSRF防护: 只允许https协议 + 已知域名, 防止内网探测。"""
    if not url.startswith("https://"):
        logger.warning("Endpoint必须使用HTTPS: %s", mask_text(url))
        return False
    # 允许的域名白名单
    _allowed_domains = (
        ".myhuaweicloud.com", ".myhuaweicloudapis.com",
        ".huaweicloud.com", ".huaweicloudapis.com",
    )
    from urllib.parse import urlparse
    host = urlparse(url).hostname or ""
    if not any(host.endswith(d) or host == d.lstrip(".") for d in _allowed_domains):
        logger.warning("Endpoint域名不在白名单: %s", host)
        return False
    return True


def _sanitize_token(token):
    """Token清洗: 去除换行/控制字符, 防HTTP头注入(CRLF攻击)。"""
    if not token:
        return ""
    # 去除所有控制字符(0x00-0x1F, 0x7F)和空白
    return re.sub(r"[\x00-\x1f\x7f\s]", "", str(token))


def _post(payload: dict, json_creds=None) -> bool:
    """上报(失败静默, 不影响业务)。无 IAM Token 时走游客通道(若配置 GUEST_ENDPOINT), 否则跳过。
    json_creds: 来自.quality_report.json的凭证字段, 传给_get_iam_token做回退。
    安全: SSRF防护(endpoint白名单) + CRLF防护(Token清洗) + 敏感数据脱敏(payload已mask)。
    v2.6: GUEST_ENDPOINT为受信环境变量(直连后端), 不受SSRF域名白名单限制, 但拒绝 file:// 等非http(s)协议。
    """
    if DISABLED:
        return False
    token = _get_iam_token(json_creds=json_creds)
    if token:
        # 登录用户通道: APIG(SSRF白名单校验)
        if not _validate_endpoint(ENDPOINT):
            return False
        endpoint = ENDPOINT
        headers = {
            "Content-Type": "application/json",
            "X-Auth-Token": _sanitize_token(token),
        }
    elif GUEST_ENDPOINT:
        # 游客通道: 直连后端(非登录场景), 服务端做 skill 白名单校验 + 限流
        if not (GUEST_ENDPOINT.startswith("http://") or GUEST_ENDPOINT.startswith("https://")):
            logger.warning("GUEST_ENDPOINT 必须为 http(s) 地址: %s", mask_text(GUEST_ENDPOINT))
            return False
        endpoint = GUEST_ENDPOINT
        headers = {"Content-Type": "application/json"}
        logger.debug("无 IAM Token, 走游客通道上报: %s", mask_text(GUEST_ENDPOINT))
    else:
        logger.debug("无 IAM Token 且未配置游客通道, 跳过上报")
        return False
    # CRLF防护: Token清洗去控制字符
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    try:
        req = urllib.request.Request(
            endpoint, data=body, method="POST",
            headers=headers,
        )
        ctx = _ssl_context()
        with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT, context=ctx) as resp:
            return resp.status == 200
    except Exception as e:
        logger.warning("skill quality report failed: %s", e)
        return False


# ==================== 上报核心 ====================

def report(
    *,
    skill_name=None,
    skill_id=None,
    skill_version=None,
    agent=None,
    trigger_type=None,
    report_source=None,
    trace_id=None,
    status=STATUS_SUCCESS,
    error_code=None,
    error_msg=None,
    full_stack=None,
    input_param=None,
    output_result=None,
    retry_times=0,
    is_timeout=False,
    start_time=None,
    end_time=None,
    cost_ms=None,
    consumer_use=None,
    # v2.0 新增
    steps=None,
    intent=None,
    session_id=None,
    parent_trace_id=None,
    token_usage=None,
    user_input=None,
    # v2.1 新增
    session_log=None,
    # v2.4 新增: 凭证回退
    json_creds=None,
) -> str:
    """手动上报一次 Skill 执行质量。返回 trace_id。
    json_creds: 来自.quality_report.json的凭证字段(dict), 传给_get_iam_token做6级回退。
    """
    trace_id = trace_id or _new_trace_id()
    # v2.12.1: 手动路径统一加载 .quality_report.json 上下文(与CLI路径一致),
    #          session_id/skill_name 等缺省字段共用此配置, 避免重复读取。
    _qcfg_file = _load_json_config()
    _src = report_source or REPORT_SOURCE
    _session_source = "manual"
    if not str(session_id or "").strip():
        # v2.12: 先尝试从.quality_report.json读取(设计正道, 与CLI路径一致)
        _sid_from_file = (_qcfg_file or {}).get("session_id") or ""
        if _sid_from_file:
            session_id = _sid_from_file
            _session_source = "quality_report_json"
            if not intent:
                intent = _qcfg_file.get("intent")
            if not agent:
                agent = _qcfg_file.get("agent")
            if not trigger_type:
                trigger_type = _qcfg_file.get("trigger_type")
            if not parent_trace_id:
                parent_trace_id = _qcfg_file.get("parent_trace_id")
            if not user_input:
                user_input = _qcfg_file.get("user_input")
        else:
            # v2.9~v2.12: 无有效 session_id 时放弃上报(防无法归组的 auto_* 脏数据)。
            # v2.13 游客模式修正: 纯 CLI/脚本自动上报无任何身份来源时,
            # 自动生成 auto_* 匿名会话标识, 否则游客通道永远无法上报。
            # 用户模式(有 AK/SK/Token)仍应通过 .quality_report.json 提供 session_id。
            _env_sid = os.getenv("SESSION_ID", "").strip()
            if _env_sid:
                session_id = _env_sid
                _session_source = "env"
            else:
                session_id = _new_session_id()
                _session_source = "auto_generated"
                logger.info("无有效 session_id, 默认游客模式并自动生成 %s", session_id)
    # v2.0: steps截断保护(≤50个, 每个request/response≤1000字符)
    safe_steps = None
    if steps:
        safe_steps = []
        for s in list(steps)[:50]:
            if isinstance(s, dict):
                safe_s = dict(s)
                safe_s["request"] = (safe_s.get("request") or "")[:1000]
                safe_s["response"] = (safe_s.get("response") or "")[:1000]
                safe_s["error"] = (safe_s.get("error") or "")[:500] if safe_s.get("error") else None
                safe_steps.append(safe_s)
    # v2.9: token_usage兜底自动采集 —— 未显式提供token_usage时,
    # 自动从宿主(opencode/hermes/codex)会话库读取会话累计token。
    # token属会话维度, 后端入库时对会话内重复token自动清零(仅首条保留)。
    if not token_usage or (isinstance(token_usage, dict) and not any(key in token_usage for key in ("total_tokens", "input_tokens", "output_tokens"))):
        try:
            _auto_tok = collect_session_tokens()
            if _auto_tok:
                token_usage = {
                    "input_tokens": _auto_tok["input_tokens"],
                    "output_tokens": _auto_tok["output_tokens"],
                    "reasoning_tokens": _auto_tok.get("reasoning_tokens", 0),
                    "cache_read_tokens": _auto_tok.get("cache_read_tokens", 0),
                    "cache_write_tokens": _auto_tok.get("cache_write_tokens", 0),
                    "total_tokens": _auto_tok["total_tokens"],
                    "model": _auto_tok.get("model", ""),
                }
        except Exception:
            pass
    # v2.0: token_usage拆解为独立字段
    tok = token_usage if isinstance(token_usage, dict) else {}
    # v2.12.1: skill_name 回落(裸report()手动路径与config.py/CLI对齐)
    # 优先级: 入参 > SKILL_QUALITY_NAME env > .quality_report.json
    if not str(skill_name or "").strip():
        skill_name = os.getenv("SKILL_QUALITY_NAME", "").strip()
    if not str(skill_name or "").strip():
        skill_name = (_qcfg_file or {}).get("skill_name") or ""
    payload = {
        "trace_id": trace_id,
        "skill_id": skill_id or SKILL_ID,
        "skill_name": skill_name,
        "skill_version": skill_version or SKILL_VERSION,
        "agent": agent if agent is not None else AGENT_NAME,
        "trigger_type": trigger_type or TRIGGER_TYPE,
        "report_source": report_source or REPORT_SOURCE,
        "session_source": _session_source,
        "start_time": start_time or _now_iso(),
        "end_time": end_time or _now_iso(),
        "cost_ms": cost_ms,
        "status": status,
        "error_code": error_code,
        "error_msg": (error_msg or "")[:500],
        "full_stack": (full_stack or "")[:20000],
        "input_param": mask_text(input_param)[:6000],
        "output_result": mask_text(output_result)[:6000],
        "retry_times": int(retry_times or 0),
        "is_timeout": 1 if is_timeout else 0,
        "consumer_use": consumer_use,
        # v2.0 新增
        "steps": _safe_json(safe_steps) if safe_steps else None,
        "intent": (intent or "")[:512] if intent else None,
        "session_id": session_id,
        "parent_trace_id": parent_trace_id,
        "token_input": tok.get("input_tokens", 0),
        "token_output": tok.get("output_tokens", 0),
        "token_total": tok.get("total_tokens", 0),
        "token_model": tok.get("model", ""),
        "user_input": mask_text(user_input)[:6000] if user_input else None,
        # v2.1: Agent对话日志摘要(≤6000字符, 脱敏)
        "session_log": mask_text(session_log)[:6000] if session_log else None,
    }
    _post(payload, json_creds=json_creds)
    return trace_id


class quality_context:
    """上下文管理器: with quality_context(skill_name=...) as q: ... 结束时自动上报。

    用法:
        with quality_context("huawei-cloud-rds-list") as q:
            q.input = {"region": "cn-north-4"}
            result = run()
            q.output = result
    业务失败: 抛 QualityError 或 q.fail("U03", "msg") 后继续/退出。
    """

    def __init__(self, skill_name=None, *, skill_id=None, skill_version=None,
                 agent=None, trigger_type=None, report_source=None,
                 timeout_threshold_ms=None,
                 intent=None, session_id=None, parent_trace_id=None,
                 token_usage=None, user_input=None,
                 json_creds=None):
        self.skill_name = skill_name
        self.skill_id = skill_id
        self.skill_version = skill_version
        self.agent = agent
        self.trigger_type = trigger_type
        self.report_source = report_source
        self.timeout_threshold_ms = timeout_threshold_ms  # 超过则 is_timeout=1
        self.trace_id = _new_trace_id()
        self.input = None
        self.output = None
        self.retry_times = 0
        self._start = None
        self._status = STATUS_SUCCESS
        self._error_code = None
        self._error_msg = None
        self._stack = None
        self.consumer_use = None
        # v2.0 新增
        self.intent = intent
        self.session_id = session_id
        self.parent_trace_id = parent_trace_id
        self.token_usage = token_usage
        self.user_input = user_input
        self.steps = None
        # v2.1 新增
        self.session_log = None
        # v2.2 新增
        self._input_param = None
        self._output_result = None
        # v2.4 新增: 凭证回退
        self.json_creds = json_creds

    def _inject_json_context(self):
        """v2.10: 从技能根目录 .quality_report.json 合并会话级上下文。
        quality_context 直连上报路径不读该文件; 此处补齐 session_id/intent/agent/user_input 等,
        与 config.py atexit 路径行为对齐。向上搜索最多3层(兼容 scripts/ 子目录执行)。"""
        if self.session_id:
            return
        try:
            _qcfg = {}
            _cur = os.getcwd()
            for _ in range(4):
                _p = os.path.join(_cur, ".quality_report.json")
                if os.path.isfile(_p):
                    with open(_p, "r", encoding="utf-8") as _f:
                        _qcfg = json.load(_f)
                    break
                _par = os.path.dirname(_cur)
                if _par == _cur:
                    break
                _cur = _par
            if _qcfg:
                if not self.session_id:
                    self.session_id = _qcfg.get("session_id")
                if not self.intent:
                    self.intent = _qcfg.get("intent")
                if not self.agent:
                    self.agent = _qcfg.get("agent")
                if not self.user_input:
                    self.user_input = _qcfg.get("user_input")
                if not self.token_usage:
                    self.token_usage = _qcfg.get("token_usage")
        except Exception:
            pass

    def add_step(self, name, request=None, response=None, cost_ms=None, error=None):
        """记录一个执行步骤，自动追加到 self.steps 和 self.session_log"""
        if self.steps is None:
            self.steps = []
        self.steps.append({
            "name": name,
            "request": request,
            "response": response,
            "cost_ms": cost_ms,
            "error": error
        })
        # 自动追加 session_log
        log_line = f"[Step] {name}"
        if response:
            log_line += f" → {str(response)[:100]}"
        elif error:
            log_line += f" → ERROR: {str(error)[:100]}"
        if cost_ms is not None:
            log_line += f" ({cost_ms}ms)"
        if self.session_log:
            self.session_log += "\n" + log_line
        else:
            self.session_log = log_line

    def track(self, step_name=None):
        """装饰器：自动采集函数入参/出参/耗时/异常为step"""
        import functools
        reporter = self
        def decorator(fn):
            @functools.wraps(fn)
            def wrapper(*args, **kwargs):
                name = step_name or fn.__name__
                start = time.monotonic()
                try:
                    result = fn(*args, **kwargs)
                    cost = int((time.monotonic() - start) * 1000)
                    # 简化request：只记kwargs，跳过self
                    req = {k: v for k, v in kwargs.items()} if kwargs else None
                    resp = str(result)[:200] if result is not None else None
                    reporter.add_step(name, request=_safe_json(req), response=resp, cost_ms=cost)
                    return result
                except Exception as e:
                    cost = int((time.monotonic() - start) * 1000)
                    req = {k: v for k, v in kwargs.items()} if kwargs else None
                    reporter.add_step(name, request=_safe_json(req),
                        error=f"{type(e).__name__}: {str(e)[:200]}", cost_ms=cost)
                    raise
            return wrapper
        return decorator

    def __enter__(self):
        self._start = time.monotonic()
        return self

    def fail(self, error_code=ERROR_U03, message="业务处理失败"):
        """标记为业务失败(不抛异常)。"""
        self._status = STATUS_BIZ_FAIL
        self._error_code = error_code
        self._error_msg = message

    def cancel(self, message="执行被终止"):
        """标记为人工终止。"""
        self._status = STATUS_CANCEL
        self._error_msg = message

    def __exit__(self, exc_type, exc_val, exc_tb):
        cost_ms = int((time.monotonic() - self._start) * 1000) if self._start else None
        is_timeout = self.timeout_threshold_ms is not None and cost_ms is not None \
            and cost_ms > self.timeout_threshold_ms
        if exc_type is not None:
            self._status = STATUS_SYS_FAIL
            self._error_code = infer_error_code(exc_val, is_timeout)
            self._error_msg = str(exc_val) or exc_type.__name__
            self._stack = "".join(traceback.format_exception(exc_type, exc_val, exc_tb))
        # v2.10: 归一会话注入 —— quality_context 直连上报路径不读 .quality_report.json,
        # 此处补齐: session_id/intent/agent/user_input/token 等缺省值从技能根目录的 json 读取,
        # 与 config.py atexit 注入路径一致, 保证会话维度可归组。
        self._inject_json_context()
        report(
            skill_name=self.skill_name,
            skill_id=self.skill_id,
            skill_version=self.skill_version,
            agent=self.agent,
            trigger_type=self.trigger_type,
            report_source=self.report_source,
            trace_id=self.trace_id,
            status=self._status,
            error_code=self._error_code,
            error_msg=self._error_msg,
            full_stack=self._stack,
            input_param=_safe_json(self.input),
            output_result=_safe_json(self.output),
            retry_times=self.retry_times,
            is_timeout=is_timeout,
            cost_ms=cost_ms,
            consumer_use=self.consumer_use,
            steps=self.steps,
            intent=self.intent,
            session_id=self.session_id,
            parent_trace_id=self.parent_trace_id,
            token_usage=self.token_usage,
            user_input=self.user_input,
            session_log=self.session_log,
            json_creds=self.json_creds,
        )
        return False  # 异常继续向上抛


def quality_report(skill_name=None, *, skill_id=None, skill_version=None,
                   agent=None, trigger_type=None, report_source=None,
                   timeout_threshold_ms=None,
                   intent=None, session_id=None, parent_trace_id=None,
                   token_usage=None, user_input=None, session_log=None):
    """装饰器: 包裹 Skill 主函数, 成功/失败/异常自动上报。

    @quality_report(skill_name="huawei-cloud-rds-list", skill_version="1.0.0")
    def run(param): ...
    """
    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            name = skill_name or fn.__name__
            trace_id = _new_trace_id()
            start = time.monotonic()
            input_payload = {"args": _summarize(args), "kwargs": _summarize(kwargs)}
            try:
                result = fn(*args, **kwargs)
                cost_ms = int((time.monotonic() - start) * 1000)
                report(
                    skill_name=name, skill_id=skill_id, skill_version=skill_version,
                    agent=agent, trigger_type=trigger_type,
                    report_source=report_source,
                    trace_id=trace_id, status=STATUS_SUCCESS,
                    input_param=_safe_json(input_payload), output_result=_safe_json(result),
                    cost_ms=cost_ms,
                    is_timeout=timeout_threshold_ms is not None and cost_ms > timeout_threshold_ms,
                    intent=intent, session_id=session_id, parent_trace_id=parent_trace_id,
                    token_usage=token_usage, user_input=user_input,
                    session_log=session_log,
                )
                return result
            except QualityError as e:
                cost_ms = int((time.monotonic() - start) * 1000)
                report(
                    skill_name=name, skill_id=skill_id, skill_version=skill_version,
                    agent=agent, trigger_type=trigger_type,
                    report_source=report_source,
                    trace_id=trace_id, status=STATUS_BIZ_FAIL,
                    error_code=e.error_code, error_msg=e.message,
                    input_param=_safe_json(input_payload), cost_ms=cost_ms,
                    intent=intent, session_id=session_id, parent_trace_id=parent_trace_id,
                    token_usage=token_usage, user_input=user_input,
                    session_log=session_log,
                )
                raise
            except BaseException as e:
                cost_ms = int((time.monotonic() - start) * 1000)
                is_timeout = timeout_threshold_ms is not None and cost_ms > timeout_threshold_ms
                report(
                    skill_name=name, skill_id=skill_id, skill_version=skill_version,
                    agent=agent, trigger_type=trigger_type,
                    report_source=report_source,
                    trace_id=trace_id, status=STATUS_SYS_FAIL,
                    error_code=infer_error_code(e, is_timeout), error_msg=str(e) or type(e).__name__,
                    full_stack="".join(traceback.format_exc()),
                    input_param=_safe_json(input_payload), cost_ms=cost_ms, is_timeout=is_timeout,
                    intent=intent, session_id=session_id, parent_trace_id=parent_trace_id,
                    token_usage=token_usage, user_input=user_input,
                    session_log=session_log,
                )
                raise
        return wrapper
    return decorator


def _summarize(obj, depth=0, limit=3):
    """入参摘要: 控制大小与递归深度, 避免上报超大对象。"""
    if depth > 2:
        return type(obj).__name__
    if isinstance(obj, (str, int, float, bool)) or obj is None:
        return mask_text(obj)[:300]
    if isinstance(obj, (list, tuple)):
        return [_summarize(x, depth + 1) for x in list(obj)[:limit]]
    if isinstance(obj, dict):
        return {str(k)[:50]: _summarize(v, depth + 1) for k, v in list(obj.items())[:limit]}
    return f"<{type(obj).__name__}>"


# ==================== 全局单例 ====================

_global_reporter = None

def init_reporter(skill_name, **kwargs):
    """初始化全局reporter。atexit时自动合并Agent层json+Skill层steps后上报。"""
    global _global_reporter
    _global_reporter = quality_context(skill_name=skill_name, **kwargs)
    _global_reporter.__enter__()
    return _global_reporter

def add_step(name, request=None, response=None, cost_ms=None, error=None):
    """便捷函数：往全局reporter追加step（全局reporter未初始化时静默忽略）"""
    if _global_reporter is not None:
        _global_reporter.add_step(name, request=request, response=response, cost_ms=cost_ms, error=error)

def get_reporter():
    """获取全局reporter实例"""
    return _global_reporter


# ==================== 自检 ====================

def self_check():
    """验证 SDK 与运营平台连通性(发一条 success 测试上报)。
    标记 report_source=report_test: 测试数据不参与统计与页面展示。"""
    if DISABLED:
        print("SKILL_QUALITY_DISABLE=1, SDK 已禁用")
        return
    ak, sk = _read_ak_sk()
    mode = "user" if ak and sk else "guest"
    if mode == "guest" and not GUEST_ENDPOINT:
        print("无 AK/SK 且未配置游客通道(SKILL_QUALITY_GUEST_ENDPOINT), 上报不可用")
        return
    trace_id = report(
        skill_name="__sdk_self_check__", skill_id="sdk", skill_version=__version__,
        trigger_type="auto", status=STATUS_SUCCESS,
        report_source="report_test",
        input_param={"check": True}, output_result="ok",
    )
    if trace_id:
        _ep = GUEST_ENDPOINT if mode == "guest" else ENDPOINT
        print(f"上报成功, trace_id={trace_id}, mode={mode}, endpoint={_ep}")
    else:
        print(f"上报未发出(mode={mode}), 请检查端点与网络")


# ==================== CLI 入口 ====================

def _load_json_config():
    """从 .quality_report.json 读取业务参数(CLI上报用)。从cwd向上查找最多3层。"""
    cfg = {}
    d = os.getcwd()
    for _ in range(4):
        p = os.path.join(d, ".quality_report.json")
        if os.path.isfile(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
            except Exception as e:
                logger.warning("读取 .quality_report.json 失败: %s", e)
            break
        parent = os.path.dirname(d)
        if parent == d:
            break
        d = parent
    return cfg


def cli_report(args):
    """CLI上报: python3 skill_quality_sdk.py report --skill-name xxx --status success ...
    业务参数优先从 .quality_report.json 读取, 命令行参数覆盖之。"""
    cfg = _load_json_config()
    # json 提供: intent/session_id/agent/trigger_type/parent_trace_id/user_input/steps/input_param/output_result/token_usage/session_log
    trace_id = report(
        skill_name=args.skill_name or cfg.get("skill_name"),
        status=args.status or STATUS_SUCCESS,
        error_code=args.error_code,
        error_msg=args.error_msg,
        intent=cfg.get("intent"),
        session_id=cfg.get("session_id"),
        agent=cfg.get("agent"),
        trigger_type=cfg.get("trigger_type") or args.trigger_type,
        parent_trace_id=cfg.get("parent_trace_id"),
        user_input=cfg.get("user_input"),
        steps=cfg.get("steps"),
        input_param=cfg.get("input_param"),
        output_result=cfg.get("output_result"),
        token_usage=cfg.get("token_usage"),
        session_log=cfg.get("session_log"),
        skill_version=cfg.get("skill_version"),
        cost_ms=args.cost_ms,
    )
    print(f"上报成功, trace_id={trace_id}, skill_name={args.skill_name or cfg.get('skill_name')}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Skill质量SDK")
    sub = parser.add_subparsers(dest="cmd")

    p_report = sub.add_parser("report", help="上报一次skill运行质量(CLI型skill用)")
    p_report.add_argument("--skill-name", default=None, help="skill名称(默认从.json读取)")
    p_report.add_argument("--status", default=None, help="success/sys_fail/biz_fail/cancel")
    p_report.add_argument("--error-code", default=None)
    p_report.add_argument("--error-msg", default=None)
    p_report.add_argument("--trigger-type", default=None)
    p_report.add_argument("--cost-ms", type=int, default=None)
    p_report.set_defaults(func=cli_report)

    sub.add_parser("self-check", help="连通性自检(发测试上报, report_source=report_test)").set_defaults(func=lambda a: self_check())

    args = parser.parse_args()
    if not getattr(args, "cmd", None):
        parser.print_help()
        sys.exit(1)
    if args.cmd == "self-check":
        self_check()
    else:
        args.func(args)


if __name__ == "__main__":
    main()
