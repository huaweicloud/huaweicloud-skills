# Markdown Export Format (`list --output`)

The export is a **rendering-only** feature: the query, filters, pagination and
derived fields are exactly those of the terminal table, so an export and the
console output of the same command describe the same records.

## Naming and path resolution

| Input | Resolution |
|-------|-----------|
| `--output` omitted | no file is written |
| `--output .` or an existing directory | `<dir>/ccm_certificates_<region>_<timestamp>.md` |
| `--output ./dir/` (trailing `/`) | same default name inside `./dir` |
| `--output ./reports/inventory.md` | that exact path (its parent directory must exist) |

- `region` — the **effective** region (CLI `--region` > `HUAWEI_REGION` > `cn-north-4`).
- `<timestamp>` — local time formatted `YYYYmmddHHMMSS` (14 digits).
- The file is UTF-8 with `\n` line endings.

## Document structure

```markdown
# 华为云 CCM 证书清单

| 摘要项 | 内容 |
|--------|------|
| Region | cn-north-4 |
| 查询条件 | 名称/域名（服务端模糊）=example.com；状态（服务端）=ISSUED；... |
| 生成时间 | 2026-11-12 18:45:00 +0800 |
| 记录数 | 返回 1 张（服务端匹配 3 张） |
| 到期分级 | 已过期=expired，即将到期=expiring（0～30 天），正常=normal，未知=unknown |

| 证书 ID | 名称 | 类型 | 绑定域名 | 状态 | 签发时间 | 到期时间 | 剩余天数 | 到期等级 |
|------|------|------|------|------|------|------|------|------|
| abcdef1234567890 | example.com | DV_SSL_CERT | example.com | 已签发 | 2026-01-01 | 2026-12-31 | 49 | 正常 |

> 数据来源：SCM v3 `GET /v3/scm/certificates`（只读）；共 1 张证书。
```

### Summary block

| Field | Source |
|-------|--------|
| `Region` | effective region |
| `查询条件` | every applied filter: `--name`, `--status`, `--expiring`, `--expire-days`, `--enterprise-project-id`, `--include-shared`, `--sort-key` / `--sort-dir`, `--limit`, `--offset` |
| `生成时间` | local time with UTC offset, format `%Y-%m-%d %H:%M:%S %z` |
| `记录数` | `返回 <returned> 张（服务端匹配 <total> 张）` — `total` is the server `total_count` for the filters |
| `到期分级` | legend tying the Chinese label to the `expiry_level` code and the active threshold |

### Table columns

| Column | Source field | Missing value |
|--------|--------------|---------------|
| 证书 ID | `id` | `-` |
| 名称 | `name` | `-` |
| 类型 | `type` (SSL / managed certificate type code, e.g. `DV_SSL_CERT`) | `-` |
| 绑定域名 | `domain` | `-` |
| 状态 | `status_label` (falls back to `status`) | `-` |
| 签发时间 | `issue_time` normalized to `YYYY-MM-DD` | `-` (the list API usually omits it) |
| 到期时间 | `expire_time` normalized to `YYYY-MM-DD` | `-` |
| 剩余天数 | `days_to_expire` (negative when expired) | `-` |
| 到期等级 | `expiry_label` (`已过期` / `即将到期` / `正常` / `未知`) | `-` |

## Escaping

Cell values go through `escape_markdown_cell`: a literal pipe becomes
`\` + `|`, a literal backslash is doubled, CR/LF become `<br>`, and an empty or
`None` value becomes `-`.

Markdown has no row-spanning cells, so multi-line values (for example a long
`sans` list copied into `domain`) are folded rather than allowed to break the table.

## Behaviour guarantees

1. **Line-for-line consistency** — the same Markdown text is both written to the
   file and printed to stdout (confirmation line goes to stderr), so
   `diff <(script ...)` against the file is empty.
2. **No empty artifacts** — a zero-record result prints
   `未查询到任何证书（total: 0），未生成 Markdown 文件。` and exits `0`; no file is created.
3. **Read-only** — only `GET /v3/scm/certificates` traffic; the export itself is a
   local file write. AK/SK, `Authorization` and `X-Security-Token` never appear in
   the document, stdout or stderr.
4. **Four error classes stay readable** — missing AK/SK (exit 3), invalid region or
   unreachable endpoint (exit 2/5), 403 permission (exit 4), empty list (exit 0,
   message above). Path problems (missing parent directory, unwritable target,
   `--output` together with `--json`) exit `2` with the offending path named.

## Verification

```bash
# Unit tests (offline, no credentials, no network)
python3 -m unittest discover -s tests -v

# Live read-only export: file content equals the stdout echo of the same run
python3 scripts/list_certificates.py list --region cn-north-4 --output ./reports/ \
  > /tmp/export-stdout.md
diff /tmp/export-stdout.md ./reports/ccm_certificates_cn-north-4_*.md && echo IDENTICAL
```