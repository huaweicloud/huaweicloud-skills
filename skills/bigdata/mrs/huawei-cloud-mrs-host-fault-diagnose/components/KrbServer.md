# KrbServer Component Fault Diagnosis Configuration

## Component Basic Info

| Item | Content |
|------|------|
| Service name | KrbServer |
| Roles | KerberosServer, KerberosAdmin |
| Process names | krb5kdc, kadmind |
| Version | FusionInsight-kerberos-1.21 |
| Install user | omm |

## Ports

| Role | Port | Description |
|------|------|------|
| KerberosServer | 21732 | KDC service port (kdc_ports) |
| KerberosAdmin | 21730 | kadmind management port |
| KerberosAdmin | 21731 | kpasswd password change port |

## Log Paths

| Role | Log directory | Key log files |
|------|----------|-------------|
| KerberosServer | /var/log/Bigdata/kerberos/ | krb5kdc.log*, kadmind.log*, check-serviceDetail.log* |
| KerberosServer (OMS) | /var/log/Bigdata/okerberos/ | oms-krb5kdc.log*, oms-kadmind.log*, checkservice_detail.log* |
| KerberosAdmin | /var/log/Bigdata/kerberos/ | KerberosAdmin_genConfigDetail.log*, genKeytab.log* |

## Install Directories

| Role | Install directory |
|------|----------|
| KerberosServer | $BIGDATA_HOME/FusionInsight_Current/1_3_KerberosServer/ |
| KerberosAdmin | $BIGDATA_HOME/FusionInsight_Current/1_3_KerberosAdmin/ |
| Component common | $BIGDATA_HOME/components/current/KrbServer/ |

## Data Directories

| Role | Data directory |
|------|----------|
| KerberosServer | $BIGDATA_HOME/tmp/krb5kdc (KDC database) |
| KerberosServer (OMS) | $BIGDATA_HOME/om-server/tmp/ (OMS KDC) |

## Health Check

| Role | Check type | Check target |
|------|---------|---------|
| KerberosServer | PID | PID file: $BIGDATA_HOME/tmp/krb-omm-kdc.pid |
| KerberosAdmin | PID | PID file: $BIGDATA_HOME/tmp/krb-omm-kadmind.pid |
| KerberosServer (OMS) | PID | PID file: $BIGDATA_HOME/om-server/tmp/krb-oms-omm-kdc.pid |
| KerberosAdmin (OMS) | PID | PID file: $BIGDATA_HOME/om-server/tmp/krb-oms-omm-kadmind.pid |

## Dependencies

| Dependency service | Dependency type | Process names | Port | Description |
|---------|---------|--------|------|------|
| LdapServer | Strong | slapd | 21750 | KDC database stored in LDAP (openldap_ldapconf) |

## Scenario-Specific Checks

### Install(install)
- Check whether krb5.conf is correctly generated (realm, kdc port, admin_server port)
- Check whether KDC database is initialized successfully
- Check whether LDAP backend connection is normal (database_module = openldap_ldapconf)
- Check whether keytab files are correctly generated
- Check whether all service principals (PRINCIPAL_LIST) are created

### Uninstall(uninstall)
- Check whether services depending on KrbServer have been uninstalled (all security cluster components depend on Kerberos, must be uninstalled last)
- Stop kadmind and krb5kdc processes before uninstalling
- Check whether KDC database needs backup ($BIGDATA_HOME/tmp/krb5kdc)
- Check whether keytab files need backup (must be re-synced to each node after recovery)
- Post-uninstall verification: krb5kdc/kadmind processes do not exist, ports 21732/21730 not listening
- Check residual files: $BIGDATA_HOME/tmp/krb5kdc/ directory, whether krb5.conf has been cleaned up

### Reinstall(reinstall)
- Check whether old KDC database needs backup ($BIGDATA_HOME/tmp/krb5kdc)
- Check whether keytab files are backed up (must be re-synced after recovery)
- Check whether LDAP backend data is preserved
- After reinstall, re-initialize KDC database and create service principals

### Start(start)
- Check whether krb5.conf configuration is correct (cat $BIGDATA_HOME/common/runtime0/krb5.conf)
- Check whether KDC port 21732 is occupied
- Check whether kadmind port 21730 is occupied
- Check whether LDAP backend service is normal
- Post-start verification: kinit test ticket acquisition

### Stop(stop)
- Check whether there are active Kerberos ticket caches (affects running services)
- Check whether there are ongoing kadmin operations
- Stop order: kadmind first, then krb5kdc

### Scale Out(scale_out)
- New node KDC needs to be added to the kdc list in krb5.conf
- New node needs to sync LDAP backend configuration
- New node needs to initialize KDC database replica
- Verify data synchronization between multiple KDCs

### Scale In(scale_in)
- Remove node from kdc list in krb5.conf
- Ensure remaining KDC nodes are available
- Check ticket cache cleanup on the scaled-in node

## Alarm Document References

| Alarm type | Alarm ID | Document path |
|----------|--------|----------|
| Service unavailable | 25500 | `../huawei-cloud-mrs-host-alarm-diagnose/alarms/25500.md` |
| Process fault | 12007 | `../huawei-cloud-mrs-host-alarm-diagnose/alarms/12007.md` (step 5 references `12007/KrbServer.md`) |
