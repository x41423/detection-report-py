import api from './client'

export interface AuditTrackPayload {
  module: string
  action: string
  description?: string
  metadata?: Record<string, unknown>
}

export interface AuditTrackResult {
  success: boolean
  throttled: boolean
}

/**
 * Fire-and-forget audit event. Never throws — audit must not break flows.
 * Returns `undefined` on any failure (network, 4xx, 5xx).
 */
export function trackAudit(payload: AuditTrackPayload): Promise<AuditTrackResult | undefined> {
  return api
    .post<AuditTrackResult>('/api/audit/track', payload)
    .then((response) => response.data)
    .catch(() => undefined)
}
