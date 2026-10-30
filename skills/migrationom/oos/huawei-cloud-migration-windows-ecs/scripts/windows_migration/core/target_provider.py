#!/usr/bin/env python3
"""
目标端基础设施编排器 — 根据源端 Agent 上报规格自动创建目的端 ECS。

设计原则（零硬编码 + 安全红线）：
  - 所有参数来自 config/migrate.yaml 的 sms_task 段（target_* / sg_* / eip_*）
  - 源端规格(cpu/内存)来自 SMS ListServers 上报数据，自动匹配规格/镜像
  - 【红线】安全组最小权限：仅放行 sg_source_cidrs（默认源端公网IP/32）的
    22/8899/8900；任何 0.0.0.0/0 放行规则直接拒绝执行
  - 【EIP】优先复用空闲未绑定 EIP；没有则按需创建
  - VPC/子网/安全组 支持复用已有（配置 id 或按名称匹配），否则自动创建

流程: resolve(源端/项目) → VPC → 子网 → 安全组+规则 → 镜像 → 规格
      → dry_run 预检 → ECS 创建 → 等待 ACTIVE → EIP(复用/创建) → 绑定
"""
from __future__ import annotations

import ipaddress
import json
import logging
import re
import random
import string
import time
import uuid
from pathlib import Path

from core.config import MigrateConfig
from core.exceptions import ConfigError, SmsApiError
from core.sms_client import SmsClient
from core.ownership import (derive_owner_id, is_owned, name_with_owner,
                            owner_tag_pairs, record_owned)

logger = logging.getLogger(__name__)

# 安全红线：禁止放行全网段
_FORBIDDEN_CIDRS = {"0.0.0.0/0", "0.0.0.0/0.0.0.0", "::/0", "0.0.0.0/0, ::/0"}


def _gateway(cidr: str) -> str:
    """子网网段第一可用 IP 作为网关。"""
    net = ipaddress.ip_network(cidr, strict=False)
    return str(net.network_address + 1)


def _net(cidr: str):
    """安全解析 CIDR（解析失败返回 None，避免拖垮编排）。"""
    try:
        return ipaddress.ip_network(cidr, strict=False)
    except Exception:  # noqa: BLE001
        return None


def _cidr_overlap(a: str, b: str) -> bool:
    """网段是否冲突：相等、包含、被包含（有交集即冲突）。"""
    na, nb = _net(a), _net(b)
    if na is None or nb is None:
        return a == b
    return na.overlaps(nb)


def _pick_nonconflict_cidr(candidates: list, avoid: list) -> str:
    """从候选网段中挑选与 avoid 列表完全无重叠（不相交）的第一个。

    candidates 为有序偏好（配置 target_vpc_cidr 优先）；全部冲突则抛错，
    绝不静默创建重叠 VPC/子网造成地址冲突（历史事故根因）。
    """
    for c in candidates:
        if not c:
            continue
        if all(not _cidr_overlap(c, x) for x in avoid if x):
            return c
    raise ConfigError(
        "候选网段全部与现有网络重叠（相等/包含/被包含）："
        f"{candidates} vs {avoid}。请显式配置 target_vpc_id/target_subnet_id "
        "或修改 target_vpc_cidr/target_subnet_cidr 为不冲突网段。")


def _resolve_cidr(preferred: str, defaults: list, avoid: list, allow_overlap: bool, what: str) -> str:
    """网段裁决：默认禁止重叠，仅明确许可（allow_cidr_overlap=true 即“有明确告知/ER 特殊组网”）才放行。

    - preferred 配置了：不冲突直接用；冲突时除非 allow_overlap 否则硬性报错（不静默换网段）。
    - preferred 未配置：从 defaults 枚举挑第一个与 avoid 全不相交的网段。
    """
    if preferred:
        if any(_cidr_overlap(preferred, x) for x in avoid if x):
            if allow_overlap:
                logger.warning(
                    "%s=%s 与现有网络重叠，但 allow_cidr_overlap=true（明确告知/ER 等特殊组网），允许创建",
                    what, preferred)
                return preferred
            raise ConfigError(
                f"{what}={preferred} 与现有网络重叠（相等/包含/被包含），默认禁止创建重叠网段。"
                "请显式配置 target_vpc_id/target_subnet_id 复用已有网络，"
                "或仅在“明确告知/ER 等特殊组网”场景显式设置 allow_cidr_overlap=true。")
        return preferred
    return _pick_nonconflict_cidr(defaults, avoid)


def _random_password(length: int = 16) -> str:
    """生成符合 ECS 复杂度要求的临时密码（大小写+数字+特殊字符）。"""
    pool = string.ascii_letters + string.digits + "!@$%^-_=+[]{}:,./?"
    while True:
        pw = "".join(random.SystemRandom().choice(pool) for _ in range(length))
        classes = sum([
            any(c.islower() for c in pw),
            any(c.isupper() for c in pw),
            any(c.isdigit() for c in pw),
            any(c in "!@$%^-_=+[]{}:,./?" for c in pw),
        ])
        if classes >= 3 and not any(w in pw for w in ("Administrator", "administrator")):
            return pw


class TargetProvider:
    """目标端基础设施编排。所有写操作必须在外部确认后调用。"""

    def __init__(self, cfg: MigrateConfig, client: SmsClient, source: dict, dry_run: bool = False):
        self.cfg = cfg
        self.client = client
        self.source = source
        self.st = cfg.sms_task
        self.dry_run = dry_run
        # 属主指纹（HMAC(migration_ak, salt||project)），跨项目天然隔离
        self._owner_id = ""
        try:
            self._owner_id = derive_owner_id(self.project_id, cfg.sms_agent.ak or "",
                                             cfg.ownership.salt, cfg.ownership.owner_tag_value)
        except Exception:
            self._owner_id = ""
        self._owned_base = Path(__file__).parent.parent
        self._flavor_name = ""
        self._image_name = ""
        self._vpc_id = ""
        self._subnet_id = ""
        self._sg_id = ""
        self._flavor_id = ""
        self._image_id = ""
        self._image_candidates: list = []
        self._image_match = ""

    # ---------- 基础 ----------

    @property
    def project_id(self) -> str:
        return self.client.project()[0]

    def _name(self, prefix: str) -> str:
        """属主指纹命名：<prefix>-<host[:16]>-<owner_id>（稳定，去时间戳供复用）。"""
        return name_with_owner(prefix, self.source.get("name", "migrate"), self._owner_id, "")

    def _stable_name(self, prefix: str, host: str = "project") -> str:
        """项目级稳定名（VPC/子网等按项目归并复用）。"""
        return name_with_owner(prefix, host, self._owner_id, "")

    def _sg_rule_fingerprint(self) -> str:
        """安全组规则指纹：hash(排序后的 来源CIDR + 端口集合) 前 8 位。

        规则相同的批量主机 → 同一指纹 → 复用同一属主 SG（N 台 → 1 个）。
        """
        import hashlib
        cidrs = ",".join(sorted(c.strip() for c in (self.st.sg_source_cidrs or [])))
        ports = ",".join(str(p) for p in sorted(self.st.sg_ports or []))
        return hashlib.sha256(f"{cidrs}|{ports}".encode()).hexdigest()[:8]

    def _sg_ingress_rules(self, sg_id: str) -> set:
        """读取安全组入方向规则集合（(protocol, multiport, cidr)）。"""
        out = set()
        data = self.client.call("VPC", "ListSecurityGroupRules/v3",
                                {"security_group_id": [sg_id], "direction": "ingress"})
        for r in data.get("security_group_rules") or data.get("rules") or []:
            if r.get("direction") == "ingress":
                out.add((r.get("protocol"), r.get("multiport") or "",
                         r.get("remote_ip_prefix") or ""))
        return out

    # ---------- 安全红线 ----------

    def _assert_no_global_sg(self, sg: dict) -> None:
        """复用已有安全组时：任一入方向规则为 0.0.0.0/0 → 直接拒绝（红线）。"""
        if not sg:
            return
        data = self.client.call("VPC", "ListSecurityGroupRules/v3",
                                {"security_group_id": [sg.get("id")], "direction": "ingress"})
        rules = data.get("security_group_rules") or data.get("rules") or []
        for r in rules:
            if r.get("direction") == "ingress" and (r.get("remote_ip_prefix") or "") in _FORBIDDEN_CIDRS:
                raise SmsApiError(
                    f"安全组 {sg.get('name', sg.get('id'))} 含 0.0.0.0/0 入方向放行规则，"
                    "违反最小权限安全红线，拒绝复用。请清理或改用自动创建。",
                    detail={"rule": r},
                )

    def _assert_cidrs_ok(self, cidrs: list) -> None:
        if not cidrs:
            raise ConfigError("sg_source_cidrs 不能为空（安全红线：必须显式放行最小来源）")
        for c in cidrs:
            if c.strip() in _FORBIDDEN_CIDRS:
                raise ConfigError(f"sg_source_cidrs 禁止包含 {c}（红线：不允许 0.0.0.0/0 放行）")

    # ---------- VPC / 子网 ----------

    def _source_network(self) -> dict:
        """定位源端 ECS 所在 VPC/子网（源端内网IP匹配），返回 {vpc_id, vpc_cidr, subnet_id, subnet_cidr}。

        【网络编排红线】目标网络要么复用源端 VPC/子网（保证源端-代理-目标同网可达），
        要么新建与源端/现有网络【完全不相交】的网段（不相等、不包含、不包含于）。
        源端非云内 ECS（无网卡）时返回 {}，走新建路径。
        """
        if getattr(self, "_src_net_cache", None) is not None:
            return self._src_net_cache
        self._src_net_cache = {}
        src_ip = (self.source or {}).get("ip") or ""
        if not src_ip:
            return self._src_net_cache
        try:
            servers = (self.client.call("ECS", "ListServersDetails", {"limit": 1000}, timeout=90)
                       .get("servers") or [])
            vpcs = (self.client.call("VPC", "ListVpcs/v2", {}, with_project=True, timeout=60)
                    .get("vpcs") or [])
            subnets = (self.client.call("VPC", "ListSubnets", {}, with_project=True, timeout=60)
                       .get("subnets") or [])
        except Exception as e:  # noqa: BLE001
            logger.warning("源端网络探测失败: %s", e)
            return self._src_net_cache
        # 1) 源端 ECS 地址 → VPC id（addresses 字典键为 VPC id）
        vpc_id = ""
        for sv in servers:
            for _k, items in (sv.get("addresses") or {}).items():
                if any(it.get("addr") == src_ip for it in items):
                    vpc_id = _k if re.fullmatch(r"[0-9a-fA-F-]{36}", _k or "") else ""
                    break
            if vpc_id:
                break
        # 2) 子网按“包含源端 IP”定位（交叉校验 vpc_id）
        ip = _net(src_ip + "/32") if src_ip else None
        subnet = next((s for s in subnets
                       if s.get("cidr") and ip and ip.subnet_of(_net(s["cidr"]))
                       and (not vpc_id or s.get("vpc_id") == vpc_id)), None)
        if subnet:
            self._src_net_cache["subnet_id"] = subnet.get("id")
            self._src_net_cache["subnet_cidr"] = subnet.get("cidr")
            vpc_id = vpc_id or subnet.get("vpc_id") or ""
        self._src_net_cache["vpc_id"] = vpc_id
        if vpc_id:
            v = next((x for x in vpcs if x.get("id") == vpc_id), None)
            if v:
                self._src_net_cache["vpc_cidr"] = v.get("cidr")
        return self._src_net_cache

    def prepare_vpc(self) -> str:
        if self._vpc_id:
            return self._vpc_id
        if self.st.target_vpc_id:
            self._vpc_id = self.st.target_vpc_id
            return self._vpc_id
        src_net = self._source_network()
        if self.dry_run:
            return "(dry-run: " + (
                f"复用源端 VPC {src_net.get('vpc_id') or 'Unknown'}"
                if src_net.get("vpc_id") else "自动新建 VPC（与源端/现有网络不相交）") + ")"
        vpcs = self.client.call("VPC", "ListVpcs/v2", {}, with_project=True).get("vpcs") or []
        existing_cidrs = [v.get("cidr") for v in vpcs if v.get("cidr")]

        # 【优先】复用源端所在 VPC：目标与源端/代理同网，杜绝跨网不通（SMS.3805 类事故）
        if src_net.get("vpc_id"):
            logger.info("复用源端所在 VPC: %s (cidr=%s)", src_net["vpc_id"], src_net.get("vpc_cidr"))
            self._vpc_id = src_net["vpc_id"]
            return self._vpc_id

        # 按名称复用（幂等重跑），不按 CIDR 匹配（历史：同 CIDR 误匹配旁路 VPC）
        stable_vpc = self._stable_name("vpc-mig")
        for v in vpcs:
            if v.get("name") in (self.st.target_vpc_name, stable_vpc) and v.get("name"):
                logger.info("复用已有 VPC: %s (%s)", v.get("id"), v.get("name"))
                self._vpc_id = v["id"]
                return v["id"]

        # 【新建】默认禁止重叠（相等/包含/被包含），仅明确许可或 ER 等特殊组网才允许
        avoid = [cidr for cidr in existing_cidrs if cidr]
        cidr = _resolve_cidr(self.st.target_vpc_cidr, ["192.168.0.0/16", "10.0.0.0/16", "172.16.0.0/16"],
                             avoid, self.st.allow_cidr_overlap, "target_vpc_cidr")
        name = self.st.target_vpc_name or self._stable_name("vpc-mig")
        data = self.client.call("VPC", "CreateVpc", {
            "vpc.name": name,
            "vpc.cidr": cidr,
            "vpc.description": "host-migration auto target vpc (owned)",
            "vpc.tags.1.key": "owner", "vpc.tags.1.value": "huawei-cloud-migration-windows-ecs",
            "vpc.tags.2.key": "owner_id", "vpc.tags.2.value": self._owner_id,
        }, with_project=True)
        vid = data["vpc"]["id"]
        self._vpc_id = vid
        record_owned(self._owned_base, "vpc", vid, name, self._owner_id)
        logger.info("VPC 已创建(属主 %s): %s (%s/%s)", self._owner_id, vid, name, cidr)
        return vid

    def prepare_subnet(self, vpc_id: str) -> str:
        if self._subnet_id:
            return self._subnet_id
        if self.st.target_subnet_id:
            self._subnet_id = self.st.target_subnet_id
            return self._subnet_id
        src_net = self._source_network()
        if self.dry_run:
            return "(dry-run: " + (
                f"复用源端子网 {src_net.get('subnet_id') or 'Unknown'}"
                if src_net.get("subnet_id") and src_net.get("vpc_id") == vpc_id
                else "自动新建子网（VPC 内不与其他子网重叠）") + ")"
        subnets = self.client.call("VPC", "ListSubnets", {"vpc_id": vpc_id}, with_project=True).get("subnets") or []

        # 【优先】复用源端所在子网（源端-代理-目标同 L2 可达）
        if src_net.get("vpc_id") == vpc_id and src_net.get("subnet_id"):
            logger.info("复用源端所在子网: %s (%s)", src_net["subnet_id"], src_net.get("subnet_cidr"))
            self._subnet_id = src_net["subnet_id"]
            return self._subnet_id

        # 按名称复用（幂等重跑），不按 CIDR 匹配
        stable_sub = self._stable_name("subnet-mig")
        for s in subnets:
            if s.get("name") in (self.st.target_subnet_name, stable_sub) and s.get("name"):
                logger.info("复用已有子网: %s (%s)", s.get("id"), s.get("cidr"))
                self._subnet_id = s["id"]
                return s["id"]

        # 【新建】子网网段必须落在 VPC 内且与其内已有子网不相交
        vpc_cidr = ""
        for v in (self.client.call("VPC", "ListVpcs/v2", {}, with_project=True).get("vpcs") or []):
            if v.get("id") == vpc_id:
                vpc_cidr = v.get("cidr") or ""
                break
        sub_cidrs = [s.get("cidr") for s in subnets if s.get("cidr")]
        # 默认禁止子网重叠；未配置 preferred 时在 VPC 网段内枚举 /24 段避让已有子网
        defaults = []
        if vpc_cidr:
            vnet = _net(vpc_cidr)
            if vnet:
                defaults = [str(vnet.network_address + i * 256) + "/24"
                            for i in range(int(vnet.num_addresses) // 256)]
        cidr = _resolve_cidr(self.st.target_subnet_cidr, defaults, sub_cidrs,
                             self.st.allow_cidr_overlap, "target_subnet_cidr")
        name = self.st.target_subnet_name or self._stable_name("subnet-mig")
        az = self.plan_az()
        data = self.client.call("VPC", "CreateSubnet", {
            "subnet.name": name,
            "subnet.cidr": cidr,
            "subnet.gateway_ip": _gateway(cidr),
            "subnet.vpc_id": vpc_id,
            "subnet.availability_zone": az,
            "subnet.description": "host-migration auto target subnet (owned)",
            "subnet.tags.1.key": "owner", "subnet.tags.1.value": "huawei-cloud-migration-windows-ecs",
            "subnet.tags.2.key": "owner_id", "subnet.tags.2.value": self._owner_id,
        }, with_project=True)
        sid = data["subnet"]["id"]
        self._subnet_id = sid
        record_owned(self._owned_base, "subnet", sid, name, self._owner_id)
        logger.info("子网已创建(属主 %s): %s (%s/%s)", self._owner_id, sid, name, cidr)
        return sid

    # ---------- 安全组（红线：最小权限） ----------

    def prepare_security_group(self, vpc_id: str) -> tuple[str, list]:
        """创建/复用安全组，并确保最小权限入方向规则存在（22/8899/8900 ← 源端 IP）。"""
        if self._sg_id:
            return self._sg_id, []
        self._assert_cidrs_ok(self.st.sg_source_cidrs)
        if self.st.target_sg_id:
            sg = {"id": self.st.target_sg_id}
            self._assert_no_global_sg(sg)
            self._sg_id = self.st.target_sg_id
            # 属主校验：非属主 SG 只读复用，禁止补规则（红线 O2）
            if is_owned(self._owned_base, sg, self._owner_id, rtype="sg"):
                return self._ensure_rules(sg)
            logger.warning("安全组 %s 非属主，仅只读复用，不添加规则", self._sg_id)
            return self._sg_id, []

        if self.dry_run:
            return "(dry-run)", [(c, ",".join(str(p) for p in self.st.sg_ports)) for c in self.st.sg_source_cidrs]

        # 复用同名安全组（配置显式指定名称时）
        sgs = self.client.call("VPC", "ListSecurityGroups/v3", {}).get("security_groups") or []
        if self.st.target_sg_name:
            for g in sgs:
                if g.get("name") == self.st.target_sg_name:
                    self._assert_no_global_sg(g)
                    self._sg_id = g.get("id")
                    if is_owned(self._owned_base, g, self._owner_id, rtype="sg"):
                        logger.info("复用属主安全组: %s", g.get("id"))
                        return self._ensure_rules(g)
                    logger.warning("安全组 %s 非属主，仅只读复用，不添加规则", g.get("id"))
                    return self._sg_id, []

        # 【规则指纹归并复用】规则相同的属主 SG 直接复用（N 台 → 1 个，防资源膨胀）
        if getattr(self.st, "sg_merge", True):
            target_rules = {
                ("tcp", ",".join(str(p) for p in sorted(self.st.sg_ports)), cidr.strip())
                for cidr in self.st.sg_source_cidrs
            }
            for g in sgs:
                if not is_owned(self._owned_base, g, self._owner_id, rtype="sg"):
                    continue
                self._assert_no_global_sg(g)
                existing = self._sg_ingress_rules(g.get("id") or "")
                if target_rules and target_rules <= existing:
                    self._sg_id = g.get("id")
                    logger.info("复用规则指纹匹配属主 SG: %s (%s) 规则覆盖 %s",
                                g.get("id"), g.get("name"), target_rules)
                    return self._sg_id, []
            logger.info("未找到规则覆盖的属主 SG，将按指纹创建新 SG（fingerprint=%s）",
                        self._sg_rule_fingerprint())

        name = self.st.target_sg_name or \
            f"sg-mig-{self._sg_rule_fingerprint()}-{self._owner_id}"[:64]
        data = self.client.call("VPC", "CreateSecurityGroup/v3", {
            "security_group.name": name,
            "security_group.description": "host-migration minimal sg (owned)",
            # API 层安全组默认企业项目 ID（0=默认项目；指定企业项目请经账号/迁移项目承载）
            "security_group.enterprise_project_id": "0",
            "security_group.tags.1.key": "owner", "security_group.tags.1.value": "huawei-cloud-migration-windows-ecs",
            "security_group.tags.2.key": "owner_id", "security_group.tags.2.value": self._owner_id,
        }, with_project=True)
        sg = data["security_group"]
        self._sg_id = sg["id"]
        record_owned(self._owned_base, "sg", sg["id"], name, self._owner_id)
        logger.info("安全组已创建(属主 %s): %s (%s)", self._owner_id, sg["id"], name)
        return self._ensure_rules(sg)

    def _ensure_rules(self, sg: dict) -> tuple[str, list]:
        """确保最小权限入方向规则存在（幂等）。

        v3 规则使用 multiport 字段（如 22,8899,8900），每个来源一条规则。
        仅添加目标规则，不触碰其他规则；已存在则跳过。
        """
        sid = sg["id"]
        target_multiport = ",".join(str(p) for p in self.st.sg_ports)
        existing = set()
        data = self.client.call("VPC", "ListSecurityGroupRules/v3",
                                {"security_group_id": [sid], "direction": "ingress"})
        for r in data.get("security_group_rules") or data.get("rules") or []:
            if r.get("direction") == "ingress":
                existing.add((r.get("protocol"), r.get("multiport") or "",
                              r.get("remote_ip_prefix") or ""))

        added = []
        for cidr in self.st.sg_source_cidrs:
            key = ("tcp", target_multiport, cidr.strip())
            if key in existing:
                logger.info("安全组规则已存在，跳过: %s <- %s", target_multiport, cidr.strip())
                continue
            if self.dry_run:
                added.append(cidr.strip())
                continue
            self.client.call("VPC", "CreateSecurityGroupRule/v3", {
                "security_group_rule.direction": "ingress",
                "security_group_rule.security_group_id": sid,
                "security_group_rule.ethertype": "IPv4",
                "security_group_rule.protocol": "tcp",
                "security_group_rule.multiport": target_multiport,
                "security_group_rule.remote_ip_prefix": cidr.strip(),
                "security_group_rule.action": "allow",
                "security_group_rule.description": "sms migration minimal",
            }, with_project=True)
            logger.info("安全组规则已添加: %s <- %s", target_multiport, cidr.strip())
            added.append(cidr.strip())
        return sid, added

    # ---------- 规格 / 镜像 ----------

    def plan_az(self) -> str:
        if not self.st.target_az:
            raise ConfigError(
                "请配置 sms_task.target_az（可用区）。代码层 cn-north-4a 兜底已移除，"
                "避免在非预期区域静默建机。"
            )
        return self.st.target_az

    # 鲲鹏(ARM) 系列前缀：Windows 镜像仅支持 x86，目标规格必须排除 ARM
    ARM_FLAVOR_PREFIXES = ("ac", "kc", "ks", "ka", "km", "kk", "cq")

    @staticmethod
    def _is_x86_flavor(fid: str) -> bool:
        f = (fid or "").lower()
        return not f.startswith(TargetProvider.ARM_FLAVOR_PREFIXES)

    def plan_flavor(self) -> str:
        if self._flavor_id:
            return self._flavor_id
        if self.st.target_flavor_id:
            self._flavor_id = str(self.st.target_flavor_id)
            return self._flavor_id
        src_cpu = int(self.source.get("cpu_quantity") or 2)
        src_mem_gb = int((self.source.get("memory") or 4 * 1024**3) / 1024**3) or 4
        az = self.plan_az()
        data = self.client.call("ECS", "ListFlavors",
                                {"availability_zone": az, "limit": 1000}, with_project=True)
        flavors = data.get("flavors") or []
        cands = [f for f in flavors
                 if int(f.get("vcpus", 0)) >= src_cpu and int(f.get("ram", 0)) >= src_mem_gb * 1024
                 and self._is_x86_flavor(f.get("id"))]
        exact = [f for f in cands
                 if int(f.get("vcpus", 0)) == src_cpu and int(f.get("ram", 0)) == src_mem_gb * 1024]
        pick = exact or cands
        if not cands:
            raise SmsApiError(f"{az} 无满足源端规格(≥{src_cpu}vCPU/{src_mem_gb}GB)的 x86 可用规格"
                              "（请在 sms_task.target_flavor_id 显式指定规格）")
        pick.sort(key=lambda f: (int(f.get("vcpus")), int(f.get("ram"))))
        fid = pick[0]["id"]
        self._flavor_id = fid
        self._flavor_name = pick[0].get("name") or fid
        logger.info("规格匹配(%s源端): %s (%s, %s vCPU / %s MB)",
                    "精确" if exact else "最小满足", fid, self._flavor_name,
                    pick[0].get("vcpus"), pick[0].get("ram"))
        return fid

    @staticmethod
    def _source_version_keyword(os_version: str) -> str:
        """从源端 os_version（如 WINDOWS2022_64BIT）提取版本年份关键字。"""
        m = re.search(r"(20\d{2})", os_version or "")
        return m.group(1) if m else ""

    def plan_image(self) -> str:
        """镜像选择：默认与源端系统版本一致（同源段 2022），支持私有镜像，支持显式指定。

        顺序: 1) config/CLI 显式 target_image_id
              2) 与源端 os_version 版本匹配（公共+私有镜像，优先 Datacenter）
              3) 兜底任意 Windows 公共镜像
        """
        if self._image_id:
            return self._image_id
        if self.st.target_image_id:
            self._image_id = self.st.target_image_id
            self._image_name = f"<user-specified {self.st.target_image_id}>"
            return self._image_id

        kw = self._source_version_keyword(self.source.get("os_version") or "")
        images = []
        for imagetype in ("gold", "private"):
            data = self.client.call("IMS", "ListImages", {
                "__os_type": "Windows", "__imagetype": imagetype,
                "__platform": "Windows", "__os_bit": "64",
            })
            images.extend(data.get("images") or [])
        images = [i for i in images if (i.get("status") or "").lower() == "active"]
        self._image_candidates = [(i.get("id"), i.get("name")) for i in images]

        if kw:
            matched = [i for i in images if kw in (i.get("name") or "")]
            if matched:
                # 同一版本内优先 Datacenter，其次按名称稳定排序（便于确定性复现）
                matched.sort(key=lambda i: (0 if "datacenter" in (i.get("name") or "").lower() else 1,
                                            str(i.get("name"))))
                img = matched[0]
                self._image_id = img.get("id")
                self._image_name = img.get("name") or img.get("id")
                logger.info("镜像选择(与源端 %s 一致): %s (%s)", self.source.get("os_version"),
                            img.get("id"), self._image_name)
                return img["id"]
            logger.warning("未找到与源端版本 %s 匹配的镜像，回退公共镜像", kw)
        if not images:
            raise SmsApiError("未找到任何活跃的 Windows 镜像（gold 或 private）")
        self._image_id = images[0].get("id")
        self._image_name = images[0].get("name") or images[0].get("id")
        logger.info("镜像选择(兜底): %s (%s)", images[0].get("id"), self._image_name)
        return self._image_id

    # ---------- ECS ----------

    def _server_params(self) -> dict:
        vpc_id = self.prepare_vpc()
        subnet_id = self.prepare_subnet(vpc_id)
        sg_id, _ = self.prepare_security_group(vpc_id)
        flavor = self.plan_flavor()
        image = self.plan_image()
        return {
            "server.name": self.st.target_name or self._name("migrate-ecs"),
            "server.flavorRef": flavor,
            "server.imageRef": image,
            "server.vpcid": vpc_id,
            "server.root_volume.volumetype": self.st.target_root_volume_type,
            "server.root_volume.size": self.st.target_root_volume_size,
            "server.nics.1.subnet_id": subnet_id,
            "server.security_groups.1.id": sg_id,
            "server.availability_zone": self.plan_az(),
            # ECS API 该版本: server.tags 为 array<string>（key.value 字符串），对象数组请用 server_tags
            "server.server_tags.1.key": "owner", "server.server_tags.1.value": "huawei-cloud-migration-windows-ecs",
            "server.server_tags.2.key": "owner_id", "server.server_tags.2.value": self._owner_id,
            "server.server_tags.3.key": "migration_source", "server.server_tags.3.value": str(self.source.get("name") or "")[:63],
        }

    def create_ecs(self, admin_pass: str) -> dict:
        params = self._server_params()

        # 幂等：按固定名称复用已创建目的端 ECS，避免中断后重跑重复建机
        if self.st.target_name:
            existing = self._find_ecs_by_name(self.st.target_name)
            if existing:
                if existing.get("status") == "ACTIVE":
                    logger.info("复用目标 ECS: %s (%s)", existing.get("id"), existing.get("name"))
                    return existing
                logger.info("目标 ECS 已存在但未就绪(%s)，等待: %s",
                            existing.get("status"), existing.get("id"))
                return self._wait_ecs(existing["id"])

        params["server.adminPass"] = admin_pass
        params["X-Client-Token"] = str(uuid.uuid4())
        check = dict(params)
        check["dry_run"] = "true"
        init = self.client.call("ECS", "CreateServers", check, with_project=True, timeout=180)
        logger.info("ECS 创建预检通过: %s", json.dumps(init, ensure_ascii=False)[:200])

        data = self.client.call("ECS", "CreateServers", params, with_project=True, timeout=180)
        ids = data.get("server_ids") or data.get("serverIds") or []
        if not ids:
            raise SmsApiError(f"ECS 创建未返回 server_ids: {json.dumps(data, ensure_ascii=False)[:300]}")
        vid = ids[0]
        record_owned(self._owned_base, "ecs", vid,
                     self.st.target_name or self._name("migrate-ecs"), self._owner_id)
        logger.info("ECS 创建中(属主 %s): %s", self._owner_id, vid)
        return self._wait_ecs(vid)

    def _wait_ecs(self, vm_id: str, timeout: int = 900) -> dict:
        deadline = time.time() + timeout
        while time.time() < deadline:
            sv = self._find_ecs_by_id(vm_id)
            if sv and sv.get("status") == "ACTIVE":
                return sv
            time.sleep(15)
        raise SmsApiError(f"ECS {vm_id} 等待 ACTIVE 超时({timeout}s)")

    def _find_ecs_by_id(self, vm_id: str) -> dict | None:
        data = self.client.call("ECS", "ListServersDetails", {"limit": 1000})
        for sv in data.get("servers") or []:
            if sv.get("id") == vm_id:
                return sv
        return None

    def _find_ecs_by_name(self, name: str) -> dict | None:
        data = self.client.call("ECS", "ListServersDetails", {"limit": 1000})
        for sv in data.get("servers") or []:
            if sv.get("name") == name:
                return sv
        return None

    def _find_eip_bound_to(self, port_id: str) -> dict | None:
        data = self.client.call("EIP", "ListPublicips", {"limit": 200}, with_project=True)
        for eip in data.get("publicips") or []:
            if eip.get("associate_instance_id") == port_id:
                return eip
        return None

    def _first_port_id(self, ecs: dict) -> str:
        addresses = ecs.get("addresses") or {}
        for _vpc, items in addresses.items():
            for it in items:
                if it.get("OS-EXT-IPS:type") == "fixed" and it.get("OS-EXT-IPS:port_id"):
                    return it["OS-EXT-IPS:port_id"]
        raise SmsApiError(f"无法从 ECS 获取网卡 port_id: {ecs.get('id')}")

    # ---------- 目的端数据盘（源端数据盘 1:1 自动创建并挂载） ----------

    def _source_data_disks(self) -> list:
        """源端数据盘列表（排除系统盘/启动盘）。字段兼容 init_target_server.disks 与 disks。

        ListServers 返回的源端对象不含磁盘明细（init_target_server），
        这里通过 show_server 回查补全——磁盘信息以 ShowServer 为唯一数据源。
        """
        src = self.source or {}
        init = (src.get("init_target_server") or {}).get("disks") or []
        disks = init if init else (src.get("disks") or [])
        if not disks and src.get("id"):
            full = self.client.show_server(src["id"]) or {}
            init = (full.get("init_target_server") or {}).get("disks") or []
            disks = init if init else (full.get("disks") or [])
        if not disks:
            return []
        sys_disk = next((d for d in disks
                         if (d.get("device_use") or "").upper() in ("OS", "BOOT") or d.get("os_disk")), None)
        return [d for d in disks if sys_disk is not None and d is not sys_disk]

    def prepare_data_disks(self, ecs: dict) -> list:
        """按源端数据盘数量/容量创建同规格 EVS 卷并挂载到目的端 ECS（幂等）。

        已挂数据卷数 >= 源端数据盘数时跳过（重跑安全）；属主指纹命名 + 登记清单。
        """
        src_data = self._source_data_disks()
        if not src_data:
            return []
        if self.dry_run:
            return [(self.st.target_root_volume_type,
                     max(1, int((d.get("size") or 0) / 1024**3))) for d in src_data]

        attach = sorted(self.client.ecs_volumes(ecs["id"]), key=lambda v: (v.get("device") or ""))
        vols = []
        for a in attach:
            vol = (self.client.call("EVS", "ShowVolume", {"volume_id": a.get("volumeId")}) or {}).get("volume") or {}
            vols.append(vol)
        # 系统盘 = bootable；数据盘 = 其余
        data_existing = [v for v in vols if str(v.get("bootable") or "").lower() != "true"]
        need = len(src_data) - len(data_existing)
        if need <= 0:
            logger.info("目的端已有 %d 块数据盘（≥源端 %d），跳过创建",
                        len(data_existing), len(src_data))
            return [v.get("id") for v in data_existing[:len(src_data)]]

        created = []
        for i in range(need):
            sd = src_data[len(data_existing) + i]
            size_gb = max(1, int((int(sd.get("size") or 0) + 1024**3 - 1) / 1024**3))
            name = name_with_owner("evs-mig", self.source.get("name", "migrate"),
                                   self._owner_id, f"d{len(data_existing) + i + 1}")
            r = self.client.call("EVS", "CreateVolume", {
                "volume.name": name,
                "volume.size": size_gb,
                "volume.volume_type": self.st.target_root_volume_type,
                "volume.availability_zone": self.plan_az(),
                "volume.tags.owner": "huawei-cloud-migration-windows-ecs",
                "volume.tags.owner_id": self._owner_id,
            }, with_project=True, timeout=180)
            ids = r.get("volume_ids") or []
            if not ids:
                raise SmsApiError(f"数据盘创建未返回 volume_ids: {str(r)[:200]}")
            vid = ids[0]
            # 等待卷 available（异步）
            deadline = time.time() + 150
            while time.time() < deadline:
                vr = self.client.call("EVS", "ListVolumes", {"id": vid}, with_project=True, timeout=60)
                vv = (vr.get("volumes") or [{}])[0]
                if vv.get("status") == "available":
                    break
                time.sleep(5)
            self.client.call("ECS", "AttachServerVolume", {
                "server_id": ecs["id"],
                "volumeAttachment.volumeId": vid,
            }, with_project=True, timeout=180)
            record_owned(self._owned_base, "evs", vid, name, self._owner_id)
            created.append(vid)
            logger.info("数据盘已创建并挂载(属主 %s): %s (%dGB) → %s",
                        self._owner_id, vid, size_gb, ecs["id"])
        return created

    # ---------- EIP（优先复用空闲，无则创建） ----------

    def prepare_eip(self) -> dict:
        if not self.st.use_eip:
            return {}
        if self.dry_run:
            return {"eip": "(dry-run)"}
        # 1) 指定复用
        if self.st.eip_id:
            return self._get_eip(self.st.eip_id)
        # 2) 空闲未绑定：优先属主空闲，其次非属主空闲（非属主仅复用，不删除/改属性）
        data = self.client.call("EIP", "ListPublicips", {"limit": 200}, with_project=True)
        free_owned, free_other = [], []
        for eip in data.get("publicips") or []:
            if not eip.get("associate_instance_id"):
                (free_owned if is_owned(self._owned_base, eip, self._owner_id, rtype="eip")
                 else free_other).append(eip)
        if free_owned:
            eip = free_owned[0]
            logger.info("复用属主空闲 EIP: %s (%s)", eip.get("id"), eip.get("public_ip_address"))
            return eip
        if free_other:
            eip = free_other[0]
            logger.warning("复用非属主空闲 EIP（仅复用不修改）: %s (%s)",
                           eip.get("id"), eip.get("public_ip_address"))
            return eip
        # 3) 按需创建（属主指纹命名 + Tags，异步接口：创建后用名称轮询定位新 EIP）
        name = name_with_owner("eip-mig", self.source.get("name", "migrate"),
                               self._owner_id, "")[:64]
        data = self.client.call("EIP", "CreatePublicip", {
            "publicip.type": self.st.eip_type,
            "publicip.alias": name,
            # 该版本 API 不支持 publicip.tags（对象数组），属主由 alias 指纹名 + record_owned 承载
            "bandwidth.share_type": "PER",
            "bandwidth.name": name,
            "bandwidth.size": self.st.eip_bandwidth_size,
            "bandwidth.charge_mode": self.st.eip_charge_mode,
        }, with_project=True, timeout=180)
        eip = data.get("publicip") or {}
        eid = eip.get("id")
        if not eid:
            # 响应无 id（异步/任务型），按别名轮询列表
            deadline = time.time() + 180
            while time.time() < deadline:
                eips = (self.client.call("EIP", "ListPublicips", {"limit": 200},
                                         with_project=True).get("publicips") or [])
                new = [e for e in eips if e.get("name") == name or e.get("alias") == name]
                if new:
                    eip = new[0]
                    eid = eip.get("id")
                    logger.info("EIP 已在列表中定位: %s (%s)", eid, eip.get("public_ip_address"))
                    break
                time.sleep(10)
        if not eid:
            raise SmsApiError(f"EIP 创建结果解析失败: {str(data)[:200]}")
        record_owned(self._owned_base, "eip", eid, name, self._owner_id)
        return self._wait_eip_ready(eid)

    def _wait_eip_ready(self, eip_id: str, timeout: int = 180) -> dict:
        """等待 EIP 就绪（ACTIVE/DOWN 且可绑定）。"""
        deadline = time.time() + timeout
        while time.time() < deadline:
            e = self._get_eip(eip_id)
            st = (e.get("status") or "").upper()
            if e.get("public_ip_address") or st in ("ACTIVE", "DOWN", "UNBOUNDED", "UNBIND"):
                return e
            time.sleep(10)
        logger.warning("EIP %s 等待就绪超时，按现状返回", eip_id)
        return self._get_eip(eip_id)

    def _get_eip(self, eip_id: str) -> dict:
        data = self.client.call("EIP", "ListPublicips", {"id": [eip_id]}, with_project=True)
        eips = data.get("publicips") or []
        return eips[0] if eips else {"id": eip_id}

    def bind_eip(self, eip_id: str, port_id: str) -> None:
        if self._find_eip_bound_to(port_id):
            logger.info("目的端 ECS 已绑定 EIP，跳过重复绑定")
            return
        self.client.call("EIP", "AssociatePublicips", {
            "publicip_id": eip_id,
            "publicip.associate_instance_id": port_id,
            "publicip.associate_instance_type": "PORT",
        }, with_project=True, timeout=180)

    # ---------- 主流程 ----------

    def prepare(self) -> dict:
        """编排目标端基础设施，返回 {vm_id, name, private_ip, eip_id, eip_address, ...}。"""
        st = self.st
        self._assert_cidrs_ok(st.sg_source_cidrs)

        if self.dry_run:
            return {
                "dry_run": True,
                "source": {"id": self.source.get("id"), "cpu": self.source.get("cpu_quantity"),
                           "memory_mb": self.source.get("memory"),
                           "os_version": self.source.get("os_version")},
                "vpc": self.prepare_vpc(),
                "subnet": "(auto)",
                "security_group_rules": [(c, p) for c in st.sg_source_cidrs for p in st.sg_ports],
                "flavor": self.plan_flavor(),
                "flavor_name": self._flavor_name,
                "image": self.plan_image(),
                "image_name": self._image_name,
                "image_match": ("源端同版本" if self._source_version_keyword(self.source.get("os_version") or "")
                                and self._source_version_keyword(self.source.get("os_version") or "") in (self._image_name or "")
                                else "兜底/用户指定"),
                "image_candidates": self._image_candidates[:10],
                "az": self.plan_az(),
                "data_volumes": [
                    {"volume_type": st.target_root_volume_type, "size_gb": gb}
                    for _, gb in self.prepare_data_disks({})
                ],
                "eip": ("(dry-run: 优先复用空闲/无则创建)" if st.use_public_ip
                        else "(私网: 不创建 EIP)"),
            }

        vpc_id = self.prepare_vpc()
        subnet_id = self.prepare_subnet(vpc_id)
        sg_id, added_rules = self.prepare_security_group(vpc_id)

        admin_pass = st.target_password or _random_password()
        ecs = self.create_ecs(admin_pass)
        vm_id = ecs["id"]
        private_ip = (ecs.get("addresses") or {}).get(next(iter((ecs.get("addresses") or {})), ""), [{}])[0].get("addr", "")
        # 源端数据盘 1:1：自动创建并挂载目标数据卷（幂等；缺则 create 阶段会被磁盘映射校验拦截）
        data_volume_ids = self.prepare_data_disks(ecs)

        result = {
            "vm_id": vm_id,
            "name": ecs.get("name"),
            "status": ecs.get("status"),
            "private_ip": private_ip,
            "az": ecs.get("OS-EXT-AZ:availability_zone") or st.target_az,
            "flavor": (ecs.get("flavor") or {}).get("id"),
            "flavor_name": self._flavor_name,
            "image_name": self._image_name,
            "image_candidates": self._image_candidates[:10],
            "vpc_id": vpc_id,
            "subnet_id": subnet_id,
            "security_group_id": sg_id,
            "security_group_rules_added": added_rules,
            "data_volume_ids": data_volume_ids,
            "admin_password": admin_pass if not st.target_password else "<config-provided>",
        }
        # 【公网/私网兼容】私网迁移（use_public_ip=false）不需要 EIP，自动跳过；
        # 公网迁移按 use_eip 决定（优先复用空闲，无则创建）。
        if st.use_eip and st.use_public_ip:
            port_id = self._first_port_id(ecs)
            bound = self._find_eip_bound_to(port_id)
            if bound:
                result["eip_id"] = bound.get("id")
                result["eip_address"] = bound.get("public_ip_address") or ""
                logger.info("复用已绑定 EIP: %s (%s)", result["eip_id"], result["eip_address"])
            else:
                eip = self.prepare_eip()
                eid = eip.get("id")
                if eid:
                    self.bind_eip(eid, port_id)
                    result["eip_id"] = eid
                    result["eip_address"] = eip.get("public_ip_address") or ""
        return result


def save_target_state(cfg: MigrateConfig, target: dict) -> Path:
    """保存编排结果到 config/target_state.json（运行时状态，类比 batch_state.json）。"""
    path = Path(__file__).parent.parent / "config" / "target_state.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    state = {k: v for k, v in target.items() if k != "admin_password"}
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def load_target_state() -> dict:
    p = Path(__file__).parent.parent / "config" / "target_state.json"
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return {}