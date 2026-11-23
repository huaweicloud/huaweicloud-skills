#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OBS Signed URL Generator
Generates OBS signed temporary download URLs with optional image processing.

Usage:
    python3 generate_signed_url.py --bucket-name BUCKET --object-key KEY \
        --server ENDPOINT [--method GET] [--expires 3600] \
        [--image-process "image/resize,w_100,h_200"] \
        [--security-token TOKEN] [--headers '{}'] [--query-params '{}']
"""

import argparse
import json
import os
import sys


def get_credentials(security_token=None):
    """Read AK/SK from environment variables. Never hardcode credentials."""
    ak = (
        os.getenv("ACCESS_KEY_ID")
        or os.getenv("OBS_ACCESS_KEY_ID")
        or os.getenv("HUAWEICLOUD_SDK_AK")
        or os.getenv("HW_ACCESS_KEY")
        or ""
    )
    sk = (
        os.getenv("SECRET_ACCESS_KEY")
        or os.getenv("OBS_SECRET_ACCESS_KEY")
        or os.getenv("HUAWEICLOUD_SDK_SK")
        or os.getenv("HW_SECRET_KEY")
        or ""
    )
    if not security_token:
        security_token = (
            os.getenv("SECURITY_TOKEN")
            or os.getenv("HUAWEICLOUD_SDK_SECURITY_TOKEN")
            or os.getenv("HW_SECURITY_TOKEN")
            or None
        )
    if not ak or not sk:
        print(
            "ERROR: AK/SK not found in environment variables. "
            "Set ACCESS_KEY_ID and SECRET_ACCESS_KEY (or OBS_ACCESS_KEY_ID/OBS_SECRET_ACCESS_KEY, "
            "HUAWEICLOUD_SDK_AK/HUAWEICLOUD_SDK_SK).",
            file=sys.stderr,
        )
        sys.exit(1)
    return ak, sk, security_token


def create_obs_client(ak, sk, server, security_token=None):
    """Create an ObsClient instance."""
    from obs import ObsClient

    kwargs = {
        "access_key_id": ak,
        "secret_access_key": sk,
        "server": server,
    }
    if security_token:
        kwargs["security_token"] = security_token

    return ObsClient(**kwargs)


def generate_signed_url(
    obs_client,
    method,
    bucket_name,
    object_key,
    expires=3600,
    headers=None,
    query_params=None,
    special_param=None,
):
    """Generate a signed URL using ObsClient.createSignedUrl."""
    resp = obs_client.createSignedUrl(
        method=method,
        bucketName=bucket_name,
        objectKey=object_key,
        specialParam=special_param,
        expires=expires,
        headers=headers,
        queryParams=query_params,
    )
    return resp


def main():
    parser = argparse.ArgumentParser(
        description="Generate OBS signed temporary download URL"
    )
    parser.add_argument(
        "--bucket-name", required=True, help="OBS bucket name"
    )
    parser.add_argument(
        "--object-key", required=True, help="Object key (path in bucket)"
    )
    parser.add_argument(
        "--method",
        default="GET",
        choices=["GET", "HEAD", "POST", "PUT", "DELETE"],
        help="HTTP method (default: GET)",
    )
    parser.add_argument(
        "--expires",
        type=int,
        default=3600,
        help="URL expiration in seconds (default: 3600)",
    )
    parser.add_argument(
        "--server",
        required=True,
        help="OBS endpoint (e.g., obs.cn-north-4.myhuaweicloud.com)",
    )
    parser.add_argument(
        "--security-token",
        default=None,
        help="Temporary security token (for temp AK/SK)",
    )
    parser.add_argument(
        "--image-process",
        default=None,
        help="Image processing command (e.g., image/resize,w_100,h_200)",
    )
    parser.add_argument(
        "--headers",
        default=None,
        help="Custom headers as JSON string",
    )
    parser.add_argument(
        "--query-params",
        default=None,
        help="Custom query params as JSON string",
    )
    parser.add_argument(
        "--special-param",
        default=None,
        help="Special parameter (e.g., acl, versionId)",
    )

    args = parser.parse_args()

    # Parse optional JSON parameters
    headers = json.loads(args.headers) if args.headers else None
    query_params = json.loads(args.query_params) if args.query_params else {}

    # Add image processing to query params if specified
    if args.image_process:
        query_params["x-image-process"] = args.image_process

    # Get credentials
    ak, sk, security_token = get_credentials(args.security_token)

    # Create OBS client
    obs_client = create_obs_client(ak, sk, args.server, security_token)

    # Generate signed URL
    resp = generate_signed_url(
        obs_client,
        method=args.method,
        bucket_name=args.bucket_name,
        object_key=args.object_key,
        expires=args.expires,
        headers=headers,
        query_params=query_params if query_params else None,
        special_param=args.special_param,
    )

    # Output result
    result = {
        "signedUrl": resp["signedUrl"],
        "actualSignedRequestHeaders": resp["actualSignedRequestHeaders"],
        "method": args.method,
        "bucketName": args.bucket_name,
        "objectKey": args.object_key,
        "expires": args.expires,
    }
    if args.image_process:
        result["imageProcess"] = args.image_process

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
