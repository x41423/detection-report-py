import type { DownloadResponsePayload } from '../api/download'

export function triggerDownload(payload: DownloadResponsePayload) {
  const url = window.URL.createObjectURL(payload.blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = payload.filename
  document.body.appendChild(anchor)
  anchor.click()
  anchor.remove()
  window.URL.revokeObjectURL(url)
}
