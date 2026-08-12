"""
CPQ Desktop Application - Main GUI
CustomTkinter interface with cascading dropdown logic and pricing card display.
"""

import customtkinter as ctk
import sqlite3
import os
import sys
import ctypes
import traceback
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


def format_dim_display(dim_str, w=None, h=None):
    """Format dimension string for display based on geometry type."""
    dim_str = str(dim_str) if dim_str else ""
    if dim_str.startswith("Ø"):
        # RMB: ØDiamètre*Hauteur
        parts = dim_str[1:].split("*")
        if len(parts) == 2:
            return f"Ø{parts[0]} × H: {parts[1]} mm"
        return f"Ø{dim_str[1:]} mm"
    elif dim_str.count("*") == 2:
        # Tôle: Largeur*Profondeur*Hauteur
        parts = dim_str.split("*")
        return f"L: {parts[0]} × P: {parts[1]} × H: {parts[2]} mm"
    else:
        # Legacy: W×H
        if w is not None and h is not None:
            return f"{w}×{h} mm"
        return f"{dim_str} mm"


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
            self, text="DÉTAILS DE TARIFICATION",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color=COLORS["text_muted"]
        )
        self.header.pack(pady=(20, 5), padx=20, anchor="w")

        self.product_label = ctk.CTkLabel(
            self, text="Sélectionner une configuration de produit",
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
            self.pr_frame, text="PR  ·  PRIX DE REVIENT (COÛT)",
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
            self.detail_frame, text="—",
            font=ctk.CTkFont(family="Segoe UI", size=14),
            text_color=COLORS["text_secondary"]
        )
        self.detail_dims.pack(pady=(0, 12), padx=15, anchor="w")

        # ── BOM Separator ──
        self.bom_sep = ctk.CTkFrame(self, height=1, fg_color=COLORS["border"])
        self.bom_sep.pack(fill="x", padx=20, pady=(10, 5))

        # ── BOM Header ──
        self.bom_header = ctk.CTkLabel(
            self, text="COMPOSANTS",
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

        # Dimensions — parse dimension string for geometry type
        dim_str = str(dim) if dim else ""
        if dim_str.startswith("Ø"):
            # RMB: ØDiamètre*Hauteur
            parts = dim_str[1:].split("*")
            if len(parts) == 2:
                self.detail_dims.configure(text=f"Diamètre: {parts[0]} mm  ×  Hauteur: {parts[1]} mm")
            else:
                self.detail_dims.configure(text=f"Diamètre: {dim_str[1:]} mm")
        elif dim_str.count("*") == 2:
            # Tôle: Largeur*Profondeur*Hauteur
            parts = dim_str.split("*")
            self.detail_dims.configure(text=f"L: {parts[0]} mm  ×  P: {parts[1]} mm  ×  H: {parts[2]} mm")
        else:
            # Legacy: Largeur*Hauteur
            self.detail_dims.configure(text=f"L: {w} mm  ×  H: {h} mm")

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

            price_text = f"{subtotal:.2f} DA" if subtotal is not None else "—"
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
        total = sum(s for _, _, _, s in components if s is not None)
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
        self.product_label.configure(text="Sélectionner une configuration de produit")
        self.pr_value.configure(text="— DA")
        self.detail_dims.configure(text="L: —  ×  H: —")
        self.clear_bom()

class AdminWindow(ctk.CTkToplevel):
    """Admin Panel with tabbed layout: Pricing editor + Product CRUD management."""

    def __init__(self, master, refresh_callback=None):
        super().__init__(master)
        self.title("Administration — Gestion des produits et de la tarification")
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
            self, text="⚙  PANNEAU D'ADMINISTRATION",
            font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"),
            text_color=COLORS["accent"]
        ).pack(pady=(16, 2), padx=24, anchor="w")

        ctk.CTkLabel(
            self, text="Gérer la tarification des produits et le catalogue",
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
            btn_frame, text="📌 Créer un point de sauvegarde", height=32,
            fg_color=COLORS["accent_dim"], hover_color=COLORS["accent"],
            command=self._create_manual_checkpoint
        )
        self.pr_checkpoint_btn.pack(side="left", padx=5)

        self.pr_restore_btn = ctk.CTkButton(
            btn_frame, text="🕒 Restaurer les données", height=32,
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
            mode_frame, text="➕  Nouveau Produit", height=36,
            fg_color=COLORS["success"], hover_color="#2ab883",
            text_color=COLORS["bg_dark"],
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self._pd_show_new_form
        )
        self.pd_new_btn.pack(side="left", padx=(0, 8))

        self.pd_edit_btn = ctk.CTkButton(
            mode_frame, text="✏  Modifier Produit", height=36,
            fg_color=COLORS["accent_dim"], hover_color=COLORS["accent"],
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self._pd_show_edit_form
        )
        self.pd_edit_btn.pack(side="left", padx=(0, 8))

        self.pd_delete_btn = ctk.CTkButton(
            mode_frame, text="🗑  Supprimer", height=36,
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
            text="Choisissez une action ci-dessus :\n\n➕  Nouveau Produit — créer une nouvelle entrée dans le catalogue\n✏  Modifier Produit — modifier les détails et les composants d'un produit\n🗑  Supprimer — retirer un produit du catalogue",
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
        self.pd_delete_btn.configure(state="disabled")
        self.pd_new_btn.configure(fg_color=COLORS["success"])
        self.pd_edit_btn.configure(fg_color=COLORS["accent_dim"])

        try:
            from calculator_gui import CalculatorFrame
            calc_frame = CalculatorFrame(self.pd_content_frame, self.db_mgr, refresh_callback=self.refresh_callback)
            calc_frame.pack(fill="both", expand=True)
        except Exception as e:
            err_msg = traceback.format_exc()
            messagebox.showerror("Erreur — Nouveau Produit", f"Impossible de charger le calculateur :\n\n{err_msg}", parent=self)

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

        ctk.CTkLabel(sel, text="SÉLECTIONNER LE PRODUIT À MODIFIER",
                     font=ctk.CTkFont(size=13, weight="bold"),
                     text_color=COLORS["accent"]).pack(pady=(10, 6), padx=14, anchor="w")

        # Category
        ctk.CTkLabel(sel, text="CATÉGORIE", font=ctk.CTkFont(size=10, weight="bold"),
                     text_color=COLORS["text_muted"]).pack(pady=(2, 1), padx=14, anchor="w")
        categories = self.db_mgr.get_categories()
        self._pd_edit_cat_map = {f"{c}  —  {n}": c for c, n in categories}
        self.pd_edit_cat_var = ctk.StringVar(value="Sélectionner une catégorie...")
        ctk.CTkOptionMenu(
            sel, variable=self.pd_edit_cat_var, values=list(self._pd_edit_cat_map.keys()),
            command=self._pd_edit_on_cat, height=32,
            fg_color=COLORS["bg_card"], button_color=COLORS["accent_dim"], corner_radius=8
        ).pack(fill="x", padx=14, pady=(0, 4))

        # Color
        ctk.CTkLabel(sel, text="COULEUR", font=ctk.CTkFont(size=10, weight="bold"),
                     text_color=COLORS["text_muted"]).pack(pady=(2, 1), padx=14, anchor="w")
        self.pd_edit_color_var = ctk.StringVar(value="Sélectionner une couleur...")
        self.pd_edit_color_menu = ctk.CTkOptionMenu(
            sel, variable=self.pd_edit_color_var, values=["—"],
            command=self._pd_edit_on_color, height=32, state="disabled",
            fg_color=COLORS["bg_card"], button_color=COLORS["accent_dim"], corner_radius=8
        )
        self.pd_edit_color_menu.pack(fill="x", padx=14, pady=(0, 4))

        # Dimension
        ctk.CTkLabel(sel, text="DIMENSION", font=ctk.CTkFont(size=10, weight="bold"),
                     text_color=COLORS["text_muted"]).pack(pady=(2, 1), padx=14, anchor="w")
        self.pd_edit_dim_var = ctk.StringVar(value="Sélectionner une dimension...")
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
            self.pd_edit_area, text="Sélectionnez un produit ci-dessus pour le modifier",
            font=ctk.CTkFont(size=13), text_color=COLORS["text_muted"]
        ).pack(pady=30)

    def _pd_edit_on_cat(self, selection):
        code = self._pd_edit_cat_map.get(selection)
        if not code:
            return
        self._pd_edit_sel_cat = code
        self.pd_edit_color_var.set("Sélectionner une couleur...")
        self.pd_edit_dim_var.set("Sélectionner une dimension...")
        self.pd_edit_dim_menu.configure(state="disabled", values=["—"])
        self._pd_product_id = None
        self.pd_delete_btn.configure(state="disabled")

        colors = self.db_mgr.get_colors_for_category(code)
        if colors:
            self.pd_edit_color_menu.configure(state="normal", values=colors)
        else:
            self.pd_edit_color_menu.configure(state="disabled", values=["Aucune couleur"])

    def _pd_edit_on_color(self, selection):
        self._pd_edit_sel_color = selection
        self.pd_edit_dim_var.set("Sélectionner une dimension...")
        self._pd_product_id = None
        self.pd_delete_btn.configure(state="disabled")

        dims = self.db_mgr.get_dimensions_for(self._pd_edit_sel_cat, selection)
        if dims:
            display = [f"{d[0]}  ({format_dim_display(d[0], d[1], d[2])})" for d in dims]
            self._pd_dim_map = {f"{d[0]}  ({format_dim_display(d[0], d[1], d[2])})": d[0] for d in dims}
            self.pd_edit_dim_menu.configure(state="normal", values=display)
        else:
            self.pd_edit_dim_menu.configure(state="disabled", values=["Aucune dimension"])

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

        ctk.CTkLabel(meta, text=f"MODIFICATION : {cat} / {color} / {dim}",
                     font=ctk.CTkFont(size=12, weight="bold"),
                     text_color=COLORS["warning"]).pack(pady=(8, 2), padx=12, anchor="w")

        dim_str = str(dim) if dim else ""

        dim_edit_row = ctk.CTkFrame(meta, fg_color="transparent")
        dim_edit_row.pack(fill="x", padx=12, pady=(2, 3))

        if dim_str.startswith("Ø"):
            # RMB: ØDiamètre*Hauteur
            parts = dim_str[1:].split("*")
            diam_val = parts[0] if len(parts) >= 1 else str(width or "")
            h_val = parts[1] if len(parts) >= 2 else str(height or "")

            ctk.CTkLabel(dim_edit_row, text="Diamètre :", width=65, anchor="w",
                         font=ctk.CTkFont(size=11), text_color=COLORS["text_secondary"]).pack(side="left")
            self.pd_edit_diameter = ctk.CTkEntry(dim_edit_row, width=70, height=28,
                                                  fg_color=COLORS["bg_card"], border_color=COLORS["accent_dim"])
            self.pd_edit_diameter.insert(0, diam_val)
            self.pd_edit_diameter.pack(side="left", padx=(0, 10))

            ctk.CTkLabel(dim_edit_row, text="Hauteur :", width=55, anchor="w",
                         font=ctk.CTkFont(size=11), text_color=COLORS["text_secondary"]).pack(side="left")
            self.pd_edit_height = ctk.CTkEntry(dim_edit_row, width=70, height=28,
                                                fg_color=COLORS["bg_card"], border_color=COLORS["accent_dim"])
            self.pd_edit_height.insert(0, h_val)
            self.pd_edit_height.pack(side="left")

            self._pd_edit_geom = "rmb"

        elif dim_str.count("*") == 2:
            # Tôle: Largeur*Profondeur*Hauteur
            parts = dim_str.split("*")

            ctk.CTkLabel(dim_edit_row, text="Largeur :", width=55, anchor="w",
                         font=ctk.CTkFont(size=11), text_color=COLORS["text_secondary"]).pack(side="left")
            self.pd_edit_width = ctk.CTkEntry(dim_edit_row, width=70, height=28,
                                               fg_color=COLORS["bg_card"], border_color=COLORS["accent_dim"])
            self.pd_edit_width.insert(0, parts[0])
            self.pd_edit_width.pack(side="left", padx=(0, 10))

            ctk.CTkLabel(dim_edit_row, text="Prof. :", width=40, anchor="w",
                         font=ctk.CTkFont(size=11), text_color=COLORS["text_secondary"]).pack(side="left")
            self.pd_edit_depth = ctk.CTkEntry(dim_edit_row, width=70, height=28,
                                               fg_color=COLORS["bg_card"], border_color=COLORS["accent_dim"])
            self.pd_edit_depth.insert(0, parts[1])
            self.pd_edit_depth.pack(side="left", padx=(0, 10))

            ctk.CTkLabel(dim_edit_row, text="Haut. :", width=40, anchor="w",
                         font=ctk.CTkFont(size=11), text_color=COLORS["text_secondary"]).pack(side="left")
            self.pd_edit_height = ctk.CTkEntry(dim_edit_row, width=70, height=28,
                                                fg_color=COLORS["bg_card"], border_color=COLORS["accent_dim"])
            self.pd_edit_height.insert(0, parts[2])
            self.pd_edit_height.pack(side="left")

            self._pd_edit_geom = "tole"

        else:
            # Legacy: Largeur*Hauteur
            ctk.CTkLabel(dim_edit_row, text="Largeur :", width=55, anchor="w",
                         font=ctk.CTkFont(size=11), text_color=COLORS["text_secondary"]).pack(side="left")
            self.pd_edit_width = ctk.CTkEntry(dim_edit_row, width=70, height=28,
                                               fg_color=COLORS["bg_card"], border_color=COLORS["accent_dim"])
            self.pd_edit_width.insert(0, str(width or ""))
            self.pd_edit_width.pack(side="left", padx=(0, 10))

            ctk.CTkLabel(dim_edit_row, text="Hauteur :", width=55, anchor="w",
                         font=ctk.CTkFont(size=11), text_color=COLORS["text_secondary"]).pack(side="left")
            self.pd_edit_height = ctk.CTkEntry(dim_edit_row, width=70, height=28,
                                                fg_color=COLORS["bg_card"], border_color=COLORS["accent_dim"])
            self.pd_edit_height.insert(0, str(height or ""))
            self.pd_edit_height.pack(side="left")

            self._pd_edit_geom = "legacy"

        ctk.CTkLabel(dim_edit_row,
                     text=f"Total: {float(cost):.2f} DA" if cost else "Total: 0.00 DA",
                     font=ctk.CTkFont(size=12, weight="bold"),
                     text_color=COLORS["accent"]).pack(side="right", padx=(0, 4))

        # ── BOM Components ──
        ctk.CTkLabel(self.pd_edit_area, text="COMPOSANTS",
                     font=ctk.CTkFont(size=12, weight="bold"),
                     text_color=COLORS["text_muted"]).pack(pady=(2, 3), anchor="w")

        self.pd_edit_bom_frame = ctk.CTkScrollableFrame(
            self.pd_edit_area, fg_color=COLORS["bg_dark"], corner_radius=10, height=120
        )
        self.pd_edit_bom_frame.pack(fill="both", expand=True, pady=(0, 4))

        # Header
        hdr = ctk.CTkFrame(self.pd_edit_bom_frame, fg_color="transparent")
        hdr.pack(fill="x", pady=(4, 2))
        ctk.CTkLabel(hdr, text="Nom", width=120, anchor="w",
                     font=ctk.CTkFont(size=10, weight="bold"),
                     text_color=COLORS["text_muted"]).pack(side="left", padx=(4, 0))
        ctk.CTkLabel(hdr, text="Qté", width=55, anchor="center",
                     font=ctk.CTkFont(size=10, weight="bold"),
                     text_color=COLORS["text_muted"]).pack(side="left", padx=2)
        ctk.CTkLabel(hdr, text="Prix unitaire", width=75, anchor="center",
                     font=ctk.CTkFont(size=10, weight="bold"),
                     text_color=COLORS["text_muted"]).pack(side="left", padx=2)
        ctk.CTkLabel(hdr, text="Sous-total", width=75, anchor="e",
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
            btn_row, text="➕ Ajouter un composant", height=28,
            fg_color="transparent", hover_color=COLORS["bg_card_hover"],
            border_width=1, border_color=COLORS["accent_dim"],
            text_color=COLORS["accent"], font=ctk.CTkFont(size=11),
            command=lambda: self._pd_add_edit_comp_row(None)
        ).pack(side="left")

        # Save button
        ctk.CTkButton(
            btn_row, text="💾  Enregistrer toutes les modifications", height=34,
            fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"],
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._pd_save_edit
        ).pack(side="right")

    def _pd_add_edit_comp_row(self, comp_id, name="", qty="1.00", price="0.00", subtotal="0.00"):
        row = ctk.CTkFrame(self.pd_edit_bom_frame, fg_color="transparent")
        row.pack(fill="x", pady=2)

        name_var = ctk.StringVar(value=name)
        ctk.CTkEntry(row, textvariable=name_var, width=120, height=28,
                     font=ctk.CTkFont(size=11), placeholder_text="Nom",
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
            confirm = messagebox.askyesno("Supprimer le composant",
                "Supprimer ce composant définitivement ?", parent=self)
            if not confirm:
                return
            self.db_mgr.delete_component(comp_id)

        self._pd_comp_vars = [(c, n, q, p, r) for c, n, q, p, r in self._pd_comp_vars if r != row]
        row.destroy()

    def _pd_save_edit(self):
        if not self._pd_product_id:
            return

        try:
            new_h = int(self.pd_edit_height.get().strip())
            if self._pd_edit_geom == "rmb":
                new_w = int(self.pd_edit_diameter.get().strip())
            else:
                new_w = int(self.pd_edit_width.get().strip())
        except ValueError:
            messagebox.showerror("Erreur", "Les dimensions doivent être des entiers.", parent=self)
            return

        # Auto-checkpoint
        product = self.db_mgr.get_product_by_id(self._pd_product_id)
        if product:
            _, cat, dim, _, _, color, _ = product
            self.db_mgr.create_checkpoint(f"Auto — avant modification {cat}/{color}/{dim}")
            # Build dimension string based on geometry type
            if self._pd_edit_geom == "rmb":
                new_dim = f"Ø{new_w}*{new_h}"
            elif self._pd_edit_geom == "tole":
                try:
                    new_depth = int(self.pd_edit_depth.get().strip())
                except ValueError:
                    new_depth = 0
                new_dim = f"{new_w}*{new_depth}*{new_h}"
            else:
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
                messagebox.showerror("Erreur", f"Nombre invalide pour '{cname}'.", parent=self)
                return

            if comp_id is not None:
                self.db_mgr.update_component(comp_id, cname, cqty, cprice)
            else:
                self.db_mgr.add_component(self._pd_product_id, cname, cqty, cprice)

        self._update_cp_status()

        prod = self.db_mgr.get_product_by_id(self._pd_product_id)
        total = float(prod[6]) if prod and prod[6] else 0
        self.pd_status.configure(
            text=f"✅ Enregistré — Total : {total:.2f} DA",
            text_color=COLORS["success"]
        )

        if self.refresh_callback:
            self.refresh_callback()

        messagebox.showinfo("Succès", f"Produit mis à jour. Nouveau total : {total:.2f} DA", parent=self)

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
            "Confirmer la suppression",
            f"Supprimer définitivement :\n\n{cat} / {color} / {dim}\nCoût : {float(cost):.2f} DA\n\nCela supprimera le produit et TOUS ses composants.\nÊtes-vous sûr ?",
            parent=self,
            icon="warning"
        )
        if not confirm:
            return

        cp_confirm = messagebox.askyesno(
            "Créer un point de sauvegarde ?",
            "Voulez-vous créer un point de sauvegarde avant de supprimer ce produit ?\n\n(Cliquez sur 'Oui' par sécurité, ou sur 'Non' pour le vaporiser à jamais sans sauvegarde).",
            parent=self
        )

        if cp_confirm:
            self.db_mgr.create_checkpoint(f"Auto — avant suppression {cat}/{color}/{dim}")
            
        self.db_mgr.delete_product(self._pd_product_id)

        self._pd_product_id = None
        self.pd_delete_btn.configure(state="disabled")
        self._update_cp_status()

        self.pd_status.configure(
            text=f"🗑 Supprimé : {cat} / {color} / {dim}",
            text_color=COLORS["error"]
        )

        if self.refresh_callback:
            self.refresh_callback()

        messagebox.showinfo("Supprimé", f"Produit retiré : {cat} / {color} / {dim}", parent=self)

        # Reset to edit selector
        self._pd_show_edit_form()

    # ═══════════════════════════════════════════════════════════════════════════
    # SHARED: Checkpoints & Restore
    # ═══════════════════════════════════════════════════════════════════════════

    def _update_cp_status(self):
        cps = self.db_mgr.list_checkpoints()
        self.cp_status.configure(text=f"📌 {len(cps)} point(s) de sauvegarde disponible(s)")

    def _create_manual_checkpoint(self):
        dialog = ctk.CTkInputDialog(text="Nom du point de sauvegarde (optionnel) :", title="Créer un point de sauvegarde")
        name = dialog.get_input()
        if name is None:
            return
        _, cp_name = self.db_mgr.create_checkpoint(name if name.strip() else None)
        self._update_cp_status()
        messagebox.showinfo("Point de sauvegarde créé", f"Enregistré : {cp_name}", parent=self)

    def _open_restore_dialog(self):
        checkpoints = self.db_mgr.list_checkpoints()
        if not checkpoints:
            messagebox.showinfo("Aucun point de sauvegarde", "Aucun point de sauvegarde disponible à restaurer.", parent=self)
            return

        restore_win = ctk.CTkToplevel(self)
        restore_win.title("Restaurer un point de sauvegarde")
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
            restore_win, text="⏪  SÉLECTIONNER LE POINT DE SAUVEGARDE À RESTAURER",
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
            text_color=COLORS["accent"]
        ).pack(pady=(20, 4), padx=20, anchor="w")

        ctk.CTkLabel(
            restore_win, text="Cela rétablira TOUS les produits et la tarification à l'état sélectionné.",
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
                row, text="Restaurer", width=80, height=32,
                fg_color=COLORS["warning"], hover_color="#e5a800",
                text_color=COLORS["bg_dark"],
                font=ctk.CTkFont(size=12, weight="bold"),
                command=lambda cid=cp_id, cname=cp_name, win=restore_win: self._do_restore(cid, cname, win)
            ).pack(side="right", padx=4)

    def _do_restore(self, checkpoint_id, checkpoint_name, dialog):
        confirm = messagebox.askyesno(
            "Confirmer la restauration",
            f"Restaurer tous les produits et la tarification à :\n\n{checkpoint_name}\n\nCette action est irréversible.",
            parent=dialog
        )
        if not confirm:
            return
        self.db_mgr.restore_checkpoint(checkpoint_id)
        dialog.destroy()
        self._update_cp_status()
        messagebox.showinfo("Restauré", f"Produits et tarification restaurés à : {checkpoint_name}", parent=self)
        if self.refresh_callback:
            self.refresh_callback()

    def _delete_checkpoint(self, checkpoint_id, dialog):
        confirm = messagebox.askyesno("Supprimer le point de sauvegarde", "Supprimer ce point de sauvegarde définitivement ?", parent=dialog)
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
        self.title("CPQ — Configuration, Prix, Devis")

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
            self.top_bar, text="⚙ Administration", width=80, height=30,
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
            self.status_label.configure(text=f"📦 {count} Produits chargés")
        except Exception:
            self.status_label.configure(text="⚠ Erreur de base de données")

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
            text="Rechercher ou sélectionner une catégorie, couleur et dimension",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=COLORS["text_secondary"]
        )
        subtitle.pack(pady=(0, 12), padx=24, anchor="w")

        # ── Search Bar ──
        self.search_frame = ctk.CTkFrame(self.left_panel, fg_color="transparent")
        self.search_frame.pack(fill="x", padx=24, pady=(0, 8))

        self.search_entry = ctk.CTkEntry(
            self.search_frame,
            placeholder_text="🔍  Rechercher une dimension (ex: 600*60)...",
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

        self.category_var = ctk.StringVar(value="Sélectionner une catégorie...")
        self.category_menu = ctk.CTkOptionMenu(
            self.left_panel,
            variable=self.category_var,
            values=["Chargement..."],
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

        self.color_var = ctk.StringVar(value="Sélectionner une couleur...")
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
        self._make_step_label(self.left_panel, "3", "DIMENSION")

        self.dim_var = ctk.StringVar(value="Sélectionner une dimension...")
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
            self.left_panel, text="↺  Réinitialiser la sélection",
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

    def _format_dim_display(self, dim_str, w=None, h=None):
        """Format dimension string for display based on geometry type."""
        return format_dim_display(dim_str, w, h)

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
                self.search_results_frame, text="Aucun résultat trouvé",
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
                text=f"{cat}  ·  {color}  ·  {dim}  ({self._format_dim_display(dim, w, h)})    —  {cost:,.2f} DA" if cost else f"{cat}  ·  {color}  ·  {dim}  ({self._format_dim_display(dim, w, h)})",
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
        display_dims = [f"{d[0]}  ({self._format_dim_display(d[0], d[1], d[2])})" for d in dims]
        self._dim_map = {f"{d[0]}  ({self._format_dim_display(d[0], d[1], d[2])})": d[0] for d in dims}
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
                text="✓ Produit trouvé — tarification affichée",
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
        self.color_var.set("Sélectionner une couleur...")
        self.dim_var.set("Sélectionner une dimension...")
        self.dim_menu.configure(state="disabled", values=["—"])
        self.pricing_card.clear_card()

        # Populate colors
        colors = self.db.get_colors_for_category(code)
        if colors:
            self.color_menu.configure(state="normal", values=colors)
            self.selector_status.configure(
                text=f"✓ {len(colors)} couleur(s) disponible(s)"
            )
        else:
            self.color_menu.configure(state="disabled", values=["Aucune couleur trouvée"])
            self.selector_status.configure(text="⚠ Aucune couleur pour cette catégorie")

    def _on_color_change(self, selection):
        self._selected_color = selection

        # Reset dimension
        self.dim_var.set("Sélectionner une dimension...")
        self.pricing_card.clear_card()

        # Populate dimensions
        dims = self.db.get_dimensions_for(self._selected_category, selection)
        self._dimensions_cache = dims
        if dims:
            display = [f"{d[0]}  ({self._format_dim_display(d[0], d[1], d[2])})" for d in dims]
            self._dim_map = {f"{d[0]}  ({self._format_dim_display(d[0], d[1], d[2])})": d[0] for d in dims}
            self.dim_menu.configure(state="normal", values=display)
            self.selector_status.configure(
                text=f"✓ {len(dims)} dimension(s) disponible(s)"
            )
        else:
            self.dim_menu.configure(state="disabled", values=["Aucune dimension trouvée"])
            self.selector_status.configure(text="⚠ Aucune dimension pour cette combinaison")

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
                text="✓ Produit trouvé — tarification affichée",
                text_color=COLORS["success"]
            )
        else:
            self.pricing_card.clear_card()
            self.selector_status.configure(
                text="⚠ Non standard — pas dans le catalogue",
                text_color=COLORS["warning"]
            )

    def refresh_view(self):
        # Refresh product count in status bar
        try:
            count = self.db.get_product_count()
            self.status_label.configure(text=f"📦 {count} Produits chargés")
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

            if current_color != "Sélectionner une couleur..." and current_color in self.color_menu.cget("values"):
                self.color_var.set(current_color)
                self._on_color_change(current_color)

                if current_dim != "Sélectionner une dimension..." and current_dim in [val.split(" ")[0] for val in self.dim_menu.cget("values")]:
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
        self.category_var.set("Sélectionner une catégorie...")
        self.color_var.set("Sélectionner une couleur...")
        self.dim_var.set("Sélectionner une dimension...")
        self.color_menu.configure(state="disabled", values=["—"])
        self.dim_menu.configure(state="disabled", values=["—"])
        self.pricing_card.clear_card()
        self.selector_status.configure(text="", text_color=COLORS["text_muted"])
        self.search_entry.delete(0, "end")
        self._hide_search_results()


# ─── Entry Point ─────────────────────────────────────────────────────────────
def _global_exception_handler(exc_type, exc_value, exc_tb):
    """Catch-all: write crash log + show messagebox for windowed mode."""
    crash_log = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "CPQ_App", "crash.log")
    try:
        os.makedirs(os.path.dirname(crash_log), exist_ok=True)
        with open(crash_log, "a", encoding="utf-8") as f:
            f.write("\n" + "="*60 + "\n")
            traceback.print_exception(exc_type, exc_value, exc_tb, file=f)
    except Exception:
        pass
    err_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    try:
        messagebox.showerror("CPQ — Erreur Inattendue", err_msg)
    except Exception:
        pass

if __name__ == "__main__":
    sys.excepthook = _global_exception_handler
    app = CPQApp()
    app.mainloop()
