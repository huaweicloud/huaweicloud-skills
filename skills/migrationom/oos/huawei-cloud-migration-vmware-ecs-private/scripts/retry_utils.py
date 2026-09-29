#!/usr/bin/env python3
"""
retry_utils.py — P3-8优化: 统一重试与回滚工具

提供指数退避重试装饰器，支持:
  - 可配置最大重试次数、初始/最大间隔、退避因子
  - 异常过滤 (仅对指定异常重试)
  - 回滚回调 (每次重试前调用)
  - 抖动 (jitter) 避免雷群效应

用法:
    from retry_utils import retry_with_backoff

    @retry_with_backoff(max_retries=3, initial_delay=2, max_delay=30)
    def flaky_operation():
        ...

    @retry_with_backoff(max_retries=5, exceptions=(TimeoutError, ConnectionError),
                        rollback=lambda ctx: cleanup(ctx))
    def network_operation():
        ...
"""

import time
import functools
import logging
import random
from typing import Callable, Tuple, Type, Any, Optional

logger = logging.getLogger(__name__)


def retry_with_backoff(
    max_retries: int = 3,
    initial_delay: float = 2.0,
    max_delay: float = 30.0,
    backoff_factor: float = 2.0,
    jitter: bool = True,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    rollback: Optional[Callable] = None,
    on_retry: Optional[Callable] = None,
):
    """指数退避重试装饰器

    Args:
        max_retries: 最大重试次数 (不含首次执行)
        initial_delay: 初始重试延迟 (秒)
        max_delay: 最大重试延迟 (秒)
        backoff_factor: 退避因子 (每次延迟乘以此值)
        jitter: 是否添加随机抖动 (避免雷群效应)
        exceptions: 仅对这些异常进行重试
        rollback: 回滚回调函数，每次重试前调用，接收 (exception, attempt, context)
        on_retry: 重试回调函数，每次重试前调用，接收 (exception, attempt, delay)

    Returns:
        装饰器函数
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            delay = initial_delay
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt >= max_retries:
                        logger.error(
                            f"P3-8: {func.__name__} failed after {max_retries + 1} attempts: {e}"
                        )
                        raise

                    # 计算延迟 (含抖动)
                    actual_delay = delay
                    if jitter:
                        actual_delay = delay * (0.5 + random.random() * 0.5)

                    logger.warning(
                        f"P3-8: {func.__name__} failed (attempt {attempt + 1}/{max_retries + 1}), "
                        f"retrying in {actual_delay:.1f}s: {e}"
                    )

                    # 回滚回调
                    if rollback:
                        try:
                            rollback(e, attempt, {"func": func.__name__, "args": args, "kwargs": kwargs})
                        except Exception as rb_err:
                            logger.warning(f"P3-8: rollback callback error: {rb_err}")

                    # 重试回调
                    if on_retry:
                        try:
                            on_retry(e, attempt, actual_delay)
                        except Exception:
                            pass

                    time.sleep(actual_delay)
                    delay = min(delay * backoff_factor, max_delay)

            # 不应到达此处，但以防万一
            raise last_exception

        # 暴露配置供外部检查
        wrapper._retry_config = {
            "max_retries": max_retries,
            "initial_delay": initial_delay,
            "max_delay": max_delay,
            "backoff_factor": backoff_factor,
        }
        return wrapper

    return decorator


class RetryContext:
    """P3-8优化: 重试上下文管理器 (非装饰器场景)

    用法:
        with RetryContext(max_retries=3) as ctx:
            for attempt in ctx:
                try:
                    result = do_something()
                    ctx.success(result)
                    break
                except Exception as e:
                    ctx.fail(e)
    """

    def __init__(
        self,
        max_retries: int = 3,
        initial_delay: float = 2.0,
        max_delay: float = 30.0,
        backoff_factor: float = 2.0,
        jitter: bool = True,
    ):
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor
        self.jitter = jitter
        self._attempt = 0
        self._delay = initial_delay
        self._result = None
        self._error = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False

    def __iter__(self):
        return self

    def __next__(self):
        if self._attempt > self.max_retries:
            raise StopIteration
        if self._attempt > 0:
            actual_delay = self._delay
            if self.jitter:
                actual_delay = self._delay * (0.5 + random.random() * 0.5)
            time.sleep(actual_delay)
            self._delay = min(self._delay * self.backoff_factor, self.max_delay)
        self._attempt += 1
        return self._attempt

    def success(self, result: Any):
        self._result = result

    def fail(self, error: Exception):
        self._error = error

    @property
    def result(self):
        return self._result

    @property
    def error(self):
        return self._error

    @property
    def attempt(self):
        return self._attempt
