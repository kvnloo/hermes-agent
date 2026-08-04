/**
 * Spatial — infinite project-knowledge desk (PRD/FRD/roadmap/specs/decisions).
 * Complements Kanban (execution state). Visual language from Spatial (get-spatial.com).
 *
 * Opt-in (`defaultEnabled: false`). Enable in Settings ▸ Plugins, then open /spatial.
 */

import './spatial.css'

import {
  type HermesPlugin,
  host,
  type KeybindContribution,
  KEYBINDS_AREA,
  PALETTE_AREA,
  type PaletteContribution,
  type RouteContribution,
  ROUTES_AREA,
  SIDEBAR_NAV_AREA,
  type SidebarNavContribution
} from '@hermes/plugin-sdk'

import { SpatialDeskPage } from './desk'

const open = () => host.navigate('/spatial')

const plugin: HermesPlugin = {
  id: 'spatial',
  name: 'Spatial',
  defaultEnabled: false,
  register(ctx) {
    ctx.registerMany([
      {
        id: 'page',
        area: ROUTES_AREA,
        data: { path: '/spatial' } satisfies RouteContribution,
        render: () => <SpatialDeskPage />
      },
      {
        id: 'nav',
        area: SIDEBAR_NAV_AREA,
        order: 55,
        data: { codicon: 'notebook', label: 'Spatial', path: '/spatial' } satisfies SidebarNavContribution
      },
      {
        id: 'open',
        area: PALETTE_AREA,
        data: {
          id: 'spatial.open',
          label: 'Spatial: Open desk',
          keywords: ['spatial', 'canvas', 'desk', 'prd', 'docs', 'roadmap'],
          run: open
        } satisfies PaletteContribution
      },
      {
        id: 'open',
        area: KEYBINDS_AREA,
        data: {
          id: 'spatial.open',
          category: 'view',
          defaults: ['mod+alt+s'],
          label: 'Spatial: Open desk',
          run: open
        } satisfies KeybindContribution
      }
    ])
  }
}

export default plugin
