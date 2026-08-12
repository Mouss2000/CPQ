"""Verify FICHE POIDS formula and cross-check calculator vs Excel."""

# 1. FICHE POIDS VERIFICATION
pdf_data = [
    ('EP 5/10', 0.5, 4.0, 8, 10, 12),
    ('EP 6/10', 0.6, 4.8, 9.6, 12, 14.4),
    ('EP 7/10', 0.7, 5.6, 11.2, 14, 16.8),
    ('EP 8/10', 0.8, 6.4, 12.8, 16, 19.2),
    ('EP 9/10', 0.9, 7.2, 14.4, 18, 21.6),
    ('EP 10/10', 1.0, 8.0, 16, 20, 24),
    ('EP 11/10', 1.1, 8.8, 17.6, 22, 26.4),
    ('EP 12/10', 1.2, 9.6, 19.2, 24, 28.8),
    ('EP 15/10', 1.5, 12.0, 24, 30, 36),
    ('EP 19/10', 1.9, 15.2, 30.4, 38, 45.6),
    ('EP 20/10', 2.0, 16.0, 32, 40, 48),
]

print("=" * 70)
print("FICHE POIDS VERIFICATION: weight_per_m2 = thickness_mm * 8")
print("=" * 70)
all_ok = True
for label, t_mm, pdf_wt, s_2x1, s_2x125, s_3x1 in pdf_data:
    calc_wt = t_mm * 8
    match_wt = abs(calc_wt - pdf_wt) < 0.001
    calc_2x1 = calc_wt * 2
    calc_2x125 = calc_wt * 2.5
    calc_3x1 = calc_wt * 3
    match_sheets = (abs(calc_2x1 - s_2x1) < 0.01 and 
                    abs(calc_2x125 - s_2x125) < 0.01 and 
                    abs(calc_3x1 - s_3x1) < 0.01)
    ok = match_wt and match_sheets
    all_ok = all_ok and ok
    status = "OK" if ok else "FAIL"
    print(f"  {label:12s}  thick={t_mm:.1f}mm  wt/m2: PDF={pdf_wt:.1f} calc={calc_wt:.1f}  [{status}]")
    
print(f"\nFICHE POIDS: {'ALL PASS' if all_ok else 'SOME FAIL'}")

# 2. EXCEL PRODUCT BLOCK FORMULA VERIFICATION
print("\n" + "=" * 70)
print("EXCEL FORMULA STRUCTURE (from raw cell analysis)")
print("=" * 70)

# GSD/GDD sheets: components have numeric qty/rate in C/D/E
# Example: GSD DD LARG 100 BL, 200*100 (left table)
print("\nEXAMPLE 1: GSD Blanc 200*100 (from Excel R5-R13)")
comps_gsd = [
    ("PROFIL", 0.768, 19.89),
    ("AIL", 0.798, 11.03),
    ("REG 100", 2, 1.24),
    ("RENF", 0, 0),
    ("CLIP", 4, 1.89),
    ("EQUERE", 4, 0.24),
]
mat_sum = 0
for name, qty, up in comps_gsd:
    sub = qty * up
    mat_sum += sub
    print(f"  {name:12s}  qty={qty:8.3f}  up={up:8.2f}  sub={sub:8.5f}")
print(f"  Material Sum = {mat_sum:.5f}")
print(f"  Excel Material Sum row (R11) = 35.07746")
print(f"  Match: {abs(mat_sum - 35.07746) < 0.001}")

exec_time_min = 15
exec_rate = 1.41  # DH/min
exec_cost = exec_time_min * exec_rate
print(f"  EXEC: {exec_time_min} min * {exec_rate} DH/min = {exec_cost:.2f}")
print(f"  Excel EXEC (R12) = 21.15")
print(f"  Match: {abs(exec_cost - 21.15) < 0.01}")

pr = mat_sum + exec_cost  # No margin on this sheet
print(f"  PR = {mat_sum:.5f} + {exec_cost:.2f} = {pr:.5f}")
print(f"  Excel PR (R13) = 56.22746")
print(f"  Match: {abs(pr - 56.22746) < 0.01}")

# GBF sheets: EXEC is text like "15 min" with cost directly in col E
print("\nEXAMPLE 2: GBF Gris 200*40 (from Excel R7-R13)")
comps_gbf = [
    ("PROFIL", 0.643, 29.12),
    ("AIL", 0.2, 15.25),
    ("T/ALUM", 0.08, 17.19),
    ("CLIP", 4, 2.89),
    ("EQUERE", 4, 0.6),
]
mat_sum_gbf = 0
for name, qty, up in comps_gbf:
    sub = qty * up
    mat_sum_gbf += sub
    print(f"  {name:12s}  qty={qty:8.3f}  up={up:8.2f}  sub={sub:8.5f}")
print(f"  Material Sum = {mat_sum_gbf:.5f}")
exec_gbf = 21  # "15 min" -> 21 DH (implied rate: 21/15 = 1.40 DH/min = 84 DH/h)
print(f"  EXEC: '15 min' -> 21 DH (implied: 1.40 DH/min = 84 DH/h)")
pr_gbf = mat_sum_gbf + exec_gbf
print(f"  PR = {mat_sum_gbf:.5f} + {exec_gbf} = {pr_gbf:.5f}")
print(f"  Excel PR (R13) = 58.10936")
print(f"  Match: {abs(pr_gbf - 58.10936) < 0.01}")

# CALCUL EN m2 sheet: uses rate=200 DH/h
print("\nEXAMPLE 3: CALCUL EN m2 sheet pattern")
print("  EXEC: time_hours * 200 DH/h")
print("  Example: 2h * 200 = 400 DH")

# 3. EXEC RATE TIERS (from full analysis)
print("\n" + "=" * 70)
print("EXEC RATE TIERS (discovered from ALL sheets)")
print("=" * 70)
rates = [
    ("1.40 DH/min (= 84 DH/h)", "GBF ALU GR ET BL (main GBF sheet)", "Most GBF products"),
    ("1.41 DH/min (= 84.6 DH/h)", "GSD/GDD individual sheets", "Time in minutes"),
    ("1.42 DH/min (= 85.2 DH/h)", "Some GSD sheets", "Minor variant"),
    ("85 DH/h", "HSD sheets (GDD/GSD/GBF)", "Time in hours"),
    ("94.63 DH/h", "GRILLES HST VERTICALE", "Specialty"),
    ("101.32 DH/h", "ETS EL HARTI, GAINAIR GRILLES", "Contract-specific"),
    ("131 DH/h", "CALCUL EN m2 (some)", "Older pricing"),
    ("200 DH/h", "CALCUL EN m2 (main), DETAIL GRIS ALI BABA", "Highest tier"),
]
for rate, sheets, note in rates:
    print(f"  {rate:30s}  {sheets:35s}  {note}")

# 4. MARGIN PATTERNS
print("\n" + "=" * 70)
print("MARGIN PATTERNS")
print("=" * 70)
print("  GBF sheets: 0% margin (PR = components + EXEC directly)")
print("  GSD/GDD individual sheets: 0% explicit (some hidden 3-10%)")
print("  CALCUL EN m2: 10% to 40% (explicit 'four X%' rows)")
print("  Formula: PR = (Material_Sum * (1 + margin%)) + EXEC_Cost")
print("  IMPORTANT: margin applies to MATERIAL ONLY, not EXEC")

# 5. CRITICAL FINDING: Calculator vs Excel architecture mismatch
print("\n" + "=" * 70)
print("CRITICAL: CALCULATOR vs EXCEL ARCHITECTURE")
print("=" * 70)
print("""
The calculator has a BASE MATERIAL section (Tole/RMB) that computes raw
sheet metal cost from dimensions + thickness + density + price/kg.

BUT: In the Excel, there is NO standalone Tole row in product blocks.
The sheet metal cost is EMBEDDED INSIDE the component unit prices:
  - T/ALUM unit_price (17.19 DH/ML) = strip_width * (thickness * 8) * price/kg
  - PROFIL, AIL prices already include material cost

The calculator's Tole section is for INDEPENDENT sheet metal cost estimation
(e.g., for custom fabrication quotes), NOT for reproducing Excel product PRs.

For reproducing Excel PRs, the formula is simply:
  PR = SUM(component_qty * component_unit_price) * (1 + margin%) + EXEC

The Tole/RMB section is an ADDITIONAL tool for estimating raw material
costs when designing new products outside the catalog.
""")

# 6. COMPONENT UNITS
print("=" * 70)
print("COMPONENT UNIT TYPES (from Excel)")
print("=" * 70)
print("""
PROFIL  -> ML (meters linear) - profile length per grille
AIL     -> ML (meters linear) - ailette strip length
T/ALUM  -> ML (meters linear) - tube aluminum length  
CLIP    -> U  (units/pieces)  - typically 4 per grille
EQUERE  -> U  (units/pieces)  - typically 4 per grille  
REG     -> U  (units/pieces)  - typically 2 per grille
RENF    -> ML (meters linear) - reinforcement strip
EXEC    -> hours or minutes   - labor time

FICHE FOURNITURE (material price reference) confirms:
  PROFIL GSD anodise: 29.12 DH/ML (imported)
  PROFIL GSD blanc:   30.44 DH/ML (imported, was 30.29 in 2022)
  PROFIL GDD anodise: 29.24 DH/ML
  PROFIL GDD blanc:   45.07 DH/ML (was 42.29 in 2022)
  AIL 100 anodise:    14.94 DH/ML
  AIL 100 blanc:      16.17 DH/ML (was 16.086 in 2022)
  AIL 200 GBF anodise:15.25 DH/ML
  AIL 200 GBF blanc:  17.06 DH/ML (was 16 in 2022)
  T/ALUM:             17.19 DH/ML
  RENF:               18.06 DH/ML (was 14.61 in 2022)
  REG 100:            1.15 DH/U
  REG 150:            1.60 DH/U
  REG 200:            1.48 DH/U
  REG 300:            1.70 DH/U
  REG 400:            1.81 DH/U
  REG 500:            2.24 DH/U
  EQUERE:             0.61 DH/U (was 0.60 in 2022)
  CLIP FC:            2.91 DH/U (was 2.89 in 2022)
""")
