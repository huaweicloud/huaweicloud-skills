# OBS Python SDK Website Configuration Notes

Use Huawei Cloud OBS Python SDK (`esdk-obs-python >= 3.x`) for static website hosting configuration.

## SDK package

- Install: `pip install esdk-obs-python`
- Required imports:
  ```python
  from obs import ObsClient, WebsiteConfiguration, IndexDocument, ErrorDocument
  ```

## Required action

Use SDK method for bucket website configuration:

```python
website = WebsiteConfiguration(
    indexDocument=IndexDocument(suffix='index.html'),
    errorDocument=ErrorDocument(key='error.html')  # optional
)
resp = client.setBucketWebsite('bucket-name', website)
```

**⚠️ Breaking Change:**  
The older SDK style used keyword arguments such as `setBucketWebsite(bucketName, indexDocumentSuffix=..., errorDocument=...)`. That pattern is **deprecated in `esdk-obs-python >= 3.x`**. The new API requires a `WebsiteConfiguration` object. `indexDocument` must be an `IndexDocument(suffix='...')` object, and `errorDocument` must be an `ErrorDocument(key='...')` object.

### Custom domain registration

If you need a custom domain, you must register it on the OBS bucket in addition to creating the DNS CNAME record:

```python
# Register a custom domain on the bucket (HTTP mode)
resp = client.setBucketCustomDomain('bucket-name', 'www.example.com')
```

### Custom domain HTTPS

OBS static website hosting serves HTTP by default, but it **does support HTTPS on a custom domain** by attaching an SSL certificate directly to the bucket custom domain (no CDN required). Only international (general) certificates are supported, not SM (Chinese national crypto) certificates. Configuration only works over HTTPS API requests.

Two ways to attach a certificate:

```python
# 1) Direct PEM upload: provide name + certificate + privateKey
cert_info = {
    "name": "cert-name",                       # 3-63 chars
    "certificate": "-----BEGIN CERTIFICATE-----\n...",   # PEM, line breaks escaped with \n
    "privateKey": "-----BEGIN RSA PRIVATE KEY-----\n..."  # no passphrase-protected keys
}
resp = client.setBucketCustomDomain('bucket-name', 'www.example.com', certificateInfo=cert_info)

# 2) Reference a CCM certificate by ID (Cloud Certificate Manager)
cert_info = {
    "name": "cert-name",                       # 3-63 chars
    "certificateId": "xxxxxxxxxxxxxxxx"        # 16-char CCM certificate ID
}
resp = client.setBucketCustomDomain('bucket-name', 'www.example.com', certificateInfo=cert_info)

# Query registered custom domains
resp = client.getBucketCustomDomain('bucket-name')
# resp.body == {'domains': [{'domainName': 'www.example.com', 'createTime': '...'}]}

# Delete a custom domain
resp = client.deleteBucketCustomDomain('bucket-name', 'www.example.com')
```

HTTPS constraints:
- OBS only hosts HTTPS certificates on **custom domains** (not the default bucket domain, which is managed by Huawei Cloud).
- Only international (general) certificates; SM (national crypto) certificates are not supported.
- At least one international certificate must be configured before a CA certificate.
- Max one international certificate + one CA certificate per custom domain; max 100 custom domains per bucket.
- Certificate binding takes effect within about 60 seconds.
- Bucket names **containing dots (`.`)** may cause HTTPS certificate verification failures on the client; use a custom domain instead.

## Minimal flow

1. Create `ObsClient` with AK/SK and OBS endpoint.
2. Create `WebsiteConfiguration` with `IndexDocument` (and optional `ErrorDocument`).
3. Call `client.setBucketWebsite(bucket_name, website)`.
4. If custom domain needed, call `client.setBucketCustomDomain(bucket_name, domain_name)`.
5. If HTTPS on the custom domain is required, attach a certificate via the `certificateInfo` dict (PEM or CCM `certificateId`).
6. Check the HTTP status code (`2xx` expected).
7. Verify the website endpoint with an HTTP GET to the root path (add `--https` to also verify TLS).

## Common failures

- `setBucketWebsite` with `unexpected keyword argument 'indexDocumentSuffix'` → use the new `WebsiteConfiguration` object style
- `403`: two common causes must both be considered and reported to the user: missing policy/ACL for anonymous public read, or insufficient AK/SK IAM permissions for website configuration / verification APIs.
- `404`: wrong index document key or file not uploaded.
- DNS mismatch: custom domain CNAME does not point to OBS website endpoint.
- Custom domain not reachable: `setBucketCustomDomain` not called on the bucket (DNS alone is insufficient).
- HTTPS certificate verification failure: the custom domain has no bound valid certificate (bind a certificate via `setBucketCustomDomain(certificateInfo=...)`, use a CCM certificate, or front OBS with CDN and terminate TLS there).
