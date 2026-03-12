# Workload Generator v2.0 - Quick Reference

## What's New in v2.0?

| Improvement | Benefit |
|-------------|---------|
| 🔄 **Multiprocessing** | True parallel execution (bypasses Python GIL) |
| 🔥 **Warmup Period** | Measures steady-state, not cold cache (default 30s) |
| ⚡ **Pre-loaded IDs** | No `ORDER BY NEWID()` scans in transactions |

---

## Quick Start

```bash
# Default (10 workers, 30s warmup, 60s test)
python sybase_ase_hammerdb_workload.py --config configuration.json

# Custom
python sybase_ase_hammerdb_workload.py \
  --config configuration.json \
  --workers 20 \
  --warmup 60 \
  --duration 300
```

---

## CLI Arguments

| Argument | Default | Description |
|----------|---------|-------------|
| `--config` | *required* | Path to configuration.json |
| `--workers` | 10 | Number of concurrent processes |
| `--duration` | 60 | Test duration in seconds (measured) |
| `--warmup` | 30 | Warmup period in seconds (not measured) |
| `--discover-only` | false | Only discover schema and exit |
| `--verbose` | false | Enable verbose output |

---

## Best Practices

1. ✅ **Always use warmup** (minimum 30s, 60-120s for production)
2. ✅ **Start small** (5-10 workers, then scale up)
3. ✅ **Monitor ASE** (use `sp_sysmon` or `sp_who` during tests)
4. ✅ **Document results** (save output for comparison)
5. ✅ **Clean data** (reset pubs2 between major test runs)

---

## Comparison: v1.0 vs v2.0

| Aspect | v1.0 | v2.0 |
|--------|------|------|
| **Execution** | Threading (GIL-limited) | Multiprocessing (true parallel) |
| **Warmup** | None | Configurable (default 30s) |
| **Random Selection** | `ORDER BY NEWID()` (scans) | Pre-loaded IDs (no scans) |
| **Metrics** | All transactions | Measurement period only |
| **Expected TPS** | ~50-60 | ~80-100 (+40-50%) |

---

**Version:** 2.0  
**Last Updated:** 2026-03-11  
**Author:** Nao Labs
