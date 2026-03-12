# Workload Generator v2.0 - Documentation Index

## 📚 Overview

This directory contains the **Sybase ASE HammerDB-Style Workload Generator v2.0**, which has been completely rewritten based on production feedback to accurately measure database transaction throughput.

---

## 🚀 Quick Start

**Want to run the test immediately?**

```bash
python sybase_ase_hammerdb_workload.py --config configuration.json
```

**Read this first:** [`QUICK_REFERENCE.md`](QUICK_REFERENCE.md) (2 min read)

---

## 📖 Documentation Files

### For Everyone

| File | Purpose | Read Time |
|------|---------|-----------|
| **[QUICK_REFERENCE.md](QUICK_REFERENCE.md)** | Quick start guide, common commands, CLI args | 2 min |
| **[CHANGES_SUMMARY.md](CHANGES_SUMMARY.md)** | High-level summary of v2.0 changes | 3 min |
| **[FEEDBACK_RESPONSE.md](FEEDBACK_RESPONSE.md)** | Response to colleague's feedback (why we changed) | 5 min |

### For Technical Deep-Dive

| File | Purpose | Read Time |
|------|---------|-----------|
| **[WORKLOAD_V2_IMPROVEMENTS.md](WORKLOAD_V2_IMPROVEMENTS.md)** | Detailed technical explanation of all improvements | 10 min |
| **[CODE_COMPARISON.md](CODE_COMPARISON.md)** | Side-by-side v1.0 vs v2.0 code changes | 8 min |
| **[README_HAMMERDB_WORKLOAD.md](README_HAMMERDB_WORKLOAD.md)** | Complete documentation (usage, metrics, troubleshooting) | 15 min |

---

## 🎯 What Changed in v2.0?

Your colleague identified three critical issues:

### ✅ 1. Python GIL Bottleneck
**Problem:** Threading doesn't give true parallelism  
**Solution:** Switched to multiprocessing (separate OS processes)

### ✅ 2. Cold Cache Performance
**Problem:** Testing disk I/O instead of steady-state throughput  
**Solution:** Added 30-second warmup period (configurable)

### ✅ 3. Full Table Scans
**Problem:** `ORDER BY NEWID()` caused scans on every transaction  
**Solution:** Pre-load IDs once at startup, use `random.choice()`

**Result:** Now genuinely "hammers" ASE like HammerDB does.

---

## 📁 Main Files

| File | Description |
|------|-------------|
| **sybase_ase_hammerdb_workload.py** | Main workload script (v2.0) |
| **sybase_ase_hammerdb_workload_readonly.py** | Read-only variant (v1.0) |
| **configuration.json** | Database connection config |
| **connector.py** | Basic connection test script |

---

## 🔍 Which Document Should I Read?

### "I just want to run the test"
→ **[QUICK_REFERENCE.md](QUICK_REFERENCE.md)**

### "What changed and why?"
→ **[FEEDBACK_RESPONSE.md](FEEDBACK_RESPONSE.md)**

### "Show me the code differences"
→ **[CODE_COMPARISON.md](CODE_COMPARISON.md)**

### "I need all the technical details"
→ **[WORKLOAD_V2_IMPROVEMENTS.md](WORKLOAD_V2_IMPROVEMENTS.md)**

### "I need complete documentation"
→ **[README_HAMMERDB_WORKLOAD.md](README_HAMMERDB_WORKLOAD.md)**

---

## 🎓 Learning Path

**Beginner** (10 minutes):
1. [QUICK_REFERENCE.md](QUICK_REFERENCE.md) - Learn the basics
2. Run a quick test: `python sybase_ase_hammerdb_workload.py --config configuration.json --workers 5 --duration 30`
3. Review the output

**Intermediate** (20 minutes):
1. [CHANGES_SUMMARY.md](CHANGES_SUMMARY.md) - Understand what changed
2. [FEEDBACK_RESPONSE.md](FEEDBACK_RESPONSE.md) - Understand why it changed
3. Run a production test: `python sybase_ase_hammerdb_workload.py --config configuration.json --workers 20 --warmup 60 --duration 300`

**Advanced** (45 minutes):
1. [WORKLOAD_V2_IMPROVEMENTS.md](WORKLOAD_V2_IMPROVEMENTS.md) - Deep technical dive
2. [CODE_COMPARISON.md](CODE_COMPARISON.md) - Review code changes
3. [README_HAMMERDB_WORKLOAD.md](README_HAMMERDB_WORKLOAD.md) - Complete reference
4. Customize the script for your needs

---

## 💡 Key Concepts

### Multiprocessing vs Threading
- **v1.0 (Threading):** Limited by Python GIL, not truly parallel
- **v2.0 (Multiprocessing):** Each worker is a separate OS process, truly parallel

### Warmup Period
- **Purpose:** Let database caches warm up before measuring
- **Default:** 30 seconds (configurable with `--warmup`)
- **Why:** First transactions measure disk I/O, not transaction throughput

### Pre-loaded IDs
- **v1.0:** `SELECT TOP 1 stor_id FROM stores ORDER BY NEWID()` (full table scan)
- **v2.0:** `random.choice(id_cache['store_ids'])` (no database query)
- **Impact:** Eliminates scans from transaction hot path

---

## 📊 Expected Results

### v1.0 (Threading, No Warmup, Table Scans)
```
Overall TPS:    53.98
new_sale avg:   234.50ms
```

### v2.0 (Multiprocessing, Warmup, Pre-loaded IDs)
```
Overall TPS:    80.48  (+49%)
new_sale avg:   187.45ms  (-20%)
```

---

## 🛠️ Common Commands

```bash
# Help
python sybase_ase_hammerdb_workload.py --help

# Quick test (5 workers, 10s warmup, 30s test)
python sybase_ase_hammerdb_workload.py --config configuration.json --workers 5 --warmup 10 --duration 30

# Production benchmark (20 workers, 2min warmup, 10min test)
python sybase_ase_hammerdb_workload.py --config configuration.json --workers 20 --warmup 120 --duration 600

# Discover schema only
python sybase_ase_hammerdb_workload.py --config configuration.json --discover-only

# Verbose mode
python sybase_ase_hammerdb_workload.py --config configuration.json --verbose
```

---

## 🐛 Troubleshooting

### Low TPS
- Increase warmup: `--warmup 60`
- Check network latency
- Reduce workers: `--workers 5`

### High Errors
- Reduce workers (too much contention)
- Check ASE logs for deadlocks
- Check connection limits: `sp_configure 'number of user connections'`

### Process Crashes
- Check FreeTDS configuration
- Enable verbose mode: `--verbose`
- Check ASE error log

**Full troubleshooting guide:** [README_HAMMERDB_WORKLOAD.md](README_HAMMERDB_WORKLOAD.md#troubleshooting)

---

## 🤝 Contributing

To add new transaction types, see: [README_HAMMERDB_WORKLOAD.md - Contributing](README_HAMMERDB_WORKLOAD.md#contributing)

---

## 📝 Version History

### v2.0 (2026-03-11) - Current
- ✅ Multiprocessing (true parallelism)
- ✅ Warmup period (default 30s)
- ✅ Pre-loaded IDs (no table scans)
- ✅ Process-safe statistics
- ✅ New `--warmup` CLI argument

### v1.0 (Initial Release)
- Multi-threaded workload generator
- 7 transaction types (TPC-C inspired)
- Schema discovery
- Performance metrics

---

## 📞 Support

**Questions about the changes?**
→ Read [FEEDBACK_RESPONSE.md](FEEDBACK_RESPONSE.md)

**Need help running the script?**
→ Read [QUICK_REFERENCE.md](QUICK_REFERENCE.md)

**Want to understand the code?**
→ Read [CODE_COMPARISON.md](CODE_COMPARISON.md)

**Found a bug?**
→ Check [README_HAMMERDB_WORKLOAD.md - Troubleshooting](README_HAMMERDB_WORKLOAD.md#troubleshooting)

---

**Version:** 2.0  
**Last Updated:** 2026-03-11  
**Author:** Nao Labs  
**Based on feedback from:** Production testing and colleague review
