#!/usr/bin/env python3
"""
OBS Security Auditor — Comprehensive bucket security configuration audit.

Checks 10 security dimensions, assigns a weighted score (0-100),
and generates a report with risk severity levels and remediation recommendations.

Usage:
    python3 obs_security_auditor.py audit --bucket {bucket} [--endpoint {endpoint}] [--output {file}] [--format text|json]

All operations are read-only (R3). No mutations to bucket configuration or objects.
Credentials are read from environment variables or obsutil config — never hardcoded.
"""

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone


# Constants & Scoring Model

SKILL_NAME = "huawei-cloud-obs-security-audit"

SCORING_MODEL = {
    "acl":            {"max": 15, "weight": "High"},
    "bpa":            {"max": 15, "weight": "High"},
    "encryption":     {"max": 15, "weight": "High"},
    "versioning":     {"max": 10, "weight": "Medium"},
    "replication":    {"max": 10, "weight": "Medium"},
    "https":          {"max": 15, "weight": "High"},
    "logging":        {"max": 10, "weight": "Medium"},
    "referer":        {"max": 5,  "weight": "Medium"},
    "cors":           {"max": 5,  "weight": "Low"},
    "naming":         {"max": 10, "weight": "Low"},
}

GRADE_LEVELS = [
    (99, "Excellent", "Security configuration is comprehensive"),
    (77, "Good", "Basically secure, some improvements needed"),
    (55, "Fair", "Security risks exist, remediation required"),
    (0,  "High Risk", "Critical security vulnerabilities, immediate remediation required"),
]

# Sequential prefix patterns (timestamps, dates, sequential IDs, alphabetic sequences)
SEQUENTIAL_PATTERNS = [
    re.compile(r'^\d{4}-\d{2}-\d{2}'),          # date prefix: 2024-01-15
    re.compile(r'^\d{8}'),                       # compact date: 20240115
    re.compile(r'^\d{10,}'),                     # timestamp: 1699836400
    re.compile(r'^[a-f0-9]{32}'),                # full hex hash (random — NOT sequential)
    re.compile(r'^\d{6,}'),                      # sequential numeric ID: 000001
]


# CLI Helper

def run_command(cmd, timeout=30):
    """Run a shell command and return (returncode, stdout, stderr).

    AST4-safe: commands are constructed internally from validated bucket names
    and fixed subcommand strings — no user input is passed raw to the shell.
    Uses shlex.split for safe argument tokenization instead of shell=True.
    """
    import shlex
    try:
        result = subprocess.run(
            shlex.split(cmd), shell=False, capture_output=True, text=True, timeout=timeout
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return 124, "", "Command timed out"
    except Exception as e:
        return 1, "", str(e)


def hcloud_obs(subcommand, bucket, args="", endpoint=None):
    """Run an hcloud obs passthrough command wrapped with skill-quality-cli.
    Format: hcloud obs <subcommand> obs://{bucket} [args]
    e.g. hcloud obs stat obs://{bucket}
         hcloud obs bucketpolicy obs://{bucket} -method=get
         hcloud obs ls obs://{bucket} -limit=1000 -s
    """
    cmd = f"skill-quality-cli run --skill-name {SKILL_NAME} -- hcloud obs {subcommand} obs://{bucket}"
    if args:
        cmd += f" {args}"
    if endpoint:
        cmd += f" -e={endpoint}"
    return run_command(cmd)


def _error_text(out, err):
    """Return error text from whichever stream has content.
    
    obsutil passthrough writes errors to stdout (not stderr), so we
    check both and return whichever is non-empty.
    """
    text = err.strip() if err.strip() else out.strip()
    return text


def _is_not_configured(out, err):
    """Check if output indicates 'not configured' (404 / NoSuchXxx / not found).
    
    obsutil passthrough writes errors to stdout, so we check both streams.
    """
    combined = (out + "\n" + err).lower()
    return ("404" in combined or
            "nosuch" in combined or
            "not found" in combined or
            "no policy" in combined or
            "no cors" in combined or
            "no encryption" in combined or
            "no such" in combined)


def _is_unsupported(out, err):
    """Check if output indicates the subcommand is not supported."""
    combined = (out + "\n" + err).lower()
    return ("unknown" in combined or
            "not supported" in combined or
            "unrecognized" in combined or
            "no such command" in combined)


# Audit Checks — each returns (score, max_score, status, detail, remediation)

def check_acl(bucket, endpoint=None):
    """Check 1: Bucket ACL permissions."""
    rc, out, err = hcloud_obs("stat", bucket, args="-acl", endpoint=endpoint)
    max_score = SCORING_MODEL["acl"]["max"]

    if rc != 0:
        return 0, max_score, "ERROR", f"Failed to get bucket stat: {_error_text(out, err)}", "Verify credentials and bucket name"

    acl = "unknown"
    for line in out.splitlines():
        line_lower = line.strip().lower()
        if "acl" in line_lower and ("private" in line_lower or "public" in line_lower):
            acl = line_lower.split(":")[-1].strip() if ":" in line_lower else line_lower
            break
        if "private" in line_lower and "acl" not in line_lower:
            # obsutil stat may show "ACL: private" or just the permission
            pass

    # More robust extraction
    if "public-read-write" in out.lower():
        acl = "public-read-write"
    elif "public-read" in out.lower():
        acl = "public-read"
    elif "private" in out.lower():
        acl = "private"

    if acl == "private":
        return max_score, max_score, "PASS", "Bucket ACL is private", "No action needed"
    elif acl == "public-read":
        return 5, max_score, "WARN", "Bucket ACL is public-read", "Set ACL to private unless public access is intentionally required"
    elif acl == "public-read-write":
        return 0, max_score, "CRITICAL", "Bucket ACL is public-read-write", "Immediately set ACL to private — public-read-write allows anyone to write"
    else:
        return 0, max_score, "WARN", f"ACL status unclear: {acl}", "Verify ACL manually via hcloud obs stat"


def check_bpa(bucket, endpoint=None):
    """Check 2: Block Public Access (BPA) status.

    Tries the obsutil dedicated ``get-public-access-block`` subcommand first.
    If that subcommand is unavailable, falls back to analyzing the bucket
    policy JSON for explicit public-access deny statements.
    """
    max_score = SCORING_MODEL["bpa"]["max"]

    # Try obsutil dedicated BPA subcommand first
    rc, out, err = hcloud_obs("get-public-access-block", bucket, endpoint=endpoint)

    if rc == 0:
        out_lower = out.lower()
        if "true" in out_lower or "enabled" in out_lower or ("block" in out_lower and "allow" not in out_lower):
            return max_score, max_score, "PASS", "BPA is enabled", "No action needed"
        else:
            return 0, max_score, "CRITICAL", "BPA is disabled", "Enable Block Public Access to prevent unintended public access"

    # Dedicated subcommand not available — fall back to bucket policy analysis
    rc, out, err = hcloud_obs("bucketpolicy -method=get", bucket, endpoint=endpoint)

    if rc != 0:
        if _is_not_configured(out, err):
            return 0, max_score, "CRITICAL", "BPA is not enabled (no bucket policy and BPA subcommand unavailable)", "Enable Block Public Access in OBS console"
        return 0, max_score, "WARN", f"Failed to query BPA: {_error_text(out, err)}", "Verify BPA status manually via OBS console"

    # Analyze bucket policy for public access denial statements
    try:
        data = json.loads(out)
        # Check for explicit deny on public access patterns
        statements = []
        if isinstance(data, dict):
            if "statement" in data:
                statements = data["statement"] if isinstance(data["statement"], list) else [data["statement"]]
            elif "Statement" in data:
                statements = data["Statement"] if isinstance(data["Statement"], list) else [data["Statement"]]

        has_public_deny = False
        for stmt in statements:
            stmt_str = json.dumps(stmt).lower()
            effect = stmt.get("Effect", stmt.get("effect", "")).lower() if isinstance(stmt, dict) else ""
            principal = str(stmt.get("Principal", stmt.get("principal", ""))).lower() if isinstance(stmt, dict) else ""
            if effect == "deny" and ("*" in principal or "anonymous" in principal or "everyone" in principal):
                has_public_deny = True
                break

        if has_public_deny:
            return max_score, max_score, "PASS", "Bucket policy contains explicit deny for public access (indirect BPA)", "Consider enabling dedicated BPA feature for comprehensive protection"
        else:
            return 0, max_score, "CRITICAL", "BPA is not configured (no dedicated BPA and no public access deny in policy)", "Enable Block Public Access in OBS console"
    except (json.JSONDecodeError, TypeError):
        return 0, max_score, "WARN", f"BPA status unclear: {out.strip()[:200]}", "Verify BPA status manually via OBS console"


def _find_bpa_value(data, depth=0):
    """Recursively search a dict/list for a BPA-related key and return its value."""
    if depth > 10:
        return None
    if isinstance(data, dict):
        for key, val in data.items():
            key_lower = str(key).lower()
            if "blockpublicaccess" in key_lower or "block_public_access" in key_lower:
                return val
            result = _find_bpa_value(val, depth + 1)
            if result is not None:
                return result
    elif isinstance(data, list):
        for item in data:
            result = _find_bpa_value(item, depth + 1)
            if result is not None:
                return result
    return None


def _extract_nested(data, parent_keys, child_keys):
    """Search a dict for any of *parent_keys* (case-insensitive) and return
    the value of the first matching *child_keys* found inside it.

    Returns ``None`` if nothing is found.
    """
    parent_keys_lower = [k.lower() for k in parent_keys]
    child_keys_lower = [k.lower() for k in child_keys]

    def _search(obj):
        if isinstance(obj, dict):
            obj_lower = {k.lower(): v for k, v in obj.items()}
            # Check if any parent key exists at this level
            for pk in parent_keys_lower:
                if pk in obj_lower:
                    parent_val = obj_lower[pk]
                    if isinstance(parent_val, dict):
                        parent_val_lower = {k.lower(): v for k, v in parent_val.items()}
                        for ck in child_keys_lower:
                            if ck in parent_val_lower:
                                return parent_val_lower[ck]
                    return parent_val
            # Recurse into values
            for v in obj.values():
                result = _search(v)
                if result is not None:
                    return result
        elif isinstance(obj, list):
            for item in obj:
                result = _search(item)
                if result is not None:
                    return result
        return None

    return _search(data)


def check_encryption(bucket, endpoint=None):
    """Check 3: Bucket encryption configuration."""
    rc, out, err = hcloud_obs("encryption -method=get", bucket, endpoint=endpoint)
    max_score = SCORING_MODEL["encryption"]["max"]

    if rc != 0:
        if _is_not_configured(out, err):
            return 0, max_score, "CRITICAL", "No encryption configured", "Enable SSE-KMS encryption for sensitive data"
        if _is_unsupported(out, err):
            return 0, max_score, "WARN", "Encryption check unavailable (obsutil subcommand not supported)", "Verify encryption manually via OBS console"
        return 0, max_score, "WARN", f"Failed to query encryption: {_error_text(out, err)}", "Verify IAM permissions for GetBucketEncryption"

    out_lower = out.lower()
    if "kms" in out_lower:
        return max_score, max_score, "PASS", "SSE-KMS encryption enabled", "No action needed"
    elif "sse-obs" in out_lower or "sse_obs" in out_lower:
        return 12, max_score, "PASS", "SSE-OBS encryption enabled", "Consider upgrading to SSE-KMS for key management"
    elif "sse-c" in out_lower or "customer" in out_lower:
        return 10, max_score, "PASS", "SSE-C encryption enabled", "Ensure customer keys are securely managed"
    else:
        try:
            data = json.loads(out)
            rules = data.get("ServerSideEncryptionConfiguration", {}).get("Rules", [])
            if rules:
                sse_type = rules[0].get("ApplyServerSideEncryptionByDefault", {}).get("SSEAlgorithm", "")
                if "kms" in sse_type.lower():
                    return max_score, max_score, "PASS", "SSE-KMS encryption enabled", "No action needed"
                elif "obs" in sse_type.lower():
                    return 12, max_score, "PASS", "SSE-OBS encryption enabled", "Consider upgrading to SSE-KMS"
                return 10, max_score, "PASS", f"Encryption type: {sse_type}", "Review encryption configuration"
            else:
                return 0, max_score, "CRITICAL", "No encryption rules configured", "Enable SSE-KMS encryption"
        except (json.JSONDecodeError, TypeError):
            return 0, max_score, "WARN", f"Encryption status unclear: {out.strip()[:200]}", "Verify encryption manually"


def check_versioning(bucket, endpoint=None):
    """Check 4: Multi-version control status."""
    rc, out, err = hcloud_obs("stat", bucket, endpoint=endpoint)
    max_score = SCORING_MODEL["versioning"]["max"]

    if rc != 0:
        return 0, max_score, "WARN", f"Failed to get bucket stat: {_error_text(out, err)}", "Verify credentials and bucket name"

    out_lower = out.lower()
    if "versioning" in out_lower and "enabled" in out_lower:
        return max_score, max_score, "PASS", "Versioning is enabled", "No action needed"
    elif "versioning" in out_lower and "suspended" in out_lower:
        return 0, max_score, "WARN", "Versioning is suspended", "Re-enable versioning for data recovery capability"
    else:
        return 0, max_score, "WARN", "Versioning is not enabled", "Enable versioning for accidental deletion recovery"


def check_replication(bucket, endpoint=None):
    """Check 5: Cross-region replication rules (parsed from bucket policy JSON).

    obsutil does not have a dedicated `replication` subcommand. We fetch the
    bucket policy JSON via `bucketpolicy -method=get` and search for
    replication-related fields (ReplicationConfiguration, replication, etc.).
    """
    max_score = SCORING_MODEL["replication"]["max"]
    rc, out, err = hcloud_obs("bucketpolicy -method=get", bucket, endpoint=endpoint)

    if rc != 0:
        if _is_not_configured(out, err):
            return 0, max_score, "WARN", "No cross-region replication configured (no bucket policy)", "Configure cross-region replication for disaster recovery"
        if _is_unsupported(out, err):
            return 0, max_score, "WARN", "Replication check unavailable (obsutil subcommand not supported)", "Verify replication manually via OBS console"
        return 0, max_score, "WARN", f"Failed to query bucket policy for replication: {_error_text(out, err)}", "Verify IAM permissions for GetBucketPolicy"

    # Search bucket policy JSON for replication-related fields
    out_lower = out.lower()
    if "replication" not in out_lower and "replicationconfiguration" not in out_lower:
        return 0, max_score, "WARN", "No cross-region replication configured (not found in bucket policy)", "Configure cross-region replication for disaster recovery"

    try:
        data = json.loads(out)
        # Look for ReplicationConfiguration in the policy
        rules = _extract_nested(data, ["ReplicationConfiguration", "replicationconfiguration"], ["Rules", "rules"])
        if rules and isinstance(rules, list) and len(rules) > 0:
            return max_score, max_score, "PASS", f"Replication configured ({len(rules)} rule(s) in bucket policy)", "No action needed"
        else:
            return 0, max_score, "WARN", "No replication rules found in bucket policy", "Configure cross-region replication"
    except (json.JSONDecodeError, TypeError):
        if "replication" in out_lower:
            return max_score, max_score, "PASS", "Replication configuration detected in bucket policy", "No action needed"
        return 0, max_score, "WARN", f"Replication status unclear: {out.strip()[:200]}", "Verify replication manually via OBS console"


def check_https(bucket, endpoint=None):
    """Check 6: HTTPS enforcement via bucket policy SecureTransport condition."""
    rc, out, err = hcloud_obs("bucketpolicy -method=get", bucket, endpoint=endpoint)
    max_score = SCORING_MODEL["https"]["max"]

    if rc != 0:
        if _is_not_configured(out, err):
            return 0, max_score, "CRITICAL", "No bucket policy configured — HTTPS not enforced", "Add a bucket policy with SecureTransport=true condition"
        return 0, max_score, "WARN", f"Failed to get bucket policy: {_error_text(out, err)}", "Verify IAM permissions for GetBucketPolicy"

    out_lower = out.lower()
    has_secure_transport = "securetransport" in out_lower and "true" in out_lower

    if has_secure_transport:
        return max_score, max_score, "PASS", "Bucket policy enforces HTTPS (SecureTransport=true)", "No action needed"
    else:
        return 0, max_score, "CRITICAL", "Bucket policy does not enforce HTTPS", "Add SecureTransport=true condition to bucket policy to enforce HTTPS-only access"


def check_logging(bucket, endpoint=None):
    """Check 7: Bucket logging status (parsed from bucket policy JSON).

    obsutil does not have a dedicated `logging` subcommand. We fetch the
    bucket policy JSON via `bucketpolicy -method=get` and search for
    logging-related fields (LoggingEnabled, TargetBucket, etc.).
    """
    max_score = SCORING_MODEL["logging"]["max"]
    rc, out, err = hcloud_obs("bucketpolicy -method=get", bucket, endpoint=endpoint)

    if rc != 0:
        if _is_not_configured(out, err):
            return 0, max_score, "WARN", "Bucket logging is not enabled (no bucket policy)", "Enable bucket logging to record all access requests"
        if _is_unsupported(out, err):
            return 0, max_score, "WARN", "Logging check unavailable (obsutil subcommand not supported)", "Verify logging manually via OBS console"
        return 0, max_score, "WARN", f"Failed to query bucket policy for logging: {_error_text(out, err)}", "Verify IAM permissions for GetBucketPolicy"

    # Search bucket policy JSON for logging-related fields
    out_lower = out.lower()
    if "logging" not in out_lower and "targetbucket" not in out_lower:
        return 0, max_score, "WARN", "Bucket logging is not configured (not found in bucket policy)", "Enable bucket logging to record all access requests"

    if "targetbucket" in out_lower or "loggingenabled" in out_lower or "target_grant" in out_lower:
        return max_score, max_score, "PASS", "Bucket logging is enabled (found in bucket policy)", "No action needed"

    try:
        data = json.loads(out)
        # Look for LoggingEnabled in the policy
        logging_config = _extract_nested(data, ["LoggingEnabled", "loggingenabled"], ["TargetBucket", "targetbucket"])
        if logging_config:
            return max_score, max_score, "PASS", "Bucket logging is enabled (found in bucket policy)", "No action needed"
        else:
            return 0, max_score, "WARN", "Bucket logging is not configured (no LoggingEnabled in policy)", "Enable bucket logging"
    except (json.JSONDecodeError, TypeError):
        if "logging" in out_lower:
            return max_score, max_score, "PASS", "Logging configuration detected in bucket policy", "No action needed"
        return 0, max_score, "WARN", f"Logging status unclear: {out.strip()[:200]}", "Verify logging manually via OBS console"


def check_referer(bucket, endpoint=None):
    """Check 8: Referer anti-hotlinking configuration (parsed from bucket policy JSON).

    obsutil does not have a dedicated `referer` subcommand. We fetch the
    bucket policy JSON via `bucketpolicy -method=get` and search for
    referer-related fields (RefererConfiguration, RefererList, etc.).
    """
    max_score = SCORING_MODEL["referer"]["max"]
    rc, out, err = hcloud_obs("bucketpolicy -method=get", bucket, endpoint=endpoint)

    if rc != 0:
        if _is_not_configured(out, err):
            return 0, max_score, "WARN", "No Referer anti-hotlinking configured (no bucket policy)", "Configure Referer rules to prevent unauthorized hotlinking"
        if _is_unsupported(out, err):
            return 0, max_score, "WARN", "Referer check unavailable (obsutil subcommand not supported)", "Verify Referer configuration manually via OBS console"
        return 0, max_score, "WARN", f"Failed to query bucket policy for Referer: {_error_text(out, err)}", "Verify IAM permissions for GetBucketPolicy"

    # Search bucket policy JSON for referer-related fields
    out_lower = out.lower()
    if "referer" not in out_lower:
        return 0, max_score, "WARN", "No Referer anti-hotlinking configured (not found in bucket policy)", "Configure Referer rules to prevent unauthorized hotlinking"

    if "referer" in out_lower and ("allow" in out_lower or "deny" in out_lower or "domain" in out_lower):
        return max_score, max_score, "PASS", "Referer anti-hotlinking is configured (found in bucket policy)", "No action needed"

    try:
        data = json.loads(out)
        # Look for RefererConfiguration in the policy
        referer_config = _extract_nested(data, ["RefererConfiguration", "refererconfiguration"], ["RefererList", "refererlist", "Rules", "rules"])
        if referer_config:
            return max_score, max_score, "PASS", "Referer anti-hotlinking is configured (found in bucket policy)", "No action needed"
        else:
            return 0, max_score, "WARN", "Referer anti-hotlinking is not configured (no RefererConfiguration in policy)", "Configure Referer rules"
    except (json.JSONDecodeError, TypeError):
        if "referer" in out_lower:
            return max_score, max_score, "PASS", "Referer configuration detected in bucket policy", "No action needed"
        return 0, max_score, "WARN", f"Referer status unclear: {out.strip()[:200]}", "Verify Referer configuration manually via OBS console"


def check_cors(bucket, endpoint=None):
    """Check 9: CORS rules."""
    rc, out, err = hcloud_obs("cors -method=get", bucket, endpoint=endpoint)
    max_score = SCORING_MODEL["cors"]["max"]

    if rc != 0:
        # No CORS configured — acceptable if no cross-domain access needed
        if _is_not_configured(out, err):
            return max_score, max_score, "PASS", "No CORS rules configured (acceptable if no cross-domain access needed)", "No action needed unless cross-domain access is required"
        return 0, max_score, "WARN", f"Failed to query CORS: {_error_text(out, err)}", "Verify IAM permissions for GetBucketCors"

    out_lower = out.lower()
    has_wildcard = "*" in out

    if has_wildcard:
        return 2, max_score, "WARN", "CORS rules contain wildcard (*) origin", "Restrict CORS origins to specific domains instead of wildcard"
    elif "allowedorigin" in out_lower or "allowedmethod" in out_lower or "corsrule" in out_lower:
        return max_score, max_score, "PASS", "CORS rules configured with specific origins", "No action needed"
    else:
        return max_score, max_score, "PASS", "No CORS rules configured (acceptable if no cross-domain access needed)", "No action needed"


def check_naming(bucket, endpoint=None, limit=1000):
    """Check 10: Object naming pattern (sequential vs random prefix)."""
    rc, out, err = hcloud_obs(f"ls -s -limit={limit}", bucket, endpoint=endpoint)
    max_score = SCORING_MODEL["naming"]["max"]

    if rc != 0:
        return 0, max_score, "WARN", f"Failed to list objects: {_error_text(out, err)}", "Verify permissions and bucket accessibility"

    # Extract object keys from ls output
    keys = []
    for line in out.strip().splitlines():
        line = line.strip()
        if not line or line.startswith("Bucket:") or line.startswith("Total:") or line.startswith("Folder:"):
            continue
        # obsutil -s output format: "Key  LastModified  Size"
        parts = line.split()
        if parts:
            keys.append(parts[0])

    if not keys:
        return max_score, max_score, "PASS", "No objects found or empty bucket", "No naming pattern risk"

    # Analyze prefixes
    sequential_count = 0
    random_count = 0

    for key in keys:
        prefix = key.split("/")[0] if "/" in key else key[:16]
        is_sequential = False

        # Check for date/timestamp/sequential numeric patterns
        if re.match(r'^\d{4}[-/]\d{2}[-/]\d{2}', prefix):       # date: 2024-01-15
            is_sequential = True
        elif re.match(r'^\d{8}', prefix):                          # compact date: 20240115
            is_sequential = True
        elif re.match(r'^\d{10,}', prefix):                        # timestamp
            is_sequential = True
        elif re.match(r'^\d{5,}$', prefix):                        # sequential numeric ID
            is_sequential = True
        elif re.match(r'^[a-z]+0*1$', prefix, re.I):               # alphabetic sequence start
            is_sequential = True

        # Hex hash prefix (32+ hex chars) is random — not sequential
        if re.match(r'^[a-f0-9]{16,}$', prefix):
            is_sequential = False
            random_count += 1
        elif is_sequential:
            sequential_count += 1
        else:
            random_count += 1

    total = len(keys)
    sequential_ratio = sequential_count / total if total > 0 else 0

    if sequential_ratio >= 0.7:
        return 0, max_score, "CRITICAL", f"Object naming uses sequential prefixes ({sequential_count}/{total} objects)", "Use hex hash prefixes instead of sequential naming to avoid performance and security issues"
    elif sequential_ratio >= 0.3:
        return 5, max_score, "WARN", f"Object naming partially uses sequential prefixes ({sequential_count}/{total} objects)", "Migrate to hex hash prefixes for better performance and security"
    else:
        return max_score, max_score, "PASS", f"Object naming uses random prefixes ({random_count}/{total} objects)", "No action needed"


# Audit Runner

AUDIT_CHECKS = [
    ("acl",          "Bucket ACL Permissions",        check_acl),
    ("bpa",          "Block Public Access (BPA)",     check_bpa),
    ("encryption",   "Bucket Encryption",             check_encryption),
    ("versioning",   "Multi-Version Control",         check_versioning),
    ("replication",  "Cross-Region Replication",      check_replication),
    ("https",        "HTTPS Enforcement",             check_https),
    ("logging",      "Bucket Logging",                check_logging),
    ("referer",      "Referer Anti-Hotlinking",       check_referer),
    ("cors",         "CORS Rules",                    check_cors),
    ("naming",       "Object Naming Pattern",         check_naming),
]


def run_full_audit(bucket, endpoint=None):
    """Run all 10 security checks and return a comprehensive report."""
    results = []
    total_score = 0
    max_total = 0

    for key, name, check_fn in AUDIT_CHECKS:
        max_score = SCORING_MODEL[key]["max"]
        max_total += max_score

        try:
            score, mx, status, detail, remediation = check_fn(bucket, endpoint)
        except Exception as e:
            score, mx, status, detail, remediation = 0, max_score, "ERROR", f"Check failed: {e}", "Review error and retry"

        total_score += score
        results.append({
            "id": key,
            "name": name,
            "score": score,
            "max_score": mx,
            "status": status,
            "detail": detail,
            "remediation": remediation,
            "weight": SCORING_MODEL[key]["weight"],
        })

    # Determine grade
    grade = "High Risk"
    grade_desc = "Critical security vulnerabilities, immediate remediation required"
    for threshold, g, desc in GRADE_LEVELS:
        if total_score >= threshold:
            grade = g
            grade_desc = desc
            break

    # Build risk list (CRITICAL and WARN items)
    risk_items = [r for r in results if r["status"] in ("CRITICAL", "WARN", "ERROR")]
    risk_items.sort(key=lambda r: {"CRITICAL": 0, "ERROR": 1, "WARN": 2}.get(r["status"], 3))

    # Build remediation list (sorted by priority)
    remediation_list = []
    for r in risk_items:
        if r["status"] == "CRITICAL":
            remediation_list.append({"priority": "P0", "item": r["name"], "action": r["remediation"]})
    for r in risk_items:
        if r["status"] == "WARN":
            remediation_list.append({"priority": "P1", "item": r["name"], "action": r["remediation"]})

    report = {
        "bucket": bucket,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_score": total_score,
        "max_score": max_total,
        "grade": grade,
        "grade_description": grade_desc,
        "checks": results,
        "risk_items": risk_items,
        "remediation_priorities": remediation_list,
    }

    return report


def format_text_report(report):
    """Format the audit report as human-readable text."""
    lines = []
    lines.append("=" * 70)
    lines.append("OBS Security Audit Report")
    lines.append("=" * 70)
    lines.append(f"Bucket:       {report['bucket']}")
    lines.append(f"Timestamp:    {report['timestamp']}")
    lines.append(f"Total Score:  {report['total_score']}/{report['max_score']}")
    lines.append(f"Grade:        {report['grade']} — {report['grade_description']}")
    lines.append("")

    lines.append("-" * 70)
    lines.append("Per-Item Results")
    lines.append("-" * 70)
    for check in report["checks"]:
        status_icon = {"PASS": "✅", "WARN": "⚠️", "CRITICAL": "🔴", "ERROR": "❌"}.get(check["status"], "?")
        lines.append(f"  {status_icon} [{check['status']:8s}] {check['name']}")
        lines.append(f"     Score: {check['score']}/{check['max_score']} (Weight: {check['weight']})")
        lines.append(f"     Detail: {check['detail']}")
        if check["status"] != "PASS":
            lines.append(f"     Fix: {check['remediation']}")
        lines.append("")

    if report["risk_items"]:
        lines.append("-" * 70)
        lines.append("Risk Items (sorted by severity)")
        lines.append("-" * 70)
        for risk in report["risk_items"]:
            lines.append(f"  [{risk['status']:8s}] {risk['name']}: {risk['detail']}")
        lines.append("")

    if report["remediation_priorities"]:
        lines.append("-" * 70)
        lines.append("Remediation Recommendations (by priority)")
        lines.append("-" * 70)
        for rec in report["remediation_priorities"]:
            lines.append(f"  [{rec['priority']}] {rec['item']}: {rec['action']}")
        lines.append("")

    lines.append("=" * 70)
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="OBS Security Auditor — Comprehensive bucket security configuration audit"
    )
    parser.add_argument("audit", help="Run security audit")
    parser.add_argument("--bucket", required=True, help="Target bucket name (no obs:// prefix)")
    parser.add_argument("--endpoint", default=None, help="OBS endpoint override")
    parser.add_argument("--output", default=None, help="Output file path for the report")
    parser.add_argument("--format", default="text", choices=["text", "json"], help="Output format (default: text)")

    args = parser.parse_args()

    print(f"Starting security audit for bucket: {args.bucket}", file=sys.stderr)

    report = run_full_audit(args.bucket, args.endpoint)

    if args.format == "json":
        output = json.dumps(report, indent=2, ensure_ascii=False)
    else:
        output = format_text_report(report)

    print(output)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output)
        print(f"\nReport saved to: {args.output}", file=sys.stderr)

    # Exit code: 0 if no critical/error risks, 1 if critical or error risks exist
    has_critical = any(r["status"] in ("CRITICAL", "ERROR") for r in report["risk_items"])
    sys.exit(1 if has_critical else 0)


if __name__ == "__main__":
    main()
