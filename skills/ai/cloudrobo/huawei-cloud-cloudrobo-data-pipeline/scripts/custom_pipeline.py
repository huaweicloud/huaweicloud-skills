#!/usr/bin/env python3
"""Validate/export conversational pipeline drafts locally. No CLI/SDK/network calls."""
import argparse
import copy
import json
import math
from pathlib import Path
import re
import sys

from platform_utils import configure_console, step_name, unique_name
from pipeline_state import StateError, data_references, validate_bindings

IDENTIFIER = re.compile(r'[A-Za-z0-9_][A-Za-z0-9_.-]{0,47}\Z')
NAME = re.compile(r'[\u4e00-\u9fa5A-Za-z0-9_./-]+\Z')
EVAL_NAMES = {'数据集质量评测-LeRobot', '数据集多样性评测-LeRobot'}
CONVERSION_NAMES = {'数据转换--H5转LeRobotV3', '数据转换--ros转LeRobotV3', '数据转换--UMI转LeRobotV3'}
ROLES = {'conversion', 'cleaning', 'processing', 'evaluation'}
ROBOT_CONFIG_REMOVED = ('robot_config 已废弃：请在该评测步骤/成员的 params.inputs 中挂载算子声明的配置输入'
                        '（如 ROBOT_CONFIG_PATH），url_path 填 OBS 目录')


def incomplete(value) -> bool:
    return value is None or value == '' or isinstance(value, str) and bool(re.search(r'<[^>]+>|\$\{[^}]+\}|\bTODO\b', value))


def validate(raw) -> tuple[dict, list, list]:
    """Return normalized draft + local findings. A valid structure is not cloud approval."""
    draft = copy.deepcopy(raw)
    issues = []; warnings = ['算子、版本、环境变量声明、资源配额尚需内网 CLI 实时复核；本地检查不授予执行许可。']
    def issue(path, message, kind='error'):
        issues.append({'kind': kind, 'path': path, 'message': message})
    def required(value, path):
        if incomplete(value):
            issue(path, '待用户补充或确认', 'missing'); return False
        return True
    def unknown(obj, allowed, path):
        for key in set(obj) - set(allowed):
            issue(path + '.' + key, ROBOT_CONFIG_REMOVED if key == 'robot_config' else '不支持此字段，请按现有 pipeline schema 配置')
    def text(value, path, mandatory=True):
        if incomplete(value):
            if mandatory:
                required(value, path)
            return False
        if not isinstance(value, str):
            issue(path, '必须为字符串'); return False
        return True
    def obs(value, path):
        if text(value, path) and not re.fullmatch(r'obs://[^/\s]+/[^\s]*', value):
            issue(path, '必须为 obs://<bucket>/<path> 路径')
    if not isinstance(draft, dict):
        return {}, [{'kind': 'error', 'path': '$', 'message': '草案必须为 JSON 对象'}], warnings
    unknown(draft, {'pipeline', 'authoring'}, '$')
    pipeline = draft.get('pipeline')
    if not isinstance(pipeline, dict):
        issue('pipeline', '必须包含 pipeline 对象'); return draft, issues, warnings
    unknown(pipeline, {'name', 'workspace_id', 'inputs', 'output', 'stages'}, 'pipeline')
    name = pipeline.get('name')
    if text(name, 'pipeline.name') and (not NAME.fullmatch(name) or not 1 <= len(name) <= 48):
        issue('pipeline.name', '须为 1–48 个中文、字母、数字或 _-./ 字符，并为任务名预留长度')
    if 'workspace_id' in pipeline:
        text(pipeline['workspace_id'], 'pipeline.workspace_id')
    inputs = pipeline.get('inputs')
    if not isinstance(inputs, list) or not inputs:
        issue('pipeline.inputs', '请提供非空的数据源对象数组', 'missing' if not inputs else 'error')
        inputs = []
    sources = {}
    for index, source in enumerate(inputs):
        path = 'pipeline.inputs[' + str(index) + ']'
        if not isinstance(source, dict):
            issue(path, '数据源必须为对象'); continue
        unknown(source, {'id', 'source_type', 'obs_path', 'local_path', 'asset_id', 'version_id', 'asset_name', 'data_source_type', 'robot_type'}, path)
        source_id = source.get('id', 'default')
        if len(inputs) > 1 and 'id' not in source:
            issue(path + '.id', '多个初始数据集须提供唯一 id')
        if not isinstance(source_id, str) or not IDENTIFIER.fullmatch(source_id):
            issue(path + '.id', '须为合法 ASCII 标识符'); continue
        if source_id in sources:
            issue(path + '.id', '初始输入 ID 重复'); continue
        sources[source_id] = source
        source_type = source.get('source_type')
        if required(source_type, path + '.source_type'):
            if source_type not in {'obs', 'local', 'asset'}:
                issue(path + '.source_type', '须为 local、obs 或 asset')
            if source_type == 'obs':
                obs(source.get('obs_path'), path + '.obs_path')
            elif source_type == 'local':
                text(source.get('local_path'), path + '.local_path')
            elif source_type == 'asset':
                text(source.get('asset_id'), path + '.asset_id')
                text(source.get('version_id'), path + '.version_id')
                if 'obs_path' in source:
                    obs(source['obs_path'], path + '.obs_path')
        for field in ('data_source_type', 'robot_type', 'asset_name'):
            if field in source:
                text(source[field], path + '.' + field)
    output = pipeline.get('output', {})
    if not isinstance(output, dict):
        issue('pipeline.output', '必须为对象'); output = {}
    unknown(output, {'asset_name', 'from_stage'}, 'pipeline.output')
    if 'asset_name' in output and text(output.get('asset_name'), 'pipeline.output.asset_name'):
        value = output['asset_name']
        if not 2 <= len(value) <= 64 or value.strip() != value or not re.fullmatch(r'[\u4e00-\u9fa5A-Za-z0-9_./ -]+', value):
            issue('pipeline.output.asset_name', '输出名须为 2–64 个合法字符，首尾不能有空格')
    authoring = draft.setdefault('authoring', {})
    if not isinstance(authoring, dict):
        issue('authoring', '必须为对象'); authoring = {}
    unknown(authoring, {'input_stage', 'upstream', 'roles', 'resources', 'output_names'}, 'authoring')
    input_stage = authoring.get('input_stage')
    input_stages = {}
    if isinstance(input_stage, dict):
        unknown(input_stage, sources, 'authoring.input_stage')
    elif not isinstance(input_stage, str) and not incomplete(input_stage):
        issue('authoring.input_stage', '须为数据阶段字符串，或 input_id → 数据阶段的对象')
    upstreams = authoring.get('upstream', {})
    if not isinstance(upstreams, dict):
        issue('authoring.upstream', '必须为对象'); upstreams = {}
    if len(sources) > 1:
        unknown(upstreams, sources, 'authoring.upstream')
    for index, (source_id, source) in enumerate(sources.items()):
        source_path = 'pipeline.inputs[' + str(index) + ']'
        phase_path = 'authoring.input_stage' + ('.' + source_id if isinstance(input_stage, dict) else '')
        phase = input_stage.get(source_id) if isinstance(input_stage, dict) else input_stage
        if required(phase, phase_path) and (not isinstance(phase, str) or phase not in {'raw', 'converted', 'cleaned', 'processed'}):
            issue(phase_path, '须为 raw、converted、cleaned 或 processed，不能由目录名猜测')
        input_stages[source_id] = phase
        if phase in ('converted', 'cleaned', 'processed') and source.get('source_type') == 'asset':
            upstream = upstreams.get(source_id, {}) if len(sources) > 1 else upstreams
            upstream_path = 'authoring.upstream' + ('.' + source_id if len(sources) > 1 else '')
            if not isinstance(upstream, dict):
                issue(upstream_path, '必须为对象'); upstream = {}
            unknown(upstream, {'target_path', 'asset_id', 'version_id', 'asset_name'}, upstream_path)
            obs(upstream.get('target_path'), upstream_path + '.target_path')
            for field in ('asset_id', 'version_id', 'asset_name'):
                text(upstream.get(field), upstream_path + '.' + field)
            for field in ('asset_id', 'version_id'):
                if not incomplete(upstream.get(field)) and source.get(field) != upstream[field]:
                    issue(upstream_path + '.' + field, '必须与 ' + source_path + ' 中的资产/版本一致')
        elif incomplete(source.get('data_source_type')):
            issue(source_path + '.data_source_type', '需确认实际数据格式，以核对算子输入；OBS/本地数据在执行时按需注册', 'missing')
    roles = authoring.get('roles', {})
    if not isinstance(roles, dict):
        issue('authoring.roles', '必须为 stage_id → 步骤用途的对象'); roles = {}
    resources = authoring.get('resources', {})
    if not isinstance(resources, dict):
        issue('authoring.resources', '必须为对象'); resources = {}
    if resources:
        unknown(resources, {'resource_pool_type', 'resource_id', 'dedicated_pool_name', 'worker_spec', 'head_spec', 'worker_num'}, 'authoring.resources')
        if resources.get('resource_pool_type') not in {'PUBLIC_POOL', 'DEDICATED_POOL'}:
            issue('authoring.resources.resource_pool_type', '须为 PUBLIC_POOL 或 DEDICATED_POOL')
        if resources.get('resource_pool_type') == 'DEDICATED_POOL':
            for field in ('resource_id', 'dedicated_pool_name'):
                text(resources.get(field), 'authoring.resources.' + field)
        for field in ('worker_spec', 'head_spec'):
            spec = resources.get(field)
            if spec is None:
                if field == 'worker_spec':
                    issue('authoring.resources.' + field, '请确认 worker 规格', 'missing')
                continue
            if not isinstance(spec, dict) or set(spec) != {'cpu', 'memory', 'gpu', 'npu'}:
                issue('authoring.resources.' + field, '须包含 cpu、memory、gpu、npu 四个数值字段'); continue
            if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or v < 0 for v in spec.values()):
                issue('authoring.resources.' + field, '资源规格必须为有限非负数值')
            elif field == 'worker_spec' and (spec['cpu'] <= 0 or spec['memory'] <= 0):
                issue('authoring.resources.' + field, 'worker 的 CPU 和内存必须大于零')
        workers = resources.get('worker_num', 1)
        if isinstance(workers, bool) or not isinstance(workers, int) or workers < 1:
            issue('authoring.resources.worker_num', '必须为正整数')
    else:
        warnings.append('尚未选择资源池和规格；执行计划确认前需补齐，4c8g 仅可作为待确认建议。')
    stages = pipeline.get('stages')
    if not isinstance(stages, list) or not stages:
        if stages is None:
            pipeline['stages'] = []
        issue('pipeline.stages', '请先选择至少一个处理或评测步骤', 'missing'); return draft, issues, warnings
    by_id = {}; stage_roles = {}; previous = None; task_ids = set(); implicit_roots = []
    stage_keys = {'id', 'kind', 'operator', 'operator_id', 'operator_source', 'algo_path', 'job_local_path', 'image', 'algo_entrance', 'params', 'depends_on', 'input_from', 'fail_fast', 'parallel_group'}
    def operator(item, path, kind):
        src = item.get('operator_source', 'preset')
        if src not in {'preset', 'workspace', 'obs'}:
            issue(path + '.operator_source', '须为 preset、workspace 或 obs')
        if src == 'obs':
            if kind == 'evaluation':
                issue(path + '.operator_source', '评测任务须引用预置或空间算法资产；OBS 代码来源当前仅支持处理任务')
            obs(item.get('algo_path'), path + '.algo_path')
            for field in ('job_local_path', 'image', 'algo_entrance'):
                if text(item.get(field), path + '.' + field) and field == 'job_local_path' and not item[field].startswith('/'):
                    issue(path + '.' + field, '容器挂载路径必须为绝对路径')
        elif not any(not incomplete(item.get(k)) for k in ('operator', 'operator_id')):
            issue(path + '.operator', '请选择精确算子名或精确 operator_id；不自动替换算子', 'missing')
        for key in ('operator', 'operator_id'):
            if key in item:
                text(item[key], path + '.' + key)
        params = item.get('params', {})
        if not isinstance(params, dict):
            issue(path + '.params', '必须为对象'); return
        unknown(params, {'envs', 'inputs'}, path + '.params')
        envs = params.get('envs', {})
        if not isinstance(envs, dict):
            issue(path + '.params.envs', '必须为环境变量名到值的映射')
        else:
            for key, value in envs.items():
                if re.search(r'(^|_)(AK|SK|SECRET|PASSWORD|ACCESS_TOKEN|API_KEY)($|_)|SECRET_ACCESS_KEY|ACCESS_KEY_ID', key, re.I):
                    issue(path + '.params.envs.' + key, '凭据不能写入管线草案，请通过 CLI 配置环境认证')
                elif not isinstance(value, (str, int, float, bool)) or isinstance(value, float) and not math.isfinite(value):
                    issue(path + '.params.envs.' + key, '环境变量值必须为标量')
                elif incomplete(value):
                    issue(path + '.params.envs.' + key, '环境变量值待补充', 'missing')
        mounts = params.get('inputs', [])
        if not isinstance(mounts, list):
            issue(path + '.params.inputs', '必须为 name/url_path 对象数组')
        else:
            names = set()
            for index, mount in enumerate(mounts):
                location = path + '.params.inputs[' + str(index) + ']'
                if not isinstance(mount, dict):
                    issue(location, '必须为对象'); continue
                unknown(mount, {'name', 'url_path'}, location)
                if text(mount.get('name'), location + '.name'):
                    if mount['name'] in names:
                        issue(location + '.name', '输入挂载名重复')
                    names.add(mount['name'])
                obs(mount.get('url_path'), location + '.url_path')
        if params:
            warnings.append(path + '：env/input 名称及枚举必须与当次算子声明核对。')
    for index, stage in enumerate(stages):
        path = 'pipeline.stages[' + str(index) + ']'
        if not isinstance(stage, dict):
            issue(path, '步骤必须为对象'); continue
        unknown(stage, stage_keys, path)
        sid = stage.get('id')
        if not text(sid, path + '.id'):
            continue
        if not IDENTIFIER.fullmatch(sid) or sid in {'plan', 'upload', 'output'}:
            issue(path + '.id', '须为 1–48 个 ASCII 标识字符，不能占用 plan/upload/output 监控节点'); continue
        if sid in by_id:
            issue(path + '.id', '步骤 ID 重复'); continue
        by_id[sid] = stage
        explicit_bindings = 'input_from' in stage
        if 'depends_on' not in stage and previous is None and not explicit_bindings:
            implicit_roots.append(stage)
        if explicit_bindings and 'depends_on' not in stage:
            refs = stage['input_from']
            stage['depends_on'] = [ref for ref in refs if isinstance(ref, str) and not ref.startswith('input:')] if isinstance(refs, list) else []
        stage.setdefault('depends_on', [previous] if previous else [])
        previous = sid
        if not isinstance(stage['depends_on'], list) or any(not isinstance(d, str) for d in stage['depends_on']):
            issue(path + '.depends_on', '须为步骤 ID 数组'); stage['depends_on'] = []
        elif len(stage['depends_on']) != len(set(stage['depends_on'])):
            issue(path + '.depends_on', '等待依赖不能重复')
        group = stage.get('parallel_group')
        preset_name = stage.get('operator') if stage.get('operator_source', 'preset') == 'preset' else None
        inferred_role = 'processing'
        if preset_name in CONVERSION_NAMES:
            inferred_role = 'conversion'
        elif preset_name == '数据清洗':
            inferred_role = 'cleaning'
        if group is not None or stage.get('kind') == 'eval' or preset_name in EVAL_NAMES:
            inferred_role = 'evaluation'
        role = roles.get(sid, inferred_role)
        if role not in ROLES:
            issue('authoring.roles.' + sid, '用途须为 conversion/cleaning/processing/evaluation'); role = 'processing'
        stage_roles[sid] = role
        if 'fail_fast' in stage and not isinstance(stage['fail_fast'], bool):
            issue(path + '.fail_fast', '必须为布尔值')
        stage.setdefault('fail_fast', role != 'evaluation')
        if role == 'evaluation':
            if stage['fail_fast'] is not False:
                issue(path + '.fail_fast', '评测必须为建议性步骤（false）')
        elif stage['fail_fast'] is not True:
            issue(path + '.fail_fast', '产生下游数据的处理步骤必须为阻断步骤（true）')
        if group is not None:
            if role != 'evaluation':
                issue(path + '.parallel_group', '并行组当前只用于建议性评测，用途须为 evaluation')
            if any(k in stage for k in ('operator', 'operator_id', 'params', 'operator_source', 'algo_path', 'image', 'algo_entrance', 'job_local_path')):
                issue(path, '并行组的算子和 params 应分别写在成员中')
            if stage.get('kind', 'eval-group') != 'eval-group':
                issue(path + '.kind', 'parallel_group 的 kind 只能为 eval-group（也可省略）')
            if not isinstance(group, list) or not group:
                issue(path + '.parallel_group', '评测并行组不能为空'); continue
            stage['kind'] = 'eval-group'
            leaves = group
        else:
            stage.setdefault('kind', 'eval' if role == 'evaluation' else 'proc')
            if stage['kind'] != ('eval' if role == 'evaluation' else 'proc'):
                issue(path + '.kind', '步骤 kind 必须与用途匹配（proc/eval）')
            leaves = [stage]
        for member_index, member in enumerate(leaves):
            member_path = path + '.parallel_group[' + str(member_index) + ']'
            if not isinstance(member, dict):
                issue(path + '.parallel_group', '成员必须为对象'); continue
            if group is not None:
                unknown(member, {'id', 'operator', 'operator_id', 'operator_source', 'params', 'kind', 'algo_path', 'job_local_path', 'image', 'algo_entrance'}, member_path)
            mid = member.get('id')
            if not isinstance(mid, str) or not IDENTIFIER.fullmatch(mid):
                issue(path + '.parallel_group.id' if group is not None else path + '.id', '成员 ID 必须是合法 ASCII 标识符'); continue
            if mid in task_ids:
                issue(path + '.id', '任务步骤/并行成员 ID 重复，会造成任务名冲突')
            task_ids.add(mid)
            if isinstance(name, str) and len(name) + len(mid) + 12 > 64:
                issue(path + '.id', '管线名 + 成员 ID + 时间戳组成的任务名超过 64 字符')
            if group is not None and member.get('kind', 'eval') != 'eval':
                issue(path + '.parallel_group.kind', '并行组当前只支持评测成员')
            operator(member, path + ('.' + mid if group is not None else ''), role)
    for sid in set(roles) - set(by_id):
        issue('authoring.roles.' + sid, '用途引用了不存在的步骤')
    ancestors = {}; visiting = set()
    def visit(sid):
        if sid in ancestors:
            return ancestors[sid]
        if sid in visiting:
            issue('pipeline.stages.' + sid, 'depends_on 存在循环依赖'); return set()
        visiting.add(sid); result = set()
        for dep in by_id[sid]['depends_on']:
            if dep not in by_id:
                issue('pipeline.stages.' + sid + '.depends_on', '依赖不存在的步骤：' + dep); continue
            result.add(dep); result.update(visit(dep))
        visiting.remove(sid); ancestors[sid] = result; return result
    for sid in by_id:
        visit(sid)
    bindings = {}
    for sid, stage in by_id.items():
        try:
            refs = data_references(stage, list(sources.values()))
            stage['input_from'] = refs
            validate_bindings(stage, by_id, list(sources.values()))
            bindings[sid] = refs
        except StateError as error:
            issue('pipeline.stages.' + sid + '.input_from', str(error))
    # Trace each actual data route; an unrelated conversion control gate cannot
    # make raw data on another branch compatible with a LeRobot consumer.
    def unconverted_sources(ref, trail):
        if ref.startswith('input:'):
            source_id = ref[6:]
            source = sources.get(source_id, {})
            if input_stages.get(source_id) == 'raw' and source.get('data_source_type') in ('h5', 'ros2', 'umi'):
                return {source_id}
            return set()
        if ref in trail or stage_roles.get(ref) == 'conversion':
            return set()
        return set().union(*(unconverted_sources(parent, trail | {ref}) for parent in bindings.get(ref, [])))
    for sid, stage in by_id.items():
        leaves = stage.get('parallel_group', [stage])
        lerobot_consumer = any(member.get('operator_source', 'preset') == 'preset'
                               and member.get('operator') in EVAL_NAMES | {'数据清洗'}
                               for member in leaves if isinstance(member, dict))
        raw_sources = set().union(*(unconverted_sources(ref, {sid}) for ref in bindings.get(sid, [])))
        if lerobot_consumer and raw_sources:
            issue('pipeline.stages.' + sid, '该预置 LeRobot 算子不能直接接收原始 H5/ROS2/UMI（' + ', '.join(sorted(raw_sources)) + '），须先转换或选择兼容当前格式的算子')
        if len(bindings.get(sid, [])) > 1:
            warnings.append('步骤 ' + sid + '：多数据集输入须通过 CLI 核实算子支持数量、顺序、格式及单数据集输出；不会自动拼接文件。')
    data_steps = [sid for sid, role in stage_roles.items() if role != 'evaluation']
    output_stage = output.get('from_stage')
    if 'from_stage' in output:
        if text(output_stage, 'pipeline.output.from_stage') and output_stage not in data_steps:
            issue('pipeline.output.from_stage', '须引用产生数据集的处理步骤，不能引用评测报告或不存在的步骤')
    elif data_steps:
        consumed = {ref for other, refs in bindings.items() if stage_roles.get(other) != 'evaluation' for ref in refs}
        data_leaves = [sid for sid in data_steps if sid not in consumed]
        if len(data_leaves) == 1:
            output_stage = data_leaves[0]
            output['from_stage'] = output_stage
        else:
            issue('pipeline.output.from_stage', '存在多个数据输出分支，请明确选择最终数据来源步骤；不会自动合并', 'missing')
    if data_steps:
        pipeline['output'] = output
    if any(role != 'evaluation' for role in stage_roles.values()) and 'asset_name' not in output:
        issue('pipeline.output.asset_name', '请确认数据输出名', 'missing')
    if 'evaluation' not in stage_roles.values():
        warnings.append('未包含评测步骤，摘要需标记“未评测”，不能声称已完成质量/多样性评测。')
    if not any(role == 'cleaning' for role in stage_roles.values()) and any(phase != 'cleaned' for phase in input_stages.values()):
        warnings.append('未包含清洗步骤，不能将普通处理输出直接宣称为已核实的 TrainingReady。')
    output_names = authoring.get('output_names', {})
    if not isinstance(output_names, dict):
        issue('authoring.output_names', '必须为 stage_id → 输出名映射')
    else:
        for sid, value in output_names.items():
            if sid not in by_id or stage_roles.get(sid) == 'evaluation':
                issue('authoring.output_names.' + sid, '输出名应引用处理步骤')
            if text(value, 'authoring.output_names.' + sid) and (not 2 <= len(value) <= 64 or value.strip() != value or not re.fullmatch(r'[\u4e00-\u9fa5A-Za-z0-9_./ -]+', value)):
                issue('authoring.output_names.' + sid, '输出名须为 2–64 个合法字符')
        for sid, role in stage_roles.items():
            if role != 'evaluation' and sid != output_stage and incomplete(output_names.get(sid)):
                warnings.append('步骤 ' + sid + ' 尚未指定数据输出名，执行计划前需确认；可先保存当前草案。')
        if isinstance(output_stage, str) and output_stage in output_names and output_names[output_stage] != output.get('asset_name'):
            issue('authoring.output_names.' + output_stage, '最终输出步骤的名称须与 pipeline.output.asset_name 一致')
    # Preserve an omitted initial dependency: the monitor then connects this first
    # task to its synthetic upload/input node, rather than drawing it before upload.
    for stage in implicit_roots:
        stage.pop('depends_on', None)
    return draft, issues, list(dict.fromkeys(warnings))


def yaml_text(value, indent=0) -> str:
    """Emit the JSON-compatible YAML subset; quote all string values, including envs."""
    space = ' ' * indent
    def scalar(item):
        return json.dumps(item, ensure_ascii=False, allow_nan=False)
    if isinstance(value, dict) and value:
        lines = []
        for key, item in value.items():
            label = key if re.fullmatch(r'[A-Za-z_][A-Za-z0-9_-]*', key) else scalar(key)
            nested = isinstance(item, (dict, list)) and bool(item)
            lines.append(space + label + ':' + ('' if nested else ' ' + scalar(item)))
            if nested:
                lines.append(yaml_text(item, indent + 2))
        return '\n'.join(lines)
    if isinstance(value, list) and value:
        lines = []
        for item in value:
            if isinstance(item, (dict, list)) and item:
                nested = yaml_text(item, indent + 2).splitlines()
                lines.append(space + '- ' + nested[0].lstrip())
                lines.extend(nested[1:])
            else:
                lines.append(space + '- ' + scalar(item))
        return '\n'.join(lines)
    return space + scalar(value)


def preview(draft, issues, warnings) -> str:
    pipeline = draft['pipeline']; authoring = draft.get('authoring', {})
    status = '未完成草案' if issues else '结构检查通过；尚未做平台验证或执行确认'
    def cell(value):
        return str(value).replace('|', '\\|').replace('\n', ' ')
    lines = ['# 自定义管线草案：' + str(pipeline.get('name') or '未命名'), '', '**状态：' + status + '**',
             '', '本文件仅预览。生成文件不会创建资产、发布版本、创建任务或初始化运行目录。',
             '', '## 数据与输出', '', '```json', json.dumps({'inputs': pipeline.get('inputs'), 'output': pipeline.get('output'),
                             'input_stage': authoring.get('input_stage'), 'upstream': authoring.get('upstream')}, ensure_ascii=False, indent=2), '```',
             '', '## 步骤与依赖', '', '| 步骤 | 类型 | 算子/来源 | 等待依赖 | 数据来源（按顺序） | 失败策略 |', '|---|---|---|---|---|---|']
    for stage in pipeline.get('stages', []):
        leaves = stage.get('parallel_group', [stage])
        for member in leaves:
            lines.append('| ' + ' | '.join(cell(v) for v in [member.get('id', '待补充'), member.get('kind', 'eval' if 'parallel_group' in stage else 'proc'),
                          str(member.get('operator', member.get('operator_id', '待选择'))) + ' / ' + member.get('operator_source', 'preset'),
                          ', '.join(stage.get('depends_on', [])) or '输入准备', ', '.join(stage.get('input_from', [])) or '待明确', '阻断' if stage.get('fail_fast', True) else '建议性']) + ' |')
    lines += ['', '## 评测配置挂载', '', '| 评测步骤 | 配置挂载 params.inputs（可选） |', '|---|---|']
    evaluations = 0
    for stage in pipeline.get('stages', []):
        if 'parallel_group' in stage or stage.get('kind') == 'eval':
            for member in stage.get('parallel_group', [stage]):
                evaluations += 1
                params = member.get('params') if isinstance(member.get('params'), dict) else {}
                mounts = params.get('inputs') if isinstance(params.get('inputs'), list) else []
                label = '; '.join(str(m.get('name', '待补充')) + ' → ' + str(m.get('url_path', '待补充'))
                                  for m in mounts if isinstance(m, dict)) or '未挂载（使用算子内置/默认配置）'
                lines.append('| ' + cell(member.get('id', '待选择')) + ' | ' + cell(label) + ' |')
    if not evaluations:
        lines.append('| — | 本管线未配置评测 |')
    lines += ['', '## 已记录的资源与参数（执行前复核）', '', '```json', json.dumps({'resources': authoring.get('resources') or '尚未选择资源池和规格',
              'output_names': authoring.get('output_names', {}), 'params': {s.get('id') or '待选择步骤': s.get('params', {m.get('id') or '待选择成员': m.get('params', {}) for m in s.get('parallel_group', [])}) for s in pipeline.get('stages', [])}}, ensure_ascii=False, indent=2), '```',
              '', '## 待补充项与校验结果', *['- ' + i['path'] + '：' + i['message'] for i in issues],
              *['- ' + warning for warning in warnings], '', '## 执行交接', '',
              '若用户仅要求创建，交付 pipeline.yaml 与本草案即结束。只有用户要求执行后，才进入原 skill 的 Stage 0：',
              '实时查询算子与数据版本，构造完整执行计划；确认后通过 pipeline_state.py 初始化 Web 运行并保留创建事务。', '']
    return '\n'.join(lines)


def export(draft, issues, warnings, directory) -> list:
    directory = Path(directory).expanduser()
    directory.mkdir(parents=True, exist_ok=True)
    header = '# DRAFT — incomplete; resolve the listed fields before execution.\n' if issues else '# Authored locally; verify current operators and confirm the execution plan before running.\n'
    contents = {'pipeline.yaml': header + yaml_text({'pipeline': draft['pipeline']}) + '\n',
                'pipeline.draft.json': json.dumps(draft, ensure_ascii=False, indent=2, allow_nan=False) + '\n',
                'pipeline-preview.md': preview(draft, issues, warnings)}
    created = []
    try:
        for name, content in contents.items():
            path = directory / name
            with path.open('x', encoding='utf-8') as file:
                created.append(path); file.write(content)
    except OSError:
        for path in created:
            path.unlink(missing_ok=True)
        raise
    return [str(path.resolve()) for path in created]


def main() -> int:
    configure_console()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['check', 'export', 'suggest-names'])
    parser.add_argument('--input', help='check/export：Agent 从对话整理的 UTF-8 JSON 草案')
    parser.add_argument('--base', action='append', help='suggest-names：短业务前缀，可重复；生成完整长度不超过 32 的建议名')
    parser.add_argument('--pipeline-name', help='suggest-names：保留的完整管线短名，配合 --stage 使用')
    parser.add_argument('--stage', action='append', help='suggest-names：步骤短 ID，可重复；生成 管线名-步骤名-月日时分秒，总长不超过 64')
    parser.add_argument('--output-dir', help='export 输出到一个新目录；不会覆盖已有文件')
    parser.add_argument('--allow-incomplete', action='store_true', help='允许保存缺项草案；格式/依赖等错误仍会阻止导出')
    args = parser.parse_args()
    try:
        if args.command == 'suggest-names':
            if args.input or args.output_dir or args.allow_incomplete:
                parser.error('suggest-names 不读写草案或提交任务；仅接受命名参数')
            if args.pipeline_name or args.stage:
                if not args.pipeline_name or not args.stage or args.base:
                    parser.error('管线步骤命名需要 --pipeline-name 和一个或多个 --stage，不能混用 --base')
                names = [{'stage': stage, 'name': step_name(args.pipeline_name, stage)} for stage in args.stage]
            elif args.base:
                names = [{'base': base, 'name': unique_name(base)} for base in args.base]
            else:
                parser.error('请提供 --pipeline-name/--stage 或 --base')
            print(json.dumps({'status': 'SUGGESTED', 'names': names}, ensure_ascii=False, indent=2))
            return 0
        if not args.input or args.base or args.pipeline_name or args.stage:
            parser.error('check/export 需要 --input，不接受命名参数')
        raw = json.loads(Path(args.input).read_text(encoding='utf-8-sig'))
        draft, issues, warnings = validate(raw)
        errors = any(i['kind'] == 'error' for i in issues)
        result = {'status': 'INVALID' if errors else 'INCOMPLETE' if issues else 'STRUCTURE_VALID',
                  'issues': issues, 'warnings': warnings}
        if args.command == 'export' and not errors and (not issues or args.allow_incomplete):
            if not args.output_dir:
                parser.error('export 需要 --output-dir')
            result['files'] = export(draft, issues, warnings, args.output_dir)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1 if errors else 2 if issues and not (args.command == 'export' and args.allow_incomplete) else 0
    except (OSError, ValueError, TypeError) as error:
        print(json.dumps({'status': 'INVALID', 'error': str(error)}, ensure_ascii=False))
        return 1


if __name__ == '__main__':
    sys.exit(main())
