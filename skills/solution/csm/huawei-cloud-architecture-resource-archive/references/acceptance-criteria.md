# Acceptance Criteria - huawei-cloud-architecture-resource-archive

## Overview

This document defines the pass/fail criteria for testing this skill, used for pre-PR validation and release acceptance.

## 1. CLI Command Format Verification

| Check item | ✅ Correct example | ❌ Wrong example |
|------------|-------------------|-----------------|
| Service name uppercase | `hcloud ECS ListServersDetails` | ~~`hcloud ecs ListServersDetails`~~ |
| Operation PascalCase | `hcloud VPC ListSecurityGroups/v3` | ~~`hcloud VPC listsecuritygroups`~~ |
| Region parameter | `--cli-region=cn-north-4` | ~~`--region=cn-north-4`~~ |
| IAM Keystone prefix | `hcloud IAM KeystoneListUsers` | ~~`hcloud IAM ListUsers`~~ |
| VPC v3 suffix | `hcloud VPC ListSecurityGroups/v3` | ~~`hcloud VPC ListSecurityGroups`~~ |

## 2. Parameter Format Verification

| Parameter | Required | Default | Verification criteria |
|-----------|----------|---------|------------------------|
| `--account` | Yes | — | Non-empty string, used for output directory naming |
| `--regions` | No | auto discovery | Comma-separated valid region IDs |
| `--services` | No | all 35 services | Comma-separated known service names |
| `--skip-check` | No | false | Boolean flag |
| `--skip-query` | No | false | Boolean flag |

## 3. Output Format Verification

| Check item | Criteria |
|------------|----------|
| Raw JSON | .json files exist under each service/region directory, JSON is parseable |
| Converted JSON | Converted JSON contains `resource_type`, `resource_id`, `name` fields |
| Marker table Excel | .xlsx file can be opened, contains 15-column header, one resource per row |
| store JSON | `_resource_store.json` is parseable, contains a resources array |

## 4. Error Handling Verification

| Scenario | Expected behavior |
|----------|-------------------|
| KooCLI not installed | Step 1 auto-installs or prompts the install command |
| AK/SK not configured | Prompt to set environment variables, abort execution |
| Insufficient permission (403) | Read iam-policies.md, show required permissions, pause and wait |
| Region without permission | Log the error and continue querying other regions |
| Service without resources | Output empty JSON, no error |
| Dormant CCE cluster | Log a warning and skip the cluster |

## 5. Security Verification

| Check item | Criteria |
|------------|----------|
| No AK/SK hardcoding | `grep -r "access.key\|secret.key" scripts/ --include="*.py"` does not match plaintext values |
| No plaintext credential output | Marker table and JSON do not contain AK/SK fields |
| Read-only operations | All hcloud commands are List/Show operations, no Create/Update/Delete |

## Pass Criteria

The PR can only be merged when all 5 categories of verification pass.
