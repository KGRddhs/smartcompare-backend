"""Files the W4-11 follow-up issues (run AFTER PR #223 merges). python issues/file_issues_w411.py [--dry]"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pr_rest import api, REPO  # noqa: E402

ISSUES = [
    ("PO-PROMPTS-02b: product display names still reach the verdict SYSTEM message raw through build_scores_summary; the appended quote/YouTube blocks and the self-critique payload sit outside a region", """
Follow-up of PR #223 (W4-11 prompt truth). W4-11 neutralised every interpolated string on the verdict USER message (both product dumps, concern, region, the appended review-quote and YouTube blocks) and fenced the refill, URL and image prompts. Two surfaces stayed out of scope:

1. **`scoring_service.build_scores_summary`** renders the product display names into the verdict SYSTEM message (the `Dimension leaders:` and tier lines that W4-10 introduced) with no sanitisation. A product name carrying a closing region tag or a newline reaches the SYSTEM role raw. Route the names through `sanitize_prompt_input` + whitespace collapse at that site (scoring_service was out of W4-11's diff by ruling R23), pin it with the hostile-name fixture the fence tests use, and add the render to the committed digest recorder (`tests/w4_11_prompt_digest_recorder.py`) so the OFF render stays byte-pinned.
2. The appended review-quote / YouTube blocks are sanitised per string but still sit OUTSIDE a `<SEARCH_RESULTS>` region, and the self-critique payload (`verdict_critique_service`) interpolates the verdict JSON without a region. Put both inside a region under the guard sentence.

Both are unflagged security controls in the R4 sense (byte-identical unless a literal tag is present); the digest gate must move exactly the keys the change touches.
"""),
    ("PO-PROMPTS-05b: the data-gap cons scrubber (the response half of W4-11's TRUTH prompt)", """
Follow-up of PR #223 (W4-11 prompt truth). Under `ENABLE_VERDICT_PROMPT_TRUTH` the verdict prompt no longer forces invented cons and the `[VERDICT_TRUTH] cons empty=N data_gap=N` canary counts, PER cons string, the three spec-7 phrases ("limited information", "no details on", "no cons noted"). The RESPONSE half was deferred: a con that describes OUR data rather than the product still ships to the phone when the model emits one anyway.

**Ask.** A scrubber in `text_sanitize` plus a `response_builder` filter that drops a cons string matching the data-gap vocabulary (the same regex the canary uses, kept in ONE place), behind its own default-OFF flag, with the flag-OFF path byte-identical. It was deferred because no cons corpus is on disk to measure over-rejection: build the corpus first (the 22-row recorded set from W4-12 plus a sample of persisted `comparisons.full_response` cons) and report the drop rate per phrase before the flag is considered for a flip. The scrubber must never empty a pros list and must leave `product_i_cons` a list (possibly empty), which the client already renders (W4-12's honest empty cons).
"""),
    ("W4-9 follow-up 05c: str(e) still reaches error fields at extract_specs, extract_price and extract_price_from_training_data", """
Recorded by PR #223 (W4-11) as a stated limit; the W4-9 redaction (#178) covered the orchestrator catches, the parser catch and the generate_comparison / extract_reviews catches, but three `extraction_service` catches still store `str(e)`:

- `extract_specs` (the except branch returns `{"error": str(e)}` shape),
- `extract_price` (same),
- `extract_price_from_training_data` (`{"amount": None, "currency": ..., "error": str(e)}` - measured in W4-11's adversary round 1 carrying the OpenAI exception text on an OverflowError).

An OpenAI SDK exception can carry the request URL, headers or a key tail in its text (the W4-9 finding), and these dicts reach `search_logs.error_message` and, on some paths, the client. Ask: store the exception TYPE name (the W4-9 constant pattern) and log the text once at WARNING through the existing redacting logger; pin each site with an exception whose text carries a marker and assert the marker never reaches the returned dict.
"""),
]


def main():
    dry = "--dry" in sys.argv
    for title, body in ISSUES:
        body = body.strip() + "\n"
        if dry:
            print("DRY", title[:80], len(body)); continue
        st, res = api("POST", f"/repos/{REPO}/issues", {"title": title, "body": body})
        if st != 201:
            print(f"FAILED status={st} {title[:60]} {str(res)[:200]}"); continue
        print(f"created #{res['number']} {res['html_url']}")


if __name__ == "__main__":
    main()
