import api from './client'
import type { ListResponse, MutationResponse } from './types'

export interface PurchaseInItem {
  id: number
  veg_name: string
  category?: string
  unit: string
  quantity: number
  unit_price: number
  amount: number
}

export interface PurchaseIn {
  id: number
  order_no: string
  supplier_id: number
  supplier_name?: string
  inbound_date: string
  total_amount: number
  status: string
  remark?: string
  items?: PurchaseInItem[]
  created_at: string
}

export interface PurchaseReturn {
  id: number
  order_no: string
  supplier_id: number
  supplier_name?: string
  return_date: string
  total_amount: number
  status: string
  remark?: string
  items?: PurchaseInItem[]
  created_at: string
}

export interface PurchaseInListParams {
  search?: string; supplier_id?: number; status?: string; limit?: number; offset?: number
}

export function getPurchaseIns(params?: PurchaseInListParams) {
  return api.get<ListResponse<PurchaseIn>>('/api/purchase/in', { params })
}

export function getPurchaseIn(id: number) {
  return api.get<PurchaseIn>(`/api/purchase/in/${id}`)
}

export function createPurchaseIn(data: {
  supplier_id: number; inbound_date: string; remark?: string
  items: { veg_name: string; quantity: number; unit_price: number; unit?: string; category?: string }[]
}) {
  return api.post<PurchaseIn>('/api/purchase/in', data)
}

export function confirmPurchaseIn(id: number) {
  return api.post<MutationResponse>(`/api/purchase/in/${id}/confirm`)
}

export function getPurchaseReturns(params?: PurchaseInListParams) {
  return api.get<ListResponse<PurchaseReturn>>('/api/purchase/return', { params })
}

export function getPurchaseReturn(id: number) {
  return api.get<PurchaseReturn>(`/api/purchase/return/${id}`)
}

export function createPurchaseReturn(data: {
  supplier_id: number; return_date: string; remark?: string
  items: { veg_name: string; quantity: number; unit_price: number }[]
}) {
  return api.post<PurchaseReturn>('/api/purchase/return', data)
}

export function confirmPurchaseReturn(id: number) {
  return api.post<MutationResponse>(`/api/purchase/return/${id}/confirm`)
}
