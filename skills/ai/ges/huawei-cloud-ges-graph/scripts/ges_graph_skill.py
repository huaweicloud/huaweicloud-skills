#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GES Memory Skill - 图引擎持久化版原子能力
用于LLM记忆系统的图数据库操作：添加节点、关系、查询、导入导出等
"""

import os
import csv
import json
import re
import time
import random
import threading
import requests
from typing import Dict, List, Optional, Any, Union

# 项目根目录
CURRENT_FILE = os.path.abspath(__file__)
SKILL_DIR = os.path.dirname(os.path.dirname(CURRENT_FILE))  # skill根目录（SKILL.md所在目录）
SCRIPTS_DIR = os.path.dirname(CURRENT_FILE)                  # scripts/
SKILLS_DIR = os.path.dirname(SKILL_DIR)     # skills
CODEMATE_DIR = os.path.dirname(SKILLS_DIR)  # .codemate
PROJECT_ROOT = os.path.dirname(CODEMATE_DIR)  # ges_skill (项目根目录)

# ====================================================================
# 通用工具：超时重试 + 优雅降级（ISSUE-001）
# ====================================================================

DEFAULT_TIMEOUT = 30
DEFAULT_MAX_RETRIES = 3
RETRYABLE_STATUS = {408, 429, 500, 502, 503, 504}
RETRYABLE_EXCEPTIONS = (requests.exceptions.Timeout,
                        requests.exceptions.ConnectionError,
                        requests.exceptions.ConnectTimeout,
                        requests.exceptions.ReadTimeout)


def request_with_retry(method: str, url: str, max_retries: int = DEFAULT_MAX_RETRIES,
                       timeout: int = DEFAULT_TIMEOUT, **kwargs) -> requests.Response:
    """带指数退避重试的 HTTP 请求。

    对超时、连接错误以及 5xx/408/429 等瞬时错误进行最多 ``max_retries`` 次重试，
    重试间隔采用指数退避 + 抖动。用户显式传入的 timeout 覆盖默认值。
    """
    kwargs.setdefault('timeout', timeout)
    attempt = 0
    last_exc = None
    while True:
        try:
            resp = requests.request(method, url, **kwargs)
            if resp.status_code in RETRYABLE_STATUS and attempt < max_retries:
                _sleep_backoff(attempt)
                attempt += 1
                continue
            return resp
        except RETRYABLE_EXCEPTIONS as e:
            last_exc = e
            if attempt >= max_retries:
                break
            _sleep_backoff(attempt)
            attempt += 1
    raise last_exc


def _sleep_backoff(attempt: int):
    base = 0.5 * (2 ** attempt)  # 0.5s, 1s, 2s, ...
    time.sleep(base + random.uniform(0, 0.25))


# ====================================================================
# Cypher 安全防护（ISSUE-002）— 危险操作模式检测 + 输入校验
# ====================================================================

# 危险操作正则：破坏性语句（无 WHERE 限定的全量删除/清空、DROP、移除约束/索引）
DANGEROUS_CYPHER_PATTERNS = [
    # MATCH (n) DETACH DELETE n / MATCH ()-[r]->() DELETE r 等全量删除
    re.compile(r'^\s*MATCH\s*\([^)]*\).*DETACH\s+DELETE', re.IGNORECASE | re.DOTALL),
    re.compile(r'^\s*MATCH\s*\([^)]*\)(\s*)-\[\s*[^]]*\s*\]-\s*\([^)]*\).*DELETE', re.IGNORECASE | re.DOTALL),
    # DROP（删除 schema/索引/约束/标签，无 WHERE 限定即视为危险）
    re.compile(r'\bDROP\s+(?:ALL|LABEL|INDEX|CONSTRAINT|SCHEMA|GRAPH|DATABASE)', re.IGNORECASE),
    # 显式的全量清空语句
    re.compile(r'DETACH\s+DELETE\s+ALL', re.IGNORECASE),
    re.compile(r'^\s*DELETE\s+ALL\b', re.IGNORECASE),
]

# 危险关键字（配合是否带 WHERE/id 限定判断）
DANGEROUS_KEYWORDS = {
    'DETACH DELETE',
    'DELETE',
    'DROP',
    'TRUNCATE',
    'REMOVE ALL',
}

# 需要显式确认的 Cypher 关键字（写出 Safari 但受限于特定 id 实例允许）
CONFIRM_REQUIRED_KEYWORDS = {
    'DETACH DELETE',
    'CALL dbms.killQuery',
}


class CypherSafetyError(Exception):
    """Cypher 语句未通过安全校验时抛出。"""


def validate_cypher(statement: str, allow_destructive: bool = False,
                    context: str = 'execute_query') -> None:
    """对 Cypher 语句做代码层安全校验（ISSUE-002）。

    校验内容：
    1. 非字符串输入直接拒绝；
    2. 危险操作模式检测：无显式 ``allow_destructive=True`` 时，拒绝全量
       DETACH DELETE / DELETE / DROP / TRUNCATE 等破坏性语句；
    3. 危险关键字限定校验：带 WHERE id(...)=$var 的定向删除（等业务无法
       预判的合法删除），仍禁止全量清空形态。

    Args:
        statement: 待校验的 Cypher 语句。
        allow_destructive: 是否允许破坏性语句（如需清空整图请走
            ``clear_graph(use_api=True)`` 专用接口并取得用户确认）。
        context: 调用方上下文标识（仅用于错误提示）。

    Raises:
        CypherSafetyError: 未通过安全校验。
    """
    if not isinstance(statement, str) or not statement.strip():
        raise CypherSafetyError(
            f"[{context}] Cypher 语句必须是非空字符串，收到: {type(statement).__name__}"
        )
    if allow_destructive:
        return

    s = statement.strip()
    low = s.upper()

    # 判定是否为"定向操作"（WHERE 限定到具体 id() / element_id()），
    # 定向删除等业务操作放行，未限定范围的全量操作拒绝
    has_where = re.search(r'\bWHERE\b', low) is not None
    has_id_scope = ('ID(' in low) or ('ELEMENT_ID(' in low)
    scoped = has_where and has_id_scope

    # 1) 显式危险模式（匹配即拒绝）；定向(MATCH...WHERE id)...DELETE 除外
    for pat in DANGEROUS_CYPHER_PATTERNS:
        if pat.search(s):
            if scoped and ('DELETE' in pat.pattern.upper() or ' DETACH' in pat.pattern.upper()):
                # 带 WHERE ... id(...) 的定向删除放行（delete_node/delete_edge 等）
                continue
            raise CypherSafetyError(
                f"[{context}] 检测到危险 Cypher 操作模式 '{pat.pattern[:40]}...'。"
                "该操作可能清空或破坏图数据。如确需执行，请显式传 "
                "allow_destructive=True（并先在 SKILL.md 安全护栏中取得用户确认）。"
            )

    # 2) 危险关键字 + 全量形态判断（匹配 DETACH DELETE / DELETE / DROP 但无
    #    WHERE 限定的定向目标时拒绝；带 WHERE ... id(n) 的定向删除允许）
    for kw in DANGEROUS_KEYWORDS:
        if kw in low:
            # 若存在 WHERE 且包含 id( / element_id( 限定，视为定向删除，放行
            if scoped:
                continue
            raise CypherSafetyError(
                f"[{context}] 检测到未限定的 '{kw}' 操作，可能破坏图数据。"
                "定向增删改请使用 WHERE ... id(n)=... 限定；全量操作请走 "
                "clear_graph() 单独接口并取得用户确认。"
            )


def validate_property_values(properties: Optional[Dict]) -> None:
    """校验属性值类型（ISSUE-002/ISSUE-010）。

    仅允许 JSON 原生标量（str/int/float/bool/None），拒绝 dict/list/bytes 等
    可能被误用为查询片段的对象，避免注入。
    """
    if not properties:
        return
    if not isinstance(properties, dict):
        raise CypherSafetyError(f"属性必须是字典，收到: {type(properties).__name__}")
    for k, v in properties.items():
        if v is None or isinstance(v, (str, int, float, bool)):
            continue
        raise CypherSafetyError(
            f"属性 '{k}' 的值类型不支持: {type(v).__name__}。"
            "仅允许 str/int/float/bool/None 等 JSON 标量。"
        )


class EnvConfig:
    """环境配置管理 - 支持环境变量和配置文件读取"""

    ENV_DIR = os.path.join(SKILL_DIR, 'config')

    ENV_VAR_MAPPING = {
        'GES_GRAPH_IP': 'graph_ip',
        'GES_GRAPH_PORT': 'graph_port',
        'GES_PROJECT_ID': 'project_id',
        'GES_GRAPH_NAME': 'graph_name',
        'GES_IAM_URL': 'iam_url',
        'GES_USERNAME': 'username',
        'GES_PASSWORD': 'password',
        'GES_DOMAIN_NAME': 'domain_name',
        'GES_REGION': 'region',
        'HUAWEI_CLOUD_AK': 'access_key',
        'HUAWEI_CLOUD_SK': 'secret_key',
    }

    @staticmethod
    def load_ges_env() -> Dict[str, str]:
        """加载GES环境配置，优先从环境变量读取，备用从 config 目录的 ges_env.csv 文件读取"""
        config = {}

        env_file = os.path.join(EnvConfig.ENV_DIR, 'ges_env.csv')
        file_config = EnvConfig._load_csv(env_file)

        for env_var, config_key in EnvConfig.ENV_VAR_MAPPING.items():
            env_value = os.environ.get(env_var)
            if env_value:
                config[config_key] = env_value
            elif file_config.get(config_key):
                config[config_key] = file_config.get(config_key)

        for key, value in file_config.items():
            if key not in config:
                config[key] = value

        required_fields = ['graph_ip', 'project_id', 'graph_name', 'iam_url', 'username', 'password', 'domain_name', 'region']
        missing_fields = [field for field in required_fields if not config.get(field)]

        if missing_fields:
            print('==============================================')
            print('⚠️  配置缺失或不完整')
            print('==============================================')
            print('\n请通过以下方式配置（环境变量优先）：')
            print('  - 环境变量: GES_GRAPH_IP, GES_PROJECT_ID, GES_GRAPH_NAME, GES_IAM_URL, GES_REGION')
            print('  - AKSK: HUAWEI_CLOUD_AK, HUAWEI_CLOUD_SK')
            print('  - 或用户名密码: GES_USERNAME, GES_PASSWORD, GES_DOMAIN_NAME')
            print('  - 或配置文件: config/ges_env.csv')
            print('\n缺失的必需配置项:')
            for field in missing_fields:
                print(f'  - {field}')
            print('==============================================\n')

        return config

    @staticmethod
    def _load_csv(filepath: str) -> Dict[str, str]:
        """读取CSV配置文件"""
        config = {}
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    config[row['key']] = row['value']
        return config


class TokenManager:
    """Token管理 - 支持AKSK方式获取Token"""

    def __init__(self):
        self.token = None
        self.token_expiry = 0
        self.config = EnvConfig.load_ges_env()

    def get_token(self) -> str:
        """获取Token，如果过期则重新获取"""
        current_time = time.time()
        if self.token and current_time < self.token_expiry - 300:
            return self.token

        env_token = os.environ.get('GES_TOKEN')
        if env_token:
            self.token = env_token
            self.token_expiry = time.time() + 3600 * 23
            return self.token

        access_key = self.config.get('access_key')
        secret_key = self.config.get('secret_key')

        if access_key and secret_key:
            try:
                self.token = self._fetch_token_by_aksk()
                return self.token
            except Exception as e:
                print(f"AKSK方式获取Token失败，尝试密码方式: {e}")

        username = self.config.get('username')
        password = self.config.get('password')
        domain_name = self.config.get('domain_name')

        if username and password:
            try:
                self.token = self._fetch_token_by_password(username, password, domain_name)
                return self.token
            except Exception as e:
                raise Exception(f"密码方式获取Token也失败了: {e}")

        raise Exception("无法获取Token，请配置AKSK或用户名密码")

    def _fetch_token_by_password(self, username: str, password: str, domain_name: str = None) -> str:
        """通过密码方式获取Token"""
        url = self.config.get('iam_url')
        project_id = self.config.get('project_id')

        if not url:
            raise Exception("ges_env.csv中缺少iam_url配置")

        headers = {'Content-Type': 'application/json'}

        # 构建请求体
        if domain_name:
            data = {
                'auth': {
                    'identity': {
                        'methods': ['password'],
                        'password': {
                            'user': {
                                'name': username,
                                'password': password,
                                'domain': {'name': domain_name}
                            }
                        }
                    },
                    'scope': {'project': {'id': project_id}}
                }
            }
        else:
            data = {
                'auth': {
                    'identity': {
                        'methods': ['password'],
                        'password': {
                            'user': {
                                'name': username,
                                'password': password
                            }
                        }
                    },
                    'scope': {'project': {'id': project_id}}
                }
            }

        resp = requests.post(url, headers=headers, json=data, timeout=30, verify=False)

        if resp.status_code not in [200, 201]:
            raise Exception(f"密码获取Token失败: {resp.status_code}, {resp.text[:200]}")

        token = resp.headers.get('X-Subject-Token')
        if not token:
            raise Exception(f"密码获取Token失败，未获取到token: {resp.text[:200]}")

        self.token_expiry = time.time() + 3600 * 23
        return token

    def _fetch_token_by_aksk(self) -> str:
        """通过AKSK方式获取Token"""
        import hashlib
        import hmac
        import datetime

        access_key = self.config.get('access_key')
        secret_key = self.config.get('secret_key')
        project_id = self.config.get('project_id')
        url = self.config.get('iam_url')
        region = self.config.get('region', 'cn-north-7')

        if not url:
            raise Exception("ges_env.csv中缺少iam_url配置")

        Service = 'iam'
        ContentType = 'application/json;charset=UTF-8'

        # 构建请求体
        Body = '{"auth": {"identity": {"methods": ["hw_access_key"],"hw_access_key": {"access": {"key": "' + access_key + '"}}},"scope": {"project": {"id": "' + project_id + '"}}}}'

        # 签名计算
        BasicDateFormat = "%Y%m%dT%H%M%SZ"
        ScopeDateFormat = "%Y%m%d"
        Algorithm = "HWS-HMAC-SHA256"

        def sign(key, msg):
            return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()

        def getSignatureKey(key, date_stamp, region, service):
            kDate = sign(('HWS' + key).encode('utf-8'), date_stamp)
            kRegion = sign(kDate, region)
            kService = sign(kRegion, service)
            kSigning = sign(kService, 'hws_request')
            return kSigning

        t = datetime.datetime.utcnow()
        hws_date = t.strftime(BasicDateFormat)
        date_stamp = t.strftime(ScopeDateFormat)
        canonical_uri = '/v3/auth/tokens/'
        canonical_headers = 'accept:' + 'application/json' + '\n' + 'content-type:' + ContentType + '\n' + 'x-hws-date:' + hws_date + '\n'
        signed_headers = 'accept;content-type;x-hws-date'
        payload_hash = hashlib.sha256(Body.encode('utf-8')).hexdigest()
        canonical_request = '\n'.join(
            ['POST', canonical_uri, '', canonical_headers, signed_headers, payload_hash])
        credential_scope = '/'.join([date_stamp, region, Service, 'hws_request'])
        string_to_sign = '\n'.join(
            [Algorithm, hws_date, credential_scope, hashlib.sha256(canonical_request.encode('utf-8')).hexdigest()])
        signing_key = getSignatureKey(secret_key, date_stamp, region, Service)
        signature = hmac.new(signing_key, string_to_sign.encode('utf-8'), hashlib.sha256).hexdigest()
        authorization_header = Algorithm + ' ' + 'Credential=' + access_key + '/' + credential_scope + ', ' + 'SignedHeaders=' + signed_headers + ', ' + 'Signature=' + signature

        headers = {
            'Accept': 'application/json',
            'Content-Type': ContentType,
            'X-Hws-Date': hws_date,
            'X-Identity-Sign': authorization_header
        }

        resp = requests.post(url, data=Body, headers=headers, timeout=30, verify=False)

        if resp.status_code not in [200, 201]:
            raise Exception(f"AKSK获取Token失败: {resp.status_code}, {resp.text[:200]}")

        token = resp.headers.get('X-Subject-Token')
        if not token:
            raise Exception(f"AKSK获取Token失败，未获取到token: {resp.text[:200]}")

        self.token_expiry = time.time() + 3600 * 23  # Token有效期通常是24小时
        return token


class OBSClient:
    """华为云OBS对象存储客户端 (使用HMAC-SHA1签名，不依赖SDK)

    虚拟主机URL格式: https://bucketname.obs.region.domain/objectkey

    签名算法: Authorization: OBS AccessKeyID:Signature
    其中: Signature = Base64(HMAC-SHA1(Your_SK, UTF8(StringToSign)))

    StringToSign格式:
    - 无Content-Type: METHOD\n\n\nDate\n/bucket/key (3个换行)
    - 有Content-Type: METHOD\n\nContent-Type\nDate\n/bucket/key
    """

    def __init__(self, access_key: str, secret_key: str, region: str = "cn-north-7"):
        """初始化OBS客户端

        Args:
            access_key: OBS访问密钥
            secret_key: OBS秘密密钥
            region: OBS区域
        """
        self.access_key = access_key
        self.secret_key = secret_key
        self.region = region
        self.server = f"obs.{region}.ulanqab.huawei.com"
        self._available = bool(access_key and secret_key)

        # 禁用SSL警告
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    def is_available(self) -> bool:
        """检查OBS是否可用"""
        return bool(self._available)

    def _require_available(self):
        """统一可用性检查（ISSUE-009：list_objects 与其他方法一致）"""
        if not self.is_available():
            raise Exception("OBS客户端不可用，请配置 access_key/secret_key 后重试")

    def _get_signature(self, method: str, bucket: str, object_key: str,
                       content_type: str = '', date: str = None) -> tuple:
        """计算OBS签名

        Returns:
            (signature, date)
        """
        import hmac
        import hashlib
        import base64
        from datetime import datetime

        if date is None:
            date = datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT')

        # 签名的path
        sign_path = f'/{bucket}/{object_key}' if object_key else f'/{bucket}/'

        if content_type:
            # 有Content-Type时的签名格式: METHOD\n\nContent-Type\nDate\n/path
            string_to_sign = f'{method}\n\n{content_type}\n{date}\n{sign_path}'
        else:
            # 无Content-Type时的签名格式: METHOD\n\n\nDate\n/path (3个换行)
            string_to_sign = f'{method}\n\n\n{date}\n{sign_path}'

        # HMAC-SHA1签名
        h = hmac.new(self.secret_key.encode('utf-8'), string_to_sign.encode('utf-8'), hashlib.sha1)
        signature = base64.b64encode(h.digest()).decode('utf-8')

        return signature, date

    def _request(self, method: str, bucket: str, object_key: str = '',
                 query: dict = None, headers: dict = None, body: bytes = None):
        """发起OBS请求"""
        import urllib.parse
        import requests

        # 构造URL
        path = f'/{object_key}' if object_key else '/'

        # 添加查询参数
        if query:
            query_string = '&'.join([f'{k}={urllib.parse.quote(str(v))}' for k, v in query.items()])
            full_path = f'{path}?{query_string}'
        else:
            full_path = path

        url = f'https://{bucket}.{self.server}{full_path}'

        # 构建请求头
        content_type = headers.get('Content-Type', '') if headers else ''
        signature, date = self._get_signature(method, bucket, object_key, content_type)

        request_headers = {
            'Host': f'{bucket}.{self.server}',
            'Date': date,
            'Authorization': f'OBS {self.access_key}:{signature}'
        }

        if headers:
            for k, v in headers.items():
                request_headers[k] = str(v) if k == 'Content-Length' else v

        # 发送请求
        response = request_with_retry(
            method=method,
            url=url,
            headers=request_headers,
            data=body,
            verify=False
        )

        if response.status_code >= 400:
            raise Exception(f'OBS请求失败 [{response.status_code}]: {response.text}')

        return response

    def list_buckets(self) -> List[str]:
        """列举所有桶"""
        self._require_available()
        # 暂不支持桶列表
        return []

    def list_objects(self, bucket: str, prefix: str = "") -> List[Dict]:
        """列举桶中的对象

        Args:
            bucket: 桶名
            prefix: 对象前缀

        Returns:
            对象列表 (包含Key, Size等信息)
        """
        self._require_available()

        response = self._request(
            method='GET',
            bucket=bucket,
            object_key='',
            query={'list-type': '2', 'prefix': prefix}
        )

        # 解析XML响应
        import re
        contents = []
        for match in re.finditer(r'<Contents><Key>([^<]+)</Key><LastModified>([^<]+)</LastModified><ETag>([^<]+)</ETag><Size>(\d+)</Size>', response.text):
            contents.append({
                'Key': match.group(1),
                'LastModified': match.group(2),
                'ETag': match.group(3),
                'Size': int(match.group(4))
            })
        return contents

    def upload_file(self, local_file: str, bucket: str, object_key: str) -> bool:
        """上传本地文件到OBS

        Args:
            local_file: 本地文件路径
            bucket: 目标桶名
            object_key: OBS中的对象键

        Returns:
            是否成功
        """
        self._require_available()

        import os
        if not os.path.exists(local_file):
            raise Exception(f"文件不存在: {local_file}")

        with open(local_file, 'rb') as f:
            file_content = f.read()

        self._request(
            method='PUT',
            bucket=bucket,
            object_key=object_key,
            headers={
                'Content-Type': 'application/octet-stream',
                'Content-Length': len(file_content)
            },
            body=file_content
        )
        return True

    def download_file(self, bucket: str, object_key: str, local_file: str) -> bool:
        """从OBS下载文件到本地

        Args:
            bucket: 桶名
            object_key: OBS中的对象键
            local_file: 本地保存路径

        Returns:
            是否成功
        """
        self._require_available()

        response = self._request(
            method='GET',
            bucket=bucket,
            object_key=object_key
        )

        with open(local_file, 'wb') as f:
            f.write(response.content)
        return True

    def delete_object(self, bucket: str, object_key: str) -> bool:
        """删除OBS中的对象

        Args:
            bucket: 桶名
            object_key: OBS中的对象键

        Returns:
            是否成功
        """
        self._require_available()

        self._request(
            method='DELETE',
            bucket=bucket,
            object_key=object_key
        )
        return True

    def get_object_url(self, bucket: str, object_key: str) -> str:
        """获取对象URL

        Args:
            bucket: 桶名
            object_key: OBS中的对象键

        Returns:
            对象的公开URL
        """
        return f'https://{bucket}.{self.server}/{object_key}'


class GESClient:
    """GES图数据库API客户端

    支持 dry-run 模式：设置环境变量 ``GES_DRY_RUN=1``（或 ``GES_MOCK=1``）
    时不发起真实网络请求，返回模拟响应，用于无 GES 实例环境下的功能验证
    （ISSUE-007）。
    """

    def __init__(self):
        self.token_mgr = TokenManager()
        self.config = EnvConfig.load_ges_env()
        self.graph_ip = self.config.get('graph_ip', '')
        self.graph_port = self.config.get('graph_port', '80')
        self.project_id = self.config.get('project_id', '')
        self.graph_name = self.config.get('graph_name', '')
        self.base_url = f"http://{self.graph_ip}:{self.graph_port}/ges/v1.0/{self.project_id}/graphs/{self.graph_name}"
        self.dry_run = os.environ.get('GES_DRY_RUN', os.environ.get('GES_MOCK', '')).strip().lower() in ('1', 'true', 'yes')

        # 初始化OBS客户端
        access_key = self.config.get('access_key', '')
        secret_key = self.config.get('secret_key', '')
        region = self.config.get('region', 'cn-north-7')
        if access_key and secret_key:
            self.obs_client = OBSClient(access_key, secret_key, region)
        else:
            self.obs_client = None

    def get_obs_client(self) -> Optional[OBSClient]:
        """获取OBS客户端"""
        return self.obs_client

    def _get_headers(self) -> Dict[str, str]:
        """获取请求头"""
        return {
            'X-Auth-Token': self.token_mgr.get_token(),
            'Content-Type': 'application/json'
        }

    def _request(self, method: str, path: str, **kwargs) -> Dict:
        """发送API请求（带超时重试 + 优雅降级，ISSUE-001）

        支持 dry-run 模式（GES_DRY_RUN=1），不发起真实网络请求。
        """
        if self.dry_run:
            return self._dry_run_response(method, path, kwargs.get('json'))

        url = f"{self.base_url}{path}"
        headers = self._get_headers()

        resp = request_with_retry(method, url, headers=headers, **kwargs, verify=False)

        if resp.status_code >= 400:
            raise Exception(f"API请求失败 [{resp.status_code}]: {resp.text}")

        try:
            return resp.json()
        except:
            return {'raw': resp.text}

    def _dry_run_response(self, method: str, path: str, body: Any = None) -> Dict:
        """dry-run 模拟响应：返回与真实 API 结构一致的占位结果。"""
        action = ''
        if 'action_id=' in path:
            action = path.split('action_id=')[-1]
        elif '/jobs/' in path:
            action = 'job-status'
        elif '/schema' in path:
            action = 'schema'
        elif '/summary' in path:
            action = 'summary'
        elif '/indices' in path:
            action = 'indices'

        if action == 'execute-cypher-query' or action == 'execute-gql-query':
            return {
                'results': [{'columns': ['n'], 'data': [{'row': [{'name': '__dry_run__'}], 'meta': [None]}]}],
                'errors': []
            }
        if action == 'job-status':
            return {'jobId': 'dry-run-job', 'status': 'complete'}
        if action == 'clear-graph':
            return {'jobId': 'dry-run-clear', 'status': 'success'}
        if action == 'schema':
            return {'results': [{'data': [{'row': [{'properties': []}]}]}]}
        if action == 'summary' or action == 'get_graph_summary':
            return {'nodeCount': 0, 'edgeCount': 0}
        if action == 'indices':
            return {'status': 'success', 'indices': []}
        # 其他 action（export/import 等）返回 jobId
        return {'jobId': f'dry-run-{action or "ok"}', 'status': 'success'}

    # ==================== Cypher查询相关API ====================

    def execute_cypher(self, statement: str, parameters: Dict = None,
                       execution_mode: str = "sync", result_data_contents: str = "row",
                       limit: int = 1000, allow_destructive: bool = False) -> Dict:
        """执行Cypher查询

        Args:
            statement: Cypher查询语句
            parameters: 查询参数（可选）
            execution_mode: 执行模式，sync/async（默认sync）
            result_data_contents: 返回格式，row/graph/raw（默认row）
            limit: 返回结果数量限制（默认1000）
            allow_destructive: 是否允许破坏性语句（默认False，ISSUE-002 安全校验）

        Returns:
            API响应结果
        """
        validate_cypher(statement, allow_destructive=allow_destructive, context='execute_cypher')
        validate_property_values(parameters)
        data = {
            "statements": [{
                "statement": statement,
                "parameters": parameters or {},
                "executionMode": execution_mode,
                "resultDataContents": [result_data_contents],
                "limit": limit
            }]
        }

        return self._request('POST', '/action?action_id=execute-cypher-query', json=data)

    def execute_gql(self, statement: str, parameters: Dict = None,
                    execution_mode: str = "sync", result_data_contents: str = "row",
                    limit: int = 1000, include_stats: bool = True,
                    allow_destructive: bool = False) -> Dict:
        """执行GQL查询

        Args:
            statement: GQL查询语句
            parameters: 查询参数（可选）
            execution_mode: 执行模式，sync/async（默认sync）
            result_data_contents: 返回格式，row/graph/raw（默认row）
            limit: 返回结果数量限制（默认1000）
            include_stats: 是否包含统计信息（默认True）
            allow_destructive: 是否允许破坏性语句（默认False，ISSUE-002 安全校验）

        Returns:
            API响应结果
        """
        validate_cypher(statement, allow_destructive=allow_destructive, context='execute_gql')
        validate_property_values(parameters)
        data = {
            "statements": [{
                "statement": statement,
                "parameters": parameters or {},
                "executionMode": execution_mode,
                "resultDataContents": [result_data_contents],
                "limit": limit,
                "includeStats": include_stats
            }]
        }

        return self._request('POST', '/action?action_id=execute-gql-query', json=data)

    def execute_gql_async(self, statement: str, parameters: Dict = None,
                          result_data_contents: str = "row") -> str:
        """异步执行GQL查询，返回job_id

        Args:
            statement: GQL查询语句
            parameters: 查询参数（可选）
            result_data_contents: 返回格式

        Returns:
            job_id，用于后续查询任务状态
        """
        result = self.execute_gql(statement, parameters, "async", result_data_contents)
        # 从响应中提取job_id
        return result.get('jobId', '')

    def execute_cypher_async(self, statement: str, parameters: Dict = None,
                             result_data_contents: str = "row") -> str:
        """异步执行Cypher查询，返回job_id

        Args:
            statement: Cypher查询语句
            parameters: 查询参数（可选）
            result_data_contents: 返回格式

        Returns:
            job_id，用于后续查询任务状态
        """
        result = self.execute_cypher(statement, parameters, "async", result_data_contents)
        # 从响应中提取job_id
        return result.get('jobId', '')

    def get_job_status(self, job_id: str) -> Dict:
        """查询Job状态

        Args:
            job_id: Job ID

        Returns:
            Job状态信息
        """
        return self._request('GET', f'/jobs/{job_id}/status')

    # ==================== Schema相关API ====================

    def get_schema(self) -> Dict:
        """获取图schema信息

        Returns:
            图的schema信息（点边类型、属性等）
        """
        return self.execute_cypher("call db.schema()", result_data_contents="graph")

    def _ensure_label_properties(self, label: str, new_properties: List[Dict]) -> Dict:
        """确保Label具有所需的属性（获取已有属性后追加新属性）

        Args:
            label: 标签名称
            new_properties: 新增属性列表

        Returns:
            执行结果
        """
        # 获取已有属性列表
        try:
            schema = self.get_label_schema(label)
            existing_props = []

            if schema and "results" in schema and schema["results"]:
                data = schema["results"][0].get("data", [])
                if data and len(data) > 0:
                    properties = data[0].get("row", [{}])[0].get("properties", [])
                    for prop in properties:
                        existing_props.append({
                            "property": {
                                "name": prop.get("name", ""),
                                "dataType": prop.get("dataType", "string"),
                                "cardinality": prop.get("cardinality", "single")
                            }
                        })
        except Exception:
            existing_props = []

        # 合并新属性（去重）
        existing_names = {p["property"]["name"] for p in existing_props}
        for prop in new_properties:
            if prop.get("property", {}).get("name") not in existing_names:
                existing_props.append(prop)

        # 更新Label Schema（追加新属性）
        data = {
            "type": "vertex",
            "properties": existing_props
        }

        return self._request("POST", f"/schema?label={label}", json=data)

    def create_or_update_label(self, label: str, properties: List[Dict], label_type: str = "vertex") -> Dict:
        """创建或更新Label及其属性

        Args:
            label: 标签名称
            properties: 属性列表，每个包含 name, dataType, cardinality
            label_type: 类型，vertex 或 edge

        Returns:
            执行结果

        Example:
            properties = [
                {"name": "content", "dataType": "string", "cardinality": "single"},
                {"name": "timestamp", "dataType": "long", "cardinality": "single"}
            ]
        """
        data = {
            "name": label,
            "type": label_type,
            "properties": []
        }

        for prop in properties:
            data["properties"].append({
                "property": {
                    "name": prop.get("name", ""),
                    "dataType": prop.get("dataType", "string"),
                    "cardinality": prop.get("cardinality", "single")
                }
            })

        return self._request('POST', '/schema/labels', json=data)

    def get_label_schema(self, label: str) -> Dict:
        """获取指定Label的schema信息

        Args:
            label: 标签名称

        Returns:
            Label的schema信息
        """
        return self._request('GET', f'/schema?label={label}')

    def create_edge_type(self, edge_type: str, properties: List[Dict] = None) -> Dict:
        """创建边类型及其属性

        Args:
            edge_type: 边类型名称
            properties: 属性列表（可选）

        Returns:
            执行结果
        """
        data = {
            "type": "edge",
            "properties": []
        }

        if properties:
            for prop in properties:
                data["properties"].append({
                    "property": {
                        "name": prop.get("name", ""),
                        "dataType": prop.get("dataType", "string"),
                        "cardinality": prop.get("cardinality", "single")
                    }
                })

        return self._request('POST', f'/schema?label={edge_type}', json=data)

    def get_graph_summary(self, label_details: bool = False) -> Dict:
        """获取图概要信息

        Args:
            label_details: 是否显示label详情

        Returns:
            图概要信息
        """
        return self._request('GET', f'/summary?label_details={str(label_details).lower()}')

    # ==================== 节点操作API ====================

    def add_node(self, node_id: str, labels: List[str] = None, properties: Dict = None,
                 upsert: bool = False, allow_destructive: bool = False) -> Dict:
        """添加节点

        Args:
            node_id: 节点ID
            labels: 节点标签列表，如 ["user", "person"]
            properties: 节点属性字典
            upsert: 幂等插入（默认False）。True 时使用 MERGE，节点已存在则更新
                属性而非重复创建（ISSUE-004）
            allow_destructive: 透传至 execute_cypher 的安全校验（一般无需开启）

        Returns:
            执行结果
        """
        labels = labels or []
        properties = properties or {}

        if not node_id:
            raise ValueError("node_id 不能为空")
        validate_property_values(properties)

        # 构建Cypher语句，使用GES特殊的 _ID_ 属性
        label_str = ':'.join(labels) if labels else ''
        if label_str:
            label_str = ':' + label_str

        props_str = ', '.join([f'{k}: ${k}' for k in properties.keys()])
        if props_str:
            props_str = ', ' + props_str

        if upsert:
            # MERGE 保证幂等性：节点不存在则创建，已存在则仅更新属性
            statement = f"MERGE (n{label_str} {{_ID_: $id}}) SET n += {{{props_str.lstrip(', ')}}} RETURN n"
        else:
            statement = f"CREATE (n{label_str} {{_ID_: $id{props_str}}}) RETURN n"
        params = {'id': node_id}
        params.update(properties)

        return self.execute_cypher(statement, parameters=params, allow_destructive=allow_destructive)

    def add_nodes_batch(self, nodes: List[Dict], upsert: bool = False) -> Dict:
        """批量添加节点

        Args:
            nodes: 节点列表，每个节点包含id, labels, properties
            upsert: 幂等插入（默认False）。True 时使用 MERGE（ISSUE-004）

        Returns:
            执行结果

        Raises:
            ValueError: 批量数量超过限制（ISSUE-010 边界处理）
        """
        MAX_BATCH = 500
        if len(nodes) > MAX_BATCH:
            raise ValueError(f"批量添加节点数超过上限 {MAX_BATCH}，请分批导入（ISSUE-010 边界保护）")

        statements = []
        params_dict = {}

        for i, node in enumerate(nodes):
            node_id = node.get('id', '')
            labels = node.get('labels', [])
            properties = node.get('properties', {})

            if not node_id:
                continue
            validate_property_values(properties)

            label_str = ':'.join(labels) if labels else ''
            if label_str:
                label_str = ':' + label_str

            props_str = ', '.join([f'{k}: ${k}_{i}' for k in properties.keys()])
            if props_str:
                props_str = ', ' + props_str

            # GES使用 _ID_ 来设置点的字符串ID
            if upsert:
                set_clause = ''
                if properties:
                    set_parts = ', '.join([f'n.{k} = ${k}_{i}' for k in properties.keys()])
                    set_clause = f' SET {set_parts}'
                statement = f"MERGE (n{label_str} {{_ID_: $id_{i}}}){set_clause}"
            else:
                statement = f"CREATE (n{label_str} {{_ID_: $id_{i}{props_str}}})"
            statements.append({
                "statement": statement,
                "parameters": {f'id_{i}': node_id},
                "resultDataContents": ["row"]
            })

            # 添加属性参数
            for k, v in properties.items():
                params_dict[f'{k}_{i}'] = v

        data = {"statements": statements}
        return self._request('POST', '/action?action_id=execute-cypher-query', json=data)

    def delete_node(self, node_id: str) -> Dict:
        """删除节点

        Args:
            node_id: 节点ID

        Returns:
            执行结果
        """
        # GES中使用 _ID_ 属性来匹配字符串ID
        statement = "MATCH (n) WHERE id(n) = $id DETACH DELETE n"
        return self.execute_cypher(statement, parameters={'id': node_id})

    def update_node(self, node_id: str, properties: Dict) -> Dict:
        """更新节点属性

        Args:
            node_id: 节点ID
            properties: 要更新的属性

        Returns:
            执行结果
        """
        # GES中使用 _ID_ 属性来匹配字符串ID
        props_str = ', '.join([f'n.{k} = ${k}' for k in properties.keys()])
        statement = f"MATCH (n) WHERE id(n) = $id SET {props_str} RETURN n"
        params = {'id': node_id}
        params.update(properties)

        return self.execute_cypher(statement, parameters=params)

    def get_node(self, node_id: str) -> Dict:
        """根据ID获取节点

        Args:
            node_id: 节点ID

        Returns:
            节点信息
        """
        # GES中使用 _ID_ 属性来匹配字符串ID
        statement = "MATCH (n) WHERE id(n) = $id RETURN n"
        return self.execute_cypher(statement, parameters={'id': node_id})

    # ==================== 边操作API ====================

    def add_edge(self, start_node_id: str, end_node_id: str,
                 edge_type: str, properties: Dict = None) -> Dict:
        """添加边

        Args:
            start_node_id: 起始节点ID
            end_node_id: 终止节点ID
            edge_type: 边类型/标签
            properties: 边属性

        Returns:
            执行结果
        """
        properties = properties or {}

        # 构建属性字符串
        if properties:
            props_parts = []
            for k in properties.keys():
                props_parts.append(f'{k}: ${k}')
            props_str = ', '.join(props_parts)
            props_clause = f' {{{props_str}}}'
        else:
            props_clause = ''

        # GES中使用 id() 函数来匹配节点ID
        statement = f"MATCH (a), (b) WHERE id(a) = $start AND id(b) = $end CREATE (a)-[r:{edge_type}{props_clause}]->(b) RETURN r"
        params = {'start': start_node_id, 'end': end_node_id}
        params.update(properties)

        return self.execute_cypher(statement, parameters=params)

    def delete_edge(self, start_node_id: str, end_node_id: str, edge_type: str = None) -> Dict:
        """删除边

        Args:
            start_node_id: 起始节点ID
            end_node_id: 终止节点ID
            edge_type: 边类型（可选）

        Returns:
            执行结果
        """
        # GES中使用 id() 函数来匹配节点ID
        if edge_type:
            statement = "MATCH (a)-[r:{}]->(b) WHERE id(a) = $start AND id(b) = $end DELETE r".format(edge_type)
        else:
            statement = "MATCH (a)-[r]->(b) WHERE id(a) = $start AND id(b) = $end DELETE r"

        return self.execute_cypher(statement, parameters={'start': start_node_id, 'end': end_node_id})

    def get_edges(self, node_id: str, direction: str = "both") -> Dict:
        """获取节点的边

        Args:
            node_id: 节点ID
            direction: 方向，both/in/out

        Returns:
            边的信息
        """
        if direction == "out":
            statement = "MATCH (n)-[r]->(m) WHERE id(n) = $id RETURN r, m"
        elif direction == "in":
            statement = "MATCH (n)<-[r]-(m) WHERE id(n) = $id RETURN r, m"
        else:
            statement = "MATCH (n)-[r]-(m) WHERE id(n) = $id RETURN r, m"

        return self.execute_cypher(statement, parameters={'id': node_id})

    # ==================== Label操作API ====================

    def add_label_to_node(self, node_id: str, label: str) -> Dict:
        """为节点添加Label

        Args:
            node_id: 节点ID
            label: 要添加的标签

        Returns:
            执行结果
        """
        statement = "MATCH (n) WHERE id(n) = $id SET n:`$label` RETURN n"
        return self.execute_cypher(statement, parameters={'id': node_id, 'label': label})

    def remove_label_from_node(self, node_id: str, label: str) -> Dict:
        """从节点移除Label

        Args:
            node_id: 节点ID
            label: 要移除的标签

        Returns:
            执行结果
        """
        # GES不支持直接移除label，但可以通过重新创建节点来实现
        statement = "MATCH (n) WHERE id(n) = $id RETURN n"
        result = self.execute_cypher(statement, parameters={'id': node_id})

        # 注意：GES实际的label移除可能需要更复杂的操作
        return result

    def get_nodes_by_label(self, label: str, limit: int = 100) -> Dict:
        """根据Label查询节点

        Args:
            label: 节点标签
            limit: 返回数量限制

        Returns:
            节点列表
        """
        statement = f"MATCH (n:`{label}`) RETURN n LIMIT {limit}"
        return self.execute_cypher(statement)

    # ==================== 导入导出API ====================

    def export_graph(self, export_path: str, vertex_set_name: str = "set_vertex",
                     edge_set_name: str = "set_edge", schema_name: str = "schema.xml",
                     obs_parameters: Dict = None) -> str:
        """导出整个图数据到OBS

        Args:
            export_path: OBS导出路径，格式: bucket/path，如 "claude/export_test/01"
            vertex_set_name: 点数据集名称，如 "set_vertex"
            edge_set_name: 边数据集名称，如 "set_edge"
            schema_name: Schema文件名，如 "schema.xml"
            obs_parameters: OBS访问参数，包含accessKey和secretKey

        Returns:
            job_id，用于查询导出任务状态

        Example:
            obs_params = {
                'accessKey': 'your_access_key',
                'secretKey': 'your_secret_key'
            }
            job_id = client.export_graph(
                export_path='claude/export_test/01',
                vertex_set_name='set_vertex',
                edge_set_name='set_edge',
                schema_name='schema.xml',
                obs_parameters=obs_params
            )
        """
        data = {
            "graphExportPath": export_path,
            "vertexSetName": vertex_set_name,
            "edgeSetName": edge_set_name,
            "schemaName": schema_name
        }

        if obs_parameters:
            data["obsParameters"] = obs_parameters

        resp = self._request('POST', '/action?action_id=export-graph', json=data)
        return resp.get('jobId', '')

    def export_query_result(self, cypher: str, export_path: str,
                            obs_parameters: Dict = None, wait_completion: bool = True) -> str:
        """导出Cypher查询结果到OBS

        注意：此API可能不被当前GES版本支持，返回404错误。
        cypher的RETURN中必须指明id或属性，用于标识节点/边

        Args:
            cypher: Cypher查询语句，RETURN中需要包含id或属性
            export_path: OBS导出路径，格式: bucket/path
            obs_parameters: OBS访问参数，包含accessKey和secretKey
            wait_completion: 是否等待查询完成后才返回export jobId

        Returns:
            export_job_id，用于查询导出任务状态

        Example:
            # 查询并导出，注意RETURN中包含id
            obs_params = {'accessKey': 'xxx', 'secretKey': 'yyy'}
            job_id = client.export_query_result(
                cypher='MATCH (n) RETURN id(n) as id, n.name as name',
                export_path='claude/export_result/01',
                obs_parameters=obs_params
            )

        Note:
            当前GES版本可能不支持此API，如返回404请使用其他方式导出数据
        """
        # 先执行异步查询
        data = {
            "statements": [{
                "statement": cypher,
                "parameters": {},
                "executionMode": "async",
                "resultDataContents": ["row"]
            }]
        }
        resp = self._request('POST', '/action?action_id=execute-cypher-query', json=data)

        # 从results中获取jobId
        query_job_id = resp.get('results', [{}])[0].get('jobId', '')
        if not query_job_id:
            raise Exception(f"无法获取查询jobId: {resp}")

        # 如果需要等待查询完成
        if wait_completion:
            # 等待查询执行完成（调用方也可以自行轮询）
            import time
            for _ in range(60):  # 最多等待2分钟
                time.sleep(2)
                status = self.get_job_status(query_job_id)
                if status.get('status') == 'complete':
                    break
                if status.get('status') == 'failed':
                    raise Exception(f"查询执行失败: {status}")

        # 导出查询结果到OBS
        export_data = {
            "exportPath": export_path,
            "fileName": "query_result.csv",
            "obsParameters": obs_parameters
        }
        export_resp = self._request('POST', f'/jobs/{query_job_id}/action?action_id=export-result', json=export_data)

        return export_resp.get('jobId', '')

    def export_job_result(self, job_id: str, export_path: str, file_name: str = "result.csv",
                          obs_parameters: Dict = None) -> Dict:
        """导出指定Job的结果到文件

        Args:
            job_id: Job ID（通常是Cypher异步查询的jobId）
            export_path: OBS导出路径，格式: bucket/path
            file_name: 导出文件名
            obs_parameters: OBS访问参数，包含accessKey和secretKey

        Returns:
            执行结果
        """
        data = {
            "exportPath": export_path,
            "fileName": file_name,
        }

        if obs_parameters:
            data["obsParameters"] = obs_parameters

        return self._request('POST', f'/jobs/{job_id}/action?action_id=export-result', json=data)

    def import_graph(self, schema_path: str, vertex_path: str = None,
                     edge_path: str = None, obs_parameters: Dict = None) -> str:
        """导入图数据

        Args:
            schema_path: OBS上的Schema文件路径，格式: bucket/path/schema.xml
            vertex_path: OBS上的点数据文件夹路径，格式: bucket/path/vertices/
            edge_path: OBS上的边数据文件夹路径，格式: bucket/path/edges/
            obs_parameters: OBS访问参数，包含accessKey和secretKey

        Returns:
            job_id，用于查询导入任务状态

        Note:
            - vertex_path和edge_path必须使用不同的文件夹
            - OBS路径格式: bucket/object-key，不需要obs://前缀
            - 建议目录结构:
                obs://bucket/schema/schema.xml
                obs://bucket/data/vertices/
                obs://bucket/data/edges/
        """
        data = {
            "schemaPath": schema_path
        }

        if vertex_path:
            data["vertexsetPath"] = vertex_path
        if edge_path:
            data["edgesetPath"] = edge_path
        if obs_parameters:
            data["obsParameters"] = obs_parameters

        resp = self._request('POST', '/action?action_id=import-graph', json=data)
        return resp.get('jobId', '')

    # ==================== 图管理API ====================

    def clear_graph(self, use_api: bool = True) -> Dict:
        """清空图中所有数据

        Args:
            use_api: 是否使用专用API方式（默认True）。若为False，则使用Cypher方式。

        Returns:
            执行结果，包含job_id（API方式）或查询结果（Cypher方式）

        Note:
            - API方式 (use_api=True): 使用 action_id=clear-graph，会返回job_id
            - Cypher方式 (use_api=False): 使用 MATCH (n) DETACH DELETE n
            - 推荐使用API方式，更彻底且支持异步执行
        """
        if use_api:
            # 使用专用clear-graph API，更彻底
            return self._request('POST', '/action?action_id=clear-graph', json={})
        else:
            # 备用Cypher方式（clear_graph 是专门的清空接口，需用户确认后走这里）
            statement = "MATCH (n) DETACH DELETE n"
            return self.execute_cypher(statement, allow_destructive=True)

    def get_graph_stats(self) -> Dict:
        """获取图统计信息

        Returns:
            图的统计信息（节点数、边数等）
        """
        return self.get_graph_summary(label_details=True)

    # ==================== 索引操作API ====================

    def create_vertex_index(self, index_name: str, label: str = None) -> Dict:
        """创建点索引

        Args:
            index_name: 索引名称
            label: 点标签（可选）

        Returns:
            执行结果
        """
        data = {
            "indexName": index_name,
            "indexType": "GlobalCompositeVertexIndex",
            "hasLabel": True if label else False,
            "indexProperty": []
        }

        return self._request('POST', '/indices', json=data)

    def create_edge_index(self, index_name: str, label: str = None) -> Dict:
        """创建边索引

        Args:
            index_name: 索引名称
            label: 边标签（可选）

        Returns:
            执行结果
        """
        data = {
            "indexName": index_name,
            "indexType": "GlobalCompositeEdgeIndex",
            "hasLabel": True if label else False,
            "indexProperty": []
        }

        return self._request('POST', '/indices', json=data)


class GESMemorySkill:
    """GES Memory Skill主类 - 提供LLM记忆系统的原子能力

    注意：GES持久化版只支持以下导出能力：
    - export_graph: 导出整图数据到OBS

    不支持以下功能：
    - export_query_result: 导出Cypher查询结果（job结果导出）
    - export_job_result: 导出Job结果到文件

    这是GES持久化版的设计限制，如需导出查询结果请使用其他方式。
    """

    def __init__(self):
        self.client = GESClient()
        self._context: Dict[str, Any] = {}
        self._context_lock = threading.Lock()
        self._context_max_keys = 100
        self._context_max_value_len = 512

    def execute_query(self, cypher: str, parameters: Dict = None, allow_destructive: bool = False) -> Dict:
        """执行自定义Cypher查询

        Args:
            cypher: Cypher查询语句
            parameters: 查询参数
            allow_destructive: 是否允许破坏性语句（默认False，安全校验阻止全量
                删除/清空；定向删除（WHERE ... id(n)=...）不受影响）

        Returns:
            查询结果
        """
        validate_cypher(cypher, allow_destructive=allow_destructive, context='execute_query')
        validate_property_values(parameters)
        result = self.client.execute_cypher(cypher, parameters=parameters)
        self._remember_query(cypher, result)
        return result

    def execute_gql(self, gql: str, parameters: Dict = None, allow_destructive: bool = False) -> Dict:
        """执行自定义GQL查询

        Args:
            gql: GQL查询语句
            parameters: 查询参数
            allow_destructive: 是否允许破坏性语句（同 execute_query）

        Returns:
            查询结果
        """
        validate_cypher(gql, allow_destructive=allow_destructive, context='execute_gql')
        validate_property_values(parameters)
        result = self.client.execute_gql(gql, parameters=parameters)
        self._remember_query(gql, result)
        return result

    def get_schema_info(self) -> Dict:
        """获取图谱Schema信息

        Returns:
            Schema信息
        """
        return self.client.get_schema()

    def get_statistics(self) -> Dict:
        """获取图谱统计信息

        Returns:
            统计信息
        """
        return self.client.get_graph_stats()

    # ==================== 多轮上下文保持（ISSUE-011） ====================

    def _remember_query(self, statement: str, result: Any) -> None:
        """记录最近一次查询语句与结果，供多轮对话上下文使用（非持久化语义）。"""
        with self._context_lock:
            if len(self._context) >= self._context_max_keys:
                self._context.pop(next(iter(self._context)))
            self._context['last_query'] = statement
            self._context['last_result'] = json.dumps(result, ensure_ascii=False, default=str)[
                :self._context_max_value_len]

    def set_context(self, key: str, value: Any) -> None:
        """写入一个上下文键值（供多轮对话携带业务变量）。

        Args:
            key: 上下文键名
            value: 上下文值（将 JSON 序列化存储）
        """
        with self._context_lock:
            if len(self._context) >= self._context_max_keys:
                self._context.pop(next(iter(self._context)))
            if isinstance(value, (dict, list)):
                value = json.dumps(value, ensure_ascii=False, default=str)[:self._context_max_value_len]
            self._context[key] = value

    def get_context(self, key: str, default: Any = None) -> Any:
        """读取一个上下文键值。

        Args:
            key: 上下文键名
            default: 键不存在时的默认值
        """
        with self._context_lock:
            return self._context.get(key, default)

    def clear_context(self) -> None:
        """清空上下文（新的对话轮次开始前调用）。"""
        with self._context_lock:
            self._context.clear()

    def get_context_snapshot(self) -> Dict[str, Any]:
        """返回当前上下文的只读快照。"""
        with self._context_lock:
            return dict(self._context)


# 便捷函数
def get_client() -> GESClient:
    """获取GES客户端实例"""
    return GESClient()


def get_skill() -> GESMemorySkill:
    """获取GES Memory Skill实例"""
    return GESMemorySkill()