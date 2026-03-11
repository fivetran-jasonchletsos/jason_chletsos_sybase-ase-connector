# Sybase ASE HammerDB-Style Workload Generator

## Overview

This workload generator simulates a **TPC-C-like benchmark** for the classic **pubs2** bookstore database. It creates realistic concurrent load with mixed read/write transactions to test Sybase ASE performance, throughput, and concurrency handling.

## Features

- **7 Transaction Types** - Mix of OLTP writes and analytical reads
- **Concurrent Workers** - Multi-threaded load simulation (configurable)
- **Real Transactions** - Inserts, updates, complex joins, and aggregations
- **Performance Metrics** - TPS, latency, error rates, success rates
- **Schema Discovery** - Automatically maps pubs2 database structure
- **Production Ready** - Proper error handling, connection pooling, commit/rollback

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
- Workers: 10 concurrent threads
- Duration: 60 seconds

### 3. Run with Custom Settings

```bash
# 20 workers for 5 minutes
python sybase_ase_hammerdb_workload.py --config configuration.json --workers 20 --duration 300

# Enable verbose logging
python sybase_ase_hammerdb_workload.py --config configuration.json --verbose
```

---

## Sample Output

```
======================================================================
  HAMMERDB-STYLE WORKLOAD TEST
======================================================================
  Workers:  10
  Duration: 60s
======================================================================

======================================================================
  WORKLOAD RESULTS
======================================================================
  Total Time:     60.12s
  Total TX:       3,245
  Total Errors:   12
  Overall TPS:    53.98

----------------------------------------------------------------------
  Transaction Type        Count   Errors    Avg(ms)        TPS
----------------------------------------------------------------------
  new_sale                1,461        2     234.50      24.31
  payment                   487        0     206.12       8.10
  order_status              486        0      37.45       8.08
  delivery                  324        0      74.23       5.39
  stock_level               325        8     366.89       5.41
  author_lookup              97        0     147.67       1.61
  publisher_report           65        2     221.34       1.08
======================================================================
```

---

## Metrics Explained

### Overall Metrics
- **Total Time**: Actual elapsed time (may exceed duration due to cleanup)
- **Total TX**: Total transactions executed across all workers
- **Total Errors**: Failed transactions (rollbacks, exceptions)
- **Overall TPS**: Transactions per second (total_tx / total_time)

### Per-Transaction Metrics
- **Count**: Number of times this transaction type was executed
- **Errors**: Number of failures for this transaction type
- **Avg(ms)**: Average response time in milliseconds
- **TPS**: Transactions per second for this specific type

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
# Test with 50 concurrent workers
python sybase_ase_hammerdb_workload.py --config configuration.json --workers 50 --duration 120
```

### Longer Duration
```bash
# Run for 10 minutes to test sustained load
python sybase_ase_hammerdb_workload.py --config configuration.json --duration 600
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

| Feature | HammerDB TPC-C | This Workload |
|---------|----------------|---------------|
| Schema | Warehouse/Orders | Bookstore (pubs2) |
| Workers | Configurable | Configurable  |
| Transaction Mix | 5 types (New Order, Payment, etc.) | 7 types (adapted)  |
| Metrics | TPS, latency, errors | TPS, latency, errors  |
| Language | TCL | Python  |
| Database Support | Multiple | Sybase ASE (FreeTDS)  |

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

1. **Start Small**: Begin with 5-10 workers, then scale up
2. **Monitor Sybase**: Use `sp_sysmon` or `sp_who` during tests
3. **Clean Data**: Reset pubs2 database between major test runs
4. **Network Proximity**: Run from same region as Sybase server
5. **Realistic Duration**: Use 5-10 minute tests for accurate metrics
6. **Document Results**: Save output for comparison over time

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Main Process                              │
│  - Load config                                               │
│  - Discover schema                                           │
│  - Create WorkloadStats (thread-safe)                        │
│  - Spawn worker threads                                      │
└─────────────────────────────────────────────────────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
   ┌────▼────┐       ┌────▼────┐       ┌────▼────┐
   │ Worker 1│       │ Worker 2│  ...  │ Worker N│
   │         │       │         │       │         │
   │ Loop:   │       │ Loop:   │       │ Loop:   │
   │ - Pick  │       │ - Pick  │       │ - Pick  │
   │   random│       │   random│       │   random│
   │   TX    │       │   TX    │       │   TX    │
   │ - Execute│      │ - Execute│      │ - Execute│
   │ - Record│       │ - Record│       │ - Record│
   │   stats │       │   stats │       │   stats │
   │ - Sleep │       │ - Sleep │       │ - Sleep │
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

**Version:** 1.0  
**Author:** Nao Labs  
**Last Updated:** 2026-03-11
