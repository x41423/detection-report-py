import type { AxiosResponse } from 'axios'

/**
 * Normalised payload returned by every endpoint that streams a file back.  The
 * server-side metadata (operation message, processed/written counts) is parsed
 * out of custom `X-*` headers so callers can react to the result without a
 * second round-trip.
 */
export interface DownloadResponsePayload {
  blob: Blob
  filename: string
  message: string
  processedFiles: number
  matchedCount: number
  writtenCount: number
  updatedCount: number
  generatedCount: number
  skippedCount: number
}

const HEADER_KEYS = {
  filename: 'content-disposition',
  message: 'x-operation-message',
  processed: 'x-processed-files',
  matched: 'x-matched-count',
  written: 'x-written-count',
  updated: 'x-updated-count',
  generated: 'x-generated-count',
  skipped: 'x-skipped-count',
} as const

function getHeader(response: AxiosResponse, key: string): string {
  const headers = response.headers as Record<string, string | undefined> | undefined
  if (!headers) return ''
  const direct = headers[key]
  if (typeof direct === 'string') return direct
  const upper = headers[key.toUpperCase()]
  if (typeof upper === 'string') return upper
  return ''
}

function decodeFilename(rawValue: string): string {
  const trimmed = (rawValue || '').trim()
  if (!trimmed) return ''
  // Prefer RFC 5987 filename* parameter (UTF-8 encoded)
  const utf8Match = trimmed.match(/filename\*=(?:UTF-8'')?([^;]+)/i)
  if (utf8Match && utf8Match[1]) {
    try {
      return decodeURIComponent(utf8Match[1].replace(/^"|"$/g, ''))
    } catch {
      return utf8Match[1].replace(/^"|"$/g, '')
    }
  }
  const asciiMatch = trimmed.match(/filename="?([^";]+)"?/i)
  if (asciiMatch && asciiMatch[1]) {
    try {
      return decodeURIComponent(asciiMatch[1])
    } catch {
      return asciiMatch[1]
    }
  }
  return ''
}

function decodeHeaderValue(rawValue: string): string {
  const trimmed = (rawValue || '').trim()
  if (!trimmed) return ''
  try {
    return decodeURIComponent(trimmed)
  } catch {
    return trimmed
  }
}

function parseIntHeader(rawValue: string): number {
  const parsed = Number.parseInt(rawValue, 10)
  return Number.isFinite(parsed) ? parsed : 0
}

/**
 * Convert an axios response that has been requested with `responseType: 'blob'`
 * into a {@link DownloadResponsePayload} ready for {@link triggerDownload}.
 */
export function toDownloadPayload(
  response: AxiosResponse,
  fallbackFilename: string,
): DownloadResponsePayload {
  const blob = response.data instanceof Blob
    ? response.data
    : new Blob([response.data])

  const filenameFromHeader = decodeFilename(getHeader(response, HEADER_KEYS.filename))
  const filename = filenameFromHeader || fallbackFilename

  return {
    blob,
    filename,
    message: decodeHeaderValue(getHeader(response, HEADER_KEYS.message)),
    processedFiles: parseIntHeader(getHeader(response, HEADER_KEYS.processed)),
    matchedCount: parseIntHeader(getHeader(response, HEADER_KEYS.matched)),
    writtenCount: parseIntHeader(getHeader(response, HEADER_KEYS.written)),
    updatedCount: parseIntHeader(getHeader(response, HEADER_KEYS.updated)),
    generatedCount: parseIntHeader(getHeader(response, HEADER_KEYS.generated)),
    skippedCount: parseIntHeader(getHeader(response, HEADER_KEYS.skipped)),
  }
}
