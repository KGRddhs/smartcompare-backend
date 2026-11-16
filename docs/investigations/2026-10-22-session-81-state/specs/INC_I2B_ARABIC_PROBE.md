# INC-I2b: Arabic-script typed names (S96 orchestrator probe, 2026-11-17 02:40 AST)

The probe is arprobe/probe.py against the base 5cd93c6a, with G ON and S ON and S OFF (identical results). The placeholders (ar.json home.compare.box_a_text / box_b_text) are "ديور سوفاج EDP" and "بلو دو شانيل EDP".

## Today, before INC-M1
- The tokenizer keeps the Arabic tokens as they are: ['ديور','سوفاج','edp'] and ['بلو','دو','شانيل','edp'].
- The image query is the typed line plus "perfume", so Serper Images is asked in Arabic script.
- The name test needs the typed script in the title:
  - brand Dior (Latin, from extraction) with an Arabic line: every Latin title fails on `name`, and every Arabic title fails on `brand`. This matches product=0 reason=name in the 02:28 run.
  - brand in Arabic: Latin titles fail on `brand`, and Arabic titles pass.
  - an empty brand: Latin titles fail on `name`, and Arabic titles pass.
- `reason=` on the IMG_RELEVANCE line is the LAST rejected candidate's reason (RelevanceCall.summary), not all five. "candidates=5 reason=denied" means at least the last tested candidate named a banned site. The banned labels are fragrantica, parfumo, basenotes and fimgs; fimgs.net is Fragrantica's picture CDN and returns True. fragranticarabia.com returns False. An Arabic query for a mainstream perfume leads with fragrance-site pictures. The deny rule is right to refuse them; the cause is the Arabic query, not the deny rule.

## After INC-M1 (identity brand + line in Latin)
- Latin titles pass; Arabic-only titles fail on `brand`, because brand_forms holds no Arabic spelling.
- That is the data lane's call: INC-M1 could add the Arabic brand spelling to brand_forms, or the query could stay Latin so that Latin titles dominate.

## INC-I2b's duty
W adds no new refusal or acceptance for an Arabic-script name; it is a parity pin. The Arabic gift words never refuse alone (I-10). Rows (new file, so the frozen RED file stays frozen):
- P-AR1: both placeholders typed, R OFF, W unset vs W ON: the same check() reason per candidate across the eight titles.
- P-AR2: the post-M1 identity (Latin brand and line, Arabic product_name) accepts the Latin titles with W ON.
- P-AR3: an Arabic title carrying an Arabic gift word alone is not refused by W.
