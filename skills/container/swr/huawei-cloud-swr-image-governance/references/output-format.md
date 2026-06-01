# SWR Image Governance — Output Format

## ShowNamespaceAuth (verified)

```json
{
  "id": 3827347,
  "name": "pancake",
  "creator_name": "hwstaff_p00506267",
  "self_auth": {
    "user_id": "05949eb5350010e21f85c017722182de",
    "user_name": "hwstaff_p00506267",
    "auth": 7
  },
  "others_auths": [
    {
      "user_id": "05949eb5350010e21f85c017722182de",
      "user_name": "hwstaff_p00506267",
      "auth": 7
    }
  ]
}
```

**Key Fields**:
- `self_auth`: Your own permission level on this namespace
- `others_auths`: Array of other users' permission levels
- `auth`: Permission value (7=manage, 3=edit, 1=read)
- `self_auth` is separate from `others_auths` — check both when auditing permissions

## ShowUserRepositoryAuth (verified)

```json
{
  "id": 3374887,
  "name": "openclaw-sandbox",
  "self_auth": {
    "user_id": "...",
    "user_name": "...",
    "auth": 7
  },
  "others_auths": []
}
```

Same structure as namespace auth but with repository `id` and `name`.

## ListRepoDomains (verified — uses `created/updated`, NOT `created_at/updated_at`)

Response is a flat JSON array (not wrapped in an object):

```json
[
  {
    "namespace": "pancake",
    "repository": "openclaw-sandbox",
    "access_domain": "shijingcheng_test",
    "permit": "read",
    "deadline": "forever",
    "description": "",
    "creator_id": "05949eb5350010e21f85c017722182de",
    "creator_name": "hwstaff_p00506267",
    "created": "2026-04-28T09:18:19.830309Z",
    "updated": "2026-04-28T09:18:19.83031Z",
    "status": true
  }
]
```

**Key Fields**:
- `access_domain`: Shared download domain name
- `permit`: Permission type (`read`)
- `deadline`: Expiration (`forever` or specific date)
- `status`: Whether the domain is active (boolean)
- `created`/`updated`: Timestamps (**NOT** `created_at`/`updated_at`)

## CheckAgency (verified)

```json
{
  "domain_id": "05949eb4190010e40f36c017b62fafa0",
  "is_agency": true
}
```

**Key Fields**:
- `is_agency`: Whether agency delegation is enabled (boolean)
- `domain_id`: Domain ID (hex string)

## ShowShareFeatureGates (verified)

```json
{
  "enable_experience": true,
  "enable_hss_service": true,
  "enable_image_scan": true,
  "enable_sm3": false,
  "enable_image_sync": true,
  "enable_cci_service": true,
  "enable_image_label": false,
  "enable_pipeline": true,
  "enable_authorization_token": true,
  "enable_resource": true,
  "enable_list_v3": true,
  "enable_image_quota": false,
  "enable_cosign_signature": true,
  "enable_enterprise_edition_link": false,
  "enable_customize_validity_period": true,
  "swr_util_download_url": ""
}
```

**Key Feature Gates**:
- `enable_experience`: Shared image experience
- `enable_image_scan`: Security scan
- `enable_image_sync`: Cross-region sync
- `enable_cosign_signature`: Cosign signature verification
- `enable_authorization_token`: Authorization token

## ListGlobalFeatureGates (verified)

```json
{
  "enableUserDefObs": true,
  "enableEnterprise": true,
  "cerAvailable": true,
  "enableIntranetAccessSwitch": true,
  "enableOBSEncryptUserKmsKey": true
}
```

**Key Feature Gates**:
- `enableUserDefObs`: Custom OBS bucket
- `enableEnterprise`: Enterprise edition features
- `cerAvailable`: CER available
- `enableIntranetAccessSwitch`: Intranet access toggle
- `enableOBSEncryptUserKmsKey`: OBS encryption with user KMS key

## ListRetentions (verified — returns empty flat array when no rules)

```json
[]
```

When retention rules exist, response format to be verified with actual API call.

## ListRepoAccessories (verified)

```json
{
  "total": 0,
  "accessories": null
}
```

**Key Fields**:
- `total`: Total count of accessories
- `accessories`: Array of accessory objects (null when empty)

## ListSharedReposDetails

Returns flat array of repository objects with same fields as ListReposDetails (name, category, description, size, is_public, num_images, num_download, created_at, updated_at, path, internal_path, domain_name, namespace, tags, status, total_range). Response format identical to image-management `ListReposDetails`.