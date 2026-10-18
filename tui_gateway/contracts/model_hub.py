"""Native model management: Hermes auxiliary slots and one ordered profile fallback chain."""
from typing import Literal

from pydantic import Field

from .base import Params, Result
from .config_free_tier_control import ModelOptionProvider
from .registry import method


class ModelHubParams(Params):
    session_id: str


class ModelRoute(Result):
    provider: str
    model: str


class ModelRole(Result):
    id: str
    label: str
    scope: Literal["profile"] = "profile"
    route: ModelRoute | None = None


class ModelHubOperations(Result):
    role_scopes: list[str] = Field(default_factory=lambda: ["profile"])
    fallback_scopes: list[str] = Field(default_factory=lambda: ["profile"])
    max_fallbacks: int = 8
    native_login: bool = False
    login_hint: str = "Use Hermes model setup in a terminal; this inventory never accepts login secrets."
    writable: bool


class ModelHubGetResult(Result):
    profile: str
    revision: str
    roles: list[ModelRole]
    fallbacks: list[ModelRoute]
    providers: list[ModelOptionProvider]
    operations: ModelHubOperations


class ModelHubSetParams(ModelHubParams):
    profile: str
    revision: str
    scope: Literal["profile"]
    operation: Literal["role", "fallbacks", "reset_roles"]
    role: str | None = None
    route: ModelRoute | None = None
    fallbacks: list[ModelRoute] = Field(default_factory=list)
    confirmed: bool = False


class ModelHubSetResult(Result):
    confirm_required: bool
    confirm_message: str = ""


method("model.hub.get", params=ModelHubParams, result=ModelHubGetResult,
       doc="Safe provider inventory, supported-operation metadata and profile auxiliary/fallback assignments.")
method("model.hub.set", params=ModelHubSetParams, result=ModelHubSetResult,
       doc="Revision-bound profile role set/clear, scoped auxiliary reset or bounded ordered fallback replacement.")
