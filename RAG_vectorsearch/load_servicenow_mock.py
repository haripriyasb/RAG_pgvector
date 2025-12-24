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

# Mock ServiceNow incidents (realistic DBA scenarios)
MOCK_INCIDENTS = [
    {
        "number": "INC0012345",
        "title": "[INC0012345] SQL Server high CPU - production database",
        "description": """
Incident: Production SQL Server CPU spiked to 98% at 2:15 AM
Affected: SQLPROD01, customer_db database
Symptoms: Query timeouts, slow page loads, 503 errors
Duration: 45 minutes

Root Cause Analysis:
Missing index on Orders table causing table scans on high-volume query.
Query: SELECT * FROM Orders WHERE OrderDate > @date AND CustomerID = @id
Execution plan showed 15M row table scan on every execution (500 times/min during peak).

Resolution:
1. Created covering index: CREATE INDEX IX_Orders_Date_Customer ON Orders(OrderDate, CustomerID) INCLUDE (OrderTotal, Status)
2. Query time: 8 seconds → 50ms
3. CPU normalized to 25%
4. Monitored for 2 hours, no recurrence

Prevention:
- Added this query pattern to code review checklist
- Implemented query store alerts for regression
- Created runbook for similar index-related CPU spikes

Related Incidents: INC0011234 (similar pattern 3 months ago)
""",
        "resolved_date": "2024-11-15",
        "url": "https://company.service-now.com/incident.do?sys_id=12345"
    },
    {
        "number": "INC0012456",
        "title": "[INC0012456] TempDB full - blocking all transactions",
        "description": """
Incident: TempDB database filled to 100%, all transactions blocked
Affected: SQLPROD02, all databases on instance
Symptoms: Complete database freeze, all queries hanging, application down
Duration: 25 minutes

Root Cause Analysis:
Long-running transaction held version store open, preventing tempdb cleanup.
Transaction: ETL job from DataWarehouse team running for 8 hours with RCSI enabled.
Version store grew from 2GB to 180GB (tempdb max size: 200GB).

Resolution:
1. Identified blocking transaction: DBCC OPENTRAN
2. Killed session 1847 (ETL job) - coordinated with DataWarehouse team
3. TempDB auto-shrunk within 5 minutes
4. Restarted ETL with smaller batches

Prevention:
- Set query timeout on ETL jobs: 2 hours max
- Implemented tempdb size monitoring (alert at 80%)
- Created version store monitoring dashboard
- Added tempdb sizing to capacity planning

Related Incidents: INC0010987, INC0011456 (tempdb issues)
""",
        "resolved_date": "2024-10-22",
        "url": "https://company.service-now.com/incident.do?sys_id=12456"
    },
    {
        "number": "INC0012567",
        "title": "[INC0012567] Deadlock storm causing transaction failures",
        "description": """
Incident: Massive deadlock storm (200+ deadlocks/minute) causing order processing failures
Affected: SQLPROD01, orders_db
Symptoms: Failed transactions, duplicate order attempts, customer complaints
Duration: 90 minutes

Root Cause Analysis:
Two competing processes accessing same tables in different order:
- Order creation: locks Orders → OrderItems → Inventory
- Inventory update: locks Inventory → OrderItems → Orders
During Black Friday traffic (10x normal), race condition triggered constant deadlocks.

Resolution:
1. Identified deadlock pattern using extended events
2. Temporarily disabled inventory auto-update job
3. Modified order creation proc to use same lock order as inventory update
4. Added NOLOCK hints where appropriate
5. Implemented retry logic in application

Prevention:
- Standardized lock ordering across all procedures
- Load testing before high-traffic events
- Implemented deadlock monitoring/alerting
- Created Black Friday runbook

Related Incidents: INC0009876 (deadlocks during last Black Friday)
""",
        "resolved_date": "2024-11-28",
        "url": "https://company.service-now.com/incident.do?sys_id=12567"
    },
    {
        "number": "INC0012678",
        "title": "[INC0012678] Always On failover - primary node unresponsive",
        "description": """
Incident: Primary SQL Server node became unresponsive, automatic failover to secondary
Affected: SQLPROD03, Availability Group AG01
Symptoms: 30-second application outage during failover, some transaction rollbacks
Duration: Failover: 30 seconds, Investigation: 3 hours

Root Cause Analysis:
Windows Update auto-installed during maintenance window, but server didn't reboot cleanly.
SQL Server service hung during shutdown, cluster detected failure, initiated failover.
Post-failover investigation showed hung LSASS process requiring hard reboot.

Resolution:
1. Automatic failover completed successfully
2. Investigated primary node (now secondary)
3. Hard rebooted primary node
4. Rejoined to AG after restart
5. Resynchronized databases (1.2TB, took 45 minutes)
6. Failed back to primary during next maintenance window

Prevention:
- Disabled Windows auto-update on SQL servers
- Implemented manual patching schedule
- Enhanced AG monitoring for failover events
- Updated runbook for AG troubleshooting
- Conducted AG disaster recovery drill

Related Incidents: INC0010234 (previous AG failover)
""",
        "resolved_date": "2024-12-01",
        "url": "https://company.service-now.com/incident.do?sys_id=12678"
    },
    {
        "number": "INC0012789",
        "title": "[INC0012789] Memory pressure - SQL Server using 100% RAM",
        "description": """
Incident: SQL Server consuming all available memory, causing OS instability
Affected: SQLPROD04
Symptoms: Slow queries, system instability, excessive paging
Duration: 2 hours

Root Cause Analysis:
SQL Server max memory not configured, defaulted to unlimited.
After database restore (2TB), buffer pool grew to consume all 256GB RAM.
Left only 2GB for OS, causing excessive paging and instability.

Resolution:
1. Set max server memory to 240GB (leaving 16GB for OS)
2. Restarted SQL Server service to release memory
3. System stabilized within 15 minutes

Prevention:
- Audited all SQL Servers for max memory configuration
- Standardized: Leave 16GB or 10% (whichever larger) for OS
- Added memory monitoring to standard checks
- Updated server build documentation

Related Incidents: INC0008765 (similar on SQLPROD07)
""",
        "resolved_date": "2024-09-18",
        "url": "https://company.service-now.com/incident.do?sys_id=12789"
    },
    {
        "number": "INC0012890",
        "title": "[INC0012890] Transaction log full - cannot process transactions",
        "description": """
Incident: Transaction log filled, blocking all writes to database
Affected: SQLPROD01, reporting_db
Symptoms: Insert/update/delete failures, ETL jobs failing, reports stale
Duration: 1 hour

Root Cause Analysis:
Transaction log backups disabled after migration to new backup solution.
Database in FULL recovery model but log never backed up.
Log grew from 10GB to max size (100GB) over 3 weeks.

Resolution:
1. Performed emergency log backup to free space
2. Configured transaction log backups (every 15 minutes)
3. Reviewed all databases for backup configuration
4. Identified 3 more databases with same issue, fixed proactively

Prevention:
- Created backup monitoring dashboard
- Automated alerts for log growth
- Quarterly backup validation process
- Updated migration checklist to verify backups

Related Incidents: INC0007654 (log full on different database)
""",
        "resolved_date": "2024-10-05",
        "url": "https://company.service-now.com/incident.do?sys_id=12890"
    },
    {
        "number": "PRB0001234",
        "title": "[PRB0001234] Recurring TempDB growth issues - Problem Task",
        "description": """
Problem Task: Pattern of tempdb filling on multiple servers over 6 months

Incidents Linked: INC0010987, INC0011456, INC0012456 (6 total tempdb incidents)

Pattern Analysis:
- All occurred between 10 PM - 2 AM
- All involved long-running ETL processes
- All on servers with RCSI enabled
- Version store growth was primary cause in 4 of 6 cases

Root Cause:
RCSI version store sizing not accounted for in tempdb capacity planning.
ETL jobs running with open transactions for hours, preventing cleanup.
Tempdb sized for non-RCSI workloads (50GB), needed 200GB+ for version store.

Permanent Solution Implemented:
1. Resized tempdb on all RCSI-enabled servers (50GB → 250GB)
2. Implemented version store monitoring (alert at 150GB)
3. Added transaction timeout to all ETL jobs (2 hour max)
4. Modified ETL to use smaller batches with COMMIT
5. Created dashboard showing version store trends
6. Updated capacity planning to include RCSI overhead

Results:
- Zero tempdb incidents in 2 months since implementation
- Average version store size: 80GB (well below threshold)
- ETL jobs complete successfully with batching

Documentation:
- Runbook: "TempDB Troubleshooting Guide"
- Dashboard: "TempDB & Version Store Monitoring"
- Standard: "RCSI Capacity Planning"
""",
        "resolved_date": "2024-11-30",
        "url": "https://company.service-now.com/problem.do?sys_id=1234"
    },

{
        "number": "INC0012991",
        "title": "[INC0012991] Blocking chain causing order processing delays",
        "description": """
Incident: Multiple blocked sessions causing 5+ minute order processing delays
Affected: SQLPROD01, orders_db
Symptoms: Orders timing out, users reporting "processing" status stuck
Duration: 75 minutes

Root Cause Analysis:
Long-running report query (25+ minutes) holding shared locks on Orders table.
Report ran during peak order processing hours (12 PM - 1 PM lunch rush).
Blocking chain: Session 892 (report) blocked 45 order processing sessions.

Blocking Details:
- Head blocker: Session 892 running inventory report
- Query: SELECT * FROM Orders JOIN OrderItems (no WHERE clause!)
- Lock type: Shared locks (S) preventing updates
- Blocked sessions: 45 order entry processes waiting

Resolution:
1. Identified blocking using sp_whoisactive
2. Killed session 892 (report query) after business approval
3. All blocked sessions completed within 2 minutes
4. Moved report to read-only secondary replica

Prevention:
- All long-running reports moved to AG secondary replica
- Implemented query timeout for all reports (5 min max)
- Added blocking alerts (> 10 blocked sessions)
- Created "Blocking Chain Investigation" runbook

Related Incidents: INC0009123 (blocking during month-end close)
""",
        "resolved_date": "2024-11-10",
        "url": "https://company.service-now.com/incident.do?sys_id=12991"
    },
    {
        "number": "INC0013102",
        "title": "[INC0013102] Index fragmentation causing query degradation",
        "description": """
Incident: Critical queries running 10x slower than baseline
Affected: SQLPROD05, warehouse_db
Symptoms: Report generation taking 2 hours instead of 12 minutes
Duration: Ongoing for 3 days before escalation

Root Cause Analysis:
Severe index fragmentation on large fact tables (500M+ rows).
Fragmentation levels: 85-95% on all nonclustered indexes.
Index maintenance job had been disabled 4 months ago during migration.

Impact Details:
- Key query: Inventory summary report
- Normal execution: 12 minutes
- Degraded performance: 2+ hours
- Execution plan showing excessive logical reads (500M vs 2M)

Resolution:
1. Identified fragmented indexes using sys.dm_db_index_physical_stats
2. Performed emergency index rebuild during maintenance window
3. Queries returned to normal performance
4. Re-enabled weekly index maintenance job

Prevention:
- Weekly index maintenance job (REBUILD if >30% frag, REORGANIZE if >10%)
- Monitoring dashboard for index fragmentation
- Monthly index health review
- Added index maintenance to migration checklist

Related Incidents: None (first occurrence)
""",
        "resolved_date": "2024-09-25",
        "url": "https://company.service-now.com/incident.do?sys_id=13102"
    },
    {
        "number": "INC0013213",
        "title": "[INC0013213] Database backup failure - log chain broken",
        "description": """
Incident: Full backup failed, breaking log backup chain
Affected: SQLPROD02, customers_db (500GB database)
Symptoms: Transaction log growing, log backups failing with error 4214
Duration: 12 hours undetected, 2 hours to resolve after detection

Root Cause Analysis:
Backup drive ran out of space during full backup (needed 520GB, only 480GB free).
Full backup failed at 94% complete, corrupting backup file.
Subsequent log backups failed with "no full backup exists" error.
Transaction log grew from 50GB to 180GB during the 12-hour window.

Alert Gap:
- Backup monitoring alert didn't fire (configured for 48-hour window)
- Disk space alert threshold too high (10% free = 100GB, missed 20GB shortage)

Resolution:
1. Cleared old backup files from backup drive
2. Performed manual full backup (compressed to 380GB)
3. Resumed transaction log backup chain
4. Truncated transaction log after successful log backup

Prevention:
- Reduced backup retention from 30 days to 14 days
- Backup monitoring alert reduced to 24-hour window
- Disk space alert increased to 15% threshold
- Implemented backup compression (40% size reduction)
- Added pre-backup disk space validation script

Related Incidents: INC0010456 (backup failures on different server)
""",
        "resolved_date": "2024-08-30",
        "url": "https://company.service-now.com/incident.do?sys_id=13213"
    },
    {
        "number": "INC0013324",
        "title": "[INC0013324] Replication lag - secondary replica 4 hours behind",
        "description": """
Incident: Always On secondary replica severely lagged behind primary
Affected: SQLPROD03, AG01 secondary replica
Symptoms: Reporting queries showing stale data, dashboard metrics incorrect
Duration: Lag accumulated over 6 hours, 3 hours to catch up

Root Cause Analysis:
Network latency spike between data centers (normal: 2ms, during incident: 150ms).
Large batch update job (50M rows) on primary during network issue.
Synchronous commit mode prevented primary updates, switched to async automatically.
Async mode allowed lag to accumulate without blocking primary.

Lag Details:
- Normal lag: < 5 seconds
- During incident: 4 hours 15 minutes
- Redo queue: 180GB
- Network throughput: Degraded from 10Gbps to 500Mbps

Resolution:
1. Identified network path congestion (faulty switch port)
2. Networking team rerouted traffic through backup path
3. Network restored to normal latency (2ms)
4. Replica caught up within 3 hours after network fix
5. Validated data consistency across replicas

Prevention:
- Implemented replica lag monitoring (alert at 5 minute lag)
- Added network latency monitoring between data centers
- Created runbook for AG lag troubleshooting
- Configured backup network path with automatic failover
- Large batch jobs now run during low-traffic hours

Related Incidents: INC0008901 (network issues affecting AG)
""",
        "resolved_date": "2024-10-15",
        "url": "https://company.service-now.com/incident.do?sys_id=13324"
    },
    {
        "number": "INC0013435",
        "title": "[INC0013435] Disk space full - database cannot grow",
        "description": """
Incident: Database files cannot auto-grow due to disk full
Affected: SQLPROD06, analytics_db
Symptoms: INSERT/UPDATE failures, error 1105 "Could not allocate space"
Duration: 1 hour

Root Cause Analysis:
Analytics database grew faster than projected (50GB/week actual vs 10GB/week projected).
Disk capacity: 2TB total, database grew to 1.95TB.
Auto-growth kicked in, but only 50GB free space remaining.
Database needed 100GB for auto-growth, but disk only had 50GB available.

Growth Analysis:
- Database size: 1.95TB
- Projected monthly growth: 40GB
- Actual growth last month: 200GB (5x projection!)
- Root cause of growth: New customer analytics not in original sizing

Resolution:
1. Identified large tables using sp_spaceused
2. Purged 6 months of archived analytics data (freed 250GB)
3. Database operations resumed
4. Ordered additional storage (4TB expansion)

Prevention:
- Implemented daily disk space monitoring
- Alert at 20% free space (was 10%)
- Created data retention policy (archive after 90 days, purge after 1 year)
- Quarterly capacity planning review
- Automated archival process for old analytics data

Related Incidents: INC0011789 (disk space on SQLPROD04)
""",
        "resolved_date": "2024-12-05",
        "url": "https://company.service-now.com/incident.do?sys_id=13435"
    },
    {
        "number": "INC0013546",
        "title": "[INC0013546] Connection pool exhaustion - application cannot connect",
        "description": """
Incident: Application unable to get database connections, users locked out
Affected: SQLPROD01, customer_db
Symptoms: "Timeout expired" errors, "Max pool size reached", 503 errors
Duration: 30 minutes

Root Cause Analysis:
Connection leak in application code after recent deployment.
New feature didn't properly dispose of database connections.
Connections accumulated: Normal 50-100 active, during incident 950+ active.
SQL Server max connections: 1000 (950 used by leaked connections).

Connection Details:
- Normal active connections: 50-100
- During incident: 950+ connections
- Most connections: Idle with open transactions
- Application: Connection pool max size = 100 per app server
- App servers: 10 servers × 100 = 1000 possible connections

Resolution:
1. Identified connection leak using sp_whoisactive
2. Killed idle sessions with old open transactions (DBCC OPENTRAN)
3. Rolled back deployment to previous version
4. Connections normalized within 5 minutes
5. Dev team fixed connection disposal in code

Prevention:
- Added connection count monitoring (alert at 500 connections)
- Implemented idle session timeout (30 minutes)
- Code review checklist now includes connection disposal check
- Added unit tests for proper connection handling
- Pre-production load testing now includes connection leak testing

Related Incidents: INC0008234 (connection issues after different deployment)
""",
        "resolved_date": "2024-11-20",
        "url": "https://company.service-now.com/incident.do?sys_id=13546"
    },
    {
        "number": "INC0013657",
        "title": "[INC0013657] Parameter sniffing causing intermittent slow queries",
        "description": """
Incident: Critical customer search query fast 90% of time, extremely slow 10% of time
Affected: SQLPROD01, customer_db
Symptoms: Some searches complete in 100ms, others take 45+ seconds
Duration: Intermittent issue over 2 weeks, 4 hours to diagnose and fix

Root Cause Analysis:
Parameter sniffing on customer search stored procedure.
Procedure compiled with parameters for large customer (1M orders).
Plan optimal for large customers, terrible for small customers (< 100 orders).
Plan cache inconsistency: Fast when compiled with small customer params, slow otherwise.

Query Details:
- Stored Proc: usp_GetCustomerOrders
- Parameter: @CustomerID
- Large customers: 1M+ orders, index seek optimal (100ms)
- Small customers: < 100 orders, index seek still used but suboptimal (45 sec!)
- Problem: Plan compiled for large customer used table scan for small customer data

Resolution:
1. Identified parameter sniffing using execution plans
2. Added OPTION (RECOMPILE) hint to problematic query
3. Alternative: Added OPTIMIZE FOR UNKNOWN hint
4. Tested with various customer sizes, all now complete in < 200ms
5. Cleared plan cache to remove bad plans

Prevention:
- Code review now checks for parameter sniffing patterns
- Added plan cache monitoring for frequent recompilations
- Created "Parameter Sniffing" runbook
- Implemented query store for plan regression detection
- Proactive OPTION (RECOMPILE) for queries with wide parameter ranges

Related Incidents: INC0009567 (similar issue on different procedure)
""",
        "resolved_date": "2024-10-01",
        "url": "https://company.service-now.com/incident.do?sys_id=13657"
    },
    {
        "number": "INC0013768",
        "title": "[INC0013768] Statistics out of date causing poor execution plans",
        "description": """
Incident: Key queries suddenly slow after weekend batch processing
Affected: SQLPROD05, warehouse_db
Symptoms: Morning reports taking 3x longer than normal
Duration: 4 hours (entire morning until discovered)

Root Cause Analysis:
Statistics not updated after large weekend data load (500M rows inserted).
Queries using execution plans optimized for pre-load data size.
Statistics showed 100M rows, actual: 600M rows after load.
Query optimizer chose nested loops (optimal for 100M), terrible for 600M rows.

Impact:
- Morning inventory report: 15 min → 45 min
- Customer analytics: 5 min → 18 min
- Sales dashboard refresh: 2 min → 9 min
- All queries showed "Estimated rows: 100M, Actual rows: 600M"

Resolution:
1. Identified stale statistics using DBCC SHOW_STATISTICS
2. Updated statistics on affected tables: UPDATE STATISTICS WITH FULLSCAN
3. Plans recompiled with accurate statistics
4. Queries returned to normal performance within minutes

Prevention:
- Modified ETL job to update statistics after large data loads
- Automated statistics update job: Daily for tables > 1M rows
- Monitoring for statistics age (alert if > 7 days since update)
- Added auto-update stats asynchronously: ON
- Created "Statistics Management" runbook

Related Incidents: INC0010789 (stale stats after migration)
""",
        "resolved_date": "2024-09-12",
        "url": "https://company.service-now.com/incident.do?sys_id=13768"
    },
    {
        "number": "INC0013879",
        "title": "[INC0013879] Query timeout errors during peak traffic",
        "description": """
Incident: Timeout errors (error 1222) during afternoon peak hours
Affected: SQLPROD01, orders_db
Symptoms: Random query timeouts, "Execution Timeout Expired" errors
Duration: Recurring daily 2 PM - 4 PM for one week

Root Cause Analysis:
Application query timeout too aggressive (15 seconds) for peak load.
Database performance degraded slightly during peak (CPU: 60% → 80%).
Queries that normally take 8-10 seconds took 18-20 seconds during peak.
Application timeout (15 sec) lower than query actual time (18-20 sec).

Contributing Factors:
- Peak traffic: 3x normal load during 2-4 PM window
- No query optimization for high-load scenarios
- Application timeout not tuned for worst-case scenarios
- Resource contention from concurrent batch jobs

Resolution:
1. Analyzed query performance during peak hours
2. Increased application timeout: 15 sec → 30 sec
3. Optimized slow queries (added indexes, rewrote subqueries)
4. Rescheduled batch jobs to run after peak hours (5 PM)
5. Queries now complete in 12-15 sec even during peak

Prevention:
- Performance testing now includes peak load scenarios
- Application timeouts set to 2x average query time
- Implemented query timeout monitoring dashboard
- Batch job scheduling now considers peak traffic windows
- Added load shedding strategy for extreme peak scenarios

Related Incidents: INC0011234 (timeout issues during Black Friday)
""",
        "resolved_date": "2024-11-05",
        "url": "https://company.service-now.com/incident.do?sys_id=13879"
    },
    {
        "number": "INC0013980",
        "title": "[INC0013980] Maintenance plan failure - integrity check corruption detected",
        "description": """
Incident: Weekly maintenance plan failed, DBCC CHECKDB reported corruption
Affected: SQLPROD04, products_db
Symptoms: Maintenance job failure alert, potential data corruption
Duration: 6 hours (diagnosis and repair)

Root Cause Analysis:
Hardware issue on storage array caused page corruption.
RAID controller battery failure led to write cache inconsistency.
Corrupted pages: 15 pages across 3 tables (Products, ProductInventory, ProductPricing).
DBCC CHECKDB detected corruption severity: Minor (no data loss, but corruption present).

Corruption Details:
- Error: "824: SQL Server detected logical consistency error"
- Affected objects: 3 tables, 15 pages
- Corruption type: Page header checksum mismatch
- Last good CHECKDB: 7 days ago (weekly maintenance)

Resolution:
1. Confirmed corruption with DBCC CHECKDB WITH ALL_ERRORMSGS
2. Identified affected rows: 47 product records
3. Restored affected pages from last night's backup using RESTORE PAGE
4. Ran DBCC CHECKDB again: No errors
5. Hardware team replaced RAID controller battery
6. Validated data integrity for affected products

Prevention:
- Increased CHECKDB frequency: Weekly → Daily (lightweight check)
- Full CHECKDB weekly during maintenance window
- Implemented page-level corruption monitoring
- Hardware monitoring for RAID controller battery status
- Added "Corruption Detection & Response" runbook
- Configured immediate alerts for any 824/825 errors

Related Incidents: INC0007890 (corruption on SQLPROD02)
""",
        "resolved_date": "2024-08-20",
        "url": "https://company.service-now.com/incident.do?sys_id=13980"
    },
]

def store_incident(incident_data):
    """Store incident/problem in database"""
    
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
    cur.execute("SELECT id FROM sql_docs WHERE url = %s", (incident_data['url'],))
    if cur.fetchone():
        cur.close()
        conn.close()
        return False
    
    # Generate embedding
    text = f"{incident_data['title']} {incident_data['description']}"
    embedding = model.encode(text).tolist()
    
    # Insert
    cur.execute("""
        INSERT INTO sql_docs (title, content, url, embedding, source, created_at)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (
        incident_data['title'],
        incident_data['description'],
        incident_data['url'],
        embedding,
        'servicenow',
        incident_data['resolved_date']
    ))
    
    conn.commit()
    cur.close()
    conn.close()
    return True

def main():
    print("="*70)
    print("  Loading Mock ServiceNow Incidents & Problems")
    print("="*70)
    print()
    
    successful = 0
    skipped = 0
    
    for incident in MOCK_INCIDENTS:
        number = incident['number']
        title = incident['title'][:50] + "..."
        print(f"Processing: {number}")
        print(f"  {title}")
        
        if store_incident(incident):
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