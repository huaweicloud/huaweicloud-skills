#!/usr/bin/env python3
"""Huawei Cloud CCE read-only query entry.

Usage: .venv/bin/python3 scripts/huawei_cce.py <subcommand> -h
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from _common import run

REGISTRY = {
    'list_clusters': {
        'method': 'list_clusters',
        'req': 'ListClustersRequest',
        'list': True,
        'action': '查询 CCE 集群列表',
        'resp': [],
        'map': {'detail': 'detail', 'status': 'status', 'type': 'type', 'version': 'version'},
        'args': [{'opts': ['--detail'], 'type': 'str', 'help': '是否返回集群详细信息，取值 true 或 false，不传则仅返回基本信息'}, {'opts': ['--status'], 'type': 'str', 'help': '集群状态过滤，例如 Available、Unavailable、ScalingUp、ScalingDown、Creating、Deleting、Error、Freezed'}, {'opts': ['--type'], 'type': 'str', 'help': '集群类型过滤，可选值：VirtualMachine（普通集群，含 CCE Turbo）、ARM64、Autopilot'}, {'opts': ['--version'], 'type': 'str', 'help': '集群版本过滤，例如 v1.28、v1.29'}],
    },
    'list_node_pools': {
        'method': 'list_node_pools',
        'req': 'ListNodePoolsRequest',
        'list': True,
        'action': '查询 CCE 集群节点池列表',
        'resp': [],
        'map': {'cluster_id': 'cluster_id', 'show_default_node_pool': 'show_default_node_pool'},
        'args': [{'opts': ['--cluster_id'], 'type': 'str', 'required': True, 'help': '集群 ID（UUID），可通过 list_clusters.py 获取'}, {'opts': ['--show_default_node_pool'], 'type': 'str', 'choices': ['true', 'false'], 'help': '是否展示默认节点池，true/false，不传则默认不展示'}, {'opts': ['--advance_status'], 'type': 'str', 'choices': ['true', 'false'], 'help': '是否返回节点池的详细状态信息，true/false'}],
    },
    'list_node_pools_by_tag': {
        'method': 'list_node_pools',
        'req': 'ListNodePoolsRequest',
        'list': True,
        'action': '按标签/标签(label)过滤 CCE 节点池（客户端过滤）',
        'resp': [],
        'map': {'cluster_id': 'cluster_id'},
        'args': [{'opts': ['--cluster_id'], 'type': 'str', 'required': True, 'help': '集群 ID（UUID），可通过 list_clusters.py 获取'}, {'opts': ['--tag'], 'type': 'str', 'action': 'append', 'metavar': 'key=value', 'help': '按节点池 userTags 过滤，可重复指定，多个标签之间为 AND 关系，例如 --tag env=prod'}, {'opts': ['--label'], 'type': 'str', 'action': 'append', 'metavar': 'key=value', 'help': '按节点池 k8s tags（Kubernetes label）过滤，可重复指定，多个之间为 AND 关系，例如 --label zone=a'}, {'opts': ['--include_default'], 'action': 'store_true', 'help': '一并查询默认节点池（show_default_node_pool=true）'}, {'opts': ['--advance_status'], 'type': 'str', 'choices': ['true', 'false'], 'help': '是否返回节点池详细状态，true/false'}],
    },
    'list_nodes': {
        'method': 'list_node_pools',
        'req': 'ListNodePoolsRequest',
        'list': True,
        'action': '查询 CCE 集群节点列表（支持全量分页）',
        'resp': [],
        'map': {'cluster_id': 'cluster_id', 'marker': 'marker'},
        'args': [{'opts': ['--cluster_id'], 'type': 'str', 'required': True, 'help': '集群 ID（UUID），可通过 list_clusters.py 获取'}, {'opts': ['--verify'], 'action': 'store_true', 'help': '与节点池 current_node 汇总数交叉校验节点总数（额外调用 ListNodePools）'}],
    },
    'show_cluster': {
        'method': 'show_cluster',
        'req': 'ShowClusterRequest',
        'list': False,
        'action': '查询 CCE 集群详情',
        'resp': [],
        'map': {'cluster_id': 'cluster_id', 'detail': 'detail'},
        'args': [{'opts': ['--cluster_id'], 'type': 'str', 'required': True, 'help': '集群 ID（UUID），可通过 list_clusters.py 获取'}, {'opts': ['--detail'], 'type': 'str', 'help': '是否返回集群详细信息，取值 true 或 false，不传则仅返回基本信息'}],
    },
    'show_cluster_tags': {
        'method': 'get_resource_tags',
        'req': 'GetResourceTagsRequest',
        'list': False,
        'action': '查询 CCE 集群的标签（只读）',
        'resp': [],
        'map': {'resource_id': 'cluster_id'},
        'args': [{'opts': ['--cluster_id'], 'type': 'str', 'required': True, 'help': '集群 ID（UUID），可通过 list_clusters.py 获取'}],
    },
    'show_node': {
        'method': 'show_node',
        'req': 'ShowNodeRequest',
        'list': False,
        'action': '查询 CCE 节点详情',
        'resp': [],
        'map': {'cluster_id': 'cluster_id', 'node_id': 'node_id'},
        'args': [{'opts': ['--cluster_id'], 'type': 'str', 'required': True, 'help': '集群 ID（UUID），可通过 list_clusters.py 获取'}, {'opts': ['--node_id'], 'type': 'str', 'required': True, 'help': '节点 ID（UUID），可通过 list_nodes.py 获取'}],
    },
    'show_node_pool': {
        'method': 'show_node_pool',
        'req': 'ShowNodePoolRequest',
        'list': False,
        'action': '查询 CCE 节点池详情',
        'resp': [],
        'map': {'cluster_id': 'cluster_id', 'nodepool_id': 'nodepool_id'},
        'args': [{'opts': ['--cluster_id'], 'type': 'str', 'required': True, 'help': '集群 ID（UUID），可通过 list_clusters.py 获取'}, {'opts': ['--nodepool_id'], 'type': 'str', 'required': True, 'help': '节点池 ID（UUID），可通过 list_node_pools.py 获取'}, {'opts': ['--advance_status'], 'type': 'str', 'choices': ['true', 'false'], 'help': '是否返回节点池详细状态，true/false'}],
    },
    'show_quota': {
        'method': 'show_quotas',
        'req': 'ShowQuotasRequest',
        'list': False,
        'action': '查询 CCE 资源配额',
        'resp': [],
        'map': {},
        'args': [],
    },
}


if __name__ == "__main__":
    sys.exit(run("cce", REGISTRY))
