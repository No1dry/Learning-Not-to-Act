# Selector wire parsing and raw-output audit (026)

The first user-started 025 rollout paused at its instruction-only registry call:
159 generated tokens failed direct json.loads, with zero visual inputs and zero
executed policy actions. OFT startup/nested identity and environment initialization
had passed. This is a technical pause, not task failure or a measured success rate.
The old code did not retain generated text, so the original offending text cannot
be reconstructed or asserted to be merely a Markdown fence.

026 shares the existing whole-output wrapper decoder between offline and online
paths. It accepts bare JSON or exactly one complete outer json/untyped code fence,
without prose, nested blocks, substring extraction, field repair or retries. The
existing registry/prediction validators are unchanged; malformed or semantically
wrong output still fails. Training prompt, weights, generation settings, goal
rules and benchmark scoring are unchanged.

Every actual generation now retains raw_output and staged wrapper/json/schema
parsing details in last_input_audit, including failure paths. Existing RPC error
frames and sidecars carry that audit. No raw text is added to model history or
actor input. Inference CLI `--audit-output NEW_JSON` also saves raw output/error
on success or failure before closing the selector; existing files are refused.

```bash
python -u -m egrs.selector.infer --mode registry \
  --config trained-selector.json --input instruction-only.json \
  --output NEW_RESULT.json --audit-output NEW_RAW_AUDIT.json
```

This is a user-started text-only model call, not file-only work. It loads the
trained selector, not OFT or a simulator, and consumes no robot rollout. Its
purpose is to capture the missing output and distinguish transport formatting
from incorrect registry content, not select weights or tune task success. Do not
repeat it automatically or claim the old failure was resolved before seeing the
new raw/schema result. Old failure output remains immutable. If registry content
itself is incorrect, report that evidence rather than silently switching to
ground-truth task definitions, a different model or a looser validator.
