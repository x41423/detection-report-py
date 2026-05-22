import api from './client'
import type { InventoryBalance, InventoryTransaction } from '../features/inventory/types'

export interface InventoryBalanceListResponse {
  success: boolean
  message: string
  items: InventoryBalance[]
  total: number
}

export interface InventoryTransactionListResponse {
  success: boolean
  message: string
  items: InventoryTransaction[]
  total: number
}

export interface InventoryTransactionMutationResponse {
  success: boolean
  message: string
  transaction: InventoryTransaction
}

export interface InventoryDeleteResponse {
  success: boolean
  message: string
}

export function getInventoryBalances(params?: {
  search?: string
  limit?: number
  include_zero?: boolean
}) {
  return api.get<InventoryBalanceListResponse>('/api/inventory/balances', { params })
}

export function getInventoryTransactions(params?: {
  search?: string
  limit?: number
  offset?: number
  source_type?: string
}) {
  return api.get<InventoryTransactionListResponse>('/api/inventory/transactions', { params })
}

export function exportInventoryBalances(params?: {
  search?: string
  include_zero?: boolean
}) {
  return api.get<Blob>('/api/inventory/export/balances', {
    params,
    responseType: 'blob',
  })
}

export function createInventoryOutbound(params: {
  business_date: string
  name: string
  unit: string
  quantity: number
  note?: string
}) {
  return api.post<InventoryTransactionMutationResponse>('/api/inventory/outbound', params)
}

export function updateInventoryOutbound(
  transactionId: number,
  params: {
    business_date: string
    name: string
    unit: string
    quantity: number
    note?: string
  },
) {
  return api.put<InventoryTransactionMutationResponse>(`/api/inventory/outbound/${transactionId}`, params)
}

export function deleteInventoryOutbound(transactionId: number) {
  return api.delete<InventoryDeleteResponse>(`/api/inventory/outbound/${transactionId}`)
}

export function createInventoryAdjustment(params: {
  business_date: string
  name: string
  unit: string
  target_quantity: number
  note?: string
}) {
  return api.post<InventoryTransactionMutationResponse>('/api/inventory/adjustments', params)
}

export function updateInventoryAdjustment(
  transactionId: number,
  params: {
    business_date: string
    name: string
    unit: string
    target_quantity: number
    note?: string
  },
) {
  return api.put<InventoryTransactionMutationResponse>(`/api/inventory/adjustments/${transactionId}`, params)
}

export function deleteInventoryAdjustment(transactionId: number) {
  return api.delete<InventoryDeleteResponse>(`/api/inventory/adjustments/${transactionId}`)
}
