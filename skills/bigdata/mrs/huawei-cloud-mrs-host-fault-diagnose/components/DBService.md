# DBService Component Fault Diagnosis Configuration

## Component Basic Info

| Item | Content |
|------|------|
| Service name | DBService |
| Roles | DBServer, DBroker |
| Process names | gaussdb, ha_monitor, ha.bin |
| Version | FusionInsight-dbservice-2.7.0 |
| Install user | ommdba (gaussdb), omm (ha) |

## Ports

| Role | Port | Description |
|------|------|------|
| DBServer | 20013 | GaussDB database port (on floating IP) |
| DBServer | 20015 | GaussDB local listening port (127.0.0.1) |
| DBroker | 20016 | DBroker service port |

## Log Paths

| Role | Log directory | Key log files |
|------|----------|-------------|
| DBServer | /var/log/Bigdata/dbservice/DB/ | gaussdb-*.log*, pg_log/error*.log* |
| DBServer (HA) | /var/log/Bigdata/dbservice/ha/ | ha.log*, runlog/ha.bin*.log* |
| DBroker | /var/log/Bigdata/dbservice/ | DBroker*.log* |
| DBServer (scripts) | /var/log/Bigdata/dbservice/scriptlog/ | *.log* |
| DBServer (health check) | /var/log/Bigdata/dbservice/healthCheck/ | *.log* |

## Install Directories

| Role | Install directory |
|------|----------|
| DBServer | $BIGDATA_HOME/FusionInsight_Current/1_4_DBServer/ |
| DBroker | $BIGDATA_HOME/FusionInsight_Current/1_5_DBroker/ |
| Component common | $BIGDATA_HOME/components/current/DBService/ |
| GaussDB binary | $BIGDATA_HOME/FusionInsight_BASE_8.6.0.1/install/FusionInsight-dbservice-2.7.0/gaussdb/ |

## Data Directories

| Role | Data directory |
|------|----------|
| DBServer | /srv/BigData/dbdata_service/data |
| DBServer (backup) | /srv/BigData/dbdata_service/backup |

## Health Check

| Role | Check type | Check target |
|------|---------|---------|
| DBServer | PID | gaussdb process, PID file in data directory |
| DBServer (HA) | PID | ha_monitor process, ha.bin process |
| DBroker | HTTP | DBroker health check interface |

## Dependencies

| Dependency service | Dependency type | Process names | Port | Description |
|---------|---------|--------|------|------|
| None | - | - | - | DBService is a base service with no external dependencies |

## Scenario-Specific Checks

### Install(install)
- Check whether GaussDB binary files are complete (gaussdb/bin/gaussdb)
- Check whether data directory /srv/BigData/dbdata_service/data is initialized (initdb)
- Check postgresql.conf key parameters (shared_buffers, max_connections, max_locks_per_transaction)
- Check pg_hba.conf authentication rules
- Check HA configuration (ha module: hacom.xml, hacom_local.xml)
- Verify gsql connection: gsql -d postgres -c "select version()"

### Uninstall(uninstall)
- Check whether components depending on this service have been uninstalled (services like Hive metastore that depend on DBService must be uninstalled first)
- Stop HA (ha_monitor, ha.bin) before uninstalling, check HA resource status
- Check whether data directory /srv/BigData/dbdata_service/data needs to be retained (business data)
- Post-uninstall verification: gaussdb process does not exist, ports 20013/20015 not listening, HA resources released
- Check residual files: whether $BIGDATA_HOME/FusionInsight_Current/*_DBServer/ directory has been cleaned up

### Reinstall(reinstall)
- Check whether data directory needs to be retained (business databases such as Hive metastore)
- Check whether backup directory /srv/BigData/dbdata_service/backup exists
- Stop HA (ha_monitor, ha.bin) before reinstalling
- Check GaussDB configuration file backup (postgresql.conf, pg_hba.conf)
- After reinstall, restore data and rebuild HA

### Start(start)
- Check data directory permissions (ommdba:dbgrp 700)
- Check shared memory configuration (ipcs -m)
- Check whether ports 20013/20015 are occupied
- Start order: gaussdb first → then ha_monitor/ha.bin
- Verify: gsql -d postgres -c "select 1"
- Check HA status: ha_resource_status

### Stop(stop)
- Check number of active connections (SELECT count(*) FROM pg_stat_activity WHERE state='active')
- Stop order: ha_monitor/ha.bin first → then gaussdb
- Check whether there are long-running queries in progress
- Check whether there are ongoing backup operations

### Scale Out(scale_out)
- New node needs to initialize GaussDB data directory
- Configure HA primary-standby relationship (modify hacom.xml)
- New node needs to sync data (pg_basebackup or physical replication)
- Check floating IP configuration
- Verify HA primary-standby failover

### Scale In(scale_in)
- Check whether the scaled-in node is the Active node (must switch first)
- Remove node from HA configuration
- Check data replica integrity of remaining nodes
- Clean up data directory of the scaled-in node

## Alarm Document References

| Alarm type | Alarm ID | Document path |
|----------|--------|----------|
| Service unavailable | 27001 | `../huawei-cloud-mrs-host-alarm-diagnose/alarms/27001.md` |
| Process fault | 12007 | `../huawei-cloud-mrs-host-alarm-diagnose/alarms/12007.md` (step 5 references `12007/DBService.md`) |
