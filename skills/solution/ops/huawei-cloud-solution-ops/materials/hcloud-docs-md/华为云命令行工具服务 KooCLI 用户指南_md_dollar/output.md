华为云命令行工具服务用户指南

文档版本 01

发布日期 2026-04-10

32

## 版权所有 (C) 华为云计算技术有限公司 2026。保留一切权利。

非经本公司书面许可，任何单位和个人不得擅自摘抄、复制本文档内容的部分或全部，并不得以任何形式传播。

## 商标声明

HUAWE和其他华为商标均为华为技术有限公司的商标。

本文档提及的其他所有商标或注册商标，由各自的所有人拥有。

## 注意

您购买的产品、服务或特性等应受华为云计算技术有限公司商业合同和条款的约束，本文档中描述的全部或部分产品、服务或特性可能不在您的购买或使用范围之内。除非合同另有约定，华为云计算技术有限公司对本文档内容不做任何明示或暗示的声明或保证。

由于产品版本升级或其他原因，本文档内容会不定期进行更新。除非另有约定，本文档仅作为使用指导，本文档中的所有陈述、信息和建议不构成任何明示或暗示的担保。

## 华为云计算技术有限公司

地址: 贵州省贵安新区黔中大道交兴功路华为云数据中心 邮编:55002

网址: https://www.huaweicloud.com/

## 目录

1 配置信息管理

1

1.1 配置命令简介

.1

1.2 初始化配置

1

1.3 新增或修改配置项

2

1.3.1 配置项参数概述.

.2

1.3.2 设置配置项中的系统参数

.4

1.3.3 设置配置项中的 custom 参数

.7

1.4 SSO 登录

7

1.5 查询配置项列表

.8

1.5.1 查询配置项列表中的系统参数

.8

1.5.2 查询配置项列表中的 custom 参数

10

1.6 查询指定配置项.

10

1.6.1 查询指定配置项中的系统参数.

10

1.6.2 查询指定配置项中的 custom 参数.

11

1.7 删除指定配置项

11

1.7.1 删除指定配置项及其 custom 参数

.11

1.7.2 删除指定配置项中的 custom 参数.

11

1.8 检查配置文件格式.

.12

1.9 删除所有配置项.

12

2 使用 HTTP 代理

13

2.1 配置 HTTP 代理.

13

2.2 解决证书 x509 问题

16

3 常用命令

.17

3.1 查看帮助信息

.17

3.2 自动补全.

17

3.3 交互式提示

18

3.4 元数据管理.

.20

3.5 查询当前版本

.21

3.6 版本更新.

.21

3.7 日志管理

21

3.8 模板管理.

.22

3.9 管理 OBS 中的数据.

.23

4 选项说明

.34

4.1 选项概述.

.34

4.2 打印帮助信息

.37

4.3 打印命令调用过程中的调试信息

.37

4.4 生成 JSON 格式 API 入参骨架

38

4.5 检查命令正确性.

40

4.6 指定区域.

41

4.7 以无配置方式 AKSK 调用云服务 API

.41

4.8 以无配置方式 AssumeRole 调用云服务 API

.42

4.9 指定用户所属账号 ID

42

4.10 指定配置项.

.42

4.11 指定配置项的认证模式.

.42

4.12 指定结果的输出格式.

43

4.13 以 JSON 文件的方式传递 API 参数

47

4.14 指定请求超时时间

49

4.15 指定请求连接重试次数.

.49

4.16 跳过 https 请求证书验证

.50

4.17 自定义请求域名

.50

4.18 结果轮询.

.51

4.19 指定签名算法.

.51

4.20 指定项目 ID

.52

5 在 API Explorer 上获取 CLI 示例

53

6 无配置方式使用 KooCLI

54

6.1 无配置方式使用概述.

54

6.2 无配置方式 AKSK.

54

6.3 无配置方式 ecsAgency.

54

7 获取认证信息

56

7.1 获取永久 AK/SK.

.56

7.2 获取账号 ID、项目 ID

.57

7.3 获取区域.

.58

7.4 获取临时 AK/SK 和 securitytoken

.58

### 1.1 配置命令简介

KooCLI配置命令包含初始化配置、配置项的增删改查等，具体命令如下表:

<table><tr><td>系统命令</td><td>功能简介</td></tr><tr><td>hcloud configure init</td><td>初始化配置</td></tr><tr><td>hcloud configure set</td><td>新增/修改配置项</td></tr><tr><td>hcloud configure sso</td><td>SSO登录</td></tr><tr><td>hcloud configure list</td><td>查询配置项列表</td></tr><tr><td>hcloud configure show</td><td>查询指定配置项</td></tr><tr><td>hcloud configure delete</td><td>删除指定配置项</td></tr><tr><td>hcloud configure test</td><td>检查配置文件格式</td></tr><tr><td>hcloud configure clear</td><td>删除所有配置项</td></tr></table>

### 1.2 初始化配置

KooCLI初始化命令用于将常用的永久AK/SK和区域信息存储在配置文件中，避免执行操作时频繁输入这些固定信息。可通过如下命令初始化配置:

hcloud configure init

输入以上命令并按回车后，会逐步提示您输入Access Key ID(必填)、Secret Access Key(必填)、默认或常用的Region(非必填)。

---

hcloud configure init

	开始初始化配置,其中"Secret Access Key"输入内容匿名化处理,获取参数可参考'https://

support.huaweicloud.com/usermanual-hcli/hcli_09.html'

	Access Key ID [required]: ******

	Secret Access Key [required]: ***

	Secret Access Key (again): ***

---

---

Region: cn-north-4

**** 						******

****** 			初始化配置成功 							******

**** 						⋆⋆⋆⋆⋆

---

### 1.3 新增或修改配置项

#### 1.3.1 配置项参数概述

如果您需要同时在多个区域或多个项目下管理资源，或者同时使用多个账号，可以通过增加配置项的方式，存储多个不同场景的固定信息。已配置多个配置项的情况下， 您可在命令中以 “--cli-profile”指定要操作或使用的配置项的名称。

KooCLI配置项中可修改的参数如下表所示。

表 1-1 配置项参数

<table><tr><td>参数名</td><td>说明</td></tr><tr><td>cli-profile</td><td>配置项名称。如果修改配置项时不指定此参数，则修改默认配置项。执行“hcloud configure show”命令可查看默认配置项的内容。</td></tr><tr><td>cli-mode</td><td>认证模式。取值范围: <br> - AKSK:分为访问密钥和临时安全凭证。访问密钥即为永久 AK/SK，临时安全凭证即为临时AK，SK和SecurityToken。 <br> - ecsAgency:当委托给ECS服务器时，在ECS服务器中使用 KooCLI调用云服务API时自动获取临时认证信息。 <br> - SSO:开通IAM身份中心并完成配置后，允许用户使用特定用户名和密码登录统一的用户门户网站，访问为其分配的多个账号下的资源。认证信息有效期内，无需多次登录。 <br> - AssumeRole:账号间委托关系建立后，被委托方通过委托方式认证，可代为管理委托方的云服务和资源。</td></tr><tr><td>cli-region</td><td>区域。</td></tr><tr><td>cli-access-key</td><td>访问密钥ID(Access Key ID，简称AK)，此参数必须和SK同步修改。</td></tr><tr><td>cli-secret-key</td><td>秘密访问密钥(Secret Access Key，简称SK)，此参数必须和 AK同步修改。</td></tr><tr><td>cli-security-token</td><td>临时安全凭证。在使用临时AK/SK认证身份时，需同时使用此参数。注意过期后需重新配置，否则调用云服务API时无法完成认证。</td></tr><tr><td>cli-local-dea</td><td>本地加密保存的认证信息及custom参数的加密算法。取值范围: <br> - intl(默认值，表示使用国际算法) <br> - gm(表示使用国密算法)</td></tr></table>

<table><tr><td>参数名</td><td>说明</td></tr><tr><td>cli-lang</td><td>KooCLI的语言。取值范围: <br> - cn(中文) <br> - en(英文)</td></tr><tr><td>cli-offline</td><td>是否使用KooCLI的离线模式。取值范围: <br> - true(表示使用离线模式) <br> - false(默认值，表示使用在线模式)</td></tr><tr><td>cli-project-id</td><td>项目ID。</td></tr><tr><td>cli-domain-id</td><td>IAM用户所属账号ID，以AKSK模式调用全局服务的API时需要。</td></tr><tr><td>cli-custom</td><td>是否操作custom参数。取值范围: <br> - true(表示要操作配置项中的custom参数) <br> - false(默认值，表示要操作配置项中的系统参数)</td></tr><tr><td>cli-read-timeout</td><td>I/O超时时间(秒)。默认取值为10秒，参数最小取值为1秒。</td></tr><tr><td>cli-connect-timeout</td><td>请求连接超时时间(秒)。默认取值为5秒，参数最小取值为1 秒。</td></tr><tr><td>cli-retry-count</td><td>请求连接重试次数。默认取值为0次，可配置的取值范围为 0~5次。</td></tr><tr><td>cli-skip-secure-verify</td><td>是否跳过https请求证书验证(不建议)。取值范围: <br> - true(表示要跳过https请求证书验证，出于安全考虑不建议) <br> - false(默认值，表示不跳过https请求证书验证)</td></tr><tr><td>cli-agency-domain-name</td><td>委托方的账号名称，必须和cli-agency-name同时使用</td></tr><tr><td>cli-agency-domain-id</td><td>委托方的账号ID，必须和cli-agency-name同时使用</td></tr><tr><td>cli-agency-name</td><td>委托名称，必须和cli-agency-domain-id或cli-agency-domain-name同时使用</td></tr><tr><td>cli-source-profile</td><td>保存被委托方认证信息的配置项。配置项的cli-source-profile 取值不能是当前配置项。</td></tr><tr><td>cli-agree-privacy-statement</td><td>是否同意隐私。首次使用KooCLI时，KooCLI会通过交互，提示用户阅读并同意隐私声明。对于不方便交互的场景，如以自动化脚本执行命令，可通过此参数配置同意隐私声明。取值范围: <br> - true(表示同意隐私声明) <br> - false(默认值，表示不同意隐私声明)</td></tr></table>

<table><tr><td>参数名</td><td>说明</td></tr><tr><td>cli-warning</td><td>是否提示命令执行过程中的Warning信息。以自动化脚本执行命令时，关闭Warning提示信息，可以避免干扰解析命令执行的输出结果。取值范围: <br> - true(默认值，表示提示Warning信息) <br> - false(表示不提示Warning信息)</td></tr><tr><td>cli-auth-encrypt</td><td>配置文件中的认证信息是否加密存储。取值范围: <br> - true(默认值，表示加密存储配置文件中的认证信息) <br> - false(表示不加密存储配置文件中的认证信息)</td></tr><tr><td>cli-sso-start-url</td><td>用户门户URL，开通IAM身份中心后生成。</td></tr><tr><td>cli-sso-region</td><td>开通IAM身份中心实例所在的区域。</td></tr><tr><td>cli-sso-account-name</td><td>账号名。</td></tr><tr><td>cli-sso-permission-set-name</td><td>权限集名称。</td></tr></table>

☐说明

- 参数 “--cli-custom” 的取值可标识向配置项中设置的参数类型:当 “--cli-custom=false” 时，设置其中的系统参数；当“--cli-custom=true”时，设置其中的custom(即用户自定义) 参数。

- 设置配置项中的系统参数时，若该配置项不存在则新增配置项，否则修改该配置项。

- 不支持向不存在的配置项中设置custom参数; 不支持在同一命令中同时设置系统参数和 custom参数。

- 向配置项中设置系统参数或custom参数，都会使该配置项成为默认配置项。

新增或修改配置项的命令为:

---

hcloud configure set --param1=paramValue1 --param2=paramValue2 ...

---

#### 1.3.2 设置配置项中的系统参数

设置配置项中的系统参数的示例如下:

- 增加配置项

新增配置项时，以 “--cli-profile” 声明配置项的名称，示例如下:

- 新增认证模式为AK/SK的配置项，其中认证参数为访问密钥，即永久AK(cli-access-key)和SK(cli-secret-key):

---

hcloud configure set --cli-profile=testAKSK --cli-mode=AKSK --cli-region=cn-north-4 --cli-access-

	key=******* --cli-secret-key=******* --cli-project-id=068119468*

	id=094518e46***************cfbc4c0 --cli-read-timeout=10 --cli-connect-timeout=5

---

- 新增认证模式为AK/SK的配置项，其中认证参数为临时安全凭证，即临时AK (cli-access-key)，SK(cli-secret-key)和SecurityToken(cli-security-token ) :

hcloud configure set --cli-profile=testAKSKST --cli-mode=AKSK --cli-region=cn-north-4 --cli-access-key=******* --cli-secret-key=****** --cli-security-token=****** --cli-project-

---

id=068119468***************af89d2e --cli-domain-id=094518e46******************cfbc4c0 --cli-read-

timeout=10 --cli-connect-timeout=5

---

当配置项的认证模式为AK/SK时，若该配置项中同时配置了cli-security-token 参数值，则默认其中cli-access-key和cli-secret-key为临时AK/SK，否则为永久AK/SK。

- 新增认证模式为ecsAgency的配置项，无需添加认证参数:

---

	hcloud configure set --cli-profile=testEcsAgency --cli-mode=ecsAgency --cli-region=cn-north4 --

cli-read-timeout=10 --cli-connect-timeout=5

---

当在被委托的ECS服务器中使用KooCLI调用云服务API时，会根据ECS委托自动获取临时认证信息。

- 新增认证模式为AssumeRole的配置项，其中认证参数为委托方的账号名 (cli-agency-domain-name)或账号ID(cli-agency-domain-id)，委托名称 ( cli-agency-name ) ，保存被委托方认证信息的配置项(cli-source-profile ) :

i. 先新增保存被委托方认证信息的配置项(非必须，可使用已添加的配置项)，其认证模式应为AKSK:

---

hcloud configure set --cli-profile=testAKSK --cli-mode=AKSK --cli-region=cn-north-4 --cli-

	access-key=******* --cli-secret-key=******

---

ii. 新增认证模式为AssumeRole的配置项。其中，将上一步的配置项作为 cli-source-profile:

---

hcloud configure set --cli-profile=testAssumeRole --cli-mode=AssumeRole --cli-region=cn-

north-4 --cli-agency-domain-id=13534326*************5cf67b --cli-agency-name=****

		cli-source-profile=testAKSK --cli-read-timeout=10 --cli-connect-timeout=5

---

新增认证模式为AssumeRole的配置项时，cli-agency-domain-id(或cli-agency-domain-name)与cli-agency-name必须同时配置；cli-profile不能与命令中的cli-source-profile取值相同；cli-source-profile指定的配置项必须已存在。

- 新增认证模式为SSO的配置项，其中认证参数为用户门户URL(cli-sso-start-url)，开通IAM身份中心实例所在的区域(cli-sso-region)，账号名(cli-sso-account-name)，权限集名称(cli-sso-permission-set-name)，其中参数cli-sso-account-name与cli-sso-permission-set-name非必填:

i. 先新增认证模式为SSO的配置项:

---

	hcloud configure set --cli-profile=testSSO --cli-mode=SSO --cli-region=cn-north-4 --cli-sso-

start-url=https://idcenter.huaweicloud.com/d-3*******6/portal --cli-sso-region=cn-north-4 --

cli-sso-account-name=ACCOUNT_01 --cli-sso-permission-set-name=PERMISSION_01

---

ii. 进行SSO登录，若第一步中未配置cli-sso-account-name与cli-sso-permission-set-name参数，登录过程中需按照提示选择账号名与权限集名称:

---

hcloud configure sso --cli-profile=testSSO

---

- 切换默认配置项

用户已配置多个配置项时，可执行如下命令切换默认配置项:

hcloud configure set --cli-profile=test

- 切换语言

语言切换后，将作用于所有配置项。切换语言的命令为:

hcloud configure set --cli-lang=en

- 切换本地数据的加密算法

用户添加配置项后，以此算法在本地加密保存取值的认证信息及custom参数。加密算法切换后，将作用于所有配置项。切换加密算法的命令为:

hcloud configure set --cli-local-dea=gm

- 切换在线/离线模式

在线/离线模式切换后，将作用于所有配置项。切换为离线模式的命令为: hcloud configure set --cli-offline=true

- 修改是否提示Warning信息

是否提示Warning信息修改后，将作用于所有配置项。以自动化脚本执行命令时，关闭Warning提示信息，可以避免干扰解析命令执行的输出结果。关闭 Warning信息的命令为:

hcloud configure set --cli-warning=false

- 修改是否同意隐私声明

是否同意隐私声明修改后，将作用于所有配置项。首次使用KooCLI时，KooCLI会通过交互，提示用户阅读并同意隐私声明。对于不方便交互的场景，如以自动化脚本执行命令，可通过如下命令配置同意隐私声明:

---

hcloud configure set --cli-agree-privacy-statement=true

---

- 修改是否加密存储配置文件中的认证信息

是否加密存储配置文件中的认证信息修改后，将作用于所有配置项。可通过如下命令配置不加密存储配置文件中的认证信息:

hcloud configure set --cli-auth-encrypt=false

- 修改指定配置项的认证模式

同一配置项可同时配置多种认证模式相关的参数。通过如下命令可指定该配置项的认证模式:

hcloud configure set --cli-profile=test --cli-mode=AKSK

- 修改指定配置项的区域

hcloud configure set --cli-profile=test --cli-region=cn-north-4

- 修改指定配置项的AK/SK

AK和SK必须一起修改:

hcloud configure set --cli-profile=test --cli-access-key=****** --cli-secret-key=******

- 修改指定配置项的项目ID

部分云服务的API需要指定项目ID，用户可先获取项目ID，再将常用的项目ID添加到配置项中:

hcloud configure set --cli-profile=test --cli-project-id=068119468*************af89d2e

- 修改指定配置项的请求连接超时时间

hcloud configure set --cli-profile=test --cli-connect-timeout=5

- 修改指定配置项的I/O超时时间

hcloud configure set --cli-profile=test --cli-read-timeout=10

- 修改指定配置项的请求连接重试次数

hcloud configure set --cli-profile=test --cli-retry-count=3

A 注意

需要注意的是，因为使用“--cli-retry-count”设置重试次数可能会导致调用接口幂等性的问题，有重复调用的风险。对于创建类的接口，请您谨慎使用。

- 修改指定配置项的跳过https请求证书验证选项的值

hcloud configure set --cli-profile=test --cli-skip-secure-verify=true

说明

注:配置项可以一次修改多个参数，例如同时修改cli-project-id和cli-region，命令如下:

hcloud configure set --cli-profile=test --cli-project-id=0681194******************\$f89d2e --cli-region=cn-north-4

#### 1.3.3 设置配置项中的 custom 参数

KooCLI支持向配置项中设置custom参数，方便用户集中管理命令中高频使用，参数值过长，或需要对其值加密处理的参数。使用如下命令进入交互模式，根据提示新增或修改配置项中的custom参数:

hcloud configure set [--cli-profile=\$\{profileName\}] --cli-custom=true

---

hcloud configure set --cli-profile=test --cli-custom=true

																1.请输入custom参数的名称: projectId

													2.此custom参数值是否加密保存(y/N): n

													3.请输入custom参数的值:068100000000000000000000000f89d2e

														此custom参数已保存，使用`Ctrl+C`可终止设置custom参数

														1.请输入custom参数值是否加密保存(y/N):y

														2. 此custom参数值是否加密保存(y/N): y

														3.请输入custom参数的值: ****

														此custom参数已保存，使用`Ctrl+C`可终止设置custom参数

---

custom参数的名称不能超过128位字符。在交互设置的过程中，用户可根据custom参数在使用中的实际需要判断该参数是否需要加密保存。对于需要加密保存的custom参数，为保障您的参数安全，对您输入的参数值进行了匿名化处理。在您输入过程中不会显示输入的字符，在输入结束回车至下一行时，会以 “****” 回显您的输入内容。

使用custom参数的方法是将命令中原参数的value值用 “custom.\$\{custom参数的名称\}" 代替，例如:

hcloud ECS NovaListServers --cli-profile=test --project_id="custom.projectId"

使用被加密存储的custom参数时，KooCLI会在可能显示其值的情况下(例如:debug 信息中打印的request请求的url，或dryrun模式下打印的body体参数)，对其值做匿名化处理。

### 1.4 SSO 登录

KooCLI的SSO登录命令通过完成SSO登录，将用户的认证信息存储在配置文件中，避免执行操作时频繁输入这些固定信息。可通过如下命令进行SSO登录:

hcloud configure sso

输入以上命令并回车后，会逐步提示您输入SSO profile name(此SSO登录后要保存的配置项名称，必填)、SSO start URL(用户门户URL，必填)、SSO region(开通 IAM身份中心所在的区域，必填)、Region(默认或常用区域，非必填)。

---

hcloud configure sso

? Input SSO profile name [required]: sso

? Input SSO start URL [required]: https://idcenter.huaweicloud.com/d-3*******6/portal

? Input SSO region [required]: cn-north-4

? Input Region: cn-north-4

	已打开浏览器页面，等待您完成SSO登录...

? Choose account name: ACCOUNT_01

	? Choose permission set name: PERMISSION_01

SSO登录成功

---

## 须知

- 在Linux等无浏览器的环境，无法自动跳转SSO登录页面，需要用户在浏览器打开打印的URL链接完成登录。

- 在网页完成登录后，选择account name和permission set name时，请使用键盘上下箭头移动，可键入筛选列表内容，按Enter键即可选中当前内容。

- SSO登录完成后，仅支持调用此列表中服务的API。

登录完成后，可使用命令查看登录后保存的认证信息及其过期时间:

hcloud configure show --cli-profile=\$\{profileName\}

---

hcloud configure show --cli-profile=sso

\{

															"name": "sso",

																"mode": "SSO",

																"accessKeyld": "",

																"secretAccessKey": "",

																"securityToken": "",

																"region": "cn-north-4",

																"projectId": "",

																	"domainId": "",

																"skipSecureVerify": "false",

																"readTimeout": 10,

																"connectTimeout": 5,

															"retryCount": 0,

																	"ssoParam": \{

																													"startUrl": "https://idcenter.huaweicloud.com/d-3*******6/portal",

																													"ssoRegion": "cn-north-4"

														\},

																"ssoAuth": \{

																														"accessTokenResult": \{

																																										"accessToken": "****",

																																											"expiresAt": "2024-05-08 00:52:50"

																										\},

																															"accountId": "0cb8*************************c3a0",

																															"agencyUrn": "iam::0cb8*************************c3a0:agency:Sys*********_******/

				\}

\}

---

### 1.5 查询配置项列表

#### 1.5.1 查询配置项列表中的系统参数

KooCLI支持多配置项，查询配置项列表中的系统参数的命令如下，查询结果支持以 table，json或tsv格式输出，默认以json格式输出:

hcloud configure list

---

hcloud configure list

\{

																"localDea": "intl",

																"language": "cn",

															"offline": "false",

															"agreePrivacy": "true",

																"warning": "true",

																"current": "test",

																"profiles": [

																													\{

																																								"name": "default",

		"mode": "AKSK",

		"accessKeyld": "*********,

		"secretAccessKey": "*****",

		"securityToken": "",

		"region": "cn-north-4",

		"projectId": "060576***************134588f135",

		"domainId": "",

		"skipSecureVerify": "false",

		"readTimeout": 10,

		"connectTimeout": 5,

		"retryCount": 0

		\},

		"name": "test",

		"mode": "AKSK",

		"accessKeyld": "********",

		"secretAccessKey": "******",

		"securityToken": "",

		"region": "cn-north-4",

		"projectId": "",

		"domainId": "",

		"skipSecureVerify": "false",

		"readTimeout": 10,

		"connectTimeout": 5,

		"retryCount": 0

	\}

]

\}

---

其中，敏感参数的值会被匿名化展示。

可以使用 "--cli-query" 对查询结果进行过滤。使用 "--cli-query" 时，默认以json格式输出，可同时使用 "--cli-output" 指定输出格式。例如以json格式输出，筛选每个配置项中的AK/SK:

---

hcloud configure list --cli-output=json --cli-query="profiles[].

\{Name:name, AK:accessKeyId, SK:secretAccessKey\}"

	\{

		"AK": "*********",

		"Name": "default",

		"SK": "*****"

	\},

		"AK": "*********",

		"Name": "test",

		"SK": "*****

\}

]

---

如需以table格式输出查询结果，命令中需要指定 "--cli-output=table" ，如下:

hcloud configure list --cli-output=table --cli-query="profiles[].

[name, accessKeyId, secretAccessKey, projectId]"

C:\\ci\}hcloud configure list --cli-output=table --cli-query="profiles[]. [name, accessKeyId, secretAccessKey, projectId]'

default|H9N******MXW|***|0605###########%f135

| --------+-----------+-------------------------------------------

test | 8NV****IOV|****

如需以tsv格式输出查询结果，命令中需要指定 “--cli-output=tsv”，如下:

hcloud configure list --cli-output=tsv --cli-query="profiles[0].

[name, accessKeyld, secretAccessKey, projectId]"

___

cretAccessKev.projectId]"

___

C:\\cli>_

#### 1.5.2 查询配置项列表中的 custom 参数

查询KooCLI配置项列表中的custom参数的命令如下，查询结果支持以table，json或 tsv格式输出，默认以json格式输出:

hcloud configure list --cli-custom=true

---

hcloud configure list --cli-custom=true

\{

	"current": "test",

	"profiles": [

		\{

			"name": "default",

			"custom": \{\}

		\},

		\{

			"name": "test",

			"custom": \{

			"password": \{

				"value": "****",

				"isEncrypted": true

			\},

			"projectId": \{

				"value": "06810000000000000000000000f89d2e",

				"isEncrypted": false

			\}

		\}

	\}

\}

---

其中，加密保存的custom参数值会被匿名化展示。

可以使用 "--cli-query" 对查询结果进行过滤，使用 "--cli-query" 时，默认以json格式输出，可同时使用 "--cli-output" 指定输出格式。例如以json格式输出，查询名称为test的配置项的所有custom参数:

---

hcloud configure list --cli-custom=true --cli-query="profiles[?name=='test'].custom" --cli-output=json

[

	\{

		"password": \{

			"isEncrypted": true,

			"value": "****"

		\},

		"projectId": \{

			"isEncrypted": false,

			"value": "06810000000000000000000000f89d2e"

	\}

	1

1

---

### 1.6 查询指定配置项

#### 1.6.1 查询指定配置项中的系统参数

使用 “--cli-profile” 指定要查询的配置项的名称，缺省时查询默认配置项。支持以 table，json或tsv格式输出，默认以json格式输出。查看指定配置项中的系统参数的命令为:

hcloud configure show [--cli-profile=\$\{profileName\}]

---

hcloud configure show --cli-profile=test

\{

	"name": "test",

	"mode": "AKSK",

	"accessKeyld": "********",

	"secretAccessKey": "****",

	"securityToken": "",

	"region": "cn-north-4",

	"projectId": "",

	"domainId": "",

	"skipSecureVerify": "false",

	"readTimeout": 10,

	"connectTimeout": 5,

	"retryCount": 0

\}

---

#### 1.6.2 查询指定配置项中的 custom 参数

使用“--cli-profile”指定要查询的配置项的名称，支持以table，json或tsv格式输出， 默认为json格式。查看指定配置项中的custom参数的命令为:

hcloud configure show [--cli-profile=\$\{profileName\}] --cli-custom=true

---

	hcloud configure show --cli-profile=test --cli-custom=true

	\{

																			"password": \{

																														"value": "****",

																														"isEncrypted": true

																\},

																		"projectId": \{

																														"value": "068100000000000000000000000f89d2e",

																														"isEncrypted": false

						\}

\}

---

### 1.7 删除指定配置项

#### 1.7.1 删除指定配置项及其 custom 参数

使用 “--cli-profile” 指定要删除的配置项的名称。删除指定配置项的命令为:

hcloud configure delete --cli-profile=\$\{profileName\}

---

hcloud configure delete --cli-profile=test

删除配置项test成功，默认配置项为default

---

删除配置项时，会同时删除其中的系统参数和custom参数。

#### 1.7.2 删除指定配置项中的 custom 参数

使用“--cli-profile”指定要删除的配置项的名称。删除指定配置项中的custom参数的命令可分为:

- 删除指定配置项中的指定custom参数:

hcloud configure delete --cli-profile=\\(\{profileName\} [--cli-custom=true] --cli-custom-key=$\{customName\}

---

	hcloud configure delete --cli-profile=test --cli-custom-key=projectId

删除配置项test中的custom参数projectId成功

- 删除指定配置项中的所有custom参数:

	hcloud configure delete --cli-profile=\$\{profileName\} --cli-custom=true

	hcloud configure delete --cli-profile=test --cli-custom=true

	删除配置项test中的所有custom参数成功

---

### 1.8 检查配置文件格式

为快速检验本地配置文件的格式是否正确，可执行如下命令:

hcloud configure test

---

hcloud configure test

	配置文件格式正确

---

### 1.9 删除所有配置项

可执行如下命令，经交互确认后即可删除所有配置项:

hcloud configure clear

hcloud configure clear

是否删除所有配置信息(y/N): y

已删除所有配置信息

### 2.1 配置 HTTP 代理

用户在使用KooCLI管理和使用云服务的资源时，可能会因为用户所在公司的内网访问限制，导致调用云服务API失败。此时，用户可使用HTTP代理访问。使用HTTP代理需要配置环境变量http_proxy和https_proxy。

## 配置 http_proxy 环境变量

请根据您系统选择并执行如下命令，配置http_proxy环境变量。

- Linux或MacOS系统

- 临时环境变量

配置http_proxy的命令为:

export http_proxy="http://username:password@proxyServer:port"

其中，proxyServer为代理服务器的域名(如果能解析)或者IP。port为端口号。如果你的代理服务器需要用户名和密码才能访问，需要填写上面的 username和password部分，否则的话，可以省略这两部分，如下:

export http_proxy="http://proxyServer:port"

- 永久环境变量

在~/.bashrc文件中添加如下内容，可将http_proxy永久配置在当前用户的环境变量中:

export http_proxy="http://username:password@proxyServer:port"

其中，proxyServer为代理服务器的域名(如果能解析)或者IP。port为端口号。如果你的代理服务器需要用户名和密码才能访问，需要填写上面的 username和password部分，否则的话，可以省略这两部分，如下:

export http_proxy="http://proxyServer:port"

请注意:永久环境变量配置完毕后，一般需要注销并重新登录，配置才可生效。

- Windows系统

- 使用cmd:

- 临时环境变量

配置http_proxy的命令为:

set http_proxy=http://username:password@proxyServer:port

其中，proxyServer为代理服务器的域名(如果能解析)或者IP。port为端口号。如果你的代理服务器需要用户名和密码才能访问，需要填写上面的username和password部分，否则的话，省略这两部分，如下: set http_proxy=http://proxyServer:port

- 永久环境变量

将http_proxy永久配置在当前用户的环境变量中的命令为: setx "http_proxy" "http://username:password@proxyServer:port"

其中，proxyServer为代理服务器的域名(如果能解析)或者IP。port为端口号。如果你的代理服务器需要用户名和密码才能访问，需要填写上面的username和password部分，否则的话，省略这两部分，如下:

---

setx "http_proxy" "http://proxyServer:port"

---

请注意:永久环境变量配置完毕后，将在新打开的终端中生效，当前终端不会立即生效。

- 使用PowerShell:

- 临时环境变量

配置http_proxy的命令为:

\$env:http_proxy="http://username:password@proxyServer:port"

其中，proxyServer为代理服务器的域名(如果能解析)或者IP。port为端口号。如果你的代理服务器需要用户名和密码才能访问，需要填写上面的username和password部分，否则的话，省略这两部分，如下: \$env:http_proxy="http://proxyServer:port"

- 永久环境变量

将http_proxy永久配置在当前用户的环境变量中的命令为:

[environment]::SetEnvironmentvariable("http_proxy", "http:// username:password@proxyServer:port", "User")

其中，proxyServer为代理服务器的域名(如果能解析)或者IP。port为端口号。如果你的代理服务器需要用户名和密码才能访问，需要填写上面的username和password部分，否则的话，省略这两部分，如下:

[environment]::SetEnvironmentvariable("http_proxy", "http://proxyServer:port", "User")

请注意:永久环境变量配置完毕后，将在新打开的终端中生效，当前终端不会立即生效。

## 配置 https_proxy 环境变量

请根据您系统选择并执行如下命令，配置https_proxy环境变量。

- Linux或MacOS系统

- 临时环境变量

配置https_proxy的命令为:

export https_proxy="https://username:password@proxyServer:port"

其中，proxyServer为代理服务器的域名(如果能解析)或者IP。port为端口号。如果你的代理服务器需要用户名和密码才能访问，需要填写上面的 username和password部分，否则的话，可以省略这两部分，如下:

export https_proxy="https://proxyServer:port"

- 永久环境变量

在~/.bashrc文件中添加如下内容，可将https_proxy永久配置在当前用户的环境变量中:

export https_proxy="https://username:password@proxyServer:port"

其中，proxyServer为代理服务器的域名(如果能解析)或者IP。port为端口号。如果你的代理服务器需要用户名和密码才能访问，需要填写上面的 username和password部分，否则的话，可以省略这两部分，如下:

---

export https_proxy="https://proxyServer:port"

---

请注意:永久环境变量配置完毕后，一般需要注销并重新登录，配置才可生效。

- Windows系统

- 使用cmd:

- 临时环境变量

配置https_proxy的命令为:

set https_proxy=https://username:password@proxyServer:port

其中，proxyServer为代理服务器的域名(如果能解析)或者IP。port为端口号。如果你的代理服务器需要用户名和密码才能访问，需要填写上面的username和password部分，否则的话，省略这两部分，如下:

---

set https_proxy = https://proxyServer:port

---

- 永久环境变量

将https_proxy永久配置在当前用户的环境变量中的命令为: setx "https_proxy" "https://username:password@proxyServer:port"

其中，proxyServer为代理服务器的域名(如果能解析)或者IP。port为端口号。如果你的代理服务器需要用户名和密码才能访问，需要填写上面的username和password部分，否则的话，省略这两部分，如下:

---

setx "https_proxy" "https://proxyServer:port"

---

请注意:永久环境变量配置完毕后，将在新打开的终端中生效，当前终端不会立即生效。

- 使用PowerShell

- 临时环境变量

---

配置https_proxy的命令为:

	\$env:https_proxy="https://username:password@proxyServer:port"

---

其中，proxyServer为代理服务器的域名(如果能解析)或者IP。port为端口号。如果你的代理服务器需要用户名和密码才能访问，需要填写上面的username和password部分，否则的话，省略这两部分，如下:

---

\$env:https_proxy="https://proxyServer:port"

---

- 永久环境变量

将https_proxy永久配置在当前用户的环境变量中的命令为:

[environment]::SetEnvironmentvariable("https_proxy", "https:// username:password@proxyServer:port", "User")

其中，proxyServer为代理服务器的域名(如果能解析)或者IP。port为端口号。如果你的代理服务器需要用户名和密码才能访问，需要填写上面的username和password部分，否则的话，省略这两部分，如下:

---

[environment]::SetEnvironmentvariable("https_proxy", "https://proxyServer:port", "User")

---

请注意:永久环境变量配置完毕后，将在新打开的终端中生效，当前终端不会立即生效。

### 2.2 解决证书 x509 问题

KooCLI管理和使用云服务的资源，用户在配置了HTTP代理的情况下，可能会出现调用云服务API时报错 x509 的问题。其原因是您公司代理修改了https网站颁发的根证书， 导致访问外网的https资源时报证书无效的错误。

您可以通过在命令中添加 “--cli-skip-secure-verify=true” 跳过证书校验(不建议)。 推荐的做法是:将您公司颁发的证书导入到操作系统的可信任CA证书下。

### 3.1 查看帮助信息

KooCLI支持在命令中添加 “--help” 参数查看帮助信息，例如:

- hcloud --help

查看KooCLI的使用方法及支持的云服务列表。

- hcloud <service> --help

查看指定云服务的operation列表。例如查看“ECS”服务的operation列表: hcloud ECS --help

- hcloud <service> <operation> --help

查看指定云服务API的详情信息。例如查看“ECS”服务中，operation为 “ShowServer”的API详情:hcloud ECS ShowServer --help

### 3.2 自动补全

KooCLI开启自动补全后，在输入命令时使用“Tab”键，会根据已有命令提示其待补全的内容。

开启自动补全功能:

hcloud auto-complete on

hcloud auto-complete on

开启成功!自动补全仅支持bash,若未生效请执行`bash`命令

关闭自动补全功能:

hcloud auto-complete off

hcloud auto-complete off

关闭成功！若未生效请执行`bash`命令

☐说明

- 自动补全功能仅支持bash。

- 自动补全提示参数时，若提示的参数名中有“[N]”，其含义为索引位，请使用数字代替该字符；若提示的参数名中有“\{*\}”，其含义为自定义参数名称，请使用任意不含“.”的字符串代替该字符；

### 3.3 交互式提示

KooCLI支持功能强大的多平台支持的交互式提示，方便命令构建，在命令中添加“一 interactive" 参数即可进入交互式提示。交互式中根据用户当前输入的内容，提示云服务名称，API的operation，参数及其描述信息，也提供部分参数值的补全功能。

- 交互式的使用方式如下:

- 交互模式中使用“Tab”或向上箭头、向下箭头键实现待补全内容的上下选择。

- 选中待补全内容后，使用空格键将已选内容追加到当前命令中。

- 进入交互模式后，使用 “Ctrl+C” 可切换至新命令行，使用 “Ctrl+D” 可退出交互模式。

- 交互式可提示和补全如下内容:

- 云服务

初次进入交互模式后，会自动提示云服务及系统命令列表。

图 3-1 交互式中提示云服务和系统命令列表

![019db8ba-f9dc-74e1-ad16-95f757e5f1e5_21_504_993_983_266_0.jpg](images/019db8ba-f9dc-74e1-ad16-95f757e5f1e5_21_504_993_983_266_0.jpg)

所提示的云服务列表中，左列展示云服务短名/系统命令，右列展示该云服务的服务名称/该系统命令的描述信息。

- API

已输入的云服务/系统命令经校验无误后，会继续提示该服务的API列表/该系统命令的子命令(或参数)。

所提示的系统命令列表中，左列展示该系统命令的子命令(或参数)，右列展示该子命令(或参数)的描述信息。

图 3-2 交互式中提示云服务的 API 列表

![019db8ba-f9dc-74e1-ad16-95f757e5f1e5_21_504_1688_980_289_0.jpg](images/019db8ba-f9dc-74e1-ad16-95f757e5f1e5_21_504_1688_980_289_0.jpg)

所提示的云服务API列表中，左列展示API的operation名称，右列展示该API 的描述信息。

图 3-3 交互式中提示系统命令的子命令

![019db8ba-f9dc-74e1-ad16-95f757e5f1e5_22_504_280_983_250_0.jpg](images/019db8ba-f9dc-74e1-ad16-95f757e5f1e5_22_504_280_983_250_0.jpg)

图 3-4 交互式中提示系统命令的参数

![019db8ba-f9dc-74e1-ad16-95f757e5f1e5_22_506_624_978_169_0.jpg](images/019db8ba-f9dc-74e1-ad16-95f757e5f1e5_22_506_624_978_169_0.jpg)

## 若已输入的云服务/系统命令非法，则不再提示任何信息。

- 参数

已输入服务名与API的operation，或已输入系统命令及其子命令经校验无误后，会继续提示该API/系统命令子命令的参数列表。

图 3-5 交互式中提示云服务 API 的参数列表

![019db8ba-f9dc-74e1-ad16-95f757e5f1e5_22_507_1095_978_106_0.jpg](images/019db8ba-f9dc-74e1-ad16-95f757e5f1e5_22_507_1095_978_106_0.jpg)

图 3-6 交互式中提示系统命令子命令的参数列表

![019db8ba-f9dc-74e1-ad16-95f757e5f1e5_22_506_1294_978_191_0.jpg](images/019db8ba-f9dc-74e1-ad16-95f757e5f1e5_22_506_1294_978_191_0.jpg)

所提示的参数列表中，左列展示参数名称；右列展示该参数的描述信息。

若已输入API的operation/系统命令子命令非法，或已输入的参数名非法，则不再提示任何信息。

- 参数值

在交互式中，在部分参数名后输入等号，会提示该参数的可取值或默认值列表。例如:若调用API的命令中当前输入的参数是 "--cli-region=" 时，会提示该API的可选区域列表。

图 3-7 交互式中提示已输入云服务 API 的可选区域列表

![019db8ba-f9dc-74e1-ad16-95f757e5f1e5_23_506_279_981_305_0.jpg](images/019db8ba-f9dc-74e1-ad16-95f757e5f1e5_23_506_279_981_305_0.jpg)

- 交互模式下的快捷键

- Ctrl + W: 将光标前的单词删除

- Ctrl + K: 将光标之后的内容删除

- Ctrl + U: 将光标之前的内容删除

- Ctrl + L: 清除屏幕

☐ 说明

- 若用户尚未添加配置项，或默认配置项中的区域不被命令中的API所支持，用户需先根据提示，从目标API支持的cli-region列表中选择合适的区域值。确定区域后，KooCLI会继续提示该API的参数列表。

- 交互式提示参数时，除自定义map类型的参数(即:参数名中包含“\{*\}”的参数)外，已输入的参数不会重复提示；若提示的参数名中有“[N]”，其含义为索引位，请使用数字代替该字符；若提示的参数名中有“\{*\}”，其含义为自定义参数名称，请使用任意不含“.”的字符串代替该字符。

- 切换至新命令行后可使用向上箭头和向下箭头浏览已执行命令的历史记录。

### 3.4 元数据管理

- 清理元数据缓存

KooCLI会缓存API调用过程中获取并保存在用户本地的元数据缓存文件，放置在如下目录下:

- 在线模式:

- Windows系统:C:\\Users\\\{您的Windows系统用户名\}\\.hcloud \\\\metaRepo\\\\

- Linux系统: /home/\{当前用户名\}/.hcloud/metaRepo/

- Mac系统: /Users/\{当前用户名\}/.hcloud/metaRepo/

- 离线模式:

- Windows系统:C:\\Users\\\{您的Windows系统用户名\}\\.hcloud \\metaOrigin\\

- Linux系统: /home/\{当前用户名\}/.hcloud/metaOrigin/

- Mac系统: /Users/\{当前用户名\}/.hcloud/metaOrigin/ 清理元数据缓存文件的命令为:

- 在线模式:

hcloud meta clear

hcloud meta clear

缓存清理成功

- 离线模式:

执行命令 “hcloud meta clear”，会清理从已下载的离线元数据包中解析出来的元数据缓存文件，离线元数据包仍然保留。之后调用API时，会重新从该离线元数据包中解析并写入新元数据缓存文件。若需完全清理离线元数据包及元数据缓存文件，用户需根据系统，删除该文件所在目录。

- 下载离线元数据包

离线元数据包下载后，将被保存在上述离线模式的目录下。下载离线元数据包的命令为:

hcloud meta download

---

hcloud meta download

下载成功

---

### 3.5 查询当前版本

查询KooCLI当前版本的命令为:

hcloud version

---

hcloud version

	当前KooCLI版本:3.2.8

---

### 3.6 版本更新

KooCLI支持本地更新， 运行更新命令经交互确认后可将其升级至最新版本。更新命令如下:

hcloud update

---

	hcloud update

KooCLI将更新到最新版本，请您确认是否继续(y/N): y

更新成功

---

执行版本更新命令时，在命令中添加 “-y” 参数，可跳过交互确认，直接更新:

---

hcloud update -y

	更新成功

---

### 3.7 日志管理

KooCLI提供日志记录和管理功能，会缓存API调用过程中产生的日志信息，日志文件保存目录如下:

- Windows系统:C:\\Users\\\{您的Windows系统用户名\\\\.hcloud\\log\\\\

- Linux系统: /home/\{当前用户名\}/.hcloud/log/

- Mac系统: /Users/\{当前用户名\}/.hcloud/log/

日志管理相关参数有:

- level: 日志记录级别，可选值为info、warning、error

- max-file-size:单个日志文件大小(MB)，min=1，max=100，默认值20

- max-file-num:日志文件保留个数(0表示保留所有日志文件)，默认值3

- retention-period:日志文件保留时间(天)(0表示永久保留)

未配置时默认日志级别为error，单个日志文件大小为20MB，日志保留个数为3。

配置日志相关参数的命令如下:

---

hcloud log set --key1=value1 --key2=value2 ...

hcloud log set --level=error --max-file-size=20 --max-file-num=3 --retention-period=30

	设置配置成功

---

查看日志相关参数的命令如下:

## hcloud log show

---

hcloud log show

\{

	"maxFileSize": 20,

	"maxFileNum": 3,

	"logLevel": "error",

	"logRetentionPeriod": 30

\}

---

### 3.8 模板管理

KooCLI提供由多条KooCLI命令组合而成的shell脚本模板，方便用户理清业务逻辑，完成复杂场景下的操作。用户可根据实际需要下载相应的模板，修改后执行即可。

可使用如下命令，进行模板的查看和下载操作。

查询已有模板列表:

## hcloud template list

---

hcloud template list

\{

	"count": 6,

	"templates": [

		\{

		"description": "基于华为云CLI，以shell脚本模板形式集成CLI调用命令，对弹性云服务器进行管理，覆盖从弹

性云服务器的创建(购买)到变更规格、再到删除的整个生命周期。",

			"detail_url": "https://codelabs.developer.huaweicloud.com/codelabs/samples/

a6ff22ee*********************18fb15",

			"id": "a6ff22ee******************18fb15",

			"title": "使用CLI便捷管理弹性云服务器ECS"

		\},

		...

		\{

		"description": "基于华为云CLI，以shell脚本模板形式集成CLI调用命令，对弹性负载均衡ELB进行管理和配

置。",

			"detail_url": "https://codelabs.developer.huaweicloud.com/codelabs/samples/

e2fb0a65*******************0a891b",

			"id": "e2fb0a65*****************0a891b",

			"title": "使用CLI便捷管理弹性负载均衡ELB"

	\}

1

\}

---

用户可根据查询结果中的模板的 “description” 了解模板的用途；单击其

“detail_url”链接，可跳转至Codelabs页面查看模板详情；“id”是模板的唯一标识，用户可根据id值下载对应的模板至本地。

☐说明

当前KooCLI模板示例持续开发中，敬请期待。

下载指定模板:

hcloud template download --template-id=\\(\{templateId\} --download-path=$ \{downloadPath\}

执行如上命令，可将指定模板下载至指定目录下。若未指定 “--download-path”，模板将被默认下载至当前目录下。下载的模板默认名称为其 “title” 值-时间戳.zip。解压后请根据需要修改和完善该模板的内容，执行即可。

### 3.9 管理 OBS 中的数据

在KooCLI中，已经集成了以命令行方式管理OBS数据的工具obsutil的功能。您可以通过使用"hcloud obs"命令，快速管理您在OBS中的数据。

## 功能概述

您可以使用KooCLI进行如下操作，管理您OBS中的数据:

表 3-1 KooCLI 集成 OBS 功能

<table><tr><td>功能</td><td>说明</td></tr><tr><td>桶基本操作</td><td>指定区域创建不同存储类型的桶、删除桶以及获取桶列表、桶配置信息等。</td></tr><tr><td>对象基本操作</td><td>管理对象，包括上传、下载、删除和列举对象等。 <br> - 支持上传单个或批量上传多个文件或文件夹。 <br> - 支持分段上传大文件。 <br> - 支持增量同步上传、下载和复制对象。 <br> - 支持复制单个对象或按对象名前缀批量复制多个对象。 <br> - 支持移动单个对象或按对象名前缀批量移动多个对象。 <br> - 支持对失败的上传、下载、复制等任务进行恢复。</td></tr><tr><td>日志记录</td><td>支持在客户端配置日志记录，记录对桶和对象的操作日志，方便统计与分析。</td></tr></table>

## 初始化配置

使用KooCLI管理OBS数据之前，您需要配置其与OBS的对接信息，包括OBS终端节点地址(Endpoint)和访问密钥(AK和SK)。获得OBS的认证后，才能使用KooCLI执行 OBS桶和对象的相关操作。

- 使用永久AK、SK进行初始化配置:

hcloud obs config -i=ak -k=sk -e=endpoint

- 使用临时AK、SK、SecurityToken进行初始化配置:

hcloud obs config -i=ak -k=sk -t=token -e=endpoint

## 检查连通性

配置完成后，您可以通过如下方式检查连通性，确认配置是否无误。

hcloud obs ls -s

根据命令回显结果，检查配置结果:

- 如果返回结果中包含 “Bucket number :”，表明配置正确。

- 如果返回结果中包含 “Http status [403]”，表明访问密钥配置有误，或没有获取桶列表的权限，需要视具体场景进一步确认根因。

- 如果返回结果中包含 “A connection attempt failed”, 表明无法连接OBS服务, 请检查网络环境是否正常。

## 命令结构

使用KooCLI管理OBS数据的命令结构如下:

hcloud obs command [parameters...] [options...]

在Windows系统中，支持进入交互命令模式:

步骤1 执行如下命令进入交互式:

hcloud obs

步骤2 按如下命令结构执行，以管理OBS数据:

command [parameters...] [options...]

如下所示:

---

hcloud obs

Enter "exit" or "quit" to logout

Enter "help" or "help command" to show help docs

Input your command:

	-->ls -limit=3 -s

	obs://bucket-001

	obs://bucket-002

		obs://bucket-003

	Bucket number: 3

---

---结束

☐说明

- command为执行的命令，例如ls, cp等。

- parameters为该命令的基本参数(必选)，例如创建桶时的桶名称。

- options为该命令的附加参数(通常为可选)，且附加参数在运行命令时必须以“-”开头。 参数支持两种传入方式“-key=value”和“-key value”，例如“-acl=private”和“-acl private”。两种参数传入方式无区别，您可以根据使用习惯选择任意一种方式。

- 方括号[]不是命令的一部分，在输入命令时，参数不能使用方括号[]括起来。

- 如命令中含有特殊字符，如&、<、>以及空格等，则需要加引号转义(macOS/Linux操作系统使用单引号，Windows操作系统使用双引号)。

☐ 说明

当在被委托的ECS服务器中使用KooCLI执行OBS的操作命令时，可在命令后添加参数“- authSource=ecsAgency”，会根据ECS委托自动获取临时认证信息用于OBS命令的鉴权。

您可以通过下表了解KooCLI支持的所有OBS操作命令，各命令的参数与obsutil一致， 参数详情可参考OBS服务桶相关命令，对象相关命令，辅助命令相关章节。

表 3-2 KooCLI 支持的所有 OBS 操作命令

<table><tr><td>类别</td><td>命令</td><td>功能</td><td>功能说明</td><td>命令结构</td></tr><tr><td rowspan="6">桶相关命令</td><td>m b</td><td>创建桶</td><td>按照用户指定的桶名创建一个新桶。 新创建桶的桶名在 OBS中必须是唯一的。一个用户可以拥有的桶的数量不能超过100个。</td><td>hcloud obs mb obs://bucket [-fs] [-az=xxx] [-acl=xxx] [- sc=xxx] [-location=xxx] [-config=xxx] [-e=xxx] [-i=xxx] [- k=xxx] [-t=xxx]</td></tr><tr><td>ls</td><td>列举桶</td><td>获取桶列表，查询到的桶列表将以桶名字典序排列。</td><td>hcloud obs ls [-s] [-du] [-sc] [-j=1] [-limit=1] [- format=default] [-config=xxx] [-e=xxx] [-i=xxx] [-k=xxx] [-t=xxx]</td></tr><tr><td>st <br> at</td><td>查询桶属性</td><td>查询单个桶的基本属性，包括桶的默认存储类型、桶的区域、桶的版本号、桶是否支持文件接口、桶的可用区、桶中对象数量、桶的存储用量以及桶的配额。</td><td>hcloud obs stat obs://bucket [-acl] [-bf=xxx] [- config=xxx] [-e=xxx] [-i=xxx] [-t=xxx] [-t=xxx]</td></tr><tr><td>ch att ri</td><td>设置桶属性</td><td>设置桶的存储类型、访问策略等属性。</td><td>hcloud obs chattri obs://bucket [-sc=xxx] [-acl=xxx] [- aclXml=xxx] [-config=xxx] [-e=xxx] [-i=xxx] [-k=xxx] [- t=xxx]</td></tr><tr><td>rm</td><td>删除桶</td><td>删除桶，待删除的桶必须为空 ( 不包含对象、历史版本对象或分段上传碎片)。</td><td>hcloud obs rm obs://bucket [-f] [-config=xxx] [-e=xxx] [- i=xxx] [-k=xxx] [-t=xxx]</td></tr><tr><td>bu <br> y</td><td>设置桶策略</td><td>设置桶策略。</td><td>hcloud obs bucketpolicy obs://bucket -method=put - localfile=xxx [-config=xxx] [-e=xxx] [-i=xxx] [-k=xxx] [- t=xxx]</td></tr></table>

<table><tr><td>类别</td><td>命令</td><td>功能</td><td>功能说明</td><td>命令结构</td></tr><tr><td rowspan="2"></td><td rowspan="2"></td><td>获取桶策略</td><td>获取桶策略。</td><td>hcloud obs bucketpolicy obs://bucket -method=get [- localfile=xxx] [-config=xxx] [-e=xxx] [-i=xxx] [-k=xxx] [- t=xxx]</td></tr><tr><td>删除桶策略</td><td>删除桶策略。</td><td>hcloud obs bucketpolicy obs://bucket -method=delete [- config=xxx] [-e=xxx] [-i=xxx] [-k=xxx] [-t=xxx]</td></tr><tr><td rowspan="2">对象相关命令</td><td>m <br> kd <br> ir</td><td>创建文件夹</td><td>在指定桶内或本地文件系统中创建文件夹。</td><td>- 在指定桶内创建文件夹: <br> hcloud obs mkdir obs://bucket/folder[/subfolder1/ subfolder2] [-config=xxx] [-e=xxx] [-i=xxx] [-k=xxx] [-t=xxx] <br> - 在本地文件系统路径中创建文件夹: <br> hcloud obs mkdir folder_url [-config=xxx] [-e=xxx] [- i=xxx] [-k=xxx] [-t=xxx]</td></tr><tr><td>cp</td><td>上传对象</td><td>上传单个或多个本地文件或文件夹至 OBS指定路径。待上传的文件可以是任何类型:文本文件、图片、视频等等。</td><td>- 上传文件: <br> hcloud obs cp file_url obs://bucket[/key] [- arcDir=xxx] [-dryRun] [-link] [-u] [-vlength] [- vmd5] [-p=1] [-threshold=5248800] [-acl=xxx] [- sc=xxx] [-meta=aaa:bbb#ccc:ddd] [-ps=auto] [- o=xxx] [-cpd=xxx] [-fr] [-o=xxx] [-config=xxx] [- e=xxx] [-i=xxx] [-k=xxx] [-t=xxx] <br> - 上传文件夹: <br> hcloud obs cp folder_url obs://bucket[/key] -r [- arcDir=xxx] [-dryRun] [-link] [-f] [-flat] [-u] [- vlength] [-vmd5] [-j=1] [-p=1] [- threshold=52428800] [-acl=xxx] [-sc=xxx] [- meta=aaa:bbb#ccc:ddd] [-ps=auto] [-include=*.xxx] [-exclude=*.xxx] [-timeRange=time1-time2] [-mf] [- o=xxx] [-cpd=xxx] [-config=xxx] [-e=xxx] [-i=xxx] [- k=xxx] [-t=xxx] <br> - 多文件/文件夹上传: <br> hcloud obs cp file1_url, folder1_url|filelist_url obs:// bucket[/prefix] -msm=1 [-r] [-arcDir=xxx] [-dryRun] [-link] [-f] [-u] [-vlength] [-vmd5] [-flat] [-j=1] [- p=1] [-threshold=52428800] [-acl=xxx] [-sc=xxx] [- meta=aaa:bbb#ccc:ddd] [-ps=auto] [-include=*.xxx [-exclude=*.xxx][-timeRange=time1-time2] [-at] [- mf] [-o=xxx] [-cpd=xxx] [-config=xxx] [-e=xxx] [- i=xxx] [-k=xxx] [-t=xxx]</td></tr></table>

<table><tr><td>类别</td><td>命令</td><td>功能</td><td>功能说明</td><td>命令结构</td></tr><tr><td rowspan="4"></td><td rowspan="4"></td><td>复制对象</td><td>复制对象或按对象名前缀批量复制对象。</td><td>- 复制单个对象: <br> hcloud obs cp obs://srcbucket/key obs://dstbucket/ [dest] [-dryRun][-u] [-crr] [-vlength] [-vmd5] [- p=1] [-threshold=52428800] [-versionId=xxx] [- acl=xxx] [-sc=xxx] [-meta=aaa:bbb#ccc:ddd] [- ps=auto] [-cpd=xxx] [-fr] [-o=xxx] [-config=xxx] [- e=xxx] [-i=xxx] [-k=xxx] [-t=xxx] <br> - 批量复制对象: <br> hcloud obs cp obs://srcbucket[/key] obs:// dstbucket[/dest] -r [-dryRun][-f] [-flat] [-u] [-crr] [- vlength] [-vmd5] [-j=1] [-p=1] [- threshold=52428800] [-acl=xxx] [-sc=xxx] [- meta=aaa:bbb#ccc:ddd] [-ps=auto] [-include=*.xxx] [-exclude=*.xxx] [-timeRange=time1-time2] [-mf] [- o=xxx] [-cpd=xxx] [-config=xxx] [-e=xxx] [-i=xxx] [- k=xxx] [-t=xxx]</td></tr><tr><td>下载对象</td><td>下载对象或按对象名前缀批量下载对象到本地。</td><td>- 下载单个对象: <br> hcloud obs cp obs://bucket/key file_or_folder_url [- tempFileDir=xxx] [-dryRun] [-u] [-vlength] [-vmd5] [-p=1] [-threshold=52428800] [-versionId=xxx] [- ps=auto] [-cpd=xxx][-fr] [-o=xxx] [-config=xxx] [- e=xxx] [-i=xxx] [-k=xxx] [-t=xxx] <br> - 批量下载对象: <br> hcloud obs cp obs://bucket[/key] folder_url -r [- tempFileDir=xxx] [-dryRun] [-f] [-flat] [-u] [- vlength] [-vmd5] [-j=1] [-p=1] [- threshold=52428800] [-ps=auto] [-include=*.xxx] [- exclude=*.xxx] [-timeRange=time1-time2] [-mf] [- o=xxx] [-cpd=xxx] [-config=xxx] [-e=xxx] [-i=xxx] [- k=xxx] [-t=xxx]</td></tr><tr><td>恢复失败的上传任务</td><td>根据任务号 (TaskId)恢复失败的上传任务。</td><td>hcloud obs cp -recover=xxx [-arcDir=xxx] [-dryRun] [-f] [-u] [-vlength] [-vmd5] [-j=1] [-p=1] [- threshold=52428800] [-acl=xxx] [-sc=xxx] [- meta=aaa:bbb#ccc:ddd] [-ps=auto] [-include='.xxx] [- exclude=*.xxx] [-timeRange=time1-time2] [-mf] [- o=xxx] [-cpd=xxx] [-clear] [-config=xxx] [-e=xxx] [- i=xxx] [-k=xxx] [-t=xxx]</td></tr><tr><td>恢复失败的复制任务</td><td>根据任务号 <br> (TaskId)恢复失败的复制任务。</td><td>hcloud obs cp -recover=xxx [-dryRun] [-f] [-u] [-crr] [- vlength] [-vmd5] [-j=1] [-p=1] [-threshold=52428800] [ acl=xxx] [-sc=xxx] [-meta=aaa:bbb#ccc:ddd] [-ps=auto] [-include=*.xxx] [-exclude=*.xxx] [-timeRange=time1- time2] [-mf] [-o=xxx] [-cpd=xxx] [-clear] [-config=xxx] [-e=xxx] [-i=xxx] [-k=xxx] [-t=xxx]</td></tr></table>

<table><tr><td>类别</td><td>命令</td><td>功能</td><td>功能说明</td><td>命令结构</td></tr><tr><td rowspan="5"></td><td></td><td>恢复失败的下载任务</td><td>根据任务号 (TaskId)恢复失败的下载任务。</td><td>hcloud obs cp -recover=xxx [-dryRun] [- tempFileDir=xxx] [-f] [-u] [-vlength] [-vmd5] [-j=1] [- p=1] [-threshold=52428800] [-ps=auto] [-include=*.xxx] [-exclude=*.xxx] [-timeRange=time1-time2] [-mf] [- o=xxx] [-cpd=xxx] [-clear] [-config=xxx] [-e=xxx] [- i=xxx] [-k=xxx] [-t=xxx]</td></tr><tr><td>st <br> at</td><td>查询对象属性</td><td>查询对象的基本属性。</td><td>hcloud obs stat obs://bucket/key [-acl][-bf=xxx] [- config=xxx] [-e=xxx] [-i=xxx] [-k=xxx] [-t=xxx]</td></tr><tr><td>ch att ri</td><td>设置对象属性</td><td>设置对象的属性或按对象名前缀批量设置对象的属性。</td><td>- 设置单个对象属性: <br> hcloud obs chattri obs://bucket/key [-sc=xxx] [- acl=xxx] [-aclXml=xxx] [-versionId=xxx] [-fr] [- o=xxx] [-config=xxx] [-e=xxx] [-i=xxx] [-k=xxx] [- t=xxx] <br> - 批量设置对象属性: <br> hcloud obs chattri obs://bucket[/key] -r [-f] [-v] [- sc=xxx] [-acl=xxx] [-aclXml=xxx] [-o=xxx] [-j=1] [- config=xxx] [-e=xxx] [-i=xxx] [-k=xxx] [-t=xxx]</td></tr><tr><td rowspan="2">ls</td><td>列举对象</td><td>查询桶内对象或多版本对象，返回对象列表将按照对象名和版本号以字典序排列。</td><td>hcloud obs ls obs://bucket[/prefix] [-s] [-d] [-v] [-du] [- marker=xxx] [-versionIdMarker=xxx] [-bf=xxx] [- limit=1] [-format=default] [-config=xxx] [-e=xxx] [- i=xxx] [-k=xxx] [-t=xxx]</td></tr><tr><td>列举分段上传 任务</td><td>查询桶内分段上传任务。</td><td>hcloud obs ls obs://bucket[/prefix] [-s] [-d] -m [-a] [- uploadIdMarker=xxx] [-marker=xxx] [-limit=1] [- format=default] [-config=xxx] [-e=xxx] [-i=xxx] [-k=xxx] [-t=xxx]</td></tr></table>

<table><tr><td>类别</td><td>命令</td><td>功能</td><td>功能说明</td><td>命令结构</td></tr><tr><td rowspan="3"></td><td>m <br> V</td><td>移动对象</td><td>移动对象或按对象名前缀批量移动对象。</td><td>- 移动单个对象: <br> hcloud obs mv obs://srcbucket/key obs://dstbucket/ [dest] [-dryRun] [-u] [-p=1] [-threshold=52428800] [-versionId=xxx] [-acl=xxx] [-sc=xxx] [- meta=aaa:bbb#ccc:ddd] [-ps=auto] [-cpd=xxx] [-fr] [-o=xxx] [-config=xxx] [-e=xxx] [-i=xxx] [-k=xxx] [- t=xxx] <br> - 批量移动对象: <br> hcloud obs mv obs://srcbucket[/key] obs:// dstbucket[/dest] -r [-dryRun] [-f] [-flat] [-u] [-j=1] [-p=1] [-threshold=52428800] [-acl=xxx] [-sc=xxx] [- meta=aaa:bbb#ccc:ddd] [-ps=auto] [-include=*.xxx] [-exclude=*.xxx] [-timeRange=time1-time2] [-mf] [- o=xxx] [-cpd=xxx] [-config=xxx] [-e=xxx] [-i=xxx] [- k=xxx] [-t=xxx]</td></tr><tr><td>sig n</td><td>生成对象的下载链接</td><td>生成指定桶内对象的下载链接，或按对象名前缀批量生成桶内对象的下载链接。</td><td>- 生成单个对象的下载链接: <br> hcloud obs sign obs://bucket/key [-e=300] [- config=xxx] [-endpoint=xxx] [-i=xxx] [-k=xxx] [- t=xxx] <br> - 按对象名前缀批量生成对象的下载链接: <br> hcloud obs sign obs://bucket[/key] -r [-e=300] [- timeRange=time1-time2] [-include=*.xxx] [- exclude=*.xxx] [-o=xxx] [-config=xxx] [- endpoint=xxx] [-i=xxx] [-k=xxx] [-t=xxx]</td></tr><tr><td>rm</td><td>删除对象</td><td>- 删除指定的对象。 <br> - 按指定的对象名前缀批量删除对象。</td><td>- 删除单个对象: <br> hcloud obs rm obs://bucket/key [-f] [- versionId=xxx] [-fr] [-o=xxx] [-config=xxx] [-e=xxx] [-i=xxx] [-k=xxx] [-t=xxx] <br> - 批量删除对象: <br> hcloud obs rm obs://bucket/[key] -r [-j=1] [-f] [-v] [-o=xxx] [-config=xxx] [-e=xxx] [-i=xxx] [-k=xxx] [- t=xxx]</td></tr></table>

<table><tr><td>类别</td><td>命令</td><td>功能</td><td>功能说明</td><td>命令结构</td></tr><tr><td rowspan="2"></td><td rowspan="2">sy <br> nc</td><td>增量同步上传对象</td><td>将本地源路径下的所有内容同步到 OBS指定目标桶， 使两边内容保持一致。这里的增量同步有两层含义: <br> 1. 增量，依次比较源文件和目标对象，只上传存在变化的源文件； <br> 2. 同步，命令执行完成后，保证本地源路径是OBS 指定目标桶的子集，即本地源路径下的所有文件均能在OBS指定目标桶中找到对应对象。</td><td>- 同步上传文件: <br> hcloud obs sync file_url obs://bucket[/key] [- arcDir=xxx] [-dryRun] [-link] [-vlength] [-vmd5] [- p=1] [-threshold=5248800] [-acl=xxx] [-sc=xxx] [- meta=aaa:bbb#ccc:ddd] [-ps=auto] [-o=xxx] [- cpd=xxx] [-fr] [-config=xxx] [-e=xxx] [-i=xxx] [- k=xxx] [-t=xxx] <br> - 同步上传文件夹: <br> hcloud obs sync folder_url obs://bucket[/key] [- arcDir=xxx] [-dryRun] [-link] [-vlength] [-vmd5] [- j=1] [-p=1] [-threshold=52428800] [-acl=xxx] [- sc=xxx] [-meta=aaa:bbb#ccc:ddd] [-ps=auto] [- include=*.xxx] [-exclude=*.xxx] [-timeRange=time1- time2] [-at] [-mf] [-o=xxx] [-cpd=xxx] [- config=xxx] [-e=xxx] [-i=xxx] [-k=xxx] [-t=xxx]</td></tr><tr><td>增量同步复制对象</td><td>将源桶指定路径下的所有对象同步到目标桶指定路径， 使两边内容保持一致。这里的增量同步有两层含义: <br> 1. 增量，依次比较源对象和目标对象，只复制存在变化的源对象； <br> 2. 同步，命令执行完成后，保证源桶指定路径是目标桶指定路径的子集，即源桶指定路径下的所有对象均能在目标桶中找到对应对象。</td><td>hcloud obs sync obs://srcbucket[/key] obs://dstbucket[/ dest] [-dryRun] [-crr] [-vlength] [-vmd5] [-j=1] [-p=1] [-threshold=52428800] [-acl=xxx] [-sc=xxx] [- meta=aaa:bbb#ccc:ddd] [-ps=auto] [-include=*.xxx] [- exclude=*.xxx] [-timeRange=time1-time2] [-mf] [- o=xxx] [-cpd=xxx] [-config=xxx] [-e=xxx] [-i=xxx] [- k=xxx] [-t=xxx]</td></tr></table>

<table><tr><td>类别</td><td>命令</td><td>功能</td><td>功能说明</td><td>命令结构</td></tr><tr><td rowspan="3"></td><td></td><td>增量同步下载对象</td><td>将OBS源桶指定路径下的所有对象同步到本地目标路径，使两边内容保持一致。这里的增量同步有两层含义: <br> 1. 增量，依次比较源对象和目标文件，只下载存在变化的源对象； <br> 2. 同步，命令执行完成后，保证 OBS指定源桶指定路径是本地目标路径的子集， 即OBS源桶指定路径下的所有对象均能在本地目标路径下找到对应文件。</td><td>hcloud obs sync obs://bucket[/key] folder_url [- tempFileDir=xxx] [-dryRun] [-vlength] [-vmd5] [-j=1] [- p=1] [-threshold=52428800] [-ps=auto] [-include=*.xxx] [-exclude=*.xxx] [-timeRange=time1-time2] [-mf] [- o=xxx] [-cpd=xxx] [-config=xxx] [-e=xxx] [-i=xxx] [- k=xxx] [-t=xxx]</td></tr><tr><td>re <br> st <br> or <br> e</td><td>恢复归档存储对象</td><td>恢复指定的存储类型为cold的对象或按指定的对象名前缀批量恢复存储类型为cold的对象。</td><td>- 恢复对象: <br> hcloud obs restore obs://bucket/key [-d=1] [-t=xxx] [-versionId=xxx] [-fr] [-o=xxx] [-config=xxx] [- e=xxx] [-i=xxx] [-k=xxx] [-token=xxx] <br> - 批量恢复对象: <br> hcloud obs restore obs://bucket[/key] -r [-f] [-v] [- d=1] [-t=xxx] [-o=xxx] [-j=1] [-config=xxx] [-e=xxx] [-i=xxx] [-k=xxx] [-token=xxx] <br> - 批量恢复指定目录下的所有对象: <br> hcloud obs restore obs://bucket/folder/ -r [-f] [-v] [- d=1] [-t=xxx] [-o=xxx] [-j=1] [-config=xxx] [-e=xxx] [-i=xxx] [-k=xxx] [-token=xxx]</td></tr><tr><td>ab <br> or <br> t</td><td>删除分段上传任务</td><td>- 通过分段上传任务的ID，删除指定桶中的分段上传任务。 <br> - 按指定的对象名前缀批量删除分段上传任务。</td><td>- 删除单个分段上传任务: <br> hcloud obs abort obs://bucket/key -u=xxx [-f] [-fr] [- o=xxx] [-config=xxx] [-e=xxx] [-i=xxx] [-k=xxx] [- t=xxx] <br> - 批量删除分段上传任务: <br> hcloud obs abort obs://bucket[/key] -r [-f] [-o=xxx] [-j=1] [-config=xxx] [-e=xxx] [-i=xxx] [-k=xxx] [- t=xxx]</td></tr></table>

<table><tr><td>类别</td><td>命令</td><td>功能</td><td>功能说明</td><td>命令结构</td></tr><tr><td rowspan="3"></td><td>cr <br> ea <br> te- <br> sh <br> ar <br> e</td><td>创建目录分享的授权码</td><td>指定桶名、对象名前缀和提取码，创建目录分享的授权码。</td><td>hcloud obs create-share obs://bucket[/prefix] [-ac=xxx] [-vp=xxx] [-dst=xxx] [-config=xxx] [-e=xxx] [-i=xxx] [- k=xxx] [-t=xxx]</td></tr><tr><td>sh <br> ar <br> e- <br> ls</td><td>授权码列举对象</td><td>使用授权码查询桶内对象，返回对象列表将按照对象名以字典序排列。</td><td>- 直接输入授权码: <br> hcloud obs share-ls authorization_code [-ac=xxx] [- prefix=xxx] [-s] [-d] [-marker=xxx] [-bf=xxx] [- limit=1] [-format=default] [-config=xxx] [-e=xxx] [- i=xxx] [-k=xxx] [-t=xxx] <br> - 使用文件路径传入授权码: <br> hcloud obs share-ls file://authorization_code_file_url [-ac=xxx] [-prefix=xxx] [-s] [-d] [-marker=xxx] [- bf=xxx] [-limit=1] [-format=default] [-config=xxx] [- e=xxx] [-i=xxx] [-k=xxx] [-t=xxx]</td></tr><tr><td>sh <br> ar <br> cp</td><td>授权码下载对象</td><td>使用授权码下载对象或按对象名前缀批量下载对象到本地。</td><td>- 直接输入授权码下载单个对象: <br> hcloud obs share-cp authorization_code file_or_folder_url -key=xxx [-ac=xxx] [-dryRun] [- tempFileDir=xxx] [-u] [-vlength] [-vmd5] [-p=1] [- threshold=52428800] [-ps=auto] [-cpd=xxx][-fr] [- o=xxx] [-config=xxx] [-e=xxx] [-i=xxx] [-k=xxx] [- t=xxx] <br> - 使用文件路径传入授权码下载单个对象: <br> hcloud obs share-cp file:// authorization_code_file_url file_or_folder_url - key=xxx [-ac=xxx] [-dryRun] [-tempFileDir=xxx] [-u] [-vlength] [-vmd5] [-p=1] [-threshold=52428800] [- ps=auto] [-cpd=xxx][-fr] [-o=xxx] [-config=xxx] [- e=xxx] [-i=xxx] [-k=xxx] [-t=xxx] <br> - 直接输入授权码批量下载对象: <br> hcloud obs share-cp authorization_code folder_url -r [-key=xxx] [-ac=xxx] [-dryRun] [-tempFileDir=xxx] [- f] [-u] [-vlength] [-vmd5] [-flat] [-j=1] [-p=1] [- threshold=52428800] [-ps=auto] [-include=*.xxx] [- exclude=*.xxx] [-timeRange=time1-time2] [-mf] [- o=xxx] [-cpd=xxx] [-config=xxx] [-e=xxx] [-i=xxx] [- k=xxx] [-t=xxx] <br> - 使用文件路径传入授权码批量下载对象: <br> hcloud obs share-cp file:// authorization_code_file_url folder_url -r [-key=xxx] [-ac=xxx] [-dryRun] [-tempFileDir=xxx] [-f] [-u] [- vlength] [-vmd5] [-flat] [-j=1] [-p=1] [- threshold=52428800] [-ps=auto] [-include=*.xxx] [- exclude=*.xxx] [-timeRange=time1-time2] [-mf] [- o=xxx] [-cpd=xxx] [-config=xxx] [-e=xxx] [-i=xxx] [- k=xxx] [-t=xxx]</td></tr></table>

<table><tr><td>类别</td><td>命令</td><td>功能</td><td>功能说明</td><td>命令结构</td></tr><tr><td rowspan="6">辅助命令</td><td>CO <br> nfi <br> g</td><td>更新配置文件</td><td>更新配置文件 (.obsutilconfig) 中的部分配置信息，可更新的配置包括:endpoint、 ak、sk、token。 <br> 关于配置文件 (.obsutilconfig) 中参数的详细说明，请参见配置参数说明。</td><td>- 交互模式更新配置 <br> hcloud obs config [-interactive] [-crr] [-config=xxx] <br> - 直接更新配置: <br> hcloud obs config [-e=xxx] [-i=xxx] [-k=xxx] [- t=xxx] [-crr] [-config=xxx]</td></tr><tr><td>cle ar</td><td>删除断点记录文件</td><td>删除指定文件夹下的断点记录文件。</td><td>hcloud obs clear [checkpoint_dir] [-u] [-d] [-c] [- config=xxx] [-e=xxx] [-i=xxx] [-k=xxx] [-t=xxx]</td></tr><tr><td>help</td><td>查看命令帮助</td><td>查看工具支持的 OBS命令，或查看某个具体命令的帮助文档。</td><td>hcloud obs help [command]</td></tr><tr><td>ve <br> rsi <br> on</td><td>查看版本号</td><td>查看所集成的 obsutil的版本号。</td><td>hcloud obs version</td></tr><tr><td>ar <br> ch <br> ive</td><td>归档日志文件</td><td>将日志文件归档到本地，或归档到指定的桶。</td><td>- 归档到本地 <br> hcloud obs archive [file_or_folder_url] [-config=xxx] [-e=xxx] [-i=xxx] [-k=xxx] [-t=xxx] <br> - 归档到指定桶: <br> hcloud obs archive obs://bucket[/key] [-config=xxx] [-e=xxx] [-i=xxx] [-k=xxx] [-t=xxx]</td></tr><tr><td>ls</td><td>列举失败结果清单文件</td><td>按最后修改时间列举指定文件夹中cp 命令及sync命令生成的失败结果清单文件。</td><td>hcloud obs ls -failed [-limit=1000] [-o=xxx]</td></tr></table>

### 4.1 选项概述

KooCLI选项是指可以直接在调用API的命令中添加的系统参数，KooCLI支持的选项及其功能如下表所示。其中除“help”，“debug”，“dryrun”，“cli-output”， “cli-query”，“cli-output-num”，“cli-jsonInput”，“cli-endpoint”之外，其余选项支持被设置到配置项中。执行命令时，命令中的参数值优先于配置项中该参数值。

表 4-1 KooCLI 选项列表

<table><tr><td>命令选项</td><td>说明</td><td>使用示例</td></tr><tr><td>help 选项</td><td>打印帮助信息</td><td>hcloud RDS ListCollations --cli-region="cn-north-4" -- help</td></tr><tr><td>debug 选项</td><td>打印命令调用过程中的调试信息。如API调用过程中的执行步骤，完整的请求 URL等。</td><td>hcloud VPC ShowVpc/v3 --cli-region="cn-north-4" -- project_id="0dd8cb*************19b5a84546" -- vpc id="0bbe***-****-****-*****235be6e7" --debua</td></tr><tr><td>dryrun 选项</td><td>检查命令正确性。执行校验后打印请求报文，跳过实际运行，不调用目标 API。</td><td>hcloud RDS CreateConfiguration --cli-region="cn-north-4" -- <br> project_id="4ff018c*******************df31948" -- datastore.type="MySQL" --datastore.version="5.7" -- values.max_connections="10" --name="test-001" -- description="test create configuration" --dryrun</td></tr><tr><td>skeleton 选项</td><td>生成JSON格式API入参骨架，便于使用--cli-jsonInput的方式传入API 参数</td><td>hcloud RDS CreateConfiguration --cli-region="cn-north-4" --skeleton</td></tr><tr><td>cli-region 选项</td><td>区域，表示在指定的区域中管理云服务资源。</td><td>hcloud EVS DeleteVolume --cli-region="cn-north-4" -- volume id="aed9****-****-****-*****0e3219cf" -- project_id="0dd8cb*************19b5a84546"</td></tr></table>

<table><tr><td>命令选项</td><td>说明</td><td>使用示例</td></tr><tr><td>cli-access-key, cli-secret-key, cli-security-token 选项</td><td>- cli-access-key: 访问密钥ID(Access Key ID，简称AK)，此参数必须和SK同时使用。 <br> - cli-secret-key: 秘密访问密钥(Secret Access Key，简称SK)，此参数必须和AK同时使用。 <br> - cli-security-token:临时安全凭证。在使用临时AK/SK认证身份时， 需同时使用此参数。 <br> 可用于以无配置方式AKSK 调用云服务API。</td><td>以无配置方式AKSK调用云服务API: <br> - 使用访问密钥(永久AK/SK): <br> hcloud RDS ListApiVersion --cli-region="cn-north-4" --cli-access-key=******* --cli-secret-key=******* <br> - 使用临时安全凭证(临时AK/SK和 SecurityToken): <br> hcloud RDS ListApiVersion --cli-region="cn-north-4" --cli-access-key=******** --cli-secret-key=******** --cli-security-token=*********</td></tr><tr><td>cli-agency-domain-id/cli-agency-domain-name, cli-agency-name, cli-source-profile 选项</td><td>- cli-agency-domain-name:委托方的账号名称，必须和cli-agency-name同时使用; <br> cli-agency-domain-id:委托方的账号ID， 必须和cli-agency-name同时使用； <br> - cli-agency-name: 委托名称，必须和cli-agency-domain-id或 cli-agency-domain-name同时使用； <br> - cli-source-profile: 保存被委托方认证信息的配置项。取值不能是当前配置项。</td><td>hcloud VPC ListAddressGroup/v3 --cli-region="cn-north-4" -- <br> project id="2cc60************xxeafa5019ef" --cli-agency-domain-id=13534326*******************5cf67b -- cli-agency-name=****** --cli-source-profile=test</td></tr><tr><td>cli-domain-id 选项</td><td>IAM用户所属账号ID。以 AKSK认证模式调用全局服务的API时需要。一般情况下，调用全局服务的API 时，KooCLI会根据用户的认证信息自动获取此参数的值。</td><td>hcloud CDN ListDomains --cli-region="cn-north-1" -- cli-domain-id="08e09a6e***************16b800"</td></tr><tr><td>cli-profile 选项</td><td>KooCLI配置项名称，配置项用于存储一组调用云服务API时所需的公共信息， 例如AK/SK，区域，项目 ID等。</td><td>hcloud EVS ListSnapshots --cli-profile=test</td></tr></table>

<table><tr><td>命令选项</td><td>说明</td><td>使用示例</td></tr><tr><td>cli-mode 选项</td><td>指定配置项的认证模式， 取值为: <br> - AKSK <br> - ecsAgency <br> - SSO <br> - AssumeRole</td><td>- 指定cli-mode为AKSK模式: <br> hcloud CCE ListNodes --cluster_id="f288****-****- ****_******_*****_ac101534" -- <br> project_id="0dd8cb**************19b5a84546" -- cli-profile=test --cli-mode=AKSK <br> - 指定cli-mode为ecsAgency模式: <br> hcloud CCE ListNodes --cluster_id="f288****-****- ****_****_****ac101534" -- <br> project_id="0dd8cb**************19b5a84546" -- cli-profile=test --cli-mode=ecsAgency</td></tr><tr><td>cli-output, cli-query, cli-output-num 选项</td><td>用于指定结果的输出格式。 <br> - cli-output 响应数据的输出格式， 取值可以为如下其一: <br> - json <br> - table <br> - tsv <br> - cli-query 筛选响应数据的 JMESPath路径 <br> - cli-output-num table输出时，是否打印行号。取值为:true 或者false</td><td>- 当cli-output的取值为json时: <br> - 调用云服务API: <br> hcloud CCE ListClusters --cli-region="cn-north-4" --type="VirtualMachine" -- project_id="0dd8cb***************19b5a --cli-query="items[0]" <br> - 调用CLI系统命令: <br> hcloud configure list --cli-output=json --cli-query="profiles[] <br> \{Name:name, Mode:mode, Ak:accessKeyId, SK:s ecretAccessKey\}" <br> - 当cli-output的取值为table时: <br> hcloud configure list --cli-output=table --cli-query="profiles[]. <br> \{Name:name, Mode:mode, Ak:accessKeyId, SK:secret AccessKey\}" <br> - 当cli-output的取值为tsv时: <br> hcloud configure list --cli-output=tsv --cli-query="profiles[]. <br> \{Name:name, Mode:mode, Ak:accessKeyId, SK:secret AccessKey\}"</td></tr><tr><td>cli-jsonInpu t 选项</td><td>指定JSON文件的方式传递 API参数。当云服务API的参数过多时，可将参数定义在一个JSON文件中， KooCLI会解析该文件中的参数内容。</td><td>hcloud ECS CreateServers --cli-region="cn-north-4" -- cli-read-timeout=60 --cli-jsonInput=C:\\cli \\Ecs_CreateServers.json</td></tr><tr><td>cli-connect-timeout , cli-read-timeout 选项</td><td>请求超时时间。 <br> - cli-connect-timeout: 请求连接超时时间 (秒)。默认值5秒，参数最小取值为1秒； <br> - cli-read-timeout: I/O 超时时间(秒)。默认值 10秒，参数最小取值为 1秒；</td><td>hcloud ECS DeleteServerPassword --cli-region="cn-north-4" -- <br> project_id="2cc60f5*************efa5019ef" -- server id="e6b99563-****-****-1820d4fd2a67" -- cli-connect-timeout=10 --cli-read-timeout=15</td></tr><tr><td>cli-retry-count 选项</td><td>请求连接重试次数。即: 若请求连接超时，会自动重试。默认取值为0次， 取值范围为0~5次。</td><td>hcloud RDS ListInstances --cli-region="cn-north-4" -- Content-Type="application/json" -- <br> project_id="2cc60***************caefa5019ef" --cli-retry-count=3</td></tr></table>

<table><tr><td>命令选项</td><td>说明</td><td>使用示例</td></tr><tr><td>cli-skip-secure-verify 选项</td><td>跳过https请求证书验证 (不建议)。取值为true或 false，默认为false。因跳过证书验证时存在安全风险，故当其取值为true 时，KooCLI会向用户交互确认。</td><td>hcloud ECS NovaListServers --cli-region="cn-north-4" --project_id="2cc6*************6caefa5019ef" --cli-skip-secure-verify=true</td></tr><tr><td>cli-endpoint 选项</td><td>自定义请求域名。 <br> 默认会请求对应区域的目标云服务，您也可以针对该云服务指定Endpoint。</td><td>hcloud IoTDA UpdateDevice --cli-region="cn-north-4" --description="test update device" -- device id="testz*******************0802" --cli-endpoint="iot-mqtts.cn-north-4.myhuaweicloud.com"</td></tr><tr><td>cli-waiter 选项</td><td>结果轮询，参数应为JSON 格式且使用双引号包裹。</td><td>hcloud ECS NovaShowServer --cli-region="cn-north-4" --server_id="e6b99563-xxxx-xxxx-xxxx-1820d4fd2a6" --cli-waiter="\{\\"expr \\":\\"server.status\\",\\"to\\":\\"ACTIVE\\",\\"timeout\\":300\}"</td></tr><tr><td>cli-auth-type 选项</td><td>指定AKSK的签名方式，仅在需指定特殊签名算法时使用。</td><td>hcloud IoTDA UpdateDevice --cli-region="cn-north-4" --description="test update device" -- device_id="testz******************6020" --cli-endpoint="iot-mqtts.cn-north-4.myhuaweicloud.com" --cli-auth-type=derivedSign</td></tr><tr><td>cli-x-project-id选项</td><td>项目ID,用于认证鉴权</td><td>hcloud VPC ListAddressGroup/v3 --cli-region="cn-north-4" --cli-x-project-id="2cc60******************caefa5019ef"</td></tr></table>

### 4.2 打印帮助信息

KooCLI支持查看命令的帮助信息。

例如查看“RDS”服务operation为“ListCollations”的API的帮助信息:

hcloud RDS ListCollations --cli-region="cn-north-4" --help

### 4.3 打印命令调用过程中的调试信息

KooCLI支持打印命令执行过程中的调试信息。

在命令中添加 “--debug” 即可:

---

hcloud VPC ShowVpc/v3 --cli-region="cn-north-4" --project_id="0dd8cb*

vpc_id="0bbe*********_***-*****235be6e7" --debug

[debug info] 2022/06/21 19:59:25 Read and connection timeouts are 40s and 30s respectively.

	[debug info] 2022/06/21 19:59:25 URL: https://vpc.cn-

	north-4.myhuaweicloud.com/v3/0dd8cb*************19b5a84546/vpc/vpcs/0bbe***-*******23

	[debug info] 2022/06/21 19:59:26 API response status code is 200.

		[debug info] 2022/06/21 19:59:26 API response X-Request-Id is f9fd68***************2e48ec7f88.

\{

														"vpc": \{

																											"id": "0bbe******......***_******235be6e7",

																											"name": "CCI-VPC-******",

																											"description": "",

																											"cidr": "192.****.*/**",

																											"extend_cidrs": [],

		"status": "ACTIVE",

		"project_id": "0dd8cb************12/9b5a84546",

		"enterprise_project_id": "0",

		"tags": [],

		"created_at": "2022-05-10T02:53:42Z",

		"updated_at": "2022-05-10T02:53:43Z",

		"cloud_resources": [

		\{

			"resource_type": "routetable",

			"resource_count": 1

		\},

			\{

				"resource_type": "virsubnet",

			"resource_count": 1

		\}

		]

	\},

	"request_id": "f9fd68***************2e48ec7f88"

\}

---

### 4.4 生成 JSON 格式 API 入参骨架

skeleton选项用于生成JSON格式API入参骨架。在命令中添加“--skeleton”选项，则在当前目录生成该API的JSON格式的入参文件，用户可填写文件中的参数值，以“-- cli-jsonInput=\$\{JSON文件名\}”传入参数，调用API:

hcloud RDS CreateConfiguration --cli-region="cn-north-4" --skeleton 已生成JSON格式API入参骨架,文件存放位置:C:\\cli\\RDS_CreateConfiguration_cn-20231108093800.json

该JSON文件的内容如下:

---

\{

	"header": \{

		"X-Language": ""

	\},

	"path": \{

			"project_id": ""

	\},

	"body": \{

		"datastore": \{

				"type": "",

				"version": ""

		\},

		"description": "",

		"name": "",

		"values": \{

		\}

	\}

\}

													骨架填写完成后，请删除此行及下列参数描述信息:

\{

	"header": \{

		"X-Language": \{

				"Required": false,

				"ParamType": "string",

				"Usage": "语言",

				"EnumValue": [

					"zh-cn",

					"en-us"

			]

	\},

	"path": \{

		"project_id": \{

				"Required": true,

				"ParamType": "string",

			"Usage": "项目ID。"

	\}

\},

"body": \{

	"datastore": \{

			"type": \{

				"Required": true,

				"ParamType": "string",

				"Usage": "数据库引擎,不区分大小写:\\n- MySQL\\n- PostgreSQL\\n- SQLServer\\n- MariaDB",

				"EnumValue": [

					"MySQL",

					"PostgreSQL",

					"SQLServer",

					"MariaDB"

				]

			\},

			"version": \{

				"Required": true,

				"ParamType": "string",

---

"Usage": "数据库版本。\\n\\n- MySQL引擎支持5.6、5.7版本。取值示例:5.7。具有相应权限的用户才可使用8.0,您可联系华为云客服人员申请。\\n- PostgreSQL引擎支持9.5、9.6、10、11版本。取值示例:9.6。\\n-Microsoft SQL Server:仅支持2017 企业版、2017 标准版、2017 web版、2014 标准版、2014 企业版、2016 标准版、2016 企业版、2012 企业版、2012 标准版、2012 web版、2008 R2 企业版、2008 R2 web版、2014 web 版、2016 web版。取值示例2014_SE。例如:2017标准版可填写2017_SE,2017企业版可填写2017_EE,2017web版可以填写2017_WEB"

---

			\}

		\},

			"description": \{

				"Required": false,

				"ParamType": "string",

				"Usage": "参数模板描述。最长256个字符，不支持>!<\\"&'=特殊字符。默认为空。"

		\},

			"name": \{

				"Required": true,

				"ParamType": "string",

				"Usage": "参数模板名称。最长64个字符,只允许大写字母、小写字母、数字、和 "-_." 特殊字符。"

		\},

			"values": \{

				"": \{

					"Required": false,

					"ParamType": "string",

					"Usage": "参数值对象,用户基于默认参数模板自定义的参数值。为空时不修改参数值。\\n\\n- key:参数

名称，\\"max_connections\\":\\"10\\"。为空时不修改参数值，key不为空时value也不可为空。\\n- value:参数

值,\\"max_connections\\":\\"10\\"。"

				\}

		\}

	\}

\}

---

## 须知

- 生成的JSON文件分为上下两部分，上半部分为cli-jsonInput需要的API参数骨架， 下半部分为各参数的描述信息及其取值规范。中间以分割线分隔。用户可参考参数的描述信息，在上半部分的骨架中填写参数值。

- JSON文件填写完成后，需删除分割线及下半部分的内容。对于未填写取值的参数， 使用时也需要删除该参数。

以上述文件为例，参数填写完成后，JSON文件的内容为:

---

\{

	"path": \{

		"project_id": "0dd8cb***************19b5a84546"

	\},

	"body": \{

		"datastore": \{

---

---

		"type": "MySQL",

		"version": "5.7"

	\},

	"description": "test create configuration",

	"name": "test-001",

	"values": \{

		"max_connections": "10"

	\}

\}

---

\}

将该文件传入命令中，以--cli-jsonInput方式调用API:

---

hcloud RDS CreateConfiguration --cli-region="cn-north-4" --cli-

jsonInput="RDS_CreateConfiguration_cn-20231108093800.json" --dryrun

cli-jsonInput中各位置(如path、query、body、formData、header、cookie)传入的API参数优先于命令传入

	dry-run模式跳过实际运行，当前请求为:

POST https://rds.cn-north-4.myhuaweicloud.com/v3/0dd8cb*

Content-Type: application/json

X-Project-Id: 0dd8cb***************19b5a84546

X-Sdk-Date: 20220621T103331Z

Authorization: ****

\{

"datastore": \{

"type": "MySQL",

"version": "5.7"

\},

"description": "test create configuration",

"name": "test-001",

"values": \{

"max_connections": "10"

\}

\}

---

### 4.5 检查命令正确性

dryrun选项用于检查所传入命令的正确性。

在命令中添加 “--dryrun” 选项，执行校验后打印请求报文，跳过实际运行，不调用目标API:

---

hcloud RDS CreateConfiguration --cli-region="cn-north-4" --project_id="0dd8cb*************19b5a84546"

datastore.type="MySQL" --datastore.version="5.7" --values.max_connections="10" --name="test-001" --

description="test create configuration" --dryrun

	dry-run模式跳过实际运行，当前请求为:

POST https://rds.cn-north-4.myhuaweicloud.com/v3/0dd8cb******************19b5a84546/configurations

Content-Type: application/json

X-Project-Id: 0dd8cb***************19b5a84546

X-Sdk-Date: 20220621T103331Z

Authorization: ****

\{

"datastore": \{

"type": "MySQL",

"version": "5.7"

\},

"description": "test create configuration",

"name": "test-001",

"values": \{

"max_connections": "10"

\}

\}

---

### 4.6 指定区域

KooCLI除了可以从配置项读取区域信息外，还可以在命令中传入cli-region值，如下:

---

hcloud EVS DeleteVolume --cli-region="cn-north-4" --volume_id="aed9

project_id="0dd8cb***************19b5a84546"

\{

	"job_id": "70a5******....*****....*****441e862b"

\}

---

说明

---

不同区域，项目也不同，因此指定区域时，一般需要同时指定项目ID。

---

### 4.7 以无配置方式 AKSK 调用云服务 API

KooCLI支持在命令中添加 “--cli-access-key”，“--cli-secret-key” 和 “--cli-security-token” 选项，以无配置方式AKSK调用云服务API。

当命令中仅使用 “--cli-access-key” 和 “--cli-secret-key” 时，默认识别该AK，SK为永久AK/SK:

---

hcloud RDS ListApiVersion --cli-region="cn-north-4" --cli-access-key=******* --cli-secret-key=******

\{

	"versions": [

		\{

			"id": "v3",

			"links": [],

			"status": "CURRENT",

			"updated": "2019-01-15T12:00:00Z"

		\},

			"id": "v1",

			"links": [],

			"status": "DEPRECATED",

			"updated": "2017-02-07T17:34:02Z"

	\}

]

\}

---

当命令中同时使用 “ --cli-access-key ”， “ --cli-secret-key” 和 “ --cli-security-token”时，默认识别该AK，SK为临时AK/SK:

---

hcloud RDS ListApiVersion --cli-region="cn-north-4" --cli-access-key=****** --cli-secret-key=******** --cli-

security-token=******

\{

	"versions": [

		\{

			"id": "v3",

			"links": [],

			"status": "CURRENT",

			"updated": "2019-01-15T12:00:00Z"

		\},

			"id": "v1",

			"links": [],

			"status": "DEPRECATED",

			"updated": "2017-02-07T17:34:02Z"

		\}

	]

\}

---

### 4.8 以无配置方式 AssumeRole 调用云服务 API

当委托方用户创建委托，将资源交由其他账号管理后，被委托方可以在命令中添加“-- cli-agency-domain-id" / "--cli-agency-domain-name", "--cli-agency-name" 和 "--cli-source-profile" 选项，使用以无配置方式AssumeRole调用云服务API，管理和使用委托方的资源:

---

hcloud VPC ListAddressGroup/v3 --cli-region="cn-north-4" --project_id="2cc60

cli-agency-domain-id=13534326*************5cf67b --cli-agency-name=****** --cli-source-profile=test

\{

	"request_id": "29ec21***************6d6b4cdd82",

	"address_groups": [],

	"page_info": \{

	"current_count": 0

	\}

\}

---

☐ 说明

上述参数中，“--cli-agency-domain-id” / “--cli-agency-domain-name”与 “--cli-agency-name”必须同时使用；“--cli-source-profile”是保存被委托方认证信息的配置项，其取值不能是当前配置项。

### 4.9 指定用户所属账号 ID

KooCLI以AKSK模式调用全局服务的API时，需添加账号ID(即cli-domain-id)。

KooCLI会在调用全局服务的API的过程中，根据用户认证信息自动获取账号ID，用户也可在命令中添加 “--cli-domain-id” 选项，如下:

---

	hcloud CDN ListDomains --cli-region="cn-north-1" --cli-domain-id="08e09a6e

																	"total": 0,

														"domains": null

\}

---

### 4.10 指定配置项

KooCLI支持多配置项，用户可将常用的AK/SK，区域等信息保存到配置项中。

使用时通过 “--cli-profile” 指定目标配置项的名称即可，如下:

---

hcloud EVS ListSnapshots --cli-profile=test

---

### 4.11 指定配置项的认证模式

KooCLI的配置项的认证模式取值为AKSK、ecsAgency、SSO、AssumeRole，推荐使用 AKSK。当使用的配置项同时配置了多种认证模式相关的参数，用户可使用 “ --cli-mode” 选项来指定配置项的认证模式:

---

hcloud CCE ListNodes --cluster_id="f288****.*****.******a<101534" --

	project_id="0dd8cb***************19b5a84546" --cli-profile=test --cli-mode=AKSK

---

☐说明

设置配置项时，需要以“--cli-profile”指定配置项的名称，同时还需根据认证模式“--cli-mode”添加相应的认证参数:

- 若配置项的认证模式为 “AKSK”，则配置时命令中“--cli-access-key”和 “--cli-secret-key”的值不能为空；

- 若配置项的认证模式为 “ecsAgency”，则配置时命令中需指定 “--cli-mode=ecsAgency";

- 若配置项的认证模式为 “SSO”，则配置时命令中 “ --cli-sso-start-url” 和 “--cli-sso-region” 的值不能为空；

- 若配置项的认证模式为 “AssumeRole”，则配置时命令中 “--cli-agency-domain-id” / “-- cli-agency-domain-name”，“--cli-agency-name”，“--cli-source-profile”的值不能为空。

### 4.12 指定结果的输出格式

命令中使用“--cli-query”传入JMESPath表达式，对结果执行JMESPath查询，方便提炼原返回结果中的关键信息；“ --cli-output”指定响应数据的输出格式；“ --cli-output-num”指定当使用table格式输出时，是否打印行号。

## 输出顺序

使用“--cli-query”指定的JMESPath表达式不同，输出的结果中各参数的排列顺序可能不同。部分表达式的输出结果不会带有输出数据的属性名(即参数的key值)，故用户需对输出数据的顺序有所把握，以便于数据处理。不同类型的JMESPath表达式，输出结果的顺序如下表所示:

表 4-2 不同 JMESPath 表达式的数据输出顺序

<table><tr><td>JMESPath表达式类型</td><td>JMESPath表达式示例</td><td>json/ table格式输出时， 是否带有属性名 (即参数的key 值)</td><td>tsv格式输出时，是否带有属性名 (即参数的key 值)</td><td>输出数据的顺序</td><td>示例</td></tr><tr><td>表达式指定至对象层级</td><td>--cli-query="items[0 ]"</td><td>是</td><td>否</td><td>以该对象各属性名的字典顺序，输出其对应的值</td><td>示例 1</td></tr><tr><td>表达式指定至对象的属性层级， 且未对属性名重命名</td><td>--cli-query="items[0 ].items[0]. [spec.flavor, me tadata.uid]"</td><td>否</td><td>否</td><td>以JMESPath表达式中指定各属性名的顺序，输出其对应的值</td><td>示例 2</td></tr></table>

<table><tr><td>JMESPath表达式类型</td><td>JMESPath表达式示例</td><td>json/ table格式输出时， 是否带有属性名 (即参数的key 值)</td><td>tsv格式输出时，是否带有属性名 (即参数的key 值)</td><td>输出数据的顺序</td><td>示例</td></tr><tr><td>表达式指定至对象的属性层级 <br> ，且对属性名进行了重命名</td><td>--cli-query="items[0 ]. <br> \{Flavor:spec.fla vor, ClusterID:m etadata.uid\}"</td><td>是</td><td>否</td><td>以其重命名后的各属性名的字典顺序，输出其对应的值</td><td>示例 3</td></tr></table>

以json输出格式为例，示范不同JMESPath表达式的数据输出顺序:

- 示例1:

指定至对象层级，KooCLI会以该对象各属性名的字典顺序，输出其对应的值。在此示例中指定至对象"items[0]"，该对象中各属性按字典顺序排序后为:

---

apiVersion, kind, metadata, spec, status。因此输出结果如下:

hcloud CCE ListClusters --cli-region="cn-north-4" --type="VirtualMachine" --

project_id="0dd8cb***************19b5a84546" --cli-query="items[0]"

		\{

																"apiVersion": "v3",

																"kind": "Cluster",

																"metadata": \{

																														"creationTimestamp": "2022-05-13 08:51:58.252509 +0000 UTC",

																														"labels": \{

																																												"FeatureGates": "elbv3,"

																											\},

																														"name": "github-**********",

																														"uid": "f288****-****-****-****ac101534",

																														"updateTimestamp": "2022-05-13 09:10:06.395875 +0000 UTC"

													\},

																	"spec": \{

																															"authentication": \{

																																										"authenticatingProxy": \{\},

																																										"mode": "rbac"

																										\},

																														"az": "multi_az",

																														"billingMode": 0,

																														"category": "CCE",

																														"containerNetwork": \{

																																										"cidr": "10.*.*/**",

																																										"mode": "vpc-router"

																											\},

																														"eniNetwork": \{\},

																														"extendParam": \{

																																											"alpha.cce/fixPoolMask": "25",

																																											"kubernetes.io/cpuManagerPolicy": "",

																																										"upgradefrom": ""

																									\},

																													"flavor": "cce.s2.small",

																														"hostNetwork": \{

																																												"SecurityGroup": "653e****_****_******_

																																												"subnet": "d5df**********.***-*****4955c724",

																																												"vpc": "c865******....******-******efe7e8d8"

																											\},

																													"kubeProxyMode": "iptables",

---

---

		"kubernetesSvcIpRange": "10.****.*/**",

		"masters": [

		\{

			"availabilityZone": "cn-north-4b"

		\},

		\{

			"availabilityZone": "cn-north-4a"

		\}

		],

		"supportlstio": true,

		"type": "VirtualMachine",

		"version": "v1.19.10-r0"

	\},

	"status": \{

		"endpoints": [

		\{

			"type": "Internal",

			"url": "https://192.****.***:5443"

		\},

		\{

			"type": "External",

			"url": "https://121.**…***5443"

		\}

		],

		"phase": "Available"

\}

\}

---

- 示例2:

指定至对象的属性层级，且未对属性名重命名，KooCLI会以指定各属性名的顺序，输出其对应的值。在此示例中指定至对象"items[0]"的两个对象属性的子属性，表达式"items[0].[spec.flavor, metadata.uid]"中先指定了其spec对象属性的 flavor属性，再指定了其metadata对象属性的uid属性，因此输出结果中，先输出 spec.flavor的值，再输出metadata.uid的值，结果如下:

---

hcloud CCE ListClusters --cli-region="cn-north-4" --type="VirtualMachine" --

project_id="0dd8cb*************19b5a84546" --cli-query="items[0].[spec.flavor, metadata.uid]"

		[

														"cce.s2.small",

													"f288****_*****_*****_****_

---

- 示例3:

指定至对象的属性层级，且对属性名进行了重命名，KooCLI会以重命名后的各属性名的字典顺序，输出其对应的值。在此示例中指定至对象"items[0]"的两个对象属性的子属性，表达式"items[0].\{Flavor:spec.flavor, ClusterID:metadata.uid\}" 中，将spec对象属性的flavor属性重命名为Flavor，将metadata对象属性的uid属性重命名为ClusterID。按字典顺序排序其重命名后的属性为:ClusterID， Flavor。因此输出结果如下:

---

	hcloud CCE ListClusters --cli-region="cn-north-4" --type="VirtualMachine" --

	project_id="0dd8cb***************19b5a84546" --cli-query="items[0].

		\{Flavor:spec.flavor, ClusterID:metadata.uid\}"

	\{

															"ClusterID": "f288****-****-****-****- <oco10534",

																"Flavor": "cce.s2.small"

\}

---

## 输出格式

---

使用“--cli-output”指定输出格式，“--cli-output”的取值可以为json，table，tsv

其中之一。

- 当 “--cli-output” 的取值为json时:

	将以json格式输出结果，如下:

hcloud configure list --cli-output=json --cli-query="profiles[].

\{Name:name, Mode:mode, Ak:accessKeyld, SK:secretAccessKey\}"

[

\{

	"Ak": "8NV******lOV",

	"Mode": "AKSK",

	"Name": "test",

	"SK": "*****

\},

	"Ak": "H9N****MXW",

	"Mode": "AKSK",

	"Name": "default",

	"SK": "*****"

\}

]

---

- 当 “--cli-output” 的取值为table时:

将以table格式输出结果，如下:

![019db8ba-f9dc-74e1-ad16-95f757e5f1e5_49_447_774_1037_264_0.jpg](images/019db8ba-f9dc-74e1-ad16-95f757e5f1e5_49_447_774_1037_264_0.jpg)

当指定 “--cli-output” 的取值为table，可以同时使用 “--cli-output-num” 指定是否打印行号:

![019db8ba-f9dc-74e1-ad16-95f757e5f1e5_49_446_1149_1036_253_0.jpg](images/019db8ba-f9dc-74e1-ad16-95f757e5f1e5_49_446_1149_1036_253_0.jpg)

- 当 “--cli-output” 的取值为tsv时:

将以tsv格式输出结果，如下:

![019db8ba-f9dc-74e1-ad16-95f757e5f1e5_49_444_1520_1040_152_0.jpg](images/019db8ba-f9dc-74e1-ad16-95f757e5f1e5_49_444_1520_1040_152_0.jpg)

tsv输出格式返回制表符和换行分隔的数据值，不包含额外的符号，方便将输出结果用于其他命令。因tsv的输出结果中不包含数据表头，故用户在使用时需把握不同类型的JMESPath表达式输出数据的顺序，防止数据用于其他命令时出现混乱， 详情请参考不同类型JMESPath表达式的数据输出顺序。

使用tsv格式输出，若jMESPath表达式中指定了多个属性名，且未对属性名重命名，则当其中某个或多个属性名被单独用 “ [ ] ” 括起来时，该属性将在输出时被换行至新的一行输出，如下:

---

![019db8ba-f9dc-74e1-ad16-95f757e5f1e5_49_447_1960_1037_138_0.jpg](images/019db8ba-f9dc-74e1-ad16-95f757e5f1e5_49_447_1960_1037_138_0.jpg)

---

---

	在上图的示例中，指定输出属性为:name，mode，accessKeyld，

	secretAccessKey。且其中的name被指定以新的一行输出。按照属性被指定时的

	顺序，第一行输出的分别为mode，accessKeyId，secretAccessKey的值，第二行

输出的是name值。

---

☐口说明

---

	可点此了解关于 “--cli-query”，“--cli-output”，“--cli-output-num” 使用时的其他注意事

项。

---

### 4.13 以 JSON 文件的方式传递 API 参数

KooCLI调用云服务的API时，如果API的参数过多，不便直接在命令中传入，用户可通过 “--cli-jsonInput” 将云服务API的部分或全部参数以JSON文件的形式输入。剩余的其他参数，例如KooCLI系统参数、未通过JSON文件传入的云服务API参数等，仍可在命令中传入，例如:

---

hcloud ECS CreateServers --cli-region="cn-north-4" --cli-read-timeout=60 --cli-jsonInput=C:\\cli

\\Ecs_CreateServers.json

\{

	"job_id": "ff808082********************ae0646",

	"serverIds": [

		"dd86******-****_****-****91527651"

	]

\}

---

通过 “--cli-jsonInput” 选项传入API参数时，首先需要编写一个JSON文件，在该文件中，各API参数需要根据其在request中的位置信息被放在对应的Key下。

构造JSON文件的方法如下:

## 使用--skeleton 参数生成

使用“--skeleton”生成并填写JSON格式API入参骨架文件，并将该文件以“--cli-jsonInput=\$\{JSON文件名\}”传入。

## 根据 API Explorer 页面生成

在API Explorer页面获取API参数，并写入JSON文件:

步骤1 在原命令末尾加 “--help”，从结果中的“Params”中查看目标API各参数的位置信息。

步骤2 创建JSON文件，建议其名称为 “\\(\{服务名\}_$\{API名\}.json”，其原始内容如下:

---

\{

	"header": \{\},

	"path": \{\},

	"query": \{\},

	"formData": \{\},

	"cookie": \{\}

	"body": \{\}

\}

---

步骤3 根据原始JSON文件中的Key的顺序填充其对应位置的参数:

---

- 对于非body位置的参数，请在原始JSON文件对应Key的大括号中，以"参数名称

	":"参数值"的格式成对填入各参数及其值，同一大括号中每对数据之间以","隔

	开，最后一对数据与 “ \} ” 之间不需要再加 ", "；

---

- 对于body位置的参数，在API Explorer页面填写其“Body”中各参数的值，填写完成后单击“切换为文本输入”，如下图所示，复制文本框中转为JSON格式的参数内容，将其粘贴在原始JSON文件的“body”Key之后，覆盖原“body”Key后对应的大括号;

图 4-1 获取用于 cli-jsonInput 文件的 body 位置参数

![019db8ba-f9dc-74e1-ad16-95f757e5f1e5_51_387_464_991_541_0.jpg](images/019db8ba-f9dc-74e1-ad16-95f757e5f1e5_51_387_464_991_541_0.jpg)

步骤4 各位置的参数填写完成后，若某个位置Key上没有参数，需在JSON文件中删除该位置的Key所在的行的内容。注意:需同时删除最外层“\}”与其前一个“\}”之间的“,”；

步骤5 在原KooCLI命令中用 "--cli-jsonInput=\$\{JSON文件所在路径\}" 代替原命令中传入的 API参数，重新调用。

如在上面的示例中， “--cli-jsonInput=C:\\cli\\Ecs_CreateServers.json” 传入的 Ecs_CreateServers.json文件的内容应为:

---

\{

	"path": \{

		"project_id": "0dd8cb41******************a84546"

	\},

	"body": \{

		"server": \{

				"adminPass": "wh***********",

				"auto_terminate_time": "2022-01-19T03:30:52Z",

				"availability_zone": "cn-north-4a",

				"data_volumes": [

					\{

						"multiattach": true,

						"shareable": true,

						"size": 100,

						"volumetype": "SATA"

				\}

			],

				"flavorRef": "2d53****_****_******_

			"imageRef": "7059***-****-****-****-*****0b5e9e4c",

			"name": "ecs_server_01",

			"nics": [

					\{

						"ipv6_enable": true,

						"subnet_id": "4eb2****-****-*****-*****-*****+ff9a042d"

				\}

			],

			"publicip": \{

					"eip": \{

						"bandwidth": \{

							"sharetype": "PER",

							"size": 30

						\},

						"iptype": "5_sbgp"

				\}

			\},

			"root_volume": \{

				"volumetype": "SATA"

			\},

			"server_tags": [

					\{

						"key": "date",

						"value": "211102"

				\}

			],

				"vpcid": "5aa5****-****-****-*****1df05a3a"

		\}

\}

---

---结束

须知

使用“ --cli-jsonInput”选项时，请留意这些注意事项。

### 4.14 指定请求超时时间

cli-connect-timeout, cli-read-timeout 选项用于设置请求超时时间。其中请求连接超时时间 "--cli-connect-timeout" 默认值为5秒，I/O超时时间 "--cli-read-timeout" 默认值为10秒:

---

hcloud ECS DeleteServerPassword --cli-region="cn-north-4" --project_id="2cc60f5************efa5019ef" --

server_id="e6b99563-****-****-1820d4fd2a67" --cli-connect-timeout=10 --cli-read-timeout=15

---

命令中可同时使用 “--cli-connect-timeout” 和 “--cli-read-timeout” 选项，也可只使用其一。

### 4.15 指定请求连接重试次数

cli-retry-count选项用于指定请求连接重试次数。即:在请求超时(因网络连接问题导致请求失败)的情况下会自动重试。“--cli-retry-count”的默认取值为0次，参数取值范围为0~5次:

---

- 若因网络连接问题导致请求失败，KooCLI会提示如下信息:

	hcloud RDS ListInstances --cli-region="cn-north-4" --Content-Type="application/json" --

	project_id="2cc60************ecaefa5019ef" --cli-retry-count=3

	[NETWORK_ERROR]连接超时4次(重试3次)请检查网络连通性

---

- 若网络连接正常，则可成功返回:

---

		hcloud RDS ListInstances --cli-region="cn-north-4" --Content-Type="application/json" --

	project_id="2cc60************eafa5019ef" --cli-retry-count=3

	\{

														"instances": [],

															"total_count": 0

\}

---

A 注意

需要注意的是，因为使用“--cli-retry-count”设置重试次数可能会导致调用接口幂等性的问题，有重复调用的风险。对于创建类的接口，请您谨慎使用。

### 4.16 跳过 https 请求证书验证

cli-skip-secure-verify选项用于指定是否跳过https请求证书验证(不建议)。当用户已配置HTTP代理，KooCLI调用云服务的API时，可能会因证书校验失败，导致请求报错 x509。用户可在命令中添加 "--cli-skip-secure-verify=true" 后执行原命令，在执行时会向用户交互以确认是否跳过https请求证书验证:

hcloud ECS NovaListServers --cli-region="cn-north-4" --project_id="2cc6*************6caefa5019ef" --cli-skip-secure-verify=true

使用`--cli-skip-secure-verify=true`跳过https请求证书验证会导致您的隐私数据暴露在公网,有被外部窃取的风险, 请确认是否跳过(y/N): y

\{

"servers": []

\}

☐说明

需要注意的是，因为使用“--cli-skip-secure-verify=true”跳过https请求证书验证会导致您的隐私数据暴露在公网，有被外部窃取的风险，不建议您这样使用。推荐的做法是将您公司颁发的证书导入到操作系统的可信任CA证书下。

### 4.17 自定义请求域名

cli-endpoint用于自定义请求云服务的域名。

KooCLI默认会请求对应区域的目标云服务，您也可以针对该云服务指定Endpoint:

---

hcloud IoTDA UpdateDevice --cli-region="cn-north-4" --description="test update device" --

device_id="testz**********************06802" --cli-endpoint="iot-mqtts.cn-north-4.myhuaweicloud.com"

\{

	"app_id" : "103b************************2620",

	"app_name" : "DefaultApp_******************8020",

	"device_id" : "testz******************8020",

	"node_id" : "testz******************80802",

	"gateway_id" : "testz************************************8020",

	"device_name" : "test************************************0802",

	"node_type" : "CATEWAY",

	"description" : "test update device",

	"fw_version" : null,

	"sw_version" : null,

	"device_sdk_version" : null,

	"auth_info" : \{

		"auth_type" : "CERTIFICATES"

		"secret" : null,

		"fingerprint" : "e30db21************************bb1772929c",

		"secure_access" : true,

		"timeout" : 0

	\}

	"product_id" : "50c1*********************588e",

	"product_name" : "50c1*********************588e",

	"status" : "INACTIVE",

	"create time" : "20220801T085024z",

	"tags" : [],

	"extension_info" : \{

		"shal_fingerprint" : "82cd23e2

		"sha256_fingerprint" : "396ldb"

---

### 4.18 结果轮询

cli-waiter用于结果轮询，参数应为JSON格式且使用双引号包裹。您可以使用此参数进行结果轮询:

hcloud ECS NovaShowServer --cli-region="cn-north-4" --server_id="e6b99563-xxxx-xxxx-xxxx-1820d4fd2a6" --cli-query="server.status" --cli-waiter="\{\\"expr\\":\\"server.status\\",\\"to\\":\\"ACTIVE\\",\\"timeout\\":300\}" 结果轮询结束, server.status的值达到期待结果ACTIVE

ACTIVE

☐说明

cli-waiter的取值中，每个字段的含义如下:

- expr required string 使用JMESPath表达式指定被轮询字段

- to required string 被轮询字段的目标值

- timeout optional int 轮询的超时时间(秒), min=1, max=600,默认值180

- interval optional int 轮询的间隔时间(秒), min=2, max=10,默认值5

A 注意

需要注意的是，因为使用“--cli-waiter”可能会导致调用接口幂等性的问题，有重复调用的风险，请您谨慎使用。建议查询类接口使用此参数。

### 4.19 指定签名算法

cli-auth-type用于指定AKSK的签名方式，在需指定特殊签名算法时添加此参数。

目前参数支持的值为 "derivedSign"，在使用aksk方式调用iotda服务时使用。

---

hcloud IoTDA UpdateDevice --cli-region="cn-north-4" --description="test update device" --

device_id="testz******************0020" --cli-endpoint="iot-mqtts.cn-north-4.myhuaweicloud.com" --cli-auth-

type=derivedSign

\{

	"app_id" : "103b************************2620",

	"app_name" : "DefaultApp_***********",

	"device_id" : "testz******************8020",

	"node_id" : "testz************************8020",

	"gateway_id" : "testz******************************************0802",

	"device_name" : "test******************************************0802",

	"node_type" : "CATEWAY",

	"description" : "test update device",

	"fw_version" : null,

	"sw_version" : null,

	"device_sdk_version" : null,

	"auth_info" : \{

		"auth_type" : "CERTIFICATES"

		"secret" : null,

		"fingerprint" : "e30db21*************************b1772920c",

		"secure_access" : true,

		"timeout" : 0

	\}

	"product_id" : "50c1************************858e",

	"product_name" : "50c1*********************588e",

	"status" : "INACTIVE",

	"create time" : "20220801T085024z",

---

---

	"tags": [],

	"extension_info" : \{

		"shal_fingerprint": "82cd23e2

		"sha256_fingerprint" : "396ldb'

	\}

\}

---

### 4.20 指定项目 ID

cli-x-project-id用于指定项目ID，用于认证鉴权，在需指定请求头中项目ID时添加此参数。

hcloud VPC ListAddressGroup/v3 --cli-region="cn-north-4" --cli-x-project-id="2cc60

---

\{

	"request_id": "29ec21*************6d6b4cdd82",

	"address_groups": [],

	"page_info": \{

	"current_count": 0

	\}

\}

---

## 在 API Explorer 上获取 CLI 示例

API Explorer上开放的各云服务API，除了支持在线调试，还能生成KooCLI命令示例 (以下简称CLI示例)。您在API Explorer界面上填写API参数，在其对应的“CLI示例” 中可直接拷贝使用。

下图为API Explorer上CDN服务的创建加速域名API。在API Explorer页面填写完成各项请求参数后，CLI示例会及时刷新命令内容。您可以将填写好请求参数的CLI示例保存，后续在KooCLI中直接调用，或集成到脚本中调用。

图 5-1 在 API Explorer 上获取 CLI 示例

![019db8ba-f9dc-74e1-ad16-95f757e5f1e5_56_390_1104_1042_506_0.jpg](images/019db8ba-f9dc-74e1-ad16-95f757e5f1e5_56_390_1104_1042_506_0.jpg)

## ☐说明

- 在API Explorer界面上，已填写值的参数，才会体现在CLI示例中。

- CLI示例会携带项目ID，区域等信息，如果您在其他项目或区域中使用，请注意替换成对应的项目ID与区域。

### 6.1 无配置方式使用概述

KooCLI既可以使用配置项调用云服务API，也提供了无配置的操作方式，无配置方式使用是指在使用KooCLI时不通过已有配置项传入当前用户的认证信息，而是直接在命令中传入当前用户认证相关的参数。此方式可使用户免于添加配置项，方便快捷地使用 KooCLI。用户可以通过如下认证方式直接调用云服务API:

- 无配置方式AKSK

- 无配置方式ecsAgency

无配置方式使用KooCLI时，需留意这些注意事项，也需了解各认证方式的优先级。

### 6.2 无配置方式 AKSK

- 访问密钥 (永久AK/SK)

用户可以在命令中直接输入永久AK(cli-access-key)和SK(cli-secret-key)调用云服务API:

hcloud ECS NovaListServers --cli-region="cn-north-4" --project_id="4ff018c3' cli-access-key=******* --cli-secret-key=********

- 临时安全凭证(临时AK/SK和SecurityToken)

用户可以在命令中直接输入临时AK(cli-access-key)，SK(cli-secret-key)和 SecurityToken ( cli-security-token ) 调用云服务API:

hcloud ECS NovaListServers --cli-region="cn-north-4" --project_id="4ff018c3 cli-access-key=****** --cli-secret-key=******* --cli-security-token=********

### 6.3 无配置方式 ecsAgency

在用户已成功建立向弹性云服务器(ECS)的委托的前提下，在ECS服务器中使用 KooCLI时，可以在命令中指定“--cli-mode=ecsAgency”，KooCLI将基于ECS委托， 自动获取临时的AK/SK和SecurityToken用于认证。

此认证方式要求用户已经建立了ECS服务器委托。若该委托尚未建立，可以在IAM对该弹性云服务器进行云服务委托授权，详细操作请参考委托其他云服务管理资源。创建完成后，在相应的弹性云服务器的详情页面“管理信息 > 委托”栏目中添加委托。

### 7.1 获取永久 AK/SK

访问密钥(AK和SK)是IAM的一种认证机制，用于对请求加密签名，确保请求的机密性、完整性和请求双方身份的正确性:

- AK(Access Key ID):访问密钥ID，是与私有访问密钥关联的唯一标识符。访问密钥ID和私有访问密钥一起使用，对请求进行加密签名。

- SK(Secret Access Key):与访问密钥ID结合使用的密钥，对请求进行加密签名，可标识发送方，并防止请求被修改。

## 约束和限制

每个用户最多可以创建两个有效的访问密钥，其一旦生成永久有效。

## 查找已下载的访问密钥

若您已生成且下载过访问密钥(AK和SK)，可在本地查找已下载的AK/SK文件，文件名一般为:credentials.csv。

如下图所示，文件包含了用户名称(User Name)，AK(Access Key Id)，SK ( Secret Access Key ) 。

图 7-1 credential.csv 文件内容

<table><tr><td></td><td>A</td><td>B</td><td>C</td></tr><tr><td>1</td><td>User Name</td><td>ACCESS KEY I d</td><td>Secret Access Key</td></tr><tr><td>2</td><td></td><td>CLANDOUNDS</td><td>zr171</td></tr></table>

## 创建新的访问密钥

如您尚未生成过或未能找到本地的AK/SK文件，可创建新的访问密钥:

步骤1 登录控制台。

步骤2 在顶部导航栏单击用户名，并选择“我的凭证”。

步骤3 进入“我的凭证”页面，单击“管理访问密钥”页签下方的“新增访问密钥”。

步骤4 在弹出的 “新增访问密钥” 对话框中，输入登录密码和对应验证码。

☐说明

- 用户如果未绑定邮箱和手机，则只需输入登录密码。

- 用户如果同时绑定了邮箱和手机，可以选择其中一种方式进行验证。

步骤5 单击 “确定”。

步骤6 根据浏览器提示，保存密钥。密钥会直接保存到浏览器默认的下载文件夹中。

☐ 说明

- 为防止访问密钥泄露，建议您将其保存到安全的位置。如果用户在此提示框中单击“取消”，则不会下载密钥，后续也将无法重新下载。如果需要使用访问密钥，可以重新创建新的访问密钥。

- 访问密钥(AK和SK)需定期更新。

步骤7 打开下载下来的“credentials.csv”文件即可获取到访问密钥(AK和SK)。

----结束

### 7.2 获取账号 ID、项目 ID

在调用云服务API的时候，大多数场景需要填入项目ID。项目ID获取步骤如下:

步骤1 注册并登录管理控制台。

步骤2 单击右上角用户名，在下拉列表中单击“我的凭证”，查看“账号ID(cli-domain-id)”、“项目ID(cli-project-id)”，如下图。

项目用于对云服务器资源进行物理隔离，默认有区域级别的隔离，也可在区域下建立多项目，做更细级别的隔离。因此，请参考下图，在项目列表中找到您的服务器资源

对应的所属区域，在其左侧获取对应区域的项目ID，单击其左侧的 ⊞ 图标可获取对应区域下的子项目ID。

图 7-2 账号 ID、项目 ID

![019db8ba-f9dc-74e1-ad16-95f757e5f1e5_60_383_1596_1047_253_0.jpg](images/019db8ba-f9dc-74e1-ad16-95f757e5f1e5_60_383_1596_1047_253_0.jpg)

☐说明

KooCLI可在API调用过程中，根据当前用户认证信息自行获取请求头中需要的账号ID、项目ID， 因此命令中可不输入该参数。

----结束

### 7.3 获取区域

在调用云服务API的时候，需要指定区域。

请参见终端节点及区域说明。

☐ 说明

KooCLI在指定的区域中管理云服务资源。

### 7.4 获取临时 AK/SK 和 securitytoken

临时AK/SK和securitytoken是系统颁发给IAM用户的临时访问令牌，有效期可在15分钟至24小时范围内设置，过期后需要重新获取。

临时AK/SK和securitytoken遵循权限最小化原则。

请参见获取临时AK/SK和securitytoken。