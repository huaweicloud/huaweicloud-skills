#!/usr/bin/env python3
import sys
import os
import argparse
import subprocess
import time
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.executor import CommandExecutor


def _get_ctrl_path(host, port, user):
    """Get SSH ControlMaster socket path"""
    return f"/tmp/ssh-ctrl-{user}@{host}:{port}"


def _is_ctrl_alive(ctrl_path):
    """Check if ControlMaster socket is alive"""
    if not os.path.exists(ctrl_path):
        return False
    check = subprocess.run(
        ['ssh', '-o', f'ControlPath={ctrl_path}', '-o', 'ControlMaster=auto',
         '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=2', 'localhost', 'echo', 'ok'],
        capture_output=True, text=True, timeout=3
    )
    return check.returncode == 0


def _ensure_connection(host, port, user, password):
    """Ensure SSH ControlMaster connection is established, return ctrl_path"""
    ctrl_path = _get_ctrl_path(host, port, user)

    # Check if existing connection is available
    if _is_ctrl_alive(ctrl_path):
        return ctrl_path

    # Clean up stale socket
    if os.path.exists(ctrl_path):
        os.unlink(ctrl_path)

    # Establish new connection (first time is slower, ~1-2 seconds)
    ssh_opts = [
        '-o', 'StrictHostKeyChecking=no',
        '-o', 'UserKnownHostsFile=/dev/null',
        '-o', f'ControlPath={ctrl_path}',
        '-o', 'ControlMaster=auto',
        '-o', 'ControlPersist=10m',   # Auto close after 10 minutes idle
        '-o', 'ServerAliveInterval=30',
        '-o', 'ServerAliveCountMax=3',
        '-p', str(port),
    ]

    # Prefer sshpass (password auth) if available, otherwise try key auth
    if password and os.path.exists('/usr/bin/sshpass'):
        cmd = ['sshpass', '-p', password, 'ssh'] + ssh_opts + [f'{user}@{host}', 'true']
    else:
        cmd = ['ssh'] + ssh_opts + [f'{user}@{host}', 'true']

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
    if result.returncode != 0:
        return None

    return ctrl_path


def _is_shell_command(command):
    """Determine if command is a direct shell command (not natural language)
    Shell command characteristics: starts with known commands or contains shell syntax"""
    # Common shell command prefixes (sorted by length descending for longest match first)
    shell_prefixes = [
        # Network tools (full commands, not substrings)
        'curl', 'wget', 'nc', 'scp', 'rsync',
        # System commands
        'ps', 'top', 'htop', 'kill', 'pkill', 'killall',
        'ls', 'll', 'cat', 'head', 'tail', 'grep', 'awk', 'sed', 'find', 'wc',
        'df', 'du', 'free', 'uptime', 'who', 'w', 'id', 'uname',
        'mkdir', 'rmdir', 'cp', 'mv', 'rm', 'touch', 'chmod', 'chown',
        'tar', 'gzip', 'gunzip', 'zip', 'unzip',
        'echo', 'printf', 'date', 'cal', 'sleep',
        'nohup', 'screen', 'tmux',
        'docker', 'docker-compose', 'kubectl',
        'python3', 'python', 'pip', 'pip3', 'node', 'npm',
        'bash', 'sh', 'source', 'export', 'env', 'which', 'whereis',
        'systemctl', 'service', 'journalctl', 'dmesg',
        'ss ', 'netstat ', 'ip ', 'ifconfig', 'ping ', 'traceroute', 'nslookup', 'dig',
        'iptables', 'ufw', 'firewall-cmd',
        'nvidia-smi', 'npu-smi',
        'git', 'vim', 'vi', 'nano',
        # Assignment and pipes
        'export ', 'VAR=', 
    ]
    cmd_stripped = command.strip()
    for prefix in shell_prefixes:
        if cmd_stripped.startswith(prefix):
            return True
    
    # Contains shell syntax patterns
    shell_patterns = ['|', '&&', '||', '>', '>>', ';', '$(', '`', '2>&1', '-c ']
    if any(p in command for p in shell_patterns):
        return True
    
    return False


def run_one_shot_fast(host, port, user, password, command, raw=False):
    """Fast mode: Use SSH ControlMaster to reuse connection
    First time ~1.5s, subsequent ~0.2s
    When raw=True, skip natural language parsing and execute raw command directly"""
    ctrl_path = _ensure_connection(host, port, user, password)
    if not ctrl_path:
        return run_one_shot_paramiko(host, port, user, password, command, raw=raw)

    # Raw mode: execute directly, bypass NL routing
    if raw:
        result = subprocess.run(
            ['ssh', '-o', f'ControlPath={ctrl_path}', '-o', 'ControlMaster=auto',
             '-o', 'BatchMode=yes', '-p', str(port), f'{user}@{host}', command],
            capture_output=True, text=True, timeout=60
        )
        if result.returncode == 0:
            if result.stdout.strip():
                print(result.stdout.strip())
        else:
            if result.stderr.strip():
                print(f"❌ Error (exit {result.returncode}): {result.stderr.strip()}")
            elif result.stdout.strip():
                print(result.stdout.strip())
        return result.returncode

    # Determine if command is natural language
    # Strategy: if it looks like a shell command, execute directly; otherwise route to NL
    is_nl = not _is_shell_command(command)

    if is_nl:
        # Natural language goes through executor (requires paramiko connection)
        executor = CommandExecutor()
        connect_text = f"SSH connect {host} port {port} user {user} password {password}"
        executor.handle_command(connect_text)
        result = executor.handle_command(command)
        print(result)
        executor.session_manager.close_all_sessions()
        return 0
    else:
        # Direct shell command goes through fast mode
        result = subprocess.run(
            ['ssh', '-o', f'ControlPath={ctrl_path}', '-o', 'ControlMaster=auto',
             '-o', 'BatchMode=yes', '-p', str(port), f'{user}@{host}', command],
            capture_output=True, text=True, timeout=60
        )
        if result.returncode == 0:
            if result.stdout.strip():
                print(result.stdout.strip())
        else:
            if result.stderr.strip():
                print(f"❌ Error (exit {result.returncode}): {result.stderr.strip()}")
            elif result.stdout.strip():
                print(result.stdout.strip())
        return result.returncode


def run_one_shot_paramiko(host, port, user, password, command, raw=False):
    """Paramiko mode: connect -> execute -> disconnect (fallback)
    When raw=True, execute command directly without NL routing"""
    executor = CommandExecutor()
    
    connect_text = f"SSH connect {host} port {port} user {user} password {password}"
    result = executor.handle_command(connect_text)
    if 'failed' in result.lower() or 'error' in result.lower():
        print(result)
        return 1

    if raw:
        # Raw mode: execute directly via paramiko, bypass NL routing
        import paramiko
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(host, port=port, username=user, password=password)
        stdin, stdout, stderr = ssh.exec_command(command, timeout=60)
        out = stdout.read().decode()
        err = stderr.read().decode()
        ssh.close()
        if out.strip():
            print(out.strip())
        if err.strip():
            print(f"⚠️ stderr: {err.strip()}")
        return 0 if not err.strip() else 1
    
    result = executor.handle_command(command)
    print(result)
    
    executor.session_manager.close_all_sessions()
    return 0


def run_one_shot(host, port, user, password, command, raw=False):
    """One-shot mode: prefer fast mode, fallback to paramiko"""
    return run_one_shot_fast(host, port, user, password, command, raw=raw)


def main():
    # Parse --command one-time execution arguments
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--host', help='SSH host IP')
    parser.add_argument('--port', type=int, default=22, help='SSH port (default 22)')
    parser.add_argument('--user', default='root', help='SSH username (default root)')
    parser.add_argument('--password', help='SSH password')
    parser.add_argument('--command', help='command to execute (one-time mode)')
    parser.add_argument('--raw', action='store_true', help='Skip NL parsing, execute raw command')
    
    # Parse known args first, ignore unknown (leave for NL mode)
    args, remaining = parser.parse_known_args()
    
    # One-time execution mode
    if args.host and args.password and args.command:
        sys.exit(run_one_shot(args.host, args.port, args.user, args.password, args.command, raw=args.raw))
    
    executor = CommandExecutor()
    
    # NL mode: execute with provided params
    if remaining or (args.host and not args.command):
        text_parts = []
        if args.host:
            text_parts.append(f"SSH connect {args.host} port {args.port} user {args.user} password {args.password or ''}")
        text_parts.extend(remaining)
        text = ' '.join(text_parts)
        if text.strip():
            result = executor.handle_command(text)
            print(result)
            return
    
    if len(sys.argv) > 1 and not remaining and not args.host:
        # No named args, treat as NL command
        text = ' '.join(sys.argv[1:])
        result = executor.handle_command(text)
        print(result)
        return
    
    print("SSH Remote Executor - Interactive Mode")
    print("======================================")
    print("Type 'exit' or 'quit' to exit")
    print("Type 'help' for help")
    print("======================================\n")
    
    # Dead loop protection - only idle timeout (suitable for remote connection scenarios)
    idle_timeout = 600  # Auto exit after 10 minutes idle
    last_activity_time = time.time()
    
    while True:
        try:
            # Check idle timeout (only after user has activity)
            current_time = time.time()
            if last_activity_time > 0 and (current_time - last_activity_time > idle_timeout):
                executor.session_manager.close_all_sessions()
                print(f"\nIdle timeout ({idle_timeout} seconds), auto exit")
                break
            
            # Get user input
            text = input("> ")
            text = text.strip()
            
            # Update activity time
            last_activity_time = time.time()
            
            if text.lower() in ('exit', 'quit', 'bye'):
                executor.session_manager.close_all_sessions()
                print("Exited, all connections closed")
                break
            
            if text.lower() == 'help':
                print("""
Help Information:

Connect command:
  SSH connect 192.168.1.100 port 22 user root password xxx
  
Execute commands:
  Enter Linux commands directly, e.g.: ls -la, df -h, top -bn1
  
System commands:
  view connections - List all active connections
  disconnect/disconnect SSH - Disconnect current connection
  cancel - Cancel pending confirmation
  confirm - Confirm sensitive operation
  exit/quit - Exit program
  
Security Features:
  - Sensitive operations (delete, modify, etc.) require confirmation
  - High-risk commands are automatically blocked
  - Passwords are only stored in memory, not written to disk
                """)
                continue
            
            result = executor.handle_command(text)
            print(result)
            print()
            
        except KeyboardInterrupt:
            executor.session_manager.close_all_sessions()
            print("\nExited, all connections closed")
            break
        except EOFError:
            executor.session_manager.close_all_sessions()
            print("\nInput ended, exiting")
            break
        except Exception as e:
            print(f"Error: {str(e)}")
            traceback.print_exc()


if __name__ == '__main__':
    main()
