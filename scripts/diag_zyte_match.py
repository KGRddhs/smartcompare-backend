"""Zyte match-tuning RECON — dump the real sephora.me candidate lists + per-gate
verdicts for the products that PENDED in the seed, so the matcher fixes are driven
by ground truth (not guessed). Read-only diagnostic; does NOT write the cache.

For each (brand, name, variant) it runs the SAME Zyte productList search the seed
runs, then for every returned candidate prints: title, raw price, fils-normalized
price, and pass/fail for each no-fab gate (counterfeit / accessory / numbers /
variant / amount / brand-aware overlap / concentration), plus what the CURRENT
_match_product picks. Then it shows what a BRAND-AWARE + concentration-aware
scorer would pick, side by side.

Run:  python -m scripts.diag_zyte_match
Needs ENABLE_ZYTE_RENDER + ZYTE_API_KEY (set below / from .env). Burns Zyte credits
(one productList extract per product — ~16 here).
"""
from __future__ import annotations

import os

os.environ["ENABLE_ZYTE_RENDER"] = "true"
os.environ.setdefault("ZYTE_TIMEOUT", "100")

try:
    from dotenv import load_dotenv
    load_dotenv(override=False)
except Exception:
    pass

import asyncio
import urllib.parse

from app.services import zyte_service as Z
from app.services.price_service import (
    is_counterfeit_listing,
    is_accessory,
    numbers_match,
    variant_mismatch,
    normalize_words,
    extract_concentration,
)

# The pended / mis-matched products from the seed (Tom Ford pairs included for the
# concentration-precision case). brand kept separate so we can test brand-aware
# overlap.
PRODUCTS = [
    ("Dior", "Sauvage", None),
    ("Dior", "Homme Intense", None),
    ("Dior", "Miss Dior", None),
    ("Marc Jacobs", "Daisy", None),
    ("Viktor Rolf", "Flowerbomb", None),
    ("Mugler", "Alien", None),
    ("Paco Rabanne", "1 Million", None),
    ("Tom Ford", "Oud Wood", None),          # concentration case: EDP 77 vs Parfum 158
    ("YSL", "Black Opium", None),            # known-good control
]


def _brand_tokens(brand: str) -> set:
    return normalize_words(brand or "")


def _gate_report(product_name: str, brand: str, prod: dict) -> str:
    name = (prod.get("name") or "").strip()
    raw = prod.get("price")
    norm = Z.normalize_bhd_amount(raw)
    p_words = normalize_words(product_name)
    t_words = normalize_words(name)
    brand_w = _brand_tokens(brand)
    # current overlap (all query words incl. brand)
    cur_overlap = (len(p_words & t_words) / len(p_words)) if p_words else 0.0
    # brand-aware overlap (distinctive product tokens only)
    distinctive = p_words - brand_w
    ba_overlap = (len(distinctive & t_words) / len(distinctive)) if distinctive else 0.0
    extra = len(t_words - p_words)
    q_conc = extract_concentration(product_name)
    t_conc = extract_concentration(name)
    gates = []
    gates.append("CF" if is_counterfeit_listing(name) else "cf")
    gates.append("ACC" if is_accessory(name) else "acc")
    gates.append("num" if numbers_match(product_name, name) else "NUM!")
    gates.append("var!" if variant_mismatch(product_name, name) else "var")
    gates.append(f"amt={norm}")
    return (
        f"      [{' '.join(gates)}] cur_ov={cur_overlap:.2f} ba_ov={ba_overlap:.2f} "
        f"extra={extra} conc:q={q_conc}/t={t_conc}\n"
        f"      title={name!r}  raw={raw}"
    )


async def diag_one(brand: str, name: str, variant):
    full = f"{brand} {name} {variant or ''}".strip()
    print(f"\n{'='*78}\nQUERY: {full!r}")
    store = Z.ZYTE_STORES["sephora.me"]
    search_url = store["search"].format(q=urllib.parse.quote(full))
    data = await Z._zyte_extract(search_url, {"productList": True})
    if not data:
        print("  !! Zyte returned NO DATA (empty extract / error) — transient-fail candidate")
        return
    products = (data.get("productList") or {}).get("products") or []
    print(f"  {len(products)} candidates returned:")
    for prod in products[:12]:
        if not isinstance(prod, dict):
            continue
        print(_gate_report(full, brand, prod))
    cur_pick = Z._match_product(products, full, brand)
    print(f"  _match_product (brand-aware) picks: "
          f"{(cur_pick or {}).get('name')!r} @ {(cur_pick or {}).get('price')}")


async def main():
    if not os.getenv("ZYTE_API_KEY"):
        print("ZYTE_API_KEY not set — aborting")
        return
    import sys
    # CLI: "Brand|Name" args override the default list (conserves Zyte credits).
    argv = sys.argv[1:]
    products = PRODUCTS
    if argv:
        products = []
        for a in argv:
            b, _, n = a.partition("|")
            products.append((b.strip(), n.strip(), None))
    for brand, name, variant in products:
        try:
            await diag_one(brand, name, variant)
        except Exception as exc:  # noqa: BLE001
            print(f"  ERROR for {brand} {name}: {exc}")


if __name__ == "__main__":
    asyncio.run(main())
