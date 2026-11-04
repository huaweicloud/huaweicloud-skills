"""Snapshot projection and explicit within-stage actions. Never advances the DAG."""
import copy
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import random
import re
import secrets
import threading
import time

from pipeline_state import (Conflict, JSONValue, RUN_TERMINAL, StateError, Store, TERMINAL, atomic_json,
                            bypass_spec, dataset_inputs, iter_steps, now, read_json_object, redact,
                            dependencies_ready, registered_inputs, registration_complete,
                            safe_id, same_step, stage_ref, task_specs, validate_task_datasets)
from sdk_adapter import SDKError, UncertainSubmission, frame_entry, frame_items, items, log_text, obs_key, unwrap
from platform_utils import step_name

LABELS = {'IDLE': '未开始', 'READY': '待提交（等待编排）', 'PENDING': '排队中', 'RUNNING': '运行中',
          'SUCCEEDED': '成功', 'FAILED': '失败', 'DELETED': '已删除', 'SKIPPED': '已跳过',
          'PROCESSING': '处理中', 'AWAITING_DECISION': '等待处理', 'TERMINATED': '已终止',
          'SUCCEEDED_WITH_WARNINGS': '成功（有告警）', 'UNKNOWN': '未知状态'}


def timestamp(value) -> float:
    result = 0.0
    if isinstance(value, (int, float)):
        result = float(value)
        if result > 10**11:
            result /= 1000
    else:
        try:
            result = datetime.fromisoformat(str(value).replace('Z', '+00:00')).timestamp()
        except (ValueError, TypeError):
            result = 0.0
    return result


def spec_for(plan, sid, mid=None) -> dict:
    return next(spec for spec in task_specs(plan) if spec['stage'] == sid and spec['member'] == mid)


def normalize_pool_config(config) -> None:
    if config.get('resource_pool_type') == 'PUBLIC_POOL':
        config.pop('resource_id', None)
        config.pop('dedicated_pool_name', None)


class Monitor:
    def __init__(self, store, client, demo=False):
        self.store = store; self.client = client; self.demo = demo
        self.cache = {}; self.lock = threading.RLock(); self.inflight = set()
        self.pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix='cloudrobo')
        self.drafts = {}; self.file_lists = {}; self.frame_lists = {}
        self.run_generations = {}
        self.revision = 0

    def close(self):
        self.pool.shutdown(wait=True, cancel_futures=True)

    def run_ids(self) -> list:
        return sorted([p.name for p in self.store.root.iterdir() if p.is_dir() and not p.is_symlink()
                       and (p / 'state.json').is_file()], reverse=True)

    def refresh_task(self, run, sid, mid, task, force=False):
        tid = task.get('task_id')
        if not tid or task.get('kind') not in {'proc', 'eval'}:
            return
        key = (run, tid)
        with self.lock:
            generation = self.run_generations.get(run, 0)
            if not (self.store.directory(run) / 'state.json').is_file():
                return
            old = self.cache.get(key, {})
            if key in self.inflight or not force and old.get('next_at', 0) > time.time():
                return
            self.inflight.add(key)
        try:
            detail = unwrap(self.client.task_detail(task['kind'], tid))
            if not isinstance(detail, dict) or not detail.get('status'):
                raise SDKError('SDK 任务详情返回中缺少 status；请在内网确认接口字段')
            status = detail['status']
            entry = {'detail': detail, 'checked_at': now(), 'fetched': time.time(), 'error': None,
                     'next_at': float('inf') if status in TERMINAL else time.time() + random.uniform(12, 18)}
            if old.get('detail', {}).get('status') != status and self.store.read(run).get('schema_version') == 2:
                previous = self.store.events(run)
                if not any(e.get('type') == 'task_status' and e.get('task_id') == tid and e.get('detail') == status for e in previous):
                    self.store.mutate(run, lambda s: None, actor='monitor', stage=sid, member=mid,
                                      expected_task=tid, event_type='task_status', detail=status)
        except Conflict:
            pass  # Historical attempts still get their own read-only detail cache.
        except (StateError, OSError, ValueError) as error:
            message = str(error)
            failures = old.get('failures', 0) + 1
            entry = {**old, 'error': message, 'failures': failures,
                     'next_at': time.time() + min(120, 15 * 2 ** min(failures - 1, 3))}
            if re.search(r'\b404\b|任务不存在|task[^\n]*not found', message, re.I):
                entry.update(detail={'status': 'DELETED', 'error_message': '任务不存在或已被删除'},
                             fetched=time.time(), checked_at=now(), error=None)
        finally:
            with self.lock:
                self.inflight.discard(key)
        with self.lock:
            if generation != self.run_generations.get(run, 0):
                return
            if not (self.store.directory(run) / 'state.json').is_file():
                return
            self.cache[key] = entry; self.revision += 1

    def delete_run(self, run, body) -> dict:
        if body.get('confirmed') is not True:
            raise StateError('请确认仅删除本地运行记录，云端任务和资产不受影响')
        result = self.store.delete_run(run, body.get('expected_version'))
        with self.lock:
            self.run_generations[run] = self.run_generations.get(run, 0) + 1
            self.cache = {key: value for key, value in self.cache.items() if key[0] != run}
            self.file_lists = {key: value for key, value in self.file_lists.items() if key[0] != run}
            self.frame_lists = {key: value for key, value in self.frame_lists.items() if key[0] != run}
            self.drafts = {key: value for key, value in self.drafts.items() if value['run'] != run}
            self.revision += 1
        return result

    def refresh_all(self, wait=False):
        futures = []
        for run in self.run_ids():
            try:
                state = self.store.read(run)
                plan = self.store.plan(run)
                specs = {(spec['stage'], spec['member']): spec for spec in task_specs(plan)}
                for sid, mid, task in iter_steps(state):
                    task = {**task, 'kind': task.get('kind', specs[sid, mid]['kind'])}
                    futures.append(self.pool.submit(self.refresh_task, run, sid, mid, copy.deepcopy(task)))
            except (OSError, StateError, ValueError):
                continue
        if wait:
            for future in futures:
                future.result()

    def snapshot(self, run) -> dict:
        state = self.store.read(run); plan = self.store.plan(run)
        specs = {(spec['stage'], spec['member']): spec for spec in task_specs(plan)}
        nodes = []; warnings = []
        readonly = state.get('schema_version') != 2
        if readonly:
            warnings.append({'tone': 'info', 'text': '旧版 checkpoint：只读模式。请在终端创建 v2 运行后再操作。'})
        beat = timestamp(state.get('orchestrator', {}).get('heartbeat_at'))
        offline = not beat or time.time() - beat > 720
        if offline and state.get('status') not in RUN_TERMINAL:
            warnings.append({'tone': 'neutral', 'text': '编排 Agent 可能离线。网页操作后，请回到终端回复“继续”，由 Agent 推进后续步骤。'})
        if state.get('pending_action'):
            warnings.append({'tone': 'warning', 'text': '有操作正在处理；如创建任务超时或服务曾中断，请先在终端核对新任务，勿重复提交。'})
        if state.get('awaiting_decision'):
            text = '管线暂停，等待处理。可选择失败步骤查看日志并重新提交，或终止后续编排。'
            if state['awaiting_decision'].get('kind') == 'skip':
                text = '已申请跳过处理步骤；请到智能体核实原输入及所有下游算子的格式兼容性。确认前不会放行后续步骤，可取消请求。'
            warnings.append({'tone': 'serious', 'text': text})
        with self.lock:
            cache = copy.deepcopy(self.cache)
        for sid, mid, task in iter_steps(state):
            spec = specs[sid, mid]
            task = {'kind': spec['kind'], 'fail_fast': spec['fail_fast'], 'attempts': [], **task}
            tid = task.get('task_id'); live = cache.get((run, tid), {})
            detail = live.get('detail', {})
            raw_status = detail.get('status', task.get('status'))
            stale = bool(tid and (not live.get('fetched') or live.get('error') or raw_status not in LABELS and raw_status not in {'POD_PENDING', 'STARTING', 'CREATED'} or
                         raw_status not in TERMINAL and time.time() - live.get('fetched', 0) > 36))
            is_pending = same_step(state.get('pending_action'), sid, mid)
            skip_requested = same_step(state.get('awaiting_decision'), sid, mid) and state['awaiting_decision'].get('kind') == 'skip'
            if is_pending:
                display = 'PROCESSING'
            elif state.get('status') in {'TERMINATED', 'FAILED'} and raw_status != 'SUCCEEDED' and not task.get('skipped'):
                display = 'TERMINATED'
            elif task.get('skipped'):
                display = 'SKIPPED'
            elif skip_requested or same_step(state.get('awaiting_decision'), sid, mid) and raw_status in {'FAILED', 'DELETED'}:
                display = 'AWAITING_DECISION'
            elif tid or raw_status:
                display = raw_status if raw_status in LABELS else 'PENDING' if raw_status in {'POD_PENDING', 'STARTING', 'CREATED'} else 'UNKNOWN'
            else:
                display = 'IDLE'  # Resolve dependencies once every node is present.
            node = {**copy.deepcopy(task), 'key': sid + ('/' + mid if mid else ''), 'stage': sid,
                    'member': mid, 'name': spec.get('name', spec.get('operator', mid or sid)),
                    'operator': spec.get('operator', ''), 'depends_on': spec['depends_on'],
                    'dependency_keys': spec['dependency_keys'],
                    'input_from': spec.get('input_from', []),
                    'layer': spec.get('layer', 0), 'external': spec.get('external', False),
                    'display_status': display, 'raw_status': raw_status, 'label': LABELS.get(display, str(raw_status)),
                    'stale': stale, 'checked_at': live.get('checked_at'), 'live': detail,
                    'error': live.get('error'), 'attempt_count': len(task.get('attempts', [])) + bool(tid)}
            node['skip_requested'] = skip_requested
            if sid == 'upload' and not mid:
                node['registrations'] = registered_inputs(state)
                node['registration_complete'] = registration_complete(node['registrations'])
            if task.get('bypassed'):
                warnings.append({'tone': 'info', 'text': node['name'] + ' 已跳过并沿用原输入；未执行该处理，不产生新数据版本。'})
            if task.get('kind') in {'proc', 'eval'}:
                try:
                    self.record(run, node, tid)
                    has_config = True
                except (OSError, StateError, ValueError):
                    has_config = False
            else:
                has_config = False
            writable = not readonly and not state.get('pending_action') and state.get('status') not in {'TERMINATED', 'FAILED'} and not stale
            completed_run = state.get('status') in {'SUCCEEDED', 'SUCCEEDED_WITH_WARNINGS'}
            advisory = not task.get('fail_fast', True)
            retryable = task.get('kind') in {'proc', 'eval'} and (raw_status in {'FAILED', 'DELETED'} or task.get('skipped') and advisory)
            node['actions'] = {'retry': bool(writable and has_config and retryable and (not completed_run or advisory)),
                               'skip': bool(writable and advisory and not completed_run and not task.get('skipped')
                                            and (not tid or raw_status in {'FAILED', 'DELETED'}))}
            node['actions'].update({'request-skip': False, 'cancel-skip': bool(writable and skip_requested)})
            node['skip_disabled_reason'] = '仅未提交、未处理的单输入处理步骤可申请跳过'
            if task['kind'] == 'proc' and not tid and not raw_status and not task.get('skipped'):
                try:
                    node['bypass'] = bypass_spec(plan, state, sid)
                    eligible = writable and not completed_run and not state.get('awaiting_decision')
                    node['actions']['request-skip'] = bool(eligible)
                    node['skip_disabled_reason'] = '请先处理当前决策或提交事务；只读、终止或完成的运行不能申请跳过'
                except StateError as error:
                    node['skip_disabled_reason'] = str(error)
            node['action_reason'] = ('旧版只读模式' if readonly else '状态可能过期，请先恢复 SDK 查询' if stale else
                                     '缺少原始提交配置，请到终端处理' if retryable and not has_config else
                                     '仅失败、删除或跳过的建议性任务可重新提交')
            nodes.append(node)
            if live.get('error'):
                warnings.append({'tone': 'critical', 'text': '无法获取最新状态：' + live['error'][:500]})
        indexed_nodes = {node['key']: node for node in nodes}
        for node in nodes:
            if node['display_status'] == 'IDLE' and dependencies_ready(node['dependency_keys'], indexed_nodes):
                node['display_status'] = 'READY'; node['label'] = LABELS['READY']
            if node['kind'] == 'manual':
                if node['display_status'] == 'SUCCEEDED':
                    node['label'] = {'plan': '已确认', 'upload': '已登记', 'output': '已核实'}.get(node['stage'], '已完成')
                    if node['stage'] == 'upload' and not node.get('registration_complete'):
                        node['label'] = '登记信息待补全'
                        warnings.append({'tone': 'warning', 'text': '上传注册被标记为完成，但本地资产、版本或路径记录不完整；请到智能体核实并补齐输入登记，无需重复上传。'})
                elif node['display_status'] == 'READY':
                    node['label'] = {'plan': '待确认', 'upload': '待登记', 'output': '待核实'}.get(node['stage'], '待处理')
        done = sum(n['display_status'] in {'SUCCEEDED', 'SKIPPED'} or not n.get('fail_fast', True) and n['raw_status'] in TERMINAL for n in nodes)
        active = next((n for n in nodes if n['display_status'] in {'AWAITING_DECISION', 'PROCESSING', 'RUNNING', 'PENDING', 'READY'}), None)
        signature = hashlib.sha256(json.dumps([state.get('version'), nodes, offline], sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:20]
        all_healthy = not any(n['stale'] for n in nodes)
        return redact({'run_id': run, 'plan': plan, 'state': state, 'nodes': nodes, 'warnings': warnings,
                       'version': signature, 'state_version': state.get('version'), 'demo': self.demo,
                       'readonly': readonly, 'agent_offline': offline, 'server_time': now(),
                       'progress': {'done': done, 'total': len(nodes), 'current': active['name'] if active else '—'},
                       'actions': {'terminate': not readonly and state.get('status') not in RUN_TERMINAL
                                   and not state.get('pending_action') and all_healthy,
                                   'delete': not readonly and state.get('status') in RUN_TERMINAL
                                   and not state.get('pending_action')}})

    def node(self, run, stage, member=None) -> dict:
        return next((n for n in self.snapshot(run)['nodes'] if n['stage'] == stage and n['member'] == member), {})

    def locate_task(self, run, tid) -> tuple[str, object, dict, bool]:
        safe_id(tid)
        for sid, mid, task in iter_steps(self.store.read(run)):
            task = {'kind': spec_for(self.store.plan(run), sid, mid)['kind'], **task}
            if task.get('task_id') == tid:
                return sid, mid, task, False
            for attempt in task.get('attempts', []):
                if attempt.get('task_id') == tid:
                    return sid, mid, {**task, **attempt}, True
        raise StateError('任务不属于当前运行')

    def record(self, run, node, tid) -> dict:
        if tid:
            return read_json_object(self.store.directory(run) / 'tasks' / (safe_id(tid) + '.json'))
        config = spec_for(self.store.plan(run), node['stage'], node['member']).get('task_config')
        if isinstance(config, dict) and config:
            return {'task_config': config}
        raise StateError('缺少原始提交配置')

    def task_detail(self, run, tid, refresh=False) -> dict:
        sid, mid, task, historical = self.locate_task(run, tid)
        if refresh or (run, tid) not in self.cache:
            self.refresh_task(run, sid, mid, task, force=refresh)
        try:
            record = self.record(run, {'stage': sid, 'member': mid}, tid)
        except (OSError, StateError):
            record = {'task_config': None}
        with self.lock:
            live = copy.deepcopy(self.cache.get((run, tid), {}))
        previous = None
        attempts = task.get('attempts', [])
        all_ids = [a['task_id'] for a in attempts] + [stage_ref(self.store.read(run), sid, mid).get('task_id')]
        index = all_ids.index(tid)
        if index:
            try:
                previous = self.record(run, {'stage': sid, 'member': mid}, all_ids[index - 1]).get('task_config')
            except (OSError, StateError):
                pass
        return redact({'record': record, 'previous_config': previous, 'live': live.get('detail', task),
                       'error': live.get('error'), 'historical': historical, 'kind': task['kind']})

    def logs(self, run, tid, system=False) -> dict:
        _, _, task, _ = self.locate_task(run, tid)
        data = self.client.log_files(task['kind'], tid, system)
        files = []
        for entry in items(data):
            if isinstance(entry, str):
                files.append({'file_name': entry, 'file_path': ''})
            elif isinstance(entry, dict):
                name = entry.get('file_name', entry.get('name'))
                if name:
                    files.append({'file_name': name, 'file_path': entry.get('file_path', entry.get('path', ''))})
        with self.lock:
            if (self.store.directory(run) / 'state.json').is_file():
                self.file_lists[(run, tid, system)] = files
        return {'files': files, 'raw': data if not files else None}

    def log_content(self, run, tid, name, path, full=False) -> dict:
        _, _, task, _ = self.locate_task(run, tid)
        with self.lock:
            known = [f for k, files in self.file_lists.items() if k[:2] == (run, tid) for f in files]
        if not any(f['file_name'] == name and f['file_path'] == path for f in known):
            raise StateError('日志文件必须来自当前任务的文件列表，请先刷新文件列表')
        data = self.client.read_log(task['kind'], tid, name, path, full)
        content = log_text(data)
        return {'content': content, 'tail': not full, 'bytes': len(content.encode('utf-8'))}

    def frames(self, run, tid, prefix=None) -> dict:
        detail = self.task_detail(run, tid)
        if detail['kind'] != 'proc':
            raise StateError('评测任务不支持 get-frames')
        base = obs_key(detail['live'].get('target_path')).rstrip('/') + '/'
        prefix = (prefix or base).rstrip('/') + '/'
        if prefix != base or '..' in prefix.split('/'):
            raise StateError('仅支持查看当前任务输出根目录的第一层文件和文件夹')
        data = self.client.frames(tid, prefix)
        entries = {}
        for item, directory in frame_items(data):
            name, directory = frame_entry(item, directory)
            if not name or name.startswith(('/', 'obs://', 'http://', 'https://')) or '\\' in name:
                continue
            if any(part in {'.', '..'} for part in name.split('/')):
                continue
            if name.rstrip('/') == base.rstrip('/'):
                continue
            key = name if name.startswith(base) else base + name
            relative = key[len(base):]
            first = relative.split('/')[0]
            if not first:
                continue
            directory = directory or '/' in relative
            previous = entries.get(first, {})
            directory = directory or previous.get('directory', False)
            entries[first] = {'name': first, 'key': base + first + ('/' if directory else ''), 'directory': directory}
        files = sorted(entries.values(), key=lambda item: (not item['directory'], item['name']))
        with self.lock:
            if (self.store.directory(run) / 'state.json').is_file():
                self.frame_lists[(run, tid)] = {item['key'] for item in files if not item['directory']}
        return {'prefix': prefix, 'base': base, 'files': files, 'raw': data if not files else None}

    def preview(self, run, tid, file=None, download=False) -> JSONValue:
        detail = self.task_detail(run, tid)
        if detail['kind'] == 'eval':
            file = obs_key(detail['live'].get('target_report_path'))
        elif file not in self.frame_lists.get((run, tid), set()):
            raise StateError('请先从输出文件列表选择文件')
        return self.client.preview(detail['kind'], tid, file, download)

    def retry_draft(self, run, sid, mid=None) -> dict:
        node = self.node(run, sid, mid)
        if not node or not node['actions']['retry']:
            raise StateError(node['action_reason'] if node else '步骤不存在')
        spec = spec_for(self.store.plan(run), sid, mid)
        if spec.get('operator_source', 'preset') != 'preset':
            raise StateError('工作空间或 OBS 自定义算子请在终端重新查询并确认后提交；网页不会复用旧算子信息。')
        record = self.record(run, node, node.get('task_id'))
        config = copy.deepcopy(record['task_config'])
        normalize_pool_config(config)
        operator = spec.get('operator', config.get('algo_name'))
        assets = items(self.client.operators(operator))
        assets = [asset for asset in assets if asset.get('name') == operator and
                  (not spec.get('operator_id') or asset.get('asset_id', asset.get('id')) == spec['operator_id'])]
        if len(assets) != 1:
            raise StateError('当前区域算子查询未得到唯一匹配，已阻止提交；请到终端确认，不会替换为其他算子。')
        asset = assets[0]; metadata = asset.get('ext_metadata', {})
        if isinstance(metadata, str):
            metadata = json.loads(metadata)
        config.update(algo_id=asset.get('asset_id', asset.get('id')), algo_name=asset['name'],
                      image=metadata.get('engine', {}).get('image_url'), algo_entrance=metadata.get('command'))
        if not all(config.get(k) for k in ('algo_id', 'image', 'algo_entrance')):
            raise StateError('最新算子元数据不完整，已阻止提交')
        def array(value) -> list:
            result = json.loads(value) if isinstance(value, str) else value
            if result is None:
                result = []
            if not isinstance(result, list):
                raise StateError('算子输入和环境变量声明必须为数组')
            return result
        # robot_config 已废弃：配置文件只通过算子声明的 inputs 挂载传入，旧记录中的值不再重新提交。
        config.pop('robot_config', None)
        old_inputs = {v['name']: v for v in array(config.get('inputs'))}
        mounts = []
        for mount in array(metadata.get('inputs')):
            mount = copy.deepcopy(mount)
            if mount.get('name') in old_inputs:
                mount['url_path'] = old_inputs[mount['name']].get('url_path', mount.get('url_path'))
            if mount.get('required') or mount.get('url_path'):
                if not str(mount.get('url_path', '')).startswith('obs://'):
                    raise StateError('最新算子的必需输入缺少 OBS 路径: ' + mount.get('name', ''))
                mounts.append(mount)
        config.pop('inputs', None)
        if mounts:
            config['inputs'] = json.dumps(mounts, ensure_ascii=False)
        old_envs = {v['key']: v for v in array(config.get('envs'))}
        envs = []
        declarations = array(metadata.get('environment_variables'))
        for declaration in declarations:
            key = declaration.get('key', declaration.get('name'))
            if key:
                envs.append({'key': key, 'value': old_envs.get(key, {}).get('value', declaration.get('default', '')),
                             'description': declaration.get('description', '')})
        config['envs'] = json.dumps(envs, ensure_ascii=False)
        datasets = array(config.get('dataset_configs'))
        if node['kind'] == 'eval':
            handoff = dataset_inputs(self.store.plan(run), self.store.read(run), sid)
            expected = handoff['task_config']
            if any(config.get(key) != expected[key] for key in ('dataset_type', 'dataset_id', 'dataset_name', 'dataset_path')):
                raise StateError('评测原输入与已核实交接记录不一致，请到智能体核对；网页不会替换数据集')
            if 'dataset_configs' in config:
                existing = validate_task_datasets(config, 'eval')
                if any(existing[0].get(key) != value for key, value in handoff['datasets'][0].items()):
                    raise StateError('评测原输入与已核实交接记录的版本不一致，请到智能体核对；网页不会替换版本')
            # Old eval records can be completed only from the matching exact handoff,
            # verified below against show-version. Never select the asset's latest version.
            config.setdefault('dataset_configs', expected['dataset_configs'])
            datasets = handoff['datasets']
        for dataset in datasets:
            self.verify_input_version(dataset)
        pipeline_name = self.store.read(run).get('pipeline_name', run)
        name = step_name(pipeline_name, mid or sid, namespace='task')
        if node['kind'] == 'proc':
            config['output_name'] = step_name(pipeline_name, sid)
        draft_id = secrets.token_urlsafe(24)
        draft = {'id': draft_id, 'run': run, 'stage': sid, 'member': mid, 'expected_task_id': node.get('task_id'),
                 'config': config, 'name': name, 'created': time.time(), 'kind': node['kind'],
                 'declarations': declarations}
        with self.lock:
            if not (self.store.directory(run) / 'state.json').is_file():
                raise StateError('运行记录已删除，请返回运行列表')
            self.drafts = {k: v for k, v in self.drafts.items() if time.time() - v['created'] < 600}
            self.drafts[draft_id] = draft
        return redact({'draft_id': draft_id, 'kind': node['kind'], 'name': name, 'config': config, 'previous_config': record['task_config'],
                       'expected_task_id': node.get('task_id'), 'expires_in': 600,
                       'editable': (['output_name', 'head_spec', 'worker_num'] if node['kind'] == 'proc' else []) + ['name', 'resource_pool_type', 'resource_id', 'dedicated_pool_name',
                                    'worker_spec', 'envs', 'inputs']})

    def verify_input_version(self, dataset) -> None:
        if not all(dataset.get(k) for k in ('asset_id', 'version_id', 'obs_path')):
            raise StateError('原始配置缺少上游资产、版本或 OBS 路径')
        version = unwrap(self.client.version(dataset['asset_id'], dataset['version_id']))
        if not isinstance(version, dict) or version.get('url') != dataset['obs_path']:
            raise StateError('上游版本信息不完整或路径已变化，请回到智能体核实产物交接')
        if version.get('status') not in {'DRAFT', 'RELEASE'}:
            raise StateError('上游版本状态 ' + str(version.get('status') or '未知')
                             + ' 尚未确认可用，请到智能体核实平台要求；网页不会自动发布版本')

    def action(self, run, body) -> dict:
        if body.get('confirmed') is not True or 'expected_task_id' not in body:
            raise StateError('操作需要明确确认并提供 expected_task_id')
        action = body.get('type'); sid = body.get('stage'); mid = body.get('member')
        expected = body['expected_task_id']; version = body.get('expected_version')
        action_id = secrets.token_hex(12)
        if action not in {'retry', 'skip', 'terminate', 'request-skip', 'cancel-skip'}:
            raise StateError('不支持的操作')
        draft = None; config = None; name = None
        if action == 'retry':
            with self.lock:
                draft = copy.deepcopy(self.drafts.get(body.get('draft_id')))
            if not draft or time.time() - draft['created'] > 600:
                raise StateError('待确认配置已过期，请重新查询算子')
            if (run, sid, mid, expected) != (draft['run'], draft['stage'], draft['member'], draft['expected_task_id']):
                raise Conflict('配置与当前步骤不一致')
            config = copy.deepcopy(draft['config']); overrides = body.get('overrides', {})
            allowed = {'name', 'output_name', 'resource_pool_type', 'resource_id', 'dedicated_pool_name',
                       'worker_spec', 'head_spec', 'worker_num', 'envs', 'inputs'}
            if draft['kind'] == 'eval':
                allowed -= {'output_name', 'head_spec', 'worker_num'}
            if not isinstance(overrides, dict) or set(overrides) - allowed:
                raise StateError('不允许修改算子元数据或数据集交接字段')
            name = overrides.get('name', draft['name'])
            for key, value in overrides.items():
                if key != 'name':
                    config[key] = value
            self.validate_config(config, name, draft['config'], draft['kind'])
        # Validation and reservation share the exact same state-file lock as the agent.
        def reserve(state):
            snapshot = self.snapshot(run)
            if action == 'terminate':
                if not snapshot['actions']['terminate']:
                    raise Conflict('当前运行不可终止，请刷新状态')
                if body.get('confirmation') != run[-4:]:
                    raise StateError('请输入 run_id 的最后四位')
                state['status'] = 'TERMINATED'; state['finished_at'] = now(); state['awaiting_decision'] = None
                return
            node = next((n for n in snapshot['nodes'] if n['stage'] == sid and n['member'] == mid), None)
            if not node or not node['actions'].get(action):
                raise Conflict('该步骤已被其他操作处理，或当前状态不允许此操作')
            task = stage_ref(state, sid, mid)
            if action == 'request-skip':
                state['awaiting_decision'] = {'kind': 'skip', 'stage': sid, 'member': mid, 'task_id': None,
                                               'input_from': node['bypass']['input_from'], 'consumers': node['bypass']['consumers']}
                state['status'] = 'AWAITING_DECISION'
            elif action == 'cancel-skip':
                state['awaiting_decision'] = None
                state['status'] = 'RUNNING'
            elif action == 'skip':
                task['skipped'] = True
                if same_step(state.get('awaiting_decision'), sid, mid):
                    state['awaiting_decision'] = None; state['status'] = 'RUNNING'
            else:
                state['pending_action'] = {'id': action_id, 'type': action, 'stage': sid, 'member': mid,
                                           'by': 'web', 'at': now(), 'name': name}
                atomic_json(self.store.directory(run) / 'pending-config.json', {'name': name, 'task_config': config})
        self.store.mutate(run, reserve, actor='web', stage=sid if action != 'terminate' else None,
                          member=mid, expected_task=expected, expected_version=version,
                          event_type=action if action != 'retry' else 'action_started')
        if action != 'retry':
            return self.snapshot(run)
        workspace = self.store.read(run).get('workspace_id')
        try:
            created = self.client.create_task(draft['kind'], name, config, workspace)
        except UncertainSubmission:
            # No blind retry: the platform might already have accepted the create.
            raise
        except StateError as error:
            def failed(state):
                if state.get('pending_action', {}).get('id') != action_id:
                    raise Conflict('操作锁已变化')
                state['pending_action'] = None
            self.store.mutate(run, failed, actor='web', stage=sid, member=mid,
                              event_type='action_failed', detail=str(error)[:1000])
            raise
        tid = safe_id(created['task_id'])
        atomic_json(self.store.directory(run) / 'tasks' / (tid + '.json'),
                    {'task_config': config, 'task_name': name, 'by': 'web', 'at': now()})
        def complete(state):
            if not state.get('pending_action') or state['pending_action']['id'] != action_id:
                raise Conflict('操作锁已变化；新任务为 ' + tid + '，请在终端核对')
            task = stage_ref(state, sid, mid)
            if task.get('task_id'):
                old = {k: v for k, v in task.items() if k != 'attempts'}
                old.update(status=self.cache.get((run, expected), {}).get('detail', {}).get('status', old.get('status')))
                task['attempts'].append(old)
            task.update(task_id=tid, task_name=name, status='PENDING', skipped=False, started_at=now())
            for key in ('output_name', 'target_path', 'target_asset_id', 'target_version_id', 'target_report_path', 'error', 'finish_at'):
                task.pop(key, None)
            state['pending_action'] = None
            if same_step(state.get('awaiting_decision'), sid, mid):
                state['awaiting_decision'] = None
            if state['status'] not in {'SUCCEEDED', 'SUCCEEDED_WITH_WARNINGS'}:
                state['status'] = 'RUNNING'
        self.store.mutate(run, complete, actor='web', stage=sid, member=mid, expected_task=expected,
                          event_type='retry', detail='新建任务 ' + tid + '，替代 ' + str(expected))
        self.refresh_task(run, sid, mid, stage_ref(self.store.read(run), sid, mid), force=True)
        return self.snapshot(run)

    def validate_config(self, config, name, original, kind='proc'):
        normalize_pool_config(config)
        validate_task_datasets(config, kind)
        if not isinstance(name, str) or not 3 <= len(name) <= 64 or not re.fullmatch(r'[\u4e00-\u9fa5a-zA-Z0-9_\-./]+', name):
            raise StateError('任务名须为 3–64 个中文、字母、数字或 _-./ 字符')
        field = 'output_name' if kind == 'proc' else 'dataset_name'
        output = config.get(field, '')
        if not isinstance(output, str) or not 2 <= len(output) <= 64 or output.strip() != output or not re.fullmatch(r'[\u4e00-\u9fa5a-zA-Z0-9_\-./ ]+', output):
            raise StateError(field + ' 须为 2–64 个合法字符，首尾不能有空格')
        if not isinstance(config.get('description', ''), str) or len(config.get('description', '')) > 512:
            raise StateError('description 须为不超过 512 字符的文本')
        for field in (('worker_spec', 'head_spec') if kind == 'proc' else ('worker_spec',)):
            spec = config.get(field, {})
            if not isinstance(spec, dict) or set(spec) - {'cpu', 'memory', 'gpu', 'npu'} or any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or v < 0 for v in spec.values()):
                raise StateError(field + ' 必须是非负数值规格对象')
        if config.get('resource_pool_type') not in {'PUBLIC_POOL', 'DEDICATED_POOL'}:
            raise StateError('无效的资源池类型')
        if config['resource_pool_type'] == 'DEDICATED_POOL':
            for field in ('resource_id', 'dedicated_pool_name'):
                value = config.get(field)
                if not isinstance(value, str) or not value.strip():
                    raise StateError('专属池需要有效的 resource_id 和 dedicated_pool_name；缺少或为空: ' + field)
                config[field] = value.strip()
        if isinstance(config.get('worker_num', 1), bool) or not isinstance(config.get('worker_num', 1), int) or config.get('worker_num', 1) < 1:
            raise StateError('worker_num 必须为正整数')
        for field, key in [('envs', 'key'), ('inputs', 'name')]:
            old = json.loads(original.get(field, '[]'))
            new = json.loads(config.get(field, '[]')) if isinstance(config.get(field, '[]'), str) else config[field]
            if not isinstance(new, list) or any(not isinstance(v, dict) for v in new) or len(new) != len(old) or {v.get(key) for v in new} != {v.get(key) for v in old}:
                raise StateError('只允许修改算子已声明的 env 值或输入 url_path')
            for value in new:
                prior = next(v for v in old if v.get(key) == value.get(key))
                mutable = 'value' if field == 'envs' else 'url_path'
                if {k: v for k, v in value.items() if k != mutable} != {k: v for k, v in prior.items() if k != mutable}:
                    raise StateError('算子声明字段不可修改')
                if value.get(mutable) == '••••••':
                    value[mutable] = prior.get(mutable)
                if field == 'inputs' and not str(value.get('url_path', '')).startswith('obs://'):
                    raise StateError('输入路径必须是 obs:// 路径')
            if new:
                config[field] = json.dumps(new, ensure_ascii=False)
            else:
                config.pop(field, None)

    def summary(self, run) -> str:
        snapshot = self.snapshot(run); state = snapshot['state']
        output = state.get('output', {})
        lines = ['# ' + state.get('pipeline_name', run), '', '- 运行：`' + run + '`',
                 '- 状态：' + LABELS.get(state.get('status'), str(state.get('status'))),
                 '- 管线产物：`' + str(output.get('target_path') or '尚未由 Agent 核实') + '`',
                 '- 产物来源步骤：`' + str(output.get('from_stage') or snapshot['plan'].get('output', {}).get('from_stage') or '见已确认执行计划；仅评测时保留输入数据集') + '`',
                 '- 资产：`' + str(output.get('target_asset_id') or '—') + '` / 版本：`' + str(output.get('target_version_id') or '—') + '`',
                 '', '| 步骤 | 状态 | 当前任务 | 历史尝试 |', '|---|---|---|---|']
        for node in snapshot['nodes']:
            lines.append('| ' + ' | '.join(str(v).replace('|', '\\|').replace('\n', ' ') for v in
                         [node['name'], node['label'] + ('（可能过期）' if node['stale'] else ''), node.get('task_id') or '—',
                          ', '.join(a['task_id'] for a in node.get('attempts', [])) or '—']) + ' |')
            report = node.get('live', {}).get('target_report_path', node.get('target_report_path'))
            if report:
                lines += ['', '- 评测报告（OBS 路径）：`' + report + '`']
        lines += ['', '## 告警', *['- ' + w['text'] for w in snapshot['warnings']],
                  *['- ' + n['name'] + '：' + n['label'] for n in snapshot['nodes']
                    if not n.get('not_applicable') and n['display_status'] in {'FAILED', 'SKIPPED', 'DELETED'}],
                  '', '## 已确认的执行计划', '', '```json', json.dumps(snapshot['plan'], ensure_ascii=False, indent=2), '```', '']
        return '\n'.join(lines)
