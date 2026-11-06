# Owner laws for burn_pace (Kevin, 2026-11-05: "respect pace by always automatically
# adjusting usage of free tier models"). Universally quantified over MODEL's domains.
# Not proven here: that the twin classifies readings correctly (parity test) or that the
# running gateway loads the twin (deployment receipt).
import Base
import ./MODEL.bend as M

# A stale or missing reading never admits a paid row (fail closed).
law stale_never_admits:
  for u: M.Used
  for p: M.Pace
  {M.admit(M.FStale{}, u, p) == False{} : Bool}

# A row at its weekly cap never serves, whatever its pace.
law at_cap_never_admits:
  for f: M.Fresh
  for p: M.Pace
  {M.admit(f, M.UAtCap{}, p) == False{} : Bool}

# A row burning at or over 1.5x sustainable pace never serves.
law hot_never_admits:
  for f: M.Fresh
  for u: M.Used
  {M.admit(f, u, M.PHot{}) == False{} : Bool}

# Non-vacuity: a fresh, under-cap, cool or unreported row is admitted.
law fresh_cool_admits:
  {M.admit(M.FFresh{}, M.UUnder{}, M.PCool{}) == True{} : Bool}

law fresh_unknown_admits:
  {M.admit(M.FFresh{}, M.UUnder{}, M.PUnknown{}) == True{} : Bool}

# When no paid row is admitted the turn goes to the free lane, never to a drained row.
law none_admitted_routes_free:
  {M.route(False{}) == M.RFree{} : M.Route}

law admitted_routes_paid:
  {M.route(True{}) == M.RPaid{} : M.Route}

# Composition: a single hot row's turn routes free.
law hot_row_routes_free:
  for f: M.Fresh
  for u: M.Used
  {M.route(M.admit(f, u, M.PHot{})) == M.RFree{} : M.Route}
