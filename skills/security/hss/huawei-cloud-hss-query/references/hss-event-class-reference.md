# HSS Event Class ID Reference

## Malware / Antivirus Events (av_*)

| event_class_id | Description (Chinese) | Description (English) |
|----------------|----------------------|----------------------|
| `av_1002` | 病毒 | Virus |
| `av_1003` | 蠕虫 | Worm |
| `av_1004` | 木马 | Trojan |
| `av_1005` | 僵尸网络 | Botnet |
| `av_1006` | 后门 | Backdoor |
| `av_1007` | 间谍软件 | Spyware |
| `av_1008` | 恶意广告软件 | Malicious adware |
| `av_1009` | 钓鱼 | Phishing |
| `av_1010` | Rootkit | Rootkit |
| `av_1011` | 勒索软件 | Ransomware |
| `av_1012` | 黑客工具 | Hacker tool |
| `av_1013` | 灰色软件 | Grayware |
| `av_1015` | Webshell | Webshell |
| `av_1016` | 挖矿软件 | Mining software |

## Login / Brute Force Events (login_*)

| event_class_id | Description (Chinese) | Description (English) |
|----------------|----------------------|----------------------|
| `login_0001` | 尝试暴力破解 | Brute force attempt |
| `login_0002` | 爆破成功 | Brute force success |

## File Protection Events (fileprotect_*)

| event_class_id | Description (Chinese) | Description (English) |
|----------------|----------------------|----------------------|
| `fileprotect_0001` | 文件提权 | File privilege escalation |
| `fileprotect_0002` | 关键文件变更 | Critical file change |
| `fileprotect_0003` | 关键文件路径变更 | Critical file path change |
| `fileprotect_0004` | 文件/目录变更 | File/directory change |

## Container Events (container_*)

| event_class_id | Description (Chinese) | Description (English) |
|----------------|----------------------|----------------------|
| `container_1001` | 容器命名空间 | Container namespace |
| `container_1002` | 容器开放端口 | Container open port |
| `container_1003` | 容器安全选项 | Container security option |
| `container_1004` | 容器挂载目录 | Container mount directory |

## Container Escape Events (containerescape_*)

| event_class_id | Description (Chinese) | Description (English) |
|----------------|----------------------|----------------------|
| `containerescape_0001` | 容器高危系统调用 | Container high-risk syscall |
| `containerescape_0002` | Shocker攻击 | Shocker attack |
| `containerescape_0003` | DirtCow攻击 | DirtCow attack |
| `containerescape_0004` | 容器文件逃逸攻击 | Container file escape attack |

## Event Type Integer Values

| event_type | Description |
|------------|-------------|
| `1001` | General malware (通用恶意软件) |
| `1002` | Virus (病毒) |

## Usage Examples

### Query all trojan alerts

```bash
hcloud HSS ListEventHandleHistory --cli-region={region} --project_id={pid} \
  --event_class_ids.1=av_1004 --limit=10 --offset=0
```

### Query all brute-force successes

```bash
hcloud HSS ListEventHandleHistory --cli-region={region} --project_id={pid} \
  --event_class_ids.1=login_0002 --severity=critical --limit=10 --offset=0
```

### Query ransomware + webshell alerts

```bash
hcloud HSS ListEventHandleHistory --cli-region={region} --project_id={pid} \
  --event_class_ids.1=av_1011 --event_class_ids.2=av_1015 --limit=10 --offset=0
```
