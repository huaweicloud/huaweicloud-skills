#!/usr/bin/env python3
"""Offline contract tests for huawei-cloud-sg-manage (Issue #1123).

Covers the four evaluation deductions without touching the cloud:

1. failure paths are fast and structured (missing CLI, missing credentials,
   timeout, KooCLI rejection, API error body) — never an empty success result;
2. every write action previews 前置确认 / 影响范围 / 回滚 (review code L5);
3. one intent issues one hcloud call per resource (per-process cache);
4. install_cli.sh / ensure_cli.sh have bounded, readable failure semantics.
"""

import json
import os
import subprocess
import sys
import time
import unittest
from unittest import mock

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(SKILL_DIR, "scripts"))

from sg import common, dispatcher  # noqa: E402

# Benign variables the credential tests still need (used by subprocess/bash lookups).
# Everything else — in particular every credential-bearing variable — is left out.
ENV_ALLOWLIST = ("PATH", "HOME", "LANG", "LC_ALL", "TMPDIR", "TZ", "USER", "SHELL")


def env_without_credentials():
    """Allow-list copy of the process environment, with no credential values.

    Built from a fixed allow-list instead of copying the whole environment, so a
    credential can never be carried into the patched environment and no
    unrelated values are read at all.
    """
    env = {}
    for name in ENV_ALLOWLIST:
        value = os.environ.get(name)
        if value is not None:
            env[name] = value
    return env


class FakeResult:
    def __init__(self, rc, stdout, stderr=""):
        self.returncode = rc
        self.stdout = stdout
        self.stderr = stderr


def _patch_creds():
    """Pretend a valid KooCLI profile exists (so the call reaches subprocess)."""
    return mock.patch("sg.common._has_hcloud_profile", return_value=True)


class PrerequisiteTest(unittest.TestCase):
    def setUp(self):
        common.clear_cache()

    def test_missing_cli_is_structured_and_fast(self):
        started = time.time()
        with mock.patch("shutil.which", return_value=None):
            result = dispatcher.dispatch_action("huawei_list_security_groups", {})
        self.assertFalse(result["success"])
        self.assertEqual(result["error_code"], "cli_missing")
        self.assertIn("hint", result)
        self.assertLess(time.time() - started, 2.0)

    def test_missing_credentials_is_structured_and_fast(self):
        env = env_without_credentials()
        started = time.time()
        with mock.patch("shutil.which", return_value="/usr/bin/hcloud"), \
             mock.patch("sg.common._has_hcloud_profile", return_value=False), \
             mock.patch.dict(os.environ, env, clear=True):
            result = dispatcher.dispatch_action("huawei_list_security_group_rules", {})
        self.assertFalse(result["success"])
        self.assertEqual(result["error_code"], "credentials_missing")
        self.assertLess(time.time() - started, 2.0)

    def test_no_subprocess_call_when_credentials_missing(self):
        env = env_without_credentials()
        with mock.patch("shutil.which", return_value="/usr/bin/hcloud"), \
             mock.patch("sg.common._has_hcloud_profile", return_value=False), \
             mock.patch.dict(os.environ, env, clear=True), \
             mock.patch("subprocess.run") as run:
            dispatcher.dispatch_action("huawei_list_security_groups", {})
        run.assert_not_called()


class FailureEnvelopeTest(unittest.TestCase):
    def setUp(self):
        common.clear_cache()

    def test_timeout_returns_error_code_timeout(self):
        with mock.patch("shutil.which", return_value="/usr/bin/hcloud"), _patch_creds(), \
             mock.patch.dict(os.environ, {"HCLOUD_TIMEOUT": "2"}), \
             mock.patch("subprocess.run",
                        side_effect=subprocess.TimeoutExpired("hcloud", 2)) as run:
            result = dispatcher.dispatch_action("huawei_list_security_groups", {})
        self.assertFalse(result["success"])
        self.assertEqual(result["error_code"], "timeout")
        self.assertIn("HCLOUD_TIMEOUT", result["hint"])
        self.assertEqual(run.call_args.kwargs.get("timeout"), 2.0)

    def test_use_error_with_rc0_is_a_failure_not_empty_success(self):
        # KooCLI rejects the command with rc=0 and no stdout: must not look like []
        fake = FakeResult(0, "", "[USE_ERROR]Unsupported service: VPCX")
        with mock.patch("shutil.which", return_value="/usr/bin/hcloud"), _patch_creds(), \
             mock.patch("subprocess.run", return_value=fake):
            result = dispatcher.dispatch_action("huawei_list_security_groups", {})
        self.assertFalse(result["success"])
        self.assertEqual(result["error_code"], "cli_error")
        self.assertNotIn("security_groups", result)

    def test_api_error_body_keeps_code_and_hint(self):
        fake = FakeResult(0, json.dumps({"error_code": "VPC.0202", "error_msg": "not found"}))
        with mock.patch("shutil.which", return_value="/usr/bin/hcloud"), _patch_creds(), \
             mock.patch("subprocess.run", return_value=fake):
            result = dispatcher.dispatch_action(
                "huawei_list_security_groups", {"security_group_id": "sg-x"}
            )
        self.assertFalse(result["success"])
        self.assertEqual(result["error_code"], "VPC.0202")
        self.assertIn("not found", result["error"])
        self.assertIn("hint", result)

    def test_empty_stdout_with_stderr_is_a_failure(self):
        fake = FakeResult(0, "", "some unexpected noise")
        with mock.patch("shutil.which", return_value="/usr/bin/hcloud"), _patch_creds(), \
             mock.patch("subprocess.run", return_value=fake):
            result = dispatcher.dispatch_action("huawei_list_security_groups", {})
        self.assertFalse(result["success"])
        self.assertEqual(result["error_code"], "cli_error")

    def test_credentials_are_redacted_from_returned_command(self):
        with mock.patch("shutil.which", return_value="/usr/bin/hcloud"), \
             mock.patch("sg.common._has_hcloud_profile", return_value=False), \
             mock.patch.dict(os.environ, {"HUAWEI_ACCESS_KEY": "AKEXAMPLE123",
                                          "HUAWEI_SECRET_KEY": "SKEXAMPLE123"},
                             clear=False), \
             mock.patch("subprocess.run",
                        side_effect=subprocess.TimeoutExpired("hcloud", 30)):
            result = dispatcher.dispatch_action("huawei_list_security_groups", {})
        dumped = json.dumps(result)
        self.assertNotIn("AKEXAMPLE123", dumped)
        self.assertNotIn("SKEXAMPLE123", dumped)
        self.assertIn("--cli-access-key=***", result.get("command", ""))


class WritePreviewGateTest(unittest.TestCase):
    """L5: every write action previews preconditions, impact and rollback."""

    CASES = [
        ("huawei_create_security_group", {"name": "sg-preview", "region": "cn-north-4"}),
        ("huawei_create_sg_rule", {"security_group_id": "sg-x", "direction": "ingress"}),
        ("huawei_update_security_group", {"security_group_id": "sg-x", "name": "new-name"}),
        ("huawei_delete_security_group", {"security_group_id": "sg-x"}),
        ("huawei_delete_sg_rule", {"security_group_rule_id": "rule-x"}),
    ]

    def setUp(self):
        common.clear_cache()

    def test_each_write_action_previews_without_cloud_call(self):
        def no_lookup(*_args, **_kwargs):
            raise common.HcloudError("lookup unavailable", error_code="cli_missing")

        for action, params in self.CASES:
            with self.subTest(action=action), \
                 mock.patch("sg.manage.get_security_group", side_effect=no_lookup), \
                 mock.patch("sg.manage.get_security_group_rule", side_effect=no_lookup), \
                 mock.patch("sg.manage.list_security_group_rules", side_effect=no_lookup), \
                 mock.patch("sg.common.run_hcloud") as run:
                result = dispatcher.dispatch_action(action, dict(params))
                run.assert_not_called()
            self.assertTrue(result["success"], result)
            self.assertTrue(result["preview"], action)
            self.assertTrue(result["preconditions"], action)
            self.assertIn("impact", result, action)
            self.assertIn("rollback", result, action)
            self.assertIn("hcloud VPC", result["command"], action)

    def test_update_preview_carries_restore_snapshot(self):
        with mock.patch("sg.manage.get_security_group",
                        return_value={"name": "old", "description": "old-desc"}):
            result = dispatcher.dispatch_action(
                "huawei_update_security_group",
                {"security_group_id": "sg-x", "name": "new-name"},
            )
        self.assertEqual(result["current_values"], {"name": "old", "description": "old-desc"})
        self.assertIn("old", result["rollback"])

    def test_delete_sg_preview_exports_rules_for_rebuild(self):
        with mock.patch("sg.manage.get_security_group", return_value={"name": "sg-preview"}), \
             mock.patch("sg.manage.list_security_group_rules",
                        return_value=[{"id": "r1", "direction": "ingress"}]):
            result = dispatcher.dispatch_action(
                "huawei_delete_security_group", {"security_group_id": "sg-x"}
            )
        self.assertEqual(len(result["rules_snapshot"]), 1)
        self.assertIn("CreateSecurityGroup/v3", result["rollback"])

    def test_delete_rule_preview_carries_captured_rule(self):
        with mock.patch("sg.manage.get_security_group_rule",
                        return_value={"id": "r1", "direction": "ingress"}):
            result = dispatcher.dispatch_action(
                "huawei_delete_sg_rule", {"security_group_rule_id": "r-1"}
            )
        self.assertEqual(result["captured_rule"]["id"], "r1")
        self.assertIn("CreateSecurityGroupRule/v3", result["rollback"])

    def test_update_uses_v3_operation_name(self):
        result = dispatcher.dispatch_action(
            "huawei_update_security_group", {"security_group_id": "sg-x", "name": "n"}
        )
        self.assertIn("UpdateSecurityGroup/v3", result["command"])


class CacheReuseTest(unittest.TestCase):
    def setUp(self):
        common.clear_cache()

    def test_list_rules_is_queried_once_per_intent(self):
        calls = []

        def fake_run(service, operation, region, params=None, project_id=None):
            calls.append(operation)
            if operation.startswith("Show"):
                return {"security_group": {"id": "sg-x", "name": "n"}}
            return {"security_group_rules": [
                {"id": "r1", "direction": "ingress", "protocol": "tcp",
                 "multiport": "22", "remote_ip_prefix": "0.0.0.0/0", "action": "allow",
                 "priority": 1, "enabled": True, "ethertype": "IPv4"},
            ]}

        with mock.patch("sg.common.run_hcloud", side_effect=fake_run):
            result = dispatcher.dispatch_action(
                "huawei_diagnose_sg_port_connectivity",
                {"security_group_id": "sg-x", "direction": "ingress", "port": "22"},
            )
        self.assertTrue(result["success"], result)
        self.assertEqual(calls.count("ListSecurityGroupRules/v3"), 1, calls)
        self.assertEqual(calls.count("ShowSecurityGroup/v3"), 1, calls)

    def test_cache_is_cleared_between_intents(self):
        calls = []

        def fake_run(*_args, **_kwargs):
            calls.append(1)
            return {"security_groups": []}

        with mock.patch("sg.common.run_hcloud", side_effect=fake_run):
            dispatcher.dispatch_action("huawei_list_security_groups", {})
            dispatcher.dispatch_action("huawei_list_security_groups", {})
        self.assertEqual(len(calls), 2)


class InstallScriptTest(unittest.TestCase):
    """install_cli.sh: bounded, readable, non-zero. ensure_cli.sh: never blocks."""

    def _bin_dir(self, skip=()):
        """Temporary PATH with only the tools the scripts need (no skill-quality-cli)."""
        import shutil, tempfile
        bindir = tempfile.mkdtemp()
        for tool in ("bash", "curl", "python3", "tar", "mktemp", "uname", "rm", "mkdir",
                     "cp", "chmod", "sed"):
            if tool in skip:
                continue
            found = shutil.which(tool)
            if found:
                os.symlink(found, os.path.join(bindir, tool))
        return bindir

    def _run(self, script, extra_env, skip=()):
        env = env_without_credentials()
        env.update(extra_env)
        env["HOME"] = self.home
        env["PATH"] = self._bin_dir(skip)
        started = time.time()
        proc = subprocess.run(
            ["bash", os.path.join(SKILL_DIR, "scripts", script)],
            capture_output=True, text=True, env=env, timeout=60,
        )
        return proc, time.time() - started

    def setUp(self):
        import tempfile
        self.home = tempfile.mkdtemp()

    def test_install_fails_fast_and_readable_without_network(self):
        proc, elapsed = self._run(
            "install_cli.sh", {"SQC_API_URL": "http://127.0.0.1:9/api"}
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("错误", proc.stderr)
        self.assertLess(elapsed, 30.0)

    def test_install_reports_missing_dependency(self):
        proc, _ = self._run("install_cli.sh", {"SQC_API_URL": "http://127.0.0.1:9/api"},
                            skip=("curl",))
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("依赖 curl", proc.stderr)

    def test_ensure_warns_and_exits_zero_when_curl_missing(self):
        proc, _ = self._run("ensure_cli.sh", {"SQC_API_URL": "http://127.0.0.1:9/api"},
                            skip=("curl",))
        self.assertEqual(proc.returncode, 0)
        self.assertIn("缺少依赖 curl", proc.stderr)

    def test_ensure_never_blocks_on_network_failure(self):
        proc, elapsed = self._run(
            "ensure_cli.sh", {"SQC_API_URL": "http://127.0.0.1:9/api"}
        )
        self.assertEqual(proc.returncode, 0)
        self.assertLess(elapsed, 30.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)