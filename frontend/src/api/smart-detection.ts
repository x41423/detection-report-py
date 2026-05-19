import api from './client'

export interface SmartRecommendItem {
  name: string
  source: 'daily_intake' | 'yesterday_inventory'
  category?: string
  reason?: string
}

export interface SmartRecommendResponse {
  today_intake: SmartRecommendItem[]
  yesterday_inventory: SmartRecommendItem[]
  missing_dates: string[]
}

export interface SmartExecuteRequest {
  selected_varieties: string[]
  date: string
  big_template: string
  small_template: string
  output_dir: string
  inspector_name: string
  manual_additions: string[]
  export_format: 'docx' | 'pdf' | 'both'
}

export interface SmartExecuteResponse {
  success: boolean
  error?: string
  output_paths: Record<string, unknown>
  pdf_files: string[]
  low_stock_alerts: Array<{ item_name: string; balance: number; unit: string }>
  summary: { total_varieties: number; generated_date: string; inspector: string }
}

export interface GapResponse {
  missing_dates: string[]
  last_detection_date: string | null
  total_missing: number
}

export interface PrepareResponse {
  big_template: string
  small_template: string
  output_dir: string
  inspector_name: string
}

export interface BackfillRequest {
  start_date: string
  end_date: string
  inspector_name: string
}

export interface BackfillResponse {
  success: boolean
  results: Array<{ date: string; success: boolean; error?: string }>
}

export async function getSmartRecommend(date?: string): Promise<SmartRecommendResponse> {
  const params = date ? `?target_date=${date}` : ''
  const { data } = await api.get(`/api/pesticide/smart/recommend${params}`)
  return data
}

export async function postSmartExecute(req: SmartExecuteRequest): Promise<SmartExecuteResponse> {
  const { data } = await api.post('/api/pesticide/smart/execute', req)
  return data
}

export async function getSmartGaps(days = 7): Promise<GapResponse> {
  const { data } = await api.get(`/api/pesticide/smart/gaps?days=${days}`)
  return data
}

export async function postSmartBackfill(req: BackfillRequest): Promise<BackfillResponse> {
  const { data } = await api.post('/api/pesticide/smart/backfill', req)
  return data
}

export async function getSmartPrepare(): Promise<PrepareResponse> {
  const { data } = await api.get('/api/pesticide/smart/prepare')
  return data
}

export async function putSmartPrepare(inspectorName: string): Promise<PrepareResponse> {
  const { data } = await api.put(`/api/pesticide/smart/prepare?inspector_name=${encodeURIComponent(inspectorName)}`)
  return data
}
