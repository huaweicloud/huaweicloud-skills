华为云命令行工具服务

## 最新动态

文档版本

发布日期 2026-04-16

32

## 版权所有 © 华为云计算技术有限公司 2026。保留一切权利。

非经本公司书面许可，任何单位和个人不得擅自摘抄、复制本文档内容的部分或全部，并不得以任何形式传播。

## 商标声明

HUAWE 和其他华为商标均为华为技术有限公司的商标。

本文档提及的其他所有商标或注册商标，由各自的所有人拥有。

## 注意

您购买的产品、服务或特性等应受华为云计算技术有限公司商业合同和条款的约束，本文档中描述的全部或部分产品、服务或特性可能不在您的购买或使用范围之内。除非合同另有约定，华为云计算技术有限公司对本文档内容不做任何明示或暗示的声明或保证。

由于产品版本升级或其他原因，本文档内容会不定期进行更新。除非另有约定，本文档仅作为使用指导，本文档中的所有陈述、信息和建议不构成任何明示或暗示的担保。

## 华为云计算技术有限公司

地址: 贵州省贵安新区黔中大道交兴功路华为云数据中心 邮编:55002

网址: https://www.huaweicloud.com/

## 目录

1 最新动态.

1

![019db8ba-19c6-7f36-8774-df1c2c039752_3_386_781_1096_231_0.jpg](images/019db8ba-19c6-7f36-8774-df1c2c039752_3_386_781_1096_231_0.jpg)

本文介绍了KooCLI各特性版本的功能发布和对应的文档动态，欢迎体验。

## 2026 年 4 月

<table><tr><td>序号</td><td>功能名称</td><td>功能描述</td><td>阶段</td><td>相关文档</td></tr><tr><td>1</td><td>支持指定项目ID</td><td>KooCLI版本:7.2.2 <br> KooCLI支持使用"--cli-x-project-id"参数指定项目ID 用于认证鉴权。</td><td>商用</td><td>指定项目ID</td></tr><tr><td>2</td><td>支持 AssumeRolere认证模式</td><td>KooCLI版本:7.2.2 <br> KooCLI支持使用认证参数"-- cli-agency-domain-name", "--cli-agency-domain-id", "--cli-agency-name", "--cli-source-profile"配置认证模式为 AssumeRole的配置项</td><td>商用</td><td>支持 AssumeRolere 认证模式</td></tr></table>

## 2025 年 4 月

<table><tr><td>序号</td><td>功能名称</td><td>功能描述</td><td>阶段</td><td>相关文档</td></tr><tr><td>1</td><td>支持指定签名算法</td><td>KooCLI版本:6.2.4 <br> KooCLI支持使用"--cli-auth-type"参数指定特殊签名算法。</td><td>商用</td><td>指定签名算法</td></tr></table>

## 2024 年 7 月

<table><tr><td>序号</td><td>功能名称</td><td>功能描述</td><td>阶段</td><td>相关文档</td></tr><tr><td>1</td><td>支持配置SSO登录参数</td><td>KooCLI版本:5.3.4 <br> KooCLI支持使用"--cli-sso-account-name", "--cli-sso-permission-set-name"参数将帐号名、权限集名称配置到配置文件中，配置后进行 sso登录时无需再次交互选择。</td><td>商用</td><td>配置账号名及权限集名称</td></tr></table>

## 2024 年 5 月

<table><tr><td>序号</td><td>功能名称</td><td>功能描述</td><td>阶段</td><td>相关文档</td></tr><tr><td>1</td><td>支持配置明文存储认证信息</td><td>KooCLI版本:5.2.7 <br> KooCLI支持使用"hcloud configure set --cli-auth-encrypt=false"配置不加密存储配置文件中的认证信息。 未配置时，默认加密存储。</td><td>商用</td><td>配置是否加密存储认证信息</td></tr><tr><td>2</td><td>支持SSO登录</td><td>KooCLI版本:5.2.7 <br> KooCLI支持使用"hcloud configure sso"命令进行SSO 登录，将用户的认证信息存储在配置文件中。</td><td>商用</td><td>支持SSO登录</td></tr></table>

## 2023 年 12 月

<table><tr><td>序号</td><td>功能名称</td><td>功能描述</td><td>阶段</td><td>相关文档</td></tr><tr><td>1</td><td>支持结果轮询</td><td>KooCLI版本:4.4.8 <br> KooCLI支持在调用API的命令中添加"--cli-waiter"选项，用于结果轮询。</td><td>商用</td><td>结果轮询</td></tr></table>

## 2023 年 11 月

<table><tr><td>序号</td><td>功能名称</td><td>功能描述</td><td>阶段</td><td>相关文档</td></tr><tr><td>1</td><td>支持生成JSON格式API入参骨架</td><td>KooCLI版本:4.4.5 <br> KooCLI支持在调用API的命令中添加"--skeleton"选项， 生成该API的JSON格式入参骨架，填写完成后可使用 “ --cli-jsonInput=\$\{JSON文件名\}”传入参数，调用 API。</td><td>商用</td><td>生成JSON格式 API入参骨架</td></tr></table>

## 2023 年 8 月

<table><tr><td>序号</td><td>功能名称</td><td>功能描述</td><td>阶段</td><td>相关文档</td></tr><tr><td>1</td><td>支持配置本地加密保存的认证信息及custom参数的加密算法</td><td>KooCLI版本:4.3.5 <br> KooCLI支持使用"hcloud configure set --cli-local-dea=gm"配置使用国密算法加密本地数据。未配置时， 默认使用取值为intl的国际算法。</td><td>商用</td><td>本地数据的加密算法</td></tr></table>

## 2023 年 4 月

<table><tr><td>序号</td><td>功能名称</td><td>功能描述</td><td>阶段</td><td>相关文档</td></tr><tr><td>1</td><td>支持配置关闭命令执行过程中的 Warning提示信息</td><td>KooCLI版本:4.2.4 <br> KooCLI支持使用"hcloud configure set --cli-warning=false"配置关闭 Warning提示信息。可以避免以自动化脚本执行命令时，输出的Warning提示信息干扰命令执行结果的解析。</td><td>商用</td><td>配置关闭 Warning提示信息</td></tr></table>

## 2023 年 2 月

<table><tr><td>序号</td><td>功能名称</td><td>功能描述</td><td>阶段</td><td>相关文档</td></tr><tr><td>1</td><td>支持以非交互的方式，配置是否同意隐私声明</td><td>KooCLI版本:4.1.6 <br> KooCLI支持使用"hcloud configure set --cli-agree-privacy-statement=true"配置同意隐私声明，以适配以自动化脚本执行KooCLI命令时，不方便通过交互方式同意隐私声明的场景。</td><td>商用</td><td>配置同意隐私声明</td></tr></table>

## 2022 年 12 月

<table><tr><td>序号</td><td>功能名称</td><td>功能描述</td><td>阶段</td><td>相关文档</td></tr><tr><td>1</td><td>支持自定义请求域名</td><td>KooCLI版本:3.4.12 <br> KooCLI调用云服务API时， 支持自定义请求域名。</td><td>商用</td><td>自定义请求域名</td></tr></table>

## 2022 年 11 月

<table><tr><td>序号</td><td>功能名称</td><td>功能描述</td><td>阶段</td><td>相关文档</td></tr><tr><td>1</td><td>KooCLI集成OBS 数据的工具 obsutil</td><td>KooCLI版本:3.4.6 <br> KooCLI集成OBS数据的工具 obsutil的功能。可以通过使用"hcloud obs"命令，快速管理OBS中的数据。</td><td>商用</td><td>管理OBS中的数据</td></tr></table>

<table><tr><td>序号</td><td>功能名称</td><td>功能描述</td><td>阶段</td><td>相关文档</td></tr><tr><td>2</td><td>支持将云服务API 的body位置参数从任一层级置空</td><td>KooCLI版本:3.4.5 <br> KooCLI支持将云服务API的 body位置参数从任一层级置空。</td><td>商用</td><td>云服务API的 body位置参数值置空</td></tr></table>

## 2022 年 6 月

<table><tr><td>序号</td><td>功能名称</td><td>功能描述</td><td>阶段</td><td>相关文档</td></tr><tr><td>1</td><td>新特性</td><td>KooCLI版本:3.2.13 <br> KooCLI支持在线/离线模式。 默认为在线模式。用户可以执行“hcloud configure set --cli-offline=true”命令将 KooCLI切换至离线模式。</td><td>商用</td><td>在线/离线模式的适用场景</td></tr></table>

## 2022 年 5 月

<table><tr><td>序号</td><td>功能名称</td><td>功能描述</td><td>阶段</td><td>相关文档</td></tr><tr><td>1</td><td>新特性</td><td>KooCLI版本:3.2.8 <br> 首次使用KooCLI时，用户需根据交互提示信息，选择是否同意其互联网连接及隐私政策声明。</td><td>商用</td><td>《隐私政策声明》</td></tr></table>

## 2021 年 11 月

<table><tr><td>序号</td><td>功能名称</td><td>功能描述</td><td>阶段</td><td>相关文档</td></tr><tr><td>1</td><td>新特性</td><td>KooCLI版本:2.4.8 <br> 支持通过 “cli-output” 选项指定输出格式，使用 "cli-query" 指定jMESPath表达式以过滤输出内容。</td><td>商用</td><td>指定输出格式</td></tr><tr><td>2</td><td>新特性</td><td>KooCLI版本:2.4.8 <br> 支持使用 “hcloud configure clear” 命令删除所有配置项。</td><td>商用</td><td>删除所有配置项</td></tr></table>

## 2021 年 10 月

<table><tr><td>序号</td><td>功能名称</td><td>功能描述</td><td>阶段</td><td>相关文档</td></tr><tr><td>1</td><td>新特性</td><td>KooCLI版本:2.4.5 <br> 支持通过 “cli-skip-secure-verify”选项，跳过https请求证书验证(不建议)。</td><td>商用</td><td>跳过https请求证书验证</td></tr><tr><td>2</td><td>新特性</td><td>KooCLI版本:2.4.4 <br> 支持通过IAM委托给弹性云服务器，以委托认证的方式在弹性云服务器中使用 KooCLI。</td><td>商用</td><td>支持ECS服务器委托认证</td></tr></table>

## 2021 年 9 月

<table><tr><td>序号</td><td>功能名称</td><td>功能描述</td><td>阶段</td><td>相关文档</td></tr><tr><td>1</td><td>新特性</td><td>KooCLI版本:2.3.14 <br> 支持设置和使用custom(即用户自定义)参数。</td><td>商用</td><td>设置和使用 custom参数</td></tr><tr><td>2</td><td>功能优化</td><td>KooCLI版本:2.3.14 <br> 修复参数取值范围只给出最小值时校验错误的问题。</td><td>商用</td><td>-</td></tr></table>

## 2021 年 8 月

<table><tr><td>序号</td><td>功能名称</td><td>功能描述</td><td>阶段</td><td>相关文档</td></tr><tr><td>1</td><td>新特性</td><td>KooCLI版本:2.3.7 <br> 新增模板管理功能:提供由多个KooCLI命令组合而成的 shell脚本模板，方便用户理清业务逻辑，完成复杂场景下的操作。</td><td>商用</td><td>模板管理</td></tr><tr><td>2</td><td>功能优化</td><td>KooCLI版本:2.3.7 <br> 命令调用结果以json输出时，支持使用“cli-json-filter”对其执行JMESPath查询。</td><td>商用</td><td>使用cli-json-filter对json结果执行JMESPath 查询</td></tr><tr><td>3</td><td>体验优化</td><td>KooCLI版本:2.3.7 <br> 统一各系统下退出交互式提示的方式。</td><td>商用</td><td>交互式提示</td></tr></table>

## 2021 年 7 月

<table><tr><td>序号</td><td>功能名称</td><td>功能描述</td><td>阶段</td><td>相关文档</td></tr><tr><td>1</td><td>功能优化</td><td>KooCLI版本:2.3.5 <br> 支持无配置方式使用 KooCLI。</td><td>商用</td><td>无配置方式使用 KooCLI</td></tr><tr><td>2</td><td>新特性</td><td>KooCLI版本:2.3.3 <br> Linux/MacOS系统通过简单命令快速安装KooCLI。</td><td>商用</td><td>快速安装</td></tr></table>

## 2021 年 6 月

<table><tr><td>序号</td><td>功能名称</td><td>功能描述</td><td>阶段</td><td>相关文档</td></tr><tr><td>1</td><td>公测转商用</td><td>KooCLI版本:2.2.12 公测转商用</td><td>商用</td><td>-</td></tr></table>

## 2021 年 5 月

<table><tr><td>序号</td><td>功能名称</td><td>功能描述</td><td>阶段</td><td>相关文档</td></tr><tr><td>1</td><td>新特性</td><td>KooCLI版本:2.2.9 <br> - 支持多系统下的交互式提示。 <br> - 支持记录系统命令调用日志。</td><td>公测</td><td>- 交互式提示 <br> - 日志管理</td></tr><tr><td>2</td><td>功能优化</td><td>KooCLI版本:2.2.9 <br> 初始化配置信息时，SK匿名化展示。</td><td>公测</td><td>初始化配置</td></tr><tr><td>3</td><td>体验优化</td><td>KooCLI版本:2.2.7 <br> 完善对云服务API各参数类型的支持。</td><td>公测</td><td>-</td></tr></table>

## 2021 年 3 月

<table><tr><td>序号</td><td>功能名称</td><td>功能描述</td><td>阶段</td><td>相关文档</td></tr><tr><td>1</td><td>新特性</td><td>KooCLI版本:2.1.13 <br> 调用云服务API时，根据命令中用户的认证信息自动获取用户未输入的必填参数 “project_id”。若用户在某区域下不存在project_id，将会自动创建。</td><td>公测</td><td>-</td></tr><tr><td>2</td><td>体验优化</td><td>KooCLI版本:2.1.13 <br> 调用多版本服务的API时，若用户未指明API的版本号的， 默认调用该API的最新版本。</td><td>公测</td><td>指定云服务API 和版本号</td></tr><tr><td>3</td><td>新特性</td><td>KooCLI版本:2.1.10 <br> 调用云服务API时，根据命令中用户的认证信息自动获取用户未输入的必填参数 "domain_id"。</td><td>公测</td><td>-</td></tr></table>

## 2021 年 2 月

<table><tr><td>序号</td><td>功能名称</td><td>功能描述</td><td>阶段</td><td>相关文档</td></tr><tr><td>1</td><td>体验优化</td><td>KooCLI版本:2.1.6 <br> 优化表格化输出:“cli-output-rows”指定的数组类参数支持其索引以“:”拼接起始位至结束位；优化表格化输出相关错误提示信息。</td><td>公测</td><td>使用cli-output-rows, cli-output-cols, cli-output-num 指定表格化输出的内容</td></tr></table>

## 2020 年 12 月

<table><tr><td>序号</td><td>功能名称</td><td>功能描述</td><td>阶段</td><td>相关文档</td></tr><tr><td>1</td><td>体验优化</td><td>KooCLI版本:1.2.10 <br> - 错误提示信息的起始位置声明其具体类型: [OPENAPI_ERROR], [CLI_ERROR]或 [USE_ERROR] <br> - 调用云服务API返回错误时，根据其返回内容中的错误码提示错误中心访问链接。</td><td>公测</td><td>错误分类及定位</td></tr></table>

## 2020 年 11 月

<table><tr><td>序号</td><td>功能名称</td><td>功能描述</td><td>阶段</td><td>相关文档</td></tr><tr><td>1</td><td>新特性</td><td>KooCLI版本:1.2.9 <br> 上线调用云服务API时的日志记录功能。</td><td>公测</td><td>日志管理</td></tr><tr><td>2</td><td>新特性</td><td>KooCLI版本:1.2.8 <br> - 增加“--dryrun”选项， 实现命令检查功能:执行校验后打印请求报文，跳过实际运行。 <br> - 添加配置文件格式测试命令“hcloud configure test”。 <br> - 增加 “--cli-retry-count” 选项，支持调用云服务 API时，网络连接超时重试机制。</td><td>公测</td><td>- 命令检查选项 <br> - 检查配置文件格式 <br> - 指定请求连接重试次数</td></tr></table>

## 2020 年 10 月

<table><tr><td>序号</td><td>功能名称</td><td>功能描述</td><td>阶段</td><td>相关文档</td></tr><tr><td>1</td><td>新特性</td><td>KooCLI版本:1.2.4 <br> 调用云服务API时，支持设置网络请求连接超时时间。</td><td>公测</td><td>指定请求连接超时时间</td></tr><tr><td>2</td><td>体验优化</td><td>KooCLI版本:1.2.4 <br> 支持带“cli-”前缀的新系统参数，处理旧系统参数与华为云API参数重名的的问题。</td><td>公测</td><td>系统参数</td></tr></table>

## 2020 年 9 月

<table><tr><td>序号</td><td>功能名称</td><td>功能描述</td><td>阶段</td><td>相关文档</td></tr><tr><td>1</td><td>体验优化</td><td>KooCLI版本:1.1.11 <br> 统一输出风格，不同类别信息以不同颜色输出。</td><td>公测</td><td>-</td></tr></table>

## 2020 年 7 月

<table><tr><td>序号</td><td>功能名称</td><td>功能描述</td><td>阶段</td><td>相关文档</td></tr><tr><td>1</td><td>新特性</td><td>KooCLI版本:1.1.1 <br> - 支持bash环境的自动补全。 <br> - 支持调用多版本云服务 API。 <br> - 支持调用结果表格化输出。</td><td>公测</td><td>- 自动补全 <br> - 指定云服务 API和版本号 <br> - 使用cli-output-rows, cli-output-cols, cli-output-num 指定表格化输出的内容</td></tr></table>

## 2020 年 5 月

<table><tr><td>序号</td><td>功能名称</td><td>功能描述</td><td>阶段</td><td>相关文档</td></tr><tr><td>1</td><td>首次上线</td><td>KooCLI版本:1.0 <br> 首次上线，支持用户通过命令行调用云服务API 。</td><td>公测</td><td>-</td></tr></table>