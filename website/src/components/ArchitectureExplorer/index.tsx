import React, { useEffect, useMemo, useState } from "react";
import Link from "@docusaurus/Link";
import {
  Background,
  Controls,
  Handle,
  MarkerType,
  Position,
  ReactFlow,
  type NodeProps,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import {
  architectureEdges,
  architectureNodes,
  architectureStages,
  type ArchitectureStage,
} from "./data";
import styles from "./styles.module.css";

interface StageNodeData extends Record<string, unknown> {
  label: string;
  summary: string;
}

function StageNode({ data, selected }: NodeProps): React.ReactElement {
  const stage = data as StageNodeData;
  return (
    <div className={`${styles.node} ${selected ? styles.nodeSelected : ""}`}>
      <Handle type="target" position={Position.Left} className={styles.handle} />
      <span className={styles.nodeTitle}>{stage.label}</span>
      <span className={styles.nodeSummary}>{stage.summary}</span>
      <Handle type="source" position={Position.Right} className={styles.handle} />
    </div>
  );
}

function StageDetails({ stage }: { stage: ArchitectureStage }): React.ReactElement {
  return (
    <aside className={styles.details} aria-live="polite" aria-label={`${stage.title} details`}>
      <span className={styles.eyebrow}>Stage {stage.order}</span>
      <h3>{stage.title}</h3>
      <p>{stage.summary}</p>
      <ul>
        {stage.details.map((detail) => <li key={detail}>{detail}</li>)}
      </ul>
      <nav aria-label={`${stage.title} references`}>
        {stage.references.map((reference) => (
          <Link key={reference.href} to={reference.href} className={styles.reference}>
            <span>{reference.kind}</span>{reference.label}
          </Link>
        ))}
      </nav>
    </aside>
  );
}

function StaticArchitecture(): React.ReactElement {
  return (
    <section className={styles.staticFallback} aria-label="Hermes request lifecycle">
      <p className={styles.fallbackIntro}>Complete request lifecycle (interactive explorer requires JavaScript):</p>
      <ol className={styles.staticGrid}>
        {architectureStages.map((stage) => (
          <li key={stage.id}>
            <strong>{stage.title}</strong>
            <p>{stage.summary}</p>
            <ul>
              {stage.details.map((detail) => <li key={detail}>{detail}</li>)}
            </ul>
            <div className={styles.staticLinks}>
              {stage.references.map((reference) => <Link key={reference.href} to={reference.href}>{reference.label}</Link>)}
            </div>
          </li>
        ))}
      </ol>
    </section>
  );
}

export default function ArchitectureExplorer(): React.ReactElement {
  const [hydrated, setHydrated] = useState(false);
  const [selectedId, setSelectedId] = useState(architectureStages[0].id);
  const selectedStage = architectureStages.find((stage) => stage.id === selectedId) ?? architectureStages[0];
  const nodeTypes = useMemo(() => ({ architectureStage: StageNode }), []);
  const edges = useMemo(() => architectureEdges.map((edge) => ({
    ...edge,
    markerEnd: { type: MarkerType.ArrowClosed },
  })), []);

  useEffect(() => setHydrated(true), []);

  if (!hydrated) return <StaticArchitecture />;

  return (
    <section className={styles.explorer} aria-label="Interactive Hermes request lifecycle explorer">
      <div className={styles.instructions} id="architecture-explorer-instructions">
        Select a stage to inspect it. Use Tab to focus a node, Enter to select it, and the controls to zoom or fit the lifecycle.
      </div>
      <div className={styles.canvas} aria-describedby="architecture-explorer-instructions">
        <ReactFlow
          nodes={architectureNodes}
          edges={edges}
          nodeTypes={nodeTypes}
          nodesDraggable={false}
          nodesConnectable={false}
          elementsSelectable
          nodesFocusable
          edgesFocusable={false}
          panOnScroll
          minZoom={0.5}
          maxZoom={1.5}
          fitView
          fitViewOptions={{ padding: 0.12 }}
          onNodeClick={(_, node) => setSelectedId(node.id)}

          proOptions={{ hideAttribution: false }}
          aria-label="Hermes request lifecycle. Nine connected stages from surfaces through durable state and the next turn."
        >
          <Background gap={24} size={1} />
          <Controls showInteractive={false} />
        </ReactFlow>
      </div>
      <StageDetails stage={selectedStage} />
      <details className={styles.semanticCopy}>
        <summary>Read the complete architecture as text</summary>
        <StaticArchitecture />
      </details>
    </section>
  );
}
