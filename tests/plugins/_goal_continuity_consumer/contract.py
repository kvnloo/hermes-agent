"""Python semantic twin of the pinned, OMP-owned goal_continuity contract."""
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from hashlib import sha256

SOURCE_SHA256 = "550c4960ac98e827f0a608086279a150325d6d45da647b9371e1871ebdee8c01"


class Goal(Enum):
    Paused = "Paused"
    Stopped = "Stopped"
    Complete = "Complete"


class Receipts(Enum):
    Missing = "Missing"


class Next(Enum):
    AuthorizedWork = "AuthorizedWork"
    ExhaustedPlan = "ExhaustedPlan"


class Wake(Enum):
    Unregistered = "Unregistered"


@dataclass(frozen=True)
class Registered:
    id: int


@dataclass(frozen=True)
class ExternalDependency:
    wake: Registered | Wake


@dataclass(frozen=True)
class Loaded:
    next: Next | ExternalDependency


@dataclass(frozen=True)
class Active:
    receipts: Receipts | Loaded


class Decision(Enum):
    RespectPause = "RespectPause"
    RespectStop = "RespectStop"
    Finish = "Finish"
    LoadWorkflow = "LoadWorkflow"
    Execute = "Execute"
    Replan = "Replan"


@dataclass(frozen=True)
class Wait:
    id: int


def verify_source(path: str) -> None:
    if sha256(Path(path).read_bytes()).hexdigest() != SOURCE_SHA256:
        raise ValueError("shared goal_continuity source hash mismatch")


def decide(goal: Goal | Active) -> Decision | Wait:
    if isinstance(goal, Goal):
        return {Goal.Paused: Decision.RespectPause, Goal.Stopped: Decision.RespectStop,
                Goal.Complete: Decision.Finish}[goal]
    if goal.receipts == Receipts.Missing:
        return Decision.LoadWorkflow
    following = goal.receipts.next
    if isinstance(following, ExternalDependency):
        return Wait(following.wake.id) if isinstance(following.wake, Registered) else Decision.Replan
    return {Next.AuthorizedWork: Decision.Execute, Next.ExhaustedPlan: Decision.Replan}[following]
