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

export type WeeklyQuoteSummaryRule = 'highest' | 'average'

export interface WeeklyQuoteSupplierOption {
  id?: number | null
  name: string
  weekly_batch_limit: number
  summary_rule: WeeklyQuoteSummaryRule
  is_builtin: boolean
  sort_order: number
}

export interface WeeklyQuoteMeasureUnitOption {
  id?: number | null
  name: string
  sort_order: number
}

export interface WeeklyQuoteSummaryOptionsResponse {
  success: boolean
  suppliers: WeeklyQuoteSupplierOption[]
  measure_units: WeeklyQuoteMeasureUnitOption[]
}

export interface WeeklyQuoteSavedBatch {
  id: number
  supplier: string
  quote_date: string
  entry_count: number
  entries: WeeklyQuoteEntryInput[]
  source_label: string
  source_path: string
  created_at: string
}

export interface WeeklyQuoteSupplierWeekOverview {
  supplier: string
  limit: number
  summary_rule: WeeklyQuoteSummaryRule
  batches: WeeklyQuoteSavedBatch[]
  batch_count: number
  entry_count: number
  summary_items: WeeklyQuoteSummaryItem[]
}

export interface WeeklyQuoteWeekOverviewResponse {
  success: boolean
  week_start: string
  week_end: string
  suppliers: WeeklyQuoteSupplierWeekOverview[]
  total_batches: number
  total_entries: number
  total_summary_items: number
  issue_messages: string[]
}

export interface WeeklyQuoteImportResponse {
  success: boolean
  message: string
  batch: WeeklyQuoteBatchInput
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

export function importWeeklyQuoteBatchFromPath(params: {
  supplier: string
  quoteDate: string
  sourcePath: string
}) {
  return api.post<WeeklyQuoteImportResponse>('/api/weekly-price/summary/import', {
    supplier: params.supplier,
    quote_date: params.quoteDate,
    source_path: params.sourcePath,
  })
}

export function getWeeklyQuoteSummaryOptions() {
  return api.get<WeeklyQuoteSummaryOptionsResponse>('/api/weekly-price/summary/options')
}

export function createWeeklyQuoteSupplier(payload: {
  name: string
  weekly_batch_limit: number
  summary_rule: WeeklyQuoteSummaryRule
}) {
  return api.post<{ success: boolean; message: string; supplier: WeeklyQuoteSupplierOption }>(
    '/api/weekly-price/summary/suppliers',
    payload,
  )
}

export function createWeeklyQuoteMeasureUnit(payload: { name: string }) {
  return api.post<{ success: boolean; message: string; measure_unit: WeeklyQuoteMeasureUnitOption }>(
    '/api/weekly-price/summary/measure-units',
    payload,
  )
}

export async function exportWeeklyQuoteSummaryWeekUpload(params: {
  workbookFile: File
  date: string
}): Promise<DownloadResponsePayload> {
  const formData = new FormData()
  formData.append('workbook_file', params.workbookFile)
  formData.append('date', params.date)
  const response = await api.post('/api/weekly-price/summary/export/week/upload', formData, {
    responseType: 'blob',
  })
  return toDownloadPayload(response, 'weekly_quote_summary.xlsx')
}

export async function saveQuoteBatch(payload: {
  supplier: string
  quote_date: string
  entries: WeeklyQuoteEntryInput[]
  source_label?: string
}) {
  return api.post<{ success: boolean; batch: WeeklyQuoteSavedBatch }>(
    '/api/weekly-price/summary/save', payload
  )
}

export async function deleteQuoteBatch(supplier: string, quote_date: string) {
  return api.post<{ success: boolean }>(
    '/api/weekly-price/summary/delete', { supplier, quote_date }
  )
}

export async function getWeeklyQuoteWeekOverview(date: string) {
  return api.get<WeeklyQuoteWeekOverviewResponse>(
    '/api/weekly-price/summary/week', { params: { date } }
  )
}

// ==================================================================
// Template storage (MinIO)
// ==================================================================

export interface TemplateInfo {
  name: string
  size: number
  updated: string
}

export interface TemplateListResponse {
  success: boolean
  templates: Record<string, TemplateInfo | null>
}

export interface TemplateReadResponse {
  success: boolean
  grid: string[][]
  rows: number
  cols: number
}

export function uploadTemplate(tmplType: string, file: File) {
  const fd = new FormData()
  fd.append('file', file)
  return api.post<{ success: boolean; message: string }>(`/api/weekly-price/template/${tmplType}`, fd)
}

export function uploadTemplateFromPath(tmplType: string, filePath: string) {
  const fd = new FormData()
  fd.append('file_path', filePath)
  return api.post<{ success: boolean; message: string }>(`/api/weekly-price/template/${tmplType}/from-path`, fd)
}

export function listTemplates() {
  return api.get<TemplateListResponse>('/api/weekly-price/templates')
}

export function readTemplate(tmplType: string) {
  return api.get<TemplateReadResponse>(`/api/weekly-price/template/${tmplType}/read`)
}

export function saveTemplate(tmplType: string, grid: string[][]) {
  return api.put<{ success: boolean; message: string }>(`/api/weekly-price/template/${tmplType}`, grid)
}

export function previewFromTemplates() {
  return api.post<WeeklyPricePreviewResponse>('/api/weekly-price/preview/templates')
}

// ==================================================================
// Paste mode (粘贴模式)
// ==================================================================

export function previewWeeklyPricePaste(params: {
  names: string[]
  prices: string[]
}) {
  return api.post<WeeklyPricePreviewResponse>(
    '/api/weekly-price/preview/paste', params
  )
}

export async function executeWeeklyPricePaste(params: {
  names: string[]
  prices: string[]
}): Promise<DownloadResponsePayload> {
  const response = await api.post(
    '/api/weekly-price/execute/paste', params,
    { responseType: 'blob' }
  )
  return toDownloadPayload(response, 'weekly_price_updated.xlsx')
}
