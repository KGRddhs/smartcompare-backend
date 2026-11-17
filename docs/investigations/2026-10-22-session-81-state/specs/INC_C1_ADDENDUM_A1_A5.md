# INC-C1 addendum: the relay orchestrator's message read 2026-11-17 about 06:10 AST (its meter reading 04:36: 58 pct)

The spec agent of wf_48c7a0c7-f18 started before this message. These items are amended in at the spec gate. Never SendMessage a workflow agent.

## Defects from the owner's first phone proof (screenshots 03:21; typed "Chanel No 5" vs "Dior Sauvage")
- **A-1:** the specs table shows Volume "100" on one side and "100 ml" on the other. Find where the client renders specs rows and whether the server sends the unit. A client fix is a unit normaliser on the volume row; otherwise it is a server dependency.
- **A-2:** the pros text says a 4.7 rating "across 107 reviews", while the reviews section says 16,000 for the same perfume. The two numbers come from different sources. LIKELY server-side (the pros text is model-written from one source; the reviews section reads another). Determine which, and name the server dependency. The client cannot rewrite model text.
- **A-3:** a con that speaks about our data, not the perfume ("Fewer detailed retailer reviews than ..."). LIKELY the server prompt and its post-filter. Name it as a server dependency, or a client filter only if a stable marker exists (no fragile text matching).

## From the link lane (S97 INC-U1): two new answer codes need wording in EN and AR ([NATIVE READ])
- **A-4:** STORE_UNREADABLE: a shop that will not let an app read its page. Offer the typed compare.
- **A-5:** UNRESOLVED_PRODUCT with not_found. Read the exact wire shape (code field, reason field) from S97's branch or merged PR, and from INC-U1_FLIP_NOTE.md in the notes root.

## The gate rule
Each of A-1..A-5 is either IN (client wording or rendering, over the air) or a SERVER DEPENDENCY. A server dependency is named, with file:line, for the owning lane. It is never built in this client unit.
