# Sybase ASE HammerDB Workload - Quick Reference

## Installation
```bash
pip install pyodbc
```

## Basic Usage

### 1. Schema Discovery
```bash
python sybase_ase_hammerdb_workload.py --config configuration.json --discover-only
```

### 2. Run Default Test (10 workers, 60 seconds)
```bash
python sybase_ase_hammerdb_workload.py --config configuration.json
```

### 3. Custom Test
```bash
python sybase_ase_hammerdb_workload.py --config configuration.json --workers 20 --duration 300
```

### 4. Verbose Mode
```bash
python sybase_ase_hammerdb_workload.py --config configuration.json --verbose
```

---

## Transaction Types

| Transaction | Type | Description | Weight |
|------------|------|-------------|--------|
| New Sale | Write | Insert orders, update inventory | 45% |
| Payment | Write | Update royalty schedules | 15% |
| Order Status | Read | Query order history | 15% |
| Delivery | Write | Update order quantities | 10% |
| Stock Level | Read | Check inventory levels | 10% |
| Author Lookup | Read | Complex joins | 3% |
| Publisher Report | Read | Aggregations | 2% |

---

## Command Line Options

```
--config PATH         Path to configuration.json (required)
--workers N           Number of concurrent workers (default: 10)
--duration N          Test duration in seconds (default: 60)
--discover-only       Only discover schema and exit
--verbose             Enable verbose output
```

---

## Understanding Output

```
======================================================================
  WORKLOAD RESULTS
======================================================================
  Total Time:     60.12s          ← Actual elapsed time
  Total TX:       3,245           ← Total transactions executed
  Total Errors:   12              ← Failed transactions
  Overall TPS:    53.98           ← Transactions per second

----------------------------------------------------------------------
  Transaction Type        Count   Errors    Avg(ms)        TPS
----------------------------------------------------------------------
  new_sale                1,461        2     234.50      24.31
  ↑                         ↑          ↑        ↑           ↑
  Name                    Count    Failures  Latency   Per-type TPS
```

---

## Performance Expectations

| Workers | Expected TPS | Expected Errors |
|---------|-------------|-----------------|
| 1-5     | 10-30       | < 5% |
| 10      | 30-60       | < 10% |
| 20      | 50-120      | < 15% |
| 50+     | 100-300     | < 20% |

*Note: Actual performance depends on network, hardware, and Sybase configuration*

---

## Troubleshooting

### High Error Rate (> 20%)
```bash
# Reduce workers
python sybase_ase_hammerdb_workload.py --config configuration.json --workers 3

# Check Sybase logs
tail -f $SYBASE/$SYBASE_ASE/install/errorlog
```

### Low TPS (< 10)
```bash
# Check network latency
ping <sybase_server>

# Run from same network as Sybase server
# Add indexes to pubs2 tables
```

### Connection Failures
```bash
# Test basic connectivity
tsql -S <server> -p <port> -U sa -P <password>

# Enable FreeTDS debug logging
export TDSDUMP=/tmp/freetds.log
python sybase_ase_hammerdb_workload.py --config configuration.json
cat /tmp/freetds.log
```

---

## Example Test Scenarios

### Scenario 1: Baseline Test
```bash
# Establish baseline with minimal load
python sybase_ase_hammerdb_workload.py --config configuration.json --workers 5 --duration 120 > baseline.txt
```

### Scenario 2: Stress Test
```bash
# Find breaking point
for workers in 10 20 50 100; do
  echo "=== Testing with $workers workers ==="
  python sybase_ase_hammerdb_workload.py --config configuration.json --workers $workers --duration 60
done
```

### Scenario 3: Sustained Load
```bash
# Long-running test (10 minutes)
python sybase_ase_hammerdb_workload.py --config configuration.json --workers 10 --duration 600
```

### Scenario 4: Read-Only Test
```bash
# Edit script to disable writes (set new_sale, payment, delivery to 0)
# Then run:
python sybase_ase_hammerdb_workload.py --config configuration.json --workers 20 --duration 60
```

---

## Files

- **sybase_ase_hammerdb_workload.py** - Main script
- **README_HAMMERDB_WORKLOAD.md** - Full documentation
- **WORKLOAD_RESULTS.md** - Test results and analysis
- **QUICK_REFERENCE.md** - This file
- **configuration.json** - Connection config

---

## Key Metrics to Monitor

1. **Overall TPS** - Target: > 30 for 10 workers
2. **Error Rate** - Target: < 10%
3. **Avg Response Time** - Target: < 500ms for most transactions
4. **Success Rate by Type** - Target: > 90% for all types

---

## Common Commands

```bash
# Quick test
python sybase_ase_hammerdb_workload.py --config configuration.json

# Schema check
python sybase_ase_hammerdb_workload.py --config configuration.json --discover-only

# Heavy load
python sybase_ase_hammerdb_workload.py --config configuration.json --workers 50 --duration 300

# Debug mode
python sybase_ase_hammerdb_workload.py --config configuration.json --verbose 2>&1 | tee debug.log
```

---

## Support

- Check **README_HAMMERDB_WORKLOAD.md** for detailed documentation
- Check **WORKLOAD_RESULTS.md** for latest test results
- Review Sybase logs: `$SYBASE/$SYBASE_ASE/install/errorlog`
- Review FreeTDS logs: `export TDSDUMP=/tmp/freetds.log`

---

**Version:** 1.0  
**Last Updated:** 2026-03-11
