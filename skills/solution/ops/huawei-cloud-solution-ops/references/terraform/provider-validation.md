# Terraform Provider Validation

这份文档用于把 provider mirror/cache 思路统一到 `huawei-cloud-solution-ops`，但不把 installer 作为默认执行能力。

## 原则

- 默认只做只读检查：Terraform CLI、`.terraformrc`、`TF_PLUGIN_CACHE_DIR`、provider cache 和 lock file。
- 不自动安装 Terraform，不自动下载 provider，不自动改写用户主目录配置。
- 需要下载 provider 时，先让用户明确确认网络行为。
- 任何 `terraform apply` 仍必须等待用户审查 exact plan 后确认。

## 推荐检查顺序

1. 运行：

```bash
python3 scripts/hcloud_terraform_context_inspect.py --pretty
```

2. 检查输出中的：

- `terraform.found`
- `terraform.version`
- `terraform_cli_config`
- `provider_cache.global_provider_cache_candidates`
- `provider_cache.plugin_cache_dir`
- `readiness.warnings`

3. 如果没有 provider cache，也没有 mirror，不要直接声称 `terraform validate` 可离线通过。

## 可选 Terraform CLI 配置

如果用户明确希望配置 provider mirror，可以在本机 Terraform CLI config 中使用类似配置：

```hcl
provider_installation {
  network_mirror {
    url     = "https://mirrors.huaweicloud.com/terraform/"
    include = ["registry.terraform.io/huaweicloud/*"]
  }

  direct {}
}
```

这只是示例，不由 skill 自动写入。

## 验证分层

- `terraform fmt -check -recursive`: 本地格式检查，不需要 provider。
- `terraform init -backend=false`: 需要 provider cache、mirror 或网络。
- `terraform validate`: 依赖 init 结果。
- `terraform plan`: 需要凭证、region/project 和真实云资源上下文。

当本地缺 provider cache 或网络不可用时，示例仍可进入 catalog，但必须在文档或最终说明里标明 `init/validate` 未执行。
