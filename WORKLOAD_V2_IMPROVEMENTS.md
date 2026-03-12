# Workload Generator v2.0 - Performance Improvements

## Summary

Based on production feedback, we've implemented three critical improvements to ensure the workload generator measures **actual database transaction throughput** rather than Python interpreter overhead, disk I/O, or table scan performance.

---

## The Three Problems (and Solutions)

### 1. Python GIL Bottleneck

**Problem Identified:**
> "It became more of a what is the limitation of the Python interpreter rather than 'hammering' ASE."

**Root Cause:**
Python's Global Interpreter Lock (GIL) prevents true parallel execution of threads. Even with 50 worker threads, only one can execute Python bytecode at a time. This means we were testing Python's threading overhead, not ASE's concurrency handling.

**Solution:**
Switched from `threading` to `multiprocessing`. Each worker is now a separate OS process with its own Python interpreter.

**Code Change:**
```python
# OLD (v1.0) - Threading
import threading
threads = []
for i in range(num_workers):
    t = threading.Thread(target=worker_thread, args=(...))
    threads.append(t)
    t.start()

# NEW (v2.0) - Multiprocessing
import multiprocessing
processes = []
for i in range(num_workers):
    p = multiprocessing.Process(target=worker_process, args=(...))
    processes.append(p)
    p.start()
```

**Impact:**
- ✅ True parallel execution (no GIL contention)
- ✅ Each process has dedicated CPU core
- ✅ Measures ASE throughput, not Python interpreter limits

---

### 2. Cold Cache Performance

**Problem Identified:**
> "With it being a small data set, I believe you're more likely testing the ASE memory cache. I believe HammerDB uses a warm-up period to ignore the initial cache."

**Root Cause:**
The first transactions after startup measure:
- Disk I/O (loading data pages into cache)
- Query plan compilation
- Connection pool initialization

This is **not representative** of steady-state performance. HammerDB explicitly has a "rampup" period to warm caches before measurement begins.

**Solution:**
Added configurable warmup period (default 30s) where workers execute transactions but metrics are **not recorded**.

**Code Change:**
```python
# NEW: Two-phase execution
while (time.time() - start_time) < (warmup_seconds + duration_seconds):
    elapsed = time.time() - start_time
    
    # Check if warmup just completed
    if elapsed >= warmup_seconds and not stats.warmup_complete.value:
        print("⏱️  Warmup complete. Starting measurement...")
        stats.warmup_complete.value = True
        stats.start_time.value = time.time()
    
    # Execute transaction
    success = execute_transaction(...)
    
    # Only record if warmup is complete
    stats.record_transaction(tx_type, duration, success)  # Ignored during warmup
```

**Impact:**
- ✅ Metrics reflect steady-state performance
- ✅ Comparable to HammerDB methodology
- ✅ Eliminates disk I/O noise from results

**Example Output:**
```
🚀 Starting 10 worker processes...
⏳ Warmup phase: 30s (warming cache, not measured)...

⏱️  Warmup complete (30s). Starting measurement...

======================================================================
  WORKLOAD RESULTS (Measurement Period Only)
======================================================================
  Measurement Time: 60.04s
  Total TX:         4,832
  Overall TPS:      80.48
```

---

### 3. Full Table Scans on Every Transaction

**Problem Identified:**
> "With the ORDER BY NEWID(), I think you're also spending time doing a full table scan, rather than testing the transaction logic."

**Root Cause:**
Every transaction that needed a random store or title was executing:
```sql
SELECT TOP 1 stor_id FROM stores ORDER BY NEWID()
```

This causes a **full table scan** + sort on every transaction. We were testing scan performance, not transaction logic.

**Solution:**
Pre-load all valid IDs once at startup into Python lists, then use `random.choice()` to pick from them locally.

**Code Change:**
```python
# NEW: Preload IDs once at startup
def preload_ids(config: dict) -> Dict[str, List]:
    conn = create_connection(config)
    cursor = conn.cursor()
    
    id_cache = {}
    
    cursor.execute("SELECT stor_id FROM stores")
    id_cache['store_ids'] = [row[0] for row in cursor.fetchall()]
    
    cursor.execute("SELECT title_id FROM titles")
    id_cache['title_ids'] = [row[0] for row in cursor.fetchall()]
    
    cursor.execute("SELECT DISTINCT title_id FROM roysched")
    id_cache['roysched_title_ids'] = [row[0] for row in cursor.fetchall()]
    
    return id_cache

# OLD (v1.0) - Full table scan every time
cursor.execute("SELECT TOP 1 stor_id FROM stores ORDER BY NEWID()")
stor_id = cursor.fetchone()[0]

# NEW (v2.0) - Random choice from pre-loaded list
stor_id = random.choice(id_cache['store_ids'])
```

**Impact:**
- ✅ Eliminates full table scans from transaction path
- ✅ Tests actual INSERT/UPDATE/JOIN logic
- ✅ Dramatically reduces average transaction time

**Example Output:**
```
======================================================================
  PRELOADING IDs (eliminating ORDER BY NEWID() scans)
======================================================================
  ✓ Loaded 6 store IDs
  ✓ Loaded 18 title IDs
  ✓ Loaded 16 roysched title IDs
======================================================================
```

---

## Performance Comparison

### Before (v1.0)
```
Overall TPS:    53.98
new_sale        Avg(ms): 234.50    TPS: 24.31
order_status    Avg(ms):  37.45    TPS:  8.08
```

### After (v2.0)
```
Overall TPS:    80.48  (+49% improvement)
new_sale        Avg(ms): 187.45    TPS: 36.21  (+49%)
order_status    Avg(ms):  28.67    TPS: 12.09  (+50%)
```

**Note:** These are illustrative numbers. Actual improvement depends on:
- Number of workers (multiprocessing benefit scales with CPU cores)
- Dataset size (preloading benefit scales with table size)
- Network latency (warmup benefit scales with cache hit ratio)

---

## Usage Changes

### New CLI Arguments

```bash
# Configure warmup period (default 30s)
python sybase_ase_hammerdb_workload.py --config configuration.json --warmup 60

# Skip warmup for quick tests (not recommended for benchmarks)
python sybase_ase_hammerdb_workload.py --config configuration.json --warmup 0
```

### Recommended Settings

**For Production Benchmarks:**
```bash
python sybase_ase_hammerdb_workload.py \
  --config configuration.json \
  --workers 20 \
  --warmup 120 \
  --duration 600
```

**For Quick Development Tests:**
```bash
python sybase_ase_hammerdb_workload.py \
  --config configuration.json \
  --workers 5 \
  --warmup 10 \
  --duration 30
```

---

## Alignment with HammerDB

| Feature | HammerDB TPC-C | v1.0 | v2.0 |
|---------|----------------|------|------|
| Parallel Execution | ✅ True (TCL threads) | ❌ GIL-limited | ✅ True (multiprocessing) |
| Warmup Period | ✅ Rampup phase | ❌ None | ✅ Configurable |
| Random Selection | ✅ Efficient | ❌ Full scans | ✅ Pre-loaded IDs |
| Metrics | ✅ Steady-state | ❌ Includes cold cache | ✅ Steady-state |

---

## Migration Guide

### Breaking Changes

1. **Import Change:**
   - v1.0 used `threading`
   - v2.0 uses `multiprocessing`
   - **Impact:** If you customized the script, update imports

2. **Statistics Class:**
   - v1.0 used `threading.Lock()`
   - v2.0 uses `multiprocessing.Manager()`
   - **Impact:** Shared state now uses Manager.dict() and Manager.Value()

3. **Output Format:**
   - v2.0 clearly separates warmup from measurement
   - **Impact:** Parse output differently if automated

### Non-Breaking Changes

- All CLI arguments remain backward compatible
- Configuration file format unchanged
- Transaction types unchanged

---

## Technical Details

### Multiprocessing Architecture

```python
# Shared state using Manager
manager = multiprocessing.Manager()
stats = WorkloadStats(manager)

# Each process gets a copy of id_cache (read-only)
for i in range(num_workers):
    p = multiprocessing.Process(
        target=worker_process,
        args=(i+1, config, stats, id_cache, ...)
    )
    p.start()
```

### Warmup Implementation

```python
# Shared boolean flag
stats.warmup_complete = manager.Value('b', False)

# Worker checks flag before recording
def record_transaction(self, tx_type: str, duration: float, success: bool):
    if not self.warmup_complete.value:
        return  # Don't record during warmup
    # ... record metrics
```

### ID Preloading

```python
# Load once at startup
id_cache = preload_ids(config)

# Use in transactions (no database query)
stor_id = random.choice(id_cache['store_ids'])
title_id = random.choice(id_cache['title_ids'])
```

---

## Validation

To verify the improvements are working:

### 1. Check Process Count
```bash
# While test is running
ps aux | grep sybase_ase_hammerdb_workload | wc -l
# Should show: 1 (main) + N (workers) = N+1 processes
```

### 2. Verify Warmup Phase
```bash
# Look for this in output:
⏳ Warmup phase: 30s (warming cache, not measured)...
⏱️  Warmup complete (30s). Starting measurement...
```

### 3. Confirm No Table Scans
```bash
# Check ASE query log (if enabled)
# Should NOT see: ORDER BY NEWID()
# Should see: Direct lookups with WHERE clauses
```

---

## Questions?

**Q: Can I disable warmup for quick tests?**
A: Yes, use `--warmup 0`, but results won't be comparable to production.

**Q: How many workers should I use?**
A: Start with number of CPU cores, then scale up. With multiprocessing, 20-50 workers is reasonable.

**Q: Will this work on Windows?**
A: Yes, but multiprocessing on Windows has limitations. Use `if __name__ == "__main__":` guard.

**Q: Can I still use threading?**
A: v1.0 script is preserved. Use v2.0 for accurate benchmarks.

---

**Version:** 2.0  
**Date:** 2026-03-11  
**Author:** Nao Labs
