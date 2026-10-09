"""Session 75, unit U3b (ruling UB-R21): the CLAUDE.md lines written by the
orchestrator at merge. Reads CLAUDE.md from stdin (bytes), applies the exact
edits, writes the result to the path in argv[1] (bytes; CRLF preserved by
working on the decoded text and re-encoding with the same newline).
Usage (dry run):  git -C <wt> show HEAD:CLAUDE.md | python claude_md_u3b_lines.py --check
Usage (apply):    python claude_md_u3b_lines.py <wt>/CLAUDE.md < <wt>/CLAUDE.md   (binary-safe)
Every edit must match EXACTLY once; otherwise nothing is written and exit 2.
PR_NUMBER is substituted into the bullet."""
import sys

PR_NUMBER = sys.argv[2] if len(sys.argv) > 2 else "<PR>"

EDITS = [
    # (1) the AI-consent paragraph of the Session 69 client surfaces bullet.
    (
        "AsyncStorage `@qaren_ai_consent_<userId>`, no server record; `AI_CONSENT_VERSION` (1) + a sha256 fence over the EN + AR copy;",
        "AsyncStorage `@qaren_ai_consent_<userId>`, no server record; `AI_CONSENT_VERSION` is **2 since U3b (session 75, PR #" + PR_NUMBER + ")**: one disclosure sentence (EN + AR, before the final sentence) says OpenAI may use the inputs and the outputs it generates to identify usage patterns, measure model quality and inform the evaluation and training of its models (decision D3 = C, organisation data sharing ON, **no per-user opt-out**; the Profile AI-sharing toggle is deleted; every existing user sees the sheet ONCE more and cannot compare until they agree, UB-R14) + a sha256 fence over the EN + AR copy (`372c5048...`, re-pinned together with the V4 constant in ONE edit if the native review changes a word);",
    ),
    # (2) the openai_service line: the #266 follow-up sentence in the Session 69 block.
    (
        "#266 `select_client_for_user` has 0 callers so the PDPL AI-sharing opt-out routes nothing (A-C21 — a guideline 5.1.2 disclosure problem for U3 / U8),",
        "#266 `select_client_for_user` has 0 callers so the PDPL AI-sharing opt-out routes nothing (A-C21 — a guideline 5.1.2 disclosure problem for U3 / U8; CLOSED by U3b, session 75: `openai_service.get_client()` takes no argument, `select_client_for_user` and `OPENAI_API_KEY_PRIVATE` are deleted, `PUT /auth/preference-toggles` still accepts `ai_sharing_enabled` as an inert field),",
    ),
    # (3) the UB-R4 sequencing sentence in the Store-build rules paragraph.
    (
        "bump `expo.version` for every native change (a new build) and never for a JS-only hotfix (or the OTA strands the installed builds).",
        "bump `expo.version` for every native change (a new build) and never for a JS-only hotfix (or the OTA strands the installed builds). **UB-R4 (session 75, binding for the lane):** no `eas update` and no store build or submission from main between the U3b merge and PR #330 being merged AND live on the API -- until then the consent sheet would state the opposite of the policy it links (guideline 5.1.2(i)).",
    ),
    # (4) the SESSION 73 block bullet, appended after the COST-METER bullet.
    (
        "nor is `/admin/stats/costs`; `metadata.openai` is client-visible on the owner's own responses (ints, USD and model ids only, the `total_cost` precedent).",
        "nor is `/admin/stats/costs`; `metadata.openai` is client-visible on the owner's own responses (ints, USD and model ids only, the `total_cost` precedent).\n- **U3b (AI consent v2 under D3 = C, session 75, PR #" + PR_NUMBER + "; client OTA-gated, backend unflagged):** `AI_CONSENT_VERSION` 2 with the one disclosure sentence (EN + AR, the AR under the [SPEC] tag pending native review: `2026-10-09-session-75-state/NATIVE_REVIEW_S75.md`), the Profile AI-sharing toggle and its three AR/EN keys removed, the sheet's ScrollView capped with a NUMBER from `useWindowDimensions` (`Math.round(0.4 * height)`, `flexGrow: 0`, `flashScrollIndicators` when it opens, `maxFontSizeMultiplier` 1.6 on the title / link / CTAs so both CTAs stay reachable at every Dynamic Type size; the on-device check at the smallest supported iPhone and at AX sizes is still owed, UB-R13); backend: `openai_service.get_client()` without a parameter, `select_client_for_user` / `OPENAI_API_KEY_PRIVATE` deleted, the route keeps accepting `ai_sharing_enabled` (inert), the OpenAPI wording no longer promises an opt-out (B5). **Sequencing UB-R4 (also in Store-build rules):** no OTA and no store build with U3b before PR #330 is live. Follow-ups (UY6): the 'Privacy' eyebrow and the Step 5 headline (LISTING-TRUTH), the inventory purposes + the stale row-12 `api.ts` anchors, the native re-pin unit.",
    ),
]


def main() -> int:
    raw = sys.stdin.buffer.read()
    text = raw.decode("utf-8")
    check = "--check" in sys.argv[1:]
    ok = True
    for old, new in EDITS:
        n = text.count(old)
        print(f"match x{n}: {old[:70]!r}")
        if n != 1:
            ok = False
    if not ok:
        print("NOT APPLIED: an edit does not match exactly once")
        return 2
    if check:
        print("dry run OK")
        return 0
    for old, new in EDITS:
        text = text.replace(old, new, 1)
    out = sys.argv[1]
    with open(out, "wb") as fh:
        fh.write(text.encode("utf-8"))
    print("written", out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
