#!/usr/bin/env python3
"""Open persisted pipeline runs (an empty list is valid). Use --demo only for an explicit demo request."""
import argparse
import hashlib
from datetime import datetime, timedelta, timezone
import hmac
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import re
import secrets
import signal
from socketserver import TCPServer
import subprocess
import sys
import tempfile
import threading
import time
from urllib.error import URLError
from urllib.parse import parse_qs, quote, unquote, urlsplit
from urllib.request import Request, urlopen
import webbrowser

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pipeline_state import (JSONValue, ROOT, RUN_TERMINAL, StateError, Store, atomic_json,
                            iter_steps, now, read_json_object, redact)
from platform_utils import configure_console, detached_process_options, file_lock, utf8_environment
from sdk_adapter import SDK, DemoSDK, sdk_status, safe_text
from monitor import Monitor

STATIC = Path(__file__).parent / 'static'
STATIC_FILES = {
    '/': ('index.html', 'text/html; charset=utf-8'),
    '/app.css': ('app.css', 'text/css; charset=utf-8'),
    **{f'/{name}.js': (f'{name}.js', 'text/javascript; charset=utf-8')
       for name in ('bootstrap', 'app', 'common', 'state', 'manual', 'pipeline', 'details',
                    'logs', 'preview', 'actions', 'navigation')},
}


def source_revision() -> str:
    root = Path(__file__).resolve().parent
    paths = [root / name for name in ('server.py', 'monitor.py', 'sdk_adapter.py')]
    paths += [root.parent / name for name in ('platform_utils.py', 'pipeline_state.py')]
    paths += [STATIC / name for name in sorted({value[0] for value in STATIC_FILES.values()})]
    digest = hashlib.sha256()
    for path in paths:
        if path.is_file():
            digest.update(path.name.encode('utf-8'))
            digest.update(path.read_bytes())
    return digest.hexdigest()[:16]


SOURCE_REVISION = source_revision()


def browser_data(value: JSONValue) -> JSONValue:
    result = value
    if isinstance(value, dict):
        result = {k: browser_data(v) for k, v in value.items()}
    elif isinstance(value, list):
        result = [browser_data(v) for v in value]
    elif isinstance(value, str) and not re.fullmatch(r'https?://[^\s<>]+', value):
        result = safe_text(value)
    return result


def demo_runs(store):
    base = {'name': 'sim-teleop-cleaning', 'workspace_id': 'ws-demo', 'region': 'cn-southwest-2',
            'inputs': [{'source_type': 'obs', 'obs_path': 'obs://demo-bucket/raw/', 'data_source_type': 'h5', 'robot_type': 'a2d'}],
            'output': {'asset_name': 'sim-teleop-cleaned'}, 'stages': [
                {'id': 'convert-lerobotv3', 'name': '格式转换', 'operator': '数据转换--H5转LeRobotV3'},
                {'id': 'cleaning', 'name': '数据清洗', 'operator': '数据清洗', 'depends_on': ['convert-lerobotv3']},
                {'id': 'evaluation', 'name': '数据评测', 'depends_on': ['cleaning'], 'fail_fast': False,
                 'parallel_group': [{'id': 'quality-eval', 'name': '质量评测', 'operator': '数据集质量评测-LeRobot'},
                                    {'id': 'diversity-eval', 'name': '多样性评测', 'operator': '数据集多样性评测-LeRobot'}]}]}
    config = {'algo_id': 'demo-algo-old', 'algo_name': '数据清洗', 'algo_entrance': 'python main.py',
              'image': 'swr.example.com/cloudrobo/operator:previous', 'algo_type': 'PRESET_ASSETS',
              'cluster_type': 'CCE', 'task_framework_type': 'K8S', 'output_type': 'DATASET',
              'output_path': 'obs://demo-bucket/output/', 'output_name': 'sim-teleop-cleaned',
              'resource_pool_type': 'PUBLIC_POOL', 'worker_spec': {'cpu': 4, 'memory': 8, 'gpu': 0, 'npu': 0},
              'head_spec': {'cpu': 0, 'memory': 0, 'gpu': 0, 'npu': 0}, 'worker_num': 1,
              'envs': '[{"key":"robot","value":"a2d","description":"机器人类型"}]',
              'dataset_configs': '[{"obs_path":"obs://demo-bucket/converted/","asset_id":"demo-dataset","version_id":"v1","asset_name":"converted","dataset_type":"BUILD_IN_ASSET"}]'}
    created_at = (datetime.now(timezone.utc) - timedelta(minutes=72)).isoformat()
    for run, status in [('demo-running-1001', 'RUNNING'), ('demo-awaiting-1002', 'AWAITING_DECISION'),
                        ('demo-completed-1003', 'SUCCEEDED_WITH_WARNINGS')]:
        if (store.directory(run) / 'state.json').exists():
            continue
        plan = base if status != 'SUCCEEDED_WITH_WARNINGS' else {**base, 'inputs': [
            {'source_type': 'asset', 'asset_id': 'demo-raw', 'version_id': 'v1',
             'data_source_type': 'h5', 'robot_type': 'a2d'}]}
        store.init(run, plan)
        def seed(state):
            state['created_at'] = created_at; state['status'] = status
            upload = state['stages']['upload']
            upload.update(target_path='obs://demo-bucket/raw/', target_asset_id='demo-raw', target_version_id='v1')
            if not upload.get('not_applicable'):
                upload['status'] = 'SUCCEEDED'
            for sid, tid in [('convert-lerobotv3', 'demo-convert'),
                             ('cleaning', 'demo-clean-1' if status == 'AWAITING_DECISION' else 'demo-clean-2')]:
                task = state['stages'][sid]
                task.update(task_id=tid, task_name='sim-teleop-' + sid, status='SUCCEEDED' if sid.startswith('convert') else 'FAILED' if status == 'AWAITING_DECISION' else 'RUNNING', started_at=created_at)
                atomic_json(store.directory(run) / 'tasks' / (tid + '.json'), {'task_config': config, 'task_name': task['task_name'], 'by': 'agent', 'at': created_at})
            if status == 'AWAITING_DECISION':
                state['awaiting_decision'] = {'stage': 'cleaning', 'member': None, 'task_id': 'demo-clean-1'}
            else:
                state['stages']['cleaning']['attempts'] = [{'task_id': 'demo-clean-1', 'status': 'FAILED', 'kind': 'proc'}]
                atomic_json(store.directory(run) / 'tasks' / 'demo-clean-1.json', {'task_config': config, 'by': 'agent', 'at': created_at})
            if status == 'SUCCEEDED_WITH_WARNINGS':
                clean = state['stages']['cleaning']; clean.update(task_id='demo-clean-finished', status='SUCCEEDED', target_path='obs://demo-bucket/training-ready/', target_asset_id='demo-ready', target_version_id='v1', output_name='sim-teleop-cleaned')
                atomic_json(store.directory(run) / 'tasks' / 'demo-clean-finished.json', {'task_config': config, 'by': 'agent', 'at': created_at})
                for mid, tid in [('quality-eval', 'demo-quality'), ('diversity-eval', 'demo-diversity')]:
                    state['stages']['evaluation']['members'][mid].update(task_id=tid, status='SUCCEEDED' if mid == 'quality-eval' else 'FAILED')
                    evaluation = {**{k: config[k] for k in ('algo_id', 'algo_name', 'algo_entrance', 'image', 'resource_pool_type', 'worker_spec', 'envs')}, 'dataset_type': 'BUILD_IN_ASSET', 'dataset_id': 'demo-ready', 'dataset_name': 'sim-teleop-cleaned', 'dataset_path': 'obs://demo-bucket/training-ready/'}
                    evaluation['inputs'] = json.dumps([{'name': 'ROBOT_CONFIG_PATH', 'url_path': 'obs://demo-bucket/robot/', 'input_type': 'MODEL', 'required': False, 'access_method': 'env'}])
                    evaluation['dataset_configs'] = json.dumps([{'dataset_type': 'BUILD_IN_ASSET', 'asset_id': 'demo-ready', 'version_id': 'v1', 'asset_name': 'sim-teleop-cleaned', 'obs_path': 'obs://demo-bucket/training-ready/'}])
                    atomic_json(store.directory(run) / 'tasks' / (tid + '.json'), {'task_config': evaluation, 'by': 'agent', 'at': created_at})
                output = {'target_path': 'obs://demo-bucket/training-ready/', 'target_asset_id': 'demo-ready', 'target_version_id': 'v1'}
                state['output'].update(output)
                state['stages']['output'].update(status='SUCCEEDED', **output)
                state['finished_at'] = now()
        store.mutate(run, seed, event_type='demo_loaded', detail='示例数据，仅用于本地交互验证')


class Server(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True
    # Native module imports fan out into parallel localhost connections.
    request_queue_size = 32

    def server_bind(self):
        # HTTPServer's default reverse-DNS lookup can stall local startup for 30+s
        # on corporate DNS/proxy setups. This service has a fixed loopback identity.
        TCPServer.server_bind(self)
        self.server_name = '127.0.0.1'
        self.server_port = self.server_address[1]

    def __init__(self, port, monitor, token=None):
        self.monitor = monitor
        self.token = token or secrets.token_urlsafe(32)
        self.last_request = time.monotonic()
        super().__init__(('127.0.0.1', port), Handler)


class Handler(BaseHTTPRequestHandler):
    server_version = 'PipelineMonitor/1.0'

    def log_message(self, *_):
        # Never put query tokens, presigned report URLs or SDK arguments into logs.
        pass

    def send_data(self, code, data=b'', content_type='application/json; charset=utf-8', headers=None) -> None:
        if not isinstance(data, bytes):
            data = json.dumps(browser_data(redact(data)), ensure_ascii=False).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('X-Frame-Options', 'DENY')
        self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-src 'none'; object-src 'none'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'")
        for key, value in (headers or {}).items():
            self.send_header(key, value)
        self.end_headers()
        if self.command != 'HEAD':
            try:
                self.wfile.write(data)
            except (BrokenPipeError, ConnectionResetError):
                pass

    def gate(self, post=False) -> bool:
        port = self.server.server_address[1]
        host = self.headers.get('Host', '')
        if host not in {f'127.0.0.1:{port}', f'localhost:{port}'}:
            self.send_data(403, {'error': 'Host 不被允许'}); return False
        self.parts = urlsplit(self.path)
        self.query = parse_qs(self.parts.query)
        if not post and self.parts.path == '/' and self.query.get('token'):
            token = self.query['token'][0]
            if hmac.compare_digest(token.encode(), self.server.token.encode()):
                run = self.query.get('run', [''])[0]
                location = '/?run=' + quote(run) if run else '/'
                self.send_data(303, headers={'Location': location,
                               'Set-Cookie': 'pipeline_session=' + self.server.token + '; HttpOnly; SameSite=Strict; Path=/'})
                return False
        cookie = SimpleCookie()
        try:
            cookie.load(self.headers.get('Cookie', ''))
            session = cookie.get('pipeline_session')
            token = session.value if session else ''
        except Exception:
            token = ''
        bearer = self.headers.get('Authorization', '').removeprefix('Bearer ')
        if not (hmac.compare_digest(token.encode(), self.server.token.encode()) or hmac.compare_digest(bearer.encode(), self.server.token.encode())):
            self.send_data(401, {'error': '请使用服务启动时输出的完整地址打开监控页面。'}); return False
        if post:
            origin = self.headers.get('Origin')
            if self.headers.get('X-Pipeline-Monitor') != '1' or origin and origin != 'http://' + host:
                self.send_data(403, {'error': '操作来源校验失败'}); return False
        self.server.last_request = time.monotonic()
        return True

    def do_GET(self) -> None:
        if not self.gate():
            return
        try:
            path = unquote(self.parts.path)
            monitor = self.server.monitor
            if path == '/api/health':
                self.send_data(200, {'ok': True, 'demo': monitor.demo, 'source_revision': SOURCE_REVISION, 'backend': 'demo' if monitor.demo else 'sdk'})
                return
            if path == '/api/runs':
                runs = []
                for run in monitor.run_ids():
                    try:
                        snap = monitor.snapshot(run)
                        runs.append({k: snap[k] for k in ('run_id', 'state', 'progress', 'nodes', 'readonly', 'demo', 'actions')})
                    except (StateError, OSError, ValueError) as error:
                        runs.append({'run_id': run, 'error': str(error)})
                self.send_data(200, {'runs': runs, 'demo': monitor.demo})
                return
            if not path.startswith('/api/'):
                if path not in STATIC_FILES:
                    self.send_data(404, {'error': '页面不存在'})
                    return
                name, mime = STATIC_FILES[path]
                self.send_data(200, (STATIC / name).read_bytes(), mime)
                return
            match = re.fullmatch(r'/api/runs/([^/]+)(?:/(.*))?', path)
            if not match:
                self.send_data(404, {'error': '接口不存在'})
                return
            run, tail = match.groups(); q = lambda key, default='': self.query.get(key, [default])[0]
            if not tail:
                snap = monitor.snapshot(run)
                if q('since') == snap['version']:
                    self.send_data(204)
                    return
                self.send_data(200, snap)
                return
            if tail == 'events':
                self.send_data(200, {'events': [e for e in monitor.store.events(run) if e['seq'] > int(q('after', '0')) and e['type'] != 'heartbeat']})
                return
            if tail == 'summary':
                self.send_data(200, safe_text(monitor.summary(run)).encode(), 'text/markdown; charset=utf-8',
                                      {'Content-Disposition': 'attachment; filename="pipeline-summary.md"'})
                return
            if tail == 'actions/retry/draft':
                self.send_data(200, monitor.retry_draft(run, q('stage'), q('member') or None))
                return
            if tail.startswith('downloads/'):
                name = tail.split('/')[1]
                if not re.fullmatch(r'[a-f0-9]{32}\.log', name):
                    raise StateError('无效的下载文件')
                file = monitor.store.directory(run) / 'logs' / name
                self.send_data(200, file.read_bytes(), 'text/plain; charset=utf-8',
                                      {'Content-Disposition': 'attachment; filename="task.log"'})
                return
            task_match = re.fullmatch(r'tasks/([^/]+)(?:/(.*))?', tail)
            if task_match:
                tid, endpoint = task_match.groups()
                if not endpoint:
                    result = monitor.task_detail(run, tid, q('refresh') == '1')
                elif endpoint == 'logs':
                    result = monitor.logs(run, tid, q('system') == 'true')
                elif endpoint == 'logs/content':
                    result = monitor.log_content(run, tid, q('file'), q('path'), q('all') == '1')
                    if result['bytes'] > 5 * 1024 * 1024:
                        result = {'too_large': True, 'bytes': result['bytes'], 'message': '完整日志超过 5 MB，请下载查看。'}
                elif endpoint == 'frames':
                    result = monitor.frames(run, tid, q('prefix') or None)
                elif endpoint == 'preview':
                    result = monitor.preview(run, tid, q('file') or None, q('download') == '1')
                else:
                    self.send_data(404, {'error': '接口不存在'})
                    return
                self.send_data(200, result)
                return
            self.send_data(404, {'error': '接口不存在'})
        except (StateError, OSError, ValueError, KeyError, TypeError) as error:
            self.send_data(getattr(error, 'code', 404 if isinstance(error, FileNotFoundError) else 400), {'error': str(error)})

    def do_POST(self) -> None:
        if not self.gate(post=True):
            return
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if length < 0 or length > 1024 * 1024 or self.headers.get('Content-Type', '').split(';')[0] != 'application/json':
                raise StateError('需要不超过 1 MB 的 JSON 请求')
            body = json.loads(self.rfile.read(length) or b'{}')
            if not isinstance(body, dict):
                raise StateError('JSON 请求必须为对象')
            if self.parts.path == '/api/shutdown':
                self.send_data(200, {'ok': True})
                threading.Thread(target=self.server.shutdown, daemon=True).start()
                return
            match = re.fullmatch(r'/api/runs/([^/]+)/(actions|delete|tasks/([^/]+)/logs/download)', unquote(self.parts.path))
            if not match:
                self.send_data(404, {'error': '接口不存在'})
                return
            run, endpoint, tid = match.groups(); monitor = self.server.monitor
            if endpoint == 'delete':
                self.send_data(200, monitor.delete_run(run, body))
                return
            if endpoint == 'actions':
                self.send_data(200, monitor.action(run, body))
                return
            data = monitor.log_content(run, tid, body.get('file', ''), body.get('path', ''), full=True)
            name = secrets.token_hex(16) + '.log'
            with monitor.store.locked(run) as run_directory:
                monitor.store.read(run)
                directory = run_directory / 'logs'
                directory.mkdir(exist_ok=True, mode=0o700)
                fd = os.open(directory / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                with os.fdopen(fd, 'w', encoding='utf-8') as file:
                    file.write(safe_text(data['content']))
            self.send_data(200, {'url': '/api/runs/' + quote(run) + '/downloads/' + name, 'bytes': data['bytes']})
        except (StateError, OSError, ValueError, KeyError, TypeError) as error:
            self.send_data(getattr(error, 'code', 404 if isinstance(error, FileNotFoundError) else 400), {'error': str(error)})


def existing(root) -> dict:
    result = {}
    try:
        metadata = read_json_object(root / '.monitor.json')
        port = int(metadata['port'])
        if not 0 < port < 65536:
            raise ValueError('无效的监控端口')
        request = Request(f'http://127.0.0.1:{port}/api/health', headers={'Authorization': 'Bearer ' + metadata['token']})
        with urlopen(request, timeout=2) as response:
            health = json.load(response)
            if isinstance(health, dict) and health.get('ok'):
                result = {**metadata, 'source_revision': health.get('source_revision')}
    except (OSError, ValueError, KeyError, URLError, StateError):
        result = {}
    return result


def serve(args, store, root) -> None:
    if args.demo:
        demo_runs(store)
    client = DemoSDK() if args.demo else SDK()
    if args.demo:
        client.statuses['demo-clean-finished'] = 'SUCCEEDED'
    monitor = Monitor(store, client, demo=args.demo)
    try:
        server = Server(args.port, monitor)
    except OSError:
        server = Server(0, monitor)
    metadata = {'pid': os.getpid(), 'port': server.server_address[1], 'token': server.token,
                'source_revision': SOURCE_REVISION}
    atomic_json(root / '.monitor.json', metadata)
    url = f'http://127.0.0.1:{metadata["port"]}/?token={server.token}' + ('&run=' + quote(args.run) if args.run else '')
    print(url, flush=True)
    if args.open:
        webbrowser.open(url)
    stopped = threading.Event()
    def poll():
        while not stopped.is_set():
            try:
                monitor.refresh_all(wait=True)
                runs = monitor.run_ids()
                if args.idle_exit > 0 and time.monotonic() - server.last_request > args.idle_exit and all(store.read(r).get('status') in RUN_TERMINAL for r in runs):
                    server.shutdown(); return
            except (OSError, StateError, ValueError):
                pass
            stopped.wait(1)
    poll_thread = threading.Thread(target=poll, daemon=True)
    poll_thread.start()
    def stop(*_):
        threading.Thread(target=server.shutdown, daemon=True).start()
    signal.signal(signal.SIGTERM, stop); signal.signal(signal.SIGINT, stop)
    try:
        server.serve_forever(poll_interval=.2)
    finally:
        stopped.set(); server.server_close()
        poll_thread.join()
        monitor.close()
        (root / '.monitor.json').unlink(missing_ok=True)


def main() -> None:
    configure_console()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runs-root', default=None)
    parser.add_argument('--run')
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--open', action='store_true')
    parser.add_argument('--stop', action='store_true')
    parser.add_argument('--background', action='store_true')
    parser.add_argument('--diagnose', action='store_true', help='只读显示服务版本及 SDK 依赖状态；不访问云端')
    parser.add_argument('--demo', action='store_true', help='仅显式演示使用：隔离的模拟数据，不调用云端接口；默认打开真实运行列表')
    parser.add_argument('--idle-exit', type=int, default=1800, help='运行均结束后，无请求自动退出秒数；0 禁用')
    args = parser.parse_args()
    temporary = tempfile.TemporaryDirectory(prefix='cloudrobo-monitor-demo-') if args.demo and not args.runs_root else None
    root = Path(args.runs_root or (temporary.name if temporary else ROOT)).expanduser().resolve()
    store = Store(root)
    current = existing(root)
    if args.diagnose:
        print(json.dumps({'platform': sys.platform, 'python': sys.executable,
                          'source_revision': SOURCE_REVISION,
                          'service_revision': current.get('source_revision'),
                          'service_running': bool(current), 'restart_required': bool(current and current.get('source_revision') != SOURCE_REVISION),
                          **sdk_status(), 'runs_root': str(root)}, ensure_ascii=False, indent=2))
        return
    if args.stop:
        if current:
            request = Request(f'http://127.0.0.1:{current["port"]}/api/shutdown', data=b'{}',
                              headers={'Authorization': 'Bearer ' + current['token'], 'X-Pipeline-Monitor': '1', 'Content-Type': 'application/json'})
            with urlopen(request, timeout=3):
                pass
        deadline = time.monotonic() + 15
        while True:
            try:
                with file_lock(root / '.monitor.lock', blocking=False):
                    break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    raise SystemExit('停止请求已发出，监控仍在结束接口处理；请稍后重试 --stop，关闭完成后再启动。不会停止云端任务。') from None
                time.sleep(.1)
        print('监控服务已停止' if current else '没有运行中的监控服务')
        return
    if current:
        if current.get('source_revision') != SOURCE_REVISION:
            raise SystemExit('检测到旧监控服务，尚未加载当前修复。请对同一 runs-root 执行 server.py --stop 后重新启动；运行记录保留，不会停止云端任务。')
        url = f'http://127.0.0.1:{current["port"]}/?token={current["token"]}' + ('&run=' + quote(args.run) if args.run else '')
        print(url, flush=True)
        if args.open:
            webbrowser.open(url)
        return
    if args.background:
        command = [sys.executable, str(Path(__file__).resolve()), '--runs-root', str(root), '--port', str(args.port), '--idle-exit', str(args.idle_exit)]
        if args.run:
            command += ['--run', args.run]
        if args.demo:
            command += ['--demo']
        if args.open:
            command += ['--open']
        with tempfile.TemporaryFile() as errors:
            process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                       stderr=errors, env=utf8_environment(), **detached_process_options())
            for _ in range(300):
                time.sleep(.1)
                if process.poll() is not None:
                    errors.seek(0)
                    error = errors.read().decode('utf-8', errors='replace')
                    raise SystemExit('后台服务启动失败：' + safe_text(error[-4000:]))
                current = existing(root)
                if current:
                    print(f'http://127.0.0.1:{current["port"]}/?token={current["token"]}' + ('&run=' + quote(args.run) if args.run else ''), flush=True)
                    if temporary:
                        temporary._finalizer.detach()  # The detached server owns this demo root.
                    return
            process.terminate()
            process.wait(timeout=5)
        raise SystemExit('后台服务 30 秒内未能启动，已停止该进程；请去掉 --background 查看错误')
    try:
        with file_lock(root / '.monitor.lock', blocking=False):
            serve(args, store, root)
    except BlockingIOError:
        raise SystemExit('另一个监控进程正在启动，请稍后重试') from None
    finally:
        if temporary:
            temporary.cleanup()


if __name__ == '__main__':
    main()
