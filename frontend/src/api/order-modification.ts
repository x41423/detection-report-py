import api from './client'
import type { ListResponse, MutationResponse } from './types'

export interface OrderModification {
  id: number; order_id: number; order_no: string; modifier_name: string
  summary: string; status: string; reviewer_name: string; review_comment: string
  created_at: string; updated_at: string
}

export function getModifications(params?: { limit?: number; offset?: number; status?: string }) {
  return api.get<ListResponse<OrderModification>>('/api/order-modification/', { params })
}
export function createModification(data: { order_id: number; order_no: string; modifier_name: string; summary: string }) {
  return api.post<MutationResponse>('/api/order-modification/', data)
}
export function approveModification(id: number, reviewer_name: string, comment: string) {
  return api.put<MutationResponse>(`/api/order-modification/${id}/approve`, null, {
    params: { reviewer_name, comment },
  })
}
export function rejectModification(id: number, reviewer_name: string, comment: string) {
  return api.put<MutationResponse>(`/api/order-modification/${id}/reject`, null, {
    params: { reviewer_name, comment },
  })
}
