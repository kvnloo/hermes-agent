# Five-second glance test

Issue: #436

Use this protocol for A/B/C. Do not explain the variant before the test.

## Setup

- same `tern-ux-v1` fixture step
- same viewport class: narrow, normal or wide
- same Tern theme/appearance
- same starting focus
- no mouse motion or animation pre-roll unique to one variant
- reveal the state and start the timer

## Ask after five seconds

1. **What is Hermes doing?**
2. **Does it need you right now?**
3. **What happens next?**
4. **Where would you type?**
5. **How would you inspect more detail?**

Record yes/no correctness for each answer.

For `needs-user` fixture steps, also record milliseconds until the participant
first identifies the actionable element. This is the
`timeToNeedsUserMs` field in the experiment receipt.

## Stop conditions

A run is invalid if:

- the participant already saw the same variant/state immediately beforehand;
- viewport dimensions differ from the paired variants;
- one branch includes debug/dev chrome the others do not;
- a transition animation was already partially complete when timing started;
- the tester had to be told where to look.

## Interpretation

This test does not decide aesthetic preference. It measures whether the visual
hierarchy communicates task state quickly enough to justify itself.
