"""
Script to manage data variations and assignments in the FinOps database
"""
import sqlite3
import random
import json
import argparse
from datetime import datetime
import pandas as pd
import numpy as np

def add_variations(type="cost", month_range=None):
    """Add cost or usage variations to billing data"""
    conn = sqlite3.connect('data/billing.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute('BEGIN TRANSACTION')
        
        if not month_range:
            # Get all available months
            cursor.execute("SELECT DISTINCT invoice_month FROM billing ORDER BY invoice_month")
            months = [row[0] for row in cursor.fetchall()]
        else:
            months = month_range
            
        # Add seasonal patterns
        seasonal_factors = {
            "01": 0.8, "02": 0.8,  # Lower in winter
            "03": 0.9, "04": 0.9, "05": 0.9,  # Normal in spring
            "06": 1.2, "07": 1.2, "08": 1.2,  # Higher in summer
            "09": 1.0, "10": 1.0,  # Normal in fall
            "11": 1.3, "12": 1.3,  # Peak in holiday season
        }
        
        for month in months:
            month_num = month.split('-')[1]
            seasonal = seasonal_factors.get(month_num, 1.0)
            
            # Apply seasonal factor with some randomness
            cursor.execute("""
                UPDATE billing 
                SET cost = ROUND(cost * ? * (0.9 + (RANDOM() % 100) / 100.0), 2)
                WHERE invoice_month = ?
            """, (seasonal, month))
            
            # Add service-specific patterns
            if type == "cost":
                # Compute services cost more in summer
                cursor.execute("""
                    UPDATE billing 
                    SET cost = ROUND(cost * 1.3, 2)
                    WHERE invoice_month = ? 
                    AND service = 'Compute'
                    AND strftime('%m', invoice_month) IN ('06','07','08')
                """, (month,))
                
                # Storage grows steadily
                cursor.execute("""
                    UPDATE billing 
                    SET cost = ROUND(cost * (1.0 + (strftime('%m', invoice_month) - '01') * 0.02), 2)
                    WHERE invoice_month = ? 
                    AND service = 'Storage'
                """, (month,))
        
        cursor.execute('COMMIT')
        print(f"Added {type} variations to billing data")
        
    except Exception as e:
        cursor.execute('ROLLBACK')
        print(f"Error: {str(e)}")
        raise
    finally:
        conn.close()

def update_assignments(unassigned_pct=10, partial_pct=12):
    """Update resource assignments with specified percentages of unassigned resources"""
    conn = sqlite3.connect('data/billing.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute('BEGIN TRANSACTION')
        
        # Get all resource IDs
        cursor.execute("SELECT resource_id FROM resources")
        all_resources = [r[0] for r in cursor.fetchall()]
        total_resources = len(all_resources)
        
        # Calculate counts
        completely_unassigned_count = int(total_resources * unassigned_pct / 100)
        partially_unassigned_count = int(total_resources * partial_pct / 100)
        
        # Shuffle resources
        random.shuffle(all_resources)
        
        # Set completely unassigned
        completely_unassigned = all_resources[:completely_unassigned_count]
        cursor.execute("""
            UPDATE resources 
            SET owner = NULL, env = NULL 
            WHERE resource_id IN ({})
        """.format(','.join('?' * len(completely_unassigned))), completely_unassigned)
        
        # Set partially unassigned (split between missing owner and env)
        partial_start = completely_unassigned_count
        partial_end = partial_start + partially_unassigned_count
        partially_unassigned = all_resources[partial_start:partial_end]
        
        mid_point = len(partially_unassigned) // 2
        missing_owner = partially_unassigned[:mid_point]
        missing_env = partially_unassigned[mid_point:]
        
        if missing_owner:
            cursor.execute("""
                UPDATE resources 
                SET owner = NULL 
                WHERE resource_id IN ({})
            """.format(','.join('?' * len(missing_owner))), missing_owner)
            
        if missing_env:
            cursor.execute("""
                UPDATE resources 
                SET env = NULL 
                WHERE resource_id IN ({})
            """.format(','.join('?' * len(missing_env))), missing_env)
        
        cursor.execute('COMMIT')
        
        # Print summary
        print("\nResource Assignment Status:")
        print("-" * 50)
        
        cursor.execute("""
            SELECT 
                CASE 
                    WHEN owner IS NULL AND env IS NULL THEN 'Completely Unassigned'
                    WHEN owner IS NULL THEN 'Missing Owner'
                    WHEN env IS NULL THEN 'Missing Environment'
                    ELSE 'Fully Assigned'
                END as status,
                COUNT(*) as count,
                ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM resources), 1) as percentage
            FROM resources
            GROUP BY 
                CASE 
                    WHEN owner IS NULL AND env IS NULL THEN 'Completely Unassigned'
                    WHEN owner IS NULL THEN 'Missing Owner'
                    WHEN env IS NULL THEN 'Missing Environment'
                    ELSE 'Fully Assigned'
                END
            ORDER BY count DESC
        """)
        
        print(f"{'Status':<25} {'Count':>8} {'Percentage':>12}")
        print("-" * 50)
        for row in cursor.fetchall():
            print(f"{row[0]:<25} {row[1]:>8} {row[2]:>11}%")
            
    except Exception as e:
        cursor.execute('ROLLBACK')
        print(f"Error: {str(e)}")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Manage data variations and assignments")
    parser.add_argument("--type", choices=["cost", "usage"], default="cost",
                      help="Type of variations to add")
    parser.add_argument("--unassigned", type=float, default=10,
                      help="Percentage of completely unassigned resources")
    parser.add_argument("--partial", type=float, default=12,
                      help="Percentage of partially unassigned resources")
    
    args = parser.parse_args()
    
    # Add variations first
    add_variations(type=args.type)
    
    # Then update assignments
    update_assignments(args.unassigned, args.partial)