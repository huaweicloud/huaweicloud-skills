# Acceptance Criteria

## Functional

- [ ] `list` returns EIP id, IP, status, bandwidth and type fields.
- [ ] `show --publicip_id {id}` returns full EIP detail including `bandwidth_share_type`.
- [ ] `metric --publicip_id {id} --metric upstream_bandwidth_usage` returns percentage
      datapoints with peak/avg summary.
- [ ] `metric --metric down_stream --metric up_stream --filter sum` returns inbound and
      outbound traffic volumes in Byte.
- [ ] `metric --filter max` returns peak bandwidth in bit/s; `--filter average` returns average.
- [ ] `--from` / `--to` time range and `--period` aggregation are honored.
- [ ] Shared-bandwidth EIP is queryable via `--bandwidth_id`.
- [ ] `--json` emits raw parseable JSON.

## Compliance

- [ ] SKILL.md exists with frontmatter `name`, `description` containing triggers, and `tags`.
- [ ] Directory matches `huawei-cloud-{product}-{function}` and frontmatter `name`.
- [ ] Every concrete hcloud command includes `--cli-region`.
- [ ] CLI parameter names verified against `hcloud <op> --help` output.
- [ ] `references/iam-policies.md` and `references/cli-installation-guide.md` exist.
- [ ] No credentials hardcoded; no cross-skill calls; read-only skill.
- [ ] Skill total size ≤ 40 MB; files ≤ 30; SKILL.md ≤ 500 lines; allowed extensions.
- [ ] PR changes only the `network/eip/huawei-cloud-eip-query` directory.

## Security

- [ ] No AK/SK literals in any file (gitleaks clean).
- [ ] No command-injection / dangerous-function patterns (skillcheck clean).
- [ ] Quality SDK vendored verbatim, zero modifications.
