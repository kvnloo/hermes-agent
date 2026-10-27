import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'

import { VoiceVisualizer } from './voice-visualizer'

afterEach(cleanup)

describe('VoiceVisualizer', () => {
  for (const variant of ['pill', 'orb', 'waveform', 'minimal'] as const) {
    it(`renders the visible state label for ${variant}`, () => {
      render(<VoiceVisualizer label="Listening" level={0.7} status="listening" variant={variant} />)
      expect(screen.getByText('Listening')).toBeTruthy()
      expect(screen.getByRole('status').getAttribute('data-variant')).toBe(variant)
    })
  }
})
