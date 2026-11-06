#!/usr/bin/env python3
"""Regression tests for the huawei-cloud-ecs-lifecycle linked resource query capability
(Issue huaweicloud-skills#1011 / vod-skill#4090).

Static tests that parse the skill's SKILL.md and references and assert:
- required sections exist (Overview, Prerequisites, Workflow, Core Commands, Reference Documents)
- the new "Linked Resource Queries" section exists and documents EVS/VPC/security-group/EIP queries
- every documented hcloud command carries --cli-region and uses the KooCLI format
  (uppercase service + PascalCase operation)
- referenced reference files exist
- SKILL.md stays within the 500-line limit and hardcodes no AK/SK

Run these tests with pytest (`python3 -m pytest tests/test_linked_resource_query.py`); the cases
are module-level functions, so direct execution (`python3 tests/test_linked_resource_query.py`)
via `unittest.main` collects 0 tests.
"""
import os
import re
import sys

SKILL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
SKILL_MD = os.path.join(SKILL_DIR, "SKILL.md")
REFERENCES_DIR = os.path.join(SKILL_DIR, "references")


def load_skill_md():
    with open(SKILL_MD, encoding="utf-8") as fh:
        return fh.read()


def test_required_sections_present():
    text = load_skill_md()
    for section in (
        "## Overview",
        "## Prerequisites",
        "## Workflow",
        "## Core Commands",
        "## Parameter Confirmation",
        "## Reference Documents",
    ):
        assert section in text, f"missing required section {section}"


def test_linked_resource_query_section_present():
    text = load_skill_md()
    assert "### Linked Resource Queries" in text, "missing Linked Resource Queries section"
    for term in ("EVS", "VPC", "security group", "EIP"):
        assert term.lower() in text.lower(), f"Linked Resource Queries should mention {term}"


_COMMAND_LINE_RE = re.compile(r"^hcloud\s+(?P<service>[A-Z][A-Z0-9]+)\s+(?P<op>[A-Za-z0-9_/]+)(?P<args>.*)$")


def _iter_hcloud_command_lines(text):
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("hcloud "):
            yield line


def test_all_commands_have_cli_region():
    text = load_skill_md()
    commands = list(_iter_hcloud_command_lines(text))
    assert commands, "expected at least one hcloud command in SKILL.md"
    for cmd in commands:
        assert "--cli-region=" in cmd, f"command missing --cli-region: {cmd}"


def test_commands_follow_koocli_format():
    text = load_skill_md()
    for cmd in _iter_hcloud_command_lines(text):
        m = _COMMAND_LINE_RE.match(cmd)
        assert m, f"command does not match hcloud <SERVICE> <Operation> format: {cmd}"
        assert m.group("service").isupper(), f"service should be uppercase: {cmd}"
        op = m.group("op")
        assert re.match(r"^[A-Z][A-Za-z0-9]+(/[vV][0-9]+)?$", op), f"operation should be PascalCase(+version): {cmd}"


def test_linked_query_commands_documented():
    text = load_skill_md()
    expected_ops = (
        "ListServerVolumeAttachments",
        "ShowVolume",
        "ListSnapshots",
        "ShowSnapshot",
        "ShowVpc",
        "ListSubnets",
        "ShowSubnet",
        "ListSecurityGroups",
        "ShowSecurityGroup",
        "ListSecurityGroupRules",
        "ListPublicips",
        "ShowPublicip",
    )
    for op in expected_ops:
        assert op in text, f"linked query operation {op} should be documented in SKILL.md"


def test_reference_files_exist():
    expected = (
        "acceptance-criteria.md",
        "cli-installation-guide.md",
        "dataflow-diagram.md",
        "iam-policies.md",
        "linked-resource-queries.md",
        "verification-method.md",
    )
    for name in expected:
        path = os.path.join(REFERENCES_DIR, name)
        assert os.path.isfile(path), f"missing reference file {name}"


def test_reference_documents_linked_in_skill_md():
    text = load_skill_md()
    for name in ("iam-policies.md", "cli-installation-guide.md", "verification-method.md",
                 "linked-resource-queries.md", "dataflow-diagram.md", "acceptance-criteria.md"):
        assert name in text, f"SKILL.md Reference Documents should link {name}"


def test_skill_md_line_count_within_limit():
    with open(SKILL_MD, encoding="utf-8") as fh:
        lines = fh.read().splitlines()
    assert len(lines) <= 500, f"SKILL.md has {len(lines)} lines, limit is 500"


def test_no_ak_sk_hardcoded():
    text = load_skill_md()
    for secret in ("AK=", "SK=", "ACCESS_KEY", "SECRET_KEY", "APIGW_KEY", "password="):
        assert secret.lower() not in text.lower(), f"possible hardcoded secret pattern: {secret}"


def test_argument_patience_indexed_form():
    text = load_skill_md()
    assert "security_group_id.1=" in text, "--security_group_id.1= indexed filter should be documented"
    assert "port_id.1=" in text, "--port_id.1= indexed filter should be documented"


def test_frontmatter_valid():
    text = load_skill_md()
    assert text.startswith("---"), "SKILL.md must start with frontmatter"
    assert "name: huawei-cloud-ecs-lifecycle" in text.split("---")[1], "frontmatter name mismatch"
    assert "description:" in text.split("---")[1], "frontmatter description missing"


if __name__ == "__main__":
    import unittest

    sys.exit(unittest.main(module=__name__, argv=sys.argv[:1]))