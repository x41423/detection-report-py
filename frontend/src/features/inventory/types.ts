export type InventoryDirection = 'IN' | 'OUT' | 'ADJUST'
export type InventorySourceType = 'daily_intake' | 'manual_outbound' | 'manual_adjust'

export interface InventoryBalance {
  display_name: string
  normalized_name: string
  veg_id: number | null
  unit_id: number
  unit_name: string
  available_quantity: number
  transaction_count: number
  last_business_date: string | null
  updated_at: string | null
}

export interface InventoryTransaction {
  id: number
  display_name: string
  normalized_name: string
  veg_id: number | null
  unit_id: number
  unit_name: string
  direction: InventoryDirection
  quantity: number
  quantity_delta: number
  business_date: string
  source_type: InventorySourceType
  source_ref_id: number | null
  target_quantity: number | null
  note: string
  created_at: string | null
  updated_at: string | null
}

export const INVENTORY_DIRECTION_LABELS: Record<InventoryDirection, string> = {
  IN: '入库',
  OUT: '出库',
  ADJUST: '盘点修正',
}

export const INVENTORY_SOURCE_LABELS: Record<InventorySourceType, string> = {
  daily_intake: '点货入库',
  manual_outbound: '手动出库',
  manual_adjust: '盘点修正',
}
