# Troubleshooting: hcloud (KooCLI) Cannot Reach CES — DNS Intranet-IP Issue

## Symptoms

When running `hcloud CES ...`:
- Connection timeout / `[ERROR] 网络连接异常`
- Error messages containing `curl: (28)`, `SSL`, `Connection timed out`
- Works in some regions (e.g. cn-east-3, cn-south-1), fails in others (e.g. cn-north-4)

## Root cause

In this sandbox/job environment, the local DNS (usually the internal DNS of the Huawei Cloud EIP environment) resolves
`ces.<region>.myhuaweicloud.com` to a **Huawei Cloud intranet IP (100.125.x.x)**.
The intranet IP is reachable only inside a Huawei Cloud VPC; this environment (public internet) cannot reach it, so the connection fails.

Measured (2026-09):
```
ces.cn-north-4.myhuaweicloud.com -> 100.125.12.100   (intranet, unreachable)
ces.cn-east-3.myhuaweicloud.com  -> 119.3.120.121    (public, reachable)
```

## Troubleshooting steps (all command-line, one-off script)

1. Confirm whether it is a DNS issue:

```bash
getent hosts ces.<region-code>.myhuaweicloud.com
```

2. If it resolves to `100.125.x.x` (or `100.64.x.x`, `10.x.x.x` and other private ranges),
   look up the domain's public resolution with an **external public DNS** (bypassing the local polluted resolution):

```bash
curl -s "https://223.5.5.5/resolve?name=ces.<region-code>.myhuaweicloud.com&type=A"
```

   Take the `data` fields of `Answer` entries whose `type` is 1 (A records) in order to get the public IP list,
   e.g. cn-north-4: `120.46.246.26`, `120.46.247.26`.

3. Verify reachability by direct public-IP connection (keep the domain as SNI so the certificate does not error):

```bash
curl -sk -o /dev/null -w "%{http_code}\n" \
  --resolve ces.<region-code>.myhuaweicloud.com:443:<public-IP> \
  https://ces.<region-code>.myhuaweicloud.com/
```

   Returning `200` means reachable.

4. Write the public IP into `/etc/hosts` (back up first):

```bash
cp /etc/hosts /etc/hosts.bak-$(date +%Y%m%d%H%M%S)
echo "<public-IP> ces.<region-code>.myhuaweicloud.com" >> /etc/hosts
```

   Re-run `getent hosts ces.<region-code>.myhuaweicloud.com` to confirm it now resolves to the public IP.

5. Call hcloud again (the CES endpoint domain is unchanged; hcloud follows the public IP in hosts):

```bash
hcloud CES ListMetrics --cli-region=cn-north-4 --namespace=SYS.ECS --limit=1 --cli-output=json
```

   Returning `{"metrics": [...]}` means recovery.

## Alternative (when you prefer not to modify /etc/hosts)

- Add `--cli-endpoint` to point hcloud at the public IP (note: may fail due to certificate SNI mismatch; prefer the /etc/hosts approach):

```bash
hcloud CES ListMetrics --cli-region=cn-north-4 --namespace=SYS.ECS \
  --cli-endpoint=https://120.46.246.26 --cli-skip-secure-verify=true ...
```

- Or temporarily increase `cli-read-timeout`/`cli-connect-timeout` to distinguish timeout from unreachability:

```bash
hcloud CES ListMetrics ... --cli-connect-timeout=10 --cli-read-timeout=30
```

## CES endpoints for common regions

| Region code | Chinese region name | Public reachability (measured 2026-09) |
|---|---|---|
| cn-east-3 | 华东-上海一 | public (119.3.120.121) |
| cn-north-4 | 华北-北京四 | DNS once pointed intranet; hosts fix needed (public 120.46.246.26) |
| cn-north-1 | 华北-北京一 | public (49.4.121.52) |
| cn-south-1 | 华南-广州 | public (124.71.88.36) |
| ap-southeast-1 | 中国-香港 | public (101.44.110.5) |
| cn-east-2 | 华东-上海二 | refer to the same batch public IP |

> Public IPs can change; follow the troubleshooting steps, and do not hardcode IPs in code.

## Applicability: CCE metrics go through AOM, same approach

CCE metrics in this skill go through `hcloud AOM` (endpoint `aom.<region>.myhuaweicloud.com`),
which is a different domain from CES. If `smoke --region <region>` shows `aom: ...` failing
(e.g. `[NETWORK_ERROR]`), run the steps above, simply replacing
`ces.<region-code>.myhuaweicloud.com` with `aom.<region-code>.myhuaweicloud.com`:

```bash
getent hosts aom.<region-code>.myhuaweicloud.com
curl -s "https://223.5.5.5/resolve?name=aom.<region-code>.myhuaweicloud.com&type=A"
```