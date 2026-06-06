import api from './client'
import type { ListResponse, MutationResponse } from './types'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface InspectionReportProduct {
  id: number
  report_id: number
  sku_id: number
  product_id: number
  batch: string
  product_name: string
  product_code: string
  sku_name: string
}

export interface InspectionReportProductForm {
  sku_id: number
  product_id: number
  batch: string
}

export interface InspectionReport {
  id: number
  report_no: string
  name: string
  file_url: string
  test_date: string
  valid_from: string
  valid_until: string
  supplier_id: number
  supplier_name: string
  submit_org: string
  test_org: string
  status: string
  source: string
  pesticide_task_id: number
  uploaded_by: number
  uploader_name: string
  product_count: number
  products: InspectionReportProduct[]
  created_at: string
  updated_at: string
}

export interface InspectionReportForm {
  name: string
  test_date: string
  valid_from: string
  valid_until: string
  supplier_id: number
  submit_org: string
  test_org: string
  file_url: string
  status: string
  products: InspectionReportProductForm[]
}

export interface InspectionReportListParams {
  search?: string
  status?: string
  supplier_id?: number
  test_date_from?: string
  test_date_to?: string
  limit?: number
  offset?: number
}

// ---------------------------------------------------------------------------
// API functions
// ---------------------------------------------------------------------------

export function getReports(params?: InspectionReportListParams) {
  return api.get<ListResponse<InspectionReport>>('/api/inspection-report/', { params })
}

export function getReport(id: number) {
  return api.get<{ success: boolean; item: InspectionReport }>(`/api/inspection-report/${id}`)
}

export function createReport(data: InspectionReportForm) {
  return api.post<MutationResponse<InspectionReport>>('/api/inspection-report/', data)
}

export function updateReport(id: number, data: Partial<InspectionReportForm>) {
  return api.put<MutationResponse<InspectionReport>>(`/api/inspection-report/${id}`, data)
}

export function deleteReport(id: number) {
  return api.delete<MutationResponse<null>>(`/api/inspection-report/${id}`)
}

export function uploadReportFile(file: File) {
  const formData = new FormData()
  formData.append('file', file)
  return api.post<{ success: boolean; message: string; url: string }>(
    '/api/inspection-report/upload',
    formData,
    { headers: { 'Content-Type': 'multipart/form-data' } },
  )
}
