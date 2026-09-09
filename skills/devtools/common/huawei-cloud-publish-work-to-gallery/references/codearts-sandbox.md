# Publishing from a CodeArts Sandbox (host-visible work dir)

CodeArts（码道/AI DevSpace）沙箱中作品的工作目录**就位于宿主机本地**：

```
/root/job-envs/sandboxes/codearts-{timestamp}/
```

因此**沙箱内的文件在宿主机可直接读写、可直接 git 操作**——把它当成一个普通项目目录处理即可，**不需要任何 `acpx`/bwrap 隔离的变通手段**。发布流程的所有步骤（扫描 README、选作品、读文件、git init/push、启动服务、截图、打包）与标准流程完全一致，只是把 `workDir` 指到沙箱目录即可。

## 检测与定位

开始前确认是否在沙箱、并定位工作目录：

```bash
# 沙箱活跃检测（CodeArts 的 ACP 健康端口）
curl -s --max-time 3 http://127.0.0.1:19300/healthz   # 返回 "ok" = 沙箱活跃

# 定位沙箱工作目录（取最新的 codearts-* 目录）
ls -dt /root/job-envs/sandboxes/codearts-* 2>/dev/null | head -1
```

若命中沙箱，`workDir` 用该目录即可；否则按标准流程在当前目录扫描。

## 运行中应用

沙箱容器与应用共享网络命名空间，宿主机可直接访问其监听端口：
- 启动/验证应用：`curl http://127.0.0.1:<port>/`
- 截图：用本地地址 `http://127.0.0.1:<port>`（**禁止用隧道 URL 截图**，会截到授权页）
- `envUrl`：用 DevBridge 隧道暴露端口获取（见 [devbridge-tunnel.md](devbridge-tunnel.md)）

## 小结

| 事项 | 做法 |
|------|------|
| 扫描/选作品/读文件/git | 直接在宿主机的沙箱目录上按标准流程做 |
| 启动应用 | 正常启动，端口宿主机可直接访问 |
| 截图 | 本地 URL |
| envUrl | DevBridge 隧道 |
| 发布/奖励 API | 宿主机正常调用 |