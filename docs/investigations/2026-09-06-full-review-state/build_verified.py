"""Build the consolidated VERIFIED JSON for the 2026-09-06 full review.

Inputs (all read-only):
  partial-<name>.json           extracted state (lanes, first verdicts, second votes) from the run-1/run-2 journals
  <session65 journals>/wf_*/journal.jsonl   the SESSION 65 continuation journals: batched second votes ({verdicts:[...]}),
                                synthesis ({report_path,...}) and critic ({gaps,...})
  FABLE overrides (below)       the orchestrator's authoritative severity/verdict where it disagrees with an agent

Output:
  docs/investigations/2026-09-06-full-review-verified.json
  (+ a printed tally per workflow)

    python docs/investigations/2026-09-06-full-review-state/build_verified.py \
        --state docs/investigations/2026-09-06-full-review-state \
        --journals "<session65 workflows dir>" \
        --out docs/investigations/2026-09-06-full-review-verified.json
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import sys

RUNS = {
    "m22-product-output": {"run1": "wf_4127a8d5-5b2", "s65": "wf_490661b3-382"},
    "m22-code-review": {"run1": "wf_cbda6ac4-a50", "s65": "wf_dc17e31e-df3"},
    "m22-load-scale": {"run1": "wf_46983729-4eb", "s65": "wf_509f5db6-d58"},
    "m22-mobile": {"run1": "wf_e23aeca8-908", "s65": "wf_c3d6962b-c9e"},
}

# Fable (orchestrator) overrides — authoritative where they differ from the agents.
# value: (final_sev, fable_verdict, note)
FABLE = {
    # load
    "LS-CACHE-REDIS-01": ("P1", "DEDUPE", "same defect as LS-REQUEST-PATH-BLOCKING-03"),
    "LS-CONCURRENCY-LIMITS-04": ("P1", "DEDUPE", "same defect as LS-REQUEST-PATH-BLOCKING-03"),
    "LS-CACHE-REDIS-02": ("P1", "CONFIRMED", "Fable's P2 downgrade WITHDRAWN after the second vote reproduced n=5 -> 5 searches + 5 extractions on one key (launch-capacity defect)"),
    "LS-CONCURRENCY-LIMITS-02": ("P1", "CONFIRMED", "Fable's P2 downgrade WITHDRAWN: measured 62 submissions / 21 queued against the real 40-worker pool from ONE fragrance compare"),
    "LS-FAILURE-MODES-COST-05": ("P2", "DOWNGRADED", "vote + Fable agree: refund runs inline with the offload flags OFF and survives shutdown; becomes a real loss the moment ENABLE_ASYNC_REDIS_OFFLOAD is ON -> W1-6 drain is a precondition for that canary"),
    "LS-MEASURED-EVIDENCE-01": ("P1", "EVIDENCE", "measured Upstash RTT 178 ms (re-measured 168-196 ms with the pooled client); not a code defect, load-model input"),
    # code
    "CR-PERFORMANCE-03": ("P1", "DEDUPE", "same defect as LS-REQUEST-PATH-BLOCKING-02"),
    "CR-SECURITY-05": ("P0", "DEDUPE", "same defect as LS-REQUEST-PATH-BLOCKING-01"),
    "CR-SECURITY-06": ("P1", "DEDUPE", "same route as LS-RATELIMIT-KEY-02"),
    "CR-CLAUDE-CONFIG-11": ("P1", "PROPOSE-ONLY", "config audit is propose-only per the orchestrator skill"),
    "CR-DELTA-CORRECTNESS-07": ("P2", "UPGRADED", "LIVE regression from M21 W3 (tradeoffs collapse)"),
    "CR-DELTA-CORRECTNESS-09": ("P2", "UPGRADED", "canary note; re-take the free-credit baseline post-M21"),
    # product
    "PO-RECORDED-MEASURED-01": ("P2", "EVIDENCE", "code half P2 (admin-read dilution); the MEASUREMENT stands as the campaign baseline: 79.7-88.6% probe volume, organic series ~1,513 rows / 80% success / p50 22.0 s"),
    "PO-RECORDED-MEASURED-02": ("P2", "DOWNGRADED", "vote: 1,032 of the 1,484 local_bhd rows are already pended by the live non-PDP guard (~15 genuinely wrong-country showable) -> P2; MUST land with/before W4-2, which would otherwise un-pend those rows and expose the label"),
    # mobile
    "MB-NETWORK-CONTRACT-14": ("P1", "DEDUPE", "= MB-RECONCILE-01 + MB-RECONCILE-07 (one metering unit)"),
    "MB-STARTUP-BUNDLE-02": ("P1", "OTHER-SESSION", "fixed on feature/m23-mobile-w1 A3 e58f022 (unmerged); re-verify after merge"),
    "MB-RECONCILE-03": ("P1", "OTHER-SESSION", "fixed on feature/m23-mobile-w1 A3 e58f022 (unmerged); re-verify after merge"),
    "MB-FLOWS-STATE-05": ("P1", "OTHER-SESSION", "fixed on feature/m23-mobile-w1 A18 b73c47e (unmerged); re-verify after merge"),
    "MB-RECONCILE-05": ("P1", "OTHER-SESSION", "fixed on feature/m23-mobile-w1 A18 b73c47e (unmerged); re-verify after merge"),
    "MB-TESTS-TRUTH-04": ("P1", "OTHER-SESSION", "fixed on feature/m23-mobile-w1 A12 4f470cc (unmerged); re-verify after merge"),
    "MB-RECONCILE-07": ("P1", "UPGRADED", "P2->P1 (data loss + server-side freemium bypass), and /url/compare 500s on success (PO-VERDICT-TRUTH-01)"),
    "MB-RECONCILE-15": ("P1", "PRODUCT-CALL", "outbound retailer link is a product decision, not a blind fix"),
}

DEDUPE_CLUSTERS = [
    ["LS-REQUEST-PATH-BLOCKING-01", "CR-SECURITY-05"],
    ["LS-REQUEST-PATH-BLOCKING-02", "CR-PERFORMANCE-03"],
    ["LS-REQUEST-PATH-BLOCKING-03", "LS-CACHE-REDIS-01", "LS-CONCURRENCY-LIMITS-04"],
    ["LS-RATELIMIT-KEY-02", "CR-SECURITY-06"],
    ["MB-RECONCILE-01", "MB-NETWORK-CONTRACT-14"],
    ["MB-RECONCILE-07", "MB-NETWORK-CONTRACT-14", "PO-VERDICT-TRUTH-01"],
    ["MB-RECONCILE-03", "MB-STARTUP-BUNDLE-02"],
    ["MB-RECONCILE-05", "MB-FLOWS-STATE-05"],
    ["LS-FAILURE-MODES-COST-01", "CR-CLAUDE-CONFIG-02"],
    ["LS-CONCURRENCY-LIMITS-01", "CR-PERFORMANCE-01"],
    ["CR-SECURITY-03", "CR-SECURITY-04"],
    ["PO-PRICE-TRUTH-01", "PO-PRICE-TRUTH-02", "PO-RECORDED-MEASURED-02"],
]


def rows(path):
    out = []
    if not os.path.exists(path):
        return out
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            try:
                out.append(json.loads(line))
            except Exception:
                continue
    return out


def s65_extract(journal):
    second, synth, critic = {}, None, None
    for e in rows(journal):
        if e.get("type") != "result":
            continue
        r = e.get("result")
        if not isinstance(r, dict):
            continue
        if isinstance(r.get("verdicts"), list):
            for v in r["verdicts"]:
                if isinstance(v, dict) and "id" in v:
                    second[v["id"]] = dict(v, stage="second-vote")
        elif "report_path" in r or "report_md" in r:
            synth = r
        elif "gaps" in r:
            critic = r
        elif "second_votes" in r and isinstance(r.get("second_votes"), list):  # the workflow's final return value
            for v in r["second_votes"]:
                if isinstance(v, dict) and "id" in v:
                    second.setdefault(v["id"], dict(v, stage="second-vote"))
            synth = synth or r.get("synth")
            critic = critic or r.get("critic")
    return second, synth, critic


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--state", required=True)
    ap.add_argument("--journals", required=True, help="SESSION 65 workflows dir (holds wf_*/journal.jsonl)")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    cluster_of = {}
    for c in DEDUPE_CLUSTERS:
        for fid in c:
            cluster_of.setdefault(fid, c[0])

    all_rows, tallies, per_wf = [], {}, {}
    for name, ids in RUNS.items():
        st = json.load(open(os.path.join(a.state, f"partial-{name}.json"), encoding="utf-8"))
        second_s65, synth, critic = s65_extract(os.path.join(a.journals, ids["s65"], "journal.jsonl"))
        second = dict(st.get("second_votes") or {})
        second.update(second_s65)
        fmap = {}
        for lane, v in st["lanes"].items():
            for f in v.get("findings", []):
                fmap[f["id"]] = dict(f, lane=lane)
        tally = collections.Counter()
        for fid, f in fmap.items():
            v1 = st["verdicts"].get(fid)
            v2 = second.get(fid)
            trail = []
            if v1:
                trail.append({"stage": "verify", "verdict": v1.get("verdict"), "sev_after": v1.get("sev_after"), "reason": v1.get("reason")})
            if v2:
                trail.append({"stage": "second-vote", "verdict": v2.get("verdict"), "sev_after": v2.get("sev_after"), "reason": v2.get("reason")})
            status = "verified"
            if not v1:
                status = "unverified"
            elif v1.get("verdict") == "REFUTED" or (v2 and v2.get("verdict") == "REFUTED"):
                status = "refuted"
            elif v1.get("verdict") == "UNVERIFIABLE" and not v2:
                status = "unverifiable"
            sev = f.get("sev")
            if v1 and v1.get("sev_after") and v1.get("verdict") in ("CONFIRMED", "DOWNGRADED", "UPGRADED"):
                sev = v1["sev_after"]
            if v2 and v2.get("sev_after") and v2.get("verdict") in ("CONFIRMED", "DOWNGRADED", "UPGRADED"):
                sev = v2["sev_after"]
            fable = FABLE.get(fid)
            if fable:
                sev = fable[0]
            row = {
                "id": fid, "workflow": name, "lane": f.get("lane"), "title": f.get("title"),
                "file": (v1 or {}).get("corrected_file") or f.get("file"),
                "line": (v1 or {}).get("corrected_line") or f.get("line"),
                "sev_filed": f.get("sev"), "sev_final": sev, "status": status,
                "measured_or_modelled": f.get("measured_or_modelled"), "m21_touched": f.get("m21_touched"),
                "dedupe": f.get("dedupe"), "confidence": f.get("confidence"),
                "fix": f.get("fix"), "test_first": f.get("test_first"), "impact": f.get("impact"),
                "verdict_trail": trail,
                "fable": {"verdict": fable[1], "note": fable[2]} if fable else None,
                "dedupe_cluster": cluster_of.get(fid),
            }
            all_rows.append(row)
            if status == "refuted":
                tally["REFUTED"] += 1
            elif status == "verified":
                tally[sev] += 1
            else:
                tally[status.upper()] += 1
        tallies[name] = dict(tally)
        per_wf[name] = {
            "run1_id": ids["run1"], "s65_id": ids["s65"],
            "filed": len(fmap), "second_votes_total": len([x for x in fmap if x in second]),
            "synth": synth, "critic": critic,
        }
        print(name, dict(tally), "| s65 second votes:", len(second_s65), "| synth:", bool(synth), "| critic:", bool(critic))

    out = {
        "review": "2026-09-06 full review (product-output / code / load-scale / mobile)", "base": "76ace90",
        "generated_by": "build_verified.py (SESSION 65, 2026-09-07)",
        "tallies": tallies, "workflows": per_wf, "dedupe_clusters": DEDUPE_CLUSTERS, "findings": all_rows,
    }
    with open(a.out, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, ensure_ascii=False)
    print("wrote", a.out, "rows", len(all_rows))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
