import { readFileSync } from 'node:fs'
import type { E2EConfig } from 'e2e'
import { NativeControl, nativeControlEngine } from './adapter.ts'
import { bugbashTools } from './bugbash-tools.ts'
import { assertOwnedInert, type Manifest } from './types.ts'

const path = process.env.NATIVE_SETTINGS_MANIFEST
if (!path) throw new Error('Use an owned NATIVE_SETTINGS_MANIFEST; no implicit native target is allowed.')
const manifest = JSON.parse(readFileSync(path, 'utf8')) as Manifest
assertOwnedInert(manifest)
const native = new NativeControl(manifest)

const context = [
  'Inert isolated Hermes Settings. Dummy localhost provider. No model turn.',
  'Never approve, never Always, Cancel is default. Do not type secrets.',
  'Do not drive physical or user panes. Pass session id on every tools, call, and close_session.',
  'Grammar: observe, tap, type, press, locate. Do not call screenshot or point tools; this engine has no image proof.',
  'Project tools: native_schema, native_settings, native_prefs, native_wire, native_config_bytes, native_hold, native_release, native_evidence, native_corrupt_inert, native_restore_inert.',
  'native_evidence returns accepted private JSON/PNG paths after gate and ownership postcheck.',
  'native_corrupt_inert/native_restore_inert only touch the owned inert config.yaml after sentinel check.',
  'Not bugs: last QA navigation-missing capture artifact; seed e2e_preserve; Cancel-default confirmations.',
  'Keep the 10 serial native-settings tests on config.ts; this config is MCP bugbash only.',
].join(' ')

export default {
  projectId: 'hermes-native-bugbash',
  targets: [{ name: 'isolated-tern', engine: nativeControlEngine(native) }],
  tests: [],
  workers: 1,
  retries: 0,
  timeout: 900000,
  actionTimeout: 30000,
  assertionTimeout: 30000,
  cleanupTimeout: 30000,
  trace: 'off',
  video: 'off',
  cache: 'off',
  output: 'results',
  reporters: ['list'],
  agents: {
    default: {
      context,
      maxSteps: 40,
      maxModelCalls: 40,
      tools: bugbashTools(native),
    },
  },
} satisfies E2EConfig
