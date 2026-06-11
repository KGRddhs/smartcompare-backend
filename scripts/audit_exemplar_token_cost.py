#!/usr/bin/env python3
"""I1.5 — few-shot exemplar token / cost audit (Bundle B S2 Lane I1).

Plan: docs/plans/2026-06-11-bundle-b-s2-plan.md § I1.5
Dossier budget: §3 — compact exemplars (~150-250 tok each, ~700 tok/category)
add ~+$0.002/call to the verdict prompt; full-schema exemplars (~1,200 tok)
were rejected.

Measures the REAL verdict-prompt delta with exemplars ON vs OFF, per category:
  base  = build_verdict_prompt(products=[{category}])  (no exemplars merged)
  block = verdict_exemplar_loader.build_exemplar_block(category)
and reports tokens + the per-call cost the block adds at the gpt-4o input
rate. Asserts the worst category stays within the +$0.002/call gate.

Re-runnable evidence: the dispatcher can run this at G3 / G6 to confirm the
budget claim against the committed data/verdict_exemplars.json.

Usage:
    python -m scripts.audit_exemplar_token_cost
    python -m scripts.audit_exemplar_token_cost --file path/to/exemplars.json

No network, no API calls — pure local token accounting.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Callable, Dict, List, Optional

_REPO_ROOT = Path(__file__).resolve().parent.parent
_CANONICAL = _REPO_ROOT / "data" / "verdict_exemplars.json"

# gpt-4o input price, USD per 1K tokens (verdict routes priority="high" -> 4o).
_USD_PER_1K_INPUT_4O = 0.0025
# The dossier §3 gate: exemplar prefill must add <= this per call.
_COST_GATE_USD = 0.002
# Per-category exemplar-block token budget (dossier §3).
_TOK_BUDGET = 700

CATEGORIES = (
    "electronics", "grocery", "supplements", "makeup", "skincare",
    "haircare", "fragrances", "fashion", "other",
)


def _token_counter() -> Callable[[str], int]:
    try:
        import tiktoken
        enc = tiktoken.encoding_for_model("gpt-4o")
        return lambda s: len(enc.encode(s))
    except Exception:  # pragma: no cover
        return lambda s: len(s) // 4


def _render_block_standalone(content: Dict, category: str) -> str:
    """Render a category's exemplar block WITHOUT importing the loader — used
    when --file points at a not-yet-committed content file (e.g. the assembled
    draft before G3). Mirrors verdict_exemplar_loader.build_exemplar_block so
    the token count matches what production will inject."""
    entry = content.get(category)
    if not isinstance(entry, dict):
        return ""
    exemplars = entry.get("exemplars") or []
    anti_patterns = entry.get("anti_patterns") or []
    if not exemplars and not anti_patterns:
        return ""
    lines: List[str] = [
        "",
        "## Verdict calibration examples (Bahrain-buyer reasoning)",
        "The examples below are synthetic teaching cases. Mirror the REASONING",
        "MOVE they demonstrate (when value-per-dinar wins vs when a premium is",
        "licensed; how a Bahrain buyer weighs local availability and Gulf",
        "climate) -- never copy their brands, numbers, or wording.",
        "",
    ]
    if anti_patterns:
        lines.append("Avoid these failure modes:")
        for ap in anti_patterns:
            name, rule = ap.get("name"), ap.get("rule")
            if name and rule:
                lines.append(f"- ANTI-PATTERN -- {name}: {rule}")
        lines.append("")
    for ex in exemplars:
        lines.append(
            f"EXAMPLE (do not copy -- teaches the reasoning move only): "
            f"{ex.get('title', '')}"
        )
        if ex.get("setup"):
            lines.append(f"Setup: {ex['setup']}")
        if ex.get("verdict_json") is not None:
            lines.append(
                "Verdict: "
                + json.dumps(ex["verdict_json"], sort_keys=True, ensure_ascii=False)
            )
        lines.append("")
    return "\n".join(lines)


def _block_renderer(content: Dict) -> Callable[[str], str]:
    """Prefer the real loader when the canonical file is what we're auditing
    (keeps the audit honest about the production code path); otherwise render
    standalone from the provided content."""
    try:
        from app.services import verdict_exemplar_loader as loader
        # Point the loader at the same content we loaded, then use its render.
        import tempfile
        tmp = Path(tempfile.gettempdir()) / "_audit_exemplars.json"
        tmp.write_text(json.dumps(content, ensure_ascii=False), encoding="utf-8")
        loader._EXEMPLAR_FILE = tmp  # type: ignore[attr-defined]
        loader.reset_cache()
        return loader.build_exemplar_block
    except Exception:
        return lambda cat: _render_block_standalone(content, cat)


def _base_prompt_tokens(category: str, toks: Callable[[str], int]) -> Optional[int]:
    """Tokens of the verdict prompt WITHOUT the exemplar block. Returns None if
    extraction_service can't be imported (keeps the audit usable offline)."""
    try:
        from app.services.extraction_service import build_verdict_prompt
        return toks(build_verdict_prompt(products=[{"category": category}]))
    except Exception:
        return None


def run_audit(content_path: Path) -> int:
    content = json.loads(content_path.read_text(encoding="utf-8"))
    toks = _token_counter()
    render = _block_renderer(content)

    print(f"=== I1.5 exemplar token/cost audit — {content_path.name} ===")
    print(
        f"{'category':<13} {'base':>6} {'block':>6} {'total':>6} "
        f"{'+cost/call':>11} {'budget':>7}"
    )
    worst_cost = 0.0
    worst_tok = 0
    any_base = False
    for cat in CATEGORIES:
        block = render(cat)
        block_tok = toks(block)
        worst_tok = max(worst_tok, block_tok)
        cost = block_tok / 1000.0 * _USD_PER_1K_INPUT_4O
        worst_cost = max(worst_cost, cost)
        base = _base_prompt_tokens(cat, toks)
        any_base = any_base or base is not None
        base_s = str(base) if base is not None else "n/a"
        total_s = str(base + block_tok) if base is not None else "n/a"
        budget_ok = "ok" if block_tok <= _TOK_BUDGET else "OVER"
        print(
            f"{cat:<13} {base_s:>6} {block_tok:>6} {total_s:>6} "
            f"{'$'+format(cost, '.5f'):>11} {budget_ok:>7}"
        )

    print()
    print(f"worst block: {worst_tok} tok (budget {_TOK_BUDGET})")
    print(
        f"worst +cost/call: ${worst_cost:.5f} "
        f"(gate +${_COST_GATE_USD:.5f}) -> "
        f"{'PASS' if worst_cost <= _COST_GATE_USD else 'FAIL'}"
    )
    print(
        "note: the block lives in the static-per-category prompt prefix, so "
        "warm prompt-cached calls bill it ~10x cheaper; the figure above is "
        "the cold/uncached upper bound."
    )
    if not any_base:
        print(
            "note: base verdict-prompt tokens unavailable (extraction_service "
            "not importable here) — block tokens + gate still measured."
        )

    ok = worst_cost <= _COST_GATE_USD and worst_tok <= _TOK_BUDGET
    return 0 if ok else 1


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="I1.5 exemplar token/cost audit")
    ap.add_argument(
        "--file", type=Path, default=_CANONICAL,
        help="exemplar JSON to audit (default: data/verdict_exemplars.json)",
    )
    args = ap.parse_args(argv)
    if not args.file.exists():
        print(f"exemplar file not found: {args.file}", file=sys.stderr)
        return 2
    return run_audit(args.file)


if __name__ == "__main__":
    raise SystemExit(main())
