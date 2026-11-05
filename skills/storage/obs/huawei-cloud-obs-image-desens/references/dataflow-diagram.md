# Data Flow Diagram

## Batch desensitization flow (`list` + `process`)

```mermaid
flowchart TD
    A[User: bucket + prefix + rule] --> B[obs_image_desens.py list/process]
    B --> C{obsutil ls obs://bucket/prefix}
    C -->|objects| D[Filter image files jpg/png/bmp/webp/gif]
    D --> E{target == source?}
    E -->|yes| F[download each image via hcloud obs cp]
    E -->|no| F
    F --> G[Pillow desensitization]
    G -->|whole| G1[pixelate whole image]
    G -->|blur| G2[Gaussian blur]
    G -->|region| G3[mosaic region x0,y0,x1,y1]
    G -->|region-blur| G4[blur region]
    G -->|region-block| G5[solid-color occlude region]
    G1 & G2 & G3 & G4 & G5 --> H[upload desensitized/key via hcloud obs cp]
    H --> I[per-file JSON report to user]
```

## Automatic on-upload flow (`setup-trigger`)

```mermaid
flowchart LR
    A[User uploads image to OBS bucket] -->|ObjectCreated event| B[FunctionGraph function]
    B --> C[download object via OBS endpoint]
    C --> D[Pillow desensitization rules]
    D --> E[upload desensitized image back to bucket/prefix]
    E --> F[result logged]
```

## Component mapping

| Step | Tool | Notes |
| ------ | ------ | ------- |
| List objects | obsutil via `hcloud obs ls` | filter by prefix + image extensions |
| Download | obsutil via `hcloud obs cp` | temp dir per run |
| Desensitize | Pillow (PIL) | mosaic / Gaussian blur / region occlude |
| Upload | obsutil via `hcloud obs cp` | target bucket/prefix, default `desensitized/` |
| Automation | huaweicloudsdkfunctiongraph | CreateFunction + CreateFunctionTrigger (OBS) |
