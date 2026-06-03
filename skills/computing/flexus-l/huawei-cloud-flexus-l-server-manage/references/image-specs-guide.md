# Flexus L System Images and Specifications Reference

## Data Source

Image and specification information is dynamically fetched from official documentation, no local configuration file needed:

- **Data Source**: https://support.huaweicloud.com/api-flexusl/create_instance_0001.html
- **Fetch Method**: Automatically retrieves latest data when executing `show-regions`, `show-images`, `show-specs`
- **Script**: `scripts/flexus_specs_extractor.py`

## Supported System Images

| Image Name | Versions | Description |
| ---------- | -------- | ----------- |
| Ubuntu | 24.04, 22.04, 20.04, 18.04, 16.04 | Linux system |
| CentOS | 8.2, 8.1, 8.0, 7.9, 7.8, 7.7... | Linux system |
| CentOS_Stream | 9.0, 8.0 | Linux system |
| Debian | 12.0, 11.1, 9.0 | Linux system |
| Huawei Cloud EulerOS | 2.0 | Huawei EulerOS |
| openEuler | 20.03, 22.03 | Open source EulerOS |
| AlmaLinux | 9.0, 9.3, 9.4 | Linux system |
| Rocky Linux | 8.4, 8.5, 8.8, 8.10, 9.0... | Linux system |
| OpenSUSE | 15.0 | Linux system |
| CoreOS | 2079.4.0 | Container OS |
| WindowsServer | 2012R2~2022 | Windows system |

## Available Specifications Reference

> **⚠️ Important: Spec code prefixes vary by region!**
>
> | Region | Spec Prefix | Example |
> | ------ | ----------- | ------- |
> | North China-Beijing 4, East China-Shanghai 1, South China-Guangzhou, etc. | `hf.*` | `hf.small.1.win` |
> | **Southwest China-Guiyang 1 (cn-southwest-2)** | `ahf.*` | `ahf.small.1.win` |
>
> **Using the wrong prefix will result in `HCSS.14000001` error!**

### Standard Specifications (hf.* prefix)

Applies to Beijing 4, Shanghai 1, Guangzhou, and other regions:

| Spec Code | OS | CPU | Memory |
| --------- | -- | --- | ------ |
| `hf.small.1.linux` | Linux | 2 vCPUs | 2GB |
| `hf.small.2.linux` | Linux | 2 vCPUs | 2GB |
| `hf.medium.1.linux` | Linux | 2 vCPUs | 4GB |
| `hf.medium.2.linux` | Linux | 2 vCPUs | 4GB |
| `hf.large.1.linux` | Linux | 2 vCPUs | 8GB |
| `hf.xlarge.1.linux` | Linux | 4 vCPUs | 8GB |
| `hf.small.1.win` | Windows | 2 vCPUs | 2GB |
| `hf.medium.1.win` | Windows | 2 vCPUs | 4GB |
| `hf.large.1.win` | Windows | 2 vCPUs | 8GB |

### Guiyang 1 Specifications (ahf.* prefix)

Applies to cn-southwest-2 region:

| Spec Code | OS | CPU | Memory |
| --------- | -- | --- | ------ |
| `ahf.small.1.win` | Windows | 2 vCPUs | 2GB |
| `ahf.medium.1.win` | Windows | 2 vCPUs | 4GB |
| `ahf.large.1.win` | Windows | 2 vCPUs | 8GB |
| `ahf.small.1.linux` | Linux | 2 vCPUs | 2GB |
| `ahf.medium.1.linux` | Linux | 2 vCPUs | 4GB |
| `ahf.large.1.linux` | Linux | 2 vCPUs | 8GB |

## Available Images Reference

**Windows Images:**

- `WindowsServer:2012R2_standard_ch`
- `WindowsServer:2016_standard_ch`
- `WindowsServer:2019_standard_ch`
- `WindowsServer:2022_standard_ch`

**Linux Images:**

- `Ubuntu:24.04`
- `Ubuntu:22.04`
- `CentOS:7.9`
- `CentOS:8.2`
- `Debian:12.0`
- `Huawei Cloud EulerOS:2.0`

> **💡 Note**: Spec codes vary by region and image version. Please refer to the official documentation [Flexus L Instance Purchase Guide](https://support.huaweicloud.com/api-flexusl/create_instance_0001.html#create_instance_0001__section1881914176434) before purchasing:
>
> - **Appendix 1**: Spec codes for each image type
> - **Appendix 2**: Spec details for each code
>
> Or use the command-line tool for real-time queries:
>
> ```bash
> python scripts/flexus_lifecycle.py --region cn-north-4 show-images
> python scripts/flexus_lifecycle.py --region cn-north-4 show-specs --image Ubuntu
> ```
