# KooCLI Installation and Authentication

## 1. Install KooCLI (hcloud)

```bash
# Linux / macOS (curl)
curl -sSL https://hwcloudcli.obs.cn-north-1.myhuaweicloud.com/cli/latest/hcloud_install.sh -o hcloud_install.sh && bash hcloud_install.sh

# Verify
hcloud version
hcloud -v
```

Alternative via pip (SDK fallback used by `list_coupons.py` when hcloud is not
installed):

```bash
pip install huaweicloudsdkcore huaweicloudsdkbss
```

## 2. Configure credentials (AK/SK)

Configure credentials **out-of-band** — never paste AK/SK into a chat, issue,
or PR:

```bash
hcloud configure set --cli-my-ak=<YOUR_ACCESS_KEY> --cli-my-sk=<YOUR_SECRET_KEY>
hcloud configure set --cli-project-id=<project_id>
hcloud configure set --cli-region=cn-north-1
```

Or export standard credential environment variables (recognized by the SDK
fallback path automatically):

```bash
export HUAWEICLOUD_SDK_AK=<YOUR_ACCESS_KEY>
export HUAWEICLOUD_SDK_SK=<YOUR_SECRET_KEY>
export HW_DOMAIN_ID=<your_domain_id>   # optional, BSS global service
```

The script itself never handles, logs, or stores credentials.

## 3. Verify BSS command availability

```bash
hcloud BSS ListSubCustomerCoupons --help
hcloud BSS ListCustomerOrders --help
```

> The coupon-list API (`ListSubCustomerCoupons`) is a **global (domain)** API
> and carries no `enterprise_project_id` parameter and no project field in its
> records. No project parameter is ever sent to it; project filtering is done
> client-side in the script via the order linkage.