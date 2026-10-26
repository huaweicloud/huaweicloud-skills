# 部署验证方法(verification-method)

本文件支撑 SKILL.md 步骤 5/6 的验证流程,覆盖方式 A(API)与方式 B(控制台)两种部署方式的验证步骤、OpenAI 兼容调用验证与验证失败定位。

## 一、服务就绪验证

| 部署方式 | 就绪验证动作 | 成功判定 |
|---------|-------------|---------|
| 方式 A(API) | `IAM_TOKEN=<token> python scripts/create_infer_service.py show --endpoint ... --project-id ... --service-id <ID>` | `status == RUNNING`;反复重启则查探针配置(见 troubleshooting) |
| 方式 B(控制台) | 在线服务列表页查看服务状态 | 状态为**运行中**;反复重启优先查健康检查启动延迟/失败次数 |

> 状态取值: `DEPLOYING`(部署中)/ `RUNNING`(运行中)/ `STOPPED` / `FAILED`(失败)/ `DELETING` / `UPGRADING` / `CONCERNING`。

## 二、调用端点获取

- 服务详情 `access_address`(公网调用 URL)即为调用端点;**`access_address: null` 时改用 `predict_url[].urls[]` 中 `type=PUBLIC` 的地址**。
- **调用 URL 格式**: `http://{PUBLIC_IP}/v2/infer/{service_id}/v1/chat/completions`(OpenAI 兼容)。
  - 协议必须是 **http**(用 https 报 `400 ModelArts.8910 Request protocol: HTTPS does not match...`);
  - 路径必须带 `/v2/infer/{service_id}` 前缀(裸 IP + `/v1/chat/completions` 报 `404 ModelArts.2836 Path not found`)。

## 三、OpenAI 兼容调用验证(步骤 6)

推荐使用 `scripts/test_inference.py`:

```bash
python scripts/test_inference.py --url http://<PUBLIC_IP>/v2/infer/<service_id>/v1/chat/completions \
    --token <推理token,若配置了推理请求认证> --model <MODEL_NAME> --prompt "你好,请介绍一下你自己"
# 可选: --max-tokens 256 --temperature 0.7
```

**等价调用(Python)**:

```python
import requests
url = "http://<PUBLIC_IP>/v2/infer/<service_id>/v1/chat/completions"
headers = {"Authorization": "Bearer <token>"}   # 仅服务配置了推理请求认证时需要
payload = {"model": "Qwen2.5-7B-Instruct",
           "messages": [{"role": "user", "content": "你好,请介绍一下你自己"}],
           "max_tokens": 256}
resp = requests.post(url, json=payload, headers=headers, timeout=120)
print(resp.json()["choices"][0]["message"]["content"])
```

**成功判定**: 返回 `choices[0].message.content` 有正常文本 → 部署成功。本地联调可用 `http://127.0.0.1:8080/v1/chat/completions` 先验证脚本与参数,再上云。

## 四、验证失败定位速查

| 现象 | 定位方向 |
|------|---------|
| 连接失败/超时 | ① 服务是否 RUNNING;② 调用 URL 协议 http + `/v2/infer/{service_id}` 前缀是否正确;③ 网络到公网 IP 是否可达 |
| `400 ModelArts.8910` | 协议用了 https,服务 protocol=HTTP → 改用 http |
| `404 ModelArts.2836 Path not found` | 路径缺 `/v2/infer/{service_id}` 前缀 |
| 401/403 | 推理请求认证 token 错误/缺失;或 IAM token 失效 |
| `choices` 为空/报模型错误 | ① `--model` 参数与 `served-model-name`(部署的 MODEL_NAME)一致;② 权重/镜像版本是否配套 |
| 服务反复重启 | 健康检查 startup 延迟 600s + 失败次数 300 是否配置;探针路径/端口与启动脚本一致(详见 `references/troubleshooting.md` 首条) |

> 完整排查表见 `references/troubleshooting.md`。
