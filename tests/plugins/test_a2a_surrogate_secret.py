"""A2A bearer comparisons must fail closed for surrogate-escaped configured secrets."""

import pytest

from plugins.platforms.a2a.security import A2ASecurityContext


@pytest.mark.parametrize("credential_source", ("peer", "shared"))
def test_surrogateescaped_configured_token_refuses_unknown_bearer(credential_source):
    # POSIX os.environ can decode an invalid UTF-8 byte 0x83 as \udc83.
    configured_token = "secret\udc83"
    context = A2ASecurityContext(
        bearer_token=configured_token if credential_source == "shared" else "",
        peer_tokens=((configured_token, "alice"),) if credential_source == "peer" else (),
        trusted_peers=frozenset(),
        allow_all_users=False,
        requested_host="127.0.0.1",
        push_secret="",
    )

    assert context.authenticate("Bearer definitely-wrong", "127.0.0.1") is None
