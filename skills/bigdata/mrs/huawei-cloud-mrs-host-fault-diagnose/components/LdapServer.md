# LdapServer Component Fault Diagnosis Configuration

## Component Basic Info

| Item | Content |
|------|------|
| Service name | LdapServer |
| Roles | SlapdServer |
| Process names | slapd |
| Version | FusionInsight-LdapServer-1.0.0 |
| Install user | omm |
| Executable path | /usr/sbin/slapd (RedHat) or /usr/lib/openldap/slapd (SUSE) |

## Ports

| Role | Port | Description |
|------|------|------|
| SlapdServer | 21750 | LDAPS (LDAP over TLS) service port |

## Log Paths

| Role | Log directory | Key log files |
|------|----------|-------------|
| SlapdServer | /var/log/Bigdata/ldapserver/ | ldapserver_chk_service.log* (service check, priority 1) |
| SlapdServer | /var/log/Bigdata/ldapserver/ | ldapserver_mon.log* (monitoring log, priority 2) |
| SlapdServer | /var/log/Bigdata/ldapserver/ | ldapserver_start.log* (startup log, priority 3) |
| SlapdServer | /var/log/Bigdata/ldapserver/ | ldapserver_status.log* (status query, priority 4) |
| SlapdServer | /var/log/Bigdata/ldapserver/ | ldapserver_metric_collect.log* (metric collection, priority 5) |

> Log path environment variable: ${LDAP_SERVER_LOG_PATH}, typically /var/log/Bigdata/ldapserver

## Install Directories

| Role | Install directory |
|------|----------|
| SlapdServer | $BIGDATA_HOME/FusionInsight_Current/1_*_SlapdServer/ |
| Component common | $BIGDATA_HOME/components/current/LdapServer/ |

## Data Directories

| Role | Data directory |
|------|----------|
| SlapdServer | $LDAPS_DATA_HOME/ldapData/ldapserver/data (BDB database) |
| SlapdServer (backup) | $BIGDATA_HOME/FusionInsight_Current/1_*_SlapdServer/backup/ |

## Health Check

| Role | Check type | Check target |
|------|---------|---------|
| SlapdServer | PID | PID file: conf/slapd.pid (generated when process is running) |
| SlapdServer | SCRIPT | ldapserver_chk_service.sh (ldapsearch verifies service availability) |

## Dependencies

| Dependency service | Dependency type | Process names | Port | Description |
|---------|---------|--------|------|------|
| None | - | - | - | LdapServer is a base service with no external dependencies |

## HA Mechanism

| Item | Content |
|------|------|
| HA mode | Provider-Consumer (primary-standby sync) |
| Sync method | syncrepl (refreshAndPersist) |
| Sync interval | 15 seconds |
| Role determination | The first IP in LDAP_SERVER_LIST is Provider, the rest are Consumers |
| Data consistency check | contextCSN comparison + key DN comparison (pg_search_dn/krbadmin/krbkdc) + entry count comparison (Peoples/Groups) |
| Sync timeout threshold | LDAP_SYNC_ALARM_THRESH_HOLD=12 (alarm after 12 consecutive sync failures) |

## Scenario-Specific Checks

### Install(install)
- Check whether slapd binary file exists (/usr/sbin/slapd or /usr/lib/openldap/slapd)
- Check whether slapd.conf is correctly generated (provider/consumer template, schema include list)
- Check whether certificate files are complete (ca.crt, sslservercert.crt, ldapserver_ssl.crt, ldapserver_ssl.key)
- Check whether certificate chain file cacert.pem is correctly generated (ca.crt + sslservercert.crt concatenated)
- Check whether server.key is decrypted from ldapserver_ssl.key (openssl rsa + certKey)
- Check whether BDB data directory is initialized (DB_CONFIG file exists)
- Check whether base.ldif is correctly imported
- Check whether kerberos.schema is correctly loaded

### Uninstall(uninstall)
- Check whether services depending on LdapServer have been uninstalled (KrbServer depends on LDAP, must uninstall KrbServer first)
- Stop slapd process before uninstalling, check whether slapd.pid file exists
- Check whether data directory needs backup ($LDAPS_DATA_HOME/ldapData/ldapserver/data)
- Check whether certificate files need backup (ca.crt, ldapserver_ssl.crt, ldapserver_ssl.key)
- Post-uninstall verification: slapd process does not exist, port 21750 not listening, slapd.pid cleaned up
- Check residual files: BDB data directory, slapd.conf, certificate files cleaned up
- Check whether ldapclient configuration needs cleanup (nsswitch.conf, ldap.conf)

### Reinstall(reinstall)
- Check whether old data directory needs backup ($LDAPS_DATA_HOME/ldapData/ldapserver/data)
- Check whether backup package is complete (tar.gz + sha256 verification)
- Stop slapd process before reinstalling
- Check slapd.conf configuration file backup (provider/consumer template)
- After reinstall, restore data and re-establish syncrepl sync relationship
- Check whether certificate files need to be regenerated

### Start(start)
- Check whether slapd.conf configuration is correct (cat conf/slapd.conf, confirm suffix, rootdn, directory path)
- Check whether port 21750 is occupied
- Check whether certificate files are complete (ca.crt, server.cert, server.key, cacert.pem)
- Check whether server.key is readable (permission 600)
- Check whether BDB data directory exists and has DB_CONFIG file
- Check whether slapd.pid file path has write permission
- Post-start verification: ldapsearch -H ldaps://<ip>:21750 -x -LLL -D cn=root,dc=hadoop,dc=com -b dc=hadoop,dc=com -s base
- Check data sync status after startup (check_ldap_data_sync_status)

### Stop(stop)
- Check whether there are active LDAP connections (netstat | grep 21750 | grep ESTABLISHED)
- Check whether there are ongoing ldapsearch operations
- Check whether slapd.pid file exists (used to get process PID)
- Post-stop verification: process does not exist, port not listening, slapd.pid cleaned up

### Scale Out(scale_out)
- New node needs to initialize BDB data directory (DB_CONFIG)
- New node needs to configure slapd.conf (consumer template, provider points to primary node)
- New node needs to sync certificate files (ca.crt, server.cert, server.key, cacert.pem)
- New node needs to establish syncrepl sync relationship (full data sync from Provider)
- Verify data sync completion (contextCSN consistent, key DN consistent, entry count consistent)
- New node needs to configure ldapclient (nsswitch.conf, ldap.conf, PAM template)

### Scale In(scale_in)
- Check whether the scaled-in node is the Provider (must switch Provider role first)
- Remove node from LDAP_SERVER_LIST
- Ensure syncrepl sync between remaining nodes is normal
- Check that slapd process on the scaled-in node has been stopped
- Clean up data directory of the scaled-in node

## Alarm Document References

| Alarm type | Alarm ID | Document path |
|----------|--------|----------|
| Service unavailable | 25000 | `../huawei-cloud-mrs-host-alarm-diagnose/alarms/25000.md` |
| Process fault | 12007 | `../huawei-cloud-mrs-host-alarm-diagnose/alarms/12007.md` (step 5 references `12007/LdapServer.md`) |
