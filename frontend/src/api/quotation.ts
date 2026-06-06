import api from './client'
import type { ListResponse, MutationResponse } from './types'

// ── Quotation ──

export interface QuotationProduct {
  id: number
  quotation_id: number
  product_id: number
  product_name: string
  product_code: string
  base_unit: string
  price: number
  is_active: number
}

export interface Quotation {
  id: number
  code: string
  name: string
  external_name: string
  currency: string
  operation_time: string
  tags: string
  status: string
  pricing_start_date: string
  pricing_end_date: string
  auto_pricing: number
  description: string
  product_count: number
  products: QuotationProduct[]
  created_at: string
  updated_at: string
}

// ── Create / Update ──

export interface QuotationCreateForm {
  name: string
  external_name?: string
  currency?: string
  operation_time?: string
  tags?: string
  status?: string
  pricing_start_date?: string
  pricing_end_date?: string
  auto_pricing?: boolean
  description?: string
  products?: { product_id: number; price: number }[]
}

export interface QuotationUpdateForm {
  name?: string
  external_name?: string
  currency?: string
  operation_time?: string
  tags?: string
  status?: string
  pricing_start_date?: string
  pricing_end_date?: string
  auto_pricing?: boolean
  description?: string
}

export interface QuotationProductCreateForm {
  product_id: number
  price: number
}

export interface QuotationProductUpdateForm {
  price?: number
  is_active?: boolean
}

// ── API functions ──

export function getQuotations(params?: {
  search?: string; status?: string; limit?: number; offset?: number
}) {
  return api.get<ListResponse<Quotation>>('/api/quotation/', { params })
}

export function getQuotation(id: number) {
  return api.get<Quotation>(`/api/quotation/${id}`)
}

export function createQuotation(data: QuotationCreateForm) {
  return api.post<MutationResponse>('/api/quotation/', data)
}

export function updateQuotation(id: number, data: QuotationUpdateForm) {
  return api.put<MutationResponse>(`/api/quotation/${id}`, data)
}

export function toggleQuotationStatus(id: number, status: string) {
  return api.post<MutationResponse>(`/api/quotation/${id}/toggle`, null, { params: { status } })
}

export function addQuotationProduct(quotationId: number, data: QuotationProductCreateForm) {
  return api.post<MutationResponse>(`/api/quotation/${quotationId}/products`, data)
}

export function updateQuotationProduct(qpId: number, data: QuotationProductUpdateForm) {
  return api.put<MutationResponse>(`/api/quotation/products/${qpId}`, data)
}

export function removeQuotationProduct(qpId: number) {
  return api.delete<MutationResponse>(`/api/quotation/products/${qpId}`)
}
