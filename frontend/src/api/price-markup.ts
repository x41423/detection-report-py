import api from './client'
import type { ListResponse, MutationResponse } from './types'

export interface PriceMarkup {
  id: number; name: string; rate: number; scope: string; scope_id: number; is_active: number; created_at: string; updated_at: string
}

export function getMarkups(params?: { limit?: number; offset?: number }) {
  return api.get<ListResponse<PriceMarkup>>('/api/price-markup/', { params })
}
export function createMarkup(data: { name: string; rate: number; scope: string; scope_id: number }) {
  return api.post<MutationResponse>('/api/price-markup/', data)
}
export function updateMarkup(id: number, data: Record<string, any>) {
  return api.put<MutationResponse>(`/api/price-markup/${id}`, data)
}
export function deleteMarkup(id: number) {
  return api.delete<MutationResponse>(`/api/price-markup/${id}`)
}
