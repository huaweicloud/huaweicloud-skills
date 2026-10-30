"""
统一配置加载器 — 从 YAML 构建 dataclass 配置对象。
零硬编码：所有值来自 config/migrate.yaml。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml


# ---- 配置 dataclass 定义 ----

@dataclass
class SourceConfig:
    host: str = ""
    username: str = ""
    password: str = ""
    winrm_port: int = 5985
    winrm_transport: str = "ntlm"
    winrm_use_ssl: bool = False
    cloud_provider: str = "none"
    os_arch: str = "x64"


@dataclass
class BatchConfig:
    hosts_csv: str = "config/hosts.csv"
    max_workers: int = 10
    state_file: str = "batch_state.json"
    signed_url_ttl: int = 3600


@dataclass
class WinRMKeepaliveConfig:
    enabled: bool = True
    interval: int = 30
    max_failures: int = 3
    reconnect: bool = True


@dataclass
class OBSConfig:
    endpoint: str = ""
    ak: str = ""
    sk: str = ""
    bucket: str = ""
    region: str = ""
    obsutil_path: str = "obsutil"


@dataclass
class PackageURI:
    obs_uri: str = ""
    http_uri: str = ""
    local_name: str = ""


@dataclass
class DownloadConfig:
    packages: dict = field(default_factory=dict)
    sandbox_download_dir: str = ""
    source_download_dir: str = ""


@dataclass
class SMSAgentConfig:
    ak: str = ""
    sk: str = ""
    domain_id: str = ""
    domain_name: str = ""
    enterprise_project: str = "0"
    region: str = ""
    install_dir: str = ""
    log_file: str = ""
    error_log_file: str = ""
    proxy_mode: bool = False
    proxy_host: str = ""
    proxy_port: int = 3128
    silent_install_args: str = "/S"
    agent_version: str = "py3"           # py3=图形界面(GUI), py2=命令行界面(CLI)
    configure_mode: str = "exe"        # Py3 配置方式: exe=纯exe直用(默认), autoit=AutoIt编译/au3
    deploy_mode: str = "precompiled"  # Py2 部署方式: precompiled=预编译exe优先(默认, 缺失/失败回退cs编译), cs=强制源端csc编译
    agent_exe_name: str = "SMS-Agent.exe"  # 安装后主程序名: py3=SMS-Agent.exe, py2=agent-start.exe


@dataclass
class AutoItConfig:
    install_dir: str = ""
    exe_path: str = ""
    silent_install_args: str = "/S"
    aut2exe_path: str = ""


@dataclass
class ProxyServerConfig:
    host: str = ""
    ssh_port: int = 22
    ssh_username: str = ""
    ssh_password: str = ""
    squid_port: int = 3128
    gost_listen_port: int = 15985
    http_server_port: int = 8080
    http_server_token: str = ""


@dataclass
class ProxyOptConfig:
    base_dir: str = ""
    config_file: str = ""
    skip: bool = False


@dataclass
class LoggingConfig:
    level: str = "INFO"
    dir: str = ""
    file: str = "migrate.log"
    max_size_mb: int = 50
    backup_count: int = 5


@dataclass
class TimeoutConfig:
    winrm_connect: int = 30
    winrm_command: int = 300
    file_transfer: int = 600
    autoit_run: int = 240
    verify_poll_interval: int = 10
    verify_max_wait: int = 600
    install_wait: int = 120


# ---- 重试策略配置 ----

@dataclass
class PhaseRetryPolicy:
    """
    单个阶段的重试策略。

    设计原则：
    - 瞬时错误（网络超时、连接中断）→ 自动重试，指数退避
    - 永久错误（认证失败、配置错误）→ 不重试，立即告警
    - 错误分类通过 retryable_errors 模式匹配实现，不硬编码在逻辑中
    """
    max_retries: int = 0          # 最大重试次数（0=不重试）
    backoff_sec: int = 5          # 基础退避秒数，实际等待 = backoff * 2^attempt
    retryable_errors: list = field(default_factory=lambda: [
        "timeout", "timed out", "connection", "connect",
        "reset", "refused", "unreachable", "transient",
        "503", "502", "429", "busy",
    ])

    def is_retryable(self, error_msg: str) -> bool:
        """判断错误是否可重试（瞬时错误）。"""
        msg_lower = error_msg.lower()
        return any(pattern in msg_lower for pattern in self.retryable_errors)

    def backoff_time(self, attempt: int) -> float:
        """计算第 attempt 次重试的退避时间（指数退避）。"""
        return self.backoff_sec * (2 ** attempt)


@dataclass
class RetryPolicy:
    """
    全局重试策略 — 按阶段名索引。

    每个阶段有独立的 PhaseRetryPolicy，从 migrate.yaml 注入，不硬编码。
    """
    phases: dict = field(default_factory=dict)

    def get(self, phase_name: str) -> PhaseRetryPolicy:
        """获取指定阶段的重试策略，未配置则返回默认（不重试）。"""
        return self.phases.get(phase_name, PhaseRetryPolicy())


@dataclass
class SmsTaskConfig:
    """SMS 控制面迁移任务配置（步骤二~五）。

    零硬编码：所有值来自 config/migrate.yaml 的 sms_task 段。
    - 凭据(AK/SK)复用 sms_agent 段，由 SmsClient 经环境变量注入 hcloud，不落盘。
    - 目标端支持两种模式：
        existing=已有服务器（优先）: target_vm_id 必填
        new=创建新服务器: vm_template_id 必填
    """
    region: str = "cn-north-4"                  # 目的端/SMS 区域
    os_type: str = "WINDOWS"                    # WINDOWS | LINUX
    migration_type: str = "MIGRATE_BLOCK"       # MIGRATE_FILE | MIGRATE_BLOCK（Windows 默认块级）
    task_name: str = ""                         # 任务名称，留空自动生成
    target_mode: str = "existing"                # existing=已有服务器(优先) | new=创建新服务器
    target_vm_id: str = ""                      # existing: 目的端 ECS ID（必填）
    target_name: str = ""                       # 目的端名称，留空自动生成
    migration_ip: str = ""                      # existing+公网: 目的端 EIP
    use_public_ip: bool = True                  # 是否公网迁移
    vm_template_id: str = ""                    # new: 自动创建虚拟机模板 ID（必填）
    auto_start: bool = False                    # create 后是否立即开始全量复制
    start_target_server: bool = False           # 迁移完成后是否启动目的端
    syncing: bool = False                       # 默认 False=完整 6 子任务；True=仅 4 子任务(持续同步)
    need_migration_test: bool = False           # 是否开启迁移演练
    is_need_consistency_check: bool = True      # 默认 True=多 CHECK_CONSISTENCY → 7 子任务
    speed_limit: int = 0                        # 迁移限速 Mbps，0=不限
    enterprise_project: str = "default"         # 企业项目
    source_server_id: str = ""                  # 源端服务器ID，留空自动发现
    poll_interval_s: int = 30                   # wait 轮询间隔
    wait_timeout_s: int = 14400                 # 全量复制最长等待时间
    # ---- 目标端基础设施（prepare-target 编排；零硬编码） ----
    target_az: str = ""                         # 可用区，必填（已移除代码层默认，避免建错区域）
    target_flavor_id: str = ""                  # 规格ID，空则按源端规格自动匹配
    target_image_id: str = ""                   # 镜像ID，空则自动选 Windows Server 2022 公共镜像
    target_vpc_id: str = ""                     # VPC ID，空则按名称匹配或自动创建
    target_vpc_cidr: str = "192.168.0.0/16"     # 自动创建 VPC 网段
    target_vpc_name: str = ""                   # 自动创建 VPC 名称，空则自动生成
    target_subnet_id: str = ""                  # 子网 ID，空则按 CIDR 匹配或自动创建
    target_subnet_cidr: str = "192.168.0.0/24"  # 自动创建子网网段
    target_subnet_name: str = ""                # 自动创建子网名称，空则自动生成
    # 【网络红线】默认禁止网段重叠（相等/包含/被包含即拒）。
    # 仅两种例外：明确告知（主动确认）/ ER 等特殊组网（人为规划的互通地址空间），此时显式置 true。
    allow_cidr_overlap: bool = False
    target_sg_id: str = ""                      # 安全组 ID，空则按名称匹配或自动创建
    target_sg_name: str = ""                    # 自动创建安全组名称，空则自动生成
    sg_source_cidrs: list = field(default_factory=list)   # 【红线】仅放行这些来源，禁止 0.0.0.0/0
    sg_ports: list = field(default_factory=lambda: [22, 8899, 8900])  # 最小放行端口
    target_root_volume_type: str = "SAS"        # 系统盘类型
    target_root_volume_size: int = 40           # 系统盘大小 GB
    target_password: str = ""                   # 目的端初始密码，空则自动生成并输出一次
    use_eip: bool = True                        # 是否绑定 EIP（公网迁移需要）
    eip_id: str = ""                            # 指定复用 EIP，空则优先空闲未绑定
    eip_bandwidth_size: int = 5                 # EIP 带宽 Mbit/s
    eip_type: str = "5_bgp"                    # EIP 线路类型（默认 5_bgp 动态BGP）
    eip_charge_mode: str = "traffic"            # 带宽计费模式 bandwidth|traffic
    # ---- 资源复用与回收（防浪费） ----
    sg_merge: bool = True                    # 安全组规则指纹归并：相同规则复用同一属主 SG
    eip_reuse_policy: str = "free-first"     # EIP 复用策略: free-first(空闲优先/属主优先) | per-host


@dataclass
class OwnershipConfig:
    """资源属主标识配置（OwnerID 指纹算法）。

    - enabled: 是否启用属主校验（默认 true，启用后非属主资源禁止更改/删除）
    - salt / owner_tag_value: 派生 owner_id 的固定盐与 owner tag 值（发布后勿改）
    - owner_id_tag: 指纹 Tag key
    - name_prefixes: 命名前缀（肉眼辨识 + 名称指纹兜底）
    - state_file: 会话属主清单（记录本 skill 创建的资源 ID/名称/指纹）
    """
    enabled: bool = True
    salt: str = "huawei-cloud-migration-windows-ecs:v1"
    owner_tag_key: str = "owner"
    owner_tag_value: str = "huawei-cloud-migration-windows-ecs"
    owner_id_tag: str = "owner_id"
    name_prefixes: tuple = ("vpc-mig-", "subnet-mig-", "sg-mig-", "eip-mig-")
    state_file: str = "config/owned_resources.json"


@dataclass
class MigrateConfig:
    scenario: str = "public"
    sandbox_host: str = ""
    source_base_dir: str = r"C:\auto_agent_opt"
    source: SourceConfig = field(default_factory=SourceConfig)
    batch: BatchConfig = field(default_factory=BatchConfig)
    winrm_keepalive: WinRMKeepaliveConfig = field(default_factory=WinRMKeepaliveConfig)
    obs: OBSConfig = field(default_factory=OBSConfig)
    download: DownloadConfig = field(default_factory=DownloadConfig)
    sms_agent: SMSAgentConfig = field(default_factory=SMSAgentConfig)
    autoit: AutoItConfig = field(default_factory=AutoItConfig)
    proxy_server: ProxyServerConfig = field(default_factory=ProxyServerConfig)
    proxyopt: ProxyOptConfig = field(default_factory=ProxyOptConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    timeout: TimeoutConfig = field(default_factory=TimeoutConfig)
    retry_policy: RetryPolicy = field(default_factory=RetryPolicy)
    sms_task: SmsTaskConfig = field(default_factory=SmsTaskConfig)
    ownership: OwnershipConfig = field(default_factory=OwnershipConfig)

    # ---- 派生路径属性（均基于 source_base_dir，消除硬编码） ----

    @property
    def source_download_dir(self) -> str:
        return self.download.source_download_dir or f"{self.source_base_dir}\\downloads"

    @property
    def source_au3_path(self) -> str:
        return f"{self.source_base_dir}\\configure_sms_agent.au3"

    @property
    def source_exe_path(self) -> str:
        return f"{self.source_base_dir}\\configure_sms_agent.exe"

    @property
    def source_bat_path(self) -> str:
        return f"{self.source_base_dir}\\run_configure.bat"

    @property
    def source_log_path(self) -> str:
        return f"{self.source_base_dir}\\configure_log.txt"


class ConfigLoader:
    """从 YAML 文件加载配置，构建 dataclass 对象。"""

    @staticmethod
    def load(config_path) -> MigrateConfig:
        path = Path(config_path)
        if not path.exists():
            raise FileNotFoundError(f"配置文件不存在: {path}")

        with open(path, "r", encoding="utf-8") as f:
            raw: dict = yaml.safe_load(f)

        cfg = MigrateConfig()
        cfg.scenario = raw.get("scenario", "public")
        cfg.sandbox_host = raw.get("sandbox_host", "")
        cfg.source_base_dir = raw.get("source_base_dir", r"C:\auto_agent_opt")

        # source
        s = raw.get("source", {})
        cfg.source = SourceConfig(
            host=s.get("host", ""),
            username=s.get("username", ""),
            password=s.get("password", ""),
            winrm_port=s.get("winrm_port", 5985),
            winrm_transport=s.get("winrm_transport", "ntlm"),
            winrm_use_ssl=s.get("winrm_use_ssl", False),
            cloud_provider=s.get("cloud_provider", "none"),
            os_arch=s.get("os_arch", "x64"),
        )

        # batch
        b = raw.get("batch", {})
        cfg.batch = BatchConfig(
            hosts_csv=b.get("hosts_csv", "config/hosts.csv"),
            max_workers=b.get("max_workers", 10),
            state_file=b.get("state_file", "batch_state.json"),
            signed_url_ttl=b.get("signed_url_ttl", 3600),
        )

        # keepalive
        k = raw.get("winrm_keepalive", {})
        cfg.winrm_keepalive = WinRMKeepaliveConfig(
            enabled=k.get("enabled", True),
            interval=k.get("interval", 30),
            max_failures=k.get("max_failures", 3),
            reconnect=k.get("reconnect", True),
        )

        # obs
        o = raw.get("obs", {})
        cfg.obs = OBSConfig(
            endpoint=o.get("endpoint", ""),
            ak=o.get("ak", ""),
            sk=o.get("sk", ""),
            bucket=o.get("bucket", ""),
            region=o.get("region", ""),
            obsutil_path=o.get("obsutil_path", "obsutil"),
        )

        # download
        d = raw.get("download", {})
        packages = {}
        for name, pkg in d.get("packages", {}).items():
            packages[name] = PackageURI(
                obs_uri=pkg.get("obs_uri", ""),
                http_uri=pkg.get("http_uri", ""),
                local_name=pkg.get("local_name", ""),
            )
        cfg.download = DownloadConfig(
            packages=packages,
            sandbox_download_dir=d.get("sandbox_download_dir", ""),
            source_download_dir=d.get("source_download_dir", ""),
        )

        # sms_agent
        sa = raw.get("sms_agent", {})
        cfg.sms_agent = SMSAgentConfig(
            ak=sa.get("ak", ""),
            sk=sa.get("sk", ""),
            domain_id=sa.get("domain_id", ""),
            domain_name=sa.get("domain_name", ""),
            enterprise_project=sa.get("enterprise_project", "0"),
            region=sa.get("region", ""),
            install_dir=sa.get("install_dir", ""),
            log_file=sa.get("log_file", ""),
            error_log_file=sa.get("error_log_file", ""),
            proxy_mode=sa.get("proxy_mode", False),
            proxy_host=sa.get("proxy_host", ""),
            proxy_port=sa.get("proxy_port", 3128),
            silent_install_args=sa.get("silent_install_args", "/S"),
            agent_version=sa.get("agent_version", "py3"),
            configure_mode=sa.get("configure_mode", "exe"),
            deploy_mode=sa.get("deploy_mode", "precompiled"),
            agent_exe_name=sa.get("agent_exe_name", "SMS-Agent.exe"),
        )

        # autoit
        ai = raw.get("autoit", {})
        cfg.autoit = AutoItConfig(
            install_dir=ai.get("install_dir", ""),
            exe_path=ai.get("exe_path", ""),
            silent_install_args=ai.get("silent_install_args", "/S"),
            aut2exe_path=ai.get("aut2exe_path", ""),
        )

        # proxy_server
        ps = raw.get("proxy_server", {})
        cfg.proxy_server = ProxyServerConfig(
            host=ps.get("host", ""),
            ssh_port=ps.get("ssh_port", 22),
            ssh_username=ps.get("ssh_username", ""),
            ssh_password=ps.get("ssh_password", ""),
            squid_port=ps.get("squid_port", 3128),
            gost_listen_port=ps.get("gost_listen_port", 15985),
            http_server_port=ps.get("http_server_port", 8080),
            http_server_token=ps.get("http_server_token", ""),
        )

        # proxyopt
        po = raw.get("proxyopt", {})
        cfg.proxyopt = ProxyOptConfig(
            base_dir=po.get("base_dir", ""),
            config_file=po.get("config_file", ""),
            skip=po.get("skip", False),
        )

        # logging
        lg = raw.get("logging", {})
        cfg.logging = LoggingConfig(
            level=lg.get("level", "INFO"),
            dir=lg.get("dir", ""),
            file=lg.get("file", "migrate.log"),
            max_size_mb=lg.get("max_size_mb", 50),
            backup_count=lg.get("backup_count", 5),
        )

        # timeout
        to = raw.get("timeout", {})
        cfg.timeout = TimeoutConfig(
            winrm_connect=to.get("winrm_connect", 30),
            winrm_command=to.get("winrm_command", 300),
            file_transfer=to.get("file_transfer", 600),
            autoit_run=to.get("autoit_run", 240),
            verify_poll_interval=to.get("verify_poll_interval", 10),
            verify_max_wait=to.get("verify_max_wait", 600),
            install_wait=to.get("install_wait", 120),
        )

        # retry_policy
        rp = raw.get("retry_policy", {})
        phase_policies = {}
        for phase_name, prp in rp.items():
            phase_policies[phase_name] = PhaseRetryPolicy(
                max_retries=prp.get("max_retries", 0),
                backoff_sec=prp.get("backoff_sec", 5),
                retryable_errors=prp.get("retryable_errors", [
                    "timeout", "timed out", "connection", "connect",
                    "reset", "refused", "unreachable", "transient",
                    "503", "502", "429", "busy",
                ]),
            )
        cfg.retry_policy = RetryPolicy(phases=phase_policies)
        # sms_task（步骤二~五 控制面配置）
        st = raw.get("sms_task", {})
        cfg.sms_task = SmsTaskConfig(
            region=st.get("region", "cn-north-4"),
            os_type=st.get("os_type", "WINDOWS"),
            migration_type=st.get("migration_type", "MIGRATE_BLOCK"),
            task_name=st.get("task_name", ""),
            target_mode=st.get("target_mode", "existing"),
            target_vm_id=st.get("target_vm_id", ""),
            target_name=st.get("target_name", ""),
            migration_ip=st.get("migration_ip", ""),
            use_public_ip=st.get("use_public_ip", True),
            vm_template_id=st.get("vm_template_id", ""),
            auto_start=st.get("auto_start", False),
            start_target_server=st.get("start_target_server", False),
            syncing=st.get("syncing", False),
            need_migration_test=st.get("need_migration_test", False),
            is_need_consistency_check=st.get("is_need_consistency_check", True),
            speed_limit=st.get("speed_limit", 0),
            enterprise_project=st.get("enterprise_project", "default"),
            source_server_id=st.get("source_server_id", ""),
            poll_interval_s=st.get("poll_interval_s", 30),
            wait_timeout_s=st.get("wait_timeout_s", 14400),
            target_az=st.get("target_az", ""),
            target_flavor_id=st.get("target_flavor_id", ""),
            target_image_id=st.get("target_image_id", ""),
            target_vpc_id=st.get("target_vpc_id", ""),
            target_vpc_cidr=st.get("target_vpc_cidr", "192.168.0.0/16"),
            target_vpc_name=st.get("target_vpc_name", ""),
            target_subnet_id=st.get("target_subnet_id", ""),
            target_subnet_cidr=st.get("target_subnet_cidr", "192.168.0.0/24"),
            target_subnet_name=st.get("target_subnet_name", ""),
            allow_cidr_overlap=bool(st.get("allow_cidr_overlap", False)),
            target_sg_id=st.get("target_sg_id", ""),
            target_sg_name=st.get("target_sg_name", ""),
            sg_source_cidrs=st.get("sg_source_cidrs") or [],
            sg_ports=st.get("sg_ports") or [22, 8899, 8900],
            target_root_volume_type=st.get("target_root_volume_type", "SAS"),
            target_root_volume_size=st.get("target_root_volume_size", 40),
            target_password=st.get("target_password", ""),
            use_eip=st.get("use_eip", True),
            eip_id=st.get("eip_id", ""),
            eip_bandwidth_size=st.get("eip_bandwidth_size", 5),
            eip_type=st.get("eip_type", "5_bgp"),
            eip_charge_mode=st.get("eip_charge_mode", "traffic"),
            sg_merge=st.get("sg_merge", True),
            eip_reuse_policy=st.get("eip_reuse_policy", "free-first"),
        )


        # ownership（资源属主标识，OwnerID 指纹算法）
        ow = raw.get("ownership", {})
        cfg.ownership = OwnershipConfig(
            enabled=ow.get("enabled", True),
            salt=ow.get("salt", "huawei-cloud-migration-windows-ecs:v1"),
            owner_tag_key=ow.get("owner_tag_key", "owner"),
            owner_tag_value=ow.get("owner_tag_value", "huawei-cloud-migration-windows-ecs"),
            owner_id_tag=ow.get("owner_id_tag", "owner_id"),
            name_prefixes=tuple(ow.get("name_prefixes") or ("vpc-mig-", "subnet-mig-", "sg-mig-", "eip-mig-")),
            state_file=ow.get("state_file", "config/owned_resources.json"),
        )

        return cfg
