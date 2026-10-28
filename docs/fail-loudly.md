# Fail-loudly contract

The demo must show missing or immature data explicitly instead of replacing it with zero.

## Rules

1. A ratio without a denominator is `null`, never `0`.
2. A weekly metric is not comparable until the week is complete and T+1 has passed.
3. A tier cell with fewer than 10 due loans per group remains visible with numerator/denominator but is not tested.
4. A model with unknown direction or insufficient sample returns a neutral verdict.
5. An Agent answer includes a caveat when it relies on synthetic data.
6. A pending write action has `executed=false` until `Command(resume=...)` is approved.

## UI behavior

- `null` renders as `—`.
- Sample gates render as `sample gate`.
- Small samples render as `待观察`, not a negative risk conclusion.
- HTTP/API failures render an explicit error block.

## API behavior

- Invalid run IDs return `404`.
- Invalid approval decision is rejected by Pydantic validation.
- Health endpoint reports the actual runtime stack.
