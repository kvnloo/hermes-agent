import type { PlanStatusResult } from '@hermes/shared/gateway-events'

import type { Entry } from './model.js'

export interface PlanSection {
  title: string
  level: number
  text: string
}

export type PlanStatus = PlanStatusResult

/** Backend plans need not use Markdown headings. */
export function reviewPlanText(text: string): Plan {
  return parsePlan(text) ?? { text, preamble: '', sections: [{ title: 'Plan', level: 1, text }] }
}

export interface Plan {
  text: string
  preamble: string
  sections: PlanSection[]
}

/** Heading-structured assistant Markdown is a review candidate, not backend authority. */
export function parsePlan(text: string): Plan | undefined {
  const headings: { title: string; level: number; offset: number }[] = []
  let fence: { marker: string; length: number } | undefined
  let offset = 0

  for (const line of text.split('\n')) {
    const marker = line.match(/^ {0,3}(`{3,}|~{3,})(.*)$/)

    if (fence) {
      if (marker && marker[1]![0] === fence.marker && marker[1]!.length >= fence.length && !marker[2]!.trim()) {
        fence = undefined
      }
    } else if (marker) {
      fence = { marker: marker[1]![0]!, length: marker[1]!.length }
    } else {
      const heading = line.match(/^ {0,3}(#{1,6})[\t ]+(.+?)\s*$/)

      if (heading) {
        headings.push({ title: heading[2]!.replace(/[\t ]+#+[\t ]*$/, ''), level: heading[1]!.length, offset })
      }
    }

    offset += line.length + 1
  }

  if (!headings.length) {
    return undefined
  }

  return {
    text,
    preamble: text.slice(0, headings[0]!.offset),
    sections: headings.map((heading, index) => ({
      title: heading.title,
      level: heading.level,
      text: text.slice(heading.offset, headings[index + 1]?.offset ?? text.length)
    }))
  }
}

/** Never infer a plan from user prompts, reasoning, tools or an incomplete turn. */
export function latestPlan(entries: readonly Entry[]): Plan | undefined {
  for (let index = entries.length - 1; index >= 0; index--) {
    const entry = entries[index]

    if (entry?.kind !== 'turn' || entry.status !== 'done') {
      continue
    }

    const plan = parsePlan(
      entry.blocks
        .filter(block => block.kind === 'text')
        .map(block => block.text)
        .join('\n\n')
    )

    if (plan) {
      return plan
    }
  }

  return undefined
}
