# Step 5: Per-request Forensics

> Goal: lock the abnormal code to **specific requests** — exact URL, client IP,
> UA, referer, cache status — and attribute the involved IPs. Read-only.

## 5.1 Obtain log download links for the anomaly window

`ShowLogs/v2` supports a single domain, ≤30 days (start_time must not be earlier than 30 days ago), left-closed right-open.

```bash
hcloud CDN ShowLogs/v2 --cli-region=cn-north-1 --domain_name=$DOMAIN \
  --start_time=$HOUR_S --end_time=$HOUR_E --page_number=1 --page_size=100 --cli-output=json \
  | jq '.logs[]|{name,start_time,end_time,link,size}'
```

Pick the file whose `[start_time, end_time)` covers the anomaly hour (CDN logs
are typically split hourly, named `YYYYMMDDHH-<domain>-cn.gz`).

## 5.2 Fetch + decompress + extract abnormal rows (JSON)

```bash
python scripts/fetch_cdn_log.py --url "<link>" --status 403,502,503,504,500,404,499 --timeout 30 --max-lines 200
```

The helper downloads the gzip, decompresses in memory, and prints one JSON
object on stdout. `rows[]` contains per-request entries:

```json
{"status":403,"client_ip":"120.46.140.45","url":"/index.html",
 "cache_status":"HIT","user_agent":"curl/8.2.1",
 "edge_node_ip":"39.136.130.12","time":"[10/Aug/2026:15:55:13 +0800]"}
```

### CDN 日志字段标准格式（华为云官方 14 字段）

> 日志行字段顺序遵循华为云官方文档定义（[通过日志分析恶意访问地址](https://support.huaweicloud.com/intl/zh-cn/bestpractice-cdn/cdn_01_0252.html)）。
> **解析要点**：第 1 个字段 `[时间]` 内部含空格（时间 + 时区，如 `[10/Aug/2026:15:55:13 +0800]`），必须作为一个整体；带引号字段（referer/protocol/method/host/url/user_agent）内部可能含空格，按引号合并。

| # | 字段 | 含义 | 示例 |
|---|------|------|------|
| 1 | `time` | 日志生成时间（含时区，**整体一个字段**） | `[10/Aug/2026:15:55:13 +0800]` |
| 2 | `client_ip` | 终端用户访问 IP | `120.46.140.45` |
| 3 | `rt` | 响应时间（单位 ms） | `7` |
| 4 | `referer` | Referer 信息（可能为 `-`） | `"http://testhw.laohand.com/"` |
| 5 | `protocol` | HTTP 协议标识 | `"HTTP/1.1"` |
| 6 | `method` | HTTP 请求方式 | `"GET"` |
| 7 | `host` | CDN 加速域名 | `"testhw.laohand.com"` |
| 8 | `url` | 请求路径 | `"/index.html"` |
| 9 | `status` | HTTP 状态码 | `403` |
| 10 | `size` | 返回字节数 | `768` |
| 11 | `cache_status` | 缓存命中状态（HIT/MISS） | `HIT` |
| 12 | `user_agent` | UA 信息（**含空格，按引号合并**） | `"curl/8.2.1"` |
| 13 | `range` | Range 范围信息（可能为 `-`） | `"-"` |
| 14 | `edge_node_ip` | CDN 服务端响应 IP | `39.136.130.12` |

**脚本字段映射**：`fetch_cdn_log.py` 的 `rows[]` 按此标准格式解析——
`client_ip`=字段 2、`url`=字段 8、`status`=字段 9、`cache_status`=字段 11、
`user_agent`=字段 12、`edge_node_ip`=字段 14、`time`=字段 1。

Decision cues from the rows:

- All rows share `cache_status=HIT` + same small body ⇒ edge-generated
  (consistent with Step 2 `bs_*` empty).
- Only a few `client_ip` values, `user_agent=curl/*` ⇒ synthetic probes
  (刷量 / monitoring), not real users.
- Same IP `200` then `403` in time order ⇒ per-IP block / rate-limit signature.

> Soft failures (HTTP non-200, empty result, bad gzip, timeout) still exit 0
> with a JSON `error.reason`; argument/library errors exit 2.

## 5.3 IP attribution

```bash
hcloud CDN ShowIpInfo/v2 --cli-region=cn-north-1 --ips=<ip1>,<ip2>,<ip3> --cli-output=json | jq '.cdn_ips[]'
```

`belongs=true` ⇒ Huawei Cloud CDN node IP; `region`/`isp` ⇒ attribution for
cross-checking the Step 3 Top-N distribution. The last log field
(`edge_node_ip`) is the serving CDN node; the 2nd field (`client_ip`) is the
end-user source.

## Exit criteria

- Concrete request rows with URL / client IP / UA / cache status captured.
- 刷量 vs real-user verdict corroborated by actual rows.
- IP attribution matches Step 3 Top-N shortlist.
