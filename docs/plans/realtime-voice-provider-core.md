# Realtime voice provider core

This slice defines a provider-neutral transport boundary without adding a vendor client or a new model-visible tool.

## Authority boundary

- `RealtimeVoiceProvider` creates transport sessions.
- `RealtimeVoiceSession` owns provider audio/text ingress, audio turn-taking, cancellation, and transport events.
- `RealtimeVoiceCoordinator` remains Hermes-owned. It admits bounded events, rejects stale cancellation epochs, deduplicates reconnect events and tool call IDs, reconciles generated text with what was heard, and returns only results from an injected Hermes dispatcher.
- Providers cannot execute tools, approve actions, mutate memory, or write durable conversation history through this interface.
- Existing STT → Hermes → TTS paths are unchanged and can be selected through the coordinator's legacy fallback.

## Event semantics

`Transcript` is cumulative and keyed by provider-neutral `item_id`; newer partial/final text replaces older text. `AssistantGenerated`, `AssistantHeard`, and `AssistantFinal` separate generated output, audible output, and a structured completed response. This supports later text-transcript surfaces such as Web Speech or native Android recognition without putting those clients in core.

Every event carries an immutable `event_id` and Hermes cancellation `epoch`. Replayed IDs and stale epochs are ignored. Tool calls additionally deduplicate by `call_id`; grouped calls settle before the coordinator requests one continuation.

## Extension seam

Plugins register implementations with `PluginContext.register_realtime_voice_provider()`. Registration is profile-scoped and unload-safe, matching existing TTS and transcription provider behavior. Core ships no xAI, OpenAI, Gemini, Discord, Desktop, WebUI, Android, or browser transport.

## Verification contract

The fake-provider suite covers two differently shaped consumers, registry resolution and plugin unload, session lifecycle, text ingress, cumulative transcript replacement, structured final responses, generated-vs-heard reconciliation, stale-event rejection, bounded admission, grouped parallel tool settlement, approval/denial routing, exactly-once results, reconnect dedupe, audit redaction, and unavailable-provider fallback.
