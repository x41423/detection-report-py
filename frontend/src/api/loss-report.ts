import api from './client'
import type { ListResponse, MutationResponse } from './types'

export interface LossReportItem {
  id: number; report_id: number; product_id: number; quantity: number
  unit_name: string; reason: string; unit_price: number; amount: number
}
export interface LossReport {
  id: number; report_no: string; report_date: string; report_type: string
  warehouse_id: number; notes: string; total_amount: number; status: string
  created_at: string; updated_at: string
}

export function getLossReports(params?: { limit?: number; offset?: number }) {
  return api.get<ListResponse<LossReport>>('/api/loss-report/', { params })
}
export function getLossReport(id: number) {
  return api.get<{ report: LossReport; items: LossReportItem[] }>(`/api/loss-report/${id}`)
}
export function createLossReport(data: Record<string, any>) {
  return api.post<MutationResponse>('/api/loss-report/', data)
}
export function updateLossReport(id: number, data: Record<string, any>) {
  return api.put<MutationResponse>(`/api/loss-report/${id}`, data)
}
export function deleteLossReport(id: number) {
  return api.delete<MutationResponse>(`/api/loss-report/${id}`)
}
