-- CPQ Application Database Schema

-- Material Rates Table
CREATE TABLE IF NOT EXISTS materials (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    unit TEXT NOT NULL,
    price_2023 REAL NOT NULL,
    category TEXT -- e.g., 'Profil', 'Ailette', 'Accessoire'
);

-- Labor/Execution Rates
CREATE TABLE IF NOT EXISTS labor_rates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    operation TEXT NOT NULL,
    rate_per_minute REAL NOT NULL
);

-- Product Categories
CREATE TABLE IF NOT EXISTS product_categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT UNIQUE NOT NULL, -- e.g., 'GSD', 'GDD'
    name TEXT NOT NULL
);

-- Products Table (Lookups from Excel TABLEAU)
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category_code TEXT NOT NULL,
    dimension TEXT NOT NULL, -- 'Width*Height'
    width INTEGER NOT NULL,
    height INTEGER NOT NULL,
    color TEXT, -- 'Blanc' or 'Gris Anodise'
    image_path TEXT,
    excel_cost REAL,
    excel_tariff REAL,
    FOREIGN KEY (category_code) REFERENCES product_categories(code)
);

-- Product BOM Components (individual cost breakdown rows)
CREATE TABLE IF NOT EXISTS product_components (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL,
    component_name TEXT NOT NULL,
    quantity REAL,
    unit_price REAL,
    subtotal REAL,
    FOREIGN KEY (product_id) REFERENCES products(id)
);

-- Global Constants
CREATE TABLE IF NOT EXISTS global_constants (
    key TEXT PRIMARY KEY,
    value REAL NOT NULL
);

-- Sheet Metal Thicknesses
CREATE TABLE IF NOT EXISTS sheet_metal_thicknesses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    reference TEXT UNIQUE NOT NULL,
    thickness_mm REAL NOT NULL
);
