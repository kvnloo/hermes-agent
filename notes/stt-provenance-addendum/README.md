# Correction: STT fallback evidence uses SDK stand-ins

The earlier STT receipt and post-v4 delivery packet incorrectly described [the test-only consumer `e0c7bbc`](https://github.com/kvnloo/hermes-agent/commit/e0c7bbc3b6f8e04e099eb7c4496c2c82edf8a638) as using the actual installed PTB `BadRequest`. It uses the exception stand-in supplied by the gateway test conftest. The claim that only `Bot.send_message` was mocked is also withdrawn: Telegram SDK modules and constants were stand-ins.

At the preserved [Artemonim owner head](https://github.com/NousResearch/hermes-agent/commit/205553904950dcdadebae52535c7b73ac7ca1eda), `tests/gateway/conftest.py` installs Telegram stand-ins before test collection unless real `telegram` is already imported. Merely installing PTB does not meet that condition. The canonical runner starts a fresh pytest subprocess per file.

A subsequent provenance-only diagnostic at the exact published commit, using the recorded interpreter and canonical startup, observed `BadRequest.__module__ = tests.gateway.conftest`, its source as `tests/gateway/conftest.py`, and `telegram` as `unittest.mock.MagicMock` without a module file. The diagnostic passed; the original functional test was deselected. Historical logs did not record exception provenance. The diagnostic file was restored byte-for-byte afterward; no published code or historical packet was rewritten.

The original causal strip/decode-order failure, restored one-test pass and 11 child-delta checks remain evidence that real Hermes formatting, metadata and adapter fallback code preserve literal transcript text **under the existing SDK stand-ins**. They do not establish real-PTB compatibility, live Telegram behavior or current-main integration. This correction adds no functional test qualification.

The environment history is unchanged: official `python-telegram-bot==22.8` was installed without dependencies from a verified 769,397-byte wheel (SHA-256 `42373918097f1b837cc4e717d588c19ea79651497ec712bb5b0c76e5e63c50e1`). That installation was not required by the recorded stand-in harness path and did not establish real SDK use. No dependency is being removed or retroactively described as absent.

`evidence.json` records exact identities, diagnostic observations and local evidence hashes. Raw logs remain local. This is an additive evidence correction, not a new fix or a replacement of the original contributor’s work.
