"""W4-8 Half A -- ``ENABLE_CATEGORY_TOKEN_FIX`` (default OFF, read per call).

``classify_category_from_text`` maps the bare synonyms ``tablet``/``tablets`` to
``electronics``, so every pharmacy "N tablets" pair (Panadol vs Adol) is
classified, priced and scored as a gadget, and on explicit_pair / vision the
NAME detection overrides a correct Supplements chip (measured at 04acb757:
``('electronics', True, 'supplements')``). The category also gates the price
path: ``electronics`` selects no pharmacy source (bolo / nasser / iHerb).

Design under test = Fable ruling R2 (recall over precision when there is no
signal): with the flag ON a ``tablet(s)`` hit is electronics UNLESS a veto fires

* a HOUSEHOLD token (descaling, dishwasher, washing machine, detergent,
  chlorine, denture, purification) -> the hit is skipped (the sweep continues;
  usually ``other``);
* else a PHARMACY signal -> ``supplements`` directly (no chip needed, no A2b):
  a dose -- design rulings R10 / R13a / R14a: a dedicated pattern, ONLY an
  explicit pharmacy unit next to a number (mg, mcg, ug, the micro sign or the
  Greek mu + g, iu, ml); GRAMS NEVER VETO, integer or decimal (next to a tablet
  a number + g/G is storage, RAM, a network generation, a Wi-Fi band or a
  G-sensor; 'tablet 1.5g' -> electronics is the stated limit; rulings R15a /
  R16a: the number starts after no letter, digit, '.' or ',', and a unit
  followed by a letter or by a digit, with or without a space, is a word or a
  model code -- 'X1.500mg', 'ML350', 'ML 350'; R16b: a model year before the MG
  car brand still reads as a dose, the stated limit W4-8g) --, a PACK count
  ``N tablets`` / ``N tabs`` (pack vocabulary adjacent -- pack, pack of,
  bottle, strip, blister, count, ct, pcs, x -- or N >= 30, a year-shaped
  1900..2099 excepted), or a pharmacy token (effervescent, chewable,
  paracetamol, ibuprofen, panadol, adol, brufen, pharmacy, laxative, antacid,
  flu, vinegar, glucose, dose, dosage -- R5's and R10's generic context
  tokens, never brand names);
* no veto -> electronics (a bare ``tablet``, every out-of-vocabulary device,
  every device string the two adversary rounds measured).

The veto applies to the ``tablet`` / ``tablets`` tokens ONLY (R10).

``_CATEGORY_SYNONYMS`` / ``canonicalize_category`` are NOT edited (pinned).
Every test sets its own flag state (the file is hermetic: the external flag
state of the run must not change any outcome). ``classify_category_llm`` is
always stubbed on ``structured_comparison_service`` (no OpenAI), the
content-safety singleton is reset, and a zero-network guard (sockets + libcurl)
fails any test that tries the network.

Labels: RED = fails at HEAD 04acb757 for the stated reason; PIN = green at HEAD
and must stay green; the KILL rows are recorded in the unit report.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import os
import socket
from pathlib import Path
from unittest.mock import patch

import pytest

import app.services.content_safety_service as css
from app.services import extraction_service as es
from app.services import price_service as ps
from app.services import source_router as sr
from app.services import structured_comparison_service as scs

FLAG = "ENABLE_CATEGORY_TOKEN_FIX"
FLAG_B = "ENABLE_BLOCKLIST_PRECISION_V2"
FIXTURES = Path(__file__).resolve().parent / "fixtures"

# The record shape of the spec, section 0 (explicit_pair branch).
SEPS = [" vs ", " VS ", " or ", " OR ", " ضد ", " أو ",
        " او ", " مقابل "]

HEAD_CORPUS_SHA = "b76fcef9a855248d72d1b7b68c14b9bf77255b51f90edbe3bfdc197c3872ec1d"
ON_CORPUS_SHA = "5b5a4b70c85ffef47ce5788e6405eb3ed5f3973656b97055deba59d7eab49e8f"
HEAD_ALL_SHA = "cac3460cd53020b681b87e41781c8ca11a6296f70925608690e2780104e8db3d"
ON_ALL_SHA = "ef29dbee204b015084fe6ee33c5fd0afb9c4b09f28b84763a6c58e42eef7b793"

PAIR_Q = "Panadol Extra 24 tablets vs Adol 500 tablets"
PAIR = ("Panadol Extra 24 tablets", "Adol 500 tablets")

# The spec's 35-row tablet probe set (probe_inputs.json, frozen here).
TABLET_PHARMACY = [
    "Panadol Extra 24 tablets vs Adol 500 tablets",
    "Panadol Extra 24 tablets",
    "Adol 500 tablets",
    "Panadol Advance 500mg 24 tablets vs Adol 500mg 24 tablets",
    "Nurofen 200mg 24 tablets vs Brufen 400mg 30 tablets",
    "Ferrous sulfate 65mg tablets vs Ferrofol capsules",
    "Claritin 10mg tablets vs Zyrtec 10mg tablets",
    "Gaviscon chewable tablets vs Rennie tablets",
    "Solpadeine effervescent tablets vs Panadol soluble tablets",
    "Strepsils lozenges vs Panadol tablets",
    "Glucophage 500mg tablets vs Metformin 500mg tablets",
    "Panadol Night 20 tablets",
    "Adol 500mg 24 tablets",
    "Panadol tablet vs Adol tablet",
    "Apple cider vinegar 60 tablets vs Goli gummies",
    "Finish Quantum dishwasher tablets vs Fairy Platinum tablets",
    "Chlorine tablets for pool vs HTH granules",
    "Vitamin C 1000mg effervescent tablets vs Redoxon",
]
TABLET_DEVICE = [
    "Samsung Galaxy Tab S10 tablet 256GB",
    "Apple iPad Air M2 tablet vs Samsung Galaxy Tab S9 tablet",
    "Lenovo Tab M10 tablet 64GB vs Huawei MatePad 11 tablet",
    "Amazon Fire HD 10 tablet vs Lenovo Tab M10",
    "Xiaomi Pad 6 tablet vs Redmi Pad SE",
    "Samsung Galaxy Tab A9 tablet",
    "Samsung tablet vs Apple tablet",
    "kids tablet 7 inch vs Fire 7 Kids tablet",
    "Microsoft Surface Pro 11 tablet vs iPad Pro 13",
    "Huawei MatePad 11.5 tablet wifi",
    "Android tablet 10 inch 128GB vs Lenovo tablet",
    "Galaxy Tab S9 FE 5G tablet",
    "Wacom One drawing tablet vs Huion Kamvas 13",
    "Kindle Fire tablet vs iPad 10th gen",
    "tablet vs laptop",
    "Samsung Galaxy Tablet S9",
    "tablet",
]
# The adversarial review's 27 out-of-vocabulary devices (R4) -- 27/27 must stay
# electronics under the flag (ruling R2).
DEVICE_OOV = [
    "Honor Pad 9 tablet", "Nokia T21 tablet", "Motorola Moto Tab G70 tablet",
    "Amazon Fire 7 tablet", "Amazon Fire HD 8 tablet vs Fire HD 10 tablet",
    "Wacom Intuos tablet", "Huion H610 Pro tablet", "XP-Pen Deco 01 tablet",
    "reMarkable 2 tablet", "Boox Note Air 3 tablet", "Teclast P85 tablet",
    "Blackview Tab 70 tablet", "Surface Go 4 tablet", "iPad 10th gen tablet",
    "Galaxy Tab S9 FE tablet", "Lenovo Tab P12 tablet", "OnePlus Pad tablet",
    "Honor Pad X9 tablet vs Redmi Pad SE tablet", "Kobo Clara tablet",
    "TCL Tab 10 tablet", "Alcatel 1T tablet", "Doogee T10 tablet",
    "Fire HD 10 Kids Pro tablet", "Apple tablet", "graphics tablet vs drawing tablet",
    "Wacom tablet vs Huion tablet", "Chuwi HiPad X tablet",
]
# Design ruling R10: EVERY device string of adversary round 1 (probe_a.py) and
# adversary round 2 (probe_a2.py), verbatim -- electronics under the flag. Each
# carries a bare integer + G (storage / RAM / network), a decimal Wi-Fi band
# (2.4G, 2.4G/5G) or a count with no pack vocabulary below 30.
DEVICE_ADV_R1 = [
    "Lenovo Tab M10 4G+64G tablet", "Android tablet 10 inch 8G RAM 128G ROM",
    "Teclast P20HD tablet 4G 64G", "Samsung Galaxy Tab A9 tablet 64G",
    "Xiaomi Pad 6 tablet 8GB 256GB", "Galaxy Tab S9 FE 5G tablet",
    "iPad 10th gen tablet 64gb wifi", "Top 10 tablets 2026", "best 5 tablets for students",
    "iPad vs Galaxy Tab: 2 tablets compared", "tablet with 12 tabs open",
    "Huawei MatePad 11.5 tablet 8G/256G", "Kids tablet 7 inch 32G",
    "Amazon Fire HD 10 tablet 32 GB", "tablet vs laptop",
    "Samsung Galaxy Tab S9 Ultra tablet 1TB 5G",
]
DEVICE_ADV_R2 = [
    "Android Tablet 8G 128G", "Teclast T50 Pro 12G 256G tablet", "Lenovo tablet 8G",
    "Tablet 10 inch 8G 256G", "Kids tablet 2.4G WiFi", "Tablet PC 10 inch 2.4G/5G WiFi",
    "Tablet 5G 2.4G dual band", "Microsoft Surface 2-in-1 tablets", "best 2 in 1 tablets",
    "compare 2 tablets", "5 tablets to buy in 2026", "10 cheap tablets for kids",
    "Top  10 tablets", "the top 3 tablets", "Top-5 tablets", "3 tablets under 500 SAR",
    "Samsung Galaxy Tab A9 tablet 4G LTE 8G", "Blackview tablet 16G RAM 256G",
    "Tablet 6G 128G", "Tablet 12G RAM 512G ROM", "Tablet 24G 512G", "tablet 1TB 12G",
    "Xiaomi Pad 6 tablet 8G 256G", "iPad tablet 2 tabs", "12 tabs open on a tablet",
    "tablet with 12 tabs opened",
]
# Adversary round 3 (probe_a3.py / probe_lookahead.py): decimal Wi-Fi bands, a
# Bluetooth version or screen size before "G-sensor", CPU clocks and decimal
# grams -- electronics under the flag (rulings R13a / R14a: grams never veto).
# Every probe string, verbatim with its ruled verdict, is in PROBE_A3_ON below.
DEVICE_ADV_R3 = [
    "Tablet 10 inch Dual WiFi 2.4G/5.0G", "Android tablet 2.4G+5.0G WiFi 6",
    "Kids tablet 5.0G WiFi", "Tablet 10.1 inch 5.0G WiFi 64GB",
    "tablet bluetooth 5.0 g-sensor", "Android tablet 10.1 G-sensor",
    "Tablet PC 7.0 G sensor", "Tablet 2.4G & 5.2G WiFi", "tablet 5.1G wifi",
    "tablet 2.45G wifi", "Tablet 2.4 G WiFi", "Tablet 2,4G WiFi",
    "tablet 5.8g", "tablet 5.80g", "tablet 2.40 g",
    "Android tablet Octa-Core 2.0GHz 4GB 64GB", "tablet 10.5 inch 1.5 GHz",
    "Tablet 10.1 inch 1.6GHz quad core", "Kids tablet 2.0 GHz 32GB",
]
# Device rows that guard a specific R10 boundary (each is a KILL row):
DEVICE_GUARDS = [
    "Lenovo Tab M10 4G tablet",          # grams never veto (R13a / R14a): an integer G
    "Lenovo Tab M10 4 G tablet",         # ... with a space either
    "Tablet 1G RAM 8G ROM",              # ... (named by R14a)
    "Redmi Pad SE tablet 6G 128G", "Kids tablet 16G",
    "Android tablet 128G", "Android tablet 256G", "Android tablet 512G",
    "Android tablet 8G RAM", "Android tablet 8G ROM", "Teclast T40 tablet 8G+128G",
    "Tablet 5.8G band",                  # ... nor a decimal G of any value
    "Tablet 2.0G",                       # ... (named by R14a)
    "Android tablet 1.5GB RAM 16GB",     # ... nor a decimal GB
    "Tablet model X1.5G",                # ... nor a model code
    "tablet 1,5g",                       # ... nor a decimal comma
    "Tablet model X500mg",               # a number glued to a letter is a model code,
                                         # not a dose (the unit pattern's lookbehind)
    "Tablet model X1.500mg",             # ... a decimal too: nothing starts after a
    "Tablet X2,500mg",                   # '.' or ',' (ruling R15a; adversary r5)
    "tablet 2 ugreen stand",             # a unit followed by a letter is a word
                                         # (the lookahead; adversary r3 probe_a3)
    "Mercedes 2015 ML350 tablet holder",  # a unit followed by a digit is a model
    "2012 ML 350 tablet mount",           # code, with or without a space (R16a;
    "2012 ML  350 tablet mount",          # ... or ANY whitespace: two spaces / a tab
    "2012 ML\t350 tablet mount",          # (Fable, after adversary r7 mutant
                                          # A7_lookahead_digit_single_space)
    "tablet 500mg2",                      # adversaries r5 / r6)
    "2024 MG4 tablet screen protector",   # ... the MG4 form too (R16a; see R16b)
    "Samsung Galaxy Tab S10 tablets",    # count needs a free-standing number
    "Teclast T40 tablets",               # ... a model number is not a count >= 30
    "Huawei MatePad 11.5 tablets",       # "11.5 tablets" is not a count
    "Huawei MatePad 11.5 tablets pack",  # ... not even next to pack vocabulary
    "Kids tablet 30 tabsets",            # 'tabs' must end the word
    "tablets",                            # bare plural, no signal
    "10 tablets",                         # R10: a bare count under 30 is no signal
    "2 tablets", "29 tablets",            # the >= 30 bound
    "best 2026 tablets",                  # a year-shaped count is not >= 30
    "1900 tablets", "2099 tablets",       # ... the year window's bounds
    # Pack vocabulary is matched as whole words, adjacent to the count:
    "Galaxy 10 tablets", "fox 10 tablets", "Duct 10 tablets", "discount 20 tablets",
    "backpack 10 tablets", "10 tablets xl",
    "USB charging strip for 2 tablets",   # a pack word elsewhere is not adjacent
    "2 tablets with charging strip",
    # Whole-token context matching (a substring match would veto these):
    "Samsung tablet for indenture paperwork",   # 'denture' inside a word
    "Kids tablet for adolescents",              # 'adol' inside a word
    "Galaxy tablet with fluid AMOLED display",  # 'flu' inside a word
    "Samsung Galaxy tablet 3 tabsets",          # 'tabs' inside a word
]
# R10: the veto applies to the tokens 'tablet' / 'tablets' ONLY -- another
# electronics synonym carrying a pharmacy / household signal stays electronics.
VETO_SCOPE_ROWS = ["pharmacy laptop", "Samsung laptop 500mg", "laptop for dishwasher repair"]
# Stated limit (rulings R13a / R14a, pinned so a change is deliberate): GRAMS
# NEVER VETO -- a gram-denominated tablet dose, integer or decimal, with no
# other pharmacy signal stays electronics under the flag ('tablet 1.5g' is the
# ruled limit row; 'Glucose 4g tablets' is caught by the glucose token, the same
# string minus 'glucose' is the limit; 'metformin' is not a pharmacy token).
STATED_LIMIT_ROWS = ["tablet 1.5g", "tablet 0.5 g", "tablet 1.9g", "4g tablets",
                     "Dextrose 4g tablets", "Metformin 1g tablets", "Metformin 0.5g tablets",
                     "Aspirin 2.4g tablets"]
# Stated limit (ruling R16b, W4-8g, NO carve-out): a car model year before the MG
# brand reads as a milligram dose under the flag (no rule separates it from a
# real '2000 mg tablets' without a new carve-out chain). Electronics OFF,
# supplements ON -- pinned in both states so the limit is measured.
STATED_LIMIT_CAR_BRAND = ["2023 MG ZS tablet holder", "tablet mount for 2021 MG HS"]
# Measured consequence of ruling R16a (a unit followed by a digit, with or without
# a space, is a model code): a dose followed by a pack number no longer vetoes on
# the dose rung, so a string with no pharmacy token and a count under 30 stays
# electronics under the flag (the flag-OFF verdict). Pinned so a change is
# deliberate; its pair / token / >= 30 forms still veto (TABLET_PHARMACY).
STATED_LIMIT_DOSE_THEN_NUMBER = ["Nurofen 200mg 24 tablets", "Ferrous sulfate 65mg 28 tablets",
                                 "Thyroxine 50mcg 28 tablets"]
MICRO = chr(0x00B5)   # the micro sign
MU = chr(0x03BC)      # the Greek small mu
# Adversary r3 probe_a3.py + probe_lookahead.py and adversary r4 probe_r13.py,
# EVERY string verbatim with its verdict under the flag (rulings R13a / R14a):
# every device string -> electronics (grams never veto); the unit rows and the
# R10 pack-count / pharmacy-token rows -> their ruled verdict.
PROBE_A3_ON = [
    ("Tablet 10 inch Dual WiFi 2.4G/5.0G", "electronics"),
    ("Android tablet 2.4G+5.0G WiFi 6", "electronics"),
    ("Kids tablet 5.0G WiFi", "electronics"),
    ("Tablet 10.1 inch 5.0G WiFi 64GB", "electronics"),
    ("tablet bluetooth 5.0 g-sensor", "electronics"),
    ("Android tablet 10.1 G-sensor", "electronics"),
    ("Tablet PC 7.0 G sensor", "electronics"),
    ("Tablet 2.4G & 5.2G WiFi", "electronics"),
    ("tablet 5.1G wifi", "electronics"),
    ("tablet 2.45G wifi", "electronics"),
    ("Tablet 2.4 G WiFi", "electronics"),
    ("Tablet 2,4G WiFi", "electronics"),
    ("Samsung Galaxy Tab 2 tablets x 128GB", "supplements"),
    ("iPad Air 2 tablets pcs", "supplements"),
    ("Bundle 2 tablets count", "supplements"),
    ("Fire HD 10 Kids 2 tablets pack", "supplements"),
    ("Amazon Fire 7 tablets 2-pack", "electronics"),
    ("2 pack Fire 7 tablets", "electronics"),
    ("Fire HD 8 tablets 3 pack", "electronics"),
    ("pack of 2 kids tablets", "electronics"),
    ("2 x Samsung tablets", "electronics"),
    ("compare 30 tablets 2026", "supplements"),
    ("32 tablets", "supplements"),
    ("Tablet 1920x1200 2 tablets", "electronics"),
    ("lenovo tablets 64 tabs open", "supplements"),
    ("Tablet 10 inch 6000 mAh", "electronics"),
    ("tablet 8mp camera", "electronics"),
    ("tablet 2 ugreen stand", "electronics"),
    ("Tablet 4 ml", "supplements"),
    ("tablet stylus 1.5mm tip", "electronics"),
    ("tablet 10.5 inch 1.5 GHz", "electronics"),
    ("Tablet 0.5G", "electronics"),
    ("tablet 5.8g", "electronics"),
    ("tablet 5.80g", "electronics"),
    ("tablet 2.40 g", "electronics"),
    ("Paracetamol 500mg tablets", "supplements"),
    ("tablet 1.5g", "electronics"),
    ("Glucose 4g tablets", "supplements"),
    ("4g tablets", "electronics"),
    ("Vitamin C 1000 IU tablets", "supplements"),
    ("pack of 10 tablets", "supplements"),
    ("30 tablets", "supplements"),
    ("10 tablets", "electronics"),
    ("Vitamin D3 1000iu tablets", "supplements"),
    ("Vitamin B12 500mcg tablets", "supplements"),
    ("Folic acid 400 ug tablets", "supplements"),
    ("Metformin 0.5g tablets", "electronics"),
    ("Aspirin 2.4g tablets", "electronics"),
    ("Salt tablets 5.8g", "electronics"),
    ("Tablet 1,000 IU", "supplements"),
    ("Omega 3 1.2g tablets", "supplements"),
    ("Calcium 1.0g tablets", "supplements"),
    ("ibuprofen 400mg 24 tablets", "supplements"),
    ("24 tablets per pack", "supplements"),
    ("Vitamin C tablets x 20", "supplements"),
    ("x20 tablets", "electronics"),
    ("20x tablets", "supplements"),
    ("20 tablets strip", "supplements"),
    ("blister of 10 tablets", "supplements"),
    ("strip 10 tablets", "supplements"),
    ("10 tablets per strip", "supplements"),
    ("Finish dishwasher tablets", "other"),
    ("Galaxy Tab S9 tablet flu season", "supplements"),
    ("tablet dose tracker app", "supplements"),
    ("tablet glucose monitor app", "supplements"),
    ("iPad tablet for pharmacy POS", "supplements"),
    ("Android tablet Octa-Core 2.0GHz 4GB 64GB", "electronics"),
    ("Tablet 10.1 inch 1.6GHz quad core", "electronics"),
    ("Kids tablet 2.0 GHz 32GB", "electronics"),
]
PROBE_R13_ON = [
    ("tablet 1.5g", "electronics"),
    ("Glucose 4g tablets", "supplements"),
    ("4g tablets", "electronics"),
    ("Paracetamol 500mg tablets", "supplements"),
    ("Claritin 10mg tablets vs Zyrtec 10mg tablets", "supplements"),
    ("Vitamin C 1000 IU tablets", "supplements"),
    ("Tablet 10 inch Dual WiFi 2.4G/5.0G", "electronics"),
    ("Android tablet 2.4G+5.0G WiFi 6", "electronics"),
    ("Kids tablet 5.0G WiFi", "electronics"),
    ("Tablet 10.1 inch 5.0G WiFi 64GB", "electronics"),
    ("Tablet 2.4G & 5.2G WiFi", "electronics"),
    ("tablet 5.1G wifi", "electronics"),
    ("tablet 2.45G wifi", "electronics"),
    ("tablet bluetooth 5.0 g-sensor", "electronics"),
    ("Android tablet 10.1 G-sensor", "electronics"),
    ("Tablet PC 7.0 G sensor", "electronics"),
    ("Android tablet Octa-Core 2.0GHz 4GB 64GB", "electronics"),
    ("tablet 10.5 inch 1.5 GHz", "electronics"),
    ("Tablet 10.1 inch 1.6GHz quad core", "electronics"),
    ("Kids tablet 2.0 GHz 32GB", "electronics"),
    ("Tablet 0.5G", "electronics"),
    ("Tablet 2.4 G WiFi", "electronics"),
    ("Tablet 2,4G WiFi", "electronics"),
    ("tablet 5.8g", "electronics"),
    ("Android tablet 1.5G RAM 16G ROM", "electronics"),
    ("Tablet quad core 1.3G", "electronics"),
    ("Kids tablet 1.0G RAM 8G storage", "electronics"),
    ("Tablet 7 inch 1.2G CPU", "electronics"),
    ("Tablet 1.8G octa core 4G LTE", "electronics"),
    ("tablet bluetooth 1.2 g-sensor", "electronics"),
    ("Android tablet 0.3MP front camera 1.5G quad-core", "electronics"),
    ("Vitamin D 25" + MICRO + "g tablets", "supplements"),
    ("Vitamin B12 500 " + MU + "g tablets", "supplements"),
]
PROBE_ROWS = sorted(dict(PROBE_A3_ON + PROBE_R13_ON).items())
# ... with the flag OFF, the rows is_supplement_query already answers (a
# vitamin / nutrient token) are supplements, every other row electronics.
PROBE_OFF_SUPPLEMENTS = sorted({
    "Vitamin C 1000 IU tablets", "Vitamin D3 1000iu tablets", "Vitamin B12 500mcg tablets",
    "Folic acid 400 ug tablets", "Omega 3 1.2g tablets", "Calcium 1.0g tablets",
    "Vitamin C tablets x 20", "Vitamin D 25" + MICRO + "g tablets",
    "Vitamin B12 500 " + MU + "g tablets"})
# The review's 25 extra pharmacy / household strings, after red-gate ruling R5's
# six generic context tokens: 14 -> supplements, 8 -> other (household), 3 stay
# electronics (brand-only strings with no generic token -- the stated R2/R5
# recall-over-precision limit, pinned below so a vocabulary edit is measured).
PX_SUPPLEMENTS = [
    "Panadol Kids tablets", "Adol Kids tablets vs Panadol Kids tablets",
    "Panadol Cold and Flu tablets", "Profinal 400 tablets", "Fevadol 500mg tablets",
    "Voltaren 50 tablets", "Brufen tablets vs Profinal tablets",
    "Panadol Night tablets", "Nothing but Panadol tablets",
    "Zyrtec 10 mg 30 tablets", "Adol 500 mg tablets",
    "Panadol Extra Optizorb 48 tablets", "Diclofenac 50mg x 20 tablets",
    "Apple cider vinegar tablets",                       # R5: 'vinegar'
]
PX_HOUSEHOLD = [
    "Samsung washing machine cleaning tablets", "LG washing machine tub clean tablets",
    "Dyson descaling tablets", "Nespresso descaling tablets",
    "Pool chlorine tablets 200g", "Bosch dishwasher tablets vs Finish tablets",
    "Steradent denture tablets vs Polident tablets",     # R5: 'denture'
    "Aquatabs water purification tablets",               # R5: 'purification'
]
PX_NO_SIGNAL = [
    "Dulcolax tablets", "Imodium tablets vs Motilium tablets",
    "Beechams Max Strength tablets",
]
# One row per veto entry: only that entry fires on the row, so deleting the
# entry (or reordering the rungs) changes exactly this row (KILL rows).
VETO_ENTRY_ROWS = [
    # R10 / R13a / R14a dose rung: each unit (both micro spellings too), with a
    # token-free product so the unit alone decides; a unit anywhere in the text
    # vetoes, also beside a device band. No gram row: grams never veto.
    ("dose_mg", "Claritin 10mg tablets vs Zyrtec 10mg tablets", "supplements"),
    ("dose_mcg", "Thyroxine 50mcg tablets", "supplements"),
    ("dose_ug", "Thyroxine 50 ug tablets", "supplements"),
    ("dose_micro_sign_ug", "tablet 5 " + MICRO + "g", "supplements"),
    ("dose_greek_mu_ug", "tablet 5 " + MU + "g", "supplements"),
    ("dose_iu", "Generic 1000 IU tablets", "supplements"),
    ("dose_ml", "Gaviscon 10ml tablets", "supplements"),
    ("dose_unit_beside_device_band", "Tablet 2.4G WiFi 500mg tablets", "supplements"),
    # Ruling R15a: the number may carry a decimal point (the decimal group is
    # load-bearing now that nothing starts after a '.'); R16a: 'tablet 500mg' and
    # 'tablet 2 ml' are unchanged by the digit exclusion after the unit.
    ("dose_decimal_point", "tablet 1.5mg", "supplements"),
    ("dose_decimal_point_space", "tablet 0.25 mg", "supplements"),
    ("dose_integer", "tablet 500mg", "supplements"),
    ("dose_ml_at_end", "tablet 2 ml", "supplements"),
    # Ruling R16d: any whitespace between the number and the unit.
    ("dose_two_spaces", "tablet 500  mg", "supplements"),
    ("dose_tab", "tablet 500\tmg", "supplements"),
    ("dose_no_break_space", "tablet 500" + chr(0x00A0) + "mg", "supplements"),
    # R10 count rung: pack vocabulary adjacent, or N >= 30 (a year excepted).
    ("count_30", "30 tablets", "supplements"),
    ("count_tabs_30", "Zyrtec 30 tabs vs Claritin tablets", "supplements"),
    ("count_1899_below_year_window", "1899 tablets", "supplements"),
    ("count_2100_above_year_window", "2100 tablets", "supplements"),
    ("count_pack_overrides_year_window", "bottle of 2000 tablets", "supplements"),
    ("count_pack_of", "pack of 10 tablets", "supplements"),
    ("count_pack_after", "10 tablets pack", "supplements"),
    ("count_pack_between", "10 pack tablets", "supplements"),
    ("count_bottle_of", "bottle of 20 tablets", "supplements"),
    ("count_strip_of", "strip of 10 tablets", "supplements"),
    ("count_per_strip", "10 tablets per strip", "supplements"),
    ("count_blister", "blister 10 tablets", "supplements"),
    ("count_count", "10 count tablets", "supplements"),
    ("count_ct", "10ct tablets", "supplements"),
    ("count_pcs", "10 pcs tablets", "supplements"),
    ("count_x_before", "3 x 10 tablets", "supplements"),
    ("count_x_after", "10 tablets x 3", "supplements"),
    ("count_tablets", "Apple cider vinegar 60 tablets vs Goli gummies", "supplements"),
    ("descaling", "Dyson descaling tablets", "other"),
    ("dishwasher", "Finish Quantum dishwasher tablets vs Fairy Platinum tablets", "other"),
    ("washing_machine", "Samsung washing machine cleaning tablets", "other"),
    ("detergent", "Persil detergent tablets vs Ariel detergent tablets", "other"),
    ("chlorine", "Chlorine tablets for pool vs HTH granules", "other"),
    # A household token wins over a dose and over a pack count (R1 rung order).
    ("household_precedes_dose", "Aquatabs water purification tablets 8.5mg", "other"),
    ("household_precedes_count", "Finish Quantum dishwasher 60 tablets", "other"),
    # Ruled semantics: a household token SKIPS the tablet hit and the sweep
    # continues to the next (shorter) synonym -- here 'food' -> grocery.
    ("household_sweep_continues", "Finish dishwasher tablets for food residue", "grocery"),
    # R1/R5: a household token wins over a pharmacy token (a denture cleaner is
    # effervescent, not a supplement).
    ("household_precedes_pharmacy_token", "Steradent denture effervescent tablets", "other"),
    ("effervescent", "Solpadeine effervescent tablets", "supplements"),
    ("chewable", "Gaviscon chewable tablets vs Rennie tablets", "supplements"),
    ("paracetamol", "Paracetamol tablets", "supplements"),
    ("ibuprofen", "Ibuprofen tablets", "supplements"),
    ("panadol", "Panadol Kids tablets", "supplements"),
    ("adol", "Adol Extra tablets", "supplements"),
    ("brufen", "Brufen tablets vs Profinal tablets", "supplements"),
    ("pharmacy", "Boots pharmacy sleep aid tablets", "supplements"),
    ("veto_precedes_electronics_brand", "Nothing but Panadol tablets", "supplements"),
    # Red-gate ruling R5: six generic context tokens, one row each.
    ("denture", "Steradent denture tablets vs Polident tablets", "other"),
    ("purification", "Aquatabs water purification tablets", "other"),
    ("laxative", "Dulcolax laxative tablets", "supplements"),
    ("antacid", "Rennie antacid tablets", "supplements"),
    ("flu", "Beechams cold and flu tablets", "supplements"),
    ("vinegar", "Apple cider vinegar tablets", "supplements"),
    # Design ruling R10: three more generic tokens, one row each.
    ("glucose", "Glucose 4g tablets", "supplements"),
    ("dose", "Aspirin low dose tablets", "supplements"),
    ("dosage", "Aspirin tablets dosage", "supplements"),
]
# The rows design rulings R10 / R13a / R14a name, verbatim (flag ON); R13a
# withdrew R10's 'tablet 1.5g -> supplements' -- it is the electronics limit row.
R10_RULED_ROWS = [
    ("Paracetamol 500mg tablets", "supplements"),
    ("Claritin 10mg tablets vs Zyrtec 10mg tablets", "supplements"),
    ("tablet 1.5g", "electronics"),
    ("Glucose 4g tablets", "supplements"),
    ("4g tablets", "electronics"),
    ("Vitamin C 1000 IU tablets", "supplements"),
    ("pack of 10 tablets", "supplements"),
    ("30 tablets", "supplements"),
    ("10 tablets", "electronics"),
]
PHARMACY_ROWS = sorted(set(TABLET_PHARMACY[0:15] + PX_SUPPLEMENTS))
HOUSEHOLD_ROWS = sorted(set(TABLET_PHARMACY[15:17] + PX_HOUSEHOLD
                            + ["Persil detergent tablets vs Ariel detergent tablets"]))
DEVICE_ROWS = sorted(set(TABLET_DEVICE + DEVICE_OOV + DEVICE_ADV_R1 + DEVICE_ADV_R2
                         + DEVICE_ADV_R3 + DEVICE_GUARDS))
ON_RECORD_C_SUPPLEMENTS_05 = {
    "chip": ["supplements", False, None], "chip_is_supp": [True, True],
    "det": "supplements", "halves": ["supplements", "other"],
    "nochip": ["supplements", False, None], "nochip_is_supp": [True, True],
}


# --------------------------------------------------------------------- fixtures

_LOOPBACK = {"127.0.0.1", "::1", "localhost", "0.0.0.0", "", None}


def _host_of(address):
    host = address[0] if isinstance(address, tuple) and address else address
    return host.decode("ascii", "replace") if isinstance(host, bytes) else host


@pytest.fixture(autouse=True)
def _zero_network(monkeypatch):
    """Refuse and record every non-loopback socket / DNS / libcurl attempt."""
    attempts = []
    real_connect = socket.socket.connect
    real_connect_ex = socket.socket.connect_ex
    real_getaddrinfo = socket.getaddrinfo

    def guard_connect(self, address):
        host = _host_of(address)
        if host not in _LOOPBACK:
            attempts.append(("connect", host))
            raise OSError("W4-8 zero-network guard: blocked connect to %r" % (host,))
        return real_connect(self, address)

    def guard_connect_ex(self, address):
        host = _host_of(address)
        if host not in _LOOPBACK:
            attempts.append(("connect_ex", host))
            raise OSError("W4-8 zero-network guard: blocked connect_ex to %r" % (host,))
        return real_connect_ex(self, address)

    def guard_getaddrinfo(host, *args, **kwargs):
        name = _host_of(host)
        if name not in _LOOPBACK:
            attempts.append(("getaddrinfo", name))
            raise socket.gaierror("W4-8 zero-network guard: blocked getaddrinfo(%r)" % (name,))
        return real_getaddrinfo(host, *args, **kwargs)

    monkeypatch.setattr(socket.socket, "connect", guard_connect)
    monkeypatch.setattr(socket.socket, "connect_ex", guard_connect_ex)
    monkeypatch.setattr(socket, "getaddrinfo", guard_getaddrinfo)

    import curl_cffi.requests as curl_requests

    def curl_guard(*args, **kwargs):
        attempts.append(("curl_cffi", str(args[:2])))
        raise RuntimeError("W4-8 zero-network guard: blocked curl_cffi request")

    monkeypatch.setattr(curl_requests, "get", curl_guard)
    monkeypatch.setattr(curl_requests.Session, "request", curl_guard)
    monkeypatch.setattr(curl_requests.AsyncSession, "request", curl_guard)
    yield
    assert not attempts, "W4-8 zero-network guard: the test attempted network I/O: %r" % (attempts,)


@pytest.fixture(autouse=True)
def _hermetic_env(monkeypatch):
    """Both W4-8 flags start UNSET in every test; each test sets its own state."""
    monkeypatch.delenv(FLAG, raising=False)
    monkeypatch.delenv(FLAG_B, raising=False)
    monkeypatch.setattr(css, "_service", None)
    yield


@pytest.fixture(autouse=True)
def a2b(monkeypatch):
    """The A2b classifier never reaches OpenAI: a counting stub (default answer
    'other', what A2b degrades to on failure)."""
    state = {"n": 0, "answer": "other"}

    async def _stub(names):
        state["n"] += 1
        return state["answer"]

    monkeypatch.setattr(scs, "classify_category_llm", _stub)
    return state


def _flag(monkeypatch, value, name=FLAG):
    if value is None:
        monkeypatch.delenv(name, raising=False)
    else:
        monkeypatch.setenv(name, value)


def _run(coro):
    """A private loop: never touches the thread's current event loop."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.run_until_complete(loop.shutdown_asyncgens())
        loop.close()


def _split(q):
    for s in SEPS:
        if s in q:
            a, b = q.split(s, 1)
            return a.strip(), b.strip()
    return q.strip(), ""


def _products(q):
    from app.utils.prompt_sanitizer import sanitize_prompt_input
    out = []
    for raw in [x for x in _split(q) if x][:2]:
        safe = sanitize_prompt_input(raw, max_length=80)
        out.append({"brand": "", "name": safe, "variant": None,
                    "category": es.classify_category_from_text(safe),
                    "search_query": safe, "_explicit": True})
    return out


async def _record(q, chip):
    products = _products(q)
    combined = " ".join(p["search_query"] for p in products)
    rec = {"det": es.classify_category_from_text(combined),
           "halves": [p["category"] for p in products]}
    for label, sel in (("chip", chip), ("nochip", None)):
        used, switched, orig = await scs._resolve_pair_category(products, sel, parser_path=False)
        rec[label] = [used, bool(switched), orig]
        rec[label + "_is_supp"] = [
            bool((used == "supplements")
                 or (used in ("other", None) and ps.is_supplement_query(p["search_query"])))
            for p in products
        ]
    return rec


def _records(keyed):
    """Build the records of {key: (query, chip)} on ONE private event loop."""
    async def _all():
        return {k: await _record(q, chip) for k, (q, chip) in keyed.items()}
    return _run(_all())


def _canon_sha(obj):
    return hashlib.sha256(json.dumps(obj, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":")).encode("utf-8")).hexdigest()


def _load(name):
    with open(FIXTURES / name, encoding="utf-8") as fh:
        return json.load(fh)


def _corpus_records():
    rows = _load("category_corpus_gcc_360.json")["rows"]
    return _records({"C:%s:%02d" % (r["truth"], r["idx"]): (r["query"], r["truth"])
                     for r in rows})


def _tablet_records():
    keyed = {"TP:%02d" % i: (q, "supplements") for i, q in enumerate(TABLET_PHARMACY)}
    keyed.update({"TD:%02d" % i: (q, "electronics") for i, q in enumerate(TABLET_DEVICE)})
    return _records(keyed)


def _capture(path, chip):
    svc = scs.get_comparison_service()
    cap = []

    async def fake_fetch(product_info, *a, **k):
        cap.append(product_info.get("category"))
        raise RuntimeError("stop after capture")

    async def drive():
        if path == "sync":
            try:
                await svc.compare_from_text(query=PAIR_Q, explicit_pair=PAIR, selected_category=chip)
            except Exception:
                pass
        else:
            agen = svc.compare_from_text_streaming(query=PAIR_Q, explicit_pair=PAIR,
                                                   selected_category=chip)
            try:
                async for _ in agen:
                    pass
            except Exception:
                pass

    with patch.object(svc, "_fetch_product_data", side_effect=fake_fetch):
        _run(drive())
    return cap


def _reader():
    fn = getattr(es, "category_token_fix_enabled", None)
    assert fn is not None, (
        "extraction_service.category_token_fix_enabled() does not exist -- the "
        "W4-8 Half A per-call flag reader is absent")
    return fn


# ------------------------------------------------------------------------ tests

@pytest.mark.parametrize("value,expected", [
    (None, False), ("", False), ("false", False), ("0", False), ("no", False),
    ("off", False), ("true", True), ("TRUE", True), (" true ", True), ("1", True),
    ("yes", True), ("on", True), ("On", True),
])
def test_flag_reader_default_off_and_truthy_forms(monkeypatch, value, expected):
    """RED (1): the reader does not exist at HEAD. Default OFF; the repo's
    truthy set, case- and whitespace-insensitive (.strip().lower())."""
    reader = _reader()
    _flag(monkeypatch, value)
    assert reader() is expected


@pytest.mark.parametrize("query", PHARMACY_ROWS)
def test_pharmacy_tablets_not_electronics_flag_on(monkeypatch, query):
    """RED (2): with the flag ON a pharmacy veto (dose / plural count / pharmacy
    token) sends a tablets row to supplements directly (ruling R2); HEAD returns
    electronics for every row (measured)."""
    _flag(monkeypatch, "true")
    assert es.classify_category_from_text(query) == "supplements", query


@pytest.mark.parametrize("query", HOUSEHOLD_ROWS)
def test_household_tablets_not_electronics_flag_on(monkeypatch, query):
    """RED (2b): a household token skips the tablet hit -> other (not
    supplements, not electronics). HEAD: electronics."""
    _flag(monkeypatch, "true")
    assert es.classify_category_from_text(query) == "other", query


@pytest.mark.parametrize("entry,query,expected", VETO_ENTRY_ROWS,
                         ids=[r[0] for r in VETO_ENTRY_ROWS])
def test_each_veto_entry_is_load_bearing_flag_on(monkeypatch, entry, query, expected):
    """RED (2c): one row per veto entry (ruling R2: each entry pinned by its own
    row or dropped; 'vitamin' / 'supplement' were dropped -- is_supplement_query
    and the longer 'supplement' synonym answer first, so they never reach the
    veto). Also pins household-before-dose and veto-before-electronics-brand.
    HEAD: electronics for every row."""
    _flag(monkeypatch, "true")
    assert es.classify_category_from_text(query) == expected, (entry, query)


@pytest.mark.parametrize("value,b_flag", [(None, None), ("false", None), ("0", None),
                                          (None, "true")])
def test_pharmacy_tablets_flag_off_identity(monkeypatch, value, b_flag):
    """PIN (3): flag unset / 'false' / '0' (and with the blocklist flag ON):
    every pharmacy, household and veto row classifies exactly as at HEAD."""
    _flag(monkeypatch, value)
    _flag(monkeypatch, b_flag, FLAG_B)
    rows = PHARMACY_ROWS + HOUSEHOLD_ROWS + [r[1] for r in VETO_ENTRY_ROWS] + PX_NO_SIGNAL
    got = {q: es.classify_category_from_text(q) for q in rows}
    assert got == {q: "electronics" for q in rows}


@pytest.mark.parametrize("value", [None, "true"])
@pytest.mark.parametrize("query", DEVICE_ROWS)
def test_device_tablets_stay_electronics(monkeypatch, value, query):
    """PIN (4): every device row -- the spec's 17, the review's 27
    out-of-vocabulary devices (27/27 required by R2), every device string of
    adversary rounds 1-3 (design rulings R10 / R13a) and the boundary guards
    (integer and decimal G, Wi-Fi bands, a model code, a unit followed by a
    letter, counts without pack vocabulary under 30, a year-shaped count,
    whole-word pack vocabulary) -- stays electronics with the flag OFF and ON.
    Kills the naive drop (M1), an 'other' default for an uncorroborated tablet,
    any gram dose and a count without the pack / >= 30 rule."""
    _flag(monkeypatch, value)
    assert es.classify_category_from_text(query) == "electronics", query


@pytest.mark.parametrize("query,expected", R10_RULED_ROWS)
def test_r10_ruled_rows_flag_on(monkeypatch, query, expected):
    """RED (design rulings R10 / R13a, verbatim rows): mg and IU are doses, a
    gram never is ('tablet 1.5g' is the R13a limit row), the glucose token
    catches 'Glucose 4g tablets' while its token-less twin '4g tablets' is the
    stated limit, 'pack of 10' and '30' are pack counts, a bare '10 tablets' is
    no signal."""
    _flag(monkeypatch, "true")
    assert es.classify_category_from_text(query) == expected, query


@pytest.mark.parametrize("value", [None, "true"])
@pytest.mark.parametrize("query", VETO_SCOPE_ROWS)
def test_veto_applies_to_tablet_tokens_only(monkeypatch, value, query):
    """PIN (R10): the veto runs on the 'tablet' / 'tablets' hit only -- a laptop
    string carrying a pharmacy token, a dose or a household token stays
    electronics in both states (a veto on every electronics synonym reddens)."""
    _flag(monkeypatch, value)
    assert es.classify_category_from_text(query) == "electronics", query


@pytest.mark.parametrize("value", [None, "true"])
@pytest.mark.parametrize("query", PX_NO_SIGNAL)
def test_no_signal_pharmacy_rows_stay_electronics(monkeypatch, value, query):
    """PIN (4b): the 3 of the review's 25 pharmacy/household strings with no veto
    signal (brand-only: Dulcolax, Imodium/Motilium, Beechams Max Strength) stay
    electronics in both states -- the measured R2/R5 precision cost (ruling R5:
    never brand names), pinned so a vocabulary change is a visible, deliberate
    edit."""
    _flag(monkeypatch, value)
    assert es.classify_category_from_text(query) == "electronics", query


@pytest.mark.parametrize("value", [None, "true"])
@pytest.mark.parametrize("query", STATED_LIMIT_ROWS)
def test_stated_limit_gram_doses_stay_electronics(monkeypatch, value, query):
    """PIN (stated limit, design rulings R13a / R14a): GRAMS NEVER VETO -- a
    gram-denominated tablet dose, integer or decimal ('tablet 1.5g', the ruled
    limit row), with no other pharmacy signal stays electronics in both states
    (next to a tablet a number + g is storage / RAM / a network generation / a
    Wi-Fi band / a G-sensor); follow-up W4-8e."""
    _flag(monkeypatch, value)
    assert es.classify_category_from_text(query) == "electronics", query


@pytest.mark.parametrize("value", [None, "true"])
@pytest.mark.parametrize("query", STATED_LIMIT_CAR_BRAND)
def test_stated_limit_car_year_before_mg_reads_as_dose(monkeypatch, value, query):
    """PIN (stated limit, ruling R16b, follow-up W4-8g): a car-accessory string
    naming the MG brand after a model year reads '2023 mg' as a dose --
    electronics with the flag OFF, supplements with it ON (no carve-out)."""
    _flag(monkeypatch, value)
    expected = "supplements" if value == "true" else "electronics"
    assert es.classify_category_from_text(query) == expected, query


@pytest.mark.parametrize("value", [None, "true"])
@pytest.mark.parametrize("query", STATED_LIMIT_DOSE_THEN_NUMBER)
def test_stated_limit_dose_followed_by_a_number_is_not_a_dose(monkeypatch, value, query):
    """PIN (measured consequence of ruling R16a): a unit followed by a digit,
    with or without a space, is a model code, so '200mg 24 tablets' does not
    veto on the dose rung; with no pharmacy token and a count under 30 the
    string stays electronics in both states."""
    _flag(monkeypatch, value)
    assert es.classify_category_from_text(query) == "electronics", query


@pytest.mark.parametrize("query,expected", PROBE_ROWS, ids=[str(i) for i in range(len(PROBE_ROWS))])
def test_adversary_r3_r4_probe_strings_verbatim(monkeypatch, query, expected):
    """PIN (rulings R13a / R14a): every string of adversary r3's probe_a3.py /
    probe_lookahead.py and adversary r4's probe_r13.py, verbatim -- every device
    string ('Tablet 0.5G', '1.5G RAM 16G ROM', 'quad core 1.3G', '1.2 g-sensor',
    the decimal Wi-Fi bands, the GHz clocks) is electronics under the flag, the
    unit / pack-count / pharmacy-token rows keep their ruled verdict; flag OFF
    every row classifies as at HEAD."""
    off = "supplements" if query in PROBE_OFF_SUPPLEMENTS else "electronics"
    assert es.classify_category_from_text(query) == off, query
    _flag(monkeypatch, "true")
    assert es.classify_category_from_text(query) == expected, query


@pytest.mark.parametrize("query", ["tablet", "tablets", "tablet vs laptop"])
def test_bare_tablet_defaults_to_electronics_flag_on(monkeypatch, query):
    """PIN (5, reversed by ruling R2): a bare tablet with no signal either way is
    ELECTRONICS under the flag (the spec's 'other' default is rejected)."""
    _flag(monkeypatch, "true")
    assert es.classify_category_from_text(query) == "electronics"


@pytest.mark.parametrize("value", [None, "true"])
@pytest.mark.parametrize("query", ["Centrum Multivitamin tablets",
                                   "Vitamin C 1000mg effervescent tablets vs Redoxon"])
def test_supplement_precedence_unchanged(monkeypatch, value, query):
    """PIN (6): is_supplement_query still answers before the sweep."""
    _flag(monkeypatch, value)
    assert es.classify_category_from_text(query) == "supplements"


@pytest.mark.parametrize("value", [None, "true"])
def test_canonicalize_tablet_untouched(monkeypatch, value):
    """PIN (7): the LLM parser's free-form 'Tablets' category still
    canonicalises to electronics (_CATEGORY_SYNONYMS is not edited)."""
    _flag(monkeypatch, value)
    assert es.canonicalize_category("tablet") == "electronics"
    assert es.canonicalize_category("Tablets") == "electronics"


def test_resolver_honours_supplements_chip_flag_on(monkeypatch, a2b):
    """RED (8): pharmacy pair + Supplements chip -> ('supplements', False, None).
    HEAD: ('electronics', True, 'supplements') -- the correct chip overridden."""
    _flag(monkeypatch, "true")
    got = _run(scs._resolve_pair_category(_products(PAIR_Q), "supplements", parser_path=False))
    assert tuple(got) == ("supplements", False, None)
    assert a2b["n"] == 0


def test_resolver_honours_supplements_chip_flag_off(monkeypatch, a2b):
    """PIN (8b): flag OFF keeps today's tuple."""
    got = _run(scs._resolve_pair_category(_products(PAIR_Q), "supplements", parser_path=False))
    assert tuple(got) == ("electronics", True, "supplements")
    assert a2b["n"] == 0


def test_resolver_no_chip_pharmacy_veto_is_the_signal_flag_on(monkeypatch, a2b):
    """RED (9, ruling R2 / open question 4 = YES): a chipless pharmacy pair goes
    to supplements WITHOUT an A2b (gpt-4o-mini) call. HEAD:
    ('electronics', False, None)."""
    _flag(monkeypatch, "true")
    a2b["answer"] = "fragrances"  # would be visible if A2b were consulted
    got = _run(scs._resolve_pair_category(_products(PAIR_Q), None, parser_path=False))
    assert tuple(got) == ("supplements", False, None)
    assert a2b["n"] == 0


def test_resolver_no_chip_pharmacy_flag_off(monkeypatch, a2b):
    """PIN (9b): flag OFF -> ('electronics', False, None), A2b not called."""
    got = _run(scs._resolve_pair_category(_products(PAIR_Q), None, parser_path=False))
    assert tuple(got) == ("electronics", False, None)
    assert a2b["n"] == 0


def test_resolver_household_no_chip_escalates_to_a2b_flag_on(monkeypatch, a2b):
    """RED (9c): a household pair has no category word left, so the blind branch
    escalates to A2b exactly once. HEAD: ('electronics', False, None), 0 calls."""
    _flag(monkeypatch, "true")
    a2b["answer"] = "other"
    q = "Finish Quantum dishwasher tablets vs Fairy Platinum tablets"
    got = _run(scs._resolve_pair_category(_products(q), None, parser_path=False))
    assert tuple(got) == ("other", False, None)
    assert a2b["n"] == 1


@pytest.mark.parametrize("chip", ["supplements", None])
def test_explicit_pair_writes_back_supplements_sync(monkeypatch, chip):
    """RED (10): sync explicit_pair capture -- _fetch_product_data receives
    'supplements' for both products, with and without the chip (R2 pins both).
    HEAD: ['electronics', 'electronics']."""
    _flag(monkeypatch, "true")
    assert _capture("sync", chip) == ["supplements", "supplements"]


@pytest.mark.parametrize("chip", ["supplements", None])
def test_explicit_pair_writes_back_supplements_stream(monkeypatch, chip):
    """RED (10): streaming twin of the sync capture. HEAD: electronics x2."""
    _flag(monkeypatch, "true")
    assert _capture("stream", chip) == ["supplements", "supplements"]


@pytest.mark.parametrize("path", ["sync", "stream"])
@pytest.mark.parametrize("chip", ["supplements", None])
def test_explicit_pair_write_back_flag_off(monkeypatch, path, chip):
    """PIN (10b): flag OFF writes today's electronics on both paths."""
    assert _capture(path, chip) == ["electronics", "electronics"]


def _names(srcs):
    return sorted(getattr(s, "domain", None) or getattr(s, "name", None) or str(s)
                  for s in srcs)


def test_supplement_category_selects_pharmacy_sources():
    """PIN (11, membership only -- review R7/R11): the category gates the
    Bahrain pharmacy adapters. This proves selector membership, not the whole
    price tier end to end."""
    assert "bolo.bh" in _names(sr.get_sitemap_sources_for_category("supplements"))
    assert "nasserpharmacy.com" in _names(sr.get_jsonapi_sources_for_category("supplements"))
    assert "bolo.bh" not in _names(sr.get_sitemap_sources_for_category("electronics"))
    assert "nasserpharmacy.com" not in _names(sr.get_jsonapi_sources_for_category("electronics"))


@pytest.mark.parametrize("value,b_flag", [(None, None), ("false", None), (None, "true")])
def test_flag_off_corpus_equality(monkeypatch, value, b_flag):
    """PIN (12): flag OFF (also with the blocklist flag ON), the 360-row corpus
    records equal the committed HEAD golden record for record, and hash to
    b76fcef9..."""
    _flag(monkeypatch, value)
    _flag(monkeypatch, b_flag, FLAG_B)
    golden = _load("category_corpus_gcc_360_head_records.json")["corpus_classification_records"]
    recs = _corpus_records()
    assert sorted(k for k in recs if recs[k] != golden.get(k)) == []
    assert recs == golden
    assert _canon_sha(recs) == HEAD_CORPUS_SHA


def test_flag_off_corpus_and_tablet_rows_hash(monkeypatch):
    """PIN (12b): flag OFF, corpus + the 35 tablet rows hash to the spec's
    off_all_sha (cac3460c...), the base the equality gate compares against."""
    recs = _corpus_records()
    recs.update(_tablet_records())
    assert _canon_sha(recs) == HEAD_ALL_SHA


def test_flag_on_corpus_delta_is_exactly_one_row(monkeypatch):
    """RED (13, re-measured for R2): flag ON, exactly C:supplements:05
    (Ferrous sulfate 65mg tablets) moves, to the supplements record, and the
    corpus hashes to 5b5a4b70... HEAD: 0 rows differ."""
    golden = _load("category_corpus_gcc_360_head_records.json")["corpus_classification_records"]
    _flag(monkeypatch, "true")
    recs = _corpus_records()
    assert sorted(k for k in recs if recs[k] != golden[k]) == ["C:supplements:05"]
    assert recs["C:supplements:05"] == ON_RECORD_C_SUPPLEMENTS_05
    assert _canon_sha(recs) == ON_CORPUS_SHA


def test_flag_on_tablet_rows_delta(monkeypatch):
    """RED (13b): flag ON, the rows that move are C:supplements:05 and the 17
    pharmacy/household tablet rows TP:00..TP:16; every device row and TP:17
    (already supplements) is unchanged; whole hash ef29dbee... (ruling R16a moved
    one half of TP:04: 'Nurofen 200mg 24 tablets' is no longer a dose -- the
    pair still vetoes through 'brufen' and '30 tablets')."""
    off = _corpus_records()
    off.update(_tablet_records())
    _flag(monkeypatch, "true")
    on = _corpus_records()
    on.update(_tablet_records())
    moved = sorted(k for k in on if on[k] != off[k])
    assert moved == ["C:supplements:05"] + ["TP:%02d" % i for i in range(17)]
    assert _canon_sha(on) == ON_ALL_SHA


def test_flag_read_per_call(monkeypatch):
    """RED (14): one process, the flag flipped between calls: ON -> supplements,
    unset -> electronics, ON -> supplements (catches an import-time read)."""
    _flag(monkeypatch, "true")
    assert es.classify_category_from_text(PAIR_Q) == "supplements"
    _flag(monkeypatch, None)
    assert es.classify_category_from_text(PAIR_Q) == "electronics"
    _flag(monkeypatch, "true")
    assert es.classify_category_from_text(PAIR_Q) == "supplements"
