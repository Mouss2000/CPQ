# Plannification — CPQ Desktop Application

> **Project:** CPQ (Configure, Price, Quote) Standalone Desktop App
> **Stack:** Python · SQLite · CustomTkinter · PyInstaller
> **Period:** June 2026 — August 2026
> **Author:** Generated from project memory logs — July 27, 2026

---

## Phase 1 — Data Extraction & Architecture (Week 1–2 of June)

**Period:** ~June 2 – June 18, 2026

| Task | Details | Status |
|------|---------|--------|
| Environment setup | Installed `openpyxl` for Excel parsing | ✅ Done |
| Excel file inspection | Identified source files: `Composants...` and `PR ET COUT...` | ✅ Done |
| Step 1: Extract & Inspect | Confirmed Excel uses hardcoded default values, not formulas | ✅ Done |
| Step 2: Schema design | Designed SQLite schema (`schema.sql`), built `database_manager.py` | ✅ Done |
| Step 3: Data import (V1) | Extracted 219 materials and 396 products with PR/PT via `importer.py` | ✅ Done |
| Architectural decision | Agreed on **Catalog-First** approach — strict lookup from Excel data, no estimation for unknown dimensions, cascading dropdown UI pattern | ✅ Done |

**Key deliverables:** `schema.sql`, `database_manager.py`, `importer.py`, seeded `cpq_data.db`

---

## Phase 2 — GUI Development (June 19 – June 24)

### June 19, 2026 — Session: Project Review & Documentation

| Task | Details | Status |
|------|---------|--------|
| Full codebase review | Reviewed `schema.sql`, `importer.py`, `database_manager.py`, `verify_db.py` | ✅ Done |
| Confirmed Steps 1–3 | Validated data extraction and architecture completion | ✅ Done |
| README generation | Created `README.md` documenting architecture, techniques, and roadmap (for report/plan directeur) | ✅ Done |
| Prepared Step 4 | Scoped GUI scaffold requirements | ✅ Done |

### June 24, 2026 — Session Part 1: Full GUI Scaffold

| Task | Details | Status |
|------|---------|--------|
| Installed CustomTkinter | v5.2.2 + `darkdetect` dependency | ✅ Done |
| Built `main_gui.py` | Dark-mode window (960×700), custom color palette | ✅ Done |
| Top bar | Live product count indicator (📦 396 products loaded) | ✅ Done |
| Cascading dropdowns | 3 linked `CTkOptionMenu`: Category → Color → Dimension | ✅ Done |
| PricingCard widget | Displays PR (Cost), PT (Tariff), Margin %, dimension details | ✅ Done |
| DatabaseQuery class | Clean separation of read-only GUI queries from DB init logic | ✅ Done |
| Reset functionality | Button to clear all selections | ✅ Done |
| First successful launch | App ran with no errors, 396 products accessible | ✅ Done |

### June 24, 2026 — Session Part 2: Critical Data Accuracy Fix

| Bug | Description | Impact |
|-----|-------------|--------|
| Bug 1 — PROFIL-only | V1 grabbed only the PROFIL row cost instead of full BOM total (all components + labor) | GBF Blanc 600×60 showed 42.28 DA instead of **114.74 DA** |
| Bug 2 — Missing Gris table | Sheets have side-by-side tables (Blanc cols A–E, Gris cols G–K). V1 only read left table | All Gris Anodisé data missing |
| Bug 3 — Wrong category | Right-side tables tagged with sheet-name category instead of header-detected category | GDD products misclassified as GSD |

**Fix:** Built `importer_v2.py` — block-based extraction, dual-table parsing, header-based category detection.

| Metric | V1 (broken) | V2 (fixed) |
|--------|-------------|------------|
| Total products | 396 | **652** |
| GDD products | 32 | **135** |
| GBF Gris Anodisé | 2 | **151** |
| GBF Blanc 600×60 cost | 42.28 DA | **114.74 DA** |

**Key deliverables:** `importer_v2.py`, re-seeded database with 652 correct products

---

## Phase 3 — Feature Enrichment & Packaging (June 27)

### June 27, 2026 — Session: BOM Breakdown, Search & First Build

| Task | Details | Status |
|------|---------|--------|
| `product_components` table | New schema table for per-product component breakdown | ✅ Done |
| Component extraction | Modified `importer_v2.py` — extracts 6 component rows per product (PROFIL, AIL, T/ALUM, CLIP, EQUERE, EXEC) | ✅ Done |
| PROFIL row fix | PROFIL was on dimension row itself — adjusted scan start | ✅ Done |
| Total components imported | **4,470** across 652 products | ✅ Done |
| Tariff removal | Removed PT (Tariff) and Margin sections from PricingCard — confirmed unnecessary by user | ✅ Done |
| BOM breakdown UI | Scrollable component list in PricingCard: name + subtotal, bold TOTAL row | ✅ Done |
| Search bar | Instant search above dropdowns, wildcard dimension matching, min 2 chars, auto-syncs cascading dropdowns | ✅ Done |
| PyInstaller packaging | Built `CPQ.exe` (~15.6 MB), bundled CustomTkinter assets + seed DB + schema | ✅ Done |
| Spec file | Created `cpq.spec` for reproducible builds | ✅ Done |
| Verification | Single-file windowed `.exe`, no console, copies seed DB to `%APPDATA%` on first run | ✅ Done |

**Key deliverables:** `CPQ.exe` (first distributable build), BOM breakdown, search functionality

---

## Phase 4 — Portability & Robustness (July 2)

### July 2, 2026 — Session: Portable EXE Fix

| Task | Details | Status |
|------|---------|--------|
| Bug: crash on foreign machines | `sqlite3.OperationalError: unable to open database file` on PCs without prior importer runs | ✅ Fixed |
| Root cause | `DatabaseQuery` assumed `%APPDATA%\CPQ_App\cpq_data.db` already existed — true on dev machine only | ✅ Identified |
| `_resource_path()` | Resolves `sys._MEIPASS` for frozen PyInstaller bundles | ✅ Done |
| `_ensure_db_exists()` | Creates `CPQ_App` directory + copies bundled seed DB on first launch | ✅ Done |
| Fallback mechanism | Creates empty DB from `schema.sql` if seed DB not found in bundle | ✅ Done |
| EXE rebuild | Rebuilt `dist\CPQ.exe` with portability fix | ✅ Done |

**Key deliverable:** Truly portable `CPQ.exe` — works on any Windows PC from USB drive

---

## Phase 5 — Admin Panel & Data Management (July 12)

### July 12, 2026 — Session: Admin Panel, Checkpoints & Rebuild

| Task | Details | Status |
|------|---------|--------|
| Admin Panel (v1 → v2) | Initial global editor was dangerous (changed all 652 products). Rewritten to **per-product editing** | ✅ Done |
| Cascading dropdowns in Admin | Category → Color → Dimension — mirrors main UI | ✅ Done |
| BOM editor table | Component Name · Qty (read-only) · Unit Price (editable) · Subtotal (auto-calculated) | ✅ Done |
| Save mechanism | Updates only selected product's components + recalculates product total via SUM | ✅ Done |
| DatabaseManager expansion | Added `get_product_id()`, `get_components_for_product()`, `update_single_component()` | ✅ Done |
| **Checkpoint system** | Auto-checkpoint before every save + manual checkpoint button (📌) | ✅ Done |
| Checkpoint schema | 3 new tables: `pricing_checkpoints`, `checkpoint_components`, `checkpoint_products` | ✅ Done |
| Restore dialog | Lists all checkpoints (newest first) with timestamps, Restore + Delete buttons, confirmation prompt | ✅ Done |
| Checkpoint DB methods | `create_checkpoint()`, `list_checkpoints()`, `restore_checkpoint()`, `delete_checkpoint()` | ✅ Done |
| ValueError fix | `price` from DB was string type — added explicit `float()` cast | ✅ Fixed |
| EXE rebuild | Updated `cpq.spec` to bundle `database_manager.py`, rebuilt `CPQ.exe` | ✅ Done |

**Key deliverable:** Self-sustaining admin panel — non-technical staff can update pricing without developer help

---

## Phase 6 — UI Polish & Cross-Resolution Support (July 15)

### July 15, 2026 — Session: Z-Order, Responsive Layout & DPI Scaling

| Task | Details | Status |
|------|---------|--------|
| Popup z-order fix | Admin and Restore windows appeared behind main window — added `transient()`, `grab_set()`, `lift()`, `after(100, focus_force)` | ✅ Fixed |
| Responsive layout | Replaced `pack` with `grid`-based 2:3 column split, removed ALL fixed pixel widths (400px panel, 340px dropdowns) | ✅ Done |
| Flexible widgets | All dropdowns/entries/buttons use `fill="x"`, PricingCard uses `fill="both", expand=True` | ✅ Done |
| Admin window sizing | 40% screen width × 75% screen height (min 560×650), auto-centered | ✅ Done |
| Restore dialog sizing | 30% screen width × 40% screen height (min 450×350), auto-centered | ✅ Done |
| DPI awareness | `ctypes.windll.shcore.SetProcessDpiAwareness(1)` — true pixel values on Windows | ✅ Done |
| Auto-scaling system | Scale factor = actual screen ÷ 1080p reference, clamped 65%–160% | ✅ Done |
| Widget scaling | `ctk.set_widget_scaling()` + `ctk.set_window_scaling()` — all widgets scale proportionally | ✅ Done |
| EXE rebuilds | Rebuilt `CPQ.exe` 3× during session with incremental fixes | ✅ Done |

**Scaling behavior:**

| Screen Resolution | Scale Factor | Effect |
|-------------------|-------------|--------|
| 1366×768 | 0.71 | Shrinks ~30% |
| 1920×1080 | 1.0 | Baseline |
| 2560×1440 | 1.33 | Grows ~33% |
| 3840×2160 (4K) | 1.6 | Max clamp |

**Key deliverable:** App works correctly across all common screen resolutions

---

## Summary of Completed Work (June – July 27, 2026)

| Phase | Period | Major Deliverables |
|-------|--------|-------------------|
| 1 — Data Extraction | June W1–W2 | Schema, importer, 219 materials, 396 products |
| 2 — GUI Development | June 19–24 | Full CustomTkinter UI, cascading dropdowns, `importer_v2.py` (652 products) |
| 3 — Features & Packaging | June 27 | BOM breakdown (4,470 components), search bar, first `CPQ.exe` build |
| 4 — Portability | July 2 | Portable EXE fix — runs on any Windows PC |
| 5 — Admin & Data Mgmt | July 12 | Per-product admin panel, checkpoint/restore system |
| 6 — UI Polish | July 15 | Responsive layout, DPI scaling, popup fixes |

---

## Forward Plan — July 28 to August 31, 2026

### Week of July 28 – August 1 (Week 1)

| Task | Priority | Description |
|------|----------|-------------|
| Tester verification | 🔴 High | Verify app on low-resolution laptop (1366×768), confirm DPI scaling works |
| Bug triage | 🔴 High | Collect and fix any bugs reported from field testing |
| EXE rebuild | 🟡 Medium | Rebuild after any fixes from testing |

### Week of August 4 – August 8 (Week 2)

| Task | Priority | Description |
|------|----------|-------------|
| Login / Authentication screen | 🟡 Medium | Windows lock screen style login, `users` table with hashed passwords, role-based access (admin vs viewer) |
| First-run setup wizard | 🟡 Medium | Create initial admin account on first launch |
| Role-based UI gating | 🟡 Medium | Admin button visible only for admin role |

### Week of August 11 – August 15 (Week 3)

| Task | Priority | Description |
|------|----------|-------------|
| Product Management CRUD | 🟡 Medium | Add/Edit/Delete products directly in app — full "Gestion" tab |
| Form flow | 🟡 Medium | Category → Color → Dimension → Component list with qty/price/subtotal |
| Duplicate prevention | 🟡 Medium | Block duplicate category+color+dimension combos on insert |
| Audit log | 🟢 Low | `audit_log` table tracking who changed what and when |

### Week of August 18 – August 22 (Week 4)

| Task | Priority | Description |
|------|----------|-------------|
| Final testing round | 🔴 High | Full regression testing on multiple machines |
| Handoff documentation | 🔴 High | User manual for non-technical staff (how to use admin panel, checkpoints, search) |
| Auto-backup mechanism | 🟢 Low | Auto-export SQLite to `.sql` dump before destructive operations |

### Week of August 25 – August 29 (Week 5)

| Task | Priority | Description |
|------|----------|-------------|
| Final report compilation | 🔴 High | Compile internship report with planning, architecture, results |
| Final `CPQ.exe` build | 🔴 High | Production build with all features, tested and validated |
| Project handoff | 🔴 High | Deliver `.exe` + documentation + source code to company |
| Knowledge transfer | 🟡 Medium | Brief staff on app usage, admin panel, checkpoint system |

---

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| DPI scaling issues on untested screens | Medium | Medium | Clamped scale factor (65%–160%), grid layout, no fixed widths |
| Staff accidentally corrupts pricing data | Medium | High | Checkpoint system with auto-save before every edit |
| Login system bypassed via direct DB access | Low | Low | Acceptable for use case — access gating, not true security |
| Excel layout changes break re-import | Low | Medium | `importer_v2.py` uses block-based extraction, not fixed cell references |
| PyInstaller antivirus false positives | Medium | Medium | Code-sign `.exe` or whitelist on target machines |

---

## File Inventory

| File | Purpose |
|------|---------|
| `main_gui.py` | Main application — GUI, search, cascading dropdowns, admin panel |
| `database_manager.py` | DB init, seeding, CRUD operations, checkpoint system |
| `importer_v2.py` | Excel → SQLite data extraction (block-based, dual-table) |
| `schema.sql` | SQLite table definitions |
| `cpq.spec` | PyInstaller build specification |
| `verify_db.py` | Database verification utility |
| `verify_components.py` | Component data verification |
| `inspect_block_structure.py` | Excel block structure inspection tool |
| `dist\CPQ.exe` | Standalone distributable application (~15.6 MB) |
| `README.md` | Project documentation |
| `MEMORY.md` | Session-by-session development log |
