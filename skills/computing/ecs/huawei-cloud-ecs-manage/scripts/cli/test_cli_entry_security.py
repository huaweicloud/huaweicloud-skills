#!/usr/bin/env python3
"""test_cli_entry_security — SC3 安全闭环可验证测试用例。

覆盖 (issue #1010 安全闭环增强):
  1. 写操作中间层拦截: 未携带显式确认 token 时拒绝执行
  2. 删除类操作默认强制先跑 --dryrun 校验(未确认时自动降级, 不产生真实删除)
  3. 凭证字段 (AK/SK/password/token) 输出层自动脱敏
  4. 只读操作不受影响(白名单之外不改变命令行为)

运行: python3 test_cli_entry_security.py  (无外部依赖, 纯标准库)
"""

import os
import subprocess
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cli_entry as c


class FakeArgs(object):
    def __init__(self, confirm_token=None):
        self.confirm_token = confirm_token
        self.json = None
        self.session_id = None


READ_COMMANDS = [
    ["hcloud", "ECS", "ListServersDetails", "--cli-region=cn-north-4"],
    ["hcloud", "ECS", "ShowServer", "--cli-region=cn-north-4", "--server_id={server_id}"],
    ["hcloud", "ECS", "ShowJob", "--cli-region=cn-north-4", "--job_id={job_id}"],
    ["hcloud", "ECS", "ShowServerLimits", "--cli-region=cn-north-4"],
    ["hcloud", "ECS", "ListFlavors", "--cli-region=cn-north-4", "--flavor_id={flavor_id}"],
    ["hcloud", "IMS", "ListImages", "--cli-region=cn-north-4", "--id={image_id}", "--status=active"],
    ["hcloud", "EVS", "CinderListQuotas", "--cli-region=cn-north-4", "--target_project_id={project_id}"],
    ["hcloud", "VPC", "ListSubnets", "--cli-region=cn-north-4"],
    ["hcloud", "EIP", "ListPublicips/v2", "--cli-region=cn-north-4"],
    ["hcloud", "KPS", "ListKeypairs", "--cli-region=cn-north-4"],
    # BUG-2 回归: 纯查询操作含 ReSize/Reset 子词, 但读前缀优先 → 应判 read
    ["hcloud", "ECS", "ListResizeFlavors", "--cli-region=cn-north-4", "--flavor_id={flavor_id}"],
    ["hcloud", "ECS", "ShowResetPasswordFlag", "--cli-region=cn-north-4", "--server_id={server_id}"],
]

WRITE_COMMANDS = [
    ["hcloud", "ECS", "CreatePostPaidServers", "--server.name={n}"],
    ["hcloud", "ECS", "BatchStartServers", "--os-start.servers.1.id={id}"],
    ["hcloud", "ECS", "BatchStopServers", "--os-stop.servers.1.id={id}", "--os-stop.type=SOFT"],
    ["hcloud", "ECS", "BatchRebootServers", "--reboot.servers.1.id={id}", "--reboot.type=SOFT"],
    ["hcloud", "ECS", "ResizeServer", "--server_id={id}", "--resize.flavorRef={f}"],
    ["hcloud", "ECS", "ReinstallServerWithCloudInit", "--server_id={id}"],
    ["hcloud", "ECS", "ResetServerPassword", "--server_id={id}"],
    ["hcloud", "ECS", "NovaCreateKeypair", "--keypair.name={name}"],
    ["hcloud", "EIP", "AssociatePublicips", "--publicip_id={eip_id}"],
    ["hcloud", "ECS", "NovaAssociateSecurityGroup", "--server_id={id}"],
    ["hcloud", "ECS", "BatchAddServerNics", "--server_id={id}", "--nics.1.subnet_id={sub}"],
    ["hcloud", "ECS", "AttachServerVolume", "--server_id={id}"],
    # BUG-1 回归: 真实变更操作不含写标记词, 但未命中读白名单 → 应判 write 被门控
    ["hcloud", "ECS", "MigrateServer", "--server_id={id}"],
    ["hcloud", "ECS", "RevertRecycleBinServer", "--server_id={id}"],
    ["hcloud", "ECS", "ExecuteServerDump", "--server_id={id}"],
    ["hcloud", "ECS", "ExecuteServerRedeploy", "--server_id={id}"],
    ["hcloud", "ECS", "NovaLockServer", "--server_id={id}"],
    ["hcloud", "ECS", "NovaUnlockServer", "--server_id={id}"],
    ["hcloud", "ECS", "RegisterServerMonitor", "--server_id={id}"],
    ["hcloud", "ECS", "AcceptScheduledEvent", "--event_id={id}"],
]

DELETE_COMMANDS = [
    ["hcloud", "ECS", "DeleteServers", "--servers.1.id={id}"],
    ["hcloud", "ECS", "NovaDeleteKeypair", "--keypair_name={name}"],
    ["hcloud", "EIP", "DisassociatePublicips", "--publicip_id={eip_id}"],
    ["hcloud", "ECS", "NovaDisassociateSecurityGroup", "--server_id={id}"],
    ["hcloud", "ECS", "BatchDeleteServerNics", "--server_id={id}", "--nics.1.id={port}"],
    ["hcloud", "ECS", "DetachServerVolume", "--server_id={id}", "--volume_id={vol}"],
]


class ClassifyOperationTest(unittest.TestCase):
    def test_read_commands_classified_read(self):
        for cmd in READ_COMMANDS:
            self.assertEqual(c._classify_operation(cmd), "read", cmd)

    def test_write_commands_classified_write(self):
        for cmd in WRITE_COMMANDS:
            self.assertEqual(c._classify_operation(cmd), "write", cmd)

    def test_delete_commands_classified_delete(self):
        for cmd in DELETE_COMMANDS:
            self.assertEqual(c._classify_operation(cmd), "delete", cmd)

    def test_invalid_command_falls_back_read(self):
        self.assertEqual(c._classify_operation([]), "read")
        self.assertEqual(c._classify_operation(["ls"]), "read")
        self.assertEqual(c._classify_operation(["hcloud", "ECS"]), "read")

    def test_read_word_not_colliding_with_write_marker(self):
        """ListServerVolumeAttachments 中的 'attach' 是子串不是单词, 不应误判为写操作。"""
        self.assertEqual(
            c._classify_operation(["hcloud", "ECS", "ListServerVolumeAttachments", "--server_id=x"]),
            "read",
        )
        self.assertEqual(
            c._classify_operation(["hcloud", "ECS", "ShowServer", "--server_id=x"]),
            "read",
        )

    def test_read_whitelist_wins_over_write_subwords(self):
        """BUG-2 回归: 含 ReSize/Reset 子词的纯查询仍应判为 read, 不能被误拦。"""
        self.assertEqual(
            c._classify_operation(["hcloud", "ECS", "ListResizeFlavors", "--server_id=x"]),
            "read",
        )
        self.assertEqual(
            c._classify_operation(["hcloud", "ECS", "ShowResetPasswordFlag", "--server_id=x"]),
            "read",
        )

    def test_no_write_marker_mutation_ops_classified_write(self):
        """BUG-1 回归: 不含 Create/Update/Delete 字样的 8 个真实变更操作必须判为 write 门控。"""
        for op in (
            "MigrateServer", "RevertRecycleBinServer", "ExecuteServerDump",
            "ExecuteServerRedeploy", "NovaLockServer", "NovaUnlockServer",
            "RegisterServerMonitor", "AcceptScheduledEvent",
        ):
            self.assertEqual(
                c._classify_operation(["hcloud", "ECS", op, "--server_id=x"]), "write", op
            )


class ConfirmTokenTest(unittest.TestCase):
    def test_trivial_tokens_rejected(self):
        for t in ("", "yes", "ok", "confirm", "update", "删除", "确认", "run", "delete"):
            self.assertFalse(c._is_valid_confirm_token(t), t)

    def test_short_tokens_rejected(self):
        self.assertFalse(c._is_valid_confirm_token("short"))

    def test_strong_tokens_accepted(self):
        for t in ("ConfirmToken123", "CONFIRMSEC123", "确认操作安全码Abc123"):
            self.assertTrue(c._is_valid_confirm_token(t), t)


class SecurityGateTest(unittest.TestCase):
    def test_read_always_allowed_without_token(self):
        args = FakeArgs()
        for cmd in READ_COMMANDS:
            allow, gated, msg = c._security_gate(cmd, args, {})
            self.assertTrue(allow, cmd)
            self.assertEqual(gated, cmd, cmd)
            self.assertIsNone(msg, cmd)

    def test_write_without_token_refused(self):
        args = FakeArgs()
        for cmd in WRITE_COMMANDS:
            allow, gated, msg = c._security_gate(cmd, args, {})
            self.assertFalse(allow, cmd)
            self.assertIsNone(gated)
            self.assertIn("确认 token", msg, cmd)

    def test_write_with_token_allowed(self):
        args = FakeArgs(confirm_token="ConfirmToken123")
        for cmd in WRITE_COMMANDS:
            allow, gated, msg = c._security_gate(cmd, args, {})
            self.assertTrue(allow, cmd)
            self.assertEqual(gated, cmd, cmd)
            self.assertIsNone(msg, cmd)

    def test_write_explicit_dryrun_allowed_without_token(self):
        """显式加 --dryrun 的写操作为只读校验, 无需确认 token 即可执行(SKILL.md create 流程先校验)。"""
        args = FakeArgs()
        for cmd in WRITE_COMMANDS:
            dry = list(cmd) + ["--dryrun"]
            allow, gated, msg = c._security_gate(dry, args, {})
            self.assertTrue(allow, cmd)
            self.assertEqual(gated, dry, cmd)
            self.assertIsNone(msg, cmd)

    def test_write_token_from_env(self):
        os.environ[c._CONFIRM_TOKEN_ENV] = "ConfirmEnvToken456"
        try:
            for cmd in WRITE_COMMANDS[:2]:
                allow, _, _ = c._security_gate(cmd, FakeArgs(), {})
                self.assertTrue(allow, cmd)
        finally:
            os.environ.pop(c._CONFIRM_TOKEN_ENV, None)

    def test_write_token_from_qcfg(self):
        for cmd in WRITE_COMMANDS[:2]:
            allow, _, _ = c._security_gate(cmd, FakeArgs(), {"confirm_token": "ConfirmQcfgToken789"})
            self.assertTrue(allow, cmd)

    def test_delete_without_token_downgraded_to_dryrun(self):
        """删除类操作未确认时: 技术强制备追加 --dryrun, 转为只读校验而非执行真实删除。"""
        args = FakeArgs()
        for cmd in DELETE_COMMANDS:
            allow, gated, msg = c._security_gate(cmd, args, {})
            self.assertTrue(allow, cmd)
            self.assertIn("--dryrun", gated, cmd)
            self.assertNotIn(cmd, [c], "no-op")
            self.assertIn("未携带显式确认 token", msg, cmd)

    def test_delete_with_token_allowed(self):
        args = FakeArgs(confirm_token="ConfirmToken123")
        for cmd in DELETE_COMMANDS:
            allow, gated, msg = c._security_gate(cmd, args, {})
            self.assertTrue(allow, cmd)
            self.assertEqual(gated, cmd, cmd)
            self.assertIsNone(msg, cmd)

    def test_delete_already_dryrun_allowed_without_token(self):
        args = FakeArgs()
        for cmd in DELETE_COMMANDS:
            dry = list(cmd) + ["--dryrun"]
            allow, gated, msg = c._security_gate(dry, args, {})
            self.assertTrue(allow, cmd)
            self.assertEqual(gated, dry, cmd)
            self.assertIsNone(msg, cmd)


class MaskSecretsTest(unittest.TestCase):
    def setUp(self):
        self._env = dict(os.environ)
        os.environ["HUAWEICLOUD_SDK_AK"] = "AK1234567890EXAMPLE"
        os.environ["HUAWEICLOUD_SDK_SK"] = "SKfedcba9876543210SECRET"

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._env)

    def test_ak_sk_values_masked(self):
        secrets = c._collect_secrets({})
        out = c._mask_secrets("ak=AK1234567890EXAMPLE sk=SKfedcba9876543210SECRET", secrets)
        self.assertNotIn("AK1234567890EXAMPLE", out)
        self.assertNotIn("SKfedcba9876543210SECRET", out)
        self.assertEqual(out.count(c._MASK), 2)

    def test_param_password_masked(self):
        secrets = c._collect_secrets({})
        for s in ("--server.adminPass=MyP@ssw0rd!", "--reset-password.new_password=Pwd!2345",
                  "--os-reinstall.adminpass=Admin@123"):
            out = c._mask_secrets(s, secrets)
            self.assertIn("******", out, s)
            self.assertNotRegex(out, r"(MyP@ssw0rd!|Pwd!2345|Admin@123)")

    def test_json_password_token_masked(self):
        secrets = c._collect_secrets({})
        out = c._mask_secrets('{"adminPass": "Admin@123", "token": "abc123xyz"}', secrets)
        self.assertNotIn("Admin@123", out)
        self.assertNotIn("abc123xyz", out)
        self.assertEqual(out, '{"adminPass": "******", "token": "******"}')

    def test_secrets_from_qcfg_masked(self):
        secrets = c._collect_secrets({"json_creds": {"ak": "qcfgAK123456", "sk": "qcfgSK123456"},
                                      "token": "qcfgToken123"})
        out = c._mask_secrets("qcfgAK123456 qcfgSK123456 qcfgToken123", secrets)
        self.assertNotIn("qcfgAK123456", out)
        self.assertNotIn("qcfgSK123456", out)
        self.assertNotIn("qcfgToken123", out)

    def test_normal_output_unmodified(self):
        secrets = c._collect_secrets({})
        normal = '{"server": {"id": "abc", "status": "ACTIVE"}} --limit=10'
        self.assertEqual(c._mask_secrets(normal, secrets), normal)

    def test_masking_empty_input(self):
        self.assertEqual(c._mask_secrets("", []), "")
        self.assertEqual(c._mask_secrets(None, []), "")


class SmokeRunTest(unittest.TestCase):
    """端到端冒烟: 安全门控在 cmd_run 全链路生效(不真正执行 hcloud, 用白名单外命令定位到校验层)。"""

    def _run_cli(self, *argv, extra_env=None):
        env = dict(os.environ)
        env["SKILL_QUALITY_REPORT"] = "0"
        if extra_env:
            env.update(extra_env)
        proc = subprocess.run(
            [sys.executable, os.path.join(os.path.dirname(__file__), "cli_entry.py")] + list(argv),
            capture_output=True, text=True, env=env, timeout=60,
        )
        return proc

    def test_write_without_token_refused_exit3(self):
        """写操作(非删除)未携带确认 token 时, cmd_run 拒绝执行并返回退出码 3(拒绝)。"""
        proc = self._run_cli(
            "run", "--skill-name", "huawei-cloud-ecs-manage",
            "hcloud", "ECS", "CreatePostPaidServers", "--server.name={n}",
        )
        self.assertEqual(proc.returncode, 3, proc.stderr)
        self.assertIn("写操作", proc.stderr)

    def test_delete_without_token_downgraded_to_dryrun(self):
        """删除类操作未确认时, cmd_run 自动追加 --dryrun 降级执行, 而非拒绝退出。"""
        proc = self._run_cli(
            "run", "--skill-name", "huawei-cloud-ecs-manage",
            "hcloud", "ECS", "DeleteServers", "--servers.1.id={id}",
        )
        self.assertNotEqual(proc.returncode, 3)
        self.assertIn("--dryrun", proc.stderr)
        self.assertIn("不产生真实删除", proc.stderr)

    def test_write_with_token_attempts_execution(self):
        """携带确认 token 的写操作放行, 进入子进程执行(白名单外命令此时定位到 hcloud 不存在 127)。"""
        proc = self._run_cli(
            "run", "--skill-name", "huawei-cloud-ecs-manage",
            "--confirm-token", "ConfirmToken123",
            "hcloud", "ECS", "CreatePostPaidServers", "--server.name={n}",
        )
        self.assertNotEqual(proc.returncode, 3)
        self.assertNotIn("已拒绝执行", proc.stderr)

    def test_read_command_runs_without_gate(self):
        """只读操作不受安全门控影响, 只走到子进程执行(hcloud 未安装/不存在时 127)。"""
        proc = self._run_cli(
            "run", "--skill-name", "huawei-cloud-ecs-manage",
            "hcloud", "ECS", "ListServersDetails", "--limit=1",
        )
        self.assertNotEqual(proc.returncode, 3)
        self.assertNotIn("确认 token", proc.stderr)

    def test_bugfix_mutate_op_without_token_refused(self):
        """BUG-1 回归: MigrateServer 等不含写标记词的变更操作无确认 token 时同样 exit 3 拒绝。"""
        for op in (
            "MigrateServer", "RevertRecycleBinServer", "ExecuteServerDump",
            "ExecuteServerRedeploy", "NovaLockServer", "NovaUnlockServer",
            "RegisterServerMonitor", "AcceptScheduledEvent",
        ):
            proc = self._run_cli(
                "run", "--skill-name", "huawei-cloud-ecs-manage",
                "hcloud", "ECS", op, "--server_id={id}",
            )
            self.assertEqual(proc.returncode, 3, f"{op}: {proc.stderr}")
            self.assertIn("确认 token", proc.stderr, op)

    def test_bugfix_mutate_op_with_token_released(self):
        """BUG-1 回归: MigrateServer/RevertRecycleBinServer 带确认 token 放行至子进程执行。"""
        for op in ("MigrateServer", "RevertRecycleBinServer", "RegisterServerMonitor"):
            proc = self._run_cli(
                "run", "--skill-name", "huawei-cloud-ecs-manage",
                "--confirm-token", "ConfirmToken123",
                "hcloud", "ECS", op, "--server_id={id}",
            )
            self.assertNotEqual(proc.returncode, 3, f"{op}: {proc.stderr}")
            self.assertNotIn("已拒绝执行", proc.stderr, op)

    def test_bugfix_read_prefix_query_not_blocked(self):
        """BUG-2 回归: ListResizeFlavors/ShowResetPasswordFlag 纯查询无 token 不被拦截(非 exit 3)。"""
        for op in ("ListResizeFlavors", "ShowResetPasswordFlag"):
            proc = self._run_cli(
                "run", "--skill-name", "huawei-cloud-ecs-manage",
                "hcloud", "ECS", op, "--server_id={id}",
            )
            self.assertNotEqual(proc.returncode, 3, f"{op}: {proc.stderr}")
            self.assertNotIn("确认 token", proc.stderr, op)


if __name__ == "__main__":
    unittest.main(verbosity=2)