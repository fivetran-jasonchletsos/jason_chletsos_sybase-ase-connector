# Code Comparison: v1.0 vs v2.0

## 1. Worker Execution Model

### v1.0 - Threading (GIL-limited)
```python
import threading

def worker_thread(worker_id, config, workload, duration_seconds, transaction_mix):
    conn = create_connection(config)
    cursor = conn.cursor()
    
    start_time = time.time()
    while (time.time() - start_time) < duration_seconds:
        tx_type = random.choice(tx_list)
        success = execute_transaction(tx_type)
        stats.record_transaction(tx_type, duration, success)

# Start workers
threads = []
for i in range(num_workers):
    t = threading.Thread(target=worker_thread, args=(...))
    t.start()
    threads.append(t)
```

### v2.0 - Multiprocessing (True Parallelism)
```python
import multiprocessing

def worker_process(worker_id, config, stats, id_cache, 
                   duration_seconds, warmup_seconds, transaction_mix):
    conn = create_connection(config)
    cursor = conn.cursor()
    
    start_time = time.time()
    while (time.time() - start_time) < (warmup_seconds + duration_seconds):
        elapsed = time.time() - start_time
        
        # Check if warmup just completed
        if elapsed >= warmup_seconds and not stats.warmup_complete.value:
            stats.warmup_complete.value = True
            stats.start_time.value = time.time()
        
        tx_type = random.choice(tx_list)
        success = execute_transaction(tx_type)
        stats.record_transaction(tx_type, duration, success)  # Ignored during warmup

# Start workers
processes = []
for i in range(num_workers):
    p = multiprocessing.Process(target=worker_process, args=(...))
    p.start()
    processes.append(p)
```

**Key Difference:** `threading.Thread` → `multiprocessing.Process`

---

## 2. Statistics Collection

### v1.0 - Thread-Safe (threading.Lock)
```python
class WorkloadStats:
    def __init__(self):
        self.lock = threading.Lock()
        self.transaction_counts = defaultdict(int)
        self.transaction_times = defaultdict(list)
        self.errors = defaultdict(int)
        self.start_time = time.time()
    
    def record_transaction(self, tx_type, duration, success=True):
        with self.lock:
            self.transaction_counts[tx_type] += 1
            self.transaction_times[tx_type].append(duration)
            if not success:
                self.errors[tx_type] += 1
```

### v2.0 - Process-Safe (multiprocessing.Manager)
```python
class WorkloadStats:
    def __init__(self, manager):
        self.lock = manager.Lock()
        self.transaction_counts = manager.dict()
        self.transaction_times = manager.dict()
        self.errors = manager.dict()
        self.start_time = manager.Value('d', 0.0)
        self.warmup_complete = manager.Value('b', False)
    
    def record_transaction(self, tx_type, duration, success=True):
        if not self.warmup_complete.value:
            return  # Don't record during warmup
        
        with self.lock:
            if tx_type not in self.transaction_counts:
                self.transaction_counts[tx_type] = 0
                self.transaction_times[tx_type] = []
                self.errors[tx_type] = 0
            
            self.transaction_counts[tx_type] += 1
            
            # Manager.dict requires copy-modify-reassign pattern
            times = list(self.transaction_times[tx_type])
            times.append(duration)
            self.transaction_times[tx_type] = times
            
            if not success:
                self.errors[tx_type] += 1
```

**Key Differences:**
- `threading.Lock()` → `manager.Lock()`
- `defaultdict()` → `manager.dict()`
- Added `warmup_complete` flag
- Manager.dict requires copy-modify-reassign for lists

---

## 3. Random Selection

### v1.0 - Full Table Scan Every Time
```python
def new_sale_transaction(self, conn, cursor):
    # Get random store - FULL TABLE SCAN!
    cursor.execute("SELECT TOP 1 stor_id FROM stores ORDER BY NEWID()")
    store = cursor.fetchone()
    stor_id = store[0]
    
    # Get random title - FULL TABLE SCAN!
    cursor.execute("SELECT TOP 1 title_id FROM titles ORDER BY NEWID()")
    title = cursor.fetchone()
    title_id = title[0]
    
    # ... rest of transaction
```

### v2.0 - Pre-loaded IDs (No Database Query)
```python
# At startup - load once
def preload_ids(config):
    conn = create_connection(config)
    cursor = conn.cursor()
    
    id_cache = {}
    
    cursor.execute("SELECT stor_id FROM stores")
    id_cache['store_ids'] = [row[0] for row in cursor.fetchall()]
    
    cursor.execute("SELECT title_id FROM titles")
    id_cache['title_ids'] = [row[0] for row in cursor.fetchall()]
    
    return id_cache

# In transaction - use cached IDs
def new_sale_transaction(self, conn, cursor):
    # Get random store - NO DATABASE QUERY!
    stor_id = random.choice(self.id_cache['store_ids'])
    
    # Get random title - NO DATABASE QUERY!
    title_id = random.choice(self.id_cache['title_ids'])
    
    # ... rest of transaction
```

**Key Difference:** Database query eliminated from transaction hot path

---

## 4. Warmup Implementation

### v1.0 - No Warmup
```python
def run_workload(config, num_workers, duration_seconds):
    stats = WorkloadStats()
    
    # Start workers immediately
    for i in range(num_workers):
        t = threading.Thread(target=worker_thread, args=(...))
        t.start()
    
    # All transactions recorded from start
```

### v2.0 - Warmup Phase
```python
def run_workload(config, num_workers, duration_seconds, warmup_seconds):
    manager = multiprocessing.Manager()
    stats = WorkloadStats(manager)
    
    # Start workers (they run warmup first)
    for i in range(num_workers):
        p = multiprocessing.Process(target=worker_process, args=(...))
        p.start()
    
    # Worker logic:
    while (time.time() - start_time) < (warmup_seconds + duration_seconds):
        elapsed = time.time() - start_time
        
        # Transition from warmup to measurement
        if elapsed >= warmup_seconds and not stats.warmup_complete.value:
            if worker_id == 1:
                print("⏱️  Warmup complete. Starting measurement...")
            stats.warmup_complete.value = True
            stats.start_time.value = time.time()
        
        # Execute transaction
        execute_transaction(...)
        
        # Record (ignored if warmup not complete)
        stats.record_transaction(...)  # Checks warmup_complete flag
```

**Key Difference:** Two-phase execution with flag-based transition

---

## 5. Main Entry Point

### v1.0
```python
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--workers", type=int, default=10)
    parser.add_argument("--duration", type=int, default=60)
    # No --warmup argument
    
    config = load_config(args.config)
    schema = discover_schema(config)
    
    run_workload(config, args.workers, args.duration)
```

### v2.0
```python
def main():
    parser = argparse.ArgumentParser(description="Sybase ASE HammerDB-Style Workload v2.0")
    parser.add_argument("--config", required=True)
    parser.add_argument("--workers", type=int, default=10)
    parser.add_argument("--duration", type=int, default=60)
    parser.add_argument("--warmup", type=int, default=30)  # NEW
    
    config = load_config(args.config)
    schema = discover_schema(config)
    
    # Preload IDs before starting workers
    id_cache = preload_ids(config)  # NEW
    
    run_workload(config, args.workers, args.duration, args.warmup)
```

**Key Differences:**
- Added `--warmup` argument
- Added `preload_ids()` call before workload starts

---

## 6. Output Format

### v1.0
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
  Overall TPS:    53.98
```

### v2.0
```
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
  Overall TPS:      80.48
```

**Key Differences:**
- Shows ID preloading phase
- Shows warmup progress
- Clarifies measurement vs warmup time
- Higher TPS (expected due to improvements)

---

## Summary of Changes

| Aspect | v1.0 | v2.0 |
|--------|------|------|
| **Parallelism** | threading (GIL-limited) | multiprocessing (true parallel) |
| **Shared State** | threading.Lock | multiprocessing.Manager |
| **Warmup** | None | Configurable (default 30s) |
| **Random Selection** | `ORDER BY NEWID()` | Pre-loaded IDs |
| **Metrics** | All transactions | Measurement period only |
| **CLI Args** | 3 args | 4 args (added --warmup) |
| **Startup** | Immediate | Preload IDs first |
| **Output** | Single phase | Two phases (warmup + measure) |

---

## Migration Checklist

- [ ] Update imports: `threading` → `multiprocessing`
- [ ] Update worker function signature (add `id_cache`, `warmup_seconds`)
- [ ] Update stats class to use Manager
- [ ] Add `preload_ids()` function
- [ ] Update transaction methods to use `id_cache`
- [ ] Add warmup logic to worker loop
- [ ] Update CLI to add `--warmup` argument
- [ ] Update output messages
- [ ] Test with small workload first
- [ ] Compare results with v1.0

---

**All changes implemented in:** `sybase_ase_hammerdb_workload.py`
