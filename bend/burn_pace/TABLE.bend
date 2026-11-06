# Prints admit() over every (Fresh, Used, Pace) in the order the parity test expects,
# then route(True), route(False). tests/agent/test_burn_pace_law_parity.py compares it
# with agent/burn_pace_gate.admit_cls / route_cls.
import Base
import ./MODEL.bend as M

def main() -> List<Bool>:
  [M.admit(M.FFresh{}, M.UUnder{}, M.PCool{}), M.admit(M.FFresh{}, M.UUnder{}, M.PUnknown{}), M.admit(M.FFresh{}, M.UUnder{}, M.PHot{}),
   M.admit(M.FFresh{}, M.UAtCap{}, M.PCool{}), M.admit(M.FFresh{}, M.UAtCap{}, M.PUnknown{}), M.admit(M.FFresh{}, M.UAtCap{}, M.PHot{}),
   M.admit(M.FStale{}, M.UUnder{}, M.PCool{}), M.admit(M.FStale{}, M.UUnder{}, M.PUnknown{}), M.admit(M.FStale{}, M.UUnder{}, M.PHot{}),
   M.admit(M.FStale{}, M.UAtCap{}, M.PCool{}), M.admit(M.FStale{}, M.UAtCap{}, M.PUnknown{}), M.admit(M.FStale{}, M.UAtCap{}, M.PHot{}),
   M.is_paid(M.route(True{})), M.is_paid(M.route(False{}))]
