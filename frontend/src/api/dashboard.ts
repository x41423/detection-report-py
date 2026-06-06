import api from './client'

export interface DashboardOverview {
  total_suppliers: number
  active_suppliers: number
  purchase_this_month: number
  orders_this_month: number
  pending_settlements: number
  low_stock_items: number
}

export interface MonthlyTrend {
  period: string
  amount: number
  count: number
}

export interface TopSupplier {
  supplier_id: number
  supplier_name: string
  total_amount: number
  order_count: number
}

export interface Dashboard {
  success: boolean
  overview: DashboardOverview
  purchase_trend: MonthlyTrend[]
  order_trend: MonthlyTrend[]
  top_suppliers: TopSupplier[]
}

export function getDashboard() {
  return api.get<Dashboard>('/api/dashboard/')
}
