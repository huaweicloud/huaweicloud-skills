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
import sys
import time
import traceback
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone

__version__ = "1.0.0"

logger = logging.getLogger("skill-quality-sdk")

# ==================== 配置 ====================

ENDPOINT = os.environ.get(
    "SKILL_QUALITY_ENDPOINT", "https://skillsapi.developer.myhuaweicloud.com/api/quality/report"
)
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


def _safe_json(value) -> str:
    try:
        return json.dumps(value, ensure_ascii=False, default=str)[:6000]
    except Exception:
        return mask_text(value)[:6000]


# ==================== IAM Token (AK/SK → X-Auth-Token) ====================

def _ssl_context():
    """SSL context: INSECURE=1 时跳过证书验证(自定义域名未配证书时用)。"""
    if INSECURE:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return ctx
    return None


def _read_ak_sk():
    """读取 AK/SK, 支持 SKILL_QUALITY_AK/SK 及华为云标准环境变量回退。"""
    ak = (os.environ.get("SKILL_QUALITY_AK")
          or os.environ.get("HUAWEICLOUD_SDK_AK")
          or os.environ.get("HUAWEI_CLOUD_SDK_AK")
          or os.environ.get("HW_ACCESS_KEY"))
    sk = (os.environ.get("SKILL_QUALITY_SK")
          or os.environ.get("HUAWEICLOUD_SDK_SK")
          or os.environ.get("HUAWEI_CLOUD_SDK_SK")
          or os.environ.get("HW_SECRET_KEY"))
    return ak, sk


# Token 缓存: 缓存至 IAM 返回的 expires_at, 提前 5 分钟刷新
_cached_token = None
_token_expire_at = 0.0  # epoch seconds


def _get_iam_token():
    """用 AK/SK 获取华为云 IAM Token, 缓存至 expires_at。无 AK/SK 返回 None。"""
    global _cached_token, _token_expire_at

    # 缓存命中
    if _cached_token and time.time() < _token_expire_at:
        return _cached_token

    ak_cred, sk_cred = _read_ak_sk()
    if not ak_cred or not sk_cred:
        logger.debug("无 AK/SK, 跳过 IAM Token 获取")
        return None

    iam_url = f"https://iam.{REGION}.myhuaweicloud.com/v3/auth/tokens"
    body = json.dumps({
        "auth": {
            "identity": {
                "methods": ["hw_ak_sk"],
                "hw_ak_sk": {"access": {"key": ak_cred}, "secret": {"key": sk_cred}},
            },
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
                    # 解析 ISO 8601: "2026-08-21T01:11:41.865000Z"
                    expires_dt = datetime.fromisoformat(expires_at_str.replace("Z", "+00:00"))
                    expire_epoch = expires_dt.timestamp()
                    # 提前 5 分钟刷新, 避免边界过期
                    _token_expire_at = expire_epoch - 300
                else:
                    _token_expire_at = time.time() + 3600 * 23  # 兜底 23h
            except Exception:
                _token_expire_at = time.time() + 3600 * 23  # 兜底 23h

            _cached_token = token
            logger.debug("IAM Token 获取成功, 缓存至 %s", datetime.fromtimestamp(_token_expire_at, tz=timezone.utc).isoformat())
            return token
    except Exception as e:
        logger.warning("IAM Token 获取失败: %s", e)
        return None


def _post(payload: dict) -> bool:
    """上报(失败静默, 不影响业务)。无 IAM Token 时不调用接口。"""
    if DISABLED:
        return False
    token = _get_iam_token()
    if not token:
        logger.debug("无 IAM Token, 跳过上报")
        return False
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    try:
        req = urllib.request.Request(
            ENDPOINT, data=body, method="POST",
            headers={
                "Content-Type": "application/json",
                "X-Auth-Token": token,
            },
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
) -> str:
    """手动上报一次 Skill 执行质量。返回 trace_id。"""
    trace_id = trace_id or _new_trace_id()
    payload = {
        "trace_id": trace_id,
        "skill_id": skill_id or SKILL_ID,
        "skill_name": skill_name,
        "skill_version": skill_version or SKILL_VERSION,
        "agent": agent if agent is not None else AGENT_NAME,
        "trigger_type": trigger_type or TRIGGER_TYPE,
        "report_source": report_source or REPORT_SOURCE,
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
    }
    _post(payload)
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
                 timeout_threshold_ms=None):
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
        )
        return False  # 异常继续向上抛


def quality_report(skill_name=None, *, skill_id=None, skill_version=None,
                   agent=None, trigger_type=None, report_source=None,
                   timeout_threshold_ms=None):
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


# ==================== 自检 ====================

def self_check():
    """验证 SDK 与运营平台连通性(发一条 success 测试上报)。"""
    if DISABLED:
        print("SKILL_QUALITY_DISABLE=1, SDK 已禁用")
        return
    ak_cred, sk_cred = _read_ak_sk()
    if not ak_cred or not sk_cred:
        print("无 AK/SK, 无法获取 IAM Token, 上报不可用")
        return
    trace_id = report(
        skill_name="__sdk_self_check__", skill_id="sdk", skill_version=__version__,
        trigger_type="auto", status=STATUS_SUCCESS,
        input_param={"check": True}, output_result="ok",
    )
    print(f"上报成功, trace_id={trace_id}, endpoint={ENDPOINT}")


if __name__ == "__main__":
    self_check()
