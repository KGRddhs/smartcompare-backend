#!/usr/bin/env python3
"""Instagram / TikTok feasibility test — interactive helper + summariser.

Plan: docs/plans/2026-06-08-backend-comparison-overhaul-plan.md § L4.4
Design: docs/plans/2026-06-08-backend-comparison-overhaul-design.md § 10
Doc:   docs/plans/2026-06-08-A-instagram-feasibility-test.md

This is a MANUAL exercise — the script does NOT scrape Instagram or
TikTok (privacy + ToS). It records the human tester's observations into
a structured JSON file, then a summariser pulls the green-light
decision per § 1 rule of the doc.

Usage:
    python scripts/instagram_feasibility_test.py init
        # bootstrap data/instagram_feasibility_findings.json with the
        # 5 stub queries; tester fills in by editing JSON OR running
        # the interactive `record` subcommand.

    python scripts/instagram_feasibility_test.py summary
        # read findings → emit green-light / cut decision

    python scripts/instagram_feasibility_test.py record --id frag-tomford-black-orchid
        # interactive walk through Step 1..Step 5 for one query
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_FINDINGS = REPO_ROOT / "data" / "instagram_feasibility_findings.json"

# 5 queries — fragrance + makeup + fashion + electronics + supplement
STUB_QUERIES: List[Dict[str, Any]] = [
    {
        "id": "frag-tomford-black-orchid",
        "category": "fragrances",
        "query": "Tom Ford Black Orchid",
        "instagram_brand_main_handle": "@tomfordbeauty",
        "tiktok_hashtag": "#tomfordblackorchid",
    },
    {
        "id": "make-fenty-pro-filtr",
        "category": "makeup",
        "query": "Fenty Pro Filt'r Foundation",
        "instagram_brand_main_handle": "@fentybeauty",
        "tiktok_hashtag": "#fentyprofiltr",
    },
    {
        "id": "fash-birkenstock-arizona",
        "category": "fashion",
        "query": "Birkenstock Arizona",
        "instagram_brand_main_handle": "@birkenstock",
        "tiktok_hashtag": "#birkenstockarizona",
    },
    {
        "id": "elec-dyson-airwrap",
        "category": "electronics",
        "query": "Dyson Airwrap",
        "instagram_brand_main_handle": "@dyson",
        "tiktok_hashtag": "#dysonairwrap",
    },
    {
        "id": "supp-gardenoflife-omega3",
        "category": "supplements",
        "query": "Garden of Life Omega-3",
        "instagram_brand_main_handle": "@gardenoflife",
        "tiktok_hashtag": "#gardenoflifeomega",
    },
]


def _empty_finding(stub: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": stub["id"],
        "category": stub["category"],
        "query": stub["query"],
        "tested_at": None,
        "tester": None,
        "instagram_brand_main": {
            "handle": stub["instagram_brand_main_handle"],
            "posts_reviewed": 0,
            "unique_signals": [],
            "notes": "",
        },
        "instagram_influencers": [
            {"handle": "@TBD_gcc_reviewer_1", "unique_signals": []},
            {"handle": "@TBD_gcc_reviewer_2", "unique_signals": []},
            {"handle": "@TBD_gcc_reviewer_3", "unique_signals": []},
        ],
        "tiktok": {
            "hashtag_reviewed": stub["tiktok_hashtag"],
            "posts_reviewed": 0,
            "unique_signals": [],
        },
        "score": None,
        "decision_rationale": "",
    }


def cmd_init(args: argparse.Namespace) -> int:
    out_path = Path(args.out or DEFAULT_FINDINGS)
    if out_path.exists() and not args.force:
        print(f"ERROR: {out_path} already exists. Use --force to overwrite.", file=sys.stderr)
        return 1
    payload = {
        "_metadata": {
            "schema_version": 1,
            "initialised_at": _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "decision_rule": (
                "Green-light if >=3 of 5 queries score >=3 unique-value "
                "(per docs/plans/2026-06-08-A-instagram-feasibility-test.md § 1)."
            ),
            "doc": "docs/plans/2026-06-08-A-instagram-feasibility-test.md",
        },
        "findings": [_empty_finding(s) for s in STUB_QUERIES],
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {out_path} with 5 stub queries. Tester fills in by editing JSON OR `record` subcommand.")
    return 0


def _load_findings(path: Path) -> Dict[str, Any]:
    if not path.exists():
        print(f"ERROR: {path} missing. Run `init` first.", file=sys.stderr)
        sys.exit(1)
    return json.loads(path.read_text(encoding="utf-8"))


def _save_findings(path: Path, payload: Dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def cmd_record(args: argparse.Namespace) -> int:
    path = Path(args.out or DEFAULT_FINDINGS)
    payload = _load_findings(path)
    target = next((f for f in payload["findings"] if f["id"] == args.id), None)
    if not target:
        print(f"ERROR: no finding with id={args.id}. Run `summary` to list IDs.", file=sys.stderr)
        return 1

    print(f"Recording findings for {target['id']} ({target['query']})")
    print(f"Walk the steps in docs/plans/2026-06-08-A-instagram-feasibility-test.md § 3.")
    print("Enter blank to skip; comma-separated for unique_signals lists.")

    target["tested_at"] = _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%d")
    target["tester"] = input(f"Tester name [{target['tester'] or 'me'}]: ").strip() or "me"

    main_handle = target["instagram_brand_main"]["handle"]
    print(f"\nStep 2 — Instagram brand main ({main_handle})")
    target["instagram_brand_main"]["posts_reviewed"] = int(input("  Posts reviewed (default 30): ") or "30")
    sig = input("  Unique signals (comma-separated): ").strip()
    target["instagram_brand_main"]["unique_signals"] = [s.strip() for s in sig.split(",") if s.strip()]
    target["instagram_brand_main"]["notes"] = input("  Notes: ").strip()

    print("\nStep 3 — Three GCC influencer accounts")
    for i in range(3):
        handle = input(f"  Influencer {i+1} handle [{target['instagram_influencers'][i]['handle']}]: ").strip() or target['instagram_influencers'][i]['handle']
        sig = input(f"  Influencer {i+1} unique signals (comma-separated): ").strip()
        target["instagram_influencers"][i] = {
            "handle": handle,
            "unique_signals": [s.strip() for s in sig.split(",") if s.strip()],
        }

    print(f"\nStep 4 — TikTok ({target['tiktok']['hashtag_reviewed']})")
    target["tiktok"]["posts_reviewed"] = int(input("  Posts reviewed (default 30): ") or "30")
    sig = input("  Unique signals (comma-separated): ").strip()
    target["tiktok"]["unique_signals"] = [s.strip() for s in sig.split(",") if s.strip()]

    print("\nStep 5 — Score (1=marketing only, 5=critical unique info)")
    target["score"] = int(input("  Score 1-5: "))
    target["decision_rationale"] = input("  Rationale (one sentence): ").strip()

    _save_findings(path, payload)
    print(f"\nSaved. Run `python scripts/instagram_feasibility_test.py summary` to see the aggregate decision.")
    return 0


def cmd_summary(args: argparse.Namespace) -> int:
    path = Path(args.out or DEFAULT_FINDINGS)
    payload = _load_findings(path)
    findings = payload["findings"]

    pending = [f["id"] for f in findings if f["score"] is None]
    scored = [f for f in findings if f["score"] is not None]
    print(f"Findings recorded: {len(scored)}/{len(findings)}")
    for f in findings:
        score = f["score"] if f["score"] is not None else "—"
        print(f"  [{score}] {f['id']:<40} {f.get('decision_rationale','')[:80]}")

    if pending:
        print(f"\n{len(pending)} pending: {pending}")
        print("Cannot emit final decision until all 5 scored.")
        return 0

    high_signal = [f for f in scored if f["score"] >= 3]
    decision = "GREEN-LIGHT Apify integration" if len(high_signal) >= 3 else "CUT Instagram/TikTok from B.4"
    print()
    print("=" * 60)
    print(f"Queries scoring >=3: {len(high_signal)}/5  Threshold: 3/5")
    print(f"Decision: {decision}")
    print("=" * 60)
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_init = sub.add_parser("init")
    p_init.add_argument("--out", default=None)
    p_init.add_argument("--force", action="store_true")

    p_record = sub.add_parser("record")
    p_record.add_argument("--id", required=True)
    p_record.add_argument("--out", default=None)

    p_summary = sub.add_parser("summary")
    p_summary.add_argument("--out", default=None)

    args = parser.parse_args(argv)
    if args.cmd == "init":
        return cmd_init(args)
    if args.cmd == "record":
        return cmd_record(args)
    if args.cmd == "summary":
        return cmd_summary(args)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
