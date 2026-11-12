# Acceptance Criteria

| # | Criterion | Command / Evidence |
|---|-----------|--------------------|
| 1 | List SCM certificates for a region with ID, name, type, domain, status, issue time, expiry time and remaining days | `python3 scripts/list_certificates.py list --region <region>`; table headers and JSON `certs[]` fields |
| 2 | Filter by certificate name (`--name`) server-side | Request query contains `content=<name>`; only matching certificates are returned |
| 3 | Filter by status (`--status`) server-side | Request query contains `status=<CODE>`; invalid status rejected with exit 2 |
| 4 | No match returns an empty list (`total: 0`) and exit code 0 | `--name no-such-certificate-xyz`; `echo $?` prints `0` |
| 5 | Show one certificate detail | `python3 scripts/list_certificates.py show --cert-id <id>`; detail fields printed |
| 6 | Missing credentials gives a readable hint without AK/SK | Run with AK/SK env unset; exit 3 and env-var template |
| 7 | 401/403 gives a readable permission hint without AK/SK | Run with a profile lacking `scm:cert:list`; exit 4 and IAM hint |
| 8 | Invalid region / unreachable endpoint gives a readable hint | `--region not-a-region` or `--endpoint 127.0.0.1:1`; exit 2/5 |
| 9 | `--json` is parseable by Agents | `python3 scripts/list_certificates.py list --json \| python3 -m json.tool` |
| 10 | Strictly read-only, no mutating API call | Source audit finds only GET requests to the two read-only paths; no apply/revoke/deploy/import/export/delete code |
| 11 | Tests pass and cover parameter construction, normalization, empty results and error branches | `python3 -m unittest discover -s tests -v` → `OK` |
| 12 | Export a Markdown certificate inventory with the default file name `ccm_certificates_<region>_<timestamp>.md`, or to an explicit `--output` path/directory | `python3 scripts/list_certificates.py list --output .` → file matching `ccm_certificates_<region>_<14-digit timestamp>.md`; `ls` evidence |
| 13 | Exported table carries ID / name / type / domain / status / issue time / expiry time / remaining days / expiry grade | Open the exported `.md`; the nine headers are present and each row has nine cells |
| 14 | Export content is line-for-line identical to the same command's terminal output and carries the region / filters / generation time / record-count summary | `--output` run: stdout equals file content (`diff` empty); summary rows `Region`, `查询条件`, `生成时间`, `记录数` present |
| 15 | Filters (`--name` / `--status` / `--limit` / `--expiring` / `--expire-days`) are reused unchanged by the export | Export with the filters set; `查询条件` lists them and the rows match the table run with the same flags |
| 16 | Empty result writes no file and reports a readable message | `--name no-such-certificate-xyz --output .`; exit `0`, message `未查询到任何证书…未生成 Markdown 文件。`, no new `.md` |
| 17 | Export errors stay readable and secret-free (missing AK/SK, bad region, 403, bad path, `--output`+`--json`) | exit `3` / `2` / `5` / `4` / `2` respectively, Chinese hint, no AK/SK in file, stdout or stderr |
| 18 | Markdown table survives `\|` and newlines in field values | Unit test `test_table_escaping`; rendered cells use `\|` and `<br>` |
| 19 | Skill states its relationship to Issue #1096 / PR #973 and does not duplicate triggers | `SKILL.md` § "Relationship to the base skill" |

## Out of Scope (must not be implemented)

- PCA private certificates and CAs.
- Certificate application/purchase, revocation, deployment/push, import/export,
  deletion or tag writes.
- Returning certificate private keys.