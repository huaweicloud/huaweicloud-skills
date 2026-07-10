# Prerequisites

## Environment Requirements

- Python >= 3.9
- pip packages: `requests`, `beautifulsoup4`
- (Optional) Playwright search: `playwright`, `aiohttp`

## Installation Steps

### Required: Lightweight HTTP Fetcher

```bash
pip install requests beautifulsoup4
```

### Optional: Playwright Search

To use `web_searcher.py` for real-time Huawei Cloud document search:

```bash
pip install playwright aiohttp
playwright install chromium
```

If you skip this step, `web_fetcher.py` can still fetch documents by known URL; only the search function will be unavailable.

## Environment Variables

| Variable | Description | Default |
| --- | --- | --- |
| `REMOTE_CHROME_HOST` | Remote Chrome address (e.g., `http://host:port`). If not set, uses local Chrome | Empty (local Chrome) |

## Verify Installation

```bash
# Verify web_fetcher
python {skill_dir}/scripts/web_fetcher.py fetch https://support.huaweicloud.com/icp/index.html --mode text

# Verify web_searcher (requires Playwright)
python {skill_dir}/scripts/web_searcher.py search "ICP备案"
```

## Troubleshooting

| Issue | Solution |
| --- | --- |
| `ModuleNotFoundError: No module named 'requests'` | `pip install requests beautifulsoup4` |
| `ModuleNotFoundError: No module named 'playwright'` | Search requires Playwright; alternatively use web_fetcher only |
| Playwright browser launch failure | Run `playwright install chromium`; or set `REMOTE_CHROME_HOST` to use a remote Chrome |
| Fetch returns 404 | Document URL may have changed; try using web_searcher to find the new URL |
| Fetch content is empty or garbled | Check network connection and verify the URL is correct |
