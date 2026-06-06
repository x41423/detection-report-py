import api from './client'
import type { ListResponse } from './types'

export interface StockAlert {
  display_name: string
  normalized_name: string
  unit_name: string
  available_quantity: number
}

export interface TransactionSummary {
  id: number
  display_name: string
  normalized_name: string
  unit_name: string
  direction: 'IN' | 'OUT' | 'ADJUST'
  quantity_delta: number
  business_date: string
  source_type: string
  note: string
  related_order_no: string
  supplier_name: string
}

export function getStockAlerts(threshold?: number) {
  return api.get<ListResponse<StockAlert>>('/api/inventory/alerts', { params: { threshold } })
}

export function getTransactionSummary(params?: {
  start_date?: string; end_date?: string; limit?: number; offset?: number
}) {
  return api.get<ListResponse<TransactionSummary>>('/api/inventory/summary', { params })
}
