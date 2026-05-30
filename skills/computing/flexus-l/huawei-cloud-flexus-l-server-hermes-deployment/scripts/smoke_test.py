#!/usr/bin/env python3
# coding: utf-8
"""
Hermes 技能冒烟测试脚本

测试内容:
1. 验证核心功能模块导入正常
2. 验证脚本内容获取功能
3. 验证参数校验功能
4. 验证目录结构完整性
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest
import warnings


class TestHermesSmoke(unittest.TestCase):
    """Hermes 技能冒烟测试用例"""

    def test_import_lib(self):
        """测试 lib 模块导入"""
        try:
            from scripts import lib
            self.assertIsNotNone(lib)
            print("✓ lib 模块导入成功")
        except ImportError as e:
            self.fail(f"✗ lib 模块导入失败: {e}")

    def test_get_hermes_script_content(self):
        """测试获取内置脚本内容"""
        from scripts.lib import get_hermes_script_content
        content = get_hermes_script_content()
        self.assertIsInstance(content, str)
        self.assertGreater(len(content), 0)
        self.assertIn("Hermes 配置工具", content)
        self.assertIn("feishu", content)
        self.assertIn("wecom", content)
        print("✓ 内置脚本内容获取成功")

    def test_default_config(self):
        """测试默认配置常量"""
        from scripts.lib import DEFAULT_BASE_URL, DEFAULT_CONFIG_PATH, DEFAULT_ENV_PATH
        self.assertEqual(DEFAULT_BASE_URL, "https://api.modelarts-maas.com/v2")
        self.assertEqual(DEFAULT_CONFIG_PATH, "/home/hermes/.hermes/config.yaml")
        self.assertEqual(DEFAULT_ENV_PATH, "/home/hermes/.hermes/.env")
        print("✓ 默认配置常量验证成功")

    def test_valid_script_types(self):
        """测试脚本类型常量"""
        from scripts.lib import VALID_SCRIPT_TYPES, VALID_RISK_LEVELS, VALID_ROTATION_STRATEGIES
        self.assertIn("SHELL", VALID_SCRIPT_TYPES)
        self.assertIn("PYTHON", VALID_SCRIPT_TYPES)
        self.assertIn("BAT", VALID_SCRIPT_TYPES)
        self.assertIn("LOW", VALID_RISK_LEVELS)
        self.assertIn("MEDIUM", VALID_RISK_LEVELS)
        self.assertIn("HIGH", VALID_RISK_LEVELS)
        self.assertIn("CONTINUE", VALID_ROTATION_STRATEGIES)
        self.assertIn("STOP", VALID_ROTATION_STRATEGIES)
        print("✓ 常量验证成功")

    def test_error_function(self):
        """测试错误响应函数"""
        from scripts.lib import _error
        result = _error("TEST_ERROR", "test message")
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["code"], "TEST_ERROR")
        self.assertEqual(result["error"]["message"], "test message")
        print("✓ 错误响应函数测试成功")

    def test_directory_structure(self):
        """测试目录结构完整性"""
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        required_files = [
            "_meta.json",
            "requirements.txt",
            "scripts/lib.py",
            "scripts/caller.py",
            "scripts/smoke_test.py"
        ]
        
        for rel_path in required_files:
            full_path = os.path.join(base_dir, rel_path)
            self.assertTrue(os.path.exists(full_path), f"缺少文件: {rel_path}")
        
        print("✓ 目录结构完整性验证成功")

    def test_caller_import(self):
        """测试 caller 模块导入"""
        try:
            from scripts import caller
            self.assertIsNotNone(caller)
            print("✓ caller 模块导入成功")
        except ImportError as e:
            self.fail(f"✗ caller 模块导入失败: {e}")


def run_tests():
    """运行冒烟测试"""
    print("=" * 60)
    print("Hermes 技能冒烟测试")
    print("=" * 60)
    print("\n正在执行测试...\n")

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=DeprecationWarning)
        warnings.simplefilter("ignore", category=PendingDeprecationWarning)
        
        loader = unittest.TestLoader()
        suite = loader.loadTestsFromTestCase(TestHermesSmoke)
        
        runner = unittest.TextTestRunner(verbosity=1)
        result = runner.run(suite)

    print("\n" + "=" * 60)
    if result.wasSuccessful():
        print("✓ 所有测试通过!")
        print("=" * 60)
        return 0
    else:
        print("✗ 部分测试失败")
        print("=" * 60)
        return 1


if __name__ == '__main__':
    sys.exit(run_tests())