#!/usr/bin/env python3
"""Huawei Cloud BMS read-only query entry.

Usage: .venv/bin/python3 scripts/huawei_bms.py <subcommand> -h
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from _common import run

REGISTRY = {
    'list_bare_metal_server_details': {
        'method': 'list_bare_metal_server_details',
        'req': 'ListBareMetalServerDetailsRequest',
        'list': True,
        'action': '查询裸金属服务器详情（按ID查询单个服务器详情）',
        'resp': [],
        'map': {'server_id': 'server_id'},
        'args': [{'opts': ['--server_id'], 'type': 'str', 'required': True, 'help': '裸金属服务器ID，可通过 list_bare_metal_servers.py 获取'}],
    },
    'list_bare_metal_servers': {
        'method': 'list_bare_metal_servers',
        'req': 'ListBareMetalServersRequest',
        'list': True,
        'action': '查询裸金属服务器列表（OpenStack原生，含总数）',
        'resp': [],
        'map': {'flavor': 'flavor', 'name': 'name', 'status': 'status', 'tags': 'tags', 'reservation_id': 'reservation_id', 'detail': 'detail', 'enterprise_project_id': 'enterprise_project_id'},
        'args': [{'opts': ['--flavor'], 'type': 'str', 'help': '裸金属服务器规格ID'}, {'opts': ['--name'], 'type': 'str', 'help': '裸金属服务器名称'}, {'opts': ['--status'], 'type': 'str', 'choices': ['ACTIVE', 'BUILD', 'ERROR', 'HARD_REBOOT', 'REBOOT', 'REBUILD', 'SHUTOFF'], 'help': '裸金属服务器状态，只有管理员可以使用DELETED状态过滤查询已经删除的裸金属服务器'}, {'opts': ['--tags'], 'type': 'str', 'help': '裸金属服务器标签：__type_baremetal'}, {'opts': ['--reservation_id'], 'type': 'str', 'help': '批量创建裸金属服务器时，指定返回的ID，用于查询本次批量创建的裸金属服务器'}, {'opts': ['--detail'], 'type': 'str', 'choices': ['1', '2', '3', '4'], 'help': '查询裸金属服务器结果的详细级别，级别越高，查询到的裸金属服务器信息越多，默认为4'}, {'opts': ['--enterprise_project_id'], 'type': 'str', 'help': '查询绑定某个企业项目的裸金属服务器，查询所有可传 all_granted_eps，可通过 ../eps/list_enterprise_projects.py 获取'}],
    },
    'list_bare_metal_servers_detail': {
        'method': 'list_bare_metal_servers_detail',
        'req': 'ListBareMetalServersDetailRequest',
        'list': True,
        'action': '查询裸金属服务器详情列表（OpenStack原生，无总数）',
        'resp': [],
        'map': {'flavor': 'flavor', 'name': 'name', 'status': 'status', 'detail': 'detail'},
        'args': [{'opts': ['--flavor'], 'type': 'str', 'help': '裸金属服务器规格ID'}, {'opts': ['--name'], 'type': 'str', 'help': '裸金属服务器名称'}, {'opts': ['--status'], 'type': 'str', 'choices': ['ACTIVE', 'BUILD', 'ERROR', 'HARD_REBOOT', 'REBOOT', 'REBUILD', 'SHUTOFF'], 'help': '裸金属服务器状态'}, {'opts': ['--detail'], 'type': 'str', 'choices': ['1', '2', '3', '4'], 'help': '查询裸金属服务器结果的详细级别，级别越高，查询到的裸金属服务器信息越多，默认为4'}],
    },
    'list_baremetal_flavor_detail_extends': {
        'method': 'list_baremetal_flavor_detail_extends',
        'req': 'ListBaremetalFlavorDetailExtendsRequest',
        'list': True,
        'action': '查询裸金属服务器规格详情列表',
        'resp': [],
        'map': {'availability_zone': 'availability_zone'},
        'args': [{'opts': ['--availability_zone'], 'type': 'str', 'help': '可用区名称，可通过 show_available_resource.py 获取'}],
    },
    'show_available_resource': {
        'method': 'show_available_resource',
        'req': 'ShowAvailableResourceRequest',
        'list': False,
        'action': '查询可用区资源信息',
        'resp': [],
        'map': {'availability_zone': 'availability_zone', 'flavor_id': 'flavor_id', 'dec_project_id': 'dec_project_id', 'check_limit': 'check_limit', 'expectation': 'expectation', 'resource_type': 'resource_type'},
        'args': [{'opts': ['--availability_zone'], 'type': 'str', 'nargs': '+', 'required': True, 'help': '可用区列表，可指定多个，如 cn-north-4a'}, {'opts': ['--flavor_id'], 'type': 'str', 'nargs': '+', 'help': '规格ID列表，可指定多个，可通过 list_baremetal_flavor_detail_extends.py 获取'}, {'opts': ['--dec_project_id'], 'type': 'str', 'nargs': '+', 'help': '专属分布式存储池ID列表，可指定多个'}, {'opts': ['--check_limit'], 'type': 'str', 'nargs': '+', 'help': '检查配额限制，可指定多个'}, {'opts': ['--expectation'], 'type': 'str', 'nargs': '+', 'help': '期望值，可指定多个'}, {'opts': ['--resource_type'], 'type': 'str', 'nargs': '+', 'help': '资源类型，可指定多个'}],
    },
    'show_baremetal_server_interface_attachments': {
        'method': 'show_baremetal_server_interface_attachments',
        'req': 'ShowBaremetalServerInterfaceAttachmentsRequest',
        'list': False,
        'action': '查询裸金属服务器网卡信息',
        'resp': [],
        'map': {'server_id': 'server_id'},
        'args': [{'opts': ['--server_id'], 'type': 'str', 'required': True, 'help': '裸金属服务器ID，可通过 list_bare_metal_servers.py 获取'}],
    },
    'show_baremetal_server_tags': {
        'method': 'show_baremetal_server_tags',
        'req': 'ShowBaremetalServerTagsRequest',
        'list': False,
        'action': '查询裸金属服务器标签',
        'resp': [],
        'map': {'server_id': 'server_id'},
        'args': [{'opts': ['--server_id'], 'type': 'str', 'required': True, 'help': '裸金属服务器ID，可通过 list_bare_metal_servers.py 获取'}],
    },
    'show_baremetal_server_volume_info': {
        'method': 'show_baremetal_server_volume_info',
        'req': 'ShowBaremetalServerVolumeInfoRequest',
        'list': False,
        'action': '查询裸金属服务器挂载的磁盘信息',
        'resp': [],
        'map': {'server_id': 'server_id'},
        'args': [{'opts': ['--server_id'], 'type': 'str', 'required': True, 'help': '裸金属服务器ID，可通过 list_bare_metal_servers.py 获取'}],
    },
    'show_job_infos': {
        'method': 'show_job_infos',
        'req': 'ShowJobInfosRequest',
        'list': False,
        'action': '查询异步任务状态',
        'resp': [],
        'map': {'job_id': 'job_id'},
        'args': [{'opts': ['--job_id'], 'type': 'str', 'required': True, 'help': '异步任务ID'}],
    },
    'show_metadata_options': {
        'method': 'show_metadata_options',
        'req': 'ShowMetadataOptionsRequest',
        'list': False,
        'action': '查询裸金属服务器元数据配置',
        'resp': [],
        'map': {'server_id': 'server_id'},
        'args': [{'opts': ['--server_id'], 'type': 'str', 'required': True, 'help': '裸金属服务器ID，可通过 list_bare_metal_servers.py 获取'}],
    },
    'show_reset_pwd': {
        'method': 'show_reset_pwd',
        'req': 'ShowResetPwdRequest',
        'list': False,
        'action': '查询裸金属服务器是否支持重置密码',
        'resp': [],
        'map': {'server_id': 'server_id'},
        'args': [{'opts': ['--server_id'], 'type': 'str', 'required': True, 'help': '裸金属服务器ID，可通过 list_bare_metal_servers.py 获取'}],
    },
    'show_server_remote_console': {
        'method': 'show_server_remote_console',
        'req': 'ShowServerRemoteConsoleRequest',
        'list': False,
        'action': '获取裸金属服务器VNC远程登录地址',
        'resp': [],
        'map': {'server_id': 'server_id'},
        'args': [{'opts': ['--server_id'], 'type': 'str', 'required': True, 'help': '裸金属服务器ID，可通过 list_bare_metal_servers.py 获取'}, {'opts': ['--protocol'], 'type': 'str', 'default': 'vnc', 'help': '远程登录协议，默认 vnc'}, {'opts': ['--type'], 'type': 'str', 'default': 'novnc', 'help': '远程登录类型，默认 novnc'}],
    },
    'show_specified_version': {
        'method': 'show_specified_version',
        'req': 'ShowSpecifiedVersionRequest',
        'list': False,
        'action': '查询BMS API指定版本信息',
        'resp': [],
        'map': {'api_version': 'api_version'},
        'args': [{'opts': ['--api_version'], 'type': 'str', 'required': True, 'help': 'API版本号，如 v1'}],
    },
    'show_tenant_quota': {
        'method': 'show_tenant_quota',
        'req': 'ShowTenantQuotaRequest',
        'list': False,
        'action': '查询裸金属服务器租户配额',
        'resp': [],
        'map': {},
        'args': [],
    },
    'show_windows_baremetal_server_pwd': {
        'method': 'show_windows_baremetal_server_pwd',
        'req': 'ShowWindowsBaremetalServerPwdRequest',
        'list': False,
        'action': '查询Windows裸金属服务器初始密码',
        'resp': [],
        'map': {'server_id': 'server_id'},
        'args': [{'opts': ['--server_id'], 'type': 'str', 'required': True, 'help': '裸金属服务器ID，可通过 list_bare_metal_servers.py 获取'}],
    },
}


if __name__ == "__main__":
    sys.exit(run("bms", REGISTRY))
