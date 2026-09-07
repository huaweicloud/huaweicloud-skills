#!/usr/bin/env python3
"""Resolve portable Huawei Cloud credential environment aliases safely."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass


@dataclass(frozen=True)
class CredentialAliasFamily:
    """Describe one access-key and secret-key environment variable pair."""

    name: str
    access_key: str
    secret_key: str


CLOUD_CREDENTIAL_FAMILIES = (
    CredentialAliasFamily("cloud_sdk", "CLOUD_SDK_AK", "CLOUD_SDK_SK"),
    CredentialAliasFamily(
        "cloud_sdk_named",
        "CLOUD_SDK_ACCESS_KEY",
        "CLOUD_SDK_SECRET_KEY",
    ),
    CredentialAliasFamily("hw", "HW_ACCESS_KEY", "HW_SECRET_KEY"),
    CredentialAliasFamily(
        "huaweicloud_id",
        "HUAWEICLOUD_ACCESS_KEY_ID",
        "HUAWEICLOUD_SECRET_ACCESS_KEY",
    ),
    CredentialAliasFamily(
        "huaweicloud_sdk",
        "HUAWEICLOUD_SDK_AK",
        "HUAWEICLOUD_SDK_SK",
    ),
    CredentialAliasFamily(
        "huaweicloud",
        "HUAWEICLOUD_ACCESS_KEY",
        "HUAWEICLOUD_SECRET_KEY",
    ),
    CredentialAliasFamily("huawei", "HUAWEI_ACCESS_KEY", "HUAWEI_SECRET_KEY"),
    CredentialAliasFamily("os", "OS_ACCESS_KEY", "OS_SECRET_KEY"),
)
REGION_ENV_NAMES = (
    "CLOUD_SDK_REGION",
    "HW_REGION_NAME",
    "HW_REGION",
    "HUAWEICLOUD_REGION",
    "HUAWEI_REGION",
    "OS_REGION_NAME",
)
PROJECT_ID_ENV_NAMES = (
    "CLOUD_SDK_PROJECT_ID",
    "HW_PROJECT_ID",
    "HUAWEICLOUD_SDK_PROJECT_ID",
    "HUAWEICLOUD_PROJECT_ID",
    "HUAWEI_PROJECT_ID",
    "OS_PROJECT_ID",
)
DOMAIN_ID_ENV_NAMES = (
    "CLOUD_SDK_DOMAIN_ID",
    "HW_DOMAIN_ID",
    "HUAWEICLOUD_SDK_DOMAIN_ID",
    "HUAWEICLOUD_DOMAIN_ID",
    "HUAWEI_DOMAIN_ID",
    "OS_DOMAIN_ID",
)
SECURITY_TOKEN_ENV_NAMES = (
    "CLOUD_SDK_SECURITY_TOKEN",
    "HW_SECURITY_TOKEN",
    "HUAWEICLOUD_SDK_SECURITY_TOKEN",
    "HUAWEICLOUD_SECURITY_TOKEN",
    "HUAWEI_SECURITY_TOKEN",
    "OS_SECURITY_TOKEN",
)
MAAS_API_KEY_ENV_NAMES = ("MAAS_API_KEY", "MODELARTS_MAAS_API_KEY")
CLOUD_ACCESS_KEY_ENV_NAMES = tuple(family.access_key for family in CLOUD_CREDENTIAL_FAMILIES)
CLOUD_SECRET_KEY_ENV_NAMES = tuple(family.secret_key for family in CLOUD_CREDENTIAL_FAMILIES)
ALL_CREDENTIAL_ENV_NAMES = tuple(
    dict.fromkeys(
        (
            *CLOUD_ACCESS_KEY_ENV_NAMES,
            *CLOUD_SECRET_KEY_ENV_NAMES,
            *REGION_ENV_NAMES,
            *PROJECT_ID_ENV_NAMES,
            *DOMAIN_ID_ENV_NAMES,
            *SECURITY_TOKEN_ENV_NAMES,
            *MAAS_API_KEY_ENV_NAMES,
        )
    )
)


def _environment(environ: Mapping[str, str] | None) -> Mapping[str, str]:
    """Return the supplied environment mapping or the current process environment."""
    return os.environ if environ is None else environ


def resolve_first_value(
    keys: tuple[str, ...] | list[str],
    environ: Mapping[str, str] | None = None,
) -> tuple[str | None, str | None]:
    """Return the first non-empty value and its environment variable name."""
    source = _environment(environ)
    for key in keys:
        value = source.get(key)
        if value is not None and value.strip():
            return value.strip(), key
    return None, None


def credential_environment_presence(
    keys: tuple[str, ...] | list[str] | None = None,
    environ: Mapping[str, str] | None = None,
) -> dict[str, dict[str, bool]]:
    """Return presence-only environment data without exposing any values."""
    source = _environment(environ)
    selected = tuple(keys) if keys is not None else ALL_CREDENTIAL_ENV_NAMES
    return {
        key: {
            "set": bool(source.get(key)),
            "empty": key in source and source.get(key) == "",
        }
        for key in selected
    }


def resolve_cloud_credentials(
    environ: Mapping[str, str] | None = None,
) -> dict[str, object]:
    """Resolve one coherent AK/SK family plus portable region and context aliases.

    A complete credential pair always wins over a partial earlier family. If no
    complete pair exists, the first partial family is returned for diagnostics.
    Values from different AK/SK naming families are never combined.
    """
    source = _environment(environ)
    selected: CredentialAliasFamily | None = None
    first_partial: CredentialAliasFamily | None = None

    for family in CLOUD_CREDENTIAL_FAMILIES:
        access_key = source.get(family.access_key)
        secret_key = source.get(family.secret_key)
        if access_key and secret_key:
            selected = family
            break
        if first_partial is None and (access_key or secret_key):
            first_partial = family

    selected = selected or first_partial
    access_key = source.get(selected.access_key) if selected else None
    secret_key = source.get(selected.secret_key) if selected else None
    region, region_source = resolve_first_value(REGION_ENV_NAMES, source)
    project_id, project_source = resolve_first_value(PROJECT_ID_ENV_NAMES, source)
    domain_id, domain_source = resolve_first_value(DOMAIN_ID_ENV_NAMES, source)
    security_token, token_source = resolve_first_value(
        SECURITY_TOKEN_ENV_NAMES,
        source,
    )
    pair_complete = bool(access_key and secret_key)

    return {
        "family": selected.name if selected else None,
        "access_key": access_key,
        "secret_key": secret_key,
        "security_token": security_token,
        "region": region,
        "project_id": project_id,
        "domain_id": domain_id,
        "pair_complete": pair_complete,
        "complete": bool(pair_complete and region),
        "sources": {
            "access_key": selected.access_key if selected and access_key else None,
            "secret_key": selected.secret_key if selected and secret_key else None,
            "security_token": token_source,
            "region": region_source,
            "project_id": project_source,
            "domain_id": domain_source,
        },
    }


def redact_credential_resolution(
    resolved: Mapping[str, object],
) -> dict[str, object]:
    """Return credential resolution metadata with secret values removed."""
    return {
        "family": resolved.get("family"),
        "access_key_set": bool(resolved.get("access_key")),
        "secret_key_set": bool(resolved.get("secret_key")),
        "security_token_set": bool(resolved.get("security_token")),
        "region_set": bool(resolved.get("region")),
        "project_id_set": bool(resolved.get("project_id")),
        "domain_id_set": bool(resolved.get("domain_id")),
        "pair_complete": bool(resolved.get("pair_complete")),
        "complete": bool(resolved.get("complete")),
        "sources": dict(resolved.get("sources") or {}),
        "visibility": "current_process_only",
        "configuration_status": ("observed_in_current_process" if resolved.get("pair_complete") else "unknown"),
    }


def resolve_maas_api_key(
    environ: Mapping[str, str] | None = None,
) -> tuple[str | None, str | None]:
    """Return the first supported MaaS API key value and its variable name."""
    return resolve_first_value(MAAS_API_KEY_ENV_NAMES, environ)
