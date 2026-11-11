# 2026-11-11 data-quality incident: the fix lane (S92-FIX)

This folder is the record of the incident fix lane. It lives on the branch `docs/incident-2026-11-11` (worktree `sc-docs-inc`). The session-81 pivot lane (S91 and its successors) keeps its own record in `../2026-10-22-session-81-state/` on `docs/session-81-state`; this lane never commits there. The relay session forwards this lane's merge and ruling lines to S91 for the main ledger.

## What happened

On 2026-11-11 the owner ran three fragrance comparisons on a phone and found the result page nearly empty. The verified report is `INCIDENT_AND_DATA_PLAN_2026-11-11.md` (the relay's shared notes folder, `incident-2026-11-11/`; twelve ranked root causes, a fix plan NOW / NEXT / STRUCTURAL, a proof on the phone per fix). The first cause is the owner's to fix (the OpenAI credential on the production web service is rejected). The rest are the code units of this lane.

## The proof standard (the owner's, binding)

Nothing is called fixed until it is seen on the app. For every unit:

1. The brief and the PR body carry the PROOF ON THE PHONE from the report: the exact pair to repeat, what must be visible, the backing row or log check.
2. A merge is reported as "merged, NOT yet proven". The relay runs the proof with the owner and sends the dated result.
3. A unit whose effect the report marks uncertain starts with a measurement, and its PR states the measured before and after.
4. Suites and gates stay necessary and are never presented as proof of a production fix.

## Files

| File | What it is |
|---|---|
| `ledger_incident.md` | One python-stamped line per event of this lane |
| `S92FIX_FIRST_REPORT.md` | The first report to the relay: three corrections to the report, the classification and order, the flag rulings, the owner rulings asked |
| `DEFECT_LEDGER_INCIDENT.md` | The unit ids of this lane and their state |
| `specs/` | Briefs, specs, spec reviews, rulings, gates, reports and PR bodies, one set per unit or group |
| `scripts/` | The lane's agent rules (`inc-common.txt`) and args files |

## Rules of this lane (short form)

- Orchestrator Claude Fable 5.2; every agent Opus 5.5 inside Workflow runs; the orchestrator never implements a unit.
- At most two gate-heavy workflows on the box across both build sessions; this lane launches one only after the relay's "slot granted". One pytest and one jest at a time across both sessions (a process probe before every run; this lane's runner tags start with `inc-`).
- Every backend change lands dark behind a new flag (default OFF, read per call, flag-OFF byte-identical and pinned) unless a ruling here classes it as a production bug fix whose OFF path is the defect. Each such ruling is sent to the relay so the owner knows exactly what changes on a deploy.
- All flag flips are the relay's, on the owner's yes per window. This lane sets nothing in production and reads no production value.
- Every merge redeploys the web service. This lane sends "READY TO MERGE" with the deploy-visible delta and merges only on the relay's word.
