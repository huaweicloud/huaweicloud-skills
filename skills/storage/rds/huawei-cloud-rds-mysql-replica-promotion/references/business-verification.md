# Business Verification after Single-to-HA Conversion (RDS for MySQL)

> This reference is presented by the SKILL **inside the Step 10 workflow summary** as a notice to the user. Business verification is a user-driven, post-workflow activity, not a workflow step: the SKILL cannot obtain verification results through hcloud, and the user runs these checks in an environment with database credentials and application access, reporting the results back in the conversation. The HA failover check is **optional** and requires the user's explicit decision.

## 1. Verify the Change Result (Console Status)

- Confirm the instance status is "Normal" (`ACTIVE`).
- Confirm the instance type has changed to "Primary/Standby" (`Ha`).
- On the instance details page, check the primary/standby information and confirm both the primary and standby nodes exist and are normal.
- Confirm the standby node's AZ is the one selected during the conversion (record `same_az` truthfully when the primary and standby are deployed in the same AZ).

## 2. Verify Primary/Standby Replication Status (SHOW SLAVE STATUS)

Connect to the primary instance's database and run:

```sql
SHOW SLAVE STATUS \G;
```

Check the following key metrics:

| Metric | Expected Value | Description |
| --- | --- | --- |
| Slave_IO_Running | Yes | The I/O thread is running and receiving logs from the primary node |
| Slave_SQL_Running | Yes | The SQL thread is running and applying logs |
| Seconds_Behind_Master | 0 or near 0 | Delay in seconds of the standby node behind the primary node; 0 means in sync |
| Last_IO_Error | Empty | No I/O thread errors |
| Last_SQL_Error | Empty | No SQL thread errors |

## 3. Verify Monitoring Metrics

On the RDS console monitoring page or through CES (Cloud Eye), check the following metrics:

| Metric | Purpose | Expected State |
| --- | --- | --- |
| CPU usage | Confirm CPU returns to normal after the change | Falls back to a normal level after the conversion completes |
| Memory usage | Confirm memory usage is normal | Within the normal threshold |
| Disk space usage | Confirm sufficient storage | Within the normal threshold |
| IOPS | Confirm I/O performance is normal | Within the normal threshold |
| Database connections | Confirm the connection count is normal | Consistent with the level before the change |
| Primary/standby sync delay | Confirm the primary and standby are in sync | Delay is 0 or near 0 |

## 4. Verify Data Consistency

Create test data on the primary instance and verify that the standby node is synced:

1. Run on the primary instance: `CREATE DATABASE IF NOT EXISTS ha_test_db;`
2. Run on the primary instance: `USE ha_test_db; CREATE TABLE test_table (id INT PRIMARY KEY, msg VARCHAR(100)); INSERT INTO test_table VALUES (1, 'HA_SYNC_TEST');`
3. Connect to the standby node (get the standby node's private IP from the console) and run: `SELECT * FROM ha_test_db.test_table;`
4. Confirm the test data is queryable on the standby node, verifying normal primary/standby sync.
5. Clean up the test data: run `DROP DATABASE ha_test_db;` on the primary instance.

## 5. Business Connectivity Verification

### 5.1 Network Connectivity Verification

Confirm network connectivity from the application server to the RDS instance:

```bash
telnet {instance private IP} {database port}
```

Example: `telnet 192.168.0.120 3306`. Expected result: connection succeeds and returns `Escape character is '^]'.`

### 5.2 Database Connection Verification

Use a MySQL client to connect to the instance and verify the database is accessible:

```bash
mysql -h {instance private IP} -P {port} -u {username} -p
```

After connecting, run the following verification SQL:

```sql
SELECT @@version;                          -- confirm the correct database version
SHOW DATABASES;                            -- confirm the business database exists
SELECT COUNT(*) FROM {business_table};      -- confirm business data is queryable
SHOW VARIABLES LIKE 'read_only';           -- should be OFF on the primary node
```

### 5.3 Application-Level Verification

Run smoke tests at the application level to verify business functions:

| Check Item | Verification Method | Expected Result |
| --- | --- | --- |
| Application startup | Restart the application service and confirm it can connect to the database | Application starts successfully with no database connection errors |
| Read/write functions | Run core business read/write operations | Reads and writes work normally, data is consistent |
| Transaction functions | Run transaction operations (BEGIN/COMMIT/ROLLBACK) | Transactions commit and roll back normally |
| Connection pool | Check the application connection pool status | Connection pool is normal, with no connection leaks or timeouts |

## 6. High Availability Verification (Optional)

> Optional: the HA failover check triggers a real primary/standby switchover in the console, which is perceptible in the production environment and is **executed only if the user decides to**. Not enforced by default.

After the instance is converted to primary/standby, the HA failover capability can be verified:

- Perform a "Primary/Standby Switchover" operation in the console (planned switchover).
- Observe the switchover process: the instance status shows "Switching Over" (`SWITCHOVER`).
- After the switchover completes, confirm business connections recover automatically (if the application uses the connection address rather than a fixed IP, no connection configuration change is needed).
- Confirm the former standby node becomes the new primary node and the former primary node becomes the new standby node.
- Confirm no data loss and business functions are normal.
