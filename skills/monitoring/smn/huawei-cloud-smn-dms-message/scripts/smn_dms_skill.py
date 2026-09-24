#!/usr/bin/env python3
"""huawei-cloud-smn-dms-message — SMN/DMS notification & message queue skill entry.

Implements the 15 huawei_* actions using the hcloud KooCLI.
SMN maps to `hcloud SMN`; DMS has no `hcloud DMS` service, so the engine
(Kafka / RabbitMQ / RocketMQ) selects the actual KooCLI service.

Every run automatically sends a quality report via `skill-quality-cli` (installed by
`scripts/ensure_cli.sh`, pinned version with SHA256 verification) — fire-and-forget,
non-blocking, never changes the business output or exit code. When the whole
command is already wrapped with `skill-quality-cli run` (SKILL_TRACE_ID is set),
the script skips its own report to avoid double counting.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import time

ENGINE_SERVICE = {
    "kafka": "Kafka",
    "rabbitmq": "RabbitMQ",
    "rocketmq": "RocketMQ",
}

ENGINE_INTENT_ASKS = {
    "list_instances": "Which DMS engine? kafka/rabbitmq/rocketmq",
    "show_instance": "Which DMS engine? kafka/rabbitmq/rocketmq",
    "create_instance": "Which DMS engine? kafka/rabbitmq/rocketmq",
    "delete_instance": "Which DMS engine? kafka/rabbitmq/rocketmq",
}


def run_hcloud(args_list, region, preview=False):
    cmd = ["hcloud"] + args_list
    if region:
        cmd.append("--cli-region=%s" % region)
    if preview:
        print("[PREVIEW] " + " ".join(cmd))
        return ""
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    except subprocess.TimeoutExpired:
        raise RuntimeError("hcloud 命令超时")
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "").strip()
        raise RuntimeError("hcloud command failed (exit %s): %s" % (proc.returncode, err))
    return proc.stdout


def print_json(raw):
    try:
        print(json.dumps(json.loads(raw), ensure_ascii=False, indent=2))
    except ValueError:
        print(raw)


def require(value, label, argv):
    if not value:
        print("ERROR: missing required argument --%s" % label)
        print("usage: %s" % " ".join(argv))
        sys.exit(2)
    return value


def validate_engine(engine, argv):
    if engine not in ENGINE_SERVICE:
        print("ERROR: 未知 engine: %s,可选 kafka/rabbitmq/rocketmq" % engine)
        print("usage: %s" % " ".join(argv))
        sys.exit(2)
    return engine


def list_smn_topics(a):
    raw = run_hcloud(["SMN", "ListTopics"], a.region)
    print_json(raw)


def list_smn_subscriptions(a):
    args = ["SMN", "ListSubscriptions"]
    for opt in ("protocol", "status", "endpoint", "limit", "offset"):
        v = getattr(a, opt)
        if v:
            args.append("--%s=%s" % (opt, v))
    print_json(run_hcloud(args, a.region))


def list_smn_message_templates(a):
    args = ["SMN", "ListMessageTemplates"]
    for opt in ("message_template_name", "protocol", "limit", "offset"):
        v = getattr(a, opt)
        if v:
            args.append("--%s=%s" % (opt, v))
    print_json(run_hcloud(args, a.region))


def list_dms_instances(a):
    engine = (a.engine or "").lower()
    require(engine, "engine (kafka|rabbitmq|rocketmq)", sys.argv)
    validate_engine(engine, sys.argv)
    service = ENGINE_SERVICE[engine]
    op = "ListInstancesDetails" if engine == "rabbitmq" else "ListInstances"
    args = [service, op, "--engine=%s" % engine]
    for opt in ("limit", "offset", "name", "status", "instance_id"):
        v = getattr(a, opt)
        if v:
            args.append("--%s=%s" % (opt, v))
    print_json(run_hcloud(args, a.region))


def list_dms_topics(a):
    require(a.instance_id, "instance_id", sys.argv)
    args = ["Kafka", "ListInstanceTopics", "--instance_id=%s" % a.instance_id]
    for opt in ("limit", "offset"):
        v = getattr(a, opt)
        if v:
            args.append("--%s=%s" % (opt, v))
    print_json(run_hcloud(args, a.region))


def analyze_smn_subscription_confirmation(a):
    args = ["SMN", "ListSubscriptions"]
    for opt in ("protocol", "status", "topic_urn"):
        v = getattr(a, opt)
        if v:
            args.append("--%s=%s" % (opt, v))
    raw = run_hcloud(args, a.region)
    data = json.loads(raw)
    subs = data.get("subscriptions", [])
    unconfirmed = [s for s in subs if s.get("status") == 0]
    print_json(raw)
    print("ANALYSIS: total subscriptions=%d, unconfirmed=%d" % (len(subs), len(unconfirmed)))
    if unconfirmed:
        print("  -> HTTP/HTTPS: run huawei_confirm_smn_subscription with the ping-back token;")
        print("  -> email: user must click the confirmation link sent to the mailbox.")
    return data


def analyze_dms_instance_status(a):
    engine = (a.engine or "").lower()
    require(engine, "engine (kafka|rabbitmq|rocketmq)", sys.argv)
    validate_engine(engine, sys.argv)
    service = ENGINE_SERVICE[engine]
    op = "ListInstancesDetails" if engine == "rabbitmq" else "ListInstances"
    raw = run_hcloud([service, op, "--engine=%s" % engine], a.region)
    data = json.loads(raw)
    instances = data.get("instances", [])
    print_json(raw)
    print("ANALYSIS: %d instances found" % len(instances))
    unhealthy = [i for i in instances if i.get("status") and i.get("status") != "RUNNING"]
    print("  -> non-RUNNING instances: %d (check status/storage/restart state)" % len(unhealthy))
    return data


def create_smn_topic(a):
    require(a.name, "name", sys.argv)
    args = ["SMN", "CreateTopic", "--name=%s" % a.name,
            "--display_name=%s" % (a.display_name or "")]
    if a.enterprise_project_id:
        args.append("--enterprise_project_id=%s" % a.enterprise_project_id)
    print_json(run_hcloud(args, a.region, preview=a.preview))


def add_smn_subscription(a):
    require(a.topic_urn, "topic_urn", sys.argv)
    require(a.protocol, "protocol", sys.argv)
    require(a.endpoint, "endpoint", sys.argv)
    args = ["SMN", "AddSubscription", "--topic_urn=%s" % a.topic_urn,
            "--protocol=%s" % a.protocol, "--endpoint=%s" % a.endpoint]
    if a.remark:
        args.append("--remark=%s" % a.remark)
    print_json(run_hcloud(args, a.region, preview=a.preview))


def create_smn_message_template(a):
    require(a.message_template_name, "message_template_name", sys.argv)
    require(a.content, "content", sys.argv)
    args = ["SMN", "CreateMessageTemplate",
            "--message_template_name=%s" % a.message_template_name,
            "--content=%s" % a.content]
    if a.protocol:
        args.append("--protocol=%s" % a.protocol)
    print_json(run_hcloud(args, a.region, preview=a.preview))


def publish_smn_message(a):
    require(a.topic_urn, "topic_urn", sys.argv)
    args = ["SMN", "PublishMessage", "--topic_urn=%s" % a.topic_urn]
    if a.message:
        args.append("--message=%s" % a.message)
    if a.subject:
        args.append("--subject=%s" % a.subject)
    if a.message_template_name:
        args.append("--message_template_name=%s" % a.message_template_name)
    if a.message_structure:
        args.append("--message_structure=%s" % a.message_structure)
    if a.time_to_live:
        args.append("--time_to_live=%s" % a.time_to_live)
    print_json(run_hcloud(args, a.region, preview=a.preview))


def create_dms_instance(a):
    engine = (a.engine or "").lower()
    require(engine, "engine (kafka|rabbitmq|rocketmq)", sys.argv)
    validate_engine(engine, sys.argv)
    service = ENGINE_SERVICE[engine]
    if engine == "kafka":
        op = "CreatePostPaidKafkaInstance"
    elif engine == "rabbitmq":
        op = "CreatePostPaidInstanceByEngine"
    else:
        op = "CreateInstanceByEngine"
    args = [service, op, "--engine=%s" % engine,
            "--name=%s" % a.name, "--engine_version=%s" % a.engine_version,
            "--product_id=%s" % a.product_id,
            "--available_zones.1=%s" % a.available_zones,
            "--vpc_id=%s" % a.vpc_id, "--subnet_id=%s" % a.subnet_id,
            "--security_group_id=%s" % a.security_group_id,
            "--storage_space=%s" % a.storage_space,
            "--storage_spec_code=%s" % a.storage_spec_code]
    if engine in ("kafka", "rocketmq"):
        args.append("--broker_num=%s" % a.broker_num)
    if engine == "rabbitmq":
        args.append("--access_user=%s" % a.access_user)
        args.append("--password=%s" % a.password)
    if a.description:
        args.append("--description=%s" % a.description)
    print_json(run_hcloud(args, a.region, preview=a.preview))


def delete_smn_topic(a):
    require(a.topic_urn, "topic_urn", sys.argv)
    print_json(run_hcloud(["SMN", "DeleteTopic", "--topic_urn=%s" % a.topic_urn],
                          a.region, preview=a.preview))


def confirm_smn_subscription(a):
    require(a.token, "token", sys.argv)
    args = ["SMN", "ConfirmSubscription", "--token=%s" % a.token]
    if a.topic_urn:
        args.append("--topic_urn=%s" % a.topic_urn)
    if a.endpoint:
        args.append("--endpoint=%s" % a.endpoint)
    print_json(run_hcloud(args, a.region, preview=a.preview))


def delete_dms_instance(a):
    engine = (a.engine or "").lower()
    require(engine, "engine (kafka|rabbitmq|rocketmq)", sys.argv)
    validate_engine(engine, sys.argv)
    service = ENGINE_SERVICE[engine]
    require(a.instance_id, "instance_id", sys.argv)
    print_json(run_hcloud([service, "DeleteInstance",
                           "--instance_id=%s" % a.instance_id], a.region, preview=a.preview))


ACTIONS = {
    "huawei_list_smn_topics": list_smn_topics,
    "huawei_list_smn_subscriptions": list_smn_subscriptions,
    "huawei_list_smn_message_templates": list_smn_message_templates,
    "huawei_list_dms_instances": list_dms_instances,
    "huawei_list_dms_topics": list_dms_topics,
    "huawei_analyze_smn_subscription_confirmation": analyze_smn_subscription_confirmation,
    "huawei_analyze_dms_instance_status": analyze_dms_instance_status,
    "huawei_create_smn_topic": create_smn_topic,
    "huawei_add_smn_subscription": add_smn_subscription,
    "huawei_create_smn_message_template": create_smn_message_template,
    "huawei_publish_smn_message": publish_smn_message,
    "huawei_create_dms_instance": create_dms_instance,
    "huawei_delete_smn_topic": delete_smn_topic,
    "huawei_confirm_smn_subscription": confirm_smn_subscription,
    "huawei_delete_dms_instance": delete_dms_instance,
}


def build_parser():
    p = argparse.ArgumentParser(prog="smn_dms_skill.py",
                                description="huawei-cloud-smn-dms-message actions dispatcher")
    p.add_argument("action", choices=sorted(ACTIONS.keys()))
    p.add_argument("--region", default=os.environ.get("HUAWEICLOUD_SDK_REGION", ""),
                   help="Huawei Cloud region")
    p.add_argument("--preview", action="store_true",
                   help="print the hcloud command without executing it (R2/R1 confirmation)")
    p.add_argument("--name", help="topic/instance/template name")
    p.add_argument("--display_name", help="topic display name")
    p.add_argument("--enterprise_project_id", help="enterprise project ID")
    p.add_argument("--topic_urn", help="SMN topic resource identifier")
    p.add_argument("--protocol", help="subscription/template protocol")
    p.add_argument("--endpoint", help="subscription endpoint or confirm endpoint")
    p.add_argument("--remark", help="subscription remark")
    p.add_argument("--message_template_name", help="message template name")
    p.add_argument("--content", help="template content / message content")
    p.add_argument("--message", help="message payload")
    p.add_argument("--subject", help="email subject")
    p.add_argument("--message_structure", help="JSON message structure")
    p.add_argument("--time_to_live", help="message retention in seconds")
    p.add_argument("--token", help="subscription confirmation token")
    p.add_argument("--engine", help="DMS engine kafka|rabbitmq|rocketmq")
    p.add_argument("--instance_id", help="DMS instance ID")
    p.add_argument("--engine_version", help="instance engine version")
    p.add_argument("--product_id", help="instance product/flavor ID")
    p.add_argument("--available_zones", help="zone ID, used as available_zones.1")
    p.add_argument("--vpc_id", help="VPC ID")
    p.add_argument("--subnet_id", help="subnet ID")
    p.add_argument("--security_group_id", help="security group ID")
    p.add_argument("--storage_space", help="storage space in GB")
    p.add_argument("--storage_spec_code", help="storage spec code")
    p.add_argument("--broker_num", help="number of brokers (Kafka/RocketMQ)")
    p.add_argument("--access_user", help="RabbitMQ access user")
    p.add_argument("--password", help="RabbitMQ password")
    p.add_argument("--description", help="instance description")
    p.add_argument("--limit", help="max records to return")
    p.add_argument("--offset", help="result offset")
    p.add_argument("--status", help="filter by status")
    return p


def _resolve_quality_cli():
    """Resolve the skill-quality-cli invocation, in priority order:
    0. `SKILL_QUALITY_CLI_HOME` (explicit dir containing `cli_entry.py` or `skill-quality-cli`)
    1. `skill-quality-cli` on PATH (after ensure_cli.sh + PATH export)
    2. `~/.local/bin/skill-quality-cli` (ensure_cli.sh install dir, even when not on PATH)
    Returns an argv list, or None when no carrier exists.
    """
    home = os.environ.get("SKILL_QUALITY_CLI_HOME")
    if home:
        entry = os.path.join(home, "cli_entry.py")
        if os.path.isfile(entry):
            return [sys.executable, entry]
        exe = os.path.join(home, "skill-quality-cli")
        if os.path.isfile(exe) and os.access(exe, os.X_OK):
            return [exe]
    exe = shutil.which("skill-quality-cli")
    if exe:
        return [exe]
    local = os.path.expanduser("~/.local/bin/skill-quality-cli")
    if os.path.isfile(local) and os.access(local, os.X_OK):
        return [local]
    return None


def report_quality(status, error_code=None, error_msg=None, cost_ms=None):
    """Fire-and-forget quality report via skill-quality-cli (unified CLI).

    Hard-bound to the dispatch main flow: called on every run (success, usage
    error, or exception) so a report can never be skipped by running the bare
    script. Failing reporting never blocks or changes the business output /
    exit code.

    Skipped when:
      - SKILL_QUALITY_DISABLE=1 (explicit opt-out),
      - SKILL_TRACE_ID is already set (the whole command is wrapped with
        `skill-quality-cli run`, which reports once itself — avoid double counting).
    """
    if os.environ.get("SKILL_QUALITY_DISABLE") == "1":
        return False
    if os.environ.get("SKILL_TRACE_ID"):  # already wrapped in `skill-quality-cli run`
        return True
    argv = _resolve_quality_cli()
    if not argv:
        return False
    cmd = argv + ["--no-auto-upgrade", "report",
                  "--skill-name", "huawei-cloud-smn-dms-message",
                  "--status", status]
    if error_code:
        cmd += ["--error-code", error_code]
    if error_msg:
        cmd += ["--error-msg", error_msg[:500]]
    if cost_ms is not None:
        cmd += ["--cost-ms", str(int(cost_ms))]
    try:
        # Truly fire-and-forget: detach the report subprocess and never wait,
        # so an unreachable/slow quality endpoint can never block the main flow.
        subprocess.Popen(cmd, stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL, start_new_session=True)
        return True
    except Exception:  # noqa: BLE001 - fire-and-forget
        return False


def main():
    t0 = time.monotonic()
    parser = build_parser()
    try:
        args = parser.parse_args()
        if not args.region:
            print("INFO: no --region supplied, the command will use the hcloud profile region.")
        if not os.environ.get("HUAWEICLOUD_SDK_AK") and not _has_hcloud_profile():
            print("WARNING: no HUAWEICLOUD_SDK_AK/SK env and no hcloud profile detected; "
                  "the command will use the local hcloud default profile.")
        ACTIONS[args.action](args)
    except SystemExit:
        # argparse usage errors / require() / validate_engine() — business failure
        report_quality("biz_fail", error_code="U02",
                       error_msg="missing required argument or invalid engine",
                       cost_ms=int((time.monotonic() - t0) * 1000))
        raise
    except RuntimeError as exc:
        # hcloud non-zero exit / timeout / network issues — system failure
        print("ERROR: %s" % exc, file=sys.stderr)
        report_quality("sys_fail", error_code="B01", error_msg=str(exc),
                       cost_ms=int((time.monotonic() - t0) * 1000))
        sys.exit(1)
    except Exception as exc:  # noqa: BLE001 - report and re-raise as failure
        print("ERROR: %s" % exc, file=sys.stderr)
        report_quality("sys_fail", error_code="B01", error_msg=str(exc),
                       cost_ms=int((time.monotonic() - t0) * 1000))
        sys.exit(1)
    else:
        report_quality("success", cost_ms=int((time.monotonic() - t0) * 1000))


def _has_hcloud_profile():
    try:
        out = subprocess.run(["hcloud", "configure", "list", "--cli-output=json"],
                             capture_output=True, text=True, timeout=60).stdout
    except Exception:
        out = ""
    if out.strip():
        try:
            data = json.loads(out)
            if isinstance(data, dict):
                profiles = data.get("profiles")
                if profiles:
                    return True
                current = data.get("current")
                if current:
                    return True
            return False
        except ValueError:
            pass
    try:
        out = subprocess.run(["hcloud", "configure", "list"],
                             capture_output=True, text=True, timeout=60).stdout
        return "default" in out
    except Exception:
        return False


if __name__ == "__main__":
    main()