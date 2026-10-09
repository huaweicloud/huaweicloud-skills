# Verification Method

## Environment Verification

1. SDK installed:
   ```bash
   python3 -c "import huaweicloudsdkbss; print(huaweicloudsdkbss.__version__ if hasattr(huaweicloudsdkbss,'__version__') else 'ok')"
   pip show huaweicloudsdkbss | head -2   # expect 3.1.x
   ```
2. Credentials present (never hardcode): `HUAWEICLOUD_SDK_AK` / `HUAWEICLOUD_SDK_SK`
   (the SDK also reads `HUAWEI_ACCESS_KEY` / `HUAWEI_SECRET_KEY`).
3. Optional: `HTTPS_PROXY` for corporate intranet environments; `SKILL_QUALITY_DISABLE=1`
   to turn off quality reporting during local debugging.

## Read-Only Smoke Test

The cheapest authorized queries to prove the credential/partner binding works:

```python
import os
from huaweicloudsdkcore.auth.credentials import GlobalCredentials
from huaweicloudsdkbss.v2 import BssClient, ListPartnerBalancesRequest, ListServiceTypesRequest

creds = GlobalCredentials(os.environ["HUAWEICLOUD_SDK_AK"], os.environ["HUAWEICLOUD_SDK_SK"])
client = BssClient.new_builder().with_credentials(creds).with_endpoints(["https://bss.myhuaweicloud.com"]).build()

resp = client.list_partner_balances(ListPartnerBalancesRequest())
print("partner balances:", [(b.account_id, b.amount) for b in resp.account_balances])

resp2 = client.list_service_types(ListServiceTypesRequest(limit=5))
print("service types:", [s.service_type_code for s in resp2.service_types])
```

Expected outcomes:
- `list_partner_balances` returns the partner account balances → partner binding OK.
- `list_service_types` returns dictionary rows → API access OK (dictionary APIs are
  usually open to any authenticated account).
- `domain_id has no access to this api` → the account is not a partner; stop and
  inform the user (see `related-commands.md` error table).
- `CBC.0151` → permission insufficient; do not retry loop.

## Per-Operation Verification

For each entry point in `semantic/catalog.yml`:
1. Copy the `####` template from `references/related-commands.md`.
2. Run with `limit=1` (minimal page) first.
3. Check the response against the fact's `grain` and `evidence_boundary` in
   `semantic/models/*.yml` — the assertion must stay within the boundary.
4. Record PASS (rows returned) / PASS-empty (authorized, zero rows) / FAIL with the
   exact error code.

## Acceptance Gate

All 30 source operations must be exercised in one of three states:
- `PASS` — authorized, data returned,
- `PASS(empty)` — authorized, no data (normal for a fresh partner account),
- `AUTH-BLOCKED` — API requires partner permission the test account lacks
  (e.g. `ListFreeResourceInfos`); marked `requires manual verification` and
  explicitly listed in the test report; the command itself is verified against
  the SDK `_http_info` source so it is a permission issue, not a syntax issue.

A skill is verifiable (not verified) when all commands are either PASS/PASS(empty)
or AUTH-BLOCKED with evidence of the exact permission error.