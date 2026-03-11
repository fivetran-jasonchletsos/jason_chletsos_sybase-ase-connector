# Sybase ASE HammerDB-Style Workload Generator

Production-ready workload generator for Sybase ASE that simulates TPC-C-like benchmark testing on the pubs2 database.

## Quick Start

### Prerequisites
```bash
pip install pyodbc
```

### Run Test
```bash
# Default test (10 workers, 60 seconds)
python sybase_ase_hammerdb_workload.py --config configuration.json

# Custom test
python sybase_ase_hammerdb_workload.py --config configuration.json --workers 20 --duration 300

# Schema discovery only
python sybase_ase_hammerdb_workload.py --config configuration.json --discover-only
```

## Features

- **7 Transaction Types**: Mix of OLTP writes and analytical reads
- **Concurrent Workers**: Multi-threaded load simulation (configurable)
- **Real Transactions**: Inserts, updates, complex joins, and aggregations
- **Performance Metrics**: TPS, latency, error rates, success rates
- **Schema Discovery**: Automatically maps pubs2 database structure
- **Production Ready**: Proper error handling, connection pooling, commit/rollback

## Transaction Mix

| Transaction Type | Weight | Description | Type |
|-----------------|--------|-------------|------|
| New Sale | 45% | Insert orders, update inventory | Write |
| Payment | 15% | Update royalty schedules | Write |
| Order Status | 15% | Query order history | Read |
| Delivery | 10% | Update order quantities | Write |
| Stock Level | 10% | Check inventory levels | Read |
| Author Lookup | 3% | Complex joins | Read |
| Publisher Report | 2% | Aggregation queries | Read |

## Configuration

Edit `configuration.json`:
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

## Command Line Options

```
--config PATH         Path to configuration.json (required)
--workers N           Number of concurrent workers (default: 10)
--duration N          Test duration in seconds (default: 60)
--discover-only       Only discover schema and exit
--verbose             Enable verbose output
```

## Understanding Output

```
======================================================================
  WORKLOAD RESULTS
======================================================================
  Total Time:     60.12s          # Actual elapsed time
  Total TX:       3,245           # Total transactions executed
  Total Errors:   12              # Failed transactions
  Overall TPS:    53.98           # Transactions per second

----------------------------------------------------------------------
  Transaction Type        Count   Errors    Avg(ms)        TPS
----------------------------------------------------------------------
  new_sale                1,461        2     234.50      24.31
  payment                   487        0     206.12       8.10
  order_status              486        0      37.45       8.08
  ...
```

## Performance Expectations

| Workers | Expected TPS | Expected Errors |
|---------|-------------|-----------------|
| 1-5     | 10-30       | < 5% |
| 10      | 30-60       | < 10% |
| 20      | 50-120      | < 15% |
| 50+     | 100-300     | < 20% |

Note: Actual performance depends on network, hardware, and Sybase configuration.

## Troubleshooting

### High Error Rate (> 20%)
```bash
# Reduce workers
python sybase_ase_hammerdb_workload.py --config configuration.json --workers 3

# Check Sybase logs
tail -f $SYBASE/$SYBASE_ASE/install/errorlog
```

### Low TPS (< 10)
- Check network latency to Sybase server
- Run from same network as Sybase server
- Add indexes to pubs2 tables
- Monitor Sybase performance with sp_sysmon

### Connection Failures
```bash
# Test basic connectivity
tsql -S <server> -p <port> -U sa -P <password>

# Enable FreeTDS debug logging
export TDSDUMP=/tmp/freetds.log
python sybase_ase_hammerdb_workload.py --config configuration.json
cat /tmp/freetds.log
```

## Use Cases

### 1. Connector Performance Testing
```bash
python sybase_ase_hammerdb_workload.py --config configuration.json --workers 20 --duration 300
```

### 2. Baseline Performance
```bash
# Before upgrade
python sybase_ase_hammerdb_workload.py --config configuration.json > baseline.txt

# After upgrade
python sybase_ase_hammerdb_workload.py --config configuration.json > after_upgrade.txt

# Compare
diff baseline.txt after_upgrade.txt
```

### 3. Stress Testing
```bash
for workers in 10 20 50 100; do
  echo "Testing with $workers workers..."
  python sybase_ase_hammerdb_workload.py --config configuration.json --workers $workers --duration 60
done
```

## Files

- **sybase_ase_hammerdb_workload.py** - Main workload script (read/write mix)
- **sybase_ase_hammerdb_workload_readonly.py** - Read-only workload alternative
- **connector.py** - Basic connection utility
- **configuration.json** - Connection configuration
- **README.md** - This file
- **INDEX.md** - Documentation navigation
- **QUICK_REFERENCE.md** - Quick command reference
- **README_HAMMERDB_WORKLOAD.md** - Detailed documentation
- **WORKLOAD_RESULTS.md** - Test results and analysis

## Best Practices

1. Start with 5-10 workers, then scale up
2. Monitor Sybase with sp_sysmon or sp_who during tests
3. Reset pubs2 database between major test runs
4. Run from same region as Sybase server for best results
5. Use 5-10 minute tests for accurate metrics
6. Document results for comparison over time

## Support

For issues or questions:
- Check Sybase ASE logs: `$SYBASE/$SYBASE_ASE/install/errorlog`
- Check FreeTDS logs: `export TDSDUMP=/tmp/freetds.log`
- Review pubs2 schema: `sp_help <table_name>`
- See detailed documentation in README_HAMMERDB_WORKLOAD.md

## Version

Version: 1.0  
Last Updated: 2026-03-11
