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
    from .npu_client import NpuClient, NpuCommandError, format_npu_error
except ImportError:
    from npu_client import NpuClient, NpuCommandError, format_npu_error


# Chinese trigger words -> English keywords (I178-3). Longest source words are
# applied first so a multi-character term wins over any shorter overlapping term.
_ZH_ALIAS_PAIRS = (
    ('昇腾状态', 'NPU status'),
    ('昇腾卡', 'NPU list'),
    ('虚拟化', 'virtualization'),
    ('昇腾', 'NPU'),
    ('温度', 'temperature'),
    ('功耗', 'power'),
    ('功率', 'power'),
    ('电源', 'power'),
    ('显存', 'memory'),
    ('内存', 'memory'),
    ('算力', 'FLOPS'),
    ('固件', 'firmware'),
    ('风扇', 'fan'),
    ('自动', 'auto'),
    ('手动', 'manual'),
    ('启用', 'enable'),
    ('开启', 'enable'),
    ('禁用', 'disable'),
    ('关闭', 'disable'),
    ('设置', 'set'),
    ('设定', 'set'),
    ('查看', 'get'),
    ('查询', 'get'),
    ('获取', 'get'),
    ('列表', 'list'),
    ('清单', 'list'),
    ('健康', 'health'),
    ('状态', 'status'),
    ('证书', 'certificate'),
    ('过期', 'expiration'),
    ('升级', 'upgrade'),
    ('回滚', 'rollback'),
    ('激活', 'activate'),
    ('模板', 'template'),
    ('创建', 'create'),
    ('销毁', 'destroy'),
    ('删除', 'delete'),
    ('设备', 'device'),
    ('进程', 'processes'),
    ('错误', 'errors'),
    ('拓扑', 'topology'),
    ('产品', 'product'),
    ('批量', 'batch'),
)
_ZH_ALIASES = tuple(sorted(_ZH_ALIAS_PAIRS, key=lambda pair: len(pair[0]), reverse=True))


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

    def handle_command(self, text) -> str:
        """Handle user command (all failures become message text, never a traceback)"""
        # Input defense: None / non-string / blank input must not crash (B115-4)
        if not isinstance(text, str) or not text.strip():
            return self._help_json("Unknown command. Please enter NPU-related commands.")

        try:
            raw = text.strip()
            lowered = raw.lower()

            # Confirm/Cancel (English keywords plus Chinese aliases)
            if lowered in ('cancel', 'abort') or raw in ('取消', '取消操作'):
                self.pending_confirmation = None
                return 'Operation cancelled'
            if (lowered in ('confirm', 'ok') or raw in ('确认', '确定')) and self.pending_confirmation:
                cmd = self.pending_confirmation
                self.pending_confirmation = None
                return self._execute_confirmed(cmd)

            # Any new command invalidates a stale confirmation gate: a later
            # 'confirm' must never execute an operation the user moved on from
            # (e.g. 'disable ECC' -> 'set ECC' -> 'confirm', I178-4).
            self.pending_confirmation = None

            # Direct npu-smi pass-through must win over NL keywords (B115-2)
            if lowered.startswith('npu-smi'):
                return self.client._run_npu_smi(raw[7:].strip())

            # Chinese trigger words are normalized to English before routing (I178-3)
            zh = self._normalize_zh(raw)

            # Natural language routing
            r = self._route_nl(zh)
            if r:
                return r

            return self._help_json("Unknown command. Please enter NPU-related commands.")
        except NpuCommandError as e:
            return format_npu_error(e)
        except Exception as e:
            return ("[ERROR] NPU-UNEXPECTED\n"
                    f"Message: {e}\n"
                    "Suggestion: 请检查命令与环境后重试；本地模式需安装 npu-smi，"
                    "SSH 模式需 --host/--user/--password")

    def _help_json(self, message: str) -> str:
        """Build the help JSON response"""
        return json.dumps({
            "status": "help",
            "message": message,
            "supported_commands": self._get_help_list()
        }, ensure_ascii=False)

    def _match(self, text: str, keywords) -> bool:
        """Case-insensitive keyword matching"""
        lowered = text.lower()
        return any(kw.lower() in lowered for kw in keywords)

    def _match_word(self, text: str, keywords) -> bool:
        """Whole-word, case-insensitive keyword matching.

        Like _match but each keyword must appear as a standalone word (bounded
        by word boundaries), so a short trigger such as 'temp' never matches
        inside a longer unrelated word such as 'template' (B852-1).
        """
        lowered = text.lower()
        pattern = r'\b(?:' + '|'.join(re.escape(kw.lower()) for kw in keywords) + r')\b'
        return re.search(pattern, lowered) is not None

    def _normalize_zh(self, text: str) -> str:
        """Translate Chinese trigger words into English keywords (I178-3).

        Each alias becomes a space-padded English word so the space-separated
        English keyword lists keep matching after translation, e.g.
        ``查看NPU温度`` -> ``get NPU temperature``.
        """
        for zh, en in _ZH_ALIASES:
            if zh in text:
                text = text.replace(zh, f' {en} ')
        return re.sub(r'\s{2,}', ' ', text).strip()

    def _route_nl(self, text: str) -> Optional[str]:
        """Natural language routing (case-insensitive, Chinese pre-normalized)"""

        # ===== FLOPS test =====
        # Matched before the batch branch: 'all NPU FLOPS' / 'all cards FLOPS' /
        # 'all devices FLOPS' are multi-card FLOPS requests and must not be
        # swallowed by the batch query (F-1).
        if self._match(text, ('compute', 'TFLOPS', 'FLOPS', 'tflops')):
            return self._handle_flops(text)

        # ===== Batch operations =====
        if self._match(text, ('all NPU', 'all NPUs', 'all cards', 'each card')):
            return self._handle_batch(text)

        # ===== Configuration commands (sensitive) =====
        if self._match(text, ('set ECC', 'enable ECC', 'disable ECC', 'ECC enable', 'ECC disable')):
            return self._handle_set_ecc(text)

        # Fan mode is matched before fan speed, otherwise 'set fan auto' falls
        # into the speed branch and silently turns into 50% (I178-1).
        if self._match(text, ('fan mode', 'auto fan', 'manual fan', 'fan auto',
                              'fan manual', 'set fan auto', 'set fan manual')):
            return self._handle_set_fan_mode(text)

        if self._match(text, ('fan speed',)) or (self._match(text, ('set fan',)) and re.search(r'\d', text)):
            return self._handle_set_fan_speed(text)

        if self._match(text, ('set fan',)):
            return ("Please specify fan mode or speed: reply 'set fan auto', "
                    "'set fan manual', or 'set fan speed <0-100>'")

        if self._match(text, ('clear ECC', 'reset ECC')):
            return self._handle_clear_ecc(text)

        # ===== Firmware upgrade commands =====
        if self._match(text, ('firmware version', 'query firmware')):
            return self._handle_upgrade_query(text)

        if self._match(text, ('upload firmware', 'upgrade firmware')):
            return self._handle_upgrade_upload(text)

        if self._match(text, ('upgrade status', 'upgrade check')):
            return self._handle_upgrade_check(text)

        if self._match(text, ('rollback firmware', 'rollback', 'roll back')):
            return self._handle_upgrade_rollback(text)

        if self._match(text, ('activate firmware', 'activate upgrade', 'firmware activate')):
            return self._handle_upgrade_activate(text)

        # Generic fallback: a bare 'firmware' request (e.g. 查看NPU固件) is a
        # version query. It stays after the specific branches above so
        # 'upgrade firmware' / 'rollback firmware' keep their own handlers (F-2).
        if self._match(text, ('firmware',)):
            return self._handle_upgrade_query(text)

        # ===== Virtualization commands =====
        if self._match(text, ('vNPU info', 'virtual NPU', 'vnpu info')):
            return self._handle_vnpu_info(text)

        if self._match(text, ('vNPU mode', 'virtualization mode', 'AVI mode', 'virtualization')):
            return self._handle_vnpu_mode(text)

        # create/destroy are matched before the template branch: the input
        # 'create vNPU NPU0 Chip0 template vir04' contains 'template' (B115-3).
        if self._match(text, ('create vNPU', 'new vNPU')):
            return self._handle_create_vnpu(text)

        if self._match(text, ('destroy vNPU', 'delete vNPU', 'destroy')):
            return self._handle_destroy_vnpu(text)

        if self._match_word(text, ('template', 'templates')) or self._match(text, ('template info', 'vNPU template', 'template-info')):
            return self._handle_template_info(text)

        # ===== Certificate commands =====
        if self._match(text, ('certificate info', 'TLS cert', 'view cert')):
            return self._handle_cert_info(text)

        if self._match(text, ('cert expiration', 'expiration threshold', 'cert threshold')):
            return self._handle_cert_period(text)

        # ===== Query commands =====
        if self._match(text, ('NPU list', 'list NPU', 'NPU devices', 'NPU cards')):
            return self._handle_list_devices()

        if self._match(text, ('NPU info', 'NPU full', 'NPU details', 'npu-smi info', 'NPU overview')):
            return self._format_output('NPU Full Information', self.client.get_full_info())

        if self._match(text, ('NPU health', 'health check', 'NPU status', 'check NPU', 'health status')):
            return self._handle_health_check()

        if self._match(text, ('chip mapping', 'chip list', 'NPU mapping')):
            chips = self.client.get_chip_mapping()
            return self._format_output('Chip Mapping', chips)

        if self._match_word(text, ('temperature', 'temp')):
            return self._handle_temperature(text)

        if self._match(text, ('power', 'NPU power')):
            return self._handle_power(text)

        if self._match(text, ('HBM', 'hbm', 'memory', 'NPU memory', 'NPU HBM')):
            return self._handle_hbm(text)

        if self._match(text, ('usage', 'NPU usage', 'utilization')):
            return self._handle_usage(text)

        if self._match(text, ('ECC', 'ecc', 'ECC errors')):
            return self._handle_ecc(text)

        if self._match(text, ('NPU processes', 'process list', 'proc-mem')):
            return self._handle_processes(text)

        if self._match(text, ('PCIe', 'pcie', 'PCIe errors')):
            return self._handle_pcie(text)

        if self._match(text, ('topology', 'NPU topology', 'topo')):
            return self._handle_topology(text)

        if self._match(text, ('product info', 'NPU product', 'product')):
            return self._handle_product(text)

        if self._match(text, ('board info', 'NPU board', 'board')):
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
        enable = self._match(text, ('enable', 'on'))
        disable = self._match(text, ('disable', 'off'))
        if enable == disable:
            # No direction (or both) given: ask instead of silently disabling (I178-4)
            return "Please specify direction: 'enable ECC' or 'disable ECC'"
        self.pending_confirmation = ('set_ecc', npu_id, chip_id, enable)
        return f"⚠️ Sensitive operation: {'enable' if enable else 'disable'} ECC for NPU {npu_id} Chip {chip_id}\n\nPlease reply 'confirm' or 'cancel'"

    def _handle_set_fan_mode(self, text: str) -> str:
        auto = self._match(text, ('auto', 'automatic'))
        mode = "auto" if auto else "manual"
        self.pending_confirmation = ('set_fan_mode', auto)
        return f"⚠️ Sensitive operation: Set fan to {mode} mode\n\nPlease reply 'confirm' or 'cancel'"

    def _handle_set_fan_speed(self, text: str) -> str:
        match = re.search(r'(\d+)\s*%', text)
        if match:
            percent = int(match.group(1))
        else:
            # Drop device ids so 'NPU0 Chip0 set fan speed 80' still reads 80
            stripped = re.sub(r'(?:NPU|npu|Chip|chip)\s*\d+', ' ', text)
            numbers = re.findall(r'\d+', stripped)
            if not numbers:
                return ("Please specify fan speed (0-100): reply 'set fan speed 80' "
                        "or use 'set fan auto' / 'set fan manual'")
            percent = int(numbers[-1])
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

    def _handle_upgrade_rollback(self, text: str) -> str:
        npu_id = self._parse_ids(text)[0]
        self.pending_confirmation = ('upgrade_rollback', npu_id)
        return (f"⚠️ Sensitive operation: Rollback firmware on NPU {npu_id} "
                "(rollback may not be supported on all devices)\n\n"
                "Please reply 'confirm' or 'cancel'")

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
            elif op == 'upgrade_rollback':
                _, npu_id = cmd
                result = self.client.rollback_firmware(npu_id)
                return f"✅ Firmware rollback initiated\n{result}"
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
        except NpuCommandError as e:
            return format_npu_error(e)
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

        if self._match_word(text, ('temperature', 'temp')):
            return self._format_batch(devices, 'temperature', '°C', '🌡️ All NPU Temperature')
        elif self._match(text, ('power', 'power consumption')):
            return self._format_batch(devices, 'power', 'W', '⚡ All NPU Power')
        elif self._match(text, ('HBM', 'hbm', 'memory')):
            return self._format_batch_hbm(devices)
        elif self._match(text, ('usage', 'utilization')):
            return self._format_batch(devices, 'ai_core_usage', '%', '📊 All NPU Usage')
        elif self._match(text, ('health', 'status')):
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

        multi_card = self._match(text, ('all NPU', 'all NPUs', 'all cards', 'all devices',
                                        'all device', 'multi-card', '8 cards'))

        npu_match = re.search(r'(?<![A-Za-z])(?:NPU|npu)\s*(\d+)', text)
        npu_id = int(npu_match.group(1)) if npu_match else None

        if not multi_card and npu_id is None:
            npu_id = 0

        if not multi_card:
            return self._test_single_flops(npu_id, precision)

        return self._test_multi_flops_async(precision)

    def _test_single_flops(self, npu_id: int, precision: str) -> str:
        """Single card FLOPS test"""
        import subprocess

        cmd = f"ascend-dmi -f -d {npu_id} -t {precision} -q"

        if self.client.ssh_host:
            output = self.client._execute(cmd)
        else:
            try:
                result = subprocess.run(shlex.split(cmd), shell=False, capture_output=True, text=True, timeout=120)
            except FileNotFoundError:
                return ("❌ ascend-dmi not found: install CANN/ascend-dmi on the target host, "
                        "or run with --host for SSH remote mode (B115-5)")
            except subprocess.TimeoutExpired:
                return "❌ FLOPS test timed out (120s)"
            if result.returncode != 0:
                summary = (result.stderr or result.stdout or "").strip()[:200]
                return f"❌ ascend-dmi failed (exit {result.returncode}): {summary}"
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
                    try:
                        result = subprocess.run(shlex.split(cmd), shell=False, capture_output=True, text=True, timeout=120)
                    except FileNotFoundError:
                        results[npu_id] = {'error': 'ascend-dmi not found: install CANN/ascend-dmi or use --host'}
                        return
                    except subprocess.TimeoutExpired:
                        results[npu_id] = {'error': 'FLOPS test timed out (120s)'}
                        return
                    if result.returncode != 0:
                        summary = (result.stderr or result.stdout or "").strip()[:200]
                        results[npu_id] = {'error': f'ascend-dmi failed (exit {result.returncode}): {summary}'}
                        return
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
            errors = []
            for i in range(npu_count):
                err = results.get(i, {}).get('error')
                if err and err not in errors:
                    errors.append(err)
            if npu_count == 0:
                lines.append("❌ No NPU devices found to test")
            elif len(errors) == 1:
                # Every card failed for the same reason (e.g. ascend-dmi is not
                # installed): report that reason instead of a bare "All tests
                # failed" (F-1, same wording as the single-card path B115-5).
                lines.append(f"❌ {errors[0]}")
            else:
                lines.append("❌ All tests failed")
                for err in errors[:3]:
                    lines.append(f"  ❌ {err}")

        return "\n".join(lines)

    # ===== Utility methods =====

    def _parse_ids(self, text: str) -> tuple:
        """Parse NPU ID and Chip ID from text"""
        # The lookbehind keeps 'vNPU 3' from being read as NPU 3: 'destroy vNPU 3'
        # targets NPU 0 and vNPU 3, not NPU 3.
        npu_match = re.search(r'(?<![A-Za-z])(?:NPU|npu)\s*(\d+)', text)
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
            "🔄 Firmware: firmware version | upgrade firmware | upgrade status | rollback firmware | activate firmware",
            "🔲 Virtualization: vNPU info | vNPU mode | template info | create vNPU | destroy vNPU",
            "🔐 Certificate: certificate info | cert expiration",
            "💡 Specify device: add 'NPU0 Chip0' after command",
        ]