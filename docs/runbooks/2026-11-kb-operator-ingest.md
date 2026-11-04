# KB operator ingest (D16 OPERATOR-INGEST)

Operator runbook for the two admin JSON routes of D16 (flag `ENABLE_OPERATOR_INGEST`,
default OFF; knob `KB_OPERATOR_PAGE_MAX`). With the flag OFF both paths answer like an
unregistered path (404). Names only: no host list, no key value, no personal value.

## Preconditions (owner)

1. Migration 045 applied (owner item 29).
2. D17 running (`ENABLE_KB_COVERAGE_ROLLUP`), so the view's coverage block has a day.
3. A ToS review recorded (`tos.reviewed_at` on the registry row) for every BLOCKED host the
   operator will capture. Live hosts are accepted as they stand; a blocked host without the
   review is refused with `KB_HOST_NOT_REVIEWED`.
4. `ENABLE_OPERATOR_INGEST` ON on `web`.

## 1. Read the queue

```
curl -s -H "X-Admin-Key: $ADMIN_API_KEY" "$API_BASE/api/v1/admin/kb/operator?limit=50"
```

The answer lists the blocked registry hosts (robots state, ToS verdict and review time), the
`needs_operator` gaps by demand and the latest coverage day. `limit` is clamped to
`KB_OPERATOR_PAGE_MAX`.

## 2. Capture a page (the bookmarklet)

Save the snippet below as a bookmark in YOUR OWN browser and click it on the merchant's
product page. It reads the page URL, every JSON-LD block and the og:image, and copies ONE
JSON object to the clipboard. It never sends anything over the network: no key ever enters a
merchant page, and the browser's cross-origin rules would refuse a post anyway.

```
javascript:(function(){var ld=[];document.querySelectorAll('script[type="application/ld+json"]').forEach(function(s){try{var v=JSON.parse(s.textContent);(Array.isArray(v)?v:[v]).forEach(function(n){if(n&&typeof n==='object'&&ld.length<20){ld.push(n);}});}catch(e){}});var og=document.querySelector('meta[property="og:image"]');var p={source:'operator',page_url:location.href,jsonld:ld};if(og&&og.content){p.og_image=og.content;}navigator.clipboard.writeText(JSON.stringify(p)).then(function(){alert('KB payload copied');});})();
```

Before posting, add what the page states and the JSON-LD lacks: `price` as
`{"amount": <number>, "currency": "<ISO-3>"}`, `size_ml`, `in_stock`, `captured_at`
(ISO-8601 with a zone), `market` (default `BH`), manual `brand` / `name` / `variant`, and
`specs` as field -> text. Extra keys are refused (422); the body is capped at 256 KB.

Licence fields: the spec fields `notes_top`, `notes_heart`, `notes_base`, `longevity` and
`sillage` are accepted ONLY with `"source": "partner"` (licensed rows); an operator capture
carrying one is refused with `KB_LICENCE_FIELD` and nothing is written.

## 3. Post it (terminal)

Paste the clipboard into a file (here `payload.json`) and post it:

```
curl -s -X POST -H "Content-Type: application/json" -H "X-Admin-Key: $ADMIN_API_KEY" \
  --data @payload.json "$API_BASE/api/v1/admin/kb/ingest"
```

`ADMIN_API_KEY` and `API_BASE` are environment variable NAMES set in the operator's own
shell; never paste a key value into a file, a ticket or a transcript.

A success returns `{"success": true, "written": {...counts...}}`; the matching open and
`needs_operator` gaps of the product are closed. Refusals are 400 with one of:
`KB_URL_REFUSED`, `KB_HOST_UNKNOWN`, `KB_HOST_CANDIDATE`, `KB_HOST_NOT_REVIEWED`,
`KB_IDENTITY_UNRESOLVED`, `KB_PAYLOAD_TOO_LARGE`, `KB_STORE_UNAVAILABLE`, `KB_LICENCE_FIELD`.

## Notes

- Rows go only through the knowledge-base row builders (insert-ignore): the product at
  identity `high` (operator-verified), the variant, the offer (evidence rung `operator`), the
  image (source `operator`) and the specs (cited to the canonical page). Reviews are never
  written by this path.
- Partner rows use the same route with `"source": "partner"`; the partner is trusted for the
  licence fields by the operator's own review (no licence text is validated by the app).
- Canary: the `[KB_OPERATOR]` log lines, the view's queue sizes, the 4xx codes.
