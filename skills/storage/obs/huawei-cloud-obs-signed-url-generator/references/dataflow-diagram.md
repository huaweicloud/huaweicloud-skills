# Data Flow Diagram

## OBS Signed URL Generation Flow

```mermaid
flowchart TD
    A[User/Agent] -->|1. Provide bucket, object, method, expires| B[generate_signed_url.py]
    B -->|2. Read AK/SK from env vars| C[Environment Variables]
    B -->|3. Read SecurityToken from env vars| D[Optional: Temp Credentials]
    B -->|4. Create ObsClient| E[OBS Python SDK]
    E -->|5. createSignedUrl method| F[Local Signature Calculation]
    F -->|6. Generate signed URL with query params| G[Signed URL Output]
    G -->|7. Optional: x-image-process param| H[Image Processing URL]
    G -->|8. Return to user| I[Third-Party Access]
    I -->|9. HTTP GET with signed URL| J[OBS Server]
    J -->|10. Verify signature & expiration| K{Valid?}
    K -->|Yes| L[Return Object/Processed Image]
    K -->|No| M[403 Forbidden]
```

## Authentication Flow

```mermaid
flowchart LR
    A[Permanent AK/SK] --> C[ObsClient]
    B[Temp AK/SK + SecurityToken] --> C
    C --> D[createSignedUrl]
    D --> E[Local V4/V2 Signature]
    E --> F[Signed URL with Auth Params]
```

## Image Processing Flow

```mermaid
flowchart TD
    A[Image Processing Request] --> B{Processing Type}
    B -->|Resize| C[image/resize,w_X,h_Y]
    B -->|Crop| D[image/crop,w_X,h_Y,g_pos]
    B -->|Rotate| E[image/rotate,angle]
    B -->|Compress| F[image/quality,q_X]
    B -->|Watermark| G[image/watermark,text_X]
    B -->|Format| H[image/format,fmt]
    B -->|Composite| I[image/resize...|image/quality...]
    C --> J[x-image-process query param]
    D --> J
    E --> J
    F --> J
    G --> J
    H --> J
    I --> J
    J --> K[createSignedUrl with queryParams]
    K --> L[Signed Image Processing URL]
```
