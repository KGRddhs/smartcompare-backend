"""INC-U1b LIFT-RULE-F (no new flag) -- the RED file (S99 lane).

Spec: INC_U1B_UNIT_SPEC.md sections 2, 3, 5, 6 as bound by GATE_INC_U1B.md UB-1..UB-13
and the relay ruling ORCH-U1B-A (UB-10: other-currency link rows are stored only while
ENABLE_URL_LINK_RESULT and ENABLE_SMART_PICK_BHD_ONLY are both ON; UB-11: the PIN rows
cover all four mixes of the two switches, each OFF switch in every OFF spelling), and by
RULINGS_INC_U1.md U-10 (no log line prints more of a pasted link than its host).
Base: main 022b292eca94b23378fa414809b8db6bb75e6b89.

The contract under test: in url_extraction_service._link_result_adapt_inner a product
whose price is kept in another convertible currency (kind "foreign": SAR, AED, KWD,
alone or beside BHD) no longer keeps the pair out of History when the keyword-only
``foreign_history`` is True; compare_from_urls reads _link_foreign_history_ok() (the
house idiom over ENABLE_SMART_PICK_BHD_ONLY, the value set of
home_routes.smart_pick_bhd_only_enabled) ONCE per compare inside ``if link_result:``.
In every state a pending unknown-currency price (FX-1), a placeholder name (FX-3) and a
degraded verdict keep the pair out.

The four mixes (L = ENABLE_URL_LINK_RESULT, G = ENABLE_SMART_PICK_BHD_ONLY):
  L off / G off  B12 (each L OFF spelling x each G OFF spelling, V1 and V2)
  L off / G on   B05 (each L OFF spelling, V1 and V2): no link row at all
  L on  / G off  B04 (each G OFF spelling) and the G OFF half of B09: rule F as frozen
  L on  / G on   B02, B03, B13 (RED: the lift) and the PIN rows B06, B07, B08, the G ON
                 half of B09, B10, B14 (what the lift never changes)

Rows marked RED fail at base on an AssertionError only (every symbol the unit adds is
read with getattr / inspect and asserted); rows marked PIN are green at base and stay
green. B1 rule: the OFF rows (B04, B05, B12) run with the frozen full() configuration
(the winner guard, the result gate, the resolver and the egress stop ON, V1 and V2) and
its recorders, plus a call recorder on the new reader. The flag-OFF bodies are recorded
literals (measured at base). The frozen INC-U1 helpers are imported read-only, as
tests/test_inc_u1_fix1.py does. Synthetic hosts and run-time ids only; no network, no
database, no credential literal.
"""

from __future__ import annotations

import app.main  # noqa: F401  -- FIRST: the dotenv hazard (common brief)

import ast
import asyncio
import copy
import inspect
import logging
import pathlib
import textwrap

import httpx
import pytest

from app.api import home_routes, profile_routes, url_routes
from app.services import database_service as dbs
from app.services import price_service, text_sanitize
from app.services import url_extraction_service as ues
from tests.test_inc_u1_fix1 import (
    AMZ_PAGE,
    AMZ_TR,
    EMPTY_PAGE,
    _no_history_query,
    _pending_currency_unknown,
)
from tests.test_inc_u1_gate_rows import (
    FULL_ON,
    P01_BODY,
    P02_BODY,
    _assert_base_requests,
)
from tests.test_inc_u1_link_result import (  # noqa: F401  -- fixtures by name
    FLAG,
    H,
    OFF_VALUES,
    PAGE_A,
    PAGE_B,
    URL1,
    URL2,
    VERDICT_ERROR,
    _FakeInsert,
    _link_on,
    _u1_env,
    _unit_ran,
    call,
    client,
    full,
    node,
    ok,
    page,
    page_reads,
    products_of,
    set_env,
    u10_assert_no_link_text,
)

G = "ENABLE_SMART_PICK_BHD_ONLY"
READER = "_link_foreign_history_ok"
# The Home readers' other switches: cleared so every row states the guard it reads.
HOME_AMBIENT = (
    "ENABLE_SMART_PICK_VERDICT_CAPTION",
    "ENABLE_PRICE_NOT_LOST",
    "ENABLE_HOME_SAVINGS_AGGREGATE",
)
ON_VALUES = ["true", " TRUE ", "1", "yes", "On"]
G_MIX_ON = ["true", " TRUE "]
NEWER = "2026-01-02T00:00:00Z"
OLDER = "2026-01-01T00:00:00Z"

# (amount, code) of product 0 (Dior Sauvage on shop-a) and product 1 (Chanel Bleu on
# shop-b); the BHD sides are the PAGE_A / PAGE_B strings of the frozen file.
PAIRS = {
    "sar-sar": ((450, "SAR"), (520, "SAR")),
    "aed-aed": ((399, "AED"), (455, "AED")),
    "sar-bhd": ((450, "SAR"), ("45.500", "BHD")),
    "bhd-aed": (("30.000", "BHD"), (455, "AED")),
    "aed-bhd": ((399, "AED"), ("45.500", "BHD")),
    "kwd-bhd": ((38.5, "KWD"), ("45.500", "BHD")),
}

# Measured at base 022b292e under the FULL_ON configuration with G unset: the L OFF
# success body of the sar-bhd pair (B05 / B12) and the L ON success bodies of the
# sar-sar and aed-bhd pairs (B04), V1 and V2.
B05_SAR_V1_BODY: dict = {
    "success": True,
    "products": [
        {
            "brand": "Dior",
            "name": "Sauvage Eau de Parfum 100ml",
            "full_name": "Sauvage Eau de Parfum 100ml",
            "variant": None,
            "category": "fragrances",
            "price": {
                "amount": 450,
                "currency": "SAR",
                "retailer": "shop-a.example",
                "url": "https://shop-a.example/p/u1sentinelpath/sauvage-edp?ref=u1sentineltoken",
                "in_stock": None,
            },
            "specs": {},
            "reviews": {"rating": "4.5", "count": "120"},
            "image_url": "https://cdn.shop-a.example/a.jpg",
            "source_url": "https://shop-a.example/p/u1sentinelpath/sauvage-edp?ref=u1sentineltoken",
            "retailer": {
                "key": "unknown",
                "domain": "shop-a.example",
                "name": "shop-a.example",
                "region": "unknown",
                "currency": "USD",
            },
        },
        {
            "brand": "Chanel",
            "name": "Bleu de Chanel Eau de Parfum 100ml",
            "full_name": "Bleu de Chanel Eau de Parfum 100ml",
            "variant": None,
            "category": "fragrances",
            "price": {
                "amount": "45.500",
                "currency": "BHD",
                "retailer": "shop-b.example",
                "url": "https://shop-b.example/p/u1sentinelpath/bleu-edp?ref=u1sentineltoken",
                "in_stock": None,
            },
            "specs": {},
            "reviews": {"rating": "4.8", "count": "300"},
            "image_url": "https://cdn.shop-b.example/b.jpg",
            "source_url": "https://shop-b.example/p/u1sentinelpath/bleu-edp?ref=u1sentineltoken",
            "retailer": {
                "key": "unknown",
                "domain": "shop-b.example",
                "name": "shop-b.example",
                "region": "unknown",
                "currency": "USD",
            },
        },
    ],
    "comparison": {
        "winner_index": 1,
        "winner_declaration": "B",
        "winner_reason": "Bleu lasts longer on skin through the day. It "
        "scores 82/100 overall.",
        "key_tradeoff": "Sauvage opens brighter.",
        "specs_comparison": {
            "product_0_advantages": ["brighter opening"],
            "product_1_advantages": ["longer wear"],
            "similar": ["EDP"],
        },
        "product_0_pros": ["fresh opening", 7, None, "   "],
        "product_0_cons": ["shorter wear"],
        "product_1_pros": ["long wear"],
        "product_1_cons": ["heavier", {"x": 1}],
    },
    "winner_index": 1,
    "recommendation": "",
    "key_differences": [],
    "category_used": "fragrances",
    "source_urls": [
        "https://shop-a.example/p/u1sentinelpath/sauvage-edp?ref=u1sentineltoken",
        "https://shop-b.example/p/u1sentinelpath/bleu-edp?ref=u1sentineltoken",
    ],
}
B05_SAR_V2_BODY: dict = {
    "success": True,
    "products": [
        {
            "brand": "Dior",
            "name": "Sauvage Eau de Parfum 100ml",
            "full_name": "Sauvage Eau de Parfum 100ml",
            "variant": None,
            "category": "fragrances",
            "price": {
                "amount": 450,
                "currency": "SAR",
                "retailer": "shop-a.example",
                "url": "https://shop-a.example/p/u1sentinelpath/sauvage-edp?ref=u1sentineltoken",
                "in_stock": None,
            },
            "specs": {},
            "reviews": {"rating": "4.5", "count": "120"},
            "image_url": "https://cdn.shop-a.example/a.jpg",
            "source_url": "https://shop-a.example/p/u1sentinelpath/sauvage-edp?ref=u1sentineltoken",
            "retailer": {
                "key": "unknown",
                "domain": "shop-a.example",
                "name": "shop-a.example",
                "region": "unknown",
                "currency": "USD",
            },
        },
        {
            "brand": "Chanel",
            "name": "Bleu de Chanel Eau de Parfum 100ml",
            "full_name": "Bleu de Chanel Eau de Parfum 100ml",
            "variant": None,
            "category": "fragrances",
            "price": {
                "amount": "45.500",
                "currency": "BHD",
                "retailer": "shop-b.example",
                "url": "https://shop-b.example/p/u1sentinelpath/bleu-edp?ref=u1sentineltoken",
                "in_stock": None,
            },
            "specs": {},
            "reviews": {"rating": "4.8", "count": "300"},
            "image_url": "https://cdn.shop-b.example/b.jpg",
            "source_url": "https://shop-b.example/p/u1sentinelpath/bleu-edp?ref=u1sentineltoken",
            "retailer": {
                "key": "unknown",
                "domain": "shop-b.example",
                "name": "shop-b.example",
                "region": "unknown",
                "currency": "USD",
            },
        },
    ],
    "comparison": {
        "winner_index": 1,
        "winner_declaration": "B",
        "winner_reason": "Bleu lasts longer on skin through the day. It "
        "scores 82/100 overall.",
        "key_tradeoff": "Sauvage opens brighter.",
        "specs_comparison": {
            "product_0_advantages": ["brighter opening"],
            "product_1_advantages": ["longer wear"],
            "similar": ["EDP"],
        },
        "product_0_pros": ["fresh opening", 7, None, "   "],
        "product_0_cons": ["shorter wear"],
        "product_1_pros": ["long wear"],
        "product_1_cons": ["heavier", {"x": 1}],
    },
    "winner_index": 1,
    "recommendation": "Bleu lasts longer on skin through the day.",
    "key_differences": ["brighter opening", "longer wear"],
    "category_used": "fragrances",
    "source_urls": [
        "https://shop-a.example/p/u1sentinelpath/sauvage-edp?ref=u1sentineltoken",
        "https://shop-b.example/p/u1sentinelpath/bleu-edp?ref=u1sentineltoken",
    ],
}
B04_SAR_SAR_V1_BODY: dict = {
    "success": True,
    "products": [
        {
            "brand": "Dior",
            "name": "Sauvage Eau de Parfum 100ml",
            "full_name": "Sauvage Eau de Parfum 100ml",
            "variant": "EDP 100ml",
            "category": "fragrances",
            "price": {
                "amount": 450,
                "currency": "SAR",
                "retailer": "shop-a.example",
                "url": "https://shop-a.example/p/u1sentinelpath/sauvage-edp?ref=u1sentineltoken",
                "in_stock": None,
                "estimate_bhd": 45.135,
                "estimate_basis": "fallback_rate",
            },
            "specs": {},
            "reviews": {"rating": "4.5", "count": "120"},
            "image_url": "https://cdn.shop-a.example/a.jpg",
            "source_url": "https://shop-a.example/p/u1sentinelpath/sauvage-edp?ref=u1sentineltoken",
            "retailer": {
                "key": "unknown",
                "domain": "shop-a.example",
                "name": "shop-a.example",
                "region": "unknown",
                "currency": "USD",
            },
            "pros": ["fresh opening"],
            "cons": ["shorter wear"],
            "rating": 4.5,
            "review_count": 120,
            "link_key": {
                "brand": "Dior",
                "line": "Sauvage",
                "concentration": "EDP",
                "size_ml": 100,
                "gtin": None,
                "resolved": True,
                "source": "lexicon",
            },
        },
        {
            "brand": "Chanel",
            "name": "Bleu de Chanel Eau de Parfum 100ml",
            "full_name": "Bleu de Chanel Eau de Parfum 100ml",
            "variant": "EDP 100ml",
            "category": "fragrances",
            "price": {
                "amount": 520,
                "currency": "SAR",
                "retailer": "shop-b.example",
                "url": "https://shop-b.example/p/u1sentinelpath/bleu-edp?ref=u1sentineltoken",
                "in_stock": None,
                "estimate_bhd": 52.156,
                "estimate_basis": "fallback_rate",
            },
            "specs": {},
            "reviews": {"rating": "4.8", "count": "300"},
            "image_url": "https://cdn.shop-b.example/b.jpg",
            "source_url": "https://shop-b.example/p/u1sentinelpath/bleu-edp?ref=u1sentineltoken",
            "retailer": {
                "key": "unknown",
                "domain": "shop-b.example",
                "name": "shop-b.example",
                "region": "unknown",
                "currency": "USD",
            },
            "pros": ["long wear"],
            "cons": ["heavier"],
            "rating": 4.8,
            "review_count": 300,
            "link_key": {
                "brand": "Chanel",
                "line": "Bleu de Chanel",
                "concentration": "EDP",
                "size_ml": 100,
                "gtin": None,
                "resolved": True,
                "source": "lexicon",
            },
        },
    ],
    "comparison": {
        "winner_index": 0,
        "winner_declaration": "",
        "winner_reason": "Dior Sauvage Eau de Parfum 100ml is the stronger "
        "overall pick.",
        "key_tradeoff": "",
        "specs_comparison": {
            "product_0_advantages": ["brighter opening"],
            "product_1_advantages": ["longer wear"],
            "similar": ["EDP"],
        },
        "product_0_pros": ["fresh opening", 7, None, "   "],
        "product_0_cons": ["shorter wear"],
        "product_1_pros": ["long wear"],
        "product_1_cons": ["heavier", {"x": 1}],
    },
    "winner_index": 0,
    "recommendation": "Dior Sauvage Eau de Parfum 100ml is the stronger overall pick.",
    "key_differences": ["brighter opening", "longer wear"],
    "category_used": "fragrances",
    "source_urls": [
        "https://shop-a.example/p/u1sentinelpath/sauvage-edp?ref=u1sentineltoken",
        "https://shop-b.example/p/u1sentinelpath/bleu-edp?ref=u1sentineltoken",
    ],
}
B04_SAR_SAR_V2_BODY: dict = {
    "success": True,
    "products": [
        {
            "brand": "Dior",
            "name": "Sauvage Eau de Parfum 100ml",
            "full_name": "Sauvage Eau de Parfum 100ml",
            "variant": "EDP 100ml",
            "category": "fragrances",
            "price": {
                "amount": 450,
                "currency": "SAR",
                "retailer": "shop-a.example",
                "url": "https://shop-a.example/p/u1sentinelpath/sauvage-edp?ref=u1sentineltoken",
                "in_stock": None,
                "estimate_bhd": 45.135,
                "estimate_basis": "fallback_rate",
            },
            "specs": {},
            "reviews": {"rating": "4.5", "count": "120"},
            "image_url": "https://cdn.shop-a.example/a.jpg",
            "source_url": "https://shop-a.example/p/u1sentinelpath/sauvage-edp?ref=u1sentineltoken",
            "retailer": {
                "key": "unknown",
                "domain": "shop-a.example",
                "name": "shop-a.example",
                "region": "unknown",
                "currency": "USD",
            },
            "pros": ["fresh opening"],
            "cons": ["shorter wear"],
            "rating": 4.5,
            "review_count": 120,
            "link_key": {
                "brand": "Dior",
                "line": "Sauvage",
                "concentration": "EDP",
                "size_ml": 100,
                "gtin": None,
                "resolved": True,
                "source": "lexicon",
            },
        },
        {
            "brand": "Chanel",
            "name": "Bleu de Chanel Eau de Parfum 100ml",
            "full_name": "Bleu de Chanel Eau de Parfum 100ml",
            "variant": "EDP 100ml",
            "category": "fragrances",
            "price": {
                "amount": 520,
                "currency": "SAR",
                "retailer": "shop-b.example",
                "url": "https://shop-b.example/p/u1sentinelpath/bleu-edp?ref=u1sentineltoken",
                "in_stock": None,
                "estimate_bhd": 52.156,
                "estimate_basis": "fallback_rate",
            },
            "specs": {},
            "reviews": {"rating": "4.8", "count": "300"},
            "image_url": "https://cdn.shop-b.example/b.jpg",
            "source_url": "https://shop-b.example/p/u1sentinelpath/bleu-edp?ref=u1sentineltoken",
            "retailer": {
                "key": "unknown",
                "domain": "shop-b.example",
                "name": "shop-b.example",
                "region": "unknown",
                "currency": "USD",
            },
            "pros": ["long wear"],
            "cons": ["heavier"],
            "rating": 4.8,
            "review_count": 300,
            "link_key": {
                "brand": "Chanel",
                "line": "Bleu de Chanel",
                "concentration": "EDP",
                "size_ml": 100,
                "gtin": None,
                "resolved": True,
                "source": "lexicon",
            },
        },
    ],
    "comparison": {
        "winner_index": 0,
        "winner_declaration": "",
        "winner_reason": "Dior Sauvage Eau de Parfum 100ml is the stronger "
        "overall pick.",
        "key_tradeoff": "",
        "specs_comparison": {
            "product_0_advantages": ["brighter opening"],
            "product_1_advantages": ["longer wear"],
            "similar": ["EDP"],
        },
        "product_0_pros": ["fresh opening", 7, None, "   "],
        "product_0_cons": ["shorter wear"],
        "product_1_pros": ["long wear"],
        "product_1_cons": ["heavier", {"x": 1}],
    },
    "winner_index": 0,
    "recommendation": "Dior Sauvage Eau de Parfum 100ml is the stronger overall pick.",
    "key_differences": ["brighter opening", "longer wear"],
    "category_used": "fragrances",
    "source_urls": [
        "https://shop-a.example/p/u1sentinelpath/sauvage-edp?ref=u1sentineltoken",
        "https://shop-b.example/p/u1sentinelpath/bleu-edp?ref=u1sentineltoken",
    ],
}
B04_AED_BHD_V1_BODY: dict = {
    "success": True,
    "products": [
        {
            "brand": "Dior",
            "name": "Sauvage Eau de Parfum 100ml",
            "full_name": "Sauvage Eau de Parfum 100ml",
            "variant": "EDP 100ml",
            "category": "fragrances",
            "price": {
                "amount": 399,
                "currency": "AED",
                "retailer": "shop-a.example",
                "url": "https://shop-a.example/p/u1sentinelpath/sauvage-edp?ref=u1sentineltoken",
                "in_stock": None,
                "estimate_bhd": 40.858,
                "estimate_basis": "fallback_rate",
            },
            "specs": {},
            "reviews": {"rating": "4.5", "count": "120"},
            "image_url": "https://cdn.shop-a.example/a.jpg",
            "source_url": "https://shop-a.example/p/u1sentinelpath/sauvage-edp?ref=u1sentineltoken",
            "retailer": {
                "key": "unknown",
                "domain": "shop-a.example",
                "name": "shop-a.example",
                "region": "unknown",
                "currency": "USD",
            },
            "pros": ["fresh opening"],
            "cons": ["shorter wear"],
            "rating": 4.5,
            "review_count": 120,
            "link_key": {
                "brand": "Dior",
                "line": "Sauvage",
                "concentration": "EDP",
                "size_ml": 100,
                "gtin": None,
                "resolved": True,
                "source": "lexicon",
            },
        },
        {
            "brand": "Chanel",
            "name": "Bleu de Chanel Eau de Parfum 100ml",
            "full_name": "Bleu de Chanel Eau de Parfum 100ml",
            "variant": "EDP 100ml",
            "category": "fragrances",
            "price": {
                "amount": "45.500",
                "currency": "BHD",
                "retailer": "shop-b.example",
                "url": "https://shop-b.example/p/u1sentinelpath/bleu-edp?ref=u1sentineltoken",
                "in_stock": None,
            },
            "specs": {},
            "reviews": {"rating": "4.8", "count": "300"},
            "image_url": "https://cdn.shop-b.example/b.jpg",
            "source_url": "https://shop-b.example/p/u1sentinelpath/bleu-edp?ref=u1sentineltoken",
            "retailer": {
                "key": "unknown",
                "domain": "shop-b.example",
                "name": "shop-b.example",
                "region": "unknown",
                "currency": "USD",
            },
            "pros": ["long wear"],
            "cons": ["heavier"],
            "rating": 4.8,
            "review_count": 300,
            "link_key": {
                "brand": "Chanel",
                "line": "Bleu de Chanel",
                "concentration": "EDP",
                "size_ml": 100,
                "gtin": None,
                "resolved": True,
                "source": "lexicon",
            },
        },
    ],
    "comparison": {
        "winner_index": 1,
        "winner_declaration": "B",
        "winner_reason": "Bleu lasts longer on skin through the day. It "
        "scores 82/100 overall.",
        "key_tradeoff": "Sauvage opens brighter.",
        "specs_comparison": {
            "product_0_advantages": ["brighter opening"],
            "product_1_advantages": ["longer wear"],
            "similar": ["EDP"],
        },
        "product_0_pros": ["fresh opening", 7, None, "   "],
        "product_0_cons": ["shorter wear"],
        "product_1_pros": ["long wear"],
        "product_1_cons": ["heavier", {"x": 1}],
    },
    "winner_index": 1,
    "recommendation": "Bleu lasts longer on skin through the day.",
    "key_differences": ["brighter opening", "longer wear"],
    "category_used": "fragrances",
    "source_urls": [
        "https://shop-a.example/p/u1sentinelpath/sauvage-edp?ref=u1sentineltoken",
        "https://shop-b.example/p/u1sentinelpath/bleu-edp?ref=u1sentineltoken",
    ],
}
B04_AED_BHD_V2_BODY: dict = {
    "success": True,
    "products": [
        {
            "brand": "Dior",
            "name": "Sauvage Eau de Parfum 100ml",
            "full_name": "Sauvage Eau de Parfum 100ml",
            "variant": "EDP 100ml",
            "category": "fragrances",
            "price": {
                "amount": 399,
                "currency": "AED",
                "retailer": "shop-a.example",
                "url": "https://shop-a.example/p/u1sentinelpath/sauvage-edp?ref=u1sentineltoken",
                "in_stock": None,
                "estimate_bhd": 40.858,
                "estimate_basis": "fallback_rate",
            },
            "specs": {},
            "reviews": {"rating": "4.5", "count": "120"},
            "image_url": "https://cdn.shop-a.example/a.jpg",
            "source_url": "https://shop-a.example/p/u1sentinelpath/sauvage-edp?ref=u1sentineltoken",
            "retailer": {
                "key": "unknown",
                "domain": "shop-a.example",
                "name": "shop-a.example",
                "region": "unknown",
                "currency": "USD",
            },
            "pros": ["fresh opening"],
            "cons": ["shorter wear"],
            "rating": 4.5,
            "review_count": 120,
            "link_key": {
                "brand": "Dior",
                "line": "Sauvage",
                "concentration": "EDP",
                "size_ml": 100,
                "gtin": None,
                "resolved": True,
                "source": "lexicon",
            },
        },
        {
            "brand": "Chanel",
            "name": "Bleu de Chanel Eau de Parfum 100ml",
            "full_name": "Bleu de Chanel Eau de Parfum 100ml",
            "variant": "EDP 100ml",
            "category": "fragrances",
            "price": {
                "amount": "45.500",
                "currency": "BHD",
                "retailer": "shop-b.example",
                "url": "https://shop-b.example/p/u1sentinelpath/bleu-edp?ref=u1sentineltoken",
                "in_stock": None,
            },
            "specs": {},
            "reviews": {"rating": "4.8", "count": "300"},
            "image_url": "https://cdn.shop-b.example/b.jpg",
            "source_url": "https://shop-b.example/p/u1sentinelpath/bleu-edp?ref=u1sentineltoken",
            "retailer": {
                "key": "unknown",
                "domain": "shop-b.example",
                "name": "shop-b.example",
                "region": "unknown",
                "currency": "USD",
            },
            "pros": ["long wear"],
            "cons": ["heavier"],
            "rating": 4.8,
            "review_count": 300,
            "link_key": {
                "brand": "Chanel",
                "line": "Bleu de Chanel",
                "concentration": "EDP",
                "size_ml": 100,
                "gtin": None,
                "resolved": True,
                "source": "lexicon",
            },
        },
    ],
    "comparison": {
        "winner_index": 1,
        "winner_declaration": "B",
        "winner_reason": "Bleu lasts longer on skin through the day. It "
        "scores 82/100 overall.",
        "key_tradeoff": "Sauvage opens brighter.",
        "specs_comparison": {
            "product_0_advantages": ["brighter opening"],
            "product_1_advantages": ["longer wear"],
            "similar": ["EDP"],
        },
        "product_0_pros": ["fresh opening", 7, None, "   "],
        "product_0_cons": ["shorter wear"],
        "product_1_pros": ["long wear"],
        "product_1_cons": ["heavier", {"x": 1}],
    },
    "winner_index": 1,
    "recommendation": "Bleu lasts longer on skin through the day.",
    "key_differences": ["brighter opening", "longer wear"],
    "category_used": "fragrances",
    "source_urls": [
        "https://shop-a.example/p/u1sentinelpath/sauvage-edp?ref=u1sentineltoken",
        "https://shop-b.example/p/u1sentinelpath/bleu-edp?ref=u1sentineltoken",
    ],
}
B04_LITERALS = {
    ("sar-sar", None): B04_SAR_SAR_V1_BODY,
    ("sar-sar", "true"): B04_SAR_SAR_V2_BODY,
    ("aed-bhd", None): B04_AED_BHD_V1_BODY,
    ("aed-bhd", "true"): B04_AED_BHD_V2_BODY,
}


@pytest.fixture(autouse=True)
def _u1b_env(monkeypatch):
    monkeypatch.delenv(G, raising=False)
    for name in HOME_AMBIENT:
        monkeypatch.delenv(name, raising=False)
    yield


# ---------------------------------------------------------------------------
# pages and helpers
# ---------------------------------------------------------------------------
def _page_a(price, currency):
    return page(
        "Sauvage EDP | Shop A",
        [
            node(
                "Sauvage Eau de Parfum 100ml",
                brand="Dior",
                price=price,
                currency=currency,
                image="https://cdn.shop-a.example/a.jpg",
                rating="4.5",
                count="120",
            )
        ],
    )


def _page_b(price, currency):
    return page(
        "Bleu EDP | Shop B",
        [
            node(
                "Bleu de Chanel Eau de Parfum 100ml",
                brand="Chanel",
                price=price,
                currency=currency,
                image="https://cdn.shop-b.example/b.jpg",
                rating="4.8",
                count="300",
            )
        ],
    )


USD_PAGE = page(
    "A",
    [node("Sauvage Eau de Parfum 100ml", brand="Dior", price="100", currency="USD")],
)


def _pages(pair):
    if pair == "bhd-bhd":
        return {URL1: ok(PAGE_A), URL2: ok(PAGE_B)}
    if pair == "usd-bhd":
        return {URL1: ok(USD_PAGE), URL2: ok(PAGE_B)}
    (a, code_a), (b, code_b) = PAIRS[pair]
    return {URL1: ok(_page_a(a, code_a)), URL2: ok(_page_b(b, code_b))}


def _num(value):
    return float(value)


def _estimate(amount, code):
    return round(price_service._convert_to_bhd(_num(amount), code), 3)


def _assert_labelled(products, spec):
    """Each price carries its own code and amount; a foreign one its estimate."""
    assert isinstance(products, list) and len(products) >= 2, products
    for product, (amount, code) in zip(products, spec):
        price = product.get("price") or {}
        assert price.get("currency") == code, price
        assert _num(price.get("amount")) == _num(amount), price
        assert "source_method" not in price, price
        assert "unavailable" not in price, price
        if code == "BHD":
            assert "estimate_bhd" not in price, price
        else:
            assert price.get("estimate_bhd") == _estimate(amount, code), price
            assert price.get("estimate_basis") == "fallback_rate", price


def _want_metadata(products):
    names = [
        text_sanitize.dedup_brand_name(p.get("brand"), p.get("name"))
        for p in products[:2]
    ]
    return {"query": f"{names[0]} vs {names[1]}", "input_type": "url"}


def _record_reader(monkeypatch):
    """A call-through recorder on the new reader (added with raising=False at base,
    removed again at teardown): the list of its calls."""
    calls: list = []
    real = getattr(ues, READER, None)

    def rec(*a, **kw):
        calls.append((a, dict(kw)))
        return real(*a, **kw) if callable(real) else False

    monkeypatch.setattr(ues, READER, rec, raising=False)
    return calls


def _compare_and_store(
    monkeypatch, client, *, pages, flag="true", g="true", v2=None, **cfg
):
    """One link compare with the save run for real through
    database_service.save_comparison over a fake insert client (the frozen u10_run
    pattern). Returns (response, harness, inserted records, reader calls)."""
    h = full(monkeypatch, H(), flag=flag, v2=v2, pages=pages, **cfg)
    set_env(monkeypatch, G, g)
    reader_calls = _record_reader(monkeypatch)
    inserted: list = []
    fake = _FakeInsert(inserted)
    monkeypatch.setattr(dbs, "get_supabase_client", lambda *a, **k: fake)

    async def real_save(**kw):
        h.ledger.saves.append(copy.deepcopy(kw))
        return await dbs.save_comparison(
            full_response=kw.get("full_response"),
            query=kw.get("query"),
            input_type=kw.get("input_type"),
            user_id=kw.get("user_id"),
        )

    monkeypatch.setattr(url_routes, "save_comparison_and_track_cohort", real_save)
    h.ledger.run_saves = True
    resp = call(client)
    for coro in h.ledger.pending:
        asyncio.run(coro)
    return resp, h, inserted, reader_calls


def _reader():
    fn = getattr(ues, READER, None)
    assert callable(
        fn
    ), "INC-U1b: url_extraction_service._link_foreign_history_ok missing"
    return fn


def _adapter_case(code0="SAR", amount0=450, name0="Sauvage EDP"):
    """A pure-adapter input: product 0 priced in ``code0`` (None: no stated code),
    product 1 a BHD price."""
    products = [
        {
            "name": name0,
            "brand": "Dior",
            "price": {"amount": amount0, "currency": code0 or "BHD"},
        },
        {
            "name": "Bleu de Chanel EDP",
            "brand": "Chanel",
            "price": {"amount": "45.500", "currency": "BHD"},
        },
    ]
    extras = [{"currency_code": code0}, {"currency_code": "BHD"}]
    return {"products": products, "comparison": {}}, extras


def _bhd_amounts(full_response):
    w = full_response["winner_index"]
    products = full_response["products"]
    return (
        _num(products[w]["price"]["amount"]),
        _num(products[1 - w]["price"]["amount"]),
    )


# ===========================================================================
# B01 the reader (RED)
# ===========================================================================
@pytest.mark.parametrize(
    "value,expected",
    [(v, True) for v in ON_VALUES] + [(v, False) for v in OFF_VALUES],
)
def test_b01_reader_house_idiom_and_home_parity(monkeypatch, value, expected):
    """RED B01: _link_foreign_history_ok() is the house idiom over
    ENABLE_SMART_PICK_BHD_ONLY: ON for the five ON spellings, OFF for the seven OFF
    spellings, and equal to home_routes.smart_pick_bhd_only_enabled() on all twelve."""
    reader = _reader()
    set_env(monkeypatch, G, value)
    assert reader() is expected, (value, reader())
    assert reader() is home_routes.smart_pick_bhd_only_enabled(), value


def test_b01b_reader_reads_the_guard_name_per_call_and_no_api_module(monkeypatch):
    """RED B01b: the reader takes no argument, reads the guard name (never the link
    flag) on every call (no import-time cache) and names no app.api module."""
    reader = _reader()
    assert not inspect.signature(reader).parameters, inspect.signature(reader)
    set_env(monkeypatch, FLAG, "true")
    set_env(monkeypatch, G, None)
    assert reader() is False, "INC-U1b: the reader follows the link flag"
    set_env(monkeypatch, FLAG, None)
    set_env(monkeypatch, G, "true")
    assert reader() is True
    set_env(monkeypatch, G, "false")
    assert reader() is False, "INC-U1b: the reader is cached"
    set_env(monkeypatch, G, "on")
    assert reader() is True, "INC-U1b: the reader is cached"
    tree = ast.parse(textwrap.dedent(inspect.getsource(reader)))
    lazy = [n for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom))]
    assert lazy == [], "INC-U1b: the reader imports (Q5: its own env read)"


# ===========================================================================
# B02 the lift: L ON + G ON (RED)
# ===========================================================================
B02_CASES = [
    pytest.param("sar-sar", None, "true", id="sar-sar"),
    pytest.param("aed-aed", None, "true", id="aed-aed"),
    pytest.param("sar-bhd", None, "true", id="sar-bhd"),
    pytest.param("bhd-aed", None, "true", id="bhd-aed"),
    pytest.param("kwd-bhd", None, "true", id="kwd-bhd"),
    pytest.param("sar-bhd", "true", "true", id="sar-bhd-v2"),
    pytest.param("sar-sar", None, " TRUE ", id="sar-sar-padded-on"),
]


@pytest.mark.parametrize("pair,v2,g", B02_CASES)
def test_b02_lifted_foreign_pair_carries_metadata_and_is_stored(
    monkeypatch, client, pair, v2, g
):
    """RED B02: L ON and G ON, a pair with a kept foreign price ships metadata {query
    "<p0> vs <p1>" (dedup_brand_name), input_type url}; ONE save with the same
    metadata, the stripped _url_log_query and input_type url, renderable, and stored
    by database_service.save_comparison; the saved prices keep their code, amount and
    estimate_bhd; the reader ran once."""
    resp, h, inserted, reader_calls = _compare_and_store(
        monkeypatch, client, pages=_pages(pair), v2=v2, g=g
    )
    body, products = products_of(resp)
    _unit_ran(h)
    want = _want_metadata(products)
    assert body.get("metadata") == want, ("INC-U1b: rule F holds", body.get("metadata"))
    _assert_labelled(products, PAIRS[pair])
    assert len(h.ledger.saves) == 1, h.ledger.saves
    saved = h.ledger.saves[0]
    assert (saved.get("full_response") or {}).get("metadata") == want, saved
    assert saved.get("query") == url_routes._url_log_query(URL1, URL2), saved
    assert saved.get("input_type") == "url", saved
    assert dbs._validate_renderable(saved.get("full_response")) is True
    assert len(inserted) == 1, inserted
    row = inserted[0]
    assert row["full_response"]["metadata"] == want, row
    assert row["query"] == url_routes._url_log_query(URL1, URL2), row
    assert row["input_type"] == "url", row
    _assert_labelled(row["full_response"]["products"], PAIRS[pair])
    assert len(reader_calls) == 1, reader_calls
    _link_on()


# ===========================================================================
# B03 the stored foreign row is skipped by every reader (RED, ORCH-U1-A)
# ===========================================================================
@pytest.mark.parametrize("pair", ["sar-sar", "sar-bhd"])
def test_b03_stored_foreign_row_skipped_by_smart_pick_and_both_savings(
    monkeypatch, client, pair
):
    """RED B03: a stored B02 row (G ON): _select_smart_pick([], [foreign]) is None and
    [foreign, bhd] picks the BHD control; Home and profile _extract_winner_loser_prices
    give (None, None) on it and the amounts on the control; with G OFF the stored row
    IS the smart pick with its foreign amounts as BHD figures (stated limit S1)."""
    resp, _h, inserted, _ = _compare_and_store(monkeypatch, client, pages=_pages(pair))
    products_of(resp)
    assert len(inserted) == 1, ("INC-U1b: the foreign link pair was not stored", pair)
    foreign_full = copy.deepcopy(inserted[0]["full_response"])
    resp_c, _hc, inserted_c, _ = _compare_and_store(
        monkeypatch, client, pages=_pages("bhd-bhd")
    )
    products_of(resp_c)
    assert len(inserted_c) == 1, inserted_c
    control_full = copy.deepcopy(inserted_c[0]["full_response"])
    foreign = {
        "id": "u1b-row-foreign",
        "full_response": foreign_full,
        "created_at": NEWER,
    }
    control = {"id": "u1b-row-bhd", "full_response": control_full, "created_at": OLDER}
    readers = (
        home_routes._extract_winner_loser_prices,
        profile_routes._extract_winner_loser_prices,
    )
    set_env(monkeypatch, G, "true")
    assert home_routes._select_smart_pick([], [foreign]) is None
    pick = home_routes._select_smart_pick([], [foreign, control])
    assert pick is not None and pick["comparison_id"] == "u1b-row-bhd", pick
    for reader in readers:
        assert reader(foreign_full) == (None, None), reader.__module__
        assert reader(control_full) == _bhd_amounts(control_full), reader.__module__
    set_env(monkeypatch, G, None)
    shown = home_routes._select_smart_pick([], [foreign])
    assert shown is not None and shown["comparison_id"] == "u1b-row-foreign", shown
    w = foreign_full["winner_index"]
    winner_amount = foreign_full["products"][w]["price"]["amount"]
    loser_amount = foreign_full["products"][1 - w]["price"]["amount"]
    assert shown["winner_price_bhd"] == _num(winner_amount), shown
    assert shown["runner_up_price_bhd"] == _num(loser_amount), shown
    for reader in readers:
        assert reader(foreign_full) == (None, None), reader.__module__


# ===========================================================================
# B04 mix L on / G off: rule F as frozen (PIN, B1)
# ===========================================================================
@pytest.mark.parametrize("v2", [None, "true"])
@pytest.mark.parametrize("pair", ["sar-sar", "aed-bhd"])
@pytest.mark.parametrize("g", OFF_VALUES)
def test_b04_mix_l_on_g_off_keeps_rule_f(monkeypatch, client, g, pair, v2):
    """PIN B04: L ON with G in each OFF spelling (the guard, gate, resolver and egress
    stop ON; V1 and V2): the body equals the base literal (rule F byte-identical), the
    prices are labelled with their own code, no metadata.query, the one save carries
    none and is not renderable."""
    h = full(monkeypatch, H(), flag="true", v2=v2, pages=_pages(pair), **FULL_ON)
    set_env(monkeypatch, G, g)
    body, products = products_of(call(client))
    _unit_ran(h)
    want = B04_LITERALS[(pair, v2)]
    assert want, ("literal not measured", pair, v2)
    assert body == want, body
    _assert_labelled(products, PAIRS[pair])
    assert "query" not in (body.get("metadata") or {}), body.get("metadata")
    assert len(h.ledger.saves) == 1, h.ledger.saves
    for saved in h.ledger.saves:
        meta = (saved.get("full_response") or {}).get("metadata") or {}
        assert "query" not in meta, saved
        assert dbs._validate_renderable(saved.get("full_response")) is False, saved
    assert h.retry_calls == [], h.retry_calls
    _link_on()


# ===========================================================================
# B05 mix L off / G on and B12 mix L off / G off: no link row at all (PIN, B1)
# ===========================================================================
_L_OFF_LITERALS = {
    ("sar-bhd", None): B05_SAR_V1_BODY,
    ("sar-bhd", "true"): B05_SAR_V2_BODY,
    ("bhd-bhd", None): P01_BODY,
    ("bhd-bhd", "true"): P02_BODY,
}


def _l_off_row(monkeypatch, client, caplog, *, flag, g, v2, pair):
    caplog.set_level(logging.INFO)
    h = full(monkeypatch, H(), flag=flag, v2=v2, pages=_pages(pair), **FULL_ON)
    set_env(monkeypatch, G, g)
    reader_calls = _record_reader(monkeypatch)
    resp = call(client)
    assert resp.status_code == 200, (resp.status_code, resp.text[:300])
    want = _L_OFF_LITERALS[(pair, v2)]
    assert want, ("literal not measured", pair, v2)
    assert resp.json() == want, resp.json()
    assert len(h.ledger.saves) == 1, h.ledger.saves
    assert h.ledger.saves[0].get("query") == f"{URL1} vs {URL2}", h.ledger.saves[0]
    assert h.retry_calls == [] and h.resolver_calls == [], (
        h.retry_calls,
        h.resolver_calls,
    )
    assert all(c["kwargs"].get("link_result") is not True for c in h.cfu_calls)
    _assert_base_requests(h)
    assert page_reads(caplog) == []
    assert reader_calls == [], reader_calls


@pytest.mark.parametrize("v2", [None, "true"])
@pytest.mark.parametrize("pair", ["sar-bhd", "bhd-bhd"])
@pytest.mark.parametrize("g", G_MIX_ON)
@pytest.mark.parametrize("flag", OFF_VALUES)
def test_b05_mix_l_off_g_on_body_is_the_base_literal(
    monkeypatch, client, caplog, flag, g, pair, v2
):
    """PIN B05: L in each OFF spelling with G ON (the guard, gate, resolver and egress
    stop ON; V1 and V2): the body equals the base literal (sar-bhd measured here,
    bhd-bhd the frozen P01 / P02 literals), the save query is f"{url1} vs {url2}", no
    URL_PAGE_READ line, and the new reader is never called."""
    _l_off_row(monkeypatch, client, caplog, flag=flag, g=g, v2=v2, pair=pair)


@pytest.mark.parametrize("v2", [None, "true"])
@pytest.mark.parametrize("g", OFF_VALUES)
@pytest.mark.parametrize("flag", OFF_VALUES)
def test_b12_mix_l_off_g_off_body_is_the_base_literal(
    monkeypatch, client, caplog, flag, g, v2
):
    """PIN B12 (UB-11): L and G each in every OFF spelling (the full configuration; V1
    and V2): the sar-bhd body equals the base literal; no reader call."""
    _l_off_row(monkeypatch, client, caplog, flag=flag, g=g, v2=v2, pair="sar-bhd")


# ===========================================================================
# B06..B10 mix L on / G on: what the lift never changes (PIN)
# ===========================================================================
B06_CASES = [
    pytest.param(
        {URL1: ok(_page_a("25", None)), URL2: ok(_page_b(520, "SAR"))},
        URL1,
        id="unknown-shop-beside-sar",
    ),
    pytest.param({AMZ_TR: ok(AMZ_PAGE), URL2: ok(PAGE_B)}, AMZ_TR, id="amazon-com-tr"),
    pytest.param(
        {AMZ_TR: ok(AMZ_PAGE), URL2: ok(_page_b(520, "SAR"))},
        AMZ_TR,
        id="amazon-com-tr-beside-sar",
    ),
]


@pytest.mark.parametrize("pages,url1", B06_CASES)
def test_b06_pending_unknown_currency_stays_out_under_the_lift(
    monkeypatch, client, pages, url1
):
    """PIN B06 (FX-1): G ON, an unknown shop without a stated currency and
    amazon.com.tr: the price is pending currency_unknown and the pair carries no
    metadata.query (no save carries one)."""
    h = full(monkeypatch, H(), pages=pages)
    set_env(monkeypatch, G, "true")
    body, products = products_of(call(client, url1=url1, url2=URL2))
    _unit_ran(h)
    _pending_currency_unknown(products[0].get("price") or {})
    _no_history_query(body, h)
    _link_on()


@pytest.mark.parametrize("placeholder_first", [True, False], ids=["first", "second"])
def test_b07_placeholder_name_stays_out_under_the_lift(
    monkeypatch, client, placeholder_first
):
    """PIN B07 (FX-3): G ON, an "Unknown Product" beside a kept SAR price (result gate
    OFF): a 200 with no metadata.query and no save carrying one."""
    if placeholder_first:
        pages = {URL1: ok(EMPTY_PAGE), URL2: ok(_page_b(520, "SAR"))}
    else:
        pages = {URL1: ok(_page_a(450, "SAR")), URL2: ok(EMPTY_PAGE)}
    h = full(monkeypatch, H(), pages=pages)
    set_env(monkeypatch, G, "true")
    resp = call(client)
    _unit_ran(h)
    assert resp.status_code == 200, (resp.status_code, resp.text[:300])
    body = resp.json()
    products = body.get("products") or []
    assert "Unknown Product" in [p.get("name") for p in products], products
    codes = [(p.get("price") or {}).get("currency") for p in products]
    assert "SAR" in codes, codes
    _no_history_query(body, h)
    _link_on()


@pytest.mark.parametrize("pair", ["sar-sar", "sar-bhd"])
def test_b08_degraded_verdict_writes_no_metadata_under_the_lift(
    monkeypatch, client, pair
):
    """PIN B08: G ON, an error dict with the egress stop OFF: the degraded 200 (the
    credit kept) carries no metadata and no save carries a query."""
    h = full(monkeypatch, H(), verdict=VERDICT_ERROR, pages=_pages(pair))
    set_env(monkeypatch, G, "true")
    body, products = products_of(call(client))
    _unit_ran(h)
    assert (body.get("comparison") or {}).get("error"), body.get("comparison")
    assert "metadata" not in body, body.get("metadata")
    _no_history_query(body, h)
    _assert_labelled(products, PAIRS[pair])
    assert h.ledger.refunds == [], h.ledger.refunds
    _link_on()


@pytest.mark.parametrize("v2", [None, "true"])
@pytest.mark.parametrize("g", ["true"] + OFF_VALUES)
@pytest.mark.parametrize("pair", ["bhd-bhd", "usd-bhd"])
def test_b09_bhd_kinds_keep_their_metadata_in_every_guard_state(
    monkeypatch, client, pair, g, v2
):
    """PIN B09: L ON, a BHD / BHD pair and a USD (converted_usd) / BHD pair, G ON and in
    each OFF spelling (B1: the guard, gate, resolver and egress stop ON; V1 and V2):
    metadata {query, input_type url} present, one save with it and the stripped
    query."""
    h = full(monkeypatch, H(), v2=v2, pages=_pages(pair), **FULL_ON)
    set_env(monkeypatch, G, g)
    body, products = products_of(call(client))
    _unit_ran(h)
    want = _want_metadata(products)
    assert body.get("metadata") == want, body.get("metadata")
    assert len(h.ledger.saves) == 1, h.ledger.saves
    saved = h.ledger.saves[0]
    assert (saved.get("full_response") or {}).get("metadata") == want, saved
    assert saved.get("query") == url_routes._url_log_query(URL1, URL2), saved
    for p in products:
        assert (p.get("price") or {}).get("currency") == "BHD", p
    if pair == "usd-bhd":
        price = products[0].get("price") or {}
        assert price.get("source_method") == "converted_usd", price
    _link_on()


@pytest.mark.parametrize("v2", [None, "true"])
def test_b10_u10_lifted_compare_logs_no_link_path_or_query(
    monkeypatch, client, caplog, v2
):
    """PIN B10 (U-10): L ON and G ON, a SAR pair whose first page times out once (one
    ordinary retry), the save run for real: no captured record carries the sentinel
    path segment or query token; the curl helper is never called."""
    caplog.set_level(logging.INFO)
    monkeypatch.setattr(logging.getLogger("httpx"), "level", logging.WARNING)
    monkeypatch.setattr(logging.getLogger("httpcore"), "level", logging.WARNING)
    (a, code_a), (b, code_b) = PAIRS["sar-sar"]
    pages = {
        URL1: [httpx.ReadTimeout, ok(_page_a(a, code_a))],
        URL2: ok(_page_b(b, code_b)),
    }
    resp, h, _inserted, _ = _compare_and_store(monkeypatch, client, pages=pages, v2=v2)
    products_of(resp)
    _unit_ran(h)
    assert len([r for r in h.pages.requests if r["url"] == URL1]) == 2, h.pages.requests
    assert h.retry_calls == [], h.retry_calls
    assert len(h.ledger.saves) == 1, h.ledger.saves
    u10_assert_no_link_text(caplog)
    _link_on()


# ===========================================================================
# B11 the savings RPC filter (PIN)
# ===========================================================================
def test_b11_rpc_filter_keeps_both_bhd_currency_lines():
    """PIN B11: migrations/036_home_savings_aggregate.sql keeps both BHD currency
    lines (:76-77), so ENABLE_HOME_SAVINGS_AGGREGATE skips a foreign row as the scan
    does."""
    root = pathlib.Path(__file__).resolve().parents[1]
    sql = root / "migrations" / "036_home_savings_aggregate.sql"
    lines = sql.read_text(encoding="utf-8").splitlines()
    assert lines[75].strip() == (
        "WHERE products -> widx -> 'price' ->> 'currency' = 'BHD'"
    ), lines[75]
    assert lines[76].strip() == (
        "AND products -> (1 - widx) -> 'price' ->> 'currency' = 'BHD'"
    ), lines[76]


# ===========================================================================
# B13 / B14 the adapter keyword (RED) and its default (PIN)
# ===========================================================================
def test_b13_adapter_takes_keyword_only_foreign_history_default_false():
    """RED B13: _link_result_adapt and _link_result_adapt_inner take a keyword-only
    foreign_history (default False); True lifts a kept foreign price, while a pending
    unknown currency, a placeholder name and a degraded verdict still write no
    metadata."""
    for name in ("_link_result_adapt", "_link_result_adapt_inner"):
        fn = getattr(ues, name, None)
        assert callable(fn), name
        param = inspect.signature(fn).parameters.get("foreign_history")
        assert param is not None, (name, "INC-U1b: no foreign_history keyword")
        assert param.kind is inspect.Parameter.KEYWORD_ONLY, (name, param.kind)
        assert param.default is False, (name, param.default)
    body, extras = _adapter_case()
    lifted = ues._link_result_adapt(body, extras, False, foreign_history=True)
    assert lifted.get("metadata") == _want_metadata(lifted["products"]), lifted
    assert lifted["products"][0]["price"].get("currency") == "SAR", lifted
    held = [
        (_adapter_case(code0=None, amount0=25), False),
        (_adapter_case(name0="Unknown Product"), False),
        (_adapter_case(), True),
    ]
    for (case_body, case_extras), degraded in held:
        out = ues._link_result_adapt(
            case_body, case_extras, degraded, foreign_history=True
        )
        assert "metadata" not in out, (degraded, out.get("metadata"))


def test_b14_three_positional_call_keeps_rule_f_whatever_the_guard_reads(monkeypatch):
    """PIN B14 (the FX-3b default): with both switches ON in the environment, the
    three-positional call (tests/test_inc_u1_fix1.py) of _link_result_adapt keeps rule
    F for a kept SAR price and still writes the BHD pair; the service names no app.api
    module."""
    set_env(monkeypatch, FLAG, "true")
    set_env(monkeypatch, G, "true")
    fn = getattr(ues, "_link_result_adapt", None)
    assert callable(fn), "INC-U1: _link_result_adapt missing"
    body, extras = _adapter_case()
    out = fn(body, extras, False)
    assert "metadata" not in out, out.get("metadata")
    assert out["products"][0]["price"].get("currency") == "SAR", out
    bhd_body, bhd_extras = _adapter_case(code0="BHD", amount0="30.000")
    bhd = fn(bhd_body, bhd_extras, False)
    assert bhd.get("metadata") == _want_metadata(bhd["products"]), bhd
    tree = ast.parse(inspect.getsource(ues))
    modules = [n.module or "" for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)]
    modules += [
        a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names
    ]
    api = [m for m in modules if m == "app.api" or m.startswith("app.api.")]
    assert api == [], api
