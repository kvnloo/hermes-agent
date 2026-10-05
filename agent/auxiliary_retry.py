"""Request preparation for same-provider auxiliary credential recovery."""

from typing import Any, Dict, Optional, Tuple


def prepare_same_provider_retry(
    *, task: Optional[str], resolved_provider: str, resolved_model: Optional[str],
    resolved_base_url: Optional[str], resolved_api_key: Optional[str],
    resolved_api_mode: Optional[str], main_runtime: Optional[Dict[str, Any]],
    final_model: Optional[str], messages: list, temperature: Optional[float],
    max_tokens: Optional[int], tools: Optional[list], effective_timeout: float,
    effective_extra_body: dict, reasoning_config: Optional[dict], async_mode: bool,
    extra_headers: Optional[Dict[str, str]] = None,
) -> Tuple[Any, Dict[str, Any]]:
    """Rebuild (client, request kwargs) for a same-provider retry after credential recovery."""
    from agent import auxiliary_client as ac

    if task == "vision":
        effective_provider, retry_client, retry_model = ac.resolve_vision_provider_client(
            provider=resolved_provider, model=final_model, base_url=resolved_base_url,
            api_key=resolved_api_key, async_mode=async_mode,
        )
    else:
        retry_client, retry_model = ac._get_cached_client(
            resolved_provider, resolved_model, async_mode=async_mode, base_url=resolved_base_url,
            api_key=resolved_api_key, api_mode=resolved_api_mode, main_runtime=main_runtime,
        )
        effective_provider = ac._effective_provider_for_client(retry_client, resolved_provider)
    if retry_client is None:
        raise RuntimeError(
            f"Auxiliary {task or 'call'}: provider {resolved_provider} could not be rebuilt after recovery"
        )
    retry_base = str(getattr(retry_client, "base_url", "") or "")
    retry_kwargs = ac._build_call_kwargs(
        effective_provider or resolved_provider, retry_model or final_model, messages,
        temperature=temperature, max_tokens=max_tokens, tools=tools, timeout=effective_timeout,
        extra_body=effective_extra_body, reasoning_config=reasoning_config,
        base_url=retry_base or resolved_base_url, task=task,
    )
    # Preserve per-request attribution headers (e.g. Copilot ``x-initiator``) so the retry keeps capability gating.
    if extra_headers:
        # Copilot's ``x-initiator: user``) across the rebuilt-client retry — dropping them here would let a
        # recovery retry silently lose capability gating (#60293).
        # Preserve per-request attribution headers across the rebuilt-client retry — see the sync variant
        # above (#60293).
        retry_kwargs["extra_headers"] = dict(extra_headers)
    if ac._is_anthropic_compat_endpoint(resolved_provider, retry_base):
        retry_kwargs["messages"] = ac._convert_openai_images_to_anthropic(retry_kwargs["messages"])
    return retry_client, retry_kwargs
