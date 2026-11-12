# Troubleshooting

| Symptom | Likely cause | Action |
|---------|--------------|--------|
| Exit 3, "未找到华为云 AK/SK 凭据" | AK/SK env vars not visible to the process | Export `HUAWEI_ACCESS_KEY` / `HUAWEI_SECRET_KEY` in the same shell, then rerun |
| Exit 4, HTTP 401 | AK/SK invalid, expired, or a temporary credential without its token | Refresh the credential; for temporary AK/SK also export `HUAWEI_SECURITY_TOKEN` |
| Exit 4, HTTP 403 `SCM.4002 Permission denied` | Missing `scm:cert:list` / `scm:cert:get` | Add the read-only IAM actions from `iam-policies.md`; do not retry with another account |
| Exit 2, "region 格式非法" | Region string malformed | Use a real region such as `cn-north-4`, `cn-east-3`, `ap-southeast-1` |
| Exit 5, "无法连接 SCM 端点" | Wrong region/endpoint, DNS, proxy or network block | Check `--region`; test connectivity to `scm.{region}.myhuaweicloud.com`; set `HTTPS_PROXY` if required by the environment |
| Empty table / `total: 0` | No certificate matches the filters | This is a normal success. Broaden `--name`, use `--status ALL`, or remove `--expiring`; check the region and enterprise project |
| `issue_time` shows `-` in list output | The ListCertificates model does not return issuance time | Use `show --cert-id <id>` to retrieve `issue_time` |
| Certificate count is capped | `--limit` was supplied | Remove `--limit` to page through the full result set |
| JSON parse failure in a downstream Agent | The command wrote an error to stderr | Check the exit code; stdout is JSON only on success |

Credential values are never printed by the script. If a shell history or CI log
might have captured a secret, rotate the AK/SK in Huawei Cloud IAM.