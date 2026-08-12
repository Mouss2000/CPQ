import sqlite3
conn = sqlite3.connect('C:/Users/SetupGame/AppData/Roaming/CPQ_App/cpq_data.db')
conn.row_factory = sqlite3.Row
cur = conn.cursor()

cur.execute("SELECT * FROM products WHERE category_code = 'GDD' AND color = 'Blanc' LIMIT 1")
p = cur.fetchone()
print(f"Produit: {p['category_code']} {p['color']} {p['dimension']}")
print(f"Excel PR: {p['excel_cost']}, Excel PT: {p['excel_tariff']}")

print("\nBOM:")
cur.execute("SELECT * FROM product_components WHERE product_id = ?", (p['id'],))
mat_sum = 0
exec_cost = 0
for c in cur.fetchall():
    print(f"{c['component_name']} | qty: {c['quantity']} | price: {c['unit_price']} | sub: {c['subtotal']}")
    if c['component_name'] != 'EXEC':
        mat_sum += c['subtotal']
    else:
        exec_cost = c['subtotal']

print(f"\nMat Sum: {mat_sum}")
print(f"Exec Cost: {exec_cost}")
