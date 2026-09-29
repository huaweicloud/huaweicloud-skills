# Acceptance Criteria

## Functional Requirements

- [ ] Skill can check credential availability via `hcloud configure list`
- [ ] Skill can verify the domain belongs to the current account via `ShowVerifyDomainOwnerInfo` (200 response)
- [ ] When credentials are invalid, abort and return "Credentials not configured. Run 'hcloud configure' to configure AK/SK first."
- [ ] When domain returns 404/CDN.0171, abort and return "Domain not under current account. Please confirm domain ownership."
- [ ] When domain returns 403, abort and return "No permission to diagnose this domain. Contact the administrator to grant CDN domain query permission."
- [ ] Skill can obtain ownership verification info via `ShowVerifyDomainOwnerInfo`
- [ ] Can identify DNS TXT verification method (dns_verify_type=TXT)
- [ ] Can identify file verification method (file_verify_url present)
- [ ] Can identify verification already passed status
- [ ] For file verification, probe whether the file exists via `python scripts/file_probe.py --url <file_verify_url> [--timeout 10]`
- [ ] `file_probe.py` returns JSON with `data.http_status == 200` and `data.content_preview` contains `verify_content` → file verification passed
- [ ] `file_probe.py` returns JSON with `data.http_status == 404` → file verification failed
- [ ] `file_probe.py` returns JSON with `data.error.reason == "connect_timeout"` → return partial results, mark "File probe timed out"
- [ ] For DNS TXT verification, query the record via `python scripts/dns_txt_probe.py --name <dns_query_name> [--resolver <ip>] [--timeout 10]`
- [ ] `dns_txt_probe.py` returns JSON with `data.txt_records` containing `verify_content` → DNS verification passed
- [ ] `dns_txt_probe.py` returns JSON with `data.txt_records` empty (or `data.error.reason == "dns_no_answer"`) → DNS verification failed
- [ ] `dns_txt_probe.py` returns JSON with `data.error.reason == "dns_timeout"` → return partial results, mark "DNS probe timed out"
- [ ] When verification already passed, report "Ownership verification has passed, may be cache latency, recommend refreshing and retrying"

## Security Constraints

- [ ] Skill is read-only, prohibits calling Create/Update/Delete commands
- [ ] When user requests configuration changes, refuse and return "This skill supports diagnosis only and does not perform configuration changes"
- [ ] Prohibit reading/echoing/printing AK/SK values
- [ ] Prohibit requiring users to input credentials directly in the conversation
- [ ] When user provides AK/SK in the conversation, stop immediately and guide secure configuration
- [ ] iam-policies.md contains `cdn:*:query*` and `cdn:configuration:queryDomains` permission statements
- [ ] Permission statement does not include any write operation permissions

## Output Format

- [ ] Report contains separator `====================` and section headers `--- xxx ---`
- [ ] Report contains analysis time, target domain
- [ ] Report contains diagnosis item list (each item contains name, status ✅/❌/⚠️, detail)
- [ ] Report contains conclusion and fix recommendations

## Timeout Control

- [ ] `python scripts/file_probe.py` enforces timeout via `--timeout` (default 10, applied to connect + read)
- [ ] `python scripts/dns_txt_probe.py` enforces timeout via `--timeout` (default 10, applied as resolver `lifetime`)
- [ ] All Python probe scripts have a 10-second default timeout
- [ ] `--timeout` accepts only values in the range [1, 30]; out-of-range values exit with code 2

## Command Format

- [ ] All hcloud commands use `--cli-region=<region>`
- [ ] All hcloud commands use `--key=value` format
- [ ] Command examples conform to `hcloud CDN <Operation> --cli-region=<region> --key=value` format

## Python Probe Scripts

- [ ] `scripts/file_probe.py` exists and accepts `--url` and `--timeout` via `argparse`
- [ ] `scripts/dns_txt_probe.py` exists and accepts `--name`, `--resolver`, and `--timeout` via `argparse`
- [ ] `python -c "import requests, dns.resolver; print('ok')"` succeeds in the runtime environment
- [ ] `requests.__version__ >= "2.25"` and `dnspython >= 2.1` are installed
- [ ] Each probe emits exactly one JSON object on stdout (parseable by the report step)
- [ ] Each probe exits with code 0 on soft failures (HTTP 4xx/5xx, NXDOMAIN, NoAnswer) and code 2 on argument / missing-library errors
- [ ] No probe script invokes `subprocess`, `os.system`, or `shell=True`
- [ ] No probe script accepts AK/SK, tokens, cookies, or `Authorization` headers
- [ ] `file_probe.py` restricts URLs to http/https schemes; redirects are not followed
- [ ] `dns_txt_probe.py` accepts `--resolver` as a single IP literal only and reports `"system"` when omitted

## File Constraints

- [ ] Directory contains SKILL.md + references/ + scripts/
- [ ] references/ contains at least iam-policies.md and cli-installation-guide.md
- [ ] Total file count in directory ≤ 30
- [ ] Total directory size ≤ 40 MB
- [ ] SKILL.md frontmatter name is `huawei-cloud-cdn-domain-ownership-verification`, matching the directory name
- [ ] SKILL.md description contains "Triggers include:"
- [ ] SKILL.md contains Overview, Prohibited Operations, Architecture, Prerequisites, Authentication, IAM Permission Policies, Core Commands, Parameter Confirmation, Core Workflows, References sections
