import api from './client'
import type { ListResponse, MutationResponse } from './types'

export interface Supplier {
  id: number
  supplier_code: string
  name: string
  company_name: string
  contact_address: string
  remark: string
  default_purchaser: string
  settlement_cycle: string
  invoice_type: string
  sales_purchase_settlement: number
  business_license: string
  bank_account_name: string
  bank_name: string
  bank_account: string
  supplier_nature: string
  purchase_auto_sync: number
  geo_location: string
  qualification_images: string
  payment_qr: string
  status: string
  created_at: string
  updated_at: string
}

export interface SupplierForm {
  supplier_code: string
  name: string
  company_name?: string
  contact_address?: string
  remark?: string
  default_purchaser?: string
  settlement_cycle?: string
  invoice_type?: string
  sales_purchase_settlement?: number
  business_license?: string
  bank_account_name?: string
  bank_name?: string
  bank_account?: string
  supplier_nature?: string
  purchase_auto_sync?: number
  geo_location?: string
  qualification_images?: string
  payment_qr?: string
}

export function getSuppliers(params?: {
  search?: string; status?: string; limit?: number; offset?: number
}) {
  return api.get<ListResponse<Supplier>>('/api/supplier/', { params })
}

export function getSupplier(id: number) {
  return api.get<{ success: boolean; item: Supplier }>(`/api/supplier/${id}`)
}

export function createSupplier(data: SupplierForm) {
  return api.post<MutationResponse & { id: number }>('/api/supplier/', data)
}

export function updateSupplier(id: number, data: Partial<SupplierForm>) {
  return api.put<MutationResponse>(`/api/supplier/${id}`, data)
}

export function deleteSupplier(id: number) {
  return api.delete<MutationResponse>(`/api/supplier/${id}`)
}
