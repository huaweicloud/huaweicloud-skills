from __future__ import annotations
"""STRUCTURE category scanner — code structure patterns affecting NPU.

Pattern:
- P_ENT: entry point detection (VLA needs NPU wrapping)
- P_VEC: vectorizable tensor-indexing loops
"""

import ast
import re
from pathlib import Path

from patterns import Issue
from .helpers import file_scanner
from config import get_config, get_context_config
from utils import get_context


_BUILD_ENTRY_CALLS = {'setup', 'setuptools.setup', 'distutils.core.setup'}

# Entry-point purpose classification: first judge by filename signals
# (train/eval/serve, etc.), then use generic content signals. Shared params
# (dataset_path/embodiment_tag, etc.) do not participate in the train
# judgment, otherwise eval/data tools would be misclassified as training
# entry points.
_ENTRY_EVAL_MARKERS = (
    'open_loop', 'closed_loop', 'rollout',
    'n_episodes', 'num_episodes', 'max_episode_steps',
    'policy_host', 'policy_port', 'env_name', 'success_rate',
)
_ENTRY_INFERENCE_MARKERS = (
    'policy_client', 'policy_server', 'inference_server',
    'model.generate', 'grpc', 'triton',
)
_ENTRY_TRAIN_MARKERS = (
    'TrainingArguments', 'trainer.train', 'MODEL_REGISTRY',
    'base_model_path', 'num_gpus', 'deepspeed', 'accelerate', 'finetune',
)


def classify_entry_purpose(file_rel: str, content: str) -> str:
    """Classify an entry point's purpose: train / inference / eval /
    deploy / test / other.

    Only train, inference, and eval entry points are recognized; test,
    CUDA/TRT deploy tools, data tools, etc. are all grouped into the
    "other" category for upstream filtering. Judgment is based on path and
    content keywords, no weighting.
    """
    name = Path(file_rel).name
    # Test scripts
    if re.search(r'(^|/)(tests?|test_|.+_test)\.py$', file_rel) \
            or name.startswith('test_') or name.endswith('_test.py') \
            or '_run_' in name or name.startswith('_run_'):
        return 'test'
    # CUDA/TRT/ONNX deployment stacks (not involved in NPU adaptation)
    if 'deployment' in file_rel or 'tensorrt' in file_rel.lower() or 'onnx' in file_rel.lower() \
            or 'import tensorrt' in content or 'import onnx' in content:
        return 'deploy'
    # Filename signals (most reliable, before content signals)
    # Note the order: eval/rollout before policy, to avoid eval-policy
    # files like rollout_policy.py being misclassified as the inference
    # side; serve_policy.py etc. on the inference side go to inference.
    if 'finetune' in name or 'train' in name:
        return 'train'
    if 'eval' in name or 'rollout' in name:
        return 'eval'
    if 'inference' in name or 'serve' in name:
        return 'inference'
    # Content signals: eval/inference-only signals take priority, avoiding
    # being swallowed by train
    if any(m in content for m in _ENTRY_EVAL_MARKERS):
        return 'eval'
    if any(m in content for m in _ENTRY_INFERENCE_MARKERS):
        return 'inference'
    # Training entry points (only strong signals, not shared params like
    # dataset_path/embodiment_tag)
    if any(m in content for m in _ENTRY_TRAIN_MARKERS):
        return 'train'
    return 'other'

_P_VEC_BATCH_SIZE_HINTS = (
    'bs', 'batch', 'batch_size', 'num_imgs', 'num_samples',
)

_P_VEC_SMALL_ATTR_HINTS = (
    'n_classes', 'num_classes', 'num_stuff_classes', 'num_things_classes',
    'num_levels', 'num_layers', 'num_dec_things', 'num_dec_stuff',
)

_P_VEC_SMALL_LOOP_THRESHOLD = 8

_P_VEC_TORCH_INDICATORS = (
    'import torch', 'from torch',
)


def _file_uses_torch(content: str) -> bool:
    for indicator in _P_VEC_TORCH_INDICATORS:
        if indicator in content:
            return True
    return False


def _is_range_loop(node) -> bool:
    if not isinstance(node.iter, ast.Call):
        return False
    return (isinstance(node.iter.func, ast.Name)
            and node.iter.func.id == 'range'
            and node.iter.args)


def _is_small_literal_range(range_arg) -> bool:
    return (isinstance(range_arg, ast.Constant)
            and isinstance(range_arg.value, int)
            and range_arg.value <= _P_VEC_SMALL_LOOP_THRESHOLD)


def _is_batch_size_range(range_arg) -> bool:
    if isinstance(range_arg, ast.Name):
        return any(hint in range_arg.id.lower() for hint in _P_VEC_BATCH_SIZE_HINTS)
    return False


def _is_self_attr_small_range(range_arg) -> bool:
    if isinstance(range_arg, ast.Attribute) and isinstance(range_arg.value, ast.Name):
        if range_arg.value.id == 'self':
            return any(hint in range_arg.attr.lower() for hint in _P_VEC_SMALL_ATTR_HINTS)
    return False


def _is_batch_len_range(range_arg) -> bool:
    if isinstance(range_arg, ast.Call):
        if isinstance(range_arg.func, ast.Name) and range_arg.func.id == 'len':
            if range_arg.args and isinstance(range_arg.args[0], ast.Name):
                return any(hint in range_arg.args[0].id.lower()
                           for hint in _P_VEC_BATCH_SIZE_HINTS)
    return False


def _is_small_or_batch_loop(node) -> bool:
    if not _is_range_loop(node):
        return False
    range_arg = node.iter.args[0]
    return (_is_small_literal_range(range_arg)
            or _is_batch_size_range(range_arg)
            or _is_self_attr_small_range(range_arg)
            or _is_batch_len_range(range_arg))


class SemanticScanner(ast.NodeVisitor):
    """Scans semantic issues that require context-aware fixes."""

    def __init__(self, file: str, lines: list[str]):
        self.file_path = file
        self.lines = lines
        self.issues: list[Issue] = []
        self._numpy_vars: set = set()
        self._scan_numpy_creations(lines)

    def _scan_numpy_creations(self, lines: list[str]):
        for line in lines:
            stripped = line.strip()
            m = re.match(
                r'(\w+)\s*=\s*np\.\s*(?:zeros|ones|array|full|empty|arange|linspace)'
                r'(?:_like)?\s*\(', stripped)
            if m:
                self._numpy_vars.add(m.group(1))

    def _add_vec_issue(self, node):
        ctx = get_context_config('P_VEC')
        self.issues.append(Issue(pattern_id='P_VEC', file=self.file_path, line=node.lineno,
        code=self.lines[node.lineno - 1].strip(),
        context=get_context(self.lines, node.lineno, before=ctx['before'], after=ctx['after'])))

    def _loop_body_has_mul_sum(self, node) -> bool:
        body_text = '\n'.join(self.lines[node.lineno - 1:node.end_lineno])
        if '.sum(' in body_text and '*' in body_text:
            if re.search(r'\(.*\*.*\)\s*\.sum\s*\(', body_text):
                return True
            lines_in_body = body_text.split('\n')
            for i, line in enumerate(lines_in_body):
                stripped = line.strip()
                if stripped.startswith('#'):
                    continue
                var_match = re.match(r'\s*(\w+)\s*=\s*\(.*\*', stripped)
                if not var_match:
                    if re.search(r'\w+\[.*\]\s*\*\s*\w+\[.*\]', stripped):
                        for j in range(i + 1, min(i + 4, len(lines_in_body))):
                            next_line = lines_in_body[j].strip()
                            if '.sum(' in next_line:
                                return True
            if re.search(r'\(\s*\n.*\*\s*\n.*\)\s*\.sum\s*\(', body_text, re.MULTILINE):
                return True
        return False

    def visit_For(self, node: ast.For) -> None:
        if self._loop_body_has_mul_sum(node):
            pass
        elif _is_small_or_batch_loop(node):
            pass
        elif self._is_tensor_index_loop(node) or self._is_tensor_subscript_assign_loop(node):
            self._add_vec_issue(node)
        self.generic_visit(node)

    def _is_tensor_index_loop(self, node) -> bool:
        if not isinstance(node.iter, ast.Call):
            return False
        if not isinstance(node.iter.func, ast.Name) or node.iter.func.id != 'range':
            return False
        if not node.iter.args:
            return False
        range_arg = node.iter.args[0]
        if isinstance(range_arg, ast.Call):
            if isinstance(range_arg.func, ast.Name) and range_arg.func.id == 'len':
                iter_var = node.target.id if isinstance(node.target, ast.Name) else None
                if iter_var and self._has_tensor_index_access(node.body, iter_var):
                    return True
        return False

    def _has_tensor_index_access(self, body, iter_var: str) -> bool:
        for stmt in body:
            if isinstance(stmt, ast.Assign) and isinstance(stmt.value, ast.Call):
                if self._is_item_call_on_index(stmt.value, iter_var):
                    return True
            if isinstance(stmt, ast.If):
                if self._has_tensor_index_access(stmt.body, iter_var):
                    return True
                if self._has_tensor_index_access(stmt.orelse, iter_var):
                    return True
        return False

    def _is_item_call_on_index(self, node, iter_var: str) -> bool:
        if not isinstance(node.func, ast.Attribute) or node.func.attr != 'item':
            return False
        subscript = node.func.value
        if not isinstance(subscript, ast.Subscript):
            return False
        if isinstance(subscript.slice, ast.Name):
            return subscript.slice.id == iter_var
        return False

    def _is_tensor_subscript_assign_loop(self, node) -> bool:
        if not isinstance(node.iter, ast.Call):
            return False
        if not isinstance(node.iter.func, ast.Name) or node.iter.func.id != 'range':
            return False
        if not node.iter.args:
            return False
        if not isinstance(node.target, ast.Name):
            return False
        iter_var = node.target.id

        for stmt in node.body:
            if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1:
                target = stmt.targets[0]
                if isinstance(target, ast.Subscript):
                    if isinstance(target.slice, ast.Name) and target.slice.id == iter_var:
                        target_name = None
                        if isinstance(target.value, ast.Name):
                            target_name = target.value.id
                        if target_name and target_name in self._numpy_vars:
                            continue
                        return True
        return False


@file_scanner()
def scan_p_ent(f: Path, content: str, lines: list[str]) -> list[Issue]:
    """Scan P_ENT (entry point detection) — VLA: transformers/accelerate.

    P_ENT: any file with a __main__ guard that imports torch is an entry
    point candidate. Files without a torch import are excluded because they
    don't need NPU device setup.

    For VLA models, entry points may use:
    - transformers.Trainer / accelerate.launch
    - torchrun for distributed training
    - custom training scripts

    Excluded: files where the __main__ guard calls setuptools.setup() or
    distutils.core.setup() are extension build scripts, not training entry
    points.

    Also detects: --local_rank argparse args (should be --local-rank for
    torchrun compatibility).
    """
    issues = []

    # Entry point candidates: have a __main__ guard and import torch or
    # tyro. tyro is a common CLI-parsing library in VLA projects — thin
    # shell entry files (only parse args then delegate to run()/main())
    # usually import tyro rather than torch directly.
    has_torch_import = ('import torch' in content or 'from torch' in content
                        or 'import tyro' in content)
    if not has_torch_import:
        return issues

    has_torch_npu_import = 'import torch_npu' in content
    if has_torch_npu_import:
        return issues

    # Only keep train/inference/eval entry points; filter out false
    # positives like test, deploy tools, data tools, etc.
    purpose = classify_entry_purpose(str(f), content)
    if purpose not in ('train', 'inference', 'eval'):
        return issues

    is_entry_point = False
    has_local_rank_arg = False
    for i, line in enumerate(lines, 1):
        if not is_entry_point and ("__name__ == '__main__'" in line or '__name__ == "__main__"' in line):
            main_block_lines = lines[i:min(i + get_config().entry_guard_lines, len(lines))]
            main_block_text = '\n'.join(main_block_lines)
            is_build_script = any(
                re.search(rf'(?:setuptools|distutils\.core)?\.?{re.escape(call)}\s*\(', main_block_text)
                for call in _BUILD_ENTRY_CALLS
            )
            if is_build_script:
                break

            is_entry_point = True
            entry_line = i
            ctx = get_context_config('P_ENT')
            issues.append(Issue(pattern_id='P_ENT', file=str(f), line=i,
            code=f"[{purpose}] {line.strip()}",
            context=get_context(lines, i, before=ctx['before'], after=ctx['after'])))
            continue

        if is_entry_point and not has_local_rank_arg and re.search(r'add_argument\s*\(\s*["\']--local_rank["\']', line):
            has_local_rank_arg = True
            ctx = get_context_config('P_ENT')
            issues.append(Issue(pattern_id='P_ENT', file=str(f), line=i,
            code=f"[{purpose}] {line.strip()}",
            context=get_context(lines, i, before=ctx['before'], after=ctx['after'])))

    return issues


def _classify_range_arg(range_arg_str: str) -> bool:
    try:
        val = int(range_arg_str)
        if val <= _P_VEC_SMALL_LOOP_THRESHOLD:
            return True
    except ValueError:
        pass

    if re.match(r'^\w+$', range_arg_str):
        if any(hint in range_arg_str.lower() for hint in _P_VEC_BATCH_SIZE_HINTS):
            return True

    len_match = re.match(r'len\s*\(\s*(\w+)\s*\)', range_arg_str)
    if len_match and any(hint in len_match.group(1).lower() for hint in _P_VEC_BATCH_SIZE_HINTS):
        return True

    self_attr_match = re.match(r'self\.(\w+)', range_arg_str)
    if self_attr_match and any(hint in self_attr_match.group(1).lower() for hint in _P_VEC_SMALL_ATTR_HINTS):
        return True

    return False


def _classify_for_loops(lines: list[str]) -> dict:
    all_for_loops: dict[int, tuple] = {}
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if not stripped.startswith('for '):
            continue

        range_match = re.match(r'for\s+\w+\s+in\s+range\s*\(', stripped)
        if not range_match:
            all_for_loops[i] = (False, False)
            continue

        range_content = stripped[stripped.index('range(') + 6:]
        paren_depth = 1
        range_arg_str = ''
        for ch in range_content:
            if ch == '(':
                paren_depth += 1
            elif ch == ')':
                paren_depth -= 1
                if paren_depth == 0:
                    break
            range_arg_str += ch

        range_arg_str = range_arg_str.strip()
        is_small = _classify_range_arg(range_arg_str)
        all_for_loops[i] = (True, is_small)

    return all_for_loops


def _find_enclosing_loop(line_no: int, lines: list[str],
                         all_for_loops: dict) -> int | None:
    append_indent = len(lines[line_no - 1]) - len(lines[line_no - 1].lstrip())
    for loop_line in sorted(all_for_loops.keys(), reverse=True):
        if loop_line < line_no:
            loop_indent = len(lines[loop_line - 1]) - len(lines[loop_line - 1].lstrip())
            if loop_indent < append_indent:
                return loop_line
    return None


def _track_append_and_cat(file_path: str, lines: list[str],
                          all_for_loops: dict, ctx: dict) -> list[Issue]:
    issues: list[Issue] = []
    append_vars: dict = {}

    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith('#'):
            continue

        append_match = re.search(r'(\w+)\s*\.\s*append\s*\(', line)
        if append_match:
            var_name = append_match.group(1)
            if var_name not in append_vars:
                enclosing_loop_line = _find_enclosing_loop(i, lines, all_for_loops)
                is_vectorizable = False
                if enclosing_loop_line is not None:
                    is_range, is_small = all_for_loops[enclosing_loop_line]
                    is_vectorizable = is_range and not is_small
                append_vars[var_name] = (i, is_vectorizable)

        cat_match = re.search(r'torch\.cat\s*\(\s*(\w+)', line)
        if cat_match:
            cat_var = cat_match.group(1)
            if cat_var in append_vars:
                append_line, is_vectorizable = append_vars[cat_var]
                if not is_vectorizable:
                    continue
                issues.append(Issue(pattern_id='P_VEC', file=file_path, line=append_line,
                code=lines[append_line - 1].strip(),
                context=get_context(lines, append_line, before=ctx['before'], after=ctx['after'])))

    return issues


def _detect_append_then_cat(file_path: str, content: str, lines: list[str], issues: list[Issue]):
    ctx = get_context_config('P_VEC')
    all_for_loops = _classify_for_loops(lines)
    new_issues = _track_append_and_cat(file_path, lines, all_for_loops, ctx)
    issues.extend(new_issues)


@file_scanner()
def scan_p_vec(f: Path, content: str, lines: list[str]) -> list[Issue]:
    """Scan complex tensor loops (P_VEC).

    Early exit: if the file does not import torch, there cannot be NPU
    tensor loops.
    """
    issues = []

    if not _file_uses_torch(content):
        return issues

    try:
        tree = ast.parse(content)
    except SyntaxError:
        return issues

    scanner = SemanticScanner(str(f), lines)
    scanner.visit(tree)
    issues.extend(scanner.issues)

    _detect_append_then_cat(str(f), content, lines, issues)

    return issues


__all__ = [
    'SemanticScanner',
    'scan_p_ent',
    'scan_p_vec',
]
