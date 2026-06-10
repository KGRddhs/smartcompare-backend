# Gold-Set Maintenance Protocol (`data/validation_gold_truth.json`)

Authored by Lane F5, Bundle B Session 1 (2026-06-10). The gold set is the answer key
the eval loop grades the engine against — 200 fact-anchored Bahrain comparison queries,
ratified by Ahmed (`_metadata.ratified_by/ratified_at`).

- **Append-only contract.** Existing entries are FROZEN — never mutate an authored
  entry's values. New work only appends. Any diff that touches lines inside an
  already-shipped entry (other than the `_metadata.queries` count) is a STOP signal:
  stop and investigate before committing. Verify frozen entries are semantically
  unchanged with a parse-and-deep-equal against the prior commit, not a substring/line
  check.

- **Expansion protocol.** (1) Write + commit a taxonomy manifest
  (`data/gold_truth_taxonomy_manifest.json`: per-category targets, ID ranges, prefixes)
  BEFORE authoring. (2) Author in batches of ~25, each entry carrying a provenance note,
  the current `max_wall_seconds` cap, 2-4 load-bearing spec keys, an
  `expected_winner_index` + one-line rationale, and 3+ `forbidden_facts`. (3) Schema test
  must pass (counts match the manifest, ids unique, every new entry has a provenance
  note). (4) The set is NOT usable as an eval baseline until winner labels are ratified.

- **Provenance bar.** Every price band names a retailer + an observed price, OR honestly
  states a widened band (e.g. GCC source × BHD conversion) when the Bahrain price is
  unverifiable online. Sources that disclaim price accuracy (e.g. goldenbahrain.com
  aggregator) are BANNED as a sole anchor — cross-check against a verified retailer and
  annotate the re-check.

- **Winner-label authority.** Winner picks are authored as a best guess but only Ahmed
  ratifies them. Record ratification in `_metadata.ratified_by` +
  `_metadata.ratified_at` (ISO 8601). An unratified expansion does not gate the eval.

- **Count-agnostic tests.** No test may hardcode the query count or any per-category
  count as a literal — drive those assertions off the taxonomy manifest so the next
  expansion doesn't break the suite.

- **Cost rule.** All price/spec research is direct-source (retailer sites via
  WebFetch/WebSearch/curl). NEVER call the SmartCompare app API for gold research — it
  burns Serper + OpenAI per call.
