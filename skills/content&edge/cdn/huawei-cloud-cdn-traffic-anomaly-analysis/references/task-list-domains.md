# Step 2: List All CDN Domains

Get all online CDN domains under the current account.

## Command

```bash
hcloud CDN ListDomains/v2 \
  --cli-region=cn-north-4 \
  --page_size=100 \
  --page_number=1 \
  --domain_status=online
```

## Response Parsing

- `total` is the total number of domains; if > 100, pagination is required
- Extract `domain_name` from each domain

## Pagination

If `total > 100`, increment `page_number` and query again until all domains are retrieved.

## Example Response

```json
{
  "total": 50,
  "domains": [
    {
      "domain_name": "www.example.com",
      "domain_status": "online"
    }
  ]
}
```
