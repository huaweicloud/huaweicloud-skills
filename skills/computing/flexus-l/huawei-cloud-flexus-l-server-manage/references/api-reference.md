# API Reference

## Huawei Cloud APIs Used

### 1. HCSS API - Flexus L Instance Management

**Base URL:** `https://hcss.cn-north-4.myhuaweicloud.com`

| Endpoint | Method | Description | Full URL |
| ---------- | -------- | ------------- | ---------- |
| `/v1/light-instances` | POST | Create Flexus L instance | `https://hcss.cn-north-4.myhuaweicloud.com/v1/light-instances` |

**Create Instance Request Body:**

```json
{
  "instance_name": "string",
  "description": "string",
  "plan_spec": "hf.small.1.win",
  "image_ref": {
    "image_name": "WindowsServer",
    "image_version": "2012R2_standard_ch"
  },
  "region": "cn-north-4",
  "charging_mode": "prePaid",
  "period_type": "month",
  "period_num": 1,
  "purchase_quantity": 1,
  "is_auto_renew": true,
  "is_auto_pay": true,
  "extra_resources": [
    {"type": "evs", "size": 20},
    {"type": "cbr", "size": 20},
    {"type": "hss"}
  ]
}
```

### 2. BSS API - Billing Service

**Base URL:** `https://bss.myhuaweicloud.com`

| Endpoint | Method | Description | Full URL |
| ---------- | -------- | ------------- | ---------- |
| `/v2/orders/subscriptions/resources/renew` | POST | Renew resources | `https://bss.myhuaweicloud.com/v2/orders/subscriptions/resources/renew` |
| `/v2/orders/subscriptions/resources/unsubscribe` | POST | Unsubscribe resources | `https://bss.myhuaweicloud.com/v2/orders/subscriptions/resources/unsubscribe` |

### 3. IAM API - Identity Management

**Endpoint:** `https://iam.myhuaweicloud.com/v3/projects`

Used to get Project ID by region.
