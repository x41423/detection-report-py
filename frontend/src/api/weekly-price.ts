import api from './client'
import { toDownloadPayload, type DownloadResponsePayload } from './download'

export interface WeeklyPriceMatchedItem {
  name: string
  old_price: number | null
  new_price: number
  changed: boolean
  match_type: 'exact' | 'alias'
}

export interface WeeklyPriceSuggestionCandidate {
  target_name: string
  score: number
}

export interface WeeklyPriceSuggestedMatch {
  source_name: string
  candidates: WeeklyPriceSuggestionCandidate[]
  preselected_target_name?: string | null
}

export interface WeeklyPricePreviewResponse {
  success: boolean
  message: string
  matched_count: number
  updated_count: number
  matched_items: WeeklyPriceMatchedItem[]
  not_matched: string[]
  not_matched_count: number
  not_matched_unique_count: number
  suggested_matches: WeeklyPriceSuggestedMatch[]
  alias_hit_count: number
  warnings: string[]
  update_start_row: number
  reference_start_row: number
}

export interface WeeklyPriceExecuteResponse {
  success: boolean
  message: string
  matched_count: number
  updated_count: number
  matched_items: WeeklyPriceMatchedItem[]
  not_matched: string[]
  not_matched_count: number
  not_matched_unique_count: number
  alias_hit_count: number
  warnings: string[]
  output_path: string
  backup_path?: string | null
}

export interface WeeklyPriceAliasItem {
  source_name: string
  target_name: string
}

export interface WeeklyPriceAliasListResponse {
  aliases: WeeklyPriceAliasItem[]
  total: number
}

export interface WeeklyQuoteEntryInput {
  name: string
  unit: string
  price: number
}

export interface WeeklyQuoteBatchInput {
  supplier: string
  quote_date: string
  entries: WeeklyQuoteEntryInput[]
}

export interface WeeklyQuoteSummaryItem {
  name: string
  unit: string
  summary_price: number
}

export interface WeeklyQuoteUnitSummary {
  supplier: string
  batch_count: number
  entry_count: number
  summary_items: WeeklyQuoteSummaryItem[]
}

export interface WeeklyQuoteImportResponse {
  success: boolean
  message: string
  batch: WeeklyQuoteBatchInput
}

export interface WeeklyQuotePreviewResponse {
  success: boolean
  message: string
  unit_summaries: WeeklyQuoteUnitSummary[]
  total_batches: number
  total_entries: number
  total_summary_items: number
  issue_messages: string[]
}

export interface WeeklyQuoteExportResponse {
  success: boolean
  message: string
  workbook_path: string
  sheet_names: string[]
  unit_summaries: WeeklyQuoteUnitSummary[]
  total_batches: number
  total_entries: number
  total_summary_items: number
}

export function executeWeeklyPrice(params: {
  update_path: string
  reference_path: string
  output_path: string
}) {
  return api.post<WeeklyPriceExecuteResponse>('/api/weekly-price/execute', params)
}

export async function executeWeeklyPriceUpload(params: {
  updateFile: File
  referenceFile: File
}): Promise<DownloadResponsePayload> {
  const formData = new FormData()
  formData.append('update_file', params.updateFile)
  formData.append('reference_file', params.referenceFile)
  const response = await api.post('/api/weekly-price/execute/upload', formData, {
    responseType: 'blob',
  })
  return toDownloadPayload(response, 'weekly_price_updated.xlsx')
}

export function previewWeeklyPrice(params: {
  update_path: string
  reference_path: string
}) {
  return api.post<WeeklyPricePreviewResponse>('/api/weekly-price/preview', params)
}

export function previewWeeklyPriceUpload(params: {
  updateFile: File
  referenceFile: File
}) {
  const formData = new FormData()
  formData.append('update_file', params.updateFile)
  formData.append('reference_file', params.referenceFile)
  return api.post<WeeklyPricePreviewResponse>('/api/weekly-price/preview/upload', formData)
}

export function getWeeklyPriceAliases() {
  return api.get<WeeklyPriceAliasListResponse>('/api/weekly-price/aliases')
}

export function upsertWeeklyPriceAliases(mappings: Record<string, string>) {
  return api.put<WeeklyPriceAliasListResponse>('/api/weekly-price/aliases', { mappings })
}

export function deleteWeeklyPriceAlias(source_name: string) {
  return api.delete<WeeklyPriceAliasListResponse>('/api/weekly-price/aliases', {
    data: { source_name },
  })
}

export function importWeeklyQuoteBatch(params: {
  supplier: string
  quote_date: string
  source_path: string
}) {
  return api.post<WeeklyQuoteImportResponse>('/api/weekly-price/summary/import', params)
}

export function importWeeklyQuoteBatchUpload(params: {
  supplier: string
  quoteDate: string
  sourceFile: File
}) {
  const formData = new FormData()
  formData.append('supplier', params.supplier)
  formData.append('quote_date', params.quoteDate)
  formData.append('source_file', params.sourceFile)
  return api.post<WeeklyQuoteImportResponse>('/api/weekly-price/summary/import/upload', formData)
}

export function previewWeeklyQuoteSummary(params: {
  batches: WeeklyQuoteBatchInput[]
}) {
  return api.post<WeeklyQuotePreviewResponse>('/api/weekly-price/summary/preview', params)
}

export function exportWeeklyQuoteSummary(params: {
  workbook_path: string
  batches: WeeklyQuoteBatchInput[]
}) {
  return api.post<WeeklyQuoteExportResponse>('/api/weekly-price/summary/export', params)
}

export async function exportWeeklyQuoteSummaryUpload(params: {
  workbookFile: File
  batches: WeeklyQuoteBatchInput[]
}): Promise<DownloadResponsePayload> {
  const formData = new FormData()
  formData.append('workbook_file', params.workbookFile)
  formData.append('batches_json', JSON.stringify(params.batches))
  const response = await api.post('/api/weekly-price/summary/export/upload', formData, {
    responseType: 'blob',
  })
  return toDownloadPayload(response, 'weekly_quote_summary.xlsx')
}
