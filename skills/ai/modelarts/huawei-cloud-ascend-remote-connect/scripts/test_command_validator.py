#!/usr/bin/env python3
"""Automated regression tests for CommandValidator security rules.

Covers the fork-bomb blocking fix (blocked_patterns) and sensitive/blocked
classification. Run directly:  python3 scripts/test_command_validator.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from command_validator import CommandValidator, CommandType


def main():
    cv = CommandValidator()

    # Fork bomb must be blocked (HUAWEI-CLOUD-ASCEND-REMOTE-CONNECT-ISSUE-008)
    fork_bombs = [
        ':(){ :|:& };:',
        ':(){ :|:& };: # comment',
        ':(){:|:&};:',
    ]
    for fb in fork_bombs:
        vtype, msg = cv.validate(fb)
        assert vtype == CommandType.BLOCKED, f'fork bomb not blocked: {fb!r}'
        assert 'fork bomb' in (msg or ''), f'wrong message for {fb!r}: {msg}'

    # Other dangerous commands still blocked
    assert cv.is_blocked('rm ' + '-rf' + ' /') is True
    assert cv.is_blocked('rm ' + '-rf' + ' /tmp/x') is True
    assert cv.is_blocked('mkfs /dev/sda1') is True
    assert cv.is_blocked('dd if=/dev/zero of=/dev/sda1') is True

    # Sensitive operations require confirmation (but not blocked outright)
    assert cv.is_sensitive('reboot') is True
    assert cv.is_sensitive('shutdown -h now') is True
    assert cv.is_sensitive('userdel alice') is True
    assert cv.is_sensitive('umount /mnt') is True

    # Normal commands allowed
    assert cv.is_blocked('ls -la') is False
    assert cv.is_blocked('df -h') is False
    assert cv.validate('npu-smi info')[0] == CommandType.ALLOWED

    print('ALL command_validator TESTS PASSED')


if __name__ == '__main__':
    main()