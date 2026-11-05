import json
import re
from typing import Optional, Dict, Any, List, Tuple

from .session_manager import SessionManager
from .command_validator import CommandValidator, CommandType


class CommandExecutor:
    def __init__(self):
        self.session_manager = SessionManager()
        self.command_validator = CommandValidator()
        self.pending_confirmation = None
        self.pending_disk_merge = None
        self.interactive = False

    # ========== Connection Parsing ==========

    def parse_connection_string(self, text: str) -> Optional[Dict[str, Any]]:
        patterns = {
            'host': r'(?:connect|address|IP|host)\s*[:：]?\s*(\d{1,3}(?:\.\d{1,3}){3})',
            'port': r'(?:port|port)\s*[:：]?\s*(\d+)',
            'user': r'(?:account|username|user|root|admin)\s*[:：]?\s*(\w+)',
            'password': r'(?:password|pwd|pass)\s*[:：]?\s*(\S+)',
            'key': r'(?:key|key-file|keyfile|private[_-]?key)\s*[:：]?\s*(\S+)',
        }
        result = {}
        for key, pattern in patterns.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                result[key] = match.group(1)
        if 'host' in result:
            result.setdefault('port', '22')
            result.setdefault('user', 'root')
            return result
        return None

    # ========== Main Entry ==========

    def handle_command(self, text: str) -> str:
        text = text.strip()

        # Cancel/Confirm
        if text in ('cancel', 'abort'):
            self.pending_confirmation = None
            self.pending_disk_merge = None
            return 'Operation cancelled'

        if text == 'confirm' and self.pending_confirmation:
            command = self.pending_confirmation
            self.pending_confirmation = None
            return self._validate_and_execute(command, confirmed=True)

        if text == 'confirm' and self.pending_disk_merge:
            return self._execute_disk_merge(self.pending_disk_merge)

        # Security: in interactive mode, never accept passwords passed in the conversation
        if self.interactive and (re.search(r'\b(?:password|pass|pwd)\b', text, re.IGNORECASE) or '密码' in text):
            return "❌ 出于安全考虑，禁止在对话中输入密码。请使用命令行参数 --password 传入。"

        # Switch Target (Switch to)
        switch_match = re.match(r'(?:switch\s+to)\s+(\d{1,3}(?:\.\d{1,3}){3})', text, re.IGNORECASE)
        if switch_match:
            host = switch_match.group(1)
            if self.session_manager.switch_by_host(host):
                return f"Switched to {host}"
            return f"❌ No active connection to {host}"

        # Connection Management
        if text == 'view connections':
            return self._list_connections()
        if text in ('disconnect SSH', 'disconnect', 'exit SSH'):
            return self._disconnect()

        # connect (parsed BEFORE natural language modules to avoid misrouting)
        connect_info = self.parse_connection_string(text)
        if connect_info:
            return self._connect(connect_info)

        # ===== Natural Language Module Routing =====
        # Match modules by priority

        # Disk Module
        r = self._handle_disk_nl(text)
        if r:
            return r

        # System Monitoring Module
        r = self._handle_system_nl(text)
        if r:
            return r

        # Network Module
        r = self._handle_network_nl(text)
        if r:
            return r

        # Docker/Container Module
        r = self._handle_docker_nl(text)
        if r:
            return r

        # Security Module
        r = self._handle_security_nl(text)
        if r:
            return r

        # Log Module
        r = self._handle_log_nl(text)
        if r:
            return r

        # File Operation Module
        r = self._handle_file_nl(text)
        if r:
            return r

        # Execute directly if connected
        if self.session_manager.active_session:
            return self._validate_and_execute(text)

        # Domain/hostname connection attempt → only IPv4 supported
        if re.search(r'[a-zA-Z]', text) and re.search(r'connect|连接|链接', text, re.IGNORECASE):
            return '❌ 仅支持 IPv4 地址格式的主机（如 192.168.1.100），不支持域名或主机名'
        return 'Please provide target host IP, port, username and password'

    # ========== Disk Module ==========

    def _handle_disk_nl(self, text: str) -> Optional[str]:
        """Disk-related natural language"""
        keywords_map = {
            # detect/view
            ('detect disk', 'view disk', 'unmounted disk', 'disk status', 'disk list', 'lsblk',
             '磁盘', '查看磁盘', '磁盘情况', '挂载', '硬盘', '磁盘列表'): 'detect',
            ('disk health', 'disk SMART', 'smartctl', 'disk check', '磁盘健康', '磁盘检查', '硬盘健康'): 'health',
            ('free space', 'available space', 'disk free', 'space check', '磁盘空间', '剩余空间', '可用空间', '空间检查'): 'space',
            ('disk space', 'disk detail', 'disk full', 'disk comprehensive', '磁盘详情', '磁盘总览', '磁盘综合', '磁盘使用'): 'full_report',
            # LVM
            ('LVM information', 'volume group info', 'VG info', 'LV info', 'logical volume', 'LVM信息', '逻辑卷', '卷组信息'): 'lvm_info',
            ('LVM extend', 'LV extend', 'logical volume extend', 'extend', '扩展逻辑卷', '扩容'): 'lvm_extend',
            # Partition
            ('partition information', 'view partition', 'fdisk', '分区信息', '查看分区'): 'partition_info',
            # mounted at/unmount
            ('auto mount on boot', 'boot mount', 'fstab', 'auto mount', '开机自动挂载', '自动挂载'): 'auto_mount',
            ('unmount', 'umount', '卸载'): 'umount',
        }

        for keywords, action in keywords_map.items():
            if any(kw in text for kw in keywords):
                if not self.session_manager.active_session:
                    return 'Please establish SSH connection first'
                if action == 'detect':
                    return self._detect_disks()
                elif action == 'full_report':
                    return self._disk_full_report()
                elif action == 'health':
                    return self._exec_simple('disk health check', 'smartctl -a /dev/sda 2>/dev/null || echo "smartctl not installed, trying lsblk"; lsblk -o NAME,SIZE,TYPE,ROTA,MOUNTPOINT')
                elif action == 'space':
                    return self._exec_simple('disk free space', 'df -h | grep -v tmpfs | grep -v devtmpfs | grep -v overlay | grep -v shm')
                elif action == 'lvm_info':
                    return self._exec_simple('LVM information', 'echo "=== volume group ==="; vgdisplay 2>/dev/null | grep -E "VG Name|VG Size|Free PE|Alloc PE"; echo; echo "=== logical volume ==="; lvdisplay 2>/dev/null | grep -E "LV Name|LV Size|VG Name"; echo; echo "=== physical volume ==="; pvdisplay 2>/dev/null | grep -E "PV Name|PV Size|VG Name"')
                elif action == 'lvm_extend':
                    return self._handle_lvm_extend(text)
                elif action == 'partition_info':
                    return self._exec_simple('partition information', 'fdisk -l 2>/dev/null || parted -l 2>/dev/null')
                elif action == 'auto_mount':
                    return self._handle_auto_mount(text)
                elif action == 'umount':
                    return self._handle_umount(text)

        # Disk merge
        if any(kw in text for kw in ('merge', 'LVM merge', 'Disk merge')):
            merge_info = self.parse_disk_merge_command(text)
            if merge_info:
                if not self.session_manager.active_session:
                    return 'Please establish SSH connection first'
                return self._confirm_disk_merge(merge_info)
            return '❌ Unable to parseDisk mergecommand. Please input in format:\nExample: Merge nvme0n1, nvme1n1, nvme2n1merged and mounted to/home'

        # mounted at(not auto mount on boot)
        mount_match = re.search(r'mounted at\s+(\S+)\s*to\s*(\S+)', text)
        if mount_match:
            if not self.session_manager.active_session:
                return 'Please establish SSH connection first'
            device, mnt = mount_match.group(1), mount_match.group(2)
            self.pending_confirmation = f'mkdir -p {mnt} && mount {device} {mnt}'
            return f'⚠️ Will mount {device} to {mnt}，confirm to execute？\n\nPlease reply "confirm" or "cancel"'

        return None

    def _handle_lvm_extend(self, text: str) -> str:
        """Handle LVM extend"""
        # parse：extend /dev/vg_home/lv_home increase by 100G
        lv_match = re.search(r'extend\s+(\S+)\s*(?:increase by|increase by|extend by)\s*(\d+)\s*[GTgt]', text)
        if lv_match:
            lv_path = lv_match.group(1)
            size = lv_match.group(2)
            self.pending_confirmation = f'lvextend -L +{size}G {lv_path} && resize2fs {lv_path}'
            return f'⚠️ Will extend logical volume {lv_path} increase by {size}G，confirm to execute？\n\nPlease reply "confirm" or "cancel"'

        # parse：extend /home increase by 100G
        mnt_match = re.search(r'extend\s+(\S+)\s*(?:increase by|increase by|extend by)\s*(\d+)\s*[GTgt]', text)
        if mnt_match:
            mnt = mnt_match.group(1)
            size = mnt_match.group(2)
            self.pending_confirmation = f'lvextend -L +{size}G $(df --output=source {mnt} | tail -1) && resize2fs $(df --output=source {mnt} | tail -1)'
            return f'⚠️ Will extend mount point {mnt} increase by {size}G，confirm to execute？\n\nPlease reply "confirm" or "cancel"'

        return '❌ Unable to parse extend command\n\nExample: extend /dev/vg_home/lv_home increase by 100G\n      extend /home increase by 50G'

    def _handle_umount(self, text: str) -> str:
        """Handle unmount"""
        target = re.search(r'unmount\s+(\S+)', text)
        if target:
            path = target.group(1)
            self.pending_confirmation = f'umount {path}'
            return f'⚠️ Sensitive: Will unmount {path}\n\nPlease reply "confirm" or "cancel"'
        return '❌ Please specify unmount target，Example: unmount /home'

    # ========== System Monitoring Module ==========

    def _handle_system_nl(self, text: str) -> Optional[str]:
        """system monitoringnatural language"""
        if not self.session_manager.active_session:
            # Only help info does not require connection
            if any(kw in text for kw in ('system monitoring', 'system info', 'help', 'help')):
                return self._system_help()
            return None

        keywords_map = {
            ('CPU info', 'CPU monitoring', 'CPU usage', 'cpu', 'CPU', '处理器', 'CPU占用', 'CPU使用', 'cpu占用'): 'cpu',
            ('memory info', 'memory monitoring', 'memory usage', 'memory', '内存', '内存占用', '内存使用', '内存信息', '内存情况'): 'memory',
            ('system info', 'system overview', 'system status', 'system monitoring', 'overview', '系统信息', '系统状态', '系统监控', '系统概览', '系统情况'): 'overview',
            ('system update', 'update system', 'upgrade', 'update', '系统更新', '更新系统', '升级系统'): 'update',
            ('uptime', 'start time', '运行时间', '开机时间'): 'uptime',
            ('user list', 'online users', 'logged-in users', 'who', '用户列表', '在线用户'): 'users',
            ('scheduled tasks', 'crontab', 'cron', '定时任务', '计划任务'): 'crontab',
            ('process list', 'process view', 'ps', 'top processes', '进程列表', '进程'): 'processes',
            ('environment variables', 'env', '环境变量'): 'env',
            ('system version', 'version info', 'OS version', '系统版本', '版本信息'): 'version',
            ('hostname', '主机名'): 'hostname',
        }

        for keywords, action in keywords_map.items():
            if any(kw in text for kw in keywords):
                if action == 'cpu':
                    return self._exec_simple('CPU info', 'echo "=== CPU model ==="; lscpu | grep "Model name"; echo; echo "=== CPU Cores ==="; nproc; echo; echo "=== CPU Load ==="; uptime; echo; echo "=== TOP5 Processes ==="; ps -eo pid,comm,%cpu --sort=-%cpu | head -6')
                elif action == 'memory':
                    return self._exec_simple('memory info', 'free -h; echo; echo "=== TOP5 memory processes ==="; ps -eo pid,comm,%mem,rss --sort=-%mem | head -6')
                elif action == 'overview':
                    return self._exec_simple('system overview', 'echo "=== host ==="; hostname; echo; echo "=== System ==="; cat /etc/os-release | head -2; echo; echo "=== Kernel ==="; uname -r; echo; echo "=== uptime ==="; uptime; echo; echo "=== CPU ==="; lscpu | grep "Model name"; echo "Cores: $(nproc)"; echo; echo "=== Memory ==="; free -h | head -2; echo; echo "=== Disk ==="; df -h | grep -v tmpfs | grep -v devtmpfs | grep -v overlay | grep -v shm')
                elif action == 'update':
                    self.pending_confirmation = 'apt-get update && apt-get upgrade -y 2>/dev/null || yum update -y 2>/dev/null || dnf upgrade -y 2>/dev/null || echo "Package manager not found"'
                    return '⚠️ Sensitive: system update\n\nWill execute system package update, may affect service operation.\n\nPlease reply "confirm" or "cancel"'
                elif action == 'uptime':
                    return self._exec_simple('uptime', 'uptime')
                elif action == 'users':
                    return self._exec_simple('online users', 'who; echo; echo "=== recent logins ==="; last -5')
                elif action == 'crontab':
                    return self._exec_simple('scheduled tasks', 'echo "=== current user crontab ==="; crontab -l 2>/dev/null; echo "=== end of crontab ==="')
                elif action == 'processes':
                    return self._exec_simple('process list', 'ps aux --sort=-%cpu | head -20')
                elif action == 'env':
                    return self._exec_simple('environment variables', 'env | sort | head -40')
                elif action == 'version':
                    return self._exec_simple('system version', 'cat /etc/os-release; echo; uname -a')
                elif action == 'hostname':
                    return self._exec_simple('hostname', 'hostname; hostnamectl 2>/dev/null')
        return None

    def _system_help(self) -> str:
        return """📋 system monitoringcommands:
- CPU info / CPU usage
- memory info / memory usage
- system overview / system status
- uptime
- user list / online users
- scheduled tasks / crontab
- process list
- system update(requires confirmation)
- system version / hostname"""

    # ========== Network Module ==========

    def _handle_network_nl(self, text: str) -> Optional[str]:
        """Network-relatednatural language"""
        if not self.session_manager.active_session:
            return None

        keywords_map = {
            ('port scan', 'port list', 'listening ports', 'open ports', '端口', '端口扫描', '端口开放', '端口情况', '开放端口', '监听端口'): 'ports',
            ('firewall status', 'firewall', 'iptables', 'ufw', '防火墙'): 'firewall',
            ('routing table', 'route', '路由表', '路由'): 'route',
            ('network interface', 'ip addr', '网卡', '网络接口'): 'nic',
            ('DNS', 'dns', 'Dns', 'domain name parse', '域名解析', 'dns解析'): 'dns',
            ('network connections', 'connection status', 'netstat', 'ss', '网络连接', '连接状态'): 'connections',
            ('network test', 'ping', '网络测试', '网络连通'): 'ping',
        }

        for keywords, action in keywords_map.items():
            if any(kw in text for kw in keywords):
                if action == 'ports':
                    return self._exec_simple('listening ports', 'ss -tlnp 2>/dev/null || netstat -tlnp 2>/dev/null')
                elif action == 'firewall':
                    return self._exec_simple('firewall status', 'echo "=== iptables ==="; iptables -L -n 2>/dev/null || echo "no permission or not installed"; echo; echo "=== ufw ==="; ufw status 2>/dev/null || echo "ufw not installed"; echo; echo "=== firewalld ==="; firewall-cmd --list-all 2>/dev/null || echo "firewalld not running"')
                elif action == 'route':
                    return self._exec_simple('routing table', 'ip route show 2>/dev/null || route -n 2>/dev/null')
                elif action == 'nic':
                    return self._exec_simple('network interface', 'ip addr show 2>/dev/null || ifconfig 2>/dev/null')
                elif action == 'dns':
                    return self._exec_simple('DNS info', 'echo "=== resolv.conf ==="; cat /etc/resolv.conf; echo; echo "=== DNS Test ==="; nslookup google.com 2>/dev/null || dig google.com 2>/dev/null || echo "DNS tools not installed"')
                elif action == 'connections':
                    return self._exec_simple('network connections', 'ss -tnp 2>/dev/null | head -30 || netstat -tnp 2>/dev/null | head -30')
                elif action == 'ping':
                    host = re.search(r'ping\s+(\S+)', text)
                    target = host.group(1) if host else 'baidu.com'
                    return self._exec_simple(f'Ping {target}', f'ping -c 4 {target}')

        # firewall operations (sensitive)
        if any(kw in text for kw in ('open ports', 'open port', 'add port')):
            port_match = re.search(r'port\s*(\d+)', text)
            if port_match:
                port = port_match.group(1)
                self.pending_confirmation = f'iptables -A INPUT -p tcp --dport {port} -j ACCEPT 2>/dev/null; firewall-cmd --add-port={port}/tcp --permanent 2>/dev/null; firewall-cmd --reload 2>/dev/null; ufw allow {port} 2>/dev/null; echo "alreadytrytestopen ports {port}"'
                return f'⚠️ Sensitive: open ports {port}\n\nPlease reply "confirm" or "cancel"'

        return None

    # ========== Docker/Container Module ==========

    def _handle_docker_nl(self, text: str) -> Optional[str]:
        """Docker containernatural language"""
        if not self.session_manager.active_session:
            return None

        # First check if it is a container-related command
        docker_keywords = ('container', 'docker', 'Docker', 'image', 'compose', 'Compose',
                           '容器', '镜像')
        if not any(kw in text for kw in docker_keywords):
            return None

        keywords_map = {
            ('container list', 'container status', 'docker ps', 'running containers',
             '容器列表', '运行容器', '容器状态', '容器'): 'ps',
            ('all containers', '全部容器', '所有容器'): 'ps_all',
            ('image list', 'docker images', 'image view', '镜像列表', '查看镜像'): 'images',
            ('container logs', 'dockerlog', 'logview', '容器日志'): 'logs',
            ('docker info', 'docker status', 'docker信息'): 'info',
            ('docker disk', 'docker size', 'docker usage', 'docker磁盘', 'docker占用'): 'disk_usage',
            ('compose status', 'compose ps'): 'compose_ps',
        }

        for keywords, action in keywords_map.items():
            if any(kw in text for kw in keywords):
                if action == 'ps':
                    return self._exec_simple('running containers', 'docker ps --format "table {{.Names}}\\t{{.Status}}\\t{{.Image}}\\t{{.Ports}}"')
                elif action == 'ps_all':
                    return self._exec_simple('all containers', 'docker ps -a --format "table {{.Names}}\\t{{.Status}}\\t{{.Image}}"')
                elif action == 'images':
                    return self._exec_simple('docker images', 'docker images --format "table {{.Repository}}\\t{{.Tag}}\\t{{.Size}}\\t{{.CreatedSince}}"')
                elif action == 'info':
                    return self._exec_simple('docker info', 'docker info 2>/dev/null | head -20')
                elif action == 'disk_usage':
                    return self._exec_simple('Docker Disk Usage', 'docker system df')
                elif action == 'compose_ps':
                    return self._exec_simple('compose status', 'docker compose ps 2>/dev/null || docker-compose ps 2>/dev/null || echo "no composeoseitemtarget"')

        # container logs(requires container name)
        log_match = re.search(r'(?:container|docker)?\s*log\s+(\S+)', text)
        if not log_match:
            log_match = re.search(r"(\S+)\s*(?:'s)?log", text)
        if log_match:
            container = log_match.group(1)
            lines_match = re.search(r'(\d+)\s*lines', text)
            lines = lines_match.group(1) if lines_match else '50'
            return self._exec_simple(f'{container}log', f'docker logs --tail {lines} {container} 2>&1')

        # containerstart/stop(sensitive)
        start_match = re.search(r'start\s+(?:container\s+)?(\S+)', text)
        if start_match:
            container = start_match.group(1)
            self.pending_confirmation = f'docker start {container}'
            return f'⚠️ Will start container {container}\n\nPlease reply "confirm" or "cancel"'

        stop_match = re.search(r'stop\s+(?:container\s+)?(\S+)', text)
        if not stop_match:
            stop_match = re.search(r'(?:container\s+)?(\S+)\s*stop', text)
        if stop_match:
            container = stop_match.group(1)
            self.pending_confirmation = f'docker stop {container}'
            return f'⚠️ Sensitive: Will stop container {container}\n\nPlease reply "confirm" or "cancel"'

        restart_match = re.search(r'restart\s+(?:container\s+)?(\S+)', text)
        if restart_match:
            container = restart_match.group(1)
            self.pending_confirmation = f'docker restart {container}'
            return f'⚠️ Sensitive: Will restart container {container}\n\nPlease reply "confirm" or "cancel"'

        # remove container(high-risk)
        rm_match = re.search(r'delete\s+(?:container\s+)?(\S+)', text)
        if rm_match:
            container = rm_match.group(1)
            self.pending_confirmation = f'docker rm -f {container}'
            return f'⚠️⚠️ High-risk: Will remove container {container}\n\nPlease reply "confirm" or "cancel"'

        # delete image(high-risk)
        rmi_match = re.search(r'delete\s+(?:image\s+)?(\S+:\S+|\S+)', text)
        if rmi_match and 'image' in text:
            image = rmi_match.group(1)
            self.pending_confirmation = f'docker rmi {image}'
            return f'⚠️⚠️ High-risk: Will delete image {image}\n\nPlease reply "confirm" or "cancel"'

        # Docker cleanup(high-risk)
        if any(kw in text for kw in ('docker cleanup', 'docker cleanup', 'docker prune', 'docker clean')):
            self.pending_confirmation = 'docker system prune -af 2>/dev/null'
            return '⚠️⚠️ High-risk: Will clean up all unused Docker resources(containers, images, networks, cache)\n\nPlease reply "confirm" or "cancel"'

        return None

    # ========== Security Module ==========

    def _handle_security_nl(self, text: str) -> Optional[str]:
        """Security-relatednatural language"""
        if not self.session_manager.active_session:
            return None

        keywords_map = {
            ('login audit', 'login records', 'recent logins', 'last', '登录审计', '登录记录', '最近登录', '登录日志'): 'login_audit',
            ('failed logins', 'login failures', 'brute force', 'btmp', '登录失败', '失败登录'): 'failed_login',
            ('SSH config', 'sshd config', 'ssh配置'): 'ssh_config',
            ('key list', 'SSH keys', 'authorized_keys', '密钥列表', 'ssh密钥'): 'ssh_keys',
            ('security check', 'security audit', 'security status', '安全检查', '安全审计', '安全状态'): 'security_check',
            ('user list', 'system users', '用户列表', '系统用户'): 'system_users',
            ('SUID files', 'suid', 'privileged files', '特权文件'): 'suid_check',
        }

        for keywords, action in keywords_map.items():
            if any(kw in text for kw in keywords):
                if action == 'login_audit':
                    return self._exec_simple('login audit', 'echo "=== recent successful logins ==="; last -20; echo; echo "=== Current Users ==="; who')
                elif action == 'failed_login':
                    return self._exec_simple('failed logins', 'lastb -20 2>/dev/null || echo "No failed login records or permission denied"')
                elif action == 'ssh_config':
                    return self._exec_simple('SSH config', 'grep -v "^#" /etc/ssh/sshd_config 2>/dev/null | grep -v "^$"')
                elif action == 'ssh_keys':
                    return '❌ 出于安全合规考虑，已禁用读取远程 SSH 授权密钥/凭据文件（authorized_keys 等）的功能，请使用其他安全检查命令。'
                elif action == 'security_check':
                    return self._exec_simple('security check', 'echo "=== open ports ==="; ss -tlnp 2>/dev/null | head -20; echo; echo "=== firewall ==="; iptables -L -n 2>/dev/null | head -10 || echo "none"; echo; echo "=== SSH config ==="; grep -E "^(PermitRootLogin|PasswordAuthentication|Port)" /etc/ssh/sshd_config 2>/dev/null; echo; echo "=== failed logins (recent 5) ==="; lastb -10 2>/dev/null | head -5 || echo "none"')
                elif action == 'system_users':
                    return self._exec_simple('system users', 'echo "=== logged-in users ==="; who 2>/dev/null || echo "none"; echo; echo "=== recent login failures ==="; lastb -10 2>/dev/null || echo "none"')
                elif action == 'suid_check':
                    return self._exec_simple('SUID files', 'find / -perm -4000 -type f 2>/dev/null | head -30')

        # Key generation (sensitive)
        if 'generate key' in text or 'create key' in text:
            key_file = '$HOME/.ssh/oa_ed25519'
            self.pending_confirmation = f'ssh-keygen -t ed25519 -f {key_file} -N "" -q && cat {key_file}.pub'
            return '⚠️ Will generate a new ED25519 key pair and print the public key\n\nPlease reply "confirm" or "cancel"'

        return None

    # ========== Log Module ==========

    def _handle_log_nl(self, text: str) -> Optional[str]:
        """Log-relatednatural language"""
        if not self.session_manager.active_session:
            return None

        keywords_map = {
            ('system logs', 'syslog', 'messages', '系统日志', '日志'): 'syslog',
            ('kernel log', 'dmesg', 'kernellog', '内核日志'): 'dmesg',
            ('SSH logs', 'sshlog', 'authlog', 'SSH日志'): 'auth_log',
            ('error log', 'errorlog', 'troubleshoot', '错误日志'): 'errors',
        }

        for keywords, action in keywords_map.items():
            if any(kw in text for kw in keywords):
                if action == 'syslog':
                    return self._exec_simple('system logs', 'tail -50 /var/log/syslog 2>/dev/null || tail -50 /var/log/messages 2>/dev/null || echo "logfilenotfindto"')
                elif action == 'dmesg':
                    return self._exec_simple('kernel log', 'dmesg | tail -30')
                elif action == 'auth_log':
                    return self._exec_simple('SSH logs', 'tail -30 /var/log/auth.log 2>/dev/null || tail -30 /var/log/secure 2>/dev/null || echo "logfilenotfindto"')
                elif action == 'errors':
                    return self._exec_simple('troubleshoot', 'echo "=== system errors ==="; journalctl -p err --no-pager -n 20 2>/dev/null || grep -i error /var/log/syslog 2>/dev/null | tail -20 || grep -i error /var/log/messages 2>/dev/null | tail -20 || echo "noneerror log"')

        # Specify log file
        log_match = re.search(r'(?:view|read|analyze)?\s*log\s+(\S+)', text)
        if log_match:
            logfile = log_match.group(1)
            lines_match = re.search(r'(\d+)\s*lines', text)
            lines = lines_match.group(1) if lines_match else '50'
            return self._exec_simple(f'log {logfile}', f'tail -{lines} {logfile} 2>/dev/null || echo "file does not exist"')

        # journalctl
        if 'journalctl' in text or 'service log' in text:
            service = re.search(r'(?:service log|journalctl)\s+(\S+)', text)
            if service:
                return self._exec_simple(f'{service.group(1)}service log', f'journalctl -u {service.group(1)} --no-pager -n 50 2>/dev/null || echo "service not found"')
            return self._exec_simple('system logs(journal)', 'journalctl --no-pager -n 30')

        return None

    # ========== File Operation Module ==========

    def _handle_file_nl(self, text: str) -> Optional[str]:
        """file operationnatural language"""
        if not self.session_manager.active_session:
            return None

        # delete file/directory(high-risk) — checked first so delete intent wins over list/view
        Delete_hit = ('delete' in text.lower() or '删除' in text)
        if Delete_hit and 'container' not in text and 'image' not in text and '容器' not in text and '镜像' not in text:
            rm_path = None
            rm_match = re.search(r'(?:delete|删除)\s*(?:file|directory|folder|文件|目录)?\s+(\S+)', text, re.IGNORECASE)
            if rm_match and rm_match.group(1):
                rm_path = rm_match.group(1)
            else:
                path_match = re.search(r'(?:/[\w.\-/]+)', text)
                if path_match:
                    rm_path = path_match.group(0)
            if rm_path:
                self.pending_confirmation = f'rm -rf {rm_path}'
                return f'⚠️⚠️ High-risk: Will delete {rm_path}\n\nPlease reply "confirm" or "cancel"'

        # view file/directory
        if any(kw in text for kw in ('view file', 'read file', 'cat file', '查看文件', '读取文件')):
            path = re.search(r'(?:view|read|cat|查看|读取)\s+(?:file\s+)?(\S+)', text)
            if not path:
                path = re.search(r'(?:/[\w.\-/]+)', text)
            if path:
                return self._exec_simple(f'view {path.group(1)}', f'cat {path.group(1)} 2>/dev/null || echo "file does not exist"')

        # list directory
        if ('list' in text or 'ls' in text or 'directory' in text or '查看' in text or '列出' in text or '目录' in text or '文件' in text):
            path_match = re.search(r'(?:/[\w.\-/]+)', text)
            if path_match:
                path = path_match.group(0)
            else:
                ls_match = re.search(r'(?:list|ls|view|查看|列出)\s*(?:directory\s+)?(\S+)', text)
                if not ls_match or not ls_match.group(1):
                    path = '/tmp'
                else:
                    path = ls_match.group(1)
            return self._exec_simple(f'list {path}', f'ls -lah {path} 2>/dev/null || echo "path does not exist"')

        # findfile
        find_match = re.search(r'find\s+(\S+)', text)
        if find_match:
            name = find_match.group(1)
            return self._exec_simple(f'find {name}', f'find / -name "{name}" -type f 2>/dev/null | head -20')

        # createdirectory
        mkdir_match = re.search(r'(?:create|create)\s*(?:directory|folder)\s+(\S+)', text)
        if mkdir_match:
            path = mkdir_match.group(1)
            self.pending_confirmation = f'mkdir -p {path}'
            return f'⚠️ Will create directory {path}\n\nPlease reply "confirm" or "cancel"'

        # create file
        touch_match = re.search(r'(?:create|create)\s*(?:file)\s+(\S+)', text)
        if touch_match:
            path = touch_match.group(1)
            self.pending_confirmation = f'touch {path}'
            return f'Will create file {path}，confirm？\n\nPlease reply "confirm" or "cancel"'

        # copyfile
        cp_match = re.search(r'copy\s+(\S+)\s*(?:to|→|->)\s*(\S+)', text)
        if cp_match:
            src, dst = cp_match.group(1), cp_match.group(2)
            self.pending_confirmation = f'cp -r {src} {dst}'
            return f'⚠️ Will copy {src} → {dst}\n\nPlease reply "confirm" or "cancel"'

        # movefile
        mv_match = re.search(r'(?:move|move)\s+(\S+)\s*(?:to|→|->)\s*(\S+)', text)
        if mv_match:
            src, dst = mv_match.group(1), mv_match.group(2)
            self.pending_confirmation = f'mv {src} {dst}'
            return f'⚠️ Sensitive: Will move {src} → {dst}\n\nPlease reply "confirm" or "cancel"'

        # chmod
        chmod_match = re.search(r'(?:chmod|chmod)\s+(\S+)\s+(\S+)', text)
        if chmod_match:
            perm, path = chmod_match.group(1), chmod_match.group(2)
            self.pending_confirmation = f'chmod {perm} {path}'
            return f'⚠️ Sensitive: Will change {path} permissions to {perm}\n\nPlease reply "confirm" or "cancel"'

        # file size
        du_match = re.search(r'(?:file size|directory size|du)\s+(\S+)', text)
        if du_match:
            path = du_match.group(1)
            return self._exec_simple(f'{path} size', f'du -sh {path} 2>/dev/null || echo "path does not exist"')

        return None

    # ========== General Execution ==========

    def _exec_simple(self, title: str, command: str) -> str:
        """Simple execution with formatted output"""
        result = self.session_manager.execute_command(command, timeout=60)
        if result.error:
            return f"❌ {title} Execution failed: {result.message}"
        output = f"📋 {title}\n"
        output += f"host: {result.target_host} | time: {result.duration:.2f}s\n"
        output += f"{'─' * 40}\n"
        if result.stdout:
            output += result.stdout
        if result.stderr:
            output += f"\n⚠️ {result.stderr}"
        return output

    # ========== Original Disk Functions ==========

    def parse_disk_merge_command(self, text: str) -> Optional[Dict[str, Any]]:
        disk_pattern = r'(nvme\d+n\d+)'
        disks = re.findall(disk_pattern, text)
        if not disks:
            return None
        mount_point = None
        for pattern in [r'mounted at\s*([/\w]+)', r'mounted at\s*([/\w]+)', r'to\s*([/\w]+)']:
            match = re.search(pattern, text)
            if match:
                mount_point = match.group(1)
                if not mount_point.startswith('/'):
                    mount_point = '/' + mount_point
                break
        if not mount_point:
            mount_point = '/home'
        return {'disks': disks, 'mount_point': mount_point}

    def _disk_full_report(self) -> str:
        """Disk full report：Physical Disks + Partition Usage + LVM Combined Volumes + Docker Directory Mapping(table format)"""
        if not self.session_manager.active_session:
            return 'Please establish SSH connection first'

        # Single command to reduce SSH round trips
        cmd = r'''echo "=====Physical Disks====="
lsblk -d -o NAME,SIZE,TYPE,ROTA,MOUNTPOINT 2>/dev/null | grep -v "loop" | grep -v "ram"
echo
echo "=====Partition Usage====="
df -h | grep -v tmpfs | grep -v devtmpfs | grep -v overlay | grep -v shm
echo
echo "=====LVM Combined Volumes====="
if command -v vgdisplay &>/dev/null; then
  echo "---volume group---"
  vgdisplay 2>/dev/null | grep -E "VG Name|VG Size|Free PE|Alloc PE"
  echo "---logical volume---"
  lvdisplay 2>/dev/null | grep -E "LV Name|LV Size|VG Name"
  echo "---physical volume---"
  pvdisplay 2>/dev/null | grep -E "PV Name|PV Size|VG Name"
else
  echo "LVM not installed"
fi
echo
echo "=====Docker Directory Mapping====="
if command -v docker &>/dev/null; then
  docker ps --format '{{.Names}}' 2>/dev/null | while read cname; do
    echo "-- $cname --"
    docker inspect "$cname" --format '{{range .Mounts}}  {{.Type}}: {{.Source}} -> {{.Destination}}{{"\n"}}{{end}}' 2>/dev/null
  done
  echo
  echo "---Docker Disk Usage---"
  docker system df 2>/dev/null
else
  echo "Docker not installed"
fi'''

        result = self.session_manager.execute_command(cmd, timeout=60)
        if result.error:
            return f"❌ Disk full reportExecution failed: {result.message}"

        raw = result.stdout or ''
        sections = {}
        current = None
        for line in raw.split('\n'):
            if line.startswith('=====') and line.endswith('====='):
                current = line.strip('=').strip()
                sections[current] = []
            elif current is not None:
                sections[current].append(line)

        output = f"📊 Disk full report\nhost: {result.target_host} | time: {result.duration:.2f}s\n{'─'*50}\n"

        # ── Physical Disks (table with usage info) ──
        output += "\n📦 Physical Disks\n"
        # Collect partition usage info first，indexed by disk name or VG name
        part_info = {}
        if 'Partition Usage' in sections:
            for l in sections['Partition Usage']:
                parts = l.split()
                if len(parts) >= 6 and parts[0] != 'Filesystem':
                    fs = parts[0]
                    mount = parts[5] if len(parts) > 5 else parts[-1]
                    if '/dev/mapper/' in fs:
                        vg_name = fs.replace('/dev/mapper/', '').split('-')[0]
                        part_info[vg_name] = (parts[1], parts[2], parts[3], parts[4], mount)
                    elif '/dev/' in fs:
                        disk_name = fs.replace('/dev/', '')
                        base = re.sub(r'p?\d+$', '', disk_name) if not disk_name.endswith('n1') else disk_name
                        if base not in part_info:
                            part_info[base] = (parts[1], parts[2], parts[3], parts[4], mount)
                        else:
                            old = part_info[base]
                            part_info[base] = (old[0], old[1], old[2], old[3], old[4] + ', ' + mount)

        if 'Physical Disks' in sections:
            lines = [l for l in sections['Physical Disks'] if l.strip()]
            disks = []
            for l in lines:
                parts = l.split()
                if len(parts) >= 3 and parts[0] != 'NAME':
                    name = '/dev/' + parts[0]
                    size = parts[1]
                    rota = parts[3] if len(parts) > 3 else '?'
                    disk_type = 'HDD' if rota == '1' else 'NVMe'
                    disks.append((name, size, disk_type, parts[0]))

            if disks:
                # detectLVM PV→VG mapping
                lvm_pvs = {}
                if 'LVM Combined Volumes' in sections:
                    pv_name = ''
                    for l in sections['LVM Combined Volumes']:
                        if 'PV Name' in l and '/dev/' in l:
                            pv_name = l.split('/dev/')[-1].strip().split()[0]
                        elif 'VG Name' in l and pv_name:
                            vg = l.split('VG Name')[-1].strip()
                            lvm_pvs[pv_name] = vg
                            pv_name = ''

                # Find system disk
                root_disk = None
                for l in lines:
                    parts = l.split()
                    if len(parts) >= 2 and parts[0] != 'NAME':
                        if parts[0].startswith('sd') and not any(c.isdigit() for c in parts[0]):
                            root_disk = '/dev/' + parts[0]
                            break

                # build row：(Disk, Size, Type, Usage, Total, Used, Available, Usage%)
                rows = []
                for d in disks:
                    dev_short = d[3]
                    if d[0] == root_disk:
                        use = 'System Disk'
                        info = part_info.get(dev_short, ('', '', '', '', ''))
                    elif dev_short in lvm_pvs:
                        vg = lvm_pvs[dev_short]
                        use = f'LVM→{vg}'
                        info = part_info.get(vg, ('', '', '', '', ''))
                    else:
                        use = 'Unallocated'
                        info = ('', '', '', '', '')
                    rows.append((d[0], d[1], d[2], use, info[0], info[1], info[2], info[3]))

                if rows:
                    col_names = ['Disk', 'Size', 'Type', 'Usage', 'Total', 'Used', 'Available', 'Usage%']
                    col_vals = [[r[i] for r in rows] for i in range(8)]
                    widths = [max(len(n), max(len(v) for v in vals) if vals else 0) + 2 for n, vals in zip(col_names, col_vals)]

                    hdr = ''.join(f"{n:<{w}}" for n, w in zip(col_names, widths))
                    output += hdr + "\n"
                    output += "─" * len(hdr) + "\n"
                    for r in rows:
                        output += ''.join(f"{r[i]:<{widths[i]}}" for i in range(8)) + "\n"
            else:
                output += "  (No data)\n"

        # ── LVM Combined Volumes ──
        output += "\n🔗 LVM Combined Volumes\n"
        if 'LVM Combined Volumes' in sections:
            lines = [l for l in sections['LVM Combined Volumes'] if l.strip()]
            if any('VG Name' in l for l in lines):
                # parseVG/LV/PV
                vgs, lvs, pvs = [], [], []
                section = ''
                for l in lines:
                    if l.strip().startswith('---'):
                        section = l.strip('-').strip().lower()
                        continue
                    if section == 'volume group':
                        if 'VG Name' in l:
                            vgs.append({'name': l.split('VG Name')[-1].strip()})
                        elif 'VG Size' in l and vgs:
                            vgs[-1]['size'] = l.split('VG Size')[-1].strip()
                    elif section == 'logical volume':
                        if 'LV Name' in l:
                            lvs.append({'name': l.split('LV Name')[-1].strip()})
                        elif 'VG Name' in l and lvs:
                            lvs[-1]['vg'] = l.split('VG Name')[-1].strip()
                        elif 'LV Size' in l and lvs:
                            lvs[-1]['size'] = l.split('LV Size')[-1].strip()
                    elif section == 'physical volume':
                        if 'PV Name' in l:
                            pvs.append({'name': l.split('PV Name')[-1].strip()})
                        elif 'VG Name' in l and pvs:
                            pvs[-1]['vg'] = l.split('VG Name')[-1].strip()
                        elif 'PV Size' in l and pvs:
                            pvs[-1]['size'] = l.split('PV Size')[-1].strip().split('/')[0].strip()

                for vg in vgs:
                    vg_name = vg.get('name', '?')
                    vg_size = vg.get('size', '?')
                    # Find PVs and LVs belonging to this VG
                    vg_pvs = [p for p in pvs if p.get('vg') == vg_name]
                    vg_lvs = [l for l in lvs if l.get('vg') == vg_name]

                    pv_count = len(vg_pvs)
                    pv_names = [p.get('name', '?') for p in vg_pvs]
                    pv_sizes = [p.get('size', '?') for p in vg_pvs]
                    lv_info = ', '.join(f"{l.get('name','?')} ({l.get('size','?')})" for l in vg_lvs)

                    output += f"\n{pv_count}disks merged into {vg_name}，mounted at /home\n"
                    # ASCII art - PV sorted by name
                    sorted_pvs = sorted(pv_names)
                    if pv_count > 0:
                        for i, pn in enumerate(sorted_pvs):
                            if i == 0:
                                output += f"{pn} ─┐\n"
                            elif i < pv_count - 1:
                                output += f"{pn} ─┤\n"
                            else:
                                output += f"{pn} ─┘── {vg_name} ── {lv_info} ── /home\n"
            else:
                output += "  (No LVM configuration)\n"
        else:
            output += "  (No LVM configuration)\n"

        # ── Partition Usage (table) ──
        output += "\n📊 Partition Usage status\n"
        if 'Partition Usage' in sections:
            lines = [l for l in sections['Partition Usage'] if l.strip()]
            if lines:
                # Parse df output
                partitions = []
                for l in lines:
                    parts = l.split()
                    if len(parts) >= 6 and parts[0] != 'Filesystem':
                        fs = parts[0]
                        # Simplify filesystem names
                        if '/dev/mapper/' in fs:
                            fs_short = fs.replace('/dev/mapper/', '')
                        elif '/dev/' in fs:
                            fs_short = fs.replace('/dev/', '')
                        else:
                            fs_short = fs
                        mount = parts[5] if len(parts) > 5 else parts[-1]
                        label = f"{fs_short} → {mount}"
                        partitions.append((label, parts[1], parts[2], parts[3], parts[4]))

                if partitions:
                    label_w = max(len(p[0]) for p in partitions) + 2
                    label_w = max(label_w, 12)
                    size_w = max(len(p[1]) for p in partitions) + 2
                    size_w = max(size_w, 8)
                    used_w = max(len(p[2]) for p in partitions) + 2
                    used_w = max(used_w, 8)
                    avail_w = max(len(p[3]) for p in partitions) + 2
                    avail_w = max(avail_w, 8)
                    pct_w = max(len(p[4]) for p in partitions) + 2
                    pct_w = max(pct_w, 8)

                    hdr = f"{'Partition':<{label_w}}{'Total':<{size_w}}{'Used':<{used_w}}{'Available':<{avail_w}}{'Usage%':<{pct_w}}"
                    output += hdr + "\n"
                    output += "─" * len(hdr) + "\n"
                    for p in partitions:
                        output += f"{p[0]:<{label_w}}{p[1]:<{size_w}}{p[2]:<{used_w}}{p[3]:<{avail_w}}{p[4]:<{pct_w}}\n"
                else:
                    output += "  (No data)\n"
            else:
                output += "  (No data)\n"

        # ── Docker Directory Mapping ──
        output += "\n🐳 Docker Directory Mapping\n"
        if 'Docker Directory Mapping' in sections:
            lines = [l for l in sections['Docker Directory Mapping'] if l.strip()]
            if lines:
                in_df = False
                for l in lines:
                    if 'Docker Disk Usage' in l or l.startswith('TYPE'):
                        in_df = True
                    if in_df:
                        output += f"  {l}\n"
                        continue
                    if l.startswith('--') and l.endswith('--'):
                        cname = l.strip('-').strip()
                        output += f"\n  📦 {cname}\n"
                    elif 'bind:' in l or 'volume:' in l:
                        # Format mapping line
                        l = l.strip()
                        arrow_pos = l.find('->')
                        if arrow_pos > 0:
                            src_dst = l[arrow_pos+2:].strip()
                            src_start = l.find(':') + 2
                            src = l[src_start:arrow_pos].strip()
                            output += f"    {src} → {src_dst}\n"
                        else:
                            output += f"    {l}\n"
            else:
                output += "  (No running containers)\n"

        return output

    def _detect_disks(self) -> str:
        if not self.session_manager.active_session:
            return 'Please establish SSH connection first'
        result = self.session_manager.execute_command('lsblk -o NAME,SIZE,TYPE,MOUNTPOINT 2>/dev/null || lsblk', timeout=30)
        if result.error:
            return f"❌ Execution failed [{result.error}]: {result.message}"
        output = result.stdout or result.stderr
        unmounted_disks, mounted_disks = [], []
        for line in output.split('\n'):
            line = line.strip()
            if not line or line.startswith('NAME'):
                continue
            parts = re.split(r'\s+', line)
            if len(parts) >= 3:
                name, size = parts[0], parts[1]
                mountpoint = parts[-1] if len(parts) > 3 else 'none'
                is_physical = (
                    (name.startswith('nvme') and 'n1' in name and 'p' not in name) or
                    re.match(r'^[sh]d[a-z]$', name) or
                    re.match(r'^x?vd[a-z]$', name) or
                    re.match(r'^mmcblk\d+$', name)
                )
                if is_physical:
                    is_mounted = mountpoint and mountpoint != 'none' and '/run/media' not in mountpoint
                    if is_mounted:
                        mounted_disks.append({'name': name, 'size': size, 'mountpoint': mountpoint})
                    else:
                        unmounted_disks.append({'name': name, 'size': size})
        response = '📊 Disk detection result\n\n'
        if unmounted_disks:
            response += '⚠️ Unmounted disks：\n'
            for disk in unmounted_disks:
                response += f"  - /dev/{disk['name']}，size {disk['size']}\n"
            if len(unmounted_disks) >= 2:
                example_disks = ', '.join([d['name'] for d in unmounted_disks[:2]])
                response += f'\n💡 Merge example: {example_disks}merged and mounted to data\n'
        else:
            response += '✅ Nounmounted disk\n'
        if mounted_disks:
            response += '\n📁 Mounted disks：\n'
            for disk in mounted_disks:
                response += f"  - /dev/{disk['name']}，{disk['size']}，mounted at {disk['mountpoint']}\n"
        return response

    def _confirm_disk_merge(self, merge_info: Dict[str, Any]) -> str:
        disks, mount_point = merge_info['disks'], merge_info['mount_point']
        self.pending_disk_merge = merge_info
        return (
            f"⚠️⚠️⚠️ Dangerous operation confirm ⚠️⚠️⚠️\n\n"
            f"📌 Merge disks: {', '.join(disks)}\n"
            f"📌 Mount point: {mount_point}\n\n"
            f"⚠️ This will format all specified disks, all data will be erased!\n\n"
            f'Please reply "confirm" to continue, or "cancel" to abort.'
        )

    def _execute_disk_merge(self, merge_info: Dict[str, Any]) -> str:
        disks, mount_point = merge_info['disks'], merge_info['mount_point']
        if not self.session_manager.active_session:
            self.pending_disk_merge = None
            return 'Please establish SSH connection first'
        disk_paths = [f'/dev/{disk}' for disk in disks]
        vg_name, lv_name = 'vgdata', 'lvdata'
        merge_script = f"""
set -e
which pvcreate || (apt-get update && apt-get install -y lvm2) > /dev/null 2>&1 || true
for disk in {' '.join(disk_paths)}; do pvcreate -y "$disk"; done
vgcreate {vg_name} {' '.join(disk_paths)}
lvcreate -l 100%FREE -n {lv_name} {vg_name}
mkfs.ext4 /dev/{vg_name}/{lv_name}
mkdir -p {mount_point}
mount /dev/{vg_name}/{lv_name} {mount_point}
echo "/dev/{vg_name}/{lv_name} {mount_point} ext4 defaults 0 2" >> /etc/fstab
echo "=== Merge completed ==="
df -h {mount_point}
"""
        self.pending_disk_merge = None
        result = self.session_manager.execute_command(merge_script, timeout=300)
        if result.error:
            return f"❌ Disk merge failed: {result.message}\n{result.stderr}"
        output = f"✅ Disk merge succeeded!\n📌 Disks: {', '.join(disks)}\n📌 Mount point: {mount_point}\n\n"
        output += result.stdout or ''
        return output

    def _handle_auto_mount(self, text: str) -> str:
        if not self.session_manager.active_session:
            return 'Please establish SSH connection first'
        if 'check' in text and 'fstab' in text:
            return self._exec_simple('fstab configuration', 'cat /etc/fstab')
        if 'fix' in text and 'fstab' in text:
            self.pending_confirmation = '_repair_fstab_action'
            return '⚠️ Will fix fstab configuration\n\nPlease reply "confirm" or "cancel"'
        device, mount_point = None, None
        match = re.search(r'(?:set\s*)?([/\w]+)\s*auto mount on boot to\s*([/\w]+)', text)
        if match:
            device, mount_point = match.group(1), match.group(2)
        if not device:
            return '❌ Format: Set /dev/sda1 auto mount on boot to /data\nOr: check fstab'
        if not device.startswith('/dev/'):
            device = '/dev/' + device
        if mount_point and not mount_point.startswith('/'):
            mount_point = '/' + mount_point
        self.pending_confirmation = f'_set_auto_mount {device} {mount_point}'
        return f'⚠️ Will set {device} auto mount on boot to {mount_point}\n\nPlease reply "confirm" or "cancel"'

    # ========== connection/execution ==========

    def _connect(self, info: Dict[str, Any]) -> str:
        try:
            host, port = info['host'], int(info.get('port', 22))
            user = info.get('user', 'root')
            cred = info.get('password')
            key = info.get('key')
            success, message = self.session_manager.create_session(host=host, port=port, username=user, password=cred, key_filename=key, timeout=30)
            if success:
                return f"✅ SSH connection successful\nhost: {host}:{port}\nuser: {user}\n\nYou can now execute commands\n\n💡 Available natural language commands:\n- CPU info / memory info / system overview\n- container list / image list / container logs xxx\n- port scan / firewall status / network interface\n- disk space / disk health / LVM information\n- login audit / security check\n- system logs / SSH logs\n- Or enter Linux commands directly"
            return f"❌ Connection failed: {message}"
        except Exception as e:
            return f"❌ Connection error: {str(e)}"

    def _validate_and_execute(self, command: str, confirmed: bool = False) -> str:
        # Special internal commands
        if command.startswith('_set_auto_mount '):
            parts = command.split(' ')
            if len(parts) >= 3:
                return self._execute_set_auto_mount(parts[1], parts[2])
            return '❌ Parameter error'
        if command == '_repair_fstab_action':
            return self._execute_repair_fstab()

        if not confirmed:
            if self.command_validator.is_blocked(command):
                return f"⚠️ Command blocked: High risk, execution prohibited"
            if self.command_validator.is_sensitive(command):
                self.pending_confirmation = command
                return f'⚠️ Security warning\n\nThis involves sensitive operation, confirm to execute?\n\nCommand: {command}\n\nPlease reply "confirm" or "cancel"'
        return self._execute_command(command)

    def _execute_command(self, command: str) -> str:
        result = self.session_manager.execute_command(command, timeout=60)
        if result.error:
            return f"❌ Execution failed [{result.error}]: {result.message}"
        output = f"📝 Execution result\nCommand: {result.command}\nhost: {result.target_host}\ntime: {result.duration:.2f}s\nExit code: {result.exit_code}\n\n"
        if result.stdout:
            output += f"STDOUT:\n{result.stdout}\n"
        if result.stderr:
            output += f"STDERR:\n{result.stderr}\n"
        return output

    def _execute_set_auto_mount(self, device: str, mount_point: str) -> str:
        if not self.session_manager.active_session:
            return 'Please establish SSH connection first'
        self.session_manager.execute_command(f'mkdir -p {mount_point}', timeout=30)
        uuid_result = self.session_manager.execute_command(f'blkid {device} | grep -oP "UUID=\\"[^\\"]+\\"" | cut -d\'"\' -f2 2>/dev/null || echo ""', timeout=30)
        uuid = (uuid_result.stdout or '').strip()
        fs_result = self.session_manager.execute_command(f'blkid {device} | grep -oP "TYPE=\\"[^\\"]+\\"" | cut -d\'"\' -f2 2>/dev/null || echo "ext4"', timeout=30)
        fs_type = (fs_result.stdout or 'ext4').strip()
        fstab_entry = f"UUID={uuid} {mount_point} {fs_type} defaults 0 2" if uuid else f"{device} {mount_point} {fs_type} defaults 0 2"
        self.session_manager.execute_command(f'cp /etc/fstab /etc/fstab.bak.$(date +%Y%m%d%H%M%S)', timeout=30)
        self.session_manager.execute_command(f'echo "{fstab_entry}" >> /etc/fstab', timeout=30)
        test_result = self.session_manager.execute_command('mount -a 2>&1', timeout=30)
        if test_result.stderr and 'failed' in test_result.stderr.lower():
            self.session_manager.execute_command('cp /etc/fstab.bak* /etc/fstab 2>/dev/null || true', timeout=30)
            return f"❌ Mount test failed, rolled back\n{test_result.stderr}"
        output = f"✅ Auto mount on boot configured successfully!\n📌 Device: {device}\n📌 Mount point: {mount_point}\n📌 entry: {fstab_entry}\n"
        verify = self.session_manager.execute_command(f'df -h {mount_point}', timeout=30)
        if verify.stdout:
            output += f"\n{verify.stdout}"
        return output

    def _execute_repair_fstab(self) -> str:
        if not self.session_manager.active_session:
            return 'Please establish SSH connection first'
        self.session_manager.execute_command('cp /etc/fstab /etc/fstab.repair.bak.$(date +%Y%m%d%H%M%S)', timeout=30)
        check = self.session_manager.execute_command('mount -a 2>&1', timeout=30)
        if check.stderr:
            return f"⚠️ fstab has issues:\n{check.stderr}\n\nSuggest manual check /etc/fstab"
        return "✅ fstab configuration is valid, mount test passed"

    def _list_connections(self) -> str:
        sessions = self.session_manager.get_session_info()
        if not sessions:
            return 'No active SSH connection'
        output = '📡 Active connections list\n\n'
        for idx, session in enumerate(sessions, 1):
            active_mark = ' ⭐' if session['is_active'] else ''
            output += f"{idx}. {session['host']}:{session['port']} (user: {session['username']}){active_mark}\n"
        return output

    def _disconnect(self) -> str:
        if self.session_manager.active_session:
            host = self.session_manager.active_session.conn_info.host
            self.session_manager.close_session()
            return f"Disconnected from {host}  SSH connection"
        return 'No active SSH connection'

    def to_json_response(self, text: str) -> str:
        result = self.handle_command(text)
        return json.dumps({'type': 'text', 'content': result}, ensure_ascii=False, indent=2)