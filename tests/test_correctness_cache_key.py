"""Wave C — cache-key correctness (genuine-price CORRECTNESS build).

The price cache key folded in only ONE size axis (size_variant_token = the ml/GB
token), so EDP 100ml and EDT 100ml COLLIDED on one key, and a variant qualifier
(FE) living only in the search_query was DROPPED — meaning a warmed EDP/256GB price
would be served for an EDT/FE request even with perfect selection. The key must
discriminate concentration + variant-qualifier + size/storage, while treating
ALIAS wording (EDT == "eau de toilette", oz == ml) as the SAME key, and staying
backward-compatible for sizeless/plain products (no needless cache-warm invalidation).

# RED on b207bfa; pass after the composite-identity cache token lands.
"""
from app.services.price_service import build_size_aware_price_cache_key
from app.services.extraction_service import get_price_cache_key, get_specs_cache_key


def _pk(identity, name="Bleu de Chanel", brand="Chanel", variant=None):
    return build_size_aware_price_cache_key(brand, name, variant, "bahrain", identity)


# --------------------------------------------------------------------------- #
# Concentration axis — EDP must NOT collide with EDT (the warm-cache EDP→EDT bug)
# --------------------------------------------------------------------------- #
def test_edp_edt_price_keys_distinct():  # RED
    assert _pk("Bleu de Chanel Eau de Parfum 100ml") != _pk("Bleu de Chanel Eau de Toilette 100ml")


def test_edt_abbreviation_same_key_as_spelled_out():  # RED (alias-tolerant)
    # "EDT" and "Eau de Toilette" are the SAME concentration → SAME key.
    assert _pk("Bleu de Chanel EDT 100ml") == _pk("Bleu de Chanel Eau de Toilette 100ml")


# --------------------------------------------------------------------------- #
# Size axis — oz and ml of the same bottle are the SAME key (alias), distinct
# sizes are distinct (existing guarantee preserved).
# --------------------------------------------------------------------------- #
def test_oz_equals_ml_same_key():  # RED
    # 3.4 oz snaps to the 100ml bottle → same key as "100ml".
    assert _pk("Bleu de Chanel Eau de Parfum 100ml") == _pk("Bleu de Chanel Eau de Parfum 3.4 oz")


def test_distinct_ml_distinct_key():  # GREEN (preserved)
    assert _pk("Bleu de Chanel Eau de Parfum 100ml") != _pk("Bleu de Chanel Eau de Parfum 50ml")


# --------------------------------------------------------------------------- #
# Variant-qualifier axis — S24 256GB must NOT collide with S24 FE 256GB even when
# the "FE" lives only in the identity_text (search query), not the name.
# --------------------------------------------------------------------------- #
def test_fe_variant_distinct_from_base_key():  # RED
    base = build_size_aware_price_cache_key(
        "Samsung", "Galaxy S24", None, "bahrain", "Samsung Galaxy S24 256GB")
    fe = build_size_aware_price_cache_key(
        "Samsung", "Galaxy S24", None, "bahrain", "Samsung Galaxy S24 FE 256GB")
    assert base != fe


def test_storage_variants_distinct_key():  # GREEN (preserved)
    k256 = build_size_aware_price_cache_key("Apple", "iPhone 15", None, "bahrain", "iPhone 15 256GB")
    k128 = build_size_aware_price_cache_key("Apple", "iPhone 15", None, "bahrain", "iPhone 15 128GB")
    assert k256 != k128


# --------------------------------------------------------------------------- #
# Backward-compat — a plain sizeless/concentrationless product keeps the legacy
# key (no cache-warm invalidation for the common case).
# --------------------------------------------------------------------------- #
def test_sizeless_product_keeps_legacy_key():  # GREEN
    assert (
        build_size_aware_price_cache_key("Acme", "Widget Classic", None, "bahrain", "")
        == get_price_cache_key("Acme", "Widget Classic", None, "bahrain")
    )


def test_plain_electronics_no_qualifier_keeps_storage_only_key():  # GREEN
    # No qualifier/concentration → the key reduces to the legacy storage-token key
    # (no invalidation of the existing electronics warmed cache).
    before = build_size_aware_price_cache_key("Apple", "iPhone 15", None, "bahrain", "iPhone 15 256GB")
    again = build_size_aware_price_cache_key("Apple", "iPhone 15 256GB", None, "bahrain", "")
    assert before == again


# --------------------------------------------------------------------------- #
# Specs cache key — same concentration alias-tolerance + EDP/EDT discrimination
# (gap #59: EDP and EDT specs collided).
# --------------------------------------------------------------------------- #
def test_specs_edp_edt_distinct():  # RED
    assert (
        get_specs_cache_key("Chanel", "Bleu de Chanel Eau de Parfum 100ml", None)
        != get_specs_cache_key("Chanel", "Bleu de Chanel Eau de Toilette 100ml", None)
    )


def test_specs_edt_abbreviation_same_key():  # RED (alias)
    assert (
        get_specs_cache_key("Chanel", "Bleu de Chanel EDT 100ml", None)
        == get_specs_cache_key("Chanel", "Bleu de Chanel Eau de Toilette 100ml", None)
    )
