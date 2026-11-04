"""Direct Python SDK access for the Web backend; Agent orchestration stays CLI."""
import copy
from importlib import metadata
import json
import re
import threading
import time

from pipeline_state import JSONValue, StateError, safe_id, validate_task_datasets


class SDKError(StateError):
    code = 502


class UncertainSubmission(SDKError):
    """A task may have been created. Keep pending_action until reconciled."""


def safe_text(value) -> str:
    text = str(value)
    # SDK errors and logs are unstructured, so mask common assignment formats too.
    return re.sub(r'(?i)((?:[\w]*SECRET[\w]*|[\w]*TOKEN[\w]*|[\w]*PASSWORD[\w]*|HUAWEI_CLOUD_AK|HUAWEI_CLOUD_SK|access_key|secret_key|\bAK\b|\bSK\b)[\s\"\x27]*[:=][\s\"\x27]*)([^\s,;\"\x27}]+)', r'\1••••••', text)


def sdk_status() -> dict:
    """Inspect installed distributions only, without loading config or credentials."""
    versions = {}
    for package in ('hw-cloudrobo-core', 'hw-cloudrobo-dataset', 'hw-cloudrobo-asset'):
        try:
            versions[package] = metadata.version(package)
        except metadata.PackageNotFoundError:
            versions[package] = None
    return {'backend': 'sdk', 'available': all(versions.values()), 'versions': versions}


def unwrap(value: JSONValue) -> JSONValue:
    result = value
    if isinstance(value, dict):
        result = value.get('payload', value)
        if isinstance(result, dict) and isinstance(result.get('item'), dict):
            result = result['item']
    return result


def items(value) -> list:
    value = unwrap(value)
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        for key in ('data', 'items', 'files', 'log_files', 'assets', 'list'):
            if isinstance(value.get(key), list):
                return value[key]
            if isinstance(value.get(key), dict):
                return items(value[key])
    return []


def frame_items(value) -> list:
    """Keep directory arrays as well as files, including empty-file responses."""
    if isinstance(value, list):
        return [(item, False) for item in value]
    if not isinstance(value, dict):
        return []
    entries = []
    for key, children in value.items():
        if key in {'payload', 'item', 'data'} and isinstance(children, (dict, list)):
            entries.extend(frame_items(children))
        elif isinstance(children, list):
            if key in {'files', 'items', 'list', 'objects', 'contents', 'Contents'}:
                entries.extend((item, False) for item in children)
            elif key in {'directories', 'folders', 'dirs', 'prefixes', 'common_prefixes',
                         'commonPrefixes', 'CommonPrefixes', 'commonPrefixs'}:
                entries.extend((item, True) for item in children)
    return entries


def frame_entry(value, directory=False) -> tuple:
    if isinstance(value, str):
        return value, directory or value.endswith('/')
    if not isinstance(value, dict):
        return '', False
    name = next((value[key] for key in ('key', 'Key', 'file_name', 'name', 'path', 'prefix', 'Prefix')
                 if isinstance(value.get(key), str) and value[key]), '')
    kind = str(value.get('type', '')).lower()
    marked = value.get('is_dir') is True or value.get('is_directory') is True or value.get('directory') is True
    return name, directory or marked or kind in {'directory', 'folder', 'dir'} or name.endswith('/')


def log_text(value) -> str:
    value = unwrap(value)
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        for key in ('content', 'log_content', 'logs', 'text', 'data'):
            if key in value:
                return log_text(value[key])
    return json.dumps(value, ensure_ascii=False, indent=2)


def obs_key(path) -> str:
    if not isinstance(path, str) or not path.startswith('obs://') or '/' not in path[6:]:
        raise StateError('尚无可用的 OBS 输出路径')
    return path[6:].split('/', 1)[1]


def created_task_result(value) -> dict:
    value = unwrap(value)
    tid = value.get('task_id', value.get('id')) if isinstance(value, dict) else None
    try:
        safe_id(tid)
    except (StateError, TypeError):
        raise UncertainSubmission('SDK 已返回但未能确认新任务 ID。请到智能体核对后恢复，勿重复提交。') from None
    if tid in {'None', 'null'}:
        raise UncertainSubmission('SDK 未返回有效任务 ID；请到智能体核对，勿重复提交。')
    return {'task_id': tid, 'detail': value}


def sdk_session(created=False):
    """Lazy imports keep offline demos and empty run lists dependency-free."""
    try:
        from cloudrobo_core.sdk import Config, HttpClient
        from cloudrobo_dataset.client import DatasetClient
        from cloudrobo_asset.client import AssetClient
    except ImportError:
        raise SDKError('Web 后端缺少或无法加载 CloudRobo SDK。请在启动 server.py 的同一 Python 环境安装兼容的 hw-cloudrobo-core、hw-cloudrobo-dataset、hw-cloudrobo-asset（评测须使用不再要求 robot_config 的版本），然后重启服务；不会回退 CLI。') from None

    class WebHttpClient(HttpClient):
        dispatched = False
        response_status = None

        def request(self, method, url, **kwargs):
            kwargs.setdefault('timeout', (10, 110 if created else 50))
            return super().request(method, url, **kwargs)

        def _do_request(self, method, url, **kwargs):
            # Auth/config failures before HTTP dispatch are definitive. Once a
            # create is sent, a lost/5xx response must retain the reservation.
            self.dispatched = True
            self.response_status = None
            response = super()._do_request(method, url, **kwargs)
            self.response_status = response.status_code
            return response

    transport = WebHttpClient(config=Config(), max_retries=0)
    transport._log_traffic = False  # Never log signed requests or credentials.
    try:
        clients = {'dataset': DatasetClient(transport), 'asset': AssetClient(transport)}
    except Exception:
        transport.close()
        raise
    return transport, clients


class SDK:
    def __init__(self):
        self.slots = threading.BoundedSemaphore(4)

    def _call(self, service, method, *args, created=False, **kwargs) -> JSONValue:
        # Each operation owns its session, so parallel requests never share a
        # requests.Session or alter global workspace/config. All sessions close.
        transport = None
        try:
            with self.slots:
                transport, clients = sdk_session(created)
                operation = getattr(clients[service], method, None)
                if not callable(operation):
                    raise SDKError('当前 SDK 不支持 ' + method + '；请更新启动 Web 的 Python 环境中的 CloudRobo SDK。')
                result = operation(*args, **kwargs)
            return created_task_result(result) if created else unwrap(result)
        except (SDKError, UncertainSubmission):
            raise
        except Exception as error:
            if created and transport is not None:
                if not transport.dispatched and method == 'create_eval_task':
                    request = args[0] if args else {}
                    if 'robot_config' not in request and 'robot_config' in str(error):
                        raise SDKError('当前 SDK 过旧，本地校验仍要求已废弃的 robot_config，本次未发送创建请求。配置文件应通过算子 inputs 挂载传入；请升级 CloudRobo SDK 后再重试。原始错误：'
                                       + safe_text(str(error))[:2000]) from None
            status = getattr(error, 'status_code', None)
            if transport is not None:
                status = status or transport.response_status
            uncertain = created and transport is not None and transport.dispatched and (status is None or status < 400 or status >= 500 or status == 408)
            if uncertain:
                raise UncertainSubmission('SDK 提交结果不确定，平台可能已创建任务。请到智能体按任务名核对，勿重复提交。') from None
            prefix = str(status) + ': ' if status else ''
            raise SDKError('CloudRobo SDK: ' + prefix + safe_text(str(error))[:4000]) from None
        finally:
            if transport is not None:
                transport.close()

    def _method(self, kind, proc, evaluation) -> str:
        if kind not in {'proc', 'eval'}:
            raise StateError('仅支持处理或评测任务')
        return proc if kind == 'proc' else evaluation

    def task_detail(self, kind, task_id) -> JSONValue:
        return self._call('dataset', self._method(kind, 'get_task_detail', 'get_eval_task_detail'), safe_id(task_id))

    def log_files(self, kind, task_id, system=False) -> JSONValue:
        return self._call('dataset', self._method(kind, 'list_log_files', 'list_eval_log_files'), safe_id(task_id), is_system=system)

    def read_log(self, kind, task_id, name, path, full=False) -> JSONValue:
        proc = 'get_task_log' if full else 'get_task_log_tail'
        evaluation = 'get_eval_task_log' if full else 'get_eval_task_log_tail'
        return self._call('dataset', self._method(kind, proc, evaluation), safe_id(task_id), name, file_path=path)

    def frames(self, task_id, prefix) -> JSONValue:
        return self._call('dataset', 'get_task_frames', safe_id(task_id), prefix=prefix)

    def preview(self, kind, task_id, file, download=False) -> JSONValue:
        options = {'is_download': download} if kind == 'eval' else {}
        return self._call('dataset', self._method(kind, 'get_task_preview', 'get_eval_task_preview'), safe_id(task_id), file, **options)

    def operators(self, name) -> JSONValue:
        return self._call('asset', 'list_publication_assets', type='algorithm', exact_name=name)

    def version(self, asset, version) -> JSONValue:
        return self._call('asset', 'show_asset_version', safe_id(asset), safe_id(version))

    def create_task(self, kind, name, config, workspace=None) -> dict:
        validate_task_datasets(config, kind)
        req = copy.deepcopy(config)
        req['name'] = name
        if kind == 'proc':
            req.setdefault('algo_type', 'PRESET_ASSETS')
        return self._call('dataset', self._method(kind, 'create_task', 'create_eval_task'), req, workspace_id=workspace, created=True)


class DemoSDK(SDK):
    """Deterministic SDK-interface simulation; never contacts the platform."""
    def __init__(self):
        super().__init__()
        self.statuses = {'demo-convert': 'SUCCEEDED', 'demo-clean-1': 'FAILED', 'demo-clean-2': 'RUNNING',
                         'demo-quality': 'SUCCEEDED', 'demo-diversity': 'FAILED'}
        self.sequence = 0

    def _call(self, service, method, *args, created=False, **kwargs) -> dict:
        if method == 'list_publication_assets':
            return {'data': [{'asset_id': 'demo-algo-current', 'name': kwargs['exact_name'],
                             'ext_metadata': {'command': 'python main.py',
                                              'engine': {'image_url': 'swr.example.com/cloudrobo/operator:demo'},
                                              'environment_variables': [{'name': 'robot', 'default': 'a2d'}],
                                              'inputs': [{'name': 'ROBOT_CONFIG_PATH', 'input_type': 'MODEL', 'required': False,
                                                          'access_method': 'env'}]}}]}
        if method == 'show_asset_version':
            return {'status': 'RELEASE', 'url': 'obs://demo-bucket/training-ready/' if args[0] == 'demo-ready' else 'obs://demo-bucket/converted/'}
        if created:
            self.sequence += 1
            tid = 'demo-retry-' + str(self.sequence)
            self.statuses[tid] = 'RUNNING'
            return {'task_id': tid, 'detail': {'status': 'RUNNING'}}
        tid = args[0]
        if method in {'get_task_detail', 'get_eval_task_detail'}:
            status = self.statuses.get(tid, 'RUNNING')
            return {'id': tid, 'status': status, 'pod_names': ['demo-worker-0'],
                    'start_at': int(time.time()) - 1100, 'finish_at': int(time.time()) if status in {'FAILED', 'SUCCEEDED'} else None,
                    'error_message': '容器退出码 137；请检查作业日志，并到 CloudRobo Console 查询资源详情（演示数据）' if status == 'FAILED' else '',
                    'target_path': 'obs://demo-bucket/training-ready/' if status == 'SUCCEEDED' else None,
                    'target_report_path': 'obs://demo-bucket/reports/quality.html' if method == 'get_eval_task_detail' and status == 'SUCCEEDED' else None}
        if method in {'list_log_files', 'list_eval_log_files'}:
            name = 'system.log' if kwargs['is_system'] else 'job-std-output.log'
            return {'files': [{'file_name': name, 'file_path': 'proc-task/logs/' + tid + '/' + name}]}
        if method in {'get_task_log', 'get_task_log_tail', 'get_eval_task_log', 'get_eval_task_log_tail'}:
            return {'item': {'content': '\n'.join([
                '10:56:02 INFO  数据清洗任务启动（本地演示）', '10:56:04 INFO  input: converted / v1',
                *['11:01:%02d INFO  processing episode %04d/0960' % (i % 60, i * 13) for i in range(1, 36)],
                '11:02:07 WARN  memory usage 7.8 GiB / 8 GiB',
                '11:02:08 ERROR worker exited: Killed (code 137)' if '1' in tid else '11:08:22 INFO  pipeline worker healthy'])}}
        if method == 'get_task_frames':
            prefix = kwargs['prefix']
            return {'prefix': prefix, 'files': ['manifest.yaml', 'meta/info.json',
                                                'data/chunk-000/episode_000001.parquet'],
                    'directories': [{'name': 'robot'}, {'prefix': prefix + 'videos/'}]}
        if method in {'get_task_preview', 'get_eval_task_preview'}:
            return {'demo': True, 'message': '本地演示预览；真实模式会实时获取平台返回的内容或临时链接。',
                    'file': args[1], 'rows': [{'episode': 1, 'frame': i, 'timestamp': i / 30} for i in range(5)]}
        raise SDKError('演示模式未实现此 SDK 方法')
