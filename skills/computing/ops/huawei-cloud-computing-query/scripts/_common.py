"""Shared command-line layer for the huawei-cloud-computing-query skill.

Every service entry (``scripts/huawei_<service>.py``) is a thin subcommand
dispatcher built on this module.  Design rules:

* ``-h`` / ``--help`` is handled by argparse before any credential or SDK
  check, so help always works on a bare host.
* Missing AK/SK exits with code 2 and a readable hint instead of a traceback.
* Missing SDK, network failures and API errors exit with code 3.
* List subcommands print a short summary by default (``--limit``/``--fields``)
  and only walk every page when ``--all`` is given.
* ``project_id`` is resolved once per process and reused.
"""

import argparse
import importlib
import json
import os
import re
import sys


EXIT_OK = 0
EXIT_USAGE = 2
EXIT_RUNTIME = 3

DEFAULT_REGION = "cn-north-4"
DEFAULT_LIMIT = 20
API_LIMIT = 1000

_PROJECT_CACHE = {}
_CREDENTIAL_KEYS = ("HW_ACCESS_KEY", "HW_SECRET_KEY", "HW_SECURITY_TOKEN")

_SERVICE_SPECS = {
    "ecs": {
        "package": "huaweicloudsdkecs.v2",
        "client": "EcsClient",
        "region": "EcsRegion",
        "title": "ECS",
    },
    "bms": {
        "package": "huaweicloudsdkbms.v1",
        "client": "BmsClient",
        "region": "BmsRegion",
        "title": "BMS",
    },
    "ims": {
        "package": "huaweicloudsdkims.v2",
        "client": "ImsClient",
        "region": "ImsRegion",
        "title": "IMS",
    },
    "as": {
        "package": "huaweicloudsdkas.v1",
        "client": "AsClient",
        "region": "AsRegion",
        "title": "AS",
    },
    "cce": {
        "package": "huaweicloudsdkcce.v3",
        "client": "CceClient",
        "region": "CceRegion",
        "title": "CCE",
    },
}

COMMON_ARGS = {"project_id", "region", "limit", "marker", "all", "fields", "json"}
_CLIENT_ONLY_ARGS = {
    "with_related", "name_contains", "export", "export_path", "sort_by",
    "top", "expect_fields", "only_available", "count", "verify", "label",
    "include_default", "match", "without_any_tag", "tag_any", "not_tag_any",
    "tag_key", "tag_value", "not_tag_key", "not_tag_value", "resource_name",
}


class CredentialError(Exception):
    pass


class RuntimeFailure(Exception):
    pass


def _root_dir():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _arg_dest(spec):
    if spec.get("dest"):
        return spec["dest"]
    options = spec.get("opts") or []
    if not options:
        return ""
    return options[0].lstrip("-").replace("-", "_")


def _add_argument(parser, spec):
    options = spec.get("opts") or []
    if not options:
        return
    kwargs = {}
    if "help" in spec:
        kwargs["help"] = spec["help"]
    if isinstance(spec.get("choices"), (list, tuple)):
        kwargs["choices"] = spec["choices"]
    if "metavar" in spec:
        kwargs["metavar"] = spec["metavar"]
    if "dest" in spec:
        kwargs["dest"] = spec["dest"]
    if spec.get("required"):
        kwargs["required"] = True
    if "default" in spec:
        kwargs["default"] = spec["default"]
    if spec.get("action") == "store_true":
        kwargs["action"] = "store_true"
    elif spec.get("action") == "count":
        kwargs["action"] = "count"
    elif spec.get("action") == "append":
        kwargs["action"] = "append"
    elif spec.get("nargs"):
        kwargs["nargs"] = spec["nargs"]
        if "const" in spec:
            kwargs["const"] = spec["const"]
    elif "type" in spec:
        kwargs["type"] = int if spec["type"] == "int" else str
    parser.add_argument(*options, **kwargs)


def build_parser(service, registry):
    spec = _SERVICE_SPECS[service]
    parser = argparse.ArgumentParser(
        prog=f"huawei_{service}.py",
        description=f"Huawei Cloud {spec['title']} read-only query entry",
    )
    subparsers = parser.add_subparsers(dest="command", metavar="<subcommand>")

    for name in sorted(registry):
        op = registry[name]
        sub = subparsers.add_parser(
            name,
            help=op.get("help") or op.get("action") or name,
            description=op.get("help") or op.get("action") or name,
        )
        sub.add_argument("--region", help=f"region, default ${'HW_REGION_NAME'} or {DEFAULT_REGION}")
        sub.add_argument("--project_id", help="project ID; resolved through IAM when omitted")
        if op.get("list"):
            sub.add_argument("--limit", type=int, default=DEFAULT_LIMIT,
                             help=f"rows to display, default {DEFAULT_LIMIT}")
            sub.add_argument("--all", action="store_true",
                             help="fetch every page and display all rows")
        sub.add_argument("--fields", help="comma-separated display fields")
        sub.add_argument("--json", action="store_true", help="print raw JSON")

        seen = set(COMMON_ARGS)
        for arg_spec in op.get("args", []):
            dest = _arg_dest(arg_spec)
            if not dest or dest in seen:
                continue
            if dest in ("export", "export_path", "top", "expect_fields"):
                continue
            seen.add(dest)
            _add_argument(sub, arg_spec)

    parser.add_argument("-v", "--version", action="version", version=f"huawei_{service}.py")
    return parser


def run(service, registry):
    parser = build_parser(service, registry)
    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return EXIT_OK

    op = registry[args.command]
    try:
        return _execute(service, op, args)
    except CredentialError as exc:
        print(str(exc), file=sys.stderr)
        return EXIT_USAGE
    except RuntimeFailure as exc:
        print(str(exc), file=sys.stderr)
        return EXIT_RUNTIME
    except KeyboardInterrupt:
        print("interrupted", file=sys.stderr)
        return EXIT_RUNTIME


def _load_credentials(service):
    ak = os.getenv("HW_ACCESS_KEY", "")
    sk = os.getenv("HW_SECRET_KEY", "")
    token = os.getenv("HW_SECURITY_TOKEN", "")
    if not ak or not sk:
        raise CredentialError(
            "missing AK/SK: set HW_ACCESS_KEY and HW_SECRET_KEY "
            "(HW_SECURITY_TOKEN is required for temporary credentials)"
        )
    return ak, sk, token


def _region(args):
    return getattr(args, "region", None) or os.getenv("HW_REGION_NAME", DEFAULT_REGION)


def _resolve_project_id(region, explicit=None, ak=None, sk=None, token=None):
    if explicit:
        return explicit
    env_pid = os.getenv("HW_PROJECT_ID", "")
    if env_pid:
        return env_pid
    cache_key = (region, bool(ak))
    if cache_key in _PROJECT_CACHE:
        return _PROJECT_CACHE[cache_key]

    project_file = os.path.join(_root_dir(), ".project_id")
    if os.path.isfile(project_file):
        try:
            with open(project_file, "r", encoding="utf-8") as handle:
                cached = handle.read().strip()
            if cached:
                _PROJECT_CACHE[cache_key] = cached
                return cached
        except OSError:
            pass

    try:
        from config import build_http_config
        from huaweicloudsdkcore.auth.credentials import BasicCredentials
        from huaweicloudsdkiam.v3 import IamClient
        from huaweicloudsdkiam.v3.model import KeystoneListProjectsRequest
        from huaweicloudsdkiam.v3.region.iam_region import IamRegion

        credentials = BasicCredentials(ak, sk)
        if token:
            credentials = credentials.with_security_token(token)
        client = (IamClient.new_builder()
                  .with_http_config(build_http_config())
                  .with_credentials(credentials)
                  .with_region(IamRegion.value_of(region))
                  .build())
        request = KeystoneListProjectsRequest()
        request.name = region
        response = client.keystone_list_projects(request)
        projects = getattr(response, "projects", None) or []
        if not projects:
            raise RuntimeFailure(f"no project found for region {region}; pass --project_id explicitly")
        resolved = None
        for project in projects:
            if getattr(project, "name", "") == region:
                resolved = project.id
                break
        resolved = resolved or projects[0].id
        _PROJECT_CACHE[cache_key] = resolved
        return resolved
    except RuntimeFailure:
        raise
    except ImportError as exc:
        raise RuntimeFailure(f"Huawei Cloud SDK is not installed: {exc}; run scripts/check_env.sh first")
    except Exception as exc:
        raise RuntimeFailure(
            f"failed to resolve project_id for region {region}: {exc}; "
            "pass --project_id or set HW_PROJECT_ID"
        )


def _build_client(service, region, ak, sk, token, project_id):
    spec = _SERVICE_SPECS[service]
    try:
        package = importlib.import_module(spec["package"])
        region_package = importlib.import_module(f"{spec['package']}.region.{service}_region")
        from config import build_http_config
        from huaweicloudsdkcore.auth.credentials import BasicCredentials
    except ImportError as exc:
        raise RuntimeFailure(f"Huawei Cloud SDK is not installed: {exc}; run scripts/check_env.sh first")

    client_cls = getattr(package, spec["client"])
    region_cls = getattr(region_package, spec["region"])
    credentials = BasicCredentials(ak, sk, project_id)
    if token:
        credentials = credentials.with_security_token(token)
    return (client_cls.new_builder()
            .with_http_config(build_http_config())
            .with_credentials(credentials)
            .with_region(region_cls.value_of(region))
            .build())


def _request_class(service, class_name):
    spec = _SERVICE_SPECS[service]
    try:
        module = importlib.import_module(f"{spec['package']}.model")
    except ImportError as exc:
        raise RuntimeFailure(f"Huawei Cloud SDK is not installed: {exc}; run check_env.sh first")
    try:
        return getattr(module, class_name)
    except AttributeError:
        try:
            package = importlib.import_module(spec["package"])
            return getattr(package, class_name)
        except AttributeError:
            raise RuntimeFailure(f"request class {class_name} is not available in the installed SDK")


def _call(service, op, args):
    region = _region(args)
    ak, sk, token = _load_credentials(service)
    project_id = _resolve_project_id(region, getattr(args, "project_id", None), ak, sk, token)
    client = _build_client(service, region, ak, sk, token, project_id)
    request_cls = _request_class(service, op["req"])

    if service == "as" and args.command == "list_resource_instances":
        request = _build_as_resource_instances_request(request_cls, args)
    else:
        request = request_cls()

    for cli_name, request_name in (op.get("map") or {}).items():
        if not hasattr(args, cli_name):
            continue
        value = getattr(args, cli_name)
        if value is not None:
            setattr(request, request_name, value)

    _apply_special_args(service, args, request)

    try:
        request._hcs_command = args.command
    except Exception:
        pass
    method = getattr(client, op["method"])
    if op.get("list") and getattr(args, "all", False) and hasattr(request, "limit"):
        try:
            request.limit = API_LIMIT
        except Exception:
            pass
    response = method(request)
    if op.get("list") and getattr(args, "all", False):
        response = _collect_all_pages(service, method, request, response, op.get("resp"))
    return response, region, project_id


_LIST_META_FIELDS = {
    "api_version", "body", "count", "discriminator", "kind", "limit",
    "marker", "page_info", "raw_content", "request_id", "schema",
    "servers_links", "start_number", "status_code", "total_count",
    "total_number", "x_request_id",
}


def _discover_list_fields(response):
    """Find list-valued attributes on an SDK response (metadata excluded)."""
    fields = []
    for name in dir(type(response)):
        if name.startswith("_") or name in _LIST_META_FIELDS:
            continue
        try:
            value = getattr(response, name)
        except Exception:
            continue
        if isinstance(value, list):
            fields.append(name)
    return fields


def _response_items(response, resp_fields=None):
    """Return ``(items, total, known_shape)`` for a list response.

    ``known_shape`` False means the response carried no recognised list
    field at all, so the caller should treat it as a shape error.  A declared
    field that is empty/None is a legitimate empty result: it is a known
    shape and yields ``([], ..., True)``.
    """
    if isinstance(response, dict):
        for key in ("items", "resources", "servers", "flavors", "events",
                    "tags", "images"):
            value = response.get(key)
            if isinstance(value, list):
                return list(value), response.get("total"), True
        return [], response.get("total"), True

    for attr in list(resp_fields or []):
        value = getattr(response, attr, None)
        if isinstance(value, list):
            return value, None, True
        if isinstance(value, dict):
            return [value], None, True
        if value is None:
            return [], None, True

    for attr in ("items", "resources", "servers", "images", "body"):
        value = getattr(response, attr, None)
        if isinstance(value, list):
            return value, None, True

    for attr in _discover_list_fields(response):
        value = getattr(response, attr, None)
        if isinstance(value, list):
            return value, None, True
        if isinstance(value, dict):
            return [value], None, True

    return None, None, False


def _next_marker(response):
    if isinstance(response, dict):
        return response.get("next_marker")
    page_info = getattr(response, "page_info", None)
    marker = getattr(page_info, "next_marker", None) if page_info else None
    return marker or getattr(response, "next_marker", None)


def _current_command(request):
    return getattr(request, "_hcs_command", "")


def _collect_all_pages(service, method, request, first_response, resp_fields=None):
    items, total, _ = _response_items(first_response, resp_fields)
    items = items or []
    collected = list(items)
    pages = 1
    page_size = API_LIMIT
    if hasattr(request, "limit"):
        try:
            request.limit = page_size
        except Exception:
            pass

    if service == "bms":
        while items and len(items) >= page_size and pages < 100:
            pages += 1
            request.offset = pages
            response = method(request)
            items, _, _ = _response_items(response, resp_fields)
            items = items or []
            collected.extend(items)
    elif service == "as" and "resource_instances" not in _current_command(request):
        start = len(collected)
        while items and len(items) >= page_size and pages < 100:
            pages += 1
            request.start_number = start
            response = method(request)
            items, _, _ = _response_items(response, resp_fields)
            items = items or []
            collected.extend(items)
            start += len(items)
    else:
        marker = _next_marker(first_response)
        while marker and pages < 100:
            pages += 1
            request.marker = marker
            response = method(request)
            items, _, _ = _response_items(response, resp_fields)
            items = items or []
            collected.extend(items)
            marker = _next_marker(response)

    if total is None:
        total = len(collected)
    return {"items": collected, "total": total}


def _apply_special_args(service, args, request):
    tag = getattr(args, "tag", None)
    not_tag = getattr(args, "not_tag", None)
    if tag:
        joined = ",".join(tag) if isinstance(tag, list) else str(tag)
        if hasattr(request, "tags"):
            request.tags = joined
    if not_tag:
        joined = ",".join(not_tag) if isinstance(not_tag, list) else str(not_tag)
        if hasattr(request, "not_tags"):
            request.not_tags = joined

    for name in ("advance_status",):
        value = getattr(args, name, None)
        if value is not None and hasattr(request, name):
            setattr(request, name, value == "true")

    for name in ("detail", "show_default_node_pool", "only_available"):
        value = getattr(args, name, None)
        if value is not None and hasattr(request, name):
            setattr(request, name, value)

    start_number = getattr(args, "start_number", None)
    if start_number is not None and hasattr(request, "start_number"):
        request.start_number = start_number


def _build_as_resource_instances_request(request_cls, args):
    try:
        from huaweicloudsdkas.v1 import QueryTagsOption, TagsMultiValue, Matches
    except ImportError as exc:
        raise RuntimeFailure(f"Huawei Cloud SDK is not installed: {exc}; run check_env.sh first")

    def pairs(values):
        result = []
        for item in values or []:
            if "=" in item:
                key, value = item.split("=", 1)
                result.append(TagsMultiValue(key=key, values=[value]))
        return result

    body = QueryTagsOption(
        tags=pairs(getattr(args, "tag", None)),
        tags_any=pairs(getattr(args, "tag_any", None)),
        not_tags=pairs(getattr(args, "not_tag", None)),
        not_tags_any=pairs(getattr(args, "not_tag_any", None)),
        matches=[Matches(key="resource_name", value=getattr(args, "match", ""))] if getattr(args, "match", None) else None,
        limit=args.limit if getattr(args, "all", False) is False else API_LIMIT,
        offset=0,
    )
    return request_cls(resource_type=args.resource_type, body=body)


def _to_dict(value):
    for method in ("to_dict", "to_str"):
        if hasattr(value, method):
            try:
                result = getattr(value, method)()
                if isinstance(result, str):
                    try:
                        return json.loads(result)
                    except ValueError:
                        return {"value": result}
                return result
            except Exception:
                continue
    if isinstance(value, dict):
        return dict(value)
    if isinstance(value, (list, tuple)):
        return [_to_dict(item) for item in value]
    if hasattr(value, "__dict__"):
        return {k: _to_dict(v) for k, v in vars(value).items() if not k.startswith("_")}
    return value


def _lookup(data, field):
    if field in data:
        return data[field]
    current = data
    for part in field.split("."):
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return None
    return current


def _flatten(data):
    row = dict(data) if isinstance(data, dict) else {"value": data}
    metadata = row.get("metadata")
    if isinstance(metadata, dict):
        if "uid" in metadata:
            row.setdefault("id", metadata.get("uid"))
        if "name" in metadata:
            row.setdefault("name", metadata.get("name"))
        if "creation_timestamp" in metadata:
            row.setdefault("created", metadata.get("creation_timestamp"))
    status = row.get("status")
    if isinstance(status, dict):
        phase = status.get("phase")
        if phase is not None:
            row["status"] = phase
        elif "status" in status:
            row["status"] = status.get("status")
    return row


def _heuristic_fields(row):
    if {"id", "name", "status"} <= set(row):
        return ["id", "name", "status"]
    fields = []
    for key in row:
        if re.search(r"(^id$|_id$)", key) and len(fields) < 1:
            fields.append(key)
    for key in row:
        if re.search(r"(^name$|_name$)", key) and key not in fields and len(fields) < 2:
            fields.append(key)
    for key in row:
        if re.search(r"(^status$|_status$|^phase$)", key) and key not in fields and len(fields) < 3:
            fields.append(key)
    return fields or list(row)[:5]


def _render_value(value):
    if value is None:
        return "-"
    if isinstance(value, (dict, list)):
        text = json.dumps(value, ensure_ascii=False, sort_keys=True)
    else:
        text = str(value)
    if len(text) > 200:
        text = text[:197] + "..."
    return text.replace("\t", " ").replace("\n", " ")


def _render_list(service, op, args, response):
    items, total, known_shape = _response_items(response, op.get("resp"))
    if not known_shape:
        raise RuntimeFailure(f"unexpected response shape for {args.command}: no list field found")
    items = items or []

    if total is None and not isinstance(response, dict):
        for attr in ("count", "total_count", "total_number"):
            value = getattr(response, attr, None)
            if isinstance(value, int):
                total = value
                break

    rows = [_flatten(_to_dict(item)) for item in items]
    fields = args.fields.split(",") if getattr(args, "fields", None) else None
    if not fields:
        fields = _heuristic_fields(rows[0]) if rows else ["id", "name", "status"]
    if not getattr(args, "all", False):
        rows = rows[:max(args.limit, 0)]

    if getattr(args, "json", False):
        print(json.dumps({"total": total if total is not None else len(items), "items": rows},
                         ensure_ascii=False, indent=2))
    else:
        print("\t".join(fields))
        for row in rows:
            print("\t".join(_render_value(_lookup(row, field)) for field in fields))
        total_text = total if total is not None else len(items)
        print(f"\n共 {total_text} 条，当前返回 {len(rows)} 条")
        if not getattr(args, "all", False) and (total is None or total > len(rows)):
            print("使用 --all 拉取全部，或使用过滤参数缩小范围")


def _render_object(service, op, args, response):
    attr = (op.get("resp") or [None])[0]
    value = getattr(response, attr, None) if attr else None
    if value is None:
        for candidate in ("items", "body", "resources"):
            candidate_value = getattr(response, candidate, None)
            if candidate_value is not None:
                value = candidate_value
                break
    if value is None:
        value = response
    data = _flatten(_to_dict(value))
    fields = args.fields.split(",") if getattr(args, "fields", None) else None
    if getattr(args, "json", False):
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return
    if fields:
        for field in fields:
            print(f"{field}: {_render_value(_lookup(data, field))}")
        return
    for key, item in data.items():
        print(f"{key}: {_render_value(item)}")


def _execute(service, op, args):
    try:
        response, region, project_id = _call(service, op, args)
    except CredentialError:
        raise
    except RuntimeFailure:
        raise
    except Exception as exc:
        try:
            from config import format_api_error
            message = format_api_error(exc, op.get("action") or args.command, _region(args))
        except Exception:
            message = f"{args.command} failed: {exc}"
        raise RuntimeFailure(message)

    if op.get("list"):
        _render_list(service, op, args, response)
    else:
        _render_object(service, op, args, response)
    return EXIT_OK