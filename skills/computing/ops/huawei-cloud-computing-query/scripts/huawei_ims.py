#!/usr/bin/env python3
"""Huawei Cloud IMS read-only query entry.

Usage: .venv/bin/python3 scripts/huawei_ims.py <subcommand> -h
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from _common import run

REGISTRY = {
    'list_image_by_tags': {
        'method': 'list_image_by_tags',
        'req': 'ListImageByTagsRequest',
        'list': True,
        'action': '按标签查询 IMS 镜像，支持通过标签键值对和资源属性进行过滤',
        'resp': [],
        'map': {},
        'args': [{'opts': ['--action'], 'type': 'str', 'choices': ['filter', 'count'], 'default': 'filter', 'help': '操作类型: filter(分页查询)/count(仅返回总数)，默认 filter'}, {'opts': ['--tag'], 'type': 'str', 'action': 'append', 'help': '包含标签(与关系)，格式: key=value，可多次指定，最多10个key，每个key最多10个values'}, {'opts': ['--tag_any'], 'type': 'str', 'action': 'append', 'help': '包含任意标签(或关系)，格式: key=value，可多次指定，最多10个key，每个key最多10个values'}, {'opts': ['--not_tag'], 'type': 'str', 'action': 'append', 'help': '不包含标签，格式: key=value，可多次指定，最多10个key，每个key最多10个values'}, {'opts': ['--not_tag_any'], 'type': 'str', 'action': 'append', 'help': '不包含任意标签，格式: key=value，可多次指定，最多10个key，每个key最多10个values'}, {'opts': ['--match'], 'type': 'str', 'action': 'append', 'help': '搜索字段，格式: key=value，可多次指定，key为resource_name/resource_id，多个key不允许重复'}, {'opts': ['--without_any_tag'], 'action': 'store_true', 'help': '查询所有不带标签的资源，此时忽略tag/not_tag/tag_any/not_tag_any'}],
    },
    'list_image_members': {
        'method': 'list_image_members',
        'req': 'ListImageMembersRequest',
        'list': True,
        'action': '查询 IMS 镜像成员列表（共享镜像的接受者信息），需要指定镜像 ID',
        'resp': [],
        'map': {'image_id': 'image_id', 'marker': 'marker'},
        'args': [{'opts': ['--image_id'], 'type': 'str', 'required': True, 'help': '镜像 ID，可通过 list_images.py 获取'}],
    },
    'list_image_tags': {
        'method': 'list_image_tags',
        'req': 'ListImageTagsRequest',
        'list': True,
        'action': '查询指定 IMS 镜像的标签列表，需要指定镜像 ID',
        'resp': [],
        'map': {'image_id': 'image_id'},
        'args': [{'opts': ['--image_id'], 'type': 'str', 'required': True, 'help': '镜像 ID，可通过 list_images.py 获取'}],
    },
    'list_images': {
        'method': 'list_images',
        'req': 'ListImagesRequest',
        'list': True,
        'action': '查询 IMS 镜像列表',
        'resp': [],
        'map': {'imagetype': 'imagetype', 'os_type': 'os_type', 'os_bit': 'os_bit', 'architecture': 'architecture', 'status': 'status', 'visibility': 'visibility', 'id': 'id', 'name': 'name', 'disk_format': 'disk_format', 'tag': 'tag', 'enterprise_project_id': 'enterprise_project_id', 'platform': 'platform', 'virtual_env_type': 'virtual_env_type', 'flavor_id': 'flavor_id', 'member_status': 'member_status', 'created_at': 'created_at', 'updated_at': 'updated_at', 'sort_key': 'sort_key', 'sort_dir': 'sort_dir', 'marker': 'marker'},
        'args': [{'opts': ['--imagetype'], 'type': 'str', 'choices': ['gold', 'private', 'shared', 'market'], 'help': '镜像类型: gold(公共镜像), private(私有镜像), shared(共享镜像), market(市场镜像)'}, {'opts': ['--os_type'], 'type': 'str', 'choices': ['Linux', 'Windows', 'Other'], 'help': '操作系统类型: Linux/Windows/Other'}, {'opts': ['--os_bit'], 'type': 'str', 'choices': ['32', '64'], 'help': '操作系统位数: 32 或 64'}, {'opts': ['--architecture'], 'type': 'str', 'choices': ['x86', 'arm'], 'help': '镜像架构类型: x86 或 arm'}, {'opts': ['--status'], 'type': 'str', 'choices': ['queued', 'saving', 'deleted', 'killed', 'active'], 'help': '镜像状态: queued(排队中)/saving(保存中)/deleted(已删除)/killed(错误)/active(可用)'}, {'opts': ['--visibility'], 'type': 'str', 'choices': ['public', 'private', 'shared'], 'help': '镜像可见性: public(公共)/private(私有)/shared(共享)'}, {'opts': ['--id'], 'type': 'str', 'help': '镜像 ID，精确查询指定镜像'}, {'opts': ['--name'], 'type': 'str', 'help': "镜像名称(精确匹配，需输入完整名称，如 'Ubuntu 22.04 server 64bit')"}, {'opts': ['--name_contains'], 'type': 'str', 'help': "镜像名称模糊搜索(客户端过滤，如 'Ubuntu' 可匹配所有名称包含Ubuntu的镜像)"}, {'opts': ['--disk_format'], 'type': 'str', 'choices': ['vhd', 'zvhd', 'raw', 'qcow2', 'zvhd2'], 'help': '镜像格式: vhd/zvhd/raw/qcow2/zvhd2'}, {'opts': ['--tag'], 'type': 'str', 'help': '标签，用户为镜像增加自定义标签后可以通过该参数过滤查询'}, {'opts': ['--enterprise_project_id'], 'type': 'str', 'help': '企业项目ID，0表示default企业项目，UUID表示指定企业项目，all_granted_eps表示所有企业项目，可通过 ../eps/list_enterprise_projects.py 获取'}, {'opts': ['--platform'], 'type': 'str', 'help': '镜像平台分类，如 Ubuntu/CentOS/Windows 等'}, {'opts': ['--virtual_env_type'], 'type': 'str', 'choices': ['FusionCompute', 'Ironic', 'DataImage'], 'help': '使用环境类型: FusionCompute(云服务器)/Ironic(裸金属)/DataImage(数据盘)'}, {'opts': ['--flavor_id'], 'type': 'str', 'help': '云服务器规格ID，用于过滤出可用公共镜像'}, {'opts': ['--member_status'], 'type': 'str', 'choices': ['accepted', 'rejected', 'pending'], 'help': '成员状态，需配合--visibility=shared使用: accepted(已接受)/rejected(已拒绝)/pending(待定)'}, {'opts': ['--created_at'], 'type': 'str', 'help': "镜像创建时间过滤，格式: 操作符:UTC时间，操作符支持gt/gte/lt/lte/eq/neq，如 'gte:2023-01-01T00:00:00Z'"}, {'opts': ['--updated_at'], 'type': 'str', 'help': '镜像修改时间过滤，格式同created_at'}, {'opts': ['--sort_key'], 'type': 'str', 'help': '排序字段，取值为镜像属性name/container_format/disk_format/status/id/size，默认为创建时间'}, {'opts': ['--sort_dir'], 'type': 'str', 'choices': ['asc', 'desc'], 'help': '排序方向: asc(升序)/desc(降序)，默认 desc'}],
    },
    'list_images_tags': {
        'method': 'list_images_tags',
        'req': 'ListImagesTagsRequest',
        'list': True,
        'action': '查询租户所有 IMS 镜像标签（系统标签+用户标签），返回所有标签键及其对应的值列表',
        'resp': [],
        'map': {},
        'args': [],
    },
    'list_os_versions': {
        'method': 'list_os_versions',
        'req': 'ListOsVersionsRequest',
        'list': True,
        'action': '查询 IMS 镜像支持的 OS 版本列表，用于创建镜像或云服务器时选择操作系统',
        'resp': [],
        'map': {'tag': 'tag'},
        'args': [{'opts': ['--tag'], 'type': 'str', 'choices': ['bms', 'uefi', 'arm', 'x86'], 'help': 'OS标签过滤: bms(支持BMS的OS列表)/uefi(支持UEFI启动的OS列表)/arm(ARM架构OS列表)/x86(x86架构OS列表)，不指定则返回所有'}],
    },
    'list_tags': {
        'method': 'list_tags',
        'req': 'ListTagsRequest',
        'list': True,
        'action': '查询租户 IMS 镜像标签列表（仅用户标签），可按镜像属性过滤',
        'resp': [],
        'map': {'imagetype': 'imagetype', 'os_type': 'os_type', 'architecture': 'architecture', 'status': 'status', 'id': 'id', 'name': 'name', 'platform': 'platform', 'virtual_env_type': 'virtual_env_type', 'enterprise_project_id': 'enterprise_project_id', 'min_disk': 'min_disk', 'member_status': 'member_status', 'created_at': 'created_at', 'updated_at': 'updated_at'},
        'args': [{'opts': ['--imagetype'], 'type': 'str', 'choices': ['gold', 'private', 'shared', 'market'], 'help': '镜像类型过滤: gold(公共)/private(私有)/shared(共享)/market(市场)'}, {'opts': ['--os_type'], 'type': 'str', 'choices': ['Linux', 'Windows', 'Other'], 'help': '操作系统类型过滤: Linux/Windows/Other'}, {'opts': ['--architecture'], 'type': 'str', 'choices': ['x86', 'arm'], 'help': '镜像架构过滤: x86/arm'}, {'opts': ['--status'], 'type': 'str', 'choices': ['queued', 'saving', 'deleted', 'killed', 'active'], 'help': '镜像状态过滤: queued/saving/deleted/killed/active'}, {'opts': ['--id'], 'type': 'str', 'help': '镜像 ID 过滤'}, {'opts': ['--name'], 'type': 'str', 'help': '镜像名称过滤'}, {'opts': ['--platform'], 'type': 'str', 'help': '镜像平台分类过滤，如 Ubuntu/CentOS/Windows'}, {'opts': ['--virtual_env_type'], 'type': 'str', 'choices': ['FusionCompute', 'Ironic', 'DataImage'], 'help': '使用环境类型过滤: FusionCompute/Ironic/DataImage'}, {'opts': ['--enterprise_project_id'], 'type': 'str', 'help': '企业项目ID过滤，0表示default企业项目，UUID表示指定企业项目，all_granted_eps表示所有企业项目，可通过 ../eps/list_enterprise_projects.py 获取'}, {'opts': ['--min_disk'], 'type': 'int', 'help': '镜像运行需要的最小磁盘，单位为GB'}, {'opts': ['--member_status'], 'type': 'str', 'choices': ['accepted', 'rejected', 'pending'], 'help': '成员状态: accepted(已接受)/rejected(已拒绝)/pending(待定)'}, {'opts': ['--created_at'], 'type': 'str', 'help': "镜像创建时间过滤，格式: 操作符:UTC时间，操作符支持gt/gte/lt/lte/eq/neq，如 'gte:2023-01-01T00:00:00Z'"}, {'opts': ['--updated_at'], 'type': 'str', 'help': '镜像修改时间过滤，格式同created_at'}],
    },
    'show_image': {
        'method': 'glance_show_image',
        'req': 'GlanceShowImageRequest',
        'list': False,
        'action': '查询 IMS 镜像详情，返回镜像的完整信息（包括元数据、大小、格式、OS信息等）',
        'resp': [],
        'map': {'image_id': 'image_id'},
        'args': [{'opts': ['--image_id'], 'type': 'str', 'required': True, 'help': '镜像 ID，可通过 list_images.py 获取'}],
    },
    'show_image_member': {
        'method': 'show_image_member',
        'req': 'ShowImageMemberRequest',
        'list': False,
        'action': '查询 IMS 镜像成员详情，获取指定共享镜像的某个成员的共享状态信息',
        'resp': [],
        'map': {'image_id': 'image_id', 'member_id': 'member_id'},
        'args': [{'opts': ['--image_id'], 'type': 'str', 'required': True, 'help': '镜像 ID，可通过 list_images.py 获取'}, {'opts': ['--member_id'], 'type': 'str', 'required': True, 'help': '成员 ID（接受共享的租户 ID），可通过 list_image_members.py 获取'}],
    },
    'show_image_quota': {
        'method': 'show_image_quota',
        'req': 'ShowImageQuotaRequest',
        'list': False,
        'action': '查询 IMS 镜像配额，包括已使用数量和配额上限',
        'resp': [],
        'map': {},
        'args': [],
    },
    'show_job': {
        'method': 'show_job',
        'req': 'ShowJobRequest',
        'list': False,
        'action': '查询 IMS 异步任务信息（如镜像创建/导出等异步操作的执行状态）',
        'resp': [],
        'map': {'job_id': 'job_id'},
        'args': [{'opts': ['--job_id'], 'type': 'str', 'required': True, 'help': '异步任务 ID，创建镜像/导出镜像等异步操作返回的 job_id'}],
    },
    'show_job_progress': {
        'method': 'show_job_progress',
        'req': 'ShowJobProgressRequest',
        'list': False,
        'action': '查询 IMS 异步任务进度（含子任务进度），比 show_job.py 返回更详细的进度信息',
        'resp': [],
        'map': {'job_id': 'job_id'},
        'args': [{'opts': ['--job_id'], 'type': 'str', 'required': True, 'help': '异步任务 ID，创建镜像/导出镜像等异步操作返回的 job_id'}],
    },
}


if __name__ == "__main__":
    sys.exit(run("ims", REGISTRY))
