## OBS 配置文件模板

使用 `--method obs` 时，需要准备 OBS 配置文件 `config/obs_config.ini`（从 `config/obs_config_template.ini` 复制）：

```ini
[obs]
bucket = your-obs-bucket
endpoint = obs.cn-north-4.myhuaweicloud.com
obsutil_path = obsutil
chunksize = 64
parallel = 8
```

**安全要求**：OBS AK/SK 不写入配置文件，通过环境变量注入：

```bash
export OBS_ACCESS_KEY=<access-key-id>
export OBS_SECRET_KEY=<access-key-secret>
```

脚本读取顺序：环境变量 `OBS_ACCESS_KEY` / `OBS_SECRET_KEY` 优先；未设置时才读取配置文件中的 `access_key` / `secret_key` 字段（用于兼容已有部署）。

- `bucket`: OBS 桶名
- `endpoint`: OBS 终端节点，按桶所在区域选择
- `obsutil_path`: obsutil 命令路径，已加入 PATH 时填 `obsutil`
- `chunksize`: OBS 外表分片大小（MB），默认 64
- `parallel`: 并行导入度，默认 8，建议不超过 DWS 节点数 × 2