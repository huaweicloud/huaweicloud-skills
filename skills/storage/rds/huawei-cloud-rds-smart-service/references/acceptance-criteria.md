# Acceptance Criteria

## Functional Requirements

### 1. Basic Q&A (Product Knowledge & Instance Query)
- [ ] Can list all RDS instances across all engines
- [ ] Can filter instances by datastore type (MySQL, PostgreSQL, SQL Server, MariaDB, GaussDB)
- [ ] Can list available flavors for each engine and version
- [ ] Can list available database versions for each engine
- [ ] Can show instance upgrade version availability
- [ ] Can show instance quotas

### 2. SQL Performance Optimization
- [ ] Can query slow SQL logs within a specified date range
- [ ] Can download slow log files
- [ ] Can query TOP SQL statements
- [ ] Can query historical TOP SQL
- [ ] Can query historical wait events
- [ ] Can show top objects (tables/indexes with high load)
- [ ] Can set SQL concurrency limits

### 3. Daily O&M (Instance Management)
- [ ] Can restart an RDS instance (with confirmation)
- [ ] Can resize instance flavor (with confirmation)
- [ ] Can enlarge disk volume (with confirmation)
- [ ] Can reduce disk volume (with confirmation)
- [ ] Can perform primary-standby switchover (with confirmation)
- [ ] Can set read-only mode
- [ ] Can update instance alias
- [ ] Can list and show task status
- [ ] Can set/show auto disk expansion policy
- [ ] Can show storage used space

### 4. Fault Diagnosis & Troubleshooting
- [ ] Can query error logs within a specified date range
- [ ] Can download error log files
- [ ] Can show replication status (primary-standby)
- [ ] Can show recovery time window
- [ ] Can list instance diagnosis results
- [ ] Can query historical sessions
- [ ] Can perform intelligent session kill (with confirmation)
- [ ] Can show second-level monitoring
- [ ] Can validate instance connection

### 5. Parameter Tuning
- [ ] Can list all parameter groups
- [ ] Can show parameter group details
- [ ] Can show instance parameter configuration
- [ ] Can create parameter group (with confirmation)
- [ ] Can update parameter group (with confirmation)
- [ ] Can apply parameter group to instance (with confirmation)
- [ ] Can update instance parameter directly (with confirmation)
- [ ] Can list parameter change history
- [ ] Can compare parameter configurations

### 6. Backup & Recovery
- [ ] Can show backup policy
- [ ] Can set backup policy (with confirmation)
- [ ] Can list backups
- [ ] Can create manual backup (with confirmation)
- [ ] Can delete manual backup (with confirmation)
- [ ] Can show backup download link
- [ ] Can restore to new instance (with confirmation)
- [ ] Can restore to existing instance (with confirmation)
- [ ] Can restore tables (table-level recovery, with confirmation)
- [ ] Can show backup usage

### 7. Security Management
- [ ] Can set security group (with confirmation)
- [ ] Can switch SSL configuration (with confirmation)
- [ ] Can list audit logs
- [ ] Can show/set audit log policy (with confirmation)

## Non-Functional Requirements

### Execution Mode
- [ ] CLI is the primary execution mode
- [ ] SDK fallback works when CLI is unavailable
- [ ] REST API fallback works when both CLI and SDK are unavailable
- [ ] Appropriate error messages are shown when all modes fail

### Safety
- [ ] All mutating operations require explicit user confirmation
- [ ] Credentials are never hardcoded or exposed in output
- [ ] Region parameter is always specified explicitly
- [ ] Error messages are actionable and clear

### Compatibility
- [ ] Supports all RDS engines: MySQL, PostgreSQL, SQL Server, MariaDB, GaussDB(for MySQL), TaurusDB
- [ ] Works with hcloud CLI 7.2.0+
- [ ] Works with huaweicloudsdkrds v3.x
- [ ] Default region is cn-north-4, overridable via --cli-region

### Documentation
- [ ] SKILL.md follows Huawei Cloud Skill Specification
- [ ] All reference documents are complete and accurate
- [ ] All commands are documented with examples
- [ ] Parameter table covers all required and optional parameters
