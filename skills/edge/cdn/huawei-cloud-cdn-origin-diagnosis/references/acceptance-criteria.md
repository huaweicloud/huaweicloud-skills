# Acceptance Criteria

## Functional Requirements

- [ ] Skill can check credential availability via `hcloud configure list`
- [ ] Skill can validate that the domain belongs to the current account via `ShowDomainDetailByName`
- [ ] When credentials are invalid, abort and return "Credentials not configured. Run `hcloud configure` to configure AK/SK first."
- [ ] When the domain returns 404, abort and return "Domain not found under the current account. Please confirm the domain ownership."
- [ ] When the domain returns 403, abort and return "No permission to diagnose this domain. Please contact the administrator to grant CDN domain query permission."
- [ ] Skill can retrieve the full domain configuration via `ShowDomainFullConfig/v2`
- [ ] Can parse the `configs.sources` field and extract origin_addr, origin_type, http_port, https_port
- [ ] Can parse the `origin_protocol` field (http / https / follow)
- [ ] When sources is empty, report "Origin not configured. Please configure the origin in the CDN console." and abort the probe step
- [ ] Select the probe protocol based on origin_protocol:
  - http → `python scripts/origin_probe.py --scheme http --host <origin_addr> --port <http_port>`
  - https → `python scripts/origin_probe.py --scheme https --host <origin_addr> --port <https_port>`
  - follow → probe both http and https
- [ ] `origin_probe.py` returning `data.connected=true` with `data.http_status` 200 / 3xx → origin reachable
- [ ] `origin_probe.py` returning `data.connected=true` with `data.http_status` 5xx, or `data.connected=false` with `data.error.reason=connect_failed` → origin unreachable, with IP whitelist prompt attached
- [ ] `origin_probe.py` returning `data.connected=false` with `data.error.reason=connect_timeout` → return partial results; note "Origin probe timed out"
- [ ] When the origin is unreachable, prompt "The origin may have a whitelist configured. Please confirm that the CDN back-to-source IP ranges have been added to the origin whitelist."

## Security Constraints

- [ ] Skill is read-only; calling Create/Update/Delete commands is prohibited
- [ ] When the user requests a configuration change, refuse and return "This skill supports diagnosis only and does not perform configuration changes."
- [ ] Reading/echoing/printing AK/SK values is prohibited
- [ ] Asking the user to input credentials directly in the conversation is prohibited
- [ ] When the user provides AK/SK in the conversation, stop immediately and guide secure configuration
- [ ] iam-policies.md includes the `cdn:*:query*` and `cdn:configuration:queryDomains` permission declarations
- [ ] The permission declaration does not include any write-operation permissions
- [ ] references/prohibited-operations.md lists all 55 prohibited non-GET operations (24 POST + 25 PUT + 6 DELETE)

## Output Format

- [ ] Report contains the separator line `====================` and section headers `--- xxx ---`
- [ ] Report contains analysis time and target domain
- [ ] Report contains origin configuration info (origin_addr, origin_type, http_port, https_port, origin_protocol)
- [ ] Report contains the diagnosis item list (each item includes a name, status ✅/❌/⚠️, and detail)
- [ ] Report contains a conclusion and remediation suggestion
- [ ] When the origin is unreachable, the report includes an IP whitelist prompt

## Timeout Control

- [ ] `scripts/origin_probe.py` uses `--timeout 10` (10-second timeout, default 10)
- [ ] All network probe commands use a 10-second timeout

## Command Format

- [ ] All hcloud commands use `--cli-region=<region>`
- [ ] All hcloud commands use the `--key=value` format
- [ ] Command examples follow the `hcloud CDN <Operation> --cli-region=<region> --key=value` format
- [ ] The probe command format is `python scripts/origin_probe.py --scheme <http|https> --host <origin_addr> --port <port> [--timeout 10]`
- [ ] `scripts/origin_probe.py` emits a single JSON object on stdout wrapped in `{result, data, error_msg}` and exits 0 on probe completion (including soft failures), 2 on argument/library errors

## File Constraints

- [ ] Directory contains SKILL.md + references/ + scripts/
- [ ] references/ contains at least iam-policies.md and cli-installation-guide.md
- [ ] Total file count in the directory ≤ 30
- [ ] Total size of the directory ≤ 40 MB
- [ ] The name field of the SKILL.md frontmatter is `huawei-cloud-cdn-origin-diagnosis`, matching the directory name
- [ ] The SKILL.md description contains "Triggers include:"
- [ ] SKILL.md contains the Overview, Prohibited Operations, Architecture, Prerequisites, Authentication, IAM Permission Policies, Core Commands, Parameter Confirmation, Core Workflows, and References sections
