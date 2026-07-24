# SMN Subscription Guide

## Overview

This guide explains how to create email/SMS subscriptions for SMN (Simple Message Notification) topics to receive alarm notifications.

## Method 1: Using Skill Script (Recommended)

The skill provides an automated script that uses your hcloud CLI configuration - **no need to manually enter AK/SK**.

### Usage

```bash
cd /mnt/d/huaweicloud-skills/skills/monitoring/ecs/huawei-cloud-ecs-alert

./scripts/create_email_subscription.sh
```

### What It Does

1. ✅ Checks hcloud CLI configuration
2. ✅ Creates email subscription to `<your-email@example.com>`
3. ✅ Uses the SMN topic (configured in script or via environment variable)
4. ✅ Returns subscription URN for verification

### Expected Output

```
==========================================
SMN Email Subscription Created
==========================================

Topic: urn:smn:cn-north-4:xxxxxxxxxxxxxxxxxxxxxxxxxxxxx:ECS_ALARM_NOTIFY
Email: user@example.com
Remark: ECS CPU Alarm Notification
Region: cn-north-4

Checking hcloud configuration...
✅ hcloud configuration is valid

Creating email subscription...

✅ Subscription created successfully!
   Subscription URN: urn:smn:cn-north-4:xxxxxxxxxxxxxxxxxxxxxxxxxxxxx:ECS_ALARM_NOTIFY:xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

⚠️  IMPORTANT: Please check email at user@example.com and click the confirmation link
   Subscription only becomes active after confirmation

==========================================
Complete
==========================================
```

### Next Steps

1. **Check your email** at `<your-email@example.com>`
2. **Click the confirmation link** in the email from Huawei Cloud
3. **Verify subscription** is active:

   ```bash
   ./scripts/list_subscriptions.sh
   ```

## Method 2: Huawei Cloud Console (Alternative)

If you prefer GUI operations:

### Steps

1. **Log in to Huawei Cloud Console**
   - URL: https://console.huaweicloud.com/smn/?region=cn-north-4

2. **Navigate to Topics**
   - Left menu: **Topic Management**
   - Region: **Beijing 4 (cn-north-4)**

3. **Find the Topic**
   - Locate: `ECS_ALARM_NOTIFY_TEST`

4. **Create Subscription**
   - Click **Subscribe** button
   - Fill in:
     - **Protocol**: Email
     - **Endpoint**: `<your-email@example.com>`
     - **Remark**: `ECS CPU Alarm Notification`
   - Click **Create**

5. **Confirm Subscription**
   - Check email at the address you provided
   - Click the confirmation link

## Verification

After creating the subscription, verify it's active:

```bash
./scripts/list_subscriptions.sh
```

Expected output:

```
========== Topic List ==========
✓ ECS_ALARM_NOTIFY_TEST

========== Subscription List ==========
  email  -> user@example.com

Query complete
```

## Troubleshooting

### Issue 1: Email Not Received

**Possible Causes**:

- Email went to spam folder
- Email address is incorrect
- Huawei Cloud email service delay

**Solutions**:

1. Check spam/junk folder
2. Verify email address is correct
3. Wait 5-10 minutes for delivery
4. Try recreating the subscription

### Issue 2: Subscription Shows "Unconfirmed"

**Solution**:

- The subscription requires email confirmation
- Check email and click the confirmation link
- If email expired, delete and recreate the subscription

### Issue 3: Permission Denied (403)

**Solution**:

- Ensure your account has `SMN FullAccess` policy
- Contact your account administrator to grant permissions

## Security Notes

- ✅ Email subscriptions are tied to your Huawei Cloud account
- ✅ Confirmation links expire after 24 hours
- ✅ Each topic supports up to 10,000 subscriptions
- ✅ Delete unused subscriptions to avoid clutter

## Related Documents

- [CLI Installation Guide](cli-installation-guide.md)
- [IAM Policies](iam-policies.md)
- [Troubleshooting](troubleshooting.md)
