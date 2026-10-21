import { readFileSync } from 'node:fs'
import type { E2EConfig } from 'e2e'
import { NativeControl, nativeControlEngine } from './adapter.ts'
import type { Manifest } from './types.ts'

const path = process.env.NATIVE_SETTINGS_MANIFEST
if (!path) throw new Error('Use ui-tsp/e2e/run.mjs; no implicit native target is allowed.')
const manifest = JSON.parse(readFileSync(path,'utf8')) as Manifest
export default {
  projectId:'hermes-native-settings',
  targets:[{name:'isolated-tern',engine:nativeControlEngine(new NativeControl(manifest))}],
  tests:['native-settings.e2e.ts'],
  workers:1,retries:0,timeout:900000,actionTimeout:30000,assertionTimeout:30000,
  cleanupTimeout:30000,trace:'off',video:'off',cache:'off',output:'results',reporters:['list','junit']
} satisfies E2EConfig
