#!/usr/bin/env python3
"""
Ascend NPU Management Skill - Main Entry
Supports three usage modes:
  1. Local mode: python3 main.py --command "NPU info"
     (Execute local npu-smi directly, for use on Ascend servers)
  2. SSH remote mode: python3 main.py --command "NPU info" --host IP --user root --password PWD
     (Execute remotely via SSH)
  3. Direct npu-smi: python3 main.py --npu-smi "info -l" [--host IP ...]
  4. Interactive mode: python3 main.py
"""

import sys
import os
import json
import argparse

# Ensure module import from same directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from executor import NpuExecutor


def run_one_shot(command: str, host: str = None, user: str = None,
                 password: str = None, port: int = 22):
    """One-shot mode: execute single command and exit"""
    executor = NpuExecutor(
        ssh_host=host, ssh_user=user,
        ssh_password=password, ssh_port=port
    )
    result = executor.handle_command(command)
    print(result)


def run_npu_smi_direct(args: str, host: str = None, user: str = None,
                       password: str = None, port: int = 22):
    """Execute npu-smi command directly"""
    executor = NpuExecutor(
        ssh_host=host, ssh_user=user,
        ssh_password=password, ssh_port=port
    )
    result = executor.client._run_npu_smi(args)
    print(result)


def run_interactive(host: str = None, user: str = None,
                    password: str = None, port: int = 22):
    """Interactive mode"""
    executor = NpuExecutor(
        ssh_host=host, ssh_user=user,
        ssh_password=password, ssh_port=port
    )

    mode = "SSH Remote" if host else "Local Direct"
    print("=" * 60)
    print(f"    🔹 Ascend NPU Management Skill")
    print(f"    Mode: {mode}" + (f" → {host}" if host else ""))
    print("=" * 60)
    print()
    print("📦 Query: NPU list | NPU info | NPU health | temperature | power | HBM | usage")
    print("🔍 Advanced: ECC | NPU processes | PCIe errors | topology | product info | board info")
    print("⚙️ Configuration: set ECC | fan mode | fan speed | clear ECC")
    print("🔄 Firmware: firmware version | upgrade firmware | upgrade status | activate firmware")
    print("🔲 Virtualization: vNPU info | vNPU mode | template info | create vNPU | destroy vNPU")
    print("🔐 Certificate: certificate info | cert expiration")
    print("💡 Specify device: append NPU0 Chip0 to command")
    print("💡 Direct command: npu-smi info -l")
    print()
    print("Type 'exit' or 'quit' to exit")
    print("=" * 60)
    print()

    while True:
        try:
            command = input("🔹 Enter command: ").strip()
            if command.lower() in ('exit', 'quit', 'q'):
                print("Exiting 👋")
                sys.exit(0)
            if not command:
                continue

            result = executor.handle_command(command)
            print(result)
            print()

        except KeyboardInterrupt:
            print("\nExiting 👋")
            sys.exit(0)
        except Exception as e:
            print(f"❌ Error: {e}")


def main():
    parser = argparse.ArgumentParser(
        description='Ascend NPU Management Skill (supports local and SSH remote modes)'
    )
    parser.add_argument('--command', '-c', help='Natural language command (one-shot mode)')
    parser.add_argument('--npu-smi', dest='npu_smi', help='Direct npu-smi command (use = to assign: --npu-smi="-v" or --npu-smi="info -l")')
    parser.add_argument('--npu-version', '-V', action='store_true', help='Query npu-smi version')

    # SSH parameters (optional, local execution if not provided)
    parser.add_argument('--host', help='SSH host IP (local execution if not provided)')
    parser.add_argument('--port', type=int, default=22, help='SSH port (default 22)')
    parser.add_argument('--user', help='SSH username')
    parser.add_argument('--password', help='SSH password')

    args = parser.parse_args()

    # One-shot: npu-smi version shortcut
    if args.npu_version:
        run_npu_smi_direct("-v", args.host, args.user, args.password, args.port)
        return

    # One-shot: natural language command
    if args.command:
        run_one_shot(args.command, args.host, args.user, args.password, args.port)
        return

    # One-shot: direct npu-smi
    if args.npu_smi:
        run_npu_smi_direct(args.npu_smi, args.host, args.user, args.password, args.port)
        return

    # Interactive mode (with optional SSH params)
    run_interactive(args.host, args.user, args.password, args.port)


if __name__ == "__main__":
    main()
