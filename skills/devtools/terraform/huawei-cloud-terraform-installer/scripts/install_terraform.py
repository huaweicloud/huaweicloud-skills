#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Terraform 环境安装脚本
支持多平台：Linux, Windows
使用二进制下载方式安装，优先使用华为云镜像源

参考文档: https://developer.hashicorp.com/terraform/install

前置要求:
    Python 3.6+

使用方法:
    python3 install_terraform.py              # 安装最新版本（默认华为云镜像）
    python3 install_terraform.py --init       # 安装后自动运行 terraform init
    python3 install_terraform.py --test       # 安装后测试 Provider 是否可用
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
# Windows 编码修复（必须在所有输出之前）
# ============================================================

if sys.platform == 'win32':
    import io
    # 修复 Windows 控制台编码问题
    if sys.stdout.encoding != 'utf-8':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    if sys.stderr.encoding != 'utf-8':
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

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

# 默认版本（定期手动更新）
DEFAULT_TERRAFORM_VERSION = "1.15.2"
DEFAULT_PROVIDER_VERSION = "1.90.0"

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
    """输出信息"""
    print(f"{Colors.BLUE}[INFO]{Colors.RESET} {msg}")


def log_success(msg: str):
    """输出成功信息"""
    print(f"{Colors.GREEN}[SUCCESS]{Colors.RESET} {msg}")


def log_warn(msg: str):
    """输出警告信息"""
    print(f"{Colors.YELLOW}[WARN]{Colors.RESET} {msg}")


def log_error(msg: str):
    """输出错误信息"""
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
        "windows": "windows",
    }

    # macOS 不支持检查
    if system == "darwin":
        print(f"\033[91m[ERROR]\033[0m macOS is not currently supported")
        print(f"\033[91m[ERROR]\033[0m Supported platforms: Linux, Windows")
        sys.exit(1)

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
            return Path(os.environ.get("PROGRAMFILES", "C:\\Program Files")) / "Terraform"
        else:
            return Path(os.environ.get("LOCALAPPDATA", os.path.expanduser("~\\AppData\\Local"))) / "Terraform"
    else:
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
# 版本检测
# ============================================================

def get_latest_version() -> str:
    """获取最新版本号"""
    log_info("正在查询版本...")

    # 方案 1: HashiCorp Releases API（优先）
    try:
        req = urllib.request.Request("https://releases.hashicorp.com/terraform/index.json")
        with urllib.request.urlopen(req, timeout=15) as response:
            data = json.loads(response.read().decode())
            versions = list(data.get("versions", {}).keys())
            # 过滤掉预发布版本（包含 - 的版本）
            stable_versions = [v for v in versions if '-' not in v]

            # 使用最新稳定版本
            if stable_versions:
                version = stable_versions[-1]
                log_success(f"使用最新稳定版本: {version} (HashiCorp Releases)")
                return version
    except Exception as e:
        log_warn(f"HashiCorp Releases 获取失败: {e}")

    # 方案 2: GitHub API（备选）
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

    # 方案 3: 使用固定稳定版本
    log_success(f"使用固定稳定版本: {DEFAULT_TERRAFORM_VERSION}")
    return DEFAULT_TERRAFORM_VERSION


# ============================================================
# 安装检查
# ============================================================

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


# ============================================================
# 下载和安装
# ============================================================

def download_terraform(version: str, system_info: Dict) -> Tuple[Optional[str], Optional[str]]:
    """下载 Terraform 二进制文件"""
    tmpdir = tempfile.mkdtemp()
    zip_path = os.path.join(tmpdir, "terraform.zip")

    # Windows: 使用固定的下载链接
    if system_info["is_windows"]:
        download_url = "https://releases.hashicorp.com/terraform/1.15.2/terraform_1.15.2_windows_amd64.zip"
        log_info("Windows 使用固定下载链接")
    else:
        # Linux: 从 HashiCorp 官方源下载
        download_url = TERRAFORM_DOWNLOAD_URL.format(
            version=version,
            os=system_info["os"],
            arch=system_info["arch"]
        )

    log_info(f"下载地址: {download_url}")

    try:
        print("正在下载...")
        urllib.request.urlretrieve(download_url, zip_path)
        log_success("下载完成")
        
        # 验证下载的文件
        if not os.path.exists(zip_path):
            log_error("下载文件不存在")
            return None, tmpdir
        
        file_size = os.path.getsize(zip_path)
        log_info(f"下载文件大小: {file_size / 1024 / 1024:.2f} MB")

        print("正在解压...")
        import zipfile
        with zipfile.ZipFile(zip_path, 'r') as zf:
            # 打印压缩包内容
            file_list = zf.namelist()
            log_info(f"压缩包内容: {file_list}")
            zf.extractall(tmpdir)

        # 列出解压后的所有文件
        extracted_files = os.listdir(tmpdir)
        log_info(f"解压后文件列表: {extracted_files}")

        # 查找解压后的二进制文件
        extracted_binary = os.path.join(tmpdir, TERRAFORM_BINARY_NAME)
        if not os.path.exists(extracted_binary):
            # 尝试不带 .exe 后缀
            extracted_binary = os.path.join(tmpdir, "terraform")
            if not os.path.exists(extracted_binary):
                # 尝试在子目录中查找
                for root, dirs, files in os.walk(tmpdir):
                    for file in files:
                        if file == TERRAFORM_BINARY_NAME or file == "terraform":
                            extracted_binary = os.path.join(root, file)
                            log_info(f"在子目录找到: {extracted_binary}")
                            break
                    if os.path.exists(extracted_binary):
                        break
                
                if not os.path.exists(extracted_binary):
                    log_error("找不到 Terraform 二进制文件")
                    log_error(f"解压目录内容: {extracted_files}")
                    return None, tmpdir

        log_success(f"找到二进制文件: {extracted_binary}")
        return extracted_binary, tmpdir

    except urllib.error.HTTPError as e:
        log_error(f"下载失败: HTTP {e.code}")
        return None, tmpdir
    except zipfile.BadZipFile as e:
        log_error(f"压缩文件损坏: {e}")
        return None, tmpdir
    except Exception as e:
        log_error(f"下载/解压失败: {e}")
        import traceback
        traceback.print_exc()
        return None, tmpdir


def install_binary(binary_path: str, system_info: Dict) -> bool:
    """安装 Terraform 二进制文件"""
    install_dir = get_install_dir(system_info)
    target_path = install_dir / TERRAFORM_BINARY_NAME

    log_info(f"正在安装到 {target_path}...")

    try:
        install_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy(binary_path, target_path)

        # Linux 设置执行权限
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

        # 规范化路径（统一使用反斜杠）
        normalized_path = path.replace('/', '\\')
        
        # 检查是否已存在（规范化比较）
        path_list = current_path.split(';')
        for existing_path in path_list:
            # 规范化现有路径
            normalized_existing = existing_path.strip().replace('/', '\\')
            if normalized_existing.lower() == normalized_path.lower():
                log_success("PATH 已包含安装目录")
                winreg.CloseKey(key)
                return True

        # 添加到 PATH
        new_path = f"{current_path};{normalized_path}" if current_path else normalized_path
        winreg.SetValueEx(key, "PATH", 0, winreg.REG_EXPAND_SZ, new_path)
        winreg.CloseKey(key)

        log_success(f"已添加到 PATH: {normalized_path}")
        log_warn("请重新打开终端使 PATH 生效")
        return True

    except Exception as e:
        log_error(f"配置 PATH 失败: {e}")
        log_warn(f"请手动添加到 PATH: {path}")
        return False


# ============================================================
# Provider 安装
# ============================================================

def install_provider(system_info: Dict) -> bool:
    """安装 HuaweiCloud Provider"""
    log_info("正在安装 HuaweiCloud Provider...")

    # 获取 Provider 版本
    provider_version = DEFAULT_PROVIDER_VERSION

    try:
        req = urllib.request.Request(f"{HUAWEI_PROVIDER_INDEX}/")
        with urllib.request.urlopen(req, timeout=30) as resp:
            content = resp.read().decode('utf-8')
            import re
            versions = re.findall(r'href="(\d+\.\d+\.\d+)\.json"', content)
            if versions:
                provider_version = versions[-1]
                log_success(f"Provider 版本: {provider_version}")
    except Exception as e:
        log_warn(f"获取版本失败: {e}，使用默认版本 {DEFAULT_PROVIDER_VERSION}")

    # 下载 Provider
    provider_url = f"{HUAWEI_PROVIDER_INDEX}/terraform-provider-huaweicloud_{provider_version}_{system_info['os']}_{system_info['arch']}.zip"
    log_info(f"下载 Provider: {provider_url}")

    tmpdir = tempfile.mkdtemp()
    zip_path = os.path.join(tmpdir, "provider.zip")

    try:
        urllib.request.urlretrieve(provider_url, zip_path)
        log_success("下载完成")
        
        # 验证下载文件
        file_size = os.path.getsize(zip_path)
        log_info(f"下载文件大小: {file_size / 1024 / 1024:.2f} MB")

        # 创建 Provider 目录
        providers_dir = get_providers_dir(system_info)
        platform_str = f"{system_info['os']}_{system_info['arch']}"
        provider_dir = providers_dir / "registry.terraform.io" / "huaweicloud" / "huaweicloud" / provider_version / platform_str
        
        log_info(f"Provider 安装目录: {provider_dir}")
        provider_dir.mkdir(parents=True, exist_ok=True)

        # 解压
        import zipfile
        with zipfile.ZipFile(zip_path, 'r') as zf:
            # 打印压缩包内容
            file_list = zf.namelist()
            log_info(f"压缩包内容: {file_list}")
            zf.extractall(provider_dir)

        # 列出解压后的文件
        extracted_files = list(provider_dir.iterdir())
        log_success(f"Provider 安装完成，文件数量: {len(extracted_files)}")
        
        # 清理临时目录
        shutil.rmtree(tmpdir)

    except Exception as e:
        log_error(f"下载失败: {e}")
        if os.path.exists(tmpdir):
            shutil.rmtree(tmpdir)
        return False

    # 配置 terraformrc
    terraformrc = get_terraformrc_path(system_info)
    providers_dir = get_providers_dir(system_info)

    # Windows 路径需要转义或使用正斜杠
    providers_path = str(providers_dir).replace('\\', '/')
    
    log_info(f"terraformrc 路径: {terraformrc}")
    log_info(f"Provider 路径: {providers_path}")

    content = f'''provider_installation {{
  filesystem_mirror {{
    path    = "{providers_path}"
    include = ["*/*/*"]
  }}
  direct {{
    exclude = ["*/*/*"]
  }}
}}
'''

    terraformrc.write_text(content, encoding='utf-8')
    log_success(f"已配置 terraformrc: {terraformrc}")

    return True


def test_provider(system_info: Dict) -> bool:
    """测试 Provider 是否可用"""
    log_info("测试 Provider 是否可用...")
    
    # 创建临时测试目录
    test_dir = tempfile.mkdtemp()
    
    # 创建最小化的 Terraform 配置
    test_tf = '''terraform {
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

# 最小化测试：仅声明一个数据源
data "huaweicloud_vpcs" "test" {}

output "test_result" {
  value = "Provider test successful"
}
'''
    
    # 写入测试文件
    test_file = Path(test_dir) / "main.tf"
    test_file.write_text(test_tf, encoding='utf-8')
    
    log_info(f"测试目录: {test_dir}")
    log_info("运行 terraform init...")
    
    try:
        # 运行 terraform init
        result = subprocess.run(
            ["terraform", "init"],
            cwd=test_dir,
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode == 0:
            log_success("terraform init 成功")
            log_info("Provider 测试通过")
            
            # 清理测试目录
            shutil.rmtree(test_dir)
            return True
        else:
            log_error(f"terraform init 失败")
            log_error(f"错误输出: {result.stderr}")
            
            # 清理测试目录
            shutil.rmtree(test_dir)
            return False
            
    except subprocess.TimeoutExpired:
        log_error("terraform init 超时")
        shutil.rmtree(test_dir)
        return False
    except FileNotFoundError:
        log_error("terraform 命令未找到，请确认 Terraform 已安装并在 PATH 中")
        shutil.rmtree(test_dir)
        return False
    except Exception as e:
        log_error(f"测试失败: {e}")
        shutil.rmtree(test_dir)
        return False


# ============================================================
# 主流程
# ============================================================

def main():
    # Python 版本检查
    if sys.version_info < (3, 6):
        print("[ERROR] Python 3.6+ is required")
        print(f"[INFO] Current version: {sys.version}")
        sys.exit(1)
    
    parser = argparse.ArgumentParser(description="Terraform 环境安装助手")
    parser.add_argument("--version", help="Terraform 版本")
    parser.add_argument("--init", action="store_true", help="安装后运行 terraform init")
    parser.add_argument("--test", action="store_true", help="安装后测试 Provider")
    parser.add_argument("--mirror", action="store_true", default=True, help="使用华为云镜像")
    parser.add_argument("--no-mirror", action="store_true", help="禁用镜像")
    parser.add_argument("--check", action="store_true", help="仅检查安装状态")
    parser.add_argument("--test-provider", action="store_true", help="测试 Provider 是否可用")
    parser.add_argument("--uninstall", action="store_true", help="卸载 Terraform")

    args = parser.parse_args()

    # 禁用颜色（如果需要）
    if not sys.stdout.isatty():
        Colors.disable()

    print()
    print("=" * 60)
    print("  Terraform 环境安装助手")
    print("=" * 60)
    print()

    # 获取系统信息
    system_info = get_system_info()

    log_info(f"系统: {system_info['system']} {system_info['machine']}")
    log_info(f"架构: {system_info['arch']}")
    log_info(f"管理员权限: {'是' if system_info['is_admin'] else '否'}")
    print()

    # 仅检查
    if args.check:
        check_installation(system_info)
        return

    # 测试 Provider
    if args.test_provider:
        test_provider(system_info)
        return

    # 卸载
    if args.uninstall:
        log_info("卸载 Terraform...")
        install_dir = get_install_dir(system_info)
        terraform_path = install_dir / TERRAFORM_BINARY_NAME

        if terraform_path.exists():
            terraform_path.unlink()
            log_success(f"已删除: {terraform_path}")
        else:
            log_warn("Terraform 未安装")

        # 清理配置
        terraformrc = get_terraformrc_path(system_info)
        if terraformrc.exists():
            terraformrc.unlink()
            log_success(f"已删除配置: {terraformrc}")

        providers_dir = get_providers_dir(system_info)
        if providers_dir.exists():
            shutil.rmtree(providers_dir)
            log_success(f"已清理 Provider: {providers_dir}")

        return

    # 检查是否已安装
    installed, installed_version = check_installation(system_info)
    if installed:
        log_warn("Terraform 已安装，跳过安装")
        if args.test:
            # TODO: 测试 Provider
            pass
        return

    # 获取版本
    version = args.version if args.version else get_latest_version()

    log_info(f"准备安装 Terraform {version}")
    print()

    # 下载
    binary_path, tmpdir = download_terraform(version, system_info)
    if not binary_path:
        log_error("下载失败")
        return

    # 安装
    if not install_binary(binary_path, system_info):
        log_error("安装失败")
        if tmpdir:
            shutil.rmtree(tmpdir)
        return

    # 清理临时目录
    if tmpdir:
        shutil.rmtree(tmpdir)

    # 安装 Provider
    if args.mirror and not args.no_mirror:
        print()
        if install_provider(system_info):
            # 测试 Provider（仅非 Windows 或已确认 PATH 生效）
            if not system_info["is_windows"]:
                print()
                log_info("测试 Provider...")
                test_provider(system_info)
            else:
                print()
                log_warn("Windows 下需要重新打开终端后才能测试 Provider")
                log_info("测试方法: 在新终端中运行 'terraform init'")

    # 完成
    print()
    print("=" * 60)
    log_success("安装完成！")
    print("=" * 60)
    print()
    
    # Windows 特殊提示
    if system_info["is_windows"]:
        print("[重要提示] Windows PATH 环境变量已更新")
        print("[必须操作] 请关闭当前终端/Shell，然后重新打开")
        print("[原因说明] Windows 环境变量更新需要重新打开终端才能生效")
        print()
        print("Agent 操作指引:")
        print("  1. 关闭当前 Shell 会话")
        print("  2. 打开新的 Shell 会话")
        print("  3. 运行: terraform version")
        print("  4. 运行: terraform init")
        print()
        print("如果不想重新打开终端，可以使用完整路径:")
        install_dir = get_install_dir(system_info)
        print(f"  {install_dir}\\terraform.exe version")
    else:
        print("下一步:")
        print("  1. 运行: terraform version")
        print("  2. 运行: terraform init")
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n用户取消")
        sys.exit(1)
    except Exception as e:
        log_error(f"未知错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
