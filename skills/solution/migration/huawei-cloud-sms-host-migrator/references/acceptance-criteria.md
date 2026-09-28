# Acceptance Criteria — huawei-cloud-sms-host-migrator

This document establishes the testing specifications, pass conditions, and failure criteria for the `huawei-cloud-sms-host-migrator` skill across unit testing, CLI integration testing, security scanning, and documentation validation.

---

## 1. Unit Testing Criteria (`scripts/`)

Unit testing validates the automated shell and Python test fixtures under `scripts/`, verifying test case parsing, concurrency execution, and CLI output result verification without generating report files.

### Test Execution
```bash
bash scripts/test-cli-commands.sh -s . -r cn-north-4 -j 4
```

### Pass Criteria
- **Execution Integrity**: The test runner `scripts/test-cli-commands.sh` executes with `set -euo pipefail` and exits with status code `0`.
- **Test Case Discovery**: Embedded Python logic cleanly parses all test cases defined in `templates/test-vars.json` without deserialization errors.
- **Suite Completion**: All 18 registered test cases (`TC-SMS-01` through `TC-SMS-18`) report `✅ PASS`.
- **CLI Output Verification**: Test results and execution summary are directly returned in the CLI output, confirming `PASS=18`, `FAIL=0`, and all expected test cases verified without persisting test-report files.
- **Output Token Matching**: Every test case output contains its expected token string (e.g., `replicate`, `source_servers`, `tasks`, `template.name`, `speed_limit`, `images`).

### Fail Criteria
- Runner terminates prematurely with a non-zero exit code or unhandled exception.
- Any test case reports `FAIL` due to command error, unexpected output, or timeout.
- Missing configuration files (`templates/test-vars.json` not found).
- Python environment missing or failing to parse JSON data.
- CLI output reports `FAIL > 0` or fails to output test execution summary.

---

## 2. Integration Testing Criteria (CLI Commands End-to-End Execution)

Integration testing verifies end-to-end KooCLI command execution against Huawei Cloud live endpoints for read-only queries and dry-run syntax verification for mutating operations.

### Scope & Execution Flow
1. **Migration State & Discovery**:
   - `hcloud SMS ShowOverview --cli-region=cn-north-4`
   - `hcloud SMS ListServers --cli-region=cn-north-4 --limit=1`
   - `hcloud SMS ListMigprojects --cli-region=cn-north-4`
   - `hcloud SMS ListTemplates --cli-region=cn-north-4`
   - `hcloud SMS ListTasks --cli-region=cn-north-4 --limit=1`
2. **Environment & Image Discovery**:
   - `hcloud IMS ListImages --cli-region=cn-north-4 --status=active --__imagetype=gold --__platform=Ubuntu --limit=1`
   - `hcloud IMS ListImages --cli-region=cn-north-4 --status=active --__imagetype=market --__platform=Windows --limit=1`
   - `hcloud IAM KeystoneListProjects --name=cn-north-4`
   - `hcloud VPC ListVpcs/v3 --cli-region=cn-north-4 --limit=1`
3. **Mutating Operation Syntax & Dry-Run Validation**:
   - `hcloud SMS CreateTemplate --help`
   - `hcloud SMS CreateTask --help`
   - `hcloud SMS CreateTask --cli-jsonInput="templates/create-task-windows.json" --dryrun`
   - `hcloud SMS CreateTask --cli-jsonInput="templates/create-task-existing-server.json" --dryrun`
   - `hcloud SMS UpdateTaskStatus --help`
   - `hcloud SMS UpdateSpeed --help`
   - `hcloud SMS DeleteTask --help`
   - `hcloud VPC ListSecurityGroupRules/v3 --help`
   - `hcloud VPC ListFirewall --help`
   - `hcloud ECS ShowServer --help`

### Pass Criteria
- **Valid JSON Responses**: All read-only commands return HTTP status `200` with well-formed JSON objects matching KooCLI schema.
- **Zero KooCLI Errors**: No error tags (`[USE_ERROR]`, `[OPENAPI_ERROR]`, or `[NETWORK_ERROR]`) emitted in standard error or standard output.
- **Dry-Run Serialization**: Windows task template serialization verifies 4-backslash double-escaping (`"name": "C:\\\\"`) in `--dryrun` mode without JSON parsing failure.
- **Mandatory Flags Adherence**: Every invoked `hcloud` command includes the required `--cli-region` flag.
- **PascalCase Operation Conformity**: All operation names strictly use PascalCase (e.g., `ShowOverview`, `CreateTask`, `UpdateTaskStatus`).

### Fail Criteria
- Command invocation returns `[USE_ERROR]` indicating unknown parameters or syntax mismatches.
- Command invocation returns `[OPENAPI_ERROR]` indicating invalid actions, schema errors, or unsupported API endpoints.
- Authentication failure (`401 Unauthorized` or `403 Forbidden`) due to missing IAM permissions or invalid profile.
- JSON template parsing fails during `--cli-jsonInput` serialization.

---

## 3. Security Scan Criteria (AK/SK Leaks & Sensitive Information)

Security scanning inspects the entire skill repository to prevent leakage of credentials, authentication keys, and sensitive internal data.

### Scanning Scope
All files within the skill package, including `SKILL.md`, `references/`, `scripts/`, and `templates/`.

### Pass Criteria
- **Zero Hardcoded Credentials**: Scans across all repository files detect zero occurrences of:
  - Huawei Cloud Access Key IDs (AK) matching regular expression `(?i)(hw|hws|huawei)?_?(ak|access_key)[\s:=]+['"][A-Za-z0-9]{20}['"]`.
  - Huawei Cloud Secret Access Keys (SK) matching regular expression `(?i)(hw|hws|huawei)?_?(sk|secret_key)[\s:=]+['"][A-Za-z0-9]{40}['"]`.
  - Private cryptographic keys (`-----BEGIN.*PRIVATE KEY-----`).
  - Raw session tokens or passwords.
- **Parameter Masking**: All sample parameters and IDs in templates and examples use bracketed placeholder syntax (e.g., `{source_server_id}`, `{task_id}`, `{sg_id}`).
- **Process List Cleanliness**: No credentials passed as visible process command-line arguments (such as `--cli-access-key` or `--cli-secret-key`); all authentication relies on KooCLI profiles or environment variables (`HW_ACCESS_KEY`, `HW_SECRET_KEY`).
- **Log Sanitation**: Verification test output files and logs contain no unmasked secret keys.

### Fail Criteria
- Discovery of any static 20-character AK or 40-character SK in plain text.
- Inclusion of real operational passwords, bearer tokens, or cloud secrets in documentation or template payloads.
- Transcripts or CLI execution outputs printing unmasked sensitive variables.

---

## 4. Document Validation Criteria (SKILL.md Format & Link Validity)

Document validation ensures structural compliance, linting correctness, and referential integrity across all markdown documentation.

### Pass Criteria
- **Frontmatter Standard**: `SKILL.md` contains valid YAML frontmatter enclosing `name`, `description`, and `tags`. The `name` attribute strictly matches the directory name `huawei-cloud-sms-host-migrator`.
- **Language Uniformity**: All documentation, reference documents, and configuration files are written strictly in English (excluding user-facing skill triggers).
- **Line Count Limits**: Total line count of `SKILL.md` is strictly under 500 lines.
- **Required Sections Present**: `SKILL.md` contains all mandated sections:
  - `Overview`
  - `Prerequisites`
  - `Workflow`
  - `Core Commands`
  - `Parameter Confirmation`
  - `KooCLI Command Format Standard`
  - `Reference Documents`
- **Link Integrity**: All relative links in markdown files (e.g., `references/agent-deployment-guide.md`, `references/pre-migration-checklist.md`, `templates/create-task.json`) resolve to existing files on the local filesystem.
- **Zero Redundant Duplication**: Shared content is referenced rather than duplicated across multiple reference files.

### Fail Criteria
- Invalid YAML frontmatter or missing mandatory frontmatter fields.
- Total line count of `SKILL.md` exceeds 500 lines.
- Any broken relative file link detected (e.g., pointing to non-existent markdown or JSON file).
- Inclusion of non-English content outside the designated skill trigger section.
