import re
from enum import Enum
from typing import Tuple, Optional, List


class CommandType(Enum):
    ALLOWED = 'allowed'
    CONFIRM_REQUIRED = 'confirm_required'
    BLOCKED = 'blocked'


class CommandValidator:
    def __init__(self):
        self.sensitive_patterns: List[Tuple[str, str]] = [
            (r'^\s*rm\s+(-[a-zA-Z]+)?\s+(-rf\b|\s+-r\s+-f\b|\s+-f\s+-r\b)', 'remove command'),
            (r'^\s*rm\s+-[a-zA-Z]*[rf][a-zA-Z]*\s+/.+', 'recursive remove system path'),
            (r'^\s*rmdir\s+/.+', 'remove system directory'),
            (r'^\s*mkfs\b', 'format command'),
            (r'^\s*fdisk\s+[-/]\s*[dD]', 'fdisk delete partition'),
            (r'^\s*parted\s+.+\s+rm\s+', 'parted delete partition'),
            (r'^\s*umount\b', 'unmount command'),
            (r'^\s*reboot\b', 'reboot command'),
            (r'^\s*shutdown\b', 'shutdown command'),
            (r'^\s*init\s+[06]\b', 'system runlevel switch'),
            (r'^\s*poweroff\b', 'power off'),
            (r'^\s*halt\b', 'system halt'),
            (r'^\s*userdel\b', 'delete user'),
            (r'^\s*groupdel\b', 'delete group'),
            (r'^\s*chmod\s+-R\b', 'recursive chmod'),
            (r'^\s*chown\s+-R\b', 'recursive chown'),
            (r'^\s*dd\s+if=\S+\s+of=\S+', 'dangerous write operation'),
        ]

        self.blocked_patterns: List[Tuple[str, str]] = [
            (r'^:\(\)\s*\{.*\|\|.*\s*\};\s*:', 'fork bomb attack'),
            (r'^\s*mkfs\s+\S*/dev/sd\S+', 'direct disk format'),
            (r'^\s*dd\s+if=/dev/zero\s+of=/dev/\S+', 'zero write to disk'),
            (r'^\s*rm\s+-rf\s+/\s*$', 'delete root directory'),
            (r'^\s*rm\s+-rf\s+/\b', 'delete system root path'),
        ]

        self.allowed_prefixes: List[str] = [
            'ls', 'pwd', 'cd', 'cat', 'grep', 'find', 'wc', 'head', 'tail',
            'echo', 'date', 'who', 'w', 'last', 'top', 'htop', 'free', 'df',
            'du', 'ps', 'netstat', 'ss', 'ping', 'traceroute', 'curl', 'wget',
            'python', 'pip', 'node', 'npm', 'git', 'docker', 'docker-compose',
            'systemctl status', 'journalctl', 'uname', 'hostname', 'ifconfig',
            'ip addr', 'ip route', 'dig', 'nslookup', 'man', 'which', 'whereis',
            'mkdir', 'touch', 'cp', 'mv', 'diff', 'patch', 'tar', 'zip',
            'unzip', 'gzip', 'bzip2', 'xz', 'ssh', 'scp', 'sftp', 'rsync',
            'crontab -l', 'passwd', 'su', 'sudo', 'apt', 'apt-get', 'yum',
            'dnf', 'rpm', 'dpkg', 'service', 'systemctl', 'lvm', 'pvdisplay',
            'vgdisplay', 'lvdisplay', 'fdisk -l', 'parted -l', 'smartctl',
            'iostat', 'vmstat', 'sar', 'tcpdump', 'nc', 'openssl', 'ssh-keygen',
            'usermod', 'groupmod', 'useradd', 'groupadd', 'cron', 'at',
            'sysctl', 'ulimit', 'ufw', 'firewall-cmd', 'iptables', 'bridge',
            'bond', 'vlan', 'route', 'netplan', 'nmcli', 'hostnamectl',
            'timedatectl', 'loginctl', 'blkid', 'lsblk', 'mount', 'fstab',
            'mkswap', 'swapon', 'swapoff', 'lsof', 'kill', 'killall', 'pkill',
        ]

    def validate(self, command: str) -> Tuple[CommandType, Optional[str]]:
        cmd = command.strip().lower()
        
        for pattern, description in self.blocked_patterns:
            if re.search(pattern, cmd):
                return CommandType.BLOCKED, f"High-risk command blocked: {description}"
        
        for pattern, description in self.sensitive_patterns:
            if re.search(pattern, cmd):
                return CommandType.CONFIRM_REQUIRED, f"Sensitive operation: {description}"
        
        for prefix in self.allowed_prefixes:
            if cmd.startswith(prefix):
                return CommandType.ALLOWED, None
        
        return CommandType.ALLOWED, None

    def is_sensitive(self, command: str) -> bool:
        result, _ = self.validate(command)
        return result == CommandType.CONFIRM_REQUIRED

    def is_blocked(self, command: str) -> bool:
        result, _ = self.validate(command)
        return result == CommandType.BLOCKED

    def get_validation_message(self, command: str) -> Optional[str]:
        result, message = self.validate(command)
        if result == CommandType.BLOCKED:
            return f"Command blocked: {message}"
        if result == CommandType.CONFIRM_REQUIRED:
            return f"Requires confirmation: {message}"
        return None
