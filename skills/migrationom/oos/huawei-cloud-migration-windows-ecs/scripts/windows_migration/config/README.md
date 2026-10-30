# config/ 模板使用说明（公网 / 私网）

本目录为内置的公网/私网迁移模板，全部为**占位符**（`<AK>`、`<SK>`、`<源端公网IP>` 等），
使用前必须替换为真实值，并保持文件权限 600、勿提交到仓库。

## 文件清单

| 文件 | 用途 |
|------|------|
| `migrate.public.yaml` | 公网场景引擎配置模板（`cp migrate.public.yaml migrate.yaml` 使用） |
| `migrate.private.yaml` | 私网场景引擎配置模板（含跳板机日志目录） |
| `env.public.sh.example` | 公网环境变量模板（`cp env.public.sh.example env.public.sh` → 填值 → source） |
| `env.private.sh.example` | 私网环境变量模板（源端+代理两条 Host_Information 对象） |
| `hosts.csv.example` | 批量主机列表 CSV 模板（兼容回退；`cp hosts.csv.example hosts.csv` 使用） |

## 使用流程

在 `scripts/windows_migration/` 下操作：

1. 选定场景并生成实际配置文件：
   - 公网：`cp config/env.public.sh.example config/env.public.sh && cp config/migrate.public.yaml config/migrate.yaml`
   - 私网：`cp config/env.private.sh.example config/env.private.sh && cp config/migrate.private.yaml config/migrate.yaml`
2. 编辑 `config/env.<scenario>.sh` 与 `config/migrate.yaml`，替换占位符（AK/SK、源端 IP/用户名/密码、region/project、代理信息）。
3. 注入环境变量并自检：
   ```bash
   source config/env.<scenario>.sh
   python3 preflight_check.py --scenario <public|private>
   ```
4. 执行迁移：
   ```bash
   python3 unified_migrate.py --scenario <public|private> --config config/migrate.yaml --batch env --workers 10
   ```

## 安全要求

- 安全组放行仅允许源端 IP/32，**禁止** `0.0.0.0/0`（私网场景放行源端内网 IP/32，否则 ATTACH_AGENT_IMAGE 失败）。
- AK/SK 与密码只存在于本地 600 权限文件中，不写入日志、不提交仓库、不在聊天中明文暴露。