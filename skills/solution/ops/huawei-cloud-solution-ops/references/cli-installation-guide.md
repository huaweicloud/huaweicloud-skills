# hcloud CLI Installation and Readiness

在任务选择 hcloud 后、当前环境未确认 CLI 可用时读取本文件。安装包、下载地址和受支持平台可能变化，具体版本以华为云官方 hcloud/KooCLI 文档和目标环境实际结果为准。

## 先检查，后安装

1. 运行 `python3 scripts/hcloud_environment_doctor.py --need hcloud --pretty`。
2. 若已发现 hcloud，再运行 `hcloud --version` 和目标 operation 的 help/metadata 检查，不重复安装。
3. 若未发现 hcloud，确认目标主机的操作系统、CPU 架构、是否允许联网和是否允许安装软件。
4. 从华为云官方文档给出的渠道获取匹配平台的安装包；官方提供校验值或签名时必须验证。
5. 安装后重新运行 doctor 和版本检查，再进入认证配置。

安装软件会改变用户环境。用户只要求查询、规划或解释时，不要自行下载安装；先说明缺少的运行依赖。无法安装 hcloud 时，按 `references/backend-selection.md` 判断 SDK 或 Terraform 是否确实适合当前任务。

## 安装后最小验证

```bash
hcloud --version
hcloud configure show
hcloud configure list --cli-output=json
```

上述输出只能证明 CLI 与本地 profile 可读取，不能证明云侧权限充分。不要输出 AK/SK、security token 或其他凭据值；认证、region/project 和 profile 规则见 `references/auth-and-context.md`。

## 进入业务命令前

- 区域级服务显式使用 `--cli-region=<region>`。
- 先用 metadata/help 证据确认 `Service`、`Operation/version` 和参数名称。
- 只读查询仍需确认作用域；变更操作继续遵守 dry-run、方案确认和回读验收要求。
- CLI 已安装但命令不可用时，先检查 PATH、版本、online/offline metadata 和 profile，不要直接重装。

进一步的运行依赖与故障分流见 `references/runtime-dependencies.md` 和 `references/error-playbook.md`。
