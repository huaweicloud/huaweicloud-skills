# Validation Rules

- The website endpoint should follow `BucketName.obs.<region>.myhuaweicloud.com`.
- Public read must be enabled for website files, or the site will return access errors.
- A custom domain must point to the OBS website endpoint with a CNAME record.
- Treat DNS propagation as eventual; the setup is not complete until name resolution works.
- Root path verification and one missing-path check are mandatory.
