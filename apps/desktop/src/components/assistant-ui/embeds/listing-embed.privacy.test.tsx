import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, expect, it } from 'vitest'

import { setRemoteMediaMode } from '@/store/remote-media'

import ListingEmbed from './listing-embed'

const FIRST = 'https://one.example/first.png?chat=secret'
const SECOND = 'https://two.example/second.png?chat=secret'
const NEXT = 'https://three.example/third.png?chat=secret'

function listing(images: string[]) {
  return <ListingEmbed code={JSON.stringify({ address: 'Sample listing', images })} streaming={false} />
}

beforeEach(() => setRemoteMediaMode('ask'))

afterEach(() => {
  cleanup()
  setRemoteMediaMode('always')
})

it('keeps listing-fence images inert until each exact URL is approved', () => {
  const { container, rerender } = render(listing([FIRST, SECOND]))

  // A model can emit a listing fence with arbitrary images, not only markdown ![] links.
  expect(container.querySelectorAll('img')).toHaveLength(0)
  expect(screen.getByRole('button', { name: 'Load from one.example' })).toBeTruthy()
  expect(screen.getByRole('button', { name: 'Load from two.example' })).toBeTruthy()

  fireEvent.click(screen.getByRole('button', { name: 'Load from one.example' }))
  expect(container.querySelector('img[src="' + FIRST + '"]')).not.toBeNull()
  expect(container.querySelector('img[src="' + SECOND + '"]')).toBeNull()

  // A streamed/update replacement must not inherit consent granted to the earlier URL.
  rerender(listing([FIRST, NEXT]))
  expect(container.querySelector('img[src="' + FIRST + '"]')).not.toBeNull()
  expect(container.querySelector('img[src="' + NEXT + '"]')).toBeNull()
  expect(screen.getByRole('button', { name: 'Load from three.example' })).toBeTruthy()
})

it('preserves the existing automatic listing gallery in Always mode', () => {
  setRemoteMediaMode('always')
  const { container } = render(listing([FIRST, SECOND]))

  expect(container.querySelector('img[src="' + FIRST + '"]')).not.toBeNull()
  expect(container.querySelector('img[src="' + SECOND + '"]')).not.toBeNull()
})
