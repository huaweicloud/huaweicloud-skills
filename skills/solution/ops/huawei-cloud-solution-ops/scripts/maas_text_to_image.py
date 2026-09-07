#!/usr/bin/env python3
"""Generate local site image assets with Huawei Cloud ModelArts MaaS.

This is the MaaS-named entry point. The implementation stays in
`qwen_text_to_image.py` for backward compatibility with existing callers.
"""

from __future__ import annotations

from qwen_text_to_image import main

if __name__ == "__main__":
    raise SystemExit(main())
