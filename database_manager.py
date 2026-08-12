import sqlite3
import os
import shutil
import sys

class DatabaseManager:
    def __init__(self, db_name="cpq_data.db"):
        self.db_name = db_name
        self.app_data_dir = self._get_app_data_dir()
        self.db_path = os.path.join(self.app_data_dir, self.db_name)
        self._initialize_db()

    def _get_app_data_dir(self):
        # Determine the user's AppData directory (cross-platform)
        if sys.platform == "win32":
            base_dir = os.environ.get("APPDATA")
        else:
            base_dir = os.path.expanduser("~/.local/share")
        
        app_dir = os.path.join(base_dir, "CPQ_App")
        os.makedirs(app_dir, exist_ok=True)
        return app_dir

    def _resource_path(self, relative_path):
        """Get absolute path to resource, works for dev and for PyInstaller bundle."""
        if getattr(sys, 'frozen', False):
            # Running as PyInstaller bundle
            base_path = sys._MEIPASS
        else:
            base_path = os.path.abspath(".")
        return os.path.join(base_path, relative_path)

    def _initialize_db(self):
        # If DB doesn't exist in AppData, check for a bundled seed DB
        if not os.path.exists(self.db_path):
            bundled_db = self._resource_path(self.db_name)
            if os.path.exists(bundled_db):
                shutil.copyfile(bundled_db, self.db_path)
            else:
                self._create_empty_db()
        # Always run migrations for tables that may be missing from old seed DBs
        self._ensure_calculator_tables()

    def _ensure_calculator_tables(self):
        """Ensure sheet_metal_thicknesses and global_constants exist with seed data."""
        conn = self.get_connection()
        try:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS global_constants (
                    key TEXT PRIMARY KEY,
                    value REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS sheet_metal_thicknesses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    reference TEXT UNIQUE NOT NULL,
                    thickness_mm REAL NOT NULL
                );
            """)
            # Seed thickness data if table is empty
            count = conn.execute("SELECT COUNT(*) FROM sheet_metal_thicknesses").fetchone()[0]
            if count == 0:
                conn.executemany(
                    "INSERT OR IGNORE INTO sheet_metal_thicknesses (reference, thickness_mm) VALUES (?, ?)",
                    [
                        ("EP 5/10",  0.5), ("EP 6/10",  0.6), ("EP 7/10",  0.7),
                        ("EP 8/10",  0.8), ("EP 9/10",  0.9), ("EP 10/10", 1.0),
                        ("EP 11/10", 1.1), ("EP 12/10", 1.2), ("EP 15/10", 1.5),
                        ("EP 19/10", 1.9), ("EP 20/10", 2.0),
                    ]
                )
            # Seed density multiplier if missing
            conn.execute(
                "INSERT OR IGNORE INTO global_constants (key, value) VALUES ('TOLE_DENSITY_MULTIPLIER', 8.0)"
            )
            conn.commit()
        finally:
            conn.close()

    def _create_empty_db(self):
        schema_path = self._resource_path("schema.sql")
        try:
            with open(schema_path, "r", encoding="utf-8") as f:
                schema_sql = f.read()
        except (FileNotFoundError, UnicodeDecodeError) as e:
            raise RuntimeError(f"Cannot read schema.sql: {e}")
        conn = sqlite3.connect(self.db_path)
        try:
            conn.executescript(schema_sql)
            conn.commit()
        except Exception:
            conn.close()
            # Remove the 0-byte DB so next launch retries instead of being stuck
            if os.path.exists(self.db_path):
                os.remove(self.db_path)
            raise
        conn.close()

    def get_connection(self):
        return sqlite3.connect(self.db_path)

    def get_unique_components(self):
        conn = self.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT component_name, MAX(unit_price) FROM product_components GROUP BY component_name ORDER BY component_name")
        rows = cur.fetchall()
        conn.close()
        return rows

    def get_categories(self):
        conn = self.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT code, name FROM product_categories ORDER BY code")
        rows = cur.fetchall()
        conn.close()
        return rows

    def get_colors_for_category(self, category_code):
        conn = self.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT DISTINCT color FROM products WHERE category_code = ? ORDER BY color", (category_code,))
        rows = [r[0] for r in cur.fetchall()]
        conn.close()
        return rows

    def get_dimensions_for(self, category_code, color):
        conn = self.get_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT DISTINCT dimension, width, height FROM products WHERE category_code = ? AND color = ? ORDER BY width, height",
            (category_code, color)
        )
        rows = cur.fetchall()
        conn.close()
        return rows

    def get_product_id(self, category_code, color, dimension):
        conn = self.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT id FROM products WHERE category_code = ? AND color = ? AND dimension = ?", (category_code, color, dimension))
        row = cur.fetchone()
        conn.close()
        return row[0] if row else None

    def get_components_for_product(self, product_id):
        conn = self.get_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT id, component_name, quantity, unit_price, subtotal FROM product_components WHERE product_id = ? ORDER BY id",
            (product_id,)
        )
        rows = cur.fetchall()
        conn.close()
        return rows

    def update_single_component(self, component_id, new_price):
        conn = self.get_connection()
        cur = conn.cursor()
        # Update this specific component row
        cur.execute(
            "UPDATE product_components SET unit_price = ?, subtotal = quantity * ? WHERE id = ?",
            (new_price, new_price, component_id)
        )
        # Get parent product_id
        cur.execute("SELECT product_id FROM product_components WHERE id = ?", (component_id,))
        product_id = cur.fetchone()[0]
        # Recalculate that product's total
        cur.execute(
            "UPDATE products SET excel_cost = (SELECT SUM(subtotal) FROM product_components WHERE product_id = ?) WHERE id = ?",
            (product_id, product_id)
        )
        conn.commit()
        conn.close()

    def update_component_price(self, component_name, new_price):
        conn = self.get_connection()
        cur = conn.cursor()
        cur.execute(
            "UPDATE product_components SET unit_price = ?, subtotal = quantity * ? WHERE component_name = ?",
            (new_price, new_price, component_name)
        )
        cur.execute("""
            UPDATE products 
            SET excel_cost = (
                SELECT SUM(subtotal) 
                FROM product_components 
                WHERE product_id = products.id
            )
            WHERE id IN (
                SELECT product_id 
                FROM product_components 
                WHERE component_name = ?
            )
        """, (component_name,))
        conn.commit()
        conn.close()

    # ─── Product CRUD ────────────────────────────────────────────────────────

    def product_exists(self, category_code, color, dimension):
        """Check if a product with this cat+color+dim already exists."""
        conn = self.get_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT COUNT(*) FROM products WHERE category_code = ? AND color = ? AND dimension = ?",
            (category_code, color, dimension)
        )
        count = cur.fetchone()[0]
        conn.close()
        return count > 0

    def add_product(self, category_code, color, dimension, width, height):
        """Insert a new product. Returns new product_id. Raises ValueError if duplicate."""
        if self.product_exists(category_code, color, dimension):
            raise ValueError(f"Product {category_code}/{color}/{dimension} already exists")
        conn = self.get_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO products (category_code, dimension, width, height, color, excel_cost, excel_tariff) VALUES (?, ?, ?, ?, ?, 0.0, NULL)",
            (category_code, dimension, width, height, color)
        )
        product_id = cur.lastrowid
        conn.commit()
        conn.close()
        return product_id

    def update_product(self, product_id, category_code, color, dimension, width, height):
        """Update product metadata."""
        conn = self.get_connection()
        cur = conn.cursor()
        cur.execute(
            "UPDATE products SET category_code = ?, color = ?, dimension = ?, width = ?, height = ? WHERE id = ?",
            (category_code, color, dimension, width, height, product_id)
        )
        conn.commit()
        conn.close()

    def delete_product(self, product_id):
        """Delete a product, its components, and clean up orphaned categories."""
        conn = self.get_connection()
        cur = conn.cursor()
        
        # Get category_code before delete
        cur.execute("SELECT category_code FROM products WHERE id = ?", (product_id,))
        row = cur.fetchone()
        cat_code = row[0] if row else None
        
        cur.execute("DELETE FROM product_components WHERE product_id = ?", (product_id,))
        cur.execute("DELETE FROM products WHERE id = ?", (product_id,))
        
        # Clean up orphaned category
        if cat_code:
            cur.execute("SELECT COUNT(*) FROM products WHERE category_code = ?", (cat_code,))
            if cur.fetchone()[0] == 0:
                cur.execute("DELETE FROM product_categories WHERE code = ?", (cat_code,))
                
        conn.commit()
        conn.close()

    def add_component(self, product_id, component_name, quantity, unit_price):
        """Add a component to a product. Recalculates product total."""
        subtotal = quantity * unit_price
        conn = self.get_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO product_components (product_id, component_name, quantity, unit_price, subtotal) VALUES (?, ?, ?, ?, ?)",
            (product_id, component_name, quantity, unit_price, subtotal)
        )
        comp_id = cur.lastrowid
        # Recalculate product total
        cur.execute(
            "UPDATE products SET excel_cost = (SELECT COALESCE(SUM(subtotal), 0) FROM product_components WHERE product_id = ?) WHERE id = ?",
            (product_id, product_id)
        )
        conn.commit()
        conn.close()
        return comp_id

    def update_component(self, component_id, component_name, quantity, unit_price):
        """Update a component's name, qty, and price. Recalculates subtotal + product total."""
        subtotal = quantity * unit_price
        conn = self.get_connection()
        cur = conn.cursor()
        cur.execute(
            "UPDATE product_components SET component_name = ?, quantity = ?, unit_price = ?, subtotal = ? WHERE id = ?",
            (component_name, quantity, unit_price, subtotal, component_id)
        )
        # Get parent product_id
        cur.execute("SELECT product_id FROM product_components WHERE id = ?", (component_id,))
        row = cur.fetchone()
        if row:
            product_id = row[0]
            cur.execute(
                "UPDATE products SET excel_cost = (SELECT COALESCE(SUM(subtotal), 0) FROM product_components WHERE product_id = ?) WHERE id = ?",
                (product_id, product_id)
            )
        conn.commit()
        conn.close()

    def delete_component(self, component_id):
        """Delete a component. Recalculates product total."""
        conn = self.get_connection()
        cur = conn.cursor()
        # Get parent product_id before delete
        cur.execute("SELECT product_id FROM product_components WHERE id = ?", (component_id,))
        row = cur.fetchone()
        if not row:
            conn.close()
            return
        product_id = row[0]
        cur.execute("DELETE FROM product_components WHERE id = ?", (component_id,))
        # Recalculate product total
        cur.execute(
            "UPDATE products SET excel_cost = (SELECT COALESCE(SUM(subtotal), 0) FROM product_components WHERE product_id = ?) WHERE id = ?",
            (product_id, product_id)
        )
        conn.commit()
        conn.close()

    def get_product_by_id(self, product_id):
        """Return product row by ID: (id, category_code, dimension, width, height, color, excel_cost)."""
        conn = self.get_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT id, category_code, dimension, width, height, color, excel_cost FROM products WHERE id = ?",
            (product_id,)
        )
        row = cur.fetchone()
        conn.close()
        return row

    def ensure_category_exists(self, code, name):
        """Insert category if not already present."""
        conn = self.get_connection()
        cur = conn.cursor()
        cur.execute("INSERT OR IGNORE INTO product_categories (code, name) VALUES (?, ?)", (code, name))
        conn.commit()
        conn.close()

    # ─── Checkpoint System ───────────────────────────────────────────────────

    def _ensure_checkpoint_tables(self):
        conn = self.get_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT category_code FROM checkpoint_products LIMIT 1")
        except sqlite3.OperationalError:
            # Column doesn't exist (old schema), wipe tables to recreate with full snapshot schema
            conn.executescript("""
                DROP TABLE IF EXISTS checkpoint_components;
                DROP TABLE IF EXISTS checkpoint_products;
                DROP TABLE IF EXISTS pricing_checkpoints;
            """)
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS pricing_checkpoints (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS checkpoint_products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                checkpoint_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                category_code TEXT,
                dimension TEXT,
                width INTEGER,
                height INTEGER,
                color TEXT,
                excel_cost REAL,
                excel_tariff REAL,
                FOREIGN KEY (checkpoint_id) REFERENCES pricing_checkpoints(id)
            );
            CREATE TABLE IF NOT EXISTS checkpoint_components (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                checkpoint_id INTEGER NOT NULL,
                component_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                component_name TEXT NOT NULL,
                quantity REAL,
                unit_price REAL,
                subtotal REAL,
                FOREIGN KEY (checkpoint_id) REFERENCES pricing_checkpoints(id)
            );
        """)
        conn.commit()
        conn.close()

    def create_checkpoint(self, name=None):
        self._ensure_checkpoint_tables()
        conn = self.get_connection()
        cur = conn.cursor()
        if not name:
            from datetime import datetime
            name = f"Checkpoint {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        cur.execute("INSERT INTO pricing_checkpoints (name) VALUES (?)", (name,))
        cp_id = cur.lastrowid
        # Snapshot all components
        cur.execute("""
            INSERT INTO checkpoint_components (checkpoint_id, component_id, product_id, component_name, quantity, unit_price, subtotal)
            SELECT ?, id, product_id, component_name, quantity, unit_price, subtotal
            FROM product_components
        """, (cp_id,))
        # Snapshot all products completely
        cur.execute("""
            INSERT INTO checkpoint_products (checkpoint_id, product_id, category_code, dimension, width, height, color, excel_cost, excel_tariff)
            SELECT ?, id, category_code, dimension, width, height, color, excel_cost, excel_tariff
            FROM products
        """, (cp_id,))
        conn.commit()
        conn.close()
        return cp_id, name

    def list_checkpoints(self):
        self._ensure_checkpoint_tables()
        conn = self.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, name, created_at FROM pricing_checkpoints ORDER BY created_at DESC")
        rows = cur.fetchall()
        conn.close()
        return rows

    def restore_checkpoint(self, checkpoint_id):
        self._ensure_checkpoint_tables()
        conn = self.get_connection()
        cur = conn.cursor()
        
        # 1. Delete all current products and components
        cur.execute("DELETE FROM product_components")
        cur.execute("DELETE FROM products")
        
        # 1.5 Restore any orphaned categories needed by the checkpoint
        cur.execute("""
            INSERT OR IGNORE INTO product_categories (code, name)
            SELECT DISTINCT category_code, category_code
            FROM checkpoint_products
            WHERE checkpoint_id = ?
        """, (checkpoint_id,))
        
        # 2. Restore products exactly as they were (preserving ID)
        cur.execute("""
            INSERT INTO products (id, category_code, dimension, width, height, color, excel_cost, excel_tariff)
            SELECT product_id, category_code, dimension, width, height, color, excel_cost, excel_tariff
            FROM checkpoint_products
            WHERE checkpoint_id = ?
        """, (checkpoint_id,))
        
        # 3. Restore components exactly as they were (preserving ID)
        cur.execute("""
            INSERT INTO product_components (id, product_id, component_name, quantity, unit_price, subtotal)
            SELECT component_id, product_id, component_name, quantity, unit_price, subtotal
            FROM checkpoint_components
            WHERE checkpoint_id = ?
        """, (checkpoint_id,))
        
        conn.commit()
        conn.close()

    def delete_checkpoint(self, checkpoint_id):
        self._ensure_checkpoint_tables()
        conn = self.get_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM checkpoint_components WHERE checkpoint_id = ?", (checkpoint_id,))
        cur.execute("DELETE FROM checkpoint_products WHERE checkpoint_id = ?", (checkpoint_id,))
        cur.execute("DELETE FROM pricing_checkpoints WHERE id = ?", (checkpoint_id,))
        conn.commit()
        conn.close()

    def get_thicknesses(self):
        conn = self.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT reference, thickness_mm FROM sheet_metal_thicknesses ORDER BY thickness_mm")
        rows = cur.fetchall()
        conn.close()
        return rows

    def get_density_multiplier(self):
        conn = self.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT value FROM global_constants WHERE key = 'TOLE_DENSITY_MULTIPLIER'")
        row = cur.fetchone()
        conn.close()
        return float(row[0]) if row else 8.0

if __name__ == "__main__":
    # Seed the initial database
    mgr = DatabaseManager()
    conn = mgr.get_connection()
    cursor = conn.cursor()

    # Seed Materials (Sample from FICHE FOURNITURE 2023)
    materials = [
        ('PROFILE GSD BLANC', 'ML', 30.44, 'Profil'),
        ('PROFILE GDD BLANC', 'ML', 45.07, 'Profil'),
        ('AILETTES 100 BLANC', 'ML', 16.17, 'Ailette'),
        ('REGLETTE 100', 'U', 1.15, 'Accessoire'),
        ('EQUERRES', 'U', 0.61, 'Accessoire'),
        ('CLIPS FC', 'U', 2.91, 'Accessoire')
    ]
    cursor.executemany("INSERT INTO materials (name, unit, price_2023, category) VALUES (?, ?, ?, ?)", materials)

    # Seed Labor Rates
    cursor.execute("INSERT INTO labor_rates (operation, rate_per_minute) VALUES (?, ?)", ('Standard Execution', 1.41))

    # Seed Categories
    cursor.executemany("INSERT OR IGNORE INTO product_categories (code, name) VALUES (?, ?)", [
        ('GSD', 'Grilles Simple Deflexion'),
        ('GDD', 'Grilles Double Deflexion')
    ])

    # Seed Constants
    cursor.execute("INSERT OR REPLACE INTO global_constants (key, value) VALUES (?, ?)", ('TOLE_DENSITY_MULTIPLIER', 8.0))

    # Seed Sheet Metal Thicknesses
    thicknesses = [
        ('EP 5/10', 0.5), ('EP 6/10', 0.6), ('EP 7/10', 0.7), ('EP 8/10', 0.8),
        ('EP 9/10', 0.9), ('EP 10/10', 1.0), ('EP 11/10', 1.1), ('EP 12/10', 1.2),
        ('EP 15/10', 1.5), ('EP 19/10', 1.9), ('EP 20/10', 2.0)
    ]
    cursor.executemany("INSERT OR IGNORE INTO sheet_metal_thicknesses (reference, thickness_mm) VALUES (?, ?)", thicknesses)

    conn.commit()
    conn.close()
    print(f"Database seeded successfully at {mgr.db_path}")
