"""LIVE-VERIFY probe — nasserpharmacy.com adapter (Wave 3b, verify-or-omit gate).

Out-of-band (NOT a unit test). Fires a SINGLE real GET to the nasser JSON search
API and confirms the static guest token still authenticates + the matcher pulls a
genuine native-BHD price. The adapter ships ONLY if this reproduces a real amount.

Re-run on deploy: the guest token is a static const baked into the app bundle and
ROTATES on a FE redeploy (F3b — the one live-credential risk). A 401 here means
re-scrape main.<hash>.js for the new token.

Usage:  python .qa-bh-sourcing/_verify_nasser.py
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.price_service import fetch_nasser_price  # noqa: E402


async def main() -> int:
    queries = [
        "Cerave Foaming Cleanser",
        "Cetaphil Gentle Skin Cleanser",
    ]
    any_genuine = False
    for q in queries:
        price = await fetch_nasser_price(q, "BHD")
        if price and price.get("amount") and price.get("source_method") == "local_bhd":
            any_genuine = True
            print(
                f"[GENUINE] '{q}' -> {price['amount']} {price['currency']} "
                f"(local_bhd) {price.get('url', '')}"
            )
        else:
            print(f"[MISS] '{q}' -> {price}")
    if any_genuine:
        print("\nVERDICT: GO — nasser returns genuine native-BHD prices (token live).")
        return 0
    print("\nVERDICT: NO-GO — no genuine BHD (token rotated? re-scrape main.*.js).")
    return 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
