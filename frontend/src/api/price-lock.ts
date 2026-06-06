import api from './client'
import type { ListResponse, MutationResponse } from './types'

export interface PriceLockItem {
  id: number
  veg_name: string
  locked_price: number
}

export interface PriceLockRule {
  id: number
  rule_code: string
  rule_name: string
  salemenu_id?: string
  salemenu_name?: string
  target_count: number
  category_count: number
  start_time?: string
  end_time?: string
  status: string
  items?: PriceLockItem[]
  created_at: string
}

export function getPriceLockRules(params?: {
  search?: string; status?: string; limit?: number; offset?: number
}) {
  return api.get<ListResponse<PriceLockRule>>('/api/price-lock/', { params })
}

export function getPriceLockRule(id: number) {
  return api.get<PriceLockRule>(`/api/price-lock/${id}`)
}

export function createPriceLockRule(data: {
  rule_name: string; salemenu_name?: string; start_time?: string; end_time?: string
  items: { veg_name: string; locked_price: number }[]
}) {
  return api.post<PriceLockRule>('/api/price-lock/', data)
}

export function updatePriceLockRule(id: number, data: {
  rule_name?: string; start_time?: string; end_time?: string
}) {
  return api.put<PriceLockRule>(`/api/price-lock/${id}`, data)
}

export function deactivatePriceLockRule(id: number) {
  return api.delete<MutationResponse>(`/api/price-lock/${id}`)
}
