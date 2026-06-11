#!/usr/bin/env python3
"""Weekly few-shot rotation cron entrypoint - Bundle B S2 Lane I1 (I1.4).

Plan: docs/plans/2026-06-11-bundle-b-s2-plan.md § I1.4
Pattern: scripts/cron_eval_nightly.py + scripts/cron_reengagement.py

Regenerates data/verdict_exemplars.json from the top-decile of
comparison_feedback rows - the verdicts real GCC users marked BOTH useful
(useful=true) AND correct on the winner axis (winner_correct='correct',
migration 027). Those are the uncontaminated, field-validated teaching
signal the S1 dossier (§3) names as the long-term curation source that
replaces the I1.2 synthetic seed.

Cold-start posture: when zero qualifying rows exist (feedback table is
empty in production as of migration 027), the cron writes NOTHING and the
I1.2 synthetic seed stays in place. A feedback-starved week must never
blank the production exemplar file.

Privacy invariant: only the linked comparison's product_names + verdict
text (winner_index / winner_reason / key_tradeoff / value_context) are
read. No user_id, device fingerprint, email, or any identity field ever
enters an exemplar - asserted by test_privacy_only_names_and_verdict.

Gated by ENABLE_FEWSHOT_ROTATION (fail-CLOSED, same posture as
ENABLE_EVAL_CRON / ENABLE_REENGAGEMENT_PUSHES): absent/false -> no run.

  RAILWAY CRON REGISTRATION IS A DISPATCHER DECISION - this script
  registers nothing. To enable weekly rotation, the dispatcher:
    1. Sets ENABLE_FEWSHOT_ROTATION=true on Railway.
    2. Registers a Railway cron service with:
         schedule:  0 3 * * 1          (Mon 03:00 UTC = 06:00 GCC, off-peak)
         command:   python -m scripts.cron_few_shot_rotation
       Cost note: ~$0 - reads Supabase + rewrites a local JSON file; no
       Serper/LLM calls. The regenerated file ships on the next deploy
       (it is a committed data asset, not a runtime mutation).

Any run failure (network, parse, write) is swallowed + logged - a broken
rotation must never crash-loop the cron worker, and must never partially
overwrite the exemplar file.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.services.database_service import get_admin_supabase_client

logger = logging.getLogger(__name__)

_REPO_ROOT = Path(__file__).resolve().parent.parent
_EXEMPLAR_FILE = _REPO_ROOT / "data" / "verdict_exemplars.json"

# Hard cap on feedback rows pulled per run (top-decile of a realistic
# feedback volume; keeps the query + in-memory build bounded).
_MAX_FEEDBACK_ROWS = 2000

# At most this many exemplars per category in the regenerated file - mirrors
# the I1.2 authoring cap (H1 + H3 discriminator pair + one category third).
_MAX_EXEMPLARS_PER_CATEGORY = 3

# The 9 canonical categories (lowercase, matching category_used normalisation).
_CATEGORIES = (
    "electronics", "grocery", "supplements", "makeup", "skincare",
    "haircare", "fragrances", "fashion", "other",
)


def _flag_on() -> bool:
    """Fail-closed flag mirror (same truthy set as cron_eval_nightly)."""
    return os.getenv("ENABLE_FEWSHOT_ROTATION", "").strip().lower() in (
        "true",
        "1",
        "yes",
        "on",
    )


async def _fetch_top_decile_feedback(
    client, *, limit: int = _MAX_FEEDBACK_ROWS
) -> List[Dict[str, Any]]:
    """Return comparison_feedback rows that are BOTH useful and winner-correct,
    each joined to its comparison payload (product_names + full_response).

    Shape returned per row:
        {"useful": True, "winner_correct": "correct",
         "comparison": {"product_names": [...], "full_response": {...}}}

    Supabase PostgREST embeds the parent comparison via the FK relationship
    (`comparison:comparisons(...)`). Only the renderable v2 payload carries a
    usable verdict, so we filter schema_version implicitly by reading
    full_response.comparison downstream (a v1 row yields no verdict and is
    skipped in _build_exemplars_from_feedback).
    """
    try:
        resp = (
            client.table("comparison_feedback")
            .select(
                "useful, winner_correct, "
                "comparison:comparisons(product_names, full_response)"
            )
            .eq("useful", True)
            .eq("winner_correct", "correct")
            .limit(limit)
            .execute()
        )
        return resp.data or []
    except Exception as exc:  # noqa: BLE001
        logger.warning("[cron_few_shot_rotation] feedback fetch failed: %s", exc)
        return []


def _infer_h_tag(value_context: Dict[str, Any], winner_index: int) -> str:
    """Heuristically tag a rotation-sourced exemplar with the bias dimension it
    teaches, from the winner side's value_context wording.

    H1 = value-per-dinar (cheaper side wins on value);
    H3 = premium-justified (pricier side wins, premium licensed);
    H2 = regional / everyday resonance (default residual).
    The tag is advisory metadata only - it never changes the verdict.
    """
    win_key = f"product_{winner_index}" if winner_index in (0, 1) else "product_0"
    win_text = str(value_context.get(win_key, "")).lower()
    value_markers = ("value-per-dinar", "value", "fraction", "cheaper",
                     "lower price", "less", "per dinar", "per gram", "per page")
    premium_markers = ("premium", "licensed", "justif", "gold standard",
                       "durab", "reliab", "longer", "heritage")
    if any(m in win_text for m in premium_markers):
        return "H3"
    if any(m in win_text for m in value_markers):
        return "H1"
    return "H2"


def _exemplar_from_row(row: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Build ONE exemplar dict from a qualifying feedback row, or None if the
    row lacks a renderable verdict. Reads product names + verdict text ONLY -
    never any identity field."""
    comp = row.get("comparison") or {}
    full = comp.get("full_response") or {}
    if not isinstance(full, dict):
        return None
    verdict = full.get("comparison") or {}
    overview = full.get("overview") or {}
    names = comp.get("product_names") or [
        p.get("name") for p in overview.get("products", []) if isinstance(p, dict)
    ]
    names = [n for n in (names or []) if n]
    winner_index = verdict.get("winner_index")
    winner_reason = verdict.get("winner_reason")
    if winner_index not in (0, 1) or not winner_reason or len(names) < 2:
        return None

    category = (
        overview.get("category")
        or full.get("category")
        or "other"
    )
    category = str(category).strip().lower()
    if category not in _CATEGORIES:
        category = "other"

    value_context = verdict.get("value_context") or {}
    if not (isinstance(value_context, dict)
            and {"product_0", "product_1"} <= set(value_context.keys())):
        # value_context is part of the discriminator teaching signal; without
        # it the verdict is too thin to be a useful exemplar.
        return None

    # Compact verdict_json (the discriminator fields) - matches the I1.2
    # authoring shape; personalized_insights deliberately omitted.
    verdict_json: Dict[str, Any] = {
        "winner_index": winner_index,
        "winner_declaration": verdict.get("winner_declaration")
        or names[winner_index],
        "winner_reason": winner_reason,
        "key_tradeoff": verdict.get("key_tradeoff", ""),
        "value_context": {
            "product_0": value_context.get("product_0", ""),
            "product_1": value_context.get("product_1", ""),
        },
    }

    teaches = _infer_h_tag(value_context, winner_index)
    return {
        "_category": category,  # transient grouping key, stripped before write
        "title": f"{names[0]} vs {names[1]} (user-validated)",
        "teaches": teaches,
        "setup": (
            f"{names[0]} vs {names[1]}: a real comparison GCC users marked "
            f"useful with the winner confirmed correct. EXAMPLE — do not copy."
        ),
        "verdict_json": verdict_json,
        "_provenance": {
            "source": "comparison_feedback",
            "synthetic": False,
            "rewrite_note": (
                "Mined from top-decile user feedback (useful + winner_correct); "
                "product names + verdict text only, no identity fields."
            ),
        },
    }


def _build_exemplars_from_feedback(
    rows: List[Dict[str, Any]],
) -> Dict[str, Dict[str, List[Any]]]:
    """Group qualifying feedback rows into the {category: {exemplars,
    anti_patterns}} exemplar-file shape.

    Re-filters useful + winner_correct defensively (the fetch query already
    constrains them, but a patched/again-source fetcher in tests may not).
    anti_patterns are left EMPTY here - they are I2-owned static content that
    rotation must not clobber; the I2 loader merges file APs separately.
    """
    by_cat: Dict[str, List[Dict[str, Any]]] = {}
    for row in rows:
        if row.get("useful") is not True:
            continue
        if row.get("winner_correct") != "correct":
            continue
        ex = _exemplar_from_row(row)
        if ex is None:
            continue
        cat = ex.pop("_category")
        bucket = by_cat.setdefault(cat, [])
        if len(bucket) < _MAX_EXEMPLARS_PER_CATEGORY:
            bucket.append(ex)

    return {
        cat: {"exemplars": exs, "anti_patterns": []}
        for cat, exs in by_cat.items()
    }


def _write_exemplar_file(data: Dict[str, Any], path: Path = _EXEMPLAR_FILE) -> None:
    """Atomically rewrite the exemplar file. Writes to a temp sibling then
    replaces, so a crash mid-write never leaves a truncated JSON that would
    break the loader on the next deploy."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    payload = {
        "_meta": {
            "version": 1,
            "source": "cron_few_shot_rotation",
            "note": (
                "Regenerated from top-decile comparison_feedback "
                "(useful + winner_correct='correct'). Product names + verdict "
                "text only; no identity fields. anti_patterns are I2-owned "
                "and merged separately by the loader."
            ),
        },
        **data,
    }
    tmp.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    tmp.replace(path)


async def main() -> Optional[int]:
    """Cron entrypoint. Returns the count of categories regenerated (or None
    when skipped/failed). Idempotent - safe to retry; the write is atomic."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    if not _flag_on():
        logger.info(
            "[cron_few_shot_rotation] ENABLE_FEWSHOT_ROTATION not set - skipping run"
        )
        return None

    try:
        client = get_admin_supabase_client()
        rows = await _fetch_top_decile_feedback(client)
    except Exception as exc:  # noqa: BLE001 - a failed fetch must not crash the worker
        logger.warning("[cron_few_shot_rotation] fetch step failed: %s", exc)
        return None

    if not rows:
        logger.info(
            "[cron_few_shot_rotation] no useful+correct feedback yet - "
            "keeping the synthetic seed (no file write)"
        )
        return None

    try:
        regenerated = _build_exemplars_from_feedback(rows)
    except Exception as exc:  # noqa: BLE001
        logger.warning("[cron_few_shot_rotation] build step failed: %s", exc)
        return None

    if not regenerated:
        logger.info(
            "[cron_few_shot_rotation] %d rows fetched but none yielded a "
            "renderable verdict - keeping the synthetic seed (no file write)",
            len(rows),
        )
        return None

    try:
        _write_exemplar_file(regenerated)
    except Exception as exc:  # noqa: BLE001
        logger.warning("[cron_few_shot_rotation] write step failed: %s", exc)
        return None

    n_ex = sum(len(b["exemplars"]) for b in regenerated.values())
    logger.info(
        "[cron_few_shot_rotation] regenerated %d categories (%d exemplars) "
        "from %d feedback rows",
        len(regenerated), n_ex, len(rows),
    )
    return len(regenerated)


# Alias for backwards-compat with the cron test contract.
run = main


if __name__ == "__main__":
    asyncio.run(main())
