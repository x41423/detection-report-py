import api from './client'
import type {
  DailyIntakeCategory,
  DailyIntakeAsrProviderSelection,
  DailyIntakeItem,
  DailyIntakeParseResponse,
  DailyIntakeSheet,
  DailyIntakeSheetSummary,
  DailyIntakeSource,
} from '../features/daily-intake/types'

export interface DailyIntakeSheetResponse {
  success: boolean
  message: string
  sheet: DailyIntakeSheet
}

export interface DailyIntakeHistoryResponse {
  success: boolean
  message: string
  sheets: DailyIntakeSheetSummary[]
}

export interface DailyIntakeItemMutationResponse {
  success: boolean
  message: string
  item: DailyIntakeItem | null
  sheet: DailyIntakeSheet
  merged: boolean
}

export interface DailyIntakeDeleteResponse {
  success: boolean
  message: string
  sheet: DailyIntakeSheet
}

export interface DailyIntakeSpeechCapabilitiesResponse {
  success: boolean
  stable_transcription_enabled: boolean
  provider: string | null
  model: string | null
  requested_device?: string | null
  requested_compute_type?: string | null
  device?: string | null
  compute_type?: string | null
  fallback_used?: boolean
  fallback_reason?: string | null
  primary_provider?: string | null
  backup_provider?: string | null
  failover_enabled?: boolean
  shadow_compare_enabled?: boolean
  providers?: Array<Record<string, unknown>>
  message: string
}

export interface DailyIntakeSpeechRuntimeDiagnosticsResponse {
  success: boolean
  dependency_available: boolean
  provider?: string | null
  model?: string | null
  requested_device?: string | null
  requested_compute_type?: string | null
  resolved_device?: string | null
  resolved_compute_type?: string | null
  effective_device?: string | null
  effective_compute_type?: string | null
  cuda_device_count: number
  supported_compute_types_cpu: string[]
  supported_compute_types_cuda: string[]
  missing_cuda_runtime_dlls: string[]
  model_loaded: boolean
  runtime_checked: boolean
  fallback_used: boolean
  fallback_reason?: string | null
  suggested_fix?: string | null
  primary_provider?: string | null
  backup_provider?: string | null
  failover_enabled?: boolean
  shadow_compare_enabled?: boolean
  providers?: Array<Record<string, unknown>>
  message: string
}

export function getTodayDailyIntake() {
  return api.get<DailyIntakeSheetResponse>('/api/daily-intake/today')
}

export function getDailyIntakeByDate(intakeDate: string) {
  return api.get<DailyIntakeSheetResponse>(`/api/daily-intake/${encodeURIComponent(intakeDate)}`)
}

export function getDailyIntakeHistory(limit = 30) {
  return api.get<DailyIntakeHistoryResponse>('/api/daily-intake/history', {
    params: { limit },
  })
}

export function getDailyIntakeSpeechCapabilities() {
  return api.get<DailyIntakeSpeechCapabilitiesResponse>('/api/daily-intake/speech-capabilities')
}

export function getDailyIntakeSpeechRuntimeDiagnostics() {
  return api.get<DailyIntakeSpeechRuntimeDiagnosticsResponse>('/api/daily-intake/speech-runtime-diagnostics')
}

export function createDailyIntakeItem(params: {
  intake_date: string
  name: string
  category: DailyIntakeCategory
  quantity: number
  unit: string
  source?: DailyIntakeSource
  transcript?: string
}) {
  return api.post<DailyIntakeItemMutationResponse>('/api/daily-intake/items', params)
}

export function updateDailyIntakeItem(
  itemId: number,
  params: {
    name: string
    category: DailyIntakeCategory
    quantity: number
    unit: string
    source?: DailyIntakeSource | null
    transcript?: string | null
  },
) {
  return api.put<DailyIntakeItemMutationResponse>(`/api/daily-intake/items/${itemId}`, params)
}

export function deleteDailyIntakeItem(itemId: number) {
  return api.delete<DailyIntakeDeleteResponse>(`/api/daily-intake/items/${itemId}`)
}

export function transcribeDailyIntakeAudio(params: {
  intake_date: string
  audio: Blob
  filename?: string
  category?: DailyIntakeCategory
  asr_provider?: DailyIntakeAsrProviderSelection
  fallback_enabled?: boolean
}) {
  const formData = new FormData()
  formData.append('intake_date', params.intake_date)
  if (params.category) {
    formData.append('category', params.category)
  }
  if (params.asr_provider) {
    formData.append('asr_provider', params.asr_provider)
  }
  if (typeof params.fallback_enabled === 'boolean') {
    formData.append('fallback_enabled', String(params.fallback_enabled))
  }
  formData.append('audio', params.audio, params.filename || 'daily-intake-recording.webm')

  return api.post<DailyIntakeParseResponse>('/api/daily-intake/transcribe-audio', formData, {
    timeout: 180000,
  })
}
