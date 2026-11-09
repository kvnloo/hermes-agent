import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'

import { appCardProblem, brandForServer, projectRoutePath } from './openui-app-card-model'
import { inspectOpenUiBoard } from './openui-catalog'
import { RichCodeBlock } from './registry'

// Exact completed source fences from T3 Code experiments/openui-lab/app-cards.test.ts
// at 3cf6d0c655d22e249398fb7ea36198bf73b4e63d.
const ride = [
  'root = Board("Ride to SFO", "UberX is the cheapest option.", [rides])',
  'rides = RideOptions("uber", "Ferry Building", "SFO Terminal 2", [{name: "UberX", minutes: 4, price: "$31.20", seats: 4}, {name: "Comfort", minutes: 6, price: "$38.90", seats: 4}, {name: "UberXL", minutes: 9, price: "$52.10", seats: 6}])'
].join('\n')

const mail = [
  'root = Board("Invoices", "Two unread invoices from Acme.", [mail])',
  'mail = MailList("invoices from Acme", [{from: "Acme Billing", subject: "Invoice #4512", snippet: "Your October invoice is ready.", time: "9:41 AM", unread: true}, {from: "Acme Billing", subject: "Invoice #4498", snippet: "September invoice attached.", time: "Oct 2", unread: false}])'
].join('\n')

const route = [
  'root = Board("To the Ferry Building", "About 18 minutes by car.", [route])',
  'route = Route("Home", "Ferry Building", "drive", 18, "6.2 mi", ["Head north on Valencia St", "Turn right onto Market St", "Arrive at Ferry Building"])'
].join('\n')

const pr = [
  'root = Board("PR #128", "Status of the auth PR.", [pr])',
  'pr = PullRequest(128, "Refresh sessions in the auth middleware", "ready", "feat/session-refresh", "main", [{name: "Tests", status: "pass", detail: "vitest · 42 passed"}, {name: "Lint", status: "pass", detail: ""}, {name: "Types", status: "pass", detail: ""}], 0)'
].join('\n')

const embed = (code: string) =>
  <RichCodeBlock code={code} fallback={<pre data-testid="fence">{code}</pre>} language="openui-v2" streaming={false} />

afterEach(cleanup)

describe('openui-v2 app cards', () => {
  it.each([
    { code: ride, brand: 'uber', title: 'Uber ride options, Ferry Building to SFO Terminal 2', value: '$52.10' },
    { code: mail, brand: 'gmail', title: 'Gmail results for invoices from Acme', value: 'Invoice #4512' },
    { code: route, brand: 'google-maps', title: 'Directions from Home to Ferry Building', value: '6.2 mi' },
    { code: pr, brand: 'github', title: 'Pull request 128, ready', value: 'All checks have passed' }
  ])('renders its real $brand lab fence with supplied values and HTTPS app links', async ({ code, brand, title, value }) => {
    expect(inspectOpenUiBoard(code)).toEqual({ kind: 'ready' })
    const { container } = render(embed(code))
    await waitFor(() => expect(screen.getByRole('region', { name: title })).toBeTruthy())
    expect(container.querySelector('[data-app-card-brand="' + brand + '"]')).toBeTruthy()
    expect(screen.getByText(value, { exact: false })).toBeTruthy()
    const links = Array.from(container.querySelectorAll('a'))
    expect(links.length).toBeGreaterThan(0)

    for (const link of links) {
      expect(link.getAttribute('href')).toMatch(/^https:\/\//)
      expect(link.getAttribute('rel')).toContain('noopener')
    }

    expect(container.querySelector('iframe, form, script, [data-action]')).toBeNull()
  })

  it.each([
    { connector: 'lyft', appName: 'Lyft' },
    { connector: 'bolt', appName: 'bolt' }
  ])('uses the correct accessible ride region name for $connector', async ({ connector, appName }) => {
    render(embed(ride.replace('"uber"', '"' + connector + '"')))
    expect(await screen.findByRole('region', {
      name: appName + ' ride options, Ferry Building to SFO Terminal 2'
    })).toBeTruthy()
  })

  it('changes only local selection and opens the ride app on explicit click', async () => {
    const { container } = render(embed(ride))
    const comfort = await screen.findByRole('button', { name: /Comfort, 6 min/ })
    fireEvent.click(comfort)
    expect(comfort.getAttribute('aria-pressed')).toBe('true')
    expect(container.querySelector('a[href="https://m.uber.com/"]')).toBeTruthy()
  })

  it('moves through supplied route steps locally and links to the actual direction query', async () => {
    const { container } = render(embed(route))
    await waitFor(() => expect(screen.getByText('Head north on Valencia St')).toBeTruthy())
    fireEvent.click(screen.getByRole('button', { name: 'Next step' }))
    expect(screen.getByText('Turn right onto Market St')).toBeTruthy()
    expect(container.querySelector('a[href*="destination=Ferry%20Building"]')).toBeTruthy()
  })

  it('keeps unknown ride connectors as plain, inert cards', async () => {
    const unknown = ride.replace('"uber"', '"bolt"')
    expect(inspectOpenUiBoard(unknown)).toEqual({ kind: 'ready' })
    const { container } = render(embed(unknown))
    await waitFor(() => expect(container.querySelector('[data-app-card-brand="unknown"]')).toBeTruthy())
    expect(container.querySelector('a')).toBeNull()
    expect(screen.getByText('$31.20')).toBeTruthy()
    expect(brandForServer('mcp__editor_uber_1234abcd')).toBe('uber')
    expect(brandForServer('nonexistent')).toBeNull()
  })

  it('rejects duplicate options, inconsistent PR states and mismatched direct URLs', () => {
    expect(inspectOpenUiBoard(ride.replace('name: "Comfort"', 'name: "UberX"')).kind).toBe('invalid')
    expect(inspectOpenUiBoard(pr.replace('"ready"', '"conflict"')).kind).toBe('invalid')
    expect(inspectOpenUiBoard(pr.replace('"ready"', '"merged"').replace(', 0)', ', 2)')).kind).toBe('invalid')
    expect(inspectOpenUiBoard(pr.replace('"pass"', '"running"')).kind).toBe('invalid')
    const wrong = pr.replace(', 0)', ', 0, [], "https://github.com/example/repo/pull/129")')
    expect(inspectOpenUiBoard(wrong).kind).toBe('invalid')
    expect(appCardProblem({ typeName: 'PullRequest', props: { state: 'invalid' } })).not.toBeNull()
  })

  it('accepts a matching direct GitHub PR link and keeps chart panels in the same board', async () => {
    const withUrl = pr.replace(', 0)', ', 0, [], "https://github.com/kvnloo/hermes-agent/pull/128")')
    expect(inspectOpenUiBoard(withUrl)).toEqual({ kind: 'ready' })

    const mixed = ride.replace('[rides])', '[rides, spend])') +
      '\nspend = BarChart("Ride spend", "USD", [{label: "Uber", value: 120}])'

    expect(inspectOpenUiBoard(mixed)).toEqual({ kind: 'ready' })
    const { container } = render(embed(withUrl))
    await waitFor(() => expect(container.querySelector('a[href="https://github.com/kvnloo/hermes-agent/pull/128"]')).toBeTruthy())
  })

  it('shows source on user request and leaves malformed fences visible', async () => {
    render(embed(mail))
    fireEvent.click(await screen.findByRole('button', { name: 'Show source' }))
    expect(screen.getByTestId('fence').textContent).toBe(mail)
    fireEvent.click(screen.getByRole('button', { name: 'Show board' }))
    expect(screen.getByText('Invoice #4512')).toBeTruthy()
  })

  it('streams complete statements as cards with placeholders, never raw source or half a card', async () => {
    const board = [
      'root = Board("Before you go", "Mail, PR and a ride.", [mail, pr, rides])',
      mail.split('\n')[1],
      pr.split('\n')[1],
      ride.split('\n')[1]
    ].join('\n')

    const stream = (code: string) =>
      <RichCodeBlock code={code} fallback={<pre data-testid="fence">{code}</pre>} language="openui-v2" streaming />

    // First line still arriving: nothing parseable yet, so a quiet status, not the source.
    const first = render(stream(board.slice(0, 30)))
    expect(first.queryByTestId('fence')).toBeNull()
    expect(await first.findByRole('status')).toBeTruthy()
    cleanup()
    // Root line plus mail done, PR line half written.
    const cut = board.indexOf('Refresh sessions')
    const { container } = render(stream(board.slice(0, cut)))
    await waitFor(() => expect(container.querySelector('[data-app-card-brand="gmail"]')).toBeTruthy())
    expect(screen.queryByTestId('fence')).toBeNull()
    expect(container.querySelector('[data-app-card-brand="github"]')).toBeNull()
    expect(container.querySelectorAll('[data-openui-pending]').length).toBe(2)
    expect(screen.getByRole('heading', { name: 'Before you go' })).toBeTruthy()
    cleanup()
    // The Markdown repair can close the open fence with a newline after the half line.
    const repaired = render(stream(board.slice(0, cut) + '\n'))
    await waitFor(() => expect(repaired.container.querySelector('[data-app-card-brand="gmail"]')).toBeTruthy())
    expect(repaired.container.querySelector('[data-app-card-brand="github"]')).toBeNull()
    expect(repaired.container.querySelectorAll('[data-openui-pending]').length).toBe(2)
  })

  it('projects only provided route coordinates and never fabricates missing geometry', () => {
    expect(projectRoutePath([], 400, 180).points).toEqual([])
    const geometry = projectRoutePath([[37.77, -122.41], [37.8, -122.4]], 400, 180)
    expect(geometry.points).toHaveLength(2)
    expect(geometry.d).toMatch(/^M/)
  })
})
