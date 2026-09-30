# Beyond-Agent Canary Lab

Tracking: #330, #340, #341.

This branch is a **research artifact lane**, not a product integration branch.

## Claim protocol

A worker claims one experiment issue (#342–#371) and should avoid editing another experiment's artifacts.

Suggested artifact directory:

```
lab/beyond-agent/<issue-number>/
  README.md
  fixtures/
  results/
  result.json
```

A result is successful when it produces discriminating evidence, including a falsification.

## Required result fields

Use `result.schema.json`.

The key field is `verdict`:

- `supports`
- `falsifies`
- `ambiguous`

Never convert "prototype ran" into "supports".

## Branch convention

Workers may fork from this branch using:

```
lab/beyond-agent/<issue-number>-<short-slug>
```

No upstream NousResearch PR is implied.

## Canary order

Wave A — cheap discriminators:
#342 #345 #348 #351 #354 #357 #360 #363 #366 #370 #371

Wave B — replay/scaling:
#343 #346 #349 #352 #355 #358 #361 #364 #367 #369

Wave C — adversarial kill:
#344 #347 #350 #353 #356 #359 #362 #365 #368

Cross-paradigm work (#369–#371) may run independently.

## Scientific rule

Do not tune the fixture after seeing the candidate result without recording a new fixture revision.

Keep raw measurements. Do not collapse evidence into one score.
