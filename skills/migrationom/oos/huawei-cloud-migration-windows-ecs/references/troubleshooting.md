# Windows 迁移排障手册与问题处理集

> 本文件是迁移问题的**统一处理集**（问题 → 根因 → 修复 + 代码位置）与**排障操作手册**（现象 → 排查步骤 → 可执行命令）的合并文档，单一来源；只在各 MD 引用本文件，不在其他文档重复记录问题。
>
> 使用方式：
> - **第一部分**：理解已解决问题、定位代码位置（开发/维护视角）；
> - **第二部分**：迁移现场出故障时按症状逐条排查（运维视角）。
>
> 关联文档：71 条安全规则与红线见 [`safety-rules.md`](./safety-rules.md)；迁移流程详解见 [`migration-workflow.md`](./migration-workflow.md)。

---

## 第一部分 · 问题 → 修复归档（按领域，含代码位置）

### 1. 源端部署与 Agent 配置

#### 1.1 迁移前源端残留未清理
- **问题**：重复迁移时旧 Agent 进程/计划任务/安装目录/`sms_domain.txt` 残留，导致新注册失败；Py2 Agent 交互被 "use last time?" 带偏（而非直接要 domain）。
- **根因**：Agent 会读取上次运行的残留状态，新旧状态混淆。
- **修复**：阶段链固化"部署前必清源端"（`phases/cleanup_source_phase.py` + `cleanup_windows.py`，幂等可重复）；环境清理按 ①打通 gost → ②清源端 → ③清代理 顺序执行（`cleanup_environment.py`）。

#### 1.2 Py3 GUI Agent 无交互桌面会话
- **问题**：无桌面会话（explorer/Session>0）时 AutoIt GUI 任务静默不执行——进程在、日志停写、控制台永远看不到源端（"假死"）。
- **根因**：WinRM 运行在 Session 0，看不到 GUI；GUI Agent 必须在 Session 1（已登录桌面）操作。
- **修复**：计划任务补 `/it`+`/ru` 投递到 Session 1；ConfigurePhase 配置前硬校验交互桌面会话，无则快速失败、超时抛异常（`phases/configure_phase.py`）。

#### 1.3 手动 `schtasks /run` 触发 `.secrets.dat` 一次性删除
- **问题**：手动执行计划任务后，日志出现 `invalid AK or SK`、控制台 `connected=false`、预检 0/14（"假成功未注册"）。
- **根因**：ConfigurePhase 写入的 `.secrets.dat` 是**一次性文件**（AutoIt/exe 读取后自动删除）；手动 `/run` 时 secrets 已缺失 → 配置程序读到空 Domain/企业项目。
- **修复**：secrets 写入后**回读校验**（AK/SK/Domain/EP 非空）+ bat 前置守卫；注册异常时只允许走官方恢复入口 `agent_recover.py`（重建 secrets → 重传 exe → 重建计划任务 → 自动 Verify）；VerifyPhase 按日志尾部（最近 100 行）致命错误判失败（`phases/configure_phase.py`、`agent_recover.py`、`phases/verify_phase.py`）。

#### 1.4 Py2 英文 OS + 中文企业项目名
- **问题**：SMS-Agent（Python 2 内部）在英文 Windows 上无法解析 API 返回的中文 EP 名，跳过 EP 选择并注册到 `default`。
- **根因**：工具层面无法修复（Agent 内部编码问题）。
- **修复**：非中文 OS 遇中文 EP 名时 `agent_config.cs` 主动预置 `default` 并记录日志，避免状态机错乱；注册后请手动调整企业项目归属或改用 Py3 方案。

#### 1.5 迁移前环境变量未配置
- **问题**：`migration_Access_Key / migration_Secret_Access_Key / migration_password / migration_domain / Host_Information` 缺失时，迁移编排半途失败或查错租户。
- **根因**：凭据/主机信息依赖环境变量注入，未配置无从执行。
- **修复**：`preflight_check.py` 独立检查；`unified_migrate.py` 启动自动拦截并提醒客户先配置，`--skip-preflight` 为逃生口（仅当所有参数已内嵌 migrate.yaml）。

### 2. 迁移任务控制面（SMS 错误码）

#### 2.1 SMS.0515 磁盘物理卷不匹配
- **问题**：`start` 后很快 `MIGRATE_FAIL`，`error_json={"error_code":"SMS.0515"}`；源端 Agent 日志 `_check_vol_param: source_vols_map={...} target_vols_map={}`；子任务卡在 `SSL_CONFIG`。
- **根因**：创建任务时 `target_server.disks[].physical_volumes` 未传（或 uuid 格式无效）→ 目标卷映射为空。
- **修复**：磁盘块必须完整携带 `physical_volumes`（name/device_use/size/used_size/uuid/file_system/index），uuid 用源端装饰格式；数量不匹配时拒绝创建（`sms_task.py::_attach_disk_mapping`）。

#### 2.2 SMS.9001 Invalid parameters + KooCLI 反斜杠转义
- **问题**：带 `physical_volumes` 的磁盘块创建任务报 `SMS.9001`；逐字段隔离发现与 `uuid`（及 `C:\` 名称）有关。
- **根因**：**KooCLI 会把参数值中的反斜杠当作转义符**，Windows 卷 uuid `\\?\Volume{...}\` 传进去即被破坏。
- **修复**：传给 hcloud 前把反斜杠翻倍（`\` → `\\`），KooCLI 反转义后还原（`sms_task.py::_escape_hcloud`）。

#### 2.3 SMS.6033 目标端磁盘信息缺失
- **问题**：磁盘块带 PV 但字段不完整时创建被拒。
- **根因**：PV 结构缺关键信息（uuid 缺失/乱格式，或 PV 数量与源端不齐）。
- **修复**：按源端 `init_target_server.disks` 完整对齐 PV 字段（含 uuid、used_size、fs、index）（`sms_task.py::_attach_disk_mapping`）。

#### 2.4 SMS.7711 任务名非法
- **问题**：部分任务名创建被拒（长名如 `migrate_windows_xyz_时间戳` 也中招）。
- **根因**：SMS 任务名有隐藏校验，长名/特定字符组合被拒。
- **修复**：任务名 ≤16 字符、仅 中文/字母/数字/下划线/短横线、禁连续双下划线，创建前校验拦截（`sms_task.py::_validate_task_name`）。

#### 2.5 SMS.7605 目的端已被其他任务占用
- **问题**：同一目标 ECS 反复创建任务时被拒。
- **根因**：失败/遗留任务仍占用目标机。
- **修复**：先删除旧任务（`sms_task.py delete --task-id <id> --yes`）再创建；`cmd_create` 幂等保护，源端已有任务时拒绝重复创建（`--force` 强来）。

#### 2.6 子任务数量 4 个 vs 6/7 个
- **问题**：`syncing=true` 的任务只有 4 个子任务（SSL_CONFIG / ATTACH_AGENT_IMAGE / FORMAT_DISK_WINDOWS / MIGRATE_WINDOWS_BLOCK），是否正常？
- **根因**：SMS 按 `syncing` 决定工作流长度：`syncing=true`=4 个；`syncing=false`=6 个；再加 `is_need_consistency_check=true`=7 个（CHECK_CONSISTENCY）。
- **修复**：当前默认 `syncing=false` + `is_need_consistency_check=true`（7 子任务：.../CONFIGURE_WINDOWS/CONSISTENCY_CHECK/DETTACH_AGENT_IMAGE）；持续同步模式下 Agent 镜像保持挂载，为正常现象。

#### 2.7 传参顺序契约：磁盘顺序错位
- **问题**：多数据盘场景下，目的端卷按设备名/扫描顺序配对，把 60GB 目标盘配给 40GB 源数据盘，或数据盘排到系统盘前面，导致磁盘归属错乱（SMS.0515 或复制错位）。
- **根因**：`target_server.disks.N` 的序号就是 SMS 判定磁盘归属的依据；迁移运行中会多一块 `SMS_Temp_Disk` 临时盘占位 `/dev/vda`，带偏系统盘识别。
- **修复**：目的端卷先剔除 `SMS_Temp_Disk`；系统盘识别优先级 `OS-EXT-SRV-ATTR:root_device_name` → EVS `bootable=true` → 设备名最小；最终 `disks.1=系统盘`、`disks.2..N=数据盘`（容量升序同序配对，目标≥源端）；任何"数量不匹配/容量不足/映射[0] 非系统盘"→ 拒绝创建并断言（`sms_task.py::_attach_disk_mapping`）。

#### 2.8 SMS.1913 迁移中新增磁盘
- **问题**：复制阶段（MIGRATE_WINDOWS_BLOCK 开始）报 `MIGRATE_FAIL / SMS.1913`；源端日志 `Get current task status error: 1013 → 1913`。
- **根因**：源端 Windows 迁移过程中 IO 监控驱动运行，期间给源端新增磁盘，新盘增量数据无法被 IO 监控捕获。
- **修复**：加盘应在**迁移开始前或源端停机期**完成；若新盘无需同步，改 `C:\SMS-Agent-Py3\config\g-property.cfg` 中 `enable_check_monitor_disk=False` 后删除旧任务重建（注意新盘数据将不被同步）。

#### 2.9 公网/私网切换参数混乱
- **问题**：公网/私网迁移在任务创建层的差异参数多，易配错。
- **根因**：目标端 EIP/私网 IP、迁移 IP 来源随场景不同。
- **修复**：创建任务时只需 `use_public_ip` 与 `migration_ip` 两个参数体现差异；`migration_ip` 留空自动推导——公网取 prepare-target 写入的 `eip_address`、私网取 `private_ip`（`sms_task.py::_build_create_params`）；`prepare-target` 私网自动跳过 EIP 创建。

### 3. 目标端编排

#### 3.1 目标规格误选 ARM（鲲鹏）机
- **问题**：自动匹配规格时选中 `ac7.large.2`（鲲鹏 ARM），无法承载 Windows。
- **根因**：规格匹配未排除 ARM 系列。
- **修复**：过滤 ARM 前缀规格（`ac/kc/ks/ka/km/kk/cq`），按源端 CPU/内存精确匹配优先（`core/target_provider.py::plan_flavor`）。

#### 3.2 可用区无默认导致建错区域
- **问题**：代码层默认 `cn-north-4a` 会让非北京四区域静默建机。
- **根因**：可用区兜底值跨区域不适用。
- **修复**：移除默认值，`sms_task.target_az` 必填，缺失即报 `ConfigError`（`core/target_provider.py::plan_az`）。

#### 3.3 EIP 创建权限不足 / 复用优先
- **问题**：`prepare-target` 创建 EIP 报 `vpc:publicIps:create` 无权限。
- **根因**：AK/SK 用户缺 EIP 创建权限。
- **修复**：优先复用指定 `eip_id` 或空闲未绑定（`status=DOWN`）EIP；无权限时提示授权或指定 EIP（`core/target_provider.py::prepare_eip`）。

#### 3.4 幂等重跑与孤儿资源
- **问题**：多次失败重跑会产生孤儿安全组/临时 ECS/测试任务。
- **根因**：创建类操作缺少复用逻辑。
- **修复**：VPC/子网按 CIDR 复用、安全组按固定名复用、ECS 按固定名（`target_name`）复用、EIP 查已绑定；测试任务立即删除（`core/target_provider.py`、`sms_task.py::cmd_create`）。

#### 3.5 安装包配置缺失
- **问题**：`download.packages` 未配置时静默使用默认文件名，下载失败难定位。
- **根因**：配置缺省掩盖错误。
- **修复**：安装包缺失时抛 `ConfigError` 明确报错，不静默兜底（`core/config.py`）。

### 4. 私网环境与网络

#### 4.1 Squid 默认开放代理
- **问题**：Squid 默认开放会成为开放代理，且私网复制失败时难排查。
- **根因**：ACL 过宽、CONNECT 隧道未收敛。
- **修复**：Squid CONNECT 仅放行迁移端口 22/8899/8900/443、默认仅放行 RFC1918 内网；私网复制失败先查代理 `access.log` 是否 `TCP_DENIED`（`proxyopt/scripts/proxy_setup_squid.sh`）。

#### 4.2 gost 配置注入风险
- **问题**：gost 配置解析使用 eval 存在注入风险。
- **根因**：shell 拼接执行配置内容。
- **修复**：配置解析去 `eval`，用 python 读 yaml 导出环境变量（`proxyopt/scripts/proxy_setup_gost.sh`）。

#### 4.3 私网环境清理顺序
- **问题**：私网下"先清理再迁移"的旧流程必失败——清源端需要经 gost 走 WinRM，而 gost 尚未建立。
- **根因**：清理顺序违反网络依赖。
- **修复**：环境清理按 ①打通 gost → ②清源端 → ③清代理 执行（`cleanup_environment.py`）；`unified_migrate.py` 阶段链同样先建 WinRM（私网经 gost）再清残留。

#### 4.4 沙箱出口网络探测误导
- **问题**：TCP 直连源端 5985 多次超时，误判"沙箱不能出公网"。
- **根因**：沙箱出口是白名单代理；`/dev/tcp` 直连绕过代理；安全组放行有时序。
- **修复**：用真实业务路径做最终判断（工具实际连接成功为准），对探测结论保持谨慎。

### 5. 安全与属主

#### 5.1 安全组 0.0.0.0/0 全放通
- **问题**：既有安全组含 `0.0.0.0/0` 入方向，或配置 `sg_source_cidrs` 含全网段。
- **根因**：最小权限原则被绕过。
- **修复**：代码硬拒绝复用/创建任何含 `0.0.0.0/0` 的安全组；`sg_source_cidrs` 含 `0.0.0.0/0` 直接配置报错；仅放行 22/8899/8900（`core/target_provider.py::_assert_no_global_sg / _assert_cidrs_ok`）。

#### 5.2 非本 skill 资源被误改/误删
- **问题**：账号内混有其他资源时，迁移编排可能误改/误删非本 skill 创建的资源。
- **根因**：缺少属主标识。
- **修复**：OwnerID 指纹（`base32(HMAC(ak, SALT‖project_id))[:8]`）+ Tags/名称/会话清单三重判属主；O1-O6 红线：非属主只读复用、删除类操作须属主 + 显式确认（`core/ownership.py`）。

#### 5.3 凭据泄露风险
- **问题**：AK/SK、密码可能出现在日志、配置文件、Git。
- **根因**：凭据处理不严。
- **修复**：hcloud 调用经环境变量注入 `--cli-access-key/--cli-secret-key` 不落盘；debug 日志 AK 打码；Py2 `watchdog.ps1` 上传后收紧 ACL（SYSTEM/Administrators）；`.secrets.dat` 一次性文件读取即删；日志/报告不记录明文密码（`core/sms_client.py`、`phases/configure_py2_phase.py`）。

### 6. 工具兼容与输入

#### 6.1 KooCLI 不支持部分枚举/接口
- **问题**：`StartServer` 不存在；`UpdateTaskStatus` 枚举仅支持 start/stop/test/…/migration_test，不含 syncing/cutover；`ListServerVolumeAttachments` 实测可能返回空。
- **根因**：KooCLI 7.2.x 建模与官方 API 不完全一致。
- **修复**：启动目的端改用 `BatchStartServers`（嵌套参数 `--os-start.servers.N.id`，`core/sms_client.py::ecs_start`）；磁盘挂载校验增加 EVS `ListVolumes --server_id` fallback（`ecs_volumes`）；`sync` 在任务已 MIGRATE_SUCCESS 时自动跳过、`cutover` 自动回退为"启动目的端 ECS"（等效割接）（`sms_task.py::cmd_sync/cmd_cutover`）。

#### 6.2 hcloud 多版本提示行破坏 JSON
- **问题**：`ListPublicips` 总返回 0 条（误报，账号实际有多个 EIP）。
- **根因**：KooCLI 对多版本 API 在 stdout 打印 `ListPublicips有多个版本...` 提示行后再输出 JSON。
- **修复**：JSON 解析先定位首个 `{`（`core/sms_client.py::_call`）。

#### 6.3 hcloud 列表参数与按 id 过滤
- **问题**：`--security_group_id=xxx` 报"不正确的参数"；`ListServersDetails --id=...` 报错。
- **根因**：KooCLI 列表参数需 `.N` 下标格式；`ListServersDetails` 不支持按 id 过滤。
- **修复**：客户端自动把 list 值展开为 `--k.1=...`；查 ECS 详情改为全量列表后内存过滤（`core/sms_client.py::_call`、`core/target_provider.py::_find_ecs_by_id`）。

#### 6.4 OBS 对象键含空格/路径与文档不一致
- **问题**：文档给的对象键不存在；真实对象键含空格（如 `SMS-Agent-Py3 (1).exe`）。
- **根因**：包分发目录结构与文档不同。
- **修复**：`obsutil ls` 实际确认对象键；配置中直接用真实键（`config/migrate.yaml download.packages.sms_agent.obs_uri`）。

#### 6.5 源端上报内网 IP vs 公网 IP
- **问题**：用源端公网 IP 查不到 SMS 源端记录。
- **根因**：Agent 上报的是源端内网 IP。
- **修复**：按名称/连接状态发现，或显式配置 `sms_task.source_server_id`（多源端时必须）（`core/sms_client.py::find_source_server`）。

### 7. 其他

#### 7.1 官网 PDF 下载被安全验证拦截
- **问题**：`sms-api-pdf.pdf` 直链返回 Security Verification 页面。
- **根因**：华为云文档站反爬（JS challenge）。
- **修复**：带 Referer（下载页）+ Cookie 会话可下载；本地无浏览器时以 `hcloud SMS xxx --help`（官方建模）为参。

#### 7.2 错误被静默吞掉
- **问题**：SMS.xxxx / Ecs.xxxx 错误被吞掉，排障困难。
- **根因**：调用层未上抛。
- **修复**：错误不静默——统一走异常层级抛给调用方，携带 error_code 与 detail（`core/exceptions.py`）。

---

## 第二部分 · 排障手册（按症状，含可执行命令）

### 1. WinRM连接问题

#### 1.1 WinRM连接超时

**现象**: `WinRMConnectionError: Connection timed out`

**排查步骤**:
1. 确认源端IP可达：`ping <source_ip>`
2. 确认WinRM端口开放：`telnet <source_ip> 5985`
3. 确认WinRM服务运行：`Get-Service WinRM`（在源端执行）
4. 确认防火墙规则：`Get-NetFirewallRule -DisplayName "WinRM*"`

**解决方案**:
```powershell
# 在源端执行
Enable-PSRemoting -Force
winrm quickconfig -q
netsh advfirewall firewall add rule name="WinRM-HTTP" dir=in action=allow protocol=TCP localport=5985
```

#### 1.2 WinRM认证失败

**现象**: `WinRMError: 401 Unauthorized`

**排查步骤**:
1. 确认用户名密码正确
2. 确认用户属于Administrators组
3. 确认Basic认证已启用

**解决方案**:
```powershell
winrm set winrm/config/service/auth '@{Basic="true"}'
winrm set winrm/config/client/auth '@{Basic="true"}'
winrm set winrm/config/service '@{AllowUnencrypted="true"}'
```

> ⚠️ `AllowUnencrypted`/HTTP(5985) 为明文，仅限内网/测试环境；生产优先 HTTPS(5986)（见 `safety-rules.md` 3.4）。

#### 1.3 WinRM内存限制

**现象**: `WinRMError: The WS-Management service cannot process the request`

**解决方案**:
```powershell
winrm set winrm/config/winrs '@{MaxMemoryPerShellMB="2048"}'
# 重启WinRM服务
Restart-Service WinRM
```

### 2. SMS Agent问题

#### 2.1 Agent安装失败

**现象**: Agent安装后服务无法启动

**排查步骤**:
1. 检查.NET Framework版本：`Get-ChildItem 'HKLM:\SOFTWARE\Microsoft\NET Framework Setup\NDP'`
2. 检查安装日志：`Get-Content "C:\Program Files\CloudSMS\agent\logs\install.log"`
3. 检查端口占用：`netstat -an | findstr :8090`

**解决方案**:
- 升级.NET Framework到4.5+
- 释放被占用的端口
- 以管理员权限重新安装

#### 2.2 Agent无法连接SMS服务端

**现象**: Agent日志显示连接超时或拒绝

**排查步骤**:
1. 测试网络：`Test-NetConnection sms.cn-north-4.myhuaweicloud.com -Port 443`
2. 检查代理设置：`netsh winhttp show proxy`
3. 检查DNS：`nslookup sms.cn-north-4.myhuaweicloud.com`

#### 2.3 Agent服务异常停止

**现象**: SMSAgentService频繁停止

**排查步骤**:
1. 查看Windows事件日志：`Get-EventLog -LogName Application -Source "SMSAgent*" -Newest 20`
2. 查看Agent错误日志：`Get-Content "C:\Program Files\CloudSMS\agent\logs\error.log" -Tail 50`
3. 检查磁盘空间：`Get-PSDrive C`

#### 2.4 手动跑计划任务导致 invalid AK or SK（实测）

**现象**: 直接 `schtasks /run /tn ConfigureSMSAgent` 后，SMS 控制台源端 `connected=false`、预检 0/14，
Configure 日志尾部出现 `invalid AK or SK`，但旧版 Verify 曾误报"注册成功(需复查)"。

**根因**: ConfigurePhase 写入的 `.secrets.dat` 是**一次性文件**——AutoIt/预编译 exe 读取后自动删除。
手动 `/run` 时 secrets 已缺失 → AutoIt 读到空 Domain/企业项目 → 视为"配置成功"却未真正注册（假成功）。

**修复（不要手动 /run，跑官方恢复入口）**:
```bash
cd scripts/windows_migration
python3 agent_recover.py --scenario private --config config/migrate.yaml   # 私网；公网用 public
```
该入口重建 `.secrets.dat`（写入后回读校验 AK/SK/Domain/EP）→ 重传 exe → 重建计划任务 → 自动 Verify；
按"日志尾部(最近100行)仍有致命错误"判失败，避免误报。退出码 0 = 恢复成功，随后
`hcloud SMS ListServers` 应显示 connected=true、checks 14/14。

**防御**: 配置 bat 已加前置守卫，secrets 缺失时快速失败并打印
`[SECRETS_MISSING] .secrets.dat missing, run: python3 agent_recover.py`。

### 3. 迁移任务问题

#### 3.1 迁移任务卡在"同步中"

**现象**: 任务长时间停留在"同步中"状态，进度不更新

**排查步骤**:
1. 检查源端Agent状态：`Get-Service SMSAgentService`
2. 检查源端网络带宽
3. 检查源端磁盘I/O：`Get-Counter '\PhysicalDisk(_Total)\% Disk Time'`
4. 查看SMS任务详情：`hcloud SMS ShowTask --id <task_id>`

**解决方案**:
- 重启Agent服务：`Restart-Service SMSAgentService`
- 检查网络是否中断
- 如果数据量过大，增加超时时间

#### 3.2 块级迁移失败

**现象**: `MIGRATE_BLOCK`任务失败，错误码`SMS.0304`

**原因**: Windows块级迁移需要源端VSS（Volume Shadow Copy Service）支持

**解决方案**:
```powershell
# 检查VSS服务
Get-Service VSS

# 启动VSS服务
net start VSS

# 设置VSS自动启动
Set-Service VSS -StartupType Manual

# 检查VSS Writer状态
vssadmin list writers
```

#### 3.3 迁移后Windows无法启动

**现象**: ECS启动后蓝屏或无法进入系统

**常见原因**:
1. 源端使用了不兼容的驱动程序
2. 系统盘分区格式不正确
3. 引导配置损坏
4. UEFI/Legacy BIOS 引导模式不匹配
5. KVM 驱动未正确安装
6. 内存大小识别异常

**解决方案**:
- 迁移前卸载不必要的第三方驱动
- 使用SMS控制台的"启动修复"功能
- 确认源端引导模式（UEFI/BIOS）与目标 ECS 一致
- 安装华为云 KVM 驱动（virtio 驱动）
- 检查目标 ECS 内存是否正确识别
- 联系华为云技术支持

#### 3.4 蓝屏问题（BSOD）

**现象**: 迁移后 ECS 启动蓝屏，错误代码如 0x0000007B

**原因**: 源端存储驱动与华为云 KVM 虚拟化不兼容

**解决方案**:
- 迁移前在源端安装华为云 CCI/ECS 驱动包
- 使用 SMS 控制台"启动修复"注入 KVM 驱动
- 如仍失败，联系华为云技术支持

#### 3.5 UEFI 引导问题

**现象**: 迁移后 ECS 无法从系统盘启动

**原因**: 源端使用 UEFI 引导，目标 ECS 镜像使用 Legacy BIOS（或反之）

**解决方案**:
- 确认源端引导模式：`bcdedit /enum firmware`
- 选择与源端引导模式一致的目标镜像
- 使用 SMS 控制台修复引导配置

#### 3.6 内存识别异常

**现象**: 迁移后 ECS 内存小于源端

**原因**: 源端内存配置非标准（如热添加内存），或 ECS 规格不匹配

**解决方案**:
- 选择与源端内存最接近的 ECS 规格
- 确认 ECS 规格内存 ≥ 源端内存

### 4. ECS创建问题

#### 4.1 Windows镜像找不到

**现象**: `ImageNotFound` 错误

**排查步骤**:
```bash
# 列出公共Windows镜像
hcloud IMS ListImages --imagetype gold --os-type Windows
```

**解决方案**:
- 确认目标region支持Windows公共镜像
- 使用自定义镜像替代

#### 4.2 ECS密码不符合要求

**现象**: ECS创建失败，密码复杂度不够

**Windows ECS密码要求**:
- 8-26个字符
- 至少包含大写字母、小写字母、数字、特殊字符中的3种
- 特殊字符：`!@$%^-_=+[{}]:,./?`

### 5. 网络问题

#### 5.1 RDP无法连接

**现象**: 迁移完成后无法通过RDP连接ECS

**排查步骤**:
1. 确认EIP已绑定：`hcloud ECS ShowServer --id <server_id>`
2. 确认安全组开放3389端口
3. 测试端口连通性：`telnet <eip> 3389`

**解决方案**:
```bash
# 添加安全组规则
hcloud VPC CreateSecurityGroupRule --security-group-id <sg_id> \
    --direction ingress --protocol tcp --port 3389 --remote-ip <管理IP>/32
```

#### 5.2 安全组规则缺失

**Windows迁移需要的安全组端口**:

| 端口 | 协议 | 用途 | 方向 |
|------|------|------|------|
| 3389 | TCP | RDP远程桌面 | ingress |
| 5985 | TCP | WinRM HTTP | ingress |
| 5986 | TCP | WinRM HTTPS | ingress |
| 445 | TCP | SMB文件共享 | ingress |
| 80 | TCP | HTTP（可选） | ingress |
| 443 | TCP | HTTPS（可选） | ingress |
| All | TCP | 出站流量 | egress |

### 6. 性能问题

#### 6.1 迁移速度慢

**优化建议**:
1. 检查源端网络带宽，建议至少100Mbps
2. 检查源端磁盘I/O性能
3. 避免在业务高峰期执行迁移
4. 使用"持续同步"模式，分阶段迁移
5. 确保源端和目标region网络质量良好

#### 6.2 源端CPU/内存占用高

**现象**: Agent运行期间源端资源占用过高

**解决方案**:
```powershell
# 限制Agent进程优先级
Get-Process SMSAgent | ForEach-Object { $_.PriorityClass = "BelowNormal" }

# 限制Agent内存（如有配置项）
# 编辑 agent_config.cfg 设置 max_memory_usage
```

### 7. 错误码参考

| 错误码 | 描述 | 解决方案 |
|--------|------|----------|
| SMS.0301 | WinRM连接失败 | 检查WinRM配置和网络 |
| SMS.0302 | 认证失败 | 检查用户名密码 |
| SMS.0303 | Agent安装失败 | 检查.NET Framework和权限 |
| SMS.0304 | VSS服务异常 | 启动VSS服务 |
| SMS.0305 | 磁盘空间不足 | 清理源端磁盘空间 |
| SMS.0306 | 网络中断 | 检查网络连通性 |
| SMS.0307 | 目标ECS创建失败 | 检查ECS规格和镜像 |
| SMS.0308 | 迁移数据校验失败 | 重新执行迁移 |
| SMS.0309 | 系统启动失败 | 使用启动修复或联系技术支持 |
| SMS.0310 | Agent版本过低 | 升级Agent到最新版本 |
| SMS.0515 | 磁盘信息获取失败 | 刷新源端磁盘信息后重试 |
| SMS.6614 | 目标磁盘容量不足 | 增大目标磁盘容量（GPT +1GB） |
| SMS.7605 | 目的端已被其他任务占用 | 先删除旧迁移任务（sms_task.py delete）再创建 |
| SMS.1100 | 通用错误 | 查看Agent日志排查具体原因 |

### 8. 磁盘相关问题

#### 8.1 GPT 分区磁盘容量不足

**现象**: 迁移失败，错误码 SMS.6614

**原因**: GPT 分区磁盘目标容量需比源端大 1GB

**解决方案**:
- 增大目标 ECS 磁盘容量（源端 + 1GB）
- 本 skill 的 `core/target_provider.py` 目标端编排已自动 +1GB buffer

#### 8.2 磁盘数量超限

**现象**: 迁移失败，提示磁盘数量超过限制

**原因**: 源端磁盘数量超过 23 块

**解决方案**:
- 减少源端磁盘数量（合并数据盘）
- 卸载不必要的磁盘

#### 8.3 源端磁盘变更后无法增量同步

**现象**: 源端磁盘调整后，增量同步失败

**原因**: SMS Agent 无法感知源端磁盘变更

**解决方案**:
- 重启 SMS Agent 服务：`Restart-Service SMSAgentService`
- 重新刷新磁盘信息：`hcloud SMS PutDiskInfo --server-id <server_id>`
- 重新创建迁移任务

### 9. 网络相关问题

#### 9.1 Agent 无法连接 SMS 服务（代理环境）

**现象**: Agent 日志显示连接超时

**原因**: 源端需通过代理服务器访问华为云

**解决方案**:
- 在 Agent 配置中设置代理服务器
- 确认代理服务器可访问 `sms.<region>.myhuaweicloud.com:443`
- 检查代理认证配置

#### 9.2 VPN/专线迁移网络配置

**现象**: 私网迁移模式下 Agent 无法注册

**原因**: VPC 网络配置不正确

**解决方案**:
- 确认 VPN/专线已正确配置
- 确认源端可访问 SMS 内网 endpoint
- 确认 VPC 路由表配置正确
- 确认安全组放通 8899/8900 端口
