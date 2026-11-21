import { describe, expect, it } from 'vitest'

import { matchEphemeralCommand, matchEphemeralTool } from './model'

// connectors.json against the tool names real MCP servers register (their READMEs / `hermes mcp test`).
// A card must grow only where the kit has one for that job; every other call on the server grows none.
// `null` = no card. Keys are the server names people give them in config.yaml.
const CATALOGS: Record<string, Record<string, string | null>> = {
  // github/github-mcp-server
  github: {
    actions_list: 'ci',
    actions_get: 'ci',
    actions_run_trigger: 'ci',
    get_job_logs: 'ci',
    list_workflow_runs: 'ci',
    get_workflow_run: 'ci',
    rerun_workflow_run: 'ci',
    get_check_runs: 'ci',
    pull_request_read: 'merge',
    list_pull_requests: 'merge',
    get_pull_request: 'merge',
    create_pull_request: 'merge',
    merge_pull_request: 'merge',
    update_pull_request: 'merge',
    get_file_contents: null,
    get_repository_tree: null,
    search_code: null,
    search_repositories: null,
    list_issues: null,
    add_issue_comment: null,
    create_gist: null,
    get_me: null,
    list_dependabot_alerts: null,
    list_code_scanning_alerts: null
  },
  // GongRzhe/Gmail-MCP-Server
  gmail: {
    search_emails: 'inbox',
    read_email: 'thread',
    send_email: 'thread',
    draft_email: 'thread',
    list_email_labels: null,
    create_label: null,
    get_or_create_label: null,
    create_filter: null,
    list_filters: null,
    download_attachment: null,
    modify_email: null,
    delete_email: null,
    batch_modify_emails: null
  },
  // nspady/google-calendar-mcp
  google_calendar: {
    'list-events': 'slots',
    'search-events': 'slots',
    'get-event': 'slots',
    'get-freebusy': 'slots',
    'create-event': 'slots',
    'update-event': 'slots',
    'respond-to-event': 'slots',
    'list-calendars': null,
    'list-colors': null,
    'manage-accounts': null,
    'get-current-time': null
  },
  // makenotion/notion-mcp-server (hosted names, then the local API-* names)
  notion: {
    'notion-search': 'search',
    'notion-fetch': 'file',
    'notion-create-pages': 'file',
    'API-post-search': 'search',
    'API-retrieve-a-page': 'file'
  },
  // modelcontextprotocol/servers (archived) slack
  slack: { slack_post_message: 'chat', slack_get_channel_history: 'chat', slack_reply_to_thread: 'chat' },
  // getsentry/sentry-mcp
  sentry: { search_issues: 'incident', search_errors: 'incident' },
  // Servers no card is drawn for (here: Chrome DevTools MCP) never grow one, whatever the tool.
  'chrome-devtools': { lighthouse_audit: null, take_screenshot: null, list_network_requests: null, performance_start_trace: null }
}

describe('ephemeral-ui connectors against real MCP tool catalogs', () => {
  for (const [server, tools] of Object.entries(CATALOGS)) {
    it(`${server}: each tool grows the right card or none`, () => {
      const got = Object.fromEntries(Object.keys(tools).map(tool => [tool, matchEphemeralTool(`mcp__${server}__${tool}`)?.kind ?? null]))
      expect(got).toEqual(tools)
    })
  }
})

// Hermes reaches GitHub through `gh` in the terminal tool (its github/* skills), not MCP.
const GH: Record<string, string | null> = {
  'gh run list -R octo/app --limit 5': 'ci',
  'gh run view 123 --log-failed': 'ci',
  'gh workflow run deploy.yml': 'ci',
  'gh pr checks 42': 'ci',
  'cd /repo && gh pr view 42 --json state': 'merge',
  'GH_PAGER= gh pr merge 42 --squash': 'merge',
  '/usr/bin/gh pr create --fill': 'merge',
  'gh issue list': null,
  'gh repo clone octo/app': null,
  'gh api repos/octo/app': null,
  'gh auth status': null,
  'git push && gh pr list': 'merge',
  'ls -la': null,
  'echo gh run list': null
}

describe('ephemeral-ui cards for CLIs run in the terminal tool', () => {
  it('gh: each command grows the right card or none', () => {
    const got = Object.fromEntries(Object.keys(GH).map(command => [command, matchEphemeralCommand(command)?.kind ?? null]))
    expect(got).toEqual(GH)
  })

  it('reads the command from terminal args and names the subcommand in the receipt', () => {
    expect(matchEphemeralTool('terminal', { command: 'gh run list' })).toMatchObject({ app: 'github', kind: 'ci', tool: 'gh run list' })
    expect(matchEphemeralTool('terminal', {})).toBeNull()
    expect(matchEphemeralTool('terminal')).toBeNull()
  })
})
