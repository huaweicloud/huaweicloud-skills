"""注册验证标记（子串匹配）。

SMS-Agent 注册成功后会在 SmsAgent_Info.log 写入以下 5 个标记子串；
验证阶段（VerifyPhase）与 Py2 配置阶段（ConfigurePy2Phase）共用同一组，
避免字面量在两处重复导致漂移。
"""
# 注册成功标记（小写子串）
MARKER_SUBSTRINGS = [
    "as/sk",              # AK/SK 校验
    "upload os info",     # 上传 OS 信息
    "upload source info", # 上传源端信息
    "schedule task",      # 启动定时任务
    "heart beat",         # 启动心跳
]

# 对应 ConfigurePy2Phase._check_registration() 返回字典的 key（保持兼容）
MARKER_KEYS = [
    "ak_sk_check",
    "upload_os_info",
    "upload_system_info",
    "schedule_task",
    "heart_beat",
]
