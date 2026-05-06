<template>
  <div class="page-shell">
    <PageHeader eyebrow="库存管理" title="入库 / 出库 / 盘点" tone="green">
      <template #aside>
        <div class="hero-metric-grid">
          <div class="hero-metric">
            <span class="hero-metric__label">商品数</span>
            <span class="hero-metric__value">{{ workflow.balances.value.length }}</span>
            <span class="hero-metric__note">当前在库 SKU 数量</span>
          </div>
          <div class="hero-metric">
            <span class="hero-metric__label">最近流水</span>
            <span class="hero-metric__value">{{ workflow.transactions.value.length }}</span>
            <span class="hero-metric__note">读取到的库存交易</span>
          </div>
        </div>
      </template>
    </PageHeader>

    <el-alert
      type="warning"
      :closable="false"
      title="本页面正在重建中"
      description="原 Inventory.vue 文件在最近一次同步中被清空。底层 useInventoryWorkflow 与后端 API 已完整恢复，可基于此重新搭建出库 / 盘点 / 异常提示等 UI。"
    />

    <el-card shadow="never" class="panel-card">
      <div class="panel-heading">
        <div>
          <div class="panel-heading__eyebrow">在库一览</div>
          <h2 class="panel-heading__title">库存余额（最小骨架）</h2>
        </div>
      </div>
      <el-table
        :data="workflow.balances.value"
        v-loading="workflow.loadingBalances.value"
        empty-text="当前没有库存数据"
      >
        <el-table-column prop="display_name" label="商品名称" min-width="140" />
        <el-table-column prop="available_quantity" label="可用库存" width="120" />
        <el-table-column prop="unit_name" label="单位" width="80" />
        <el-table-column prop="last_business_date" label="最近业务日" width="140" />
        <el-table-column prop="transaction_count" label="流水数" width="100" />
      </el-table>
    </el-card>

    <el-card shadow="never" class="panel-card">
      <div class="panel-heading">
        <div>
          <div class="panel-heading__eyebrow">流水</div>
          <h2 class="panel-heading__title">最近交易</h2>
        </div>
      </div>
      <el-table
        :data="workflow.transactions.value"
        v-loading="workflow.loadingTransactions.value"
        empty-text="还没有流水记录"
      >
        <el-table-column prop="business_date" label="业务日" width="120" />
        <el-table-column prop="display_name" label="商品" min-width="140" />
        <el-table-column prop="direction" label="方向" width="100">
          <template #default="{ row }">
            <el-tag size="small" :type="directionTagType(row.direction)">
              {{ directionLabel(row.direction) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="quantity_delta" label="数量变化" width="120" />
        <el-table-column prop="unit_name" label="单位" width="80" />
        <el-table-column prop="source_type" label="来源" width="120">
          <template #default="{ row }">{{ sourceLabel(row.source_type) }}</template>
        </el-table-column>
        <el-table-column prop="note" label="备注" min-width="120" />
      </el-table>
    </el-card>

    <StatusLog ref="statusLogRef" />
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import PageHeader from '../components/PageHeader.vue'
import StatusLog from '../components/StatusLog.vue'
import { useInventoryWorkflow } from '../features/inventory/composables/useInventoryWorkflow'
import {
  INVENTORY_DIRECTION_LABELS as directionLabels,
  INVENTORY_SOURCE_LABELS as sourceLabels,
  type InventoryDirection,
  type InventorySourceType,
} from '../features/inventory/types'

const statusLogRef = ref<InstanceType<typeof StatusLog>>()
const workflow = useInventoryWorkflow(statusLogRef)

function directionTagType(direction: InventoryDirection): 'success' | 'warning' | 'info' {
  if (direction === 'IN') return 'success'
  if (direction === 'OUT') return 'warning'
  return 'info'
}

function directionLabel(direction: string): string {
  return direction in directionLabels ? directionLabels[direction as InventoryDirection] : direction
}

function sourceLabel(sourceType: string): string {
  return sourceType in sourceLabels ? sourceLabels[sourceType as InventorySourceType] : sourceType
}
</script>
