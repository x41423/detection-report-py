import api from './client'
import type { ListResponse, MutationResponse } from './types'

export interface Supplier {
  id: number
  code: string
  name: string
  contact_person?: string
  contact_phone?: string
  contact_address?: string
  supplier_type: string
  business_license?: string
  tax_number?: string
  bank_name?: string
  bank_account?: string
  settlement_method: string
  payment_terms?: string
  credit_limit: number
  level: string
  status: string
  remark?: string
  settlement_person?: string
  settlement_phone?: string
  date_dimension?: string
  period_start_day?: number
  settlement_day?: number
  freeze_status?: number
  approval_status?: number
  sorting_priority?: number
  created_at: string
  updated_at: string
}

export interface SupplierCreateForm {
  name: string
  contact_person?: string
  contact_phone?: string
  contact_address?: string
  supplier_type?: string
  business_license?: string
  tax_number?: string
  bank_name?: string
  bank_account?: string
  settlement_method?: string
  payment_terms?: string
  credit_limit?: number
  level?: string
  remark?: string
}

export interface SupplierUpdateForm {
  name?: string
  contact_person?: string
  contact_phone?: string
  contact_address?: string
  supplier_type?: string
  business_license?: string
  tax_number?: string
  bank_name?: string
  bank_account?: string
  settlement_method?: string
  payment_terms?: string
  credit_limit?: number
  level?: string
  status?: string
  remark?: string
}

export function getSuppliers(params?: {
  search?: string; status?: string; supplier_type?: string; level?: string; limit?: number; offset?: number
}) {
  return api.get<ListResponse<Supplier>>('/api/merchant/', { params })
}

export function getSupplier(id: number) {
  return api.get<Supplier>(`/api/merchant/${id}`)
}

export function createSupplier(data: SupplierCreateForm) {
  return api.post<MutationResponse & { id: number; code: string }>('/api/merchant/', data)
}

export function updateSupplier(id: number, data: SupplierUpdateForm) {
  return api.put<MutationResponse>(`/api/merchant/${id}`, data)
}

export function deleteSupplier(id: number) {
  return api.delete<MutationResponse>(`/api/merchant/${id}`)
}

export function activateSupplier(id: number) {
  return api.post<MutationResponse>(`/api/merchant/${id}/activate`)
}

export function hardDeleteSupplier(id: number) {
  return api.delete<MutationResponse>(`/api/merchant/${id}/hard`)
}
