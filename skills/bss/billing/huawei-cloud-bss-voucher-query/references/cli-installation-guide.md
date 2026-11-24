# KooCLI Installation and Authentication

## 1. Install KooCLI (hcloud)

Install in three separate steps — download, verify, then execute. Never pipe a
downloaded script into an interpreter, and never chain the download and the
execution in one command.

**Step 1 — download the official installer script (no execution):**

```bash
curl -fsSL -o hcloud_install.sh \
  https://hwcloudcli.obs.cn-north-1.myhuaweicloud.com/cli/latest/hcloud_install.sh
```

**Step 2 — verify the downloaded file before running it:**

```bash
# 2a. Record the digest and compare it with the value published on the official
#     KooCLI download page / a copy obtained from a trusted machine.
sha256sum hcloud_install.sh

# 2b. Read the script. It must only download/unpack the hcloud binary and set up
#     PATH; any network call to a host other than the official Huawei Cloud OBS
#     endpoint, any credential handling, or any unrelated side effect → stop.
less hcloud_install.sh
```

Proceed only when the digest matches the trusted reference **and** the script
content has been reviewed.

**Step 3 — execute the reviewed local file (separate command):**

```bash
bash ./hcloud_install.sh
```

**Step 4 — verify the installation:**

```bash
hcloud version
hcloud -v
```

If the digest cannot be cross-checked, prefer the pip channel below (artifacts
are integrity-checked by pip against the index) or install from the official
package published on the Huawei Cloud download page.

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