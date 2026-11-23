# Image Processing Guide

## Overview

OBS image processing allows you to process images via URL parameters. The `x-image-process` query parameter carries processing commands that are applied to the image when it is downloaded.

## Command Format

```
image/{operation},{param1}_{value1},{param2}_{value2}
```

Multiple operations are separated by `|`:

```
image/resize,w_100,h_200|image/quality,q_85|image/format,png
```

## Supported Operations

### 1. Image Resize (`image/resize`)

| Parameter | Description | Example |
|-----------|-------------|---------|
| `w` | Width in pixels | `w_100` |
| `h` | Height in pixels | `h_200` |
| `s` | Scale ratio (1-1000) | `s_50` |
| `p` | Percentage scale (1-1000) | `p_50` |

Example: `image/resize,w_100,h_200`

### 2. Image Crop (`image/crop`)

| Parameter | Description | Example |
|-----------|-------------|---------|
| `w` | Crop width | `w_100` |
| `h` | Crop height | `h_100` |
| `g` | Gravity position (se, nw, center, etc.) | `g_se` |
| `r` | Inscribed circle radius | `r_50` |

Example: `image/crop,w_100,h_100,g_se`

### 3. Image Rotate (`image/rotate`)

| Parameter | Description | Example |
|-----------|-------------|---------|
| `{angle}` | Rotate angle (0-360) | `90` |
| `auto` | Auto-rotate by EXIF | `auto` |

Example: `image/rotate,90`

### 4. Image Compress (`image/quality`)

| Parameter | Description | Example |
|-----------|-------------|---------|
| `q` | Relative quality (1-100) | `q_85` |
| `Q` | Absolute quality (1-100) | `Q_85` |

Example: `image/quality,q_85`

### 5. Image Slim (`image/slim`)

No parameters needed. Reduces file size with minimal quality loss.

Example: `image/slim`

### 6. Image Effects (`image/bright`, `image/contrast`, etc.)

| Operation | Parameter | Description | Example |
|-----------|-----------|-------------|---------|
| Brightness | `b` | Brightness value (-100 to 100) | `image/bright,b_50` |
| Contrast | `d` | Contrast value (-100 to 100) | `image/contrast,d_50` |
| Sharpen | `s` | Sharpen value (0-100) | `image/sharpen,s_50` |
| Blur | `r`, `s` | Radius and sigma | `image/blur,r_3,s_2` |

### 7. Image Watermark (`image/watermark`)

| Parameter | Description | Example |
|-----------|-------------|---------|
| `text` | Base64-encoded text | `text_aGVsbG8` |
| `image` | Base64-encoded image URL | `image_aW1hZ2U=` |
| `size` | Font size | `size_50` |
| `color` | Hex color | `color_FF0000` |
| `g` | Gravity position | `g_se` |
| `x`, `y` | Offset | `x_10,y_10` |

Example: `image/watermark,text_aGVsbG8gV29ybGQ,size_50,color_FF0000`

### 8. Format Conversion (`image/format`)

| Format | Description |
|--------|-------------|
| `jpg` | Convert to JPEG |
| `png` | Convert to PNG |
| `webp` | Convert to WebP |
| `bmp` | Convert to BMP |
| `gif` | Convert to GIF |
| `tiff` | Convert to TIFF |

Example: `image/format,png`

### 9. Image Info (`image/info`)

Returns image metadata (format, size, average color).

Example: `image/info`

### 10. Multi-Operation Composite

Use `|` to chain multiple operations. Operations execute left to right.

Example: `image/resize,w_200,h_200|image/quality,q_85|image/format,png`

## Usage with Signed URL

```python
from obs import ObsClient

obs_client = ObsClient(access_key_id=ak, secret_access_key=sk, server=server)

resp = obs_client.createSignedUrl(
    method='GET',
    bucketName='my-bucket',
    objectKey='photo.jpg',
    expires=3600,
    queryParams={'x-image-process': 'image/resize,w_100,h_200'}
)
print(resp['signedUrl'])
```

## References

- [Image Processing Overview](https://support.huaweicloud.com/intl/zh-cn/usermanual-obs/obs_01_0001.html)
- [Download Object with Image Processing](https://support.huaweicloud.com/intl/zh-cn/sdk-python-devg-obs/obs_22_2021.html)
- [Generate Signed URL](https://support.huaweicloud.com/intl/zh-cn/sdk-python-devg-obs/obs_22_1301.html)
