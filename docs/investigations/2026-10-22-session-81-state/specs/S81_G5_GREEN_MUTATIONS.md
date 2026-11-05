# S81-G5 GREEN mutation table (the two GREEN gate rows; byte copies of scripts/cron_learning.py)

Harness <scratchpad>/S81-G5_green/mut/gr_mut.py: .qa-mutation.lock held during the run and removed after; the target
restored from the byte copy and sha256-verified after each mutant (f6aa1f6ad31257b739fc5c92807056096d396966351898c10cd27bfbd2f28f20).

| id | inverse edit (exact-string, matched once) | killing node | result | pyt |
|---|---|---|---|---|
| GR1-inv | `_Cases.add` records an actor only on the case's first report (GC-2 inverse) | tests/test_s81_g5_gate_rows.py::test_g5_gr1_two_actors_one_case | KILLED: AssertionError (1, 1, False) != (1, 2, False) | [pyt] tag=g5green-mut-GR1-inv start=2026-11-05 04:35:12 end=2026-11-05 04:35:16 elapsed=4s bound=600s status=FAIL rc=1 (1 failed, 1 passed) |
| GR2-inv | the de-identification screen moved after the per-category cut (GC-3 inverse) | tests/test_s81_g5_gate_rows.py::test_g5_gr2_screen_before_cut | KILLED: AssertionError count 4 != 5 | [pyt] tag=g5green-mut-GR2-inv start=2026-11-05 04:35:16 end=2026-11-05 04:35:24 elapsed=8s bound=600s status=FAIL rc=1 (1 failed, 1 passed) |

Green on the real bytes: [pyt] tag=g5green-gr start=2026-11-05 04:34:51 end=2026-11-05 04:34:54 elapsed=3s bound=600s status=OK rc=0 (2 passed; hermeticity 2; netguard 0).
