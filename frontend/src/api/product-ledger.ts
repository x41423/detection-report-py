import api from './client'
import type { ListResponse } from './types'

export interface LedgerEntry {
  id: number; display_name: string; direction: string; quantity_delta: number
  business_date: string; source_type: string; unit_name: string
  product_id: number; note: string; created_at: string
}
export interface LedgerSummary {
  in_qty: number; out_qty: number; net_qty: number; transaction_count: number
}

export function getLedger(params: { product_id?: number; date_from?: string; date_to?: string; limit?: number; offset?: number }) {
  return api.get<ListResponse<LedgerEntry>>('/api/dashboard/product-ledger', { params })
}
export function getLedgerSummary(params: { product_id?: number; date_from?: string; date_to?: string }) {
  return api.get<{ summary: LedgerSummary }>('/api/dashboard/product-ledger/summary', { params })
}
