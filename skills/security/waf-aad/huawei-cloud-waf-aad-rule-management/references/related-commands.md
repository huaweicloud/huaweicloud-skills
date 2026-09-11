# Related Commands & Context

Auxiliary hcloud commands and external context useful when operating the `huawei-cloud-waf-aad-rule-management` skill.

## WAF auxiliary commands

```bash
# Geo regions supported for geo rules (source of {geoip} values)
hcloud WAF ShowPolicyGeoipMap --cli-region={region} --project_id={project_id}

# Instance details (dedicated WAF instances)
hcloud WAF ShowInstance --cli-region={region} --project_id={project_id} --instance_id={instance_id}
```

Verify each auxiliary operation with `--help` before first use; only commands listed in SKILL.md
Core Commands are guaranteed verified in this skill version.

## DNS / CNAME context (external, not hcloud)

- WAF protected domains must publish a **CNAME record pointing to the WAF endpoint** (the `cname`
  value returned by `ListCompositeHosts` / `ShowCompositeHost`).
- Verify with `dig +short <domain> CNAME` or `nslookup`.
- Do NOT point the record at the origin server IP — that bypasses WAF.

## EIP context

- AAD protects EIPs (Standard: one EIP; Enterprise: whole network segment). EIP binding itself is
  managed in the console (Anti-DDoS → EIP binding) or via VPC EIP services — not via this skill's CLI
  baseline.

## KooCLI general tips

```bash
hcloud configure list                 # show current auth profile
hcloud WAF ListInstance --help        # authoritative WAF parameter names — always re-check before building commands
hcloud AAD ListInstance --help        # authoritative AAD parameter names — always re-check before building commands
```

> **Golden rule:** run `hcloud WAF <Operation> --help` / `hcloud AAD <Operation> --help` before
> constructing any command; `--help` output is the only authoritative source for parameter names
> and required flags.
