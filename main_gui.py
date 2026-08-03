"""
CPQ Desktop Application - Main GUI
CustomTkinter interface with cascading dropdown logic and pricing card display.
"""

import customtkinter as ctk
import sqlite3
import os
import sys
import ctypes
from tkinter import messagebox
from database_manager import DatabaseManager


# ─── DPI Awareness (must be set before any Tk window is created) ─────────────
# This ensures winfo_screenwidth/height return TRUE pixel values on Windows,
# not scaled values (e.g. 1920 instead of 1280 on a 150% scaled display).
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)  # PROCESS_SYSTEM_DPI_AWARE
except (AttributeError, OSError):
    pass  # Non-Windows or older Windows — skip gracefully


# ─── Theme & Appearance ─────────────────────────────────────────────────────
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# ─── Color Palette ───────────────────────────────────────────────────────────
COLORS = {
    "bg_dark":       "#0f1117",
    "bg_card":       "#1a1d27",
    "bg_card_hover": "#22263a",
    "accent":        "#4f8cff",
    "accent_hover":  "#6ba1ff",
    "accent_dim":    "#2a4a8f",
    "text_primary":  "#e8eaf0",
    "text_secondary":"#8b8fa3",
    "text_muted":    "#565b6e",
    "border":        "#2a2d3a",
    "success":       "#34d399",
    "warning":       "#fbbf24",
    "error":         "#f87171",
    "pr_color":      "#4f8cff",
    "pt_color":      "#34d399",
}


class DatabaseQuery:
    """Handles all SQLite queries for the GUI."""

    def __init__(self):
        self.db_path = self._resolve_db_path()
        self._ensure_db_exists()

    def _resource_path(self, relative_path):
        """Get absolute path to resource, works for dev and PyInstaller bundle."""
        if getattr(sys, 'frozen', False):
            base_path = sys._MEIPASS
        else:
            base_path = os.path.abspath(".")
        return os.path.join(base_path, relative_path)

    def _resolve_db_path(self):
        if sys.platform == "win32":
            base = os.environ.get("APPDATA")
        else:
            base = os.path.expanduser("~/.local/share")
        app_dir = os.path.join(base, "CPQ_App")
        if not os.path.exists(app_dir):
            os.makedirs(app_dir)
        return os.path.join(app_dir, "cpq_data.db")

    def _ensure_db_exists(self):
        """Copy bundled seed DB to AppData if it doesn't exist yet."""
        if not os.path.exists(self.db_path):
            import shutil
            bundled_db = self._resource_path("cpq_data.db")
            if os.path.exists(bundled_db):
                shutil.copy2(bundled_db, self.db_path)
            else:
                # Fallback: create empty DB from schema
                schema_path = self._resource_path("schema.sql")
                conn = sqlite3.connect(self.db_path)
                if os.path.exists(schema_path):
                    with open(schema_path, "r") as f:
                        conn.executescript(f.read())
                conn.commit()
                conn.close()

    def _conn(self):
        return sqlite3.connect(self.db_path)

    def get_categories(self):
        """Return list of (code, name) tuples."""
        conn = self._conn()
        cur = conn.cursor()
        cur.execute("SELECT code, name FROM product_categories ORDER BY code")
        rows = cur.fetchall()
        conn.close()
        return rows

    def get_colors_for_category(self, category_code):
        """Return distinct colors available for a category."""
        conn = self._conn()
        cur = conn.cursor()
        cur.execute(
            "SELECT DISTINCT color FROM products WHERE category_code = ? ORDER BY color",
            (category_code,)
        )
        rows = [r[0] for r in cur.fetchall()]
        conn.close()
        return rows

    def get_dimensions_for(self, category_code, color):
        """Return sorted dimension strings for a category+color."""
        conn = self._conn()
        cur = conn.cursor()
        cur.execute(
            """SELECT DISTINCT dimension, width, height 
               FROM products 
               WHERE category_code = ? AND color = ? 
               ORDER BY width, height""",
            (category_code, color)
        )
        rows = cur.fetchall()
        conn.close()
        return rows

    def get_product(self, category_code, color, dimension):
        """Return full product row for exact match."""
        conn = self._conn()
        cur = conn.cursor()
        cur.execute(
            """SELECT category_code, dimension, width, height, color, 
                      excel_cost, excel_tariff 
               FROM products 
               WHERE category_code = ? AND color = ? AND dimension = ?""",
            (category_code, color, dimension)
        )
        row = cur.fetchone()
        conn.close()
        return row

    def get_product_count(self):
        conn = self._conn()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM products")
        count = cur.fetchone()[0]
        conn.close()
        return count


    def get_product_components(self, category_code, color, dimension):
        conn = self._conn()
        cur = conn.cursor()
        cur.execute("""
            SELECT pc.component_name, pc.quantity, pc.unit_price, pc.subtotal
            FROM product_components pc
            JOIN products p ON pc.product_id = p.id
            WHERE p.category_code = ? AND p.color = ? AND p.dimension = ?
            ORDER BY pc.id
        """, (category_code, color, dimension))
        rows = cur.fetchall()
        conn.close()
        return rows

    def search_products(self, query):
        """Search products by dimension substring. Returns list of (cat, color, dimension, width, height, cost)."""
        conn = self._conn()
        cur = conn.cursor()
        cur.execute("""
            SELECT category_code, color, dimension, width, height, excel_cost
            FROM products
            WHERE dimension LIKE ?
            ORDER BY width, height, category_code, color
            LIMIT 20
        """, (f"%{query}%",))
        rows = cur.fetchall()
        conn.close()
        return rows


class PricingCard(ctk.CTkFrame):
    """Displays PR (Cost) and BOM breakdown in a styled card layout."""

    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.configure(
            fg_color=COLORS["bg_card"],
            corner_radius=16,
            border_width=1,
            border_color=COLORS["border"]
        )

        # ── Header ──
        self.header = ctk.CTkLabel(
            self, text="PRICING DETAILS",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color=COLORS["text_muted"]
        )
        self.header.pack(pady=(20, 5), padx=20, anchor="w")

        self.product_label = ctk.CTkLabel(
            self, text="Select a product configuration",
            font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"),
            text_color=COLORS["text_primary"]
        )
        self.product_label.pack(pady=(0, 15), padx=20, anchor="w")

        # ── Separator ──
        self.sep = ctk.CTkFrame(self, height=1, fg_color=COLORS["border"])
        self.sep.pack(fill="x", padx=20, pady=5)

        # ── PR (Cost) Section ──
        self.pr_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.pr_frame.pack(fill="x", padx=20, pady=(15, 5))

        self.pr_label = ctk.CTkLabel(
            self.pr_frame, text="PR  ·  PRIX DE REVIENT (COST)",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=COLORS["text_secondary"]
        )
        self.pr_label.pack(anchor="w")

        self.pr_value = ctk.CTkLabel(
            self.pr_frame, text="— DA",
            font=ctk.CTkFont(family="Segoe UI", size=36, weight="bold"),
            text_color=COLORS["pr_color"]
        )
        self.pr_value.pack(anchor="w", pady=(2, 0))

        # ── Dimension Details ──
        self.detail_frame = ctk.CTkFrame(
            self, fg_color=COLORS["bg_dark"], corner_radius=12
        )
        self.detail_frame.pack(fill="x", padx=20, pady=(20, 10))

        self.detail_header = ctk.CTkLabel(
            self.detail_frame, text="DIMENSIONS",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=COLORS["text_muted"]
        )
        self.detail_header.pack(pady=(12, 2), padx=15, anchor="w")

        self.detail_dims = ctk.CTkLabel(
            self.detail_frame, text="W: —  ×  H: —",
            font=ctk.CTkFont(family="Segoe UI", size=14),
            text_color=COLORS["text_secondary"]
        )
        self.detail_dims.pack(pady=(0, 12), padx=15, anchor="w")

        # ── BOM Separator ──
        self.bom_sep = ctk.CTkFrame(self, height=1, fg_color=COLORS["border"])
        self.bom_sep.pack(fill="x", padx=20, pady=(10, 5))

        # ── BOM Header ──
        self.bom_header = ctk.CTkLabel(
            self, text="BILL OF MATERIALS",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color=COLORS["text_muted"]
        )
        self.bom_header.pack(pady=(5, 5), padx=20, anchor="w")

        # ── BOM Scrollable Frame ──
        self.bom_frame = ctk.CTkScrollableFrame(
            self, height=200,
            fg_color=COLORS["bg_dark"],
            corner_radius=12
        )
        self.bom_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))

    def update_card(self, product_data, components=None):
        """Update card with product tuple: (cat, dim, w, h, color, cost, ...)."""
        if not product_data:
            self.clear_card()
            return

        cat, dim, w, h, color, cost = product_data[:6]

        # Product title
        cat_names = {
            "GSD": "Grille Simple Déflexion",
            "GDD": "Grille Double Déflexion",
            "GBF": "Grille à Barre Fixe"
        }
        title = f"{cat_names.get(cat, cat)} — {color}"
        self.product_label.configure(text=title)

        # PR
        if cost is not None:
            self.pr_value.configure(text=f"{cost:,.2f} DA")
        else:
            self.pr_value.configure(text="N/A")

        # Dimensions
        self.detail_dims.configure(text=f"W: {w} mm  ×  H: {h} mm")

        # BOM
        if components:
            self.update_bom(components)

    def update_bom(self, components):
        """Populate the BOM breakdown with component rows."""
        self.clear_bom()

        for name, qty, unit_price, subtotal in components:
            row = ctk.CTkFrame(self.bom_frame, fg_color="transparent")
            row.pack(fill="x", pady=2)

            ctk.CTkLabel(
                row, text=name,
                font=ctk.CTkFont(family="Segoe UI", size=13),
                text_color=COLORS["text_secondary"]
            ).pack(side="left", padx=(5, 0))

            price_text = f"{subtotal:.2f} DA" if subtotal else "—"
            ctk.CTkLabel(
                row, text=price_text,
                font=ctk.CTkFont(family="Segoe UI", size=13),
                text_color=COLORS["text_primary"]
            ).pack(side="right", padx=(0, 5))

        # ── Total separator ──
        ctk.CTkFrame(
            self.bom_frame, height=1, fg_color=COLORS["border"]
        ).pack(fill="x", padx=5, pady=(8, 4))

        # ── Total row ──
        total = sum(s for _, _, _, s in components if s)
        total_row = ctk.CTkFrame(self.bom_frame, fg_color="transparent")
        total_row.pack(fill="x", pady=(2, 4))

        ctk.CTkLabel(
            total_row, text="TOTAL",
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            text_color=COLORS["accent"]
        ).pack(side="left", padx=(5, 0))

        ctk.CTkLabel(
            total_row, text=f"{total:.2f} DA",
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            text_color=COLORS["accent"]
        ).pack(side="right", padx=(0, 5))

    def clear_bom(self):
        """Clear all children in the BOM frame."""
        for widget in self.bom_frame.winfo_children():
            widget.destroy()

    def clear_card(self):
        self.product_label.configure(text="Select a product configuration")
        self.pr_value.configure(text="— DA")
        self.detail_dims.configure(text="W: —  ×  H: —")
        self.clear_bom()

class AdminWindow(ctk.CTkToplevel):
    """Admin Panel with tabbed layout: Pricing editor + Product CRUD management."""

    def __init__(self, master, refresh_callback=None):
        super().__init__(master)
        self.title("Admin Panel — Product & Pricing Management")
        self.configure(fg_color=COLORS["bg_dark"])

        # ── Screen-aware sizing ──
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        win_w = max(680, int(screen_w * 0.45))
        win_h = max(750, int(screen_h * 0.8))
        x = (screen_w - win_w) // 2
        y = (screen_h - win_h) // 2
        self.geometry(f"{win_w}x{win_h}+{x}+{y}")
        self.minsize(680, 750)

        self.transient(master)
        self.grab_set()
        self.lift()
        self.after(100, self.focus_force)
        self.refresh_callback = refresh_callback
        self.db_mgr = DatabaseManager()

        # ── Title ──
        ctk.CTkLabel(
            self, text="⚙  ADMIN PANEL",
            font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"),
            text_color=COLORS["accent"]
        ).pack(pady=(16, 2), padx=24, anchor="w")

        ctk.CTkLabel(
            self, text="Manage product pricing and catalog entries",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=COLORS["text_secondary"]
        ).pack(pady=(0, 8), padx=24, anchor="w")

        # ── Main Content Area ──
        self.main_content = ctk.CTkFrame(self, fg_color=COLORS["bg_card"], corner_radius=12)
        self.main_content.pack(fill="both", expand=True, padx=24, pady=(0, 8))
        
        self._build_products_tab()

        # ── Bottom: Checkpoints & Restore ──
        bottom_frame = ctk.CTkFrame(self, fg_color="transparent")
        bottom_frame.pack(fill="x", padx=24, pady=(0, 12))
        
        self.cp_status = ctk.CTkLabel(
            bottom_frame, text="",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=COLORS["text_muted"]
        )
        self.cp_status.pack(side="top", pady=(0, 4))
        
        btn_frame = ctk.CTkFrame(bottom_frame, fg_color="transparent")
        btn_frame.pack(side="top")

        self.pr_checkpoint_btn = ctk.CTkButton(
            btn_frame, text="📌 Create Restore Point", height=32,
            fg_color=COLORS["accent_dim"], hover_color=COLORS["accent"],
            command=self._create_manual_checkpoint
        )
        self.pr_checkpoint_btn.pack(side="left", padx=5)

        self.pr_restore_btn = ctk.CTkButton(
            btn_frame, text="🕒 Restore Data", height=32,
            fg_color="transparent", hover_color=COLORS["bg_card_hover"],
            border_width=1, border_color=COLORS["warning"],
            text_color=COLORS["warning"],
            command=self._open_restore_dialog
        )
        self.pr_restore_btn.pack(side="left", padx=5)

        self._update_cp_status()

    def _build_products_tab(self):
        tab = self.main_content
        self._pd_product_id = None
        self._pd_dim_map = {}
        self._pd_comp_vars = []
        self._pd_mode = None  # "new" or "edit"

        # ── Mode Buttons: New vs Edit/Delete ──
        mode_frame = ctk.CTkFrame(tab, fg_color="transparent")
        mode_frame.pack(fill="x", padx=12, pady=(12, 6))

        self.pd_new_btn = ctk.CTkButton(
            mode_frame, text="➕  New Product", height=36,
            fg_color=COLORS["success"], hover_color="#2ab883",
            text_color=COLORS["bg_dark"],
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self._pd_show_new_form
        )
        self.pd_new_btn.pack(side="left", padx=(0, 8))

        self.pd_edit_btn = ctk.CTkButton(
            mode_frame, text="✏  Edit Existing", height=36,
            fg_color=COLORS["accent_dim"], hover_color=COLORS["accent"],
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self._pd_show_edit_form
        )
        self.pd_edit_btn.pack(side="left", padx=(0, 8))

        self.pd_delete_btn = ctk.CTkButton(
            mode_frame, text="🗑  Delete", height=36,
            fg_color="transparent", hover_color=COLORS["error"],
            border_width=1, border_color=COLORS["error"],
            text_color=COLORS["error"],
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self._pd_delete_product, state="disabled"
        )
        self.pd_delete_btn.pack(side="right")

        # ── Dynamic Content Area ──
        self.pd_content_frame = ctk.CTkFrame(tab, fg_color="transparent")
        self.pd_content_frame.pack(fill="both", expand=True, padx=12, pady=(0, 8))

        self._pd_show_welcome()

        # ── Status ──
        self.pd_status = ctk.CTkLabel(
            tab, text="",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=COLORS["text_muted"]
        )
        self.pd_status.pack(pady=(0, 6))

    def _pd_clear_content(self):
        for w in self.pd_content_frame.winfo_children():
            w.destroy()

    def _pd_show_welcome(self):
        self._pd_clear_content()
        self._pd_mode = None
        self._pd_product_id = None
        self.pd_delete_btn.configure(state="disabled")

        msg = ctk.CTkLabel(
            self.pd_content_frame,
            text="Choose an action above:\n\n➕  New Product — create a new catalog entry\n✏  Edit Existing — modify a product's details & components\n🗑  Delete — remove a product from the catalog",
            font=ctk.CTkFont(family="Segoe UI", size=13),
            text_color=COLORS["text_secondary"],
            justify="left"
        )
        msg.pack(pady=40, padx=20)

    # ─── NEW PRODUCT FORM ────────────────────────────────────────────────────

    def _pd_show_new_form(self):
        self._pd_clear_content()
        self._pd_mode = "new"
        self._pd_product_id = None
        self._pd_comp_vars = []
        self.pd_delete_btn.configure(state="disabled")
        self.pd_new_btn.configure(fg_color=COLORS["success"])
        self.pd_edit_btn.configure(fg_color=COLORS["accent_dim"])

        container = self.pd_content_frame

        # ── Product Info Form ──
        form = ctk.CTkFrame(container, fg_color=COLORS["bg_dark"], corner_radius=12)
        form.pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(form, text="NEW PRODUCT",
                     font=ctk.CTkFont(size=13, weight="bold"),
                     text_color=COLORS["success"]).pack(pady=(10, 6), padx=14, anchor="w")

        # Category (editable — type new or pick existing)
        cat_row = ctk.CTkFrame(form, fg_color="transparent")
        cat_row.pack(fill="x", padx=14, pady=3)
        ctk.CTkLabel(cat_row, text="Category:", width=80, anchor="w",
                     font=ctk.CTkFont(size=12), text_color=COLORS["text_secondary"]).pack(side="left")
        existing_cats = [c for c, _ in self.db_mgr.get_categories()]
        self.pd_new_cat_var = ctk.StringVar(value=existing_cats[0] if existing_cats else "")
        ctk.CTkComboBox(
            cat_row, variable=self.pd_new_cat_var,
            values=existing_cats, height=32,
            fg_color=COLORS["bg_card"], border_color=COLORS["accent_dim"],
            button_color=COLORS["accent_dim"], corner_radius=8,
            font=ctk.CTkFont(size=12)
        ).pack(side="left", fill="x", expand=True, padx=(8, 0))

        # Color (editable — type new or pick existing)
        color_row = ctk.CTkFrame(form, fg_color="transparent")
        color_row.pack(fill="x", padx=14, pady=3)
        ctk.CTkLabel(color_row, text="Color:", width=80, anchor="w",
                     font=ctk.CTkFont(size=12), text_color=COLORS["text_secondary"]).pack(side="left")
        existing_colors = list(set(
            c for cat_code, _ in self.db_mgr.get_categories()
            for c in self.db_mgr.get_colors_for_category(cat_code)
        ))
        existing_colors.sort()
        self.pd_new_color_var = ctk.StringVar(value=existing_colors[0] if existing_colors else "")
        ctk.CTkComboBox(
            color_row, variable=self.pd_new_color_var,
            values=existing_colors if existing_colors else [""], height=32,
            fg_color=COLORS["bg_card"], border_color=COLORS["accent_dim"],
            button_color=COLORS["accent_dim"], corner_radius=8,
            font=ctk.CTkFont(size=12)
        ).pack(side="left", fill="x", expand=True, padx=(8, 0))

        # Width
        w_row = ctk.CTkFrame(form, fg_color="transparent")
        w_row.pack(fill="x", padx=14, pady=3)
        ctk.CTkLabel(w_row, text="Width (mm):", width=80, anchor="w",
                     font=ctk.CTkFont(size=12), text_color=COLORS["text_secondary"]).pack(side="left")
        self.pd_new_width = ctk.CTkEntry(w_row, height=32, placeholder_text="e.g. 600",
                                          fg_color=COLORS["bg_card"], border_color=COLORS["accent_dim"])
        self.pd_new_width.pack(side="left", fill="x", expand=True, padx=(8, 0))

        # Height
        h_row = ctk.CTkFrame(form, fg_color="transparent")
        h_row.pack(fill="x", padx=14, pady=3)
        ctk.CTkLabel(h_row, text="Height (mm):", width=80, anchor="w",
                     font=ctk.CTkFont(size=12), text_color=COLORS["text_secondary"]).pack(side="left")
        self.pd_new_height = ctk.CTkEntry(h_row, height=32, placeholder_text="e.g. 60",
                                           fg_color=COLORS["bg_card"], border_color=COLORS["accent_dim"])
        self.pd_new_height.pack(side="left", fill="x", expand=True, padx=(8, 0))

        # Separator
        ctk.CTkFrame(form, height=1, fg_color=COLORS["border"]).pack(fill="x", padx=14, pady=(8, 4))

        # ── BOM Components Section ──
        ctk.CTkLabel(form, text="COMPONENTS (BOM)",
                     font=ctk.CTkFont(size=12, weight="bold"),
                     text_color=COLORS["text_muted"]).pack(pady=(4, 4), padx=14, anchor="w")

        self.pd_new_bom_frame = ctk.CTkScrollableFrame(
            form, fg_color=COLORS["bg_card"], corner_radius=10, height=140
        )
        self.pd_new_bom_frame.pack(fill="both", expand=True, padx=14, pady=(0, 6))

        # Header
        hdr = ctk.CTkFrame(self.pd_new_bom_frame, fg_color="transparent")
        hdr.pack(fill="x", pady=(4, 2))
        ctk.CTkLabel(hdr, text="Name", width=130, anchor="w",
                     font=ctk.CTkFont(size=10, weight="bold"),
                     text_color=COLORS["text_muted"]).pack(side="left", padx=(4, 0))
        ctk.CTkLabel(hdr, text="Qty", width=60, anchor="center",
                     font=ctk.CTkFont(size=10, weight="bold"),
                     text_color=COLORS["text_muted"]).pack(side="left", padx=2)
        ctk.CTkLabel(hdr, text="Unit Price", width=80, anchor="center",
                     font=ctk.CTkFont(size=10, weight="bold"),
                     text_color=COLORS["text_muted"]).pack(side="left", padx=2)

        # Pre-populate with standard component names
        default_comps = ["PROFIL", "AIL", "T/ALUM", "CLIP", "EQUERE", "EXEC"]
        for comp_name in default_comps:
            self._pd_add_new_comp_row(self.pd_new_bom_frame, comp_name)

        # Add Component button
        add_row = ctk.CTkFrame(form, fg_color="transparent")
        add_row.pack(fill="x", padx=14, pady=(0, 10))

        ctk.CTkButton(
            add_row, text="➕ Add Component", height=30,
            fg_color="transparent", hover_color=COLORS["bg_card_hover"],
            border_width=1, border_color=COLORS["accent_dim"],
            text_color=COLORS["accent"],
            font=ctk.CTkFont(size=11),
            command=lambda: self._pd_add_new_comp_row(self.pd_new_bom_frame)
        ).pack(side="left")

        # ── Create Button ──
        ctk.CTkButton(
            container, text="✅  Create Product", height=42,
            fg_color=COLORS["success"], hover_color="#2ab883",
            text_color=COLORS["bg_dark"],
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self._pd_create_product
        ).pack(fill="x", pady=(4, 0))

    def _pd_add_new_comp_row(self, parent, name="", qty="1.00", price="0.00"):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=2)

        name_var = ctk.StringVar(value=name)
        ctk.CTkEntry(row, textvariable=name_var, width=130, height=30,
                     font=ctk.CTkFont(size=11), placeholder_text="Component",
                     fg_color=COLORS["bg_dark"], border_color=COLORS["accent_dim"]
                     ).pack(side="left", padx=(4, 2))

        qty_var = ctk.StringVar(value=qty)
        ctk.CTkEntry(row, textvariable=qty_var, width=60, height=30,
                     font=ctk.CTkFont(size=11),
                     fg_color=COLORS["bg_dark"], border_color=COLORS["accent_dim"]
                     ).pack(side="left", padx=2)

        price_var = ctk.StringVar(value=price)
        ctk.CTkEntry(row, textvariable=price_var, width=80, height=30,
                     font=ctk.CTkFont(size=11),
                     fg_color=COLORS["bg_dark"], border_color=COLORS["accent_dim"]
                     ).pack(side="left", padx=2)

        ctk.CTkButton(
            row, text="✕", width=28, height=28,
            fg_color="transparent", hover_color=COLORS["error"],
            text_color=COLORS["error"], font=ctk.CTkFont(size=12),
            command=lambda r=row, v=(name_var, qty_var, price_var): self._pd_remove_comp_row(r, v)
        ).pack(side="right", padx=(2, 4))

        self._pd_comp_vars.append((name_var, qty_var, price_var, row))

    def _pd_remove_comp_row(self, row, var_tuple):
        self._pd_comp_vars = [(n, q, p, r) for n, q, p, r in self._pd_comp_vars if r != row]
        row.destroy()

    def _pd_create_product(self):
        cat = self.pd_new_cat_var.get().strip().upper()
        color = self.pd_new_color_var.get().strip()

        if not cat:
            messagebox.showerror("Error", "Category cannot be empty.", parent=self)
            return
        if not color:
            messagebox.showerror("Error", "Color cannot be empty.", parent=self)
            return

        try:
            width = int(self.pd_new_width.get().strip())
            height = int(self.pd_new_height.get().strip())
        except ValueError:
            messagebox.showerror("Error", "Width and Height must be integers.", parent=self)
            return

        if width <= 0 or height <= 0:
            messagebox.showerror("Error", "Width and Height must be positive.", parent=self)
            return

        dimension = f"{width}*{height}"

        # Auto-create category if it's new
        self.db_mgr.ensure_category_exists(cat, cat)

        # Duplicate check
        if self.db_mgr.product_exists(cat, color, dimension):
            messagebox.showerror("Error",
                f"Product {cat} / {color} / {dimension} already exists.\nUse Edit mode to modify it.",
                parent=self)
            return

        # Validate components
        comp_data = []
        for name_var, qty_var, price_var, _ in self._pd_comp_vars:
            cname = name_var.get().strip()
            if not cname:
                continue
            try:
                cqty = float(qty_var.get())
                cprice = float(price_var.get())
            except ValueError:
                messagebox.showerror("Error", f"Invalid number for component '{cname}'.", parent=self)
                return
            comp_data.append((cname, cqty, cprice))

        if not comp_data:
            messagebox.showerror("Error", "Add at least one component.", parent=self)
            return

        # Auto-checkpoint
        self.db_mgr.create_checkpoint(f"Auto — before adding {cat}/{color}/{dimension}")

        # Create product
        try:
            product_id = self.db_mgr.add_product(cat, color, dimension, width, height)
        except ValueError as e:
            messagebox.showerror("Error", str(e), parent=self)
            return

        # Add components
        for cname, cqty, cprice in comp_data:
            self.db_mgr.add_component(product_id, cname, cqty, cprice)

        # Get final cost
        prod = self.db_mgr.get_product_by_id(product_id)
        total = prod[6] if prod else 0

        self._update_cp_status()
        self.pd_status.configure(
            text=f"✅ Created: {cat} / {color} / {dimension} — Total: {total:.2f} DA",
            text_color=COLORS["success"]
        )

        if self.refresh_callback:
            self.refresh_callback()

        messagebox.showinfo("Product Created",
            f"New product added:\n\n{cat} / {color} / {dimension}\n{len(comp_data)} components\nTotal: {total:.2f} DA",
            parent=self)

    # ─── EDIT EXISTING PRODUCT ───────────────────────────────────────────────

    def _pd_show_edit_form(self):
        self._pd_clear_content()
        self._pd_mode = "edit"
        self._pd_product_id = None
        self._pd_comp_vars = []
        self.pd_delete_btn.configure(state="disabled")
        self.pd_new_btn.configure(fg_color=COLORS["accent_dim"])
        self.pd_edit_btn.configure(fg_color=COLORS["accent"])

        container = self.pd_content_frame

        # ── Selector ──
        sel = ctk.CTkFrame(container, fg_color=COLORS["bg_dark"], corner_radius=12)
        sel.pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(sel, text="SELECT PRODUCT TO EDIT",
                     font=ctk.CTkFont(size=13, weight="bold"),
                     text_color=COLORS["accent"]).pack(pady=(10, 6), padx=14, anchor="w")

        # Category
        ctk.CTkLabel(sel, text="CATEGORY", font=ctk.CTkFont(size=10, weight="bold"),
                     text_color=COLORS["text_muted"]).pack(pady=(2, 1), padx=14, anchor="w")
        categories = self.db_mgr.get_categories()
        self._pd_edit_cat_map = {f"{c}  —  {n}": c for c, n in categories}
        self.pd_edit_cat_var = ctk.StringVar(value="Select category...")
        ctk.CTkOptionMenu(
            sel, variable=self.pd_edit_cat_var, values=list(self._pd_edit_cat_map.keys()),
            command=self._pd_edit_on_cat, height=32,
            fg_color=COLORS["bg_card"], button_color=COLORS["accent_dim"], corner_radius=8
        ).pack(fill="x", padx=14, pady=(0, 4))

        # Color
        ctk.CTkLabel(sel, text="COLOR", font=ctk.CTkFont(size=10, weight="bold"),
                     text_color=COLORS["text_muted"]).pack(pady=(2, 1), padx=14, anchor="w")
        self.pd_edit_color_var = ctk.StringVar(value="Select color...")
        self.pd_edit_color_menu = ctk.CTkOptionMenu(
            sel, variable=self.pd_edit_color_var, values=["—"],
            command=self._pd_edit_on_color, height=32, state="disabled",
            fg_color=COLORS["bg_card"], button_color=COLORS["accent_dim"], corner_radius=8
        )
        self.pd_edit_color_menu.pack(fill="x", padx=14, pady=(0, 4))

        # Dimension
        ctk.CTkLabel(sel, text="DIMENSION", font=ctk.CTkFont(size=10, weight="bold"),
                     text_color=COLORS["text_muted"]).pack(pady=(2, 1), padx=14, anchor="w")
        self.pd_edit_dim_var = ctk.StringVar(value="Select dimension...")
        self.pd_edit_dim_menu = ctk.CTkOptionMenu(
            sel, variable=self.pd_edit_dim_var, values=["—"],
            command=self._pd_edit_on_dim, height=32, state="disabled",
            fg_color=COLORS["bg_card"], button_color=COLORS["accent_dim"], corner_radius=8
        )
        self.pd_edit_dim_menu.pack(fill="x", padx=14, pady=(0, 10))

        # ── Edit Area (populated after product selected) ──
        self.pd_edit_area = ctk.CTkFrame(container, fg_color="transparent")
        self.pd_edit_area.pack(fill="both", expand=True)

        ctk.CTkLabel(
            self.pd_edit_area, text="Select a product above to edit",
            font=ctk.CTkFont(size=13), text_color=COLORS["text_muted"]
        ).pack(pady=30)

    def _pd_edit_on_cat(self, selection):
        code = self._pd_edit_cat_map.get(selection)
        if not code:
            return
        self._pd_edit_sel_cat = code
        self.pd_edit_color_var.set("Select color...")
        self.pd_edit_dim_var.set("Select dimension...")
        self.pd_edit_dim_menu.configure(state="disabled", values=["—"])
        self._pd_product_id = None
        self.pd_delete_btn.configure(state="disabled")

        colors = self.db_mgr.get_colors_for_category(code)
        if colors:
            self.pd_edit_color_menu.configure(state="normal", values=colors)
        else:
            self.pd_edit_color_menu.configure(state="disabled", values=["No colors"])

    def _pd_edit_on_color(self, selection):
        self._pd_edit_sel_color = selection
        self.pd_edit_dim_var.set("Select dimension...")
        self._pd_product_id = None
        self.pd_delete_btn.configure(state="disabled")

        dims = self.db_mgr.get_dimensions_for(self._pd_edit_sel_cat, selection)
        if dims:
            display = [f"{d[0]}  ({d[1]}×{d[2]} mm)" for d in dims]
            self._pd_dim_map = {f"{d[0]}  ({d[1]}×{d[2]} mm)": d[0] for d in dims}
            self.pd_edit_dim_menu.configure(state="normal", values=display)
        else:
            self.pd_edit_dim_menu.configure(state="disabled", values=["No dimensions"])

    def _pd_edit_on_dim(self, selection):
        dim_key = self._pd_dim_map.get(selection)
        if not dim_key:
            return
        self._pd_edit_sel_dim = dim_key
        self._pd_product_id = self.db_mgr.get_product_id(
            self._pd_edit_sel_cat, self._pd_edit_sel_color, dim_key)
        if self._pd_product_id:
            self.pd_delete_btn.configure(state="normal")
            self._pd_load_edit_form()

    def _pd_load_edit_form(self):
        for w in self.pd_edit_area.winfo_children():
            w.destroy()
        self._pd_comp_vars = []

        product = self.db_mgr.get_product_by_id(self._pd_product_id)
        if not product:
            return

        _, cat, dim, width, height, color, cost = product

        # ── Product Metadata ──
        meta = ctk.CTkFrame(self.pd_edit_area, fg_color=COLORS["bg_dark"], corner_radius=10)
        meta.pack(fill="x", pady=(0, 6))

        ctk.CTkLabel(meta, text=f"EDITING: {cat} / {color} / {dim}",
                     font=ctk.CTkFont(size=12, weight="bold"),
                     text_color=COLORS["warning"]).pack(pady=(8, 2), padx=12, anchor="w")

        dim_edit_row = ctk.CTkFrame(meta, fg_color="transparent")
        dim_edit_row.pack(fill="x", padx=12, pady=(2, 8))

        ctk.CTkLabel(dim_edit_row, text="Width:", width=50, anchor="w",
                     font=ctk.CTkFont(size=11), text_color=COLORS["text_secondary"]).pack(side="left")
        self.pd_edit_width = ctk.CTkEntry(dim_edit_row, width=70, height=28,
                                           fg_color=COLORS["bg_card"], border_color=COLORS["accent_dim"])
        self.pd_edit_width.insert(0, str(width))
        self.pd_edit_width.pack(side="left", padx=(0, 10))

        ctk.CTkLabel(dim_edit_row, text="Height:", width=50, anchor="w",
                     font=ctk.CTkFont(size=11), text_color=COLORS["text_secondary"]).pack(side="left")
        self.pd_edit_height = ctk.CTkEntry(dim_edit_row, width=70, height=28,
                                            fg_color=COLORS["bg_card"], border_color=COLORS["accent_dim"])
        self.pd_edit_height.insert(0, str(height))
        self.pd_edit_height.pack(side="left")

        ctk.CTkLabel(dim_edit_row,
                     text=f"Total: {float(cost):.2f} DA" if cost else "Total: 0.00 DA",
                     font=ctk.CTkFont(size=12, weight="bold"),
                     text_color=COLORS["accent"]).pack(side="right", padx=(0, 4))

        # ── BOM Components ──
        ctk.CTkLabel(self.pd_edit_area, text="COMPONENTS",
                     font=ctk.CTkFont(size=12, weight="bold"),
                     text_color=COLORS["text_muted"]).pack(pady=(2, 3), anchor="w")

        self.pd_edit_bom_frame = ctk.CTkScrollableFrame(
            self.pd_edit_area, fg_color=COLORS["bg_dark"], corner_radius=10, height=120
        )
        self.pd_edit_bom_frame.pack(fill="both", expand=True, pady=(0, 4))

        # Header
        hdr = ctk.CTkFrame(self.pd_edit_bom_frame, fg_color="transparent")
        hdr.pack(fill="x", pady=(4, 2))
        ctk.CTkLabel(hdr, text="Name", width=120, anchor="w",
                     font=ctk.CTkFont(size=10, weight="bold"),
                     text_color=COLORS["text_muted"]).pack(side="left", padx=(4, 0))
        ctk.CTkLabel(hdr, text="Qty", width=55, anchor="center",
                     font=ctk.CTkFont(size=10, weight="bold"),
                     text_color=COLORS["text_muted"]).pack(side="left", padx=2)
        ctk.CTkLabel(hdr, text="Unit Price", width=75, anchor="center",
                     font=ctk.CTkFont(size=10, weight="bold"),
                     text_color=COLORS["text_muted"]).pack(side="left", padx=2)
        ctk.CTkLabel(hdr, text="Subtotal", width=75, anchor="e",
                     font=ctk.CTkFont(size=10, weight="bold"),
                     text_color=COLORS["text_muted"]).pack(side="right", padx=(0, 36))

        ctk.CTkFrame(self.pd_edit_bom_frame, height=1, fg_color=COLORS["border"]).pack(fill="x", padx=4, pady=1)

        # Load existing components
        components = self.db_mgr.get_components_for_product(self._pd_product_id)
        for comp_id, name, qty, unit_price, subtotal in components:
            self._pd_add_edit_comp_row(
                comp_id, name,
                f"{float(qty):.2f}" if qty else "0.00",
                f"{float(unit_price):.2f}" if unit_price else "0.00",
                f"{float(subtotal):.2f}" if subtotal else "0.00"
            )

        # Add component button
        btn_row = ctk.CTkFrame(self.pd_edit_area, fg_color="transparent")
        btn_row.pack(fill="x", pady=(2, 4))

        ctk.CTkButton(
            btn_row, text="➕ Add Component", height=28,
            fg_color="transparent", hover_color=COLORS["bg_card_hover"],
            border_width=1, border_color=COLORS["accent_dim"],
            text_color=COLORS["accent"], font=ctk.CTkFont(size=11),
            command=lambda: self._pd_add_edit_comp_row(None)
        ).pack(side="left")

        # Save button
        ctk.CTkButton(
            btn_row, text="💾  Save All Changes", height=34,
            fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"],
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._pd_save_edit
        ).pack(side="right")

    def _pd_add_edit_comp_row(self, comp_id, name="", qty="1.00", price="0.00", subtotal="0.00"):
        row = ctk.CTkFrame(self.pd_edit_bom_frame, fg_color="transparent")
        row.pack(fill="x", pady=2)

        name_var = ctk.StringVar(value=name)
        ctk.CTkEntry(row, textvariable=name_var, width=120, height=28,
                     font=ctk.CTkFont(size=11), placeholder_text="Name",
                     fg_color=COLORS["bg_card"], border_color=COLORS["accent_dim"]
                     ).pack(side="left", padx=(4, 2))

        qty_var = ctk.StringVar(value=qty)
        ctk.CTkEntry(row, textvariable=qty_var, width=55, height=28,
                     font=ctk.CTkFont(size=11),
                     fg_color=COLORS["bg_card"], border_color=COLORS["accent_dim"]
                     ).pack(side="left", padx=2)

        price_var = ctk.StringVar(value=price)
        ctk.CTkEntry(row, textvariable=price_var, width=75, height=28,
                     font=ctk.CTkFont(size=11),
                     fg_color=COLORS["bg_card"], border_color=COLORS["accent_dim"]
                     ).pack(side="left", padx=2)

        sub_label = ctk.CTkLabel(row, text=f"{subtotal} DA", width=75, anchor="e",
                                  font=ctk.CTkFont(size=11),
                                  text_color=COLORS["text_secondary"])
        sub_label.pack(side="left", padx=2)

        ctk.CTkButton(
            row, text="✕", width=26, height=26,
            fg_color="transparent", hover_color=COLORS["error"],
            text_color=COLORS["error"], font=ctk.CTkFont(size=11),
            command=lambda r=row, cid=comp_id: self._pd_remove_edit_comp(r, cid)
        ).pack(side="right", padx=(2, 4))

        self._pd_comp_vars.append((comp_id, name_var, qty_var, price_var, row))

    def _pd_remove_edit_comp(self, row, comp_id):
        if comp_id is not None:
            confirm = messagebox.askyesno("Delete Component",
                "Remove this component permanently?", parent=self)
            if not confirm:
                return
            self.db_mgr.delete_component(comp_id)

        self._pd_comp_vars = [(c, n, q, p, r) for c, n, q, p, r in self._pd_comp_vars if r != row]
        row.destroy()

    def _pd_save_edit(self):
        if not self._pd_product_id:
            return

        try:
            new_w = int(self.pd_edit_width.get().strip())
            new_h = int(self.pd_edit_height.get().strip())
        except ValueError:
            messagebox.showerror("Error", "Width/Height must be integers.", parent=self)
            return

        # Auto-checkpoint
        product = self.db_mgr.get_product_by_id(self._pd_product_id)
        if product:
            _, cat, dim, _, _, color, _ = product
            self.db_mgr.create_checkpoint(f"Auto — before edit {cat}/{color}/{dim}")
            new_dim = f"{new_w}*{new_h}"
            self.db_mgr.update_product(self._pd_product_id, cat, color, new_dim, new_w, new_h)

        # Update/add components
        for comp_id, name_var, qty_var, price_var, _ in self._pd_comp_vars:
            cname = name_var.get().strip()
            if not cname:
                continue
            try:
                cqty = float(qty_var.get())
                cprice = float(price_var.get())
            except ValueError:
                messagebox.showerror("Error", f"Invalid number for '{cname}'.", parent=self)
                return

            if comp_id is not None:
                self.db_mgr.update_component(comp_id, cname, cqty, cprice)
            else:
                self.db_mgr.add_component(self._pd_product_id, cname, cqty, cprice)

        self._update_cp_status()

        prod = self.db_mgr.get_product_by_id(self._pd_product_id)
        total = float(prod[6]) if prod and prod[6] else 0
        self.pd_status.configure(
            text=f"✅ Saved — Total: {total:.2f} DA",
            text_color=COLORS["success"]
        )

        if self.refresh_callback:
            self.refresh_callback()

        messagebox.showinfo("Saved", f"Product updated. New total: {total:.2f} DA", parent=self)

        # Reload to refresh comp IDs
        self._pd_load_edit_form()

    # ─── DELETE PRODUCT ──────────────────────────────────────────────────────

    def _pd_delete_product(self):
        if not self._pd_product_id:
            return

        product = self.db_mgr.get_product_by_id(self._pd_product_id)
        if not product:
            return

        _, cat, dim, _, _, color, cost = product

        confirm = messagebox.askyesno(
            "Confirm Delete",
            f"Permanently delete:\n\n{cat} / {color} / {dim}\nCost: {float(cost):.2f} DA\n\nThis will remove the product and ALL its components.\nAre you sure?",
            parent=self,
            icon="warning"
        )
        if not confirm:
            return

        cp_confirm = messagebox.askyesno(
            "Create Restore Point?",
            "Do you want to create a restore point before deleting this product?\n\n(Click 'Yes' for safety, or 'No' to vaporize it forever without a backup).",
            parent=self
        )

        if cp_confirm:
            self.db_mgr.create_checkpoint(f"Auto — before deleting {cat}/{color}/{dim}")
            
        self.db_mgr.delete_product(self._pd_product_id)

        self._pd_product_id = None
        self.pd_delete_btn.configure(state="disabled")
        self._update_cp_status()

        self.pd_status.configure(
            text=f"🗑 Deleted: {cat} / {color} / {dim}",
            text_color=COLORS["error"]
        )

        if self.refresh_callback:
            self.refresh_callback()

        messagebox.showinfo("Deleted", f"Product removed: {cat} / {color} / {dim}", parent=self)

        # Reset to edit selector
        self._pd_show_edit_form()

    # ═══════════════════════════════════════════════════════════════════════════
    # SHARED: Checkpoints & Restore
    # ═══════════════════════════════════════════════════════════════════════════

    def _update_cp_status(self):
        cps = self.db_mgr.list_checkpoints()
        self.cp_status.configure(text=f"📌 {len(cps)} checkpoint(s) available")

    def _create_manual_checkpoint(self):
        dialog = ctk.CTkInputDialog(text="Checkpoint name (optional):", title="Create Checkpoint")
        name = dialog.get_input()
        if name is None:
            return
        _, cp_name = self.db_mgr.create_checkpoint(name if name.strip() else None)
        self._update_cp_status()
        messagebox.showinfo("Checkpoint Created", f"Saved: {cp_name}", parent=self)

    def _open_restore_dialog(self):
        checkpoints = self.db_mgr.list_checkpoints()
        if not checkpoints:
            messagebox.showinfo("No Checkpoints", "No checkpoints available to restore.", parent=self)
            return

        restore_win = ctk.CTkToplevel(self)
        restore_win.title("Restore Checkpoint")
        restore_win.configure(fg_color=COLORS["bg_dark"])

        screen_w = restore_win.winfo_screenwidth()
        screen_h = restore_win.winfo_screenheight()
        rw = max(450, int(screen_w * 0.3))
        rh = max(350, int(screen_h * 0.4))
        rx = (screen_w - rw) // 2
        ry = (screen_h - rh) // 2
        restore_win.geometry(f"{rw}x{rh}+{rx}+{ry}")

        restore_win.transient(self)
        restore_win.grab_set()
        restore_win.lift()
        restore_win.after(100, restore_win.focus_force)

        ctk.CTkLabel(
            restore_win, text="⏪  SELECT CHECKPOINT TO RESTORE",
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
            text_color=COLORS["accent"]
        ).pack(pady=(20, 4), padx=20, anchor="w")

        ctk.CTkLabel(
            restore_win, text="This will revert ALL products and pricing to the selected state.",
            font=ctk.CTkFont(size=12), text_color=COLORS["warning"]
        ).pack(pady=(0, 12), padx=20, anchor="w")

        scroll = ctk.CTkScrollableFrame(restore_win, fg_color=COLORS["bg_card"], corner_radius=12)
        scroll.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        for cp_id, cp_name, cp_time in checkpoints:
            row = ctk.CTkFrame(scroll, fg_color="transparent")
            row.pack(fill="x", pady=4)

            ctk.CTkLabel(
                row, text=f"📌 {cp_name}",
                font=ctk.CTkFont(size=13, weight="bold"),
                text_color=COLORS["text_primary"]
            ).pack(side="left", padx=(8, 0))

            ctk.CTkLabel(
                row, text=cp_time,
                font=ctk.CTkFont(size=11),
                text_color=COLORS["text_muted"]
            ).pack(side="left", padx=(12, 0))

            ctk.CTkButton(
                row, text="🗑", width=32, height=32,
                fg_color="transparent", hover_color=COLORS["error"],
                text_color=COLORS["error"],
                command=lambda cid=cp_id, win=restore_win: self._delete_checkpoint(cid, win)
            ).pack(side="right", padx=(4, 8))

            ctk.CTkButton(
                row, text="Restore", width=80, height=32,
                fg_color=COLORS["warning"], hover_color="#e5a800",
                text_color=COLORS["bg_dark"],
                font=ctk.CTkFont(size=12, weight="bold"),
                command=lambda cid=cp_id, cname=cp_name, win=restore_win: self._do_restore(cid, cname, win)
            ).pack(side="right", padx=4)

    def _do_restore(self, checkpoint_id, checkpoint_name, dialog):
        confirm = messagebox.askyesno(
            "Confirm Restore",
            f"Restore all products and pricing to:\n\n{checkpoint_name}\n\nThis cannot be undone.",
            parent=dialog
        )
        if not confirm:
            return
        self.db_mgr.restore_checkpoint(checkpoint_id)
        dialog.destroy()
        self._update_cp_status()
        messagebox.showinfo("Restored", f"Products and pricing restored to: {checkpoint_name}", parent=self)
        if self.refresh_callback:
            self.refresh_callback()

    def _delete_checkpoint(self, checkpoint_id, dialog):
        confirm = messagebox.askyesno("Delete Checkpoint", "Delete this checkpoint permanently?", parent=dialog)
        if not confirm:
            return
        self.db_mgr.delete_checkpoint(checkpoint_id)
        dialog.destroy()
        self._update_cp_status()
        self._open_restore_dialog()


class CPQApp(ctk.CTk):
    """Main application window."""

    def __init__(self):
        super().__init__()

        self.db = DatabaseQuery()
        self.title("CPQ — Configure Price Quote")

        # ── Screen-aware sizing + DPI scaling ──
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()

        # Scale factor: everything is designed for 1080p (1920x1080).
        # On smaller/larger screens, scale widgets proportionally.
        REF_W, REF_H = 1920, 1080
        scale_w = screen_w / REF_W
        scale_h = screen_h / REF_H
        scale_factor = min(scale_w, scale_h)  # Use the tighter axis
        scale_factor = max(0.65, min(scale_factor, 1.6))  # Clamp: 65%–160%

        ctk.set_widget_scaling(scale_factor)
        ctk.set_window_scaling(scale_factor)

        win_w = max(int(700 * scale_factor), int(screen_w * 0.65))
        win_h = max(int(500 * scale_factor), int(screen_h * 0.75))
        # Don't exceed screen
        win_w = min(win_w, screen_w - 40)
        win_h = min(win_h, screen_h - 80)
        x = (screen_w - win_w) // 2
        y = (screen_h - win_h) // 2
        self.geometry(f"{win_w}x{win_h}+{x}+{y}")
        self.minsize(int(700 * scale_factor), int(500 * scale_factor))
        self.configure(fg_color=COLORS["bg_dark"])

        # State
        self._selected_category = None
        self._selected_color = None
        self._dimensions_cache = []

        self._build_layout()
        self._populate_categories()

    def _build_layout(self):
        # ── Top Bar ──
        self.top_bar = ctk.CTkFrame(self, height=56, fg_color=COLORS["bg_card"],
                                     corner_radius=0)
        self.top_bar.pack(fill="x")
        self.top_bar.pack_propagate(False)

        self.logo_label = ctk.CTkLabel(
            self.top_bar, text="⬡  CPQ",
            font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"),
            text_color=COLORS["accent"]
        )
        self.logo_label.pack(side="left", padx=24)

        self.admin_btn = ctk.CTkButton(
            self.top_bar, text="⚙ Admin", width=80, height=30,
            command=self.open_admin, fg_color=COLORS["accent_dim"]
        )
        self.admin_btn.pack(side="left", padx=20)

        self.status_label = ctk.CTkLabel(
            self.top_bar, text="",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=COLORS["text_muted"]
        )
        self.status_label.pack(side="right", padx=24)

        # Update status with product count
        try:
            count = self.db.get_product_count()
            self.status_label.configure(text=f"📦 {count} products loaded")
        except Exception:
            self.status_label.configure(text="⚠ Database error")

        # ── Main Container (grid-based for responsive scaling) ──
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.pack(fill="both", expand=True, padx=24, pady=20)
        self.main_container.columnconfigure(0, weight=2, minsize=320)
        self.main_container.columnconfigure(1, weight=3, minsize=300)
        self.main_container.rowconfigure(0, weight=1)

        # Left Panel — Selectors
        self.left_panel = ctk.CTkFrame(
            self.main_container, fg_color=COLORS["bg_card"],
            corner_radius=16, border_width=1, border_color=COLORS["border"]
        )
        self.left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 12))

        self._build_selectors()

        # Right Panel — Pricing Card
        self.pricing_card = PricingCard(self.main_container)
        self.pricing_card.grid(row=0, column=1, sticky="nsew", padx=(12, 0))

    def _build_selectors(self):
        # Title
        title = ctk.CTkLabel(
            self.left_panel, text="CONFIGURATION",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color=COLORS["text_muted"]
        )
        title.pack(pady=(24, 4), padx=24, anchor="w")

        subtitle = ctk.CTkLabel(
            self.left_panel,
            text="Search or select category, color, and dimension",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=COLORS["text_secondary"]
        )
        subtitle.pack(pady=(0, 12), padx=24, anchor="w")

        # ── Search Bar ──
        self.search_frame = ctk.CTkFrame(self.left_panel, fg_color="transparent")
        self.search_frame.pack(fill="x", padx=24, pady=(0, 8))

        self.search_entry = ctk.CTkEntry(
            self.search_frame,
            placeholder_text="🔍  Search dimension (e.g. 600*60)...",
            height=40,
            font=ctk.CTkFont(family="Segoe UI", size=13),
            fg_color=COLORS["bg_dark"],
            border_color=COLORS["accent_dim"],
            text_color=COLORS["text_primary"],
            placeholder_text_color=COLORS["text_muted"],
            corner_radius=10
        )
        self.search_entry.pack(fill="x")
        self.search_entry.bind("<KeyRelease>", self._on_search_change)

        # ── Search Results (hidden by default) ──
        self.search_results_frame = ctk.CTkScrollableFrame(
            self.left_panel,
            height=0,
            fg_color=COLORS["bg_dark"],
            corner_radius=10
        )
        self._search_visible = False

        # ── Separator between search and dropdowns ──
        self.search_sep = ctk.CTkFrame(self.left_panel, height=1, fg_color=COLORS["border"])
        self.search_sep.pack(fill="x", padx=24, pady=(4, 12))

        # ── Step 1: Category ──
        self._make_step_label(self.left_panel, "1", "PRODUCT CATEGORY")

        self.category_var = ctk.StringVar(value="Select category...")
        self.category_menu = ctk.CTkOptionMenu(
            self.left_panel,
            variable=self.category_var,
            values=["Loading..."],
            command=self._on_category_change,
            height=40,
            font=ctk.CTkFont(family="Segoe UI", size=13),
            dropdown_font=ctk.CTkFont(family="Segoe UI", size=13),
            fg_color=COLORS["bg_dark"],
            button_color=COLORS["accent_dim"],
            button_hover_color=COLORS["accent"],
            dropdown_fg_color=COLORS["bg_card"],
            dropdown_hover_color=COLORS["accent_dim"],
            corner_radius=10
        )
        self.category_menu.pack(fill="x", padx=24, pady=(0, 16))

        # ── Step 2: Color ──
        self._make_step_label(self.left_panel, "2", "COLOR / FINISH")

        self.color_var = ctk.StringVar(value="Select color...")
        self.color_menu = ctk.CTkOptionMenu(
            self.left_panel,
            variable=self.color_var,
            values=["—"],
            command=self._on_color_change,
            height=40,
            font=ctk.CTkFont(family="Segoe UI", size=13),
            dropdown_font=ctk.CTkFont(family="Segoe UI", size=13),
            fg_color=COLORS["bg_dark"],
            button_color=COLORS["accent_dim"],
            button_hover_color=COLORS["accent"],
            dropdown_fg_color=COLORS["bg_card"],
            dropdown_hover_color=COLORS["accent_dim"],
            corner_radius=10,
            state="disabled"
        )
        self.color_menu.pack(fill="x", padx=24, pady=(0, 16))

        # ── Step 3: Dimension ──
        self._make_step_label(self.left_panel, "3", "DIMENSION (W × H)")

        self.dim_var = ctk.StringVar(value="Select dimension...")
        self.dim_menu = ctk.CTkOptionMenu(
            self.left_panel,
            variable=self.dim_var,
            values=["—"],
            command=self._on_dimension_change,
            height=40,
            font=ctk.CTkFont(family="Segoe UI", size=13),
            dropdown_font=ctk.CTkFont(family="Segoe UI", size=13),
            fg_color=COLORS["bg_dark"],
            button_color=COLORS["accent_dim"],
            button_hover_color=COLORS["accent"],
            dropdown_fg_color=COLORS["bg_card"],
            dropdown_hover_color=COLORS["accent_dim"],
            corner_radius=10,
            state="disabled"
        )
        self.dim_menu.pack(fill="x", padx=24, pady=(0, 24))

        # ── Reset Button ──
        self.reset_btn = ctk.CTkButton(
            self.left_panel, text="↺  Reset Selection",
            command=self._reset_all,
            height=38,
            font=ctk.CTkFont(family="Segoe UI", size=13),
            fg_color="transparent",
            border_width=1,
            border_color=COLORS["border"],
            hover_color=COLORS["bg_card_hover"],
            text_color=COLORS["text_secondary"],
            corner_radius=10
        )
        self.reset_btn.pack(fill="x", padx=24, pady=(8, 24))

        # ── Status Indicator ──
        self.selector_status = ctk.CTkLabel(
            self.left_panel, text="",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=COLORS["text_muted"]
        )
        self.selector_status.pack(pady=(0, 16), padx=24, anchor="w")

    def _make_step_label(self, parent, step_num, text):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", padx=24, pady=(4, 6))

        badge = ctk.CTkLabel(
            frame, text=step_num, width=24, height=24,
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            fg_color=COLORS["accent_dim"],
            corner_radius=12,
            text_color=COLORS["accent"]
        )
        badge.pack(side="left", padx=(0, 8))

        label = ctk.CTkLabel(
            frame, text=text,
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=COLORS["text_secondary"]
        )
        label.pack(side="left")

    # ─── Search Logic ────────────────────────────────────────────────────────

    def _on_search_change(self, event=None):
        query = self.search_entry.get().strip()
        if len(query) < 2:
            self._hide_search_results()
            return
        results = self.db.search_products(query)
        self._show_search_results(results)

    def _show_search_results(self, results):
        # Clear previous
        for w in self.search_results_frame.winfo_children():
            w.destroy()

        if not results:
            self.search_results_frame.configure(height=40)
            if not self._search_visible:
                self.search_results_frame.pack(after=self.search_frame, fill="x", padx=24, pady=(0, 4))
                self._search_visible = True
            lbl = ctk.CTkLabel(
                self.search_results_frame, text="No results found",
                font=ctk.CTkFont(family="Segoe UI", size=12),
                text_color=COLORS["text_muted"]
            )
            lbl.pack(pady=8)
            return

        # Show results frame
        display_height = min(len(results) * 36, 180)
        self.search_results_frame.configure(height=display_height)
        if not self._search_visible:
            self.search_results_frame.pack(after=self.search_frame, fill="x", padx=24, pady=(0, 4))
            self._search_visible = True

        cat_names = {
            "GSD": "GSD", "GDD": "GDD", "GBF": "GBF"
        }
        for cat, color, dim, w, h, cost in results:
            row_btn = ctk.CTkButton(
                self.search_results_frame,
                text=f"{cat}  ·  {color}  ·  {dim}  ({w}×{h})    —  {cost:,.2f} DA" if cost else f"{cat}  ·  {color}  ·  {dim}  ({w}×{h})",
                font=ctk.CTkFont(family="Segoe UI", size=12),
                fg_color="transparent",
                hover_color=COLORS["accent_dim"],
                text_color=COLORS["text_secondary"],
                anchor="w",
                height=32,
                corner_radius=8,
                command=lambda c=cat, co=color, d=dim: self._on_search_select(c, co, d)
            )
            row_btn.pack(fill="x", padx=2, pady=1)

    def _hide_search_results(self):
        if self._search_visible:
            self.search_results_frame.pack_forget()
            self._search_visible = False
            for w in self.search_results_frame.winfo_children():
                w.destroy()

    def _on_search_select(self, category_code, color, dimension):
        """Handle click on search result — load product and sync dropdowns."""
        # Hide search results
        self._hide_search_results()
        self.search_entry.delete(0, "end")

        # Sync state
        self._selected_category = category_code
        self._selected_color = color

        # Sync category dropdown
        for display, code in self._category_map.items():
            if code == category_code:
                self.category_var.set(display)
                break

        # Sync color dropdown
        colors = self.db.get_colors_for_category(category_code)
        self.color_menu.configure(state="normal", values=colors)
        self.color_var.set(color)

        # Sync dimension dropdown
        dims = self.db.get_dimensions_for(category_code, color)
        self._dimensions_cache = dims
        display_dims = [f"{d[0]}  ({d[1]}×{d[2]} mm)" for d in dims]
        self._dim_map = {f"{d[0]}  ({d[1]}×{d[2]} mm)": d[0] for d in dims}
        self.dim_menu.configure(state="normal", values=display_dims)
        for disp, dim_key in self._dim_map.items():
            if dim_key == dimension:
                self.dim_var.set(disp)
                break

        # Load product + BOM
        product = self.db.get_product(category_code, color, dimension)
        components = self.db.get_product_components(category_code, color, dimension)
        if product:
            self.pricing_card.update_card(product, components)
            self.selector_status.configure(
                text="✓ Product found — pricing displayed",
                text_color=COLORS["success"]
            )

    # ─── Cascade Logic ───────────────────────────────────────────────────────

    def _populate_categories(self):
        categories = self.db.get_categories()
        display_values = [f"{code}  —  {name}" for code, name in categories]
        self._category_map = {f"{code}  —  {name}": code for code, name in categories}
        self.category_menu.configure(values=display_values)

    def _on_category_change(self, selection):
        code = self._category_map.get(selection)
        if not code:
            return
        self._selected_category = code

        # Reset downstream
        self.color_var.set("Select color...")
        self.dim_var.set("Select dimension...")
        self.dim_menu.configure(state="disabled", values=["—"])
        self.pricing_card.clear_card()

        # Populate colors
        colors = self.db.get_colors_for_category(code)
        if colors:
            self.color_menu.configure(state="normal", values=colors)
            self.selector_status.configure(
                text=f"✓ {len(colors)} color(s) available"
            )
        else:
            self.color_menu.configure(state="disabled", values=["No colors found"])
            self.selector_status.configure(text="⚠ No colors for this category")

    def _on_color_change(self, selection):
        self._selected_color = selection

        # Reset dimension
        self.dim_var.set("Select dimension...")
        self.pricing_card.clear_card()

        # Populate dimensions
        dims = self.db.get_dimensions_for(self._selected_category, selection)
        self._dimensions_cache = dims
        if dims:
            display = [f"{d[0]}  ({d[1]}×{d[2]} mm)" for d in dims]
            self._dim_map = {f"{d[0]}  ({d[1]}×{d[2]} mm)": d[0] for d in dims}
            self.dim_menu.configure(state="normal", values=display)
            self.selector_status.configure(
                text=f"✓ {len(dims)} dimension(s) available"
            )
        else:
            self.dim_menu.configure(state="disabled", values=["No dimensions found"])
            self.selector_status.configure(text="⚠ No dimensions for this combo")

    def _on_dimension_change(self, selection):
        dim_key = self._dim_map.get(selection)
        if not dim_key:
            return

        # Fetch product
        product = self.db.get_product(
            self._selected_category, self._selected_color, dim_key
        )

        # Fetch BOM components
        components = self.db.get_product_components(
            self._selected_category, self._selected_color, dim_key
        )

        if product:
            self.pricing_card.update_card(product, components)
            self.selector_status.configure(
                text="✓ Product found — pricing displayed",
                text_color=COLORS["success"]
            )
        else:
            self.pricing_card.clear_card()
            self.selector_status.configure(
                text="⚠ Non-Standard — not in catalog",
                text_color=COLORS["warning"]
            )

    def refresh_view(self):
        # Refresh product count in status bar
        try:
            count = self.db.get_product_count()
            self.status_label.configure(text=f"📦 {count} products loaded")
        except Exception:
            pass

        # Save current selections
        current_cat = self.category_var.get()
        current_color = self.color_var.get()
        current_dim = self.dim_var.get()

        # Repopulate top-level categories from DB
        self._populate_categories()

        # Attempt to restore previous cascade state
        if current_cat in self._category_map:
            self.category_var.set(current_cat)
            self._on_category_change(current_cat)

            if current_color != "Select color..." and current_color in self.color_menu.cget("values"):
                self.color_var.set(current_color)
                self._on_color_change(current_color)

                if current_dim != "Select dimension..." and current_dim in [val.split(" ")[0] for val in self.dim_menu.cget("values")]:
                    # Need to match the full string for the dropdown if we want, but _on_dimension_change handles the raw dim string or display string
                    self.dim_var.set(current_dim)
                    self._on_dimension_change(current_dim)
        else:
            self._reset_all()
            
    def open_admin(self):
        AdminWindow(self, refresh_callback=self.refresh_view)

    def _reset_all(self):
        self._selected_category = None
        self._selected_color = None
        self._dimensions_cache = []
        self.category_var.set("Select category...")
        self.color_var.set("Select color...")
        self.dim_var.set("Select dimension...")
        self.color_menu.configure(state="disabled", values=["—"])
        self.dim_menu.configure(state="disabled", values=["—"])
        self.pricing_card.clear_card()
        self.selector_status.configure(text="", text_color=COLORS["text_muted"])
        self.search_entry.delete(0, "end")
        self._hide_search_results()


# ─── Entry Point ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = CPQApp()
    app.mainloop()
