"""AOM metric query helpers backed by signed AOM HTTP APIs."""

from __future__ import annotations

from typing import Any, Dict, Optional

from .common import get_credentials_with_region, get_security_token


def get_aom_prom_metrics_http(
    region: str,
    aom_instance_id: str,
    query: str,
    start: Optional[int] = None,
    end: Optional[int] = None,
    step: int = 60,
    hours: int = 1,
    ak: Optional[str] = None,
    sk: Optional[str] = None,
    project_id: Optional[str] = None,
    security_token: Optional[str] = None,
) -> Dict[str, Any]:
    """Get Prometheus range-query metrics from AOM using signed HTTP requests."""
    import hashlib
    import hmac
    import time as time_module
    import urllib.parse
    from urllib.parse import quote, unquote

    import requests

    access_key, secret_key, proj_id = get_credentials_with_region(region, ak, sk, project_id)
    token = get_security_token(security_token)
    if not access_key or not secret_key:
        return {"success": False, "error": "Credentials not provided"}
    if not proj_id:
        return {"success": False, "error": "Project ID not found. Please provide project_id parameter."}

    now = int(time_module.time())
    end_time = end if end else now
    start_time = start if start else (end_time - hours * 3600)

    base_url = f"https://aom.{region}.myhuaweicloud.com"
    query_params = [
        ("end", str(end_time)),
        ("query", query),
        ("start", str(start_time)),
        ("step", str(step)),
    ]

    if aom_instance_id and aom_instance_id not in {"default", "0", "Prometheus_AOM_Default"}:
        resource_path = f"/v1/{proj_id}/{aom_instance_id}/aom/api/v1/query_range"
    else:
        resource_path = f"/v1/{proj_id}/aom/api/v1/query_range"

    def url_encode(value: str) -> str:
        return quote(value, safe="~")

    uri_parts = [url_encode(part) for part in unquote(resource_path).split("/")]
    canonical_uri = "/".join(uri_parts)
    if not canonical_uri.endswith("/"):
        canonical_uri += "/"

    sorted_params = sorted(query_params, key=lambda item: item[0])
    canonical_querystring = "&".join(
        f"{url_encode(key)}={url_encode(str(value))}" for key, value in sorted_params
    )

    timestamp = time_module.strftime("%Y%m%dT%H%M%SZ", time_module.gmtime(now))
    host_header = f"aom.{region}.myhuaweicloud.com"
    canonical_header_items = [
        ("host", host_header),
        ("x-project-id", proj_id),
        ("x-sdk-date", timestamp),
    ]
    if token:
        canonical_header_items.append(("x-security-token", token))
    signed_headers = ";".join(key for key, _ in canonical_header_items)
    canonical_headers = "".join(f"{key}:{value}\n" for key, value in canonical_header_items)
    hashed_body = hashlib.sha256(b"").hexdigest()
    canonical_request = "\n".join([
        "GET",
        canonical_uri,
        canonical_querystring,
        canonical_headers,
        signed_headers,
        hashed_body,
    ])

    algorithm = "SDK-HMAC-SHA256"
    hashed_canonical_request = hashlib.sha256(canonical_request.encode("utf-8")).hexdigest()
    string_to_sign = f"{algorithm}\n{timestamp}\n{hashed_canonical_request}"
    signature = hmac.new(
        secret_key.encode("utf-8"),
        string_to_sign.encode("utf-8"),
        hashlib.sha256,
    ).digest().hex()
    authorization = (
        f"{algorithm} Access={access_key}, SignedHeaders={signed_headers}, Signature={signature}"
    )

    url_query_string = "&".join(
        f"{key}={urllib.parse.quote(str(value))}" for key, value in query_params
    )
    url = f"{base_url}{resource_path}?{url_query_string}"
    headers = {
        "Host": host_header,
        "X-Project-Id": proj_id,
        "X-Sdk-Date": timestamp,
        "Authorization": authorization,
    }
    if token:
        headers["X-Security-Token"] = token

    try:
        response = requests.get(url, headers=headers, verify=True, timeout=30)
        if response.status_code != 200:
            return {
                "success": False,
                "error": f"HTTP {response.status_code}: {response.text[:500]}",
                "url": url,
                "request_headers": {
                    key: value
                    for key, value in headers.items()
                    if key not in {"Authorization", "X-Security-Token"}
                },
                "request_context": {
                    "canonical_uri": canonical_uri,
                    "signed_headers": signed_headers,
                },
            }
        result = response.json()
    except Exception as exc:
        return {"success": False, "error": str(exc), "url": url}

    return {
        "success": True,
        "region": region,
        "aom_instance_id": aom_instance_id,
        "source": "signed_http",
        "query": query,
        "time_range": {"start": start_time, "end": end_time, "step": step},
        "endpoint": f"{base_url}{resource_path}",
        "url": url,
        "result": result,
    }
