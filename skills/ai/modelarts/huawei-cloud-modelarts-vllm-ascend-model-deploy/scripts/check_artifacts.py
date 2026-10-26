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
    need = ["start_vllm.sh", "health_check.sh"]
    # multinode / pd_colocate 需要 get_master_ip.py
    if deploy_form in ("multinode", "pd_colocate"):
        need.append("get_master_ip.py")
    missing = [f for f in need if not os.path.isfile(os.path.join(art_dir, f))]
    if missing:
        return _fail(f"产物目录 {art_dir} 缺少文件: {', '.join(missing)}"
                     f"(部署形式 {deploy_form} 需要 {', '.join(need)})")
    _pass("产物文件齐全: " + ", ".join(need))


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


def c08_multinode_adaptation(ctx):
    """1.8 多节点/PD 共置: get_master_ip.py 存在且被引用。"""
    deploy_form = ctx["deploy_form"]
    art_dir = ctx["artifact_dir"]
    if deploy_form not in ("multinode", "pd_colocate"):
        _pass("非多节点/PD 共置形式,跳过 master/slave 检查")
        return
    start = os.path.join(art_dir, "start_vllm.sh")
    content = _read(start)
    if "get_master_ip.py" not in content:
        return _fail(f"{deploy_form} 部署形式但 start_vllm.sh 未引用 get_master_ip.py")
    if not os.path.isfile(os.path.join(art_dir, "get_master_ip.py")):
        return _fail("start_vllm.sh 引用 get_master_ip.py 但产物目录缺少该文件")
    # DP 动态推导检查
    if "--dp-size" not in content:
        _warn("start_vllm.sh 未发现 get_master_ip.py --dp-size 动态推导 DATA_PARALLEL_SIZE,"
              "建议改用动态推导(见模板)")
    _pass("get_master_ip.py 存在且被 start_vllm.sh 引用")


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
    _pass("start_vllm.sh 包含 VLLM_ROLE 角色分支(prefill/decode)")


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


def c11_doc_params_hard(ctx):
    """1.11 模型文档必备参数齐全(经 --doc-params 传入)。"""
    doc_params = ctx.get("doc_params") or {}
    if not doc_params:
        _pass("未提供 --doc-params,跳过模型文档参数对照(建议提供)")
        return
    start = os.path.join(ctx["artifact_dir"], "start_vllm.sh")
    content = _read(start)
    missing = []
    for key, val in doc_params.items():
        key_in = key in content
        if isinstance(val, str) and val:
            val_in = val in content
        else:
            val_in = True
        if not key_in or not val_in:
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
    multinode/pd_colocate 模板用 TENSOR_PARALLEL_SIZE 变量名,single/pd 用 TP_SIZE,
    旧 S03 正则只匹配 TENSOR_PARALLEL_SIZE,对 TP_SIZE 静默跳过。

    检查逻辑: 同时匹配两种变量名,若提供 --tp-size 则要求脚本默认值一致(FAIL);
    若脚本默认值是从 ASCEND_RT_VISIBLE_DEVICES 推导(非固定数字),则 FAIL 要求改为固定值。
    若提供 --num-attention-heads(模型注意力头数),则要求 TP 能被头数整除(FAIL),
    否则 vLLM 启动硬校验崩溃(实测: Qwen3.8-27B 头数 24 + TP=16 → 24%16≠0 →
    ValueError: Total number of attention heads (24) must be divisible by tensor
    parallel size,master/slave 全部崩溃)。
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
            f"by tensor parallel size,master/slave 全部崩溃)。"
            f"TP 必须取头数的约数(如头数 24 → TP ∈ 2/4/6/8/12/24),"
            f"且不超过单节点卡数"
        )
    _pass(f"TP_SIZE 默认值={default_val}" + (f"(与文档推荐 TP={tp} 一致)" if tp else ""))


def c13_role_specific_args(ctx):
    """1.13 角色专属参数归属校验(仅 master 命令有、slave 命令没有的参数,
    禁止放入所有节点共享的 MODEL_ARGS 数组)。

    根因: 多节点/PD 共置场景下各节点运行同一脚本,slave 节点由模板自动追加
    --headless;若共享的 MODEL_ARGS 数组混入 master 专属参数(如
    --api-server-count 1),slave 同时获得两者,vllm 参数校验直接拒绝
    (ValueError: --api-server-count=1 cannot be used with --headless),
    slave 在参数解析阶段崩溃,部署失败。

    黑名单: --api-server-count、--nnodes、--node-rank、--master-addr、
    --master-port。--headless 由模板 SLAVE_OPTS 自动处理,不在检查范围。
    """
    deploy_form = ctx["deploy_form"]
    if deploy_form not in ("multinode", "pd_colocate"):
        _pass("非多节点/PD 共置形式,跳过角色专属参数归属校验")
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
            f"数组——slave 节点会同时获得该参数与自动追加的 --headless,"
            f"vllm 参数校验拒绝(如 --api-server-count=1 cannot be used with "
            f"--headless),slave 在参数解析阶段崩溃,部署失败。"
            f"多节点场景 master 默认即 API server(--api-server-count 默认 1),"
            f"无需显式设置,请从 MODEL_ARGS 移除。"
        )
    _pass("MODEL_ARGS 未包含角色专属参数(--api-server-count/--nnodes/"
          "--node-rank/--master-addr/--master-port)")


def c14_headless_dp_lb_match(ctx):
    """1.14 --headless 与 DP LB 模式匹配(vLLM 0.23.0 默认 vs external/hybrid)。

    vLLM 0.23.0 **默认**非 external/hybrid DP LB 模式: slave **必须**追加 --headless,
    否则报 RuntimeError: Remote engine N must use --headless unless in external or
    hybrid dp lb mode(实测 vLLM 0.23.0 + multinode 2 节点 BF16 部署触发)。
    vLLM ≥ v0.30.0rc1 启用 external/hybrid DP LB 模式时,slave 禁 --headless(报反向错误)。
    DP LB 模式由环境变量 DP_LB_MODE=external|hybrid 显式声明,与 DATA_PARALLEL_SIZE_LOCAL 无关。
    """
    deploy_form = ctx["deploy_form"]
    if deploy_form not in ("multinode", "pd_colocate"):
        _pass("非多节点/PD 共置形式,跳过 --headless 与 DP LB 模式匹配校验")
        return
    start = os.path.join(ctx["artifact_dir"], "start_vllm.sh")
    if not os.path.isfile(start):
        _fail("start_vllm.sh 不存在,无法校验 --headless 与 DP LB 模式匹配")
        return
    content = _read(start)
    # 必须有 DP_LB_MODE 条件判断分支(以模板 start_vllm.multinode.sh 为准)
    has_dp_lb_mode_check = bool(re.search(r'DP_LB_MODE="\$\{DP_LB_MODE', content))
    has_headless_in_default_branch = bool(
        re.search(r'SLAVE_OPTS="--headless"', content)
        and re.search(r'DP_LB_MODE="\$\{DP_LB_MODE', content))
    has_http_server_placeholder = bool(re.search(r'python -m http\.server', content))
    if not has_dp_lb_mode_check:
        return _fail(
            "slave 分支未按 DP_LB_MODE 条件判断(以模板 start_vllm.multinode.sh / "
            "start_vllm.pd_colocate.sh 为准)。vLLM 0.23.0 默认 DP LB 模式 slave 必须"
            "加 --headless,external/hybrid 模式禁 --headless,需通过 DP_LB_MODE "
            "环境变量区分(与 DATA_PARALLEL_SIZE_LOCAL 无关)"
        )
    if not has_headless_in_default_branch:
        return _fail(
            "默认 DP LB 模式分支未追加 --headless。vLLM 0.23.0 默认非 external/hybrid "
            "DP LB 模式: slave 必须加 --headless(实测报 RuntimeError: Remote engine N "
            "must use --headless unless in external or hybrid dp lb mode)"
        )
    if not has_http_server_placeholder:
        return _fail(
            "slave 加 --headless 后不监听 API,需占位 http server 承接探针"
            "(nohup python -m http.server 8080)"
        )
    _pass("--headless 按 DP_LB_MODE 条件判定(默认加,external/hybrid 不加)")


# ---------- 性能最优检查(软性) ----------

def s01_doc_params_soft(ctx):
    """2.1 模型文档性能参数齐全度(软性)。"""
    doc_params = ctx.get("doc_params") or {}
    if not doc_params:
        _warn("未提供 --doc-params,无法对照模型文档性能参数。建议传入模型文档推荐的参数清单")
        return
    start = os.path.join(ctx["artifact_dir"], "start_vllm.sh")
    content = _read(start)
    missing = [f"{k}={v}" for k, v in doc_params.items()
               if k not in content or (isinstance(v, str) and v and v not in content)]
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
        m = re.search(r'DATA_PARALLEL_SIZE="\$\{DATA_PARALLEL_SIZE:-\$\{DP_SIZE_DEFAULT:-(\d+)\}\}"', content)
        if m:
            _pass(f"DATA_PARALLEL_SIZE 由 rank table 动态推导(--dp-size,默认兜底 {m.group(1)})")
        elif '--dp-size' not in content:
            _warn(f"期望 DP={dp},但脚本未发现 --dp-size 动态推导,核对 DATA_PARALLEL_SIZE 来源")


def s04_deploy_config_advice(ctx):
    """2.4 部署配置建议(软性,非脚本内容)。"""
    deploy_form = ctx["deploy_form"]
    advice = []
    if deploy_form in ("multinode", "pd_colocate"):
        advice.append("部署时配置超节点亲和组实例数=N(副本内节点数)")
    if deploy_form == "pd":
        advice.append("部署时同一部署单元内 2 个推理单元分别注入 VLLM_ROLE=prefill/decode + 不同 PORT")
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
        ("H08", "1.8 多节点/PD共置适配", c08_multinode_adaptation),
        ("H09", "1.9 PD 分离适配", c09_pd_role_adaptation),
        ("H10", "1.10 相对路径定位", c10_relative_path),
        ("H11", "1.11 模型文档必备参数", c11_doc_params_hard),
        ("H12", "1.12 TP_SIZE 固定值与文档一致", c12_tp_size_match),
        ("H13", "1.13 角色专属参数归属校验", c13_role_specific_args),
        ("H14", "1.14 --headless 与 DP LB 模式匹配", c14_headless_dp_lb_match),
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
                   choices=["single", "multinode", "pd", "pd_colocate"],
                   help="部署形式: single/multinode/pd(分离)/pd_colocate(共置)")
    p.add_argument("--doc-params", default="",
                   help="模型文档推荐启动参数 JSON(性能检查对照),如 "
                        '{"max-model-len":"131072","quantization":"ascend"}')
    p.add_argument("--model-doc-url", default="", help="vllm-ascend 模型文档 URL(仅记录核对来源)")
    p.add_argument("--expect-port", type=int, default=8080, help="期望监听端口(默认 8080)")
    p.add_argument("--tp-size", type=int, default=None, help="期望 TP(卡数)")
    p.add_argument("--dp-size", type=int, default=None, help="期望 DP(节点数)")
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
