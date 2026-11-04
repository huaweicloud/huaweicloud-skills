#!/usr/bin/env python3
"""Offline protocol, action and HTTP smoke tests. No credentials or cloud calls."""
from concurrent.futures import ThreadPoolExecutor
from http.client import HTTPConnection
import importlib.util
import io
import copy
import errno
import json
import os
import socket
from pathlib import Path
import sys
import subprocess
import tempfile
import threading
import time
import unittest
from unittest.mock import Mock, patch

MONITOR = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(MONITOR), str(MONITOR.parent)]
from pipeline_state import (Conflict, RESULT_FIELDS, StateError, Store, atomic_json, dataset_inputs,
                            dependencies_ready, execution_frontier, normalize_plan, read_json_object, redact, stage_ref, task_specs, validate_task_datasets)
from sdk_adapter import SDK, DemoSDK, SDKError, UncertainSubmission, created_task_result, sdk_status, unwrap
from monitor import Monitor, spec_for, timestamp
from server import SOURCE_REVISION, Server, browser_data, demo_runs, existing
from custom_pipeline import export as export_pipeline, preview as preview_pipeline, validate as validate_pipeline
import platform_utils


ROBOT_MOUNT = {'name': 'ROBOT_CONFIG_PATH', 'url_path': 'obs://example-bucket/robot/'}


def task_input_config(kind='proc') -> dict:
    entry = {'dataset_type': 'BUILD_IN_ASSET', 'asset_id': 'dataset-1', 'version_id': 'v1',
             'asset_name': '测试数据', 'obs_path': 'obs://bucket/path/'}
    config = {'dataset_configs': json.dumps([entry], ensure_ascii=False)}
    if kind == 'eval':
        config.update(dataset_type='BUILD_IN_ASSET', dataset_id='dataset-1',
                      dataset_name='测试数据', dataset_path='obs://bucket/path/')
    return config


class SDKTests(unittest.TestCase):
    def test_invalid_dataset_versions_or_eval_identity_fail_before_sdk_session(self):
        invalid = [None, '', '[]', '{}', '[null]', 'not-json', []]
        for key, value in [('version_id', None), ('version_id', ''), ('asset_id', ''), ('obs_path', '/tmp/data')]:
            entry = json.loads(task_input_config()['dataset_configs'])[0]
            entry[key] = value
            invalid.append(json.dumps([entry]))
        for kind in ('proc', 'eval'):
            for value in invalid:
                with self.subTest(kind=kind, value=value), patch('sdk_adapter.sdk_session') as session:
                    with self.assertRaises(StateError):
                        SDK().create_task(kind, 'version-check', {**task_input_config(kind), 'dataset_configs': value})
                    session.assert_not_called()
        for key in ('dataset_id', 'dataset_name', 'dataset_path', 'dataset_type'):
            with self.subTest(key=key), patch('sdk_adapter.sdk_session') as session:
                with self.assertRaisesRegex(StateError, '不一致'):
                    SDK().create_task('eval', 'mismatch', {**task_input_config('eval'), key: 'different'})
                session.assert_not_called()
        config = task_input_config('eval')
        config['dataset_configs'] = json.dumps(json.loads(config['dataset_configs']) * 2)
        with patch('sdk_adapter.sdk_session') as session, self.assertRaisesRegex(StateError, '恰好包含一个'):
            SDK().create_task('eval', 'multi-eval', config)
        session.assert_not_called()

    def test_direct_obs_inputs_require_no_fabricated_asset_or_version(self):
        entry = {'dataset_type': 'UDF_OBS_ASSET', 'obs_path': 'obs://example/direct/'}
        config = {'dataset_type': 'UDF_OBS_ASSET', 'dataset_path': entry['obs_path'], 'dataset_name': 'direct-input',
                  'dataset_configs': json.dumps([entry])}
        for kind in ('proc', 'eval'):
            transport = Mock(dispatched=False, response_status=None)
            operation = Mock(return_value={'id': 'created-obs-task'})
            clients = {'dataset': Mock(create_task=operation, create_eval_task=operation)}
            with patch('sdk_adapter.sdk_session', return_value=(transport, clients)):
                SDK().create_task(kind, 'direct-obs', config)
            self.assertEqual(json.loads(operation.call_args.args[0]['dataset_configs']), [entry])
            transport.close.assert_called_once()

    def test_eval_without_config_mounts_sends_no_robot_config_or_inputs(self):
        transport = Mock(dispatched=False, response_status=None)
        operation = Mock(return_value={'task_id': 'eval-basic'})
        config = {'algo_id': 'quality-algo', **task_input_config('eval')}
        with patch('sdk_adapter.sdk_session', return_value=(transport, {'dataset': Mock(create_eval_task=operation)})):
            self.assertEqual(SDK().create_task('eval', 'basic-check', config)['task_id'], 'eval-basic')
        self.assertNotIn('robot_config', operation.call_args.args[0])
        self.assertNotIn('inputs', operation.call_args.args[0])
        self.assertEqual(config, {'algo_id': 'quality-algo', **task_input_config('eval')})
        transport.close.assert_called_once()

    def test_missing_sdk_gives_dependency_guidance_without_cli_fallback(self):
        with patch.dict(sys.modules, {'cloudrobo_dataset.client': None}), patch('subprocess.run') as run, patch('subprocess.Popen') as spawn:
            with self.assertRaisesRegex(SDKError, '同一 Python 环境安装'):
                SDK().task_detail('proc', 'task-1')
            run.assert_not_called()
            spawn.assert_not_called()

    def test_offline_import_demo_and_diagnostics_do_not_load_credentials(self):
        with patch('sdk_adapter.sdk_session', side_effect=AssertionError('offline must not load config')):
            self.assertEqual(DemoSDK().task_detail('proc', 'demo-convert')['status'], 'SUCCEEDED')
            self.assertEqual(sdk_status()['backend'], 'sdk')
            with tempfile.TemporaryDirectory() as directory:
                monitor = Monitor(Store(directory), SDK())
                monitor.refresh_all(wait=True)
                self.assertEqual(monitor.run_ids(), [])
                monitor.close()

    def test_parallel_requests_own_sessions_close_and_obey_limit(self):
        active = 0
        peak = 0
        transports = []
        lock = threading.Lock()
        def factory(_created):
            nonlocal active, peak
            transport = Mock(dispatched=False, response_status=None)
            transports.append(transport)
            def operation(task):
                nonlocal active, peak
                with lock:
                    active += 1
                    peak = max(peak, active)
                time.sleep(.02)
                with lock:
                    active -= 1
                return {'payload': {'id': task, 'status': 'RUNNING'}}
            return transport, {'dataset': Mock(get_task_detail=operation)}
        client = SDK()
        with patch('sdk_adapter.sdk_session', side_effect=factory), ThreadPoolExecutor(max_workers=10) as pool:
            results = list(pool.map(lambda i: client.task_detail('proc', 'task-' + str(i)), range(10)))
        self.assertEqual(len(results), 10)
        self.assertGreater(peak, 1)
        self.assertLessEqual(peak, 4)
        for transport in transports:
            transport.close.assert_called_once()

    def test_unsupported_sdk_method_and_invalid_kind_never_dispatch(self):
        transport = Mock(dispatched=False, response_status=None)
        with patch('sdk_adapter.sdk_session', return_value=(transport, {'dataset': object()})):
            with self.assertRaisesRegex(SDKError, '当前 SDK 不支持'):
                SDK().task_detail('proc', 'task-1')
        transport.close.assert_called_once()
        with patch('sdk_adapter.sdk_session') as session:
            with self.assertRaises(StateError):
                SDK().task_detail('train', 'task-1')
            with self.assertRaises(StateError):
                SDK().version('../asset', 'v1')
            session.assert_not_called()


@unittest.skipUnless(sdk_status()['available'], 'run with Python containing CloudRobo SDK for real SDK contract checks')
class InstalledSDKTests(unittest.TestCase):
    """Use installed SDK classes and signer, intercept only the HTTP socket layer."""
    def setUp(self):
        from types import SimpleNamespace
        import requests
        self.requests = requests
        self.calls = []
        self.code = 200
        self.payload = {'payload': {'id': 'sdk-task-1', 'status': 'RUNNING'}}
        self.failure = None
        self.config = SimpleNamespace(ak='test-ak', sk='test-sk', log_traffic=True,
            ca_bundle=None, verify_ssl=True, https_proxy=None, http_proxy=None,
            proxy_username=None, proxy_password=None, no_proxy='sdk-test.invalid',
            get_endpoint=lambda service: 'https://sdk-test.invalid/' + service)
        def request(method, url, **kwargs):
            self.calls.append((method, url, kwargs))
            if self.failure:
                raise self.failure
            response = requests.Response()
            response.status_code = self.code
            response.headers['Retry-After'] = '.001'
            response._content = json.dumps(self.payload).encode()
            return response
        self.patches = [patch('cloudrobo_core.sdk.Config', return_value=self.config),
                        patch('requests.Session.request', side_effect=request),
                        patch('requests.Session.close'),
                        patch('subprocess.run', side_effect=AssertionError('no Web CLI')),
                        patch('subprocess.Popen', side_effect=AssertionError('no Web CLI'))]
        self.mocks = [item.start() for item in self.patches]
        for item in self.patches:
            self.addCleanup(item.stop)
        self.client = SDK()
        self.proc = {'algo_id': 'algo-1', 'algo_name': '测试算子', 'algo_entrance': 'python main.py',
            'image': 'test-image', 'catalog_id': 'catalog-1', 'resource_pool_type': 'PUBLIC_POOL',
            'cluster_type': 'CCE', 'task_framework_type': 'K8S',
            'dataset_configs': json.dumps([{'dataset_type': 'BUILD_IN_ASSET', 'asset_id': key, 'version_id': 'v1',
                                          'asset_name': key, 'obs_path': 'obs://bucket/' + key + '/'} for key in ('数据A', '数据B')], ensure_ascii=False),
            'output_type': 'BUILD_IN_ASSET', 'output_name': '测试数据',
            'head_spec': {'cpu': 0, 'memory': 0}, 'worker_spec': {'cpu': 4, 'memory': 8},
            'worker_num': 1, 'evs_spec': {'size': 10}, 'inputs': '[{"name":"挂载","url_path":"obs://bucket/path/"}]'}
        self.evaluation = {'algo_id': 'algo-1', 'algo_name': '质量评测', 'algo_entrance': 'python main.py',
            'image': 'test-image', 'dataset_type': 'BUILD_IN_ASSET', 'dataset_id': 'dataset-1',
            'dataset_name': '测试数据', 'dataset_path': 'obs://bucket/path/',
            'dataset_configs': task_input_config('eval')['dataset_configs'],
            'resource_pool_type': 'PUBLIC_POOL', 'worker_spec': {'cpu': 4, 'memory': 8}}

    def test_real_sdk_read_contracts_timeouts_signing_and_session_cleanup(self):
        for kind, segment in (('proc', 'proc-tasks'), ('eval', 'eval-tasks')):
            self.assertEqual(self.client.task_detail(kind, 'task-1')['id'], 'sdk-task-1')
            self.assertTrue(self.calls[-1][1].endswith('/' + segment + '/task-1'))
            self.client.log_files(kind, 'task-1', True)
            self.assertEqual(self.calls[-1][2]['params'], {'is_system': 'true'})
            self.client.read_log(kind, 'task-1', 'job.log', 'logs/中文/job.log')
            self.assertEqual(self.calls[-1][2]['params']['end_byte'], 65536)
            self.assertEqual(self.calls[-1][2]['params']['file_path'], 'logs/中文/job.log')
            self.client.read_log(kind, 'task-1', 'job.log', 'logs/job.log', full=True)
            self.assertEqual(self.calls[-1][2]['params']['end_byte'], 1000000)
            self.client.preview(kind, 'task-1', 'output/质量.html', True)
            expected = {'file_name': 'output/质量.html'}
            if kind == 'eval':
                expected['isDownload'] = True
            self.assertEqual(self.calls[-1][2]['params'], expected)
        self.client.frames('task-1', 'output/sub/')
        self.assertEqual(self.calls[-1][2]['params'], {'prefix': 'output/sub/'})
        self.client.operators('数据清洗')
        self.assertEqual(self.calls[-1][2]['params'], {'type': 'algorithm', 'exact_name': '数据清洗'})
        self.client.version('asset-1', 'version-1')
        self.assertTrue(self.calls[-1][1].endswith('/assets/asset-1/versions/version-1'))
        for method, _, options in self.calls:
            self.assertEqual(method, 'GET')
            self.assertEqual(options['timeout'], (10, 50))
            self.assertIn('Authorization', options['headers'])
        self.assertEqual(self.mocks[2].call_count, len(self.calls))

    def test_real_sdk_create_preserves_config_types_workspace_and_no_retry(self):
        for kind, config, segment in (('proc', self.proc, 'proc-tasks'), ('eval', self.evaluation, 'eval-tasks')):
            original = copy.deepcopy(config)
            result = self.client.create_task(kind, '测试-task', config, 'workspace-explicit')
            self.assertEqual(result['task_id'], 'sdk-task-1')
            self.assertEqual(config, original)
            method, url, options = self.calls[-1]
            self.assertEqual(method, 'POST')
            self.assertTrue(url.endswith('/' + segment))
            body = json.loads(options['data'])
            self.assertEqual(body['workspace_id'], 'workspace-explicit')
            self.assertEqual(body['name'], '测试-task')
            for key, value in original.items():
                self.assertEqual(body[key], value)
            self.assertEqual(json.loads(body['dataset_configs']), json.loads(config['dataset_configs']))
            self.assertTrue(all(entry['version_id'] == 'v1' for entry in json.loads(body['dataset_configs'])))
            self.assertEqual(options['timeout'], (10, 110))
        self.assertEqual(len(self.calls), 2)
        self.assertEqual(self.mocks[2].call_count, 2)

    def test_real_cli_preserves_dataset_versions_through_sdk_and_http_body(self):
        from click.testing import CliRunner
        from cloudrobo_dataset.cli import dataset
        from sdk_adapter import sdk_session
        for kind, config in (('proc', self.proc), ('eval', self.evaluation)):
            transport, clients = sdk_session()
            try:
                args = [kind, 'create-task', '--name', 'version-wire-check', '--workspace-id', 'workspace-explicit',
                        '--task-config', json.dumps(config, ensure_ascii=False)]
                if kind == 'proc':
                    args += ['--algo-type', 'PRESET_ASSETS']
                before = len(self.calls)
                with patch('cloudrobo_dataset.cli.get_client', return_value=clients['dataset']):
                    result = CliRunner().invoke(dataset, args)
                self.assertEqual(result.exit_code, 0, result.output)
                self.assertEqual(len(self.calls), before + 1)
                sent = json.loads(self.calls[-1][2]['data'])
                self.assertEqual(sent['dataset_configs'], config['dataset_configs'])
                self.assertTrue(all(item['version_id'] == 'v1' for item in json.loads(sent['dataset_configs'])))
            finally:
                transport.close()

    def test_retry_pool_matrix_preserves_wire_config_and_history(self):
        for kind in ('proc', 'eval'):
            for status in ('FAILED', 'DELETED'):
                for previous_pool in ('PUBLIC_POOL', 'DEDICATED_POOL'):
                    for selected_pool in ('PUBLIC_POOL', 'DEDICATED_POOL'):
                        with self.subTest(kind=kind, status=status, previous=previous_pool, selected=selected_pool):
                            self.verify_retry_pool_case(kind, status, previous_pool, selected_pool)
        self.assertEqual(len(self.calls), 16)

    def verify_retry_pool_case(self, kind, status, previous_pool, selected_pool):
        with tempfile.TemporaryDirectory() as directory:
            store = Store(directory)
            demo_runs(store)
            source = DemoSDK()
            if kind == 'proc':
                run, sid, mid, tid = 'demo-awaiting-1002', 'cleaning', None, 'demo-clean-1'
            else:
                run, sid, mid, tid = 'demo-completed-1003', 'evaluation', 'diversity-eval', 'demo-diversity'
            source.statuses[tid] = status
            monitor = Monitor(store, source, demo=True)
            try:
                path = store.directory(run) / 'tasks' / (tid + '.json')
                record = read_json_object(path)
                config = record['task_config']
                config.update(resource_pool_type=previous_pool, resource_id='previous-id', dedicated_pool_name='previous-pool')
                if kind == 'proc':
                    config.update(catalog_id='test-catalog', evs_spec={'size': 10}, output_type='BUILD_IN_ASSET')
                atomic_json(path, record)
                original = path.read_bytes()
                monitor.refresh_task(run, sid, mid, stage_ref(store.read(run), sid, mid), force=True)
                draft = monitor.retry_draft(run, sid, mid)
                overrides = {'resource_pool_type': selected_pool}
                if selected_pool == 'DEDICATED_POOL' and previous_pool != selected_pool:
                    overrides.update(resource_id=' selected-id ', dedicated_pool_name=' selected-pool ')
                elif selected_pool == 'PUBLIC_POOL' and status == 'FAILED':
                    # Older clients can still send empty optional fields.
                    overrides.update(resource_id='', dedicated_pool_name='')
                count = len(self.calls)
                with patch.object(source, 'create_task', side_effect=self.client.create_task):
                    result = monitor.action(run, {'type': 'retry', 'stage': sid, 'member': mid,
                        'expected_task_id': tid, 'draft_id': draft['draft_id'], 'confirmed': True,
                        'expected_version': store.read(run)['version'], 'overrides': overrides})
                self.assertEqual(len(self.calls), count + 1)
                method, url, options = self.calls[-1]
                self.assertEqual(method, 'POST')
                self.assertTrue(url.endswith('/proc-tasks' if kind == 'proc' else '/eval-tasks'))
                wire = json.loads(options['data'])
                self.assertEqual(wire['resource_pool_type'], selected_pool)
                if selected_pool == 'PUBLIC_POOL':
                    self.assertNotIn('resource_id', wire)
                    self.assertNotIn('dedicated_pool_name', wire)
                else:
                    prefix = 'previous' if previous_pool == selected_pool else 'selected'
                    self.assertEqual(wire['resource_id'], prefix + '-id')
                    self.assertEqual(wire['dedicated_pool_name'], prefix + '-pool')
                self.assertEqual(wire['dataset_configs'], config['dataset_configs'])
                self.assertEqual(wire['worker_spec'], config['worker_spec'])
                self.assertEqual(wire['workspace_id'], 'ws-demo')
                if kind == 'eval':
                    for key in ('dataset_id', 'dataset_name', 'dataset_path', 'dataset_type'):
                        self.assertEqual(wire[key], config[key])
                    mounts = lambda value: {m['name']: m['url_path'] for m in json.loads(value)}
                    self.assertEqual(mounts(wire['inputs']), mounts(config['inputs']))
                    self.assertNotIn('robot_config', wire)
                    for key in ('output_name', 'head_spec', 'worker_num'):
                        self.assertNotIn(key, wire)
                task = stage_ref(result['state'], sid, mid)
                self.assertEqual(task['task_id'], 'sdk-task-1')
                self.assertTrue(any(attempt['task_id'] == tid for attempt in task['attempts']))
                self.assertIsNone(result['state']['pending_action'])
                self.assertEqual(path.read_bytes(), original)
            finally:
                monitor.close()

    def test_real_sdk_errors_uncertainty_and_preview_manual_retry(self):
        for code, error in ((400, SDKError), (401, SDKError), (404, SDKError), (409, SDKError),
                            (429, SDKError), (408, UncertainSubmission), (500, UncertainSubmission),
                            (503, UncertainSubmission)):
            self.code = code
            self.payload = {'error_msg': 'test failure'}
            before = len(self.calls)
            with self.subTest(code=code), self.assertRaises(error):
                self.client.create_task('proc', '测试-task', self.proc, 'workspace-1')
            self.assertEqual(len(self.calls), before + 1)
        self.code = 500
        before = len(self.calls)
        with self.assertRaises(SDKError):
            self.client.preview('eval', 'task-1', 'report.html')
        self.assertEqual(len(self.calls), before + 1)
        self.code = 200
        self.payload = {'payload': {'url': 'https://report.invalid'}}
        self.assertIn('url', self.client.preview('eval', 'task-1', 'report.html'))
        self.failure = self.requests.Timeout('test timeout')
        before = len(self.calls)
        with self.assertRaises(UncertainSubmission):
            self.client.create_task('eval', '测试-task', self.evaluation, 'workspace-1')
        self.assertEqual(len(self.calls), before + 1)
        with self.assertRaises(SDKError):
            self.client.task_detail('eval', 'task-1')

    def test_real_sdk_validation_precedes_dispatch_and_missing_id_is_uncertain(self):
        with self.assertRaises(StateError):
            self.client.create_task('proc', '测试-task', {}, 'workspace-1')
        self.assertEqual(self.calls, [])
        self.payload = {'payload': {'status': 'PENDING'}}
        with self.assertRaises(UncertainSubmission):
            self.client.create_task('proc', '测试-task', self.proc, 'workspace-1')
        self.assertEqual(len(self.calls), 1)

    def test_installed_sdk_accepts_eval_without_removed_robot_config(self):
        from cloudrobo_dataset.client import EVAL_TASK_REQUIRED_FIELDS
        config = copy.deepcopy(self.evaluation)
        if 'robot_config' in EVAL_TASK_REQUIRED_FIELDS:
            with self.assertRaisesRegex(SDKError, '已废弃的 robot_config.*本次未发送创建请求.*升级'):
                self.client.create_task('eval', 'basic-eval', config, 'workspace-1')
            self.assertEqual(self.calls, [])
        else:
            self.client.create_task('eval', 'basic-eval', config, 'workspace-1')
            self.assertNotIn('robot_config', json.loads(self.calls[-1][2]['data']))


class RuntimeCompatibilityTests(unittest.TestCase):
    def test_short_unique_names_keep_suffix_and_cap_complete_length(self):
        clock = Mock()
        clock.now.return_value.strftime.return_value = '1018102430'
        with patch.object(platform_utils, 'datetime', clock), patch.object(platform_utils, '_NAMING_STAMP', ''), patch.object(platform_utils, '_GENERATED_NAMES', set()):
            first = platform_utils.unique_name('清洗输出' * 20)
            second = platform_utils.unique_name('清洗输出' * 20)
            task = platform_utils.unique_name('pipeline-stage-' * 10, max_length=64)
        self.assertEqual(len(first), 32)
        self.assertEqual(len(second), 32)
        self.assertTrue(first[:-11].startswith(second[:-13]))
        self.assertTrue(first.endswith('-1018102430'))
        self.assertTrue(second.endswith('-1018102430-2'))
        self.assertEqual(len(task), 64)
        self.assertTrue(task.endswith('-1018102430'))
        clock.now.return_value.strftime.assert_called_with('%m%d%H%M%S')

    def test_step_names_preserve_grouping_namespaces_and_full_limit(self):
        clock = Mock()
        clock.now.return_value.strftime.return_value = '1018102430'
        with patch.object(platform_utils, 'datetime', clock), patch.object(platform_utils, '_NAMING_STAMP', ''), patch.object(platform_utils, '_GENERATED_NAMES', set()):
            self.assertEqual(platform_utils.step_name('teleop', 'clean'), 'teleop-clean-1018102430')
            self.assertEqual(platform_utils.step_name('teleop', 'clean'), 'teleop-clean-1018102430-2')
            self.assertEqual(platform_utils.step_name('teleop', 'clean', namespace='task'), 'teleop-clean-1018102430')
            boundary = platform_utils.step_name('p' * 40, 's' * 12)
            self.assertEqual(boundary, 'p' * 40 + '-' + 's' * 12 + '-1018102430')
            self.assertEqual(len(boundary), 64)
            for pipeline, stage in [('p' * 40, 's' * 12), ('p' * 41, 's' * 12)]:
                with self.assertRaisesRegex(ValueError, '超过 64 字符，请缩短'):
                    platform_utils.step_name(pipeline, stage)
            for pipeline, stage in [('', 'clean'), ('teleop', '数据清洗'), ('bad:name', 'clean')]:
                with self.assertRaises(ValueError):
                    platform_utils.step_name(pipeline, stage)

    def test_unique_names_reject_invalid_base_or_length(self):
        for base in ('', '   ', '<output>', 'bad:name', None):
            with self.subTest(base=base), self.assertRaises(ValueError):
                platform_utils.unique_name(base)
        for limit in (17, 65, True, '32'):
            with self.subTest(limit=limit), self.assertRaises(ValueError):
                platform_utils.unique_name('clean', max_length=limit)

    def test_windows_imports_without_fcntl(self):
        code = '''import subprocess, http.server, pathlib, sys, types
sys.modules['fcntl'] = None
sys.modules['msvcrt'] = types.SimpleNamespace()
sys.platform = 'win32'
import platform_utils, pipeline_state, custom_pipeline, server
assert platform_utils.IS_WINDOWS
'''
        env = {**platform_utils.utf8_environment(), 'PYTHONPATH': os.pathsep.join((str(MONITOR), str(MONITOR.parent)))}
        process = subprocess.run([sys.executable, '-c', code], env=env, capture_output=True,
                                 text=True, encoding='utf-8', timeout=10)
        self.assertEqual(process.returncode, 0, process.stderr)

    def test_windows_lock_retries_contention_and_unlocks_same_byte(self):
        offsets = []
        backend = Mock(LK_NBLCK=1, LK_UNLCK=0)
        def lock(descriptor, mode, length):
            offsets.append((os.lseek(descriptor, 0, os.SEEK_CUR), mode, length))
            if len(offsets) == 1:
                raise PermissionError(errno.EACCES, 'busy')
        backend.locking.side_effect = lock
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(platform_utils, 'IS_WINDOWS', True), patch.object(platform_utils, '_locking_backend', backend), patch.object(platform_utils.time, 'sleep') as sleep:
                with self.assertRaisesRegex(ValueError, 'inside'):
                    with platform_utils.file_lock(Path(directory) / 'lock') as file:
                        file.seek(8)
                        raise ValueError('inside')
                self.assertTrue(file.closed)
                sleep.assert_called_once_with(.05)
        self.assertEqual(offsets, [(0, 1, 1), (0, 1, 1), (0, 0, 1)])

    def test_windows_lock_nonblocking_and_unexpected_errors(self):
        with tempfile.TemporaryDirectory() as directory:
            for number, expected in ((errno.EACCES, BlockingIOError), (errno.EBADF, OSError)):
                backend = Mock(LK_NBLCK=1, LK_UNLCK=0)
                backend.locking.side_effect = OSError(number, 'lock failed')
                with self.subTest(errno=number), patch.object(platform_utils, 'IS_WINDOWS', True), patch.object(platform_utils, '_locking_backend', backend), patch.object(platform_utils.time, 'sleep') as sleep:
                    with self.assertRaises(expected):
                        with platform_utils.file_lock(Path(directory) / 'lock', blocking=False):
                            self.fail('must not enter protected section')
                    backend.locking.assert_called_once()
                    sleep.assert_not_called()

    def test_native_lock_releases_after_body_exception(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / '运行 lock'
            with self.assertRaises(ValueError):
                with platform_utils.file_lock(path):
                    raise ValueError('interrupted')
            with platform_utils.file_lock(path, blocking=False):
                self.assertTrue(path.exists())

    def test_windows_atomic_replace_retries_and_preserves_previous_state(self):
        original_replace = os.replace
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / 'state.json'
            source = Path(directory) / 'new.json'
            target.write_text('old', encoding='utf-8')
            source.write_text('new', encoding='utf-8')
            calls = []
            def replace(first, second):
                calls.append(1)
                if len(calls) == 1:
                    raise PermissionError(errno.EACCES, 'sharing violation')
                original_replace(first, second)
            with patch.object(platform_utils, 'IS_WINDOWS', True), patch.object(platform_utils.os, 'replace', side_effect=replace), patch.object(platform_utils.time, 'sleep'):
                platform_utils.atomic_replace(source, target)
            self.assertEqual(target.read_text(encoding='utf-8-sig'), 'new')
            source.write_text('next', encoding='utf-8')
            with patch.object(platform_utils, 'IS_WINDOWS', True), patch.object(platform_utils.os, 'replace', side_effect=PermissionError('busy')):
                with self.assertRaises(PermissionError):
                    platform_utils.atomic_replace(source, target, timeout=0)
            self.assertEqual(target.read_text(encoding='utf-8-sig'), 'new')
            self.assertTrue(source.exists())

    def test_detached_process_options_are_platform_specific(self):
        with patch.object(platform_utils, 'IS_WINDOWS', True), patch.object(subprocess, 'CREATE_NO_WINDOW', 0x08000000, create=True), patch.object(subprocess, 'CREATE_NEW_PROCESS_GROUP', 512, create=True):
            self.assertEqual(platform_utils.detached_process_options(), {'creationflags': 0x08000200})
        with patch.object(platform_utils, 'IS_WINDOWS', False):
            self.assertEqual(platform_utils.detached_process_options(), {'start_new_session': True})

    def test_windows_hidden_startup_info_and_server_flags(self):
        startup = type('Startup', (), {'dwFlags': 0, 'wShowWindow': 1})()
        with patch.object(platform_utils, 'IS_WINDOWS', True), patch.object(subprocess, 'STARTUPINFO', return_value=startup, create=True), patch.object(subprocess, 'STARTF_USESHOWWINDOW', 1, create=True), patch.object(subprocess, 'SW_HIDE', 0, create=True), patch.object(subprocess, 'CREATE_NO_WINDOW', 0x08000000, create=True), patch.object(subprocess, 'CREATE_NEW_PROCESS_GROUP', 512, create=True):
            options = platform_utils.hidden_process_options()
            self.assertIs(options['startupinfo'], startup)
            self.assertEqual(startup.dwFlags & 1, 1)
            self.assertEqual(startup.wShowWindow, 0)
            self.assertEqual(platform_utils.detached_process_options()['creationflags'], 0x08000200)

    def test_processes_share_checkpoint_lock_on_unicode_path(self):
        code = '''import sys, time
from pipeline_state import Store
store = Store(sys.argv[1])
def increment(state):
    time.sleep(.005)
    state['counter'] = state.get('counter', 0) + 1
for _ in range(10):
    store.mutate('counter', increment)
'''
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / '管线 records'
            store = Store(root)
            store.init('counter', {'monitor_bookends': False, 'stages': [{'id': 'step', 'kind': 'manual'}]})
            env = {**platform_utils.utf8_environment(), 'PYTHONPATH': str(MONITOR.parent)}
            children = [subprocess.Popen([sys.executable, '-c', code, str(root)], env=env,
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE) for _ in range(2)]
            try:
                for process in children:
                    _, error = process.communicate(timeout=15)
                    self.assertEqual(process.returncode, 0, error.decode('utf-8', errors='replace'))
            finally:
                for process in children:
                    if process.poll() is None:
                        process.kill()
                        process.wait(timeout=5)
            self.assertEqual(store.read('counter')['counter'], 20)
            self.assertEqual(store.read('counter')['version'], 21)
            self.assertEqual([event['seq'] for event in store.events('counter')], list(range(1, 22)))

    def test_utf8_bom_authoring_and_checkpoint_cli(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / '含空格 目录'
            root.mkdir()
            draft = root / 'choices.json'
            draft.write_text(json.dumps(CustomPipelineTests().choices(), ensure_ascii=False), encoding='utf-8-sig')
            command = [sys.executable, str(MONITOR.parent / 'custom_pipeline.py'), 'export', '--input', str(draft), '--output-dir', str(root / '输出')]
            result = subprocess.run(command, capture_output=True, env={**platform_utils.utf8_environment(), 'PYTHONIOENCODING': 'ascii'}, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr.decode('utf-8', errors='replace'))
            self.assertIn('pipeline-preview.md', result.stdout.decode('utf-8'))
            plan = root / 'plan.json'
            plan.write_text(json.dumps({'name': '中文管线', 'stages': [{'id': 'step'}]}, ensure_ascii=False), encoding='utf-8-sig')
            command = [sys.executable, str(MONITOR.parent / 'pipeline_state.py'), '--runs-root', str(root / '状态'), '--run', 'bom-run', 'init', '--plan', str(plan)]
            result = subprocess.run(command, capture_output=True, env={**platform_utils.utf8_environment(), 'PYTHONIOENCODING': 'ascii'}, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr.decode('utf-8', errors='replace'))
            self.assertEqual(json.loads(result.stdout)['pipeline_name'], '中文管线')

    def test_windows_reserved_ids_are_rejected(self):
        from pipeline_state import safe_id
        with patch('pipeline_state.IS_WINDOWS', True):
            for identifier in ('CON', 'nul.json', 'COM1', 'lpt9.txt', 'run.'):
                with self.subTest(identifier=identifier), self.assertRaises(StateError):
                    safe_id(identifier)
            self.assertEqual(safe_id('win-run-01'), 'win-run-01')


def merge_choices():
    return {'pipeline': {'name': 'branch-merge',
                        'inputs': [{'id': key, 'source_type': 'asset', 'asset_id': 'asset-' + key,
                                    'version_id': 'v1', 'asset_name': 'data-' + key,
                                    'obs_path': 'obs://example/' + key + '/', 'data_source_type': 'csv'}
                                   for key in ('left', 'right')],
                        'output': {'asset_name': 'merged-output'},
                        'stages': [{'id': 'A', 'operator_id': 'workspace-filter', 'operator_source': 'workspace', 'input_from': ['input:left']},
                                   {'id': 'B', 'operator_id': 'workspace-map', 'operator_source': 'workspace', 'input_from': ['input:right']},
                                   {'id': 'C', 'operator_id': 'workspace-merge', 'operator_source': 'workspace',
                                    'depends_on': ['A', 'B'], 'input_from': ['B', 'A']}]},
            'authoring': {'input_stage': {'left': 'raw', 'right': 'raw'}}}


class CustomPipelineTests(unittest.TestCase):
    def test_suggest_names_cli_is_short_and_readonly(self):
        with tempfile.TemporaryDirectory() as directory:
            command = [sys.executable, str(MONITOR.parent / 'custom_pipeline.py'), 'suggest-names', '--base', 'clean', '--base', 'convert']
            result = subprocess.run(command, cwd=directory, capture_output=True, text=True, encoding='utf-8')
            self.assertEqual(result.returncode, 0, result.stderr)
            response = json.loads(result.stdout)
            self.assertEqual(response['status'], 'SUGGESTED')
            self.assertEqual([item['base'] for item in response['names']], ['clean', 'convert'])
            for item in response['names']:
                self.assertLessEqual(len(item['name']), 32)
                self.assertRegex(item['name'], r'^.+-\d{10}(?:-\d+)?$')
            self.assertEqual(list(Path(directory).iterdir()), [])
            invalid = subprocess.run(command + ['--base', '<invalid>'], cwd=directory, capture_output=True, text=True, encoding='utf-8')
            self.assertEqual(invalid.returncode, 1)
            self.assertEqual(json.loads(invalid.stdout)['status'], 'INVALID')
            grouped = command[:3] + ['--pipeline-name', 'teleop', '--stage', 'convert', '--stage', 'clean']
            result = subprocess.run(grouped, cwd=directory, capture_output=True, text=True, encoding='utf-8')
            self.assertEqual(result.returncode, 0, result.stderr)
            names = json.loads(result.stdout)['names']
            self.assertEqual([item['stage'] for item in names], ['convert', 'clean'])
            for item in names:
                self.assertTrue(item['name'].startswith('teleop-' + item['stage'] + '-'))
                self.assertLessEqual(len(item['name']), 64)
                self.assertRegex(item['name'], r'^teleop-(convert|clean)-\d{10}$')
            for arguments in [['--pipeline-name', 'teleop'], ['--stage', 'clean'],
                              ['--pipeline-name', 'teleop', '--stage', 'clean', '--base', 'mixed']]:
                rejected = subprocess.run(command[:3] + arguments, cwd=directory, capture_output=True, text=True, encoding='utf-8')
                self.assertEqual(rejected.returncode, 2)
            self.assertEqual(list(Path(directory).iterdir()), [])

    def test_exact_output_names_are_preserved_and_full_limit_is_64(self):
        raw = self.choices()
        raw['pipeline']['output']['asset_name'] = '精' * 64
        raw['authoring']['output_names'] = {'convert': 'explicit-converted'}
        first, issues, _ = validate_pipeline(raw)
        second, repeated_issues, _ = validate_pipeline(first)
        self.assertEqual(issues, [])
        self.assertEqual(repeated_issues, [])
        self.assertEqual(first['pipeline']['output'], second['pipeline']['output'])
        self.assertEqual(first['authoring']['output_names'], second['authoring']['output_names'])
        self.assertEqual(second['pipeline']['output']['asset_name'], '精' * 64)
        self.assertEqual(second['authoring']['output_names']['convert'], 'explicit-converted')
        raw['pipeline']['output']['asset_name'] += '长'
        self.assertTrue(any(item['path'] == 'pipeline.output.asset_name' and item['kind'] == 'error' for item in validate_pipeline(raw)[1]))

    def choices(self):
        return {'pipeline': {'name': 'custom-quality',
                            'inputs': [{'source_type': 'obs', 'obs_path': 'obs://example-bucket/raw/', 'data_source_type': 'h5'}],
                            'output': {'asset_name': 'custom-cleaned'},
                            'stages': [{'id': 'convert', 'operator': '数据转换--H5转LeRobotV3'},
                                       {'id': 'cleaning', 'operator': '数据清洗'},
                                       {'id': 'evaluation',
                                        'parallel_group': [{'id': 'quality', 'operator': '数据集质量评测-LeRobot'}]}]},
                'authoring': {'input_stage': 'raw', 'resources': {'resource_pool_type': 'PUBLIC_POOL',
                              'worker_spec': {'cpu': 4, 'memory': 8, 'gpu': 0, 'npu': 0}, 'worker_num': 1}}}

    def test_natural_language_choices_produce_explicit_single_eval_pipeline(self):
        raw = self.choices(); original = copy.deepcopy(raw)
        draft, issues, warnings = validate_pipeline(raw)
        self.assertEqual(issues, [])
        self.assertEqual(raw, original)
        stages = draft['pipeline']['stages']
        self.assertEqual(stages[1]['depends_on'], ['convert'])
        self.assertEqual(stages[2]['depends_on'], ['cleaning'])
        self.assertFalse(stages[2]['fail_fast'])
        self.assertEqual(len(stages[2]['parallel_group']), 1)
        monitor_plan = normalize_plan(draft)
        self.assertEqual(next(s for s in monitor_plan['stages'] if s['id'] == 'convert')['depends_on'], ['upload'])
        self.assertTrue(warnings)  # Structural validity never establishes cloud readiness.

    def test_empty_choices_remain_incomplete_without_template(self):
        raw = {'pipeline': {'stages': []}, 'authoring': {}}
        draft, issues, _ = validate_pipeline(raw)
        self.assertEqual(draft['pipeline']['stages'], [])
        self.assertTrue(issues)
        self.assertTrue(all(i['kind'] == 'missing' for i in issues))
        self.assertNotIn('output', draft['pipeline'])

    def test_preset_only_workflow_does_not_add_standard_stages(self):
        raw = self.choices()
        raw['pipeline']['inputs'][0]['data_source_type'] = 'csv'
        raw['pipeline']['stages'] = [
            {'id': 'filter', 'operator': '示例内置筛选'},
            {'id': 'sample', 'operator': '示例内置抽样'}]
        draft, issues, _ = validate_pipeline(raw)
        self.assertEqual(issues, [])
        self.assertEqual([s['operator'] for s in draft['pipeline']['stages']], ['示例内置筛选', '示例内置抽样'])
        self.assertEqual(draft['pipeline']['output']['from_stage'], 'sample')
        self.assertEqual(draft['pipeline']['stages'][1]['depends_on'], ['filter'])

    def test_workspace_only_workflow_can_process_raw_input(self):
        raw = self.choices()
        raw['pipeline']['stages'] = [
            {'id': 'private-clean', 'operator': '数据清洗', 'operator_source': 'workspace'},
            {'id': 'private-map', 'operator_id': 'workspace-map-asset', 'operator_source': 'workspace'}]
        draft, issues, _ = validate_pipeline(raw)
        self.assertEqual(issues, [])
        self.assertEqual(draft['pipeline']['output']['from_stage'], 'private-map')
        self.assertTrue(all(s['operator_source'] == 'workspace' for s in draft['pipeline']['stages']))
        raw['authoring']['input_stage'] = 'processed'
        for source in ({'source_type': 'obs', 'obs_path': 'obs://example-bucket/processed/', 'data_source_type': 'h5'},
                       {'source_type': 'local', 'local_path': 'C:/data/processed', 'data_source_type': 'h5'}):
            raw['pipeline']['inputs'] = [source]
            self.assertEqual(validate_pipeline(raw)[1], [])

    def test_mixed_sources_export_chosen_workflow_and_monitor_output(self):
        raw = self.choices()
        raw['pipeline']['inputs'][0]['data_source_type'] = 'csv'
        raw['pipeline']['stages'] = [
            {'id': 'filter', 'operator': '示例内置筛选'},
            {'id': 'private-map', 'operator_id': 'workspace-map-asset', 'operator_source': 'workspace'},
            {'id': 'audit', 'kind': 'eval', 'operator_id': 'workspace-audit-asset', 'operator_source': 'workspace'}]
        draft, issues, warnings = validate_pipeline(raw)
        self.assertEqual(issues, [])
        self.assertEqual(draft['pipeline']['output']['from_stage'], 'private-map')
        self.assertEqual(draft['pipeline']['stages'][-1]['depends_on'], ['private-map'])
        plan = normalize_plan(draft)
        self.assertEqual(plan['stages'][-1]['name'], '产物核对')
        self.assertEqual(plan['stages'][-1]['depends_on'], ['audit'])
        with tempfile.TemporaryDirectory() as directory:
            export_pipeline(draft, issues, warnings, directory)
            saved = json.loads((Path(directory) / 'pipeline.draft.json').read_text(encoding='utf-8'))
            self.assertEqual(saved['pipeline'], draft['pipeline'])
            self.assertIn('private-map', (Path(directory) / 'pipeline-preview.md').read_text(encoding='utf-8'))

    def test_evaluation_accepts_compatible_input_without_cleaning(self):
        raw = self.choices()
        raw['pipeline']['stages'] = [raw['pipeline']['stages'][-1]]
        raw['pipeline']['inputs'] = [{'source_type': 'asset', 'asset_id': 'asset-1', 'version_id': 'v1', 'data_source_type': 'lerobotv3'}]
        raw['pipeline'].pop('output')
        raw['authoring'].update(input_stage='converted', upstream={'target_path': 'obs://example-bucket/converted/',
                               'asset_id': 'asset-1', 'version_id': 'v1', 'asset_name': 'converted-data'})
        self.assertEqual(validate_pipeline(raw)[1], [])
        raw['authoring'] = {'input_stage': 'raw'}
        raw['pipeline']['inputs'] = [{'source_type': 'obs', 'obs_path': 'obs://example-bucket/raw/', 'data_source_type': 'h5'}]
        self.assertTrue(any('须先转换' in i['message'] for i in validate_pipeline(raw)[1]))
        raw['pipeline']['stages'][0]['parallel_group'][0].update(operator='自有H5评测', operator_source='workspace')
        self.assertEqual(validate_pipeline(raw)[1], [])

    def test_output_selection_and_parallel_terminal_monitor_dependencies(self):
        raw = self.choices()
        raw['pipeline']['inputs'][0]['data_source_type'] = 'csv'
        raw['pipeline']['stages'] = [
            {'id': 'root', 'operator': '示例预处理'},
            {'id': 'first', 'operator': '示例筛选', 'depends_on': ['root']},
            {'id': 'second', 'operator': '示例抽样', 'depends_on': ['root']}]
        self.assertTrue(any(i['path'] == 'pipeline.output.from_stage' for i in validate_pipeline(raw)[1]))
        raw['pipeline']['output']['from_stage'] = 'first'
        draft, issues, _ = validate_pipeline(raw)
        self.assertEqual(issues, [])
        self.assertEqual(set(normalize_plan(draft)['stages'][-1]['depends_on']), {'first', 'second'})
        for invalid in ('unknown-stage', ['first']):
            raw['pipeline']['output']['from_stage'] = invalid
            self.assertTrue(any(i['path'] == 'pipeline.output.from_stage' for i in validate_pipeline(raw)[1]))
        raw = self.choices()
        raw['pipeline']['output']['from_stage'] = 'evaluation'
        self.assertTrue(any('数据集' in i['message'] for i in validate_pipeline(raw)[1]))

    def test_cycle_unknown_dependency_and_task_name_limits(self):
        raw = self.choices(); raw['pipeline']['stages'][0]['depends_on'] = ['evaluation']
        self.assertTrue(any('循环' in i['message'] for i in validate_pipeline(raw)[1]))
        raw = self.choices(); raw['pipeline']['stages'][1]['depends_on'] = ['missing-step']
        self.assertTrue(any('不存在' in i['message'] for i in validate_pipeline(raw)[1]))
        raw = self.choices(); raw['pipeline']['name'] = 'a' * 48
        self.assertTrue(any('64' in i['message'] for i in validate_pipeline(raw)[1]))

    def test_partial_evaluation_requires_matching_cleaned_asset_handoff(self):
        raw = self.choices(); raw['pipeline']['stages'] = [raw['pipeline']['stages'][-1]]
        raw['pipeline']['inputs'] = [{'source_type': 'asset', 'asset_id': 'asset-1', 'version_id': 'v1'}]
        raw['authoring'].update(input_stage='cleaned', upstream={'target_path': 'obs://example-bucket/cleaned/',
                               'asset_id': 'asset-1', 'version_id': 'v1', 'asset_name': 'cleaned-data'})
        raw['pipeline'].pop('output')  # Eval-only authoring does not invent a new dataset output.
        self.assertEqual(validate_pipeline(raw)[1], [])
        raw['authoring']['upstream']['version_id'] = 'v2'
        self.assertTrue(any('一致' in i['message'] for i in validate_pipeline(raw)[1]))
        raw['authoring']['upstream'].pop('asset_name')
        self.assertTrue(any(i['kind'] == 'missing' for i in validate_pipeline(raw)[1]))

    def test_custom_workspace_stage_keeps_transitive_cleaning_dependency(self):
        raw = self.choices()
        raw['pipeline']['stages'].insert(2, {'id': 'private-filter', 'operator': '我的脱敏算子', 'operator_source': 'workspace'})
        raw['authoring']['roles'] = {'private-filter': 'processing'}
        draft, issues, _ = validate_pipeline(raw)
        self.assertEqual(issues, [])
        self.assertEqual(draft['pipeline']['stages'][-1]['depends_on'], ['private-filter'])
        raw['pipeline']['stages'][2].update(operator_source='obs', algo_path='obs://example-bucket/code/',
                                          job_local_path='/workspace/operator', image='swr.example.com/operator:v1', algo_entrance='python main.py')
        self.assertEqual(validate_pipeline(raw)[1], [])

    def test_bad_order_ambiguous_sources_and_report_as_dataset_are_rejected(self):
        raw = self.choices(); raw['pipeline']['stages'][1]['depends_on'] = []
        self.assertTrue(any('须先转换' in i['message'] for i in validate_pipeline(raw)[1]))
        raw = self.choices(); raw['pipeline']['stages'][1]['depends_on'] = ['convert', 'evaluation']
        self.assertTrue(any('input_from' in i['message'] for i in validate_pipeline(raw)[1]))
        raw = self.choices(); raw['pipeline']['stages'].append({'id': 'after-report', 'operator': 'custom'})
        self.assertTrue(any('报告' in i['message'] for i in validate_pipeline(raw)[1]))

    def test_two_single_dataset_branches_merge_and_export_in_chosen_order(self):
        raw = merge_choices()
        draft, issues, warnings = validate_pipeline(raw)
        self.assertEqual(issues, [])
        self.assertEqual(draft['pipeline']['output']['from_stage'], 'C')
        self.assertEqual(draft['pipeline']['stages'][1]['depends_on'], [])
        self.assertEqual(draft['pipeline']['stages'][2]['input_from'], ['B', 'A'])
        plan = normalize_plan(draft)
        self.assertEqual(next(stage for stage in plan['stages'] if stage['id'] == 'B')['depends_on'], ['upload'])
        self.assertTrue(any('多数据集' in warning for warning in warnings))
        with tempfile.TemporaryDirectory() as directory:
            export_pipeline(draft, issues, warnings, directory)
            exported = json.loads((Path(directory) / 'pipeline.draft.json').read_text(encoding='utf-8'))
            self.assertEqual(exported['pipeline']['stages'][2]['input_from'], ['B', 'A'])
            preview = (Path(directory) / 'pipeline-preview.md').read_text(encoding='utf-8')
            self.assertIn('B, A', preview)
            self.assertIn('数据来源', preview)
            self.assertIn('input_from:', (Path(directory) / 'pipeline.yaml').read_text(encoding='utf-8'))

    def test_single_source_can_fan_out_and_dependencies_infer_from_explicit_inputs(self):
        raw = merge_choices()
        raw['pipeline']['inputs'] = [raw['pipeline']['inputs'][0]]
        raw['authoring']['input_stage'] = 'raw'
        raw['pipeline']['stages'][1]['input_from'] = ['input:left']
        raw['pipeline']['stages'][2].pop('depends_on')
        draft, issues, _ = validate_pipeline(raw)
        self.assertEqual(issues, [])
        self.assertEqual(draft['pipeline']['stages'][2]['depends_on'], ['B', 'A'])

    def test_report_can_be_waited_on_but_not_consumed_and_eval_stays_single_input(self):
        raw = merge_choices()
        check = {'id': 'check', 'kind': 'eval', 'operator_id': 'workspace-audit', 'operator_source': 'workspace',
                 'input_from': ['A']}
        raw['pipeline']['stages'].insert(2, check)
        raw['pipeline']['stages'][-1]['depends_on'].append('check')
        draft, issues, _ = validate_pipeline(raw)
        self.assertEqual(issues, [])
        self.assertEqual(draft['pipeline']['stages'][-1]['input_from'], ['B', 'A'])
        raw['pipeline']['stages'][-1]['input_from'] = ['A', 'check']
        self.assertTrue(any('报告' in issue['message'] for issue in validate_pipeline(raw)[1]))
        check['input_from'] = ['A', 'B']
        self.assertTrue(any('评测接口只接受一个' in issue['message'] for issue in validate_pipeline(raw)[1]))

    def test_data_bindings_reject_invalid_refs_and_ambiguous_initial_inputs(self):
        for refs in (None, [], ['A', 'A'], ['input:missing'], ['missing'], ['A', 1], ['C']):
            raw = merge_choices()
            raw['pipeline']['stages'][-1]['input_from'] = refs
            with self.subTest(refs=refs):
                self.assertTrue(validate_pipeline(raw)[1])
                with self.assertRaises(StateError):
                    normalize_plan(raw)
        raw = merge_choices()
        raw['pipeline']['stages'][-1]['depends_on'] = ['A']
        self.assertTrue(any('等待依赖' in issue['message'] for issue in validate_pipeline(raw)[1]))
        for change in ('duplicate-id', 'missing-id', 'no-binding'):
            raw = merge_choices()
            if change == 'duplicate-id':
                raw['pipeline']['inputs'][1]['id'] = 'left'
            elif change == 'missing-id':
                raw['pipeline']['inputs'][1].pop('id')
            else:
                raw['pipeline']['stages'][0].pop('input_from')
            with self.subTest(change=change):
                self.assertTrue(validate_pipeline(raw)[1])
                with self.assertRaises(StateError):
                    normalize_plan(raw)

    def test_unrelated_conversion_gate_does_not_convert_another_data_route(self):
        raw = self.choices()
        raw['pipeline']['stages'][1].update(depends_on=['convert'], input_from=['input:default'])
        self.assertTrue(any('须先转换' in issue['message'] for issue in validate_pipeline(raw)[1]))
        raw['pipeline']['stages'][1]['input_from'] = ['convert', 'input:default']
        self.assertTrue(any('须先转换' in issue['message'] for issue in validate_pipeline(raw)[1]))

    def test_multiple_processed_input_contexts_require_each_exact_version(self):
        raw = merge_choices()
        raw['authoring']['input_stage'] = {'left': 'converted', 'right': 'cleaned'}
        raw['authoring']['upstream'] = {
            key: {'asset_id': 'asset-' + key, 'version_id': 'v1', 'asset_name': 'data-' + key,
                  'target_path': 'obs://example/' + key + '/'} for key in ('left', 'right')}
        self.assertEqual(validate_pipeline(raw)[1], [])
        raw['authoring']['upstream']['right']['version_id'] = 'v2'
        self.assertTrue(any('right.version_id' in issue['path'] and '一致' in issue['message'] for issue in validate_pipeline(raw)[1]))

    def test_control_only_gate_does_not_choose_final_data_output(self):
        raw = merge_choices()
        raw['pipeline']['stages'][-1]['input_from'] = ['A']
        issues = validate_pipeline(raw)[1]
        self.assertTrue(any(issue['path'] == 'pipeline.output.from_stage' for issue in issues))
        raw['pipeline']['output']['from_stage'] = 'C'
        self.assertEqual(validate_pipeline(raw)[1], [])

    def test_params_credentials_failure_policy_and_dedicated_pool_validation(self):
        raw = self.choices(); raw['pipeline']['stages'][1]['params'] = {'checks': ['blur'], 'envs': {'HUAWEI_CLOUD_AK': 'do-not-store'}}
        raw['pipeline']['stages'][1]['fail_fast'] = False
        raw['authoring']['resources']['resource_pool_type'] = 'DEDICATED_POOL'
        issues = validate_pipeline(raw)[1]
        self.assertTrue(any(i['path'].endswith('.checks') for i in issues))
        self.assertTrue(any('凭据' in i['message'] for i in issues))
        self.assertTrue(any('阻断' in i['message'] for i in issues))
        self.assertTrue(any(i['path'].endswith('.resource_id') for i in issues))
        self.assertNotIn('do-not-store', json.dumps(issues))

    def test_exports_keep_preferences_separate_and_preserve_existing_files(self):
        draft, issues, warnings = validate_pipeline(self.choices())
        with tempfile.TemporaryDirectory() as directory:
            paths = export_pipeline(draft, issues, warnings, directory)
            self.assertEqual(len(paths), 3)
            yaml = (Path(directory) / 'pipeline.yaml').read_text(encoding='utf-8-sig')
            self.assertNotIn('authoring:', yaml)
            self.assertNotIn('worker_spec:', yaml)
            saved = json.loads((Path(directory) / 'pipeline.draft.json').read_text(encoding='utf-8-sig'))
            self.assertEqual(saved['authoring']['resources']['worker_spec']['memory'], 8)
            before = {p: Path(p).read_bytes() for p in paths}
            with self.assertRaises(FileExistsError):
                export_pipeline(draft, issues, warnings, directory)
            self.assertTrue(all(Path(p).read_bytes() == data for p, data in before.items()))

    def test_preview_surfaces_eval_config_mounts_and_unselected_intermediate_output(self):
        raw = self.choices()
        raw['pipeline']['stages'][-1]['parallel_group'][0]['params'] = {'inputs': [ROBOT_MOUNT]}
        draft, issues, warnings = validate_pipeline(raw)
        self.assertEqual(issues, [])
        content = preview_pipeline(draft, issues, warnings)
        self.assertIn('| quality | ROBOT_CONFIG_PATH → obs://example-bucket/robot/ |', content)
        self.assertTrue(any('convert' in warning and '输出名' in warning for warning in warnings))
        draft['authoring']['output_names'] = {'convert': 'chosen-converted'}
        _, issues, warnings = validate_pipeline(draft)
        self.assertEqual(issues, [])
        self.assertFalse(any('convert' in warning and '输出名' in warning for warning in warnings))

    def test_parallel_members_mount_configs_independently(self):
        raw = self.choices()
        group = raw['pipeline']['stages'][-1]
        group['parallel_group'][0]['params'] = {'inputs': [ROBOT_MOUNT]}
        diversity = {**ROBOT_MOUNT, 'url_path': 'obs://example-bucket/diversity-robot/'}
        group['parallel_group'].append({'id': 'diversity', 'operator': '数据集多样性评测-LeRobot',
                                        'params': {'inputs': [diversity]}})
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'choices.json'
            source.write_text(json.dumps(raw), encoding='utf-8')
            command = [sys.executable, str(MONITOR.parent / 'custom_pipeline.py')]
            for arguments in [['check'], ['export', '--output-dir', str(root / 'export')]]:
                result = subprocess.run(command + arguments + ['--input', str(source)], capture_output=True, text=True, encoding='utf-8')
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertEqual(json.loads(result.stdout)['status'], 'STRUCTURE_VALID')
            saved = read_json_object(root / 'export' / 'pipeline.draft.json')
            plan = normalize_plan(saved)
            preview = (root / 'export' / 'pipeline-preview.md').read_text(encoding='utf-8')
            yaml = (root / 'export' / 'pipeline.yaml').read_text(encoding='utf-8')
            for mid, mount in [('quality', ROBOT_MOUNT), ('diversity', diversity)]:
                self.assertEqual(spec_for(plan, 'evaluation', mid)['params']['inputs'], [mount])
                self.assertIn('| ' + mid + ' | ROBOT_CONFIG_PATH → ' + mount['url_path'] + ' |', preview)
                self.assertIn(mount['url_path'], yaml)
            self.assertNotIn('robot_config', yaml)

    def test_parallel_member_without_mounts_uses_operator_default_config(self):
        raw = self.choices()
        group = raw['pipeline']['stages'][-1]
        group['parallel_group'][0]['params'] = {'inputs': [ROBOT_MOUNT]}
        group['parallel_group'].append({'id': 'diversity', 'operator': '数据集多样性评测-LeRobot'})
        draft, issues, warnings = validate_pipeline(raw)
        self.assertEqual(issues, [])
        self.assertNotIn('inputs', spec_for(normalize_plan(draft), 'evaluation', 'diversity').get('params', {}))
        self.assertIn('| diversity | 未挂载（使用算子内置/默认配置） |', preview_pipeline(draft, issues, warnings))

    def test_standalone_and_parallel_evaluation_export_without_mounts(self):
        for grouped in (False, True):
            with self.subTest(grouped=grouped), tempfile.TemporaryDirectory() as directory:
                raw = self.choices()
                stage = raw['pipeline']['stages'][-1]
                if not grouped:
                    member = stage.pop('parallel_group')[0]
                    stage.update(kind='eval', operator=member['operator'], id='quality')
                draft, issues, warnings = validate_pipeline(raw)
                self.assertEqual(issues, [])
                export_pipeline(draft, issues, warnings, directory)
                yaml = (Path(directory) / 'pipeline.yaml').read_text(encoding='utf-8-sig')
                self.assertNotIn('robot_config', yaml)
                self.assertNotIn('ROBOT_CONFIG_PATH', yaml)
                preview = (Path(directory) / 'pipeline-preview.md').read_text(encoding='utf-8')
                self.assertIn('| quality | 未挂载（使用算子内置/默认配置） |', preview)

    def test_removed_robot_config_is_rejected_with_mount_guidance(self):
        cases = {'pipeline.stages[2].robot_config': lambda stage: stage.update(robot_config='obs://example-bucket/robot/'),
                 'pipeline.stages[2].parallel_group[0].robot_config':
                     lambda stage: stage['parallel_group'][0].update(robot_config='obs://example-bucket/robot/')}
        for path, mutate in cases.items():
            with self.subTest(path=path):
                raw = self.choices()
                mutate(raw['pipeline']['stages'][-1])
                issues = validate_pipeline(raw)[1]
                self.assertEqual([i['path'] for i in issues], [path])
                self.assertIn('params.inputs', issues[0]['message'])
        raw = self.choices()
        member = raw['pipeline']['stages'][-1].pop('parallel_group')[0]
        raw['pipeline']['stages'][-1].update(kind='eval', operator=member['operator'], robot_config='obs://example-bucket/robot/')
        self.assertEqual([i['path'] for i in validate_pipeline(raw)[1]], ['pipeline.stages[2].robot_config'])

    def test_invalid_eval_mount_path_is_reported(self):
        for value in (None, '', 'C:/robot/', 'https://example/robot/'):
            with self.subTest(value=value):
                raw = self.choices()
                raw['pipeline']['stages'][-1]['parallel_group'][0]['params'] = {'inputs': [{**ROBOT_MOUNT, 'url_path': value}]}
                issues = validate_pipeline(raw)[1]
                self.assertTrue(any(i['path'].endswith('.params.inputs[0].url_path') for i in issues), issues)

    def test_cli_incomplete_draft_and_invalid_export(self):
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory); source = directory / 'choices.json'
            raw = self.choices(); raw['pipeline']['stages'][-1]['parallel_group'][0].pop('operator')
            source.write_text(json.dumps(raw))
            command = [sys.executable, str(MONITOR.parent / 'custom_pipeline.py')]
            checked = subprocess.run(command + ['check', '--input', str(source)], capture_output=True, text=True)
            self.assertEqual(checked.returncode, 2)
            out = directory / 'draft'
            exported = subprocess.run(command + ['export', '--input', str(source), '--output-dir', str(out), '--allow-incomplete'], capture_output=True, text=True)
            self.assertEqual(exported.returncode, 0, exported.stdout)
            self.assertTrue((out / 'pipeline.yaml').read_text(encoding='utf-8-sig').startswith('# DRAFT'))
            self.assertFalse((directory / 'pipeline-runs').exists())
            raw['pipeline']['stages'][0]['depends_on'] = ['evaluation']; source.write_text(json.dumps(raw))
            invalid = subprocess.run(command + ['export', '--input', str(source), '--output-dir', str(directory / 'invalid'), '--allow-incomplete'], capture_output=True, text=True)
            self.assertEqual(invalid.returncode, 1)
            self.assertFalse((directory / 'invalid').exists())


class MonitorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = Store(self.temp.name)
        demo_runs(self.store)
        self.client = DemoSDK()
        self.client.statuses['demo-clean-finished'] = 'SUCCEEDED'
        self.monitor = Monitor(self.store, self.client, demo=True)
        self.monitor.refresh_all(wait=True)
        self.run = 'demo-awaiting-1002'

    def tearDown(self):
        self.monitor.close()
        self.temp.cleanup()

    def retry_body(self):
        draft = self.monitor.retry_draft(self.run, 'cleaning')
        return {'type': 'retry', 'stage': 'cleaning', 'member': None,
                'expected_task_id': 'demo-clean-1', 'confirmed': True, 'draft_id': draft['draft_id'],
                'overrides': {'worker_spec': {'cpu': 4, 'memory': 16, 'gpu': 0, 'npu': 0}}}

    def test_sdk_payload_and_create_result(self):
        self.assertEqual(unwrap({'payload': {'item': {'id': 'id-1'}}})['id'], 'id-1')
        self.assertEqual(created_task_result({'payload': {'id': 'new-1'}})['task_id'], 'new-1')
        for value in ({}, {'id': None}, {'id': 'None'}, {'id': '../bad'}, 'not json'):
            with self.subTest(value=value), self.assertRaises(UncertainSubmission):
                created_task_result(value)

    def test_plan_dependencies_cycle_and_parallel(self):
        plan = normalize_plan({'stages': [{'id': 'a'}, {'id': 'b', 'parallel_group': [{'id': 'x'}, {'id': 'y'}]}]})
        self.assertEqual(next(s for s in plan['stages'] if s['id'] == 'a')['depends_on'], ['upload'])
        with self.assertRaises(StateError):
            normalize_plan({'monitor_bookends': False, 'stages': [{'id': 'a', 'depends_on': ['b']}, {'id': 'b', 'depends_on': ['a']}]})
        with self.assertRaises(StateError):
            normalize_plan({'stages': [{'id': 'a', 'parallel_group': [{'id': 'x'}, {'id': 'x'}]}]})

    def test_path_and_membership_guards(self):
        with self.assertRaises(StateError):
            self.store.read('../outside')
        with self.assertRaises(StateError):
            self.monitor.task_detail(self.run, 'not-in-run')
        with self.assertRaises(StateError):
            self.monitor.log_content(self.run, 'demo-clean-1', 'fake.log', '/tmp/secret')
        with self.assertRaises(StateError):
            self.monitor.frames('demo-completed-1003', 'demo-quality')

    def test_upload_preparation_matches_input_source(self):
        asset = {'source_type': 'asset', 'asset_id': 'existing-asset', 'version_id': 'v3'}
        for inputs, skipped in [([], False), ([{'source_type': 'local', 'local_path': '/tmp/raw'}], False),
                                ([{'source_type': 'obs', 'obs_path': 'obs://example/raw/'}], False),
                                ([{'source_type': 'asset', 'asset_id': 'unresolved-version'}], False),
                                ([{**asset, 'id': 'existing'}, {'id': 'extra', 'source_type': 'obs', 'obs_path': 'obs://example/extra/'}], False),
                                ([asset], True)]:
            with self.subTest(inputs=inputs):
                binding = ['input:' + inputs[0].get('id', 'default')] if inputs else None
                stage = {'id': 'process', **({'input_from': binding} if binding else {})}
                plan = normalize_plan({'inputs': inputs, 'stages': [stage]})
                self.assertEqual(next(s for s in plan['stages'] if s['id'] == 'upload')['not_applicable'], skipped)
        self.store.init('existing-input', {'inputs': [asset], 'stages': [{'id': 'process'}]})
        upload = self.store.read('existing-input')['stages']['upload']
        self.assertEqual(upload['status'], 'SKIPPED')
        self.assertTrue(upload['not_applicable'])
        self.assertIsNone(upload['task_id'])
        self.assertEqual(self.monitor.node('existing-input', 'upload')['display_status'], 'SKIPPED')
        self.assertFalse(self.monitor.node('existing-input', 'upload')['actions']['retry'])
        self.assertEqual(self.monitor.node('existing-input', 'process')['display_status'], 'READY')
        self.assertEqual(self.client.sequence, 0)

    def test_status_and_service_lookup_return_contracts(self):
        samples = [(None, 0.0), ('invalid', 0.0), (1700000000, 1700000000.0),
                   (1700000000000, 1700000000.0), ('2023-11-14T22:13:20Z', 1700000000.0)]
        for value, expected in samples:
            with self.subTest(value=value):
                actual = timestamp(value)
                self.assertIsInstance(actual, float)
                self.assertEqual(actual, expected)
        self.assertEqual(self.monitor.node(self.run, 'missing-stage'), {})
        metadata = self.store.root / '.monitor.json'
        self.assertEqual(existing(self.store.root), {})
        for value in [[], {'port': 0}, {'port': 'invalid'}]:
            atomic_json(metadata, value)
            self.assertEqual(existing(self.store.root), {})
        valid = {'port': 8765, 'token': 'test-local-token', 'pid': 123}
        atomic_json(metadata, valid)
        for response, expected in [('{"ok": true}', {**valid, 'source_revision': None}), ('[]', {}), ('{"ok": false}', {})]:
            with patch('server.urlopen', return_value=io.StringIO(response)):
                self.assertEqual(existing(self.store.root), expected)

    def test_checkpoint_and_task_records_require_json_objects(self):
        run = 'json-object-contract'
        self.store.init(run, {'stages': [{'id': 'process'}]})
        directory = self.store.directory(run)
        for filename, read in [('state.json', lambda: self.store.read(run)),
                               ('plan.json', lambda: self.store.plan(run)),
                               ('tasks/invalid-task.json', lambda: self.monitor.record(run, {}, 'invalid-task'))]:
            with self.subTest(filename=filename):
                path = directory / filename
                atomic_json(path, [])
                with self.assertRaises(StateError):
                    read()
                atomic_json(path, {'valid': True})
                self.assertEqual(read_json_object(path), {'valid': True})

    def test_omitted_upload_does_not_block_finish_or_create_warning(self):
        run = 'existing-input-finish'
        self.store.init(run, {'inputs': [{'source_type': 'asset', 'asset_id': 'existing', 'version_id': 'v1'}],
                              'stages': [{'id': 'process'}]})
        def complete(state):
            state['stages']['process']['status'] = 'SUCCEEDED'
            state['stages']['output']['status'] = 'SUCCEEDED'
            state['output'].update(target_path='obs://example/result/', target_asset_id='result', target_version_id='v2')
        self.store.mutate(run, complete)
        command = [sys.executable, str(MONITOR.parent / 'pipeline_state.py'), '--runs-root', self.temp.name, '--run', run, 'finish']
        result = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.store.read(run)['status'], 'SUCCEEDED')
        warnings = self.monitor.summary(run).split('## 告警', 1)[1].split('## 已确认', 1)[0]
        self.assertNotIn('上传注册', warnings)

    def test_redaction_nested_json_strings(self):
        raw = {'envs': '[{"key":"HUAWEI_CLOUD_AK","value":"do-not-display"},{"key":"robot","value":"a2d"}]',
               'nested': {'password': 'hidden'}, 'task_name': 'valid-task'}
        masked = json.dumps(redact(raw))
        self.assertNotIn('do-not-display', masked); self.assertNotIn('hidden', masked)
        self.assertIn('a2d', masked); self.assertIn('valid-task', masked)
        self.assertNotIn('hidden-default', json.dumps(redact({'name': 'API_SECRET', 'default': 'hidden-default'})))

    def test_signed_report_urls_remain_usable_but_errors_are_masked(self):
        url = 'https://obs.example.com/report?security_token=signed-value'
        value = browser_data({'url': url, 'error': 'PASSWORD=hidden-value'})
        self.assertEqual(value['url'], url)
        self.assertNotIn('hidden-value', value['error'])

    def test_retry_fresh_config_and_attempt_history(self):
        body = self.retry_body()
        draft = self.monitor.drafts[body['draft_id']]
        self.assertEqual(draft['config']['algo_id'], 'demo-algo-current')
        result = self.monitor.action(self.run, body)
        task = result['state']['stages']['cleaning']
        self.assertNotEqual(task['task_id'], 'demo-clean-1')
        self.assertEqual(task['attempts'][0]['task_id'], 'demo-clean-1')
        self.assertIsNone(result['state']['pending_action'])
        self.assertIsNone(result['state']['awaiting_decision'])
        config = self.monitor.record(self.run, {'stage': 'cleaning', 'member': None}, task['task_id'])['task_config']
        self.assertEqual(config['worker_spec']['memory'], 16)

    def test_public_pool_retry_removes_dedicated_fields_for_failed_and_deleted_tasks(self):
        cases = [(self.run, 'cleaning', None, 'demo-clean-1', 'FAILED'),
                 ('demo-completed-1003', 'evaluation', 'diversity-eval', 'demo-diversity', 'DELETED')]
        for run, sid, mid, tid, status in cases:
            with self.subTest(status=status, stage=sid):
                self.client.statuses[tid] = status
                self.monitor.refresh_task(run, sid, mid, stage_ref(self.store.read(run), sid, mid), force=True)
                path = self.store.directory(run) / 'tasks' / (tid + '.json')
                record = read_json_object(path)
                record['task_config'].update(resource_pool_type='PUBLIC_POOL', resource_id='stale-id', dedicated_pool_name='stale-name')
                atomic_json(path, record)
                before = path.read_bytes()
                draft = self.monitor.retry_draft(run, sid, mid)
                self.assertEqual(draft['previous_config']['resource_id'], 'stale-id')
                for field in ('resource_id', 'dedicated_pool_name'):
                    self.assertNotIn(field, draft['config'])
                body = {'type': 'retry', 'stage': sid, 'member': mid, 'expected_task_id': tid,
                        'confirmed': True, 'draft_id': draft['draft_id'],
                        'overrides': {'resource_pool_type': 'PUBLIC_POOL', 'resource_id': '', 'dedicated_pool_name': ''}}
                with patch.object(self.client, 'create_task', wraps=self.client.create_task) as create:
                    self.monitor.action(run, body)
                config = create.call_args.args[2]
                self.assertEqual(config['resource_pool_type'], 'PUBLIC_POOL')
                for field in ('resource_id', 'dedicated_pool_name'):
                    self.assertNotIn(field, config)
                self.assertEqual(path.read_bytes(), before)

    def test_retry_switches_from_dedicated_to_public_without_reusing_pool_fields(self):
        path = self.store.directory(self.run) / 'tasks' / 'demo-clean-1.json'
        record = read_json_object(path)
        record['task_config'].update(resource_pool_type='DEDICATED_POOL', resource_id='original-id', dedicated_pool_name='original-pool')
        atomic_json(path, record)
        body = self.retry_body()
        self.assertEqual(self.monitor.drafts[body['draft_id']]['config']['resource_id'], 'original-id')
        body['overrides']['resource_pool_type'] = 'PUBLIC_POOL'
        with patch.object(self.client, 'create_task', wraps=self.client.create_task) as create:
            self.monitor.action(self.run, body)
        config = create.call_args.args[2]
        self.assertNotIn('resource_id', config)
        self.assertNotIn('dedicated_pool_name', config)
        self.assertEqual(read_json_object(path), record)

    def test_dedicated_pool_retry_rejects_missing_or_blank_fields_before_submission(self):
        body = self.retry_body()
        before = self.store.read(self.run)
        invalid = [{}, {'resource_id': 'real-id'}, {'dedicated_pool_name': 'real-pool'},
                   {'resource_id': '   ', 'dedicated_pool_name': 'real-pool'},
                   {'resource_id': 'real-id', 'dedicated_pool_name': None},
                   {'resource_id': 42, 'dedicated_pool_name': 'real-pool'}]
        for fields in invalid:
            body['overrides'] = {'resource_pool_type': 'DEDICATED_POOL', **fields}
            with self.subTest(fields=fields), patch.object(self.client, 'create_task') as create:
                with self.assertRaisesRegex(StateError, '专属池需要有效的'):
                    self.monitor.action(self.run, body)
                create.assert_not_called()
            self.assertEqual(self.store.read(self.run), before)
        body['overrides'] = {'resource_pool_type': 'DEDICATED_POOL',
                             'resource_id': ' real-id ', 'dedicated_pool_name': ' real-pool '}
        with patch.object(self.client, 'create_task', wraps=self.client.create_task) as create:
            self.monitor.action(self.run, body)
        self.assertEqual(create.call_args.args[2]['resource_id'], 'real-id')
        self.assertEqual(create.call_args.args[2]['dedicated_pool_name'], 'real-pool')

    def test_retry_short_names_change_per_draft_and_clear_old_artifact_name(self):
        self.store.mutate(self.run, lambda state: state['stages']['cleaning'].update(output_name='old-cleaned'))
        before = self.store.read(self.run)
        record_before = self.monitor.record(self.run, {'stage': 'cleaning'}, 'demo-clean-1')
        clock = Mock()
        clock.now.return_value.strftime.return_value = '1018102430'
        with patch.object(platform_utils, 'datetime', clock), patch.object(platform_utils, '_NAMING_STAMP', ''), patch.object(platform_utils, '_GENERATED_NAMES', set()):
            first = self.monitor.retry_draft(self.run, 'cleaning')
            second = self.monitor.retry_draft(self.run, 'cleaning')
        self.assertNotEqual(first['name'], second['name'])
        self.assertNotEqual(first['config']['output_name'], second['config']['output_name'])
        self.assertLessEqual(len(second['name']), 64)
        self.assertLessEqual(len(second['config']['output_name']), 64)
        self.assertEqual(first['name'], 'sim-teleop-cleaning-cleaning-1018102430')
        self.assertEqual(first['config']['output_name'], first['name'])
        self.assertEqual(second['name'], first['name'] + '-2')
        self.assertEqual(second['config']['output_name'], second['name'])
        self.assertEqual(self.store.read(self.run), before)
        self.assertEqual(self.monitor.record(self.run, {'stage': 'cleaning'}, 'demo-clean-1'), record_before)
        body = {'type': 'retry', 'stage': 'cleaning', 'expected_task_id': 'demo-clean-1',
                'confirmed': True, 'draft_id': second['draft_id'], 'overrides': {}}
        result = self.monitor.action(self.run, body)
        task = result['state']['stages']['cleaning']
        self.assertNotIn('output_name', task)
        self.assertEqual(task['attempts'][-1]['output_name'], 'old-cleaned')
        record = self.monitor.record(self.run, {'stage': 'cleaning'}, task['task_id'])
        self.assertEqual(record['task_config']['output_name'], second['config']['output_name'])

    def test_retry_explicit_output_obeys_complete_64_character_limit(self):
        body = self.retry_body()
        body['overrides']['output_name'] = 'n' * 65
        with self.assertRaisesRegex(StateError, '2–64'):
            self.monitor.action(self.run, body)
        self.assertEqual(self.client.sequence, 0)
        body['overrides']['output_name'] = 'n' * 64
        result = self.monitor.action(self.run, body)
        task = result['state']['stages']['cleaning']
        record = self.monitor.record(self.run, {'stage': 'cleaning'}, task['task_id'])
        self.assertEqual(record['task_config']['output_name'], 'n' * 64)
        self.assertEqual(self.client.sequence, 1)

    def test_concurrent_retry_only_creates_one(self):
        one = self.retry_body(); two = self.retry_body()
        def attempt(body):
            try:
                self.monitor.action(self.run, body); return 'ok'
            except Conflict:
                return 'conflict'
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(attempt, [one, two]))
        self.assertEqual(sorted(results), ['conflict', 'ok'])
        self.assertEqual(self.client.sequence, 1)

    def test_agent_cas_conflict(self):
        state = self.store.read(self.run)
        self.store.set_task(self.run, 'cleaning', None, 'demo-clean-1', 'agent-new-task', {'output_name': 'new'}, 'new-task')
        with self.assertRaises(Conflict):
            self.store.mutate(self.run, lambda s: None, stage='cleaning', expected_task='demo-clean-1')
        with self.assertRaises(Conflict):
            self.store.mutate(self.run, lambda s: None, expected_version=state['version'])

    def test_terminal_reservation_and_reconciliation(self):
        self.store.mutate(self.run, lambda state: state['stages']['cleaning'].update(output_name='old-output'))
        body = self.retry_body()
        path = Path(self.temp.name) / 'confirmed-config.json'
        atomic_json(path, self.monitor.record(self.run, {'stage': 'cleaning'}, 'demo-clean-1')['task_config'])
        base = [sys.executable, str(MONITOR.parent / 'pipeline_state.py'), '--runs-root', self.temp.name, '--run', self.run]
        reserve = subprocess.run(base + ['reserve-task', '--stage', 'cleaning', '--expect-task', 'demo-clean-1',
                                        '--name', 'terminal-confirmed-task', '--config', str(path)], capture_output=True)
        self.assertEqual(reserve.returncode, 0, reserve.stderr)
        with self.assertRaises(Conflict):
            self.monitor.action(self.run, body)
        action_id = self.store.read(self.run)['pending_action']['id']
        done = subprocess.run(base + ['resolve-action', '--action-id', action_id, '--task-id', 'terminal-created-task'], capture_output=True)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(self.store.read(self.run)['stages']['cleaning']['task_id'], 'terminal-created-task')
        self.assertNotIn('output_name', self.store.read(self.run)['stages']['cleaning'])
        self.assertEqual(self.store.read(self.run)['stages']['cleaning']['attempts'][-1]['output_name'], 'old-output')
        self.assertIsNone(self.store.read(self.run)['pending_action'])
        self.assertEqual(self.client.sequence, 0)

    def test_parallel_members_reserve_serially_without_waiting_for_completion(self):
        run = 'parallel-submit'
        self.store.init(run, {'monitor_bookends': False, 'stages': [{'id': 'evaluation',
                         'parallel_group': [{'id': 'quality-eval'}, {'id': 'diversity-eval'}]}]})
        path = Path(self.temp.name) / 'eval-config.json'
        atomic_json(path, {'algo_name': 'test-evaluation', **task_input_config('eval')})
        base = [sys.executable, str(MONITOR.parent / 'pipeline_state.py'), '--runs-root', self.temp.name, '--run', run]
        def reserve(member):
            return subprocess.run(base + ['reserve-task', '--stage', 'evaluation', '--member', member,
                                  '--expect-task', 'none', '--name', member, '--config', str(path)],
                                  capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(reserve('quality-eval').returncode, 0)
        first = self.store.read(run)
        rejected = reserve('diversity-eval')
        self.assertEqual(rejected.returncode, 3)
        self.assertIn('quality-eval', rejected.stderr)
        self.assertIn(first['pending_action']['id'], rejected.stderr)
        self.assertNotIn('管线已终止', rejected.stderr)
        self.assertEqual(self.store.read(run), first)
        resolved = subprocess.run(base + ['resolve-action', '--action-id', first['pending_action']['id'],
                                  '--task-id', 'quality-task'], capture_output=True)
        self.assertEqual(resolved.returncode, 0, resolved.stderr)
        self.assertEqual(reserve('diversity-eval').returncode, 0)
        self.assertEqual(self.store.read(run)['stages']['evaluation']['members']['quality-eval']['status'], 'PENDING')
        self.store.mutate(run, lambda state: state.update(status='TERMINATED', pending_action=None))
        terminated = reserve('diversity-eval')
        self.assertEqual(terminated.returncode, 3)
        self.assertIn('TERMINATED', terminated.stderr)
        self.assertNotIn('已有未完成', terminated.stderr)

    def test_unified_task_graph_adapts_both_syntaxes_and_preserves_member_config(self):
        for grouped in (False, True):
            with self.subTest(grouped=grouped):
                members = [{'id': 'A', 'kind': 'eval', 'params': {'envs': {'robot': 'member-A'}}},
                           {'id': 'B', 'kind': 'eval', 'params': {'inputs': [{**ROBOT_MOUNT, 'url_path': 'obs://example/B/'}]}}]
                stages = [{'id': 'upstream', 'kind': 'proc'}]
                if grouped:
                    stages.append({'id': 'checks', 'depends_on': ['upstream'], 'parallel_group': members})
                    stages.append({'id': 'join', 'kind': 'manual', 'depends_on': ['checks']})
                else:
                    stages.extend([{**member, 'depends_on': ['upstream']} for member in members])
                    stages.append({'id': 'join', 'kind': 'manual', 'depends_on': ['A', 'B']})
                run = 'normalized-' + str(grouped)
                self.store.init(run, {'monitor_bookends': False, 'stages': stages})
                self.store.mutate(run, lambda state: state['stages']['upstream'].update(status='SUCCEEDED'))
                plan = self.store.plan(run)
                before = copy.deepcopy(plan)
                specs = task_specs(plan)
                self.assertEqual(plan, before)
                self.assertTrue(all('parallel_group' not in spec for spec in specs))
                next(spec for spec in specs if spec['id'] == 'A')['params']['envs']['robot'] = 'changed-copy'
                self.assertEqual(plan, before)
                result = execution_frontier(plan, self.store.read(run))
                self.assertEqual(result['action'], 'submit')
                self.assertTrue(all('robot_config' not in item for item in result['ready']))
                self.assertEqual(next(spec for spec in specs if spec['id'] == 'B')['params']['inputs'][0]['url_path'], 'obs://example/B/')
                expected = ['checks/A', 'checks/B'] if grouped else ['A', 'B']
                self.assertEqual([item['key'] for item in result['ready']], expected)
                self.assertEqual(next(spec for spec in specs if spec['key'] == 'join')['dependency_keys'], expected)
                web_ready = [node['key'] for node in self.monitor.snapshot(run)['nodes'] if node['kind'] == 'eval'
                             and node['display_status'] == 'READY']
                self.assertEqual(web_ready, expected)

    def test_ready_tasks_cli_prioritizes_unsubmitted_sibling_over_polling_active_task(self):
        run = 'ready-siblings'
        self.store.init(run, {'monitor_bookends': False, 'stages': [{'id': 'A', 'depends_on': []},
                              {'id': 'B', 'depends_on': []}, {'id': 'join', 'kind': 'manual', 'depends_on': ['A', 'B']}]})
        base = [sys.executable, str(MONITOR.parent / 'pipeline_state.py'), '--runs-root', self.temp.name, '--run', run]
        def frontier():
            before = {path: path.read_bytes() for path in self.store.directory(run).rglob('*') if path.is_file()}
            result = subprocess.run(base + ['ready-tasks'], capture_output=True, text=True, encoding='utf-8')
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(all(path.read_bytes() == value for path, value in before.items()))
            return json.loads(result.stdout)
        self.assertEqual([item['key'] for item in frontier()['ready']], ['A', 'B'])
        source = Path(self.temp.name) / 'ready-config.json'
        atomic_json(source, {'algo_name': 'example', **task_input_config()})
        for sid in ('A', 'B'):
            reserved = subprocess.run(base + ['reserve-task', '--stage', sid, '--expect-task', 'none',
                                              '--name', sid, '--config', str(source)], capture_output=True)
            self.assertEqual(reserved.returncode, 0, reserved.stderr)
            pending = frontier()
            self.assertEqual(pending['action'], 'reconcile')
            self.assertEqual(pending['ready'], [])
            reconciled = subprocess.run(base + ['resolve-action', '--action-id', pending['pending_action']['id'],
                                                '--task-id', 'task-' + sid], capture_output=True)
            self.assertEqual(reconciled.returncode, 0, reconciled.stderr)
            result = frontier()
            if sid == 'A':
                self.assertEqual(result['action'], 'submit')
                self.assertEqual([item['key'] for item in result['ready']], ['B'])
                self.assertEqual(result['active'][0]['status'], 'PENDING')
            else:
                self.assertEqual(result['action'], 'poll')
                self.assertEqual([item['key'] for item in result['active']], ['A', 'B'])
        self.assertEqual(self.monitor.node(run, 'join')['display_status'], 'IDLE')

    def test_unified_dependency_gate_handles_group_join_failure_and_skips(self):
        self.assertFalse(dependencies_ready(['missing'], {}))
        for fail_fast in (False, True):
            for status in ('RUNNING', 'SUCCEEDED', 'FAILED', 'DELETED', 'SKIPPED'):
                with self.subTest(fail_fast=fail_fast, status=status):
                    expected = status in {'SUCCEEDED', 'SKIPPED'} or not fail_fast and status in {'FAILED', 'DELETED'}
                    self.assertEqual(dependencies_ready(['A'], {'A': {'status': status, 'fail_fast': fail_fast}}), expected)
                    self.assertEqual(dependencies_ready(['A'], {'A': {'display_status': status, 'raw_status': status,
                                                                     'fail_fast': fail_fast}}), expected)
        run = 'ready-join'
        self.store.init(run, {'monitor_bookends': False, 'inputs': [{'source_type': 'asset', 'asset_id': 'input',
                                                                  'version_id': 'v1', 'obs_path': 'obs://example/input/'}], 'stages': [
            {'id': 'checks', 'depends_on': [], 'parallel_group': [{'id': 'A'}, {'id': 'B'}]},
            {'id': 'next', 'depends_on': ['checks'], 'input_from': ['input:default']}]})
        def progressed(state):
            members = state['stages']['checks']['members']
            members['A'].update(task_id='task-A', status='SUCCEEDED')
            members['B'].update(task_id='task-B', status='RUNNING')
        state = self.store.mutate(run, progressed)
        self.assertEqual(execution_frontier(self.store.plan(run), state)['action'], 'poll')
        self.assertEqual(self.monitor.node(run, 'next')['display_status'], 'IDLE')
        state = self.store.mutate(run, lambda current: current['stages']['checks']['members']['B'].update(status='FAILED'))
        result = execution_frontier(self.store.plan(run), state)
        self.assertEqual(result['action'], 'submit')
        self.assertEqual([item['key'] for item in result['ready']], ['next'])
        self.assertEqual(self.monitor.node(run, 'next')['display_status'], 'READY')

    def test_ready_frontier_does_not_resubmit_failures_or_override_run_decisions(self):
        self.store.init('frontier-guards', {'monitor_bookends': False, 'stages': [{'id': key, 'depends_on': []}
                                                                                 for key in ('A', 'B', 'C')]})
        plan = self.store.plan('frontier-guards')
        state = self.store.read('frontier-guards')
        state['stages']['A'].update(status='FAILED', task_id='failed-task')
        state['stages']['B'].update(status='SKIPPED', skipped=True)
        self.assertEqual([item['key'] for item in execution_frontier(plan, state)['ready']], ['C'])
        state['awaiting_decision'] = {'stage': 'C', 'member': None, 'kind': 'skip'}
        self.assertEqual(execution_frontier(plan, state)['action'], 'decide')
        state['awaiting_decision'] = None
        for fields, action in [({'status': 'TERMINATED'}, 'stopped'), ({'schema_version': 1}, 'readonly'),
                               ({'pending_action': {'id': 'uncertain-submit', 'stage': 'A'}}, 'reconcile')]:
            guarded = {**state, **fields}
            before = copy.deepcopy(guarded)
            result = execution_frontier(plan, guarded)
            self.assertEqual(result['action'], action)
            self.assertEqual(result['ready'], [])
            self.assertEqual(guarded, before)

    def test_result_field_error_lists_unknown_and_legal_fields_without_mutation(self):
        path = Path(self.temp.name) / 'output-result.json'
        atomic_json(path, {'status': 'SUCCEEDED', 'target_asset_name': 'must-not-be-mapped'})
        base = [sys.executable, str(MONITOR.parent / 'pipeline_state.py'), '--runs-root', self.temp.name,
                '--run', self.run, 'set-result', '--stage', 'output', '--expect-task', 'none', '--result', str(path)]
        before = self.store.read(self.run)
        rejected = subprocess.run(base, capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(rejected.returncode, 1)
        self.assertIn('target_asset_name', rejected.stderr)
        for field in RESULT_FIELDS:
            self.assertIn(field, rejected.stderr)
        self.assertEqual(self.store.read(self.run), before)
        atomic_json(path, {'status': 'SUCCEEDED', 'output_name': 'verified-output',
                          'target_path': 'obs://example/final/', 'target_asset_id': 'final', 'target_version_id': 'v1'})
        accepted = subprocess.run(base, capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(accepted.returncode, 0, accepted.stderr)
        self.assertEqual(self.store.read(self.run)['output']['output_name'], 'verified-output')
        self.assertNotIn('target_asset_name', self.store.read(self.run)['output'])

    def test_retry_accepts_verified_draft_and_release_but_rejects_changed_or_unready_inputs(self):
        original = self.client._call
        version = {'status': 'DRAFT', 'url': 'obs://demo-bucket/converted/'}
        def query(service, method, *args, **kwargs):
            if method == 'show_asset_version':
                return dict(version)
            return original(service, method, *args, **kwargs)
        with patch.object(self.client, '_call', side_effect=query) as calls:
            for status in ('DRAFT', 'RELEASE'):
                version['status'] = status
                self.monitor.retry_draft(self.run, 'cleaning')
            for status in ('CREATING', 'ARCHIVE', None):
                version['status'] = status
                with self.subTest(status=status), self.assertRaisesRegex(StateError, '尚未确认可用'):
                    self.monitor.retry_draft(self.run, 'cleaning')
            version.update(status='DRAFT', url='obs://example/changed/')
            with self.assertRaisesRegex(StateError, '路径已变化'):
                self.monitor.retry_draft(self.run, 'cleaning')
            version['url'] = 'obs://demo-bucket/converted/'
            result = self.monitor.action(self.run, self.retry_body())
            self.assertIsNone(result['state']['pending_action'])
            self.assertTrue(any(call.args[:2] == ('dataset', 'create_task') for call in calls.call_args_list))
            self.assertFalse(any(call.args[:2] == ('asset', 'update_asset_version') for call in calls.call_args_list))

    def prepare_merge_run(self):
        raw = merge_choices()
        draft, issues, _ = validate_pipeline(raw)
        self.assertEqual(issues, [])
        self.store.init('multi-input', draft)
        def complete(state):
            for key in ('A', 'B'):
                state['stages'][key].update(status='SUCCEEDED', target_path='obs://example/' + key + '/',
                                            target_asset_id='output-' + key, target_version_id='v2', output_name='data-' + key)
        self.store.mutate('multi-input', complete)
        return self.store.plan('multi-input'), self.store.read('multi-input')

    def test_ordered_handoff_and_cli_are_readonly_and_wait_for_both_producers(self):
        plan, state = self.prepare_merge_run()
        resolved = dataset_inputs(plan, state, 'C')
        self.assertEqual([item['asset_id'] for item in resolved['datasets']], ['output-B', 'output-A'])
        self.assertEqual(json.loads(resolved['task_config']['dataset_configs']), resolved['datasets'])
        self.assertEqual(self.monitor.node('multi-input', 'C')['input_from'], ['B', 'A'])
        self.assertEqual(self.monitor.node('multi-input', 'C')['display_status'], 'READY')
        args = [sys.executable, str(MONITOR.parent / 'pipeline_state.py'), '--runs-root', self.temp.name,
                '--run', 'multi-input', 'resolve-inputs', '--stage', 'C']
        called = subprocess.run(args, capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(called.returncode, 0, called.stderr)
        self.assertEqual(json.loads(called.stdout), resolved)
        self.assertEqual(self.store.read('multi-input'), state)
        self.store.mutate('multi-input', lambda current: current['stages']['B'].update(status='RUNNING'))
        self.assertEqual(self.monitor.node('multi-input', 'C')['display_status'], 'IDLE')
        with self.assertRaisesRegex(StateError, '尚未完成'):
            dataset_inputs(plan, self.store.read('multi-input'), 'C')
        self.store.mutate('multi-input', lambda current: current['stages']['B'].update(status='SUCCEEDED', skipped=True))
        with self.assertRaisesRegex(StateError, '成功的处理步骤'):
            dataset_inputs(plan, self.store.read('multi-input'), 'C')

    def test_initial_bindings_and_supplied_metadata_do_not_replace_confirmed_assets(self):
        plan, state = self.prepare_merge_run()
        resolved = dataset_inputs(plan, state, 'B')
        self.assertEqual([item['asset_id'] for item in resolved['datasets']], ['asset-right'])
        before = copy.deepcopy(state)
        for supplied in ({'B': {}}, {'right': []}, {'right': {'version_id': 'v2'}},
                         {'right': {'target_path': 'obs://example/unapproved/'}},
                         {'right': {'obs_path': 'obs://example/changed/'}}):
            with self.subTest(supplied=supplied), self.assertRaises(StateError):
                dataset_inputs(plan, state, 'B', supplied)
        self.assertEqual(state, before)
        state['inputs'][1].pop('asset_name')
        with self.assertRaisesRegex(StateError, '缺少资产'):
            dataset_inputs(plan, state, 'B')
        values = {'right': {'asset_name': 'verified-right'}}
        self.assertEqual(dataset_inputs(plan, state, 'B', values)['datasets'][0]['asset_name'], 'verified-right')
        state['inputs'][1] = {'id': 'right', 'source_type': 'obs', 'obs_path': 'obs://example/raw-right/'}
        with self.assertRaisesRegex(StateError, '缺少资产'):
            dataset_inputs(plan, state, 'B')
        supplied = {'right': {'asset_id': 'new-right', 'version_id': 'v3', 'asset_name': 'registered-right', 'obs_path': 'obs://example/registered-right/'}}
        self.assertEqual(dataset_inputs(plan, state, 'B', supplied)['datasets'][0]['asset_id'], 'new-right')

    def test_eval_handoff_and_cli_preserve_exact_version_for_single_and_grouped_steps(self):
        for grouped in (False, True):
            with self.subTest(grouped=grouped):
                run = 'eval-wire-version-' + str(grouped)
                stage = {'id': 'checks', 'kind': 'eval'}
                if grouped:
                    stage = {'id': 'checks', 'parallel_group': [{'id': 'quality'}, {'id': 'diversity'}]}
                state = self.store.init(run, {'inputs': [{'source_type': 'asset', 'asset_id': 'input', 'version_id': 'exact-v2',
                    'asset_name': 'input-data', 'obs_path': 'obs://example/exact-v2/'}], 'stages': [stage]})
                fragment = dataset_inputs(self.store.plan(run), state, 'checks')
                wire = fragment['task_config']
                self.assertEqual(json.loads(wire['dataset_configs']), fragment['datasets'])
                self.assertEqual(json.loads(wire['dataset_configs'])[0]['version_id'], 'exact-v2')
                self.assertEqual(wire['dataset_id'], 'input')
                self.assertEqual(wire['dataset_path'], 'obs://example/exact-v2/')
                result = subprocess.run([sys.executable, str(MONITOR.parent / 'pipeline_state.py'), '--runs-root', self.temp.name,
                    '--run', run, 'resolve-inputs', '--stage', 'checks'], capture_output=True, text=True, encoding='utf-8')
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(json.loads(result.stdout), fragment)
                self.assertEqual(self.store.read(run), state)
                for key in ('dataset_configs',):
                    self.assertIsInstance(wire[key], str)
                incomplete = copy.deepcopy(state)
                incomplete['inputs'][0].pop('version_id')
                with self.assertRaisesRegex(StateError, '确切版本'):
                    dataset_inputs(self.store.plan(run), incomplete, 'checks')

    def test_reserve_rejects_missing_version_without_writing_pending_state(self):
        run = self.run
        before = self.store.read(run)
        config = task_input_config()
        entry = json.loads(config['dataset_configs'])[0]
        entry.pop('version_id')
        config['dataset_configs'] = json.dumps([entry])
        path = Path(self.temp.name) / 'missing-version-config.json'
        atomic_json(path, config)
        result = subprocess.run([sys.executable, str(MONITOR.parent / 'pipeline_state.py'), '--runs-root', self.temp.name,
            '--run', run, 'reserve-task', '--stage', 'cleaning', '--expect-task', 'demo-clean-1',
            '--name', 'confirmed-retry', '--config', str(path)], capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn('version_id', result.stderr)
        self.assertEqual(self.store.read(run), before)
        self.assertFalse((self.store.directory(run) / 'pending-config.json').exists())

    def test_control_only_advisory_failure_is_waited_on_but_not_included_as_data(self):
        raw = merge_choices()
        raw['pipeline']['stages'].insert(2, {'id': 'check', 'kind': 'eval', 'operator_id': 'workspace-check',
                                            'operator_source': 'workspace', 'input_from': ['A']})
        raw['pipeline']['stages'][-1]['depends_on'].append('check')
        draft, issues, _ = validate_pipeline(raw)
        self.assertEqual(issues, [])
        self.store.init('multi-control', draft)
        def recorded(state):
            for key in ('A', 'B'):
                state['stages'][key].update(status='SUCCEEDED', target_path='obs://example/' + key + '/',
                                            target_asset_id=key, target_version_id='v1', output_name='data-' + key)
            state['stages']['check'].update(status='FAILED', target_report_path='obs://example/report/')
        state = self.store.mutate('multi-control', recorded)
        plan = self.store.plan('multi-control')
        self.assertEqual(dataset_inputs(plan, state, 'C')['input_from'], ['B', 'A'])
        self.assertEqual(self.monitor.node('multi-control', 'C')['display_status'], 'READY')
        state['stages']['check']['status'] = 'RUNNING'
        with self.assertRaisesRegex(StateError, '尚未完成'):
            dataset_inputs(plan, state, 'C')

    def test_legacy_single_upload_handoff_uses_registered_target_path(self):
        plan = normalize_plan({'inputs': [{'source_type': 'obs', 'obs_path': 'obs://example/raw/'}], 'stages': [{'id': 'task'}]})
        self.store.init('single-upload', plan)
        def uploaded(state):
            state['stages']['upload'].update(status='SUCCEEDED', target_path='obs://example/registered/',
                                             target_asset_id='registered-asset', target_version_id='v4', output_name='registered-data')
        state = self.store.mutate('single-upload', uploaded)
        next(stage for stage in plan['stages'] if stage['id'] == 'task').pop('input_from')
        data = dataset_inputs(plan, state, 'task')['datasets'][0]
        self.assertEqual(data['obs_path'], 'obs://example/registered/')
        self.assertEqual(data['asset_id'], 'registered-asset')

    def test_record_single_input_cli_persists_registration_before_next_step(self):
        run = 'registered-input'
        self.store.init(run, {'inputs': [{'source_type': 'local', 'local_path': 'C:/数据/input'}],
                              'stages': [{'id': 'A'}]})
        self.assertEqual(self.monitor.node(run, 'upload')['label'], '待登记')
        self.assertNotEqual(self.monitor.node(run, 'A')['display_status'], 'READY')
        metadata = {'default': {'asset_id': 'registered-asset', 'version_id': 'v2',
                                'asset_name': 'registered-data', 'obs_path': 'obs://example/actual-version/'}}
        source = Path(self.temp.name) / 'registered-inputs.json'
        source.write_text(json.dumps(metadata, ensure_ascii=False), encoding='utf-8-sig')
        result = subprocess.run([sys.executable, str(MONITOR.parent / 'pipeline_state.py'), '--runs-root', self.temp.name,
                                '--run', run, 'record-inputs', '--inputs-file', str(source), '--expect-version', '1'],
                                capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(result.returncode, 0, result.stderr)
        state = self.store.read(run)
        self.assertEqual(state['inputs'][0]['local_path'], 'C:/数据/input')
        self.assertEqual(state['inputs'][0]['source_type'], 'local')
        self.assertEqual(state['inputs'][0]['asset_id'], 'registered-asset')
        self.assertEqual(state['stages']['upload']['target_version_id'], 'v2')
        upload = self.monitor.node(run, 'upload')
        self.assertEqual(upload['label'], '已登记')
        self.assertEqual(upload['display_status'], 'SUCCEEDED')
        self.assertFalse(upload['skipped'])
        self.assertTrue(upload['registration_complete'])
        self.assertEqual(upload['registrations'][0]['asset_id'], 'registered-asset')
        data = dataset_inputs(self.store.plan(run), state, 'A')['datasets'][0]
        self.assertEqual(data['obs_path'], metadata['default']['obs_path'])
        self.assertEqual(self.monitor.node(run, 'A')['display_status'], 'READY')
        self.assertEqual(self.store.events(run)[-1]['type'], 'inputs_recorded')

    def test_registered_ids_do_not_reclassify_local_or_obs_sources_as_reused_assets(self):
        metadata = {'asset_id': 'prepared-asset', 'version_id': 'v1', 'asset_name': 'prepared-data',
                    'obs_path': 'obs://example/prepared/'}
        for kind in ('local', 'obs'):
            with self.subTest(kind=kind):
                run = 'prepared-' + kind
                original = {**metadata, 'source_type': kind}
                if kind == 'local':
                    original['local_path'] = 'C:/数据/input'
                self.store.init(run, {'inputs': [original], 'stages': [{'id': 'A'}]})
                self.assertEqual(self.monitor.node(run, 'upload')['label'], '待登记')
                state = self.store.record_inputs(run, {'default': metadata}, 1)
                self.assertEqual(state['inputs'][0], original)
                upload = self.monitor.node(run, 'upload')
                self.assertEqual(upload['display_status'], 'SUCCEEDED')
                self.assertFalse(upload['skipped'])
                self.assertEqual(upload['label'], '已登记')
                self.assertEqual(dataset_inputs(self.store.plan(run), state, 'A')['datasets'][0]['asset_id'], 'prepared-asset')

    def test_upload_skip_result_requires_reused_assets_and_is_atomic(self):
        result_file = Path(self.temp.name) / 'skip-upload.json'
        atomic_json(result_file, {'status': 'SKIPPED'})
        cases = [('local', [{'source_type': 'local', 'local_path': 'C:/data/raw'}]),
                 ('obs', [{'source_type': 'obs', 'obs_path': 'obs://example/raw/'}]),
                 ('unknown', []),
                 ('mixed', [{'id': 'existing', 'source_type': 'asset', 'asset_id': 'existing', 'version_id': 'v1'},
                            {'id': 'new', 'source_type': 'obs', 'obs_path': 'obs://example/new/'}]),
                 ('asset', [{'source_type': 'asset', 'asset_id': 'existing', 'version_id': 'v1'}])]
        for kind, inputs in cases:
            with self.subTest(kind=kind):
                run = 'skip-upload-' + kind
                stage = {'id': 'A'}
                if len(inputs) > 1:
                    stage['input_from'] = ['input:existing']
                before = self.store.init(run, {'inputs': inputs, 'stages': [stage]})
                command = [sys.executable, str(MONITOR.parent / 'pipeline_state.py'), '--runs-root', self.temp.name,
                           '--run', run, 'set-result', '--stage', 'upload', '--expect-task', 'none',
                           '--result', str(result_file)]
                result = subprocess.run(command, capture_output=True, text=True, encoding='utf-8')
                if kind == 'asset':
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(self.monitor.node(run, 'upload')['display_status'], 'SKIPPED')
                else:
                    self.assertEqual(result.returncode, 1, result.stderr)
                    self.assertIn('record-inputs', result.stderr)
                    self.assertEqual(self.store.read(run), before)

    def test_record_inputs_clears_incorrect_skip_when_original_source_is_preserved(self):
        metadata = {'asset_id': 'registered-asset', 'version_id': 'v2', 'asset_name': 'registered-data',
                    'obs_path': 'obs://example/registered/'}
        for kind in ('local', 'obs'):
            with self.subTest(kind=kind):
                run = 'repair-upload-' + kind
                original = {'source_type': kind, 'obs_path': 'obs://example/raw/'}
                if kind == 'local':
                    original = {'source_type': kind, 'local_path': 'C:/data/raw'}
                self.store.init(run, {'inputs': [original], 'stages': [{'id': 'A'}]})
                before = self.store.mutate(run, lambda state: state['stages']['upload'].update(
                    status='SKIPPED', skipped=True, not_applicable=True, skip_reason='incorrect legacy skip'))
                state = self.store.record_inputs(run, {'default': metadata}, before['version'])
                self.assertEqual(state['inputs'][0], {**original, **metadata})
                upload = self.monitor.node(run, 'upload')
                self.assertEqual(upload['display_status'], 'SUCCEEDED')
                self.assertEqual(upload['label'], '已登记')
                self.assertFalse(upload['skipped'])
                self.assertFalse(upload['not_applicable'])
                self.assertNotIn('skip_reason', upload)
                self.assertEqual(self.monitor.node(run, 'A')['display_status'], 'READY')

    def test_multi_input_registration_is_persisted_per_source_without_flattening(self):
        run = 'multi-registration'
        self.store.init(run, {'inputs': [{'id': key, 'source_type': 'obs', 'obs_path': 'obs://example/' + key + '/'}
                                        for key in ('left', 'right')],
                              'stages': [{'id': key, 'input_from': ['input:' + source]}
                                         for key, source in [('A', 'left'), ('B', 'right')]]})
        metadata = {key: {'asset_id': 'asset-' + key, 'version_id': 'v-' + key,
                          'asset_name': 'data-' + key, 'obs_path': 'obs://example/' + key + '/'}
                    for key in ('left', 'right')}
        self.store.record_inputs(run, {'left': metadata['left']}, 1)
        upload = self.monitor.node(run, 'upload')
        self.assertFalse(upload['registration_complete'])
        self.assertNotEqual(upload['label'], '已登记')
        state = self.store.record_inputs(run, {'right': metadata['right']}, 2)
        upload = self.monitor.node(run, 'upload')
        self.assertTrue(upload['registration_complete'])
        self.assertEqual([source['asset_id'] for source in upload['registrations']], ['asset-left', 'asset-right'])
        self.assertNotIn('target_asset_id', state['stages']['upload'])
        self.assertTrue(all(self.monitor.node(run, key)['display_status'] == 'READY' for key in ('A', 'B')))
        for key, source in [('A', 'left'), ('B', 'right')]:
            self.assertEqual(dataset_inputs(self.store.plan(run), state, key)['datasets'][0]['asset_id'], 'asset-' + source)

    def test_registration_rejects_stale_invalid_or_replaced_inputs_atomically(self):
        run = 'registration-guards'
        self.store.init(run, {'inputs': [{'source_type': 'asset', 'asset_id': 'existing', 'version_id': 'v1',
                                         'obs_path': 'obs://example/original/'}], 'stages': [{'id': 'A'}]})
        valid = {'default': {'asset_id': 'existing', 'version_id': 'v1', 'asset_name': 'original',
                              'obs_path': 'obs://example/original/'}}
        before = self.store.read(run)
        invalid = [{}, {'other': valid['default']}, {'default': []}, {'default': {'asset_id': 'existing'}}]
        for key, value in [('asset_id', 'replacement'), ('version_id', 'v2'), ('obs_path', 'obs://example/changed/'),
                           ('obs_path', 'C:/local'), ('asset_name', ''), ('secret', 'must-not-be-stored')]:
            fields = {**valid['default'], key: value}
            invalid.append({'default': fields})
        for supplied in invalid:
            with self.subTest(supplied=supplied), self.assertRaises(StateError):
                self.store.record_inputs(run, supplied, before['version'])
            self.assertEqual(self.store.read(run), before)
        with self.assertRaises(Conflict):
            self.store.record_inputs(run, valid, 99)
        state = self.store.record_inputs(run, valid, 1)
        self.assertTrue(state['stages']['upload']['not_applicable'])
        self.assertEqual(state['stages']['upload']['status'], 'SKIPPED')
        self.assertEqual(self.monitor.node(run, 'upload')['registrations'][0]['asset_id'], 'existing')

    def test_upload_success_without_registration_is_rejected_and_legacy_gap_is_visible(self):
        run = 'unrecorded-upload'
        self.store.init(run, {'inputs': [{'source_type': 'obs', 'obs_path': 'obs://example/raw/'}],
                              'stages': [{'id': 'A'}]})
        source = Path(self.temp.name) / 'upload-result.json'
        atomic_json(source, {'status': 'SUCCEEDED'})
        command = [sys.executable, str(MONITOR.parent / 'pipeline_state.py'), '--runs-root', self.temp.name, '--run', run,
                   'set-result', '--stage', 'upload', '--expect-task', 'none', '--result', str(source)]
        before = self.store.read(run)
        rejected = subprocess.run(command, capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(rejected.returncode, 1)
        self.assertIn('record-inputs', rejected.stderr)
        self.assertEqual(self.store.read(run), before)
        self.store.mutate(run, lambda state: state['stages']['upload'].update(status='SUCCEEDED'))
        self.assertEqual(self.monitor.node(run, 'upload')['label'], '登记信息待补全')
        self.assertTrue(any('无需重复上传' in warning['text'] for warning in self.monitor.snapshot(run)['warnings']))
        atomic_json(source, {'status': 'SUCCEEDED', 'target_asset_id': 'legacy',
                             'target_version_id': 'v3', 'target_path': 'obs://example/legacy/'})
        accepted = subprocess.run(command, capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(accepted.returncode, 0, accepted.stderr)
        self.assertEqual(self.monitor.node(run, 'upload')['label'], '已登记')

    def test_sibling_processing_branches_submit_while_first_is_running(self):
        run = 'parallel-processing'
        self.store.init(run, {'inputs': [{'source_type': 'asset', 'asset_id': 'raw', 'version_id': 'v1',
                                         'asset_name': 'raw', 'obs_path': 'obs://example/raw/'}],
                              'stages': [{'id': key, 'input_from': ['input:default']} for key in ('A', 'B')]
                              + [{'id': 'C', 'input_from': ['A', 'B']}]})
        source = Path(self.temp.name) / 'parallel-config.json'
        atomic_json(source, {'algo_name': 'processing', **task_input_config()})
        base = [sys.executable, str(MONITOR.parent / 'pipeline_state.py'), '--runs-root', self.temp.name, '--run', run]
        for key in ('A', 'B'):
            self.assertEqual(self.monitor.node(run, key)['display_status'], 'READY')
            reserved = subprocess.run(base + ['reserve-task', '--stage', key, '--expect-task', 'none', '--name', key,
                                              '--config', str(source)], capture_output=True, text=True, encoding='utf-8')
            self.assertEqual(reserved.returncode, 0, reserved.stderr)
            action_id = self.store.read(run)['pending_action']['id']
            resolved = subprocess.run(base + ['resolve-action', '--action-id', action_id, '--task-id', 'task-' + key],
                                      capture_output=True, text=True, encoding='utf-8')
            self.assertEqual(resolved.returncode, 0, resolved.stderr)
            self.store.mutate(run, lambda state: state['stages'][key].update(status='RUNNING'))
        self.assertEqual(self.store.read(run)['stages']['A']['status'], 'RUNNING')
        self.assertEqual(self.store.read(run)['stages']['B']['status'], 'RUNNING')
        self.assertEqual(self.monitor.node(run, 'C')['display_status'], 'IDLE')
        with self.assertRaisesRegex(StateError, '尚未完成'):
            dataset_inputs(self.store.plan(run), self.store.read(run), 'C')

    def test_retry_rechecks_all_input_versions_and_preserves_order(self):
        path = self.store.directory(self.run) / 'tasks' / 'demo-clean-1.json'
        record = read_json_object(path)
        datasets = json.loads(record['task_config']['dataset_configs'])
        datasets.append({**datasets[0], 'asset_id': 'side-asset', 'version_id': 'v2', 'obs_path': 'obs://example/side/'})
        record['task_config']['dataset_configs'] = json.dumps(datasets)
        atomic_json(path, record)
        original = self.client._call
        queries = []
        invalid_second = False
        def query(service, method, *args, **kwargs):
            if method == 'show_asset_version':
                asset = args[0]
                queries.append(asset)
                data = next(item for item in datasets if item['asset_id'] == asset)
                return {'status': 'DRAFT', 'url': 'obs://example/changed/' if invalid_second and asset == 'side-asset' else data['obs_path']}
            return original(service, method, *args, **kwargs)
        with patch.object(self.client, '_call', side_effect=query) as calls:
            draft = self.monitor.retry_draft(self.run, 'cleaning')
            self.assertEqual(json.loads(draft['config']['dataset_configs']), datasets)
            self.assertEqual(queries, [datasets[0]['asset_id'], 'side-asset'])
            before = self.store.read(self.run)
            invalid_second = True
            with self.assertRaisesRegex(StateError, '路径已变化'):
                self.monitor.retry_draft(self.run, 'cleaning')
            self.assertEqual(self.store.read(self.run), before)
            self.assertFalse(any(call.args[:2] == ('dataset', 'create_task') for call in calls.call_args_list))

    def test_finish_requires_verified_artifact_and_terminal_steps(self):
        base = [sys.executable, str(MONITOR.parent / 'pipeline_state.py'), '--runs-root', self.temp.name]
        rejected = subprocess.run(base + ['--run', self.run, 'finish'], capture_output=True)
        self.assertEqual(rejected.returncode, 1)
        completed = subprocess.run(base + ['--run', 'demo-completed-1003', 'finish'], capture_output=True)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(self.store.read('demo-completed-1003')['status'], 'SUCCEEDED_WITH_WARNINGS')

    def test_historical_task_detail_and_torn_event_recovery(self):
        result = self.monitor.task_detail('demo-running-1001', 'demo-clean-1')
        self.assertTrue(result['historical'])
        self.assertEqual(result['live']['status'], 'FAILED')
        self.assertEqual(result['live']['pod_names'], ['demo-worker-0'])
        path = self.store.directory(self.run) / 'events.jsonl'
        previous = self.store.events(self.run)
        state = self.store.read(self.run)
        path.write_text('\n'.join(json.dumps(e) for e in previous[:-1]) + '\n{"seq":', encoding='utf-8')
        recovered = self.store.events(self.run)
        self.assertEqual(recovered[-1]['seq'], state['event_seq'])

    def test_blocking_cannot_skip_and_advisory_can(self):
        with self.assertRaises(Conflict):
            self.monitor.action(self.run, {'type': 'skip', 'stage': 'cleaning', 'expected_task_id': 'demo-clean-1', 'confirmed': True})
        self.monitor.action(self.run, {'type': 'skip', 'stage': 'evaluation', 'member': 'quality-eval', 'expected_task_id': None, 'confirmed': True})
        self.assertTrue(self.store.read(self.run)['stages']['evaluation']['members']['quality-eval']['skipped'])

    def prepare_bypass_run(self):
        run = 'bypass-clean'
        source = {'source_type': 'asset', 'asset_id': 'original', 'version_id': 'v3', 'asset_name': 'original-data',
                  'obs_path': 'obs://example/original/', 'data_source_type': 'lerobotv3'}
        self.store.init(run, {'inputs': [source], 'output': {'from_stage': 'clean'}, 'stages': [
            {'id': 'clean', 'operator': '数据清洗'},
            {'id': 'eval', 'kind': 'eval', 'operator': '数据集质量评测-LeRobot'}]})
        return run

    def skip_request(self, run, stage='clean', action='request-skip'):
        return self.monitor.action(run, {'type': action, 'stage': stage, 'member': None, 'confirmed': True,
                                        'expected_task_id': None, 'expected_version': self.store.read(run)['version']})

    def test_unstarted_processing_skip_request_and_cancel_do_not_forward_data(self):
        run = self.prepare_bypass_run()
        before = self.store.read(run)
        self.assertTrue(self.monitor.node(run, 'clean')['actions']['request-skip'])
        requested = self.skip_request(run)
        self.assertEqual(requested['state']['stages'], before['stages'])
        self.assertEqual(self.monitor.node(run, 'clean')['display_status'], 'AWAITING_DECISION')
        self.assertEqual(self.monitor.node(run, 'eval')['display_status'], 'IDLE')
        self.assertTrue(self.monitor.node(run, 'clean')['actions']['cancel-skip'])
        with self.assertRaisesRegex(Conflict, '跳过兼容性'):
            self.store.set_task(run, 'clean', None, None, 'unsafe-created', {}, 'unsafe')
        cancelled = self.skip_request(run, action='cancel-skip')
        self.assertEqual(cancelled['state']['stages'], before['stages'])
        self.assertIsNone(cancelled['state']['awaiting_decision'])
        self.assertEqual(self.client.sequence, 0)

    def test_verified_skip_cli_forwards_exact_original_asset_and_finishes_with_warning(self):
        run = self.prepare_bypass_run()
        requested = self.skip_request(run)['state']
        args = [sys.executable, str(MONITOR.parent / 'pipeline_state.py'), '--runs-root', self.temp.name, '--run', run,
                'resolve-skip', '--stage', 'clean', '--expect-version', str(requested['version']), '--decision', 'skip',
                '--compatibility-note', 'CLI verified original LeRobot input and downstream quality operator contract']
        resolved = subprocess.run(args, capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(resolved.returncode, 0, resolved.stderr)
        state = self.store.read(run)
        item = state['stages']['clean']
        self.assertTrue(item['bypassed'])
        self.assertIsNone(item['task_id'])
        self.assertEqual(item['output_name'], 'original-data')
        self.assertEqual(item['target_version_id'], 'v3')
        handoff = dataset_inputs(self.store.plan(run), state, 'eval')
        self.assertEqual(handoff['task_config']['dataset_id'], 'original')
        self.assertEqual(handoff['datasets'][0]['version_id'], 'v3')
        with self.assertRaisesRegex(Conflict, '原输入跳过'):
            self.store.set_task(run, 'clean', None, None, 'unsafe-later', {}, 'unsafe')
        def finishable(current):
            current['stages']['eval']['status'] = 'SUCCEEDED'
            current['stages']['output']['status'] = 'SUCCEEDED'
            current['output'].update({key: item[key] for key in ('target_path', 'target_asset_id', 'target_version_id')})
        self.store.mutate(run, finishable)
        finished = subprocess.run(args[:6] + ['finish'], capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(finished.returncode, 0, finished.stderr)
        self.assertEqual(self.store.read(run)['status'], 'SUCCEEDED_WITH_WARNINGS')
        self.assertEqual(self.client.sequence, 0)

    def test_required_conversion_and_multi_input_merge_cannot_be_bypassed(self):
        run = 'required-conversion'
        self.store.init(run, {'inputs': [{'source_type': 'obs', 'obs_path': 'obs://example/raw/', 'data_source_type': 'h5'}],
                              'stages': [{'id': 'convert', 'operator': '数据转换--H5转LeRobotV3'}, {'id': 'clean', 'operator': '数据清洗'}]})
        before = self.store.read(run)
        node = self.monitor.node(run, 'convert')
        self.assertFalse(node['actions']['request-skip'])
        self.assertIn('不兼容', node['skip_disabled_reason'])
        with self.assertRaises(Conflict):
            self.skip_request(run, 'convert')
        self.assertEqual(self.store.read(run), before)
        self.prepare_merge_run()
        self.assertFalse(self.monitor.node('multi-input', 'C')['actions']['request-skip'])
        self.assertIn('多输入合并', self.monitor.node('multi-input', 'C')['skip_disabled_reason'])

    def test_skip_requires_compatibility_note_ready_source_and_current_state_version(self):
        run = self.prepare_bypass_run()
        version = self.skip_request(run)['state']['version']
        before = self.store.read(run)
        with self.assertRaisesRegex(StateError, 'CLI 核实'):
            self.store.resolve_skip(run, 'clean', version, 'skip')
        self.assertEqual(self.store.read(run), before)
        current = self.store.mutate(run, lambda state: state['orchestrator'].update(heartbeat_at='new-beat'))
        with self.assertRaisesRegex(Conflict, '状态版本'):
            self.store.resolve_skip(run, 'clean', version, 'skip', 'verified')
        self.assertEqual(self.store.read(run), current)
        current = self.store.mutate(run, lambda state: state['stages']['upload'].update(status=None, skipped=False))
        with self.assertRaisesRegex(StateError, '尚未完成'):
            self.store.resolve_skip(run, 'clean', current['version'], 'skip', 'verified')
        self.assertEqual(self.store.read(run), current)
        kept = self.store.resolve_skip(run, 'clean', current['version'], 'keep')
        self.assertIsNone(kept['awaiting_decision'])
        self.assertFalse(kept['stages']['clean']['skipped'])

    def test_skip_request_cannot_replace_other_decision_or_rewrite_started_downstream(self):
        run = self.prepare_bypass_run()
        current = self.store.mutate(run, lambda state: state.update(awaiting_decision={'stage': 'eval', 'member': None}, status='AWAITING_DECISION'))
        with self.assertRaises(Conflict):
            self.skip_request(run)
        self.assertEqual(self.store.read(run), current)
        self.store.mutate(run, lambda state: state.update(awaiting_decision=None, status='RUNNING'))
        self.store.set_task(run, 'eval', None, None, 'already-started', {}, 'existing-eval')
        self.assertFalse(self.monitor.node(run, 'clean')['actions']['request-skip'])
        self.assertIn('下游已经提交', self.monitor.node(run, 'clean')['skip_disabled_reason'])

    def test_multiple_branch_bypasses_keep_merge_input_order_and_original_versions(self):
        draft, issues, _ = validate_pipeline(merge_choices())
        self.assertEqual(issues, [])
        self.store.init('skip-branches', draft)
        for stage in ('A', 'B'):
            version = self.skip_request('skip-branches', stage)['state']['version']
            self.store.resolve_skip('skip-branches', stage, version, 'skip', 'CLI verified merge accepts this original CSV branch')
        result = dataset_inputs(self.store.plan('skip-branches'), self.store.read('skip-branches'), 'C')
        self.assertEqual([item['asset_id'] for item in result['datasets']], ['asset-right', 'asset-left'])
        self.assertEqual([item['version_id'] for item in result['datasets']], ['v1', 'v1'])

    def test_processing_skip_respects_legacy_terminal_and_existing_task_guards(self):
        run = self.prepare_bypass_run()
        for changes in ({'schema_version': 1}, {'status': 'TERMINATED'}, {'status': 'SUCCEEDED'}):
            original = self.store.read(run)
            altered = {**original, **changes}
            atomic_json(self.store.directory(run) / 'state.json', altered)
            with self.subTest(changes=changes), self.assertRaises((StateError, Conflict)):
                self.skip_request(run)
            self.assertEqual(self.store.read(run), altered)
            atomic_json(self.store.directory(run) / 'state.json', original)
        self.store.set_task(run, 'clean', None, None, 'queued-existing', {}, 'existing')
        self.assertFalse(self.monitor.node(run, 'clean')['actions']['request-skip'])

    def delete_body(self, run='demo-completed-1003'):
        return {'confirmed': True, 'expected_version': self.store.read(run)['version']}

    def test_delete_terminal_runs_removes_files_caches_and_leaves_cloud_untouched(self):
        before_cloud = copy.deepcopy(self.client.statuses)
        before_other = self.store.read(self.run)
        for status in ['SUCCEEDED', 'SUCCEEDED_WITH_WARNINGS', 'FAILED', 'TERMINATED']:
            run = 'delete-' + status.lower().replace('_', '-')
            self.store.init(run, {'name': 'delete-example', 'stages': [{'id': 'work'}]})
            self.store.mutate(run, lambda state: state.update(status=status))
            directory = self.store.directory(run)
            atomic_json(directory / 'tasks' / 'task.json', {'task_config': {}})
            (directory / 'logs').mkdir()
            (directory / 'logs/task.log').write_text('local log')
            self.monitor.cache[(run, 'task')] = {'detail': {}}
            self.monitor.file_lists[(run, 'task', False)] = []
            self.monitor.frame_lists[(run, 'task')] = set()
            self.monitor.drafts[run] = {'run': run}
            self.assertTrue(self.monitor.snapshot(run)['actions']['delete'])
            with patch.object(self.client, '_call', side_effect=AssertionError('delete must be local')) as cloud:
                result = self.monitor.delete_run(run, self.delete_body(run))
                cloud.assert_not_called()
            self.assertTrue(result['deleted'])
            self.assertFalse(result['cleanup_pending'])
            self.assertFalse(directory.exists())
            self.assertNotIn(run, self.monitor.run_ids())
            self.assertNotIn((run, 'task'), self.monitor.cache)
            self.assertNotIn((run, 'task', False), self.monitor.file_lists)
            self.assertNotIn((run, 'task'), self.monitor.frame_lists)
            self.assertNotIn(run, self.monitor.drafts)
        self.assertEqual(self.client.statuses, before_cloud)
        self.assertEqual(self.store.read(self.run), before_other)
        self.assertFalse(list(self.store.root.glob('.deleted-*')))

    def test_delete_requires_confirmation_terminal_schema_and_no_pending_submission(self):
        run = 'demo-completed-1003'
        for confirmed in [None, False, 'true']:
            with self.subTest(confirmed=confirmed), self.assertRaises(StateError):
                self.monitor.delete_run(run, {**self.delete_body(run), 'confirmed': confirmed})
        for active in [self.run, 'demo-running-1001']:
            self.assertFalse(self.monitor.snapshot(active)['actions']['delete'])
            with self.assertRaises(Conflict):
                self.monitor.delete_run(active, self.delete_body(active))
        self.store.mutate(run, lambda state: state.update(pending_action={'id': 'uncertain-create'}))
        self.assertFalse(self.monitor.snapshot(run)['actions']['delete'])
        with self.assertRaisesRegex(Conflict, '提交事务'):
            self.monitor.delete_run(run, self.delete_body(run))
        state = self.store.read(run)
        state.update(schema_version=1, pending_action=None)
        atomic_json(self.store.directory(run) / 'state.json', state)
        with self.assertRaisesRegex(StateError, '旧版'):
            self.monitor.delete_run(run, self.delete_body(run))
        self.assertTrue(self.store.directory(run).exists())

    def test_delete_rejects_stale_versions_and_busy_shared_lock(self):
        run = 'demo-completed-1003'
        before = self.store.read(run)
        with self.assertRaises(Conflict):
            self.monitor.delete_run(run, {'confirmed': True, 'expected_version': before['version'] + 1})
        for version in [None, True, '1', 0]:
            with self.subTest(version=version), self.assertRaises(StateError):
                self.monitor.delete_run(run, {'confirmed': True, 'expected_version': version})
        with self.store.locked(run), self.assertRaisesRegex(Conflict, '其他操作'):
            self.monitor.delete_run(run, self.delete_body(run))
        self.assertEqual(self.store.read(run), before)
        self.assertFalse((self.store.directory(run) / 'state.deleting.json').exists())

    def test_delete_move_failure_restores_state_for_retry(self):
        run = 'demo-completed-1003'
        directory = self.store.directory(run)
        before = self.store.read(run)
        def replace(source, target):
            if Path(source) == directory:
                with self.assertRaises(Conflict):
                    self.store.init(run, {'stages': [{'id': 'new'}]})
                with self.assertRaises(FileNotFoundError):
                    self.store.mutate(run, lambda state: state.update(status='RUNNING'))
                raise PermissionError('directory in use')
            platform_utils.atomic_replace(source, target)
        with patch('pipeline_state.atomic_replace', side_effect=replace), self.assertRaisesRegex(StateError, '记录已保留'):
            self.monitor.delete_run(run, self.delete_body(run))
        self.assertEqual(self.store.read(run), before)
        self.assertTrue((directory / 'plan.json').exists())
        self.assertFalse((directory / 'state.deleting.json').exists())
        self.assertTrue(self.monitor.delete_run(run, self.delete_body(run))['deleted'])

    def test_delete_cleanup_error_reports_remaining_local_directory(self):
        run = 'demo-completed-1003'
        with patch('pipeline_state.shutil.rmtree', side_effect=PermissionError('file in use')):
            result = self.monitor.delete_run(run, self.delete_body(run))
        self.assertTrue(result['cleanup_pending'])
        self.assertIn('部分本地文件未能清理', result['warning'])
        self.assertFalse(self.store.directory(run).exists())
        self.assertNotIn(run, self.monitor.run_ids())
        remaining = list(self.store.root.glob('.deleted-*'))
        self.assertEqual(len(remaining), 1)
        self.assertTrue((remaining[0] / 'state.deleting.json').exists())

    def test_delete_does_not_follow_symlinks_or_recreate_from_stale_agent(self):
        run = 'demo-completed-1003'
        with tempfile.TemporaryDirectory() as outside:
            sentinel = Path(outside) / 'keep.txt'
            sentinel.write_text('outside record')
            root_link = self.store.root / 'outside-link'
            try:
                root_link.symlink_to(outside, target_is_directory=True)
            except OSError:
                self.skipTest('Symlink creation requires platform permission')
            with self.assertRaises(StateError):
                self.monitor.delete_run('outside-link', {'confirmed': True, 'expected_version': 1})
            (self.store.directory(run) / 'linked-dir').symlink_to(outside, target_is_directory=True)
            self.monitor.delete_run(run, self.delete_body(run))
            self.assertEqual(sentinel.read_text(), 'outside record')
            with self.assertRaises(FileNotFoundError):
                self.store.mutate(run, lambda state: state.update(status='RUNNING'))
            self.assertFalse(self.store.directory(run).exists())

    def test_delete_discards_late_inflight_task_refresh(self):
        run = 'demo-completed-1003'
        entered = threading.Event()
        release = threading.Event()
        task = copy.deepcopy(self.store.read(run)['stages']['cleaning'])
        def detail(*_):
            entered.set()
            self.assertTrue(release.wait(timeout=5))
            return {'status': 'SUCCEEDED'}
        with patch.object(self.client, 'task_detail', side_effect=detail), ThreadPoolExecutor(max_workers=1) as pool:
            pending = pool.submit(self.monitor.refresh_task, run, 'cleaning', None, task, True)
            self.assertTrue(entered.wait(timeout=5))
            try:
                self.monitor.delete_run(run, self.delete_body(run))
            finally:
                release.set()
            pending.result(timeout=5)
        self.assertFalse(any(key[0] == run for key in self.monitor.cache))
        self.assertFalse(self.store.directory(run).exists())

    def test_delete_and_completed_eval_retry_cannot_both_succeed(self):
        run = 'demo-completed-1003'
        draft = self.monitor.retry_draft(run, 'evaluation', 'diversity-eval')
        version = self.store.read(run)['version']
        barrier = threading.Barrier(2)
        def perform(action):
            barrier.wait(timeout=5)
            try:
                if action == 'delete':
                    self.monitor.delete_run(run, {'confirmed': True, 'expected_version': version})
                else:
                    self.monitor.action(run, {'type': 'retry', 'stage': 'evaluation', 'member': 'diversity-eval',
                        'expected_task_id': 'demo-diversity', 'confirmed': True, 'expected_version': version,
                        'draft_id': draft['draft_id'], 'overrides': {}})
                return action
            except (StateError, OSError):
                return 'rejected'
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(perform, ['delete', 'retry']))
        self.assertEqual(results.count('rejected'), 1)
        self.assertNotEqual('delete' in results, 'retry' in results)
        self.assertEqual(self.client.sequence, int('retry' in results))
        self.assertEqual(self.store.directory(run).exists(), 'retry' in results)

    def test_http_delete_uses_auth_csrf_cas_and_removes_only_requested_record(self):
        run = 'demo-completed-1003'
        server = Server(0, self.monitor, 'local-delete-test')
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        port = server.server_address[1]
        headers = {'Cookie': 'pipeline_session=local-delete-test', 'X-Pipeline-Monitor': '1', 'Content-Type': 'application/json'}
        def request(method, path, body=None, extra=None):
            connection = HTTPConnection('127.0.0.1', port, timeout=5)
            connection.request(method, path, None if body is None else json.dumps(body), headers=headers if extra is None else extra)
            response = connection.getresponse()
            result = response.status, response.read()
            connection.close()
            return result
        try:
            path = '/api/runs/' + run + '/delete'
            body = self.delete_body(run)
            self.assertEqual(request('POST', path, body, {})[0], 401)
            self.assertEqual(request('POST', path, body, {'Cookie': headers['Cookie'], 'Content-Type': 'application/json'})[0], 403)
            self.assertEqual(request('POST', path, body, {**headers, 'Origin': 'http://other.example'})[0], 403)
            self.assertEqual(request('POST', path, {**body, 'confirmed': False})[0], 400)
            self.assertEqual(request('POST', path, {**body, 'expected_version': 0})[0], 400)
            self.assertEqual(request('POST', path, {**body, 'expected_version': body['expected_version'] + 1})[0], 409)
            self.assertEqual(request('POST', '/api/runs/%2E%2E%2Foutside/delete', body)[0], 404)
            with patch.object(self.client, '_call', side_effect=AssertionError('Deletion never calls cloud')):
                code, data = request('POST', path, body)
                self.assertEqual(code, 200, data)
                self.assertTrue(json.loads(data)['deleted'])
                self.assertEqual(request('GET', '/api/runs/' + run)[0], 404)
                self.assertEqual(request('POST', path, body)[0], 404)
                code, data = request('GET', '/api/runs')
                self.assertEqual(code, 200)
                self.assertNotIn(run, [item['run_id'] for item in json.loads(data)['runs']])
            self.assertEqual(request('GET', '/api/runs/' + self.run)[0], 200)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

    def test_terminate_keeps_cloud_tasks(self):
        with self.assertRaises(StateError):
            self.monitor.action(self.run, {'type': 'terminate', 'expected_task_id': None, 'confirmed': True, 'confirmation': 'oops'})
        self.monitor.action(self.run, {'type': 'terminate', 'expected_task_id': None, 'confirmed': True, 'confirmation': '1002'})
        self.assertEqual(self.store.read(self.run)['status'], 'TERMINATED')
        self.assertEqual(self.client.statuses['demo-clean-1'], 'FAILED')
        self.assertFalse(self.monitor.node(self.run, 'cleaning')['actions']['retry'])

    def test_uncertain_create_keeps_reservation(self):
        body = self.retry_body(); original = self.client._call
        def call(service, method, *args, **kwargs):
            if kwargs.get('created'):
                raise UncertainSubmission('提交超时')
            return original(service, method, *args, **kwargs)
        self.client._call = call
        with self.assertRaises(UncertainSubmission):
            self.monitor.action(self.run, body)
        self.assertIsNotNone(self.store.read(self.run)['pending_action'])
        self.assertFalse(self.monitor.node(self.run, 'cleaning')['actions']['retry'])

    def test_parallel_eval_retry_preserves_each_mount_and_drops_legacy_robot_config(self):
        run = 'demo-completed-1003'
        expected = {}
        for mid in self.store.read(run)['stages']['evaluation']['members']:
            expected[mid] = 'obs://demo-bucket/robot/' + mid + '/'
            tid = self.store.read(run)['stages']['evaluation']['members'][mid]['task_id']
            path = self.store.directory(run) / 'tasks' / (tid + '.json')
            record = read_json_object(path)
            record['task_config']['inputs'] = json.dumps([{**ROBOT_MOUNT, 'url_path': expected[mid]}])
            record['task_config']['robot_config'] = 'obs://demo-bucket/legacy-robot/'
            atomic_json(path, record)
            self.client.statuses[tid] = 'FAILED'
        for mid, url in expected.items():
            tid = self.store.read(run)['stages']['evaluation']['members'][mid]['task_id']
            self.monitor.refresh_task(run, 'evaluation', mid, self.monitor.node(run, 'evaluation', mid), force=True)
            draft = self.monitor.retry_draft(run, 'evaluation', mid)
            self.assertNotIn('robot_config', draft['config'])
            self.assertEqual([m['url_path'] for m in json.loads(draft['config']['inputs'])], [url])
            body = {'type': 'retry', 'stage': 'evaluation', 'member': mid, 'expected_task_id': tid,
                    'confirmed': True, 'draft_id': draft['draft_id'], 'overrides': {}}
            with patch.object(self.client, 'create_task', wraps=self.client.create_task) as create:
                self.monitor.action(run, body)
            submitted = create.call_args.args[2]
            self.assertNotIn('robot_config', submitted)
            self.assertEqual([m['url_path'] for m in json.loads(submitted['inputs'])], [url])
            self.assertNotEqual(self.monitor.node(run, 'evaluation', mid)['task_id'], tid)

    def test_eval_retry_uses_original_top_level_dataset_without_processing_output_fields(self):
        run = 'demo-completed-1003'
        sid, mid, tid = 'evaluation', 'diversity-eval', 'demo-diversity'
        draft = self.monitor.retry_draft(run, sid, mid)
        self.assertEqual(draft['kind'], 'eval')
        for key in ('output_name', 'head_spec', 'worker_num'):
            self.assertNotIn(key, draft['config'])
        body = {'type': 'retry', 'stage': sid, 'member': mid, 'expected_task_id': tid,
                'confirmed': True, 'draft_id': draft['draft_id'], 'overrides': {}}
        original = copy.deepcopy(draft['config'])
        with patch.object(self.client, 'create_task', wraps=self.client.create_task) as create:
            result = self.monitor.action(run, body)
        create.assert_called_once()
        self.assertEqual(create.call_args.args[0], 'eval')
        submitted = create.call_args.args[2]
        for key in ('dataset_id', 'dataset_name', 'dataset_path', 'dataset_type', 'dataset_configs', 'inputs'):
            self.assertEqual(submitted[key], original[key])
        self.assertIsNone(result['state']['pending_action'])
        node = self.monitor.node(run, sid, mid)
        self.assertEqual(node['attempts'][0]['task_id'], tid)
        record = read_json_object(self.store.directory(run) / 'tasks' / (node['task_id'] + '.json'))
        self.assertNotIn('output_name', record['task_config'])
        self.client.statuses[node['task_id']] = 'FAILED'
        self.monitor.refresh_task(run, sid, mid, node, force=True)
        # An already confirmed data source cannot silently be replaced on retry.
        self.store.mutate(run, lambda state: state['stages']['cleaning'].update(target_version_id='changed-version', target_path='obs://changed/path/'))
        with self.assertRaisesRegex(StateError, '原输入与已核实交接记录不一致'):
            self.monitor.retry_draft(run, sid, mid)

    def test_eval_without_mounts_remains_ready_and_retry_preserves_omission(self):
        for grouped in (False, True):
            run = 'basic-eval-' + str(grouped).lower()
            stage = {'id': 'evaluation', 'kind': 'eval', 'fail_fast': False, 'operator': '数据集多样性评测-LeRobot'}
            if grouped:
                stage = {'id': 'evaluation', 'fail_fast': False,
                         'parallel_group': [{'id': 'diversity', 'operator': '数据集多样性评测-LeRobot'}]}
            state = self.store.init(run, {'inputs': [{'source_type': 'asset', 'asset_id': 'input', 'version_id': 'v1'}],
                                          'stages': [stage]})
            frontier = execution_frontier(self.store.plan(run), state)
            self.assertEqual(frontier['action'], 'submit')
            self.assertNotIn('robot_config', frontier['ready'][0])
        run, sid, mid, tid = 'demo-completed-1003', 'evaluation', 'diversity-eval', 'demo-diversity'
        path = self.store.directory(run) / 'tasks' / (tid + '.json')
        record = read_json_object(path)
        record['task_config'].pop('inputs', None)
        atomic_json(path, record)
        draft = self.monitor.retry_draft(run, sid, mid)
        self.assertNotIn('robot_config', draft['config'])
        self.assertNotIn('inputs', draft['config'])
        body = {'type': 'retry', 'stage': sid, 'member': mid, 'expected_task_id': tid,
                'confirmed': True, 'draft_id': draft['draft_id'], 'overrides': {}}
        with patch.object(self.client, 'create_task', wraps=self.client.create_task) as create:
            self.monitor.action(run, body)
        self.assertNotIn('robot_config', create.call_args.args[2])
        self.assertNotIn('inputs', create.call_args.args[2])
        new_tid = self.monitor.node(run, sid, mid)['task_id']
        self.assertNotIn('inputs', self.monitor.task_detail(run, new_tid)['record']['task_config'])

    def test_init_rejects_removed_robot_config_but_keeps_saved_plans_readable(self):
        stage = {'id': 'evaluation', 'kind': 'eval', 'fail_fast': False, 'operator': '数据集质量评测-LeRobot',
                 'robot_config': 'obs://bucket/robot/'}
        group = {'id': 'evaluation', 'fail_fast': False,
                 'parallel_group': [{'id': 'quality', 'operator': '数据集质量评测-LeRobot', 'robot_config': 'obs://bucket/robot/'}]}
        for index, item in enumerate((stage, group)):
            run = 'removed-robot-config-' + str(index)
            with self.assertRaisesRegex(StateError, 'robot_config 已废弃.*params.inputs'):
                self.store.init(run, {'inputs': [{'source_type': 'asset', 'asset_id': 'input', 'version_id': 'v1'}],
                                      'stages': [item]})
            self.assertFalse((self.store.directory(run) / 'state.json').exists())
        run = 'demo-completed-1003'
        plan = self.store.plan(run)
        next(s for s in plan['stages'] if s['id'] == 'evaluation')['robot_config'] = 'obs://legacy/robot/'
        atomic_json(self.store.directory(run) / 'plan.json', plan)
        self.assertEqual(self.store.plan(run), plan)
        self.monitor.snapshot(run)

    def test_legacy_eval_retry_adds_only_verified_exact_version_and_preserves_history(self):
        run, sid, mid, tid = 'demo-completed-1003', 'evaluation', 'diversity-eval', 'demo-diversity'
        path = self.store.directory(run) / 'tasks' / (tid + '.json')
        record = read_json_object(path)
        record['task_config'].pop('dataset_configs')
        atomic_json(path, record)
        before = path.read_bytes()
        with patch.object(self.client, 'version', wraps=self.client.version) as version:
            draft = self.monitor.retry_draft(run, sid, mid)
        version.assert_called_once_with('demo-ready', 'v1')
        expected = [{'dataset_type': 'BUILD_IN_ASSET', 'asset_id': 'demo-ready', 'version_id': 'v1',
                     'asset_name': 'sim-teleop-cleaned', 'obs_path': 'obs://demo-bucket/training-ready/'}]
        self.assertEqual(json.loads(draft['config']['dataset_configs']), expected)
        self.assertNotIn('dataset_configs', draft['previous_config'])
        self.assertEqual(path.read_bytes(), before)
        body = {'type': 'retry', 'stage': sid, 'member': mid, 'expected_task_id': tid,
                'confirmed': True, 'draft_id': draft['draft_id'], 'overrides': {}}
        with patch.object(self.client, 'create_task', wraps=self.client.create_task) as create:
            self.monitor.action(run, body)
        self.assertEqual(json.loads(create.call_args.args[2]['dataset_configs']), expected)
        self.assertEqual(path.read_bytes(), before)

    def test_eval_retry_rejects_changed_version_even_when_path_and_asset_are_unchanged(self):
        run, sid, mid, tid = 'demo-completed-1003', 'evaluation', 'diversity-eval', 'demo-diversity'
        path = self.store.directory(run) / 'tasks' / (tid + '.json')
        for value in ('different-version', '', None):
            record = read_json_object(path)
            datasets = json.loads(record['task_config']['dataset_configs'])
            datasets[0]['version_id'] = value
            record['task_config']['dataset_configs'] = json.dumps(datasets)
            atomic_json(path, record)
            with self.subTest(value=value), patch.object(self.client, 'create_task') as create:
                with self.assertRaises(StateError):
                    self.monitor.retry_draft(run, sid, mid)
                create.assert_not_called()
        record['task_config'].pop('dataset_configs')
        atomic_json(path, record)
        self.store.mutate(run, lambda state: state['stages']['cleaning'].pop('target_version_id'))
        with self.assertRaisesRegex(StateError, '确切版本'):
            self.monitor.retry_draft(run, sid, mid)

    def test_sdk_failure_releases_reservation(self):
        body = self.retry_body(); original = self.client._call
        def call(service, method, *args, **kwargs):
            if kwargs.get('created'):
                raise SDKError('配额不足')
            return original(service, method, *args, **kwargs)
        self.client._call = call
        with self.assertRaises(SDKError):
            self.monitor.action(self.run, body)
        self.assertIsNone(self.store.read(self.run)['pending_action'])
        self.assertTrue(any(e['type'] == 'action_failed' for e in self.store.events(self.run)))

    def test_operator_not_found_and_metadata_edit_blocked(self):
        body = self.retry_body(); body['overrides']['image'] = 'arbitrary-image'
        with self.assertRaises(StateError):
            self.monitor.action(self.run, body)
        original = self.client._call
        self.client._call = lambda service, method, *args, **kw: {'data': []} if method == 'list_publication_assets' else original(service, method, *args, **kw)
        with self.assertRaises(StateError):
            self.monitor.retry_draft(self.run, 'cleaning')

    def test_stale_queries_disable_mutations(self):
        self.monitor.cache[(self.run, 'demo-clean-1')]['error'] = '认证失败'
        snap = self.monitor.snapshot(self.run)
        self.assertFalse(snap['actions']['terminate'])
        self.assertFalse(next(n for n in snap['nodes'] if n['stage'] == 'cleaning')['actions']['retry'])

    def test_legacy_readonly(self):
        state = self.store.read(self.run); state['schema_version'] = 1
        atomic_json(self.store.directory(self.run) / 'state.json', state)
        snap = self.monitor.snapshot(self.run)
        self.assertTrue(snap['readonly'])
        self.assertFalse(snap['actions']['terminate'])
        with self.assertRaises(StateError):
            self.store.mutate(self.run, lambda s: None)

    def test_output_first_level_merges_files_and_separate_directory_arrays(self):
        base = 'training-ready/'
        fixtures = [
            {'payload': {'item': {'files': ['manifest.yaml'], 'directories': ['data', {'name': 'meta'}],
                                  'folders': [{'path': 'robot/'}], 'common_prefixes': [{'prefix': base + 'videos/'}]}}},
            {'data': {'files': [], 'CommonPrefixes': [{'Prefix': base + 'empty/'}]}}
        ]
        for fixture in fixtures:
            with self.subTest(fixture=fixture), patch.object(self.client, 'frames', return_value=fixture) as query:
                result = self.monitor.frames(self.run, 'demo-convert')
                query.assert_called_once_with('demo-convert', base)
                folders = [item['name'] for item in result['files'] if item['directory']]
                if folders == ['empty']:
                    self.assertEqual(len(result['files']), 1)
                else:
                    self.assertEqual(folders, ['data', 'meta', 'robot', 'videos'])
                    self.assertEqual(result['files'][-1], {'name': 'manifest.yaml', 'key': base + 'manifest.yaml', 'directory': False})

    def test_output_nested_objects_project_to_one_level_and_only_files_preview(self):
        fixture = {'files': ['manifest.yaml', 'data/chunk-000/one.parquet', 'data/chunk-001/two.parquet',
                             {'Key': 'training-ready/videos/camera/front.mp4'}, {'name': 'meta', 'type': 'directory'}],
                   'directories': ['data/']}
        with patch.object(self.client, 'frames', return_value=fixture) as query:
            result = self.monitor.frames(self.run, 'demo-convert')
            self.assertEqual([item['name'] for item in result['files']], ['data', 'meta', 'videos', 'manifest.yaml'])
            query.assert_called_once()
        self.assertEqual(self.monitor.frame_lists[(self.run, 'demo-convert')], {'training-ready/manifest.yaml'})
        with patch.object(self.client, 'preview', return_value={'content': 'manifest'}) as preview:
            for path in ['training-ready/data/', 'training-ready/data/chunk-000/one.parquet']:
                with self.subTest(path=path), self.assertRaisesRegex(StateError, '先从输出文件列表'):
                    self.monitor.preview(self.run, 'demo-convert', path)
            preview.assert_not_called()
            self.monitor.preview(self.run, 'demo-convert', 'training-ready/manifest.yaml')
            preview.assert_called_once_with('proc', 'demo-convert', 'training-ready/manifest.yaml', False)

    def test_output_listing_stays_at_root_and_rejects_other_prefixes(self):
        with patch.object(self.client, 'frames', return_value={'files': ['manifest.yaml']}) as query:
            for prefix in ['training-ready/sub/', 'training-ready-other/', '../training-ready/', 'other/']:
                with self.subTest(prefix=prefix), self.assertRaisesRegex(StateError, '第一层'):
                    self.monitor.frames(self.run, 'demo-convert', prefix)
            query.assert_not_called()
            self.monitor.frames(self.run, 'demo-convert', 'training-ready')
            query.assert_called_once_with('demo-convert', 'training-ready/')
        with patch.object(self.monitor, 'task_detail', return_value={'kind': 'proc', 'live': {'target_path': 'obs://bucket/output'}}), patch.object(self.client, 'frames', return_value={'files': ['manifest.yaml']}) as query:
            self.assertEqual(self.monitor.frames(self.run, 'demo-convert')['base'], 'output/')
            query.assert_called_once_with('demo-convert', 'output/')

    def test_output_listing_rejects_unsafe_entries_and_refresh_clears_old_files(self):
        fixture = {'files': ['manifest.yaml', '', None, 7, {}, 'training-ready/', '../escape', './bad',
                             'data/../../escape', '/absolute', 'obs://other/leak', 'http://example/leak',
                             'bad\\path', {'name': 'plain.txt', 'is_dir': False}], 'dirs': ['empty']}
        with patch.object(self.client, 'frames', return_value=fixture):
            result = self.monitor.frames(self.run, 'demo-convert')
        self.assertEqual([item['name'] for item in result['files']], ['empty', 'manifest.yaml', 'plain.txt'])
        with patch.object(self.client, 'frames', return_value={'files': []}):
            self.assertEqual(self.monitor.frames(self.run, 'demo-convert')['files'], [])
        self.assertEqual(self.monitor.frame_lists[(self.run, 'demo-convert')], set())

    def test_logs_frames_and_summary(self):
        files = self.monitor.logs(self.run, 'demo-clean-1')['files']
        self.assertIn('Killed', self.monitor.log_content(self.run, 'demo-clean-1', files[0]['file_name'], files[0]['file_path'])['content'])
        frames = self.monitor.frames(self.run, 'demo-convert')
        self.assertTrue(frames['files'])
        file = next(item for item in frames['files'] if not item['directory'])
        self.assertIn('rows', self.monitor.preview(self.run, 'demo-convert', file['key']))
        self.assertIn('管线产物', self.monitor.summary('demo-completed-1003'))
        self.assertIn('demo-clean-1', self.monitor.summary('demo-completed-1003'))

    def test_web_queries_and_actions_never_spawn_cli(self):
        with patch('subprocess.run', side_effect=AssertionError('Web must use SDK')), patch('subprocess.Popen', side_effect=AssertionError('Web must use SDK')):
            self.monitor.refresh_all(wait=True)
            self.test_logs_frames_and_summary()
            self.monitor.action(self.run, self.retry_body())
        self.assertEqual(self.client.sequence, 1)

    def test_background_start_port_fallback_reuse_and_stop(self):
        root = Path(self.temp.name) / 'Web 中文 records'
        args = [sys.executable, str(MONITOR / 'server.py'), '--runs-root', str(root)]
        with socket.socket() as occupied:
            occupied.bind(('127.0.0.1', 0)); occupied.listen()
            port = occupied.getsockname()[1]
            started = subprocess.run(args + ['--demo', '--background', '--port', str(port), '--idle-exit', '0'],
                                     capture_output=True, text=True, encoding='utf-8', timeout=10)
            self.assertEqual(started.returncode, 0, started.stderr)
            try:
                path = root / '.monitor.json'
                metadata = json.loads(path.read_text(encoding='utf-8'))
                self.assertNotEqual(metadata['port'], port)
                if os.name != 'nt':
                    self.assertEqual(os.stat(path).st_mode & 0o777, 0o600)
                reused = subprocess.run(args + ['--run', self.run], capture_output=True, text=True, encoding='utf-8', timeout=5)
                self.assertEqual(reused.returncode, 0, reused.stderr)
                self.assertEqual(json.loads(path.read_text(encoding='utf-8'))['pid'], metadata['pid'])
            finally:
                stopped = subprocess.run(args + ['--stop'], capture_output=True, timeout=5)
                self.assertEqual(stopped.returncode, 0, stopped.stderr)
                self.assertFalse((root / '.monitor.json').exists())
                with platform_utils.file_lock(root / '.monitor.lock', blocking=False):
                    pass
                for _ in range(20):
                    if not (root / '.monitor.json').exists():
                        break
                    time.sleep(.05)

    def test_old_service_version_is_diagnosed_and_not_silently_reused(self):
        server = Server(0, self.monitor, 'old-service-test-token')
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        root = self.store.root
        atomic_json(root / '.monitor.json', {'pid': os.getpid(), 'port': server.server_address[1], 'token': server.token})
        args = [sys.executable, str(MONITOR / 'server.py'), '--runs-root', str(root)]
        before = self.store.read(self.run)
        try:
            with patch('server.SOURCE_REVISION', 'previous-build'):
                diagnosed = subprocess.run(args + ['--diagnose'], capture_output=True, text=True, encoding='utf-8', timeout=10)
                self.assertEqual(diagnosed.returncode, 0, diagnosed.stderr)
                data = json.loads(diagnosed.stdout)
                self.assertTrue(data['restart_required'])
                self.assertEqual(data['service_revision'], 'previous-build')
                self.assertNotIn(server.token, diagnosed.stdout)
                started = subprocess.run(args + ['--background'], capture_output=True, text=True, encoding='utf-8', timeout=10)
                self.assertNotEqual(started.returncode, 0)
                self.assertIn('旧监控服务', started.stderr)
            self.assertEqual(self.store.read(self.run), before)
            self.assertEqual(self.client.sequence, 0)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)
            (root / '.monitor.json').unlink(missing_ok=True)

    def test_http_auth_host_csrf_cookie_and_snapshot(self):
        with patch('socket.getfqdn', side_effect=AssertionError('本地服务不应查询 DNS')):
            server = Server(0, self.monitor, 'test-session-secret')
        thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
        port = server.server_address[1]
        def request(method, path, headers=None, body=None):
            connection = HTTPConnection('127.0.0.1', port, timeout=5)
            connection.request(method, path, body=body, headers=headers or {})
            response = connection.getresponse(); content = response.read(); result = response.status, dict(response.getheaders()), content
            connection.close(); return result
        try:
            self.assertEqual(request('GET', '/api/runs')[0], 401)
            self.assertEqual(request('GET', '/', {'Host': 'evil.example'})[0], 403)
            code, headers, _ = request('GET', '/?token=test-session-secret&run=' + self.run)
            self.assertEqual(code, 303); self.assertNotIn('token', headers['Location'])
            self.assertIn('HttpOnly', headers['Set-Cookie']); self.assertIn('SameSite=Strict', headers['Set-Cookie'])
            cookie = {'Cookie': 'pipeline_session=test-session-secret'}
            with patch.object(self.client, '_call') as query:
                self.assertEqual(request('GET', '/api/runs/' + self.run + '/tasks/demo-clean-1/resource-usage', cookie)[0], 404)
                query.assert_not_called()
            code, headers, body = request('GET', '/api/runs/' + self.run, cookie)
            self.assertEqual(code, 200); self.assertNotIn('Access-Control-Allow-Origin', headers)
            snap = json.loads(body)
            self.assertEqual(request('GET', '/api/runs/' + self.run + '?since=' + snap['version'], cookie)[0], 204)
            self.assertEqual(request('POST', '/api/runs/' + self.run + '/actions', cookie, b'{}')[0], 403)
            evil = {**cookie, 'X-Pipeline-Monitor': '1', 'Origin': 'http://evil.example', 'Content-Type': 'application/json'}
            self.assertEqual(request('POST', '/api/runs/' + self.run + '/actions', evil, b'{}')[0], 403)
            code, _, page = request('GET', '/', cookie)
            self.assertEqual(code, 200)
            self.assertIn(b'<script defer src="./bootstrap.js"></script>', page)
            scripts = list((Path(__file__).resolve().parents[1] / 'static').glob('*.js'))
            for script in scripts:
                with self.subTest(script=script.name):
                    self.assertEqual(request('GET', '/' + script.name)[0], 401)
                    code, headers, content = request('GET', '/' + script.name, cookie)
                    self.assertEqual(code, 200)
                    self.assertEqual(headers['Content-Type'], 'text/javascript; charset=utf-8')
                    self.assertEqual(content, script.read_bytes())
            with ThreadPoolExecutor(max_workers=len(scripts)) as pool:
                responses = pool.map(lambda script: request('GET', '/' + script.name, cookie)[0], scripts)
                self.assertEqual(list(responses), [200] * len(scripts))
            self.assertEqual(request('GET', '/unknown.js', cookie)[0], 404)
            self.assertEqual(request('GET', '/server.py', cookie)[0], 404)
            self.assertEqual(request('GET', '/../../etc/passwd', cookie)[0], 404)
        finally:
            server.shutdown(); server.server_close(); thread.join()


if __name__ == '__main__':
    unittest.main(verbosity=2)
