#!/usr/bin/env python3
"""Shared, locked pipeline checkpoint protocol. Python 3.9+, Windows/macOS/Linux."""
import argparse
import copy
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import sys
import tempfile
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Dict, List, Union

from platform_utils import IS_WINDOWS, atomic_replace, configure_console, file_lock

JSONValue = Union[None, bool, int, float, str, List['JSONValue'], Dict[str, 'JSONValue']]

ROOT = Path.home() / '.cloudrobo' / 'pipeline-runs'
TERMINAL = {'SUCCEEDED', 'FAILED', 'DELETED'}
RUN_TERMINAL = {'SUCCEEDED', 'SUCCEEDED_WITH_WARNINGS', 'FAILED', 'TERMINATED'}
RESULT_FIELDS = ('status', 'output_name', 'target_path', 'target_asset_id', 'target_version_id',
                 'target_report_path', 'error', 'start_at', 'finish_at', 'pod_names')


class StateError(Exception):
    code = 400


class Conflict(StateError):
    code = 409


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def safe_id(value) -> str:
    if not isinstance(value, str) or not re.fullmatch(r'[a-zA-Z0-9_][a-zA-Z0-9_.-]{0,159}', value):
        raise StateError('无效的运行、步骤或任务 ID')
    reserved = {'CON', 'PRN', 'AUX', 'NUL', 'CONIN$', 'CONOUT$'}
    reserved.update(f'{prefix}{number}' for prefix in ('COM', 'LPT') for number in range(1, 10))
    if IS_WINDOWS and (value.endswith('.') or value.split('.')[0].upper() in reserved):
        raise StateError('ID 不能使用 Windows 保留设备名或以点结尾')
    return value


def atomic_json(path, value) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix='.write-')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as file:
            json.dump(value, file, ensure_ascii=False, indent=2)
            file.write('\n')
            file.flush()
            os.fsync(file.fileno())
        atomic_replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def read_json_object(path) -> dict:
    value = json.loads(Path(path).read_text(encoding='utf-8-sig'))
    if not isinstance(value, dict):
        raise StateError('JSON 文件必须包含对象: ' + Path(path).name)
    return value


def redact(value: JSONValue) -> JSONValue:
    """Mask secrets in nested objects, env entries and JSON-array string fields."""
    secret = re.compile(r'(^|_)(AK|SK)($|_)|SECRET|TOKEN|PASSWORD|ACCESS.?KEY|CREDENTIAL', re.I)
    result = value
    if isinstance(value, dict):
        if secret.search(str(value.get('key', value.get('name', '')))) and ('value' in value or 'default' in value):
            result = {k: ('••••••' if k in {'value', 'default'} else redact(v)) for k, v in value.items()}
        else:
            result = {k: ('••••••' if secret.search(k) else redact(v)) for k, v in value.items()}
    elif isinstance(value, list):
        result = [redact(item) for item in value]
    elif isinstance(value, str) and value.lstrip().startswith(('[', '{')):
        try:
            result = json.dumps(redact(json.loads(value)), ensure_ascii=False)
        except ValueError:
            pass
    return result


def data_references(stage, inputs) -> list:
    """Ordered data bindings; dependencies may additionally contain control-only gates."""
    if 'input_from' in stage:
        refs = stage['input_from']
    else:
        dependencies = stage.get('depends_on', [])
        if len(dependencies) > 1:
            raise StateError('多个等待依赖须用 input_from 明确数据来源和顺序')
        if dependencies == ['upload']:
            dependencies = []  # Legacy v2 root: synthetic registration is not a dataset producer.
        refs = dependencies or ['input:' + str(item.get('id', 'default')) for item in inputs]
        if not dependencies and len(inputs) > 1:
            raise StateError('多个初始数据集须用 input_from 明确选择，不自动合并')
    if not isinstance(refs, list) or not refs or any(not isinstance(ref, str) or not ref for ref in refs):
        raise StateError('input_from 须为非空的数据来源字符串数组')
    if len(refs) != len(set(refs)):
        raise StateError('input_from 不能包含重复的数据来源')
    if stage.get('kind') in {'eval', 'eval-group'} and len(refs) != 1:
        raise StateError('评测接口只接受一个数据集；请先用处理/合并算子得到单个数据集')
    return list(refs)


def validate_bindings(stage, stages, inputs) -> None:
    """Validate data producers separately from control dependencies."""
    refs = data_references(stage, inputs)
    sources = {str(item.get('id', 'default')) for item in inputs}
    for ref in refs:
        if ref.startswith('input:'):
            if ref[6:] not in sources:
                raise StateError('初始输入不存在：' + ref)
        else:
            if ref not in stages:
                raise StateError('数据来源步骤不存在：' + ref)
            if stages[ref].get('kind') != 'proc':
                raise StateError('评测只产出报告或该步骤不产出数据集，不能作为数据来源：' + ref)
            if ref not in stage['depends_on']:
                raise StateError('input_from 的数据来源须包含在 depends_on 等待依赖中：' + ref)


def is_bypassed(item) -> bool:
    return bool(item.get('bypassed') and item.get('skipped') and item.get('status') == 'SKIPPED')


def source_format(plan, state, ref, visited=None) -> str:
    """Known format hints only; unknown workspace contracts require live Agent checks."""
    visited = set() if visited is None else visited
    if ref in visited:
        raise StateError('跳过数据来源存在循环')
    if ref.startswith('input:'):
        source = next((item for item in state.get('inputs', []) if str(item.get('id', 'default')) == ref[6:]), {})
        return str(source.get('data_source_type') or '').lower()
    item = state['stages'].get(ref, {})
    if is_bypassed(item):
        return source_format(plan, state, item['bypass_from'], visited | {ref})
    spec = next((stage for stage in plan['stages'] if stage['id'] == ref), {})
    name = spec.get('operator') if spec.get('operator_source', 'preset') == 'preset' else ''
    if name in {'数据转换--H5转LeRobotV3', '数据转换--ros转LeRobotV3', '数据转换--UMI转LeRobotV3', '数据清洗'}:
        return 'lerobotv3'
    return ''


def bypass_spec(plan, state, sid) -> dict:
    stage = next((item for item in plan['stages'] if item['id'] == sid), {})
    if stage.get('kind') != 'proc' or stage.get('external'):
        raise StateError('仅未提交的处理步骤可以申请保留原输入跳过')
    refs = data_references(stage, plan.get('inputs', []))
    if len(refs) != 1:
        raise StateError('多输入合并步骤不能原样跳过为单输出，请回智能体调整管线')
    affected = {sid}
    consumers = []
    changed = True
    while changed:
        changed = False
        for target in plan['stages']:
            if target['kind'] == 'manual' or target['id'] in affected:
                continue
            inputs = data_references(target, plan.get('inputs', []))
            if affected.intersection(inputs):
                affected.add(target['id'])
                changed = True
                if sid in inputs:
                    consumers.append(target)
    for target in affected - {sid}:
        item = state['stages'][target]
        members = list(item.get('members', {}).values()) or [item]
        if any(value.get('task_id') or value.get('status') in TERMINAL for value in members):
            raise StateError('下游已经提交或完成，不能改变其数据来源：' + target)
    actual_format = source_format(plan, state, refs[0])
    for target in consumers:
        leaves = target.get('parallel_group', [target])
        for member in leaves:
            name = member.get('operator') if member.get('operator_source', 'preset') == 'preset' else ''
            if name in {'数据清洗', '数据集质量评测-LeRobot', '数据集多样性评测-LeRobot'} and actual_format in {'h5', 'ros2', 'umi'}:
                raise StateError('原输入格式 ' + actual_format + ' 不兼容后续 ' + target['id'] + ' 的 LeRobot 输入要求，不能跳过必要转换')
    return {'input_from': refs, 'consumers': [item['id'] for item in consumers],
            'format': actual_format or '需智能体核实'}


def dataset_inputs(plan, state, sid, resolved_inputs=None) -> dict:
    """Build an ordered CLI input fragment from recorded outputs; never call the cloud."""
    stage = next((item for item in plan['stages'] if item['id'] == sid), None)
    if not stage or stage.get('kind') not in {'proc', 'eval', 'eval-group'}:
        raise StateError('数据输入仅适用于处理或评测步骤')
    validate_bindings(stage, {item['id']: item for item in plan['stages']}, plan.get('inputs', []))
    refs = data_references(stage, plan.get('inputs', []))
    for dependency in stage['depends_on']:
        gate = state['stages'][dependency]
        members = list(gate.get('members', {}).values()) or [gate]
        if any(not item.get('skipped') and item.get('status') != 'SUCCEEDED'
               and (item.get('fail_fast', True) or item.get('status') not in TERMINAL) for item in members):
            raise StateError('等待依赖尚未完成：' + dependency)
    sources = {str(item.get('id', 'default')): item for item in state.get('inputs', [])}
    supplied = {} if resolved_inputs is None else resolved_inputs
    if not isinstance(supplied, dict) or set(supplied) - set(sources):
        raise StateError('inputs-file 须为初始输入 ID 到已核实数据字段的对象，不能覆盖步骤输出')
    allowed = {'asset_id', 'version_id', 'asset_name', 'obs_path'}
    for name, values in supplied.items():
        if not isinstance(values, dict) or set(values) - allowed:
            raise StateError('inputs-file 每项仅允许 asset_id、version_id、asset_name、obs_path：' + name)
        original = sources[name]
        if original.get('source_type') == 'asset' and any(
                field in values and values[field] != original.get(field) for field in ('asset_id', 'version_id')):
            raise StateError('初始资产与确切版本不能被 inputs-file 替换：' + name)
        if original.get('source_type') == 'asset' and original.get('obs_path'):
            if 'obs_path' in values and values['obs_path'] != original['obs_path']:
                raise StateError('已确认的初始资产路径不能被 inputs-file 替换：' + name)
    datasets = []
    for ref in refs:
        if ref.startswith('input:'):
            name = ref[6:]
            if name not in sources:
                raise StateError('初始输入不存在：' + name)
            data = {**sources[name], **supplied.get(name, {})}
            if len(sources) == 1 and not data.get('asset_id'):
                upload = state['stages'].get('upload', {})
                data.update({key: upload[key] for key in ('target_path', 'target_asset_id', 'target_version_id', 'output_name') if upload.get(key)})
        else:
            data = state['stages'].get(ref, {})
            completed = data.get('status') == 'SUCCEEDED' and not data.get('skipped')
            if data.get('kind') != 'proc' or not (completed or is_bypassed(data)):
                raise StateError('数据来源必须是成功的处理步骤：' + ref)
        path = data.get('target_path') or data.get('obs_path')
        if not isinstance(path, str) or not re.fullmatch(r'obs://[^/\s]+/[^\s]*', path):
            raise StateError('数据来源缺少已核实的 OBS 路径：' + ref)
        dataset = {'dataset_type': 'BUILD_IN_ASSET', 'obs_path': path,
                   'asset_id': data.get('target_asset_id') or data.get('asset_id'),
                   'version_id': data.get('target_version_id') or data.get('version_id'),
                   'asset_name': data.get('output_name') or data.get('asset_name')}
        if any(not isinstance(value, str) or not value.strip() for value in dataset.values()):
            raise StateError('数据来源缺少资产、确切版本或名称：' + ref + '；请先核实交接信息')
        datasets.append(dataset)
    config = {'dataset_configs': json.dumps(datasets, ensure_ascii=False)}
    if stage['kind'] in {'eval', 'eval-group'}:
        entry = datasets[0]
        config.update(dataset_type=entry['dataset_type'], dataset_id=entry['asset_id'],
                      dataset_name=entry['asset_name'], dataset_path=entry['obs_path'])
    return {'input_from': refs, 'datasets': datasets, 'task_config': config}


def validate_task_datasets(config, kind) -> list:
    """Validate the wire representation, including the versions Console cloning needs."""
    value = config.get('dataset_configs')
    if not isinstance(value, str):
        raise StateError('dataset_configs 必须为 JSON 数组字符串；资产输入必须携带确切 version_id')
    try:
        datasets = json.loads(value)
    except ValueError:
        raise StateError('dataset_configs 不是有效的 JSON 数组字符串') from None
    if not isinstance(datasets, list) or not datasets or any(not isinstance(item, dict) for item in datasets):
        raise StateError('dataset_configs 必须包含至少一项数据集对象')
    if kind == 'eval' and len(datasets) != 1:
        raise StateError('评测 dataset_configs 必须恰好包含一个数据集')
    for index, item in enumerate(datasets):
        label = 'dataset_configs[' + str(index) + ']'
        if item.get('dataset_type') not in {'BUILD_IN_ASSET', 'UDF_OBS_ASSET'}:
            raise StateError(label + '.dataset_type 无效')
        if not isinstance(item.get('obs_path'), str) or not re.fullmatch(r'obs://[^/\s]+/[^\s]*', item['obs_path']):
            raise StateError(label + '.obs_path 必须为已核实的 OBS 路径')
        if item['dataset_type'] == 'BUILD_IN_ASSET':
            for key in ('asset_id', 'asset_name', 'version_id'):
                if not isinstance(item.get(key), str) or not item[key].strip():
                    raise StateError(label + '.' + key + ' 缺失；请核实确切资产版本，不使用最新版本猜测')
        if kind == 'eval':
            mapping = {'dataset_type': 'dataset_type', 'dataset_path': 'obs_path'}
            if item['dataset_type'] == 'BUILD_IN_ASSET':
                mapping.update(dataset_id='asset_id', dataset_name='asset_name')
            if any(config.get(key) != item.get(source) for key, source in mapping.items()):
                raise StateError('评测顶层数据集字段与 dataset_configs 的资产或路径不一致')
    return datasets


def reuses_registered_inputs(inputs) -> bool:
    """Use original run sources, not the assets produced by input preparation."""
    return bool(inputs and all(
        isinstance(item, dict) and item.get('source_type') == 'asset'
        and item.get('asset_id') and item.get('version_id') for item in inputs))


def reject_removed_fields(raw) -> None:
    """New runs only; saved legacy plans stay readable."""
    stages = raw.get('pipeline', raw).get('stages', [])
    stages = stages.values() if isinstance(stages, dict) else stages
    for stage in stages:
        if not isinstance(stage, dict):
            continue
        for item in [stage, *[m for m in stage.get('parallel_group') or [] if isinstance(m, dict)]]:
            if 'robot_config' in item:
                raise StateError('robot_config 已废弃：请在评测成员 params.inputs 中挂载算子声明的配置输入'
                                 '（如 ROBOT_CONFIG_PATH），url_path 填 OBS 目录：' + str(item.get('id', stage.get('id'))))


def normalize_plan(raw) -> dict:
    plan = copy.deepcopy(raw.get('pipeline', raw))
    stages = plan.get('stages', [])
    if isinstance(stages, dict):
        stages = [dict(v, id=k) for k, v in stages.items()]
    if not stages:
        raise StateError('计划必须包含非空 stages')
    # Resolve bindings before synthetic bookends so upload/output never become datasets.
    inputs = plan.get('inputs', [])
    if not isinstance(inputs, list) or any(not isinstance(item, dict) for item in inputs):
        raise StateError('inputs 必须为数据源对象数组')
    input_ids = [safe_id(item.get('id', 'default')) for item in inputs]
    if len(input_ids) != len(set(input_ids)):
        raise StateError('多个初始输入须提供唯一 id')
    previous_data = None
    for stage in stages:
        stage.setdefault('kind', 'eval-group' if stage.get('parallel_group') else 'proc')
        if stage.get('kind') == 'manual':
            previous_data = None
            continue
        if 'input_from' in stage:
            stage['input_from'] = data_references(stage, plan.get('inputs', []))
            stage.setdefault('depends_on', [ref for ref in stage['input_from'] if not ref.startswith('input:')])
        else:
            dependencies = stage.get('depends_on', [previous_data] if previous_data else [])
            if not isinstance(dependencies, list) or any(not isinstance(dep, str) for dep in dependencies):
                raise StateError('depends_on 必须为步骤 ID 数组')
            # Legacy monitoring plans without source metadata remain viewable.
            if inputs or dependencies:
                stage['input_from'] = data_references({**stage, 'depends_on': dependencies}, inputs)
        previous_data = stage['id']
    output_step = None
    if plan.get('monitor_bookends', True):
        ids = {stage['id'] for stage in stages}
        if 'plan' not in ids:
            stages.insert(0, {'id': 'plan', 'name': '计划确认', 'kind': 'manual', 'depends_on': []})
        if 'upload' not in ids:
            stages.insert(1, {'id': 'upload', 'name': '上传注册', 'kind': 'manual', 'depends_on': ['plan']})
        if 'output' not in ids:
            output_step = {'id': 'output', 'name': '产物核对', 'kind': 'manual'}
            stages.append(output_step)
    seen = set()
    previous = None
    for stage in stages:
        sid = safe_id(stage['id'])
        if sid in seen:
            raise StateError('步骤 ID 重复: ' + sid)
        seen.add(sid)
        stage.setdefault('name', {'cleaning': '数据清洗', 'convert-lerobotv3': '格式转换'}.get(sid, sid))
        stage.setdefault('depends_on', [previous] if previous else [])
        if not isinstance(stage['depends_on'], list) or any(not isinstance(dep, str) for dep in stage['depends_on']):
            raise StateError('depends_on 必须为步骤 ID 数组')
        if len(stage['depends_on']) != len(set(stage['depends_on'])):
            raise StateError('depends_on 不能包含重复依赖')
        stage.setdefault('kind', 'eval-group' if stage.get('parallel_group') else 'proc')
        stage.setdefault('fail_fast', stage['kind'] not in {'eval', 'eval-group'})
        if stage['kind'] != 'manual' and not stage['depends_on'] and not stage.get('external'):
            if any(item['id'] == 'upload' for item in stages):
                stage['depends_on'] = ['upload']
        if sid == 'upload' and stage['kind'] == 'manual':
            stage['not_applicable'] = reuses_registered_inputs(plan.get('inputs', []))
            if stage['not_applicable']:
                stage['skip_reason'] = '复用已有数据资产版本，无需上传或注册；输入版本与路径在计划确认中核实。'
        members = stage.get('parallel_group', [])
        member_ids = [safe_id(m['id']) for m in members]
        if len(member_ids) != len(set(member_ids)) or stage['kind'] == 'eval-group' and not members:
            raise StateError('并行成员不能为空且 ID 不能重复')
        previous = sid
    if output_step is not None:
        earlier = [stage for stage in stages if stage is not output_step]
        dependencies = {dep for stage in earlier for dep in stage['depends_on']}
        output_step['depends_on'] = [stage['id'] for stage in earlier if stage['id'] not in dependencies]
    layers = {}
    def visit(sid, stack) -> int:
        if sid in layers:
            return layers[sid]
        if sid in stack or sid not in seen:
            raise StateError('计划包含循环或不存在的依赖: ' + sid)
        stage = next(s for s in stages if s['id'] == sid)
        layers[sid] = 1 + max((visit(d, stack | {sid}) for d in stage['depends_on']), default=-1)
        return layers[sid]
    for stage in stages:
        stage['layer'] = visit(stage['id'], set())
        if 'input_from' in stage:
            validate_bindings(stage, {item['id']: item for item in stages}, inputs)
    plan['stages'] = stages
    return plan


def stage_ref(state, stage, member=None) -> dict:
    try:
        result = state['stages'][stage]
        return result['members'][member] if member else result
    except (KeyError, TypeError):
        raise StateError('步骤或并行成员不存在') from None


def registered_inputs(state) -> list:
    """Project recorded initial datasets, including the legacy single-upload fields."""
    sources = copy.deepcopy(state.get('inputs', []))
    upload = state.get('stages', {}).get('upload', {})
    if not sources and upload.get('target_asset_id'):
        sources = [{}]
    if len(sources) == 1:
        source = sources[0]
        legacy = {'asset_id': 'target_asset_id', 'version_id': 'target_version_id',
                  'obs_path': 'target_path', 'asset_name': 'output_name'}
        for field, old_field in legacy.items():
            if upload.get(old_field) and (source.get('source_type') != 'asset' or not source.get(field)):
                source[field] = upload[old_field]
    return [dict(source, id=source.get('id', 'default')) for source in sources]


def registration_complete(sources) -> bool:
    return bool(sources) and all(
        all(isinstance(source.get(key), str) and source[key].strip() for key in ('asset_id', 'version_id', 'obs_path'))
        and re.fullmatch(r'obs://[^/\s]+/[^\s]*', source['obs_path']) for source in sources)


def iter_steps(state):
    for sid, stage in state.get('stages', {}).items():
        if 'members' in stage:
            for mid, member in stage['members'].items():
                yield sid, mid, member
        else:
            yield sid, None, stage


def same_step(pointer, stage, member) -> bool:
    return bool(pointer and pointer.get('stage') == stage and pointer.get('member') == member)


def task_specs(plan) -> list:
    """Adapt both stage and group syntax into one task graph without rewriting saved plans."""
    stage_keys = {}
    for stage in plan['stages']:
        sid = stage['id']
        stage_keys[sid] = [sid + '/' + member['id'] for member in stage['parallel_group']] if stage.get('parallel_group') else [sid]
    specs = []
    for stage in plan['stages']:
        sid = stage['id']
        members = stage.get('parallel_group') or [None]
        base = {key: value for key, value in stage.items() if key != 'parallel_group'}
        for member in members:
            spec = copy.deepcopy(base)
            mid = None
            if member:
                spec.update(copy.deepcopy(member))
                spec['kind'] = member.get('kind', 'eval')
                mid = member['id']
            spec.update(stage=sid, member=mid, key=sid + '/' + mid if mid else sid)
            spec['dependency_keys'] = [key for dependency in stage['depends_on'] for key in stage_keys[dependency]]
            specs.append(spec)
    return specs


def dependencies_ready(keys, tasks) -> bool:
    """The same completion gates for checkpoint tasks and projected Web nodes."""
    for key in keys:
        if key not in tasks:
            return False
        task = tasks[key]
        status = task.get('display_status', task.get('status'))
        if task.get('skipped') or status in {'SUCCEEDED', 'SKIPPED'}:
            continue
        if not task.get('fail_fast', True) and task.get('raw_status', status) in TERMINAL:
            continue
        return False
    return True


def execution_frontier(plan, state) -> dict:
    """Read-only scheduling advice. No cloud calls, automatic submits or retry authorization."""
    specs = task_specs(plan)
    tasks = {spec['key']: {**spec, **stage_ref(state, spec['stage'], spec['member'])} for spec in specs}
    ready = []
    active = []
    for spec in specs:
        task = tasks[spec['key']]
        if spec['kind'] not in {'proc', 'eval'} or task.get('skipped'):
            continue
        item = {key: spec.get(key) for key in ('key', 'stage', 'member', 'kind', 'operator', 'operator_id',
                                              'operator_source', 'input_from', 'dependency_keys')}
        item.update(task_id=task.get('task_id'), status=task.get('status'))
        if task.get('task_id') and task.get('status') not in TERMINAL:
            active.append(item)
        unsubmitted = not task.get('task_id') and task.get('status') in {None, 'IDLE', 'READY'}
        if unsubmitted and not same_step(state.get('awaiting_decision'), spec['stage'], spec['member']):
            if dependencies_ready(spec['dependency_keys'], tasks):
                ready.append(item)
    if state.get('schema_version') != 2:
        action = 'readonly'
    elif state.get('status') in RUN_TERMINAL:
        action = 'stopped'
    elif state.get('pending_action'):
        action = 'reconcile'
    elif ready:
        action = 'submit'
    elif active:
        action = 'poll'
    elif state.get('awaiting_decision'):
        action = 'decide'
    else:
        action = 'blocked'
    # Include an awaiting_decision summary so the Agent need not call `show` to see the pending decision.
    awaiting = state.get('awaiting_decision')
    awaiting_summary = None
    if awaiting:
        awaiting_summary = {
            'kind': awaiting.get('kind'),
            'stage': awaiting.get('stage'),
            'member': awaiting.get('member'),
            'task_id': awaiting.get('task_id'),
            'input_from': awaiting.get('input_from'),
            'consumers': awaiting.get('consumers'),
        }
    return {'state_version': state.get('version'), 'action': action,
            'ready': ready if action == 'submit' else [], 'active': active,
            'pending_action': copy.deepcopy(state.get('pending_action')),
            'awaiting_decision': awaiting_summary}


class Store:
    def __init__(self, root=ROOT):
        self.root = Path(root).expanduser().resolve()
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)

    def directory(self, run) -> Path:
        result = self.root / safe_id(run)
        if result.is_symlink() or result.resolve().parent != self.root:
            raise StateError('无效的运行目录')
        return result

    @contextmanager
    def locked(self, run, *, blocking=True):
        directory = self.directory(run)
        if not directory.is_dir():
            raise FileNotFoundError('运行不存在')
        with file_lock(directory / '.lock', blocking=blocking):
            yield directory

    def read(self, run) -> dict:
        return read_json_object(self.directory(run) / 'state.json')

    def plan(self, run) -> dict:
        path = self.directory(run) / 'plan.json'
        if path.exists():
            return read_json_object(path)
        # Legacy v1 checkpoint: infer a read-only layout without upgrading it.
        state = self.read(run)
        return normalize_plan({'name': state.get('pipeline_name', run), 'monitor_bookends': False,
                               'stages': [dict(id=k, kind='eval-group' if v.get('members') else 'proc',
                                               parallel_group=[{'id': m} for m in v.get('members', {})])
                                          for k, v in state.get('stages', {}).items()]})

    def init(self, run, raw) -> dict:
        reject_removed_fields(raw)
        plan = normalize_plan(raw)
        directory = self.directory(run)
        directory.mkdir(exist_ok=True, mode=0o700)
        with self.locked(run):
            if (directory / 'state.json').exists() or (directory / 'state.deleting.json').exists():
                raise Conflict('运行已存在，未覆盖')
            state = {'schema_version': 2, 'run_id': run, 'pipeline_name': plan.get('name', run),
                     'workspace_id': plan.get('workspace_id'), 'region': plan.get('region'),
                     'created_at': now(), 'updated_at': now(), 'version': 1, 'status': 'RUNNING',
                     'orchestrator': {'heartbeat_at': now()}, 'pending_action': None,
                     'awaiting_decision': None, 'inputs': plan.get('inputs', []),
                     'output': plan.get('output', {}), 'stages': {}, 'event_seq': 1}
            for stage in plan['stages']:
                item = {'kind': stage['kind'], 'fail_fast': stage['fail_fast'], 'task_id': None,
                        'status': 'SUCCEEDED' if stage['id'] == 'plan' or stage.get('external') else None,
                        'skipped': False, 'attempts': [], 'external': bool(stage.get('external'))}
                if stage['id'] == 'upload' and stage['kind'] == 'manual' and stage.get('not_applicable'):
                    item.update(status='SKIPPED', skipped=True, not_applicable=True,
                                skip_reason=stage['skip_reason'])
                if stage.get('external'):
                    item.update(stage.get('artifacts', {}))
                if stage.get('parallel_group'):
                    item['members'] = {member['id']: {'kind': member.get('kind', 'eval'),
                                      'fail_fast': stage['fail_fast'], 'task_id': None,
                                      'status': None, 'skipped': False, 'attempts': []}
                                       for member in stage['parallel_group']}
                state['stages'][stage['id']] = item
            atomic_json(directory / 'plan.json', plan)
            self._commit(directory, state, {'seq': 1, 'ts': now(), 'actor': 'agent',
                                           'type': 'initialized', 'detail': '执行计划已确认'})
        return state

    def delete_run(self, run, expected_version) -> dict:
        """Remove one finished local run; never call a platform operation."""
        if type(expected_version) is not int or expected_version < 1:
            raise StateError('删除需要有效的 expected_version，请刷新运行列表')
        directory = self.directory(run)
        tombstone = directory / 'state.deleting.json'
        try:
            with self.locked(run, blocking=False):
                state = self.read(run)
                if state.get('schema_version') != 2:
                    raise StateError('旧版记录为只读模式，不能在网页删除')
                if state.get('version') != expected_version:
                    raise Conflict('状态已变化，请刷新后重新确认删除')
                if state.get('status') not in RUN_TERMINAL:
                    raise Conflict('只能删除已完成、失败或终止的运行；请先终止后续编排')
                if state.get('pending_action'):
                    raise Conflict('有未核实的任务提交事务，请先到智能体核实后再删除')
                # Block further checkpoint writes before closing the Windows lock.
                atomic_replace(directory / 'state.json', tombstone)
        except BlockingIOError:
            raise Conflict('记录正被其他操作使用，请稍后刷新并重试') from None
        removed = self.root / ('.deleted-' + run + '-' + secrets.token_hex(8))
        try:
            atomic_replace(directory, removed)
        except OSError:
            with self.locked(run):
                atomic_replace(tombstone, directory / 'state.json')
            raise StateError('本地目录正在被占用或无删除权限，记录已保留，请关闭相关文件后重试') from None
        result = {'deleted': True, 'run_id': run, 'cleanup_pending': False}
        try:
            shutil.rmtree(removed)
        except OSError:
            result.update(cleanup_pending=True, warning='记录已从列表移除，但部分本地文件未能清理。请检查目录权限或文件占用后清理 runs-root 下的 ' + removed.name)
        return result

    def _commit(self, directory, state, event):
        # Persist the event in the checkpoint transaction first. Recover the append if
        # the process dies between atomic checkpoint replacement and events.jsonl.
        state['_last_event'] = event
        atomic_json(directory / 'state.json', state)
        self._append_event(directory, event)

    def _append_event(self, directory, event):
        path = directory / 'events.jsonl'
        events = self._events_at(directory)
        if events and events[-1]['seq'] >= event['seq']:
            return
        if path.exists():
            raw = path.read_bytes()
            if raw and not raw.endswith(b'\n'):
                # Remove a torn final append before replaying the checkpoint event.
                with open(path, 'r+b') as file:
                    file.truncate(raw.rfind(b'\n') + 1)
        with open(path, 'a', encoding='utf-8') as file:
            os.chmod(path, 0o600)
            file.write(json.dumps(event, ensure_ascii=False) + '\n')
            file.flush()
            os.fsync(file.fileno())

    def _events_at(self, directory) -> list:
        path = directory / 'events.jsonl'
        result = []
        if path.exists():
            for line in path.read_text(encoding='utf-8-sig').splitlines():
                try:
                    result.append(json.loads(line))
                except ValueError:
                    continue
        return result

    def events(self, run) -> list:
        with self.locked(run) as directory:
            state = self.read(run)
            if state.get('_last_event'):
                self._append_event(directory, state['_last_event'])
            return self._events_at(directory)

    def mutate(self, run, callback, *, actor='agent', event_type='updated', stage=None,
               member=None, expected_task=..., expected_version=None, detail='') -> dict:
        with self.locked(run) as directory:
            state = self.read(run)
            if state.get('schema_version') != 2:
                raise StateError('旧版 checkpoint 为只读模式')
            if state.get('_last_event'):
                self._append_event(directory, state['_last_event'])
            if expected_version is not None and state['version'] != expected_version:
                raise Conflict('状态版本已变化，请刷新后重试')
            if stage and expected_task is not ... and stage_ref(state, stage, member).get('task_id') != expected_task:
                raise Conflict('该步骤已被其他操作处理')
            callback(state)
            state['version'] += 1
            state['event_seq'] = state.get('event_seq', 0) + 1
            state['updated_at'] = now()
            event = {'seq': state['event_seq'], 'ts': now(), 'actor': actor, 'type': event_type,
                     'stage': stage, 'member': member, 'detail': detail}
            if stage:
                event['task_id'] = stage_ref(state, stage, member).get('task_id')
            self._commit(directory, state, event)
            return state

    def record_inputs(self, run, supplied, expected_version) -> dict:
        """Persist CLI-verified input metadata locally; never upload or register in the cloud."""
        if type(expected_version) is not int or expected_version < 1:
            raise StateError('输入登记需要有效的 expected_version，请重新读取状态')
        def update(state):
            if state['status'] in RUN_TERMINAL or state.get('pending_action'):
                raise Conflict('管线已结束或有操作正在执行，不能更新输入登记')
            sources = state.get('inputs', [])
            by_id = {source.get('id', 'default'): source for source in sources}
            allowed = {'asset_id', 'version_id', 'asset_name', 'obs_path'}
            if not isinstance(supplied, dict) or not supplied or set(supplied) - set(by_id):
                raise StateError('输入登记必须按已存在的输入 ID 提供非空对象；单输入未命名时使用 default')
            for source_id, values in supplied.items():
                if not isinstance(values, dict) or set(values) != allowed:
                    raise StateError('输入登记每项必须且只能包含 asset_id、version_id、asset_name、obs_path：' + source_id)
                if any(not isinstance(value, str) or not value.strip() for value in values.values()):
                    raise StateError('输入登记字段必须为非空字符串：' + source_id)
                if not re.fullmatch(r'obs://[^/\s]+/[^\s]*', values['obs_path']):
                    raise StateError('输入登记 obs_path 必须为已核实的 OBS 路径：' + source_id)
                source = by_id[source_id]
                existing = next(item for item in registered_inputs(state) if item['id'] == source_id)
                for key in ('asset_id', 'version_id'):
                    if existing.get(key) and existing[key] != values[key]:
                        raise Conflict('不能替换已登记的输入资产或确切版本：' + source_id)
                fixed_path = source.get('source_type') == 'asset' or existing.get('asset_id')
                if fixed_path and existing.get('obs_path') and existing['obs_path'] != values['obs_path']:
                    raise Conflict('不能替换已登记的输入版本路径：' + source_id)
                source.update(values)
            upload = state['stages'].get('upload')
            if upload and registration_complete(registered_inputs(state)):
                if not upload.get('not_applicable') or not reuses_registered_inputs(sources):
                    upload.update(status='SUCCEEDED', skipped=False, not_applicable=False, finish_at=now())
                    upload.pop('skip_reason', None)
                if len(sources) == 1:
                    source = sources[0]
                    upload.update(target_path=source['obs_path'], target_asset_id=source['asset_id'],
                                  target_version_id=source['version_id'], output_name=source['asset_name'])
        return self.mutate(run, update, expected_version=expected_version, event_type='inputs_recorded',
                           detail='已记录通过 CLI 核实的初始数据资产与版本')

    def set_task(self, run, stage, member, expected, task_id, config, name=None, actor='agent') -> dict:
        safe_id(task_id)
        def update(state):
            if state['status'] in RUN_TERMINAL or state.get('pending_action'):
                raise Conflict('管线已结束或有操作正在执行')
            item = stage_ref(state, stage, member)
            decision = state.get('awaiting_decision') or {}
            if same_step(decision, stage, member) and decision.get('kind') == 'skip':
                raise Conflict('该步骤正等待跳过兼容性校验，请先处理跳过请求')
            if is_bypassed(item):
                raise Conflict('该步骤已确认保留原输入跳过，不能再提交任务')
            if item.get('status') == 'SUCCEEDED':
                raise Conflict('首版不支持重跑已成功步骤')
            if item.get('task_id'):
                if item.get('status') not in TERMINAL:
                    raise Conflict('不能替换正在运行的任务')
                item['attempts'].append(copy.deepcopy({k: v for k, v in item.items() if k != 'attempts'}))
            atomic_json(self.directory(run) / 'tasks' / (task_id + '.json'),
                        {'task_config': config, 'task_name': name, 'by': actor, 'at': now()})
            item.update(task_id=task_id, task_name=name, status='PENDING', skipped=False, started_at=now())
            for key in ('output_name', 'target_path', 'target_asset_id', 'target_version_id', 'target_report_path', 'error', 'finish_at'):
                item.pop(key, None)
            if same_step(state.get('awaiting_decision'), stage, member):
                state['awaiting_decision'] = None
                state['status'] = 'RUNNING'
        return self.mutate(run, update, stage=stage, member=member, expected_task=expected,
                           actor=actor, event_type='task_submitted')

    def resolve_skip(self, run, sid, version, decision, note='', supplied=None) -> dict:
        if decision not in {'skip', 'keep'}:
            raise StateError('decision 仅支持 skip 或 keep')
        plan = self.plan(run)
        def resolve(state):
            request = state.get('awaiting_decision', {}) or {}
            if request.get('kind') != 'skip' or not same_step(request, sid, None):
                raise Conflict('当前没有该步骤的跳过校验请求')
            if state.get('pending_action') or state['status'] in RUN_TERMINAL:
                raise Conflict('当前运行不可处理跳过请求')
            item = stage_ref(state, sid)
            if item.get('task_id') or item.get('status') or item.get('skipped'):
                raise Conflict('步骤已经提交或处理，请刷新状态')
            if decision == 'skip':
                if not isinstance(note, str) or not note.strip():
                    raise StateError('跳过前须记录已通过 CLI 核实原输入与所有下游算子兼容的说明')
                spec = bypass_spec(plan, state, sid)
                dataset = dataset_inputs(plan, state, sid, supplied)['datasets'][0]
                item.update(status='SKIPPED', skipped=True, bypassed=True, bypass_from=spec['input_from'][0],
                            target_path=dataset['obs_path'], target_asset_id=dataset['asset_id'],
                            target_version_id=dataset['version_id'], output_name=dataset['asset_name'],
                            skip_reason=note.strip(), finish_at=now())
            state['awaiting_decision'] = None
            state['status'] = 'RUNNING'
        return self.mutate(run, resolve, stage=sid, expected_task=None, expected_version=version,
                           event_type='bypass' if decision == 'skip' else 'skip_cancelled', detail=note[:2000])


def main() -> int:
    configure_console()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runs-root', default=str(ROOT))
    parser.add_argument('--run', required=True)
    sub = parser.add_subparsers(dest='command', required=True)
    init = sub.add_parser('init'); init.add_argument('--plan', required=True)
    sub.add_parser('show'); sub.add_parser('heartbeat')
    sub.add_parser('ready-tasks', help='只读查询统一任务图的就绪集合；先提交所有就绪任务再等待')
    resolve = sub.add_parser('resolve-inputs', help='只读生成按 input_from 排序的 CLI 输入片段；不调用云端')
    resolve.add_argument('--stage', required=True)
    resolve.add_argument('--inputs-file', help='初始输入 ID 到已核实 asset_id/version_id/asset_name/obs_path 的 JSON 对象')
    record = sub.add_parser('record-inputs', help='把 CLI 已核实的初始输入登记写入本地状态；不调用云端')
    record.add_argument('--inputs-file', required=True, help='输入 ID 到 asset_id/version_id/asset_name/obs_path 的 JSON 文件路径')
    record.add_argument('--expect-version', required=True, type=int)
    bypass = sub.add_parser('resolve-skip', help='智能体核实兼容性后应用或取消网页跳过请求')
    bypass.add_argument('--stage', required=True)
    bypass.add_argument('--expect-version', type=int, required=True)
    bypass.add_argument('--decision', choices=['skip', 'keep'], required=True)
    bypass.add_argument('--compatibility-note', default='')
    bypass.add_argument('--inputs-file')
    legacy = sub.add_parser('import-legacy')
    legacy.add_argument('--checkpoint', required=True, help='导入旧 checkpoint，仅用于只读查看')
    recover = sub.add_parser('resolve-action')
    recover.add_argument('--action-id', required=True)
    resolution = recover.add_mutually_exclusive_group(required=True)
    resolution.add_argument('--task-id', help='已通过 show-task 核实的新任务 ID')
    resolution.add_argument('--not-created', action='store_true', help='已确认平台没有创建任务')
    for command in ('set-task', 'reserve-task', 'set-result', 'await-decision'):
        child = sub.add_parser(command)
        child.add_argument('--stage', required=True); child.add_argument('--member')
        child.add_argument('--expect-task', required=True, help='当前 task_id；无任务时用 none')
        if command in {'set-task', 'reserve-task'}:
            if command == 'set-task':
                child.add_argument('--task-id', required=True)
            child.add_argument('--config', required=True)
            child.add_argument('--name', required=command == 'reserve-task')
        if command == 'set-result':
            child.add_argument('--result', required=True, help='JSON 对象，允许字段：' + ', '.join(RESULT_FIELDS))
    sub.add_parser('finish')
    args = parser.parse_args()
    store = Store(args.runs_root)
    try:
        if args.command == 'init':
            result = store.init(args.run, json.loads(Path(args.plan).read_text(encoding='utf-8-sig')))
        elif args.command == 'show':
            result = store.read(args.run)
        elif args.command == 'ready-tasks':
            with store.locked(args.run):
                result = execution_frontier(store.plan(args.run), store.read(args.run))
        elif args.command == 'record-inputs':
            result = store.record_inputs(args.run, read_json_object(args.inputs_file), args.expect_version)
        elif args.command == 'resolve-inputs':
            supplied = read_json_object(args.inputs_file) if args.inputs_file else None
            with store.locked(args.run):
                result = dataset_inputs(store.plan(args.run), store.read(args.run), args.stage, supplied)
        elif args.command == 'resolve-skip':
            supplied = read_json_object(args.inputs_file) if args.inputs_file else None
            result = store.resolve_skip(args.run, args.stage, args.expect_version, args.decision,
                                        args.compatibility_note, supplied)
        elif args.command == 'import-legacy':
            directory = store.directory(args.run)
            directory.mkdir(exist_ok=True, mode=0o700)
            with store.locked(args.run):
                if (directory / 'state.json').exists():
                    raise Conflict('运行已存在，未覆盖')
                result = json.loads(Path(args.checkpoint).read_text(encoding='utf-8-sig'))
                result.update(schema_version=1, run_id=args.run)
                atomic_json(directory / 'state.json', result)
        elif args.command == 'resolve-action':
            def recover_action(state):
                pending = state.get('pending_action')
                if not pending or pending['id'] != args.action_id:
                    raise Conflict('待核对的操作 ID 已变化')
                if args.task_id:
                    safe_id(args.task_id)
                    record = json.loads((store.directory(args.run) / 'pending-config.json').read_text(encoding='utf-8-sig'))
                    item = stage_ref(state, pending['stage'], pending.get('member'))
                    if item.get('task_id'):
                        item['attempts'].append(copy.deepcopy({k: v for k, v in item.items() if k != 'attempts'}))
                    atomic_json(store.directory(args.run) / 'tasks' / (args.task_id + '.json'),
                                {**record, 'task_name': record['name'], 'by': 'agent', 'at': now()})
                    item.update(task_id=args.task_id, task_name=record['name'], status='PENDING', skipped=False, started_at=now())
                    for key in ('output_name', 'target_path', 'target_asset_id', 'target_version_id', 'target_report_path', 'error', 'finish_at'):
                        item.pop(key, None)
                    if same_step(state.get('awaiting_decision'), pending['stage'], pending.get('member')):
                        state['awaiting_decision'] = None
                    if state['status'] not in RUN_TERMINAL:
                        state['status'] = 'RUNNING'
                state['pending_action'] = None
            result = store.mutate(args.run, recover_action, event_type='action_reconciled',
                                  detail='已核实新任务 ' + args.task_id if args.task_id else '已确认未创建任务')
        elif args.command == 'heartbeat':
            result = store.mutate(args.run, lambda s: s['orchestrator'].update(heartbeat_at=now()), event_type='heartbeat')
        elif args.command == 'finish':
            def finish(state):
                if state.get('pending_action') or state['status'] in {'TERMINATED', 'FAILED'}:
                    raise Conflict('不能完成已终止或正在操作的管线')
                steps = [v for _, _, v in iter_steps(state)]
                if any(not v.get('skipped') and v.get('status') not in TERMINAL for v in steps):
                    raise StateError('仍有步骤未完成')
                if any(v.get('fail_fast', True) and v.get('status') != 'SUCCEEDED'
                       and not (v.get('not_applicable') and v.get('skipped')) and not is_bypassed(v) for v in steps):
                    raise StateError('阻断步骤尚未成功')
                if not all(state.get('output', {}).get(k) for k in ('target_path', 'target_asset_id', 'target_version_id')):
                    raise StateError('请先通过 output 步骤记录已核实的管线产物；仅评测时记录原输入数据集')
                state['status'] = 'SUCCEEDED_WITH_WARNINGS' if any(
                    not v.get('not_applicable') and (v.get('skipped') or v.get('status') != 'SUCCEEDED')
                    for v in steps) else 'SUCCEEDED'
                state['finished_at'] = now(); state['awaiting_decision'] = None
            result = store.mutate(args.run, finish, event_type='finished')
        else:
            expected = None if args.expect_task == 'none' else args.expect_task
            if args.command == 'set-task':
                result = store.set_task(args.run, args.stage, args.member, expected, args.task_id,
                                        json.loads(Path(args.config).read_text(encoding='utf-8-sig')), args.name)
            elif args.command == 'reserve-task':
                config = json.loads(Path(args.config).read_text(encoding='utf-8-sig'))
                def reserve(state):
                    task = stage_ref(state, args.stage, args.member)
                    decision = state.get('awaiting_decision') or {}
                    if same_step(decision, args.stage, args.member) and decision.get('kind') == 'skip':
                        raise Conflict('该步骤正等待跳过兼容性校验，请先处理跳过请求')
                    if is_bypassed(task):
                        raise Conflict('该步骤已确认保留原输入跳过，不能再预留提交事务')
                    if state['status'] in {'TERMINATED', 'FAILED'}:
                        raise Conflict('管线状态为 ' + state['status'] + '，不能预留新的提交事务')
                    pending = state.get('pending_action')
                    if pending:
                        raise Conflict('同一管线已有未完成的提交事务：步骤 ' + str(pending.get('stage'))
                                       + '，成员 ' + str(pending.get('member') or '无')
                                       + '，操作 ID ' + str(pending.get('id'))
                                       + '。请等待该事务完成；若提交中断，先核实后 resolve，再 reserve 下一成员。云端任务仍可并行运行。')
                    if task.get('task_id') and task.get('status') not in {'FAILED', 'DELETED'}:
                        raise Conflict('只能为未提交、失败或删除的步骤创建任务')
                    if state['status'] in RUN_TERMINAL and (task.get('fail_fast', True) or not (task.get('status') in {'FAILED', 'DELETED'} or task.get('skipped'))):
                        raise Conflict('完成后的运行只允许补跑失败或跳过的建议性步骤')
                    validate_task_datasets(config, task['kind'])
                    state['pending_action'] = {'id': secrets.token_hex(12), 'type': 'submit',
                                               'stage': args.stage, 'member': args.member, 'by': 'agent',
                                               'at': now(), 'name': args.name}
                    atomic_json(store.directory(args.run) / 'pending-config.json', {'name': args.name, 'task_config': config})
                result = store.mutate(args.run, reserve, stage=args.stage, member=args.member,
                                      expected_task=expected, event_type='action_started')
            else:
                fields = read_json_object(args.result) if args.command == 'set-result' else {}
                unknown = sorted(set(fields) - set(RESULT_FIELDS))
                if unknown:
                    raise StateError('set-result 不支持字段：' + ', '.join(unknown)
                                     + '；允许字段：' + ', '.join(RESULT_FIELDS))
                def update(state):
                    if state.get('pending_action') or state['status'] in {'TERMINATED', 'FAILED'}:
                        raise Conflict('管线已终止或有操作正在执行')
                    item = stage_ref(state, args.stage, args.member)
                    if is_bypassed(item):
                        raise Conflict('该处理步骤已校验后跳过，请使用其记录的原输入产物，不能覆盖跳过结果')
                    decision = state.get('awaiting_decision') or {}
                    if decision.get('kind') == 'skip':
                        if args.command == 'await-decision' or same_step(decision, args.stage, args.member):
                            raise Conflict('请先通过 resolve-skip 处理已有跳过请求，不能覆盖该决策')
                    if args.command == 'set-result':
                        if args.stage == 'upload' and fields.get('status') == 'SKIPPED':
                            if not item.get('not_applicable') or not reuses_registered_inputs(state.get('inputs', [])):
                                raise StateError('只有本次开始前复用的已有资产才能跳过上传注册；本地或 OBS 输入完成准备后请用 record-inputs 记录为已登记')
                        item.update(fields)
                        if args.stage == 'upload' and item.get('status') == 'SUCCEEDED' and state.get('inputs'):
                            if not registration_complete(registered_inputs(state)):
                                raise StateError('上传注册成功前须记录每份输入的资产 ID、确切版本和 OBS 路径；请使用 record-inputs，不能只写 status')
                        if args.stage == 'output':
                            state['output'].update(fields)
                        if same_step(state.get('awaiting_decision'), args.stage, args.member) and fields.get('status') == 'SUCCEEDED':
                            state['awaiting_decision'] = None; state['status'] = 'RUNNING'
                    else:
                        if item.get('status') not in {'FAILED', 'DELETED'}:
                            raise StateError('只有失败或删除的步骤需要等待处理')
                        state['awaiting_decision'] = {'stage': args.stage, 'member': args.member, 'task_id': expected}
                        state['status'] = 'AWAITING_DECISION'
                result = store.mutate(args.run, update, stage=args.stage, member=args.member,
                                      expected_task=expected, event_type=args.command.replace('-', '_'))
        print(json.dumps(redact(result), ensure_ascii=False, indent=2))
    except Conflict as error:
        print(str(error), file=sys.stderr); return 3
    except (StateError, OSError, ValueError, KeyError) as error:
        print(str(error), file=sys.stderr); return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
