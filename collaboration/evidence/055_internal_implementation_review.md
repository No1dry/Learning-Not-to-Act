# Task055 internal focused implementation review

This is an internal review of the isolated implementation against the pinned Task055 work order. The separate Codex acceptance and user-run real construction remain pending.

## Finding and disposition

**Important, resolved.** The original `preparation.read_bank` verified artifacts only for ready rows. An affected CPU fake produced a failed source followed by an interrupted source. Deleting the first source's `failure.json` and control ledger originally left the readback at two failed sources without an integrity error. Failed rows now persist their per-source artifact inventory and SHA-256 values. The reader checks that inventory and any recorded ledger, binds ready source and ledger paths to each episode, and rejects missing or modified evidence. Independent focused verification returned five passing tests covering deletion/modification, the checkpoint storage stop, and the source build/readback round trip. The final combined54-test run is archived in `055_cpu_fake.junit.xml`; the original five-test review run remains in local handoff evidence.

## Native and orchestration checks

- The final scene check matches the pinned upstream living-room implementation. The workspace table appears in parsed fixtures and is skipped in the instantiated fixture map. The basket site must belong to the basket body's descendant tree. Exact BDDL bytes, original indexed array, compiled model topology, derived predicates, goal order and instruction are checked at their respective boundaries.
- The source producer settles the fixed canonical index, transplants only A's measured free-joint pose/velocity and preserves the complementary state bits. It reuses the core physical validator, native release measurements and protocol confirmation window. Independent restores compare the actual typed observation with the construction artifact under the core RGB rule. I separately removed the wrist camera in the CPU double and observed admission fail.
- Source order and caps are fixed at three times fifty. Preparation records a running source before native work. Each control call is charged before stepping. A checkpoint storage error stops the current build and subsequent sources. Existing output is rejected. This limit is per construction directory; a second independently chosen directory is a new invocation under operator control.
- The only CLI routes are build and inspect. The package adds no normal-bank, training, model, registration change to an old suite, or scoring entry point.

No outstanding critical or important defect identified in the reviewed paths. Verification was limited to source inspection and Task055 CPU/fake checks. Real parsing in an installed native runtime, physical construction, real population yield and model outcomes remain unmeasured.
