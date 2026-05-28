# KooCLI Installation Guide

## Step 1: Preparation

Before using KooCLI, text prompt users about the preparation work needed:
1.[Register Huawei account and complete real-name authentication](https://support.huaweicloud.com/qs-hcli/hcli_02_002.html#hcli_02_002__section544111119366)
2.[Create IAM user and authorize](https://support.huaweicloud.com/qs-hcli/hcli_02_002.html#hcli_02_002__section10273653161410)
3.[Get access key (AK/SK)](https://support.huaweicloud.com/qs-hcli/hcli_02_002.html#hcli_02_002__section10548184715361)

## Step 2: Installation on Different Systems

### Linux and MacOS System Installation
```bash
curl -sSL https://cn-north-4-hdn-koocli.obs.cn-north-4.myhuaweicloud.com/cli/latest/hcloud_install.sh -o ./hcloud_install.sh && bash ./hcloud_install.sh
```
The above command downloads KooCLI to "/usr/local/hcloud/" directory by default and moves it to "/usr/local/bin/" directory for convenient use of hcloud command in any directory (before completing this step, please ensure PATH system variable contains "/usr/local/bin/" path).

You can modify the file download directory during command execution based on interactive information. If permission insufficient is prompted during execution, you can switch to root user and re-execute the installation command.

If you want to use default configuration and skip interactive mode, you can add "-y" at the end of the command, as follows:
```bash
curl -sSL https://cn-north-4-hdn-koocli.obs.cn-north-4.myhuaweicloud.com/cli/latest/hcloud_install.sh -o ./hcloud_install.sh && bash ./hcloud_install.sh -y
```

### Windows System Installation
1.[Click here to download](https://cn-north-4-hdn-koocli.obs.cn-north-4.myhuaweicloud.com/cli/latest/huaweicloud-cli-windows-amd64.zip) KooCLI adapted for Windows system.

2.Extract the downloaded zip package to get hcloud.exe

3.(Optional) Add the directory where KooCLI is located to the system environment variable Path for convenient use of hcloud command in any directory in cmd window.
Windows 10 and Windows 8 search and select "View advanced system settings", then click "Environment Variables";
Windows 7 right-click the "Computer" icon on the desktop, select "Properties" from the menu. Click the "Advanced system settings" link, then click "Environment Variables".

Enter the environment variables graphical interface, in the "User variables" list, select the environment variable named "Path" and click "Edit".
In the edit environment variable interface, click "New" and enter the path of the directory where hcloud.exe file is located.
Click "OK" three times to save this modification.
(Optional) Open cmd window, execute the following command to check if environment variable contains the directory where hcloud.exe file is located, if exists it means configuration is successful.
```bash
set path
```

4.(Optional) Open Windows system cmd window (if you did not execute step 3 above, you need to enter the directory where the tool is located), input and execute the following command to verify if KooCLI is installed successfully.
```bash
hcloud version
# Current KooCLI version: x.x.x
```

The system displays version information similar to the following, indicating successful installation:
```bash
hcloud version
# Current KooCLI version: x.x.x
```

### Step 3: Initialize Configuration
You can initialize configuration through the following command, after entering the command press Enter to enter interactive mode, input each parameter value according to interface prompts:
```bash
hcloud configure init
```
>hcloud configure init
Start initializing configuration, where "Secret Access Key" input is anonymized
Access Key ID [required]: ********
Secret Access Key [required]: ****
Secret Access Key (again): ****
Region: cn-north-4

>Note:
During initialization, the value of "Secret Access Key" needs to be confirmed twice. To ensure your account security, your input "Secret Access Key" has been anonymized. During your input process, the entered characters will not be displayed, when you finish input and press Enter to the next line, your input content will be echoed with "*". After configuration is complete, KooCLI will encrypt and save authentication-related sensitive information in the configuration items locally.
If you re-execute the initialization command, the original configuration file will be deleted and a new configuration file will be regenerated, configuration file save location is as follows:
Windows system: C:\Users\{Your Windows system username}\.hcloud\config.json
Linux system: /home/{current username}/.hcloud/config.json
Mac system: /Users/{current username}/.hcloud/config.json

After initialization is complete, you can query configuration information through the following command:
```bash
hcloud configure show --cli-profile=default
```
