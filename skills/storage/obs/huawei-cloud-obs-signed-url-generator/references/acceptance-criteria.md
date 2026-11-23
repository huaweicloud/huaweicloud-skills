# Acceptance Criteria

## Functional Requirements

| ID | Criterion | Verification Method |
|----|-----------|-------------------|
| AC-01 | SKILL.md exists with valid YAML frontmatter | validate-skill.sh |
| AC-02 | name field matches directory name | validate-skill.sh |
| AC-03 | description includes feature summary and trigger conditions | Manual review |
| AC-04 | tags field has ≤ 5 entries | validate-skill.sh |
| AC-05 | No version field in frontmatter | validate-skill.sh |
| AC-06 | Overview section present | validate-skill.sh |
| AC-07 | Prerequisites section present | validate-skill.sh |
| AC-08 | Workflow section present | validate-skill.sh |
| AC-09 | Core Commands section present | validate-skill.sh |
| AC-10 | Parameter Confirmation section present | validate-skill.sh |
| AC-11 | Reference Documents section present | validate-skill.sh |
| AC-12 | generate_signed_url.py script exists and is executable | File check |
| AC-13 | Script supports --bucket-name, --object-key, --method, --expires, --server | Manual test |
| AC-14 | Script supports --image-process for image processing | Manual test |
| AC-15 | Script supports --security-token for temporary credentials | Manual test |
| AC-16 | Script supports --headers and --query-params as JSON | Manual test |
| AC-17 | No hardcoded credentials in any file | validate-skill.sh |
| AC-18 | ensure_cli.sh and install_cli.sh exist | validate-skill.sh |
| AC-19 | SKILL.md ≤ 500 lines | validate-skill.sh |
| AC-20 | Total files ≤ 30 | validate-skill.sh |
| AC-21 | All file extensions in allowlist | validate-skill.sh |
| AC-22 | references/iam-policies.md exists | validate-skill.sh |
| AC-23 | references/cli-installation-guide.md exists | validate-skill.sh |
| AC-24 | references/image-processing-guide.md exists | File check |
| AC-25 | references/dataflow-diagram.md exists | File check |
| AC-26 | templates/test-vars.json exists | File check |

## Non-Functional Requirements

| ID | Criterion | Verification Method |
|----|-----------|-------------------|
| NFR-01 | Script execution time < 5 seconds | Manual test |
| NFR-02 | Clear error messages for missing parameters | Manual test |
| NFR-03 | Credentials read from environment variables only | Code review |
| NFR-04 | Python 3.8+ compatible | Code review |
