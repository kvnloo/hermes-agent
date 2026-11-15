import { act, cleanup, renderHook } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { downloadBlob } from '@/lib/download'
import { notifyError } from '@/store/notifications'

import { useImageDownload } from './use-image-download'

vi.mock('@/i18n', () => ({
  useI18n: () => ({
    t: {
      desktop: {
        imageSaved: 'Image saved',
        imageDownloadFailed: 'Image download failed',
        downloadStarted: 'Download started',
        restartToUseSaveImage: 'Restart to use Save Image',
        restartToSaveImages: 'Restart to save images'
      }
    }
  })
}))

vi.mock('@/lib/download', async importOriginal => ({
  ...(await importOriginal<typeof import('@/lib/download')>()),
  downloadBlob: vi.fn()
}))

vi.mock('@/store/notifications', () => ({
  notify: vi.fn(),
  notifyError: vi.fn()
}))

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
  vi.clearAllMocks()
})

describe('useImageDownload', () => {
  it('keeps renderer blob URLs out of Electron IPC while retaining native HTTPS saves', async () => {
    const saveImageFromUrl = vi.fn(async () => true)
    vi.stubGlobal('hermesDesktop', { saveImageFromUrl })

    const blobUrl = 'blob:http://localhost:5174/pasted-image'
    const image = new Blob(['pixels'], { type: 'image/png' })
    const fetchImage = vi.fn(async () => ({ ok: true, blob: async () => image }))
    vi.stubGlobal('fetch', fetchImage)

    const { result, rerender } = renderHook(({ src }) => useImageDownload(src), {
      initialProps: { src: blobUrl }
    })
    await act(async () => {
      await result.current.download()
    })

    expect(saveImageFromUrl).not.toHaveBeenCalled()
    expect(fetchImage).toHaveBeenCalledWith(blobUrl)
    expect(downloadBlob).toHaveBeenCalledWith(image, 'pasted-image.png')

    const httpsUrl = 'https://example.com/photo.jpg'
    rerender({ src: httpsUrl })
    await act(async () => {
      await result.current.download()
    })

    expect(saveImageFromUrl).toHaveBeenCalledOnce()
    expect(saveImageFromUrl).toHaveBeenCalledWith(httpsUrl)
    expect(fetchImage).toHaveBeenCalledTimes(1)
    expect(notifyError).not.toHaveBeenCalled()
  })
})
