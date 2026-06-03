# Flexus L 系统镜像与规格参考

## 数据获取方式

镜像和规格信息从官方文档动态获取，不依赖本地配置文件：

- **数据来源**: https://support.huaweicloud.com/api-flexusl/create_instance_0001.html
- **获取方式**: 执行 `show-regions`、`show-images`、`show-specs` 时自动获取最新数据
- **脚本**: `scripts/flexus_specs_extractor.py`

## 支持的系统镜像

| 镜像名称 | 版本 | 说明 |
| --------- | ------ | ------ |
| Ubuntu | 24.04, 22.04, 20.04, 18.04, 16.04 | Linux 系统 |
| CentOS | 8.2, 8.1, 8.0, 7.9, 7.8, 7.7... | Linux 系统 |
| CentOS_Stream | 9.0, 8.0 | Linux 系统 |
| Debian | 12.0, 11.1, 9.0 | Linux 系统 |
| Huawei Cloud EulerOS | 2.0 | 华为欧拉系统 |
| openEuler | 20.03, 22.03 | 开源欧拉系统 |
| AlmaLinux | 9.0, 9.3, 9.4 | Linux 系统 |
| Rocky Linux | 8.4, 8.5, 8.8, 8.10, 9.0... | Linux 系统 |
| OpenSUSE | 15.0 | Linux 系统 |
| CoreOS | 2079.4.0 | 容器操作系统 |
| WindowsServer | 2012R2~2022 | Windows 系统 |

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
| `hf.small.1.linux` | Linux | 2核 | 2GB |
| `hf.small.2.linux` | Linux | 2核 | 2GB |
| `hf.medium.1.linux` | Linux | 2核 | 4GB |
| `hf.medium.2.linux` | Linux | 2核 | 4GB |
| `hf.large.1.linux` | Linux | 2核 | 8GB |
| `hf.xlarge.1.linux` | Linux | 4核 | 8GB |
| `hf.small.1.win` | Windows | 2核 | 2GB |
| `hf.medium.1.win` | Windows | 2核 | 4GB |
| `hf.large.1.win` | Windows | 2核 | 8GB |

### 贵阳一规格（ahf.* 前缀）

适用于 cn-southwest-2 区域：

| 规格编码 | OS | CPU | 内存 |
| --------- | ----- | ----- | ------ |
| `ahf.small.1.win` | Windows | 2核 | 2GB |
| `ahf.medium.1.win` | Windows | 2核 | 4GB |
| `ahf.large.1.win` | Windows | 2核 | 8GB |
| `ahf.small.1.linux` | Linux | 2核 | 2GB |
| `ahf.medium.1.linux` | Linux | 2核 | 4GB |
| `ahf.large.1.linux` | Linux | 2核 | 8GB |

## 可用镜像参考

**Windows 镜像：**

- `WindowsServer:2012R2_standard_ch`
- `WindowsServer:2016_standard_ch`
- `WindowsServer:2019_standard_ch`
- `WindowsServer:2022_standard_ch`

**Linux 镜像：**

- `Ubuntu:24.04`
- `Ubuntu:22.04`
- `CentOS:7.9`
- `CentOS:8.2`
- `Debian:12.0`
- `Huawei Cloud EulerOS:2.0`

> **💡 备注**：各区域、镜像版本支持的规格编码各有差异，购买前请查阅官方文档 [Flexus L 实例购买指南](https://support.huaweicloud.com/api-flexusl/create_instance_0001.html#create_instance_0001__section1881914176434)：
>
> - **附录1**：各类镜像对应的规格编码
> - **附录2**：规格编码对应的规格信息
>
> 或使用命令行工具实时查询：
>
> ```bash
> python scripts/flexus_lifecycle.py --region cn-north-4 show-images
> python scripts/flexus_lifecycle.py --region cn-north-4 show-specs --image Ubuntu
> ```
