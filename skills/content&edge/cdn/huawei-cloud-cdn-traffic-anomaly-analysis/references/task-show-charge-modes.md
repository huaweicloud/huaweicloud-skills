# Step 1: Query Account Billing Mode

Query the account's billing mode to determine which metric to analyze.

## Command

```bash
hcloud CDN ShowChargeModes \
  --cli-region=cn-north-4 \
  --product_type=base
```

## Response Parsing

- Extract the record where `status == "active"` from the `result` array
- Extract the `charge_mode` field (e.g., `bw_95`, `flux`, `bw`, etc.)
- If there are records for both domestic and overseas, use the record where `service_area == "mainland_china"`

## Example Response

```json
{
  "result": [
    {
      "status": "active",
      "service_area": "mainland_china",
      "charge_mode": "bw_95"
    }
  ]
}
```

## Billing Mode Mapping

| Billing Mode | Description | Metric to Query |
|--------------|-------------|-----------------|
| `bw_95` | 95th percentile bandwidth | Daily 95th bandwidth |
| `flux` | Traffic-based | Daily traffic |
| `combine_flux` | Combined traffic | Daily traffic |
| `bw` | Bandwidth-based | Daily peak bandwidth |
| `bw_peak` | Daily peak monthly average | Daily peak bandwidth |
