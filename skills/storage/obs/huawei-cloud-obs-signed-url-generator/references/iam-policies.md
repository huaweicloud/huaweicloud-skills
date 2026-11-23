# IAM Policies for OBS Signed URL Generator

## Overview

This document defines the least-privilege IAM policies required for the OBS Signed URL Generator skill.

## Required Permissions

The skill generates signed URLs using OBS Python SDK. The principal (user or agency) needs the following OBS permissions:

### Minimum Required Policy

```json
{
    "Version": "5.0",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "obs:bucket:GetObject",
                "obs:object:GetObject"
            ],
            "Resource": [
                "obs:*:*:bucket:*",
                "obs:*:*:object:*"
            ]
        }
    ]
}
```

### Scoped to Specific Bucket

```json
{
    "Version": "5.0",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "obs:bucket:GetObject",
                "obs:object:GetObject"
            ],
            "Resource": [
                "obs:*:*:bucket:my-bucket",
                "obs:*:*:object:my-bucket/*"
            ]
        }
    ]
}
```

### With HEAD (Metadata) Access

```json
{
    "Version": "5.0",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "obs:bucket:GetObject",
                "obs:object:GetObject",
                "obs:object:GetMetadata"
            ],
            "Resource": [
                "obs:*:*:bucket:*",
                "obs:*:*:object:*"
            ]
        }
    ]
}
```

## System Policy Reference

The following Huawei Cloud system policies are relevant:

| Policy Name | Description |
|-------------|-------------|
| OBS ReadOnlyAccess | Read-only access to OBS buckets and objects |
| Tenant Administrator | Full access including image processing (recommended for image processing features) |

## Notes

- The `createSignedUrl` method generates URLs locally using AK/SK — it does not make API calls to OBS
- The signed URL grants temporary access to the object; the URL consumer needs no IAM permissions
- For image processing features, the account must have image processing enabled on the bucket
- Temporary credentials (AK/SK + SecurityToken) must have the same OBS permissions as permanent credentials
- IAM action names follow the `obs:{resource_type}:{action}` format verified via Huawei Cloud IAM documentation
