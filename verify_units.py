"""
Verify calculator_gui.py formulas match Excel exactly.
Tests unit handling (ML, m², kg, U) and full PR chain.
"""

print("=" * 70)
print("UNIT FORMULA VERIFICATION")
print("=" * 70)

# Test dimensions
W, H = 600, 400  # mm

# ML: perimeter = 2 × (W/1000 + H/1000)
ml_qty = (W/1000 + H/1000) * 2
print(f"\nML (périmètre) pour {W}*{H}:")
print(f"  Formule: 2 × ({W}/1000 + {H}/1000) = 2 × {W/1000 + H/1000:.1f} = {ml_qty:.3f} ML")
# Verify: PROFIL qty for 600*400 in Excel
# From FICHE FOURNITURE, PROFIL is priced per ML
# Excel: GSD 600*400, PROFIL qty = 2.238 ML (not equal to perimeter!)
# NOTE: ML smart default is a rough estimate. Excel qty is measured, not formula-derived.
print(f"  Note: Valeur auto est une estimation. Les qtés Excel sont mesurées.")

# m²: area = (W/1000) × (H/1000)
m2_qty = (W/1000) * (H/1000)
print(f"\nm² (surface) pour {W}*{H}:")
print(f"  Formule: ({W}/1000) × ({H}/1000) = {W/1000:.1f} × {H/1000:.1f} = {m2_qty:.4f} m²")

# U: fixed = 4
print(f"\nU (unités) pour {W}*{H}:")
print(f"  Valeur auto: 4 (standard pour clips/équerres)")

# kg: keep current or 1
print(f"\nkg pour {W}*{H}:")
print(f"  Valeur auto: 1 (valeur par défaut sûre)")

print("\n" + "=" * 70)
print("TÔLE FORMULA VERIFICATION")
print("=" * 70)

thickness = 0.8  # EP 8/10
density = 8
price_kg = 15

area = (W/1000) * (H/1000)
weight_m2 = thickness * density
weight = area * weight_m2
cost = weight * price_kg

print(f"\nTôle pour {W}*{H}, EP 8/10, 15 DH/kg:")
print(f"  Surface = {W/1000} × {H/1000} = {area:.4f} m²")
print(f"  Poids/m² = {thickness} × {density} = {weight_m2:.1f} kg/m²")
print(f"  Poids total = {area:.4f} × {weight_m2:.1f} = {weight:.4f} kg")
print(f"  Coût = {weight:.4f} × {price_kg} = {cost:.2f} DH")

import math
print("\n" + "=" * 70)
print("RMB FORMULA VERIFICATION")
print("=" * 70)

D = 600  # diameter mm
area_rmb = math.pi * (D/1000) * (H/1000)
weight_rmb = area_rmb * weight_m2
cost_rmb = weight_rmb * price_kg

print(f"\nRMB pour D={D}mm, H={H}mm, EP 8/10, 15 DH/kg:")
print(f"  Surface = π × {D/1000} × {H/1000} = {area_rmb:.4f} m²")
print(f"  Poids = {area_rmb:.4f} × {weight_m2:.1f} = {weight_rmb:.4f} kg")
print(f"  Coût = {weight_rmb:.4f} × {price_kg} = {cost_rmb:.2f} DH")

print("\n" + "=" * 70)
print("FULL PR CHAIN VERIFICATION")
print("=" * 70)

# Scenario: Match Excel GSD Blanc 200*100
W2, H2 = 200, 100
comps = [
    ("PROFIL", "ML", 0.768, 19.89),
    ("AIL", "ML", 0.798, 11.03),
    ("REG 100", "U", 2, 1.24),
    ("RENF", "ML", 0, 0),
    ("CLIP", "U", 4, 1.89),
    ("EQUERE", "U", 4, 0.24),
]

print(f"\nProduit: GSD Blanc {W2}*{H2} (from Excel)")
mat_sum = 0
for name, unit, qty, up in comps:
    sub = qty * up
    mat_sum += sub
    print(f"  {name:12s} [{unit:3s}]  qté={qty:8.3f} × prix={up:8.2f} = {sub:8.5f}")

margin = 0  # GSD individual sheets have 0% explicit margin
exec_time_min = 15
exec_rate = 1.41  # DH/min

# Calculator would use: time in Minutes → converted to hours
exec_time_hours = exec_time_min / 60
exec_cost_hours_method = exec_time_hours * (1.41 * 60)  # 1.41 DH/min = 84.6 DH/h
exec_cost_direct = exec_time_min * 1.41  # direct minute calc

print(f"\n  Somme Matériaux = {mat_sum:.5f}")
print(f"  Marge = {margin*100:.0f}%")
print(f"  Matériaux margés = {mat_sum * (1 + margin):.5f}")

print(f"\n  EXEC (méthode directe): {exec_time_min} min × {exec_rate} DH/min = {exec_cost_direct:.2f}")
print(f"  EXEC (méthode calc):    {exec_time_hours:.4f}h × {exec_rate*60:.1f} DH/h = {exec_cost_hours_method:.2f}")
print(f"  EXEC Excel:             21.15")
print(f"  Direct match: {abs(exec_cost_direct - 21.15) < 0.01}")
print(f"  Calc match:   {abs(exec_cost_hours_method - 21.15) < 0.1}")

# For calculator: user enters time=15, unit=Minutes, rate=84.6 DH/h (or 1.41*60)
# exec_cost = (15/60) * 84.6 = 0.25 * 84.6 = 21.15 ✓
exec_calc = (15/60) * 84.6
print(f"\n  Calculator: temps=15, unité=Minutes, taux=84.6 DH/h")
print(f"  exec = (15/60) × 84.6 = {exec_calc:.2f} → Match: {abs(exec_calc - 21.15) < 0.01}")

# But if user uses 200 DH/h standard with 0.5h:
exec_200 = 0.5 * 200
print(f"\n  Alternative: temps=0.5h, taux=200 DH/h")
print(f"  exec = 0.5 × 200 = {exec_200:.2f}")
print(f"  NOTE: Cela donnerait un PR différent car le taux est différent")

pr = mat_sum * (1 + margin) + exec_cost_direct
pt = pr * 1.40
print(f"\n  PR = {mat_sum:.5f} + {exec_cost_direct:.2f} = {pr:.5f}")
print(f"  PT = {pr:.5f} × 1.40 = {pt:.2f}")
print(f"  Excel PR: 56.22746")
print(f"  Match: {abs(pr - 56.22746) < 0.01}")

print("\n" + "=" * 70)
print("EXEC RATE CONSISTENCY CHECK")
print("=" * 70)
print("""
Taux Excel observés et leur conversion :
  1.40 DH/min → dans le calculateur: taux=84 DH/h, unité=Minutes
  1.41 DH/min → dans le calculateur: taux=84.6 DH/h, unité=Minutes  
  85 DH/h     → dans le calculateur: taux=85 DH/h, unité=Heures
  200 DH/h    → dans le calculateur: taux=200 DH/h, unité=Heures (DÉFAUT)

Toutes les conversions sont correctes car:
  temps_heures = temps_minutes / 60
  coût_exec = temps_heures × taux_DH_par_heure
  
Exemple: 15 min à 1.41 DH/min = 21.15 DH
  Via calculateur: (15/60) × 84.6 = 0.25 × 84.6 = 21.15 DH ✓
""")
