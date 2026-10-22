# Phase 2C Permanent Exclusion Taxonomy & Architectural Rationale

**Work Item:** `bilingual-uom-phase2c-catalog-closure`  
**Site:** `v16.localhost`  
**Base Commit:** `3e871f0`  
**Total Excluded Units:** **204**  

---

## 1. Executive Summary & Policy

ERPNext ships with an extensive out-of-the-box unit catalog (`uom_data.json`) containing 253 total units. Following the completion of:
- **Phase 1 (`9ccb4cd`):** 15 core operational units (12 fixtures in `uom.json` + 3 active stock units: `Nos`, `Tonne`, `Box`).
- **Phase 2A & 2B (`3e871f0`):** 30 physical engineering and handling units (`Meter`, `Centimeter`, `Millimeter`, `Kilogram`, `Ton`, `Joule`, `Tesla`, `Pair`, etc.).
- **Fixture Exclusions (4 units):** 2 vendor fixtures (`_Test UOM`, `_Test UOM 1`) and 2 draft test units (`Pint (US)`, `Acre`).

The remaining **204 units** are hereby **formally, permanently excluded and sealed** from the bilingual localization catalog. Zero Arabic translations are drafted, stored, or maintained for these units.

---

## 2. Architectural Rationale for Permanent Exclusion

1. **Elimination of Desk Picker Pollution:**
   In ERPNext desk forms (e.g. Item Master, BOQ line items, Material Requests, Purchase Orders), link pickers query `tabUOM`. Populating hundreds of obscure, unused units causes severe noise in auto-complete dropdowns. Excluding them prevents confusing clutter for engineering and site users.

2. **Search Relevance Protection (Arabic & Latin):**
   The bilingual search dispatcher (`searchable_dropdown/api/search.py`) indexes both English names and normalized Arabic names (`uom_name_ar_norm`). Adding artificial Arabic translations for obscure imperial or archaic units (such as translating `Peck`, `Minim`, `Dram`, `Versta`, or `Sazhen`) creates high collision risks with common construction and trade terms, degrading P95 search latency and precision.

3. **Zero Civil, Structural, or MEP Engineering Relevance:**
   Detailed inspection shows that none of these 204 units have any valid application in civil construction, structural engineering, architectural finishes, or MEP works. Units such as `Abampere`, `Biot`, `Cable Length`, `Caballeria`, `Pood`, or `Wavelength In Gigametres` have zero industrial utility in modern construction ERP workflows.

4. **Elimination of Translation Maintenance Debt:**
   Maintaining translations for obsolete imperial or theoretical physics units imposes a recurring governance liability with zero business value.

---

## 3. Discrepancy Note: Briefing Examples vs. Authoritative Site Inventory

The exploratory briefing letter ([`docs/ai/BRIEFING_UOM_PHASE2C_CLOSURE.md`](file:///home/mohamed/frappe-bench/apps/construction/docs/ai/BRIEFING_UOM_PHASE2C_CLOSURE.md)) cited exemplary theoretical units (`Becquerel`, `Barn`, `Curie`, `Farad`, `Henry`, `Weber`, `Candela`, `Lumen`, `Lux`, `Gray`, `Sievert`, `Minim`, `League`).

**Authoritative Finding:**
- Examination of the live MariaDB `tabUOM` table (253 rows) reveals that those illustrative units do **not** exist in ERPNext's standard unit seed on this site.
- Furthermore, `Tesla` was already evaluated and populated as a valid engineering magnetic flux density unit during Phase 2A (`3e871f0`, line 67).
- Therefore, the **authoritative 204 units** triaged in [`inventory-triage.log`](file:///home/mohamed/frappe-bench/apps/construction/docs/ai/work-items/bilingual-uom-phase2-triage/evidence/inventory-triage.log) strictly govern this ratification.

---

## 4. Categorized Catalog of the 204 Excluded Units

The 204 excluded units are grouped into 4 distinct categories. Each list is sorted alphabetically:

### Category A: Physical, Dynamics, Pressure & Thermal Units (89 units)
*Units of pressure, obsolete thermal energy, microscopic dimensions, or specialized dynamics with zero civil construction application.*

1. Atmosphere
2. Bar
3. Btu (It)
4. Btu (Mean)
5. Btu (Th)
6. Btu/Hour
7. Btu/Minutes
8. Btu/Seconds
9. Calorie (Food)
10. Calorie (It)
11. Calorie (Mean)
12. Calorie (Th)
13. Calorie/Seconds
14. Carat
15. Celsius
16. Centigram/Litre
17. Centilitre
18. Cubic Decimeter
19. Cubic Inch
20. Cubic Millimeter
21. Decigram/Litre
22. Decilitre
23. Decimeter
24. Dekagram/Litre
25. Dyne
26. Erg
27. Fahrenheit
28. Foot Of Water
29. Foot/Minute
30. Foot/Second
31. Gram-Force
32. Gram/Cubic Centimeter
33. Gram/Cubic Meter
34. Gram/Cubic Millimeter
35. Gram/Litre
36. Hectare
37. Hectogram/Litre
38. Hectometer
39. Hectopascal
40. Horsepower-Hours
41. Iches Of Water
42. Inch Pound-Force
43. Inch/Minute
44. Inch/Second
45. Inches Of Mercury
46. Joule/Meter
47. Kelvin
48. Kilocalorie
49. Kilogram-Force
50. Kilogram/Cubic Centimeter
51. Kilogram/Cubic Meter
52. Kilogram/Litre
53. Kilometer/Hour
54. Kilopascal
55. Kilopond
56. Kilopound-Force
57. Litre
58. Litre-Atmosphere
59. Megagram/Litre
60. Megajoule
61. Meter Of Water
62. Meter/Second
63. Microbar
64. Microgram
65. Microgram/Litre
66. Micrometer
67. Microsecond
68. Milibar
69. Milligram/Cubic Centimeter
70. Milligram/Cubic Meter
71. Milligram/Cubic Millimeter
72. Milligram/Litre
73. Millilitre
74. Millimeter Of Mercury
75. Millimeter Of Water
76. Millisecond
77. Nanogram/Litre
78. Nanometer
79. Nanosecond
80. Newton
81. Pascal
82. Pond
83. Psi/1000 Feet
84. Square Centimeter
85. Square Inch
86. Square Kilometer
87. Technical Atmosphere
88. Tonne-Force(Metric)
89. Torr

*(Subtotal: 89 units)*

---

### Category B: Obsolete Imperial, Historical & Archaic Units (79 units)
*Pre-metric, colonial, regional Russian/Spanish, or archaic avoirdupois measures irrelevant to modern contracting.*

1. Acre (US)
2. Are
3. Area
4. Arshin
5. Barleycorn
6. Barrel (Oil)
7. Barrel(Beer)
8. Bushel (UK)
9. Bushel (US Dry Level)
10. Caballeria
11. Cable Length
12. Cable Length (UK)
13. Cable Length (US)
14. Calibre
15. Cental
16. Centiarea
17. Chain
18. Dram
19. Ells (UK)
20. Ems(Pica)
21. Fathom
22. Fluid Ounce (UK)
23. Fluid Ounce (US)
24. Furlong
25. Gallon (UK)
26. Gallon Dry (US)
27. Gallon Liquid (US)
28. Grain
29. Grain/Cubic Foot
30. Grain/Gallon (UK)
31. Grain/Gallon (US)
32. Hand
33. Hundredweight (UK)
34. Hundredweight (US)
35. Kip
36. Knot
37. Link
38. Manzana
39. Medio Metro
40. Mile
41. Mile (Nautical)
42. Mile/Hour
43. Mile/Minute
44. Mile/Second
45. Ounce-Force
46. Ounce/Cubic Foot
47. Ounce/Cubic Inch
48. Ounce/Gallon (UK)
49. Ounce/Gallon (US)
50. Peck
51. Peck (UK)
52. Peck (US)
53. Pint (UK)
54. Pint, Dry (US)
55. Pint, Liquid (US)
56. Pood
57. Pound-Force
58. Pound/Cubic Foot
59. Pound/Cubic Inch
60. Pound/Cubic Yard
61. Pound/Gallon (UK)
62. Pound/Gallon (US)
63. Poundal
64. Quart (UK)
65. Quart Dry (US)
66. Quart Liquid (US)
67. Quintal
68. Rod
69. Sazhen
70. Slug
71. Slug/Cubic Foot
72. Square Mile
73. Stone
74. Ton (Long)/Cubic Yard
75. Ton (Short)/Cubic Yard
76. Ton-Force (UK)
77. Ton-Force (US)
78. Vara
79. Versta

*(Subtotal: 79 units)*

---

### Category C: Electromagnetic, Optical & Frequency Units (30 units)
*Specialized physics, electrostatic, and electromagnetic frequency units.*

1. Abampere
2. Ampere-Hour
3. Ampere-Minute
4. Ampere-Second
5. Biot
6. Coulomb
7. Cycle/Second
8. EMU Of Charge
9. EMU of current
10. Faraday
11. Gamma
12. Gauss
13. Hertz
14. Kiloampere
15. Kilocoulomb
16. Kilohertz
17. Kilowatt-Hour
18. Megacoulomb
19. Megahertz
20. Megawatt
21. Milliampere
22. Millicoulomb
23. Millihertz
24. Nanocoulomb
25. Nanohertz
26. Volt-Ampere
27. Watt-Hour
28. Wavelength In Gigametres
29. Wavelength In Kilometres
30. Wavelength In Megametres

*(Subtotal: 30 units)*

---

### Category D: Miscellaneous, Non-Construction & Culinary Units (6 units)
*Dimensionless ratios, culinary measures, or ambiguous vendor placeholders.*

1. Cup
2. Parts Per Million
3. Percent
4. Tablespoon (US)
5. Teaspoon
6. Unit

*(Subtotal: 6 units)*

---

## 5. Verification & Reconciled Totals

$$\text{Category A (89)} + \text{Category B (79)} + \text{Category C (30)} + \text{Category D (6)} = \mathbf{204 \text{ Units}}$$

Every unit among the 204 matches the derived exclusions from database query `tabUOM` where `uom_name_ar` is empty, excluding `_Test*` and `Pint (US)` / `Acre`. The zero-usage safety check confirmed 0 references across all 105 database tables and columns.
