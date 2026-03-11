#!/usr/bin/env python3
"""
Sybase ASE HammerDB-Style Workload Generator (Read-Only Version)

This is a READ-ONLY version of the workload that avoids transaction log issues.
Perfect for testing connection performance and query throughput without writes.

USAGE:
  python sybase_ase_hammerdb_workload_readonly.py --config configuration.json --workers 10 --duration 60
"""

import argparse
import json
import time
import sys
import random
import threading
from datetime import datetime
from typing import List, Dict
from collections import defaultdict

try:
    import pyodbc
except ImportError:
    print("❌ pyodbc not installed. Run: pip install pyodbc")
    sys.exit(1)


def load_config(config_path: str) -> dict:
    """Load configuration from JSON file."""
    try:
        with open(config_path, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"❌ Config file not found: {config_path}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON in config file: {e}")
        sys.exit(1)


def create_connection(config: dict):
    """Create a connection to Sybase ASE with autocommit (read-only safe)."""
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
        f"Timeout=30;"
        f"LoginTimeout=10"
    )
    # Use autocommit=True to avoid transaction log issues
    return pyodbc.connect(connection_str, autocommit=True)


class WorkloadStats:
    """Thread-safe statistics collector."""
    
    def __init__(self):
        self.lock = threading.Lock()
        self.transaction_counts = defaultdict(int)
        self.transaction_times = defaultdict(list)
        self.errors = defaultdict(int)
        self.start_time = time.time()
    
    def record_transaction(self, tx_type: str, duration: float, success: bool = True):
        """Record a transaction result."""
        with self.lock:
            self.transaction_counts[tx_type] += 1
            self.transaction_times[tx_type].append(duration)
            if not success:
                self.errors[tx_type] += 1
    
    def get_summary(self) -> Dict:
        """Get summary statistics."""
        with self.lock:
            total_time = time.time() - self.start_time
            summary = {
                'total_time': total_time,
                'transactions': {},
                'total_tx': sum(self.transaction_counts.values()),
                'total_errors': sum(self.errors.values())
            }
            
            for tx_type, count in self.transaction_counts.items():
                times = self.transaction_times[tx_type]
                summary['transactions'][tx_type] = {
                    'count': count,
                    'errors': self.errors[tx_type],
                    'avg_time': sum(times) / len(times) if times else 0,
                    'min_time': min(times) if times else 0,
                    'max_time': max(times) if times else 0,
                    'tps': count / total_time if total_time > 0 else 0
                }
            
            return summary


class Pubs2ReadOnlyWorkload:
    """pubs2 database READ-ONLY workload generator."""
    
    def __init__(self, config: dict, stats: WorkloadStats, verbose: bool = False):
        self.config = config
        self.stats = stats
        self.running = True
        self.verbose = verbose
    
    def order_status_query(self, cursor) -> bool:
        """Query order status with joins."""
        try:
            cursor.execute("""
                SELECT s.stor_id, st.stor_name, s.ord_num, s.date, 
                       sd.title_id, t.title, sd.qty, sd.discount
                FROM sales s
                JOIN stores st ON s.stor_id = st.stor_id
                JOIN salesdetail sd ON s.stor_id = sd.stor_id AND s.ord_num = sd.ord_num
                JOIN titles t ON sd.title_id = t.title_id
                WHERE s.stor_id = (SELECT TOP 1 stor_id FROM stores ORDER BY NEWID())
                ORDER BY s.date DESC
            """)
            results = cursor.fetchall()
            return len(results) >= 0  # Success even if empty
        except Exception as e:
            if self.verbose:
                print(f"  ⚠️  Order Status query failed: {e}")
            return False
    
    def stock_level_query(self, cursor) -> bool:
        """Query inventory levels."""
        try:
            cursor.execute("""
                SELECT t.title_id, t.title, t.type, 
                       ISNULL(t.total_sales, 0) as total_sales,
                       (SELECT SUM(qty) FROM salesdetail WHERE title_id = t.title_id) as total_ordered
                FROM titles t
                WHERE ISNULL(t.total_sales, 0) < 5000
                ORDER BY total_sales ASC
            """)
            results = cursor.fetchall()
            return len(results) >= 0
        except Exception as e:
            if self.verbose:
                print(f"  ⚠️  Stock Level query failed: {e}")
            return False
    
    def author_lookup_query(self, cursor) -> bool:
        """Complex author/title join query."""
        try:
            cursor.execute("""
                SELECT a.au_lname, a.au_fname, t.title, t.price, ta.royaltyper
                FROM authors a
                JOIN titleauthor ta ON a.au_id = ta.au_id
                JOIN titles t ON ta.title_id = t.title_id
                WHERE a.state = 'CA'
                ORDER BY a.au_lname, t.title
            """)
            results = cursor.fetchall()
            return len(results) >= 0
        except Exception as e:
            if self.verbose:
                print(f"  ⚠️  Author Lookup failed: {e}")
            return False
    
    def publisher_report_query(self, cursor) -> bool:
        """Complex publisher aggregation query."""
        try:
            cursor.execute("""
                SELECT p.pub_name, 
                       COUNT(DISTINCT t.title_id) as num_titles,
                       SUM(ISNULL(t.total_sales, 0)) as total_sales,
                       AVG(t.price) as avg_price
                FROM publishers p
                LEFT JOIN titles t ON p.pub_id = t.pub_id
                GROUP BY p.pub_name
                ORDER BY total_sales DESC
            """)
            results = cursor.fetchall()
            return len(results) >= 0
        except Exception as e:
            if self.verbose:
                print(f"  ⚠️  Publisher Report failed: {e}")
            return False
    
    def sales_analysis_query(self, cursor) -> bool:
        """Analyze sales by store."""
        try:
            cursor.execute("""
                SELECT st.stor_name, 
                       COUNT(DISTINCT s.ord_num) as num_orders,
                       SUM(sd.qty) as total_qty,
                       AVG(sd.discount) as avg_discount
                FROM stores st
                LEFT JOIN sales s ON st.stor_id = s.stor_id
                LEFT JOIN salesdetail sd ON s.stor_id = sd.stor_id AND s.ord_num = sd.ord_num
                GROUP BY st.stor_name
                ORDER BY total_qty DESC
            """)
            results = cursor.fetchall()
            return len(results) >= 0
        except Exception as e:
            if self.verbose:
                print(f"  ⚠️  Sales Analysis failed: {e}")
            return False
    
    def title_search_query(self, cursor) -> bool:
        """Search titles by type."""
        try:
            title_types = ['business', 'psychology', 'mod_cook', 'trad_cook', 'popular_comp']
            title_type = random.choice(title_types)
            cursor.execute("""
                SELECT title_id, title, type, price, pubdate
                FROM titles
                WHERE type = ?
                ORDER BY price DESC
            """, title_type)
            results = cursor.fetchall()
            return len(results) >= 0
        except Exception as e:
            if self.verbose:
                print(f"  ⚠️  Title Search failed: {e}")
            return False
    
    def royalty_report_query(self, cursor) -> bool:
        """Generate royalty report."""
        try:
            cursor.execute("""
                SELECT a.au_lname, a.au_fname, 
                       t.title, ta.royaltyper,
                       ISNULL(t.total_sales, 0) * t.price * (ta.royaltyper / 100.0) as estimated_royalty
                FROM authors a
                JOIN titleauthor ta ON a.au_id = ta.au_id
                JOIN titles t ON ta.title_id = t.title_id
                WHERE t.price IS NOT NULL
                ORDER BY estimated_royalty DESC
            """)
            results = cursor.fetchall()
            return len(results) >= 0
        except Exception as e:
            if self.verbose:
                print(f"  ⚠️  Royalty Report failed: {e}")
            return False


def worker_thread(worker_id: int, config: dict, workload: Pubs2ReadOnlyWorkload, 
                  duration_seconds: int, transaction_mix: Dict[str, int]):
    """Worker thread that executes random read-only transactions."""
    
    if workload.verbose:
        print(f"  🔧 Worker {worker_id} started")
    
    try:
        conn = create_connection(config)
        cursor = conn.cursor()
        
        # Build weighted transaction list
        tx_list = []
        for tx_type, weight in transaction_mix.items():
            tx_list.extend([tx_type] * weight)
        
        start_time = time.time()
        tx_count = 0
        
        while workload.running and (time.time() - start_time) < duration_seconds:
            # Select random transaction type
            tx_type = random.choice(tx_list)
            
            tx_start = time.time()
            success = False
            
            try:
                if tx_type == 'order_status':
                    success = workload.order_status_query(cursor)
                elif tx_type == 'stock_level':
                    success = workload.stock_level_query(cursor)
                elif tx_type == 'author_lookup':
                    success = workload.author_lookup_query(cursor)
                elif tx_type == 'publisher_report':
                    success = workload.publisher_report_query(cursor)
                elif tx_type == 'sales_analysis':
                    success = workload.sales_analysis_query(cursor)
                elif tx_type == 'title_search':
                    success = workload.title_search_query(cursor)
                elif tx_type == 'royalty_report':
                    success = workload.royalty_report_query(cursor)
                
                tx_duration = time.time() - tx_start
                workload.stats.record_transaction(tx_type, tx_duration, success)
                tx_count += 1
                
                # Small delay to avoid overwhelming the database
                time.sleep(random.uniform(0.01, 0.05))
                
            except Exception as e:
                tx_duration = time.time() - tx_start
                workload.stats.record_transaction(tx_type, tx_duration, False)
        
        cursor.close()
        conn.close()
        if workload.verbose:
            print(f"  ✅ Worker {worker_id} completed {tx_count} transactions")
        
    except Exception as e:
        print(f"  ❌ Worker {worker_id} crashed: {e}")


def run_workload(config: dict, num_workers: int = 10, duration_seconds: int = 60, verbose: bool = False):
    """Run the READ-ONLY workload."""
    
    print("\n" + "="*70)
    print("  HAMMERDB-STYLE WORKLOAD TEST (READ-ONLY)")
    print("="*70)
    print(f"  Workers:  {num_workers}")
    print(f"  Duration: {duration_seconds}s")
    print(f"  Mode:     READ-ONLY (No transaction log issues)")
    print("="*70)
    
    # Transaction mix (READ-ONLY queries only)
    transaction_mix = {
        'order_status': 25,      # 25% order queries
        'stock_level': 20,       # 20% stock queries
        'author_lookup': 20,     # 20% complex joins
        'publisher_report': 15,  # 15% aggregations
        'sales_analysis': 10,    # 10% sales analysis
        'title_search': 5,       # 5% title searches
        'royalty_report': 5      # 5% royalty reports
    }
    
    stats = WorkloadStats()
    workload = Pubs2ReadOnlyWorkload(config, stats, verbose)
    
    # Start worker threads
    threads = []
    start_time = time.time()
    
    for i in range(num_workers):
        t = threading.Thread(
            target=worker_thread,
            args=(i+1, config, workload, duration_seconds, transaction_mix)
        )
        t.start()
        threads.append(t)
        time.sleep(0.1)  # Stagger thread starts
    
    # Wait for completion
    for t in threads:
        t.join()
    
    workload.running = False
    total_time = time.time() - start_time
    
    # Print results
    print("\n" + "="*70)
    print("  WORKLOAD RESULTS")
    print("="*70)
    
    summary = stats.get_summary()
    
    print(f"  Total Time:     {summary['total_time']:.2f}s")
    print(f"  Total TX:       {summary['total_tx']}")
    print(f"  Total Errors:   {summary['total_errors']}")
    print(f"  Overall TPS:    {summary['total_tx'] / summary['total_time']:.2f}")
    print("\n" + "-"*70)
    print(f"  {'Transaction Type':<20} {'Count':>8} {'Errors':>8} {'Avg(ms)':>10} {'TPS':>10}")
    print("-"*70)
    
    for tx_type, tx_stats in sorted(summary['transactions'].items()):
        print(f"  {tx_type:<20} {tx_stats['count']:>8} {tx_stats['errors']:>8} "
              f"{tx_stats['avg_time']*1000:>10.2f} {tx_stats['tps']:>10.2f}")
    
    print("="*70)


def main():
    parser = argparse.ArgumentParser(description="Sybase ASE HammerDB-Style Workload (READ-ONLY)")
    parser.add_argument("--config", required=True, help="Path to configuration.json")
    parser.add_argument("--workers", type=int, default=10, help="Number of concurrent workers (default: 10)")
    parser.add_argument("--duration", type=int, default=60, help="Test duration in seconds (default: 60)")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
    args = parser.parse_args()

    print("\n" + "="*70)
    print("  Sybase ASE HammerDB-Style Workload Generator (READ-ONLY)")
    print("="*70)

    config = load_config(args.config)
    print(f"  Server:   {config.get('server')}:{config.get('port')}")
    print(f"  Database: {config.get('database')}")
    print(f"  User:     {config.get('user_id')}")
    
    # Run workload
    run_workload(config, num_workers=args.workers, duration_seconds=args.duration, verbose=args.verbose)
    
    print("\n✅ Workload test complete!")


if __name__ == "__main__":
    main()
