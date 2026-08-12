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
from tkinter import messagebox, filedialog
from database_manager import DatabaseManager
from PIL import Image


# ─── DPI Awareness (must be set before any Tk window is created) ─────────────
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)  # PROCESS_SYSTEM_DPI_AWARE
except (AttributeError, OSError):
    pass  # Non-Windows or older Windows — skip gracefully


# ─── Theme & Appearance ─────────────────────────────────────────────────────
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# ─── Color Palette ───────────────────────────────────────────────────────────
COLORS = {
    "bg_dark":       "#161616",
    "bg_card":       "#1E1E1E",
    "bg_card_hover": "#2A2A2A",
    "bg_input":      "#1A1A1A",
    "accent":        "#F05B28",
    "accent_hover":  "#FF7A4D",
    "accent_dim":    "#3D1E10",
    "text_primary":  "#FFFFFF",
    "text_secondary":"#999999",
    "text_muted":    "#555555",
    "border":        "#2E2E2E",
    "success":       "#34d399",
    "warning":       "#fbbf24",
    "error":         "#f87171",
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
                      excel_cost, excel_tariff, image_path 
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


class CPQApp(ctk.CTk):
    """Main application window."""

    def __init__(self):
        super().__init__()

        self.db = DatabaseQuery()
        self.db_mgr = DatabaseManager()
        self.title("CPQ — Configuration, Prix, Devis")

        # ── Screen-aware sizing + DPI scaling ──
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()

        # Scale factor: everything is designed for 1080p (1920x1080).
        REF_W, REF_H = 1920, 1080
        scale_w = screen_w / REF_W
        scale_h = screen_h / REF_H
        scale_factor = min(scale_w, scale_h)
        scale_factor = max(0.65, min(scale_factor, 1.6))

        ctk.set_widget_scaling(scale_factor)
        ctk.set_window_scaling(scale_factor)

        win_w = max(int(1200 * scale_factor), int(screen_w * 0.75))
        win_h = max(int(800 * scale_factor), int(screen_h * 0.85))
        win_w = min(win_w, screen_w - 40)
        win_h = min(win_h, screen_h - 80)
        x = (screen_w - win_w) // 2
        y = (screen_h - win_h) // 2
        self.geometry(f"{win_w}x{win_h}+{x}+{y}")
        self.minsize(int(1000 * scale_factor), int(700 * scale_factor))
        self.configure(fg_color=COLORS["bg_dark"])

        # State
        self._selected_category = None
        self._selected_color = None
        self._dimensions_cache = []
        self._active_tab = "catalogue"
        self._calc_loaded = False
        self._admin_loaded = False

        self._build_layout()
        self._populate_categories()

    def _build_layout(self):
        # 1. HEADER BAR
        self.top_bar = ctk.CTkFrame(self, height=56, fg_color=COLORS["bg_card"], corner_radius=0)
        self.top_bar.pack(fill="x")
        self.top_bar.pack_propagate(False)

        logo_frame = ctk.CTkFrame(self.top_bar, fg_color="transparent")
        logo_frame.pack(side="left", padx=24, pady=10)

        # Orange square logo with dark "H"
        self.logo_square = ctk.CTkLabel(
            logo_frame, text="H", width=28, height=28,
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
            fg_color=COLORS["accent"], text_color=COLORS["bg_dark"], corner_radius=4
        )
        self.logo_square.pack(side="left", padx=(0, 10))

        # HACHANI bold white
        self.logo_text = ctk.CTkLabel(
            logo_frame, text="HACHANI",
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
            text_color=COLORS["text_primary"]
        )
        self.logo_text.pack(side="left", padx=(0, 6))

        # Subtitle
        self.logo_sub = ctk.CTkLabel(
            logo_frame, text="CONFIGURATION PRIX DEVIS",
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
            text_color=COLORS["text_secondary"]
        )
        self.logo_sub.pack(side="left", pady=(4, 0))

        self.status_label = ctk.CTkLabel(
            self.top_bar, text="",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=COLORS["text_secondary"]
        )
        self.status_label.pack(side="right", padx=24)
        self._update_status_count()

        # 2. HERO SECTION
        self.hero_section = ctk.CTkFrame(self, height=90, fg_color=COLORS["bg_dark"], corner_radius=0)
        self.hero_section.pack(fill="x", padx=24, pady=(20, 10))
        self.hero_section.pack_propagate(False)

        self.hero_left = ctk.CTkFrame(self.hero_section, fg_color="transparent")
        self.hero_left.pack(side="left", fill="y")
        
        self.hero_kicker = ctk.CTkLabel(
            self.hero_left, text="CATALOGUE DE PRIX",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color=COLORS["accent"]
        )
        self.hero_kicker.pack(anchor="w")

        self.hero_title = ctk.CTkLabel(
            self.hero_left, text="GRILLES\nALUMINIUM", justify="left",
            font=ctk.CTkFont(family="Segoe UI", size=24, weight="bold"),
            text_color=COLORS["text_primary"]
        )
        self.hero_title.pack(anchor="w", pady=(0, 0))

        self.hero_right = ctk.CTkFrame(self.hero_section, fg_color="transparent")
        self.hero_right.pack(side="right", fill="y", pady=(10, 0))

        self.hero_desc = ctk.CTkLabel(
            self.hero_right, text="Recherchez et configurez des produits dans\nle catalogue de prix HACHANI.",
            justify="right",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=COLORS["text_secondary"]
        )
        self.hero_desc.pack(anchor="e")

        # 3. HORIZONTAL TAB STEPPER
        self.tab_stepper = ctk.CTkFrame(self, height=44, fg_color="transparent", corner_radius=0)
        self.tab_stepper.pack(fill="x", padx=24, pady=(0, 20))
        
        self.btn_catalogue = ctk.CTkButton(
            self.tab_stepper, text="🔧  CATALOGUE", height=40, width=160,
            command=lambda: self._switch_tab("catalogue"),
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            corner_radius=6
        )
        self.btn_catalogue.pack(side="left", padx=(0, 8))

        self.btn_calculateur = ctk.CTkButton(
            self.tab_stepper, text="⚙  CALCULATEUR", height=40, width=160,
            command=lambda: self._switch_tab("calculateur"),
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            corner_radius=6
        )
        self.btn_calculateur.pack(side="left", padx=(0, 8))

        self.btn_admin = ctk.CTkButton(
            self.tab_stepper, text="🛠  ADMINISTRATION", height=40, width=160,
            command=lambda: self._switch_tab("administration"),
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            corner_radius=6
        )
        self.btn_admin.pack(side="left")

        self.step_indicator = ctk.CTkLabel(
            self.tab_stepper, text="MODULE 1 / 3",
            font=ctk.CTkFont(family="Consolas", size=12, weight="bold"),
            text_color=COLORS["text_secondary"]
        )
        self.step_indicator.pack(side="right", padx=10)

        # 4. CONTENT AREA
        self.content_area = ctk.CTkFrame(self, fg_color="transparent")
        self.content_area.pack(fill="both", expand=True, padx=24, pady=(0, 20))

        # Create frames for each tab
        self.catalogue_frame = ctk.CTkFrame(self.content_area, fg_color="transparent")
        self.calculator_frame = ctk.CTkFrame(self.content_area, fg_color="transparent")
        self.admin_frame = ctk.CTkFrame(self.content_area, fg_color="transparent")

        self._build_catalogue_tab()
        
        # 5. FOOTER
        self.footer = ctk.CTkFrame(self, height=40, fg_color="transparent")
        self.footer.pack(fill="x", padx=24, pady=(0, 10))
        self.footer.pack_propagate(False)

        self.footer_sep = ctk.CTkFrame(self.footer, height=1, fg_color=COLORS["border"])
        self.footer_sep.pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(
            self.footer, text="© 2026 HACHANI — USAGE INTERNE UNIQUEMENT",
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
            text_color=COLORS["text_muted"]
        ).pack(side="left")

        ctk.CTkLabel(
            self.footer, text="DOCUMENT CONFIDENTIEL",
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
            text_color=COLORS["warning"]
        ).pack(side="right")

        # Initialize to catalogue tab
        self._switch_tab("catalogue")

    def _update_status_count(self):
        try:
            count = self.db.get_product_count()
            self.status_label.configure(text=f"{count} PRODUITS")
        except Exception:
            self.status_label.configure(text="⚠ ERREUR BDD")

    def _switch_tab(self, tab_name):
        self._active_tab = tab_name
        
        for frame in [self.catalogue_frame, self.calculator_frame, self.admin_frame]:
            frame.pack_forget()

        if tab_name == "catalogue":
            self.catalogue_frame.pack(fill="both", expand=True)
            self.hero_kicker.configure(text="CATALOGUE DE PRIX")
            self.hero_title.configure(text="GRILLES\nALUMINIUM")
            self.hero_desc.configure(text="Recherchez et configurez des produits dans\nle catalogue de prix HACHANI.")
            self.step_indicator.configure(text="MODULE 1 / 3")
            
            self.btn_catalogue.configure(fg_color=COLORS["accent"], text_color=COLORS["bg_dark"], hover_color=COLORS["accent_hover"])
            self.btn_calculateur.configure(fg_color=COLORS["bg_card"], text_color=COLORS["text_secondary"], hover_color=COLORS["bg_card_hover"])
            self.btn_admin.configure(fg_color=COLORS["bg_card"], text_color=COLORS["text_secondary"], hover_color=COLORS["bg_card_hover"])
            
        elif tab_name == "calculateur":
            if not self._calc_loaded:
                self._build_calculator_tab()
                self._calc_loaded = True
            
            self.calculator_frame.pack(fill="both", expand=True)
            self.hero_kicker.configure(text="NOUVEAU PRODUIT")
            self.hero_title.configure(text="CALCULATEUR\nDE PRIX")
            self.hero_desc.configure(text="Créez et évaluez de nouveaux produits avec\nle calculateur de coûts de production.")
            self.step_indicator.configure(text="MODULE 2 / 3")
            
            self.btn_catalogue.configure(fg_color=COLORS["bg_card"], text_color=COLORS["text_secondary"], hover_color=COLORS["bg_card_hover"])
            self.btn_calculateur.configure(fg_color=COLORS["accent"], text_color=COLORS["bg_dark"], hover_color=COLORS["accent_hover"])
            self.btn_admin.configure(fg_color=COLORS["bg_card"], text_color=COLORS["text_secondary"], hover_color=COLORS["bg_card_hover"])
            
        elif tab_name == "administration":
            if not self._admin_loaded:
                self._build_admin_tab()
                self._admin_loaded = True
                
            self.admin_frame.pack(fill="both", expand=True)
            self.hero_kicker.configure(text="GESTION DES PRODUITS")
            self.hero_title.configure(text="PANNEAU\nD'ADMINISTRATION")
            self.hero_desc.configure(text="Modifiez, supprimez et gérez les points de\nsauvegarde du catalogue de prix.")
            self.step_indicator.configure(text="MODULE 3 / 3")
            
            self.btn_catalogue.configure(fg_color=COLORS["bg_card"], text_color=COLORS["text_secondary"], hover_color=COLORS["bg_card_hover"])
            self.btn_calculateur.configure(fg_color=COLORS["bg_card"], text_color=COLORS["text_secondary"], hover_color=COLORS["bg_card_hover"])
            self.btn_admin.configure(fg_color=COLORS["accent"], text_color=COLORS["bg_dark"], hover_color=COLORS["accent_hover"])

    # ─── CATALOGUE TAB ───────────────────────────────────────────────────────
    def _build_catalogue_tab(self):
        self.catalogue_frame.columnconfigure(0, weight=65, uniform="col")
        self.catalogue_frame.columnconfigure(1, weight=35, uniform="col")
        self.catalogue_frame.rowconfigure(0, weight=1)

        # Left Column (~65%)
        self.cat_left = ctk.CTkFrame(
            self.catalogue_frame, fg_color="transparent",
            border_width=1, border_color=COLORS["border"], corner_radius=10
        )
        self.cat_left.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        cat_left_content = ctk.CTkFrame(self.cat_left, fg_color="transparent")
        cat_left_content.pack(fill="both", expand=True, padx=30, pady=30)

        hdr_frame = ctk.CTkFrame(cat_left_content, fg_color="transparent")
        hdr_frame.pack(fill="x", pady=(0, 20))
        
        ctk.CTkLabel(
            hdr_frame, text="🔧", font=ctk.CTkFont(size=20), text_color=COLORS["accent"]
        ).pack(side="left", padx=(0, 10))
        
        ctk.CTkLabel(
            hdr_frame, text="SÉLECTION PRODUIT",
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
            text_color=COLORS["text_primary"]
        ).pack(side="left")

        ctk.CTkLabel(
            cat_left_content, text="Rechercher ou configurer via les listes déroulantes",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=COLORS["text_secondary"]
        ).pack(anchor="w", pady=(0, 20))

        # Search Bar
        self.search_frame = ctk.CTkFrame(cat_left_content, fg_color="transparent")
        self.search_frame.pack(fill="x", pady=(0, 8))

        self.search_entry = ctk.CTkEntry(
            self.search_frame,
            placeholder_text="🔍 Rechercher une dimension (ex: 600*60)...",
            height=44,
            font=ctk.CTkFont(family="Segoe UI", size=13),
            fg_color=COLORS["bg_input"],
            border_color=COLORS["border"],
            text_color=COLORS["text_primary"],
            placeholder_text_color=COLORS["text_muted"],
            corner_radius=6
        )
        self.search_entry.pack(fill="x")
        self.search_entry.bind("<KeyRelease>", self._on_search_change)

        self.search_results_frame = ctk.CTkScrollableFrame(
            cat_left_content, height=0, fg_color=COLORS["bg_card"], corner_radius=6
        )
        self._search_visible = False

        ctk.CTkFrame(cat_left_content, height=1, fg_color=COLORS["border"]).pack(fill="x", pady=(20, 20))

        # Cascading Dropdowns
        self._make_dropdown_label(cat_left_content, "CATÉGORIE")
        self.category_var = ctk.StringVar(value="Sélectionner une catégorie...")
        self.category_menu = ctk.CTkOptionMenu(
            cat_left_content, variable=self.category_var, values=["Chargement..."],
            command=self._on_category_change, height=44,
            font=ctk.CTkFont(family="Segoe UI", size=13),
            dropdown_font=ctk.CTkFont(family="Segoe UI", size=13),
            fg_color=COLORS["bg_input"], button_color=COLORS["bg_input"],
            button_hover_color=COLORS["bg_card_hover"],
            dropdown_fg_color=COLORS["bg_card"], dropdown_hover_color=COLORS["bg_card_hover"],
            corner_radius=6
        )
        self.category_menu.pack(fill="x", pady=(0, 16))

        self._make_dropdown_label(cat_left_content, "COULEUR")
        self.color_var = ctk.StringVar(value="Sélectionner une couleur...")
        self.color_menu = ctk.CTkOptionMenu(
            cat_left_content, variable=self.color_var, values=["—"],
            command=self._on_color_change, height=44,
            font=ctk.CTkFont(family="Segoe UI", size=13),
            dropdown_font=ctk.CTkFont(family="Segoe UI", size=13),
            fg_color=COLORS["bg_input"], button_color=COLORS["bg_input"],
            button_hover_color=COLORS["bg_card_hover"],
            dropdown_fg_color=COLORS["bg_card"], dropdown_hover_color=COLORS["bg_card_hover"],
            corner_radius=6, state="disabled"
        )
        self.color_menu.pack(fill="x", pady=(0, 16))

        self._make_dropdown_label(cat_left_content, "DIMENSION")
        self.dim_var = ctk.StringVar(value="Sélectionner une dimension...")
        self.dim_menu = ctk.CTkOptionMenu(
            cat_left_content, variable=self.dim_var, values=["—"],
            command=self._on_dimension_change, height=44,
            font=ctk.CTkFont(family="Segoe UI", size=13),
            dropdown_font=ctk.CTkFont(family="Segoe UI", size=13),
            fg_color=COLORS["bg_input"], button_color=COLORS["bg_input"],
            button_hover_color=COLORS["bg_card_hover"],
            dropdown_fg_color=COLORS["bg_card"], dropdown_hover_color=COLORS["bg_card_hover"],
            corner_radius=6, state="disabled"
        )
        self.dim_menu.pack(fill="x", pady=(0, 24))

        self.reset_btn = ctk.CTkButton(
            cat_left_content, text="RÉINITIALISER",
            command=self._reset_all, height=40,
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            fg_color="transparent", border_width=1, border_color=COLORS["border"],
            hover_color=COLORS["bg_card_hover"], text_color=COLORS["text_muted"],
            corner_radius=6
        )
        self.reset_btn.pack(fill="x", pady=(0, 10))

        self.selector_status = ctk.CTkLabel(
            cat_left_content, text="",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color=COLORS["text_muted"]
        )
        self.selector_status.pack(anchor="w")

        # Right Column (~35%)
        self.cat_right = ctk.CTkFrame(self.catalogue_frame, fg_color="transparent")
        self.cat_right.grid(row=0, column=1, sticky="nsew", padx=(10, 0))

        # Card 0: IMAGE
        self.card_img = ctk.CTkFrame(self.cat_right, fg_color=COLORS["bg_card"], corner_radius=10)
        self.card_img.pack(fill="x", pady=(0, 10))
        
        c0_content = ctk.CTkFrame(self.card_img, fg_color="transparent")
        c0_content.pack(fill="both", expand=True, padx=20, pady=20)
        
        ctk.CTkLabel(
            c0_content, text="APERÇU DU PRODUIT",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=COLORS["accent"]
        ).pack(anchor="w", pady=(0, 10))
        
        self.lbl_image = ctk.CTkLabel(
            c0_content, text="Aucune image",
            font=ctk.CTkFont(family="Segoe UI", size=12, slant="italic"),
            text_color=COLORS["text_muted"]
        )
        self.lbl_image.pack(anchor="center")

        # Card 1: PRIX DE REVIENT
        self.card_prix = ctk.CTkFrame(self.cat_right, fg_color=COLORS["bg_card"], corner_radius=10)
        self.card_prix.pack(fill="x", pady=(0, 10))
        
        c1_content = ctk.CTkFrame(self.card_prix, fg_color="transparent")
        c1_content.pack(fill="both", expand=True, padx=20, pady=20)
        
        ctk.CTkLabel(
            c1_content, text="PRIX DE REVIENT",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=COLORS["accent"]
        ).pack(anchor="w")
        
        self.lbl_product_sub = ctk.CTkLabel(
            c1_content, text="SÉLECTIONNER UN PRODUIT",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            text_color=COLORS["text_secondary"]
        )
        self.lbl_product_sub.pack(anchor="w", pady=(4, 15))
        
        self.lbl_prix = ctk.CTkLabel(
            c1_content, text="— DA",
            font=ctk.CTkFont(family="Consolas", size=32, weight="bold"),
            text_color=COLORS["text_primary"]
        )
        self.lbl_prix.pack(anchor="w")

        # Card 2: COMPOSANTS
        self.card_comp = ctk.CTkFrame(self.cat_right, fg_color=COLORS["bg_card"], corner_radius=10)
        self.card_comp.pack(fill="both", expand=True, pady=(0, 10))
        
        c2_content = ctk.CTkFrame(self.card_comp, fg_color="transparent")
        c2_content.pack(fill="both", expand=True, padx=20, pady=20)
        
        ctk.CTkLabel(
            c2_content, text="COMPOSANTS",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=COLORS["accent"]
        ).pack(anchor="w", pady=(0, 10))
        
        self.bom_list = ctk.CTkScrollableFrame(c2_content, fg_color="transparent")
        self.bom_list.pack(fill="both", expand=True)

        # Card 3: DIMENSIONS
        self.card_dim = ctk.CTkFrame(self.cat_right, fg_color=COLORS["bg_card"], corner_radius=10)
        self.card_dim.pack(fill="x")
        
        c3_content = ctk.CTkFrame(self.card_dim, fg_color="transparent")
        c3_content.pack(fill="both", expand=True, padx=20, pady=20)
        
        ctk.CTkLabel(
            c3_content, text="DIMENSIONS",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=COLORS["accent"]
        ).pack(anchor="w", pady=(0, 5))
        
        self.lbl_dims = ctk.CTkLabel(
            c3_content, text="—",
            font=ctk.CTkFont(family="Consolas", size=14),
            text_color=COLORS["text_primary"]
        )
        self.lbl_dims.pack(anchor="w")

    def _make_dropdown_label(self, parent, text):
        f = ctk.CTkFrame(parent, fg_color="transparent")
        f.pack(fill="x")
        ctk.CTkLabel(
            f, text=text,
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=COLORS["text_primary"]
        ).pack(side="left")
        ctk.CTkLabel(
            f, text=" *",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=COLORS["accent"]
        ).pack(side="left")

    # ─── CALCULATEUR TAB ─────────────────────────────────────────────────────
    def _build_calculator_tab(self):
        try:
            from calculator_gui import CalculatorFrame
            self.calc_instance = CalculatorFrame(self.calculator_frame, self.db_mgr, refresh_callback=self.refresh_view)
            self.calc_instance.pack(fill="both", expand=True)
        except Exception as e:
            err_msg = traceback.format_exc()
            messagebox.showerror("Erreur — Nouveau Produit", f"Impossible de charger le calculateur :\n\n{err_msg}", parent=self)

    # ─── ADMINISTRATION TAB ──────────────────────────────────────────────────
    def _build_admin_tab(self):
        self._pd_product_id = None
        self._pd_dim_map = {}
        self._pd_comp_vars = []
        
        # Container
        admin_content = ctk.CTkFrame(self.admin_frame, fg_color=COLORS["bg_card"], corner_radius=10)
        admin_content.pack(fill="both", expand=True)
        
        # Mode Buttons
        mode_frame = ctk.CTkFrame(admin_content, fg_color="transparent")
        mode_frame.pack(fill="x", padx=20, pady=20)
        
        self.pd_edit_btn = ctk.CTkButton(
            mode_frame, text="✏ MODIFIER PRODUIT", height=40,
            fg_color=COLORS["accent"], text_color=COLORS["bg_dark"], hover_color=COLORS["accent_hover"],
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            corner_radius=6, command=self._pd_show_edit_form
        )
        self.pd_edit_btn.pack(side="left", padx=(0, 10))
        
        self.pd_delete_btn = ctk.CTkButton(
            mode_frame, text="🗑 SUPPRIMER", height=40,
            fg_color="transparent", hover_color=COLORS["error"],
            border_width=1, border_color=COLORS["error"], text_color=COLORS["error"],
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            corner_radius=6, command=self._pd_delete_product, state="disabled"
        )
        self.pd_delete_btn.pack(side="right")
        
        # Edit Area
        self.pd_content_frame = ctk.CTkFrame(admin_content, fg_color="transparent")
        self.pd_content_frame.pack(fill="both", expand=True, padx=20, pady=(0, 10))
        
        # Checkpoints Area
        cp_frame = ctk.CTkFrame(admin_content, fg_color="transparent")
        cp_frame.pack(fill="x", padx=20, pady=20)
        
        ctk.CTkFrame(cp_frame, height=1, fg_color=COLORS["border"]).pack(fill="x", pady=(0, 15))
        
        self.cp_status = ctk.CTkLabel(
            cp_frame, text="", font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=COLORS["text_secondary"]
        )
        self.cp_status.pack(side="top", pady=(0, 10))
        
        btn_frame = ctk.CTkFrame(cp_frame, fg_color="transparent")
        btn_frame.pack(side="top")
        
        ctk.CTkButton(
            btn_frame, text="📌 CRÉER POINT SAUVEGARDE", height=36,
            fg_color=COLORS["accent_dim"], text_color=COLORS["text_primary"], hover_color=COLORS["accent"],
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            corner_radius=6, command=self._create_manual_checkpoint
        ).pack(side="left", padx=(0, 10))
        
        ctk.CTkButton(
            btn_frame, text="🕒 RESTAURER DONNÉES", height=36,
            fg_color="transparent", text_color=COLORS["warning"], hover_color=COLORS["bg_card_hover"],
            border_width=1, border_color=COLORS["warning"],
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            corner_radius=6, command=self._open_restore_dialog
        ).pack(side="left")
        
        self.pd_status = ctk.CTkLabel(
            admin_content, text="", font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=COLORS["text_muted"]
        )
        self.pd_status.pack(pady=(0, 10))

        self._update_cp_status()
        self._pd_show_edit_form()

    # ─── ADMIN: EDIT FORM ────────────────────────────────────────────────────
    def _pd_clear_content(self):
        for w in self.pd_content_frame.winfo_children():
            w.destroy()

    def _pd_show_edit_form(self):
        self._pd_clear_content()
        self._pd_product_id = None
        self._pd_comp_vars = []
        self.pd_delete_btn.configure(state="disabled")

        container = self.pd_content_frame

        sel = ctk.CTkFrame(container, fg_color="transparent")
        sel.pack(fill="x", pady=(0, 10))
        
        ctk.CTkLabel(
            sel, text="SÉLECTIONNER LE PRODUIT À MODIFIER",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=COLORS["accent"]
        ).pack(anchor="w", pady=(0, 10))

        row_sel = ctk.CTkFrame(sel, fg_color="transparent")
        row_sel.pack(fill="x")
        row_sel.columnconfigure((0, 1, 2), weight=1, uniform="sel")

        # Category
        f_cat = ctk.CTkFrame(row_sel, fg_color="transparent")
        f_cat.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        ctk.CTkLabel(f_cat, text="CATÉGORIE", font=ctk.CTkFont(size=10, weight="bold"), text_color=COLORS["text_muted"]).pack(anchor="w", pady=(0, 2))
        categories = self.db_mgr.get_categories()
        self._pd_edit_cat_map = {f"{c} — {n}": c for c, n in categories}
        self.pd_edit_cat_var = ctk.StringVar(value="Catégorie...")
        ctk.CTkOptionMenu(
            f_cat, variable=self.pd_edit_cat_var, values=list(self._pd_edit_cat_map.keys()),
            command=self._pd_edit_on_cat, height=36,
            fg_color=COLORS["bg_input"], button_color=COLORS["bg_input"],
            button_hover_color=COLORS["bg_card_hover"], corner_radius=6
        ).pack(fill="x")

        # Color
        f_col = ctk.CTkFrame(row_sel, fg_color="transparent")
        f_col.grid(row=0, column=1, sticky="nsew", padx=5)
        ctk.CTkLabel(f_col, text="COULEUR", font=ctk.CTkFont(size=10, weight="bold"), text_color=COLORS["text_muted"]).pack(anchor="w", pady=(0, 2))
        self.pd_edit_color_var = ctk.StringVar(value="Couleur...")
        self.pd_edit_color_menu = ctk.CTkOptionMenu(
            f_col, variable=self.pd_edit_color_var, values=["—"],
            command=self._pd_edit_on_color, height=36, state="disabled",
            fg_color=COLORS["bg_input"], button_color=COLORS["bg_input"],
            button_hover_color=COLORS["bg_card_hover"], corner_radius=6
        )
        self.pd_edit_color_menu.pack(fill="x")

        # Dimension
        f_dim = ctk.CTkFrame(row_sel, fg_color="transparent")
        f_dim.grid(row=0, column=2, sticky="nsew", padx=(5, 0))
        ctk.CTkLabel(f_dim, text="DIMENSION", font=ctk.CTkFont(size=10, weight="bold"), text_color=COLORS["text_muted"]).pack(anchor="w", pady=(0, 2))
        self.pd_edit_dim_var = ctk.StringVar(value="Dimension...")
        self.pd_edit_dim_menu = ctk.CTkOptionMenu(
            f_dim, variable=self.pd_edit_dim_var, values=["—"],
            command=self._pd_edit_on_dim, height=36, state="disabled",
            fg_color=COLORS["bg_input"], button_color=COLORS["bg_input"],
            button_hover_color=COLORS["bg_card_hover"], corner_radius=6
        )
        self.pd_edit_dim_menu.pack(fill="x")

        self.pd_edit_area = ctk.CTkFrame(container, fg_color="transparent")
        self.pd_edit_area.pack(fill="both", expand=True)

        ctk.CTkLabel(
            self.pd_edit_area, text="Sélectionnez un produit ci-dessus pour le modifier",
            font=ctk.CTkFont(family="Segoe UI", size=13), text_color=COLORS["text_muted"]
        ).pack(pady=40)

    def _pd_edit_on_cat(self, selection):
        code = self._pd_edit_cat_map.get(selection)
        if not code:
            return
        self._pd_edit_sel_cat = code
        self.pd_edit_color_var.set("Couleur...")
        self.pd_edit_dim_var.set("Dimension...")
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
        self.pd_edit_dim_var.set("Dimension...")
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

        _, cat, dim, width, height, color, image_path, cost, tariff = product
        self._pd_current_image_path = image_path

        meta = ctk.CTkFrame(self.pd_edit_area, fg_color="transparent")
        meta.pack(fill="x", pady=(10, 10))

        # Edit Image button
        img_frame = ctk.CTkFrame(meta, fg_color="transparent")
        img_frame.pack(side="right", padx=(10, 0))
        
        self.pd_img_label = ctk.CTkLabel(img_frame, text=os.path.basename(image_path) if image_path else "Aucune image", font=ctk.CTkFont(size=10), text_color=COLORS["text_muted"])
        self.pd_img_label.pack(side="top")
        
        ctk.CTkButton(img_frame, text="🖼 Modifier Image", height=28, width=120, fg_color=COLORS["bg_card_hover"], hover_color=COLORS["border"], text_color=COLORS["text_primary"], command=self._pd_choose_image).pack(side="top", pady=(2, 0))

        ctk.CTkLabel(
            meta, text=f"MODIFICATION : {cat} / {color} / {dim}",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=COLORS["warning"]
        ).pack(pady=(0, 5), anchor="w")

        dim_str = str(dim) if dim else ""
        dim_edit_row = ctk.CTkFrame(meta, fg_color="transparent")
        dim_edit_row.pack(fill="x")

        if dim_str.startswith("Ø"):
            parts = dim_str[1:].split("*")
            diam_val = parts[0] if len(parts) >= 1 else str(width or "")
            h_val = parts[1] if len(parts) >= 2 else str(height or "")

            ctk.CTkLabel(dim_edit_row, text="DIAMÈTRE", width=70, anchor="w", font=ctk.CTkFont(size=11, weight="bold"), text_color=COLORS["text_secondary"]).pack(side="left")
            self.pd_edit_diameter = ctk.CTkEntry(dim_edit_row, width=80, height=30, fg_color=COLORS["bg_input"], border_color=COLORS["border"], corner_radius=6)
            self.pd_edit_diameter.insert(0, diam_val)
            self.pd_edit_diameter.pack(side="left", padx=(0, 15))

            ctk.CTkLabel(dim_edit_row, text="HAUTEUR", width=70, anchor="w", font=ctk.CTkFont(size=11, weight="bold"), text_color=COLORS["text_secondary"]).pack(side="left")
            self.pd_edit_height = ctk.CTkEntry(dim_edit_row, width=80, height=30, fg_color=COLORS["bg_input"], border_color=COLORS["border"], corner_radius=6)
            self.pd_edit_height.insert(0, h_val)
            self.pd_edit_height.pack(side="left")
            self._pd_edit_geom = "rmb"
        elif dim_str.count("*") == 2:
            parts = dim_str.split("*")
            ctk.CTkLabel(dim_edit_row, text="LARGEUR", width=70, anchor="w", font=ctk.CTkFont(size=11, weight="bold"), text_color=COLORS["text_secondary"]).pack(side="left")
            self.pd_edit_width = ctk.CTkEntry(dim_edit_row, width=80, height=30, fg_color=COLORS["bg_input"], border_color=COLORS["border"], corner_radius=6)
            self.pd_edit_width.insert(0, parts[0])
            self.pd_edit_width.pack(side="left", padx=(0, 15))

            ctk.CTkLabel(dim_edit_row, text="PROFONDEUR", width=80, anchor="w", font=ctk.CTkFont(size=11, weight="bold"), text_color=COLORS["text_secondary"]).pack(side="left")
            self.pd_edit_depth = ctk.CTkEntry(dim_edit_row, width=80, height=30, fg_color=COLORS["bg_input"], border_color=COLORS["border"], corner_radius=6)
            self.pd_edit_depth.insert(0, parts[1])
            self.pd_edit_depth.pack(side="left", padx=(0, 15))

            ctk.CTkLabel(dim_edit_row, text="HAUTEUR", width=70, anchor="w", font=ctk.CTkFont(size=11, weight="bold"), text_color=COLORS["text_secondary"]).pack(side="left")
            self.pd_edit_height = ctk.CTkEntry(dim_edit_row, width=80, height=30, fg_color=COLORS["bg_input"], border_color=COLORS["border"], corner_radius=6)
            self.pd_edit_height.insert(0, parts[2])
            self.pd_edit_height.pack(side="left")
            self._pd_edit_geom = "tole"
        else:
            ctk.CTkLabel(dim_edit_row, text="LARGEUR", width=70, anchor="w", font=ctk.CTkFont(size=11, weight="bold"), text_color=COLORS["text_secondary"]).pack(side="left")
            self.pd_edit_width = ctk.CTkEntry(dim_edit_row, width=80, height=30, fg_color=COLORS["bg_input"], border_color=COLORS["border"], corner_radius=6)
            self.pd_edit_width.insert(0, str(width or ""))
            self.pd_edit_width.pack(side="left", padx=(0, 15))

            ctk.CTkLabel(dim_edit_row, text="HAUTEUR", width=70, anchor="w", font=ctk.CTkFont(size=11, weight="bold"), text_color=COLORS["text_secondary"]).pack(side="left")
            self.pd_edit_height = ctk.CTkEntry(dim_edit_row, width=80, height=30, fg_color=COLORS["bg_input"], border_color=COLORS["border"], corner_radius=6)
            self.pd_edit_height.insert(0, str(height or ""))
            self.pd_edit_height.pack(side="left")
            self._pd_edit_geom = "legacy"

        ctk.CTkLabel(
            dim_edit_row,
            text=f"TOTAL : {float(cost):.2f} DA" if cost else "TOTAL : 0.00 DA",
            font=ctk.CTkFont(family="Consolas", size=14, weight="bold"),
            text_color=COLORS["accent"]
        ).pack(side="right", padx=(0, 4))

        # BOM Components
        ctk.CTkLabel(
            self.pd_edit_area, text="COMPOSANTS",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=COLORS["text_muted"]
        ).pack(pady=(10, 5), anchor="w")

        self.pd_edit_bom_frame = ctk.CTkScrollableFrame(
            self.pd_edit_area, fg_color=COLORS["bg_dark"], corner_radius=6, height=180
        )
        self.pd_edit_bom_frame.pack(fill="both", expand=True, pady=(0, 10))

        # Header
        hdr = ctk.CTkFrame(self.pd_edit_bom_frame, fg_color="transparent")
        hdr.pack(fill="x", pady=(4, 2))
        ctk.CTkLabel(hdr, text="NOM", width=180, anchor="w", font=ctk.CTkFont(size=10, weight="bold"), text_color=COLORS["text_muted"]).pack(side="left", padx=(4, 0))
        ctk.CTkLabel(hdr, text="QTÉ", width=70, anchor="center", font=ctk.CTkFont(size=10, weight="bold"), text_color=COLORS["text_muted"]).pack(side="left", padx=2)
        ctk.CTkLabel(hdr, text="P.U.", width=90, anchor="center", font=ctk.CTkFont(size=10, weight="bold"), text_color=COLORS["text_muted"]).pack(side="left", padx=2)
        ctk.CTkLabel(hdr, text="S-TOTAL", width=90, anchor="e", font=ctk.CTkFont(size=10, weight="bold"), text_color=COLORS["text_muted"]).pack(side="right", padx=(0, 40))

        ctk.CTkFrame(self.pd_edit_bom_frame, height=1, fg_color=COLORS["border"]).pack(fill="x", padx=4, pady=4)

        components = self.db_mgr.get_components_for_product(self._pd_product_id)
        for comp_id, name, qty, unit_price, subtotal in components:
            self._pd_add_edit_comp_row(
                comp_id, name,
                f"{float(qty):.2f}" if qty else "0.00",
                f"{float(unit_price):.2f}" if unit_price else "0.00",
                f"{float(subtotal):.2f}" if subtotal else "0.00"
            )

        # Buttons
        btn_row = ctk.CTkFrame(self.pd_edit_area, fg_color="transparent")
        btn_row.pack(fill="x")

        ctk.CTkButton(
            btn_row, text="➕ AJOUTER COMPOSANT", height=32,
            fg_color="transparent", hover_color=COLORS["bg_card_hover"],
            border_width=1, border_color=COLORS["border"],
            text_color=COLORS["text_primary"], font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            command=lambda: self._pd_add_edit_comp_row(None), corner_radius=6
        ).pack(side="left")

        ctk.CTkButton(
            btn_row, text="💾 ENREGISTRER MODIFICATIONS", height=36,
            fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"], text_color=COLORS["bg_dark"],
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            command=self._pd_save_edit, corner_radius=6
        ).pack(side="right")

    def _pd_add_edit_comp_row(self, comp_id, name="", qty="1.00", price="0.00", subtotal="0.00"):
        row = ctk.CTkFrame(self.pd_edit_bom_frame, fg_color="transparent")
        row.pack(fill="x", pady=2)

        name_var = ctk.StringVar(value=name)
        ctk.CTkEntry(
            row, textvariable=name_var, width=180, height=30,
            font=ctk.CTkFont(family="Segoe UI", size=11), placeholder_text="Nom",
            fg_color=COLORS["bg_input"], border_color=COLORS["border"], corner_radius=6
        ).pack(side="left", padx=(4, 2))

        qty_var = ctk.StringVar(value=qty)
        ctk.CTkEntry(
            row, textvariable=qty_var, width=70, height=30,
            font=ctk.CTkFont(family="Consolas", size=11),
            fg_color=COLORS["bg_input"], border_color=COLORS["border"], corner_radius=6
        ).pack(side="left", padx=2)

        price_var = ctk.StringVar(value=price)
        ctk.CTkEntry(
            row, textvariable=price_var, width=90, height=30,
            font=ctk.CTkFont(family="Consolas", size=11),
            fg_color=COLORS["bg_input"], border_color=COLORS["border"], corner_radius=6
        ).pack(side="left", padx=2)

        ctk.CTkLabel(
            row, text=f"{subtotal} DA", width=90, anchor="e",
            font=ctk.CTkFont(family="Consolas", size=11, weight="bold"),
            text_color=COLORS["text_secondary"]
        ).pack(side="left", padx=2)

        ctk.CTkButton(
            row, text="✕", width=30, height=30,
            fg_color="transparent", hover_color=COLORS["error"],
            text_color=COLORS["error"], font=ctk.CTkFont(size=12, weight="bold"),
            command=lambda r=row, cid=comp_id: self._pd_remove_edit_comp(r, cid)
        ).pack(side="right", padx=(2, 4))

        self._pd_comp_vars.append((comp_id, name_var, qty_var, price_var, row))

    def _pd_remove_edit_comp(self, row, comp_id):
        if comp_id is not None:
            confirm = messagebox.askyesno("Supprimer le composant", "Supprimer ce composant définitivement ?", parent=self)
            if not confirm:
                return
            self.db_mgr.delete_component(comp_id)
        self._pd_comp_vars = [(c, n, q, p, r) for c, n, q, p, r in self._pd_comp_vars if r != row]
        row.destroy()

    def _pd_choose_image(self):
        path = filedialog.askopenfilename(filetypes=[("Images", "*.png *.jpg *.jpeg")])
        if path:
            import shutil
            dest_dir = os.path.join(self.db_mgr.app_data_dir, "images")
            os.makedirs(dest_dir, exist_ok=True)
            import uuid
            ext = os.path.splitext(path)[1]
            new_name = f"img_{uuid.uuid4().hex[:8]}{ext}"
            dest_path = os.path.join(dest_dir, new_name)
            shutil.copy2(path, dest_path)
            self._pd_current_image_path = dest_path
            self.pd_img_label.configure(text=new_name)

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

        product = self.db_mgr.get_product_by_id(self._pd_product_id)
        if product:
            _, cat, dim, _, _, color, _, _, _ = product
            self.db_mgr.create_checkpoint(f"Auto — avant modification {cat}/{color}/{dim}")
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
            self.db_mgr.update_product(self._pd_product_id, cat, color, new_dim, new_w, new_h, image_path=self._pd_current_image_path)

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
        total = float(prod[7]) if prod and prod[7] else 0
        self.pd_status.configure(text=f"✅ ENREGISTRÉ — TOTAL : {total:.2f} DA", text_color=COLORS["success"])
        self.refresh_view()
        messagebox.showinfo("Succès", f"Produit mis à jour. Nouveau total : {total:.2f} DA", parent=self)
        self._pd_load_edit_form()

    def _pd_delete_product(self):
        if not self._pd_product_id:
            return
        product = self.db_mgr.get_product_by_id(self._pd_product_id)
        if not product:
            return
        _, cat, dim, _, _, color, _, cost, _ = product

        confirm = messagebox.askyesno(
            "Confirmer la suppression",
            f"Supprimer définitivement :\n\n{cat} / {color} / {dim}\nCoût : {float(cost):.2f} DA\n\nCela supprimera le produit et TOUS ses composants.\nÊtes-vous sûr ?",
            parent=self, icon="warning"
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
        self.pd_status.configure(text=f"🗑 SUPPRIMÉ : {cat} / {color} / {dim}", text_color=COLORS["error"])
        self.refresh_view()
        messagebox.showinfo("Supprimé", f"Produit retiré : {cat} / {color} / {dim}", parent=self)
        self._pd_show_edit_form()

    def _update_cp_status(self):
        cps = self.db_mgr.list_checkpoints()
        self.cp_status.configure(text=f"📌 {len(cps)} POINT(S) DE SAUVEGARDE DISPONIBLE(S)")

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
            restore_win, text="⏪ SÉLECTIONNER LE POINT DE SAUVEGARDE À RESTAURER",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            text_color=COLORS["accent"]
        ).pack(pady=(20, 4), padx=20, anchor="w")

        ctk.CTkLabel(
            restore_win, text="Cela rétablira TOUS les produits et la tarification à l'état sélectionné.",
            font=ctk.CTkFont(size=12), text_color=COLORS["warning"]
        ).pack(pady=(0, 12), padx=20, anchor="w")

        scroll = ctk.CTkScrollableFrame(restore_win, fg_color=COLORS["bg_card"], corner_radius=10)
        scroll.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        for cp_id, cp_name, cp_time in checkpoints:
            row = ctk.CTkFrame(scroll, fg_color="transparent")
            row.pack(fill="x", pady=4)

            ctk.CTkLabel(
                row, text=f"📌 {cp_name}", font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
                text_color=COLORS["text_primary"]
            ).pack(side="left", padx=(8, 0))

            ctk.CTkLabel(
                row, text=cp_time, font=ctk.CTkFont(family="Consolas", size=11), text_color=COLORS["text_muted"]
            ).pack(side="left", padx=(12, 0))

            ctk.CTkButton(
                row, text="🗑", width=32, height=32,
                fg_color="transparent", hover_color=COLORS["error"], text_color=COLORS["error"],
                command=lambda cid=cp_id, win=restore_win: self._delete_checkpoint(cid, win)
            ).pack(side="right", padx=(4, 8))

            ctk.CTkButton(
                row, text="RESTAURER", width=80, height=32,
                fg_color=COLORS["warning"], hover_color="#e5a800", text_color=COLORS["bg_dark"],
                font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
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
        self.refresh_view()

    def _delete_checkpoint(self, checkpoint_id, dialog):
        confirm = messagebox.askyesno("Supprimer le point de sauvegarde", "Supprimer ce point de sauvegarde définitivement ?", parent=dialog)
        if not confirm:
            return
        self.db_mgr.delete_checkpoint(checkpoint_id)
        dialog.destroy()
        self._update_cp_status()
        self._open_restore_dialog()

    # ─── SEARCH / CASCADE / REFRESH ──────────────────────────────────────────
    def _format_dim_display(self, dim_str, w=None, h=None):
        return format_dim_display(dim_str, w, h)

    def _on_search_change(self, event=None):
        query = self.search_entry.get().strip()
        if len(query) < 2:
            self._hide_search_results()
            return
        results = self.db.search_products(query)
        self._show_search_results(results)

    def _show_search_results(self, results):
        for w in self.search_results_frame.winfo_children():
            w.destroy()
        if not results:
            self.search_results_frame.configure(height=40)
            if not self._search_visible:
                self.search_results_frame.pack(after=self.search_frame, fill="x", pady=(0, 10))
                self._search_visible = True
            ctk.CTkLabel(
                self.search_results_frame, text="AUCUN RÉSULTAT",
                font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
                text_color=COLORS["text_muted"]
            ).pack(pady=8)
            return

        display_height = min(len(results) * 36, 180)
        self.search_results_frame.configure(height=display_height)
        if not self._search_visible:
            self.search_results_frame.pack(after=self.search_frame, fill="x", pady=(0, 10))
            self._search_visible = True

        for cat, color, dim, w, h, cost in results:
            text_disp = f"{cat} · {color} · {dim} ({self._format_dim_display(dim, w, h)})"
            if cost: text_disp += f" — {cost:,.2f} DA"
            ctk.CTkButton(
                self.search_results_frame, text=text_disp,
                font=ctk.CTkFont(family="Segoe UI", size=12), fg_color="transparent",
                hover_color=COLORS["bg_card_hover"], text_color=COLORS["text_secondary"],
                anchor="w", height=32, corner_radius=6,
                command=lambda c=cat, co=color, d=dim: self._on_search_select(c, co, d)
            ).pack(fill="x", padx=2, pady=1)

    def _hide_search_results(self):
        if self._search_visible:
            self.search_results_frame.pack_forget()
            self._search_visible = False
            for w in self.search_results_frame.winfo_children():
                w.destroy()

    def _on_search_select(self, category_code, color, dimension):
        self._hide_search_results()
        self.search_entry.delete(0, "end")
        self._selected_category = category_code
        self._selected_color = color

        for display, code in self._category_map.items():
            if code == category_code:
                self.category_var.set(display)
                break

        colors = self.db.get_colors_for_category(category_code)
        self.color_menu.configure(state="normal", values=colors)
        self.color_var.set(color)

        dims = self.db.get_dimensions_for(category_code, color)
        self._dimensions_cache = dims
        display_dims = [f"{d[0]}  ({self._format_dim_display(d[0], d[1], d[2])})" for d in dims]
        self._dim_map = {f"{d[0]}  ({self._format_dim_display(d[0], d[1], d[2])})": d[0] for d in dims}
        self.dim_menu.configure(state="normal", values=display_dims)
        for disp, dim_key in self._dim_map.items():
            if dim_key == dimension:
                self.dim_var.set(disp)
                break

        self._update_cards(category_code, color, dimension)

    def _populate_categories(self):
        categories = self.db.get_categories()
        display_values = [f"{code} — {name}" for code, name in categories]
        self._category_map = {f"{code} — {name}": code for code, name in categories}
        self.category_menu.configure(values=display_values)

    def _on_category_change(self, selection):
        code = self._category_map.get(selection)
        if not code: return
        self._selected_category = code
        self.color_var.set("Sélectionner une couleur...")
        self.dim_var.set("Sélectionner une dimension...")
        self.dim_menu.configure(state="disabled", values=["—"])
        self._clear_cards()
        colors = self.db.get_colors_for_category(code)
        if colors:
            self.color_menu.configure(state="normal", values=colors)
            self.selector_status.configure(text=f"✓ {len(colors)} COULEUR(S)")
        else:
            self.color_menu.configure(state="disabled", values=["Aucune couleur"])
            self.selector_status.configure(text="⚠ AUCUNE COULEUR")

    def _on_color_change(self, selection):
        self._selected_color = selection
        self.dim_var.set("Sélectionner une dimension...")
        self._clear_cards()
        dims = self.db.get_dimensions_for(self._selected_category, selection)
        self._dimensions_cache = dims
        if dims:
            display = [f"{d[0]}  ({self._format_dim_display(d[0], d[1], d[2])})" for d in dims]
            self._dim_map = {f"{d[0]}  ({self._format_dim_display(d[0], d[1], d[2])})": d[0] for d in dims}
            self.dim_menu.configure(state="normal", values=display)
            self.selector_status.configure(text=f"✓ {len(dims)} DIMENSION(S)")
        else:
            self.dim_menu.configure(state="disabled", values=["Aucune dimension"])
            self.selector_status.configure(text="⚠ AUCUNE DIMENSION")

    def _on_dimension_change(self, selection):
        dim_key = self._dim_map.get(selection)
        if not dim_key: return
        self._update_cards(self._selected_category, self._selected_color, dim_key)

    def _update_cards(self, cat, color, dim):
        product = self.db.get_product(cat, color, dim)
        components = self.db.get_product_components(cat, color, dim)
        
        if product:
            p_cat, p_dim, p_w, p_h, p_col, p_cost, p_tariff, p_img = product
            
            cat_names = {"GSD": "Grille Simple Déflexion", "GDD": "Grille Double Déflexion", "GBF": "Grille à Barre Fixe"}
            title = f"{cat_names.get(p_cat, p_cat)} — {p_col}".upper()
            self.lbl_product_sub.configure(text=title)
            
            # Update Image
            if p_img and os.path.exists(p_img):
                try:
                    pil_img = Image.open(p_img)
                    # Resize proportionally to fit in max 250x250 for display
                    pil_img.thumbnail((250, 250))
                    ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=pil_img.size)
                    self.lbl_image.configure(image=ctk_img, text="")
                except Exception:
                    self.lbl_image.configure(image=None, text="Image introuvable ou invalide")
            else:
                self.lbl_image.configure(image=None, text="Aucune image")
            
            if p_cost is not None:
                self.lbl_prix.configure(text=f"{p_cost:,.2f} DA")
            else:
                self.lbl_prix.configure(text="N/A")
                
            dim_str = str(p_dim) if p_dim else ""
            if dim_str.startswith("Ø"):
                parts = dim_str[1:].split("*")
                if len(parts) == 2:
                    self.lbl_dims.configure(text=f"DIAMÈTRE: {parts[0]} mm × HAUTEUR: {parts[1]} mm")
                else:
                    self.lbl_dims.configure(text=f"DIAMÈTRE: {dim_str[1:]} mm")
            elif dim_str.count("*") == 2:
                parts = dim_str.split("*")
                self.lbl_dims.configure(text=f"L: {parts[0]} mm × P: {parts[1]} mm × H: {parts[2]} mm")
            else:
                self.lbl_dims.configure(text=f"L: {p_w} mm × H: {p_h} mm")
                
            for w in self.bom_list.winfo_children():
                w.destroy()
                
            if components:
                for name, qty, unit_price, subtotal in components:
                    row = ctk.CTkFrame(self.bom_list, fg_color="transparent")
                    row.pack(fill="x", pady=2)
                    ctk.CTkLabel(row, text="■", font=ctk.CTkFont(size=10), text_color=COLORS["accent"]).pack(side="left", padx=(0, 8))
                    ctk.CTkLabel(row, text=str(name).upper(), font=ctk.CTkFont(family="Segoe UI", size=12), text_color=COLORS["text_secondary"]).pack(side="left")
                    price_text = f"{subtotal:,.2f} DA" if subtotal is not None else "—"
                    ctk.CTkLabel(row, text=price_text, font=ctk.CTkFont(family="Consolas", size=12), text_color=COLORS["text_primary"]).pack(side="right")

                ctk.CTkFrame(self.bom_list, height=1, fg_color=COLORS["border"]).pack(fill="x", pady=(10, 5))
                total = sum(s for _, _, _, s in components if s is not None)
                total_row = ctk.CTkFrame(self.bom_list, fg_color="transparent")
                total_row.pack(fill="x")
                ctk.CTkLabel(total_row, text="TOTAL", font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"), text_color=COLORS["accent"]).pack(side="left")
                ctk.CTkLabel(total_row, text=f"{total:,.2f} DA", font=ctk.CTkFont(family="Consolas", size=14, weight="bold"), text_color=COLORS["accent"]).pack(side="right")
                
            self.selector_status.configure(text="✓ PRODUIT TROUVÉ", text_color=COLORS["success"])
        else:
            self._clear_cards()
            self.selector_status.configure(text="⚠ NON STANDARD", text_color=COLORS["warning"])

    def _clear_cards(self):
        self.lbl_product_sub.configure(text="SÉLECTIONNER UN PRODUIT")
        self.lbl_prix.configure(text="— DA")
        self.lbl_dims.configure(text="—")
        for w in self.bom_list.winfo_children():
            w.destroy()

    def refresh_view(self):
        self._update_status_count()
        current_cat = self.category_var.get()
        current_color = self.color_var.get()
        current_dim = self.dim_var.get()
        self._populate_categories()

        if current_cat in self._category_map:
            self.category_var.set(current_cat)
            self._on_category_change(current_cat)
            if current_color != "Sélectionner une couleur..." and current_color in self.color_menu.cget("values"):
                self.color_var.set(current_color)
                self._on_color_change(current_color)
                if current_dim != "Sélectionner une dimension..." and current_dim in [val.split(" ")[0] for val in self.dim_menu.cget("values")]:
                    self.dim_var.set(current_dim)
                    self._on_dimension_change(current_dim)
        else:
            self._reset_all()

    def _reset_all(self):
        self._selected_category = None
        self._selected_color = None
        self._dimensions_cache = []
        self.category_var.set("Sélectionner une catégorie...")
        self.color_var.set("Sélectionner une couleur...")
        self.dim_var.set("Sélectionner une dimension...")
        self.color_menu.configure(state="disabled", values=["—"])
        self.dim_menu.configure(state="disabled", values=["—"])
        self._clear_cards()
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
    app.report_callback_exception = _global_exception_handler
    app.mainloop()
