#!/usr/bin/env python3
"""
NPU Command Executor - Natural Language to npu-smi Command Conversion
Supports: Query/Configuration/Firmware Upgrade/Virtualization/Certificate Management
"""

import re
import shlex
import json
from typing import Dict, Any, Optional, List

try:
    from .npu_client import NpuClient
except ImportError:
    from npu_client import NpuClient


class NpuExecutor:
    """NPU Natural Language Command Executor"""

    # Sensitive operation keywords
    SENSITIVE_KEYWORDS = ('set', 'modify', 'clear', 'upgrade', 'activate', 'create', 'destroy', 'import')

    def __init__(self, ssh_host=None, ssh_user=None, ssh_password=None, ssh_port=22):
        self.client = NpuClient(
            ssh_host=ssh_host, ssh_user=ssh_user,
            ssh_password=ssh_password, ssh_port=ssh_port
        )
        self.pending_confirmation = None

    def handle_command(self, text: str) -> str:
        """Handle user command"""
        text = text.strip()

        # Confirm/Cancel
        if text in ('cancel', 'abort'):
            self.pending_confirmation = None
            return 'Operation cancelled'
        if text in ('confirm', 'ok') and self.pending_confirmation:
            cmd = self.pending_confirmation
            self.pending_confirmation = None
            return self._execute_confirmed(cmd)

        # Natural language routing
        r = self._route_nl(text)
        if r:
            return r

        # Direct npu-smi command
        if text.startswith('npu-smi'):
            return self.client._run_npu_smi(text[7:].strip())

        return json.dumps({
            "status": "help",
            "message": "Unknown command. Please enter NPU-related commands.",
            "supported_commands": self._get_help_list()
        }, ensure_ascii=False)

    def _route_nl(self, text: str) -> Optional[str]:
        """Natural language routing"""

        # ===== Batch operations =====
        if any(kw in text for kw in ('all NPU', 'all NPUs', 'all cards', 'each card')):
            return self._handle_batch(text)

        # ===== FLOPS test =====
        if any(kw in text for kw in ('compute', 'TFLOPS', 'FLOPS', 'tflops')):
            return self._handle_flops(text)

        # ===== Configuration commands (sensitive) =====
        if any(kw in text for kw in ('set ECC', 'enable ECC', 'disable ECC', 'ECC enable', 'ECC disable')):
            return self._handle_set_ecc(text)

        if any(kw in text for kw in ('fan mode', 'auto fan', 'manual fan')):
            return self._handle_set_fan_mode(text)

        if any(kw in text for kw in ('fan speed', 'set fan')):
            return self._handle_set_fan_speed(text)

        if any(kw in text for kw in ('clear ECC', 'reset ECC')):
            return self._handle_clear_ecc(text)

        # ===== Firmware upgrade commands =====
        if any(kw in text for kw in ('firmware version', 'query firmware')):
            return self._handle_upgrade_query(text)

        if any(kw in text for kw in ('upload firmware', 'upgrade firmware')):
            return self._handle_upgrade_upload(text)

        if any(kw in text for kw in ('upgrade status', 'upgrade check')):
            return self._handle_upgrade_check(text)

        if any(kw in text for kw in ('activate firmware',)):
            return self._handle_upgrade_activate(text)

        # ===== Virtualization commands =====
        if any(kw in text for kw in ('vNPU info', 'virtual NPU', 'vnpu info')):
            return self._handle_vnpu_info(text)

        if any(kw in text for kw in ('vNPU mode', 'virtualization mode', 'AVI mode')):
            return self._handle_vnpu_mode(text)

        if any(kw in text for kw in ('template info', 'vNPU template', 'template')):
            return self._handle_template_info(text)

        if any(kw in text for kw in ('create vNPU', 'new vNPU')):
            return self._handle_create_vnpu(text)

        if any(kw in text for kw in ('destroy vNPU', 'delete vNPU', 'destroy')):
            return self._handle_destroy_vnpu(text)

        # ===== Certificate commands =====
        if any(kw in text for kw in ('certificate info', 'TLS cert', 'view cert')):
            return self._handle_cert_info(text)

        if any(kw in text for kw in ('cert expiration', 'expiration threshold', 'cert threshold')):
            return self._handle_cert_period(text)

        # ===== Query commands =====
        if any(kw in text for kw in ('NPU list', 'list NPU', 'NPU devices', 'NPU cards')):
            return self._handle_list_devices()

        if any(kw in text for kw in ('NPU info', 'NPU full', 'NPU details', 'npu-smi info', 'NPU overview')):
            return self._format_output('NPU Full Information', self.client.get_full_info())

        if any(kw in text for kw in ('NPU health', 'health check', 'NPU status', 'check NPU', 'health status')):
            return self._handle_health_check()

        if any(kw in text for kw in ('chip mapping', 'chip list', 'NPU mapping')):
            chips = self.client.get_chip_mapping()
            return self._format_output('Chip Mapping', chips)

        if any(kw in text for kw in ('temperature', 'NPU temp', 'temp')):
            return self._handle_temperature(text)

        if any(kw in text for kw in ('power', 'NPU power')):
            return self._handle_power(text)

        if any(kw in text for kw in ('HBM', 'hbm', 'NPU memory', 'NPU HBM')):
            return self._handle_hbm(text)

        if any(kw in text for kw in ('usage', 'NPU usage', 'utilization')):
            return self._handle_usage(text)

        if any(kw in text for kw in ('ECC', 'ecc', 'ECC errors')):
            return self._handle_ecc(text)

        if any(kw in text for kw in ('NPU processes', 'process list', 'proc-mem')):
            return self._handle_processes(text)

        if any(kw in text for kw in ('PCIe', 'pcie', 'PCIe errors')):
            return self._handle_pcie(text)

        if any(kw in text for kw in ('topology', 'NPU topology', 'topo')):
            return self._handle_topology(text)

        if any(kw in text for kw in ('product info', 'NPU product', 'product')):
            return self._handle_product(text)

        if any(kw in text for kw in ('board info', 'NPU board', 'board')):
            return self._handle_board(text)

        return None

    # ===== Query handling =====

    def _handle_list_devices(self) -> str:
        try:
            devices = self.client.parse_full_info()
            if not devices:
                return "No NPU devices found"
            lines = ["📦 NPU Device List", f"Device count: {len(devices)}", ""]
            for dev in devices:
                status_icon = "🟢" if dev.get('health') == 'OK' else "🔴"
                lines.append(f"  NPU {dev['npu_id']} | Chips: {dev.get('chip_count', 1)} | {status_icon} {dev.get('health', 'Unknown')}")
            return "\n".join(lines)
        except Exception:
            result = self.client.list_devices()
            devices = result.get("devices", [])
            if not devices:
                return "No NPU devices found"
            lines = ["📦 NPU Device List", f"Device count: {len(devices)}", ""]
            for dev in devices:
                health = self.client.get_health(dev["npu_id"])
                status_icon = "🟢" if health == "OK" else "🔴"
                lines.append(f"  NPU {dev['npu_id']} | Chips: {dev['chip_count']} | {status_icon} {health}")
            return "\n".join(lines)

    def _handle_health_check(self) -> str:
        try:
            devices = self.client.parse_full_info()
            if not devices:
                return "No NPU devices found"
            lines = ["🏥 NPU Health Check", ""]
            issues = 0
            for dev in devices:
                health = dev.get('health', 'Unknown')
                icon = "🟢" if health == 'OK' else "🔴"
                npu_id = dev['npu_id']
                lines.append(f"  NPU {npu_id}: {icon} {health}")
                if health != 'OK':
                    issues += 1
                    if dev.get('temperature') is not None:
                        lines.append(f"    Temperature: {dev['temperature']}°C")
                    if dev.get('power') is not None:
                        lines.append(f"    Power: {dev['power']}W")
            lines.append("")
            if issues == 0:
                lines.append("✅ All devices healthy")
            else:
                lines.append(f"⚠️ {issues} device(s) with issues")
            return "\n".join(lines)
        except Exception:
            result = self.client.list_devices()
            devices = result.get("devices", [])
            if not devices:
                return "No NPU devices found"
            lines = ["🏥 NPU Health Check", ""]
            issues = 0
            for dev in devices:
                npu_id = dev["npu_id"]
                health = self.client.get_health(npu_id)
                icon = "🟢" if health == "OK" else "🔴"
                lines.append(f"  NPU {npu_id}: {icon} {health}")
                if health != "OK":
                    issues += 1
                    temp = self.client.get_temperature(npu_id, 0)
                    power = self.client.get_power(npu_id, 0)
                    if temp:
                        lines.append(f"    Temperature: {temp}")
                    if power:
                        lines.append(f"    Power: {power}")
            lines.append("")
            if issues == 0:
                lines.append("✅ All devices healthy")
            else:
                lines.append(f"⚠️ {issues} device(s) with issues")
            return "\n".join(lines)

    def _handle_temperature(self, text: str) -> str:
        npu_id, chip_id = self._parse_ids(text)
        result = self.client.get_temperature(npu_id, chip_id)
        return self._format_output(f'🌡️ NPU {npu_id} Chip {chip_id} Temperature', result)

    def _handle_power(self, text: str) -> str:
        npu_id, chip_id = self._parse_ids(text)
        result = self.client.get_power(npu_id, chip_id)
        return self._format_output(f'⚡ NPU {npu_id} Chip {chip_id} Power', result)

    def _handle_hbm(self, text: str) -> str:
        npu_id, chip_id = self._parse_ids(text)
        mem = self.client.get_memory(npu_id, chip_id)
        usage = self.client.get_hbm_usage(npu_id, chip_id)
        output = f"💾 NPU {npu_id} Chip {chip_id} Memory Info\n"
        output += f"{'─' * 40}\n"
        if mem:
            for k, v in mem.items():
                output += f"  {k}: {v}\n"
        if usage:
            output += "\nUsage:\n"
            for k, v in usage.items():
                output += f"  {k}: {v}%\n"
        return output.strip()

    def _handle_usage(self, text: str) -> str:
        npu_id, chip_id = self._parse_ids(text)
        result = self.client.get_hbm_usage(npu_id, chip_id)
        return self._format_output(f'📊 NPU {npu_id} Chip {chip_id} Usage', result)

    def _handle_ecc(self, text: str) -> str:
        npu_id, chip_id = self._parse_ids(text)
        result = self.client.get_ecc_errors(npu_id, chip_id)
        return self._format_output(f'🔍 NPU {npu_id} Chip {chip_id} ECC Errors', result)

    def _handle_processes(self, text: str) -> str:
        npu_id, chip_id = self._parse_ids(text)
        result = self.client.get_processes(npu_id, chip_id)
        return self._format_output(f'📋 NPU {npu_id} Chip {chip_id} Processes', result)

    def _handle_pcie(self, text: str) -> str:
        npu_id, chip_id = self._parse_ids(text)
        result = self.client.get_pcie_errors(npu_id, chip_id)
        return self._format_output(f'🔌 NPU {npu_id} Chip {chip_id} PCIe Errors', result)

    def _handle_topology(self, text: str) -> str:
        npu_id, chip_id = self._parse_ids(text)
        result = self.client.get_topology(npu_id, chip_id)
        return self._format_output(f'🔗 NPU {npu_id} Chip {chip_id} Topology', result)

    def _handle_product(self, text: str) -> str:
        npu_id, chip_id = self._parse_ids(text)
        result = self.client.get_product_info(npu_id, chip_id)
        return self._format_output(f'🏷️ NPU {npu_id} Chip {chip_id} Product Info', result)

    def _handle_board(self, text: str) -> str:
        npu_id = self._parse_ids(text)[0]
        result = self.client.get_board_info(npu_id)
        return self._format_output(f'📟 NPU {npu_id} Board Info', result)

    # ===== Configuration handling =====

    def _handle_set_ecc(self, text: str) -> str:
        npu_id, chip_id = self._parse_ids(text)
        enable = any(kw in text for kw in ('enable', 'on'))
        action = "enable" if enable else "disable"
        self.pending_confirmation = ('set_ecc', npu_id, chip_id, enable)
        return f"⚠️ Sensitive operation: {action} ECC for NPU {npu_id} Chip {chip_id}\n\nPlease reply 'confirm' or 'cancel'"

    def _handle_set_fan_mode(self, text: str) -> str:
        auto = any(kw in text for kw in ('auto', 'automatic'))
        mode = "auto" if auto else "manual"
        self.pending_confirmation = ('set_fan_mode', auto)
        return f"⚠️ Sensitive operation: Set fan to {mode} mode\n\nPlease reply 'confirm' or 'cancel'"

    def _handle_set_fan_speed(self, text: str) -> str:
        match = re.search(r'(\d+)%?', text)
        percent = int(match.group(1)) if match else 50
        self.pending_confirmation = ('set_fan_speed', percent)
        return f"⚠️ Sensitive operation: Set fan speed to {percent}%\n\nPlease reply 'confirm' or 'cancel'"

    def _handle_clear_ecc(self, text: str) -> str:
        npu_id, chip_id = self._parse_ids(text)
        self.pending_confirmation = ('clear_ecc', npu_id, chip_id)
        return f"⚠️ Sensitive operation: Clear ECC error count for NPU {npu_id} Chip {chip_id}\n\nPlease reply 'confirm' or 'cancel'"

    # ===== Firmware upgrade handling =====

    def _handle_upgrade_query(self, text: str) -> str:
        component = self._parse_component(text)
        npu_id = self._parse_ids(text)[0]
        result = self.client.upgrade_query(component, npu_id)
        return self._format_output(f'🔄 NPU {npu_id} {component} Firmware Version', result)

    def _handle_upgrade_upload(self, text: str) -> str:
        component = self._parse_component(text)
        npu_id = self._parse_ids(text)[0]
        file_match = re.search(r'[\w/\-.]+\.(hpm|bin|pkg)', text)
        firmware_file = file_match.group(0) if file_match else "<please specify firmware path>"
        self.pending_confirmation = ('upgrade_upload', component, npu_id, firmware_file)
        return f"⚠️ Sensitive operation: Upload {component} firmware {firmware_file} to NPU {npu_id}\n\nPlease reply 'confirm' or 'cancel'"

    def _handle_upgrade_check(self, text: str) -> str:
        component = self._parse_component(text)
        npu_id = self._parse_ids(text)[0]
        result = self.client.upgrade_check(component, npu_id)
        return self._format_output(f'📋 NPU {npu_id} {component} Upgrade Status', result)

    def _handle_upgrade_activate(self, text: str) -> str:
        component = self._parse_component(text)
        npu_id = self._parse_ids(text)[0]
        self.pending_confirmation = ('upgrade_activate', component, npu_id)
        return f"⚠️ Sensitive operation: Activate {component} firmware on NPU {npu_id} (requires reboot)\n\nPlease reply 'confirm' or 'cancel'"

    # ===== Virtualization handling =====

    def _handle_vnpu_info(self, text: str) -> str:
        npu_id, chip_id = self._parse_ids(text)
        result = self.client.get_vnpu_info(npu_id, chip_id)
        return self._format_output(f'🔲 NPU {npu_id} Chip {chip_id} vNPU Info', result)

    def _handle_vnpu_mode(self, text: str) -> str:
        result = self.client.get_vnpu_mode()
        return self._format_output('🔲 vNPU/AVI Mode', result)

    def _handle_template_info(self, text: str) -> str:
        npu_id = self._parse_ids(text)[0]
        result = self.client.get_template_info(npu_id if npu_id else None)
        return self._format_output(f'📋 vNPU Template Info', result)

    def _handle_create_vnpu(self, text: str) -> str:
        npu_id, chip_id = self._parse_ids(text)
        tmpl_match = re.search(r'(vir\d+)', text)
        template = tmpl_match.group(1) if tmpl_match else "vir04"
        self.pending_confirmation = ('create_vnpu', npu_id, chip_id, template)
        return f"⚠️ Sensitive operation: Create vNPU on NPU {npu_id} Chip {chip_id} (template: {template})\n\nPlease reply 'confirm' or 'cancel'"

    def _handle_destroy_vnpu(self, text: str) -> str:
        npu_id, chip_id = self._parse_ids(text)
        vnpu_match = re.search(r'vNPU\s*(\d+)', text)
        vnpu_id = int(vnpu_match.group(1)) if vnpu_match else 100
        self.pending_confirmation = ('destroy_vnpu', npu_id, chip_id, vnpu_id)
        return f"⚠️ Sensitive operation: Destroy vNPU {vnpu_id} on NPU {npu_id} Chip {chip_id}\n\nPlease reply 'confirm' or 'cancel'"

    # ===== Certificate handling =====

    def _handle_cert_info(self, text: str) -> str:
        npu_id, chip_id = self._parse_ids(text)
        result = self.client.get_tls_cert(npu_id, chip_id)
        return self._format_output(f'🔐 NPU {npu_id} Chip {chip_id} TLS Certificate', result)

    def _handle_cert_period(self, text: str) -> str:
        npu_id, chip_id = self._parse_ids(text)
        result = self.client.get_cert_period(npu_id, chip_id)
        return self._format_output(f'🔐 NPU {npu_id} Chip {chip_id} Certificate Expiration', result)

    # ===== Confirmed execution =====

    def _execute_confirmed(self, cmd) -> str:
        """Execute confirmed operation"""
        try:
            op = cmd[0]
            if op == 'set_ecc':
                _, npu_id, chip_id, enable = cmd
                result = self.client.set_ecc_enable(npu_id, chip_id, enable)
                return f"✅ ECC {'enabled' if enable else 'disabled'}\n{result}"
            elif op == 'set_fan_mode':
                _, auto = cmd
                result = self.client.set_fan_mode(auto)
                return f"✅ Fan set to {'auto' if auto else 'manual'} mode\n{result}"
            elif op == 'set_fan_speed':
                _, percent = cmd
                result = self.client.set_fan_speed(percent)
                return f"✅ Fan speed set to {percent}%\n{result}"
            elif op == 'clear_ecc':
                _, npu_id, chip_id = cmd
                result = self.client.clear_ecc_errors(npu_id, chip_id)
                return f"✅ ECC errors cleared\n{result}"
            elif op == 'upgrade_upload':
                _, component, npu_id, firmware_file = cmd
                result = self.client.upgrade_upload(component, npu_id, firmware_file)
                return f"✅ {component} firmware uploaded\n{result}"
            elif op == 'upgrade_activate':
                _, component, npu_id = cmd
                result = self.client.upgrade_activate(component, npu_id)
                return f"✅ {component} firmware activated (requires reboot)\n{result}"
            elif op == 'create_vnpu':
                _, npu_id, chip_id, template = cmd
                result = self.client.create_vnpu(npu_id, chip_id, template)
                return f"✅ vNPU created\n{result}"
            elif op == 'destroy_vnpu':
                _, npu_id, chip_id, vnpu_id = cmd
                result = self.client.destroy_vnpu(npu_id, chip_id, vnpu_id)
                return f"✅ vNPU {vnpu_id} destroyed\n{result}"
            else:
                return "❌ Unknown operation"
        except Exception as e:
            return f"❌ Execution failed: {e}"

    # ===== Batch operations =====

    def _handle_batch(self, text: str) -> str:
        """Batch query for all NPUs"""
        try:
            devices = self.client.parse_full_info()
        except Exception:
            return "❌ Failed to get NPU information"

        if not devices:
            return "No NPU devices found"

        if any(kw in text for kw in ('temperature', 'temp')):
            return self._format_batch(devices, 'temperature', '°C', '🌡️ All NPU Temperature')
        elif any(kw in text for kw in ('power', 'power consumption')):
            return self._format_batch(devices, 'power', 'W', '⚡ All NPU Power')
        elif any(kw in text for kw in ('HBM', 'hbm', 'memory')):
            return self._format_batch_hbm(devices)
        elif any(kw in text for kw in ('usage', 'utilization')):
            return self._format_batch(devices, 'ai_core_usage', '%', '📊 All NPU Usage')
        elif any(kw in text for kw in ('health', 'status')):
            return self._format_batch_health(devices)
        else:
            return self._format_batch_overview(devices)

    def _format_batch(self, devices: list, key: str, unit: str, title: str) -> str:
        """Format batch single metric output"""
        lines = [title, "─" * 50]
        values = []
        for dev in devices:
            val = dev.get(key)
            if val is not None:
                try:
                    num = float(val)
                    values.append(num)
                    lines.append(f"  NPU {dev['npu_id']}: {num:.1f}{unit}")
                except (ValueError, TypeError):
                    lines.append(f"  NPU {dev['npu_id']}: {val}{unit}")
            else:
                lines.append(f"  NPU {dev['npu_id']}: N/A")
        if values:
            lines.append(f"  ─────────────")
            lines.append(f"  Avg: {sum(values)/len(values):.1f}{unit}  Max: {max(values):.1f}{unit}  Min: {min(values):.1f}{unit}")
        return "\n".join(lines)

    def _format_batch_hbm(self, devices: list) -> str:
        """Format batch HBM output"""
        lines = ["💾 All NPU HBM Usage", "─" * 50]
        for dev in devices:
            hbm_used = dev.get('hbm_used', 'N/A')
            hbm_total = dev.get('hbm_total', 'N/A')
            lines.append(f"  NPU {dev['npu_id']}: {hbm_used} / {hbm_total}")
        return "\n".join(lines)

    def _format_batch_health(self, devices: list) -> str:
        """Format batch health check"""
        lines = ["🏥 All NPU Health Status", "─" * 50]
        issues = 0
        for dev in devices:
            health = dev.get('health', 'Unknown')
            icon = "🟢" if health == 'OK' else "🔴"
            lines.append(f"  NPU {dev['npu_id']}: {icon} {health}")
            if health != 'OK':
                issues += 1
        lines.append("")
        lines.append("✅ All healthy" if issues == 0 else f"⚠️ {issues} device(s) with issues")
        return "\n".join(lines)

    def _format_batch_overview(self, devices: list) -> str:
        """Format batch full overview"""
        lines = ["📊 All NPU Overview", "─" * 60]
        lines.append(f"{'NPU':>4} {'Health':>4} {'Temp':>6} {'Power':>7} {'AICore':>7} {'HBM':>10}")
        lines.append("─" * 60)
        for dev in devices:
            npu = dev['npu_id']
            health = dev.get('health', '?')
            h_icon = "🟢" if health == 'OK' else "🔴"
            temp = f"{dev.get('temperature', 'N/A')}°C" if dev.get('temperature') else "N/A"
            power = f"{dev.get('power', 'N/A')}W" if dev.get('power') else "N/A"
            usage = f"{dev.get('ai_core_usage', 'N/A')}%" if dev.get('ai_core_usage') else "N/A"
            hbm_u = dev.get('hbm_used', '?')
            hbm_t = dev.get('hbm_total', '?')
            hbm = f"{hbm_u}/{hbm_t}"
            lines.append(f"  {npu:>2}  {h_icon}  {temp:>6} {power:>7} {usage:>7} {hbm:>10}")
        return "\n".join(lines)

    # ===== FLOPS test =====

    def _handle_flops(self, text: str) -> str:
        """Handle FLOPS test request"""
        import subprocess
        import sys

        precision = 'fp16'
        for p in ['fp32', 'bf16', 'int8', 'fp16', 'hf32', 'fp8']:
            if p in text.lower():
                precision = p
                break

        multi_card = any(kw in text for kw in ('all NPU', 'all NPUs', 'all cards', 'multi-card', '8 cards'))

        npu_match = re.search(r'(?:NPU|npu)\s*(\d+)', text)
        npu_id = int(npu_match.group(1)) if npu_match else None

        if not multi_card and npu_id is None:
            npu_id = 0

        if not multi_card:
            return self._test_single_flops(npu_id, precision)

        return self._test_multi_flops_async(precision)

    def _test_single_flops(self, npu_id: int, precision: str) -> str:
        """Single card FLOPS test"""
        import subprocess
        import sys

        cmd = f"ascend-dmi -f -d {npu_id} -t {precision} -q"

        if self.client.ssh_host:
            output = self.client._execute(cmd)
        else:
            result = subprocess.run(shlex.split(cmd), shell=False, capture_output=True, text=True, timeout=120)
            output = result.stdout

        return self._parse_flops_output(output, npu_id, precision)

    def _parse_flops_output(self, output: str, npu_id: int, precision: str) -> str:
        """Parse FLOPS test output"""
        lines = [f"🚀 NPU {npu_id} FLOPS Test ({precision.upper()})", "─" * 50]

        for line in output.split('\n'):
            match = re.search(r'(\d+)\s+([\d,]+)\s+(\d+)\s+([\d.]+)\s+([\d.]+)', line)
            if match:
                device = match.group(1)
                exec_times = match.group(2)
                duration = match.group(3)
                tflops = float(match.group(4))
                power = float(match.group(5))

                lines.append(f"  Device: NPU {device}")
                lines.append(f"  Execute Times: {exec_times}")
                lines.append(f"  Duration: {duration} ms")
                lines.append(f"  FLOPS: {tflops:.2f} TFLOPS@{precision.upper()}")
                lines.append(f"  Power: {power:.1f} W")
                break
        else:
            lines.append("❌ Parse failed, raw output:")
            lines.append(output)

        return "\n".join(lines)

    def _test_multi_flops_async(self, precision: str) -> str:
        """Multi-card FLOPS test (async concurrent)"""
        import subprocess
        import sys
        import threading

        try:
            devices = self.client.parse_full_info()
            npu_count = len(devices)
        except:
            npu_count = 8

        results = {}
        threads = []

        def test_npu(npu_id):
            try:
                cmd = f"ascend-dmi -f -d {npu_id} -t {precision} -q"
                if self.client.ssh_host:
                    output = self.client._execute(cmd)
                else:
                    result = subprocess.run(shlex.split(cmd), shell=False, capture_output=True, text=True, timeout=120)
                    output = result.stdout

                for line in output.split('\n'):
                    match = re.search(r'(\d+)\s+([\d,]+)\s+(\d+)\s+([\d.]+)\s+([\d.]+)', line)
                    if match:
                        results[npu_id] = {
                            'tflops': float(match.group(4)),
                            'power': float(match.group(5)),
                            'duration': int(match.group(3))
                        }
                        break
            except Exception as e:
                results[npu_id] = {'error': str(e)}

        for i in range(npu_count):
            t = threading.Thread(target=test_npu, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join(timeout=120)

        lines = [f"🚀 Multi-Card FLOPS Test ({precision.upper()})", "─" * 60]
        lines.append(f"{'NPU':>4}  {'TFLOPS':>10}  {'Power(W)':>8}  {'Duration(ms)':>12}")
        lines.append("─" * 60)

        total_tflops = 0
        total_power = 0
        success_count = 0

        for i in range(npu_count):
            if i in results and 'tflops' in results[i]:
                r = results[i]
                total_tflops += r['tflops']
                total_power += r['power']
                success_count += 1
                lines.append(f"  {i:>2}  {r['tflops']:>10.2f}  {r['power']:>8.1f}  {r['duration']:>12}")
            else:
                lines.append(f"  {i:>2}  {'N/A':>10}  {'N/A':>8}  {'N/A':>12}")

        lines.append("─" * 60)
        if success_count > 0:
            lines.append(f"Total: {total_tflops:.2f} TFLOPS@{precision.upper()}, Power: {total_power:.1f}W")
        else:
            lines.append("❌ All tests failed")

        return "\n".join(lines)

    # ===== Utility methods =====

    def _parse_ids(self, text: str) -> tuple:
        """Parse NPU ID and Chip ID from text"""
        npu_match = re.search(r'(?:NPU|npu)\s*(\d+)', text)
        chip_match = re.search(r'(?:Chip|chip)\s*(\d+)', text)
        npu_id = int(npu_match.group(1)) if npu_match else 0
        chip_id = int(chip_match.group(1)) if chip_match else 0
        return npu_id, chip_id

    def _parse_component(self, text: str) -> str:
        """Parse firmware component name"""
        for comp in ('mcu', 'bootloader', 'vrd'):
            if comp in text.lower():
                return comp
        return 'mcu'

    def _format_output(self, title: str, data: Any) -> str:
        """Format output"""
        if isinstance(data, dict):
            lines = [f"{title}", "─" * 40]
            for k, v in data.items():
                lines.append(f"  {k}: {v}")
            return "\n".join(lines)
        elif isinstance(data, list):
            lines = [f"{title}", "─" * 40]
            for item in data:
                if isinstance(item, dict):
                    lines.append(f"  {item}")
                else:
                    lines.append(f"  {item}")
            return "\n".join(lines)
        else:
            return f"{title}\n{'─' * 40}\n{data}"

    def _get_help_list(self) -> List[str]:
        return [
            "📦 Query: NPU list | NPU info | NPU health | temperature | power | HBM | usage | ECC | NPU processes | PCIe errors | topology | product info | board info",
            "⚙️ Configuration: set ECC | fan mode | fan speed | clear ECC",
            "🔄 Firmware: firmware version | upgrade firmware | upgrade status | activate firmware",
            "🔲 Virtualization: vNPU info | vNPU mode | template info | create vNPU | destroy vNPU",
            "🔐 Certificate: certificate info | cert expiration",
            "💡 Specify device: add 'NPU0 Chip0' after command",
        ]