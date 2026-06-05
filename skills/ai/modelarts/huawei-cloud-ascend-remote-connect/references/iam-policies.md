# IAM Permission Policy

## Overview

This document describes the permission requirements for the Huawei Cloud Ascend Remote Connection skill.

## Target Server Permissions

### SSH Access Requirements

The user account used for SSH connection must have:

| Permission | Description |
|------------|-------------|
| SSH login | Access to SSH service (port 22) |
| Command execution | Execute basic shell commands |
| sudo privileges | For system management operations |

### Minimum Required Privileges

```bash
# Example sudoers configuration for non-root user
echo "ascend-user ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers.d/ascend-user
```

## Allowed Commands

### Safe Commands (No confirmation required)
- `npu-smi info` - NPU status check
- `ls`, `cat`, `head`, `tail` - File operations
- `df -h`, `free -h`, `uptime` - System monitoring
- `ps`, `top` - Process viewing
- `ss`, `netstat` - Network information

### Sensitive Commands (Require confirmation)
- `rm`, `rmdir` - Delete operations
- `mkfs` - Format operations
- `umount` - Unmount operations
- `reboot`, `shutdown` - System restart/shutdown
- `docker rm`, `docker rmi` - Container/image removal

### Blocked Commands (Always blocked)
- Fork bomb patterns
- Direct disk formatting without confirmation

## Security Best Practices

### 1. Use Non-Root User

```bash
# Create dedicated user
useradd -m ascend-admin
usermod -aG sudo ascend-admin
```

### 2. Restrict SSH Access

```bash
# Edit SSH configuration
sed -i 's/^PermitRootLogin yes/PermitRootLogin no/' /etc/ssh/sshd_config
sed -i 's/^#AllowUsers/AllowUsers/' /etc/ssh/sshd_config
echo "AllowUsers ascend-admin" >> /etc/ssh/sshd_config
systemctl restart sshd
```

### 3. Use Key-Based Authentication (Recommended)

```bash
# On client machine
ssh-keygen -t ed25519
ssh-copy-id ascend-admin@<server-ip>

# On server - disable password authentication
sed -i 's/^PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config
systemctl restart sshd
```

### 4. Firewall Configuration

```bash
# Allow only specific IPs
iptables -A INPUT -p tcp --dport 22 -s <trusted-ip> -j ACCEPT
iptables -A INPUT -p tcp --dport 22 -j DROP
```

## Permission Matrix

| Operation | Required Permission |
|-----------|---------------------|
| Connect to server | SSH access |
| View NPU status | Regular user |
| View system info | Regular user |
| Disk management | sudo |
| System updates | sudo |
| Container management | sudo or docker group |
| User management | sudo |

## Audit Logging

Enable SSH logging for security auditing:

```bash
# Configure SSH logging
echo "LogLevel VERBOSE" >> /etc/ssh/sshd_config
systemctl restart sshd

# Monitor logs
tail -f /var/log/auth.log
```