#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""校验 ModelArts 部署产物的可用性(硬性 FAIL)与性能(软性 WARN)。

可用性: 文件齐全、LF 行尾、bash 语法、启动命令用 bash、权重自检、端口/探针一致、
多节点/PD 适配、相对路径定位、角色专属参数归属。
性能: 对照 --doc-params 模型文档推荐参数与昇腾环境变量,提示缺失项。
退出码: 0=全通过, 1=有 FAIL, 2=参数错误
"""

import argparse
import json
import os
import re
import subprocess
import sys

# ---------- 检查项定义 ----------
# 可用性检查(硬性): (编号, 标题, 检查函数)
HARD_CHECKS = []

# 性能检查(软性): (编号, 标题, 检查函数)
SOFT_CHECKS = []

# 自检结果计数(_fail/_warn 调用即计数,main() 每次运行前重置)
FAIL_COUNT = 0
WARN_COUNT = 0


def _read(path):
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def _fail(msg):
    global FAIL_COUNT
    FAIL_COUNT += 1
    print(f"  [FAIL] {msg}")


def _warn(msg):
    global WARN_COUNT
    WARN_COUNT += 1
    print(f"  [WARN] {msg}")


def _pass(msg=""):
    print(f"  [PASS] {msg}" if msg else "  [PASS]")


# ---------- 可用性检查(硬性) ----------

def c01_file_completeness(ctx):
    """1.1 产物文件齐全。"""
    art_dir = ctx["artifact_dir"]
    deploy_form = ctx["deploy_form"]
    dp_size = ctx.get("dp_size") or 1
    need = ["start_vllm.sh", "health_check.sh"]
    # DP>1(多实例)时需要 get_master_ip.py 做 rank table 主从判定;
    # DP=1(单实例)时 start_vllm.sh 与 health_check.sh 的 get_master_ip 调用均被
    # DATA_PARALLEL_SIZE>1 条件包裹跳过,不需要该文件(见 SKILL.md 3.3 探针行为与 3.4 复制规则)。
    if dp_size > 1:
        need.append("get_master_ip.py")
    # PD 分离部署需要 load_balance_proxy_server_example.py(proxy 角色启动脚本)
    if deploy_form == "pd":
        need.append("load_balance_proxy_server_example.py")
    missing = [f for f in need if not os.path.isfile(os.path.join(art_dir, f))]
    if missing:
        return _fail(f"产物目录 {art_dir} 缺少文件: {', '.join(missing)}"
                     f"(部署形式 {deploy_form} DP={dp_size} 需要 {', '.join(need)})")
    _pass(f"产物文件齐全: {', '.join(need)} (DP={dp_size})")


def c02_lf_line_ending(ctx):
    """1.2 LF 行尾(禁 CRLF,否则 bash 报 $'\\r': command not found)。"""
    art_dir = ctx["artifact_dir"]
    bad = []
    for root, _, files in os.walk(art_dir):
        for f in files:
            if f.endswith(".sh") or f.endswith(".py"):
                p = os.path.join(root, f)
                with open(p, "rb") as fh:
                    if b"\r\n" in fh.read():
                        bad.append(f)
    if bad:
        return _fail(f"存在 CRLF 行尾: {', '.join(bad)}。转 LF 后重新校验。")
    _pass("全部 .sh/.py 文件为 LF 行尾")


def c03_bash_syntax(ctx):
    """1.3 bash -n 语法检查。"""
    art_dir = ctx["artifact_dir"]
    for f in ("start_vllm.sh", "health_check.sh"):
        p = os.path.join(art_dir, f)
        if not os.path.isfile(p):
            continue
        # Windows(Git Bash)下 bash 不识别盘符绝对路径(如 O:/...),先 cd 到
        # 产物目录再用相对文件名执行 bash -n
        r = subprocess.run(["bash", "-n", f], capture_output=True, text=True,
                           cwd=art_dir)
        if r.returncode != 0:
            return _fail(f"{f} bash 语法错误: {r.stderr.strip()}")
    _pass("start_vllm.sh / health_check.sh 通过 bash -n 语法检查")


def c04_bash_array_not_sh(ctx):
    """1.4 脚本用 bash 数组(禁 sh 执行)。检查 shebang 与 MODEL_ARGS 数组。"""
    p = os.path.join(ctx["artifact_dir"], "start_vllm.sh")
    if os.path.isfile(p):
        content = _read(p)
        if "MODEL_ARGS=(" in content:
            _pass("start_vllm.sh 使用 bash 数组 MODEL_ARGS=(...)")
        else:
            _fail("start_vllm.sh 未找到 bash 数组 MODEL_ARGS=( 定义(脚本可能被 sh 执行时语法错误)")


def c05_model_weight_check(ctx):
    """1.5 权重挂载自检(检查脚本内 config.json 存在性校验)。"""
    p = os.path.join(ctx["artifact_dir"], "start_vllm.sh")
    if os.path.isfile(p):
        content = _read(p)
        if "config.json" in content and "MODEL_PATH" in content:
            _pass("start_vllm.sh 内置权重挂载自检(config.json + MODEL_PATH)")
        else:
            _fail("start_vllm.sh 缺少权重挂载自检(应检查 ${MODEL_PATH}/config.json 存在)")


def c06_port_consistency(ctx):
    """1.6 监听端口一致(默认 8080,与探针/部署配置一致)。"""
    art_dir = ctx["artifact_dir"]
    expect = str(ctx.get("expect_port", 8080))
    start = os.path.join(art_dir, "start_vllm.sh")
    health = os.path.join(art_dir, "health_check.sh")
    problems = []
    if os.path.isfile(start):
        content = _read(start)
        m = re.search(r'PORT="\$\{PORT:-(:?\d+)\}"', content)
        if m and m.group(1) != expect:
            problems.append(f"start_vllm.sh 默认 PORT={m.group(1)} != 期望 {expect}")
    if os.path.isfile(health):
        content = _read(health)
        m = re.search(r'PORT="\$\{PORT:-(:?\d+)\}"', content)
        if m and m.group(1) != expect:
            problems.append(f"health_check.sh 默认 PORT={m.group(1)} != 期望 {expect}")
    if problems:
        return _fail("; ".join(problems))
    _pass(f"启动/探针脚本默认 PORT 一致 = {expect}")


def c07_probe_cmd(ctx):
    """1.7 探针命令一致性(health_check.sh startup|readiness|liveness)。"""
    art_dir = ctx["artifact_dir"]
    health = os.path.join(art_dir, "health_check.sh")
    if not os.path.isfile(health):
        return _fail("health_check.sh 不存在")
    content = _read(health)
    for probe in ("startup", "liveness", "readiness"):
        if f'"{probe}"' not in content and f"'{probe}'" not in content and probe not in content:
            _fail(f"health_check.sh 缺少 {probe} 探针分支")
            return
    _pass("health_check.sh 包含 startup/liveness/readiness 三类探针分支")


def c08_multi_node_adaptation(ctx):
    """1.8 多实例/PD 适配: get_master_ip.py 存在且被引用,且调用被条件包裹。

    统一规则: 数据并行总数 DP>1(多实例)时需要 get_master_ip.py 做 rank table 主从判定;
    DP=1(单实例)时 start_vllm.sh 与 health_check.sh 的 get_master_ip 调用均被
    DATA_PARALLEL_SIZE>1 或 GLOBAL_RANK_TABLE_FILE_PATH 条件包裹跳过,不需要该文件
    (见 SKILL.md 3.3 探针行为与 3.4 复制规则)。
    调用未被条件包裹直接 FAIL: DP=1 时会触发 get_master_ip.py fallback 噪声 + 浪费 Python 启动开销,
    违反 SKILL.md 3.3/3.4 设计意图(应跳过而非 fallback)。
    """
    deploy_form = ctx["deploy_form"]
    art_dir = ctx["artifact_dir"]
    if deploy_form not in ("multi_node", "pd"):
        _pass("非多实例/PD 形式,跳过 master/worker 检查")
        return
    dp_size = ctx.get("dp_size") or 1
    start = os.path.join(art_dir, "start_vllm.sh")
    content = _read(start)
    # 提取实际调用行:含 python3 ... get_master_ip.py 的非注释行
    call_lines = [
        line for line in content.splitlines()
        if "get_master_ip.py" in line
        and "python3" in line
        and not line.lstrip().startswith("#")
    ]
    if dp_size <= 1:
        # DP=1 时所有 get_master_ip.py 调用必须被条件包裹:调用行所在上下文须含
        # DATA_PARALLEL_SIZE>1 或 GLOBAL_RANK_TABLE_FILE_PATH 条件判定
        unguarded = []
        for line in call_lines:
            # 检查同段(向前 15 行)是否有条件包裹
            idx = content.splitlines().index(line)
            ctx_block = "\n".join(content.splitlines()[max(0, idx-15):idx+1])
            if ("DATA_PARALLEL_SIZE" not in ctx_block
                    and "GLOBAL_RANK_TABLE_FILE_PATH" not in ctx_block):
                unguarded.append(line.strip())
        if unguarded:
            return _fail(
                f"DP={dp_size}(单实例)但 start_vllm.sh 含未被条件包裹的 get_master_ip.py 调用:"
                f" {unguarded}——调用应被 DATA_PARALLEL_SIZE>1 或 GLOBAL_RANK_TABLE_FILE_PATH 条件包裹跳过"
                f"(见 SKILL.md 3.3 探针行为与 3.4 复制规则)"
            )
        _pass(f"DP={dp_size}(单实例),get_master_ip.py 调用均被条件包裹跳过")
        return
    if "get_master_ip.py" not in content:
        return _fail(f"{deploy_form} DP={dp_size}>1 但 start_vllm.sh 未引用 get_master_ip.py")
    if not os.path.isfile(os.path.join(art_dir, "get_master_ip.py")):
        return _fail(f"start_vllm.sh 引用 get_master_ip.py 但产物目录缺少该文件(DP={dp_size}>1)")
    _pass(f"DP={dp_size}>1,get_master_ip.py 存在且被 start_vllm.sh 引用")


def c09_pd_role_adaptation(ctx):
    """1.9 PD 分离: VLLM_ROLE 角色分支与不同 PORT。"""
    deploy_form = ctx["deploy_form"]
    if deploy_form != "pd":
        _pass("非 PD 分离形式,跳过 VLLM_ROLE 检查")
        return
    start = os.path.join(ctx["artifact_dir"], "start_vllm.sh")
    content = _read(start)
    if "VLLM_ROLE" not in content:
        return _fail("pd(PD 分离)部署形式但 start_vllm.sh 未包含 VLLM_ROLE 角色分支")
    _pass("start_vllm.sh 包含 VLLM_ROLE 角色分支(proxy/prefill/decode)")


def c10_relative_path(ctx):
    """1.10 脚本内文件引用相对定位(禁硬编码 /code/)。"""
    art_dir = ctx["artifact_dir"]
    bad = []
    for f in ("start_vllm.sh", "health_check.sh"):
        p = os.path.join(art_dir, f)
        if not os.path.isfile(p):
            continue
        content = _read(p)
        # 只检查非注释行的硬编码路径(注释中的"/code/"(如"禁止硬编码 /code/")
        # 是说明文字,不算违规)
        for line in content.splitlines():
            line_stripped = line.strip()
            if not line_stripped or line_stripped.startswith("#"):
                continue
            if re.search(r'(?<![A-Za-z])/code/(?!health_check|start_vllm|get_master_ip)', line):
                bad.append(f)
                break
    if bad:
        return _fail(f"{', '.join(bad)} 存在硬编码路径(/code/ 等),必须用 $(dirname \"$0\") 相对定位")
    _pass("脚本内文件引用使用相对定位")


def _normalize_json_value(val):
    """规范化 JSON 值用于跨字面差异匹配。

    脚本中 JSON 参数常以 bash 单引号包裹 + 内部双引号 + 空格形式出现
    (如 --speculative-config '{"method": "qwen3_5_mtp", ...}'),
    而 --doc-params 传入的 JSON 字符串可能无空格/引号顺序不同,
    字面子串匹配会误判 FAIL。规范化为去空格 + 去引号后的 token 集合。
    """
    if not isinstance(val, str) or not val:
        return val
    try:
        parsed = json.loads(val)
        return json.dumps(parsed, sort_keys=True, separators=(",", ":"))
    except (json.JSONDecodeError, TypeError):
        return val.strip()


def _extract_script_json_values(content, key):
    """从脚本内容提取 key 对应的 JSON 字面值(支持单/双引号包裹)。

    匹配 `--key '{...}'` 或 `--key "{...}"` 或 `--key={...}` 形式,
    返回规范化后的 JSON 字符串列表(无匹配时返回空列表)。
    """
    values = []
    # 匹配 --key 后跟单引号或双引号包裹的 JSON 对象/数组
    pattern = rf'{re.escape(key)}\s+[\'"]({{\s*.*?\s*}}|\[\s*.*?\s*\])[\'"]'
    for m in re.finditer(pattern, content, re.DOTALL):
        values.append(_normalize_json_value(m.group(1)))
    # 匹配 --key={...} 形式
    pattern_eq = rf'{re.escape(key)}=([\'"]?)({{\s*.*?\s*}}|\[\s*.*?\s*\])\1'
    for m in re.finditer(pattern_eq, content, re.DOTALL):
        values.append(_normalize_json_value(m.group(2)))
    return values


def c11_doc_params_hard(ctx):
    """1.11 模型文档必备参数齐全(经 --doc-params 传入)。

    JSON 值匹配采用规范化比较(去空格 + 去引号顺序差异),
    避免 --doc-params 传入的 JSON 字面空格/引号与脚本中不一致导致误判 FAIL。
    """
    doc_params = ctx.get("doc_params") or {}
    if not doc_params:
        _pass("未提供 --doc-params,跳过模型文档参数对照(建议提供)")
        return
    start = os.path.join(ctx["artifact_dir"], "start_vllm.sh")
    content = _read(start)
    missing = []
    for key, val in doc_params.items():
        if key not in content:
            missing.append(f"{key}={val}")
            continue
        if not (isinstance(val, str) and val):
            continue
        # JSON 值: 规范化后比较(脚本中提取的 JSON 值 vs --doc-params 传入值)
        if val.lstrip().startswith(("{", "[")):
            script_values = _extract_script_json_values(content, key)
            normalized_val = _normalize_json_value(val)
            if normalized_val not in script_values:
                missing.append(f"{key}={val}")
        else:
            if val not in content:
                missing.append(f"{key}={val}")
    if missing:
        return _fail(f"模型文档推荐参数在脚本中缺失: {', '.join(missing)}"
                     f"(对照 {ctx.get('model_doc_url', '模型文档')})")
    _pass("模型文档推荐参数已全部包含在脚本中")


def c12_tp_size_match(ctx):
    """1.12 TP_SIZE 与文档推荐/资源规格一致(硬性)。

    根因: single/pd 模板 TP_SIZE 默认从 ASCEND_RT_VISIBLE_DEVICES 推导,
    ModelArts 注入单卡(如 "0")时推导为 TP=1,大模型权重装不进单卡显存,
    KV cache 为负 → 启动崩溃(ValueError: No available memory for the cache blocks)。
    multi_node 模板用 TENSOR_PARALLEL_SIZE 变量名,single/pd 用 TP_SIZE,
    旧 S03 正则只匹配 TENSOR_PARALLEL_SIZE,对 TP_SIZE 静默跳过。

    检查逻辑: 同时匹配两种变量名,若提供 --tp-size 则要求脚本默认值一致(FAIL);
    若脚本默认值是从 ASCEND_RT_VISIBLE_DEVICES 推导(非固定数字),则 FAIL 要求改为固定值。
    若提供 --num-attention-heads(模型注意力头数),则要求 TP 能被头数整除(FAIL),
    否则 vLLM 启动硬校验崩溃(实测: Qwen3.8-27B 头数 24 + TP=16 → 24%16≠0 →
    ValueError: Total number of attention heads (24) must be divisible by tensor
    parallel size,master/worker 全部崩溃)。
    """
    tp = ctx.get("tp_size")
    heads = ctx.get("attention_heads")
    start = os.path.join(ctx["artifact_dir"], "start_vllm.sh")
    if not os.path.isfile(start):
        return
    content = _read(start)
    # 匹配两种变量名: TP_SIZE="${TP_SIZE:-N}" 或 TENSOR_PARALLEL_SIZE="${TENSOR_PARALLEL_SIZE:-N}"
    # 用 [^}]+ 匹配到 } 为止(动态推导值含空格/$(...),\S+ 会在空格处截断导致不匹配)
    m = re.search(r'(?:TP_SIZE|TENSOR_PARALLEL_SIZE)="\$\{(?:TP_SIZE|TENSOR_PARALLEL_SIZE):-([^}]+)\}"', content)
    if not m:
        return _fail("start_vllm.sh 未找到 TP_SIZE/TENSOR_PARALLEL_SIZE 变量定义")
    default_val = m.group(1)
    # 若默认值是动态推导(非纯数字),如 $(echo "${ASCEND_RT_VISIBLE_DEVICES}" ...)
    if not default_val.isdigit():
        return _fail(
            f"TP_SIZE 默认值为动态推导('{default_val}'),"
            f"ModelArts 注入 ASCEND_RT_VISIBLE_DEVICES 可能只给单卡导致 TP=1,"
            f"大模型权重装不进单卡显存 → KV cache 为负 → 启动崩溃。"
            f"必须改为模型文档推荐的固定值(如 2/4/8)"
        )
    # 若提供了 --tp-size,要求脚本默认值一致
    if tp is not None and int(default_val) != tp:
        return _fail(
            f"TP_SIZE 默认值={default_val} != 文档推荐/期望 TP={tp}。"
            f"TP_SIZE 直接决定模型权重能否放进显存(权重/TP ≤ 单卡显存),"
            f"不一致会导致 OOM 或 KV cache 为负崩溃"
        )
    # 若提供了 --num-attention-heads,要求 TP 能被头数整除(模型架构硬约束)
    # 头数 % TP == 0 才合法(TP 必须是头数的约数)
    if heads is not None and heads % int(default_val) != 0:
        return _fail(
            f"TP_SIZE={default_val} 不能被模型注意力头数({heads})整除,"
            f"vLLM 启动硬校验失败(实测 Qwen3.8-27B 头数 24 + TP=16 → "
            f"ValueError: Total number of attention heads (24) must be divisible "
            f"by tensor parallel size,master/worker 全部崩溃)。"
            f"TP 必须取头数的约数(如头数 24 → TP ∈ 2/4/6/8/12/24),"
            f"且不超过单节点卡数"
        )
    _pass(f"TP_SIZE 默认值={default_val}" + (f"(与文档推荐 TP={tp} 一致)" if tp else ""))


def c13_role_specific_args(ctx):
    """1.13 角色专属参数归属校验(仅 master 命令有、worker 命令没有的参数,
    禁止放入所有节点共享的 MODEL_ARGS 数组)。

    根因: 非 single 形式(multi_node/pd)场景下各节点运行同一脚本,worker 节点由模板自动追加
    --headless;若共享的 MODEL_ARGS 数组混入 master 专属参数(如
    --api-server-count 1),worker 同时获得两者,vllm 参数校验直接拒绝
    (ValueError: --api-server-count=1 cannot be used with --headless),
    worker 在参数解析阶段崩溃,部署失败。

    黑名单: --api-server-count、--nnodes、--node-rank、--master-addr、
    --master-port。--headless 由模板 WORKER_OPTS 自动处理,不在检查范围。
    """
    deploy_form = ctx["deploy_form"]
    if deploy_form not in ("multi_node", "pd"):
        _pass("非多实例/PD 形式,跳过角色专属参数归属校验")
        return
    start = os.path.join(ctx["artifact_dir"], "start_vllm.sh")
    if not os.path.isfile(start):
        _fail("start_vllm.sh 不存在,无法校验 MODEL_ARGS")
        return
    content = _read(start)
    m = re.search(r'MODEL_ARGS=\((.*?)\)', content, re.S)
    if not m:
        _fail("start_vllm.sh 未找到 MODEL_ARGS=(...) 数组定义")
        return
    # 数组内容按行拆分,忽略注释行
    body_lines = [ln.strip() for ln in m.group(1).splitlines()
                  if ln.strip() and not ln.strip().startswith("#")]
    body_text = " ".join(body_lines)
    blacklist = ["--api-server-count", "--nnodes", "--node-rank",
                 "--master-addr", "--master-port"]
    found = [b for b in blacklist if re.search(rf'{re.escape(b)}(\s|=|$)', body_text)]
    if found:
        return _fail(
            f"MODEL_ARGS 数组包含角色专属参数: {', '.join(found)}。"
            f"角色专属参数(仅 master 命令有)禁止放入所有节点共享的 MODEL_ARGS "
            f"数组——worker 节点会同时获得该参数与自动追加的 --headless,"
            f"vllm 参数校验拒绝(如 --api-server-count=1 cannot be used with "
            f"--headless),worker 在参数解析阶段崩溃,部署失败。"
            f"多节点场景 master 默认即 API server(--api-server-count 默认 1),"
            f"无需显式设置,请从 MODEL_ARGS 移除。"
        )
    _pass("MODEL_ARGS 未包含角色专属参数(--api-server-count/--nnodes/"
          "--node-rank/--master-addr/--master-port)")


def c14_headless_dp_lb_match(ctx):
    """1.14 --headless 与 DP LB 模式匹配(vLLM 0.23.0 默认 vs external/hybrid)。

    vLLM 0.23.0 **默认**非 external/hybrid DP LB 模式: worker **必须**追加 --headless,
    否则报 RuntimeError: Remote engine N must use --headless unless in external or
    hybrid dp lb mode(实测 vLLM 0.23.0 + multi_node 2 节点 BF16 部署触发)。
    vLLM ≥ v0.30.0rc1 启用 external/hybrid DP LB 模式时,worker 禁 --headless(报反向错误)。
    DP LB 模式由环境变量 DP_LB_MODE=external|hybrid 显式声明,与 DATA_PARALLEL_SIZE_LOCAL 无关。
    """
    deploy_form = ctx["deploy_form"]
    if deploy_form not in ("multi_node", "pd"):
        _pass("非多实例/PD 形式,跳过 --headless 与 DP LB 模式匹配校验")
        return
    start = os.path.join(ctx["artifact_dir"], "start_vllm.sh")
    if not os.path.isfile(start):
        _fail("start_vllm.sh 不存在,无法校验 --headless 与 DP LB 模式匹配")
        return
    content = _read(start)
    # 必须有 DP_LB_MODE 条件判断分支(以模板 start_vllm.multi_node.sh / start_vllm.pd.sh 为准)
    has_dp_lb_mode_check = bool(re.search(r'DP_LB_MODE="\$\{DP_LB_MODE', content))
    has_headless_in_default_branch = bool(
        re.search(r'WORKER_OPTS="--headless"', content)
        and re.search(r'DP_LB_MODE="\$\{DP_LB_MODE', content))
    has_http_server_placeholder = bool(re.search(r'python -m http\.server', content))
    if not has_dp_lb_mode_check:
        return _fail(
            "worker 分支未按 DP_LB_MODE 条件判断(以模板 start_vllm.multi_node.sh / "
            "start_vllm.pd.sh 为准)。vLLM 0.23.0 默认 DP LB 模式 worker 必须"
            "加 --headless,external/hybrid 模式禁 --headless,需通过 DP_LB_MODE "
            "环境变量区分(与 DATA_PARALLEL_SIZE_LOCAL 无关)"
        )
    if not has_headless_in_default_branch:
        return _fail(
            "默认 DP LB 模式分支未追加 --headless。vLLM 0.23.0 默认非 external/hybrid "
            "DP LB 模式: worker 必须加 --headless(实测报 RuntimeError: Remote engine N "
            "must use --headless unless in external or hybrid dp lb mode)"
        )
    if has_http_server_placeholder:
        return _fail(
            "脚本含占位 http.server——会占用 PORT 与 vLLM --master-port PP/DP 通信冲突,"
            "worker 卡在 distributed_init(详见 references/artifact-check.md H14)"
        )
    _pass(
        "--headless 按 DP_LB_MODE 条件判定(默认加,external/hybrid 不加);"
        "worker 探针改探 master /health(health_check.sh 经 get_master_ip.py 实现),禁占位 http server"
    )


def c15_quant_weight_match(ctx):
    """1.15 量化参数 × 权重文件交叉校验(硬性)。

    根因: BF16 原版权重无 quant_model_description.json,误带 --quantization ascend
    会启动崩溃(ModelSlim Quantization Config Not Found);w8a8 量化版权重含该文件,
    误漏则推理精度退化。脚本侧的运行时校验是兜底防线,本检查在产物上传前提前拦截。

    校验逻辑:
      --quantization ascend 参数来源(任一存在即视为启用):
        a) MODEL_ARGS 数组中显式出现
        b) EXTRA_ARGS/PD_EXTRA_ARGS 字符串中显式出现
        c) QUANTIZATION 环境变量驱动(multi_node 模板的 QUANT_OPTS)
      检查 start_vllm.sh 是否包含交叉校验代码段(quant_model_description.json),
      以确认模板已注入该防御。
    """
    start = os.path.join(ctx["artifact_dir"], "start_vllm.sh")
    if not os.path.isfile(start):
        return
    content = _read(start)
    if "quant_model_description.json" not in content:
        return _fail(
            "start_vllm.sh 缺少量化参数 × 权重文件交叉校验(quant_model_description.json),"
            "BF16 权重误带 --quantization ascend 会在运行时崩溃。"
            "按 templates/start_vllm.<form>.sh 补充交叉校验代码段"
        )
    _pass("start_vllm.sh 含量化参数 × 权重文件交叉校验")


def c16_kv_transfer_tp_dp_var(ctx):
    """1.16 PD 模板 kv-transfer-config 内 tp_size/dp_size 变量化(硬性)。

    根因: PD 模板 start_vllm.pd.sh 的 kv-transfer-config JSON 内
    kv_connector_extra_config.{prefill,decode}.{tp_size,dp_size} 描述各角色 vLLM
    引擎内部 KV cache 分片方式,必须等于该角色的 --tensor-parallel-size /
    --data-parallel-size。模板早期版本硬编码为 1,在 TP>1 或 DP>1 时触发 pydantic
    校验: KV transfer 'prefill' config has a conflicting tensor/data parallel
    size. Expected N, but got 1(模型权重加载前分钟级内秒级退出,非应用超时)。

    校验逻辑:
      a) 非 PD 形式直接跳过(该 JSON 仅 PD 模板存在);
      b) PD 形式必须存在 KV_TRANSFER_CONFIG 拼装行;
      c) 该行内 prefill/decode 的 tp_size 必须为 ${TP_SIZE} 变量引用;
         prefill dp_size 必须为 ${PREFILL_DP_SIZE}、decode dp_size 必须为
         ${DECODE_DP_SIZE} 变量引用(按官网 PD 脚本 kv_connector_extra_config
         推导,prefill DP=1,decode DP=节点数×卡数/TP),出现裸数字即 FAIL。
    """
    deploy_form = ctx["deploy_form"]
    if deploy_form != "pd":
        _pass("非 PD 形式,跳过 kv-transfer-config 变量化校验")
        return
    start = os.path.join(ctx["artifact_dir"], "start_vllm.sh")
    if not os.path.isfile(start):
        _fail("start_vllm.sh 不存在,无法校验 kv-transfer-config 变量化")
        return
    content = _read(start)
    m = re.search(r'KV_TRANSFER_CONFIG="\{.*?kv_connector.*?\}"', content, re.S)
    if not m:
        return _fail(
            "PD 形式 start_vllm.sh 缺少 KV_TRANSFER_CONFIG 拼装行"
            "(以 templates/start_vllm.pd.sh 为准)"
        )
    line = m.group(0)
    # 合法: prefill/decode 的 tp_size 引用 ${TP_SIZE}(组内张量并行度);
    # prefill dp_size 引用 ${PREFILL_DP_SIZE},decode dp_size 引用 ${DECODE_DP_SIZE}
    # (按官网 PD 脚本推导:prefill DP=1,decode DP=节点数×卡数/TP,模板固定填入)。
    # bash 字符串中 JSON 字段名为转义引号 \",正则匹配可选反斜杠前缀。
    # prefill 段定义为 \"prefill\" 到 \"decode\" 之间的子串,避免 [^}]* 因 JSON 嵌套 }
    # 提前截断导致 tp_size 落在段外误判
    prefill_seg = re.search(r'\\"prefill\\":\s*\{(.*?)\\"decode\\"', line, re.S)
    prefill_text = prefill_seg.group(1) if prefill_seg else ""
    decode_seg = re.search(r'\\"decode\\":\s*\{(.*)', line, re.S)
    decode_text = decode_seg.group(1) if decode_seg else ""
    has_prefill_tp_var = '\\"tp_size\\": ${TP_SIZE}' in prefill_text
    has_prefill_dp_var = '\\"dp_size\\": ${PREFILL_DP_SIZE}' in prefill_text
    has_decode_tp_var = '\\"tp_size\\": ${TP_SIZE}' in decode_text
    has_decode_dp_var = '\\"dp_size\\": ${DECODE_DP_SIZE}' in decode_text
    # 裸数字(tp_size: 1 等)是模板硬编码遗留的明确错误信号
    has_raw_number = bool(re.search(r'\\"(tp_size|dp_size)\\":\s*\d+', line))
    if has_raw_number:
        return _fail(
            "kv-transfer-config 内 tp_size/dp_size 硬编码为裸数字"
            "(应为 ${TP_SIZE}/${PREFILL_DP_SIZE}/${DECODE_DP_SIZE} 变量)。"
            "TP>1 或 DP>1 时触发 pydantic 校验: KV transfer 'prefill' config has a "
            "conflicting tensor/data parallel size. Expected N, but got 1"
        )
    if not (has_prefill_tp_var and has_prefill_dp_var
            and has_decode_tp_var and has_decode_dp_var):
        return _fail(
            "kv-transfer-config 内 prefill/decode 的 tp_size/dp_size 未全部"
            "引用 ${TP_SIZE}/${PREFILL_DP_SIZE}/${DECODE_DP_SIZE} 变量"
            f"(prefill.tp_size={has_prefill_tp_var}, prefill.dp_size={has_prefill_dp_var}, "
            f"decode.tp_size={has_decode_tp_var}, decode.dp_size={has_decode_dp_var})"
        )
    _pass("kv-transfer-config 内 tp_size/dp_size 引用 ${TP_SIZE}/${PREFILL_DP_SIZE}/${DECODE_DP_SIZE} 变量")


def c17_flashcomm1_tp_match(ctx):
    """1.17 enable_flashcomm1 × TP_SIZE 通用交叉校验(硬性,所有部署形式覆盖)。

    根因: vLLM 0.23.0 AscendConfig pydantic 校验强制 `enable_flashcomm1` 仅在
    tp_size > 1 时可用,TP=1 时 `Assertion failed, Flash Comm v1 is only supported
    when tp_size > 1.`,在 create_engine_config 阶段崩溃(模型权重加载前分钟级
    秒级退出)。该约束与部署形式无关(single/multi_node/pd 任何
    形式 TP=1 均崩),根因常为 agent 误把文档量化版示例(含量化版 enable_flashcomm1)
    当 BF16+TP=1 示例套用。

    校验逻辑:
      a) 未提供 --tp-size 时跳过(无判定依据);
      b) TP=1 时,start_vllm.sh 全文(MODEL_ARGS/EXTRA_ARGS/PD_EXTRA_ARGS/
         --additional-config 任一来源)出现 enable_flashcomm1 即 FAIL;
      c) TP>1 时不限制(虽 PD 分离按 3.2 仍不带,但本检查仅校验 TP=1 通用约束)。
    """
    tp = ctx.get("tp_size")
    if tp is None:
        _pass("未提供 --tp-size,跳过 enable_flashcomm1 × TP 交叉校验")
        return
    if tp > 1:
        _pass(f"TP={tp}>1,enable_flashcomm1 允许(本检查仅拦截 TP=1 通用崩溃)")
        return
    start = os.path.join(ctx["artifact_dir"], "start_vllm.sh")
    if not os.path.isfile(start):
        return
    content = _read(start)
    # 仅检测 enable_flashcomm1 实际启用(取值为 true),排除说明性注释/字符串
    # 匹配模式: enable_flashcomm1": true 或 enable_flashcomm1":true(JSON 内启用)
    # 不匹配: 注释行(# ...enable_flashcomm1...)或字符串说明
    enabled = bool(re.search(r'[\"\\]+enable_flashcomm1[\"\\]+\s*:\s*true', content))
    if enabled:
        return _fail(
            f"TP={tp} 时 start_vllm.sh 启用 enable_flashcomm1: true(vLLM 0.23.0 强制 "
            "tp_size>1 才允许,TP=1 触发 pydantic 校验崩溃 "
            "`Assertion failed, Flash Comm v1 is only supported when tp_size > 1.`)。"
            "根因: 误把文档量化版示例的 enable_flashcomm1 套用到 TP=1 部署;"
            "修复: --additional-config 移除 enable_flashcomm1,仅留 enable_cpu_binding"
        )
    _pass(f"TP={tp} 时 start_vllm.sh 未启用 enable_flashcomm1(避免 vLLM pydantic 崩溃)")


def c18_first_unit_not_worker_decode(ctx):
    """1.18 第一推理单元不能是 worker/decode(硬性,官网+ModelArts 平台约束)。

    核心规范(强制): 部署的第一推理单元(group 0 / unit_configs[0])不能出现
    worker 或 decode 启动的实例——ModelArts 在线服务所有请求都发送到 group 0,
    worker/decode 不具备接受请求功能。

    本检查扫描 start_vllm.sh 的角色判定逻辑,确保 VLLM_ROLE=worker 或
    VLLM_ROLE=decode 不被设为第一推理单元(通过脚本角色分支顺序推断)。
    实际请求体层校验由 create_infer_service.py validate_request_body() 承载,
    本检查作为产物侧补充(产物脚本不含 unit_configs 顺序信息,仅做角色分支存在性校验)。
    """
    deploy_form = ctx["deploy_form"]
    if deploy_form not in ("multi_node", "pd"):
        _pass("非多机/PD 形式,跳过第一推理单元角色校验")
        return
    start = os.path.join(ctx["artifact_dir"], "start_vllm.sh")
    if not os.path.isfile(start):
        return
    content = _read(start)
    if deploy_form == "multi_node":
        if "VLLM_ROLE" in content and "master" not in content.lower():
            return _fail("multi_node 形式 start_vllm.sh 含 VLLM_ROLE 但无 master 角色(第一推理单元须为 master)")
        _pass("multi_node 形式第一推理单元为 master")
    elif deploy_form == "pd":
        if "proxy" not in content.lower():
            return _fail("pd 形式 start_vllm.sh 无 proxy 角色分支(第一推理单元须为 proxy)")
        _pass("pd 形式第一推理单元为 proxy")


def c19_pd_kv_port_range(ctx):
    """1.19 PD 分离 kv_port 范围校验(硬性,官网 F4 约束)。

    官网: Mooncake AscendDirectTransport 在 [20000, 20000 + npu_per_node × 1000)
    随机分配端口,kv_port 需避开此范围:
      8 卡 → kv_port ≥ 28000
      16 卡 → kv_port ≥ 36000
    kv_port 与 AscendDirectTransport 随机端口冲突会导致间歇性
    zmq.error.ZMQError: Address already in use。
    """
    deploy_form = ctx["deploy_form"]
    if deploy_form != "pd":
        _pass("非 PD 形式,跳过 kv_port 范围校验")
        return
    start = os.path.join(ctx["artifact_dir"], "start_vllm.sh")
    if not os.path.isfile(start):
        return
    content = _read(start)
    m = re.search(r'KV_PORT="\$\{KV_PORT:-(\d+)\}"', content)
    if not m:
        _warn("PD 形式 start_vllm.sh 未找到 KV_PORT 默认值,跳过范围校验")
        return
    kv_port = int(m.group(1))
    tp = ctx.get("tp_size")
    if tp is None:
        _warn("未提供 --tp-size,按 8 卡阈值 28000 校验")
        threshold = 28000
    else:
        threshold = 36000 if tp > 8 else 28000
    if kv_port < threshold:
        return _fail(
            f"PD 形式 kv_port={kv_port} < {threshold}(官网约束: "
            f"{'16 卡' if tp and tp > 8 else '8 卡'} kv_port 需 ≥ {threshold} 避开 "
            f"AscendDirectTransport 随机端口 [20000, {20000 + (16 if tp and tp > 8 else 8) * 1000})"
        )
    _pass(f"PD 形式 kv_port={kv_port} ≥ {threshold}(避开 AscendDirectTransport 随机端口)")


# ---------- 性能最优检查(软性) ----------


def c20_health_check_decode_probe_local(ctx):
    """1.20 health_check.sh decode 角色探本地 /health(硬性)。

    PD 形式 decode 每节点独立暴露 API(文档 4P4D: D0-D3 各自 API),
    readiness 探针必须探本地 /health,禁止探 group master。
    """
    deploy_form = ctx["deploy_form"]
    if deploy_form != "pd":
        _pass("非 PD 形式,跳过 decode 探本地校验")
        return
    hc = os.path.join(ctx["artifact_dir"], "health_check.sh")
    if not os.path.isfile(hc):
        return
    content = _read(hc)
    if re.search(r'VLLM_ROLE.*!=.*decode', content) or re.search(r'VLLM_ROLE.*!= "decode"', content):
        _pass("health_check.sh decode 角色探本地 /health(含 VLLM_ROLE != decode 条件包裹)")
    else:
        _fail("health_check.sh decode 角色未探本地 /health(须含 VLLM_ROLE != decode 条件包裹,禁止探 group master)")


def c21_health_check_worker_process_match(ctx):
    """1.21 health_check.sh PP/DP worker 进程匹配(硬性)。

    PP/DP worker(--headless)容器内无 vllm serve 独立进程,
    check_process() 必须额外匹配 vllm.v1.worker / base_worker.py。
    """
    deploy_form = ctx["deploy_form"]
    if deploy_form not in ("multi_node", "pd"):
        _pass("非多机/PD 形式,跳过 worker 进程匹配校验")
        return
    hc = os.path.join(ctx["artifact_dir"], "health_check.sh")
    if not os.path.isfile(hc):
        return
    content = _read(hc)
    if re.search(r'vllm\.v1\.worker', content) or re.search(r'base_worker\.py', content):
        _pass("health_check.sh 含 PP/DP worker 进程匹配(vllm.v1.worker / base_worker.py)")
    else:
        _fail("health_check.sh check_process() 缺少 PP/DP worker 进程匹配(须含 pgrep -f vllm.v1.worker 或 base_worker.py)")


def c22_health_check_decode_port_dp_rank(ctx):
    """1.22 health_check.sh decode PORT 按 DP rank 推导(硬性)。

    decode 各节点独立 API 端口递增(D0=7100, D1=7101...),
    health_check.sh 禁止硬编码 PORT=7100,须按 DP rank 推导。
    """
    deploy_form = ctx["deploy_form"]
    if deploy_form != "pd":
        _pass("非 PD 形式,跳过 decode PORT 推导校验")
        return
    hc = os.path.join(ctx["artifact_dir"], "health_check.sh")
    if not os.path.isfile(hc):
        return
    content = _read(hc)
    if re.search(r'DECODE_START_PORT.*\+.*_dp_rank', content) or re.search(r'DECODE_START_PORT.*\+.*dp_rank', content, re.I):
        _pass("health_check.sh decode PORT 按 DP rank 推导(非硬编码 7100)")
    else:
        _fail("health_check.sh decode PORT 未按 DP rank 推导(禁止硬编码 7100,须含 DECODE_START_PORT + DP_rank)")


def c23_pp_master_port_independent(ctx):
    """1.23 PP master_port 独立于 API port(硬性)。

    PP 分布式通信(distributed_init tcp://master:master_port)与
    API server(uvicorn bind --port)同端口会导致 uvicorn bind 失败。
    """
    deploy_form = ctx["deploy_form"]
    if deploy_form != "pd":
        _pass("非 PD 形式,跳过 PP master_port 校验")
        return
    start = os.path.join(ctx["artifact_dir"], "start_vllm.sh")
    if not os.path.isfile(start):
        return
    content = _read(start)
    has_pp = re.search(r'pipeline.parallel.size.*[1-9]', content, re.I)
    if not has_pp:
        _pass("PD 形式无 PP 多节点,跳过 master_port 校验")
        return
    master_port_var = re.search(r'--master-port\s+"\$\{(\w+)"', content)
    port_var = re.search(r'--port\s+"\$\{(\w+)"', content)
    if not master_port_var or not port_var:
        _warn("未找到 --master-port 或 --port 变量,跳过校验")
        return
    if master_port_var.group(1) == port_var.group(1):
        _fail(f"PP --master-port 与 --port 同变量({master_port_var.group(1)}),须独立(如 VLLM_MASTER_PORT=29500)")
    else:
        _pass(f"PP --master-port({master_port_var.group(1)})与 --port({port_var.group(1)})独立")


def c24_health_check_multi_node_worker_probe_master(ctx):
    """1.24 health_check.sh multi_node worker 探针目标探 master(硬性)。

    multi_node 形态 master/worker 实例均不注入 VLLM_ROLE(仅 PD 分离注入),
    readiness 探针分支条件若要求 VLLM_ROLE 非空,multi_node worker 会落入
    默认 target_ip=127.0.0.1 探本地 /health;但 worker 加 --headless 不监听 API,
    /health 永远不通 → readiness 永久失败 → 实例异常重启循环。
    修复:有 GLOBAL_RANK_TABLE_FILE_PATH 即进多实例分支,worker 解析 group 0
    第一个 server IP 作为 target_ip 探 master /health。
    """
    deploy_form = ctx["deploy_form"]
    if deploy_form != "multi_node":
        _pass("非 multi_node 形式,跳过 worker 探针目标校验")
        return
    hc = os.path.join(ctx["artifact_dir"], "health_check.sh")
    if not os.path.isfile(hc):
        return
    content = _read(hc)
    bad = re.search(r'GLOBAL_RANK_TABLE_FILE_PATH.*&&.*VLLM_ROLE', content)
    if bad:
        _fail(
            "health_check.sh 多实例探针分支条件含 GLOBAL_RANK_TABLE_FILE_PATH && VLLM_ROLE,"
            "multi_node 形态 master/worker 均不注入 VLLM_ROLE(仅 PD 分离注入),"
            "worker 会落入默认 target_ip=127.0.0.1 探本地 /health,但 worker 加 --headless 不监听 API,"
            "/health 永远不通 → readiness 永久失败 → 实例异常重启循环。"
            "修复:条件改为仅判 GLOBAL_RANK_TABLE_FILE_PATH 非空(有 rank table 即多实例场景)"
        )
    else:
        _pass("health_check.sh 多实例探针分支仅判 GLOBAL_RANK_TABLE_FILE_PATH,multi_node worker 探 master /health")


def c25_multi_node_dp_start_rank_dynamic(ctx):
    """1.25 multi_node DP_START_RANK 动态推导(硬性)。

    ModelArts multi_node 形态不注入 DP_START_RANK envs(与 PD 分离不同,PD 经
    envs 注入),必须从 rank table 动态推导(get_master_ip.py --dp-rank)。
    硬编码 0 会导致 worker 节点也启动 engine rank 0,与 master 冲突,vLLM 报
    "HELLO message from remote engine 0, expected it to be local",worker 5
    分钟超时 "Did not receive response from front-end process"。
    DATA_PARALLEL_SIZE 同理必须 --dp-size 动态推导(envs 不注入,与 PD 分离
    PREFILL_DP_SIZE/DECODE_DP_SIZE 由脚本固定填入不同)。
    """
    deploy_form = ctx["deploy_form"]
    if deploy_form != "multi_node":
        _pass("非 multi_node 形式,跳过 DP_START_RANK 动态推导校验")
        return
    start = os.path.join(ctx["artifact_dir"], "start_vllm.sh")
    if not os.path.isfile(start):
        return
    content = _read(start)
    has_dp_rank = re.search(r'get_master_ip\.py["\s]*--dp-rank', content)
    has_dp_size = re.search(r'get_master_ip\.py["\s]*--dp-size', content)
    if not has_dp_rank:
        _fail(
            "start_vllm.sh DP_START_RANK 未动态推导(missing get_master_ip.py --dp-rank),"
            "ModelArts multi_node 不注入 DP_START_RANK envs(与 PD 分离不同),"
            "硬编码 0 会导致 worker 也启动 engine rank 0,与 master 冲突,"
            "vLLM 报 'HELLO message from remote engine 0, expected it to be local'"
        )
    elif not has_dp_size:
        _fail(
            "start_vllm.sh DATA_PARALLEL_SIZE 未动态推导(missing get_master_ip.py --dp-size),"
            "ModelArts multi_node 不注入 DP_SIZE envs,硬编码不符会致跨节点通信失败"
        )
    else:
        _pass("start_vllm.sh DP_START_RANK/DP_SIZE 从 rank table 动态推导(--dp-rank/--dp-size)")


def c26_pd_model_args_constraints(ctx):
    """1.26 PD 分离 MODEL_ARGS 填充约束(硬性,违反=运行期 CUDAGraph 捕获崩溃)。

    PD 分离下 prefill/decode 是两个独立 vLLM 实例,禁止照搬模型文档单节点示例
    的单引擎内优化参数。两条强制约束(SKILL.md 3.2 共同要点):
      ① --speculative-config 禁止(MTP 投机解码 → CUDAGraph 捕获阶段
         `RuntimeError: src size vs slice size` 崩溃);
      ② --additional-config 不带 enable_flashcomm1 仅留 {"enable_cpu_binding":true}
         (enable_flashcomm1 是单引擎内 TP 通信优化,PD 分离 prefill/decode 独立
         实例未经文档验证)。

    H17 仅校验 enable_flashcomm1 × TP=1 通用约束,本检查补充 PD 形式 TP>1 时
    enable_flashcomm1 也应禁用的 PD 专属约束。--compilation-config 的
    cudagraph_capture_sizes 非强制(已验证不带也成功),不纳入本检查。
    """
    deploy_form = ctx["deploy_form"]
    if deploy_form != "pd":
        _pass("非 PD 形式,跳过 PD MODEL_ARGS 填充约束校验")
        return
    start = os.path.join(ctx["artifact_dir"], "start_vllm.sh")
    if not os.path.isfile(start):
        return
    content = _read(start)
    # ① --speculative-config 禁止(检测实际启用,排除注释/字符串说明)
    has_speculative = bool(re.search(r'[\"\\\'\\]+--speculative-config\\b', content))
    if has_speculative:
        return _fail(
            "PD 形式 start_vllm.sh 含 --speculative-config(MTP 投机解码),"
            "PD 分离 prefill/decode 独立实例照搬单节点 MTP 优化 → CUDAGraph 捕获阶段 "
            "`RuntimeError: src size vs slice size` 崩溃。"
            "修复: 移除 --speculative-config(Single 形式才允许 MTP)"
        )
    # ② --additional-config 不带 enable_flashcomm1
    has_flashcomm_enabled = bool(re.search(r'[\"\\]+enable_flashcomm1[\"\\]+\s*:\s*true', content))
    if has_flashcomm_enabled:
        return _fail(
            "PD 形式 start_vllm.sh 启用 enable_flashcomm1: true,"
            "enable_flashcomm1 是单引擎内 TP 通信优化,PD 分离 prefill/decode 独立实例"
            "未经文档验证(即使 TP>1 也应禁用,与 H17 TP=1 通用约束互补)。"
            "修复: --additional-config 移除 enable_flashcomm1,仅留 {\"enable_cpu_binding\":true}"
        )
    _pass("PD 形式 MODEL_ARGS 两约束均通过(无 speculative-config / 无 enable_flashcomm1)")


def s01_doc_params_soft(ctx):
    """2.1 模型文档性能参数齐全度(软性)。

    JSON 值匹配采用规范化比较(与 c11 一致),避免字面空格/引号差异误判。
    """
    doc_params = ctx.get("doc_params") or {}
    if not doc_params:
        _warn("未提供 --doc-params,无法对照模型文档性能参数。建议传入模型文档推荐的参数清单")
        return
    start = os.path.join(ctx["artifact_dir"], "start_vllm.sh")
    content = _read(start)
    missing = []
    for k, v in doc_params.items():
        if k not in content:
            missing.append(f"{k}={v}")
            continue
        if not (isinstance(v, str) and v):
            continue
        if v.lstrip().startswith(("{", "[")):
            script_values = _extract_script_json_values(content, k)
            normalized_v = _normalize_json_value(v)
            if normalized_v not in script_values:
                missing.append(f"{k}={v}")
        elif v not in content:
            missing.append(f"{k}={v}")
    if missing:
        _warn(f"模型文档推荐参数未在脚本中发现(可能通过 EXTRA_ARGS/PD_EXTRA_ARGS 注入,"
              f"或需要补充): {', '.join(missing)}。对照模型文档核对是否为文档要求项")
    else:
        _pass("模型文档性能参数已全部内联到脚本")


def s02_ascend_env(ctx):
    """2.2 昇腾环境变量(软性)。"""
    start = os.path.join(ctx["artifact_dir"], "start_vllm.sh")
    if not os.path.isfile(start):
        return
    content = _read(start)
    common = ["PYTORCH_NPU_ALLOC_CONF", "HCCL_BUFFSIZE", "OMP_PROC_BIND"]
    missing = [e for e in common if e not in content]
    if missing:
        _warn(f"常见昇腾环境变量未在 start_vllm.sh 中发现: {', '.join(missing)}"
              f"(以模型文档为准,文档未要求可不加)")
    else:
        _pass("常见昇腾环境变量已设置(PYTORCH_NPU_ALLOC_CONF/HCCL_BUFFSIZE/OMP_PROC_BIND)")


def s03_tp_dp_match(ctx):
    """2.3 TP/DP 与资源规格匹配(软性)。"""
    tp = ctx.get("tp_size")
    dp = ctx.get("dp_size")
    if tp is None and dp is None:
        _warn("未提供 --tp-size/--dp-size,跳过 TP/DP 匹配检查(建议提供)")
        return
    start = os.path.join(ctx["artifact_dir"], "start_vllm.sh")
    content = _read(start)
    if tp is not None:
        # 同时匹配 TP_SIZE 和 TENSOR_PARALLEL_SIZE 两种变量名
        m = re.search(r'(?:TP_SIZE|TENSOR_PARALLEL_SIZE)="\$\{(?:TP_SIZE|TENSOR_PARALLEL_SIZE):-(\d+)\}"', content)
        if m and int(m.group(1)) != tp:
            _warn(f"脚本默认 TP={m.group(1)} != 期望 {tp}(部署时可用环境变量覆盖)")
        elif m:
            _pass(f"TP 默认值 = {tp}")
    if dp is not None:
        m = re.search(r'DATA_PARALLEL_SIZE="\$\{DATA_PARALLEL_SIZE:-(\d+)\}"', content)
        if m:
            _pass(f"DATA_PARALLEL_SIZE 默认值 = {m.group(1)}(模板按方案固定填入)")
        elif 'DATA_PARALLEL_SIZE' not in content:
            _warn(f"期望 DP={dp},但脚本未发现 DATA_PARALLEL_SIZE 变量,核对 DATA_PARALLEL_SIZE 来源")


def s04_deploy_config_advice(ctx):
    """2.4 部署配置建议(软性,非脚本内容)。"""
    deploy_form = ctx["deploy_form"]
    advice = []
    if deploy_form in ("multi_node", "pd"):
        advice.append("部署时配置超节点亲和组实例数=N(实例数: 跨节点子场景 N=跨节点数,单节点多实例子场景 N=实例数)")
    if deploy_form == "pd":
        advice.append("部署时同一部署单元内 3 个推理单元分别注入 VLLM_ROLE=proxy/prefill/decode(PORT 已在脚本内按角色内置默认值 proxy=8080/prefill=8080/decode=7100,无需注入)")
    if advice:
        _warn("部署配置建议: " + "; ".join(advice) + "(按 SKILL.md 4.4 核对)")


# ---------- 注册检查项 ----------

def register():
    global HARD_CHECKS, SOFT_CHECKS
    HARD_CHECKS = [
        ("H01", "1.1 产物文件齐全", c01_file_completeness),
        ("H02", "1.2 LF 行尾", c02_lf_line_ending),
        ("H03", "1.3 bash 语法", c03_bash_syntax),
        ("H04", "1.4 bash 数组(禁 sh)", c04_bash_array_not_sh),
        ("H05", "1.5 权重挂载自检", c05_model_weight_check),
        ("H06", "1.6 端口一致性", c06_port_consistency),
        ("H07", "1.7 探针命令", c07_probe_cmd),
        ("H08", "1.8 多实例/PD分离适配", c08_multi_node_adaptation),
        ("H09", "1.9 PD 分离适配", c09_pd_role_adaptation),
        ("H10", "1.10 相对路径定位", c10_relative_path),
        ("H11", "1.11 模型文档必备参数", c11_doc_params_hard),
        ("H12", "1.12 TP_SIZE 固定值与文档一致", c12_tp_size_match),
        ("H13", "1.13 角色专属参数归属校验", c13_role_specific_args),
        ("H14", "1.14 --headless 与 DP LB 模式匹配", c14_headless_dp_lb_match),
        ("H15", "1.15 量化参数 × 权重文件交叉校验", c15_quant_weight_match),
        ("H16", "1.16 PD 模板 kv-transfer-config 变量化", c16_kv_transfer_tp_dp_var),
        ("H17", "1.17 enable_flashcomm1 × TP_SIZE 通用交叉校验", c17_flashcomm1_tp_match),
        ("H18", "1.18 第一推理单元不能是 worker/decode", c18_first_unit_not_worker_decode),
        ("H19", "1.19 PD 分离 kv_port 范围校验", c19_pd_kv_port_range),
        ("H20", "1.20 health_check.sh decode 探本地 /health", c20_health_check_decode_probe_local),
        ("H21", "1.21 health_check.sh PP/DP worker 进程匹配", c21_health_check_worker_process_match),
        ("H22", "1.22 health_check.sh decode PORT 按 DP rank 推导", c22_health_check_decode_port_dp_rank),
        ("H23", "1.23 PP master_port 独立于 API port", c23_pp_master_port_independent),
        ("H24", "1.24 health_check.sh multi_node worker 探针探 master", c24_health_check_multi_node_worker_probe_master),
        ("H25", "1.25 multi_node DP_START_RANK/DP_SIZE 动态推导", c25_multi_node_dp_start_rank_dynamic),
        ("H26", "1.26 PD 分离 MODEL_ARGS 填充约束", c26_pd_model_args_constraints),
    ]
    SOFT_CHECKS = [
        ("S01", "2.1 模型文档性能参数齐全度", s01_doc_params_soft),
        ("S02", "2.2 昇腾环境变量", s02_ascend_env),
        ("S03", "2.3 TP/DP 匹配", s03_tp_dp_match),
        ("S04", "2.4 部署配置建议", s04_deploy_config_advice),
    ]


def parse_args():
    p = argparse.ArgumentParser(description="校验 ModelArts 部署产物可用性与性能最优性")
    p.add_argument("--artifact-dir", required=True, help="本地产物目录(如 ./Qwen3-8B-pd)")
    p.add_argument("--deploy-form", required=True,
                   choices=["single", "multi_node", "pd"],
                   help="部署形式: single(单机部署)/multi_node(多机部署)/pd(PD 分离部署)")
    p.add_argument("--doc-params", default="",
                   help="模型文档推荐启动参数 JSON(性能检查对照),如 "
                        '{"max-model-len":"131072","quantization":"ascend"}')
    p.add_argument("--model-doc-url", default="", help="vllm-ascend 模型文档 URL(仅记录核对来源)")
    p.add_argument("--expect-port", type=int, default=8080, help="期望监听端口(默认 8080)")
    p.add_argument("--tp-size", type=int, default=None, help="期望 TP(卡数)")
    p.add_argument("--dp-size", type=int, default=None, help="期望 DP(组内 DP 总秩数=data-parallel-size)")
    p.add_argument("--num-attention-heads", type=int, default=None,
                   help="模型注意力头数(从模型 config.json 的 num_attention_heads 获取)。"
                        "提供后 H12 硬性校验 TP 必须能被头数整除(头数 24 + TP=16 → "
                        "vLLM 启动硬校验崩溃 ValueError: attention heads must be "
                        "divisible by tensor parallel size)")
    return p.parse_args()


def main():
    args = parse_args()
    if not os.path.isdir(args.artifact_dir):
        print(f"[错误] 产物目录不存在: {args.artifact_dir}")
        return 2
    try:
        doc_params = json.loads(args.doc_params) if args.doc_params else {}
    except json.JSONDecodeError as e:
        print(f"[错误] --doc-params 不是合法 JSON: {e}")
        return 2

    ctx = {
        "artifact_dir": args.artifact_dir,
        "deploy_form": args.deploy_form,
        "doc_params": doc_params,
        "model_doc_url": args.model_doc_url,
        "expect_port": args.expect_port,
        "tp_size": args.tp_size,
        "dp_size": args.dp_size,
        "attention_heads": args.num_attention_heads,
    }

    register()
    global FAIL_COUNT, WARN_COUNT
    FAIL_COUNT = 0
    WARN_COUNT = 0
    print(f"=== 部署产物自检: {args.artifact_dir} (部署形式: {args.deploy_form}) ===")
    print(f"--- 可用性检查(硬性,FAIL 不得上传) ---")
    for code, title, fn in HARD_CHECKS:
        print(f"{code} {title}")
        try:
            fn(ctx)
        except Exception as e:
            _fail(f"检查异常: {e}")
    print(f"--- 性能最优检查(软性,WARN 提示不阻断) ---")
    for code, title, fn in SOFT_CHECKS:
        print(f"{code} {title}")
        try:
            fn(ctx)
        except Exception as e:
            _warn(f"检查异常: {e}")

    print("=== 自检结果 ===")
    if FAIL_COUNT:
        print(f"FAIL: {FAIL_COUNT} 项硬性检查未通过,禁止上传 OBS(按 references/artifact-check.md 修复后重跑)")
        return 1
    if WARN_COUNT:
        print(f"WARN: {WARN_COUNT} 项软性检查提示(不阻断上传,按需优化)")
    print("PASS: 全部硬性检查通过,可上传 OBS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
