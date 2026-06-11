"""Sub-category detection + product-type schema lookup.

Lane 2 (Backend Comparison Engine Overhaul). 25+ product-type schemas live
here. The `_build_specs_prompt` in `extraction_service.py` calls
`detect_product_type` + `get_schema_for_type` to inject a tailored field list
into the GPT-4o-mini system prompt — so an iPhone gets
display/processor/ram/...  while a washing machine gets
capacity_kg/spin_rpm/energy_class.

Detection is keyword-based and synchronous.
"""

from typing import List


PRODUCT_TYPE_KEYWORDS = {
    # Electronics (12)
    "electronics.phone":     ["iphone", "galaxy s", "pixel", "xiaomi", "oneplus", "nothing phone", "smartphone", "phone"],
    "electronics.tv":        ["tv", "qled", "oled", "led tv", "smart tv", "bravia", "neo qled"],
    "electronics.laptop":    ["macbook", "thinkpad", "xps", "yoga", "envy", "pavilion", "laptop", "notebook"],
    "electronics.tablet":    ["ipad", "galaxy tab", "tablet", "surface"],
    "electronics.smartwatch":["apple watch", "galaxy watch", "fitbit", "garmin", "smartwatch"],
    "electronics.headphones":["airpods", "wh-1000xm", "qc ultra", "buds", "headphones", "earbuds"],
    "electronics.speaker":   ["sonos", "homepod", "bose soundlink", "speaker"],
    # Washer/refrigerator declared BEFORE ac so the more-specific compound
    # keywords ("washing machine", "refrigerator", "side by side") win over
    # the short "ac" alias (which would otherwise substring-match inside
    # "machine" -> ma[c]hine).
    "electronics.washer":    ["washing machine", "washer dryer", "front load", "top load"],
    "electronics.refrigerator":["refrigerator", "fridge", "side by side", "french door"],
    "electronics.ac":        ["split ac", "air conditioner", "inverter ac", " ac"],
    "electronics.vacuum":    ["vacuum", "dyson v", "roomba", "robovac", "stick vacuum"],
    "electronics.gaming_console":["ps5", "xbox series", "switch", "playstation"],

    # Supplements (6) — order matters: more specific keywords go first so
    # "vitamin d" hits supplements.vitamin and "multivitamin" hits .multivitamin
    "supplements.fish_oil":  ["fish oil", "omega 3", "omega-3"],
    "supplements.preworkout":["pre-workout", "preworkout", "pre workout"],
    "supplements.protein":   ["whey", "casein", "iso100", "plant protein", "protein powder"],
    "supplements.multivitamin":["multivitamin", "one a day", "centrum"],
    "supplements.vitamin":   ["vitamin d", "vitamin c", "vitamin b"],
    "supplements.mineral":   ["zinc", "magnesium", "iron supplement", "calcium"],

    # Fragrances (3) — niche brand checks BEFORE concentration keywords so
    # "Creed Aventus EDP" maps to .niche, not .edp
    "fragrances.niche":      ["mfk", "creed", "initio", "frederic malle", "amouage"],
    "fragrances.edp":        ["eau de parfum", "edp"],
    "fragrances.edt":        ["eau de toilette", "edt"],

    # Makeup (3)
    "makeup.foundation":     ["foundation", "pro filt'r", "fit me", "luminous"],
    "makeup.lipstick":       ["lipstick", "matte lip", "lip color"],
    "makeup.mascara":        ["mascara", "sky high", "telescopic", "diorshow"],

    # Skincare (3)
    "skincare.sunscreen":    ["sunscreen", "spf", "sun cream"],
    "skincare.cleanser":     ["cleanser", "face wash", "foaming wash"],
    "skincare.serum":        ["serum", "vitamin c serum", "niacinamide"],

    # Haircare (1)
    "haircare.shampoo":      ["shampoo"],

    # Fashion (3)
    "fashion.bag":           ["bag", "tote", "satchel", "handbag", "backpack"],
    "fashion.shoe":          ["sneaker", "shoe", "trainer", "boot", "loafer", "air force", "stan smith"],
    "fashion.watch":         ["watch", "rolex", "omega", "seiko", "casio"],

    # Grocery (3)
    "grocery.oil":           ["olive oil", "cooking oil", "extra virgin"],
    "grocery.tea":           ["earl grey", "green tea", "black tea", "tea"],
    "grocery.chocolate":     ["chocolate", "cocoa", "dark chocolate"],
}


PRODUCT_TYPE_SCHEMAS = {
    "electronics.phone":     ["display", "processor", "ram", "storage", "battery", "rear_camera", "front_camera", "os", "5G", "weight", "water_resistance", "charging_w"],
    "electronics.tv":        ["screen_size", "panel_type", "resolution", "refresh_rate", "hdr", "smart_os", "ports_hdmi", "audio_w", "consumption_kwh"],
    "electronics.laptop":    ["display", "cpu", "gpu", "ram", "storage", "battery_hrs", "weight", "ports", "os", "keyboard_layout"],
    "electronics.tablet":    ["display", "processor", "ram", "storage", "battery", "weight", "os", "stylus_support"],
    "electronics.smartwatch":["display", "sensors", "battery_days", "water_resistance", "connectivity", "weight", "compatibility"],
    "electronics.headphones":["driver_mm", "anc", "battery_hrs", "weight", "codecs", "bt_version", "water_resistance"],
    "electronics.speaker":   ["driver_count", "power_w", "battery_hrs", "connectivity", "water_resistance", "smart_assistant"],
    "electronics.ac":        ["capacity_btu", "energy_class", "inverter", "noise_db", "modes", "filter", "wifi", "refrigerant", "coverage_sqm"],
    "electronics.washer":    ["capacity_kg", "spin_rpm", "energy_class", "load_type", "programs", "noise_db", "inverter", "dimensions"],
    "electronics.refrigerator":["capacity_l", "doors", "energy_class", "ice_maker", "freezer_position", "noise_db"],
    "electronics.vacuum":    ["suction_pa", "battery_min", "weight", "dustbin_l", "filtration", "attachments"],
    "electronics.gaming_console":["storage", "controller", "video_output", "online_service", "exclusives_count"],
    "supplements.vitamin":   ["dose_iu_mcg", "form", "third_party_tested", "allergens", "serving_size", "count"],
    "supplements.mineral":   ["dose_mg", "form", "chelation", "bioavailability", "serving_size", "count"],
    "supplements.protein":   ["protein_g_serving", "carbs", "fat", "calories", "amino_profile", "filtration", "flavors", "container_size"],
    "supplements.preworkout":["caffeine_mg", "beta_alanine_g", "creatine_g", "citrulline_g", "servings"],
    "supplements.fish_oil":  ["epa_mg", "dha_mg", "third_party_tested", "molecularly_distilled", "serving_size", "count"],
    "supplements.multivitamin":["vitamins_count", "minerals_count", "form", "iron_included", "serving_size", "count"],
    # S2 I2.4 (H8) — `heat_stability` appended to every makeup/skincare/
    # fragrances subtype so the Gulf-climate signal extracts on the subtype
    # path (which overrides the category list for nearly all real queries).
    # Verdict-awareness signal only — NO scoring dimension touched.
    "fragrances.edp":        ["concentration", "longevity_hrs", "sillage", "projection_m", "scent_family", "notes_top", "notes_heart", "notes_base", "volume_ml", "season", "occasion", "heat_stability"],
    "fragrances.edt":        ["concentration", "longevity_hrs", "sillage", "scent_family", "notes_top", "notes_heart", "notes_base", "volume_ml", "season", "occasion", "heat_stability"],
    "fragrances.niche":      ["concentration", "longevity_hrs", "sillage", "projection_m", "scent_family", "notes_top", "notes_heart", "notes_base", "perfumer", "house_year_founded", "volume_ml", "heat_stability"],
    "makeup.foundation":     ["shade_range_count", "finish", "coverage", "skin_type", "spf", "fragrance_free", "vegan", "vol_ml", "heat_stability"],
    "makeup.lipstick":       ["finish", "color", "longevity_hrs", "transfer_proof", "moisturising", "vegan", "vol_g", "heat_stability"],
    "makeup.mascara":        ["brush_type", "formula", "smudge_proof", "water_proof", "lash_effect", "vegan", "color", "heat_stability"],
    "skincare.serum":        ["hero_active", "secondary_actives", "ph", "comedogenic", "fragrance_free", "skin_type", "vol_ml", "heat_stability"],
    "skincare.sunscreen":    ["spf", "pa_rating", "filter_type", "finish", "water_resist_min", "fragrance_free", "white_cast", "heat_stability"],
    "skincare.cleanser":     ["cleanser_type", "ph", "skin_type", "actives", "fragrance_free", "vol_ml", "heat_stability"],
    "haircare.shampoo":      ["sulfate_free", "paraben_free", "silicone_free", "target_concern", "hair_type", "vol_ml", "scent"],
    "fashion.bag":           ["material", "lining", "hardware", "closure", "dimensions", "strap_drop", "origin", "weight"],
    "fashion.shoe":          ["upper_material", "sole", "closure", "sizing_run", "width", "last_shape", "origin"],
    "fashion.watch":         ["case_material", "movement", "water_resist_atm", "crystal", "diameter_mm", "strap", "complications"],
    "grocery.oil":           ["variety", "origin", "acidity_pct", "filtration", "organic", "volume_ml"],
    "grocery.tea":           ["type", "origin", "format", "caffeine", "bags_count", "organic"],
    "grocery.chocolate":     ["cacao_pct", "origin", "vegan", "sugar_g_serving", "weight_g"],
}


def detect_product_type(product_name: str, category: str) -> str:
    """Keyword-based sub-type detection.

    Returns ``"<category>.<sub_type>"`` (e.g., ``"electronics.phone"``). When
    no keyword matches but the category has at least one known sub-type,
    returns the first sub-type for the category (deterministic fallback).
    When the category itself is unknown, returns ``"<category>.default"``.
    """
    if not product_name:
        candidates = [k for k in PRODUCT_TYPE_KEYWORDS if k.startswith(f"{category}.")]
        if candidates:
            return candidates[0]
        return f"{category}.default"

    name_lower = product_name.lower()
    candidates = [k for k in PRODUCT_TYPE_KEYWORDS if k.startswith(f"{category}.")]

    for type_key in candidates:
        for kw in PRODUCT_TYPE_KEYWORDS[type_key]:
            if kw in name_lower:
                return type_key

    if candidates:
        return candidates[0]
    return f"{category}.default"


def get_schema_for_type(type_key: str) -> List[str]:
    """Return the field list for `type_key` (empty list when unknown)."""
    return list(PRODUCT_TYPE_SCHEMAS.get(type_key, []))
