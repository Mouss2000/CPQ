import re
import os

file_path = r'C:\Users\SetupGame\OneDrive\Desktop\prototype\main_gui.py'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

replacements = [
    ('text="PRICING DETAILS"', 'text="DÉTAILS DE TARIFICATION"'),
    ('text="Select a product configuration"', 'text="Sélectionner une configuration de produit"'),
    ('text="PR  ·  PRIX DE REVIENT (COST)"', 'text="PR  ·  PRIX DE REVIENT (COÛT)"'),
    ('text="DIMENSIONS"', 'text="DIMENSIONS"'),
    ('text="BILL OF MATERIALS"', 'text="COMPOSANTS"'),
    ('text="TOTAL"', 'text="TOTAL"'),
    ('title("Admin Panel — Product & Pricing Management")', 'title("Administration — Gestion des produits et de la tarification")'),
    ('text="⚙  ADMIN PANEL"', 'text="⚙  PANNEAU D\'ADMINISTRATION"'),
    ('text="Manage product pricing and catalog entries"', 'text="Gérer la tarification des produits et le catalogue"'),
    ('text="📌 Create Restore Point"', 'text="📌 Créer un point de sauvegarde"'),
    ('text="🕒 Restore Data"', 'text="🕒 Restaurer les données"'),
    ('text="➕  New Product"', 'text="➕  Nouveau Produit"'),
    ('text="✏  Edit Existing"', 'text="✏  Modifier Produit"'),
    ('text="🗑  Delete"', 'text="🗑  Supprimer"'),
    ('text="Choose an action above:\\n\\n➕  New Product — create a new catalog entry\\n✏  Edit Existing — modify a product\'s details & components\\n🗑  Delete — remove a product from the catalog"', 'text="Choisissez une action ci-dessus :\\n\\n➕  Nouveau Produit — créer une nouvelle entrée dans le catalogue\\n✏  Modifier Produit — modifier les détails et les composants d\'un produit\\n🗑  Supprimer — retirer un produit du catalogue"'),
    ('text="SELECT PRODUCT TO EDIT"', 'text="SÉLECTIONNER LE PRODUIT À MODIFIER"'),
    ('text="CATEGORY"', 'text="CATÉGORIE"'),
    ('value="Select category..."', 'value="Sélectionner une catégorie..."'),
    ('text="COLOR"', 'text="COULEUR"'),
    ('value="Select color..."', 'value="Sélectionner une couleur..."'),
    ('text="DIMENSION"', 'text="DIMENSION"'),
    ('value="Select dimension..."', 'value="Sélectionner une dimension..."'),
    ('text="Select a product above to edit"', 'text="Sélectionnez un produit ci-dessus pour le modifier"'),
    ('text=f"EDITING: {cat} / {color} / {dim}"', 'text=f"MODIFICATION : {cat} / {color} / {dim}"'),
    ('text="Width:"', 'text="Largeur :"'),
    ('text="Height:"', 'text="Hauteur :"'),
    ('text="COMPONENTS"', 'text="COMPOSANTS"'),
    ('text="Name"', 'text="Nom"'),
    ('text="Qty"', 'text="Qté"'),
    ('text="Unit Price"', 'text="Prix unitaire"'),
    ('text="Subtotal"', 'text="Sous-total"'),
    ('text="➕ Add Component"', 'text="➕ Ajouter un composant"'),
    ('text="💾  Save All Changes"', 'text="💾  Enregistrer toutes les modifications"'),
    ('placeholder_text="Name"', 'placeholder_text="Nom"'),
    ('messagebox.askyesno("Delete Component",\n                "Remove this component permanently?", parent=self)', 'messagebox.askyesno("Supprimer le composant",\n                "Supprimer ce composant définitivement ?", parent=self)'),
    ('messagebox.showerror("Error", "Width/Height must be integers.", parent=self)', 'messagebox.showerror("Erreur", "La largeur/hauteur doivent être des entiers.", parent=self)'),
    ('f"Auto — before edit {cat}/{color}/{dim}"', 'f"Auto — avant modification {cat}/{color}/{dim}"'),
    ('messagebox.showerror("Error", f"Invalid number for \'{cname}\'.", parent=self)', 'messagebox.showerror("Erreur", f"Nombre invalide pour \'{cname}\'.", parent=self)'),
    ('text=f"✅ Saved — Total: {total:.2f} DA"', 'text=f"✅ Enregistré — Total : {total:.2f} DA"'),
    ('messagebox.showinfo("Saved", f"Product updated. New total: {total:.2f} DA", parent=self)', 'messagebox.showinfo("Succès", f"Produit mis à jour. Nouveau total : {total:.2f} DA", parent=self)'),
    ('messagebox.askyesno(\n            "Confirm Delete",\n            f"Permanently delete:\\n\\n{cat} / {color} / {dim}\\nCost: {float(cost):.2f} DA\\n\\nThis will remove the product and ALL its components.\\nAre you sure?",\n            parent=self,\n            icon="warning"\n        )', 'messagebox.askyesno(\n            "Confirmer la suppression",\n            f"Supprimer définitivement :\\n\\n{cat} / {color} / {dim}\\nCoût : {float(cost):.2f} DA\\n\\nCela supprimera le produit et TOUS ses composants.\\nÊtes-vous sûr ?",\n            parent=self,\n            icon="warning"\n        )'),
    ('messagebox.askyesno(\n            "Create Restore Point?",\n            "Do you want to create a restore point before deleting this product?\\n\\n(Click \'Yes\' for safety, or \'No\' to vaporize it forever without a backup).",\n            parent=self\n        )', 'messagebox.askyesno(\n            "Créer un point de sauvegarde ?",\n            "Voulez-vous créer un point de sauvegarde avant de supprimer ce produit ?\\n\\n(Cliquez sur \'Oui\' par sécurité, ou sur \'Non\' pour le vaporiser à jamais sans sauvegarde).",\n            parent=self\n        )'),
    ('f"Auto — before deleting {cat}/{color}/{dim}"', 'f"Auto — avant suppression {cat}/{color}/{dim}"'),
    ('text=f"🗑 Deleted: {cat} / {color} / {dim}"', 'text=f"🗑 Supprimé : {cat} / {color} / {dim}"'),
    ('messagebox.showinfo("Deleted", f"Product removed: {cat} / {color} / {dim}", parent=self)', 'messagebox.showinfo("Supprimé", f"Produit retiré : {cat} / {color} / {dim}", parent=self)'),
    ('text=f"📌 {len(cps)} checkpoint(s) available"', 'text=f"📌 {len(cps)} point(s) de sauvegarde disponible(s)"'),
    ('text="Checkpoint name (optional):", title="Create Checkpoint"', 'text="Nom du point de sauvegarde (optionnel) :", title="Créer un point de sauvegarde"'),
    ('messagebox.showinfo("Checkpoint Created", f"Saved: {cp_name}", parent=self)', 'messagebox.showinfo("Point de sauvegarde créé", f"Enregistré : {cp_name}", parent=self)'),
    ('messagebox.showinfo("No Checkpoints", "No checkpoints available to restore.", parent=self)', 'messagebox.showinfo("Aucun point de sauvegarde", "Aucun point de sauvegarde disponible à restaurer.", parent=self)'),
    ('restore_win.title("Restore Checkpoint")', 'restore_win.title("Restaurer un point de sauvegarde")'),
    ('text="⏪  SELECT CHECKPOINT TO RESTORE"', 'text="⏪  SÉLECTIONNER LE POINT DE SAUVEGARDE À RESTAURER"'),
    ('text="This will revert ALL products and pricing to the selected state."', 'text="Cela rétablira TOUS les produits et la tarification à l\'état sélectionné."'),
    ('text="Restore"', 'text="Restaurer"'),
    ('messagebox.askyesno(\n            "Confirm Restore",\n            f"Restore all products and pricing to:\\n\\n{checkpoint_name}\\n\\nThis cannot be undone.",\n            parent=dialog\n        )', 'messagebox.askyesno(\n            "Confirmer la restauration",\n            f"Restaurer tous les produits et la tarification à :\\n\\n{checkpoint_name}\\n\\nCette action est irréversible.",\n            parent=dialog\n        )'),
    ('messagebox.showinfo("Restored", f"Products and pricing restored to: {checkpoint_name}", parent=self)', 'messagebox.showinfo("Restauré", f"Produits et tarification restaurés à : {checkpoint_name}", parent=self)'),
    ('messagebox.askyesno("Delete Checkpoint", "Delete this checkpoint permanently?", parent=dialog)', 'messagebox.askyesno("Supprimer le point de sauvegarde", "Supprimer ce point de sauvegarde définitivement ?", parent=dialog)'),
    ('text="⚙ Admin"', 'text="⚙ Administration"'),
    ('text=f"📦 {count} products loaded"', 'text=f"📦 {count} Produits chargés"'),
    ('text="⚠ Database error"', 'text="⚠ Erreur de base de données"'),
    ('text="CONFIGURATION"', 'text="CONFIGURATION"'),
    ('text="Search or select category, color, and dimension"', 'text="Rechercher ou sélectionner une catégorie, couleur et dimension"'),
    ('placeholder_text="🔍  Search dimension (e.g. 600*60)..."', 'placeholder_text="🔍  Rechercher une dimension (ex: 600*60)..."'),
    ('text="PRODUCT CATEGORY"', 'text="CATÉGORIE DE PRODUIT"'),
    ('values=["Loading..."]', 'values=["Chargement..."]'),
    ('text="COLOR / FINISH"', 'text="COULEUR / FINITION"'),
    ('text="DIMENSION (W × H)"', 'text="DIMENSION (L × H)"'),
    ('text="↺  Reset Selection"', 'text="↺  Réinitialiser la sélection"'),
    ('text="No results found"', 'text="Aucun résultat trouvé"'),
    ('text="✓ Product found — pricing displayed"', 'text="✓ Produit trouvé — tarification affichée"'),
    ('text=f"✓ {len(colors)} color(s) available"', 'text=f"✓ {len(colors)} couleur(s) disponible(s)"'),
    ('values=["No colors found"]', 'values=["Aucune couleur trouvée"]'),
    ('text="⚠ No colors for this category"', 'text="⚠ Aucune couleur pour cette catégorie"'),
    ('text=f"✓ {len(dims)} dimension(s) available"', 'text=f"✓ {len(dims)} dimension(s) disponible(s)"'),
    ('values=["No dimensions found"]', 'values=["Aucune dimension trouvée"]'),
    ('text="⚠ No dimensions for this combo"', 'text="⚠ Aucune dimension pour cette combinaison"'),
    ('text="⚠ Non-Standard — not in catalog"', 'text="⚠ Non standard — pas dans le catalogue"'),
    ('values=["No colors"]', 'values=["Aucune couleur"]'),
    ('values=["No dimensions"]', 'values=["Aucune dimension"]'),
    ('"Select color..."', '"Sélectionner une couleur..."'),
    ('"Select dimension..."', '"Sélectionner une dimension..."'),
    ('"Select category..."', '"Sélectionner une catégorie..."')
]

for old, new in replacements:
    content = content.replace(old, new)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Translation script executed successfully.")
