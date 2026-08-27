#!/usr/bin/env python3
"""Detect local OS and architecture, classify DevKit install support.

Usage:
    python detect_os.py

Output (stdout, one line per key=value):
    os_type=<Windows|openEuler|CentOS|Ubuntu|Kylin|UOS|EulerOS|Debian|SUSE|NeoKylin|macOS|unsupported>
    os_name=<full OS name>
    os_version=<OS version>
    arch=<x86_64|aarch64|AMD64|arm64>
    local_install_supported=<true|false>

Exit code: 0 on success, 1 on failure.
"""
import platform
import sys
import os


# DevKit-supported OS list for local installation
SUPPORTED_OS = {
    'openEuler': True,
    'CentOS': True,
    'Ubuntu': True,
    'Kylin': True,
    'UOS': True,
    'EulerOS': True,
    'Debian': True,
    'SUSE': True,
    'SLES': True,
    'NeoKylin': True,
}


def detect_os():
    """Detect OS type, name, version, architecture, and DevKit local install support."""
    system = platform.system()
    machine = platform.machine()

    # Normalize architecture
    arch_map = {
        'AMD64': 'x86_64',
        'x86_64': 'x86_64',
        'aarch64': 'aarch64',
        'arm64': 'aarch64',
        'i386': 'x86_64',
        'i686': 'x86_64',
    }
    arch = arch_map.get(machine, machine)

    if system == 'Windows':
        # Windows detection via platform
        version = platform.version()
        # Try to get Windows product name (e.g., "Windows Server 2019 Standard")
        os_name = 'Windows'
        try:
            import winreg
            with winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r'SOFTWARE\Microsoft\Windows NT\CurrentVersion'
            ) as key:
                try:
                    os_name, _ = winreg.QueryValueEx(key, 'ProductName')
                except FileNotFoundError:
                    pass
        except Exception:
            pass
        return {
            'os_type': 'Windows',
            'os_name': os_name,
            'os_version': version,
            'arch': arch,
            'local_install_supported': False,
        }

    elif system == 'Darwin':
        # macOS
        os_name = 'macOS'
        os_version = platform.mac_ver()[0]
        return {
            'os_type': 'macOS',
            'os_name': os_name,
            'os_version': os_version,
            'arch': arch,
            'local_install_supported': False,
        }

    elif system == 'Linux':
        # Linux detection: read /etc/os-release
        os_name = 'Linux'
        os_version = ''
        os_id = ''

        # Method 1: /etc/os-release (standard)
        try:
            with open('/etc/os-release') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('ID='):
                        os_id = line.split('=', 1)[1].strip('"')
                    elif line.startswith('NAME='):
                        os_name = line.split('=', 1)[1].strip('"')
                    elif line.startswith('VERSION_ID='):
                        os_version = line.split('=', 1)[1].strip('"')
        except FileNotFoundError:
            pass

        # Method 2: fallback to platform.linux_distribution() or /etc/<distro>-release
        if not os_id:
            try:
                # Python 3.8+ removed linux_distribution, try custom parsing
                for release_file in ['/etc/redhat-release', '/etc/centos-release',
                                     '/etc/openEuler-release', '/etc/kylin-release',
                                     '/etc/uos-release', '/etc/debian_version',
                                     '/etc/SuSE-release']:
                    if os.path.exists(release_file):
                        with open(release_file) as f:
                            content = f.read().strip()
                        os_name = content
                        # Extract ID from release file name
                        basename = os.path.basename(release_file).replace('-release', '').replace('_version', '')
                        os_id = basename
                        break
            except Exception:
                pass

        # Classify OS type
        os_type = 'unsupported'
        for supported_id in SUPPORTED_OS:
            if supported_id.lower() in os_id.lower() or supported_id.lower() in os_name.lower():
                os_type = supported_id
                break

        return {
            'os_type': os_type,
            'os_name': os_name,
            'os_version': os_version,
            'arch': arch,
            'local_install_supported': SUPPORTED_OS.get(os_type, False),
        }

    else:
        return {
            'os_type': 'unsupported',
            'os_name': system,
            'os_version': platform.release(),
            'arch': arch,
            'local_install_supported': False,
        }


def main():
    result = detect_os()
    # Output as key=value lines for easy parsing
    for key, value in result.items():
        print("{0}={1}".format(key, value))
    return 0


if __name__ == '__main__':
    sys.exit(main())
