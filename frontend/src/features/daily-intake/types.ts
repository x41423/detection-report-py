export type DailyIntakeCategory = 'vegetable' | 'frozen' | 'meat'
export type DailyIntakeSource = 'manual' | 'voice'
export type DailyIntakeParseStatus = 'parsed' | 'invalid'
export type DailyIntakeAsrProviderSelection = 'auto' | 'qwen3-asr' | 'faster-whisper'
export type DailyIntakeSpeechState =
  | 'idle'
  | 'authorizing'
  | 'listening'
  | 'parsing'
  | 'unsupported'
  | 'blocked'
  | 'permission-denied'
  | 'error'

export interface DailyIntakeMergePreview {
  item_id: number
  current_quantity: number
  next_quantity: number
  unit_name: string
  merge_count: number
}

export interface DailyIntakeItem {
  id: number
  sheet_id: number
  veg_id: number | null
  raw_name: string
  normalized_name: string
  category: DailyIntakeCategory
  quantity: number
  source: DailyIntakeSource
  transcript: string
  last_source: DailyIntakeSource
  last_transcript: string
  merge_count: number
  last_confirmed_at: string | null
  created_at: string | null
  updated_at: string | null
  unit_id: number
  unit_name: string
}

export interface DailyIntakeSheet {
  id: number
  intake_date: string
  status: string
  created_at: string | null
  updated_at: string | null
  item_count: number
  total_quantity: number
  quantity_by_unit: Record<string, number>
  items: DailyIntakeItem[]
}

export interface DailyIntakeSheetSummary {
  id: number
  intake_date: string
  status: string
  created_at: string | null
  updated_at: string | null
  item_count: number
  total_quantity: number
}

export interface DailyIntakeParseResponse {
  success: boolean
  message: string
  raw_transcript: string
  draft_name: string
  normalized_name: string
  quantity: number | null
  unit: string | null
  category_hint: DailyIntakeCategory | null
  warnings: string[]
  parse_status: DailyIntakeParseStatus
  requires_confirmation: boolean
  merge_preview: DailyIntakeMergePreview | null
  asr_provider?: string | null
  asr_model?: string | null
  asr_fallback_used?: boolean
  asr_fallback_reason?: string | null
  asr_duration_ms?: number | null
  asr_warnings?: string[]
  asr_shadow_recorded?: boolean
}

export const DAILY_INTAKE_CATEGORY_OPTIONS: Array<{
  label: string
  value: DailyIntakeCategory
}> = [
  { label: '蔬菜', value: 'vegetable' },
  { label: '冻品', value: 'frozen' },
  { label: '肉类', value: 'meat' },
]

export const DAILY_INTAKE_CATEGORY_LABELS: Record<DailyIntakeCategory, string> = {
  vegetable: '蔬菜',
  frozen: '冻品',
  meat: '肉类',
}

export const DAILY_INTAKE_UNITS = ['斤', '公斤', '包', '个', '条', '筐', '箱', '袋', '盒', '瓶', '桶', '罐', '块', '升', '克'] as const
