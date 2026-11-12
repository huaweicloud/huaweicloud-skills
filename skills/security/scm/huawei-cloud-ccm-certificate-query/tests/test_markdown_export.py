#!/usr/bin/env python3
"""Offline unit tests for the Markdown export of the CCM certificate query script.

No network access and no real AK/SK are required: the SCM client and the paging
helper are stubbed, and fixtures are fixed samples.
"""

import contextlib
import datetime
import io
import os
import shutil
import sys
import tempfile
import unittest
from unittest import mock

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
SCRIPT_DIR = os.path.abspath(os.path.join(TESTS_DIR, "..", "scripts"))
sys.path.insert(0, SCRIPT_DIR)

import list_certificates as lc  # noqa: E402


FIXED_NOW = datetime.datetime(2026, 11, 12, 0, 0, 0, tzinfo=datetime.timezone.utc)


class MarkdownExportTest(unittest.TestCase):
    """Rendering, naming, path resolution and escaping for the md export."""

    def _cert(self, **overrides):
        raw = {
            "id": "abcdef1234567890",
            "name": "example.com",
            "type": "DV_SSL_CERT",
            "domain": "example.com",
            "status": "ISSUED",
            "issue_time": "2026-01-01 00:00:00",
            "expire_time": "2026-12-31 23:59:59",
        }
        raw.update(overrides)
        return lc.normalize_certificate(raw, now=FIXED_NOW)

    def test_default_output_name(self):
        self.assertEqual(
            lc.default_output_name("cn-north-4", "20261112184500"),
            "ccm_certificates_cn-north-4_20261112184500.md",
        )
        self.assertRegex(
            lc.default_output_name("cn-east-3"),
            r"^ccm_certificates_cn-east-3_\d{14}\.md$",
        )

    def test_resolve_output_path(self):
        tmpdir = tempfile.mkdtemp()
        try:
            self.assertEqual(lc.resolve_output_path(None, "cn-north-4", "20261112184500"),
                             "ccm_certificates_cn-north-4_20261112184500.md")
            self.assertEqual(
                lc.resolve_output_path(tmpdir, "cn-north-4", "20261112184500"),
                os.path.join(tmpdir, "ccm_certificates_cn-north-4_20261112184500.md"),
            )
            self.assertEqual(
                lc.resolve_output_path(tmpdir + os.sep, "cn-north-4", "20261112184500"),
                os.path.join(tmpdir, "ccm_certificates_cn-north-4_20261112184500.md"),
            )
            explicit = os.path.join(tmpdir, "report.md")
            self.assertEqual(lc.resolve_output_path(explicit, "cn-north-4"), explicit)
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_resolve_output_path_missing_dir(self):
        with self.assertRaises(lc.UsageError) as ctx:
            lc.resolve_output_path("/no/such/dir/report.md", "cn-north-4")
        self.assertEqual(ctx.exception.exit_code, 2)
        self.assertIn("导出目录不存在", str(ctx.exception))

    def test_markdown_has_summary_and_all_columns(self):
        cert = self._cert()
        document = lc.render_markdown(
            [cert],
            region="cn-north-4",
            filters={"name": "example.com", "status": "ISSUED", "expire_days": 30,
                     "limit": 20, "offset": 0, "sort_key": "certExpiredTime",
                     "sort_dir": "ASC", "include_shared": False},
            total=3,
            threshold=30,
            generated_at="2026-11-12 18:45:00 +0800",
        )
        self.assertTrue(document.startswith("# 华为云 CCM 证书清单"))
        for header in lc.MD_TABLE_HEADERS:
            self.assertIn(header, document)
        self.assertIn("cn-north-4", document)
        self.assertIn("example.com", document)
        self.assertIn("2026-11-12 18:45:00 +0800", document)
        self.assertIn("返回 1 张（服务端匹配 3 张）", document)
        self.assertIn("已签发", document)
        self.assertIn("| 49 |", document)
        self.assertIn("正常", document)

    def test_markdown_rows_match_terminal_table_values(self):
        certs = [self._cert(id="aaaa"), self._cert(id="bbbb", name="expired.cn",
                                                   status="EXPIRED",
                                                   expire_time="2026-11-01 00:00:00")]
        document = lc.render_markdown(certs, region="cn-north-4", generated_at="t",
                                      threshold=30)
        table = lc.render_table(certs)
        for cert in certs:
            cells = lc.markdown_row(cert)
            self.assertEqual(cells[0], cert["id"])
            self.assertEqual(cells[1], cert["name"])
            self.assertEqual(cells[4], cert["status_label"])
            self.assertEqual(cells[7], str(cert["days_to_expire"]))
            self.assertEqual(cells[8], cert["expiry_label"])
            for cell in (cert["id"], cert["name"], cert["status_label"]):
                self.assertIn(cell, table)
                self.assertIn(cell, document)
        self.assertEqual(lc.markdown_row(certs[1])[8], "已过期")

    def test_table_escaping(self):
        self.assertEqual(lc.escape_markdown_cell("a|b"), "a\\|b")
        self.assertEqual(lc.escape_markdown_cell("line1\nline2"), "line1<br>line2")
        self.assertEqual(lc.escape_markdown_cell("cr\r\nlf"), "cr<br>lf")
        self.assertEqual(lc.escape_markdown_cell(None), "-")
        self.assertEqual(lc.escape_markdown_cell(""), "-")
        cert = self._cert(name="broken|name", domain="multi\nline.example")
        row = lc.markdown_row(cert)
        self.assertEqual(row[1], "broken\\|name")
        self.assertEqual(row[3], "multi<br>line.example")
        document = lc.render_markdown([cert], region="cn-north-4", generated_at="t")
        self.assertNotIn("multi\nline", document)

    def test_empty_list_render_is_placeholder(self):
        document = lc.render_markdown([], region="cn-north-4", total=0,
                                      generated_at="t")
        self.assertIn("无匹配证书（共 0 条）", document)
        self.assertIn("返回 0 张", document)


class ExportCliTest(unittest.TestCase):
    """End-to-end CLI behaviour with the SCM client and paging mocked out."""

    ENV = {"HUAWEI_ACCESS_KEY": "AK_FOR_TEST", "HUAWEI_SECRET_KEY": "SK_FOR_TEST",
           "HUAWEI_REGION": "cn-north-4"}

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.cert = lc.normalize_certificate({
            "id": "abcdef1234567890",
            "name": "example.com",
            "type": "DV_SSL_CERT",
            "domain": "example.com",
            "status": "ISSUED",
            "expire_time": "2026-12-31 23:59:59",
        }, now=FIXED_NOW)

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _run(self, argv, certs, total):
        class FakeScm:
            def __init__(self, *args, **kwargs):
                pass

        out, err = io.StringIO(), io.StringIO()
        with mock.patch.dict(os.environ, self.ENV, clear=False), \
                mock.patch.object(lc, "ScmClient", FakeScm), \
                mock.patch.object(lc, "collect_certificates",
                                  lambda *a, **k: (list(certs), total)), \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = lc.main(argv)
        return code, out.getvalue(), err.getvalue()

    def test_export_to_directory_uses_default_name_and_echoes_markdown(self):
        code, out, err = self._run(["list", "--output", self.tmpdir], [self.cert], 1)
        self.assertEqual(code, 0)
        files = os.listdir(self.tmpdir)
        self.assertEqual(len(files), 1)
        self.assertRegex(files[0], r"^ccm_certificates_cn-north-4_\d{14}\.md$")
        with open(os.path.join(self.tmpdir, files[0]), encoding="utf-8") as handle:
            content = handle.read()
        self.assertEqual(content, out if out.endswith("\n") else out + "\n")
        self.assertIn("已导出 1 张证书到", err)

    def test_export_to_explicit_file_path(self):
        target = os.path.join(self.tmpdir, "custom.md")
        code, out, _ = self._run(["list", "--output", target], [self.cert], 1)
        self.assertEqual(code, 0)
        self.assertTrue(os.path.isfile(target))
        with open(target, encoding="utf-8") as handle:
            self.assertIn("# 华为云 CCM 证书清单", handle.read())

    def test_export_content_carries_filters_and_count(self):
        target = os.path.join(self.tmpdir, "filtered.md")
        code, _, _ = self._run(
            ["list", "--output", target, "--name", "example.com",
             "--status", "issued", "--expire-days", "45", "--limit", "20"],
            [self.cert], 5,
        )
        self.assertEqual(code, 0)
        with open(target, encoding="utf-8") as handle:
            content = handle.read()
        self.assertIn("example.com", content)
        self.assertIn("ISSUED", content)
        self.assertIn("到期分级阈值（天）=45", content)
        self.assertIn("条数上限=20", content)
        self.assertIn("返回 1 张（服务端匹配 5 张）", content)

    def test_empty_list_writes_no_file(self):
        code, out, _ = self._run(["list", "--output", self.tmpdir], [], 0)
        self.assertEqual(code, 0)
        self.assertEqual(os.listdir(self.tmpdir), [])
        self.assertIn("未生成 Markdown 文件", out)

    def test_output_and_json_are_mutually_exclusive(self):
        code, _, err = self._run(
            ["list", "--output", self.tmpdir, "--json"], [self.cert], 1)
        self.assertEqual(code, 2)
        self.assertIn("--output 与 --json 不能同时使用", err)
        self.assertEqual(os.listdir(self.tmpdir), [])

    def test_unwritable_target_is_readable_error(self):
        with self.assertRaises(lc.UsageError) as ctx:
            lc.write_markdown(self.tmpdir, "# doc")
        self.assertEqual(ctx.exception.exit_code, 2)
        self.assertIn("无法写入 Markdown 文件", str(ctx.exception))

    def test_export_never_leaks_credentials(self):
        target = os.path.join(self.tmpdir, "noleak.md")
        code, out, err = self._run(["list", "--output", target], [self.cert], 1)
        self.assertEqual(code, 0)
        with open(target, encoding="utf-8") as handle:
            content = handle.read()
        for secret in (self.ENV["HUAWEI_ACCESS_KEY"], self.ENV["HUAWEI_SECRET_KEY"]):
            self.assertNotIn(secret, content)
            self.assertNotIn(secret, out)
            self.assertNotIn(secret, err)


if __name__ == "__main__":
    unittest.main()
