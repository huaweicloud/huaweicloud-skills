# Flexus L 系统镜像与规格参考

> 本文档从 SKILL_CN.md 移出，避免技能文档臃肿。

## 支持的系统镜像

配置文件 `image_specs.json` 定义了各区域支持的系统镜像和规格映射：

| 镜像名称 | 版本 | 说明 |
| --------- | ------ | ------ |
| Ubuntu | 22.04, 20.04 | Linux 系统 |
| CentOS | 7.9, 8.0 | Linux 系统 |
| Debian | 11.0, 12.0 | Linux 系统 |
| WindowsServer | 2019_standard_ch, 2022_standard_ch | Windows 系统 |

## 可用规格参考

> **⚠️ 重要：规格编码前缀因区域而异！**
>
> | 区域 | 规格前缀 | 示例 |
> | ------ | ---------- | ------ |
> | 华北-北京四、华东-上海一、华南-广州等 | `hf.*` | `hf.small.1.win` |
> | **西南-贵阳一 (cn-southwest-2)** | `ahf.*` | `ahf.small.1.win` |
>
> **使用错误前缀会导致 `HCSS.14000001` 错误！**

### 标准规格（hf.* 前缀）

适用于北京四、上海一、广州等区域：

| 规格编码 | OS | CPU | 内存 |
| --------- | ----- | ----- | ------ |
| `hf.small.1.linux` | Linux | 1核 | 1GB |
| `hf.small.2.linux` | Linux | 1核 | 2GB |
| `hf.medium.1.linux` | Linux | 2核 | 2GB |
| `hf.medium.2.linux` | Linux | 2核 | 4GB |
| `hf.large.1.linux` | Linux | 4核 | 4GB |
| `hf.xlarge.1.linux` | Linux | 8核 | 8GB |
| `hf.small.1.win` | Windows | 1核 | 2GB |
| `hf.medium.1.win` | Windows | 2核 | 4GB |
| `hf.large.1.win` | Windows | 4核 | 8GB |

### 贵阳一规格（ahf.* 前缀）

适用于 cn-southwest-2 区域：

| 规格编码 | OS | CPU | 内存 |
| --------- | ----- | ----- | ------ |
| `ahf.small.1.win` | Windows | 1核 | 2GB |
| `ahf.medium.1.win` | Windows | 2核 | 4GB |
| `ahf.large.1.win` | Windows | 4核 | 8GB |
| `ahf.small.1.linux` | Linux | 1核 | 1GB |
| `ahf.medium.1.linux` | Linux | 2核 | 2GB |
| `ahf.large.1.linux` | Linux | 4核 | 8GB |

## 可用镜像参考

**Windows 镜像：**

- `WindowsServer:2012R2_standard_ch`
- `WindowsServer:2016_standard_ch`
- `WindowsServer:2019_standard_ch`
- `WindowsServer:2022_standard_ch`

**Linux 镜像：**

- `Ubuntu:22.04_amd64`
- `CentOS:7.9_amd64`
- `Debian:10.2.0_amd64`

> **💡 备注**：各区域、镜像版本支持的规格编码各有差异，购买前请查阅官方文档 [Flexus L 实例购买指南](https://support.huaweicloud.com/api-flexusl/create_instance_0001.html#create_instance_0001__section1881914176434)：
>
> - **附录1**：各类镜像对应的规格编码
> - **附录2**：规格编码对应的规格信息
