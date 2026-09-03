# Component Fault Diagnosis Configuration Template

> Copy this file, rename it to `<component_name>.md` (e.g. `KrbServer.md`, `DBService.md`), fill in the following information to support all scenario diagnoses.

## Component Basic Info

| Item | Content |
|------|------|
| Service name | <service name, e.g. KrbServer, DBService, HDFS> |
| Roles | <list of role names, e.g. KerberosServer/KerberosAdmin; DBServer/DBroker> |
| Process names | <process names, e.g. krb5kdc/kadmind; gaussdb/ha_monitor> |
| Version | <e.g. FusionInsight-kerberos-1.21; FusionInsight-dbservice-2.7.0> |
| Install user | <e.g. omm> |

## Ports

| Role | Port | Description |
|------|------|------|
| <role1> | <port1> | <description> |
| <role2> | <port2> | <description> |

## Log Paths

| Role | Log directory | Key log files |
|------|----------|-------------|
| <role1> | /var/log/Bigdata/<directory>/ | <filename>* |
| <role2> | /var/log/Bigdata/<directory>/ | <filename>* |

## Install Directories

| Role | Install directory |
|------|----------|
| <role1> | $BIGDATA_HOME/FusionInsight_Current/<instance_number>_<role>/ |
| <role2> | $BIGDATA_HOME/components/current/<component_name>/ |

## Data Directories

| Role | Data directory |
|------|----------|
| <role1> | <e.g. /srv/BigData/dbdata_service/data> |

## Health Check

| Role | Check type | Check target |
|------|---------|---------|
| <role1> | PID/HTTP/SCRIPT | <e.g. PID file path; HTTP URL; script path> |

## Dependencies

| Dependency service | Dependency type | Process names | Port | Description |
|---------|---------|--------|------|------|
| <dependent service> | Strong/Weak | <dependency service process name> | <dependency service port> | <description> |

## Scenario-Specific Checks

### Install(install)
- <additional check points for install scenario, e.g. configuration file generation, permission initialization>

### Uninstall(uninstall)
- <additional check points for uninstall scenario, e.g. dependency check, data cleanup confirmation>

### Reinstall(reinstall)
- <additional check points for reinstall scenario, e.g. data retention check, configuration backup>

### Reinstall Host(reinstall_host)
- <additional check points for host reinstall scenario, e.g. SSH mutual trust recovery, data directory mounting, full component reinstallation>

### Start(start)
- <additional check points for start scenario>

### Stop(stop)
- <additional check points for stop scenario>

### Scale Out(scale_out)
- <additional check points for scale_out scenario>

### Scale In(scale_in)
- <additional check points for scale_in scenario>

## Alarm Document References

| Alarm type | Alarm ID | Document path |
|----------|--------|----------|
| Service unavailable | <alarm_id> | `../huawei-cloud-mrs-host-alarm-diagnose/alarms/<alarm_id>.md` |
| Process fault | 12007 | `../huawei-cloud-mrs-host-alarm-diagnose/alarms/12007.md` (step 5 references `12007/<component_name>.md`) |
