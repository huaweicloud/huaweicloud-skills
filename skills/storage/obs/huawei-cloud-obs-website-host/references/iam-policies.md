# IAM Policy - Huawei Cloud OBS Website Host

## Permission Usage

| API Action | Permission | Purpose |
|------------|------------|---------|
| obs:bucket:HeadBucket | Read bucket existence/access status | Verify bucket exists and caller can access it before configuration |
| obs:bucket:GetBucketLocation | Read bucket region | Verify bucket region matches expected deployment region |
| obs:bucket:GetBucketCustomDomainConfiguration | Read bucket custom domain configuration | Check whether a custom domain is already registered |
| obs:bucket:GetBucketWebsite | Read bucket website configuration | Check static website hosting settings |
| dns:recordset:list | List DNS recordsets | Check whether the CNAME record exists |
| dns:zone:get | Read DNS zone details | Confirm the target zone exists |
| dns:zone:list | List DNS zones | Find the target zone |
| obs:bucket:PutBucketCustomDomainConfiguration | Update bucket custom domain configuration | Register or update a custom domain |
| obs:bucket:PutBucketWebsite | Update bucket website configuration | Set index/error page |
| dns:recordset:create | Create DNS recordset | Create the CNAME record |

## Minimum Policy JSON

```json
{
  "Version": "1.1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "obs:bucket:HeadBucket",
        "obs:bucket:GetBucketLocation",
        "obs:bucket:GetBucketCustomDomainConfiguration",
        "obs:bucket:GetBucketWebsite",
        "obs:bucket:PutBucketCustomDomainConfiguration",
        "obs:bucket:PutBucketWebsite",
        "dns:recordset:create",
        "dns:recordset:list",
        "dns:zone:get",
        "dns:zone:list"
      ],
      "Resource": [
        "*"
      ]
    }
  ]
}
```

## Notes

- If you run `verify_obs_website.py` with `--bucket-name/--region`, `obs:bucket:HeadBucket` and `obs:bucket:GetBucketLocation` are required.
- If you only configure bucket-level static website hosting and do not use a custom domain, DNS permissions are optional.
- If you use a custom domain, both OBS and DNS permissions above are required.
