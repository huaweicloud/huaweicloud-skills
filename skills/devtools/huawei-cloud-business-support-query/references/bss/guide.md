# BSS Python Script Usage Guide

---

### list_cities.py — Query City List

Purpose: Query city list, including query count.
Usage: python scripts/bss/list_cities.py -h

---

### list_conversions.py — Query Measurement Unit Conversion Information

Purpose: Query measurement unit conversion information.
Usage: python scripts/bss/list_conversions.py -h

---

### list_costs.py — Query Cost List

Purpose: Query cost list, including currency.
Usage: python scripts/bss/list_costs.py -h

---

### list_counties.py — Query District/County List

Purpose: Query district/county list, including query count.
Usage: python scripts/bss/list_counties.py -h

---

### list_customer_account_change_records.py — Query Customer Account Transaction Details

Purpose: Query customer account transaction details, including account_change_id,
transaction detail type, transaction time, transaction ID, change amount,
balance after change, income/expense type, billing period, payment channel ID,
payment channel number, consumption time, account name, cloud service type name,
resource type name, currency.
Usage: python scripts/bss/list_customer_account_change_records.py -h

---

### list_customer_bills_fee_records.py — Query Customer Bill Fee Records

Purpose: Query customer bill fee records, including currency.
Usage: python scripts/bss/list_customer_bills_fee_records.py -h

---

### list_customer_bills_monthly_break_down.py — Query Customer Bill Monthly Amortization Details

Purpose: Query customer bill monthly amortization details, including currency.
Usage: python scripts/bss/list_customer_bills_monthly_break_down.py -h

---

### list_customer_coupon_change_records.py — Query Customer Coupon Transaction Details

Purpose: Query customer coupon transaction details, including coupon ID,
transaction detail type, transaction time, transaction ID, change amount,
balance after change, income/expense type, billing period, account name,
cloud service type name, resource type name, currency.
Usage: python scripts/bss/list_customer_coupon_change_records.py -h

---

### list_customer_orders.py — Query Customer Order List

Purpose: Query customer order list.
Usage: python scripts/bss/list_customer_orders.py -h

---

### list_customerself_resource_record_details.py — Query Customer Resource Consumption Record Details

Purpose: Query customer resource consumption record details, including currency.
Usage: python scripts/bss/list_customerself_resource_record_details.py -h

---

### list_customerself_resource_records.py — Query Customer Resource Consumption Records

Purpose: Query customer resource consumption records, including currency.
Usage: python scripts/bss/list_customerself_resource_records.py -h

---

### list_enterprise_multi_account.py — Query Enterprise Multi-Account Recoverable Balance

Purpose: Query enterprise multi-account recoverable balance.
Usage: python scripts/bss/list_enterprise_multi_account.py -h

---

### list_enterprise_organizations.py — Query Enterprise Organization Node List

Purpose: Query enterprise organization node list.
Usage: python scripts/bss/list_enterprise_organizations.py -h

---

### list_enterprise_sub_customers.py — Query Enterprise Sub-Customer List

Purpose: Query enterprise sub-customer list.
Usage: python scripts/bss/list_enterprise_sub_customers.py -h

---

### list_free_resource_infos.py — Query Free Resource Information List

Purpose: Query free resource information list.
Usage: python scripts/bss/list_free_resource_infos.py -h

---

### list_free_resource_usages.py — Query Free Resource Usage

Purpose: Query free resource usage.
Usage: python scripts/bss/list_free_resource_usages.py -h

---

### list_free_resources_usage_records.py — Query Free Resource Usage Records

Purpose: Query free resource usage records.
Usage: python scripts/bss/list_free_resources_usage_records.py -h

---

### list_measure_units.py — Query Measurement Unit List

Purpose: Query measurement unit list.
Usage: python scripts/bss/list_measure_units.py -h

---

### list_multi_account_retrieve_coupons.py — Query Enterprise Multi-Account Recoverable Cash Coupons

Purpose: Query enterprise multi-account recoverable cash coupons.
Usage: python scripts/bss/list_multi_account_retrieve_coupons.py -h

---

### list_multi_account_transfer_coupons.py — Query Enterprise Multi-Account Transferable Cash Coupons

Purpose: Query enterprise multi-account transferable cash coupons.
Usage: python scripts/bss/list_multi_account_transfer_coupons.py -h

---

### list_pay_per_use_customer_resources.py — Query Pay-Per-Use Customer Resource List

Purpose: Query pay-per-use customer resource list.
Usage: python scripts/bss/list_pay_per_use_customer_resources.py -h

---

### list_provinces.py — Query Province List

Purpose: Query province list, including query count.
Usage: python scripts/bss/list_provinces.py -h

---

### list_renew_rate_on_period.py — Query Yearly/Monthly Product Renewal Pricing

Purpose: Query yearly/monthly product renewal pricing.
Usage: python scripts/bss/list_renew_rate_on_period.py -h

---

### list_resource_types.py — Query Resource Type List

Purpose: Query resource type list.
Usage: python scripts/bss/list_resource_types.py -h

---

### list_resource_usage.py — Query Resource Usage

Purpose: Query resource usage, including effective days.
Usage: python scripts/bss/list_resource_usage.py -h

---

### list_resource_usage_summary.py — Query Resource Usage Summary

Purpose: Query resource usage summary, including total count.
Usage: python scripts/bss/list_resource_usage_summary.py -h

---

### list_service_resources.py — Query Service Resource List

Purpose: Query service resource list.
Usage: python scripts/bss/list_service_resources.py -h

---

### list_service_types.py — Query Service Type List

Purpose: Query service type list.
Usage: python scripts/bss/list_service_types.py -h

---

### list_stored_value_cards.py — Query Stored Value Card List

Purpose: Query stored value card list, including card_id, card_name, status, face_value, balance, effective_time, expiry_time.
Usage: python scripts/bss/list_stored_value_cards.py -h

---

### list_usage_types.py — Query Usage Type List

Purpose: Query usage type list.
Usage: python scripts/bss/list_usage_types.py -h

---

### show_customer_account_balances.py — Query Customer Account Balance

Purpose: Query customer account balance, including account ID, account_type, amount, currency, designated_amount, credit_amount, measurement unit ID.
Usage: python scripts/bss/show_customer_account_balances.py -h

---

### show_customer_monthly_sum.py — Query Customer Monthly Summary Bill

Purpose: Query customer monthly summary bill, including total count.
Usage: python scripts/bss/show_customer_monthly_sum.py -h

---

### show_customer_order_details.py — Query Customer Order Details

Purpose: Query customer order details.
Usage: python scripts/bss/show_customer_order_details.py -h

---

### show_multi_account_transfer_amount.py — Query Enterprise Multi-Account Transferable Balance

Purpose: Query enterprise multi-account transferable balance.
Usage: python scripts/bss/show_multi_account_transfer_amount.py -h

---

### show_refund_order_details.py — Query Refund Order Details

Purpose: Query refund order details.
Usage: python scripts/bss/show_refund_order_details.py -h

---

## Enhanced Pricing Inquiry Scripts

The following scripts provide enhanced pricing inquiry capabilities, covering scenarios that the BSS pricing API does not support or is difficult to use.

---

### list_on_demand_resource_ratings.py — On-Demand Resource Pricing

Purpose: Query on-demand resource pricing, supports `--preset` preset templates to simplify parameters, `--sort price` to sort by price.
Supported cloud services follow the pricing support matrix; for unsupported cloud services, indicate that the current product does not support pricing inquiry.
Usage: python scripts/bss/list_on_demand_resource_ratings.py -h

---

### list_rate_on_period_detail.py — Yearly/Monthly Pricing

Purpose: Query yearly/monthly product pricing details, supports `--preset` preset templates to simplify parameters.
Supported cloud services follow the pricing support matrix; for unsupported cloud services, indicate that the current product does not support pricing inquiry.
Usage: python scripts/bss/list_rate_on_period_detail.py -h

---

### inquiry_elb.py — ELB Dedicated Pricing

Purpose: ELB elastic load balancing pricing, based on LCU billing model (dedicated type = LCU fee + instance fee, shared type = free).
Fetches real-time specifications and LCU count via ELB API, supports `--type L4/L7/elastic/all`, `--az_count`, `--show_sold_out`.
Usage: python scripts/bss/inquiry_elb.py -h

---

### inquiry_nat.py — NAT Gateway Dedicated Pricing

Purpose: NAT gateway pricing, supports public NAT (specifications 1-4) and private NAT (Small-Extra-xlarge).
Fetches available specification list via NAT API, combines with pricing table to output on-demand/monthly prices.
Usage: python scripts/bss/inquiry_nat.py -h

---

### inquiry_dcs.py — DCS Distributed Cache Dedicated Pricing

Purpose: DCS cache pricing, supports single/standby/Cluster architecture, billed by memory specification.
Outputs on-demand and monthly prices for each specification.
Usage: python scripts/bss/inquiry_dcs.py -h

---

## Pricing Support Matrix

The following summarizes the support status of each cloud service in the BSS pricing scripts.

| Cloud Service | Billing Mode | On-Demand Pricing | Period Pricing |
|---------------|-------------|-------------------|----------------|
| Elastic Cloud Server (ECS) | On-demand, Period | `--preset ecs` | `--preset ecs` |
| Elastic Volume Service (EVS) | On-demand, Period | `--preset evs` | `--preset evs` |
| Elastic IP - Bandwidth (EIP-BW) | On-demand, Period | `--preset eip-bw` | `--preset eip-bw` |
| Elastic IP - Traffic (EIP-Flow) | On-demand | `--preset eip-flow` | - |
| Elastic IP (EIP-IP) | On-demand, Period | `--preset eip-ip` | `--preset eip-ip` |
| Virtual Private Cloud (VPC) | On-demand | `--preset vpc` | - |
| Elastic Load Balance (ELB) | On-demand, Period | `inquiry_elb.py` | `inquiry_elb.py` |
| NAT Gateway (NAT) | On-demand, Period | `inquiry_nat.py` | `inquiry_nat.py` |
| Object Storage Service (OBS) | On-demand | `--preset obs` | - |
| Scalable File Service (SFS) | On-demand, Period | `--preset sfs` | `--preset sfs` |
| Virtual Private Network (VPN) | On-demand, Period | `--preset vpn` | `--preset vpn` |
| Cloud Eye (CES) | On-demand | `--preset ces` | - |
| Image Management Service (IMS) | On-demand | `--preset ims` | - |
| Bare Metal Server (BMS) | Period | - | `--preset bms` |
