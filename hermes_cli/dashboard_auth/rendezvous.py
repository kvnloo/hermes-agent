"""Same-user plugin activation using the token published by this backend."""
from __future__ import annotations

import hmac

from hermes_cli.dashboard_auth.base import DashboardAuthProvider, TokenPrincipal
from hermes_cli.dashboard_auth.registry import register_global_provider
from hermes_cli.dashboard_auth.token_auth import register_token_route

ACTIVATION_PATH = "/api/dashboard/agent-plugins/activate"


class RendezvousTokenProvider(DashboardAuthProvider):
    name = "host-rendezvous"
    display_name = "Local plugin activation"
    supports_token = True
    supports_session = False
    interactive_login = False
    token_paths = frozenset({ACTIVATION_PATH})

    def __init__(self, token: str) -> None:
        self._token = token

    def verify_token(self, *, token: str) -> TokenPrincipal | None:
        if token and self._token and hmac.compare_digest(token.encode(), self._token.encode()):
            return TokenPrincipal(principal="host-owner", provider=self.name, scopes=("plugin-activation",))
        return None

    def start_login(self, *, redirect_uri):
        raise NotImplementedError("Rendezvous tokens have no login flow")

    def complete_login(self, *, code, state, code_verifier, redirect_uri):
        raise NotImplementedError("Rendezvous tokens have no login flow")

    def verify_session(self, *, access_token):
        return None

    def refresh_session(self, *, refresh_token):
        raise NotImplementedError("Rendezvous tokens have no session")

    def revoke_session(self, *, refresh_token):
        return None


def register_activation_auth(token: str) -> None:
    """Called only after this process publishes its owner-only rendezvous token."""
    register_global_provider(RendezvousTokenProvider(token))
    register_token_route(ACTIVATION_PATH)
