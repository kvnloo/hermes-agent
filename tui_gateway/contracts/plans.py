"""Live-session, revision-bound plan review; ordinary Markdown is never authority."""
from typing import Literal

from pydantic import Field, StrictBool

from .base import Result
from .common import SessionParams
from .registry import method


class PlanAnnotation(Result):
    section: int = Field(ge=0)
    text: str = Field(min_length=1, max_length=16000)


class PlanRevision(Result):
    id: str
    revision: int = Field(ge=1)
    text: str
    annotations: list[PlanAnnotation]
    decision: Literal["pending", "approved", "refined"]


class PlanStatusResult(Result):
    enabled: bool
    generating: bool
    plan: PlanRevision | None


class PlanModeParams(SessionParams):
    enabled: StrictBool


class PlanTargetParams(SessionParams):
    plan_id: str = Field(min_length=1)
    revision: int = Field(ge=1, strict=True)


class PlanEditParams(PlanTargetParams):
    text: str = Field(min_length=1, max_length=200000)


class PlanAnnotateParams(PlanTargetParams):
    section: int = Field(ge=0, strict=True)
    text: str = Field(max_length=16000)


class PlanDecideParams(PlanTargetParams):
    intent: Literal["approve", "refine"]
    feedback: str = Field(default="", max_length=16000)


method("plan.status", params=SessionParams, result=PlanStatusResult)
method("plan.mode", params=PlanModeParams, result=PlanStatusResult)
method("plan.edit", params=PlanEditParams, result=PlanStatusResult)
method("plan.annotate", params=PlanAnnotateParams, result=PlanStatusResult)
method("plan.decide", params=PlanDecideParams, result=PlanStatusResult)
