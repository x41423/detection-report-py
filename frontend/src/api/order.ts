import api from './client'
import type { ListResponse, MutationResponse } from './types'

export interface OrderItem {
  id: number
  product_name: string
  product_id?: string
  category?: string
  unit: string
  quantity: number
  unit_price: number
  amount: number
}

export interface Order {
  id: number
  order_no: string
  // -- 客户 --
  merchant_name?: string
  merchant_id?: string
  merchant_tag?: string
  // -- 时间 --
  order_date: string
  receive_start_date?: string
  receive_end_date?: string
  receive_start_time?: string
  receive_end_time?: string
  operation_time?: string
  // -- 配送 --
  delivery_method?: string
  receiver?: string
  delivery_address?: string
  sign_method?: string
  // -- 订单 --
  order_type?: string
  order_amount: number
  freight: number
  sales_amount_incl_freight: number
  discount_amount: number
  order_status: string
  outbound_status?: string
  remark?: string
  // -- 关联 --
  related_outbound_no?: string
  third_party_order_no?: string
  // -- 自定义 --
  custom_field_1?: string
  custom_field_2?: string
  custom_field_3?: string
  // -- v5 新增字段 --
  payment_status?: string
  loading_status?: string
  print_status?: string
  driver_name?: string
  order_source?: string
  sorting_status?: string
  inspection_status?: string
  cabinet_status?: string
  route_name?: string
  pickup_point?: string
  total_order_quantity?: number
  accounting_quantity_sale?: number
  accounting_quantity_base?: number
  product_category_count?: number
  merchant_custom_code?: string
  after_sale_amount?: number
  should_refund_amount?: number
  edit_status?: string
  vehicle_status?: string
  batch_status?: string
  batch_merchant_name?: string
  main_sorting_category?: string
  main_sorting_category_count?: number
  // -- 元数据 --
  operator?: string
  items?: OrderItem[]
  created_at: string
}

export interface OrderAfterSale {
  id: number
  order_id: number
  product_name: string
  after_sale_type?: string
  return_quantity: number
  return_amount: number
  status: string
}

// -- 新建订单表单（对齐观麦订单创建页面） --
export interface OrderCreateForm {
  merchant_name?: string
  merchant_id?: string
  merchant_tag?: string
  order_date: string
  receive_start_date?: string
  receive_end_date?: string
  receive_start_time?: string
  receive_end_time?: string
  operation_time?: string
  delivery_method?: string
  receiver?: string
  delivery_address?: string
  sign_method?: string
  order_type?: string
  freight?: number
  discount_amount?: number
  remark?: string
  related_outbound_no?: string
  third_party_order_no?: string
  custom_field_1?: string
  custom_field_2?: string
  custom_field_3?: string
  items: { product_name: string; quantity: number; unit_price: number; unit?: string }[]
}

// -- 复制订单选项 --
export interface OrderCopyOptions {
  copy_type: 'normal' | 'yes' | 'no'
  sync_unit_price: 'yes' | 'no'
  sync_price_change_rate: 'yes' | 'no'
  copy_outbound_quantity: 'yes' | 'no'
}

// -- 列偏好 --
export interface ColumnPreferenceResponse {
  page_key: string
  visible_columns: string[]
}

// ====================================================================
// API 函数
// ====================================================================

export function getOrders(params?: {
  search?: string; merchant_name?: string; order_status?: string;
  date_mode?: string; date_from?: string; date_to?: string;
  limit?: number; offset?: number
}) {
  return api.get<ListResponse<Order>>('/api/order/', { params })
}

export function getOrder(id: number) {
  return api.get<Order>(`/api/order/${id}`)
}

export function createOrder(data: OrderCreateForm) {
  return api.post<MutationResponse<Order>>('/api/order/', data)
}

export function updateOrder(id: number, data: Partial<OrderCreateForm>) {
  return api.put<MutationResponse<Order>>(`/api/order/${id}`, data)
}

export function deleteOrder(id: number) {
  return api.delete<MutationResponse>(`/api/order/${id}`)
}

export function copyOrder(id: number, options: OrderCopyOptions) {
  return api.post<MutationResponse<{ new_order_id: number; new_order_no: string }>>(`/api/order/${id}/copy`, options)
}

export function confirmOrderOutbound(id: number) {
  return api.post<MutationResponse>(`/api/order/${id}/outbound`)
}

export function undoOrderOutbound(id: number) {
  return api.post<MutationResponse>(`/api/order/${id}/undo-outbound`)
}

export function getAfterSales(orderId: number) {
  return api.get<OrderAfterSale[]>(`/api/order/${orderId}/after-sale`)
}

export function createAfterSale(orderId: number, data: {
  product_name: string; after_sale_type?: string; return_quantity?: number; return_amount?: number
}) {
  return api.post<MutationResponse>(`/api/order/${orderId}/after-sale`, data)
}

// -- 列偏好 --
export function saveColumnPreference(pageKey: string, visibleColumns: string[]) {
  return api.put<MutationResponse>('/api/order/column-preference', {
    page_key: pageKey,
    visible_columns: visibleColumns,
  })
}

export function getColumnPreference(pageKey: string = 'order_list') {
  return api.get<ColumnPreferenceResponse>('/api/order/column-preference', { params: { page_key: pageKey } })
}
