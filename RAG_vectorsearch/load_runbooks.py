import psycopg2
from pgvector.psycopg2 import register_vector
from sentence_transformers import SentenceTransformer
import os
from dotenv import load_dotenv

load_dotenv()

# Load model
print("Loading embedding model...")
model = SentenceTransformer('all-MiniLM-L6-v2')
print("✅ Model loaded\n")

# Mock Runbooks and Documentation
MOCK_RUNBOOKS = [
    {
        "doc_id": "DOC-0001",
        "title": "DR Environment Architecture and Setup Guide",
        "description": """
Document: Disaster Recovery Environment Architecture
Last Updated: 2024-11-15
Owner: Infrastructure Team

**Overview:**
The Disaster Recovery (DR) environment is a hot standby replica of our production 
SQL Server infrastructure, designed to ensure business continuity in case of 
primary site failure.

**Architecture:**

Primary Data Center (Atlanta):
- 10 SQL Server instances (SQLPROD01-10)
- Always On Availability Groups (3 AGs)
- 50TB total database storage
- 10Gbps network connectivity

DR Data Center (Phoenix):
- 10 SQL Server instances (SQLDR01-10)
- Asynchronous replica mode
- 50TB storage capacity (matched)
- Dedicated 10Gbps link to Atlanta

**Network Setup:**
- Dedicated fiber connection: Atlanta ↔ Phoenix
- Latency: 45-50ms average
- Bandwidth: 10Gbps dedicated
- Backup route via internet VPN (1Gbps)

**Always On Configuration:**
```sql
-- Primary Replica (Atlanta)
Synchronous Commit: Within data center only
Automatic Failover: Between Atlanta nodes

-- DR Replica (Phoenix)  
Asynchronous Commit: To Phoenix
Manual Failover: DR activation requires approval
Readable Secondary: Yes (reporting workload offload)
```

**Database Synchronization:**
- Real-time: Always On async replication
- RPO (Recovery Point Objective): < 5 minutes
- RTO (Recovery Time Objective): < 30 minutes
- Replication lag monitoring: Alert at 2 minutes

**Infrastructure Components:**

SQL Server Configuration:
- Version: SQL Server 2022 Enterprise
- Memory: 256GB per server
- CPU: 32 cores per server
- Storage: SSD, RAID 10
- OS: Windows Server 2022

Network Configuration:
- Primary-DR latency: 45-50ms
- Replication traffic: Compressed, encrypted
- Listener: DR-SQL-Listener.company.com (disabled by default)
- VIP failover: Automated via DNS

**Monitoring:**
- Replication lag dashboard: Grafana
- Alerts: PagerDuty integration
- Health checks: Every 60 seconds
- Failover automation: Rundeck scripts

**Failover Process:**
See DOC-0007 "DR Failover Procedure"

**Cost:**
- Infrastructure: $50K/month
- Network: $15K/month (dedicated line)
- Licensing: Covered under SA
- Total: ~$65K/month

**Testing Schedule:**
- Quarterly DR drill: Failover testing
- Monthly: Replication lag validation
- Weekly: Backup restoration tests

**Related Documents:**
- DOC-0007: DR Failover Procedure
- DOC-0003: Always On Setup Guide
- DOC-0009: Network Architecture
""",
        "url": "https://company.sharepoint.com/sites/IT/DR-Architecture",
        "category": "infrastructure"
    },
    {
        "doc_id": "DOC-0002",
        "title": "Code Promotion Process - Development to Production",
        "description": """
Document: Code Promotion Workflow
Last Updated: 2024-12-01
Owner: DevOps Team

**Overview:**
Standard process for promoting application code and database changes from 
Development → QA → Staging → Production.

**Environments:**

1. Development (DEV)
   - Server: DEV-APP-01, DEV-SQL-01
   - Purpose: Active development
   - Access: All developers
   - Data: Anonymized production snapshot
   - Deployment: Automatic on merge to dev branch

2. QA (Quality Assurance)
   - Server: QA-APP-01, QA-SQL-01
   - Purpose: Testing and validation
   - Access: QA team, developers (read-only)
   - Data: Full test dataset
   - Deployment: Manual trigger after dev validation

3. Staging (UAT - User Acceptance Testing)
   - Server: STG-APP-01, STG-SQL-01
   - Purpose: Final validation before production
   - Access: Business users, QA team
   - Data: Sanitized production copy (refreshed weekly)
   - Deployment: Manual, requires approval

4. Production (PROD)
   - Server: PROD-APP-01 through 10, SQLPROD01-10
   - Purpose: Live customer environment
   - Access: Production support team only
   - Deployment: Change control process required

**Promotion Workflow:**

**Step 1: Development**
```
Developer → Creates feature branch
         → Commits code to Git
         → Creates Pull Request
         → Code review (2 approvals required)
         → Merge to dev branch
         → Auto-deploy to DEV environment
```

**Step 2: QA Deployment**
```
Trigger: Manual button in Azure DevOps
Process:
1. QA lead triggers deployment
2. Automated tests run (unit + integration)
3. If tests pass → Deploy to QA
4. QA team performs manual testing
5. QA sign-off in Jira ticket

Approvers: QA Lead
Timeline: 1-2 days
```

**Step 3: Staging Deployment**
```
Trigger: QA approval + release manager
Process:
1. Create change request in ServiceNow
2. Release manager reviews
3. Schedule deployment window
4. Deploy to Staging
5. UAT testing by business users
6. Sign-off from business stakeholders

Approvers: Release Manager + Business Owner
Timeline: 3-5 days
```

**Step 4: Production Deployment**
```
Trigger: UAT sign-off + change approval board (CAB)
Process:
1. Submit to CAB (meets Tuesdays, Thursdays)
2. CAB approval required
3. Schedule maintenance window
4. Pre-deployment checklist:
   ☑ Backup production database
   ☑ Runbook prepared
   ☑ Rollback plan documented
   ☑ All approvals obtained
   ☑ Communication sent to users

5. Deployment (during maintenance window):
   - 6 PM EST Friday preferred
   - Max 2-hour window
   - On-call team standing by

6. Post-deployment validation:
   ☑ Smoke tests pass
   ☑ Application monitoring green
   ☑ Database health check
   ☑ User acceptance confirmation

7. Close change request

Approvers: CAB (5 members), VP Engineering
Timeline: 1-2 weeks from QA sign-off
```

**Database Changes:**

Schema Changes:
```sql
-- Backward compatible changes only
-- Example: Adding new column
ALTER TABLE Orders ADD COLUMN Priority INT DEFAULT 1;

-- Prohib

ited: Dropping columns in same release
-- Two-phase approach required
```

Migration Process:
1. Generate migration script
2. Test on DEV copy of production data
3. DBA review required
4. Execute in each environment
5. Validate data integrity

**Emergency Hotfix Process:**

For P1/P2 production issues:
1. Create hotfix branch from main
2. Fast-track QA (2-hour testing max)
3. Emergency CAB approval (via Slack)
4. Deploy directly to production
5. Backport to other environments

Approval: VP Engineering + DBA Lead

**Tools:**

Source Control: GitHub Enterprise
CI/CD: Azure DevOps Pipelines
Change Management: ServiceNow
Deployment: Octopus Deploy
Monitoring: Datadog, Grafana

**Rollback Procedure:**

If deployment fails:
1. Immediately notify #incidents Slack channel
2. Execute rollback script (automated)
3. Restore database from pre-deployment backup
4. Validate rollback successful
5. Incident post-mortem within 24 hours

**Key Contacts:**

Release Manager: Sarah Chen (sarah.chen@company.com)
DBA Lead: Mike Rodriguez (mike.r@company.com)  
DevOps Lead: Alex Kim (alex.kim@company.com)
CAB Chair: Jennifer Wu (jennifer.wu@company.com)

**Related Documents:**
- DOC-0005: Production Access Request
- DOC-0006: Database Change Guidelines
- DOC-0011: Emergency Hotfix Process
""",
        "url": "https://company.sharepoint.com/sites/Engineering/Code-Promotion",
        "category": "process"
    },
    {
        "doc_id": "DOC-0005",
        "title": "Production Access Request Process",
        "description": """
Document: Production Environment Access
Last Updated: 2024-10-20
Owner: Security & Compliance Team

**Overview:**
Production access is strictly controlled due to compliance requirements 
(SOC 2, HIPAA, PCI-DSS). All access is logged, monitored, and requires 
business justification.

**Access Levels:**

Level 1: Read-Only Production Database
- View data, execution plans, performance metrics
- Cannot modify data or schema
- Used by: DBAs for troubleshooting
- Approval: Manager + DBA Lead

Level 2: Production Database Write Access
- Can modify data (with restrictions)
- Used for: Data fixes, emergency patches
- Approval: VP Engineering + Security

Level 3: Production Server Admin
- Full server access
- Used for: Infrastructure changes
- Approval: CTO + Security

Level 4: Application Admin (Production)
- Full application access
- Used for: Configuration changes
- Approval: VP Engineering + Product Owner

**Standard Access Request:**

**Step 1: Submit Request**
```
Portal: https://access.company.com
Form Fields:
- Access Type: [Read-Only / Write / Admin]
- System: [Database / Server / Application]
- Justification: [Required - Business reason]
- Duration: [Temporary or Permanent]
- Ticket Reference: [Jira or ServiceNow #]
```

**Step 2: Manager Approval**
- Manager reviews justification
- Validates business need
- Timeline: 1 business day

**Step 3: Security Review**
- Background check verification
- Compliance training completion check
- Security questionnaire
- Timeline: 2-3 business days

**Step 4: Technical Approval**
- DBA Lead (for database access)
- Infrastructure Lead (for server access)
- App Owner (for application access)
- Timeline: 1 business day

**Step 5: Access Provisioning**
- Automated via Active Directory groups
- JIT (Just-In-Time) access enabled
- MFA required for all production access
- Timeline: 1-2 hours after all approvals

**Total Timeline: 3-5 business days**

**Just-In-Time (JIT) Access:**

For temporary access (troubleshooting):
```
1. Request via Slack: #production-access
2. Provide ticket number (Jira/ServiceNow)
3. Specify duration (max 4 hours)
4. Manager + DBA Lead approval in Slack
5. Access granted immediately
6. Auto-revoked after time limit
7. All actions logged in audit trail
```

Approval: Manager + on-call DBA Lead
Timeline: 5-15 minutes

**Emergency Access:**

P1 Incident requiring immediate access:
```
1. Call on-call lead: (555) 0100
2. Explain emergency situation
3. Verbal approval recorded
4. Access granted via break-glass account
5. All actions recorded
6. Post-incident review required within 24 hours
```

**Access Renewal:**

Production access expires:
- Read-only: Every 90 days
- Write access: Every 30 days
- Admin access: Every 14 days

Renewal process:
1. Automated email 7 days before expiration
2. Click renewal link
3. Reconfirm business justification
4. Manager re-approval required
5. Access renewed for same period

**Monitoring & Compliance:**

All production access is:
✓ Logged to SIEM (Splunk)
✓ Monitored for unusual activity
✓ Reviewed weekly by Security team
✓ Audited quarterly for compliance

Automated Alerts:
- Access outside business hours
- Bulk data export
- Schema modifications
- Failed login attempts (3+)
- Privilege escalation

**Access Revocation:**

Immediate revocation if:
- Employee termination
- Role change (no longer needs access)
- Policy violation
- Security incident
- Manager request

**Training Requirements:**

Before production access granted:
☑ Security Awareness Training (annual)
☑ Data Privacy Training (annual)  
☑ Production Access Policy Acknowledgment
☑ HIPAA Training (if accessing PHI)
☑ PCI Training (if accessing payment data)

**Tools:**

Access Portal: Okta Access Gateway
MFA: Duo Security
Audit Logging: Splunk
JIT Access: CyberArk
VPN: Cisco AnyConnect

**Common Scenarios:**

Scenario 1: New DBA joins team
→ Request Level 1 (Read-Only) permanent access
→ Approvers: Manager + DBA Lead + Security
→ Timeline: 3-5 days

Scenario 2: Developer needs to fix data bug
→ Request Level 2 (Write) JIT access for 2 hours
→ Approvers: Manager + on-call DBA via Slack
→ Timeline: 10-15 minutes

Scenario 3: On-call responding to P1 incident
→ Emergency break-glass access
→ Approvers: Verbal from on-call lead
→ Timeline: Immediate
→ Post-incident review: Within 24 hours

**Key Contacts:**

Security Team: security@company.com
Access Support: #production-access (Slack)
Emergency: (555) 0100 (24/7 on-call)
Compliance: compliance@company.com

**Related Documents:**
- DOC-0008: Security Policy
- DOC-0010: Data Access Guidelines
- DOC-0012: Incident Response Procedures
""",
        "url": "https://company.sharepoint.com/sites/Security/Production-Access",
        "category": "security"
    },
    {
        "doc_id": "DOC-0003",
        "title": "Always On Availability Groups Setup Guide",
        "description": """
Document: SQL Server Always On Configuration
Last Updated: 2024-09-10
Owner: Database Team

**Prerequisites:**

Before configuring Always On:
☑ Windows Server Failover Cluster (WSFC) configured
☑ SQL Server Enterprise Edition on all nodes
☑ Same SQL Server version on all replicas
☑ Database in FULL recovery model
☑ Network connectivity between nodes
☑ Service accounts configured with proper permissions
☑ Shared storage OR distributed availability group

**Step-by-Step Setup:**

**1. Enable Always On Feature**
```powershell
# On each SQL Server instance
Enable-SqlAlwaysOn -ServerInstance 'SQLPROD01' -Force

# Restart SQL Server service
Restart-Service MSSQLSERVER
```

**2. Create Availability Group**
```sql
-- On primary replica
CREATE AVAILABILITY GROUP AG_ProductionDB
FOR DATABASE [CustomerDB], [OrdersDB], [InventoryDB]
REPLICA ON
  -- Primary Replica (SQLPROD01)
  'SQLPROD01' WITH (
    ENDPOINT_URL = 'TCP://SQLPROD01.company.local:5022',
    AVAILABILITY_MODE = SYNCHRONOUS_COMMIT,
    FAILOVER_MODE = AUTOMATIC,
    SESSION_TIMEOUT = 10,
    PRIMARY_ROLE(ALLOW_CONNECTIONS = ALL),
    SECONDARY_ROLE(ALLOW_CONNECTIONS = READ_ONLY)
  ),
  
  -- Secondary Replica (SQLPROD02)
  'SQLPROD02' WITH (
    ENDPOINT_URL = 'TCP://SQLPROD02.company.local:5022',
    AVAILABILITY_MODE = SYNCHRONOUS_COMMIT,
    FAILOVER_MODE = AUTOMATIC,
    SESSION_TIMEOUT = 10,
    SECONDARY_ROLE(ALLOW_CONNECTIONS = READ_ONLY)
  ),
  
  -- DR Replica (SQLDR01)
  'SQLDR01' WITH (
    ENDPOINT_URL = 'TCP://SQLDR01.company.local:5022',
    AVAILABILITY_MODE = ASYNCHRONOUS_COMMIT,
    FAILOVER_MODE = MANUAL,
    SESSION_TIMEOUT = 30,
    SECONDARY_ROLE(ALLOW_CONNECTIONS = READ_ONLY)
  );
GO
```

**3. Create Listener**
```sql
ALTER AVAILABILITY GROUP AG_ProductionDB
ADD LISTENER 'AG-Prod-Listener' (
  WITH IP ((N'10.10.1.100', N'255.255.255.0')),
  PORT = 1433
);
GO
```

**4. Join Secondary Replicas**
```sql
-- On SQLPROD02 and SQLDR01
ALTER AVAILABILITY GROUP AG_ProductionDB JOIN;
GO

-- Join databases
ALTER DATABASE [CustomerDB] SET HADR AVAILABILITY GROUP = AG_ProductionDB;
ALTER DATABASE [OrdersDB] SET HADR AVAILABILITY GROUP = AG_ProductionDB;
ALTER DATABASE [InventoryDB] SET HADR AVAILABILITY GROUP = AG_ProductionDB;
GO
```

**Monitoring:**
```sql
-- Check AG health
SELECT 
  ag.name AS AGName,
  ar.replica_server_name AS ReplicaServer,
  ar.availability_mode_desc AS AvailabilityMode,
  ar.failover_mode_desc AS FailoverMode,
  ars.role_desc AS CurrentRole,
  ars.operational_state_desc AS State,
  ars.synchronization_health_desc AS SyncHealth
FROM sys.availability_groups ag
JOIN sys.availability_replicas ar ON ag.group_id = ar.group_id
JOIN sys.dm_hadr_availability_replica_states ars ON ar.replica_id = ars.replica_id;

-- Check replication lag
SELECT 
  ar.replica_server_name,
  db_name(database_id) AS DatabaseName,
  drs.log_send_queue_size AS LogSendQueue_KB,
  drs.redo_queue_size AS RedoQueue_KB,
  drs.last_commit_time
FROM sys.dm_hadr_database_replica_states drs
JOIN sys.availability_replicas ar ON drs.replica_id = ar.replica_id;
```

**Common Configuration:**

Synchronous Commit (In Data Center):
- Use for automatic failover
- Near-zero data loss (RPO ~ 0)
- Network latency < 5ms required

Asynchronous Commit (DR Site):
- Use for geographic redundancy
- Manual failover only
- Network latency tolerant (works with 50ms+)
- RPO depends on replication lag

**Backup Strategy:**

With Always On:
- Backup on secondary replica (offload primary)
- Configure backup priority:
```sql
ALTER AVAILABILITY GROUP AG_ProductionDB
MODIFY REPLICA ON 'SQLPROD02' WITH (BACKUP_PRIORITY = 90);
-- Primary will backup only if secondary unavailable
```

**Failover:**

Automatic Failover (synchronous only):
- Happens automatically on primary failure
- Application connection string uses listener
- Minimal downtime (5-15 seconds)

Manual Failover:
```sql
-- On target secondary replica
ALTER AVAILABILITY GROUP AG_ProductionDB FAILOVER;
```

**Best Practices:**

✓ Use listener for application connections
✓ Monitor replication lag (alert at 30 seconds)
✓ Regular failover testing (quarterly)
✓ Document failover runbook
✓ Configure alerts for synchronization issues
✓ Use readable secondaries for reporting
✓ Offload backups to secondary replica

**Troubleshooting:**

Issue: Synchronization Lag
- Check network latency between sites
- Review large transaction activity
- Check IO subsystem performance

Issue: Automatic Failover Not Working
- Verify SYNCHRONOUS_COMMIT mode
- Check WSFC quorum health
- Validate network connectivity

Issue: Cannot Connect via Listener
- Verify listener IP reachable
- Check DNS resolution
- Review firewall rules (port 1433)

**Related Documents:**
- DOC-0001: DR Environment Architecture
- DOC-0004: Backup and Recovery Guide
- DOC-0007: DR Failover Procedure
""",
        "url": "https://company.sharepoint.com/sites/DBA/AlwaysOn-Setup",
        "category": "setup-guide"
    },
    {
        "doc_id": "DOC-0004",
        "title": "Database Backup and Recovery Strategy",
        "description": """
Document: Backup & Recovery Procedures
Last Updated: 2024-11-01
Owner: Database Team

**Backup Schedule:**

**Production Databases:**

Full Backups:
- Frequency: Daily at 2 AM EST
- Retention: 30 days on-site, 90 days off-site
- Location: \\BACKUP01\SQLBackups\Full\
- Cloud: Azure Blob Storage (cool tier)

Differential Backups:
- Frequency: Every 6 hours (8 AM, 2 PM, 8 PM)
- Retention: 7 days
- Location: \\BACKUP01\SQLBackups\Diff\

Transaction Log Backups:
- Frequency: Every 15 minutes
- Retention: 7 days
- Location: \\BACKUP01\SQLBackups\TLog\
- Critical: Ensures < 15 min RPO

**Backup Script:**
```sql
-- Full Backup
BACKUP DATABASE [CustomerDB]
TO DISK = '\\BACKUP01\SQLBackups\Full\CustomerDB_FULL_20241215.bak'
WITH COMPRESSION, 
     CHECKSUM,
     STATS = 10,
     COPY_ONLY; -- For AG environments

-- Differential Backup
BACKUP DATABASE [CustomerDB]
TO DISK = '\\BACKUP01\SQLBackups\Diff\CustomerDB_DIFF_20241215_1400.bak'
WITH DIFFERENTIAL, COMPRESSION, CHECKSUM;

-- Transaction Log Backup
BACKUP LOG [CustomerDB]
TO DISK = '\\BACKUP01\SQLBackups\TLog\CustomerDB_LOG_20241215_140015.trn'
WITH COMPRESSION, CHECKSUM;
```

**Backup Validation:**

Automated daily checks:
```sql
-- Verify backup integrity
RESTORE VERIFYONLY 
FROM DISK = '\\BACKUP01\SQLBackups\Full\CustomerDB_FULL_20241215.bak'
WITH CHECKSUM;

-- Check backup history
SELECT 
  database_name,
  backup_start_date,
  backup_finish_date,
  DATEDIFF(MINUTE, backup_start_date, backup_finish_date) AS Duration_Minutes,
  backup_size / 1024 / 1024 AS Size_MB,
  compressed_backup_size / 1024 / 1024 AS Compressed_MB
FROM msdb.dbo.backupset
WHERE backup_start_date >= DATEADD(DAY, -7, GETDATE())
ORDER BY backup_start_date DESC;
```

**Recovery Scenarios:**

**Scenario 1: Full Database Recovery**
```sql
-- 1. Put database in single-user mode
ALTER DATABASE CustomerDB SET SINGLE_USER WITH ROLLBACK IMMEDIATE;

-- 2. Restore full backup
RESTORE DATABASE CustomerDB
FROM DISK = '\\BACKUP01\SQLBackups\Full\CustomerDB_FULL_20241215.bak'
WITH NORECOVERY, REPLACE;

-- 3. Restore differential (if available)
RESTORE DATABASE CustomerDB  
FROM DISK = '\\BACKUP01\SQLBackups\Diff\CustomerDB_DIFF_20241215_1400.bak'
WITH NORECOVERY;

-- 4. Restore transaction logs
RESTORE LOG CustomerDB
FROM DISK = '\\BACKUP01\SQLBackups\TLog\CustomerDB_LOG_20241215_140015.trn'
WITH NORECOVERY;

-- (Repeat for all logs up to desired point)

-- 5. Bring database online
RESTORE DATABASE CustomerDB WITH RECOVERY;

-- 6. Set to multi-user
ALTER DATABASE CustomerDB SET MULTI_USER;
```

**Scenario 2: Point-in-Time Recovery**
```sql
-- Restore to specific time: 2024-12-15 14:30:00
RESTORE DATABASE CustomerDB
FROM DISK = '\\BACKUP01\SQLBackups\Full\CustomerDB_FULL_20241215.bak'
WITH NORECOVERY, REPLACE;

RESTORE LOG CustomerDB
FROM DISK = '\\BACKUP01\SQLBackups\TLog\CustomerDB_LOG_20241215_140015.trn'
WITH NORECOVERY, STOPAT = '2024-12-15 14:30:00';

RESTORE DATABASE CustomerDB WITH RECOVERY;
```

**Scenario 3: Single Table Recovery**

Using third-party tool (Redgate SQL Backup):
```
1. Restore database to temp location
2. Export specific table data
3. Import into production database
4. Validate data integrity
```

**RPO/RTO Targets:**

| Database Tier | RPO | RTO | Strategy |
|---------------|-----|-----|----------|
| Tier 1 (Critical) | 15 min | 30 min | Always On + Log backups every 15 min |
| Tier 2 (Important) | 1 hour | 2 hours | Full + Diff + Log every hour |
| Tier 3 (Standard) | 24 hours | 4 hours | Full daily + Diff 6-hourly |

**Backup Monitoring:**

Alerts configured for:
✗ Backup failure
✗ Backup duration > 2x baseline
✗ Backup older than 36 hours
✗ Backup restore test failure
✗ Low disk space on backup drive (< 20%)

**Offsite Backup:**

Azure Blob Storage sync:
- Syncs nightly at 4 AM
- Encrypted in transit (TLS 1.3)
- Encrypted at rest (AES-256)
- Immutable storage (WORM) for compliance
- Cost: ~$200/month (50TB compressed)

**Backup Testing:**

Weekly: Automated restore test on DEV
Monthly: Full restore drill to isolated environment
Quarterly: DR failover test with full restore

**Tools:**

Backup: SQL Server native + Ola Hallengren scripts
Monitoring: SQL Sentry
Offsite: Azure Backup
Verification: Ola Hallengren maintenance solution

**Related Documents:**
- DOC-0007: DR Failover Procedure
- DOC-0003: Always On Setup
- DOC-0013: Recovery Time Matrix
""",
        "url": "https://company.sharepoint.com/sites/DBA/Backup-Recovery",
        "category": "process"
    },
    {
        "doc_id": "DOC-0006",
        "title": "SQL Server Performance Troubleshooting Runbook",
        "description": """
Document: Performance Troubleshooting Steps
Last Updated: 2024-12-10
Owner: Database Performance Team

**When to Use This Runbook:**
- CPU > 80% for 5+ minutes
- Query response times > 3x baseline
- Application timeout errors
- User reports of slowness

**Step 1: Quick Health Check (2 minutes)**
```sql
-- Check current activity
EXEC sp_whoisactive 
  @get_plans = 1,
  @get_locks = 1,
  @find_block_leaders = 1;

-- Check wait stats
SELECT TOP 10 
  wait_type,
  wait_time_ms / 1000.0 AS wait_time_sec,
  waiting_tasks_count
FROM sys.dm_os_wait_stats
WHERE wait_type NOT IN (
  'CLR_SEMAPHORE', 'LAZYWRITER_SLEEP', 'RESOURCE_QUEUE', 
  'SLEEP_TASK', 'SLEEP_SYSTEMTASK', 'SQLTRACE_BUFFER_FLUSH', 'WAITFOR'
)
ORDER BY wait_time_ms DESC;

-- Check CPU usage
SELECT 
  SQLProcessUtilization AS SQL_CPU,
  SystemIdle,
  100 - SystemIdle - SQLProcessUtilization AS Other_Process_CPU
FROM (
  SELECT TOP 1
    record.value('(./Record/@id)[1]', 'int') AS record_id,
    record.value('(./Record/SchedulerMonitorEvent/SystemHealth/SystemIdle)[1]', 'int') AS SystemIdle,
    record.value('(./Record/SchedulerMonitorEvent/SystemHealth/ProcessUtilization)[1]', 'int') AS SQLProcessUtilization
  FROM (
    SELECT CAST(record AS XML) AS record
    FROM sys.dm_os_ring_buffers
    WHERE ring_buffer_type = N'RING_BUFFER_SCHEDULER_MONITOR'
  ) AS x
  ORDER BY record_id DESC
) AS y;
```

**Step 2: Identify Root Cause**

**Symptom: High CPU**

Check for:
```sql
-- Find expensive queries
SELECT TOP 5
  qs.execution_count,
  qs.total_worker_time / 1000 AS total_cpu_ms,
  qs.total_worker_time / qs.execution_count / 1000 AS avg_cpu_ms,
  SUBSTRING(qt.text, (qs.statement_start_offset/2)+1,
    ((CASE qs.statement_end_offset
      WHEN -1 THEN DATALENGTH(qt.text)
      ELSE qs.statement_end_offset
    END - qs.statement_start_offset)/2) + 1) AS query_text
FROM sys.dm_exec_query_stats qs
CROSS APPLY sys.dm_exec_sql_text(qs.sql_handle) qt
ORDER BY qs.total_worker_time DESC;
```

Common causes:
- Missing indexes (table scans)
- Parameter sniffing
- Statistics out of date
- Parallelism issues

**Symptom: Blocking**
```sql
-- Find blocking chain
SELECT 
  SPID = er.session_id,
  Status = ses.status,
  [Login] = ses.login_name,
  Host = ses.host_name,
  BlkBy = er.blocking_session_id,
  DBName = DB_Name(er.database_id),
  CommandType = er.command,
  ObjectName = OBJECT_NAME(st.objectid),
  SQLStatement = st.text,
  ElapsedMS = er.total_elapsed_time,
  CPUTime = er.cpu_time,
  IOReads = er.logical_reads + er.reads,
  IOWrites = er.writes
FROM sys.dm_exec_requests er
INNER JOIN sys.dm_exec_sessions ses ON er.session_id = ses.session_id
CROSS APPLY sys.dm_exec_sql_text(er.sql_handle) st
WHERE er.blocking_session_id <> 0
   OR er.session_id IN (SELECT blocking_session_id 
                        FROM sys.dm_exec_requests 
                        WHERE blocking_session_id <> 0);
```

**Symptom: Memory Pressure**
```sql
-- Check memory clerks
SELECT TOP 10
  type AS ClerkType,
  SUM(pages_kb) / 1024 AS Size_MB
FROM sys.dm_os_memory_clerks
GROUP BY type
ORDER BY SUM(pages_kb) DESC;

-- Check buffer pool usage
SELECT 
  DB_NAME(database_id) AS DatabaseName,
  COUNT(*) * 8 / 1024 AS Size_MB
FROM sys.dm_os_buffer_descriptors
GROUP BY database_id
ORDER BY COUNT(*) DESC;
```

**Step 3: Immediate Actions**

**For High CPU from Missing Index:**
```sql
-- Find missing index recommendations
SELECT 
  mid.statement AS TableName,
  migs.avg_user_impact AS AvgImpact,
  migs.user_seeks AS Seeks,
  'CREATE INDEX IX_' + 
    REPLACE(REPLACE(mid.statement, '[', ''), ']', '') + 
    '_' + REPLACE(REPLACE(ISNULL(mid.equality_columns, ''), ', ', '_'), '[', '')
    + ' ON ' + mid.statement +
    ' (' + ISNULL(mid.equality_columns, '') + 
    ISNULL(', ' + mid.inequality_columns, '') + ')' +
    ISNULL(' INCLUDE (' + mid.included_columns + ')', '') AS CreateIndexSQL
FROM sys.dm_db_missing_index_details mid
INNER JOIN sys.dm_db_missing_index_groups mig ON mid.index_handle = mig.index_handle
INNER JOIN sys.dm_db_missing_index_group_stats migs ON mig.index_group_handle = migs.group_handle
WHERE migs.avg_user_impact > 50
  AND migs.user_seeks > 100
ORDER BY migs.avg_user_impact DESC;
```

**For Blocking:**
```sql
-- Kill blocking session (AFTER approval!)
-- KILL <session_id>;

-- Or wait for it to complete
```

**For Memory Pressure:**
```sql
-- Clear procedure cache (CAUTION!)
DBCC FREEPROCCACHE;

-- Or clear for specific database
DBCC FREEPROCCACHE WITH NO_INFOMSGS;
```

**Step 4: Long-Term Solutions**

✓ Index optimization
✓ Query rewriting
✓ Statistics update
✓ Parameter sniffing mitigation (OPTION RECOMPILE)
✓ Hardware upgrade (if resource constrained)

**Escalation:**

Escalate if:
- Cannot identify root cause in 15 minutes
- Issue requires code changes
- Requires infrastructure changes
- Impacts multiple systems

Contact: #dba-oncall (Slack) or page DBA lead

**Post-Incident:**
- Document findings in ServiceNow incident
- Update runbook if new scenario encountered
- Implement preventive measures

**Related Documents:**
- INC-History: Past performance incidents
- DOC-0009: Index Maintenance Guide
- DOC-0010: Query Tuning Standards
""",
        "url": "https://company.sharepoint.com/sites/DBA/Performance-Troubleshooting",
        "category": "runbook"
    },
    {
        "doc_id": "DOC-0007",
        "title": "Disaster Recovery Failover Procedure",
        "description": """
Document: DR Failover Runbook
Last Updated: 2024-11-25
Owner: Infrastructure & Database Teams

**⚠️ CRITICAL: This procedure fails over production to DR site**

**When to Execute:**
- Primary data center complete outage
- Network failure preventing access to primary
- Catastrophic failure of primary infrastructure
- Approved DR drill

**Decision Authority:**
- Business Hours: VP Engineering + CTO
- After Hours: On-call Infrastructure Lead + DBA Lead

**Pre-Failover Checklist:**

☑ Confirm primary site is truly down (not network issue)
☑ Verify DR site health (all green)
☑ Conference bridge active (all teams joined)
☑ Communication sent to:
  - Executive team
  - All engineering teams  
  - Customer support
  - External status page updated
☑ Approvals documented in #dr-failover Slack channel

**Estimated Time: 20-30 minutes**

**Failover Steps:**

**Phase 1: Preparation (5 min)**
```powershell
# 1. Join conference bridge
# Dial: (555) 0123, Code: 789456

# 2. Confirm all teams present:
- Infrastructure Lead
- DBA Lead
- Application Lead
- Network Lead
- Security Lead

# 3. Assign roles:
- Coordinator: Infrastructure Lead
- DBA: Primary DBA on-call
- Network: Network engineer
- Comms: Engineering manager
```

**Phase 2: Database Failover (10 min)**
```sql
-- On DR SQL Server (SQLDR01)

-- 1. Check replication status
SELECT 
  ar.replica_server_name,
  drs.synchronization_state_desc,
  drs.synchronization_health_desc,
  drs.log_send_queue_size,
  drs.redo_queue_size
FROM sys.dm_hadr_database_replica_states drs
JOIN sys.availability_replicas ar ON drs.replica_id = ar.replica_id;

-- 2. Force failover (data loss possible!)
ALTER AVAILABILITY GROUP AG_ProductionDB FORCE_FAILOVER_ALLOW_DATA_LOSS;

-- 3. Verify DR is now primary
SELECT 
  ag.name,
  ar.replica_server_name,
  ars.role_desc
FROM sys.availability_groups ag
JOIN sys.availability_replicas ar ON ag.group_id = ar.group_id
JOIN sys.dm_hadr_availability_replica_states ars ON ar.replica_id = ars.replica_id;
-- Should show SQLDR01 as PRIMARY

-- 4. Set databases to READ_WRITE if needed
ALTER DATABASE CustomerDB SET READ_WRITE;
ALTER DATABASE OrdersDB SET READ_WRITE;
```

**Phase 3: DNS and Network (5 min)**
```powershell
# 1. Update DNS to point to DR listener
# (Automated via Rundeck job)
./rundeck-job.ps1 -Job "DR-DNS-Failover" -Approve $true

# 2. Verify DNS propagation
nslookup PROD-SQL-Listener.company.com
# Should return DR site IP: 10.20.1.100

# 3. Test connectivity
Test-NetConnection -ComputerName PROD-SQL-Listener.company.com -Port 1433
```

**Phase 4: Application Validation (10 min)**
```
1. Application servers automatically reconnect
   - Connection pooling handles failover
   - Applications should recover in 30-60 seconds

2. Smoke tests:
   ☑ Login to application
   ☑ Create test order
   ☑ Run critical reports
   ☑ Verify data integrity

3. Monitor application logs:
   - Check for connection errors
   - Verify queries executing normally

4. Load testing (if time permits):
   - Simulate normal traffic
   - Verify performance acceptable
```

**Phase 5: Communication**
```
# Internal (Slack #engineering-all):
"✅ DR Failover Complete
- Database: Failed over to Phoenix DR
- Status: All systems operational
- Applications: Reconnected successfully  
- Next: Monitoring for 1 hour
- Expected primary restoration: TBD"

# External (status.company.com):
"Systems have been restored. All services operational. 
We are operating from our disaster recovery site."

# Customer Support:
"DR failover successful. Customers can resume normal operations."
```

**Post-Failover Monitoring (1 hour)**

Monitor:
- Application performance (Datadog)
- Database performance (sp_whoisactive every 5 min)
- Error rates (must be < baseline +5%)
- Network latency between DR and office
- User feedback (#customer-support channel)

**Rollback Procedure:**

When primary site restored:
```sql
-- 1. Verify primary site healthy
-- 2. Synchronize databases (may take hours for large databases)
-- 3. Plan maintenance window
-- 4. Fail back to primary:

ALTER AVAILABILITY GROUP AG_ProductionDB FAILOVER;

-- 5. Update DNS back to primary
-- 6. Verify applications reconnected
```

**Estimated Rollback Time: 4-8 hours**
(Depends on data to re-sync)

**Testing Schedule:**

Quarterly DR drills:
- Q1: Database failover only
- Q2: Full DR failover (non-business hours)
- Q3: Database failover only
- Q4: Full DR failover + rollback

**Key Contacts:**

**Primary:**
- Infrastructure Lead: Mike Chen (mike.chen@company.com) (555) 0101
- DBA Lead: Sarah Johnson (sarah.j@company.com) (555) 0102
- Network Lead: Alex Rodriguez (alex.r@company.com) (555) 0103

**Backup (if primary unavailable):**
- VP Engineering: (555) 0100
- CTO: (555) 0099

**Conference Bridge:** (555) 0123, Code: 789456

**Lessons Learned from Past Drills:**

2024-Q2: DNS propagation took 10 minutes (expected 2 min)
  → Fixed: Pre-cache DNS on all app servers

2024-Q4: Application connection strings hardcoded to primary
  → Fixed: Updated to use listener name

**Related Documents:**
- DOC-0001: DR Architecture
- DOC-0003: Always On Setup
- DOC-0011: Communication Templates
- DOC-0014: Post-Incident Review Template
""",
        "url": "https://company.sharepoint.com/sites/DBA/DR-Failover",
        "category": "runbook"
    }
]

def store_runbook(runbook_data):
    """Store runbook in database"""
    
    conn = psycopg2.connect(
        host=os.getenv('DB_HOST'),
        database=os.getenv('DB_NAME'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        port=os.getenv('DB_PORT')
    )
    register_vector(conn)
    cur = conn.cursor()
    
    # Check if exists
    cur.execute("SELECT id FROM sql_docs WHERE url = %s", (runbook_data['url'],))
    if cur.fetchone():
        cur.close()
        conn.close()
        return False
    
    # Generate embedding
    text = f"{runbook_data['title']} {runbook_data['description']}"
    embedding = model.encode(text).tolist()
    
    # Insert
    cur.execute("""
        INSERT INTO sql_docs (title, content, url, embedding, source, created_at)
        VALUES (%s, %s, %s, %s, %s, NOW())
    """, (
        runbook_data['title'],
        runbook_data['description'],
        runbook_data['url'],
        embedding,
        'documentation'  # New source type
    ))
    
    conn.commit()
    cur.close()
    conn.close()
    return True

def main():
    print("="*70)
    print("  Loading Runbooks & Documentation")
    print("="*70)
    print()
    
    successful = 0
    skipped = 0
    
    for runbook in MOCK_RUNBOOKS:
        doc_id = runbook['doc_id']
        title = runbook['title'][:60] + "..."
        print(f"Processing: {doc_id}")
        print(f"  {title}")
        
        if store_runbook(runbook):
            print(f"  ✅ Stored\n")
            successful += 1
        else:
            print(f"  ⏭️  Already exists\n")
            skipped += 1
    
    print("="*70)
    print(f"  ✅ Successfully added: {successful}")
    print(f"  ⏭️  Already existed: {skipped}")
    print("="*70)
    
    # Show final counts
    conn = psycopg2.connect(
        host=os.getenv('DB_HOST'),
        database=os.getenv('DB_NAME'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        port=os.getenv('DB_PORT')
    )
    cur = conn.cursor()
    cur.execute("SELECT source, COUNT(*) FROM sql_docs GROUP BY source ORDER BY source")
    print("\nDatabase contents:")
    for source, count in cur.fetchall():
        print(f"  {source}: {count} documents")
    cur.close()
    conn.close()

if __name__ == "__main__":
    main()