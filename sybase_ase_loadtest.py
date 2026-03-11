#!/usr/bin/env python3
"""
Sybase ASE Load Test Script
Tests connection performance, query throughput, and batch fetch speed.
Usage: python sybase_ase_loadtest.py --config configuration.json
"""

import argparse
import json
import time
import sys

try:
    import pyodbc
except ImportError:
    print(" pyodbc not installed. Run: pip install pyodbc")
    sys.exit(1)


def load_config(config_path: str) -> dict:
    try:
        with open(config_path, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f" Config file not found: {config_path}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f" Invalid JSON in config file: {e}")
        sys.exit(1)


def create_connection(config: dict):
    server = config.get("server")
    port = int(config.get("port"))
    database = config.get("database")
    user_id = config.get("user_id")
    password = config.get("password")

    connection_str = (
        f"DRIVER=FreeTDS;"
        f"SERVER={server};"
        f"PORT={port};"
        f"DATABASE={database};"
        f"UID={user_id};"
        f"PWD={password};"
        f"TDS_Version=5.0;"
        f"ClientCharset=UTF-8;"
        f"Timeout=10;"
        f"LoginTimeout=10"
    )
    return pyodbc.connect(connection_str)


def test_connection(config: dict):
    print("\n" + "="*60)
    print("  TEST 1: Connection")
    print("="*60)
    start = time.time()
    try:
        conn = create_connection(config)
        elapsed = time.time() - start
        print(f" Connected to {config['server']}:{config['port']} in {elapsed:.3f}s")
        conn.close()
        return True
    except Exception as e:
        print(f" Connection failed: {e}")
        return False


def test_row_count(config: dict):
    print("\n" + "="*60)
    print("  TEST 2: Row Count & Date Range")
    print("="*60)
    try:
        conn = create_connection(config)
        cursor = conn.cursor()

        start = time.time()
        cursor.execute("SELECT COUNT(*) FROM sales")
        count = cursor.fetchone()[0]
        elapsed = time.time() - start
        print(f" Total rows in sales: {count} (query took {elapsed:.3f}s)")

        cursor.execute("SELECT MIN(date), MAX(date) FROM sales")
        row = cursor.fetchone()
        print(f" Date range: {row[0]} → {row[1]}")

        cursor.close()
        conn.close()
        return count
    except Exception as e:
        print(f" Row count test failed: {e}")
        return 0


def test_batch_fetch(config: dict, batch_size: int = 1000):
    print("\n" + "="*60)
    print(f"  TEST 3: Batch Fetch (batch_size={batch_size})")
    print("="*60)
    try:
        conn = create_connection(config)
        cursor = conn.cursor()

        start = time.time()
        cursor.execute("SELECT * FROM sales ORDER BY date")
        column_names = [col[0] for col in cursor.description]
        print(f" Columns: {column_names}")

        total_rows = 0
        batch_count = 0
        batch_times = []

        while True:
            batch_start = time.time()
            results = cursor.fetchmany(batch_size)
            if not results:
                break
            batch_elapsed = time.time() - batch_start
            batch_times.append(batch_elapsed)
            total_rows += len(results)
            batch_count += 1
            print(f"   Batch {batch_count}: {len(results)} rows in {batch_elapsed:.3f}s")

        total_elapsed = time.time() - start
        avg_batch_time = sum(batch_times) / len(batch_times) if batch_times else 0
        rows_per_sec = total_rows / total_elapsed if total_elapsed > 0 else 0

        print(f"\n Fetched {total_rows} rows in {total_elapsed:.3f}s")
        print(f"   Batches: {batch_count}")
        print(f"   Avg batch time: {avg_batch_time:.3f}s")
        print(f"   Throughput: {rows_per_sec:.1f} rows/sec")

        cursor.close()
        conn.close()
        return total_rows, rows_per_sec
    except Exception as e:
        print(f" Batch fetch test failed: {e}")
        return 0, 0


def test_incremental_query(config: dict, last_created: str = "1970-01-01T00:00:00"):
    print("\n" + "="*60)
    print(f"  TEST 4: Incremental Query (date > '{last_created}')")
    print("="*60)
    try:
        conn = create_connection(config)
        cursor = conn.cursor()

        start = time.time()
        cursor.execute(f"SELECT COUNT(*) FROM sales WHERE date > '{last_created}'")
        count = cursor.fetchone()[0]
        elapsed = time.time() - start
        print(f" Rows with date > '{last_created}': {count} (query took {elapsed:.3f}s)")

        cursor.close()
        conn.close()
        return count
    except Exception as e:
        print(f" Incremental query test failed: {e}")
        return 0


def print_summary(conn_ok, row_count, rows_per_sec, incremental_count):
    print("\n" + "="*60)
    print("  SUMMARY")
    print("="*60)
    print(f"  Connection:        {' OK' if conn_ok else ' FAILED'}")
    print(f"  Total rows:        {row_count}")
    print(f"  Throughput:        {rows_per_sec:.1f} rows/sec")
    print(f"  Incremental rows:  {incremental_count}")
    if rows_per_sec > 0 and row_count > 0:
        est_sync_time = row_count / rows_per_sec
        print(f"  Est. full sync:    {est_sync_time:.1f}s ({est_sync_time/60:.1f} min)")
    print("="*60)


def main():
    parser = argparse.ArgumentParser(description="Sybase ASE Load Test")
    parser.add_argument("--config", required=True, help="Path to configuration.json")
    parser.add_argument("--batch-size", type=int, default=1000, help="Batch size for fetch test (default: 1000)")
    parser.add_argument("--last-created", default="1970-01-01T00:00:00", help="Last created timestamp for incremental test")
    args = parser.parse_args()

    print("\n" + "="*60)
    print("  Sybase ASE Load Test")
    print("="*60)

    config = load_config(args.config)
    print(f"  Server:   {config.get('server')}:{config.get('port')}")
    print(f"  Database: {config.get('database')}")
    print(f"  User:     {config.get('user_id')}")

    conn_ok = test_connection(config)
    if not conn_ok:
        print("\n Cannot proceed - connection failed.")
        sys.exit(1)

    row_count = test_row_count(config)
    total_rows, rows_per_sec = test_batch_fetch(config, batch_size=args.batch_size)
    incremental_count = test_incremental_query(config, last_created=args.last_created)

    print_summary(conn_ok, row_count, rows_per_sec, incremental_count)


if __name__ == "__main__":
    main()