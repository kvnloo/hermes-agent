// Two opt-in native Tern inspections, not alternative agents or execution surfaces.
// Visual references: Graphify-Labs / ArchiveExplorer and HANCORE (@hancore_linux).
import type { Key } from '@stencil-hq/tern'

import type { Overlay, OverlayHost } from '../overlay.js'
import {
  type CodeGraph, graphEdges, graphMatches, type MachineSnapshot, readGraph, readMachine, type Snapshot
} from '../reference-dashboards.js'
import { ActionButton } from '../view/action-button.js'

type Dashboard = 'map' | 'machine'
interface Host extends OverlayHost {
  readonly sid: string | null
  readonly overlays: readonly Overlay[]
}
interface Loaders {
  map(): Promise<Snapshot<CodeGraph>>
  machine(): Promise<Snapshot<MachineSnapshot>>
}
const defaultLoaders: Loaders = { map: readGraph, machine: readMachine }
const keyFor = (kind: Dashboard) => kind === 'map' ? 'graphify-map' : 'machine-health'
const labelFor = (kind: Dashboard) => kind === 'map' ? 'Code map · Graphify' : 'Machine health · snapshot'
const count = (value: number | null) => value === null ? 'not measured' : String(value)
const limited = (value: string, limit = 92) => value.slice(0, limit)
const evidence = (risk: string) =>
  risk === 'high' ? '!' : risk === 'medium' ? '▲' : risk === 'low' ? '·' : '?'

/** No background refresh: only explicit opens and Refresh actions read source files. */
export function openReferenceDashboard(
  host: Host, kind: Dashboard, filter = '', loaders: Loaders = defaultLoaders
): Overlay {
  const sid = host.sid
  let closed = false
  let version = 0
  let busy = false
  let selected = ''
  let data: Snapshot<CodeGraph> | Snapshot<MachineSnapshot> | null = null
  let focusIndex = 0

  const current = () => !closed && host.sid === sid && host.overlays.includes(overlay)
  const close = () => host.close(overlay)
  const nodes = () => kind === 'map' && data?.status === 'ready'
    ? graphMatches(data.value as CodeGraph, filter)
    : []
  const selectedNode = () => {
    const matches = nodes()
    return matches.find(n => n.id === selected) ?? matches[0]
  }
  const refresh = async () => {
    if (!current() || busy) { return }
    busy = true
    const readVersion = ++version
    host.changed()
    try {
      const result = await loaders[kind]()
      if (current() && readVersion === version) {
        // Replace atomically. An invalid new file is never displayed as last-known-good live data.
        data = result
        if (kind === 'map') {
          const rows = nodes()
          if (!rows.some(row => row.id === selected)) {
            selected = rows[0]?.id ?? ''
            focusIndex = 0
          }
        }
      }
    } catch {
      if (current() && readVersion === version) {
        data = { status: 'invalid', note: 'Dashboard snapshot could not be opened.' }
      }
    } finally {
      busy = false
      if (current() && readVersion === version) { host.changed() }
    }
  }
  const select = (id: string) => {
    if (!current() || host.overlays.at(-1) !== overlay) { return }
    const rows = nodes()
    if (rows.some(row => row.id === id)) {
      selected = id
      focusIndex = rows.findIndex(row => row.id === id)
      host.changed()
    }
  }

  const overlay: Overlay = {
    key: keyFor(kind),
    modal: true,
    onClose() { closed = true; version++ },
    onKey(key: Key) {
      if (!current() || host.overlays.at(-1) !== overlay) { return true }
      if (key.name === 'escape' || key.name === 'q') {
        close()
      } else if (key.name === 'r') {
        void refresh()
      } else if (kind === 'map' && (key.name === 'up' || key.name === 'down')) {
        const rows = nodes()
        if (rows.length) {
          focusIndex = (focusIndex + (key.name === 'down' ? 1 : -1) + rows.length) % rows.length
          select(rows[focusIndex]!.id)
        }
      }
      return true
    },
    node(id) {
      const valid = current()
      const graph = valid && kind === 'map' && data?.status === 'ready' ? data.value as CodeGraph : null
      const machine = valid && kind === 'machine' && data?.status === 'ready' ? data.value as MachineSnapshot : null
      const rows = graph ? nodes() : []
      const node = graph ? selectedNode() : undefined
      const links = node && graph ? graphEdges(graph, node.id) : []
      const high = machine?.updates.filter(x => x.risk === 'high').length ?? 0
      const medium = machine?.updates.filter(x => x.risk === 'medium').length ?? 0
      const unclassified = machine?.updates.filter(x => x.risk === 'unclassified').length ?? 0
      const severity = machine?.updatesChecked
        ? high ? `${high} high risk flagged by snapshot` : unclassified ? 'Risk classification incomplete' : 'No high risk flagged by snapshot'
        : 'Update check not available'

      return (
        <overlay anchor="center" head={labelFor(kind)} key={id.slice('layer.'.length)} modal role={kind === 'map' ? 'hermes.dashboard.graphify' : 'hermes.dashboard.machine'} size="lg">
          <col gap="sm" key="body">
            <row align="center" gap="sm" key="header">
              <text key="credit" text={kind === 'map'
                ? 'Code structure · Graphify-Labs · ArchiveExplorer reference'
                : 'Host diagnostics · HANCORE (@hancore_linux) design reference'
              } />
              <ActionButton key="refresh" onClick={() => void refresh()} role="omp.btn" text="Refresh  r" />
              <ActionButton key="close" onClick={close} role="omp.btn" text="Close  esc" />
            </row>
            {!valid ? <text key="stale" text="Session changed. Reopen this dashboard in the current session." tone="warning" /> : null}
            {valid && busy ? <text key="loading" text="Reading local snapshot…" /> : null}
            {valid && data && data.status !== 'ready' ? (
              <col gap="xs" key="empty">
                <text key="reason" text={data.note} tone={data.status === 'missing' ? undefined : 'warning'} />
                <text key="path" text={kind === 'map'
                  ? 'Run graphify update . in this project, then reopen /map or press r.'
                  : 'Run the explicit machine snapshot collector; see ui-tsp/REFERENCE_DASHBOARDS.md.'} />
              </col>
            ) : null}
            {graph ? (
              <col gap="sm" key="graph">
                <text key="source" text="graphify-out/graph.json · read only · architecture links, not agent traffic" />
                <text key="totals" text={`${graph.nodes.length} symbols · ${graph.links.length} edges · showing ${rows.length} hubs${filter ? ` matching “${limited(filter, 60)}”` : ''}`} />
                <row gap="sm" key="columns">
                  <col gap="xs" key="roster">
                    <text key="label" text="SYMBOLS  ↑↓ inspect  ·  /map query to filter" />
                    {rows.map(row => (
                      <ActionButton key={row.id} onClick={() => select(row.id)} role="omp.btn"
                        text={`${row.id === (node?.id ?? '') ? '▸' : '·'} ${limited(row.label, 56)} (${row.degree})`} />
                    ))}
                    {!rows.length ? <text key="none" text="No matching symbols." /> : null}
                  </col>
                  <col gap="xs" key="inspector">
                    <text key="inspector-title" text={node ? `INSPECT  ${limited(node.label)}` : 'INSPECT  none'} />
                    {node ? <text key="origin" text={`Source: ${node.sourceFile || 'not reported'}`} /> : null}
                    {node ? <text key="community" text={`Community: ${node.community || 'not reported'}`} /> : null}
                    {links.map((edge, index) => (
                      <text key={`edge-${index}`} text={`${edge.direction === 'out' ? '→' : '←'} ${limited(edge.direction === 'out' ? edge.target : edge.source, 42)} · ${limited(edge.relation, 34)} · ${edge.confidence}`} />
                    ))}
                    {node && !links.length ? <text key="no-edges" text="No referenced edges." /> : null}
                    {node && node.degree > links.length ? <text key="truncated" text={`Showing ${links.length} of ${node.degree} incident edges`} /> : null}
                  </col>
                </row>
                <text key="path" text="Graphify's graph.html is the full interactive force-directed visualization. This native inspector does not execute Graphify." />
              </col>
            ) : null}
            {machine ? (
              <col gap="sm" key="machine">
                <text key="stamp" text={`${limited(machine.machine || 'Unnamed host')} · ${limited(machine.os || 'OS unknown')} · captured ${machine.capturedAt} · NOT LIVE`} />
                <kv items={[
                  { k: '01 PENDING', v: machine.updatesChecked ? `${machine.updates.length} packages` : 'not scanned' },
                  { k: '02 PROBLEMS', v: machine.problemsChecked ? `${machine.problems.length} subjects` : 'not scanned' },
                  { k: '03 HIGH RISK', v: `${high} flagged / ${unclassified} unclassified` },
                  { k: '04 MED RISK', v: String(medium) },
                  { k: '05 DISK USED', v: machine.diskPercent === null ? 'not measured' : `${Math.round(machine.diskPercent)}%` },
                  { k: '06 DISK FREE', v: machine.availableGiB === null ? 'not measured' : `${machine.availableGiB.toFixed(1)} GiB` },
                  { k: 'PACKAGES INSTALLED', v: count(machine.installedPackages) }
                ]} key="metrics" />
                <text key="eye" text={`  ◌ ── ◉ [${'█'.repeat(Math.min(16, high))}${'▒'.repeat(Math.min(16, medium))}${'·'.repeat(Math.min(16, unclassified)) || 'not assessed'}] ◉ ── ◌`} />
                <text key="risk" text={severity} tone={high ? 'warning' : undefined} />
                <text key="updates-head" text="UPDATES · package / old → new · risk (top 10)" />
                {machine.updates.slice(0, 10).map((item, i) => <text key={`upd-${i}`}
                  text={`${evidence(item.risk)} ${limited(item.package, 56)} ${limited(item.from, 16)} → ${limited(item.to, 16)} · ${item.risk}`} />)}
                {!machine.updates.length ? <text key="no-updates" text={machine.updatesChecked ? 'None reported by collector.' : 'Update list not scanned.'} /> : null}
                <text key="problem-head" text="PROBLEMS · measured subjects (top 8)" />
                {machine.problems.slice(0, 8).map((p, i) => <text key={`problem-${i}`} text={`${p.count} × ${limited(p.subject)} · ${p.kind}`} />)}
                {!machine.problems.length ? <text key="no-problems" text={machine.problemsChecked ? 'None reported by collector.' : 'Problem history not scanned.'} /> : null}
                <text key="events-head" text="RECENT EVENTS · snapshot entries (top 8)" />
                {machine.events.slice(0, 8).map((ev, i) => <text key={`event-${i}`} text={`${ev.time}  ${limited(ev.source, 30)}  ${limited(ev.message, 100)}`} />)}
                {!machine.events.length ? <text key="no-events" text="No events provided by snapshot." /> : null}
                <text key="safety" text="Review first. This panel cannot upgrade packages, run commands or restart services." />
              </col>
            ) : null}
          </col>
        </overlay>
      )
    }
  }

  host.open(overlay)
  void refresh()
  return overlay
}
