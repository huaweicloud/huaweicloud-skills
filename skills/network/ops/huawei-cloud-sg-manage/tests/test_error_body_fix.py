#!/usr/bin/env python3
"""Offline verification for the run_hcloud API-error fix (SKI-1501 / Fixes #782).

Simulates hcloud returning rc=0 with a Huawei Cloud business-error body and
checks that write operations report success=false + error instead of
success=true.
"""
import json
import sys
import os
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))

from sg import common, manage, dispatcher  # noqa: E402


class FakeResult:
    def __init__(self, rc, stdout, stderr=""):
        self.returncode = rc
        self.stdout = stdout
        self.stderr = stderr


def fake_subprocess_run_ok(command, **kwargs):
    # rc=0 with an error body -> the scenario the bug report describes
    return FakeResult(0, json.dumps({
        "error_code": "VPC.0202",
        "error_msg": "security group rule not found",
    }))


class ErrorBodyDetectionTest(unittest.TestCase):
    def test_run_hcloud_raises_on_error_code_body(self):
        with mock.patch("shutil.which", return_value="/usr/bin/hcloud"), \
             mock.patch("subprocess.run", side_effect=fake_subprocess_run_ok):
            with self.assertRaises(RuntimeError) as ctx:
                common.run_hcloud("VPC", "DeleteSecurityGroupRule/v3", "cn-north-4", {"security_group_rule_id": "x"})
            self.assertIn("VPC.0202", str(ctx.exception))
            self.assertIn("security group rule not found", str(ctx.exception))

    def test_env_credentials_respected(self):
        with mock.patch("shutil.which", return_value="/usr/bin/hcloud"), \
             mock.patch.dict(os.environ, {}, clear=True), \
             mock.patch("sg.common._has_hcloud_profile", return_value=False), \
             mock.patch.dict(os.environ, {"HUAWEI_ACCESS_KEY": "AK", "HUAWEI_SECRET_KEY": "SK"}), \
             mock.patch("subprocess.run", side_effect=fake_subprocess_run_ok):
            with self.assertRaises(RuntimeError):
                common.run_hcloud("VPC", "DeleteSecurityGroupRule/v3", "cn-north-4", {"security_group_rule_id": "x"})

    def test_error_dict_shape(self):
        def fake(command, **kw):
            return FakeResult(0, json.dumps({"error": {"code": "VPC.1234", "message": "bad request"}}))
        with mock.patch("shutil.which", return_value="/usr/bin/hcloud"), \
             mock.patch("subprocess.run", side_effect=fake):
            with self.assertRaises(RuntimeError) as ctx:
                common.run_hcloud("VPC", "CreateSecurityGroup/v3", "cn-north-4", {"security_group.name": "n"})
            self.assertIn("VPC.1234", str(ctx.exception))
            self.assertIn("bad request", str(ctx.exception))

    def test_success_body_unchanged(self):
        def fake(command, **kw):
            return FakeResult(0, json.dumps({"security_group_rules": [{"id": "r1"}]}))
        with mock.patch("shutil.which", return_value="/usr/bin/hcloud"), \
             mock.patch("subprocess.run", side_effect=fake):
            data = common.run_hcloud("VPC", "ListSecurityGroupRules/v3", "cn-north-4", {})
            self.assertEqual(data, {"security_group_rules": [{"id": "r1"}]})

    def test_dispatcher_create_returns_success_false_on_api_error(self):
        # Patch manage.run_hcloud (the symbol manage.py actually calls) to
        # simulate the CLI returning rc=0 with a business-error body: the
        # fixed run_hcloud raises RuntimeError, which the dispatcher
        # converts into success=false + error.
        def fake_run_hcloud(service, operation, region, params=None, project_id=None):
            raise RuntimeError(
                f"hcloud {service} {operation} returned an API error: "
                "error_code=VPC.0202, error_msg=security group rule not found"
            )
        with mock.patch.object(manage, "run_hcloud", side_effect=fake_run_hcloud):
            result = dispatcher.dispatch_action("huawei_delete_sg_rule", {
                "security_group_rule_id": "does-not-exist",
                "confirmed": "true",
                "region": "cn-north-4",
            })
        self.assertFalse(result.get("success"))
        self.assertIn("VPC.0202", result.get("error", ""))
        self.assertIn("security group rule not found", result.get("error", ""))

        # same for a create operation
        def fake_create(service, operation, region, params=None, project_id=None):
            raise RuntimeError(
                f"hcloud {service} {operation} returned an API error: "
                "error_code=VPC.1234, error_msg=invalid parameter"
            )
        with mock.patch.object(manage, "run_hcloud", side_effect=fake_create):
            result = dispatcher.dispatch_action("huawei_create_security_group", {
                "name": "test-sg",
                "confirmed": "true",
                "region": "cn-north-4",
            })
        self.assertFalse(result.get("success"))
        self.assertIn("VPC.1234", result.get("error", ""))
        self.assertIn("invalid parameter", result.get("error", ""))

    def test_body_error_helper(self):
        # _extract_api_error returns (code, msg) tuples for the supported
        # error envelopes and None for success / non-dict payloads.
        self.assertIsNone(common._extract_api_error({"security_groups": []}))
        self.assertIsNone(common._extract_api_error({"error": False}))
        self.assertIsNone(common._extract_api_error("not a dict"))
        self.assertEqual(
            common._extract_api_error({"error_code": "E1", "error_msg": "m1"}),
            ("E1", "m1"),
        )
        self.assertEqual(
            common._extract_api_error({"error": {"code": "E2", "message": "m2"}}),
            ("E2", "m2"),
        )
        self.assertEqual(
            common._extract_api_error({"code": "E3", "message": "m3"}),
            ("E3", "m3"),
        )
        # generic "error" key without code/message is not an error envelope
        self.assertIsNone(common._extract_api_error({"error": "boom"}))


if __name__ == "__main__":
    unittest.main(verbosity=2)