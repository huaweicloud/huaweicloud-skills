#!/usr/bin/env python3
"""
SMS 控制面迁移任务编排 CLI（对应官方最佳实践「创建Windows主机迁移任务」步骤二~五）。

用法:
  # 步骤二前: 发现源端 / 罗列目的端候选
  python3 sms_task.py discover
  python3 sms_task.py ecs-list

  # 步骤二: 设置迁移目的端（创建迁移任务；existing=已有服务器优先，new=自动创建）
  python3 sms_task.py create                     # 默认按 config/sms_task 段
  python3 sms_task.py create --target-name xxx --target-vm-id <ECS_ID> --no-start
  python3 sms_task.py create --mode new --vm-template-id <TMPL_ID>

  # 步骤三: 开始服务器全量复制 + 监控
  python3 sms_task.py start
  python3 sms_task.py wait --target-state SYNCING --timeout 14400

  # 步骤四: 同步增量数据 / 启动目的端
  python3 sms_task.py sync
  python3 sms_task.py cutover

  # 步骤五: 清理快照资源（不可逆，需 --yes）
  python3 sms_task.py cleanup --yes

  # 可编排: 一条命令串起流程
  python3 sms_task.py pipeline --steps discover,create,start,wait --target-state SYNCING

退出码: 0=成功 1=失败 2=配置错误
所有变更类操作（create/start/sync/cutover/cleanup/delete）默认交互确认，--yes 跳过。
"""
from __future__ import annotations

import argparse
import json
import re
import logging
import sys
import time
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.config import ConfigLoader, MigrateConfig  # noqa: E402
from core.exceptions import ConfigError, MigrationError, SmsApiError  # noqa: E402
from core.sms_client import SmsClient, UPDATE_TASK_STATUS_OPS  # noqa: E402
from core.target_provider import TargetProvider, save_target_state, load_target_state  # noqa: E402
from core.ownership import derive_owner_id, is_owned, record_owned, remove_owned, require_owned  # noqa: E402

logger = logging.getLogger("sms_task")


# ---- 状态机（ListTasks/ShowTask 的迁移任务状态） ----
_TERMINAL_FAIL = {"MIGRATE_FAIL", "ABORT", "ABORTING"}
_TERMINAL_OK = {"MIGRATE_SUCCESS"}


def setup_logging(level: str = "INFO", log_dir: str = "", json_mode: bool = False) -> None:
    log_dir_p = Path(log_dir) if log_dir else PROJECT_ROOT / "logs"
    log_dir_p.mkdir(parents=True, exist_ok=True)
    handlers = [
        RotatingFileHandler(log_dir_p / "sms_task.log", maxBytes=50 * 1024 * 1024,
                            backupCount=5, encoding="utf-8"),
    ]
    if not json_mode:
        handlers.insert(0, logging.StreamHandler(sys.stdout))
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=handlers,
    )


def _out(data: dict) -> None:
    sys.stdout.write(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    sys.stdout.flush()


def _confirm(prompt: str, yes: bool) -> bool:
    """变更操作确认。yes=True 直接放行；非交互环境（无 stdin）默认拒绝。"""
    if yes:
        return True
    if not sys.stdin.isatty():
        logger.warning("非交互环境且未带 --yes，已拒绝执行: %s", prompt)
        return False
    try:
        ans = input(f"{prompt} [y/N]: ").strip().lower()
        return ans in ("y", "yes")
    except EOFError:
        return False


def _client(cfg: MigrateConfig) -> SmsClient:
    return SmsClient(ak=cfg.sms_agent.ak, sk=cfg.sms_agent.sk, region=cfg.sms_task.region)


def _task_id(cfg: MigrateConfig, client: SmsClient, args: argparse.Namespace) -> str:
    """解析任务 ID：优先命令行，其次已有任务（按源端）。"""
    if args.task_id:
        return args.task_id
    source = _resolve_source(cfg, client, args)
    task = client.find_task(source["id"])
    if not task:
        raise SmsApiError(f"源端 {source['id']} 下未发现迁移任务，请先执行 create")
    tid = task.get("id") or task.get("task_id")
    if not tid:
        raise SmsApiError(f"任务数据缺少 ID: {json.dumps(task, ensure_ascii=False)[:200]}")
    return tid


def _owner_id_of(cfg: MigrateConfig, client: SmsClient) -> str:
    """当前账号/项目派生属主指纹（HMAC(migration_ak, salt||project)）。"""
    pid, _ = client.project()
    return derive_owner_id(pid, cfg.sms_agent.ak or "",
                           cfg.ownership.salt, cfg.ownership.owner_tag_value)


def _require_task_owned(cfg: MigrateConfig, client: SmsClient, task_id: str, action: str) -> None:
    """红线：迁移任务状态变更前必须确认属主（Tags 无 → 名称指纹 / 会话清单）。"""
    if not cfg.ownership.enabled:
        return
    task = client.show_task(task_id)
    owner_id = _owner_id_of(cfg, client)
    require_owned(PROJECT_ROOT, task, owner_id, rtype="task", action=action)


def _resolve_source(cfg: MigrateConfig, client: SmsClient, args: argparse.Namespace) -> dict:
    if cfg.sms_task.source_server_id:
        sid = cfg.sms_task.source_server_id
        try:
            detail = client.show_server(sid)
            return {"id": sid, "name": detail.get("name"), "os_version": detail.get("os_version"),
                    "cpu_quantity": detail.get("cpu_quantity"), "memory": detail.get("memory")}
        except Exception:
            return {"id": sid}
    return client.find_source_server(ip=args.source_ip or cfg.source.host)


# SMS 任务名称红线（实测固化，SMS.7711）：
#   - 字符集：仅允许 中文/字母/数字/下划线/短横线（官方约束）
#   - 长度：<= 16 字符（实测 33 拒绝、17 通过、20 的 mig_<owner>_<host> 被拒，
#     为兼容多版本 API 取更保守上限 16）
#   - 禁止连续双下划线 __（实测 含连续 __ 被拒；短名 mig_web01_1 通过）
#   - 属主前缀：mig_ 开头，便于一眼辨识本 skill 创建
_MAX_TASK_NAME_LEN = 16
_TASK_NAME_RE = re.compile(r"^[\u4e00-\u9fa5A-Za-z0-9_-]+$")


def _sanitize_task_base(base: str) -> str:
    """源端名 → 任务名可用基名（保留 中文/字母/数字/下划线/短横线）。"""
    return "".join(c if (c.isalnum() or c in "_-") else "_" for c in base).strip("_-")


def _default_task_name(cfg: MigrateConfig, source: dict, owner_id: str = "") -> str:
    base = _sanitize_task_base(source.get("name") or "migrate") or "migrate"
    # 属主指纹任务名：mig_<owner_id>_<host[:3]>，<= 16、无双下划线（SMS.7711 实测红线 + 属主辨识）
    if owner_id:
        return f"mig_{owner_id}_{base[:3]}"[:_MAX_TASK_NAME_LEN]
    # 无指纹（兼容/离线）: mig_<host[:12]>，<= 16
    core = base[:_MAX_TASK_NAME_LEN - 8]
    return f"mig_{core}"[:_MAX_TASK_NAME_LEN]


def _validate_task_name(name: str, *, allow_len: int = _MAX_TASK_NAME_LEN) -> None:
    """创建前校验任务名：字符集 + 长度，违规直接抛 ConfigError（杜绝 SMS.7711）。"""
    if not name or not name.strip():
        raise ConfigError("任务名不能为空（请用 --name 指定或留空自动生成）")
    if len(name) > allow_len:
        raise ConfigError(
            f"任务名过长：{len(name)} > {allow_len} 字符，触发 SMS.7711。"
            f"请使用简短名称（示例: mig_{'hostname'[:12]} 或 --name 自定义 ≤{allow_len} 字符）")
    if not _TASK_NAME_RE.match(name):
        raise ConfigError(
            f"任务名含非法字符：{name!r}。仅允许 中文/字母/数字/下划线/短横线。"
            f"（示例: mig_web01_1）")
    if "__" in name:
        raise ConfigError(f"任务名含连续双下划线：{name!r}，实测触发 SMS.7711。请使用单下划线。")
    if name.startswith("_") or name.endswith("_"):
        raise ConfigError(f"任务名不能以下划线开头/结尾：{name!r}")


def _build_create_params(cfg: MigrateConfig, client: SmsClient, source: dict,
                         args: argparse.Namespace) -> dict:
    st = cfg.sms_task
    project_id, _ = client.project()
    target_name = (args.target_name or st.target_name or f"target-{source.get('name', 'migrate')}").strip()

    owner_id = derive_owner_id(project_id, cfg.sms_agent.ak or "",
                               cfg.ownership.salt, cfg.ownership.owner_tag_value)
    task_name = args.name or st.task_name or _default_task_name(cfg, source, owner_id)
    _validate_task_name(task_name)

    params: dict = {
        "name": task_name,
        "project_id": project_id,
        "project_name": st.region,
        "region_id": st.region,
        "region_name": st.region,
        "source_server.id": source["id"],
        "target_server.name": target_name,
        "type": st.migration_type,
        "os_type": st.os_type,
        "auto_start": "false" if args.no_start else ("true" if st.auto_start else "false"),
        "exist_server": "true" if st.target_mode == "existing" else "false",
        "use_public_ip": "true" if st.use_public_ip else "false",
        "syncing": "true" if st.syncing else "false",
        "start_target_server": "true" if st.start_target_server else "false",
        "need_migration_test": "true" if st.need_migration_test else "false",
        "is_need_consistency_check": "true" if st.is_need_consistency_check else "false",
    }
    if st.speed_limit and st.speed_limit > 0:
        params["speed_limit"] = st.speed_limit
    if st.enterprise_project and st.enterprise_project not in ("", "default"):
        # HTTP API 层面企业项目通过 migproject 承载；此处显式记录配置供审计
        logger.info("企业项目: %s（经迁移项目归属，不直接入参）", st.enterprise_project)

    if st.target_mode == "existing":
        state = load_target_state()
        vm_id = args.target_vm_id or st.target_vm_id or state.get("vm_id", "")
        if not vm_id:
            raise ConfigError("existing 模式必须提供目的端 ECS ID（--target-vm-id / sms_task.target_vm_id / 先执行 prepare-target）")
        params["target_server.vm_id"] = vm_id
        # 【公网/私网兼容】迁移 IP 按使用场景自动推导：
        #   公网(use_public_ip=true): migration_ip = 目的端 EIP（prepare-target 自动写入 eip_address）
        #   私网(use_public_ip=false): migration_ip = 目的端私有 IP（prepare-target 自动写入 private_ip）
        # 显式传入的 args.migration_ip / st.migration_ip 始终优先。
        use_public = bool(st.use_public_ip)
        migration_ip = args.migration_ip or st.migration_ip or ""
        if not migration_ip:
            migration_ip = state.get("eip_address", "") if use_public else state.get("private_ip", "")
        if migration_ip:
            params["migration_ip"] = migration_ip
        elif use_public:
            raise ConfigError("公网迁移需要目的端 EIP：请先执行 prepare-target（use_eip=true）或 --migration-ip 指定")
        else:
            raise ConfigError("私网迁移需要目的端私有 IP：请先执行 prepare-target 或 --migration-ip 指定")
        # 【磁盘映射】系统盘↔系统盘、数据盘↔数据盘：按源端磁盘顺序 1:1 映射到目的端 EVS 卷
        _attach_disk_mapping(params, client, source["id"], vm_id)
    elif st.target_mode == "new":
        tmpl = args.vm_template_id or st.vm_template_id
        if not tmpl:
            raise ConfigError("new 模式必须提供自动创建模板 ID（--vm-template-id 或 sms_task.vm_template_id）")
        params["vm_template_id"] = tmpl
    else:
        raise ConfigError(f"未知 target_mode: {st.target_mode}（可选 existing/new）")
    return params


# ---- 各命令 ----

def cmd_discover(cfg, client, args):
    """步骤二前: 发现源端服务器（只读）。"""
    source = _resolve_source(cfg, client, args)
    task = client.find_task(source["id"])
    _out({"source_server": source, "existing_task": task})


def cmd_ecs_list(cfg, client, args):
    """已有服务器模式: 罗列目的端候选 ECS（只读）。"""
    data = client.list_ecs(name=args.ecs_name)
    servers = data.get("servers", data.get("servers_detail") or [])
    rows = []
    for s in servers:
        rows.append({
            "id": s.get("id"),
            "name": s.get("name"),
            "status": s.get("status"),
            "flavor": (s.get("flavor") or {}).get("id"),
            "az": (s.get("OS-EXT-AZ:availability_zone") or s.get("az") or ""),
            "created": s.get("created"),
        })
    _out({"count": len(rows), "servers": rows})


def cmd_prepare_target(cfg, client, args):
    """目标端基础设施编排：VPC/子网/安全组(最小权限)/ECS/EIP。

    --dry-run 只解析计划（规格/镜像/VPC/空闲EIP），不创建任何资源。
    实际执行为生产变更（创建 ECS/VPC/EIP），需 --yes 或交互确认。
    """
    source = _resolve_source(cfg, client, args)
    provider = TargetProvider(cfg, client, source, dry_run=args.dry_run)
    plan = provider.prepare()
    if args.dry_run:
        _out({"action": "prepare-target", "dry_run": True, "plan": plan})
        return
    prompt = (
        "将创建目的端资源（生产变更）:\n"
        f"  ECS={plan.get('name')} flavor={plan.get('flavor')} az={plan.get('az')}\n"
        f"  安全组规则(仅放行): {plan.get('security_group_rules_added')}\n"
        f"  EIP={plan.get('eip_address') or '(不绑定)'}"
    )
    if not _confirm(prompt, args.yes):
        raise SmsApiError("用户取消创建目的端")
    path = save_target_state(cfg, plan)
    plan["state_file"] = str(path)
    _out({"action": "prepare-target", "result": plan})


def _escape_hcloud(v):
    """KooCLI 参数值中反斜杠会被当作转义符，需翻倍传递（如 Windows 卷 uuid）。"""
    return v.replace("\\", "\\\\") if isinstance(v, str) else v


def _attach_disk_mapping(params: dict, client, source_id: str, vm_id: str) -> None:
    """构建显式磁盘映射（系统盘↔系统盘、数据盘↔数据盘），防 SMS.0515/9001/6033。

    ================= 顺序契约（四重保证，缺一不可） =================
    最终写入 target_server.disks.N 的顺序严格为：
        [0] 系统盘（disk.1）         —— 固定第一位
        [1..] 数据盘按【容量升序】   —— 源端与目的端各自排序后【同序配对】
                                                          （源端小盘 ↔ 目标端 同序 小盘；
                                                           源端大盘 ↔ 目标端 同序 大盘）

    1. 系统盘识别：
       源端——init_target_server.disks 中 device_use ∈ {OS,BOOT} 或 os_disk=true，兜底取第一块；
       目的端——按 ECS 根设备名：OS-EXT-SRV-ATTR:root_device_name（Windows 通常 /dev/vda），
                兜底取第一块挂载卷。
    2. 数据盘识别：除系统盘外的其余盘/卷。
    3. 数据盘内部顺序：源端数据盘与目的端数据卷各自按 size(GB)【升序】排序后逐一配对；
       配对要求 目标盘容量 >= 源盘容量（同序下防 60G 目标对 40G 源 这类错配），
       不满足直接拒绝创建（而不是硬塞错误参数触发 SMS.0515）。
    4. 最终 disks.N 序号 = 上方排序后的数组序号（N 从 1 开始），
       KooCLI 传参即 --target_server.disks.1=系统盘、--target_server.disks.2=第一个数据盘(容量最小)…

    【断言】映射[0] 必须为系统盘；否则视为编程错误直接崩溃，绝不带错序创建任务。
    0515/9001/6033 铁律（见 references/troubleshooting.md 2.1~2.3）：
      - physical_volumes 必须带（否则运行期 0515）
      - uuid 用源端装饰格式，KooCLI 传参反斜杠翻倍（否则 9001）
      - PV/磁盘信息不全会导致 6033
    """
    src = client.show_server(source_id)
    init = (src.get("init_target_server") or {}).get("disks") or []
    src_disks = init if init else (src.get("disks") or [])
    if not src_disks:
        logger.warning("源端无磁盘信息，跳过磁盘映射（可能引发 0515，请人工核对）")
        return

    # 目的端卷 + 容量（EVS）
    attach = sorted(client.ecs_volumes(vm_id), key=lambda v: (v.get("device") or ""))
    vols = []
    for a in attach:
        vid = a.get("volumeId")
        vol = client.call("EVS", "ShowVolume", {"volume_id": vid})
        size_gb = (vol.get("volume") or {}).get("size")
        vols.append({
            "volumeId": vid,
            "device": a.get("device") or "",
            "size_gb": int(size_gb) if size_gb else 0,
            "name": (vol.get("volume") or {}).get("name") or "",
            "bootable": (vol.get("volume") or {}).get("bootable") == "true",
        })
    if not vols:
        raise ConfigError("目的端 ECS 无挂载卷，无法建磁盘映射")
    # 排除 SMS 迁移临时盘（运行中任务挂载的 Agent 镜像盘，名称固定前缀），
    # 否则会干扰系统盘识别、破坏 系统盘↔系统盘 顺序（SMS.0515 高危）。
    pre_filter = [v for v in vols if not v["name"].startswith("SMS_Temp_Disk")]
    if pre_filter:
        vols = pre_filter
    else:
        raise ConfigError("目的端除 SMS 临时盘外无业务卷，无法建磁盘映射")

    # 系统盘（目标端根设备识别）
    ecs_meta = {}
    try:
        data = client.call("ECS", "ListServersDetails", {"limit": 1000})
        for sv in data.get("servers") or []:
            if sv.get("id") == vm_id:
                ecs_meta = sv
                break
    except Exception:
        pass
    root_dev = ecs_meta.get("OS-EXT-SRV-ATTR:root_device_name") or "/dev/vda"
    # 系统盘识别优先级：根设备名 → EVS bootable=true → 设备名最小（vda）。
    # 注意：迁移运行中会多一块 SMS 临时盘（已在上一步过滤），避免误判。
    tgt_sys = next((v for v in vols if v["device"] == root_dev), None)
    if tgt_sys is None:
        tgt_sys = next((v for v in vols if v.get("bootable")), None)
    if tgt_sys is None:
        tgt_sys = vols[0]
    tgt_data = [v for v in vols if v["volumeId"] != tgt_sys["volumeId"]]

    src_sys = next((d for d in src_disks
                    if (d.get("device_use") or "").upper() in ("OS", "BOOT") or d.get("os_disk")), src_disks[0])
    src_data = [d for d in src_disks if d is not src_sys]

    if len(src_data) != len(tgt_data):
        raise ConfigError(
            f"数据盘数量不匹配：源端 {len(src_data)} 块，目的端 {len(tgt_data)} 块。"
            "请先在目的端补挂数据盘（数据盘对数据盘）后再创建任务。",
        )

    # 数据盘按容量精确配对（多盘防错配）
    src_data_sorted = sorted(src_data, key=lambda d: int(d.get("size") or 0))
    tgt_data_sorted = sorted(tgt_data, key=lambda v: v["size_gb"] * 1024**3)
    mapping = [(src_sys, tgt_sys)]  # 系统盘在前（与官方示例/源端顺序一致）
    if src_data:
        for sd, tv in zip(src_data_sorted, tgt_data_sorted):
            s_gb = int((sd.get("size") or 0) / 1024**3)
            t_gb = tv["size_gb"]
            if t_gb < s_gb:
                raise ConfigError(
                    f"数据盘容量不足：源端 {s_gb}GB，目的端 {t_gb}GB（{tv['device']}）。"
                    "同序配对后目标盘容量必须 >= 源端（防止 60G对40G 类错配）。",
                )
            mapping.append((sd, tv))
    sys_gb = int((src_sys.get("size") or 0) / 1024**3)
    tgt_sys_gb = tgt_sys["size_gb"]
    if tgt_sys_gb < sys_gb:
        raise ConfigError(f"系统盘容量不足：目的端 {tgt_sys_gb}GB < 源端 {sys_gb}GB")

    # 【顺序契约断言】mapping[0] 必须是系统盘（disk.1）；否则直接报错，禁止带错序创建
    if (mapping[0][0].get("device_use") or "").upper() not in ("OS", "BOOT") and not mapping[0][0].get("os_disk"):
        raise ConfigError("磁盘映射顺序错误：disks.1 应为系统盘，编码异常，已拒绝创建")

    disks_plan = []
    # 按顺序契约写 param：idx=1 系统盘；idx>=2 数据盘（容量升序）
    # 序号的物理意义 = KooCLI/API 的 disks.N，直接影响 SMS 对磁盘归属的判定，严禁 reorder
    for idx, (sd, tv) in enumerate(mapping, start=1):
        base = f"target_server.disks.{idx}"
        params[f"{base}.name"] = _escape_hcloud(sd.get("name") or f"disk {idx-1}")
        params[f"{base}.disk_id"] = tv["volumeId"]
        if sd.get("size") is not None:
            params[f"{base}.size"] = sd["size"]
        if sd.get("used_size") is not None:
            params[f"{base}.used_size"] = sd["used_size"]
        if sd.get("device_use"):
            params[f"{base}.device_use"] = sd["device_use"]
        pvs = sd.get("physical_volumes") or []
        for j, pv in enumerate(pvs, start=1):
            pb = f"{base}.physical_volumes.{j}"
            if pv.get("name"):
                params[f"{pb}.name"] = _escape_hcloud(pv["name"])
            if pv.get("device_use"):
                params[f"{pb}.device_use"] = pv["device_use"]
            if pv.get("size") is not None:
                params[f"{pb}.size"] = pv["size"]
            if pv.get("used_size") is not None:
                params[f"{pb}.used_size"] = pv["used_size"]
            if pv.get("uuid"):
                params[f"{pb}.uuid"] = _escape_hcloud(pv["uuid"])
            if pv.get("file_system"):
                params[f"{pb}.file_system"] = pv["file_system"]
            if pv.get("index") is not None:
                params[f"{pb}.index"] = pv["index"]
            if pv.get("mount_point"):
                params[f"{pb}.mount_point"] = _escape_hcloud(pv["mount_point"])
        vgs = sd.get("volume_groups") or []
        for j, vg in enumerate(vgs, start=1):
            vb = f"{base}.volume_groups.{j}"
            if vg.get("name"):
                params[f"{vb}.name"] = _escape_hcloud(vg["name"])
            if vg.get("size") is not None:
                params[f"{vb}.size"] = vg["size"]
            if vg.get("free_size") is not None:
                params[f"{vb}.free_size"] = vg["free_size"]
        disks_plan.append((idx, sd.get("name"), sd.get("device_use"), tv["volumeId"],
                           tv["device"], tv["size_gb"], len(pvs)))
    logger.info("磁盘映射（源→目的，容量对齐）: %s", disks_plan)


def cmd_templates(cfg, client, args):
    """创建新服务器模式: 罗列可用虚拟机配置模板（只读）。"""
    data = client.list_templates()
    rows = []
    for t in data.get("templates") or []:
        nics = t.get("nics") or []
        sgs = t.get("security_groups") or []
        rows.append({
            "id": t.get("id"),
            "name": t.get("name"),
            "az": t.get("availability_zone") or "",
            "flavor": t.get("flavor") or "",
            "vpc": (t.get("vpc") or {}).get("name") or "",
            "subnet": nics[0].get("name") if nics else "",
            "security_group": sgs[0].get("name") if sgs else "",
            "region": t.get("region") or "",
        })
    _out({"count": len(rows), "templates": rows})


def cmd_create(cfg, client, args):
    """步骤二: 设置迁移目的端 → 创建迁移任务。"""
    source = _resolve_source(cfg, client, args)
    if not args.force:
        existing = client.find_task(source["id"])
        if existing:
            raise SmsApiError(
                f"源端 {source['id']} 下已有迁移任务，幂等保护拒绝重复创建: "
                f"{existing.get('id')} (state={existing.get('state')})；确需重来请 --force",
                detail={"existing_task": existing},
            )
    params = _build_create_params(cfg, client, source, args)
    prompt = (f"创建迁移任务: name={params['name']} | 源端={params['source_server.id']} "
              f"| 模式={cfg.sms_task.target_mode} | 目的端={params.get('target_server.name')} "
              f"vm_id={params.get('target_server.vm_id') or params.get('vm_template_id') or '-'}")
    if not _confirm(prompt, args.yes):
        raise SmsApiError("用户取消创建")
    data = client.create_task(params)
    task_id = data.get("id") or data.get("task_id") or ""
    if task_id:
        record_owned(PROJECT_ROOT, "task", task_id, params.get("name", ""), _owner_id_of(cfg, client))
    _out({"action": "create", "task_id": task_id, "params": params, "resp": data})


def cmd_start(cfg, client, args):
    """步骤三: 开始服务器全量复制。"""
    task_id = _task_id(cfg, client, args)
    _require_task_owned(cfg, client, task_id, "start")
    if not _confirm(f"启动迁移任务 {task_id} 的全量复制?", args.yes):
        raise SmsApiError("用户取消启动")
    data = client.update_task_status(task_id, "start")
    _out({"action": "start", "task_id": task_id, "resp": data})


def cmd_stop(cfg, client, args):
    """暂停/停止当前迁移任务（UpdateTaskStatus operation=stop）。"""
    task_id = _task_id(cfg, client, args)
    _require_task_owned(cfg, client, task_id, "stop")
    if not _confirm(f"停止迁移任务 {task_id}？（停止复制，可后续处理）", args.yes):
        raise SmsApiError("用户取消停止")
    data = client.update_task_status(task_id, "stop")
    _out({"action": "stop", "task_id": task_id, "resp": data})


def cmd_status(cfg, client, args):
    """状态/进度（只读）。"""
    task_id = _task_id(cfg, client, args)
    data = client.show_task(task_id)
    _out({"task_id": task_id, "task": data})


def cmd_wait(cfg, client, args):
    """轮询等待任务到达目标状态（默认 SYNCING，持续同步模式下全量复制完成的标志）。"""
    task_id = _task_id(cfg, client, args)
    target = args.target_state.upper()
    deadline = time.time() + args.timeout
    while time.time() < deadline:
        data = client.show_task(task_id)
        state = (data.get("state") or "").upper()
        cycle = data.get("migration_cycle") or ""
        logger.info("[wait] task=%s state=%s cycle=%s", task_id, state, cycle)
        if state in _TERMINAL_FAIL:
            raise SmsApiError(f"任务失败（state={state}）", detail={"task": data})
        if state == target or state in _TERMINAL_OK or (target == "SYNCING" and state == "SYNCING"):
            _out({"task_id": task_id, "state": state, "migration_cycle": cycle, "task": data})
            return
        time.sleep(cfg.sms_task.poll_interval_s)
    raise SmsApiError(f"等待超时({args.timeout}s)：state={state or 'unknown'}")


def cmd_sync(cfg, client, args):
    """步骤四: 同步增量数据（KooCLI 7.2.x 兼容）。

    KooCLI 7.2.x 的 UpdateTaskStatus 枚举不含 syncing（见 UPDATE_TASK_STATUS_OPS）：
    config 默认 syncing=false，全量复制完成即 MIGRATE_SUCCESS，无需增量同步，
    任务已成功时直接跳过（skipped=true），避免流程中断。
    显式 --operation 透传仍按原样调用（兼容支持该枚举的新 KooCLI/API）。
    """
    task_id = _task_id(cfg, client, args)
    _require_task_owned(cfg, client, task_id, "sync")
    op = args.operation or "syncing"
    # 显式透传且 KooCLI 支持 → 直接调用
    if op in UPDATE_TASK_STATUS_OPS:
        if not _confirm(f"对任务 {task_id} 执行同步 (operation={op})?", args.yes):
            raise SmsApiError("用户取消同步")
        data = client.update_task_status(task_id, op)
        _out({"action": "sync", "task_id": task_id, "operation": op, "resp": data})
        return
    # syncing 不在枚举：优先尝试调用（兼容新版本），仅当枚举类错误时回退跳过
    try:
        if not _confirm(f"对任务 {task_id} 执行增量同步 (operation={op})?", args.yes):
            raise SmsApiError("用户取消同步")
        data = client.update_task_status(task_id, op)
        _out({"action": "sync", "task_id": task_id, "operation": op, "resp": data})
    except SmsApiError as e:
        hint = str(e)
        if "USE_ERROR" not in hint and "不支持" not in hint and "operation" not in hint:
            raise
        st = client.show_task(task_id)
        rstate = (st.get("state") or "").upper()
        if rstate in _TERMINAL_OK:
            reason = f"KooCLI {op} 枚举不支持；任务已是 {rstate}（syncing=false 全量模式），无需增量同步"
            logger.warning("%s: %s", reason, str(e)[:160])
            _out({"action": "sync", "task_id": task_id, "operation": op,
                  "skipped": True, "reason": reason, "task": st})
            return
        raise


def cmd_cutover(cfg, client, args):
    """启动目的端（等效割接，KooCLI 7.2.x 兼容）。

    KooCLI 7.2.x 的 UpdateTaskStatus 枚举不含 cutover；
    回退逻辑 = 校验任务非失败 → 用 ECS BatchStartServers 启动目的端（= 退出持续同步并开机）。
    """
    task_id = _task_id(cfg, client, args)
    _require_task_owned(cfg, client, task_id, "cutover")
    if not _confirm(f"启动目的端 (任务 {task_id})? 请先确认源端业务已停止!", args.yes):
        raise SmsApiError("用户取消启动目的端")
    # 1) 优先尝试官方 cutover（新 KooCLI/API 支持时走标准流程）
    try:
        data = client.update_task_status(task_id, "cutover")
        _out({"action": "cutover", "task_id": task_id, "operation": "cutover", "resp": data})
        return
    except SmsApiError as e:
        hint = str(e)
        if "USE_ERROR" not in hint and "不支持" not in hint and "operation" not in hint:
            raise
        logger.warning("KooCLI 不支持 operation=cutover，回退为“启动目的端 ECS”（等效割接）: %s", str(e)[:160])
    # 2) 回退：校验任务非失败终态 → 启动目的端 ECS
    st = client.show_task(task_id)
    rstate = (st.get("state") or "").upper()
    logger.info("任务 %s 当前 state=%s", task_id, rstate)
    if rstate in _TERMINAL_FAIL:
        raise SmsApiError(f"任务失败（state={rstate}），禁止启动目的端")
    vm_id = args.target_vm_id or cfg.sms_task.target_vm_id or load_target_state().get("vm_id", "")
    if not vm_id:
        raise ConfigError("回退割接需要目的端 ECS ID：--target-vm-id / sms_task.target_vm_id / 先执行 prepare-target")
    data = client.ecs_start(vm_id)
    _out({"action": "cutover", "task_id": task_id, "mode": "fallback:start-ecs",
          "operation": "cutover", "vm_id": vm_id, "task_state": rstate, "resp": data})


def cmd_cleanup(cfg, client, args):
    """步骤五: 清理快照资源（不可逆，删除割接/同步快照）。"""
    task_id = _task_id(cfg, client, args)
    _require_task_owned(cfg, client, task_id, "cleanup")
    if not _confirm(f"清理迁移任务 {task_id} 的快照资源？清理后无法再增量同步（不可逆）!", args.yes):
        raise SmsApiError("用户取消清理")
    data = client.update_task_status(task_id, "clear")
    _out({"action": "cleanup", "task_id": task_id, "resp": data})


def cmd_delete(cfg, client, args):
    """删除迁移任务（不可逆）。"""
    task_id = _task_id(cfg, client, args)
    _require_task_owned(cfg, client, task_id, "delete")
    if not _confirm(f"删除迁移任务 {task_id}？（不可逆）", args.yes):
        raise SmsApiError("用户取消删除")
    data = client.delete_task(task_id)
    _out({"action": "delete", "task_id": task_id, "resp": data})


def cmd_release(cfg, client, args):
    """资源回收（用后即还，防浪费）: release-eip / release-sg。

    - release-eip <id>: 校验属主且未绑定 → 删除属主 EIP 并从清单移除
    - release-sg  <id>: 校验属主 → 删除属主安全组并从清单移除
    仅限属主资源；非属主拒绝；删除需交互确认（--yes 跳过）。
    """
    owner_id = _owner_id_of(cfg, client)
    rid = args.resource_id.strip()
    kind = args.resource_type
    if kind == "eip":
        eips = client.call("EIP", "ListPublicips", {"id": [rid]}, with_project=True).get("publicips") or []
        if not eips:
            # 资源不存在但清单有？给明确提示
            _out({"action": "release-eip", "resource_id": rid, "status": "not_found"})
            return
        eip = eips[0]
        require_owned(PROJECT_ROOT, eip, owner_id, rtype="eip", action="release(delete)")
        if eip.get("associate_instance_id"):
            raise SmsApiError(f"EIP {rid} 仍绑定中（{eip.get('associate_instance_id')}），"
                              "请先解绑或确认业务不再使用后再回收")
        if not _confirm(f"删除属主 EIP {rid} ({eip.get('public_ip_address') or '-'})？", args.yes):
            raise SmsApiError("用户取消回收 EIP")
        client.call("EIP", "DeletePublicip", {"publicip_id": rid}, with_project=True, timeout=180)
        remove_owned(PROJECT_ROOT, rid, owner_id)
        _out({"action": "release-eip", "resource_id": rid, "status": "deleted"})
    elif kind == "sg":
        sgs = client.call("VPC", "ListSecurityGroups/v3", {}).get("security_groups") or []
        sg = next((g for g in sgs if g.get("id") == rid), None)
        if not sg:
            _out({"action": "release-sg", "resource_id": rid, "status": "not_found"})
            return
        require_owned(PROJECT_ROOT, sg, owner_id, rtype="sg", action="release(delete)")
        if not _confirm(f"删除属主安全组 {rid} ({sg.get('name') or '-'})？", args.yes):
            raise SmsApiError("用户取消回收安全组")
        client.call("VPC", "DeleteSecurityGroup/v3", {"security_group_id": rid},
                    with_project=True, timeout=180)
        remove_owned(PROJECT_ROOT, rid, owner_id)
        _out({"action": "release-sg", "resource_id": rid, "status": "deleted"})
    else:
        raise ConfigError("--resource-type 仅支持 eip / sg")


def cmd_pipeline(cfg, client, args):
    """可编排: 按 --steps 顺序执行（默认 discover,create,start,wait）。"""
    steps = [s.strip() for s in args.steps.split(",") if s.strip()]
    results = {}
    for step in steps:
        logger.info("===== pipeline step: %s =====", step)
        handler = {
            "discover": cmd_discover, "templates": cmd_templates,
            "prepare-target": cmd_prepare_target,
            "create": cmd_create, "start": cmd_start, "stop": cmd_stop,
            "status": cmd_status, "wait": cmd_wait, "sync": cmd_sync,
            "cutover": cmd_cutover, "cleanup": cmd_cleanup, "delete": cmd_delete,
            "ecs-list": cmd_ecs_list,
        }.get(step)
        if handler is None:
            raise ConfigError(f"pipeline 未知步骤: {step}")
        try:
            handler(cfg, client, args)
            results[step] = "ok"
        except MigrationError as e:
            results[step] = f"fail: {e.message}"
            raise
    _out({"pipeline": results, "steps": steps})


def main() -> int:
    parser = argparse.ArgumentParser(
        description="SMS 控制面迁移任务编排 — 步骤二~五（Windows / 目标端已有服务器优先）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="示例见文件头注释。所有变更操作需 --yes 或交互确认。",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    def add_common(p):
        p.add_argument("--config", default="config/migrate.yaml", help="配置文件路径")
        p.add_argument("--json", action="store_true", dest="json_output", help="JSON 输出")
        p.add_argument("--yes", action="store_true", help="跳过交互确认")
        p.add_argument("--source-ip", default="", help="覆盖源端 IP 发现")
        p.add_argument("--task-id", default="", help="指定迁移任务 ID（默认按源端自动查找）")

    p = sub.add_parser("discover", help="发现源端服务器（只读）"); add_common(p)
    p = sub.add_parser("ecs-list", help="罗列目的端候选 ECS（只读）")
    add_common(p); p.add_argument("--ecs-name", default="", help="按名称过滤 ECS")
    p = sub.add_parser("prepare-target", help="自动创建目的端 ECS+网络+安全组+EIP")
    add_common(p)
    p.add_argument("--dry-run", action="store_true", help="只解析计划，不创建任何资源")
    p = sub.add_parser("templates", help="罗列可用 VM 模板（new 模式选型，只读）"); add_common(p)

    p = sub.add_parser("create", help="步骤二: 创建迁移任务（设置目的端）")
    add_common(p)
    p.add_argument("--name", default="", help="覆盖任务名称")
    p.add_argument("--target-name", default="", help="覆盖目的端名称")
    p.add_argument("--target-vm-id", default="", help="覆盖目的端 ECS ID（existing 模式）")
    p.add_argument("--migration-ip", default="", help="覆盖目的端 EIP（existing+公网）")
    p.add_argument("--vm-template-id", default="", help="覆盖自动创建模板 ID（new 模式）")
    p.add_argument("--no-start", action="store_true", help="创建后不自动开始迁移")
    p.add_argument("--force", action="store_true", help="源端已有任务时仍创建")

    p = sub.add_parser("start", help="步骤三: 开始全量复制"); add_common(p)
    p = sub.add_parser("stop", help="暂停/停止迁移任务"); add_common(p)
    p = sub.add_parser("status", help="查询任务状态/进度（只读）"); add_common(p)
    p = sub.add_parser("wait", help="轮询等待任务到目标状态")
    add_common(p)
    p.add_argument("--target-state", default="SYNCING", help="目标状态（默认 SYNCING）")
    p.add_argument("--timeout", type=int, default=14400, help="最长等待秒数")

    p = sub.add_parser("sync", help="步骤四: 同步增量数据"); add_common(p)
    p.add_argument("--operation", default="", help="透传 operation（默认 syncing）")
    p = sub.add_parser("cutover", help="启动目的端（持续同步退出+开机）"); add_common(p)
    p.add_argument("--target-vm-id", default="", help="回退割接时指定目的端 ECS ID（默认取 target_state.json / sms_task.target_vm_id）")
    p = sub.add_parser("cleanup", help="步骤五: 清理快照资源（不可逆）"); add_common(p)
    p = sub.add_parser("release", help="回收属主资源（用后即还）")
    add_common(p)
    p.add_argument("--resource-type", required=True, choices=["eip", "sg"], help="回收资源类型")
    p.add_argument("--resource-id", required=True, help="资源 ID")
    p = sub.add_parser("delete", help="删除迁移任务（不可逆）"); add_common(p)

    p = sub.add_parser("pipeline", help="可编排执行多个步骤")
    add_common(p)
    p.add_argument("--steps", default="discover,create,start,wait", help="逗号分隔步骤序列")
    p.add_argument("--target-state", default="SYNCING", help="wait 目标状态")
    p.add_argument("--timeout", type=int, default=14400, help="wait 最长等待秒数")

    args = parser.parse_args()

    cfg_path = Path(args.config)
    if not cfg_path.is_absolute():
        cfg_path = PROJECT_ROOT / cfg_path
    try:
        cfg = ConfigLoader.load(cfg_path)
    except Exception as e:
        if getattr(args, "json_output", False):
            _out({"exit_code": 2, "success": False, "error": str(e)})
        else:
            print(f"配置加载失败: {e}", file=sys.stderr)
        return 2

    setup_logging(cfg.logging.level, cfg.logging.dir, json_mode=getattr(args, "json_output", False))
    client = _client(cfg)

    try:
        handler = {
            "discover": cmd_discover, "ecs-list": cmd_ecs_list,
            "prepare-target": cmd_prepare_target, "templates": cmd_templates,
            "create": cmd_create,
            "start": cmd_start, "stop": cmd_stop,
            "status": cmd_status, "wait": cmd_wait, "release": cmd_release,
            "sync": cmd_sync, "cutover": cmd_cutover, "cleanup": cmd_cleanup,
            "delete": cmd_delete, "pipeline": cmd_pipeline,
        }[args.cmd]
        handler(cfg, client, args)
        return 0
    except MigrationError as e:
        if getattr(args, "json_output", False):
            _out({"exit_code": 1, "success": False, **e.to_dict()})
        else:
            print(f"执行失败: [{e.error_code}] {e.message}", file=sys.stderr)
        return 1
    except Exception as e:
        if getattr(args, "json_output", False):
            _out({"exit_code": 1, "success": False, "error_type": type(e).__name__, "error": str(e)})
        else:
            print(f"执行异常: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())