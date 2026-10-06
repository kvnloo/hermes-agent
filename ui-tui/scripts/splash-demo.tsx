// Standalone player for the launch splash — no gateway required.
//
//   npx tsx scripts/splash-demo.tsx                  # plays once, "ready" after 3.5s
//   npx tsx scripts/splash-demo.tsx --design atlas   # a specific design
//   npx tsx scripts/splash-demo.tsx --hold           # idles until a key is pressed
//   npx tsx scripts/splash-demo.tsx --loop           # replays forever (Ctrl+C to quit)
//   npx tsx scripts/splash-demo.tsx --gallery        # h / l step through every design
//   npx tsx scripts/splash-demo.tsx --frame 2600 [cols rows]   # print one frame
import { AlternateScreen, render } from '@hermes/ink'
import React, { useEffect, useState } from 'react'

import { LaunchSplash, pickSplashDesign, splashColorDepth } from '../src/components/launchSplash.js'
import { renderSplashFrame, SPLASH_DESIGN_NAMES } from '../src/splash/index.js'

const args = process.argv.slice(2)
const flag = (name: string) => args.includes(name)
const value = (name: string) => (args.includes(name) ? args[args.indexOf(name) + 1] : undefined)
const first = Math.max(0, SPLASH_DESIGN_NAMES.indexOf(pickSplashDesign(value('--design') ?? '')))
const frameAt = args.indexOf('--frame')

if (frameAt >= 0) {
  const width = Number(args[frameAt + 2]) || process.stdout.columns || 80
  const height = Number(args[frameAt + 3]) || process.stdout.rows || 24

  process.stdout.write(
    renderSplashFrame({
      color: splashColorDepth(),
      design: SPLASH_DESIGN_NAMES[first],
      elapsedMs: Number(args[frameAt + 1]) || 2600,
      height,
      status: 'summoning hermes…',
      width
    }).join('\n') + '\n'
  )
  process.exit(0)
}

const STEPS = ['summoning hermes…', 'starting gateway', 'loading skills', 'opening session']
const gallery = flag('--gallery')
const hold = flag('--hold') || gallery
const loop = flag('--loop') || gallery

function Demo() {
  const [step, setStep] = useState(0)
  const [run, setRun] = useState(0)
  const [index, setIndex] = useState(first)
  const count = SPLASH_DESIGN_NAMES.length

  useEffect(() => {
    setStep(0)

    const id = setInterval(() => setStep(n => n + 1), 900)

    return () => clearInterval(id)
  }, [run, index])

  const name = SPLASH_DESIGN_NAMES[index]!
  const status = gallery
    ? `${index + 1}/${count} ${name} · h/l switch · q quit`
    : STEPS[Math.min(step, STEPS.length - 1)]

  return (
    <AlternateScreen>
      <LaunchSplash
        design={name}
        key={`${index}:${run}`}
        onDone={() => (loop ? setTimeout(() => setRun(n => n + 1), 500) : process.exit(0))}
        onInput={input => {
          if (!gallery) {
            return false
          }

          if (input === 'q') {
            process.exit(0)
          }

          if (input === 'l' || input === 'h') {
            setIndex(i => (i + (input === 'l' ? 1 : count - 1)) % count)
          } else if (input === 'r' || input === ' ') {
            setRun(n => n + 1)
          }

          return true
        }}
        ready={!hold && step >= STEPS.length}
        status={status}
      />
    </AlternateScreen>
  )
}

render(<Demo />, { exitOnCtrlC: true })
