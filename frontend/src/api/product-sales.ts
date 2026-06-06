import api from './client'

export interface SalesSummary {
  order_count: number
  total_amount: number
  total_sales: number
  merchant_count: number
}

export interface TopProduct {
  product_name: string
  total_amount: number
  total_qty: number
  order_count: number
}

export interface CategorySales {
  category: string
  total_amount: number
  item_count: number
}

export function getProductSalesSummary(params?: { date_from?: string; date_to?: string }) {
  return api.get<{ success: boolean; data: SalesSummary }>('/api/dashboard/product-sales/summary', { params })
}

export function getProductSalesTop(params?: { date_from?: string; date_to?: string; limit?: number }) {
  return api.get<{ success: boolean; items: TopProduct[] }>('/api/dashboard/product-sales/top', { params })
}

export function getProductSalesByCategory(params?: { date_from?: string; date_to?: string }) {
  return api.get<{ success: boolean; items: CategorySales[] }>('/api/dashboard/product-sales/by-category', { params })
}
