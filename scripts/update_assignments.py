"""
Script to add specific percentages of unassigned resources
"""
import sqlite3
import random

def update_assignments():
    conn = sqlite3.connect('data/billing.db')
    cursor = conn.cursor()
    
    try:
        # Start transaction
        cursor.execute('BEGIN TRANSACTION')
        
        # Get total number of resources
        cursor.execute("SELECT COUNT(*) FROM resources")
        total_resources = cursor.fetchone()[0]
        
        # Calculate counts based on percentages
        completely_unassigned_count = int(total_resources * 0.10)  # 10%
        partially_unassigned_count = int(total_resources * 0.12)  # 12%
        
        # Get all resource IDs
        cursor.execute("SELECT resource_id FROM resources ORDER BY RANDOM()")
        all_resources = [r[0] for r in cursor.fetchall()]
        
        # 1. Set completely unassigned resources (10%)
        completely_unassigned = all_resources[:completely_unassigned_count]
        cursor.execute("""
            UPDATE resources 
            SET owner = NULL, env = NULL 
            WHERE resource_id IN ({})
        """.format(','.join('?' * len(completely_unassigned))), completely_unassigned)
        
        # 2. Set partially unassigned resources (12%)
        partially_unassigned = all_resources[completely_unassigned_count:completely_unassigned_count + partially_unassigned_count]
        
        # Split partially unassigned between missing owner and missing env
        half_point = len(partially_unassigned) // 2
        missing_owner = partially_unassigned[:half_point]
        missing_env = partially_unassigned[half_point:]
        
        # Update missing owner
        if missing_owner:
            cursor.execute("""
                UPDATE resources 
                SET owner = NULL 
                WHERE resource_id IN ({})
            """.format(','.join('?' * len(missing_owner))), missing_owner)
        
        # Update missing environment
        if missing_env:
            cursor.execute("""
                UPDATE resources 
                SET env = NULL 
                WHERE resource_id IN ({})
            """.format(','.join('?' * len(missing_env))), missing_env)
        
        # Commit changes
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
        
        # Print cost impact for latest month
        print("\nSeptember 2025 Cost Distribution:")
        print("-" * 65)
        
        cursor.execute("""
            WITH monthly_costs AS (
                SELECT 
                    CASE 
                        WHEN r.owner IS NULL AND r.env IS NULL THEN 'Completely Unassigned'
                        WHEN r.owner IS NULL THEN 'Missing Owner'
                        WHEN r.env IS NULL THEN 'Missing Environment'
                        ELSE 'Fully Assigned'
                    END as status,
                    SUM(b.cost) as total_cost
                FROM billing b
                JOIN resources r ON b.resource_id = r.resource_id
                WHERE b.invoice_month = '2025-09'
                GROUP BY 
                    CASE 
                        WHEN r.owner IS NULL AND r.env IS NULL THEN 'Completely Unassigned'
                        WHEN r.owner IS NULL THEN 'Missing Owner'
                        WHEN r.env IS NULL THEN 'Missing Environment'
                        ELSE 'Fully Assigned'
                    END
            )
            SELECT 
                status,
                ROUND(total_cost, 2) as cost,
                ROUND(total_cost * 100.0 / (SELECT SUM(total_cost) FROM monthly_costs), 1) as percentage
            FROM monthly_costs
            ORDER BY cost DESC
        """)
        
        print(f"{'Status':<25} {'Cost':>15} {'Percentage':>12}")
        print("-" * 65)
        for row in cursor.fetchall():
            print(f"{row[0]:<25} ${row[1]:>14,.2f} {row[2]:>11}%")
            
    except Exception as e:
        cursor.execute('ROLLBACK')
        print(f"Error: {str(e)}")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    update_assignments()