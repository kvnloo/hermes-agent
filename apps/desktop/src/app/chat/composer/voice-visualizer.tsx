import { cn } from '@/lib/utils'

import type { ConversationStatus } from './hooks/use-voice-conversation'

export type VoiceVisualizerVariant = 'pill' | 'orb' | 'waveform' | 'minimal'

export interface VoiceVisualizerProps {
  label: string
  level: number
  status: ConversationStatus | 'error'
  variant?: VoiceVisualizerVariant
}

const BAR_WEIGHTS = [0.45, 0.75, 1, 0.7, 0.9, 0.55, 0.8]

/** Original token-driven voice presence. It deliberately uses no vendor art or
 * brand geometry; every color resolves through the active Hermes theme. */
export function VoiceVisualizer({ label, level, status, variant = 'orb' }: VoiceVisualizerProps) {
  const normalized = Math.max(0, Math.min(1, level))
  const activeLevel = status === 'listening' || status === 'speaking' ? normalized : 0.18

  return (
    <div
      aria-live="polite"
      className={cn('voice-visualizer', `voice-visualizer--${variant}`, `voice-visualizer--${status}`)}
      data-status={status}
      data-variant={variant}
      role="status"
    >
      {variant === 'orb' && (
        <span aria-hidden="true" className="voice-visualizer__orb" style={{ '--voice-level': activeLevel } as React.CSSProperties}>
          <span className="voice-visualizer__orb-core" />
        </span>
      )}
      {(variant === 'pill' || variant === 'waveform') && (
        <span aria-hidden="true" className="voice-visualizer__bars">
          {BAR_WEIGHTS.map((weight, index) => (
            <span
              className="voice-visualizer__bar"
              key={index}
              style={{ '--voice-bar': 0.2 + activeLevel * weight } as React.CSSProperties}
            />
          ))}
        </span>
      )}
      {variant === 'minimal' && <span aria-hidden="true" className="voice-visualizer__dot" />}
      <span className="voice-visualizer__label">{label}</span>
    </div>
  )
}
