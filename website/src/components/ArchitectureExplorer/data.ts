import type { Edge, Node } from "@xyflow/react";

export interface ArchitectureReference {
  label: string;
  href: string;
  kind: "Guide" | "Source" | "Tests";
}

export interface ArchitectureStage {
  id: string;
  order: string;
  title: string;
  summary: string;
  details: string[];
  references: ArchitectureReference[];
  position: { x: number; y: number };
}

export const architectureStages: ArchitectureStage[] = [
  {
    id: "surfaces",
    order: "01",
    title: "Surfaces",
    summary: "CLI, TUI, Desktop, ACP, batch, API, cron, and messaging accept work.",
    details: ["Each surface normalizes user intent before entering the shared agent runtime.", "Surface-specific presentation stays outside the core conversation loop."],
    references: [
      { label: "Architecture guide", href: "/developer-guide/architecture", kind: "Guide" },
      { label: "CLI source", href: "https://github.com/NousResearch/hermes-agent/blob/main/cli.py", kind: "Source" },
      { label: "ACP source", href: "https://github.com/NousResearch/hermes-agent/tree/main/acp_adapter", kind: "Source" },
    ],
    position: { x: 0, y: 0 },
  },
  {
    id: "session-gateway",
    order: "02",
    title: "Session / Gateway",
    summary: "Routing, authorization, history, interrupts, and session identity converge.",
    details: ["Gateway adapters normalize platform events and resolve a durable session key.", "CLI and other direct surfaces restore the same conversation model without gateway routing."],
    references: [
      { label: "Gateway internals", href: "/developer-guide/gateway-internals", kind: "Guide" },
      { label: "Gateway source", href: "https://github.com/NousResearch/hermes-agent/blob/main/gateway/run.py", kind: "Source" },
      { label: "Gateway tests", href: "https://github.com/NousResearch/hermes-agent/tree/main/tests/gateway", kind: "Tests" },
    ],
    position: { x: 300, y: 0 },
  },
  {
    id: "prompt-assembly",
    order: "03",
    title: "Prompt Assembly",
    summary: "Stable instructions, project context, skills, memory, and history form the request.",
    details: ["Prompt tiers preserve a byte-stable cached prefix for the life of a conversation.", "Compression is the controlled exception when history exceeds the context budget."],
    references: [
      { label: "Prompt assembly", href: "/developer-guide/prompt-assembly", kind: "Guide" },
      { label: "Prompt builder", href: "https://github.com/NousResearch/hermes-agent/blob/main/agent/prompt_builder.py", kind: "Source" },
      { label: "Prompt tests", href: "https://github.com/NousResearch/hermes-agent/tree/main/tests/agent", kind: "Tests" },
    ],
    position: { x: 600, y: 0 },
  },
  {
    id: "agent-loop",
    order: "04",
    title: "Agent Loop",
    summary: "AIAgent coordinates model calls, tool turns, budgets, retries, and completion.",
    details: ["The synchronous loop preserves strict message-role alternation across provider and tool turns.", "Interrupts, iteration budgets, fallback, and context compression are enforced here."],
    references: [
      { label: "Agent loop internals", href: "/developer-guide/agent-loop", kind: "Guide" },
      { label: "Agent source", href: "https://github.com/NousResearch/hermes-agent/blob/main/run_agent.py", kind: "Source" },
      { label: "Agent tests", href: "https://github.com/NousResearch/hermes-agent/tree/main/tests/agent", kind: "Tests" },
    ],
    position: { x: 900, y: 0 },
  },
  {
    id: "provider-runtime",
    order: "05",
    title: "Provider Runtime",
    summary: "Provider, model, credentials, API mode, and fallback route resolve per call.",
    details: ["One resolver maps configured provider/model identity to the concrete transport.", "Chat Completions, Codex Responses, and Anthropic Messages retain provider-specific wire behavior."],
    references: [
      { label: "Provider runtime", href: "/developer-guide/provider-runtime", kind: "Guide" },
      { label: "Runtime resolver", href: "https://github.com/NousResearch/hermes-agent/blob/main/hermes_cli/runtime_provider.py", kind: "Source" },
      { label: "Provider tests", href: "https://github.com/NousResearch/hermes-agent/tree/main/tests/providers", kind: "Tests" },
    ],
    position: { x: 1200, y: 0 },
  },
  {
    id: "tools-approvals",
    order: "06",
    title: "Tools / Approvals",
    summary: "Schemas are filtered, calls dispatched, and risky actions held for approval.",
    details: ["Toolsets and availability checks determine the model-visible schema at session start.", "The registry dispatches handlers while approval gates protect dangerous terminal actions."],
    references: [
      { label: "Tools runtime", href: "/developer-guide/tools-runtime", kind: "Guide" },
      { label: "Tool dispatch", href: "https://github.com/NousResearch/hermes-agent/blob/main/model_tools.py", kind: "Source" },
      { label: "Approval tests", href: "https://github.com/NousResearch/hermes-agent/blob/main/tests/tools/test_approval.py", kind: "Tests" },
    ],
    position: { x: 900, y: 250 },
  },
  {
    id: "events-delivery",
    order: "07",
    title: "Events / Delivery",
    summary: "Streaming deltas, tool progress, final output, and hooks return to the surface.",
    details: ["Callbacks translate runtime events into the presentation contract of each surface.", "Gateway delivery handles platform limits, streaming, edits, media, and final reconciliation."],
    references: [
      { label: "Gateway delivery", href: "/developer-guide/gateway-internals#message-flow", kind: "Guide" },
      { label: "Delivery source", href: "https://github.com/NousResearch/hermes-agent/blob/main/gateway/delivery.py", kind: "Source" },
      { label: "Delivery tests", href: "https://github.com/NousResearch/hermes-agent/blob/main/tests/gateway/test_stream_final_contract.py", kind: "Tests" },
    ],
    position: { x: 600, y: 250 },
  },
  {
    id: "state",
    order: "08",
    title: "Sessions / Memory / Usage / State",
    summary: "Messages, lineage, model usage, memory, and routing state persist durably.",
    details: ["SessionDB stores messages, usage attribution, lineage, routing, and searchable state in SQLite.", "Memory providers and session search add recall without changing the stable prompt prefix mid-session."],
    references: [
      { label: "Session storage", href: "/developer-guide/session-storage", kind: "Guide" },
      { label: "State source", href: "https://github.com/NousResearch/hermes-agent/blob/main/hermes_state.py", kind: "Source" },
      { label: "State tests", href: "https://github.com/NousResearch/hermes-agent/blob/main/tests/test_hermes_state.py", kind: "Tests" },
    ],
    position: { x: 300, y: 250 },
  },
];

export const architectureNodes: Node[] = architectureStages.map((stage) => ({
  id: stage.id,
  position: stage.position,
  data: { label: `${stage.order}  ${stage.title}`, summary: stage.summary },
  type: "architectureStage",
  ariaLabel: `${stage.order}, ${stage.title}. ${stage.summary}`,
}));

const lifecycle = ["surfaces", "session-gateway", "prompt-assembly", "agent-loop", "provider-runtime", "tools-approvals", "events-delivery", "state"];

export const architectureEdges: Edge[] = lifecycle.slice(0, -1).map((source, index) => ({
  id: `edge:${source}->${lifecycle[index + 1]}`,
  source,
  target: lifecycle[index + 1],
  type: "smoothstep",
  animated: true,
}));

architectureEdges.push({ id: "edge:state->session-gateway", source: "state", target: "session-gateway", type: "smoothstep", animated: true });
