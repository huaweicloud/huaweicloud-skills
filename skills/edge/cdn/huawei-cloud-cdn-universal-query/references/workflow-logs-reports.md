# Workflow 4: Download Logs and Reports

> Use this workflow when you need to download CDN access logs or export statistics reports.

## Prerequisites

- hcloud CLI installed and authenticated
- Target domain name (for `ShowLogs/v2`)
- Time range in millisecond UTC timestamps
- For Excel downloads: ensure sufficient disk space (output is binary)

## Steps

### Step 1: Query CDN access logs

```bash
hcloud CDN ShowLogs/v2 --cli-region=cn-north-1 \
  --domain_name=<your-domain> \
  --start_time=<ms> \
  --end_time=<ms>
```

**Parameters:**
- `--domain_name` (required)
- `--start_time`, `--end_time` (required): Millisecond UTC timestamps

**Pitfall:** If the domain belongs to an enterprise project, the query may fail with `user has no enterprise project id:{0}`. Use a domain that is NOT tied to an enterprise project. See Pitfall #6.

**Returns:** List of log files with download URLs. Each log file typically covers 1 hour of traffic.

**Log file content:** Each log line contains: client IP, request time, method, URL, status code, bytes sent, referer, user-agent, etc.

### Step 2: Query refresh/preheat task history (optional)

If you need to correlate logs with refresh/preheat events:

```bash
hcloud CDN ShowHistoryTasks/v2 --cli-region=cn-north-1 --page_number=<page_number> --page_size=<page_size>
```

**Pitfall:** `--page_number` and `--page_size` MUST be passed together. Passing only one returns `CDN.0001: Parameter error`. See Pitfall #5.

**Optional filters:**
- `--start_time`, `--end_time`: Filter by time range
- `--task_type`: Filter by task type (`refresh`, `preheat`)
- `--status`: Filter by status (`processing`, `done`, `failed`)

### Step 3: Get task details (if needed)

```bash
hcloud CDN ShowHistoryTaskDetails/v2 --cli-region=cn-north-1 --history_tasks_id=<task_id>
```

**Returns:** Detailed info for a specific refresh/preheat task (URL list, processing status per URL).

### Step 4: Download statistics Excel

```bash
hcloud CDN DownloadStatisticsExcel --cli-region=cn-north-1 \
  --domain_name=<your-domain> \
  --start_time=<ms> \
  --end_time=<ms> \
  --excel_type=<excel_type> \
  --cli-read-timeout=60
```

**Required parameters:**
- `--domain_name`: Domain name (comma-separated for multiple; `all` for all domains)
- `--start_time`, `--end_time`: Millisecond UTC timestamps
- `--excel_type`: One of `excel_type_usage` / `excel_type_access` / `excel_type_origin` / `excel_type_http_code` (enum: excel_type_usage, excel_type_access, excel_type_origin, excel_type_http_code)

**Critical:**
- `--cli-read-timeout=60` is REQUIRED (default 10s is too short). See Pitfall #7.
- Output is **binary** (xlsx/zip format, starts with `PK` header).
- Do NOT attempt to parse as text or JSON.

**Optional:**
- `--enterprise_project_id`: Enterprise project ID
- `--excel_language`: Excel language (enum: zh-cn, en-us; default zh-cn)
- `--interval`: Query interval in seconds (enum: 300, 3600, 86400)
- `--service_area`: Service area (enum: mainland, overseas, global)

**To save to file:**
```bash
hcloud CDN DownloadStatisticsExcel --cli-region=cn-north-1 \
  --domain_name=<your-domain> \
  --start_time=<ms> --end_time=<ms> \
  --excel_type=<excel_type> \
  --cli-read-timeout=60 > stats.xlsx
```

### Step 5: Download region/carrier Excel (optional)

```bash
hcloud CDN DownloadRegionCarrierExcel --cli-region=cn-north-1 \
  --domain_name=<your-domain> \
  --start_time=<ms> \
  --end_time=<ms> \
  --excel_type=<excel_type> \
  --country=<country> \
  --cli-read-timeout=60
```

**Required parameters:**
- `--domain_name`: Domain name (comma-separated for multiple; `all` for all domains)
- `--start_time`, `--end_time`: Millisecond UTC timestamps
- `--excel_type`: One of `excel_type_usage` / `excel_type_access` / `excel_type_region` / `excel_type_carrier` / `excel_type_country` / `excel_type_top_url` (enum: excel_type_usage, excel_type_access, excel_type_region, excel_type_carrier, excel_type_country, excel_type_top_url)

**Optional (with dependency rules):**
- `--carrier`: Carrier filter (effective with `excel_type_carrier`)
- `--country`: Country filter (enum: cn, all); when `excel_type=excel_type_region`, MUST be `cn`
- `--region`: Region filter (only effective when `--country=cn`)
- `--enterprise_project_id`, `--excel_language` (enum: zh-cn, en-us), `--interval` (enum: 300, 3600, 86400)

**Same caveats as `DownloadStatisticsExcel`:**
- `--cli-read-timeout=60` is REQUIRED.
- Output is binary.
- Additionally, `excel_type_region` requires `--country=cn`.

### Step 6: List export tasks (optional)

```bash
hcloud CDN ListExportTasks --cli-region=cn-north-1 --task_id=<task_id> --task_name=<task_name>
```

**Parameters:** `--task_id`, `--task_name` (both required); `--limit`, `--offset` (optional)

**Returns:** List of export tasks (export type, status, download URL).

## Binary Output Handling

Both `DownloadStatisticsExcel` and `DownloadRegionCarrierExcel` return binary content (xlsx/zip format).

**Identification:** Output starts with `PK` header (zip magic bytes).

**Handling:**
- Redirect to file: `> report.xlsx`
- Do NOT pipe through text tools (`grep`, `awk`, etc.)
- Open with Excel or parse with `openpyxl`/`pandas` in Python

## Common Issues

- **ShowLogs/v2 enterprise project error**: Use a domain NOT tied to an enterprise project.
- **DownloadStatisticsExcel timeout**: Always add `--cli-read-timeout=60`.
- **Binary output as text**: The output is binary — redirect to file, do not parse as text.
- **ShowHistoryTasks/v2 parameter error**: Always pass `--page_number` AND `--page_size` together.
- **ShowUrlTaskInfo/v2 empty results**: Max time span is 24 hours. See Pitfall #9.
