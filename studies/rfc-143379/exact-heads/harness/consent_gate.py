"""Downstream candidate only. No production caller supplies this provenance yet.

The host must retain authenticated user consent outside model-visible history.
The host must bind every proposed write, including a whole batch, to its sources.
A model-supplied role, source ID, 'trusted' field, or consent claim is not authority.
This module does not parse model text to establish trust. Missing bindings fail closed.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import Enum
from typing import Callable


class Authority(str, Enum):
    AUTHENTICATED_USER = "authenticated_user_transport"
    UNTRUSTED_TOOL = "untrusted_tool_result"
    MODEL_SUMMARY = "model_generated_summary"


class Consent(str, Enum):
    ALLOW = "allow_persistence"
    DENY = "deny_persistence"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class SourceConsent:
    source_id: str
    authority: Authority
    consent: Consent


@dataclass(frozen=True)
class WriteBinding:
    proposal_digest: str
    source_ids: tuple[str, ...]


@dataclass(frozen=True)
class HostProvenance:
    """In-process input from a trusted host adapter, not deserialized tool arguments.

    Types are not a security sandbox. The caller must keep construction of these
    objects outside model-controlled dispatch and must not trust model-selected links.
    The fixture host is the only implemented adapter in this downstream experiment.
    """

    sources: tuple[SourceConsent, ...]
    bindings: tuple[WriteBinding, ...]


def proposal_digest(*, action=None, target="memory", content=None, old_text=None,
                    new_text=None, operations=None) -> str:
    """Bind the complete production payload. Store objects are not model arguments."""
    payload = {"action": action, "target": target, "content": content,
               "old_text": old_text, "new_text": new_text, "operations": operations}
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"),
                         ensure_ascii=False, allow_nan=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _refusal(reason: str) -> str:
    # Do not echo source text or the rejected proposal into a durable response log.
    return json.dumps({"success": False, "blocked": True,
                       "consent_gate": "candidate_trusted_source_opt_out",
                       "reason": reason})


def guarded_memory_tool(production_memory_tool: Callable[..., str], *,
                        trusted_provenance: HostProvenance | None,
                        action=None, target="memory", content=None, old_text=None,
                        new_text=None, operations=None, store=None) -> str:
    """Reject before calling the real tool, its staging gate, or its file-backed store.

    Unknown source mappings block the whole write. A deny on any bound source blocks
    the whole batch. Compaction must retain the original authenticated source binding.
    The host can delegate allowed writes to the unchanged production API.
    """
    if not isinstance(trusted_provenance, HostProvenance):
        return _refusal("missing_trusted_provenance")
    payload = {"action": action, "target": target, "content": content,
               "old_text": old_text, "new_text": new_text, "operations": operations}
    digest = proposal_digest(**payload)
    matches = [binding for binding in trusted_provenance.bindings
               if binding.proposal_digest == digest]
    if len(matches) != 1 or not matches[0].source_ids:
        return _refusal("missing_or_ambiguous_source_binding")
    sources = {source.source_id: source for source in trusted_provenance.sources}
    if len(sources) != len(trusted_provenance.sources):
        return _refusal("ambiguous_source_registry")
    bound = [sources.get(source_id) for source_id in matches[0].source_ids]
    if any(source is None for source in bound):
        return _refusal("unknown_bound_source")
    if any(source.authority != Authority.AUTHENTICATED_USER for source in bound):
        return _refusal("untrusted_source_authority")
    if any(source.consent == Consent.DENY for source in bound):
        return _refusal("source_opted_out")
    if any(source.consent != Consent.ALLOW for source in bound):
        return _refusal("source_consent_unknown")
    return production_memory_tool(**payload, store=store)
