# BSS Service SDK Initialization Notes

## Key Requirement: GlobalCredentials

BSS (Business Support System) service SDK **must** use `GlobalCredentials` instead of `BasicCredentials`.

## Correct Initialization

```python
from huaweicloudsdkcore.auth.credentials import GlobalCredentials
from huaweicloudsdkbss.v2.bss_client import BssClient
from huaweicloudsdkbss.v2.region.bss_region import BssRegion

credentials = GlobalCredentials(
    ak=os.environ.get("HUAWEI_ACCESS_KEY"),
    sk=os.environ.get("HUAWEI_SECRET_KEY")
)

client = BssClient.new_builder() \
    .with_credentials(credentials) \
    .with_endpoints(["https://bss.myhuaweicloud.com"]) \
    .build()
```

## Common Mistakes

| Mistake | Why It Fails | Fix |
|---------|-------------|-----|
| Using `BasicCredentials` | BSS is a global service, not region-specific | Use `GlobalCredentials` |
| Using `with_region(BssRegion.value_of("cn-north-4"))` | BSS doesn't support region-based routing | Use `with_endpoints(["https://bss.myhuaweicloud.com"])` |
| `list_sub_customer_coupons` returns 400 | Default `limit` may exceed max value | BSS `limit` max is 100, not 200 |

## Environment Variables

- `HUAWEI_ACCESS_KEY` or `HWC_AK` — Access Key
- `HUAWEI_SECRET_KEY` or `HWC_SK` — Secret Key

**Never hardcode AK/SK in scripts or SKILL.md.**
