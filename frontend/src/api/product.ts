import api from './client'
import type { ListResponse, MutationResponse } from './types'
import axios from 'axios'

// ── Product SKU ──

export interface ProductSku {
  id: number
  product_id: number
  sku_code: string
  spec_name: string
  sku_type: string
  is_listed: number
  price: number
  stock: number
  // Phase 1 字段
  pricing_method: string
  min_order_qty: number
  sale_spec_value: number
  sale_spec_unit: string
  reference_cost: number
  purchase_spec: string
  stock_setting: string
  stock_limit_value: number
  // Phase 2 字段
  pricing_rule: string
  is_spot: number
  default_stock_slot: string
  waste_ratio: number
  box_type: string
  // Phase 3 字段
  order_round_up: number
  is_cycle_item: number
}

// ── Product ──

export interface Product {
  id: number
  code: string
  name: string
  alias: string
  category_id: number | null
  category_name: string | null
  product_type: string
  custom_code: string
  delivery_method: string
  purchase_type: string
  base_unit: string
  image_url: string
  shelf_life_days: number
  purchase_mode: string
  default_supplier_id: number | null
  description: string
  tax_category_code: string
  tax_rate: number
  custom_field_1: string
  custom_field_2: string
  custom_field_3: string
  has_inspection_report: number
  is_active: number
  // Phase 3 字段
  performance_method: string
  suggested_min_cost: number
  product_tags: string
  fixed_url: string
  notes: string
  skus: ProductSku[]
  created_at: string
  updated_at: string
}

// ── Category ──

export interface Category {
  id: number
  name: string
  parent_id: number | null
  level: number
  sort_order: number
  children?: Category[]
}

// ── Create / Update ──

export interface ProductCreateForm {
  name: string
  alias?: string
  category_id?: number | null
  product_type?: string
  custom_code?: string
  delivery_method?: string
  purchase_type?: string
  base_unit?: string
  image_url?: string
  shelf_life_days?: number
  purchase_mode?: string
  default_supplier_id?: number | null
  description?: string
  tax_category_code?: string
  tax_rate?: number
  custom_field_1?: string
  custom_field_2?: string
  custom_field_3?: string
  has_inspection_report?: boolean
  // Phase 3 字段
  performance_method?: string
  suggested_min_cost?: number
  product_tags?: string
  fixed_url?: string
  notes?: string
}

export interface ProductUpdateForm {
  name?: string
  alias?: string
  category_id?: number | null
  product_type?: string
  custom_code?: string
  delivery_method?: string
  purchase_type?: string
  base_unit?: string
  image_url?: string
  shelf_life_days?: number
  purchase_mode?: string
  default_supplier_id?: number | null
  description?: string
  tax_category_code?: string
  tax_rate?: number
  custom_field_1?: string
  custom_field_2?: string
  custom_field_3?: string
  has_inspection_report?: boolean
  // Phase 3 字段
  performance_method?: string
  suggested_min_cost?: number
  product_tags?: string
  fixed_url?: string
  notes?: string
}

export interface SkuCreateForm {
  sku_code?: string
  spec_name?: string
  sku_type?: string
  is_listed?: boolean
  price?: number
  stock?: number
  // Phase 1 字段
  pricing_method?: string
  min_order_qty?: number
  sale_spec_value?: number
  sale_spec_unit?: string
  reference_cost?: number
  purchase_spec?: string
  stock_setting?: string
  stock_limit_value?: number
  // Phase 2 字段
  pricing_rule?: string
  is_spot?: boolean
  default_stock_slot?: string
  waste_ratio?: number
  box_type?: string
  // Phase 3 字段
  order_round_up?: boolean
  is_cycle_item?: boolean
}

// ── API functions ──

export function getProducts(params?: {
  search?: string; category_id?: number; limit?: number; offset?: number
  include_inactive?: boolean
}) {
  return api.get<ListResponse<Product>>('/api/product/', { params })
}

export function activateProduct(id: number) {
  return api.put<MutationResponse>(`/api/product/${id}/activate`)
}

export function getCategories() {
  return api.get<ListResponse<Category>>('/api/product/categories')
}

export function createCategory(data: { name: string; parent_id?: number; sort_order?: number }) {
  return api.post<MutationResponse<{ id: number }>>('/api/product/categories', data)
}

export function updateCategory(id: number, data: { name?: string; parent_id?: number; sort_order?: number }) {
  return api.put<MutationResponse>(`/api/product/categories/${id}`, data)
}

export function deleteCategory(id: number) {
  return api.delete<MutationResponse>(`/api/product/categories/${id}`)
}

export function getProduct(id: number) {
  return api.get<Product>(`/api/product/${id}`)
}

export function createProduct(data: ProductCreateForm) {
  return api.post<MutationResponse<Product>>('/api/product/', data)
}

export function updateProduct(id: number, data: ProductUpdateForm) {
  return api.put<MutationResponse<Product>>(`/api/product/${id}`, data)
}

export function deleteProduct(id: number) {
  return api.delete<MutationResponse>(`/api/product/${id}`)
}

export function getSkus(productId: number) {
  return api.get<ListResponse<ProductSku>>(`/api/product/${productId}/skus`)
}

export function createSku(productId: number, data: SkuCreateForm) {
  return api.post<MutationResponse>(`/api/product/${productId}/skus`, data)
}

export function updateSku(skuId: number, data: SkuCreateForm) {
  return api.put<MutationResponse>(`/api/product/skus/${skuId}`, data)
}

// ── Image Upload ──

export function uploadProductImage(file: File) {
  const formData = new FormData()
  formData.append('file', file)
  const token = localStorage.getItem('token')
  return axios.post<{ success: boolean; message: string; url: string }>(
    '/api/product/upload-image',
    formData,
    {
      headers: {
        'Content-Type': 'multipart/form-data',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
    },
  )
}
