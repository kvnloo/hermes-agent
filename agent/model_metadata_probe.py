"""Proxy policy for model-metadata probes."""


def _probe_trust_env(base_url: str) -> bool:
    """Probe local engines directly, but keep environment proxies for hosted endpoints."""
    from agent.model_metadata import is_local_endpoint

    return not is_local_endpoint(base_url)
