# Category 3: Refresh / Log / Export APIs (8 APIs)

> All commands should use `--cli-region=cn-north-1`. All operations are read-only (GET).
> Time parameters are millisecond UTC timestamps.

## API List

### 1. ShowHistoryTasks/v2 — Get refresh/preheat task history

```bash
hcloud CDN ShowHistoryTasks/v2 --cli-region=cn-north-1 --page_number=<page_number> --page_size=<page_size>
```

**Parameters:**
- `--page_number` (required): Page number (starting from 1)
- `--page_size` (required): Page size (max 100)

**Pitfall:** `--page_number` and `--page_size` MUST be passed together. Passing only one returns `CDN.0001: Parameter error`. See Pitfall #5.

**Optional filters:**
- `--start_date`, `--end_date`: Filter by time range (ms UTC). **Note:** names differ from ShowUrlTaskInfo/v2 (`--start_time`/`--end_time`) — verify per command
- `--task_type`: Filter by task type (`refresh`, `preheat`)
- `--status`: Filter by status (`processing`, `done`, `failed`)

**Returns:** Task list with `id`, `task_type`, `status`, `urls`, `create_time`.

---

### 2. ShowHistoryTaskDetails/v2 — Get task details

```bash
hcloud CDN ShowHistoryTaskDetails/v2 --cli-region=cn-north-1 --history_tasks_id=<task_id>
```

**Parameters:** `--history_tasks_id` (required, string, path parameter)

**Returns:** Detailed info for a specific refresh/preheat task (URL list, processing status per URL).

---

### 3. ShowUrlTaskInfo/v2 — Get URL task info

```bash
hcloud CDN ShowUrlTaskInfo/v2 --cli-region=cn-north-1 \
  --start_time=<ms> \
  --end_time=<ms>
```

**Parameters:** `--start_time`, `--end_time` (required): Millisecond UTC timestamps

**Pitfall:** Max time span is **24 hours**. Larger ranges return errors or empty results. See Pitfall #9.

**Returns:** URL-level task info within the specified 24-hour window.

---

### 4. ListBanUrl — Get banned URL list

```bash
hcloud CDN ListBanUrl --cli-region=cn-north-1 [--start_time=<ms>] [--end_time=<ms>] [--url=<url>] [--page_number=<n>] [--page_size=<n>]
```

**Parameters (all optional):**
- `--start_time`, `--end_time` (optional): Filter by time range (millisecond UTC timestamps)
- `--url` (optional): Filter by specific URL
- `--page_number`, `--page_size` (optional): Pagination

**Returns:** List of banned URLs (URL blocking feature).

---

### 5. ShowLogs/v2 — Get CDN logs

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

**Returns:** Log file list with download URLs (each log file covers 1 hour).

---

### 6. ListExportTasks — Get export task list

```bash
hcloud CDN ListExportTasks --cli-region=cn-north-1 \
  --task_id=<task_id> \
  --task_name=<task_name> \
  --limit=<limit> \
  --offset=<offset>
```

**Parameters:**
- `--task_id`, `--task_name` (both required): Task ID and task name for filtering
- `--limit`, `--offset` (optional): Pagination (user-provided integers)

**Returns:** List of export tasks (export type, status, download URL).

---

### 7. DownloadStatisticsExcel — Download statistics Excel

```bash
hcloud CDN DownloadStatisticsExcel --cli-region=cn-north-1 \
  --domain_name=<your-domain> \
  --start_time=<ms> \
  --end_time=<ms> \
  --excel_type=<excel_type> \
  --cli-read-timeout=60
```

**Parameters:**
- `--domain_name` (required): Domain name; supports multiple domains comma-separated; `all` for all domains
- `--start_time`, `--end_time` (required): Millisecond UTC timestamps
- `--excel_type` (required): Excel type, one of:
  - `excel_type_usage` — usage statistics
  - `excel_type_access` — access statistics
  - `excel_type_origin` — origin pull statistics
  - `excel_type_http_code` — HTTP status code statistics
- `--cli-read-timeout=60` (REQUIRED): Override default 10s timeout

**Optional:**
- `--enterprise_project_id`: Enterprise project ID
- `--excel_language`: Excel language (enum: `zh-cn`, `en-us`; default: `zh-cn`)
- `--interval`: Time granularity in seconds (enum: `300`, `3600`, `86400`)
- `--service_area`: Service area (enum: `mainland`, `overseas`, `global`)

**Pitfall:** Default `readTimeout` (10s) is too short for large exports. MUST add `--cli-read-timeout=60`. Output is binary (xlsx/zip format, starts with `PK` header). See Pitfall #7.

**Output:** Binary Excel file (do NOT parse as text).

---

### 8. DownloadRegionCarrierExcel — Download region/carrier Excel

```bash
hcloud CDN DownloadRegionCarrierExcel --cli-region=cn-north-1 \
  --domain_name=<your-domain> \
  --start_time=<ms> \
  --end_time=<ms> \
  --excel_type=<excel_type> \
  --country=<country> \
  --cli-read-timeout=60
```

**Parameters:**
- `--domain_name` (required): Domain name; supports multiple domains comma-separated; `all` for all domains
- `--start_time`, `--end_time` (required): Millisecond UTC timestamps
- `--excel_type` (required): Excel type, one of:
  - `excel_type_usage` — usage statistics
  - `excel_type_access` — access statistics
  - `excel_type_region` — region distribution (requires `--country=cn`)
  - `excel_type_carrier` — carrier distribution
  - `excel_type_country` — country distribution
  - `excel_type_top_url` — top URL statistics
- `--cli-read-timeout=60` (REQUIRED): Override default 10s timeout

**Optional (with dependency rules):**
- `--carrier`: Carrier filter (user-provided string, e.g. `China-Mobile`, `China-Unicom`, `China-Telecom`; effective with `excel_type_carrier`)
- `--country`: Country filter (enum: `cn`, `all`); when `excel_type=excel_type_region`, MUST be `cn`
- `--region`: Region filter (user-provided string, e.g. `huabei`, `huadong`; only effective when `--country=cn`)
- `--enterprise_project_id`: Enterprise project ID
- `--excel_language`: Excel language (enum: `zh-cn`, `en-us`; default: `zh-cn`)
- `--interval`: Time granularity in seconds (enum: `300`, `3600`, `86400`)

**Pitfall:** Same as `DownloadStatisticsExcel` — binary output, needs extended timeout. Additionally, `excel_type_region` requires `--country=cn`.

**Output:** Binary Excel file with region/carrier distribution data.

---

## Common Workflow

```
Step 1: ShowHistoryTasks/v2 → list refresh/preheat tasks (with pagination)
Step 2: ShowHistoryTaskDetails/v2 → get details for specific task
Step 3: ShowLogs/v2 → get CDN access logs (verify domain is NOT in enterprise project)
Step 4: DownloadStatisticsExcel / DownloadRegionCarrierExcel → export reports (binary)
```

## Binary Output Handling

Both `DownloadStatisticsExcel` and `DownloadRegionCarrierExcel` return binary content (xlsx/zip format). The output starts with `PK` header (zip magic bytes).

**To save the output to a file:**

```bash
hcloud CDN DownloadStatisticsExcel --cli-region=cn-north-1 \
  --domain_name=<your-domain> \
  --start_time=<ms> --end_time=<ms> \
  --excel_type=<excel_type> \
  --cli-read-timeout=60 > report.xlsx
```

Do NOT attempt to parse the output as text or JSON.
