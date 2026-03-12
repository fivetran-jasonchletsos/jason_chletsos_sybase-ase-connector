# Sybase ASE HammerDB-Style Workload Generator

## Overview

This workload generator simulates a **TPC-C-like benchmark** for the classic **pubs2** bookstore database. It creates realistic concurrent load with mixed read/write transactions to test Sybase ASE performance, throughput, and concurrency handling.

## Features

- **7 Transaction Types** - Mix of OLTP writes and analytical reads
- **Multiprocessing Architecture** - True parallel execution (bypasses Python GIL)
- **Warm-up Period** - Configurable cache warming phase before measurement
- **Pre-loaded IDs** - Eliminates `ORDER BY NEWID()` full table scans
- **Real Transactions** - Inserts, updates, complex joins, and aggregations
- **Performance Metrics** - TPS, latency, error rates, success rates
- **Schema Discovery** - Automatically maps pubs2 database structure
- **Production Ready** - Proper error handling, connection pooling, commit/rollback

## Version 2.0 Improvements

Based on production feedback, v2.0 addresses three critical performance bottlenecks:

### 1. **Multiprocessing vs Threading**
- **Problem**: Python's GIL (Global Interpreter Lock) limits true parallelism with threads
- **Solution**: Switched to `multiprocessing` for genuine OS-level parallelism
- **Impact**: Each worker is a separate process with its own Python interpreter

### 2. **Warm-up Period**
- **Problem**: Initial transactions measure disk I/O and cache loading, not steady-state performance
- **Solution**: Added configurable warm-up period (default 30s) where transactions run but aren't measured
- **Impact**: Metrics reflect true transaction throughput after caches are warm

### 3. **Pre-loaded ID Lists**
- **Problem**: `ORDER BY NEWID()` causes full table scans on every transaction
- **Solution**: Pre-load all valid IDs at startup, use `random.choice()` in Python
- **Impact**: Eliminates table scans, tests actual transaction logic instead of scan performance

---

## Transaction Mix

The workload simulates realistic bookstore operations with the following distribution:

| Transaction Type | Weight | Description | Type |
|-----------------|--------|-------------|------|
| **New Sale** | 45% | Insert orders into `sales` and `salesdetail`, update inventory | Write |
| **Payment** | 15% | Update royalty schedules in `roysched` | Write |
| **Order Status** | 15% | Query order history with multi-table joins | Read |
| **Delivery** | 10% | Update order quantities in `salesdetail` | Write |
| **Stock Level** | 10% | Check inventory levels across titles | Read |
| **Author Lookup** | 3% | Complex joins across authors/titles/publishers | Read |
| **Publisher Report** | 2% | Aggregation queries with GROUP BY | Read |

**Total: ~70% Writes, ~30% Reads** (TPC-C-like ratio)

---

## Installation

### Prerequisites

```bash
# Install required Python packages
pip install pyodbc
```

### FreeTDS Configuration

Ensure FreeTDS is configured (already done if connector.py works):

```bash
# macOS
brew install freetds

# Linux
apt-get install freetds-dev
```

---

## Usage

### 1. Discover Schema Only

```bash
python sybase_ase_hammerdb_workload.py --config configuration.json --discover-only
```

**Output:**
```
======================================================================
  SCHEMA DISCOVERY
======================================================================
  authors: au_id, au_lname, au_fname, phone, address, city, state, country, postalcode
  titles: title_id, title, type, pub_id, price, advance, total_sales, notes, pubdate, contract
  sales: stor_id, ord_num, date
  salesdetail: stor_id, ord_num, title_id, qty, discount
  ...
```

### 2. Run Workload with Defaults

```bash
python sybase_ase_hammerdb_workload.py --config configuration.json
```

**Defaults:**
- Workers: 10 concurrent processes
- Warmup: 30 seconds (cache warming, not measured)
- Duration: 60 seconds (measured)
- Total runtime: 90 seconds

### 3. Run with Custom Settings

```bash
# 20 workers for 5 minutes with 60s warmup
python sybase_ase_hammerdb_workload.py --config configuration.json --workers 20 --duration 300 --warmup 60

# Skip warmup for quick tests (not recommended for benchmarking)
python sybase_ase_hammerdb_workload.py --config configuration.json --warmup 0

# Enable verbose logging
python sybase_ase_hammerdb_workload.py --config configuration.json --verbose
```

---

## Sample Output

```
======================================================================
  Sybase ASE HammerDB-Style Workload Generator v2.0
======================================================================
  Server:   35.223.102.32:5000
  Database: pubs2
  User:     sa

======================================================================
  SCHEMA DISCOVERY
======================================================================
  📋 authors: au_id, au_lname, au_fname, ...
  📋 titles: title_id, title, type, pub_id, ...
  📋 sales: stor_id, ord_num, date
  ...

======================================================================
  PRELOADING IDs (eliminating ORDER BY NEWID() scans)
======================================================================
  ✓ Loaded 6 store IDs
  ✓ Loaded 18 title IDs
  ✓ Loaded 16 roysched title IDs
======================================================================

======================================================================
  HAMMERDB-STYLE WORKLOAD TEST (v2.0)
======================================================================
  Workers:       10
  Warmup Period: 30s (cache warming, not measured)
  Test Duration: 60s (measured)
  Total Runtime: 90s
======================================================================

  🚀 Starting 10 worker processes...
  ⏳ Warmup phase: 30s (warming cache, not measured)...

  ⏱️  Warmup complete (30s). Starting measurement...

======================================================================
  WORKLOAD RESULTS (Measurement Period Only)
======================================================================
  Measurement Time: 60.04s
  Total TX:         4,832
  Total Errors:     8
  Overall TPS:      80.48

----------------------------------------------------------------------
  Transaction Type        Count   Errors    Avg(ms)        TPS
----------------------------------------------------------------------
  author_lookup             145        0      89.23       2.41
  delivery                  483        0      52.34       8.04
  new_sale                2,174        2     187.45      36.21
  order_status              726        0      28.67      12.09
  payment                   726        0     156.78      12.09
  publisher_report           96        6     245.12       1.60
  stock_level               482        0     298.34       8.03
======================================================================
```

---

## Metrics Explained

### Overall Metrics
- **Measurement Time**: Time spent in measurement phase (excludes warmup)
- **Total TX**: Total transactions executed during measurement period
- **Total Errors**: Failed transactions (rollbacks, exceptions)
- **Overall TPS**: Transactions per second (total_tx / measurement_time)

### Per-Transaction Metrics
- **Count**: Number of times this transaction type was executed
- **Errors**: Number of failures for this transaction type
- **Avg(ms)**: Average response time in milliseconds
- **TPS**: Transactions per second for this specific type

### Understanding the Warmup Period

The warmup period is **critical** for accurate benchmarking:

1. **During Warmup (first 30s by default)**:
   - Workers execute transactions normally
   - Database caches warm up (data pages, query plans, etc.)
   - Disk I/O stabilizes
   - Metrics are **NOT recorded**

2. **During Measurement (next 60s by default)**:
   - All transactions are recorded
   - Reflects steady-state performance
   - Comparable to HammerDB methodology

**Why this matters**: Without warmup, your first transactions measure cold cache performance (disk I/O) rather than true transaction throughput.

---

## Configuration File

The script uses the same `configuration.json` as the connector:

```json
{
  "name": "sybase_ase",
  "type": "sybase_ase",
  "server": "35.223.102.32",
  "port": "5000",
  "database": "pubs2",
  "user_id": "sa",
  "password": "your_password"
}
```

---

## Performance Tuning

### Increase Concurrency
```bash
# Test with 50 concurrent workers (processes, not threads)
python sybase_ase_hammerdb_workload.py --config configuration.json --workers 50 --duration 120
```

### Longer Duration & Warmup
```bash
# Run for 10 minutes with 2 minute warmup (recommended for production benchmarks)
python sybase_ase_hammerdb_workload.py --config configuration.json --duration 600 --warmup 120
```

### Quick Test (Skip Warmup)
```bash
# For development/debugging only - not representative of real performance
python sybase_ase_hammerdb_workload.py --config configuration.json --warmup 0 --duration 30
```

### Adjust Transaction Mix

Edit the `transaction_mix` dictionary in `run_workload()`:

```python
transaction_mix = {
    'new_sale': 50,          # Increase writes
    'payment': 20,
    'order_status': 10,      # Reduce reads
    'delivery': 10,
    'stock_level': 5,
    'author_lookup': 3,
    'publisher_report': 2
}
```

---

## Troubleshooting

### High Error Rate

**Symptoms:** `Total Errors` > 10% of transactions

**Causes:**
1. **Unique constraint violations** - Order numbers colliding (rare with timestamp-based generation)
2. **Connection timeouts** - Too many workers for available connections
3. **Lock contention** - Multiple workers updating same rows

**Solutions:**
```bash
# Reduce workers
python sybase_ase_hammerdb_workload.py --config configuration.json --workers 5

# Check Sybase connection limits
isql -Usa -P -S$SYBASE_SERVER
1> sp_configure 'number of user connections'
2> go
```

### Low TPS

**Symptoms:** Overall TPS < 10

**Causes:**
1. Network latency to Sybase server
2. Insufficient Sybase resources (CPU, memory)
3. Slow disk I/O on Sybase server

**Solutions:**
- Run workload from same network as Sybase server
- Monitor Sybase performance with `sp_sysmon`
- Check Sybase logs for warnings

### Connection Failures

**Symptoms:** Workers crashing with connection errors

**Causes:**
1. FreeTDS configuration issues
2. Sybase server connection limit reached
3. Network firewall blocking connections

**Solutions:**
```bash
# Test basic connectivity
tsql -S $SERVER -p $PORT -U sa -P $PASSWORD

# Check FreeTDS logs
export TDSDUMP=/tmp/freetds.log
export TDSDUMPCONFIG=/tmp/freetds_config.log
```

---

## Comparison to HammerDB

This workload is inspired by **HammerDB's TPC-C benchmark** but adapted for pubs2:

| Feature | HammerDB TPC-C | This Workload (v2.0) |
|---------|----------------|----------------------|
| Schema | Warehouse/Orders | Bookstore (pubs2) |
| Workers | Configurable | Configurable (multiprocessing)  |
| Warmup Period | Yes (rampup) | Yes (configurable, default 30s)  |
| Transaction Mix | 5 types (New Order, Payment, etc.) | 7 types (adapted)  |
| Random Selection | Weighted random | Pre-loaded IDs (no table scans)  |
| Metrics | TPS, latency, errors | TPS, latency, errors  |
| Language | TCL | Python  |
| Database Support | Multiple | Sybase ASE (FreeTDS)  |

**Key Alignment with HammerDB**:
- ✅ Warmup period before measurement
- ✅ True parallel execution (multiprocessing)
- ✅ No full table scans during transactions
- ✅ Measures steady-state throughput, not cold cache performance

---

## Use Cases

### 1. **Connector Performance Testing**
Validate that the Sybase ASE connector can handle concurrent load:
```bash
python sybase_ase_hammerdb_workload.py --config configuration.json --workers 20 --duration 300
```

### 2. **Baseline Performance**
Establish baseline TPS before infrastructure changes:
```bash
# Before upgrade
python sybase_ase_hammerdb_workload.py --config configuration.json > baseline.txt

# After upgrade
python sybase_ase_hammerdb_workload.py --config configuration.json > after_upgrade.txt

# Compare
diff baseline.txt after_upgrade.txt
```

### 3. **Stress Testing**
Find breaking point with increasing workers:
```bash
for workers in 10 20 50 100; do
  echo "Testing with $workers workers..."
  python sybase_ase_hammerdb_workload.py --config configuration.json --workers $workers --duration 60
done
```

### 4. **Latency Testing**
Measure response times under different loads:
```bash
# Light load
python sybase_ase_hammerdb_workload.py --config configuration.json --workers 5

# Heavy load
python sybase_ase_hammerdb_workload.py --config configuration.json --workers 50
```

---

## Best Practices

1. **Always Use Warmup**: Default 30s minimum; use 60-120s for production benchmarks
2. **Start Small**: Begin with 5-10 workers, then scale up
3. **Monitor Sybase**: Use `sp_sysmon` or `sp_who` during tests
4. **Clean Data**: Reset pubs2 database between major test runs
5. **Network Proximity**: Run from same region as Sybase server
6. **Realistic Duration**: Use 5-10 minute measurement periods for accurate metrics
7. **Document Results**: Save output for comparison over time
8. **Understand the Metrics**: Warmup TPS ≠ Measurement TPS (warmup includes cold cache)

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Main Process                              │
│  - Load config                                               │
│  - Discover schema                                           │
│  - Preload IDs (eliminate ORDER BY NEWID() scans)           │
│  - Create WorkloadStats (process-safe with Manager)         │
│  - Spawn worker PROCESSES (not threads)                     │
└─────────────────────────────────────────────────────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
   ┌────▼────┐       ┌────▼────┐       ┌────▼────┐
   │Process 1│       │Process 2│  ...  │Process N│
   │ (PID 1) │       │ (PID 2) │       │ (PID N) │
   │         │       │         │       │         │
   │ Warmup: │       │ Warmup: │       │ Warmup: │
   │ - Run TX│       │ - Run TX│       │ - Run TX│
   │ - Don't │       │ - Don't │       │ - Don't │
   │   record│       │   record│       │   record│
   │         │       │         │       │         │
   │ Measure:│       │ Measure:│       │ Measure:│
   │ - Pick  │       │ - Pick  │       │ - Pick  │
   │   random│       │   random│       │   random│
   │   TX    │       │   TX    │       │   TX    │
   │ - Use   │       │ - Use   │       │ - Use   │
   │   cached│       │   cached│       │   cached│
   │   IDs   │       │   IDs   │       │   IDs   │
   │ - Execute│      │ - Execute│      │ - Execute│
   │ - Record│       │ - Record│       │ - Record│
   │   stats │       │   stats │       │   stats │
   └────┬────┘       └────┬────┘       └────┬────┘
        │                  │                  │
        └──────────────────┼──────────────────┘
                           │
                    ┌──────▼──────┐
                    │   Sybase    │
                    │     ASE     │
                    │   (pubs2)   │
                    └─────────────┘
```

**Key Architectural Improvements (v2.0)**:
- **Multiprocessing**: Each worker is a separate OS process with its own Python interpreter (bypasses GIL)
- **Shared State**: Uses `multiprocessing.Manager` for process-safe statistics collection
- **ID Caching**: Pre-loads all IDs once at startup, shared across all processes
- **Two-Phase Execution**: Warmup phase (cache warming) + Measurement phase (recorded metrics)

---

## Contributing

To add new transaction types:

1. Add method to `Pubs2Workload` class:
```python
def my_new_transaction(self, conn, cursor) -> bool:
    try:
        cursor.execute("SELECT ...")
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        return False
```

2. Update `transaction_mix` in `run_workload()`:
```python
transaction_mix = {
    'new_sale': 40,
    'my_new_transaction': 5,  # Add here
    ...
}
```

3. Add to worker thread execution:
```python
elif tx_type == 'my_new_transaction':
    success = workload.my_new_transaction(conn, cursor)
```

---

## License

This script is provided as-is for testing Sybase ASE connectivity and performance.

---

## Support

For issues or questions:
- Check Sybase ASE logs: `$SYBASE/$SYBASE_ASE/install/errorlog`
- Check FreeTDS logs: `export TDSDUMP=/tmp/freetds.log`
- Review pubs2 schema: `sp_help <table_name>`

---

**Version:** 2.0  
**Author:** Nao Labs  
**Last Updated:** 2026-03-11

## Changelog

### v2.0 (2026-03-11)
- **Breaking**: Switched from threading to multiprocessing (true parallelism)
- **New**: Added warmup period (default 30s) before measurement
- **New**: Pre-load IDs to eliminate `ORDER BY NEWID()` full table scans
- **Improved**: Metrics now reflect steady-state performance, not cold cache
- **Improved**: Process-safe statistics collection with `multiprocessing.Manager`
- **New**: `--warmup` CLI argument to configure warmup duration

### v1.0 (Initial Release)
- Multi-threaded workload generator
- 7 transaction types (TPC-C inspired)
- Schema discovery
- Performance metrics (TPS, latency, errors)
