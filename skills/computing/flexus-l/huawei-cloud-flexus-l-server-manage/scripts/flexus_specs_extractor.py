#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Huawei Cloud Flexus L Instance Spec Code Extractor

Features:
- Fetch image and spec info from official documentation in real-time
- No dependency on local config files
- On-demand calls, returns latest data

Usage:
    python3 flexus_specs_extractor.py              # Get all data
    python3 flexus_specs_extractor.py --specs      # Get spec definitions only
    python3 flexus_specs_extractor.py --images     # Get system images only
    python3 flexus_specs_extractor.py --regions    # Get region info
"""

import urllib.request
import re
import json
import sys
import time
import random
import gzip
from typing import List, Dict, Optional

from config import REGIONS


# Configuration constants
REQUEST_TIMEOUT = 20
MIN_DELAY = 0.3
MAX_DELAY = 1.0

# Known system image names
KNOWN_IMAGE_NAMES = [
    'WindowsServer', 'Ubuntu', 'CentOS', 'Debian', 'Huawei Cloud EulerOS',
    'AlmaLinux', 'Rocky Linux', 'openEuler', 'OpenSUSE', 'CoreOS',
    'CentOS_Stream', 'Fedora', 'EulerOS',
]


class FlexusSpecsExtractor:
    """Huawei Cloud Flexus L instance spec code extractor"""
    
    def __init__(self):
        self.url = "https://support.huaweicloud.com/api-flexusl/create_instance_0001.html"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9',
            'Accept-Language': 'zh-CN,zh;q=0.9',
        }
        self.html_content = None
    
    def fetch_page(self) -> bool:
        """Fetch page content"""
        try:
            delay = random.uniform(MIN_DELAY, MAX_DELAY)
            time.sleep(delay)
            
            req = urllib.request.Request(self.url, headers=self.headers)
            with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as response:
                if response.status != 200:
                    return False
                
                raw_data = response.read()
                try:
                    self.html_content = raw_data.decode('utf-8')
                except UnicodeDecodeError:
                    try:
                        self.html_content = gzip.decompress(raw_data).decode('utf-8')
                    except Exception:
                        return False
                
                return True
                
        except Exception:
            return False
    
    def extract_all_tables(self) -> List[Dict]:
        """Extract all tables"""
        if not self.html_content:
            return []
        
        tables = []
        table_pattern = r'<table[^>]*>(.*?)</table>'
        table_matches = re.findall(table_pattern, self.html_content, re.DOTALL)
        
        for i, table_html in enumerate(table_matches):
            rows = self._parse_table_rows(table_html)
            if rows:
                table_info = {
                    'index': i,
                    'rows': rows,
                    'header': rows[0] if rows else [],
                    'data': rows[1:] if len(rows) > 1 else [],
                    'type': 'unknown',
                }
                table_info['type'] = self._identify_table_type(table_info)
                tables.append(table_info)
        
        return tables
    
    def _parse_table_rows(self, table_html: str) -> List[List[str]]:
        """Parse table rows"""
        rows = re.findall(r'<tr[^>]*>(.*?)</tr>', table_html, re.DOTALL)
        result = []
        
        for row in rows:
            cells = re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', row, re.DOTALL)
            clean_cells = []
            for cell in cells:
                clean = re.sub(r'<[^>]+>', ' ', cell)
                clean = re.sub(r'&nbsp;', ' ', clean)
                clean = re.sub(r'\s+', ' ', clean).strip()
                clean_cells.append(clean)
            
            if clean_cells and any(c for c in clean_cells):
                result.append(clean_cells)
        
        return result
    
    def _identify_table_type(self, table_info: Dict) -> str:
        """Identify table type"""
        header = table_info['header']
        data = table_info['data']
        header_text = ' '.join(header).lower()
        
        # Spec table identification
        if 'vcpu' in header_text and '规格编码' in header_text:
            if data:
                first_col = ' '.join([r[0] if r else '' for r in data[:5]])
                if '.win' in first_col:
                    return 'spec_windows'
                elif '.linux' in first_col:
                    return 'spec_linux'
            return 'spec_linux'
        
        # System image table identification
        if '系统镜像' in header_text or '镜像名称' in header_text:
            return 'system_images'
        
        if data:
            first_col_samples = [row[0] if row else '' for row in data[:10]]
            first_col_text = ' '.join(first_col_samples)
            
            # Spec table identification
            if '.linux' in first_col_text or '.win' in first_col_text:
                return 'spec_windows' if '.win' in first_col_text else 'spec_linux'
            
            # System image table identification
            for name in KNOWN_IMAGE_NAMES:
                if name in first_col_text:
                    return 'system_images'
        
        return 'unknown'
    
    def get_regions(self) -> Dict:
        """Get region information"""
        return REGIONS
    
    def get_spec_definitions(self) -> Dict:
        """Get spec definitions"""
        if not self.html_content and not self.fetch_page():
            return {}
        
        tables = self.extract_all_tables()
        spec_definitions = {}
        
        spec_tables = [t for t in tables if t['type'] in ('spec_linux', 'spec_windows')]
        
        for table in spec_tables:
            header = table['header']
            data = table['data']
            
            col_map = self._identify_spec_columns(header)
            
            for row in data:
                try:
                    spec_info = self._parse_spec_row(row, col_map)
                    if spec_info and spec_info.get('spec_code'):
                        spec_code = spec_info['spec_code']
                        del spec_info['spec_code']
                        if self._validate_spec(spec_code, spec_info):
                            spec_definitions[spec_code] = spec_info
                except Exception:
                    continue
        
        return spec_definitions
    
    def _identify_spec_columns(self, header: List[str]) -> Dict[str, int]:
        """Identify spec table columns"""
        col_map = {}
        
        for i, h in enumerate(header):
            h_lower = h.lower()
            if '规格编码' in h or 'spec' in h_lower:
                col_map['spec_code'] = i
            elif 'vcpu' in h_lower or 'cpu' in h_lower:
                col_map['vcpu'] = i
            elif '内存' in h or 'memory' in h_lower:
                col_map['memory'] = i
            elif '磁盘' in h or 'disk' in h_lower:
                col_map['disk'] = i
            elif '带宽' in h or 'bandwidth' in h_lower:
                col_map['bandwidth'] = i
            elif '流量' in h or 'traffic' in h_lower:
                col_map['traffic'] = i
        
        col_map.setdefault('spec_code', 0)
        col_map.setdefault('vcpu', 1)
        col_map.setdefault('memory', 2)
        col_map.setdefault('disk', 3)
        col_map.setdefault('bandwidth', 4)
        col_map.setdefault('traffic', 5)
        
        return col_map
    
    def _parse_spec_row(self, row: List[str], col_map: Dict) -> Optional[Dict]:
        """Parse spec row"""
        def extract_number(text: str) -> float:
            match = re.search(r'[\d.]+', text)
            return float(match.group()) if match else 0
        
        def safe_get(key: str) -> str:
            idx = col_map.get(key, -1)
            return row[idx] if 0 <= idx < len(row) else ''
        
        try:
            spec_code = safe_get('spec_code')
            
            if not spec_code or '规格编码' in spec_code:
                return None
            
            if not re.match(r'^[a-z]+\.', spec_code):
                return None
            
            os_type = 'windows' if '.win' in spec_code else 'linux'
            
            return {
                'spec_code': spec_code,
                'vcpu': int(extract_number(safe_get('vcpu'))),
                'memory': extract_number(safe_get('memory')),
                'disk': int(extract_number(safe_get('disk'))),
                'bandwidth': int(extract_number(safe_get('bandwidth'))),
                'traffic': int(extract_number(safe_get('traffic'))),
                'os': os_type,
            }
        except (ValueError, IndexError):
            return None
    
    def _validate_spec(self, spec_code: str, spec_info: Dict) -> bool:
        """Validate spec data"""
        return spec_info['vcpu'] > 0 and spec_info['memory'] > 0 and spec_info['disk'] > 0
    
    def get_system_images(self) -> Dict:
        """Get system images"""
        if not self.html_content and not self.fetch_page():
            return {}
        
        tables = self.extract_all_tables()
        system_images = {}
        
        image_tables = [t for t in tables if t['type'] == 'system_images']
        
        for table in image_tables:
            data = table['data']
            
            for row in data:
                try:
                    if len(row) < 7:
                        continue
                    
                    image_name = row[0].strip()
                    
                    is_valid = False
                    for known in KNOWN_IMAGE_NAMES:
                        if known.lower() in image_name.lower() or image_name.lower() in known.lower():
                            is_valid = True
                            break
                    
                    if not is_valid:
                        for i, cell in enumerate(row):
                            cell_clean = cell.strip()
                            for known in KNOWN_IMAGE_NAMES:
                                if known.lower() == cell_clean.lower():
                                    image_name = known
                                    is_valid = True
                                    row = row[i:] + row[:i]
                                    break
                            if is_valid:
                                break
                    
                    if not is_valid:
                        continue
                    
                    image_info = self._parse_image_row(row)
                    if image_info:
                        system_images[image_name] = image_info
                        
                except Exception:
                    continue
        
        return system_images
    
    def _parse_image_row(self, row: List[str]) -> Optional[Dict]:
        """Parse image row - supports all 6 regions"""
        def parse_specs(text: str) -> List[str]:
            specs = []
            for line in text.split('\n'):
                line = line.strip()
                if not line or line == '-':
                    continue
                line = re.sub(r'（[^）]+）', '', line)
                line = re.sub(r'\([^)]+\)', '', line)
                for spec in line.split():
                    if spec and '.' in spec and (spec.endswith('.linux') or spec.endswith('.win')):
                        specs.append(spec)
            return specs
        
        def parse_version(text: str) -> str:
            versions = [v.strip() for v in text.split('\n') if v.strip() and v.strip() != '-']
            return '\n'.join(versions) if versions else ''
        
        try:
            if len(row) < 7:
                return None
            
            # Parse base regions from table columns
            beijing_version = parse_version(row[1] if len(row) > 1 else '')
            beijing_specs = parse_specs(row[2] if len(row) > 2 else '')
            hongkong_version = parse_version(row[3] if len(row) > 3 else '')
            hongkong_specs = parse_specs(row[4] if len(row) > 4 else '')
            guizhou_version = parse_version(row[5] if len(row) > 5 else '')
            guizhou_specs = parse_specs(row[6] if len(row) > 6 else '')
            
            return {
                # Primary regions from table
                'beijing': {
                    'version': beijing_version,
                    'specs': beijing_specs,
                },
                'hongkong': {
                    'version': hongkong_version,
                    'specs': hongkong_specs,
                },
                'guizhou': {
                    'version': guizhou_version,
                    'specs': guizhou_specs,
                },
                # Derived regions (same as base regions per official docs)
                'shanghai': {
                    'version': beijing_version,
                    'specs': beijing_specs,
                },
                'guangzhou': {
                    'version': beijing_version,
                    'specs': beijing_specs,
                },
                'singapore': {
                    'version': hongkong_version,
                    'specs': hongkong_specs,
                },
            }
        except IndexError:
            return None
    
    def get_all(self) -> Dict:
        """Get all data"""
        if not self.fetch_page():
            return {'error': 'Unable to obtain page data'}
        
        return {
            'regions': self.get_regions(),
            'spec_definitions': self.get_spec_definitions(),
            'system_images': self.get_system_images(),
        }


def main():
    """Main function"""
    args = sys.argv[1:]
    
    extractor = FlexusSpecsExtractor()
    
    if '--regions' in args:
        data = extractor.get_regions()
    elif '--specs' in args:
        if not extractor.fetch_page():
            data = {'error': 'Unable to obtain page data'}
        else:
            data = extractor.get_spec_definitions()
    elif '--images' in args:
        if not extractor.fetch_page():
            data = {'error': 'Unable to obtain page data'}
        else:
            data = extractor.get_system_images()
    else:
        data = extractor.get_all()
    
    print(json.dumps(data, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
