import sqlite3
import os

db_path = os.path.expandvars(r'%APPDATA%\CPQ_App\cpq_data.db')
conn = sqlite3.connect(db_path)
cur = conn.cursor()
cur.execute("DELETE FROM product_categories WHERE LOWER(code) IN ('ventq', 'clima') OR LOWER(name) IN ('ventq', 'clima')")
print(f"Deleted {cur.rowcount} orphaned categories.")
conn.commit()
conn.close()
