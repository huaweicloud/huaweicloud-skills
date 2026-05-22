#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Terraform 环境安装脚本
支持多平台：Linux (Ubuntu/Debian/RHEL/CentOS), macOS, Windows
支持多种安装方式：APT/Chocolatey/Scoop（推荐）、二进制下载
优先使用华为云镜像源

参考文档: https://developer.hashicorp.com/terraform/install

使用方法:
    python3 install_terraform.py              # 安装最新版本（默认华为云镜像）
    python3 install_terraform.py --init       # 安装后自动运行 terraform init
    python3 install_terraform.py --test       # 安装后测试 Provider 是否可用
    python3 install_terraform.py --no-mirror  # 禁用华为云镜像，使用官方源
    python3 install_terraform.py --method binary   # 强制使用二进制下载
    python3 install_terraform.py --version 1.15.2  # 安装指定版本
    python3 install_terraform.py --check      # 仅检查安装状态
    python3 install_terraform.py --uninstall  # 卸载 Terraform
"""

import os
import sys
import argparse
import subprocess
import urllib.request
import urllib.error
import json
import tempfile
import shutil
import platform
from pathlib import Path
from typing import Optional, Tuple, Dict, List


# ============================================================
# 配置常量
# ============================================================

TERRAFORM_BINARY_NAME = "terraform.exe" if sys.platform == "win32" else "terraform"

# Terraform 下载源
GITHUB_API_URL = "https://api.github.com/repos/hashicorp/terraform/releases/latest"
TERRAFORM_DOWNLOAD_URL = "https://releases.hashicorp.com/terraform/{version}/terraform_{version}_{os}_{arch}.zip"
HASHICORP_APT_URL = "https://apt.releases.hashicorp.com"

# 华为云镜像配置
HUAWEI_MIRROR_URL = "https://mirrors.huaweicloud.com/terraform"
HUAWEI_PROVIDER_INDEX = f"{HUAWEI_MIRROR_URL}/registry.terraform.io/huaweicloud/huaweicloud"

# 测试用的 Terraform 脚本
TEST_TF_SCRIPT = '''terraform {
  required_providers {
    huaweicloud = {
      source  = "huaweicloud/huaweicloud"
      version = ">= 1.80.0"
    }
  }
}

provider "huaweicloud" {
  region = "cn-north-4"
}

data "huaweicloud_vpcs" "all" {}

output "vpc_count" {
  value = length(data.huaweicloud_vpcs.all.vpcs)
}
'''


# ============================================================
# 工具函数
# ============================================================

class Colors:
    """终端颜色"""
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'

    @classmethod
    def disable(cls):
        cls.RED = cls.GREEN = cls.YELLOW = cls.BLUE = cls.RESET = ''


def log_info(msg: str):
    print(f"{Colors.BLUE}[INFO]{Colors.RESET} {msg}")

def log_success(msg: str):
    print(f"{Colors.GREEN}[SUCCESS]{Colors.RESET} {msg}")

def log_warn(msg: str):
    print(f"{Colors.YELLOW}[WARN]{Colors.RESET} {msg}")

def log_error(msg: str):
    print(f"{Colors.RED}[ERROR]{Colors.RESET} {msg}")


def get_system_info() -> Dict:
    """获取系统信息（跨平台）"""
    system = platform.system().lower()
    machine = platform.machine().lower()
    
    # 架构映射
    arch_map = {
        "x86_64": "amd64",
        "amd64": "amd64",
        "aarch64": "arm64",
        "arm64": "arm64",
        "armv7l": "arm",
        "i386": "386",
        "i686": "386",
    }
    
    os_map = {
        "linux": "linux",
        "darwin": "darwin",
        "windows": "windows",
    }
    
    # 检测 Linux 发行版
    is_debian = False
    is_rhel = False
    if system == "linux":
        try:
            with open("/etc/os-release", "r") as f:
                content = f.read().lower()
                is_debian = "ubuntu" in content or "debian" in content
                is_rhel = "rhel" in content or "centos" in content or "rocky" in content or "almalinux" in content
        except:
            pass
    
    # Windows 检测
    is_windows = system == "windows"
    
    # 检测管理员权限
    is_admin = False
    if is_windows:
        try:
            import ctypes
            is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
        except:
            pass
    else:
        is_admin = os.geteuid() == 0 if hasattr(os, 'geteuid') else False
    
    return {
        "os": os_map.get(system, system),
        "arch": arch_map.get(machine, machine),
        "system": system,
        "machine": machine,
        "is_debian": is_debian,
        "is_rhel": is_rhel,
        "is_windows": is_windows,
        "is_admin": is_admin,
    }


def get_install_dir(system_info: Dict) -> Path:
    """获取安装目录（跨平台）"""
    if system_info["is_windows"]:
        if system_info["is_admin"]:
            # 管理员：Program Files
            return Path(os.environ.get("PROGRAMFILES", "C:\\Program Files")) / "Terraform"
        else:
            # 普通用户：LocalAppData
            return Path(os.environ.get("LOCALAPPDATA", os.path.expanduser("~\\AppData\\Local"))) / "Terraform"
    else:
        # Linux/macOS
        if system_info["is_admin"]:
            return Path("/usr/local/bin")
        else:
            return Path.home() / ".local" / "bin"


def get_provider_cache_dir(system_info: Dict) -> Path:
    """获取 Provider 缓存目录（跨平台）"""
    if system_info["is_windows"]:
        return Path(os.environ.get("APPDATA", os.path.expanduser("~\\AppData\\Roaming"))) / "terraform.d" / "plugin-cache"
    else:
        return Path.home() / ".terraform.d" / "plugin-cache"


def get_terraformrc_path(system_info: Dict) -> Path:
    """获取 Terraform CLI 配置文件路径（跨平台）"""
    if system_info["is_windows"]:
        return Path(os.environ.get("APPDATA", os.path.expanduser("~\\AppData\\Roaming"))) / "terraform.rc"
    else:
        return Path.home() / ".terraformrc"


def get_providers_dir(system_info: Dict) -> Path:
    """获取 Provider 安装目录（跨平台）"""
    if system_info["is_windows"]:
        return Path(os.environ.get("APPDATA", os.path.expanduser("~\\AppData\\Roaming"))) / "terraform.d" / "providers"
    else:
        return Path.home() / ".terraform.d" / "providers"


# ============================================================
# 网络检测
# ============================================================

def check_network() -> Dict[str, bool]:
    """检查网络连通性"""
    log_info("检查网络连通性...")
    
    results = {}
    
    # 核心源（必须可访问）
    core_endpoints = [
        ("hashicorp", "https://releases.hashicorp.com", "HashiCorp Releases"),
        ("huawei_mirror", HUAWEI_MIRROR_URL, "华为云镜像"),
    ]
    
    # 备选源（可选）
    optional_endpoints = [
        ("registry", "https://registry.terraform.io", "Terraform Registry"),
        ("github", "https://github.com", "GitHub (备选)"),
    ]
    
    # 检测核心源
    for key, url, name in core_endpoints:
        try:
            req = urllib.request.Request(url)
            urllib.request.urlopen(req, timeout=5)
            results[key] = True
            print(f"   ✅ {name} 可访问")
        except:
            results[key] = False
            print(f"   ❌ {name} 不可访问")
    
    # 检测备选源（不阻塞）
    for key, url, name in optional_endpoints:
        try:
            req = urllib.request.Request(url)
            urllib.request.urlopen(req, timeout=3)
            results[key] = True
            print(f"   ✅ {name} 可访问")
        except:
            results[key] = False
            print(f"   ⚠️  {name} 不可访问（备选源）")
    
    return results


# ============================================================
# Terraform 安装
# ============================================================

def get_latest_version() -> str:
    """获取最新版本号（优先使用最新稳定版本）"""
    log_info("正在查询版本...")
    
    # 已知最新版本（用于直接验证）
    known_latest = "1.15.2"
    
    # 方案 1: HashiCorp Releases API（优先）
    try:
        req = urllib.request.Request("https://releases.hashicorp.com/terraform/index.json")
        with urllib.request.urlopen(req, timeout=15) as response:
            data = json.loads(response.read().decode())
            versions = list(data.get("versions", {}).keys())
            # 过滤掉预发布版本（包含 - 的版本）
            stable_versions = [v for v in versions if '-' not in v]
            
            # 按语义版本排序，确保取到最新
            stable_versions.sort(key=lambda v: [int(x) for x in v.split('.')])
            
            if stable_versions:
                version = stable_versions[-1]
                # 如果 index.json 版本低于已知最新版本，使用已知版本
                if version < known_latest:
                    log_warn(f"index.json 最新版本 {version} 低于已知版本 {known_latest}")
                    version = known_latest
                log_success(f"使用最新稳定版本: {version} (HashiCorp Releases)")
                return version
    except Exception as e:
        log_warn(f"HashiCorp Releases 获取失败: {e}")
    
    # 方案 2: 直接验证已知最新版本
    try:
        test_url = f"https://releases.hashicorp.com/terraform/{known_latest}/"
        req = urllib.request.Request(test_url)
        with urllib.request.urlopen(req, timeout=10) as response:
            if response.status == 200:
                log_success(f"使用已知最新版本: {known_latest} (直接验证)")
                return known_latest
    except:
        pass
    
    # 方案 3: GitHub API（备选）
    try:
        req = urllib.request.Request(GITHUB_API_URL)
        req.add_header("Accept", "application/vnd.github.v3+json")
        req.add_header("User-Agent", "Terraform-Installer/1.0")
        
        with urllib.request.urlopen(req, timeout=15) as response:
            data = json.loads(response.read().decode())
            version = data["tag_name"].lstrip("v")
            log_warn(f"使用 GitHub 最新版本: {version}")
            return version
    except Exception as e:
        log_warn(f"GitHub API 获取失败: {e}")
    
    # 方案 4: 使用固定稳定版本（兜底）
    log_success(f"使用固定稳定版本: {known_latest}")
    return known_latest


def check_installation(system_info: Dict) -> Tuple[bool, Optional[str]]:
    """检查 Terraform 是否已安装"""
    install_dir = get_install_dir(system_info)
    terraform_path = install_dir / TERRAFORM_BINARY_NAME
    
    # 也检查系统 PATH
    try:
        if system_info["is_windows"]:
            result = subprocess.run(
                ["where", "terraform"],
                capture_output=True,
                text=True,
                timeout=5,
                shell=True
            )
        else:
            result = subprocess.run(
                ["which", "terraform"],
                capture_output=True,
                text=True,
                timeout=5
            )
        if result.returncode == 0:
            terraform_path = Path(result.stdout.strip().split('\n')[0])
    except:
        pass
    
    if terraform_path.exists():
        try:
            result = subprocess.run(
                [str(terraform_path), "version", "-json"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                info = json.loads(result.stdout)
                version = info.get("terraform_version", "unknown")
                log_success(f"Terraform 已安装: v{version}")
                print(f"   安装路径: {terraform_path}")
                return True, version
            else:
                result = subprocess.run(
                    [str(terraform_path), "version"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                version_line = result.stdout.split("\n")[0] if result.stdout else ""
                log_success(f"Terraform 已安装: {version_line}")
                print(f"   安装路径: {terraform_path}")
                return True, version_line
        except Exception as e:
            log_warn(f"Terraform 已存在但无法执行: {e}")
            return True, None
    else:
        log_error("Terraform 未安装")
        return False, None


def install_via_apt(system_info: Dict) -> bool:
    """通过 APT 安装（Linux Debian/Ubuntu）"""
    log_info("使用 APT 包管理器安装...")
    
    if not system_info["is_debian"]:
        log_warn("当前系统不是 Debian/Ubuntu，跳过 APT 方式")
        return False
    
    commands = [
        ("清理旧的 GPG 密钥", "rm -f /usr/share/keyrings/hashicorp-archive-keyring.gpg"),
        ("添加 HashiCorp GPG 密钥", f"wget -q -O - {HASHICORP_APT_URL}/gpg | gpg --batch --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg"),
        ("添加 HashiCorp APT 源", f'echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] {HASHICORP_APT_URL} $(lsb_release -cs) main" > /etc/apt/sources.list.d/hashicorp.list'),
        ("更新 APT 缓存", "apt-get update -qq"),
        ("安装 Terraform", "apt-get install -y terraform"),
    ]
    
    for desc, cmd in commands:
        print(f"  🔧 {desc}...")
        try:
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=120
            )
            if result.returncode != 0:
                log_error(f"失败: {result.stderr[:200]}")
                return False
        except Exception as e:
            log_error(f"异常: {e}")
            return False
    
    log_success("APT 安装完成")
    return True


def install_via_chocolatey(system_info: Dict) -> bool:
    """通过 Chocolatey 安装（Windows）"""
    log_info("使用 Chocolatey 安装...")
    
    if not system_info["is_windows"]:
        return False
    
    # 检查 Chocolatey 是否安装
    try:
        result = subprocess.run(
            ["choco", "--version"],
            capture_output=True,
            text=True,
            timeout=10,
            shell=True
        )
        if result.returncode != 0:
            log_warn("Chocolatey 未安装")
            return False
    except:
        log_warn("Chocolatey 未安装")
        return False
    
    # 安装 Terraform
    try:
        result = subprocess.run(
            ["choco", "install", "terraform", "-y"],
            capture_output=True,
            text=True,
            timeout=300,
            shell=True
        )
        if result.returncode == 0:
            log_success("Chocolatey 安装完成")
            return True
        else:
            log_error(f"安装失败: {result.stderr[:200]}")
            return False
    except Exception as e:
        log_error(f"异常: {e}")
        return False


def install_via_scoop(system_info: Dict) -> bool:
    """通过 Scoop 安装（Windows 用户级）"""
    log_info("使用 Scoop 安装...")
    
    if not system_info["is_windows"]:
        return False
    
    # 检查 Scoop 是否安装
    try:
        result = subprocess.run(
            ["scoop", "--version"],
            capture_output=True,
            text=True,
            timeout=10,
            shell=True
        )
        if result.returncode != 0:
            log_warn("Scoop 未安装")
            return False
    except:
        log_warn("Scoop 未安装")
        return False
    
    # 安装 Terraform
    try:
        result = subprocess.run(
            ["scoop", "install", "terraform"],
            capture_output=True,
            text=True,
            timeout=300,
            shell=True
        )
        if result.returncode == 0:
            log_success("Scoop 安装完成")
            return True
        else:
            log_error(f"安装失败: {result.stderr[:200]}")
            return False
    except Exception as e:
        log_error(f"异常: {e}")
        return False


def download_terraform(version: str, system_info: Dict) -> Tuple[Optional[str], Optional[str]]:
    """下载 Terraform 二进制文件"""
    download_url = TERRAFORM_DOWNLOAD_URL.format(
        version=version,
        os=system_info["os"],
        arch=system_info["arch"]
    )
    
    log_info(f"下载地址: {download_url}")
    
    tmpdir = tempfile.mkdtemp()
    zip_path = os.path.join(tmpdir, "terraform.zip")
    
    try:
        print("⬇️ 正在下载...")
        urllib.request.urlretrieve(download_url, zip_path)
        log_success("下载完成")
        
        print("📂 正在解压...")
        import zipfile
        with zipfile.ZipFile(zip_path, 'r') as zf:
            zf.extractall(tmpdir)
        
        # 查找解压后的二进制文件
        extracted_binary = os.path.join(tmpdir, TERRAFORM_BINARY_NAME)
        if not os.path.exists(extracted_binary):
            # 尝试不带 .exe 后缀
            extracted_binary = os.path.join(tmpdir, "terraform")
            if not os.path.exists(extracted_binary):
                log_error(f"解压后文件列表: {os.listdir(tmpdir)}")
                return None, tmpdir
        
        return extracted_binary, tmpdir
        
    except urllib.error.HTTPError as e:
        log_error(f"下载失败: HTTP {e.code}")
        return None, tmpdir
    except Exception as e:
        log_error(f"下载/解压失败: {e}")
        return None, tmpdir


def install_binary(binary_path: str, system_info: Dict) -> bool:
    """安装 Terraform 二进制文件"""
    install_dir = get_install_dir(system_info)
    target_path = install_dir / TERRAFORM_BINARY_NAME
    
    log_info(f"正在安装到 {target_path}...")
    
    try:
        install_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy(binary_path, target_path)
        
        # Linux/macOS 设置执行权限
        if not system_info["is_windows"]:
            os.chmod(target_path, 0o755)
        
        log_success("二进制安装完成")
        
        # Windows: 添加到 PATH
        if system_info["is_windows"]:
            add_to_windows_path(str(install_dir), system_info)
        
        return True
    except PermissionError:
        log_error("权限不足，请使用管理员权限运行")
        return False
    except Exception as e:
        log_error(f"安装失败: {e}")
        return False


def add_to_windows_path(path: str, system_info: Dict) -> bool:
    """添加到 Windows PATH 环境变量"""
    if not system_info["is_windows"]:
        return True
    
    log_info("配置 Windows PATH...")
    
    try:
        import winreg
        
        # 选择注册表位置
        if system_info["is_admin"]:
            # 系统级 PATH
            key = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment",
                0, winreg.KEY_SET_VALUE | winreg.KEY_READ
            )
        else:
            # 用户级 PATH
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Environment",
                0, winreg.KEY_SET_VALUE | winreg.KEY_READ
            )
        
        # 读取当前 PATH
        try:
            current_path, _ = winreg.QueryValueEx(key, "PATH")
        except:
            current_path = ""
        
        # 检查是否已存在
        if path.lower() not in current_path.lower():
            new_path = f"{current_path};{path}" if current_path else path
            winreg.SetValueEx(key, "PATH", 0, winreg.REG_EXPAND_SZ, new_path)
            log_success(f"已添加到 PATH: {path}")
            print("   ⚠️ 请重新打开终端使 PATH 生效")
        else:
            print(f"   PATH 已包含: {path}")
        
        winreg.CloseKey(key)
        return True
        
    except ImportError:
        log_warn("无法导入 winreg，请手动添加到 PATH")
        print(f"   手动添加: {path}")
        return False
    except Exception as e:
        log_warn(f"配置 PATH 失败: {e}")
        print(f"   请手动添加到 PATH: {path}")
        return False


def verify_installation(system_info: Dict) -> bool:
    """验证安装"""
    log_info("验证安装...")
    
    try:
        result = subprocess.run(
            ["terraform", "version"],
            capture_output=True,
            text=True,
            timeout=10,
            shell=system_info["is_windows"]
        )
        
        if result.returncode == 0:
            log_success("Terraform 安装成功!")
            print(f"   {result.stdout.strip()}")
            return True
        else:
            log_error(f"验证失败: {result.stderr}")
            return False
    except Exception as e:
        log_error(f"验证失败: {e}")
        return False


def uninstall_terraform(system_info: Dict) -> bool:
    """卸载 Terraform"""
    log_info("正在卸载 Terraform...")
    
    cleaned = False
    
    # Linux: 检查 APT 安装
    if system_info["is_debian"]:
        try:
            result = subprocess.run(
                ["dpkg", "-l", "terraform"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0 and "terraform" in result.stdout:
                print("  检测到 APT 安装，使用 apt-get 卸载...")
                subprocess.run(
                    ["apt-get", "remove", "-y", "terraform"],
                    capture_output=True
                )
                print("  ✅ 已通过 APT 卸载 terraform 包")
                cleaned = True
        except:
            pass
        
        # 清理 APT 相关文件
        gpg_keyring = "/usr/share/keyrings/hashicorp-archive-keyring.gpg"
        apt_source = "/etc/apt/sources.list.d/hashicorp.list"
        
        if os.path.exists(gpg_keyring):
            os.remove(gpg_keyring)
            print(f"  ✅ 已删除 GPG 密钥: {gpg_keyring}")
            cleaned = True
        
        if os.path.exists(apt_source):
            os.remove(apt_source)
            print(f"  ✅ 已删除 APT 源: {apt_source}")
            cleaned = True
    
    # Windows: 检查 Chocolatey/Scoop
    if system_info["is_windows"]:
        try:
            result = subprocess.run(
                ["choco", "uninstall", "terraform", "-y"],
                capture_output=True,
                text=True,
                timeout=60,
                shell=True
            )
            if result.returncode == 0:
                print("  ✅ 已通过 Chocolatey 卸载")
                cleaned = True
        except:
            pass
        
        try:
            result = subprocess.run(
                ["scoop", "uninstall", "terraform"],
                capture_output=True,
                text=True,
                timeout=60,
                shell=True
            )
            if result.returncode == 0:
                print("  ✅ 已通过 Scoop 卸载")
                cleaned = True
        except:
            pass
    
    # 删除二进制文件
    install_dir = get_install_dir(system_info)
    terraform_path = install_dir / TERRAFORM_BINARY_NAME
    if terraform_path.exists():
        terraform_path.unlink()
        print(f"  ✅ 已删除二进制: {terraform_path}")
        cleaned = True
    
    # 清理缓存
    providers_dir = get_providers_dir(system_info)
    if providers_dir.exists():
        shutil.rmtree(providers_dir)
        print(f"  ✅ 已清理 Provider: {providers_dir}")
        cleaned = True
    
    cache_dir = get_provider_cache_dir(system_info)
    if cache_dir.exists():
        shutil.rmtree(cache_dir)
        print(f"  ✅ 已清理缓存: {cache_dir}")
        cleaned = True
    
    # 清理配置文件
    terraformrc = get_terraformrc_path(system_info)
    if terraformrc.exists():
        terraformrc.unlink()
        print(f"  ✅ 已删除配置: {terraformrc}")
        cleaned = True
    
    if cleaned:
        log_success("卸载完成，环境已清理干净")
    else:
        log_warn("未发现需要清理的文件")
    
    return True


# ============================================================
# Provider 配置
# ============================================================

def setup_provider_cache(system_info: Dict) -> Path:
    """配置 Provider 缓存目录"""
    log_info("配置 Provider 缓存...")
    
    cache_dir = get_provider_cache_dir(system_info)
    cache_dir.mkdir(parents=True, exist_ok=True)
    print(f"   ✅ 缓存目录: {cache_dir}")
    
    os.environ["TF_PLUGIN_CACHE_DIR"] = str(cache_dir)
    
    if not system_info["is_windows"]:
        print(f"\n   💡 建议在 ~/.bashrc 或 ~/.zshrc 中添加:")
        print(f'      export TF_PLUGIN_CACHE_DIR="{cache_dir}"')
    else:
        print(f"\n   💡 建议在系统环境变量中添加:")
        print(f'      TF_PLUGIN_CACHE_DIR = "{cache_dir}"')
    
    return cache_dir


def setup_huawei_mirror(system_info: Dict) -> bool:
    """配置华为云镜像源（下载并安装 Provider）"""
    log_info("配置华为云镜像源...")
    
    # 获取最新 Provider 版本
    log_info("获取 Provider 版本...")
    try:
        req = urllib.request.Request(f"{HUAWEI_PROVIDER_INDEX}/")
        with urllib.request.urlopen(req, timeout=30) as resp:
            content = resp.read().decode('utf-8')
            import re
            versions = re.findall(r'href="(\d+\.\d+\.\d+)\.json"', content)
            if versions:
                provider_version = versions[-1]
                log_success(f"Provider 版本: {provider_version}")
            else:
                provider_version = "1.81.0"
    except Exception as e:
        log_warn(f"获取版本失败: {e}，使用默认版本 1.81.0")
        provider_version = "1.81.0"
    
    # 下载 Provider
    provider_url = f"{HUAWEI_PROVIDER_INDEX}/terraform-provider-huaweicloud_{provider_version}_{system_info['os']}_{system_info['arch']}.zip"
    log_info(f"下载 Provider: {provider_url}")
    
    try:
        tmpdir = tempfile.mkdtemp()
        zip_path = os.path.join(tmpdir, "provider.zip")
        urllib.request.urlretrieve(provider_url, zip_path)
        log_success("下载完成")
        
        # 创建 Provider 目录
        providers_dir = get_providers_dir(system_info)
        platform_str = f"{system_info['os']}_{system_info['arch']}"
        provider_dir = providers_dir / "registry.terraform.io" / "huaweicloud" / "huaweicloud" / provider_version / platform_str
        provider_dir.mkdir(parents=True, exist_ok=True)
        
        # 解压
        import zipfile
        with zipfile.ZipFile(zip_path, 'r') as zf:
            zf.extractall(provider_dir)
        
        # 设置 Provider 执行权限
        for provider_file in provider_dir.glob("terraform-provider-*"):
            os.chmod(provider_file, 0o755)
            log_info(f"设置权限: {provider_file.name}")
        
        log_success(f"Provider 安装完成: {provider_dir}")
        shutil.rmtree(tmpdir)
        
    except Exception as e:
        log_error(f"下载失败: {e}")
        return False
    
    # 配置 terraformrc
    terraformrc = get_terraformrc_path(system_info)
    providers_dir = get_providers_dir(system_info)
    
    # Windows 路径需要转义或使用正斜杠
    providers_path = str(providers_dir).replace('\\', '/')
    
    config_content = f'''provider_installation {{
  filesystem_mirror {{
    path    = "{providers_path}"
    include = ["registry.terraform.io/huaweicloud/*"]
  }}
  direct {{
    exclude = ["registry.terraform.io/huaweicloud/*"]
  }}
}}
'''
    
    try:
        if terraformrc.exists():
            backup = terraformrc.with_suffix(".backup")
            shutil.copy(terraformrc, backup)
            print(f"   已备份现有配置到: {backup}")
        
        terraformrc.write_text(config_content)
        log_success(f"CLI 配置: {terraformrc}")
        return True
    except Exception as e:
        log_error(f"配置失败: {e}")
        return False


# ============================================================
# 测试功能
# ============================================================

def run_terraform_init(workdir: Optional[str] = None, use_mirror: bool = True, system_info: Dict = None) -> bool:
    """运行 terraform init"""
    if system_info is None:
        system_info = get_system_info()
    
    log_info("运行 terraform init...")
    
    if workdir:
        os.chdir(workdir)
    
    tf_files = [f for f in os.listdir(".") if f.endswith(".tf")]
    if not tf_files:
        log_warn("当前目录没有 .tf 文件，跳过 init")
        return True
    
    print(f"   发现 {len(tf_files)} 个 .tf 文件")
    
    if use_mirror:
        setup_huawei_mirror(system_info)
    
    try:
        result = subprocess.run(
            ["terraform", "init"],
            capture_output=True,
            text=True,
            timeout=300,
            env=os.environ.copy(),
            shell=system_info["is_windows"]
        )
        
        if result.returncode == 0:
            log_success("terraform init 成功")
            return True
        else:
            log_error("terraform init 失败")
            print(result.stderr)
            return False
    except Exception as e:
        log_error(f"执行失败: {e}")
        return False


def test_provider(workdir: Optional[str] = None, system_info: Dict = None) -> bool:
    """测试 Provider 是否可用"""
    if system_info is None:
        system_info = get_system_info()
    
    log_info("测试 Provider 是否可用...")
    
    if workdir:
        test_dir = Path(workdir) / ".tf_test"
    else:
        test_dir = Path(tempfile.mkdtemp(prefix="tf_test_"))
    
    try:
        test_dir.mkdir(parents=True, exist_ok=True)
        (test_dir / "main.tf").write_text(TEST_TF_SCRIPT)
        print(f"   测试目录: {test_dir}")
        
        print("   1. 运行 terraform init...")
        result = subprocess.run(
            ["terraform", "init"],
            cwd=test_dir,
            capture_output=True,
            text=True,
            timeout=120,
            env=os.environ.copy(),
            shell=system_info["is_windows"]
        )
        
        if result.returncode != 0:
            log_error(f"init 失败: {result.stderr[:200]}")
            return False
        
        print("   ✅ init 成功")
        
        print("   2. 运行 terraform plan...")
        result = subprocess.run(
            ["terraform", "plan"],
            cwd=test_dir,
            capture_output=True,
            text=True,
            timeout=60,
            env=os.environ.copy(),
            shell=system_info["is_windows"]
        )
        
        if result.returncode != 0:
            if "AkSk" in result.stderr or "credentials" in result.stderr.lower():
                log_warn("Provider 可用，但未配置华为云认证")
                print("\n   💡 请配置华为云认证:")
                print("      export HUAWEICLOUD_ACCESS_KEY=xxx")
                print("      export HUAWEICLOUD_SECRET_KEY=xxx")
                return True
            else:
                log_error(f"plan 失败: {result.stderr[:200]}")
                return False
        
        log_success("Provider 测试成功")
        return True
        
    except Exception as e:
        log_error(f"测试失败: {e}")
        return False
    finally:
        if not workdir and test_dir.exists():
            shutil.rmtree(test_dir, ignore_errors=True)


# ============================================================
# 主函数
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="Terraform 环境安装脚本 (跨平台支持)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
    python3 install_terraform.py              # 自动安装（默认华为云镜像）
    python3 install_terraform.py --init       # 安装 + 初始化
    python3 install_terraform.py --test       # 安装 + 测试
    python3 install_terraform.py --no-mirror  # 使用官方源（需要网络畅通）
    python3 install_terraform.py --method apt      # 使用 APT 安装 (Linux)
    python3 install_terraform.py --method choco    # 使用 Chocolatey (Windows)
    python3 install_terraform.py --method scoop    # 使用 Scoop (Windows)
    python3 install_terraform.py --method binary   # 使用二进制下载
    python3 install_terraform.py --version 1.14.8  # 安装指定版本
    python3 install_terraform.py --check      # 仅检查安装状态
    python3 install_terraform.py --uninstall  # 卸载 Terraform
        """
    )
    
    parser.add_argument(
        "--method",
        choices=["apt", "choco", "scoop", "binary", "auto"],
        default="auto",
        help="安装方式: apt(Linux), choco(Windows Chocolatey), scoop(Windows Scoop), binary(二进制下载), auto(自动选择)"
    )
    parser.add_argument("--version", help="指定安装版本（仅 binary 方式有效）")
    parser.add_argument("--check", action="store_true", help="仅检查安装状态，不安装")
    parser.add_argument("--uninstall", action="store_true", help="卸载 Terraform")
    parser.add_argument("--init", action="store_true", help="安装后自动运行 terraform init")
    parser.add_argument("--test", action="store_true", help="安装后测试 Provider 是否可用")
    parser.add_argument("--dir", help="terraform init 的工作目录")
    parser.add_argument("--mirror", action="store_true", default=True, help="使用华为云镜像（默认启用）")
    parser.add_argument("--no-mirror", action="store_true", help="禁用华为云镜像，使用官方源")
    parser.add_argument("--no-color", action="store_true", help="禁用颜色输出")
    
    args = parser.parse_args()
    
    if args.no_color:
        Colors.disable()
    
    print("=" * 60)
    print("🏗️  Terraform 环境安装脚本 (跨平台)")
    print("=" * 60)
    
    # 获取系统信息
    system_info = get_system_info()
    print(f"🖥️  系统: {system_info['system']} {system_info['machine']}")
    print(f"   OS: {system_info['os']}, Arch: {system_info['arch']}")
    
    if system_info["is_windows"]:
        print(f"   平台: Windows")
        print(f"   管理员权限: {'是' if system_info['is_admin'] else '否'}")
    elif system_info["is_debian"]:
        print(f"   包管理器: APT (Debian/Ubuntu)")
    elif system_info["is_rhel"]:
        print(f"   包管理器: YUM/DNF (RHEL/CentOS)")
    
    install_dir = get_install_dir(system_info)
    print(f"   安装目录: {install_dir}")
    
    # 卸载模式
    if args.uninstall:
        uninstall_terraform(system_info)
        return 0
    
    # 检查安装状态
    installed, current_version = check_installation(system_info)
    
    if args.check:
        return 0 if installed else 1
    
    # 检查网络
    network = check_network()
    
    if not installed:
        # 确定安装方式
        method = args.method
        if method == "auto":
            if system_info["is_windows"]:
                # Windows: 直接使用 binary（跳过包管理器检测，避免超时）
                # 原因：scoop/choco 检测慢，binary 直接下载更快
                method = "binary"
                log_info("Windows: 使用 binary 方式（直接下载）")
            elif system_info["is_debian"]:
                method = "apt"
            else:
                method = "binary"
        
        print(f"\n📌 安装方式: {method}")
        
        tmpdir = None
        package_installed = False
        
        try:
            # 尝试包管理器安装
            if method == "apt":
                package_installed = install_via_apt(system_info)
            elif method == "choco":
                package_installed = install_via_chocolatey(system_info)
            elif method == "scoop":
                package_installed = install_via_scoop(system_info)
            
            # 包管理器失败或选择 binary，使用二进制下载
            if not package_installed:
                if method != "binary":
                    log_warn(f"{method} 安装失败，尝试二进制下载...")
                
                version = args.version if args.version else get_latest_version()
                binary_path, tmpdir = download_terraform(version, system_info)
                
                if not binary_path:
                    return 1
                
                if not install_binary(binary_path, system_info):
                    return 1
            
            # 验证
            if not verify_installation(system_info):
                return 1
            
        finally:
            if tmpdir and os.path.exists(tmpdir):
                shutil.rmtree(tmpdir)
    
    # 配置 Provider 缓存
    setup_provider_cache(system_info)
    
    # 配置华为云镜像
    use_mirror = args.mirror and not args.no_mirror
    if use_mirror:
        log_info("使用华为云镜像（默认）")
        setup_huawei_mirror(system_info)
    else:
        log_info("使用官方源（--no-mirror）")
    
    # 运行 terraform init
    if args.init:
        if not run_terraform_init(args.dir, use_mirror=use_mirror, system_info=system_info):
            return 1
    
    # 测试 Provider
    if args.test:
        if not test_provider(args.dir, system_info):
            return 1
    
    print("\n" + "=" * 60)
    print("🎉 完成！")
    print("=" * 60)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
