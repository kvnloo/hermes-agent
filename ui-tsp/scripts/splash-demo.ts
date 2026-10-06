// Plays the launch splash in a Tern pane without a gateway or a model: the
// same LaunchSplash the app mounts, over a stand-in session surface.
//
//   npx tsx scripts/splash-demo.ts                    # the gallery
//   npx tsx scripts/splash-demo.ts --design atlas     # start on one design
//   npx tsx scripts/splash-demo.ts --once             # play one launch, then exit
//
// Gallery keys: h / l previous / next design · r replay · t swap the skin
// (what a skin.changed event does) · q quit. `SPLASH_DEMO_AT=<ms>` freezes
// the clock at that instant, for a stable still.
import { connect, ui } from '@stencil-hq/tern'

import { paletteOf } from '../src/palette.js'
import { SPLASH_DESIGN_NAMES, SPLASH_ROLE } from '../src/splash/index.js'
import { LaunchSplash, pickSplashDesign, splashInsets } from '../src/splash/launch.js'

const args = process.argv.slice(2)
const value = (name: string) => (args.includes(name) ? args[args.indexOf(name) + 1] : undefined)
const once = args.includes('--once')
const frozen = process.env.SPLASH_DEMO_AT ? Number(process.env.SPLASH_DEMO_AT) : null

// A second skin, to show the splash following a skin.changed event.
const EMBER = {
  colors: {
    background: '#1b0b05',
    banner_dim: '#c98a5a',
    ui_accent: '#ffd166',
    ui_border: '#a8502a',
    ui_text: '#ffe9d6'
  },
  name: 'ember'
}

const session = await connect({ app: 'hermes' })
const launched = performance.now()

if (!session) {
  console.error('This demo needs a Tern pane (the Tern Surface Protocol).')
  process.exit(75)
}

const chrome = session.open({ id: 'hermes', mode: 'inline', role: 'omp.session', title: 'hermes' })

chrome.palette(paletteOf(undefined))
chrome.render(
  ui.card({ head: 'session chrome', key: 'stand-in' }, ui.text({ key: 't', text: 'The splash hands off to this.' }))
)

let index = Math.max(0, SPLASH_DESIGN_NAMES.indexOf(pickSplashDesign(value('--design') ?? '')))
let ember = false
let splash: LaunchSplash | undefined
let quit = false

let release = () => {}

const play = () => {
  const name = SPLASH_DESIGN_NAMES[index]!
  const started = performance.now()
  let released = 0

  // Frozen: run up to the still's instant and hold there until a key releases the clock.
  const clock = () => {
    const real = performance.now()

    return released ? started + frozen! + (real - released) : Math.min(real, started + frozen!)
  }

  splash = new LaunchSplash({
    design: name,
    now: frozen === null ? undefined : clock,
    onDone: () => {
      if (once || quit) {
        // Leave the stand-in chrome up for a beat so the hand-off can be seen.
        setTimeout(() => void session.close().then(() => process.exit(0)), once ? 1500 : 0)
      } else {
        play()
      }
    },
    open: () => session.open({ id: 'splash', mode: 'screen', role: SPLASH_ROLE, title: 'hermes' }),
    palette: paletteOf(ember ? EMBER : undefined),
    size: () => splashInsets(session.caps.cols, process.stdout.rows ?? 24),
    status: once
      ? 'summoning hermes…'
      : `${index + 1}/${SPLASH_DESIGN_NAMES.length} ${name} · h/l switch · t skin · q quit`
  })
  release = () => (released ||= performance.now())
  splash.start()

  if (once) {
    setTimeout(() => splash?.ready(), 3500)
  }
}

play()

for await (const input of session) {
  if (input.type !== 'key') {
    continue
  }

  const key = input.key.name

  // The Enter that launched the demo can still be in flight.
  if (performance.now() - launched < 400) {
    continue
  }

  release()

  if (once || key === 'q' || (input.key.ctrl && key === 'c')) {
    quit = true
    splash?.skip()
  } else if (key === 'l' || key === 'h') {
    index = (index + (key === 'l' ? 1 : SPLASH_DESIGN_NAMES.length - 1)) % SPLASH_DESIGN_NAMES.length
    splash?.skip()
  } else if (key === 'r') {
    splash?.skip()
  } else if (key === 't') {
    ember = !ember
    splash?.palette(paletteOf(ember ? EMBER : undefined))
  }
}
