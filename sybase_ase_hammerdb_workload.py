#!/usr/bin/env python3
"""
Sybase ASE HammerDB-Style Workload Generator for pubs2 Database

This script simulates a TPC-C-like workload for the classic pubs2 bookstore schema.
It generates concurrent transactions across multiple worker threads to test database
performance, throughput, and concurrency handling.

TRANSACTION MIX (TPC-C inspired):
  - New Sale (45%):        Insert new orders into sales/salesdetail, update inventory
  - Payment (15%):         Update royalty schedules (write operations)
  - Order Status (15%):    Query order history with joins (read operations)
  - Delivery (10%):        Update order quantities (write operations)
  - Stock Level (10%):     Check inventory levels (read operations)
  - Author Lookup (3%):    Complex multi-table joins (read operations)
  - Publisher Report (2%): Aggregation queries (read operations)

USAGE:
  # Discover schema only
  python sybase_ase_hammerdb_workload.py --config configuration.json --discover-only

  # Run workload with defaults (10 workers, 60 seconds)
  python sybase_ase_hammerdb_workload.py --config configuration.json

  # Run with custom settings
  python sybase_ase_hammerdb_workload.py --config configuration.json --workers 20 --duration 300

METRICS REPORTED:
  - Transactions per second (TPS) overall and per transaction type
  - Average/min/max response times
  - Error counts and success rates
  - Total throughput under concurrent load

Author: Nao Labs
Version: 1.0
"""

import argparse
import json
import time
import sys
import random
import threading
from datetime import datetime, timedelta
from typing import List, Dict, Tuple
from collections import defaultdict

try:
    import pyodbc
except ImportError:
    print(" pyodbc not installed. Run: pip install pyodbc")
    sys.exit(1)


# ============================================================================
# Configuration & Connection
# ============================================================================

def load_config(config_path: str) -> dict:
    """Load configuration from JSON file."""
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
    """Create a connection to Sybase ASE."""
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
    return pyodbc.connect(connection_str, autocommit=False)


# ============================================================================
# Schema Discovery
# ============================================================================

def discover_schema(config: dict) -> Dict[str, List[str]]:
    """Discover all tables and their columns in pubs2."""
    print("\n" + "="*70)
    print("  SCHEMA DISCOVERY")
    print("="*70)
    
    conn = create_connection(config)
    cursor = conn.cursor()
    
    # Get all user tables
    cursor.execute("""
        SELECT name 
        FROM sysobjects 
        WHERE type = 'U' 
        ORDER BY name
    """)
    
    tables = [row[0] for row in cursor.fetchall()]
    schema = {}
    
    for table in tables:
        cursor.execute(f"SELECT * FROM {table} WHERE 1=0")
        columns = [col[0] for col in cursor.description]
        schema[table] = columns
        print(f"  📋 {table}: {', '.join(columns)}")
    
    cursor.close()
    conn.close()
    
    return schema


# ============================================================================
# Workload Statistics
# ============================================================================

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


# ============================================================================
# Transaction Types (pubs2 specific)
# ============================================================================

class Pubs2Workload:
    """pubs2 database workload generator."""
    
    def __init__(self, config: dict, stats: WorkloadStats, verbose: bool = False):
        self.config = config
        self.stats = stats
        self.running = True
        self.verbose = verbose
    
    def new_sale_transaction(self, conn, cursor) -> bool:
        """Simulate a new book sale (similar to TPC-C New Order)."""
        try:
            # Get random store
            cursor.execute("SELECT TOP 1 stor_id FROM stores ORDER BY NEWID()")
            store = cursor.fetchone()
            if not store:
                return False
            stor_id = store[0]
            
            # Get random title
            cursor.execute("SELECT TOP 1 title_id FROM titles ORDER BY NEWID()")
            title = cursor.fetchone()
            if not title:
                return False
            title_id = title[0]
            
            # Generate unique order number with timestamp to avoid collisions
            ord_num = f"ORD{int(time.time() * 1000) % 1000000000}{random.randint(100, 999)}"
            qty = random.randint(1, 50)
            discount = round(random.uniform(0, 10), 2)
            sale_date = datetime.now().strftime('%Y-%m-%d')
            
            # Insert into sales table (only stor_id, ord_num, date)
            cursor.execute("""
                INSERT INTO sales (stor_id, ord_num, date)
                VALUES (?, ?, ?)
            """, stor_id, ord_num, sale_date)
            
            # Insert into salesdetail table (qty, title_id, discount)
            cursor.execute("""
                INSERT INTO salesdetail (stor_id, ord_num, title_id, qty, discount)
                VALUES (?, ?, ?, ?, ?)
            """, stor_id, ord_num, title_id, qty, discount)
            
            # Update title inventory (total_sales)
            cursor.execute("""
                UPDATE titles 
                SET total_sales = ISNULL(total_sales, 0) + ?
                WHERE title_id = ?
            """, qty, title_id)
            
            conn.commit()
            return True
            
        except Exception as e:
            conn.rollback()
            if self.verbose:
                print(f"    New Sale error: {e}")
            return False
    
    def payment_transaction(self, conn, cursor) -> bool:
        """Simulate a payment/royalty update (similar to TPC-C Payment)."""
        try:
            # Get random title and update royalty
            cursor.execute("SELECT TOP 1 title_id FROM roysched ORDER BY NEWID()")
            title = cursor.fetchone()
            if not title:
                return False
            title_id = title[0]
            
            # Update royalty schedule
            cursor.execute("""
                UPDATE roysched
                SET royalty = royalty + ?
                WHERE title_id = ?
            """, random.uniform(0.5, 2.0), title_id)
            
            conn.commit()
            return True
            
        except Exception as e:
            conn.rollback()
            return False
    
    def order_status_query(self, conn, cursor) -> bool:
        """Query order status (similar to TPC-C Order Status)."""
        try:
            # Get random store's orders with details
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
            return len(results) > 0
            
        except Exception as e:
            return False
    
    def delivery_transaction(self, conn, cursor) -> bool:
        """Simulate book delivery/shipment (similar to TPC-C Delivery)."""
        try:
            # Update oldest pending sales - reduce quantities
            cursor.execute("""
                UPDATE salesdetail
                SET qty = qty - 1
                WHERE (stor_id, ord_num) IN (
                    SELECT TOP 10 s.stor_id, s.ord_num
                    FROM sales s
                    JOIN salesdetail sd ON s.stor_id = sd.stor_id AND s.ord_num = sd.ord_num
                    WHERE sd.qty > 1
                    ORDER BY s.date ASC
                )
            """)
            
            conn.commit()
            return True
            
        except Exception as e:
            conn.rollback()
            return False
    
    def stock_level_query(self, conn, cursor) -> bool:
        """Query inventory levels (similar to TPC-C Stock Level)."""
        try:
            # Check low stock titles
            cursor.execute("""
                SELECT t.title_id, t.title, t.type, 
                       ISNULL(t.total_sales, 0) as total_sales,
                       (SELECT SUM(qty) FROM salesdetail WHERE title_id = t.title_id) as total_ordered
                FROM titles t
                WHERE ISNULL(t.total_sales, 0) < 5000
                ORDER BY total_sales ASC
            """)
            
            results = cursor.fetchall()
            return len(results) > 0
            
        except Exception as e:
            return False
    
    def author_lookup_query(self, conn, cursor) -> bool:
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
            return len(results) > 0
            
        except Exception as e:
            return False
    
    def publisher_report_query(self, conn, cursor) -> bool:
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
            return len(results) > 0
            
        except Exception as e:
            return False


# ============================================================================
# Worker Thread
# ============================================================================

def worker_thread(worker_id: int, config: dict, workload: Pubs2Workload, 
                  duration_seconds: int, transaction_mix: Dict[str, int]):
    """Worker thread that executes random transactions."""
    
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
                if tx_type == 'new_sale':
                    success = workload.new_sale_transaction(conn, cursor)
                elif tx_type == 'payment':
                    success = workload.payment_transaction(conn, cursor)
                elif tx_type == 'order_status':
                    success = workload.order_status_query(conn, cursor)
                elif tx_type == 'delivery':
                    success = workload.delivery_transaction(conn, cursor)
                elif tx_type == 'stock_level':
                    success = workload.stock_level_query(conn, cursor)
                elif tx_type == 'author_lookup':
                    success = workload.author_lookup_query(conn, cursor)
                elif tx_type == 'publisher_report':
                    success = workload.publisher_report_query(conn, cursor)
                
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
            print(f"   Worker {worker_id} completed {tx_count} transactions")
        
    except Exception as e:
        print(f"   Worker {worker_id} crashed: {e}")


# ============================================================================
# Main Workload Runner
# ============================================================================

def run_workload(config: dict, num_workers: int = 10, duration_seconds: int = 60, verbose: bool = False):
    """Run the HammerDB-style workload."""
    
    print("\n" + "="*70)
    print("  HAMMERDB-STYLE WORKLOAD TEST")
    print("="*70)
    print(f"  Workers:  {num_workers}")
    print(f"  Duration: {duration_seconds}s")
    print("="*70)
    
    # Transaction mix (weights)
    transaction_mix = {
        'new_sale': 45,          # 45% new sales (write-heavy)
        'payment': 15,           # 15% payments (write)
        'order_status': 15,      # 15% order queries (read)
        'delivery': 10,          # 10% deliveries (write)
        'stock_level': 10,       # 10% stock queries (read)
        'author_lookup': 3,      # 3% complex joins (read)
        'publisher_report': 2    # 2% aggregations (read)
    }
    
    stats = WorkloadStats()
    workload = Pubs2Workload(config, stats, verbose)
    
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


# ============================================================================
# Main Entry Point
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description="Sybase ASE HammerDB-Style Workload")
    parser.add_argument("--config", required=True, help="Path to configuration.json")
    parser.add_argument("--workers", type=int, default=10, help="Number of concurrent workers (default: 10)")
    parser.add_argument("--duration", type=int, default=60, help="Test duration in seconds (default: 60)")
    parser.add_argument("--discover-only", action="store_true", help="Only discover schema and exit")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
    args = parser.parse_args()

    print("\n" + "="*70)
    print("  Sybase ASE HammerDB-Style Workload Generator")
    print("="*70)

    config = load_config(args.config)
    print(f"  Server:   {config.get('server')}:{config.get('port')}")
    print(f"  Database: {config.get('database')}")
    print(f"  User:     {config.get('user_id')}")

    # Discover schema
    schema = discover_schema(config)
    
    if args.discover_only:
        print("\n Schema discovery complete. Exiting.")
        return
    
    # Run workload
    run_workload(config, num_workers=args.workers, duration_seconds=args.duration, verbose=args.verbose)
    
    print("\n✅ Workload test complete!")


if __name__ == "__main__":
    main()
