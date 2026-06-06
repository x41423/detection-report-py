import api from './client'
import type { ListResponse, MutationResponse } from './types'

export interface AgreementPrice {
  id: number; supplier_id: number; product_id: number; price: number; unit_name: string
  effective_from: string; effective_to: string; is_active: number; created_at: string; updated_at: string
}

export function getAgreements(params?: { limit?: number; offset?: number }) {
  return api.get<ListResponse<AgreementPrice>>('/api/agreement-price/', { params })
}
export function createAgreement(data: Record<string, any>) {
  return api.post<MutationResponse>('/api/agreement-price/', data)
}
export function updateAgreement(id: number, data: Record<string, any>) {
  return api.put<MutationResponse>(`/api/agreement-price/${id}`, data)
}
export function deleteAgreement(id: number) {
  return api.delete<MutationResponse>(`/api/agreement-price/${id}`)
}
