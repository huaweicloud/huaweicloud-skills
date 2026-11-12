#!/usr/bin/env python3
"""Offline unit tests for the CCM certificate query script.

No network access and no real AK/SK are required: signing uses dummy
credentials and responses are fixed samples.
"""

import datetime
import json
import os
import sys
import unittest

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
SCRIPT_DIR = os.path.abspath(os.path.join(TESTS_DIR, "..", "scripts"))
sys.path.insert(0, SCRIPT_DIR)

import list_certificates as lc  # noqa: E402


FIXED_NOW = datetime.datetime(2026, 11, 12, 0, 0, 0, tzinfo=datetime.timezone.utc)


class CredentialTest(unittest.TestCase):
    def test_missing_credentials(self):
        with self.assertRaises(lc.CredentialError) as ctx:
            lc.load_credentials({"HUAWEI_ACCESS_KEY": "AK_ONLY"})
        self.assertEqual(ctx.exception.exit_code, 3)
        self.assertIn("HUAWEI_ACCESS_KEY", str(ctx.exception))
        self.assertNotIn("AK_ONLY", str(ctx.exception))

    def test_credential_env_priority_and_token(self):
        creds = lc.load_credentials({
            "HW_ACCESS_KEY": "old",
            "HUAWEI_ACCESS_KEY": "new-ak",
            "HW_SECRET_KEY": "old-sk",
            "HUAWEI_SECRET_KEY": "new-sk",
            "HUAWEI_SECURITY_TOKEN": "token-1",
        })
        self.assertEqual(creds["ak"], "new-ak")
        self.assertEqual(creds["sk"], "new-sk")
        self.assertEqual(creds["token"], "token-1")

    def test_temporary_credentials_without_token_are_allowed(self):
        creds = lc.load_credentials({
            "HUAWEI_AK": "ak",
            "HUAWEI_SK": "sk",
        })
        self.assertEqual(creds["token"], "")


class RegionTest(unittest.TestCase):
    def test_cli_region_wins(self):
        self.assertEqual(lc.resolve_region("cn-east-3", {"HUAWEI_REGION": "cn-north-4"}), "cn-east-3")

    def test_env_region_and_default(self):
        self.assertEqual(lc.resolve_region(None, {"HUAWEI_REGION": "ap-southeast-1"}), "ap-southeast-1")
        self.assertEqual(lc.resolve_region(None, {}), lc.DEFAULT_REGION)

    def test_invalid_region(self):
        with self.assertRaises(lc.UsageError):
            lc.resolve_region("not-a-region", {})

    def test_build_host(self):
        self.assertEqual(
            lc.build_host("cn-north-4"),
            "scm.cn-north-4.myhuaweicloud.com",
        )
        self.assertEqual(
            lc.build_host("cn-north-4", "https://scm.example.com/"),
            "scm.example.com",
        )
        self.assertEqual(
            lc.build_host("cn-north-4", "127.0.0.1:9443"),
            "127.0.0.1:9443",
        )


class StatusTest(unittest.TestCase):
    def test_status_aliases(self):
        self.assertEqual(lc.normalize_status("issued"), "ISSUED")
        self.assertEqual(lc.normalize_status(" expired "), "EXPIRED")
        self.assertEqual(lc.normalize_status("all"), "ALL")
        self.assertEqual(lc.normalize_status("*"), "ALL")
        self.assertIsNone(lc.normalize_status(None))

    def test_unknown_status(self):
        with self.assertRaises(lc.UsageError) as ctx:
            lc.normalize_status("NOT_A_STATUS")
        self.assertIn("ISSUED", str(ctx.exception))


class QueryConstructionTest(unittest.TestCase):
    def test_list_query_maps_name_to_content_and_status(self):
        pairs = lc.build_list_query(
            name="example.com",
            status="issued",
            expiring=15,
            offset=10,
            limit=20,
            enterprise_project_id="0",
            include_shared=True,
            sort_key="certExpiredTime",
            sort_dir="desc",
        )
        mapping = dict(pairs)
        self.assertEqual(mapping["content"], "example.com")
        self.assertEqual(mapping["status"], "ISSUED")
        self.assertEqual(mapping["expired_days_since"], "15")
        self.assertEqual(mapping["offset"], "10")
        self.assertEqual(mapping["limit"], "20")
        self.assertEqual(mapping["enterprise_project_id"], "0")
        self.assertEqual(mapping["owned_by_self"], "false")
        self.assertEqual(mapping["sort_key"], "certExpiredTime")
        self.assertEqual(mapping["sort_dir"], "DESC")

    def test_all_status_is_not_forwarded(self):
        pairs = lc.build_list_query(status="ALL")
        self.assertNotIn("status", dict(pairs))

    def test_limit_is_clamped_to_api_bounds(self):
        self.assertEqual(dict(lc.build_list_query(limit=1))["limit"], "10")
        self.assertEqual(dict(lc.build_list_query(limit=999))["limit"], "50")

    def test_invalid_sort(self):
        with self.assertRaises(lc.UsageError):
            lc.build_list_query(sort_key="bad")
        with self.assertRaises(lc.UsageError):
            lc.build_list_query(sort_dir="up")


class SigningTest(unittest.TestCase):
    DUMMY_AK = "AKIDEXAMPLE"
    DUMMY_SK = "SKEXAMPLE0123456789"
    HOST = "scm.cn-north-4.myhuaweicloud.com"
    PATH = "/v3/scm/certificates"
    QUERY = [
        ("content", "example.com"),
        ("status", "ISSUED"),
        ("limit", "50"),
        ("offset", "0"),
        ("owned_by_self", "false"),
        ("sort_key", "certExpiredTime"),
        ("sort_dir", "ASC"),
    ]
    EXPECTED = (
        "SDK-HMAC-SHA256 Access=AKIDEXAMPLE, "
        "SignedHeaders=host;x-sdk-date;x-security-token, "
        "Signature=7c226e7ec0be58ce00c3e9ddd5f8779dd910db6d27b491bf7755ff9891e6a1d5"
    )

    def test_signature_matches_official_sdk_algorithm(self):
        headers = lc.sign_headers(
            "GET", self.HOST, self.PATH, self.QUERY, self.DUMMY_AK, self.DUMMY_SK,
            token="tok", timestamp="20261112T090000Z",
        )
        self.assertEqual(headers["Authorization"], self.EXPECTED)
        self.assertEqual(headers["Host"], self.HOST)
        self.assertEqual(headers["X-Sdk-Date"], "20261112T090000Z")

    def test_query_change_changes_signature(self):
        base = lc.sign_headers("GET", self.HOST, self.PATH, self.QUERY,
                               self.DUMMY_AK, self.DUMMY_SK, timestamp="20261112T090000Z")
        changed_query = list(self.QUERY)
        changed_query[1] = ("status", "EXPIRED")
        changed = lc.sign_headers("GET", self.HOST, self.PATH, changed_query,
                                  self.DUMMY_AK, self.DUMMY_SK, timestamp="20261112T090000Z")
        self.assertNotEqual(base["Authorization"], changed["Authorization"])

    def test_secret_key_is_not_written_to_headers(self):
        headers = lc.sign_headers("GET", self.HOST, self.PATH, [], self.DUMMY_AK, self.DUMMY_SK,
                                  timestamp="20261112T090000Z")
        self.assertNotIn(self.DUMMY_SK, json.dumps(headers))

    def test_canonical_query_is_sorted_and_encoded(self):
        query = lc.canonical_query_string([("b", "x y"), ("a", "1"), ("a", "0")])
        self.assertEqual(query, "a=0&a=1&b=x%20y")

    def test_canonical_uri_has_trailing_slash(self):
        self.assertEqual(lc.canonical_uri("v3/scm/certificates"), "/v3/scm/certificates/")
        self.assertEqual(lc.canonical_uri("/v3/scm/certificates/abc"), "/v3/scm/certificates/abc/")


class DateAndExpiryTest(unittest.TestCase):
    def test_parse_formats(self):
        self.assertEqual(lc.parse_certificate_date("2026-12-31 23:59:59"), datetime.date(2026, 12, 31))
        self.assertEqual(lc.parse_certificate_date("2026/12/31"), datetime.date(2026, 12, 31))
        self.assertEqual(lc.parse_certificate_date("2026-12-31T23:59:59Z"), datetime.date(2026, 12, 31))
        self.assertIsNone(lc.parse_certificate_date(""))
        self.assertIsNone(lc.parse_certificate_date("not-a-date"))

    def test_days_to_expire(self):
        self.assertEqual(lc.days_to_expire("2026-11-12 10:00:00", now=FIXED_NOW), 0)
        self.assertEqual(lc.days_to_expire("2026-11-13", now=FIXED_NOW), 1)
        self.assertEqual(lc.days_to_expire("2026-11-11", now=FIXED_NOW), -1)
        self.assertIsNone(lc.days_to_expire(None, now=FIXED_NOW))

    def test_grade_boundaries(self):
        self.assertEqual(lc.grade_expiry(-1), "expired")
        self.assertEqual(lc.grade_expiry(0), "expiring")
        self.assertEqual(lc.grade_expiry(30), "expiring")
        self.assertEqual(lc.grade_expiry(31), "normal")
        self.assertEqual(lc.grade_expiry(None, status="EXPIRED"), "expired")
        self.assertEqual(lc.grade_expiry(None, status="ISSUED"), "unknown")


class NormalizationTest(unittest.TestCase):
    def test_normalize_list_item(self):
        raw = {
            "id": "1234567890abcdef",
            "name": "example.com",
            "type": "DV_SSL_CERT",
            "domain": "example.com",
            "sans": "www.example.com",
            "status": "ISSUED",
            "expire_time": "2026-12-31 23:59:59",
            "validity_period": 12,
            "deploy_support": True,
        }
        cert = lc.normalize_certificate(raw, threshold=30, now=FIXED_NOW)
        self.assertEqual(cert["id"], "1234567890abcdef")
        self.assertEqual(cert["status_label"], "已签发")
        self.assertEqual(cert["days_to_expire"], 49)
        self.assertEqual(cert["expiry_level"], "normal")
        self.assertEqual(cert["expiry_label"], "正常")
        self.assertTrue(cert["deploy_support"])
        self.assertIsNone(cert["issue_time"])

    def test_missing_fields_are_none_without_failure(self):
        cert = lc.normalize_certificate({}, now=FIXED_NOW)
        self.assertIsNone(cert["id"])
        self.assertIsNone(cert["days_to_expire"])
        self.assertEqual(cert["expiry_level"], "unknown")

    def test_empty_list_payload(self):
        certs, total = lc.normalize_list_payload({"certificates": [], "total_count": 0})
        self.assertEqual(certs, [])
        self.assertEqual(total, 0)

    def test_list_payload_total_count(self):
        certs, total = lc.normalize_list_payload(
            {"certificates": [{"id": "a"}, {"id": "b"}], "total_count": 7},
            now=FIXED_NOW,
        )
        self.assertEqual(len(certs), 2)
        self.assertEqual(total, 7)

    def test_show_payload_extra_fields(self):
        cert = lc.normalize_show_payload({
            "id": "abc",
            "status": "ISSUED",
            "issue_time": "2026-01-01 00:00:00",
            "not_after": "2026-12-31 23:59:59",
            "fingerprint": "FF",
            "application_info": {"contact_email": "ops@example.com"},
            "authentification": [{"domain": "example.com"}],
        }, now=FIXED_NOW)
        self.assertEqual(cert["issue_time"], "2026-01-01 00:00:00")
        self.assertEqual(cert["days_to_expire"], 49)
        self.assertEqual(cert["fingerprint"], "FF")
        self.assertEqual(cert["application_info"]["contact_email"], "ops@example.com")
        self.assertEqual(cert["authentification"][0]["domain"], "example.com")


class ErrorClassificationTest(unittest.TestCase):
    def test_401(self):
        err = lc.classify_http_error(401, b'{"error_code":"SCM.4001","error_msg":"Unauthorized"}')
        self.assertIsInstance(err, lc.AuthError)
        self.assertIn("401", str(err))
        self.assertIn("SCM.4001", str(err))

    def test_403_names_required_actions(self):
        err = lc.classify_http_error(
            403,
            json.dumps({
                "error_code": "SCM.4002",
                "error_msg": "Permission denied",
                "encoded_authorization_message": "very-long-encoded-blob",
            }).encode(),
        )
        self.assertIsInstance(err, lc.AuthError)
        self.assertIn("scm:cert:list", str(err))
        self.assertIn("scm:cert:get", str(err))
        self.assertNotIn("very-long-encoded-blob", str(err))

    def test_400_and_500(self):
        self.assertIsInstance(lc.classify_http_error(400, b'{"error_msg":"bad"}'), lc.ApiError)
        self.assertIsInstance(lc.classify_http_error(500, b''), lc.ApiError)

    def test_error_body_without_json(self):
        self.assertEqual(lc.extract_error_message(b"plain text"), "")


class FakeClient:
    def __init__(self, pages):
        self.pages = pages
        self.calls = []

    def get(self, path, query_pairs):
        self.calls.append((path, dict(query_pairs)))
        return self.pages.pop(0)


class PaginationTest(unittest.TestCase):
    def test_collects_all_pages(self):
        client = FakeClient([
            {"certificates": [{"id": "a"}, {"id": "b"}], "total_count": 3},
            {"certificates": [{"id": "c"}], "total_count": 3},
        ])
        certs, total = lc.collect_certificates(client, [], now=FIXED_NOW)
        self.assertEqual([c["id"] for c in certs], ["a", "b", "c"])
        self.assertEqual(total, 3)
        self.assertEqual(client.calls[0][1]["offset"], "0")
        self.assertEqual(client.calls[1][1]["offset"], "2")

    def test_limit_caps_records(self):
        client = FakeClient([
            {"certificates": [{"id": "a"}, {"id": "b"}], "total_count": 2},
        ])
        certs, total = lc.collect_certificates(client, [], limit=1, now=FIXED_NOW)
        self.assertEqual(len(certs), 1)
        self.assertEqual(total, 2)

    def test_empty_page_stops_pagination(self):
        client = FakeClient([{"certificates": [], "total_count": 0}])
        certs, total = lc.collect_certificates(client, [], now=FIXED_NOW)
        self.assertEqual(certs, [])
        self.assertEqual(total, 0)
        self.assertEqual(len(client.calls), 1)


class RenderTest(unittest.TestCase):
    def test_empty_table(self):
        output = lc.render_table([])
        self.assertIn("共 0 张证书", output)
        self.assertIn("到期分级", output)

    def test_table_contains_certificate_fields(self):
        cert = lc.normalize_certificate({
            "id": "abcdef1234567890",
            "name": "example.com",
            "type": "DV_SSL_CERT",
            "domain": "example.com",
            "status": "ISSUED",
            "expire_time": "2026-12-31 23:59:59",
        }, now=FIXED_NOW)
        output = lc.render_table([cert])
        self.assertIn("example.com", output)
        self.assertIn("已签发", output)
        self.assertIn("49", output)

    def test_detail_contains_labels(self):
        cert = lc.normalize_show_payload({"id": "abcdef", "status": "ISSUED"}, now=FIXED_NOW)
        output = lc.render_detail(cert)
        self.assertIn("证书 ID", output)
        self.assertIn("到期分级", output)


class ReadOnlyAuditTest(unittest.TestCase):
    def test_only_get_requests(self):
        source = open(os.path.join(SCRIPT_DIR, "list_certificates.py"), encoding="utf-8").read()
        self.assertIn('method="GET"', source)
        for method in ("POST", "PUT", "PATCH", "DELETE"):
            self.assertNotIn('method="%s"' % method, source)
        self.assertNotIn("http.client", source)

    def test_only_read_only_paths(self):
        self.assertEqual(lc.LIST_PATH, "/v3/scm/certificates")
        self.assertEqual(lc.SHOW_PATH, "/v3/scm/certificates/{certificate_id}")


if __name__ == "__main__":
    unittest.main()
