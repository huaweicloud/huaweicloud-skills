# Reference Example Inventory

这份文档把参考仓库中的 example 目录结构完整搬运到 skill 内部，方便后续删除参考仓库后仍能知道还有哪些可复用变体。

说明：
- `validated stack`: 当前 skill 中已经有对应的已验证 `*_stack`。
- `variant only`: 当前还没有独立 stack，但适合作为增强版示例、组合型示例或规则素材。

## antiddos
- current skill status: validated stack exists
- `basic`
- `default-protection-policy`
- `lts-config`

## aom
- current skill status: validated stack exists
- `action-callback`
- `alarm-rule`
- `alarm-rule/distribute-alarm`
- `alarm-rule/prevent-elb-alarm-storm`

## apig
- current skill status: validated stack exists
- `api-custom-authorizer-with-functiongraph`
- `kafka-forward-plugin`
- `proxy-cache-plugin`

## as
- current skill status: validated stack exists
- `alarm-policy`
- `scaling-configuration`
- `scaling-group`

## bms
- current skill status: validated stack exists
- `bms-instance`
- `bms-reset-password`
- `volume-attach`

## cbh
- current skill status: validated stack exists
- `basic-instance`
- `change-instance-type`
- `ha-instance`

## cbr
- current skill status: validated stack exists
- `vault-server`
- `vault-turbo`
- `vault-volume`

## cc
- current skill status: validated stack exists
- `bandwidth-package`
- `central-network`
- `global-connection-bandwidth`

## cce
- current skill status: validated stack exists
- `addon-autoscaler`
- `addon-coredns`
- `kubenetes`
- `kubenetes/authenticate-with-config`
- `kubenetes/namespace`
- `kubenetes/pvc-with-existing-obs-bucket`
- `kubenetes/pvc-with-new-obs-bucket`
- `node`
- `node-partition`
- `node-pool`
- `standard-cluster`
- `turbo-cluster`

## cci
- current skill status: validated stack exists
- `deployment`
- `network`
- `service`

## cdn
- current skill status: validated stack exists
- `cache-management`
- `domain-with-https-and-cache`
- `rule-engine`

## ces
- current skill status: validated stack exists
- `alarm-template`
- `dashboard`
- `resource-group`

## coc
- current skill status: validated stack exists
- `script`
- `script-execution`
- `script-order-execution`

## cts
- current skill status: validated stack exists
- `data-tracker`
- `notification`
- `system-tracker`

## dc
- current skill status: validated stack exists
- `connect-gateway`
- `global-gateway`
- `hosted-connect`
- `virtual-interface`

## dcs
- current skill status: validated stack exists
- `redis-data-sync`
- `redis-high-availability-instance`
- `redis-single-instance`

## deh
- current skill status: validated stack exists
- `associate-ecs-instance`
- `instance`
- `query-resource-quota`

## dew
- current skill status: validated stack exists
- `csms-secret`
- `kms-key`
- `kps-keypair`

## dms
- current skill status: validated stack exists
- `kafka`
- `kafka/instance-configuration`
- `kafka/public-access-instance-network`
- `kafka/replicate-instance-data`
- `kafka/topic-message-produce`
- `rabbitmq`
- `rabbitmq/basic-instance`
- `rabbitmq/message-producer-and-consumer`
- `rabbitmq/monitoring-with-ces-smn-alarm`
- `rocketmq`
- `rocketmq/basic-instance`
- `rocketmq/consumer-group`
- `rocketmq/message-send`
- `rocketmq/migration-task`

## dns
- current skill status: validated stack exists
- `custom-line`
- `endpoint`
- `public-zone-cross-accounts`
- `zone`

## ecs
- current skill status: validated stack exists
- `attached-interface`
- `attached-volume`
- `basic`
- `instance-associate-eip`
- `instance-provisioners`
- `instance-with-userdata`
- `prepaid-instance`

## eg
- current skill status: validated stack exists
- `event-subscriptions`
- `event-subscriptions/custom`
- `event-subscriptions/obs-to-kafka`
- `event-subscriptions/vpc-to-eg`

## elb
- current skill status: validated stack exists
- `dedicated-loadbalancer-with-as`
- `dedicated-loadbalancer-with-full-configuration`
- `shared-loadbalancer-with-full-configuration`

## er
- current skill status: validated stack exists
- `flow-log`
- `route-table`
- `share-instance`
- `vpc-attachment`

## esw
- current skill status: validated stack exists
- `connection`
- `connection-vport-bind`
- `instance`

## evs
- current skill status: validated stack exists
- `snapshot`
- `snapshot-group`
- `volume`

## fgs
- current skill status: validated stack exists
- `triggers`
- `triggers/cts`
- `triggers/eg`
- `triggers/timer`

## hss
- current skill status: validated stack exists
- `host-group`
- `postpaid-host-protection`
- `prepaid-quota`

## iam
- current skill status: validated stack exists
- `users-authorized-through-group`
- `v5`
- `v5/group-policies-associate`
- `v5/password-policy`

## identity-center
- current skill status: validated stack exists
- `group`
- `instance-configuration`
- `password-policy`

## ims
- current skill status: validated stack exists
- `cross-account-migration-with-data-image`
- `cross-account-migration-with-whole-image`
- `export-image-to-obs`

## lts
- current skill status: validated stack exists
- `log-stream`
- `log-transfer`
- `sql-alarm-rule`

## nat
- current skill status: variant only
- `dnat-basic`
- `nat-gateway-vpc-peering`
- `snat-basic`

## obs
- current skill status: validated stack exists
- `bucket-with-encryption`
- `bucket-with-website`
- `object-upload-with-content`
- `object-upload-with-encryption`
- `object-upload-with-source`

## oms
- current skill status: validated stack exists
- `migrate-objects-by-group`
- `migrate-objects-by-task`

## organizations
- current skill status: validated stack exists
- `organization`
- `organization-account`
- `organization-unit`

## ram
- current skill status: validated stack exists
- `automated-resource-share-invitation-processing`
- `cross-account-resource-share`
- `fine-grained-permission-management`

## rds
- current skill status: validated stack exists
- `mysql-instance-associate-eip`
- `mysql-single-instance`
- `postgresql-ha-instance`
- `read-replica-instance`
- `sqlserver-single-instance`

## rgc
- current skill status: validated stack exists
- `account`
- `account-enroll`
- `template`

## rms
- current skill status: validated stack exists
- `assignment-package`
- `policy-assignment`
- `resource-aggregator`

## sdrs
- current skill status: validated stack exists
- `drill`
- `protected-instance`
- `protection-group`

## secmaster
- current skill status: validated stack exists
- `playbook`
- `playbook/custom-rule-and-trigger-by-event`
- `workflow-version`
- `workspace`

## sfs-turbo
- current skill status: validated stack exists
- `obs-target`
- `permission-rule`
- `turbo-file-system`

## smn
- current skill status: validated stack exists
- `ces-event-alarm-rule`
- `publish-message`
- `topic-with-aom-alarm-notification`

## sms
- current skill status: validated stack exists
- `migration-project`
- `migration-task`
- `server-template`

## swr
- current skill status: validated stack exists
- `organization`
- `repository`
- `retention-policy`

## tms
- current skill status: validated stack exists
- `batch-associate-tags`
- `preset-tags`
- `query-resource-types`

## vpc
- current skill status: variant only
- `basic`
- `peering`
- `security-group`
- `vip`

## vpcep
- current skill status: validated stack exists
- `approval`
- `endpoint`
- `service`

## vpn
- current skill status: validated stack exists
- `connection`
- `gateway`
- `user`

## waf
- current skill status: validated stack exists
- `cloud-domain`
- `dedicated-domain`
- `dedicated-instance`

## workspace
- current skill status: variant only
- `app`
- `app/policy-group`
- `app/policy-group-scaling-policy`
- `app/server-group`
- `desktop`
- `desktop/basic`

