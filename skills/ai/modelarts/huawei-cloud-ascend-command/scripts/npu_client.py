#!/usr/bin/env python3
"""
NPU Client - Execute npu-smi commands (local or SSH remote)
Self-contained, no dependency on other skills
"""

import subprocess
import json
import re
import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field


@dataclass
class NpuDevice:
    """NPU Device Information"""
    npu_id: int = 0
    chip_count: int = 0
    model: str = ""
    health: str = ""
    temperature: float = 0.0
    power: float = 0.0
    hbm_usage: float = 0.0
    hbm_total: int = 0
    hbm_used: int = 0
    ecc_single: int = 0
    ecc_double: int = 0
    ai_core_usage: float = 0.0


class NpuClient:
    """
    NPU Command Client - Self-contained
    Supports two modes:
    1. SSH mode: Execute remotely via paramiko
    2. Local mode: Execute npu-smi directly (requires local installation)
    """

    def __init__(self, ssh_host: str = None, ssh_user: str = None,
                 ssh_password: str = None, ssh_port: int = 22):
        self.ssh_host = ssh_host
        self.ssh_user = ssh_user
        self.ssh_password = ssh_password
        self.ssh_port = ssh_port
        self._ssh_client = None

    def _get_ssh_client(self):
        """Get or create SSH connection (using paramiko)"""
        if self._ssh_client is None:
            import paramiko
            self._ssh_client = paramiko.SSHClient()
            self._ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self._ssh_client.connect(
                hostname=self.ssh_host,
                port=self.ssh_port,
                username=self.ssh_user,
                password=self.ssh_password,
                timeout=30,
                look_for_keys=False,
                allow_agent=False
            )
        return self._ssh_client

    def _run_npu_smi(self, args: str) -> str:
        """Execute npu-smi command"""
        cmd = f"npu-smi {args}"
        return self._execute(cmd)

    def _execute(self, command: str) -> str:
        """Execute command (SSH remote or local direct)"""
        if self.ssh_host:
            # SSH remote mode: using paramiko directly
            try:
                client = self._get_ssh_client()
                stdin, stdout, stderr = client.exec_command(command, timeout=60)
                output = stdout.read().decode('utf-8')
                err = stderr.read().decode('utf-8')
                if not output and err:
                    return f"Error: {err.strip()}"
                return output
            except Exception as e:
                # Reconnect on connection error
                if self._ssh_client:
                    try:
                        self._ssh_client.close()
                    except:
                        pass
                    self._ssh_client = None
                # Retry once
                try:
                    client = self._get_ssh_client()
                    stdin, stdout, stderr = client.exec_command(command, timeout=60)
                    output = stdout.read().decode('utf-8')
                    return output
                except Exception as e2:
                    return f"SSH Error: {str(e2)}"
        else:
            # Local direct mode: execute npu-smi directly
            import shlex
            result = subprocess.run(
                shlex.split(command), shell=False,
                capture_output=True, text=True, timeout=60
            )
            if result.returncode != 0 and result.stderr:
                return f"Error (exit {result.returncode}): {result.stderr.strip()}"
            return result.stdout

    def close(self):
        """Close SSH connection"""
        if self._ssh_client:
            try:
                self._ssh_client.close()
            except:
                pass
            self._ssh_client = None
    # ===== Device Queries =====

    def list_devices(self) -> Dict[str, Any]:
        """List all NPU devices"""
        output = self._run_npu_smi("info -l")
        devices = []
        current_id = None
        current_count = 0

        for line in output.split('\n'):
            if 'NPU ID' in line:
                match = re.search(r'NPU ID\s*:\s*(\d+)', line)
                if match:
                    if current_id is not None:
                        devices.append({"npu_id": current_id, "chip_count": current_count})
                    current_id = int(match.group(1))
                    current_count = 0
            elif 'Chip Count' in line:
                match = re.search(r'Chip Count\s*:\s*(\d+)', line)
                if match:
                    current_count = int(match.group(1))

        if current_id is not None:
            devices.append({"npu_id": current_id, "chip_count": current_count})

        return {"devices": devices, "count": len(devices)}

    def get_health(self, npu_id: int = 0) -> str:
        """Query device health status"""
        output = self._run_npu_smi(f"info -t health -i {npu_id}")
        match = re.search(r'Health[A-Za-z ]*:\s*(\w+)', output)
        return match.group(1) if match else "Unknown"

    def get_board_info(self, npu_id: int = 0) -> Dict[str, str]:
        """Query board information"""
        output = self._run_npu_smi(f"info -t board -i {npu_id}")
        info = {}
        for line in output.split('\n'):
            if ':' in line:
                key, _, val = line.partition(':')
                info[key.strip()] = val.strip()
        return info

    def get_chip_mapping(self) -> List[Dict[str, Any]]:
        """Query chip mapping"""
        output = self._run_npu_smi("info -m")
        chips = []
        for line in output.split('\n'):
            parts = line.split()
            if len(parts) >= 4 and parts[0].isdigit():
                chips.append({
                    "npu_id": int(parts[0]),
                    "chip_id": int(parts[1]),
                    "chip_logic_id": parts[2],
                    "chip_name": parts[3]
                })
        return chips

    def get_temperature(self, npu_id: int = 0, chip_id: int = 0) -> Dict[str, Any]:
        """Query temperature"""
        output = self._run_npu_smi(f"info -t temp -i {npu_id} -c {chip_id}")
        temps = {}
        for line in output.split('\n'):
            if 'Temperature' in line and ':' in line:
                key, _, val = line.partition(':')
                match = re.search(r'[\d.]+', val.strip())
                if match:
                    temps[key.strip()] = float(match.group())
        return temps

    def get_power(self, npu_id: int = 0, chip_id: int = 0) -> Dict[str, Any]:
        """Query power consumption"""
        output = self._run_npu_smi(f"info -t power -i {npu_id} -c {chip_id}")
        power = {}
        for line in output.split('\n'):
            if 'Power' in line and ':' in line:
                key, _, val = line.partition(':')
                match = re.search(r'[\d.]+', val.strip())
                if match:
                    power[key.strip()] = float(match.group())
        return power

    def get_memory(self, npu_id: int = 0, chip_id: int = 0) -> Dict[str, Any]:
        """Query memory"""
        output = self._run_npu_smi(f"info -t memory -i {npu_id} -c {chip_id}")
        mem = {}
        for line in output.split('\n'):
            if ':' in line:
                key, _, val = line.partition(':')
                mem[key.strip()] = val.strip()
        return mem

    def get_hbm_usage(self, npu_id: int = 0, chip_id: int = 0) -> Dict[str, Any]:
        """Query HBM usage"""
        output = self._run_npu_smi(f"info -t usages -i {npu_id} -c {chip_id}")
        usages = {}
        for line in output.split('\n'):
            if 'Usage' in line and ':' in line:
                key, _, val = line.partition(':')
                match = re.search(r'[\d.]+', val.strip())
                if match:
                    usages[key.strip()] = float(match.group())
        return usages

    def get_ecc_errors(self, npu_id: int = 0, chip_id: int = 0) -> Dict[str, Any]:
        """Query ECC errors"""
        output = self._run_npu_smi(f"info -t ecc -i {npu_id} -c {chip_id}")
        ecc = {}
        for line in output.split('\n'):
            if 'Error' in line and ':' in line:
                key, _, val = line.partition(':')
                match = re.search(r'\d+', val.strip())
                if match:
                    ecc[key.strip()] = int(match.group())
        return ecc

    def get_processes(self, npu_id: int = 0, chip_id: int = 0) -> str:
        """Query running processes"""
        return self._run_npu_smi(f"info -t proc-mem -i {npu_id} -c {chip_id}")

    def get_pcie_errors(self, npu_id: int = 0, chip_id: int = 0) -> str:
        """Query PCIe errors"""
        return self._run_npu_smi(f"info -t pcie-err -i {npu_id} -c {chip_id}")

    def get_topology(self, npu_id: int = 0, chip_id: int = 0) -> str:
        """Query topology"""
        return self._run_npu_smi(f"info -t topo -i {npu_id} -c {chip_id}")

    def get_product_info(self, npu_id: int = 0, chip_id: int = 0) -> str:
        """Query product information"""
        return self._run_npu_smi(f"info -t product -i {npu_id} -c {chip_id}")

    # ===== Configuration Operations =====

    def set_ecc_enable(self, npu_id: int, chip_id: int, enable: bool) -> str:
        """Set ECC enable"""
        val = 1 if enable else 0
        return self._run_npu_smi(f"set -t ecc-enable -i {npu_id} -c {chip_id} -d {val}")

    def set_fan_mode(self, auto: bool) -> str:
        """Set fan mode"""
        val = 1 if auto else 0
        return self._run_npu_smi(f"set -t pwm-mode -d {val}")

    def set_fan_speed(self, percent: int) -> str:
        """Set fan speed"""
        percent = max(0, min(100, percent))
        return self._run_npu_smi(f"set -t pwm-duty-ratio -d {percent}")

    def set_vnpu_mode(self, mode: str) -> str:
        """Set vNPU mode (docker/vm)"""
        val = 0 if mode == 'docker' else 1
        return self._run_npu_smi(f"set -t vnru-mode -d {val}")

    def clear_ecc_errors(self, npu_id: int, chip_id: int) -> str:
        """Clear ECC error count"""
        return self._run_npu_smi(f"clear -t ecc-info -i {npu_id} -c {chip_id}")

    # ===== Firmware Upgrade =====

    def upgrade_query(self, component: str, npu_id: int) -> str:
        """Query firmware version"""
        return self._run_npu_smi(f"upgrade -b {component} -i {npu_id}")

    def upgrade_upload(self, component: str, npu_id: int, firmware_file: str) -> str:
        """Upload firmware"""
        return self._run_npu_smi(f"upgrade -t {component} -i {npu_id} -f {firmware_file}")

    def upgrade_check(self, component: str, npu_id: int) -> str:
        """Check upgrade status"""
        return self._run_npu_smi(f"upgrade -q {component} -i {npu_id}")

    def upgrade_activate(self, component: str, npu_id: int) -> str:
        """Activate firmware"""
        return self._run_npu_smi(f"upgrade -a {component} -i {npu_id}")

    # ===== Virtualization =====

    def get_vnpu_info(self, npu_id: int, chip_id: int) -> str:
        """Query vNPU information"""
        return self._run_npu_smi(f"info -t info-vnpu -i {npu_id} -c {chip_id}")

    def get_vnpu_mode(self) -> str:
        """Query vNPU mode"""
        return self._run_npu_smi("info -t vnru-mode")

    def get_template_info(self, npu_id: int = None) -> str:
        """Query template information"""
        cmd = "info -t template-info"
        if npu_id is not None:
            cmd += f" -i {npu_id}"
        return self._run_npu_smi(cmd)

    def create_vnpu(self, npu_id: int, chip_id: int, template: str,
                    vnpu_id: int = None, vgroup_id: int = None) -> str:
        """Create vNPU"""
        cmd = f"set -t create-vnru -i {npu_id} -c {chip_id} -f {template}"
        if vnpu_id is not None:
            cmd += f" -v {vnpu_id}"
        if vgroup_id is not None:
            cmd += f" -g {vgroup_id}"
        return self._run_npu_smi(cmd)

    def destroy_vnpu(self, npu_id: int, chip_id: int, vnpu_id: int) -> str:
        """Destroy vNPU"""
        return self._run_npu_smi(f"set -t destroy-vnru -i {npu_id} -c {chip_id} -v {vnpu_id}")

    # ===== Certificate Management =====

    def get_tls_cert(self, npu_id: int, chip_id: int) -> str:
        """View TLS certificate"""
        return self._run_npu_smi(f"info -t tls-cert -i {npu_id} -c {chip_id}")

    def get_cert_period(self, npu_id: int, chip_id: int) -> str:
        """Query certificate expiration threshold"""
        return self._run_npu_smi(f"info -t tls-cert-period -i {npu_id} -c {chip_id}")

    def set_cert_period(self, npu_id: int, chip_id: int, days: int) -> str:
        """Set certificate expiration threshold"""
        return self._run_npu_smi(f"set -t tls-cert-period -i {npu_id} -c {chip_id} -s {days}")

    # ===== Full Information =====

    def get_full_info(self) -> str:
        """Get full NPU information (npu-smi info)"""
        return self._run_npu_smi("info")

    def get_full_info_all(self) -> str:
        """Get detailed information for all devices"""
        return self._run_npu_smi("info -l -t board")

    def parse_full_info(self) -> List[Dict[str, Any]]:
        """
        Get full information and parse all devices with one npu-smi info call
        Avoids per-card serial calls, performance improved from O(N) SSH to O(1) SSH
        """
        output = self.get_full_info()
        devices = []
        current = None

        for line in output.split('\n'):
            line = line.strip()
            if not line or line.startswith('+') or line.startswith('| NPU') or line.startswith('| Chip') or 'npu-smi' in line:
                continue

            # NPU line: "| 0     910B3               | OK            | 92.2        49                0    / 0             |"
            # Pattern: NPU_ID  Model  |  Health  |  Power  Temp  Hugepages
            npu_match = re.match(r'\|\s*(\d+)\s+(\S+)\s+\|\s+(\w+)\s+\|\s*([\d.]+)\s+([\d.]+)\s+(\d+)\s*/\s*(\d+)', line)
            if npu_match:
                if current is not None:
                    devices.append(current)
                current = {
                    'npu_id': int(npu_match.group(1)),
                    'model': npu_match.group(2),
                    'health': npu_match.group(3),
                    'chip_count': 1,
                    'power': float(npu_match.group(4)),
                    'temperature': float(npu_match.group(5)),
                    'ai_core_usage': None,
                    'hbm_used': None,
                    'hbm_total': None,
                    'memory_used': None,
                    'memory_total': None,
                }
                continue

            # Chip line: "| 0                         | 0000:C1:00.0  | 0           0    / 0          3405 / 65536         |"
            # Pattern: Chip_ID  |  Bus-Id  |  AICore(%)  Memory_Used / Memory_Total  HBM_Used / HBM_Total
            chip_match = re.match(r'\|\s*\d+\s+\|\s+[\d:A-F.]+\s+\|\s*([\d.]+)\s+(\d+)\s*/\s*(\d+)\s+(\d+)\s*/\s*(\d+)', line)
            if chip_match and current is not None:
                current['ai_core_usage'] = float(chip_match.group(1))
                current['memory_used'] = int(chip_match.group(2))
                current['memory_total'] = int(chip_match.group(3))
                current['hbm_used'] = int(chip_match.group(4))
                current['hbm_total'] = int(chip_match.group(5))
                continue

        if current is not None:
            devices.append(current)

        return devices

    # ===== Batch Execution Optimization =====

    def execute_batch(self, commands: List[str], separator: str = "===SEPARATOR===") -> Dict[str, str]:
        """
        Execute multiple commands in batch (one SSH round-trip)
        
        Args:
            commands: Command list
            separator: Separator for parsing command outputs
            
        Returns:
            Dict[command, output] Output results for each command
            
        Example:
            results = client.execute_batch([
                "npu-smi info",
                "ascend-dmi -f -d 0 -t fp16 -q"
            ])
        """
        # Combine all commands with separator
        combined = f" echo '{separator}' && ".join(commands)
        output = self._execute(combined)
        
        # Parse command outputs
        results = {}
        parts = output.split(separator)
        
        # First part is the output of the first command
        for i, cmd in enumerate(commands):
            if i < len(parts):
                results[cmd] = parts[i].strip()
            else:
                results[cmd] = ""
                
        return results

    def test_flops_single(self, device_id: int = 0, dtype: str = "fp16") -> Dict[str, Any]:
        """
        Single device FLOPS test (Fast, ~2 seconds)
        
        Args:
            device_id: NPU device ID
            dtype: Data type (fp16/fp32/bf16/int8)
            
        Returns:
            FLOPS test result
        """
        output = self._execute(f"ascend-dmi -f -d {device_id} -t {dtype} -q")
        return self._parse_flops_output(output)

    def test_flops_parallel(self, device_ids: List[int] = None, dtype: str = "fp16") -> Dict[int, Dict[str, Any]]:
        """
        Multi-device parallel FLOPS test (Async execution, ~2 seconds total)
        
        Args:
            device_ids: NPU device ID list, defaults to all 8 devices
            dtype: Data type (fp16/fp32/bf16/int8)
            
        Returns:
            Dict[device_id, result] FLOPS test results for each device
        """
        if device_ids is None:
            device_ids = list(range(8))
            
        # Build parallel commands: execute each device test in background, results to temp files
        import tempfile
        import os
        
        # Use temp directory to store results for each device
        tmp_dir = "/tmp/npu_flops_test"
        self._execute(f"mkdir -p {tmp_dir}")
        
        # Start all tests in parallel
        parallel_cmds = []
        for did in device_ids:
            cmd = f"ascend-dmi -f -d {did} -t {dtype} -q > {tmp_dir}/npu_{did}.txt 2>&1 &"
            parallel_cmds.append(cmd)
        
        # Start all background tasks at once
        self._execute(" && ".join(parallel_cmds))
        
        # Wait for all tasks to complete (FLOPS test takes ~2 seconds)
        import time
        time.sleep(2.5)  # Wait for tests to complete
        
        # Collect results
        results = {}
        for did in device_ids:
            output = self._execute(f"cat {tmp_dir}/npu_{did}.txt 2>/dev/null || echo ''")
            results[did] = self._parse_flops_output(output)
            
        # Cleanup temp files
        self._execute(f"rm -rf {tmp_dir}")
        
        return results

    def _parse_flops_output(self, output: str) -> Dict[str, Any]:
        """Parse FLOPS test output"""
        result = {
            "device": None,
            "tflops": None,
            "power": None,
            "duration": None,
            "raw": output
        }
        
        # Parse output
        # Device        Execute Times        Duration(ms)        TFLOPS@FP16          Power(W)
        # 0             360,000,000          1702                313.548            239.300003
        for line in output.split('\n'):
            parts = line.split()
            if len(parts) >= 5 and parts[0].isdigit():
                try:
                    result["device"] = int(parts[0])
                    result["duration"] = int(parts[2].replace(',', ''))
                    result["tflops"] = float(parts[3])
                    result["power"] = float(parts[4])
                except (ValueError, IndexError):
                    pass
                break
                
        return result
