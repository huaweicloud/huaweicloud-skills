# IAM Python 脚本使用指南

---

## v5 接口

### 用户管理

---

### list_users_v5.py — 查询 IAM 用户列表

作用：查询 IAM 用户列表 (v5)，包括 用户ID、用户名、是否启用、描述、创建时间。
用法详见：python scripts/iam/list_users_v5.py -h

---

### show_user_v5.py — 查询 IAM 用户详情

作用：查询 IAM 用户详情 (v5)。
用法详见：python scripts/iam/show_user_v5.py -h

---

### show_user_last_login_v5.py — 查询 IAM 用户最后登录时间

作用：查询 IAM 用户最后登录时间 (v5)。
用法详见：python scripts/iam/show_user_last_login_v5.py -h

---

### show_login_profile_v5.py — 查询 IAM 用户登录配置

作用：查询 IAM 用户登录配置 (v5)。
用法详见：python scripts/iam/show_login_profile_v5.py -h

---

### list_groups_v5.py — 查询 IAM 用户组列表

作用：查询 IAM 用户组列表 (v5)，包括 组ID、组名称、描述、创建时间。
用法详见：python scripts/iam/list_groups_v5.py -h

---

### show_group_v5.py — 查询 IAM 用户组详情

作用：查询 IAM 用户组详情 (v5)。
用法详见：python scripts/iam/show_group_v5.py -h

---

### show_group_summary.py — 查询 IAM 用户组摘要

作用：查询 IAM 用户组摘要 (v5)，包括 组ID、组名称、描述、user_count。
用法详见：python scripts/iam/show_group_summary.py -h

---

### list_policies_v5.py — 查询 IAM 策略列表

作用：查询 IAM 策略列表 (v5)，包括 策略ID、策略名称、策略类型、描述、创建时间。
用法详见：python scripts/iam/list_policies_v5.py -h

---

### list_policy_versions_v5.py — 查询 IAM 策略版本列表

作用：查询 IAM 策略版本列表 (v5)，包括 版本ID、是否默认、创建时间。
用法详见：python scripts/iam/list_policy_versions_v5.py -h

---

### list_attached_user_policies_v5.py — 查询 IAM 用户附加策略列表

作用：查询 IAM 用户附加策略列表 (v5)，包括 策略ID、策略名称、attached_at。
用法详见：python scripts/iam/list_attached_user_policies_v5.py -h

---

### list_attached_group_policies_v5.py — 查询 IAM 用户组附加策略列表

作用：查询 IAM 用户组附加策略列表 (v5)，包括 策略ID、策略名称、attached_at。
用法详见：python scripts/iam/list_attached_group_policies_v5.py -h

---

### list_attached_agency_policies_v5.py — 查询 IAM 委托附加策略列表

作用：查询 IAM 委托附加策略列表 (v5)，包括 策略ID、策略名称、attached_at。
用法详见：python scripts/iam/list_attached_agency_policies_v5.py -h

---

### list_entities_for_policy_v5.py — 查询 IAM 策略授权实体列表

作用：查询 IAM 策略授权实体列表 (v5)，包括 委托ID、attached_at。
用法详见：python scripts/iam/list_entities_for_policy_v5.py -h

---

### list_agencies_v5.py — 查询 IAM 委托列表

作用：查询 IAM 委托列表 (v5)，包括 委托ID、委托名称、trust_domain_id、trust_domain_name、描述、创建时间。
用法详见：python scripts/iam/list_agencies_v5.py -h

---

### list_access_keys_v5.py — 查询 IAM AK/SK 列表

作用：查询 IAM AK/SK 列表 (v5)，包括 用户ID、access_key_id、状态、创建时间。
用法详见：python scripts/iam/list_access_keys_v5.py -h

---

### show_access_key_last_used_v5.py — 查询 IAM AK/SK 最后使用时间

作用：查询 IAM AK/SK 最后使用时间 (v5)。
用法详见：python scripts/iam/show_access_key_last_used_v5.py -h

---

### list_mfa_devices_v5.py — 查询 IAM MFA 设备列表

作用：查询 IAM MFA 设备列表 (v5)，包括 用户ID、序列号、是否启用。
用法详见：python scripts/iam/list_mfa_devices_v5.py -h

---

### list_service_principals_v5.py — 查询 IAM 服务主体列表

作用：查询 IAM 服务主体列表 (v5)，包括 service_principal、display_name、描述。
用法详见：python scripts/iam/list_service_principals_v5.py -h

---

### list_registered_services_for_auth_schema_v5.py — 查询 IAM 认证模式注册服务列表

作用：查询 IAM 认证模式注册服务列表 (v5)，包括 service_code。
用法详见：python scripts/iam/list_registered_services_for_auth_schema_v5.py -h

---

### show_login_policy_v5.py — 查询 IAM 登录策略

作用：查询 IAM 登录策略 (v5)。
用法详见：python scripts/iam/show_login_policy_v5.py -h

---

### show_password_policy_v5.py — 查询 IAM 密码策略

作用：查询 IAM 密码策略 (v5)。
用法详见：python scripts/iam/show_password_policy_v5.py -h

---

### list_custom_policies.py — 查询 IAM 自定义策略列表

作用：查询 IAM 自定义策略列表 (v3)，包括 ID、名称、display_name、类型、服务目录、描述。
用法详见：python scripts/iam/list_custom_policies.py -h

---

### show_custom_policy.py — 查询 IAM 自定义策略详情

作用：查询 IAM 自定义策略详情 (v3)。
用法详见：python scripts/iam/show_custom_policy.py -h

---

### show_agency.py — 查询 IAM 委托详情

作用：查询 IAM 委托详情 (v3)。
用法详见：python scripts/iam/show_agency.py -h

---

### list_domain_permissions_for_agency.py — 查询 IAM 委托全局权限列表

作用：查询 IAM 委托全局权限列表 (v3)，包括 ID、名称、display_name、类型、服务目录、描述。
用法详见：python scripts/iam/list_domain_permissions_for_agency.py -h

---

### list_project_permissions_for_agency.py — 查询 IAM 委托项目权限列表

作用：查询 IAM 委托项目权限列表 (v3)，包括 ID、名称、display_name、类型、服务目录、描述。
用法详见：python scripts/iam/list_project_permissions_for_agency.py -h

---

### list_permanent_access_keys.py — 查询 IAM 永久 AK/SK 列表

作用：查询 IAM 永久 AK/SK 列表 (v3)，包括 用户ID、访问密钥、状态、创建时间、描述。
用法详见：python scripts/iam/list_permanent_access_keys.py -h

---

### show_permanent_access_key.py — 查询 IAM 永久 AK/SK 详情

作用：查询 IAM 永久 AK/SK 详情 (v3)。
用法详见：python scripts/iam/show_permanent_access_key.py -h

---

### show_user.py — 查询 IAM 用户详情

作用：查询 IAM 用户详情 (v3)。
用法详见：python scripts/iam/show_user.py -h

---

### list_user_login_protects.py — 查询 IAM 用户登录保护列表

作用：查询 IAM 用户登录保护列表 (v3)，包括 用户ID、是否启用、验证方式。
用法详见：python scripts/iam/list_user_login_protects.py -h

---

### list_user_mfa_devices.py — 查询 IAM 用户 MFA 设备列表

作用：查询 IAM 用户 MFA 设备列表 (v3)，包括 用户ID、序列号。
用法详见：python scripts/iam/list_user_mfa_devices.py -h

---

### list_enterprise_projects_for_user.py — 查询 IAM 用户企业项目列表

作用：查询 IAM 用户企业项目列表 (v3)，包括 项目ID。
用法详见：python scripts/iam/list_enterprise_projects_for_user.py -h

---

### list_enterprise_projects_for_group.py — 查询 IAM 用户组企业项目列表

作用：查询 IAM 用户组企业项目列表 (v3)，包括 项目ID。
用法详见：python scripts/iam/list_enterprise_projects_for_group.py -h

---

### show_domain_login_policy.py — 查询 IAM 域登录策略

作用：查询 IAM 域登录策略 (v3)。
用法详见：python scripts/iam/show_domain_login_policy.py -h

---

### show_domain_password_policy.py — 查询 IAM 域密码策略

作用：查询 IAM 域密码策略 (v3)。
用法详见：python scripts/iam/show_domain_password_policy.py -h

---

### show_domain_protect_policy.py — 查询 IAM 域保护策略

作用：查询 IAM 域保护策略 (v3)。
用法详见：python scripts/iam/show_domain_protect_policy.py -h

---

### show_domain_api_acl_policy.py — 查询 IAM 域 API ACL 策略

作用：查询 IAM 域 API ACL 策略 (v3)。
用法详见：python scripts/iam/show_domain_api_acl_policy.py -h

---

### show_domain_console_acl_policy.py — 查询 IAM 域控制台 ACL 策略

作用：查询 IAM 域控制台 ACL 策略 (v3)。
用法详见：python scripts/iam/show_domain_console_acl_policy.py -h

---

### show_domain_quota.py — 查询 IAM 域配额

作用：查询 IAM 域配额 (v3)，包括 类型、已使用、配额、单位。
用法详见：python scripts/iam/show_domain_quota.py -h

---

### show_project_quota.py — 查询 IAM 项目配额

作用：查询 IAM 项目配额 (v3)，包括 类型、已使用、配额、单位。
用法详见：python scripts/iam/show_project_quota.py -h

---

### show_project_details_and_status.py — 查询 IAM 项目详情和状态

作用：查询 IAM 项目详情和状态 (v3)。
用法详见：python scripts/iam/show_project_details_and_status.py -h

---

### show_open_id_connect_config.py — 查询 IAM OpenID Connect 配置

作用：查询 IAM OpenID Connect 配置 (v3)。
用法详见：python scripts/iam/show_open_id_connect_config.py -h

---

### get_account_summary_v5.py — 查询账号摘要

作用：查询账号摘要 (v5)，包括 users、groups、agencies、policies 等数量及配额。
用法详见：python scripts/iam/get_account_summary_v5.py -h

---

### get_agency_v5.py — 查询委托详情

作用：查询委托详情 (v5)，包括 agency_id、agency_name、description、trust_domain_id、trust_domain_name、created_at、max_session_duration、urn、path、tags。
用法详见：python scripts/iam/get_agency_v5.py -h

---

### get_policy_v5.py — 查询策略详情

作用：查询策略详情 (v5)，包括 policy_id、policy_name、policy_type、urn、path、description、default_version_id、attachment_count、created_at、updated_at。
用法详见：python scripts/iam/get_policy_v5.py -h

---

### get_policy_version_v5.py — 查询策略版本详情

作用：查询策略版本详情 (v5)，包括 version_id、is_default、created_at、document。
用法详见：python scripts/iam/get_policy_version_v5.py -h

---

### get_asymmetric_signature_switch_v5.py — 查询非对称签名开关

作用：查询非对称签名开关 (v5)，包括 domain_id、asymmetric_signature_switch。
用法详见：python scripts/iam/get_asymmetric_signature_switch_v5.py -h

---

### get_authorization_schema_v5.py — 查询授权方案

作用：查询授权方案 (v5)，包括 version、actions、resources、conditions、operations。
用法详见：python scripts/iam/get_authorization_schema_v5.py -h

---

### get_feature_status_v5.py — 查询特性状态

作用：查询特性状态 (v5)。
用法详见：python scripts/iam/get_feature_status_v5.py -h

---

### get_service_linked_agency_deletion_status_v5.py — 查询服务关联委托删除状态

作用：查询服务关联委托删除状态 (v5)，包括 status、reason、agency_usage_list。
用法详见：python scripts/iam/get_service_linked_agency_deletion_status_v5.py -h

---

### list_resource_tags_v5.py — 查询资源标签

作用：查询资源标签 (v5)，包括 tag_key、tag_value。
用法详见：python scripts/iam/list_resource_tags_v5.py -h

---

### get_project_id.py — 获取指定区域的项目 ID

作用：获取指定区域的项目 ID。
用法详见：python scripts/iam/get_project_id.py -h

---

### list_agencies.py — 查询委托列表

作用：查询委托列表 (v3)，包括 id、name、domain_id、trust_domain_id、trust_domain_name、description、duration、expire_time、agency_urn、created_at。
用法详见：python scripts/iam/list_agencies.py -h

---

### list_all_projects_permissions_for_agency.py — 查询委托所有项目权限

作用：查询委托所有项目权限 (v3)，包括 id、name。
用法详见：python scripts/iam/list_all_projects_permissions_for_agency.py -h

---

### check_all_projects_permission_for_agency.py — 检查委托是否拥有所有项目权限

作用：检查委托是否拥有所有项目权限 (v3)。
用法详见：python scripts/iam/check_all_projects_permission_for_agency.py -h

---

### check_domain_permission_for_agency.py — 检查委托是否拥有域权限

作用：检查委托是否拥有域权限 (v3)。
用法详见：python scripts/iam/check_domain_permission_for_agency.py -h

---

### check_project_permission_for_agency.py — 检查委托是否拥有项目权限

作用：检查委托是否拥有项目权限 (v3)。
用法详见：python scripts/iam/check_project_permission_for_agency.py -h

---

### list_groups_for_enterprise_project.py — 查询企业项目下用户组列表

作用：查询企业项目下用户组列表 (v3)，包括 id、name、domain_id、description、created_at。
用法详见：python scripts/iam/list_groups_for_enterprise_project.py -h

---

### list_users_for_enterprise_project.py — 查询企业项目下用户列表

作用：查询企业项目下用户列表 (v3)，包括 id、name、domain_id、enabled、description、policy_num。
用法详见：python scripts/iam/list_users_for_enterprise_project.py -h

---

### list_roles_for_group_on_enterprise_project.py — 查询用户组在企业项目上的角色

作用：查询用户组在企业项目上的角色 (v3)，包括 id、name、display_name、type、catalog、description、flag。
用法详见：python scripts/iam/list_roles_for_group_on_enterprise_project.py -h

---

### list_roles_for_user_on_enterprise_project.py — 查询用户在企业项目上的角色

作用：查询用户在企业项目上的角色 (v3)，包括 id、name、display_name、type、catalog、description、flag。
用法详见：python scripts/iam/list_roles_for_user_on_enterprise_project.py -h

---

### show_domain_role_assignments.py — 查询域角色分配

作用：查询域角色分配 (v3)，包括 id、name。
用法详见：python scripts/iam/show_domain_role_assignments.py -h

---

### show_metadata.py — 查询身份提供商元数据

作用：查询身份提供商元数据 (v3)，包括 id、idp_id、protocol_id、domain_id、entity_id、xaccount_type、update_time、data。
用法详见：python scripts/iam/show_metadata.py -h

---

## Keystone 接口

---

### keystone_list_auth_domains.py — 查询用户可访问域列表

作用：查询用户可访问域列表 (v3)，包括 id、name、enabled、description。
用法详见：python scripts/iam/keystone_list_auth_domains.py -h

---

### keystone_list_auth_projects.py — 查询用户可访问项目列表

作用：查询用户可访问项目列表 (v3)，包括 id、name、enabled、description、domain_id、parent_id。
用法详见：python scripts/iam/keystone_list_auth_projects.py -h

---

### keystone_list_endpoints.py — 查询终端节点列表

作用：查询终端节点列表 (v3)，包括 id、interface、region_id、service_id、url、region、enabled。
用法详见：python scripts/iam/keystone_list_endpoints.py -h

---

### keystone_list_federation_domains.py — 查询联邦认证域列表

作用：查询联邦认证域列表 (v3)，包括 id、name、enabled、description。
用法详见：python scripts/iam/keystone_list_federation_domains.py -h

---

### keystone_list_federation_projects.py — 查询联邦认证项目列表

作用：查询联邦认证项目列表 (v3)，包括 id、name、enabled、description、domain_id、parent_id。
用法详见：python scripts/iam/keystone_list_federation_projects.py -h

---

### keystone_list_groups.py — 查询用户组列表

作用：查询用户组列表 (v3)，包括 id、name、domain_id、description、create_time。
用法详见：python scripts/iam/keystone_list_groups.py -h

---

### keystone_list_groups_for_user.py — 查询用户所属用户组

作用：查询用户所属用户组 (v3)，包括 id、name、domain_id、description、create_time。
用法详见：python scripts/iam/keystone_list_groups_for_user.py -h

---

### keystone_list_identity_providers.py — 查询身份提供商列表

作用：查询身份提供商列表 (v3)，包括 id、enabled、description、sso_type、remote_ids。
用法详见：python scripts/iam/keystone_list_identity_providers.py -h

---

### keystone_list_mappings.py — 查询映射列表

作用：查询映射列表 (v3)，包括 id、rules。
用法详见：python scripts/iam/keystone_list_mappings.py -h

---

### keystone_list_permissions.py — 查询权限列表

作用：查询权限列表 (v3)，包括 id、name、display_name、type、catalog。
用法详见：python scripts/iam/keystone_list_permissions.py -h

---

### keystone_list_projects.py — 查询项目列表

作用：查询项目列表 (v3)，包括 id、name、domain_id、enabled、description。
用法详见：python scripts/iam/keystone_list_projects.py -h

---

### keystone_list_projects_for_user.py — 查询用户可访问项目

作用：查询用户可访问项目 (v3)，包括 id、name、domain_id、enabled、description、parent_id。
用法详见：python scripts/iam/keystone_list_projects_for_user.py -h

---

### keystone_list_protocols.py — 查询协议列表

作用：查询协议列表 (v3)，包括 id、mapping_id。
用法详见：python scripts/iam/keystone_list_protocols.py -h

---

### keystone_list_regions.py — 查询区域列表

作用：查询区域列表 (v3)，包括 id、description、parent_region_id、type。
用法详见：python scripts/iam/keystone_list_regions.py -h

---

### keystone_list_services.py — 查询服务列表

作用：查询服务列表 (v3)，包括 id、name、type、enabled、description。
用法详见：python scripts/iam/keystone_list_services.py -h

---

### keystone_list_users.py — 查询用户列表

作用：查询用户列表 (v3)，包括 id、name、domain_id、enabled、description。
用法详见：python scripts/iam/keystone_list_users.py -h

---

### keystone_list_users_for_group_by_admin.py — 管理员查询用户组下用户

作用：管理员查询用户组下用户 (v3)，包括 id、name、domain_id、enabled、description、pwd_status、password_expires_at。
用法详见：python scripts/iam/keystone_list_users_for_group_by_admin.py -h

---

### keystone_list_versions.py — 查询 Keystone 版本列表

作用：查询 Keystone 版本列表 (v3)，包括 id、status、updated。
用法详见：python scripts/iam/keystone_list_versions.py -h

---

### keystone_list_domain_permissions_for_group.py — 查询用户组域权限

作用：查询用户组域权限 (v3)，包括 id、name、display_name、type、catalog、description、flag、domain_id。
用法详见：python scripts/iam/keystone_list_domain_permissions_for_group.py -h

---

### keystone_list_project_permissions_for_group.py — 查询用户组项目权限

作用：查询用户组项目权限 (v3)，包括 id、name、display_name、type、catalog、description、flag、domain_id。
用法详见：python scripts/iam/keystone_list_project_permissions_for_group.py -h

---

### keystone_list_all_project_permissions_for_group.py — 查询用户组所有项目权限

作用：查询用户组所有项目权限 (v3)，包括 id、name、display_name、type、catalog、description、flag。
用法详见：python scripts/iam/keystone_list_all_project_permissions_for_group.py -h

---

### keystone_show_catalog.py — 查询服务目录

作用：查询服务目录 (v3)，包括 id、name、type、endpoints_count。
用法详见：python scripts/iam/keystone_show_catalog.py -h

---

### keystone_show_endpoint.py — 查询终端节点详情

作用：查询终端节点详情 (v3)，包括 id、interface、region_id、service_id、url、region、enabled、links。
用法详见：python scripts/iam/keystone_show_endpoint.py -h

---

### keystone_show_group.py — 查询用户组详情

作用：查询用户组详情 (v3)，包括 id、name、domain_id、description、create_time、links。
用法详见：python scripts/iam/keystone_show_group.py -h

---

### keystone_show_identity_provider.py — 查询身份提供商详情

作用：查询身份提供商详情 (v3)，包括 id、enabled、description、sso_type、remote_ids、links。
用法详见：python scripts/iam/keystone_show_identity_provider.py -h

---

### keystone_show_mapping.py — 查询映射详情

作用：查询映射详情 (v3)，包括 id、links、rules。
用法详见：python scripts/iam/keystone_show_mapping.py -h

---

### keystone_show_permission.py — 查询权限详情

作用：查询权限详情 (v3)，包括 id、name、display_name、type、catalog、description、domain_id、flag、description_cn、links、policy、updated_time、created_time。
用法详见：python scripts/iam/keystone_show_permission.py -h

---

### keystone_show_project.py — 查询项目详情

作用：查询项目详情 (v3)，包括 id、name、domain_id、enabled、description、is_domain、parent_id、links。
用法详见：python scripts/iam/keystone_show_project.py -h

---

### keystone_show_protocol.py — 查询协议详情

作用：查询协议详情 (v3)，包括 id、mapping_id、links。
用法详见：python scripts/iam/keystone_show_protocol.py -h

---

### keystone_show_region.py — 查询区域详情

作用：查询区域详情 (v3)，包括 id、description、parent_region_id、type、links、locales。
用法详见：python scripts/iam/keystone_show_region.py -h

---

### keystone_show_security_compliance.py — 查询安全合规配置

作用：查询安全合规配置 (v3)，包括 password_regex、password_regex_description。
用法详见：python scripts/iam/keystone_show_security_compliance.py -h

---

### keystone_show_security_compliance_by_option.py — 按选项查询安全合规配置

作用：按选项查询安全合规配置 (v3)，包括 password_regex、password_regex_description。
用法详见：python scripts/iam/keystone_show_security_compliance_by_option.py -h

---

### keystone_show_service.py — 查询服务详情

作用：查询服务详情 (v3)，包括 id、name、type、enabled、description、links。
用法详见：python scripts/iam/keystone_show_service.py -h

---

### keystone_show_user.py — 查询用户详情

作用：查询用户详情 (v3 Keystone)，包括 id、name、domain_id、enabled、description、pwd_status、last_project_id、password_expires_at、access_mode、links。
用法详见：python scripts/iam/keystone_show_user.py -h

---

### keystone_show_version.py — 查询 Keystone 版本详情

作用：查询 Keystone 版本详情 (v3)，包括 id、status、updated、links、media_types。
用法详见：python scripts/iam/keystone_show_version.py -h

---

### keystone_validate_token.py — 校验 Token

作用：校验 Token (v3)，包括 methods、expires_at、issued_at。
用法详见：python scripts/iam/keystone_validate_token.py -h

---

### keystone_checkrole_for_group.py — 检查用户组角色

作用：检查用户组角色 (v3)。
用法详见：python scripts/iam/keystone_checkrole_for_group.py -h

---

### keystone_check_domain_permission_for_group.py — 检查用户组是否拥有域权限

作用：检查用户组是否拥有域权限 (v3)。
用法详见：python scripts/iam/keystone_check_domain_permission_for_group.py -h

---

### keystone_check_project_permission_for_group.py — 检查用户组是否拥有项目权限

作用：检查用户组是否拥有项目权限 (v3)。
用法详见：python scripts/iam/keystone_check_project_permission_for_group.py -h

---

### keystone_check_user_in_group.py — 检查用户是否在用户组中

作用：检查用户是否在用户组中 (v3)。
用法详见：python scripts/iam/keystone_check_user_in_group.py -h
