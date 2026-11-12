# Verification Method

## 1. Offline Unit Tests (no cloud credentials)

The pure-function layer is covered by `tests/test_list_certificates.py`:
parameter construction, status normalization, request signing, response
normalization, expiry grading, empty results, pagination/capping and error
classification. The Markdown export is covered by `tests/test_markdown_export.py`:
default naming, path resolution (file / existing dir / trailing separator),
summary + nine-column layout, filter propagation, escaping, empty-list-no-file,
`--output` + `--json` conflict, credential non-leakage. Run:

```bash
cd skills/security/scm/huawei-cloud-ccm-certificate-query
python3 -m unittest discover -s tests -v
```

Expected: `OK` with all tests passing. No network access and no real AK/SK are
required.

## 2. Syntax / Help Check

```bash
python3 scripts/list_certificates.py --help
python3 scripts/list_certificates.py list --help
python3 scripts/list_certificates.py show --help
```

Each command must exit 0 and list the documented parameters.

## 3. Live Read-Only Verification (requires out-of-band AK/SK)

Credentials are configured outside the conversation; never paste AK/SK into a
chat or command line.

```bash
export HUAWEI_ACCESS_KEY="<your-access-key-id>"        # out of band
read -rs HUAWEI_SECRET_KEY; export HUAWEI_SECRET_KEY    # silent prompt
export HUAWEI_REGION="cn-north-4"

# List all certificates
python3 scripts/list_certificates.py list

# Server-side name filter; an unmatched name must return an empty list with exit 0
python3 scripts/list_certificates.py list --name no-such-certificate-xyz
echo $?

# Server-side status filter
python3 scripts/list_certificates.py list --status ISSUED --json

# Detail query using an ID from the list output
python3 scripts/list_certificates.py show --cert-id <certificate-id> --json
```

Checks:

- `--name` / `--status` are forwarded as `content` / `status` query parameters
  (verify in a proxy/log or by observing the filtered result set).
- No-match returns `{"certs": [], "total": 0}` (JSON) and exit code 0.
- `--json` output parses with `python3 -m json.tool`.
- Output contains ID, name, type, domain, status, issue/expiry time, remaining
  days and expiry grade.
- The table and JSON never contain AK/SK values.

## 4. Markdown Export Verification

```bash
# Export into a scratch directory with the default file name, then diff the
# echo against the file (they must be identical)
mkdir -p /tmp/ccm-export
python3 scripts/list_certificates.py list --region cn-north-4 --output /tmp/ccm-export \
  > /tmp/ccm-stdout.md 2>/tmp/ccm-stderr.txt
diff /tmp/ccm-stdout.md /tmp/ccm-export/ccm_certificates_cn-north-4_*.md && echo IDENTICAL
ls /tmp/ccm-export

# Explicit path + filters, and the filters must appear in the summary block
python3 scripts/list_certificates.py list --region cn-north-4 \
  --status ISSUED --expire-days 45 --limit 20 --output /tmp/ccm-export/filtered.md
grep -E '查询条件|到期分级阈值|条数上限' /tmp/ccm-export/filtered.md

# Empty result must not create a file
python3 scripts/list_certificates.py list --name no-such-certificate-xyz \
  --output /tmp/ccm-export/empty
ls -A /tmp/ccm-export/empty 2>/dev/null || echo "no directory created (expected)"
```

Checks:

- Default file name matches `ccm_certificates_<region>_<14-digit timestamp>.md`.
- The document has the `Region` / `查询条件` / `生成时间` / `记录数` summary rows and
  the nine result columns (ID / 名称 / 类型 / 绑定域名 / 状态 / 签发时间 / 到期时间 /
  剩余天数 / 到期等级).
- Row values equal the terminal table of the same command (`-` for missing values).
- An empty result prints `未查询到任何证书（total: 0），未生成 Markdown 文件。`, exit 0,
  and leaves no file behind.
- The exported file, stdout and stderr never contain AK/SK values.

## 5. Negative Paths

| Case | How to trigger | Expected |
|------|----------------|----------|
| Missing credentials | Run with AK/SK env vars unset | Exit 3 + env-var template, no secret values |
| Insufficient permission | Use a profile without `scm:cert:list` | Exit 4 + hint naming the IAM actions |
| Invalid region | `--region not-a-region` | Exit 2/5 + readable region hint |
| Unreachable endpoint | `--endpoint 127.0.0.1:1` | Exit 5 + readable network hint |
| Unknown status | `--status NOT_A_STATUS` | Exit 2 + list of valid statuses |
| Export to a missing directory | `--output /no/such/dir/x.md` | Exit 2 + `导出目录不存在` hint, nothing written |
| Export + JSON together | `--output . --json` | Exit 2 + mutual-exclusion hint |

## 6. Read-Only Audit

```bash
grep -nE 'POST|PUT|PATCH|DELETE' scripts/list_certificates.py
```

Only the `urlopen(..., method="GET")` call and the read-only paths
`/v3/scm/certificates` / `/v3/scm/certificates/{id}` are present. There is no
mutating operation implementation.