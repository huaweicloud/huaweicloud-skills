#!/usr/bin/env python3
"""
excel_reader.py — Excel 参数读取器 (2 Sheet 页)

从 Excel 文件读取迁移参数，支持:
  - Sheet1 '主机信息': 源端主机 + 目标端创建参数 (15 列)
  - Sheet2 '代理主机信息': 代理 ECS 连接信息 (6 列)
  - 目标端自动创建: region_id/project_id/target_image_id/target_AZ
  - 参数校验和必填字段检查

  注意: AK/SK 凭证不再从 Excel 读取 (v2.8.1 安全规范)。
  请通过环境变量 migration_Access_Key / migration_Secret_Access_Key 提供凭证。
  主机密码支持占位符 ${env_var_name}，读取时自动从环境变量替换。
  支持任意 ${...} 占位符 (如 ${migration_password}, ${custom_key} 等)。
  若密码列为明文值则直接使用 (向后兼容)。

Excel 列定义:
  Sheet1: 主机名|内网IP|端口号|用户名|密码|region_id|region_name|project_id|project_name|os_type|use_public_ip|target_image_id|target_AZ
  Sheet2: 主机名称|公网IP|私网IP|端口|用户名|密码
"""

import os
import re
import logging
from typing import Optional, Dict, List, Any, Set

logger = logging.getLogger(__name__)

try:
    import openpyxl
except ImportError:
    openpyxl = None


# ──────────────────────────────────────────────────────────────
# Sheet1 '主机信息' 列映射 (15 列)
# ──────────────────────────────────────────────────────────────
HOST_SHEET_COLUMNS = {
    "主机名": "source_name",
    "内网IP": "source_ip",
    "端口号": "source_ssh_port",
    "用户名": "source_username",
    "密码": "source_password",
    "region_id": "region_id",
    "region_name": "region_name",
    "project_id": "project_id",
    "project_name": "project_name",
    "os_type": "os_type",
    "use_public_ip": "use_public_ip",
    "target_image_id": "target_image_id",
    "target_AZ": "target_az",
}

# ──────────────────────────────────────────────────────────────
# Sheet2 '代理主机信息' 列映射 (6 列)
# ──────────────────────────────────────────────────────────────
PROXY_SHEET_COLUMNS = {
    "主机名称": "proxy_name",
    "公网IP": "proxy_public_ip",
    "私网IP": "proxy_private_ip",
    "端口": "proxy_ssh_port",
    "用户名": "proxy_username",
    "密码": "proxy_password",
}

# 必填字段 (Sheet1)
REQUIRED_HOST_FIELDS = ["source_ip", "source_username", "source_password",
                        "region_id", "project_id"]

# 默认值
DEFAULTS = {
    "source_ssh_port": 22,
    "source_username": "root",
    "os_type": "Linux",
    "use_public_ip": False,
    "proxy_ssh_port": 22,
}

# Sheet 名称 (支持中英文变体)
HOST_SHEET_NAMES = ["主机信息", "源端主机信息", "hosts", "Sheet1"]
PROXY_SHEET_NAMES = ["代理主机信息", "代理信息", "proxy", "Sheet2"]


class ExcelReader:
    """Excel 参数读取器 (2 Sheet 页)"""

    def __init__(self, file_path: str):
        """
        Args:
            file_path: Excel 文件路径
        """
        self.file_path = file_path
        self.hosts: List[Dict[str, Any]] = []
        self.proxy: Optional[Dict[str, Any]] = None
        # 追踪 Excel 中出现的所有 ${...} 占位符对应的环境变量名
        self.required_env_vars: Set[str] = set()
        # 追踪未能从环境变量解析的占位符 (env_var_name -> field_name)
        self.unresolved_placeholders: Dict[str, str] = {}

    def read(self) -> Dict[str, Any]:
        """读取 Excel 全部 2 个 Sheet 页

        Returns:
            {
                "hosts": [...],      # Sheet1 源端主机列表
                "proxy": {...},      # Sheet2 代理主机信息
            }
        """
        if openpyxl is None:
            raise ImportError("openpyxl is required. Install: pip install openpyxl")

        if not os.path.exists(self.file_path):
            raise FileNotFoundError(f"Excel file not found: {self.file_path}")

        logger.info(f"Reading Excel: {self.file_path}")

        wb = openpyxl.load_workbook(self.file_path, read_only=True, data_only=True)

        # 识别 Sheet 页
        sheet_names = wb.sheetnames
        logger.info(f"Sheet names: {sheet_names}")

        host_sheet = self._find_sheet(wb, HOST_SHEET_NAMES)
        proxy_sheet = self._find_sheet(wb, PROXY_SHEET_NAMES)

        # 读取各 Sheet
        if host_sheet:
            self.hosts = self._read_host_sheet(host_sheet)
            logger.info(f"Read {len(self.hosts)} host entries from Sheet1")
        else:
            logger.warning("Host info sheet not found, trying first sheet")
            if sheet_names:
                self.hosts = self._read_host_sheet(wb[sheet_names[0]])

        if proxy_sheet:
            self.proxy = self._read_proxy_sheet(proxy_sheet)
            if self.proxy:
                logger.info(f"Read proxy info from Sheet2: {self.proxy.get('proxy_name', 'N/A')} "
                            f"(public_ip={self.proxy.get('proxy_public_ip', 'N/A')})")
            else:
                logger.warning("Proxy sheet found but contains no valid data rows")
        else:
            # 回退: 尝试第二个 Sheet (按索引)
            if len(sheet_names) >= 2:
                logger.warning(f"Proxy sheet not found by name {PROXY_SHEET_NAMES}, "
                               f"trying second sheet by index: '{sheet_names[1]}'")
                self.proxy = self._read_proxy_sheet(wb[sheet_names[1]])
                if self.proxy:
                    logger.info(f"Read proxy info from fallback sheet: "
                                f"{self.proxy.get('proxy_name', 'N/A')} "
                                f"(public_ip={self.proxy.get('proxy_public_ip', 'N/A')})")
                else:
                    logger.warning("Fallback proxy sheet also contains no valid data")
            else:
                logger.warning("Proxy info sheet not found and no second sheet available")

        wb.close()

        # 校验
        self._validate()

        return {
            "hosts": self.hosts,
            "proxy": self.proxy,
        }

    def _find_sheet(self, wb, possible_names: List[str]):
        """按候选名称查找 Sheet 页"""
        for name in possible_names:
            if name in wb.sheetnames:
                return wb[name]
        return None

    # ──────────────────────────────────────────────────────────
    #  Sheet1: 主机信息
    # ──────────────────────────────────────────────────────────

    def _read_host_sheet(self, ws) -> List[Dict[str, Any]]:
        """读取 Sheet1 主机信息"""
        headers = self._read_headers(ws)
        col_indices = self._map_columns(headers, HOST_SHEET_COLUMNS)

        logger.info(f"Sheet1 detected columns: {list(col_indices.values())}")

        rows = []
        for row_idx, row in enumerate(ws.iter_rows(min_row=2), start=2):
            entry = {}
            has_data = False

            for col_idx, field_name in col_indices.items():
                cell_value = row[col_idx].value if col_idx < len(row) else None
                if cell_value is not None and str(cell_value).strip():
                    has_data = True
                    entry[field_name] = self._parse_value(field_name, cell_value)

            if not has_data:
                continue

            # 应用默认值
            for k, v in DEFAULTS.items():
                if k not in entry:
                    entry[k] = v

            # 空值字段处理
            entry.setdefault("target_image_id", "")  # 空 = 与源端一致
            entry.setdefault("target_az", "")         # 空 = 随机 AZ

            entry["_row"] = row_idx
            rows.append(entry)

        return rows

    # ──────────────────────────────────────────────────────────
    #  Sheet2: 代理主机信息
    # ──────────────────────────────────────────────────────────

    def _read_proxy_sheet(self, ws) -> Optional[Dict[str, Any]]:
        """读取 Sheet2 代理主机信息 (取第一行有效数据)"""
        headers = self._read_headers(ws)
        logger.info(f"Sheet2 headers: {headers}")
        col_indices = self._map_columns(headers, PROXY_SHEET_COLUMNS)
        logger.info(f"Sheet2 mapped columns: {col_indices}")

        if not col_indices:
            logger.warning("Sheet2: no columns matched proxy sheet column map, "
                           f"expected headers: {list(PROXY_SHEET_COLUMNS.keys())}")
            return None

        for row in ws.iter_rows(min_row=2):
            entry = {}
            has_data = False

            for col_idx, field_name in col_indices.items():
                cell_value = row[col_idx].value if col_idx < len(row) else None
                if cell_value is not None and str(cell_value).strip():
                    has_data = True
                    entry[field_name] = self._parse_value(field_name, cell_value)

            if has_data:
                # 应用默认值
                entry.setdefault("proxy_ssh_port", 22)
                entry.setdefault("proxy_username", "root")
                return entry

        return None

    # ──────────────────────────────────────────────────────────
    #  辅助方法
    # ──────────────────────────────────────────────────────────

    def _read_headers(self, ws) -> List[str]:
        """读取表头行"""
        headers = []
        for cell in next(ws.iter_rows(min_row=1, max_row=1)):
            headers.append(str(cell.value).strip() if cell.value else "")
        return headers

    def _map_columns(self, headers: List[str], column_map: Dict[str, str]) -> Dict[int, str]:
        """映射列名到字段名"""
        col_indices = {}
        for idx, header in enumerate(headers):
            if header in column_map:
                col_indices[idx] = column_map[header]
        return col_indices

    # 通用占位符正则: 匹配 ${env_var_name}
    _PLACEHOLDER_RE = re.compile(r'\$\{([a-zA-Z_][a-zA-Z0-9_]*)\}')

    def _parse_value(self, field_name: str, value: Any) -> Any:
        """解析单元格值

        支持通用占位符 ${env_var_name}:
          - 扫描所有字符串值中的 ${...} 模式
          - 从环境变量读取对应值并替换
          - 追踪所有占位符到 self.required_env_vars
          - 未解析的记录到 self.unresolved_placeholders
          - 明文值直接返回 (向后兼容)

        注意: Sheet2 代理密码 (proxy_password) 不走占位符解析，
              保持 Excel 直接读取方式。
        """
        if value is None:
            return None

        s = str(value).strip()

        # 布尔字段
        if field_name == "use_public_ip":
            return s.lower() in ("true", "yes", "1", "是", "y")

        # 整数字段
        if field_name in ("source_ssh_port", "proxy_ssh_port"):
            try:
                return int(s)
            except ValueError:
                return DEFAULTS.get(field_name, 0)

        # Sheet2 代理密码不走占位符解析，直接返回
        if field_name == "proxy_password":
            return s

        # 通用占位符解析: 扫描 ${...} 模式
        placeholders = self._PLACEHOLDER_RE.findall(s)
        if placeholders:
            result = s
            for env_name in placeholders:
                self.required_env_vars.add(env_name)
                env_val = os.environ.get(env_name)
                if env_val:
                    result = result.replace(f"${{{env_name}}}", env_val)
                    logger.info(
                        f"{field_name}: 从环境变量 {env_name} 解析占位符 ${{{env_name}}}"
                    )
                else:
                    # 记录未解析的占位符
                    self.unresolved_placeholders[env_name] = field_name
                    logger.warning(
                        f"{field_name}: 占位符 ${{{env_name}}} 但环境变量 {env_name} 未设置, "
                        f"保留占位符原值 (后续校验将报错)"
                    )
            return result

        # 明文值直接返回 (向后兼容)
        return s

    def _validate(self):
        """校验数据"""
        errors = []

        for i, host in enumerate(self.hosts):
            row_num = host.get("_row", i + 2)
            source_ip = host.get("source_ip", "")

            # 检查必填字段
            for field in REQUIRED_HOST_FIELDS:
                if field not in host or not host[field]:
                    errors.append(f"Sheet1 Row {row_num}: missing required field '{field}'")

            # 检查 IP 格式
            if source_ip and not self._is_valid_ip(source_ip):
                errors.append(f"Sheet1 Row {row_num}: invalid IP '{source_ip}'")

            # 私网迁移检查
            if not host.get("use_public_ip", False):
                if not self.proxy:
                    errors.append(f"Sheet1 Row {row_num}: private network migration requires proxy info (Sheet2)")

        # 代理主机校验
        if self.proxy:
            proxy_ip = self.proxy.get("proxy_public_ip", "")
            if proxy_ip and not self._is_valid_ip(proxy_ip):
                errors.append(f"Sheet2: invalid proxy public IP '{proxy_ip}'")
            proxy_private = self.proxy.get("proxy_private_ip", "")
            if proxy_private and not self._is_valid_ip(proxy_private):
                errors.append(f"Sheet2: invalid proxy private IP '{proxy_private}'")

        if errors:
            for err in errors:
                logger.error(err)
            raise ValueError(f"Excel validation failed with {len(errors)} errors:\n" + "\n".join(errors))

        logger.info("Excel validation passed")

    def _is_valid_ip(self, ip: str) -> bool:
        """简单 IP 格式校验"""
        parts = ip.split(".")
        if len(parts) != 4:
            return False
        for part in parts:
            try:
                n = int(part)
                if n < 0 or n > 255:
                    return False
            except ValueError:
                return False
        return True

    # ──────────────────────────────────────────────────────────
    #  便捷方法
    # ──────────────────────────────────────────────────────────

    def filter_private(self) -> List[Dict]:
        """筛选私网迁移条目"""
        return [h for h in self.hosts if not h.get("use_public_ip", False)]

    def filter_public(self) -> List[Dict]:
        """筛选公网迁移条目"""
        return [h for h in self.hosts if h.get("use_public_ip", False)]

    def get_summary(self) -> Dict[str, Any]:
        """获取汇总信息"""
        return {
            "total_hosts": len(self.hosts),
            "private": len(self.filter_private()),
            "public": len(self.filter_public()),
            "has_proxy": self.proxy is not None,
            "file": self.file_path,
        }

    def get_proxy(self) -> Optional[Dict[str, Any]]:
        """获取代理主机信息"""
        return self.proxy

    def get_hosts(self) -> List[Dict[str, Any]]:
        """获取主机列表"""
        return self.hosts

    def get_required_env_vars(self) -> Set[str]:
        """获取 Excel 中所有占位符对应的环境变量名集合

        Returns:
            环境变量名集合, 如 {'migration_password', 'custom_key'}
        """
        return self.required_env_vars

    def get_unresolved_placeholders(self) -> Dict[str, str]:
        """获取未能从环境变量解析的占位符

        Returns:
            {env_var_name: field_name} 映射
        """
        return self.unresolved_placeholders

    def read_all_sheets(self, excel_path: str = None) -> Dict[str, Any]:
        """读取全部2个Sheet页, 返回统一格式

        Args:
            excel_path: Excel文件路径 (可选, 默认使用初始化时的路径)

        Returns:
            {
                "hosts": [...],         # Sheet1 源端主机列表
                "proxy_hosts": [...],   # Sheet2 代理主机列表
            }
        """
        path = excel_path or self.file_path
        reader = ExcelReader(path)
        reader.read()

        # 转换 proxy dict → list 格式
        proxy_hosts = []
        if reader.proxy:
            p = reader.proxy
            proxy_hosts.append({
                "name": p.get("proxy_name", ""),
                "public_ip": p.get("proxy_public_ip", ""),
                "private_ip": p.get("proxy_private_ip", ""),
                "port": p.get("proxy_ssh_port", 22),
                "username": p.get("proxy_username", "root"),
                "password": p.get("proxy_password", ""),
            })

        return {
            "hosts": reader.hosts,
            "proxy_hosts": proxy_hosts,
        }


def create_template(output_path: str):
    """创建 Excel 模板 (2 Sheet 页)"""
    if openpyxl is None:
        raise ImportError("openpyxl is required")

    wb = openpyxl.Workbook()

    # ── Sheet1: 主机信息 ──
    ws1 = wb.active
    ws1.title = "主机信息"
    _write_sheet_headers(ws1, list(HOST_SHEET_COLUMNS.keys()))

    example1 = {
        "主机名": "example-host-001",
        "内网IP": "192.168.0.186",
        "端口号": "",
        "用户名": "your-username",
        "密码": "your-password-here",
        "region_id": "cn-north-4",
        "region_name": "华北-北京四",
        "project_id": "",
        "project_name": "",
        "os_type": "Linux",
        "use_public_ip": "false",  # Issue 3: 私网迁移专用 Skill, 默认且强制使用私网
        "target_image_id": "",
        "target_AZ": "",
    }
    _write_sheet_row(ws1, 2, list(HOST_SHEET_COLUMNS.keys()), example1)

    # ── Sheet2: 代理主机信息 ──
    ws2 = wb.create_sheet("代理主机信息")
    _write_sheet_headers(ws2, list(PROXY_SHEET_COLUMNS.keys()))

    example2 = {
        "主机名称": "example-proxy-host",
        "公网IP": "192.0.2.1",
        "私网IP": "172.16.0.125",
        "端口": "",
        "用户名": "your-username",
        "密码": "your-password-here",
    }
    _write_sheet_row(ws2, 2, list(PROXY_SHEET_COLUMNS.keys()), example2)

    # 列宽
    for ws in [ws1, ws2]:
        for col in range(1, ws.max_column + 1):
            ws.column_dimensions[openpyxl.utils.get_column_letter(col)].width = 20

    wb.save(output_path)
    logger.info(f"Template created: {output_path}")


def _write_sheet_headers(ws, headers: List[str]):
    """写入表头行"""
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = openpyxl.styles.Font(bold=True, color="FFFFFF")
        cell.fill = openpyxl.styles.PatternFill(
            start_color="4472C4", end_color="4472C4", fill_type="solid"
        )


def _write_sheet_row(ws, row_idx: int, headers: List[str], data: Dict[str, Any]):
    """写入数据行"""
    for col, header in enumerate(headers, 1):
        if header in data:
            ws.cell(row=row_idx, column=col, value=data[header])
