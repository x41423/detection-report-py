import api from './client'
import type { ListResponse, MutationResponse } from './types'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface InventoryTransaction {
  id: number
  veg_id: number | null
  display_name: string
  normalized_name: string
  unit_id: number
  unit_name: string
  direction: string
  quantity_delta: number
  quantity: number
  business_date: string
  source_type: string
  source_ref_id: number | null
  note: string
  created_at: string
}

export interface InventoryBalance {
  id: number
  veg_id: number | null
  display_name: string
  unit_name: string
  quantity: number
  last_updated: string
}

export interface InventoryTransactionParams {
  search?: string
  source_type?: string
  direction?: string
  date_from?: string
  date_to?: string
  limit?: number
  offset?: number
}

// ---------------------------------------------------------------------------
// API functions
// ---------------------------------------------------------------------------

export function getInventoryTransactions(params?: InventoryTransactionParams) {
  return api.get<ListResponse<InventoryTransaction>>('/api/inventory/transactions', { params })
}

export function getInventoryBalances(params?: { search?: string; limit?: number; include_zero?: boolean }) {
  return api.get<ListResponse<InventoryBalance>>('/api/inventory/balances', { params })
}

export function exportInventoryBalances(params?: { search?: string; include_zero?: boolean }) {
  return api.get('/api/inventory/export/balances', { params, responseType: 'blob' })
}

export function createInventoryOutbound(data: {
  business_date: string; name: string; unit: string; quantity: number; note?: string
}) {
  return api.post<MutationResponse>('/api/inventory/outbound', data)
}

export function updateInventoryOutbound(id: number, data: {
  business_date: string; name: string; unit: string; quantity: number; note?: string
}) {
  return api.put<MutationResponse>(`/api/inventory/outbound/${id}`, data)
}

export function deleteInventoryOutbound(id: number) {
  return api.delete<MutationResponse>(`/api/inventory/outbound/${id}`)
}

export function createInventoryAdjustment(data: {
  business_date: string; name: string; unit: string; target_quantity: number; note?: string
}) {
  return api.post<MutationResponse>('/api/inventory/adjustments', data)
}

export function updateInventoryAdjustment(id: number, data: {
  business_date: string; name: string; unit: string; target_quantity: number; note?: string
}) {
  return api.put<MutationResponse>(`/api/inventory/adjustments/${id}`, data)
}

export function deleteInventoryAdjustment(id: number) {
  return api.delete<MutationResponse>(`/api/inventory/adjustments/${id}`)
}
