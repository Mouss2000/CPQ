import sqlite3
from database_manager import DatabaseManager

db = DatabaseManager()
conn = db.get_connection()
cursor = conn.cursor()

with open("schema.sql", "r") as f:
    schema = f.read()

cursor.executescript(schema)
conn.commit()

thicknesses = [
    ('EP 5/10', 0.5), ('EP 6/10', 0.6), ('EP 7/10', 0.7), ('EP 8/10', 0.8),
    ('EP 9/10', 0.9), ('EP 10/10', 1.0), ('EP 11/10', 1.1), ('EP 12/10', 1.2),
    ('EP 15/10', 1.5), ('EP 19/10', 1.9), ('EP 20/10', 2.0)
]
cursor.execute("INSERT OR REPLACE INTO global_constants (key, value) VALUES (?, ?)", ('TOLE_DENSITY_MULTIPLIER', 8.0))
for ref, th in thicknesses:
    cursor.execute("INSERT OR IGNORE INTO sheet_metal_thicknesses (reference, thickness_mm) VALUES (?, ?)", (ref, th))

conn.commit()
conn.close()

print("Migration successful.")
