import api from './client'
import type { ListResponse, MutationResponse } from './types'

export interface Settlement {
  id: number
  supplier_id: number
  supplier_name?: string
  settlement_period: string
  payable_amount: number
  paid_amount: number
  fee_amount: number
  discount_amount: number
  balance_amount: number
  reconciliation_status: string
  status: string
  remark?: string
  created_at: string
}

export function getSettlements(params?: {
  supplier_id?: number; period?: string; status?: string; limit?: number; offset?: number
}) {
  return api.get<ListResponse<Settlement>>('/api/settlement/', { params })
}

export function getSettlement(id: number) {
  return api.get<Settlement>(`/api/settlement/${id}`)
}

export function createSettlement(data: {
  supplier_id: number; settlement_period: string; payable_amount?: number
  paid_amount?: number; fee_amount?: number; discount_amount?: number; remark?: string
}) {
  return api.post<Settlement>('/api/settlement/', data)
}

export function autoCreateSettlement(supplierId: number, period: string) {
  return api.post<MutationResponse & { record: Settlement }>(
    '/api/settlement/auto', null, { params: { supplier_id: supplierId, period } }
  )
}

export function confirmSettlement(id: number) {
  return api.post<MutationResponse>(`/api/settlement/${id}/confirm`)
}
