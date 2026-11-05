from __future__ import annotations
"""Heuristic functions and AST utilities for VLA scanner detection.

Adapted from ascend-driving-patcher: removed the matmul-specific helpers
(_is_torch_matmul_call, analyze_reshape_chain, MatmulExpandScanner support),
kept the generic utilities (file_scanner, trace_var_source, ScopeTracker).
"""

import ast
import re
from dataclasses import dataclass
from functools import wraps
from pathlib import Path
from typing import Callable

from config import get_config
from utils import get_context, read_py_file_content, is_test_file, is_config_file
from patterns import Issue


def _ctx_line_indicates_dict(tensor_var: str, ctx: str, ctx_stripped: str) -> bool:
    """Check whether a context line shows dict/list initialization or a
    type annotation."""
    ev = re.escape(tensor_var)
    if re.match(rf'{ev}\s*=\s*\{{', ctx_stripped):
        return True
    if re.match(rf'{ev}\s*=\s*\w*[Dd]ict\s*\(', ctx_stripped):
        return True
    if re.match(rf'{ev}\s*=\s*\{{[^}}]*:', ctx_stripped):
        return True
    if re.match(rf'{ev}\s*=\s*\[', ctx_stripped):
        return True
    if re.match(rf'{ev}\s*=\s*list\s*\(', ctx_stripped):
        return True
    if re.search(rf'{ev}\s*:\s*(Dict|dict|List|list)\b', ctx):
        return True
    if re.match(rf'{ev}\s*=.*\.(items|keys|values|split|pop)\(\)', ctx_stripped):
        return True
    return False


def _name_or_value_indicates_dict(tensor_var: str, value: str) -> bool:
    """Check whether a variable-name hint or a missing value suggests
    dict/list."""
    cfg = get_config()
    var_lower = tensor_var.lower()
    if any(hint in var_lower for hint in cfg.dict_name_hints):
        return True
    if any(hint in var_lower for hint in cfg.list_name_hints):
        return True
    if not any(hint in value for hint in cfg.tensor_value_hints):
        return True
    return False


def looks_like_dict_assignment(tensor_var: str, value: str, context_lines: list[str]) -> bool:
    """Use heuristics to determine whether an assignment is a dict or
    list."""
    for ctx in context_lines:
        if _ctx_line_indicates_dict(tensor_var, ctx, ctx.strip()):
            return True
    if _name_or_value_indicates_dict(tensor_var, value):
        return True
    return False


def _get_call_name(node: ast.Call):
    """Resolve the dotted name of an AST Call node."""
    if isinstance(node.func, ast.Attribute):
        val = node.func.value
        if isinstance(val, ast.Name):
            return f"{val.id}.{node.func.attr}"
        elif isinstance(val, ast.Attribute):
            inner = _get_attr_str(val)
            return f"{inner}.{node.func.attr}" if inner else node.func.attr
    elif isinstance(node.func, ast.Name):
        return node.func.id
    return None


def _get_attr_str(node: ast.AST):
    """Resolve a chained ast.Attribute node into a dotted string."""
    if isinstance(node, ast.Name):
        return node.id
    elif isinstance(node, ast.Attribute):
        inner = _get_attr_str(node.value)
        return f"{inner}.{node.attr}" if inner else node.attr
    return None


def file_scanner(skip_tests: bool = False, skip_configs: bool = False) -> Callable:
    """Decorator that handles the file-reading boilerplate for
    scanners."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(files: list[Path]) -> list[Issue]:
            issues = []
            for f in files:
                result = read_py_file_content(f)
                if result is None:
                    continue
                content, lines = result
                if skip_tests and is_test_file(f):
                    continue
                if skip_configs and is_config_file(f):
                    continue
                issues.extend(func(f, content, lines))
            return issues
        return wrapper
    return decorator


_RHS_CLASSIFIERS: list[tuple[str, re.Pattern | tuple[str, ...]]] = [
    ("numpy",         re.compile(r'\.cpu\(\)\s*\.numpy\(\)')),
    ("from_numpy",    re.compile(r'torch\.from_numpy\s*\(')),
    ("numpy",         ("np.", "numpy.", "np.where", "np.unique", "np.array",
                       "np.zeros", "np.ones", "np.arange", "np.load", "np.nan")),
    ("torch",         ("torch.", ".npu(", ".cuda(", ".to(", ".detach(", ".float(", ".half(")),
    ("tensor_method", (".view(", ".reshape(", ".squeeze(", ".unsqueeze(",
                       ".new_zeros(", ".new_ones(", ".expand(",
                       ".permute(", ".transpose(", ".contiguous(",
                       ".clone(", ".gather(", ".scatter(", ".index_select(",
                       ".cat(", ".stack(")),
    ("python_builtin",("len(", "range(", "int(", "float(", "round(",
                       "abs(", ".item()", ".shape", ".size(", ".numel()",
                       "math.", "isinstance(", "list(", "dict(", "set(",
                       "tuple(", "str(", "bool(", "sorted(", "enumerate(")),
]

_TYPE_CAST_METHODS_RE = re.compile(r'\)\s*\.\s*(?:long|float|half|int|bool|to|contiguous|squeeze|unsqueeze|view|reshape|permute|transpose|expand|clone|detach|cpu|cuda|npu)\s*\(\)\s*$')
_PAREN_METHOD_RE = re.compile(r'\(.*\)\s*\.')
_LITERAL_RE = re.compile(r'^[-+]?\d+\.?\d*$')
_INDEX_EXPR_RE = re.compile(r'\w+\s*\[')
_SIMPLE_VAR_RE = re.compile(r'^(\w+)$')
_ASSIGN_RE_TEMPLATE = r'^\s*{var}\s*=\s*(.+)$'
_UNPACK_RE_TEMPLATE = r'^\s*(?:\w+\s*,\s*)*{var}\s*(?:,\s*\w+)*\s*=\s*(.+)$'
_NUMPY_RE = re.compile(r'\bnp\.\w+|\bnumpy\.\w+')
_TORCH_RE = re.compile(r'\btorch\.\w+|\.npu\(|\.cuda\(|\.to\(|\.detach\(|\.float\(|\.half\(')


def _extract_rhs(var_name: str, stripped: str) -> str | None:
    assign_re = re.compile(_ASSIGN_RE_TEMPLATE.format(var=re.escape(var_name)))
    m = assign_re.match(stripped)
    if m:
        return m.group(1).strip()
    unpack_re = re.compile(_UNPACK_RE_TEMPLATE.format(var=re.escape(var_name)))
    m = unpack_re.match(stripped)
    return m.group(1).strip() if m else None


def _classify_rhs(rhs: str) -> str:
    inner = _TYPE_CAST_METHODS_RE.sub(')', rhs)
    if inner != rhs:
        return _classify_rhs(inner)
    if rhs.startswith('(') and rhs.endswith(')') and _PAREN_METHOD_RE.search(rhs) is None:
        depth = 0
        for ch in rhs:
            depth += 1 if ch == '(' else -1 if ch == ')' else 0
            if depth == 0 and ch != ')':
                break
        else:
            return _classify_rhs(rhs[1:-1])
    for kind, pattern in _RHS_CLASSIFIERS:
        if isinstance(pattern, re.Pattern):
            if pattern.search(rhs):
                return kind
        elif any(ind in rhs for ind in pattern):
            return kind
    if _LITERAL_RE.match(rhs) or rhs in ('True', 'False', 'None'):
        return "literal"
    if rhs.startswith(('[', '{')) and not _PAREN_METHOD_RE.search(rhs):
        return "literal"
    if _INDEX_EXPR_RE.match(rhs):
        return "index_expr"
    if _NUMPY_RE.search(rhs) and not _TORCH_RE.search(rhs):
        return "numpy"
    if re.search(r'\w+\s*(?:[-+*/%]|//)\s*\w+', rhs):
        return "arithmetic_expr"
    return "unknown"


def _resolve_arithmetic_source(
    rhs: str, lines: list[str], lineno: int,
    max_backward: int, offset: int, visited: set[str],
) -> tuple[str | None, int]:
    has_numpy, any_torch = False, False
    operands = re.split(r'\s*(?:[-+*/%]|//)\s*', rhs)
    _CPU_NUMPY_BASE_RE = re.compile(r'^(\w+)\.cpu\(\)\s*\.numpy\(\)')
    for op in operands:
        op = op.strip()
        if re.match(r'^\w+\.\w+$', op) or op.startswith('self.'):
            continue
        if re.match(r'^[-+]?\d+\.?\d*$', op):
            continue
        cpu_numpy_match = _CPU_NUMPY_BASE_RE.match(op)
        if cpu_numpy_match:
            base_var = cpu_numpy_match.group(1)
            sk, _ = trace_var_source(base_var, lines, lineno,
                                     max_backward - offset, visited)
            if sk in ("torch", "from_numpy", "tensor_method"):
                any_torch = True
            elif sk == "numpy":
                has_numpy = True
            continue
        op_var = re.match(r'^(\w+)$', op)
        if op_var:
            sk, _ = trace_var_source(op_var.group(1), lines, lineno,
                                     max_backward - offset, visited)
            if sk in ("torch", "from_numpy", "tensor_method"):
                any_torch = True
            elif sk == "numpy":
                has_numpy = True
    if any_torch:
        return ("torch", lineno)
    if has_numpy:
        return ("numpy", lineno)
    return ("unknown", lineno)


def trace_var_source(
    var_name: str,
    lines: list[str],
    start_lineno: int,
    max_backward: int | None = None,
    _visited: set[str] | None = None,
) -> tuple[str | None, int]:
    """Walk backward from start_lineno to find the most recent assignment
    of var_name, then classify its RHS expression.

    Returns (source_kind, lineno). source_kind is one of {numpy, torch,
    from_numpy, tensor_method, index_expr, python_builtin, literal,
    unknown, param_default}.
    """
    visited = _visited or set()
    if var_name in visited:
        return ("unknown", 0)
    visited = visited | {var_name}
    if max_backward is None:
        max_backward = get_config().var_source_max_backward

    for offset in range(1, max_backward + 1):
        lineno = start_lineno - offset
        if lineno < 1:
            break
        stripped = lines[lineno - 1].strip()
        if stripped.startswith('#'):
            continue

        rhs = _extract_rhs(var_name, stripped)
        if rhs is None:
            if re.match(rf'^\s*def\s+\w+\s*\([^)]*\b{re.escape(var_name)}\b', stripped):
                return ("param_default", lineno)
            continue

        kind = _classify_rhs(rhs)
        if kind == "arithmetic_expr":
            return _resolve_arithmetic_source(rhs, lines, lineno, max_backward, offset, visited)
        if kind == "index_expr":
            base_match = re.match(r'^(\w+)\s*\[', rhs)
            if base_match:
                return trace_var_source(base_match.group(1), lines, lineno,
                                       max_backward - offset, visited)
            return ("index_expr", lineno)
        if kind != "unknown":
            return (kind, lineno)

        simple_var = _SIMPLE_VAR_RE.match(rhs)
        if simple_var:
            return trace_var_source(simple_var.group(1), lines, lineno,
                                   max_backward - offset, visited)
        return ("unknown", lineno)

    return (None, 0)


def var_source_is_numpy(var_name: str, lines: list[str], lineno: int,
                        max_backward: int | None = None) -> bool:
    kind, _ = trace_var_source(var_name, lines, lineno, max_backward)
    return kind == "numpy"


def var_source_is_python_scalar(var_name: str, lines: list[str], lineno: int,
                                max_backward: int | None = None) -> bool:
    kind, _ = trace_var_source(var_name, lines, lineno, max_backward)
    return kind in ("python_builtin", "literal", "param_default")


class ScopeTracker:
    """Mixin implementing scope-aware variable tracking in AST
    visitors."""

    def _init_scope_tracking(self):
        self._scope_stack: list[dict] = []

    def _enter_scope(self):
        self._scope_stack.append(self._capture_state())

    def _exit_scope(self):
        if self._scope_stack:
            self._restore_state(self._scope_stack.pop())

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._enter_scope()
        self.generic_visit(node)
        self._exit_scope()

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self._enter_scope()
        self.generic_visit(node)
        self._exit_scope()

    def _capture_state(self) -> dict:
        raise NotImplementedError("Subclass must implement _capture_state()")

    def _restore_state(self, state: dict):
        raise NotImplementedError("Subclass must implement _restore_state()")
