# Acceptance Criteria — huawei-cloud-cce-cluster-migrator

This document establishes the testing specifications, pass conditions, and failure criteria for the `huawei-cloud-cce-cluster-migrator` skill across unit testing, CLI integration testing, security scanning, and documentation validation.

---

## 1. Unit Testing Criteria (`scripts/`)

Unit testing validates the automated shell and Python test harness under `scripts/`, evaluating test variable parsing, concurrent worker dispatching, and CLI output result verification without generating report files.

### Test Execution

```bash
bash scripts/test-cli-commands.sh -s . -r cn-north-4 -j 4
```

### Pass Criteria

- **Execution Integrity**: The test runner `scripts/test-cli-commands.sh` executes with `set -euo pipefail` and exits with status code `0`.
- **Test Case Discovery**: Embedded Python parser successfully loads all test cases defined in `templates/test-vars.json` without syntax or JSON errors.
- **Suite Completion**: All 13 registered test cases (`TC-01` through `TC-13`) complete with status `PASS`.
- **CLI Output Verification**: Test results and execution summary are directly returned in the CLI output, confirming `13/13 passed`, `0 failed`, and all expected test cases verified without persisting test-report files.
- **Output Token Matching**: Every test case output contains its expected token string (e.g., `Cluster`, `clusterFlavorSpecs`, `Addon`, `cce:cluster:list`, `5.0`, `nat_gateways`, `snat_rules`, `auths`, `namespaces`, `vpcs`, `loadbalancers`, `publicips`).

### Fail Criteria

- Runner terminates prematurely with a non-zero exit code or uncaught shell/python error.
- Any test case reports `FAIL` due to command execution error, unexpected output token, or timeout.
- Missing configuration files (`templates/test-vars.json` not found).
- Python binary not found or failing to parse test cases.
- CLI output reports failed test cases (`failed > 0`) or fails to output test execution summary.

---

## 2. Integration Testing Criteria (CLI Commands End-to-End Execution)

Integration testing verifies end-to-end KooCLI command execution across target cloud services (CCE, NAT, SWR, VPC, ELB, EIP, IAM) and Kubernetes toolchain connectivity against live endpoints.

### Scope & Execution Flow

1. **Target Cluster Assessment & Sizing**:
   - `hcloud CCE ListClusters --cli-region=<region_id>`
   - `hcloud CCE GetClusterFlavorSpecs --cli-region=<region_id> --clusterType=VirtualMachine`
   - `hcloud CCE ListAddonTemplates --cli-region=<region_id>`
2. **IAM Policy & Schema Verification**:
   - `hcloud IAM GetAuthorizationSchemaV5 --cli-region=<region_id> --service_code=cce`
   - `hcloud IAM GetPolicyVersionV5 --cli-region=<region_id> --policy_id=CCEFullPolicy --version_id=v1`
   - `hcloud IAM GetPolicyVersionV5 --cli-region=<region_id> --policy_id=CCEReadOnlyPolicy --version_id=v1`
3. **Network, Egress & SWR Registry**:
   - `hcloud NAT ListNatGateways --cli-region=<region_id>`
   - `hcloud NAT ListNatGatewaySnatRules --cli-region=<region_id>`
   - `hcloud VPC ListVpcs --cli-region=<region_id>`
   - `hcloud SWR CreateSecret --cli-region=<region_id>`
   - `hcloud SWR ListNamespaces --cli-region=<region_id>`
4. **Traffic Ingress & Dedicated ELB**:
   - `hcloud ELB ListLoadBalancers/v3 --cli-region=<region_id>`
   - `hcloud EIP ListPublicips/v3 --cli-region=<region_id> --associate_instance_type.1=ELB`
5. **Cluster Access & Add-ons**:
   - `hcloud CCE update-kubeconfig --cluster-id={target_cluster_id} --region=cn-north-4`
   - `hcloud CCE ListAddonInstances --cli-region=<region_id> --cluster_id={target_cluster_id}`

### Pass Criteria

- **Valid JSON Responses**: All read-only commands return HTTP status `200` with well-formed JSON objects matching KooCLI schema.
- **Zero KooCLI Errors**: No error tags (`[USE_ERROR]`, `[OPENAPI_ERROR]`, or `[NETWORK_ERROR]`) emitted in command outputs.
- **IAM Policy Version Compliance**: Policy queries for `CCEFullPolicy` and `CCEReadOnlyPolicy` return `"Version": "5.0"`. Schema query returns official `cce:cluster:list` action.
- **SWR Authentication**: `hcloud SWR CreateSecret` outputs valid authentication payload parseable by Docker or Skopeo.
- **Mandatory Flags Adherence**: Every `hcloud` command specifies `--cli-region` (or `--region` for `update-kubeconfig`).
- **PascalCase Operation Conformity**: All operation names strictly follow PascalCase convention.

### Fail Criteria

- Command invocation returns `[USE_ERROR]` indicating unknown parameters or syntax errors.
- Command invocation returns `[OPENAPI_ERROR]` indicating invalid actions, schema errors, or unsupported endpoints.
- Authorization failure (`403 Forbidden`) due to missing IAM permissions.
- Outdated IAM policy versions returned (e.g. non-5.0 version or fabricated actions).

---

## 3. Security Scan Criteria (AK/SK Leaks & Sensitive Information)

Security scanning inspects the entire skill package to guarantee zero exposure of API keys, tokens, or credentials across documentation, scripts, and Kubernetes manifests.

### Scanning Scope

All files within the skill package, including `SKILL.md`, `references/`, `scripts/`, and `templates/`.

### Pass Criteria

- **Zero Hardcoded Credentials**: Scans across all repository files detect zero occurrences of:
  - Huawei Cloud Access Key IDs (AK) matching regular expression `(?i)(hw|hws|huawei)?_?(ak|access_key)[\s:=]+['"][A-Za-z0-9]{20}['"]`.
  - Huawei Cloud Secret Access Keys (SK) matching regular expression `(?i)(hw|hws|huawei)?_?(sk|secret_key)[\s:=]+['"][A-Za-z0-9]{40}['"]`.
  - Cryptographic private keys (`-----BEGIN.*PRIVATE KEY-----`).
  - Cleartext passwords or long-lived authentication tokens.
- **Manifest Parameterization**: Kubernetes templates (e.g., `image-migrator-auth.json`, `velero-sc-mapping.yaml`) use placeholder values or instruct users to supply secrets dynamically at runtime.
- **Dynamic Credential Handling**: SWR Docker login tokens are generated dynamically in memory via `hcloud SWR CreateSecret` and piped securely without persisting unencrypted tokens to disk.
- **Clean Execution Logs**: Verification test reports and log files contain no unmasked secret tokens.

### Fail Criteria

- Discovery of any static 20-character AK or 40-character SK in plain text.
- Plaintext database passwords, private keys, or API tokens committed in templates or documentation.
- Test logs or shell output recording unredacted credentials.

---

## 4. Document Validation Criteria (SKILL.md Format & Link Validity)

Document validation verifies structural compliance, markdown linting, and referential integrity across all skill files.

### Pass Criteria

- **Frontmatter Standard**: `SKILL.md` contains valid YAML frontmatter with `name`, `description`, and `tags`. The `name` attribute strictly matches `huawei-cloud-cce-cluster-migrator`.
- **Language Uniformity**: All documentation, reference guides, and templates are written strictly in English (excluding user-facing skill triggers).
- **Line Count Limits**: Total line count of `SKILL.md` is strictly under 500 lines.
- **Required Sections Present**: `SKILL.md` contains all mandated sections:
  - `Overview`
  - `Prerequisites`
  - `Workflow`
  - `Core Commands`
  - `Parameter Confirmation`
  - `KooCLI Command Format Standard`
  - `Reference Documents`
- **Link Integrity**: All relative links in markdown files (e.g., `references/swr-image-sync-guide.md`, `references/storage-pv-migration-guide.md`, `references/velero-migration-guide.md`, `templates/pvc-evs-template.yaml`) resolve to existing files on the local filesystem.
- **Zero Redundant Duplication**: Shared content is referenced rather than duplicated across multiple reference files.

### Fail Criteria

- Missing or malformed YAML frontmatter in `SKILL.md`.
- Total line count of `SKILL.md` exceeds 500 lines.
- Broken relative file links pointing to missing markdown or YAML files.
- Non-English content in reference guides or template files outside skill trigger declarations.
