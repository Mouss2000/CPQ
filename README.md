# CPQ Desktop Application: Project Status & Overview

This document outlines the architectural approach, completed milestones, technical strategies, and future roadmap for the CPQ (Configure, Price, Quote) Desktop Application. This serves as a comprehensive reference for reporting and future development planning.

## 1. The Broader Vision
The core mission of this project is to transition complex manufacturing pricing mechanisms currently trapped in massive, fragile `.xlsx` spreadsheets into a **standalone, zero-backend Python desktop application**. 

By migrating to a dedicated desktop app, the business reduces human error, guarantees pricing consistency, and provides sales and engineering teams with a user-friendly "Digital Pricing Catalog." The application is designed to be fully portable and distributable to any PC without requiring local database servers or cloud infrastructure.

## 2. What We Have Done & How We Did It

### Data Extraction & Reverse-Engineering (The "Catalog-First" Approach)
Rather than attempting to hallucinate or natively calculate complex mathematical formulas from the Excel files (`Composants des caissons...` and `PR ET COUT GRILLES...`), we adopted a **"Catalog-First" Strategy**.
- **Technique:** We treated the Excel spreadsheets as an absolute source of truth. We wrote extraction scripts using `openpyxl` (`importer.py`) to parse thousands of rows of predefined calculations and extract the final computed Cost (PR) and Tariff (PT) values.
- **Why:** This ensures 100% pricing accuracy matching the existing business logic. If a dimension does not exist in the spreadsheet, it is cleanly flagged as a "Non-Standard" custom order rather than risking an incorrect mathematical estimation.

### Relational Database Architecture
We replaced the flat-file spreadsheet structure with a robust relational database using **SQLite**.
- **Technique:** Designed a normalized schema (`schema.sql`) breaking data down into `materials`, `labor_rates`, `product_categories`, and specific `products`.
- **Implementation:** The `importer.py` script utilizes Regular Expressions (`re`) to intelligently parse dimension strings (e.g., extracting "100" and "200" from "100 * 200") and color mappings to populate the SQL tables cleanly.

### Standalone Local Data Management
To ensure the application can be packaged and run anywhere without admin rights, we engineered a dynamic database initialization system.
- **Technique:** Developed `database_manager.py` which detects the operating system and automatically copies a seeded SQLite `.db` file into the user's local `AppData` directory (e.g., `C:\Users\<User>\AppData\Roaming\CPQ_App`).
- **Why:** Packaged executables (like those made by PyInstaller) often run from read-only temporary directories. By migrating the database to `AppData`, we ensure the application maintains necessary Read/Write privileges for future updates or custom configurations.

## 3. Future Roadmap

### Modern Graphical User Interface (GUI)
We will transition from the backend data infrastructure to a modern frontend application.
- **Technology:** We will utilize **CustomTkinter** to build a sleek, dark-mode capable desktop interface (`main_gui.py`) that feels premium and responsive.

### Guided Cascading Logic
To prevent user input errors and ensure pricing validity, the UI will implement a strict, guided workflow.
- **Technique:** Implementation of cascading dropdown menus (Category -> Color -> Dimension).
- **Execution:** Each dropdown selection will dynamically trigger an SQLite query to populate the next dropdown. This restricts the user to only selecting product combinations that have been pre-verified and successfully extracted from the Excel source.

### The "Pricing Card" & BOM Viewer
Once a valid configuration is selected, the application will display a clean "Pricing Card."
- **Execution:** This view will instantly fetch the precise PR (Cost) and PT (Tariff) from the database, alongside a breakdown of the Bill of Materials (BOM) and labor rates, giving the user immediate, accurate pricing insights.

### PyInstaller Packaging
The final step of the pipeline.
- **Technique:** We will compile the entire Python ecosystem (code, `CustomTkinter` assets, and the seeded SQLite database) into a single `.exe` file using **PyInstaller**. This will allow any employee to simply double-click and run the application with zero technical setup required.
