# Acceptance Criteria

## Functional Requirements

- [ ] Skill can check credential availability via `hcloud configure list`
- [ ] Skill can validate the domain belongs to the current account via `ShowDomainDetailByName`
- [ ] Skill can retrieve the domain expected CNAME via `ShowDomainDetailByName`
- [ ] When credentials are invalid, abort and return "Credentials not configured. Run `hcloud configure` first to configure AK/SK"
- [ ] When domain returns 404, abort and return "Domain not under the current account. Please confirm the domain ownership"
- [ ] When domain returns 403, abort and return "No permission to diagnose this domain. Please contact the administrator to grant CDN domain query permission"
- [ ] Skill can resolve the domain to obtain the IP list via `python scripts/dns_resolve.py --domain <domain> --timeout 10`
- [ ] `dns_resolve.py` returns JSON with `data.resolved_ips` non-empty and `data.error == null` → continue to Step 3
- [ ] `dns_resolve.py` returns JSON with `data.resolved_ips` empty and `data.error == null` → report "Domain not resolved", prompt to configure DNS CNAME pointing to `<cname>`
- [ ] `dns_resolve.py` returns JSON with `data.error.reason == "dns_timeout"` → return partial results, mark "DNS probe timeout"
- [ ] `dns_resolve.py` returns JSON with `data.error.reason == "dns_nxdomain"` → report "Domain does not exist (NXDOMAIN)"
- [ ] `dns_resolve.py` returns JSON with `data.error.reason == "missing_library"` (exit 2) → abort skill, prompt to install `dnspython>=2.1`
- [ ] Skill can query IP attribution via `ShowIpInfo/v2`
- [ ] The `--ips` parameter of ShowIpInfo/v2 supports multiple IPs (English comma separated)
- [ ] When the IP count exceeds 20, only the first 20 are taken and noted in the report
- [ ] All IPs belongs=true → report "Resolved to Huawei Cloud CDN"
- [ ] All IPs belongs=false → report "Not resolved to Huawei Cloud CDN", prompt to configure CNAME
- [ ] Some IPs belongs=true → report "Partially resolved to Huawei Cloud CDN", prompt "Some regions may have switched; multi-region probing is recommended"
- [ ] Report includes the CDN expected CNAME information

## Security Constraints

- [ ] Skill is read-only; no Create/Update/Delete commands are called
- [ ] When the user requests a configuration change, refuse and return "This skill supports diagnosis only; no configuration change operations are performed"
- [ ] Prohibited from reading/echoing/printing AK/SK values
- [ ] Prohibited from asking the user to input credentials directly in the conversation
- [ ] When the user provides AK/SK in the conversation, stop immediately and guide secure configuration
- [ ] iam-policies.md includes the `cdn:domain:get` permission statement
- [ ] Permission statements do not include any write operation permissions
- [ ] references/prohibited-operations.md lists all 55 prohibited non-GET operations (24 POST + 25 PUT + 6 DELETE)

## Related Skills (Multi-Direction Diagnosis)

- [ ] SKILL.md contains a "Related Skills" section referencing `huawei-cloud-cdn-certificate-diagnosis`, `huawei-cloud-cdn-domain-ownership-verification`, and `huawei-cloud-cdn-origin-diagnosis`
- [ ] The Related Skills section maps each related skill to its trigger scenario (certificate errors / ownership verification failure / origin pull failures)
- [ ] The Related Skills section instructs the agent to run synchronized diagnosis of other directions when the user's issue matches
- [ ] No direct cross-skill script invocation is documented (skills are invoked as whole skills, not their internal scripts)

## Output Format

- [ ] Report includes the separator `====================` and section titles `--- xxx ---`
- [ ] Report includes analysis time, target domain, Expected CNAME
- [ ] Report includes a DNS Resolution section listing the resolved IP list
- [ ] Report includes a diagnosis items list (each item contains name, status ✅/❌/⚠️, detail)
- [ ] Report includes conclusion and remediation suggestion
- [ ] Partial resolution scenario includes the false positive prompt "Some regions may have switched; multi-region probing is recommended"

## Timeout Control

- [ ] `dns_resolve.py` enforces a 10-second timeout via `--timeout 10` (default, range `[1, 30]`)
- [ ] All network probe commands have a 10-second timeout

## Command Format

- [ ] All hcloud commands use `--cli-region=<region>`
- [ ] All hcloud commands use the `--key=value` format
- [ ] Command examples conform to the `hcloud CDN <Operation> --cli-region=<region> --key=value` format
- [ ] DNS probe uses the `python scripts/dns_resolve.py --domain <domain_name> [--timeout 10]` format
- [ ] `dns_resolve.py` emits a single JSON object on stdout wrapped in `{result, data, error_msg}`; `data` contains fields `domain`, `resolved_ips`, `duration_ms`, `error`

## IP Query Constraints

- [ ] ShowIpInfo/v2 queries at most 20 IPs per call
- [ ] When IPs exceed 20, only the first 20 are queried
- [ ] The IP count limit is noted in the report (if applicable)

## File Constraints

- [ ] Directory contains SKILL.md + references/ + scripts/
- [ ] references/ contains at least iam-policies.md and cli-installation-guide.md
- [ ] Total file count in the directory ≤ 30
- [ ] Total directory size ≤ 40 MB
- [ ] The name in the SKILL.md frontmatter is `huawei-cloud-cdn-dns-resolution-diagnosis`, matching the directory name
- [ ] SKILL.md description contains "Triggers include:"
- [ ] SKILL.md contains the Overview, Prohibited Operations, Architecture, KooCLI Command Format Standard, Prerequisites, Authentication, IAM Permission Policies, Core Commands, Parameter Confirmation, Core Workflows, References sections
