import customtkinter as ctk
from tkinter import messagebox, filedialog
from database_manager import DatabaseManager
import math
import os
import shutil
import uuid

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

class CalculatorFrame(ctk.CTkFrame):
    def __init__(self, master, db_mgr, refresh_callback=None, **kwargs):
        super().__init__(master, fg_color=COLORS["bg_dark"], **kwargs)
        
        self.refresh_callback = refresh_callback
        self.db_mgr = db_mgr
        self.thicknesses = self.db_mgr.get_thicknesses()
        self.density_mult = self.db_mgr.get_density_multiplier()
        
        self.comp_rows = []
        self.current_totals = (0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        
        self.exec_time_var = ctk.StringVar(value="0.5")
        self.exec_rate_var = ctk.StringVar(value="200")
        self.exec_time_unit_var = ctk.StringVar(value="Heures")
        self.margin_var = ctk.StringVar(value="40")
        self.remise_var = ctk.StringVar(value="0")
        self.pt_mult_var = ctk.StringVar(value="1.40")
        self.w_var = ctk.StringVar(value="600")
        self.h_var = ctk.StringVar(value="400")
        self.depth_var = ctk.StringVar(value="300")
        self.diameter_var = ctk.StringVar(value="300")
        self.image_path_var = ctk.StringVar(value="")

        # Base Material variables
        self.tole_check_var = ctk.BooleanVar(value=True)
        self.tole_th_var = ctk.StringVar(value="EP 8/10")
        self.tole_price_var = ctk.StringVar(value="15")
        self.tole_weight_var = ctk.StringVar(value="0.000 kg")
        self.tole_subtotal_var = ctk.StringVar(value="0.00")
        
        self.rmb_check_var = ctk.BooleanVar(value=False)
        self.rmb_th_var = ctk.StringVar(value="EP 8/10")
        self.rmb_price_var = ctk.StringVar(value="15")
        self.rmb_weight_var = ctk.StringVar(value="0.000 kg")
        self.rmb_subtotal_var = ctk.StringVar(value="0.00")
        
        self._build_ui()

    def _build_ui(self):
        # Header
        ctk.CTkLabel(self, text="🖩  CALCULATEUR & NOMENCLATURE", font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"), text_color=COLORS["accent"]).pack(pady=(16, 4), padx=24, anchor="w")
        
        main_scroll = ctk.CTkScrollableFrame(self, fg_color=COLORS["bg_dark"])
        main_scroll.pack(fill="both", expand=True, padx=12, pady=12)
        
        # ── 1. IDENTITÉ PRODUIT ──
        meta_frame = ctk.CTkFrame(main_scroll, fg_color=COLORS["bg_card"], corner_radius=8)
        meta_frame.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(meta_frame, text="1. IDENTITÉ PRODUIT", font=ctk.CTkFont(size=12, weight="bold"), text_color=COLORS["accent"]).pack(anchor="w", padx=14, pady=(10, 5))
        
        row1 = ctk.CTkFrame(meta_frame, fg_color="transparent")
        row1.pack(fill="x", padx=14, pady=5)
        
        cats = [c[0] for c in self.db_mgr.get_categories()]
        self.cat_var = ctk.StringVar(value=cats[0] if cats else "CUSTOM")
        ctk.CTkLabel(row1, text="Catégorie :", width=70, anchor="w", text_color=COLORS["text_secondary"]).pack(side="left")
        ctk.CTkComboBox(row1, variable=self.cat_var, values=cats, width=120, fg_color=COLORS["bg_dark"], border_color=COLORS["border"]).pack(side="left", padx=(0, 15))
        
        colors = ["Blanc", "Gris Anodisé", "Personnalisé"]
        self.color_var = ctk.StringVar(value="Blanc")
        ctk.CTkLabel(row1, text="Couleur :", width=55, anchor="w", text_color=COLORS["text_secondary"]).pack(side="left")
        ctk.CTkComboBox(row1, variable=self.color_var, values=colors, width=130, fg_color=COLORS["bg_dark"], border_color=COLORS["border"]).pack(side="left", padx=(0, 15))
        
        row_img = ctk.CTkFrame(meta_frame, fg_color="transparent")
        row_img.pack(fill="x", padx=14, pady=(5, 3))
        
        ctk.CTkLabel(row_img, text="Image :", width=70, anchor="w", text_color=COLORS["text_secondary"]).pack(side="left")
        ctk.CTkButton(row_img, text="Sélectionner", width=100, fg_color=COLORS["bg_dark"], border_color=COLORS["border"], border_width=1, hover_color=COLORS["bg_card_hover"], command=self.choose_image).pack(side="left", padx=(0, 15))
        self.lbl_selected_img = ctk.CTkLabel(row_img, text="Aucune image sélectionnée", text_color=COLORS["text_muted"], font=ctk.CTkFont(size=11, slant="italic"))
        self.lbl_selected_img.pack(side="left")
        
        row2 = ctk.CTkFrame(meta_frame, fg_color="transparent")
        row2.pack(fill="x", padx=14, pady=(5, 3))
        
        ctk.CTkLabel(row2, text="Largeur (mm) :", width=100, anchor="w", text_color=COLORS["text_secondary"]).pack(side="left")
        w_entry = ctk.CTkEntry(row2, textvariable=self.w_var, width=80, fg_color=COLORS["bg_dark"], border_color=COLORS["border"])
        w_entry.pack(side="left", padx=(0, 15))
        w_entry.bind("<KeyRelease>", self.recalculate)
        
        ctk.CTkLabel(row2, text="Profondeur (mm) :", width=120, anchor="w", text_color=COLORS["text_secondary"]).pack(side="left")
        d_entry = ctk.CTkEntry(row2, textvariable=self.depth_var, width=80, fg_color=COLORS["bg_dark"], border_color=COLORS["border"])
        d_entry.pack(side="left", padx=(0, 15))
        d_entry.bind("<KeyRelease>", self.recalculate)

        row3 = ctk.CTkFrame(meta_frame, fg_color="transparent")
        row3.pack(fill="x", padx=14, pady=(3, 3))
        
        ctk.CTkLabel(row3, text="Diamètre (mm) :", width=100, anchor="w", text_color=COLORS["text_secondary"]).pack(side="left")
        diam_entry = ctk.CTkEntry(row3, textvariable=self.diameter_var, width=80, fg_color=COLORS["bg_dark"], border_color=COLORS["border"])
        diam_entry.pack(side="left", padx=(0, 15))
        diam_entry.bind("<KeyRelease>", self.recalculate)
        
        ctk.CTkLabel(row3, text="Hauteur (mm) :", width=120, anchor="w", text_color=COLORS["text_secondary"]).pack(side="left")
        h_entry = ctk.CTkEntry(row3, textvariable=self.h_var, width=80, fg_color=COLORS["bg_dark"], border_color=COLORS["border"])
        h_entry.pack(side="left", padx=(0, 10))
        h_entry.bind("<KeyRelease>", self.recalculate)

        # ── 2. MATIÈRE PREMIÈRE ──
        base_frame = ctk.CTkFrame(main_scroll, fg_color=COLORS["bg_card"], corner_radius=8)
        base_frame.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(base_frame, text="2. MATIÈRE PREMIÈRE (CALCUL AUTO)", font=ctk.CTkFont(size=12, weight="bold"), text_color=COLORS["accent"]).pack(anchor="w", padx=14, pady=(10, 5))
        
        th_vals = [t[0] for t in self.thicknesses] if self.thicknesses else ["EP 8/10"]
        
        # Tôle Row
        tole_row = ctk.CTkFrame(base_frame, fg_color="transparent")
        tole_row.pack(fill="x", padx=14, pady=(5, 2))
        
        tole_cb = ctk.CTkCheckBox(tole_row, text="Tôle (Plat)", variable=self.tole_check_var, width=120, command=lambda: self.toggle_base_row("tole"))
        tole_cb.pack(side="left", padx=(0, 10))
        
        self.tole_th_cb = ctk.CTkComboBox(tole_row, variable=self.tole_th_var, values=th_vals, width=100, fg_color=COLORS["bg_dark"], border_color=COLORS["border"], command=lambda _: self.recalculate())
        self.tole_th_cb.pack(side="left", padx=(0, 10))

        ctk.CTkLabel(tole_row, text="Prix/kg :", text_color=COLORS["text_secondary"]).pack(side="left", padx=(5, 2))
        self.tole_price_ent = ctk.CTkEntry(tole_row, textvariable=self.tole_price_var, width=60, fg_color=COLORS["bg_dark"], border_color=COLORS["border"])
        self.tole_price_ent.pack(side="left", padx=(0, 15))
        self.tole_price_ent.bind("<KeyRelease>", self.recalculate)

        ctk.CTkLabel(tole_row, text="Poids :", text_color=COLORS["text_secondary"]).pack(side="left", padx=(5, 2))
        ctk.CTkLabel(tole_row, textvariable=self.tole_weight_var, font=ctk.CTkFont(weight="bold"), width=70, anchor="w").pack(side="left", padx=(0, 15))
        
        ctk.CTkLabel(tole_row, text="Sous-total :", text_color=COLORS["text_secondary"]).pack(side="left", padx=(5, 2))
        ctk.CTkLabel(tole_row, textvariable=self.tole_subtotal_var, font=ctk.CTkFont(weight="bold"), text_color=COLORS["accent"], width=60, anchor="e").pack(side="left", padx=(0, 5))

        # RMB Row
        rmb_row = ctk.CTkFrame(base_frame, fg_color="transparent")
        rmb_row.pack(fill="x", padx=14, pady=(2, 10))
        
        rmb_cb = ctk.CTkCheckBox(rmb_row, text="RMB (Circ.)", variable=self.rmb_check_var, width=120, command=lambda: self.toggle_base_row("rmb"))
        rmb_cb.pack(side="left", padx=(0, 10))
        
        self.rmb_th_cb = ctk.CTkComboBox(rmb_row, variable=self.rmb_th_var, values=th_vals, width=100, fg_color=COLORS["bg_dark"], border_color=COLORS["border"], command=lambda _: self.recalculate())
        self.rmb_th_cb.pack(side="left", padx=(0, 10))

        ctk.CTkLabel(rmb_row, text="Prix/kg :", text_color=COLORS["text_secondary"]).pack(side="left", padx=(5, 2))
        self.rmb_price_ent = ctk.CTkEntry(rmb_row, textvariable=self.rmb_price_var, width=60, fg_color=COLORS["bg_dark"], border_color=COLORS["border"])
        self.rmb_price_ent.pack(side="left", padx=(0, 15))
        self.rmb_price_ent.bind("<KeyRelease>", self.recalculate)

        ctk.CTkLabel(rmb_row, text="Poids :", text_color=COLORS["text_secondary"]).pack(side="left", padx=(5, 2))
        ctk.CTkLabel(rmb_row, textvariable=self.rmb_weight_var, font=ctk.CTkFont(weight="bold"), width=70, anchor="w").pack(side="left", padx=(0, 15))
        
        ctk.CTkLabel(rmb_row, text="Sous-total :", text_color=COLORS["text_secondary"]).pack(side="left", padx=(5, 2))
        ctk.CTkLabel(rmb_row, textvariable=self.rmb_subtotal_var, font=ctk.CTkFont(weight="bold"), text_color=COLORS["accent"], width=60, anchor="e").pack(side="left", padx=(0, 5))


        # ── 3. COMPOSANTS ADDITIONNELS (NOMENCLATURE) ──
        self.bom_frame = ctk.CTkFrame(main_scroll, fg_color=COLORS["bg_card"], corner_radius=8)
        self.bom_frame.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(self.bom_frame, text="3. COMPOSANTS ADDITIONNELS", font=ctk.CTkFont(size=12, weight="bold"), text_color=COLORS["accent"]).pack(anchor="w", padx=14, pady=(10, 5))
        
        self.comp_container = ctk.CTkFrame(self.bom_frame, fg_color="transparent")
        self.comp_container.pack(fill="x", padx=14, pady=5)
        
        hdr = ctk.CTkFrame(self.comp_container, fg_color="transparent")
        hdr.pack(fill="x", pady=2)
        ctk.CTkLabel(hdr, text="Nom", width=120, anchor="w", font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"), text_color=COLORS["text_muted"]).pack(side="left", padx=2)
        ctk.CTkLabel(hdr, text="Unité", width=90, anchor="w", font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"), text_color=COLORS["text_muted"]).pack(side="left", padx=2)
        ctk.CTkLabel(hdr, text="Qté", width=100, anchor="w", font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"), text_color=COLORS["text_muted"]).pack(side="left", padx=2)
        ctk.CTkLabel(hdr, text="Prix/Unité", width=80, anchor="w", font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"), text_color=COLORS["text_muted"]).pack(side="left", padx=2)
        ctk.CTkLabel(hdr, text="Sous-total", width=80, anchor="e", font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"), text_color=COLORS["text_muted"]).pack(side="left", padx=2)
        
        ctk.CTkButton(self.bom_frame, text="➕ Ajouter Composant", command=self.add_comp_row, fg_color="transparent", border_width=1, border_color=COLORS["accent"], text_color=COLORS["accent"], height=28).pack(pady=(5, 10), padx=14, anchor="w")

        # ── 4. TARIFICATION & MAIN D'ŒUVRE ──
        pr_frame = ctk.CTkFrame(main_scroll, fg_color=COLORS["bg_card"], corner_radius=8)
        pr_frame.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(pr_frame, text="4. TARIFICATION & MAIN D'ŒUVRE", font=ctk.CTkFont(size=12, weight="bold"), text_color=COLORS["accent"]).pack(anchor="w", padx=14, pady=(10, 5))
        
        grid = ctk.CTkFrame(pr_frame, fg_color="transparent")
        grid.pack(fill="x", padx=14, pady=5)
        
        # Labor row
        ctk.CTkLabel(grid, text="Temps EXEC :", width=100, anchor="w").grid(row=0, column=0, pady=5)
        e1 = ctk.CTkEntry(grid, textvariable=self.exec_time_var, width=70, fg_color=COLORS["bg_dark"], border_color=COLORS["border"])
        e1.grid(row=0, column=1, padx=5)
        e1.bind("<KeyRelease>", self.recalculate)
        
        # Time unit toggle (Minutes / Heures)
        time_unit_cb = ctk.CTkComboBox(grid, variable=self.exec_time_unit_var, values=["Heures", "Minutes"], width=95, fg_color=COLORS["bg_dark"], border_color=COLORS["border"], command=lambda _: self.recalculate())
        time_unit_cb.grid(row=0, column=2, padx=5)
        
        ctk.CTkLabel(grid, text="Taux EXEC (DH/h) :", width=130, anchor="w").grid(row=0, column=3, pady=5)
        e2 = ctk.CTkEntry(grid, textvariable=self.exec_rate_var, width=70, fg_color=COLORS["bg_dark"], border_color=COLORS["border"])
        e2.grid(row=0, column=4, padx=5)
        e2.bind("<KeyRelease>", self.recalculate)
        
        # Margin row with preset buttons
        ctk.CTkLabel(grid, text="Marge (%) :", width=100, anchor="w").grid(row=1, column=0, pady=5)
        e3 = ctk.CTkEntry(grid, textvariable=self.margin_var, width=70, fg_color=COLORS["bg_dark"], border_color=COLORS["border"])
        e3.grid(row=1, column=1, padx=5)
        e3.bind("<KeyRelease>", self.recalculate)
        
        # Margin preset buttons
        margin_presets = ctk.CTkFrame(grid, fg_color="transparent")
        margin_presets.grid(row=1, column=2, columnspan=2, padx=5, sticky="w")
        for pct in ["0", "10", "30", "40"]:
            ctk.CTkButton(
                margin_presets, text=f"{pct}%", width=38, height=24,
                fg_color=COLORS["accent_dim"], hover_color=COLORS["accent"],
                font=ctk.CTkFont(size=11),
                command=lambda p=pct: (self.margin_var.set(p), self.recalculate())
            ).pack(side="left", padx=1)
        
        # Remise row
        ctk.CTkLabel(grid, text="Remise (%) :", width=100, anchor="w").grid(row=2, column=0, pady=5)
        e4 = ctk.CTkEntry(grid, textvariable=self.remise_var, width=70, fg_color=COLORS["bg_dark"], border_color=COLORS["border"])
        e4.grid(row=2, column=1, padx=5)
        e4.bind("<KeyRelease>", self.recalculate)
        
        # PT multiplier row
        ctk.CTkLabel(grid, text="Coeff. PT :", width=100, anchor="w").grid(row=2, column=3, pady=5)
        e5 = ctk.CTkEntry(grid, textvariable=self.pt_mult_var, width=70, fg_color=COLORS["bg_dark"], border_color=COLORS["border"])
        e5.grid(row=2, column=4, padx=5)
        e5.bind("<KeyRelease>", self.recalculate)

        # ── 5. RÉSULTATS ──
        res_frame = ctk.CTkFrame(main_scroll, fg_color=COLORS["bg_dark"], corner_radius=8, border_width=1, border_color=COLORS["accent"])
        res_frame.pack(fill="x", pady=(10, 10))
        
        self.lbl_mat_sum = ctk.CTkLabel(res_frame, text="Somme Matériaux : 0.00 DH", font=ctk.CTkFont(family="Consolas", size=14))
        self.lbl_mat_sum.pack(pady=(10, 2), padx=20, anchor="w")
        self.lbl_exec = ctk.CTkLabel(res_frame, text="Coût EXEC : 0.00 DH", font=ctk.CTkFont(family="Consolas", size=14))
        self.lbl_exec.pack(pady=2, padx=20, anchor="w")
        self.lbl_pr = ctk.CTkLabel(res_frame, text="PR (Coût de Revient) : 0.00 DH", font=ctk.CTkFont(family="Consolas", size=16, weight="bold"), text_color=COLORS["accent"])
        self.lbl_pr.pack(pady=2, padx=20, anchor="w")
        self.lbl_pt = ctk.CTkLabel(res_frame, text="PT (Prix de Vente) : 0.00 DH", font=ctk.CTkFont(family="Consolas", size=16, weight="bold"), text_color=COLORS["success"])
        self.lbl_pt.pack(pady=2, padx=20, anchor="w")
        self.lbl_net = ctk.CTkLabel(res_frame, text="Prix Net (après Remise) : 0.00 DH", font=ctk.CTkFont(family="Consolas", size=16, weight="bold"), text_color="#fff")
        self.lbl_net.pack(pady=(2, 10), padx=20, anchor="w")
        
        # Formula breakdown label
        self.lbl_formula = ctk.CTkLabel(res_frame, text="", font=ctk.CTkFont(size=11), text_color=COLORS["text_muted"], wraplength=600, justify="left")
        self.lbl_formula.pack(pady=(0, 10), padx=20, anchor="w")
        
        ctk.CTkButton(self, text="💾  Enregistrer au Catalogue", command=self.save_to_catalog, fg_color=COLORS["success"], hover_color="#2ab883", text_color=COLORS["bg_dark"], font=ctk.CTkFont(size=14, weight="bold"), height=42).pack(fill="x", padx=24, pady=(0, 24))
        
        self.toggle_base_row("tole")
        self.toggle_base_row("tole")
        self.toggle_base_row("rmb")

    def choose_image(self):
        path = filedialog.askopenfilename(filetypes=[("Images", "*.png *.jpg *.jpeg")])
        if path:
            self.image_path_var.set(path)
            self.lbl_selected_img.configure(text=os.path.basename(path))

    def toggle_base_row(self, row_type):
        if row_type == "tole":
            state = "normal" if self.tole_check_var.get() else "disabled"
            self.tole_th_cb.configure(state=state)
            self.tole_price_ent.configure(state=state)
        elif row_type == "rmb":
            state = "normal" if self.rmb_check_var.get() else "disabled"
            self.rmb_th_cb.configure(state=state)
            self.rmb_price_ent.configure(state=state)
        self.recalculate()

    def add_comp_row(self, name="", unit="ML", qty="1", price="0", is_removable=True, is_checked=True):
        row = ctk.CTkFrame(self.comp_container, fg_color="transparent")
        row.pack(fill="x", pady=2)
        
        n_var = ctk.StringVar(value=name)
        n_ent = ctk.CTkEntry(row, textvariable=n_var, width=120, height=28, fg_color=COLORS["bg_dark"], border_color=COLORS["border"])
        n_ent.pack(side="left", padx=2)
        
        u_var = ctk.StringVar(value=unit)
        units = ["ML", "m²", "kg", "U"]
        u_cb = ctk.CTkComboBox(row, variable=u_var, values=units, width=90, height=28, fg_color=COLORS["bg_dark"], border_color=COLORS["border"], command=lambda _: self.recalculate())
        u_cb.pack(side="left", padx=2)
        
        q_var = ctk.StringVar(value=qty)
        q_ent = ctk.CTkEntry(row, textvariable=q_var, width=100, height=28, fg_color=COLORS["bg_dark"], border_color=COLORS["border"])
        q_ent.pack(side="left", padx=2)
        q_ent.bind("<KeyRelease>", self.recalculate)
        
        p_var = ctk.StringVar(value=price)
        p_ent = ctk.CTkEntry(row, textvariable=p_var, width=80, height=28, fg_color=COLORS["bg_dark"], border_color=COLORS["border"])
        p_ent.pack(side="left", padx=2)
        p_ent.bind("<KeyRelease>", self.recalculate)
        
        sub_lbl = ctk.CTkLabel(row, text="0.00", width=80, anchor="e")
        sub_lbl.pack(side="left", padx=2)
        
        def update_ui(*_):
            try:
                w = float(self.w_var.get() or 0)
                h = float(self.h_var.get() or 0)
            except ValueError:
                w, h = 0, 0
                
            new_u = u_var.get()
            if new_u == "ML":
                # Perimeter in meters: 2 × (W/1000 + H/1000)
                q_var.set(f"{(w/1000 + h/1000) * 2:.3f}")
            elif new_u == "m²":
                # Area in m²: (W/1000) × (H/1000)
                q_var.set(f"{(w/1000) * (h/1000):.4f}")
            elif new_u == "U":
                q_var.set("4")
            else:
                try:
                    float(q_var.get())
                except ValueError:
                    q_var.set("1")
            self.recalculate()
            
        u_var.trace_add("write", update_ui)
        
        check_var = ctk.BooleanVar(value=is_checked)
        
        def toggle_row():
            state = "normal" if check_var.get() else "disabled"
            n_ent.configure(state=state)
            u_cb.configure(state=state)
            p_ent.configure(state=state)
            q_ent.configure(state=state)
            self.recalculate()

        if is_removable:
            ctk.CTkButton(row, text="✕", width=28, height=28, fg_color="transparent", text_color=COLORS["error"], hover_color=COLORS["bg_card"], command=lambda r=row, d=(n_var, u_var, q_var, p_var, sub_lbl, row, check_var): self.remove_comp_row(r, d)).pack(side="right", padx=2)
        else:
            cb = ctk.CTkCheckBox(row, text="", variable=check_var, width=28, command=toggle_row)
            cb.pack(side="right", padx=2)
            toggle_row()
        
        self.comp_rows.append((n_var, u_var, q_var, p_var, sub_lbl, row, check_var))
        self.recalculate()

    def remove_comp_row(self, row, data):
        if data in self.comp_rows:
            self.comp_rows.remove(data)
        row.destroy()
        self.recalculate()

    def recalculate(self, *_):
        try:
            w = float(self.w_var.get() or 0)
            h = float(self.h_var.get() or 0)
            depth = float(self.depth_var.get() or 0)
            diameter = float(self.diameter_var.get() or 0)
        except ValueError:
            w, h, depth, diameter = 0, 0, 0, 0
            
        mat_sum = 0.0
        th_map = {t[0]: t[1] for t in self.thicknesses} if self.thicknesses else {"EP 8/10": 0.8}
        
        # 1. Base Material Calc (Tôle) — perimeter unrolled: 2×(W+D) × H
        tole_weight = 0.0
        tole_subtotal = 0.0
        if self.tole_check_var.get():
            try:
                price = float(self.tole_price_var.get() or 0)
            except ValueError:
                price = 0.0
            th_mm = th_map.get(self.tole_th_var.get(), 0.8)
            weight_m2 = th_mm * self.density_mult
            # Rectangular duct: unrolled width = 2×(Largeur+Profondeur), height = Hauteur
            perim_m = 2 * (w / 1000 + depth / 1000)
            area = perim_m * (h / 1000)
            tole_weight = area * weight_m2
            tole_subtotal = tole_weight * price
            
            self.tole_weight_var.set(f"{tole_weight:.3f} kg")
            self.tole_subtotal_var.set(f"{tole_subtotal:.2f}")
            mat_sum += tole_subtotal
        else:
            self.tole_weight_var.set("0.000 kg")
            self.tole_subtotal_var.set("0.00")

        # 1b. Base Material Calc (RMB) — area = π × Diameter × Hauteur
        rmb_weight = 0.0
        rmb_subtotal = 0.0
        if self.rmb_check_var.get():
            try:
                price = float(self.rmb_price_var.get() or 0)
            except ValueError:
                price = 0.0
            th_mm = th_map.get(self.rmb_th_var.get(), 0.8)
            weight_m2 = th_mm * self.density_mult
            # Cylindrical: circumference = π × Diameter, height = Hauteur
            area = math.pi * (diameter / 1000) * (h / 1000)
            rmb_weight = area * weight_m2
            rmb_subtotal = rmb_weight * price
            
            self.rmb_weight_var.set(f"{rmb_weight:.3f} kg")
            self.rmb_subtotal_var.set(f"{rmb_subtotal:.2f}")
            mat_sum += rmb_subtotal
        else:
            self.rmb_weight_var.set("0.000 kg")
            self.rmb_subtotal_var.set("0.00")
            
        # 2. Additional Components Calc — subtotal = qty × price_per_unit
        for n_var, u_var, q_var, p_var, sub_lbl, _, check_var in self.comp_rows:
            if not check_var.get():
                sub_lbl.configure(text="0.00")
                continue
                
            try:
                price = float(p_var.get() or 0)
                qty = float(q_var.get() or 0)
            except ValueError:
                price, qty = 0.0, 0.0
                
            subtotal = qty * price
            sub_lbl.configure(text=f"{subtotal:.2f}")
            mat_sum += subtotal
            
        # 3. Labor — convert time to hours if entered in minutes
        try:
            e_time_raw = float(self.exec_time_var.get() or 0)
            e_rate = float(self.exec_rate_var.get() or 0)
        except ValueError:
            e_time_raw, e_rate = 0, 0
        
        # Convert to hours for calculation
        if self.exec_time_unit_var.get() == "Minutes":
            e_time_hours = e_time_raw / 60.0
        else:
            e_time_hours = e_time_raw
            
        exec_cost = e_time_hours * e_rate
        
        # 4. Margins & Discounts
        # Margin applies to MATERIAL SUM only (not EXEC) — verified from Excel
        try:
            margin = float(self.margin_var.get() or 0) / 100
            remise = float(self.remise_var.get() or 0) / 100
        except ValueError:
            margin, remise = 0, 0
        
        # PT multiplier — editable (default 1.40 = 40% markup)
        try:
            pt_mult = float(self.pt_mult_var.get() or 1.40)
        except ValueError:
            pt_mult = 1.40
            
        margined_mat = mat_sum * (1 + margin)
        pr = margined_mat + exec_cost
        pt = pr * pt_mult
        net = pt * (1 - remise)
        
        self.lbl_mat_sum.configure(text=f"Somme Matériaux : {mat_sum:.2f} DH")
        self.lbl_exec.configure(text=f"Coût EXEC : {exec_cost:.2f} DH")
        self.lbl_pr.configure(text=f"PR (Coût de Revient) : {pr:.2f} DH")
        self.lbl_pt.configure(text=f"PT (Prix de Vente) : {pt:.2f} DH")
        self.lbl_net.configure(text=f"Prix Net (après Remise) : {net:.2f} DH")
        
        # Formula breakdown for transparency
        time_display = f"{e_time_raw:.1f} min" if self.exec_time_unit_var.get() == "Minutes" else f"{e_time_raw:.2f} h"
        formula_text = (
            f"Formule : PR = (Σ Matériaux × (1 + {margin*100:.0f}%)) + (EXEC {time_display} × {e_rate:.0f} DH/h)\n"
            f"         = ({mat_sum:.2f} × {1+margin:.2f}) + ({e_time_hours:.4f}h × {e_rate:.0f}) "
            f"= {margined_mat:.2f} + {exec_cost:.2f} = {pr:.2f} DH\n"
            f"PT = PR × {pt_mult:.2f} = {pt:.2f} DH"
        )
        if remise > 0:
            formula_text += f"  |  Net = PT × (1 - {remise*100:.0f}%) = {net:.2f} DH"
        self.lbl_formula.configure(text=formula_text)
        
        self.current_totals = (pr, pt, net, tole_weight, rmb_weight, e_time_hours, e_rate)

    def save_to_catalog(self):
        self.recalculate()
        
        cat = self.cat_var.get().strip().upper()
        color = self.color_var.get().strip()
        
        # Build dimension string based on active geometry
        if self.tole_check_var.get():
            dim = f"{self.w_var.get().strip()}*{self.depth_var.get().strip()}*{self.h_var.get().strip()}"
        elif self.rmb_check_var.get():
            dim = f"Ø{self.diameter_var.get().strip()}*{self.h_var.get().strip()}"
        else:
            dim = f"{self.w_var.get().strip()}*{self.h_var.get().strip()}"
        
        if not cat or not color:
            messagebox.showerror("Erreur", "La catégorie et la couleur ne doivent pas être vides.", parent=self)
            return
            
        try:
            h_int = int(float(self.h_var.get().strip()))
            if self.rmb_check_var.get():
                w_int = int(float(self.diameter_var.get().strip()))
            else:
                w_int = int(float(self.w_var.get().strip()))
        except ValueError:
            messagebox.showerror("Erreur", "Les dimensions doivent être des nombres entiers pour enregistrer au catalogue.", parent=self)
            return

        # Ensure the category exists in product_categories so it shows up in the dropdowns
        self.db_mgr.ensure_category_exists(cat, cat)

        if self.db_mgr.product_exists(cat, color, dim):
            messagebox.showerror("Erreur", f"Le produit {cat} / {color} / {dim} existe déjà.", parent=self)
            return
            
        try:
            dest_img_path = None
            src_img = self.image_path_var.get()
            if src_img and os.path.exists(src_img):
                dest_dir = os.path.join(self.db_mgr.app_data_dir, "images")
                os.makedirs(dest_dir, exist_ok=True)
                ext = os.path.splitext(src_img)[1]
                new_name = f"img_{uuid.uuid4().hex[:8]}{ext}"
                dest_img_path = os.path.join(dest_dir, new_name)
                shutil.copy2(src_img, dest_img_path)
                
            pid = self.db_mgr.add_product(cat, color, dim, w_int, h_int, image_path=dest_img_path)
        except Exception as e:
            messagebox.showerror("Erreur", str(e), parent=self)
            return
            
        # Save Base Materials
        pr, pt, net, tole_weight, rmb_weight, e_time_hours, e_rate = self.current_totals
        if self.tole_check_var.get() and tole_weight > 0:
            try: price = float(self.tole_price_var.get() or 0)
            except (ValueError, TypeError): price = 0.0
            self.db_mgr.add_component(pid, "Tôle", tole_weight, price)
            
        if self.rmb_check_var.get() and rmb_weight > 0:
            try: price = float(self.rmb_price_var.get() or 0)
            except (ValueError, TypeError): price = 0.0
            self.db_mgr.add_component(pid, "RMB", rmb_weight, price)
            
        # Save additional components
        for n_var, u_var, q_var, p_var, sub_lbl, _, check_var in self.comp_rows:
            if not check_var.get(): continue
            name = n_var.get().strip()
            if not name: continue
            
            try:
                qty = float(q_var.get() or 0)
                price = float(p_var.get() or 0)
            except ValueError:
                qty, price = 0.0, 0.0
                
            self.db_mgr.add_component(pid, name, qty, price)
            
        # Add EXEC as a component (always stored in hours)
        if e_time_hours > 0:
            self.db_mgr.add_component(pid, "EXEC", e_time_hours, e_rate)
            
        conn = self.db_mgr.get_connection()
        try:
            cur = conn.cursor()
            cur.execute("UPDATE products SET excel_cost = ?, excel_tariff = ? WHERE id = ?", (pr, pt, pid))
            conn.commit()
        finally:
            conn.close()
        
        if self.refresh_callback:
            self.refresh_callback()
            
        messagebox.showinfo("Succès", f"Produit enregistré au catalogue !\nPR : {pr:.2f} DH\nPT : {pt:.2f} DH", parent=self)
