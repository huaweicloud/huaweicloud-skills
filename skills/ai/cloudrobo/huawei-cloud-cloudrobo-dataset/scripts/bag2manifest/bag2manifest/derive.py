"""字段派生表达式 —— 让用户对原始字段做组合/后处理.

场景举例:
    * 左右夹爪指关节取绝对值相加: ``abs(f0) + abs(f1)``
    * 合力: ``sqrt(f0*f0 + f1*f1 + f2*f2)``
    * 比例: ``f0 / (f1 + 1e-6)``
    * 限幅: ``clip(f0, -1, 1)``

约定:
    * 输入字段按顺序命名为 ``f0, f1, ...`` (在 UI 里会明确提示映射关系)
    * 只允许四则/幂/取模运算、一元正负、括号, 以及白名单函数
    * 用 ``ast`` 白名单校验后由解释器逐节点求值, 不调用 eval/exec, 不执行任意代码
"""

from __future__ import annotations

import ast
import math
import operator
import re
from typing import Any, Sequence

import numpy as np

FUNCS: dict[str, Any] = {
    "abs": np.abs,
    "min": np.minimum,
    "max": np.maximum,
    "sqrt": np.sqrt,
    "exp": np.exp,
    "log": np.log,
    "clip": lambda x, lo, hi: np.clip(x, lo, hi),
    "where": np.where,
}

_ALLOWED = (
    ast.Expression, ast.BinOp, ast.UnaryOp, ast.Load, ast.Constant,
    ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow, ast.Mod, ast.FloorDiv,
    ast.USub, ast.UAdd, ast.Compare, ast.Gt, ast.Lt, ast.GtE, ast.LtE, ast.Eq, ast.NotEq,
)
_VAR_RE = re.compile(r"^f\d+$")


class ExprError(ValueError):
    pass


def check_expr(expr: str) -> ast.Expression:
    """校验表达式合法性; 不合法抛 ExprError."""
    if not isinstance(expr, str):
        raise ExprError("表达式必须为字符串")
    expr = expr.strip()
    if not expr:
        raise ExprError("表达式为空")
    try:
        tree = ast.parse(expr, mode="eval")
    except SyntaxError as e:
        raise ExprError(f"表达式语法错误: {e.msg}") from e
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) != 1:
            raise ExprError("比较表达式仅支持单个比较，组合条件请嵌套 where")
        if isinstance(node, ast.Constant) and (not isinstance(node.value, (int, float)) or isinstance(node.value, bool)):
            raise ExprError("表达式常量必须为数值")
        if isinstance(node, _ALLOWED):
            continue
        if isinstance(node, ast.Name):
            # 函数调用里的名字 (如 abs) 在 ast.Call 分支单独校验
            if node.id in FUNCS:
                continue
            if not _VAR_RE.match(node.id):
                raise ExprError(f"未知变量 `{node.id}`，只能用 f0、f1、…（按输入字段顺序）")
            continue
        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name) or node.func.id not in FUNCS:
                name = ast.unparse(node.func) if isinstance(node.func, ast.AST) else "?"
                raise ExprError(f"不允许的函数 `{name}`，可用: {', '.join(FUNCS)}")
            arity = {"abs": 1, "sqrt": 1, "exp": 1, "log": 1, "min": 2, "max": 2, "clip": 3, "where": 3}[node.func.id]
            if len(node.args) != arity:
                raise ExprError(f"{node.func.id} 需要 {arity} 个参数")
            if node.keywords:
                raise ExprError("函数不支持关键字参数")
            continue
        raise ExprError(f"不允许的语法: {type(node).__name__}")
    return tree


def required_vars(expr: str) -> int:
    """表达式里用到的最大变量下标 + 1."""
    tree = check_expr(expr)
    idx = [-1]
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id not in FUNCS:
            idx.append(int(node.id[1:]))
    return max(idx) + 1


_BIN_OPS: dict[type, Any] = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
    ast.Div: operator.truediv, ast.Pow: operator.pow, ast.Mod: operator.mod,
    ast.FloorDiv: operator.floordiv,
}
_UNARY_OPS: dict[type, Any] = {ast.USub: operator.neg, ast.UAdd: operator.pos}
_CMP_OPS: dict[type, Any] = {
    ast.Gt: operator.gt, ast.Lt: operator.lt, ast.GtE: operator.ge,
    ast.LtE: operator.le, ast.Eq: operator.eq, ast.NotEq: operator.ne,
}


def _evaluate(node: ast.AST, env: dict[str, np.ndarray]) -> Any:
    """遍历 check_expr 校验过的 AST 直接求值; 不使用 eval/compile, 只认白名单节点."""
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Name):
        if node.id not in env:
            raise ExprError(f"未知变量 `{node.id}`")
        return env[node.id]
    if isinstance(node, ast.BinOp) and type(node.op) in _BIN_OPS:
        return _BIN_OPS[type(node.op)](_evaluate(node.left, env), _evaluate(node.right, env))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY_OPS:
        return _UNARY_OPS[type(node.op)](_evaluate(node.operand, env))
    if isinstance(node, ast.Compare) and len(node.ops) == 1 and type(node.ops[0]) in _CMP_OPS:
        return _CMP_OPS[type(node.ops[0])](_evaluate(node.left, env), _evaluate(node.comparators[0], env))
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in FUNCS:
        return FUNCS[node.func.id](*(_evaluate(a, env) for a in node.args))
    raise ExprError(f"不允许的语法: {type(node).__name__}")


def eval_array(expr: str, inputs: Sequence[str], series_by_key: dict[str, Sequence]) -> np.ndarray:
    """按元素求值, 返回 float 数组 (可能含 nan)."""
    check_expr(expr)
    if not inputs:
        raise ExprError("至少需要 1 个输入字段")
    arrs = []
    for k in inputs:
        s = series_by_key.get(k)
        if s is None:
            raise ExprError(f"输入字段不存在: {k}")
        arrs.append(np.asarray([np.nan if v is None else float(v) for v in s], dtype=float))
    n = max((a.size for a in arrs), default=0)
    env = {f"f{i}": a for i, a in enumerate(arrs)}
    try:
        out = _evaluate(check_expr(expr).body, env)
    except ExprError:
        raise
    except Exception as e:  # noqa: BLE001
        raise ExprError(f"求值失败: {e}") from e
    out = np.asarray(out, dtype=float)
    if out.ndim == 0:
        out = np.full(n, float(out))
    if out.size != n and out.size == 1:
        out = np.full(n, float(out.reshape(-1)[0]))
    return out.reshape(-1)


def to_series(arr: np.ndarray) -> list[float | None]:
    return [None if not math.isfinite(v) else round(float(v), 6) for v in arr]


def stats_of(arr: np.ndarray) -> dict:
    finite = arr[np.isfinite(arr)]
    if finite.size == 0:
        return {"min": 0.0, "max": 0.0, "mean": 0.0, "std": 0.0,
                "constant": True, "near_constant": True}
    lo, hi = float(finite.min()), float(finite.max())
    exact = (hi - lo) < 1e-9
    return {
        "min": round(lo, 6), "max": round(hi, 6),
        "mean": round(float(finite.mean()), 6), "std": round(float(finite.std()), 6),
        "constant": exact, "near_constant": bool((not exact) and (hi - lo) < 1e-3),
    }


# --------------------------------------------------------------------------- #
# plan 项的统一表达
# --------------------------------------------------------------------------- #
def is_expr(item: Any) -> bool:
    return isinstance(item, dict) and "expr" in item


def item_id(item: Any, index: int = 0) -> str:
    """给一个向量项一个稳定可读的 key (用于绘图/表格)."""
    if isinstance(item, dict) and item.get("strategy") == "next_state":
        return "→ " + (item.get("name") or f"state[{item.get('state_index')}]")
    if is_expr(item):
        return "ƒ " + (item.get("name") or (item.get("expr") or "expr")[:24])
    if isinstance(item, dict) and "locator" in item:
        return item["locator"]
    return str(item)


def item_path(item: Any) -> str | None:
    return None if is_expr(item) else str(item)
