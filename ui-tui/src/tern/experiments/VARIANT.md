# Variant C — attention-minimal hybrid

Issue: #436

## Question

Can we make the next required action discoverable faster than either baseline by
letting state **earn** attention instead of reserving attention permanently?

## Constraint

Do not treat "minimal" as "hide information." Consequential state must become
more visible, not less. The experiment removes ambient competition around it.

## First implementation slice

Use the shared fixture to test:

1. transcript + composer as the only always-present Hermes-owned surfaces
2. one compact active-state lane while work is running
3. a singular needs-user presentation for approval/clarification/failure
4. completion settling into history
5. inspection on demand rather than persistent diagnostic chrome

No additional visual invention is justified until the shared metrics show where
A or B actually lose attention.

## Success condition

Lowest time-to-needs-user and persistent-element count without reducing glance
comprehension or hiding consequential state.
