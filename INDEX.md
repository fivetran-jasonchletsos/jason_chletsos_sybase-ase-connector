# Sybase ASE HammerDB Workload - Documentation Index

## 📦 Files Included

### Core Files
1. **sybase_ase_hammerdb_workload.py** (19 KB)
   - Main workload generator script
   - TPC-C-style benchmark for pubs2 database
   - Multi-threaded concurrent load testing

2. **configuration.json** (119 B)
   - Database connection configuration
   - Server, port, credentials

### Documentation
3. **QUICK_REFERENCE.md** (5.2 KB) ⭐ **START HERE**
   - Quick commands and examples
   - Common troubleshooting
   - Performance expectations

4. **README_HAMMERDB_WORKLOAD.md** (12 KB)
   - Complete documentation
   - Architecture details
   - Advanced configuration
   - Use cases and best practices

5. **WORKLOAD_RESULTS.md** (6.4 KB)
   - Latest test results
   - Performance analysis
   - Recommendations
   - Next steps

6. **INDEX.md** (This file)
   - Documentation overview
   - Quick navigation

---

## 🚀 Quick Start (3 Steps)

### Step 1: Install Dependencies
```bash
pip install pyodbc
```

### Step 2: Verify Configuration
```bash
cat configuration.json
# Should show your Sybase ASE connection details
```

### Step 3: Run Test
```bash
python sybase_ase_hammerdb_workload.py --config configuration.json
```

**Expected Output:**
```
======================================================================
  HAMMERDB-STYLE WORKLOAD TEST
======================================================================
  Workers:  10
  Duration: 60s
======================================================================
[... test runs ...]
======================================================================
  WORKLOAD RESULTS
======================================================================
  Total Time:     60.12s
  Total TX:       3,245
  Total Errors:   12
  Overall TPS:    53.98
```

---

## 📖 Documentation Guide

### For First-Time Users
1. Read **QUICK_REFERENCE.md** (5 min)
2. Run basic test (see Quick Start above)
3. Review **WORKLOAD_RESULTS.md** for expected performance

### For Advanced Users
1. Read **README_HAMMERDB_WORKLOAD.md** (15 min)
2. Customize transaction mix
3. Run stress tests with varying worker counts
4. Monitor Sybase performance during tests

### For Troubleshooting
1. Check **QUICK_REFERENCE.md** → Troubleshooting section
2. Enable verbose mode: `--verbose`
3. Check **WORKLOAD_RESULTS.md** → Known Issues
4. Review Sybase and FreeTDS logs

---

## 🎯 Common Use Cases

### Use Case 1: Validate Connector Performance
**Goal:** Ensure Sybase ASE connector can handle production load

**Steps:**
```bash
# 1. Baseline test
python sybase_ase_hammerdb_workload.py --config configuration.json --workers 10 --duration 60

# 2. Check TPS > 30 and errors < 10%
# 3. If good, proceed to stress test
python sybase_ase_hammerdb_workload.py --config configuration.json --workers 50 --duration 300
```

**Documentation:** See README_HAMMERDB_WORKLOAD.md → Use Cases → Connector Performance Testing

---

### Use Case 2: Establish Performance Baseline
**Goal:** Document current performance before infrastructure changes

**Steps:**
```bash
# Run standardized test
python sybase_ase_hammerdb_workload.py --config configuration.json --workers 10 --duration 300 > baseline_$(date +%Y%m%d).txt

# Save results
git add baseline_*.txt
git commit -m "Performance baseline before upgrade"
```

**Documentation:** See README_HAMMERDB_WORKLOAD.md → Use Cases → Baseline Performance

---

### Use Case 3: Find Breaking Point
**Goal:** Determine maximum sustainable load

**Steps:**
```bash
# Test with increasing workers
for workers in 10 20 50 100 200; do
  echo "=== Testing with $workers workers ==="
  python sybase_ase_hammerdb_workload.py --config configuration.json --workers $workers --duration 60
done
```

**Documentation:** See README_HAMMERDB_WORKLOAD.md → Use Cases → Stress Testing

---

### Use Case 4: Debug Connection Issues
**Goal:** Diagnose connectivity problems

**Steps:**
```bash
# 1. Test basic connectivity
tsql -S 35.223.102.32 -p 5000 -U sa -P <password>

# 2. Enable debug logging
export TDSDUMP=/tmp/freetds.log
python sybase_ase_hammerdb_workload.py --config configuration.json --verbose

# 3. Review logs
cat /tmp/freetds.log
```

**Documentation:** See QUICK_REFERENCE.md → Troubleshooting → Connection Failures

---

## 📊 Understanding Results

### Key Metrics

| Metric | Good | Warning | Critical |
|--------|------|---------|----------|
| Overall TPS | > 30 | 10-30 | < 10 |
| Error Rate | < 5% | 5-20% | > 20% |
| Avg Response Time | < 500ms | 500-2000ms | > 2000ms |
| Success Rate | > 95% | 80-95% | < 80% |

### Sample Good Result
```
Total Time:     60.12s
Total TX:       3,245
Total Errors:   12              ← 0.4% error rate ✅
Overall TPS:    53.98           ← Good throughput ✅
```

### Sample Problem Result
```
Total Time:     64.64s
Total TX:       163
Total Errors:   110             ← 67.5% error rate ⚠️
Overall TPS:    2.52            ← Low throughput ⚠️
```

**Action:** See WORKLOAD_RESULTS.md → Analysis → Issues Identified

---

## 🔧 Customization

### Adjust Worker Count
```bash
# Light load
python sybase_ase_hammerdb_workload.py --config configuration.json --workers 5

# Heavy load
python sybase_ase_hammerdb_workload.py --config configuration.json --workers 50
```

### Adjust Duration
```bash
# Quick test (1 minute)
python sybase_ase_hammerdb_workload.py --config configuration.json --duration 60

# Long test (10 minutes)
python sybase_ase_hammerdb_workload.py --config configuration.json --duration 600
```

### Modify Transaction Mix
Edit `sybase_ase_hammerdb_workload.py`:
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

**Documentation:** See README_HAMMERDB_WORKLOAD.md → Performance Tuning

---

## 🐛 Troubleshooting Quick Links

| Issue | Solution | Documentation |
|-------|----------|---------------|
| High error rate | Reduce workers, check logs | QUICK_REFERENCE.md → Troubleshooting |
| Low TPS | Check network, add indexes | WORKLOAD_RESULTS.md → Recommendations |
| Connection failures | Test with tsql, check FreeTDS | QUICK_REFERENCE.md → Connection Failures |
| Slow response times | Run from same network, tune Sybase | README_HAMMERDB_WORKLOAD.md → Performance Tuning |

---

## 📚 Full Documentation Structure

```
📁 Sybase ASE HammerDB Workload
│
├── 📄 INDEX.md (this file)
│   └── Overview and navigation
│
├── 📄 QUICK_REFERENCE.md ⭐ START HERE
│   ├── Installation
│   ├── Basic usage
│   ├── Command options
│   ├── Troubleshooting
│   └── Common commands
│
├── 📄 README_HAMMERDB_WORKLOAD.md
│   ├── Overview
│   ├── Transaction types
│   ├── Architecture
│   ├── Performance tuning
│   ├── Use cases
│   ├── Best practices
│   └── Contributing
│
├── 📄 WORKLOAD_RESULTS.md
│   ├── Latest test results
│   ├── Performance analysis
│   ├── Issues identified
│   ├── Recommendations
│   └── Next steps
│
├── 🐍 sybase_ase_hammerdb_workload.py
│   └── Main workload script
│
└── ⚙️ configuration.json
    └── Connection configuration
```

---

## 🎓 Learning Path

### Beginner (30 minutes)
1. Read QUICK_REFERENCE.md
2. Run basic test
3. Understand output metrics

### Intermediate (1 hour)
1. Read README_HAMMERDB_WORKLOAD.md → Overview
2. Run tests with different worker counts
3. Review WORKLOAD_RESULTS.md

### Advanced (2+ hours)
1. Read full README_HAMMERDB_WORKLOAD.md
2. Customize transaction mix
3. Implement monitoring
4. Tune Sybase configuration
5. Add new transaction types

---

## 📞 Support Resources

### Documentation
- **Quick help:** QUICK_REFERENCE.md
- **Detailed info:** README_HAMMERDB_WORKLOAD.md
- **Test results:** WORKLOAD_RESULTS.md

### Logs
```bash
# Sybase ASE logs
$SYBASE/$SYBASE_ASE/install/errorlog

# FreeTDS logs
export TDSDUMP=/tmp/freetds.log
cat /tmp/freetds.log

# Workload logs
python sybase_ase_hammerdb_workload.py --config configuration.json --verbose 2>&1 | tee workload.log
```

### Sybase Monitoring
```sql
-- Active connections
sp_who

-- Lock information
sp_lock

-- System monitor (1 minute sample)
sp_sysmon '00:01:00'
```

---

## ✅ Checklist for Sharing with Colleagues

- [ ] All files present (5 files)
- [ ] configuration.json has correct credentials
- [ ] pyodbc installed (`pip install pyodbc`)
- [ ] FreeTDS configured
- [ ] Basic test runs successfully
- [ ] Documentation reviewed
- [ ] Known issues documented in WORKLOAD_RESULTS.md

---

## 📝 Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-03-11 | Initial release |
|     |            | - 7 transaction types |
|     |            | - Multi-threaded workers |
|     |            | - Comprehensive documentation |
|     |            | - Test results and analysis |

---

## 🚀 Next Steps

1. **Immediate:** Run basic test to validate setup
   ```bash
   python sybase_ase_hammerdb_workload.py --config configuration.json
   ```

2. **Short-term:** Review WORKLOAD_RESULTS.md and address issues
   - Reduce error rate
   - Improve response times
   - Tune transaction mix

3. **Long-term:** Establish continuous performance monitoring
   - Run daily baseline tests
   - Track TPS trends over time
   - Alert on performance degradation

---

**Documentation maintained by:** Nao Labs  
**Last updated:** 2026-03-11  
**Questions?** Review QUICK_REFERENCE.md → Troubleshooting
