<template>
  <div class="page-shell">
    <PageHeader eyebrow="库存管理" title="入库 / 出库 / 盘点" tone="green">
      <template #actions>
        <div class="action-cluster">
          <el-button @click="workflow.downloadBalanceExport()" :loading="workflow.exportingBalances.value">
            导出 CSV
          </el-button>
          <el-button @click="workflow.refreshAll()">
            刷新
          </el-button>
        </div>
      </template>

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
          <div class="hero-metric">
            <span class="hero-metric__label">低库存</span>
            <span class="hero-metric__value">{{ workflow.lowStockCount.value }}</span>
            <span class="hero-metric__note">≤ 阈值 {{ workflow.lowStockThreshold.value }}</span>
          </div>
          <div class="hero-metric">
            <span class="hero-metric__label">负库存</span>
            <span class="hero-metric__value">{{ workflow.negativeStockCount.value }}</span>
            <span class="hero-metric__note">可能存在出库超量或盘点偏差</span>
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
          <div class="panel-heading__eyebrow">设置</div>
          <h2 class="panel-heading__title">低库存阈值</h2>
          <p class="panel-heading__description">
            当可用库存 ≤ 此阈值时，在库表格会高亮提示。点击「保存」生效。
          </p>
        </div>
      </div>
      <div class="action-cluster">
        <el-input-number
          v-model="workflow.lowStockThreshold.value"
          :min="0"
          :step="1"
          size="large"
          class="threshold-input"
        />
        <el-button
          type="primary"
          :loading="workflow.savingThreshold.value"
          @click="workflow.saveLowStockThreshold()"
        >
          保存阈值
        </el-button>
      </div>
    </el-card>

    <div class="field-grid two-up">
      <el-card shadow="never" class="panel-card">
        <div class="panel-heading">
          <div>
            <div class="panel-heading__eyebrow">出库</div>
            <h2 class="panel-heading__title">手动商品出库</h2>
          </div>
        </div>

        <el-form :model="workflow.outboundDraft" label-position="top" class="field-grid">
          <el-form-item label="商品名称">
            <el-input v-model="workflow.outboundDraft.name" placeholder="例如：白菜" />
          </el-form-item>
          <div class="field-grid two-up">
            <el-form-item label="出库数量">
              <el-input-number
                v-model="workflow.outboundDraft.quantity"
                :min="0"
                :step="1"
                :precision="1"
              />
            </el-form-item>
            <el-form-item label="单位">
              <el-select v-model="workflow.outboundDraft.unit">
                <el-option
                  v-for="unit in UNITS"
                  :key="unit"
                  :label="unit"
                  :value="unit"
                />
              </el-select>
            </el-form-item>
          </div>
          <el-form-item label="备注">
            <el-input v-model="workflow.outboundDraft.note" placeholder="选填" />
          </el-form-item>
          <el-button
            type="primary"
            :loading="workflow.submittingOutbound.value"
            @click="workflow.submitOutbound()"
          >
            提交出库
          </el-button>
        </el-form>
      </el-card>

      <el-card shadow="never" class="panel-card">
        <div class="panel-heading">
          <div>
            <div class="panel-heading__eyebrow">盘点</div>
            <h2 class="panel-heading__title">盘点修正</h2>
          </div>
        </div>

        <el-form :model="workflow.adjustmentDraft" label-position="top" class="field-grid">
          <el-form-item label="商品名称">
            <el-input v-model="workflow.adjustmentDraft.name" placeholder="例如：白菜" />
          </el-form-item>
          <div class="field-grid two-up">
            <el-form-item label="目标库存">
              <el-input-number
                v-model="workflow.adjustmentDraft.targetQuantity"
                :min="0"
                :step="1"
                :precision="1"
              />
            </el-form-item>
            <el-form-item label="单位">
              <el-select v-model="workflow.adjustmentDraft.unit">
                <el-option
                  v-for="unit in UNITS"
                  :key="unit"
                  :label="unit"
                  :value="unit"
                />
              </el-select>
            </el-form-item>
          </div>
          <el-form-item label="备注">
            <el-input v-model="workflow.adjustmentDraft.note" placeholder="选填" />
          </el-form-item>
          <el-button
            type="primary"
            :loading="workflow.submittingAdjustment.value"
            @click="workflow.submitAdjustment()"
          >
            提交盘点修正
          </el-button>
        </el-form>
      </el-card>
    </div>

    <el-card shadow="never" class="panel-card">
      <div class="panel-heading">
        <div>
          <div class="panel-heading__eyebrow">在库一览</div>
          <h2 class="panel-heading__title">库存余额</h2>
        </div>
        <div class="action-cluster">
          <el-input
            v-model="workflow.balanceSearch.value"
            placeholder="搜索商品名…"
            clearable
            :prefix-icon="Search"
            class="panel-search"
            @clear="workflow.balanceCurrentPage.value = 1; workflow.loadBalances()"
            @keyup.enter="workflow.balanceCurrentPage.value = 1; workflow.loadBalances()"
          />
          <el-button @click="workflow.balanceCurrentPage.value = 1; workflow.loadBalances()">搜索</el-button>
        </div>
      </div>

      <div class="balance-toolbar">
        <el-radio-group
          v-model="workflow.balanceStatusFilter.value"
          size="small"
          @change="workflow.onBalanceStatusChange"
        >
          <el-radio-button value="all">全部 ({{ workflow.balances.value.length }})</el-radio-button>
          <el-radio-button value="low_stock">低库存 ({{ workflow.lowStockCount.value }})</el-radio-button>
          <el-radio-button value="negative">负库存 ({{ workflow.negativeStockCount.value }})</el-radio-button>
        </el-radio-group>
      </div>

      <el-table
        :data="workflow.pagedBalances.value"
        v-loading="workflow.loadingBalances.value"
        :row-class-name="workflow.getBalanceRowClassName"
        empty-text="当前没有库存数据"
        highlight-current-row
        @row-click="workflow.prefillFromBalance"
        @sort-change="workflow.onBalanceSortChange"
      >
        <el-table-column prop="display_name" label="商品名称" min-width="140" sortable="custom" />
        <el-table-column prop="available_quantity" label="可用库存" width="120" sortable="custom">
          <template #default="{ row }">
            <span :class="{ 'balance--low': row.available_quantity > 0 && row.available_quantity <= Number(workflow.lowStockThreshold.value || 0), 'balance--negative': row.available_quantity < 0 }">
              {{ row.available_quantity }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="unit_name" label="单位" width="80" />
        <el-table-column prop="last_business_date" label="最近业务日" width="140" sortable="custom" />
        <el-table-column prop="transaction_count" label="流水数" width="100" sortable="custom" />
        <el-table-column label="操作" width="100" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link size="small" @click.stop="workflow.prefillFromBalance(row)">
              填入表单
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        v-model:current-page="workflow.balanceCurrentPage.value"
        v-model:page-size="workflow.balancePageSize.value"
        :page-sizes="[10, 20, 50]"
        :total="workflow.filteredBalances.value.length"
        layout="total, sizes, prev, pager, next, jumper"
        class="balance-pagination"
        @current-change="workflow.onBalancePageChange"
        @size-change="workflow.onBalanceSizeChange"
      />
    </el-card>

    <el-card shadow="never" class="panel-card">
      <div class="panel-heading">
        <div>
          <div class="panel-heading__eyebrow">流水</div>
          <h2 class="panel-heading__title">最近交易</h2>
        </div>
        <div class="action-cluster">
          <el-select
            v-model="workflow.transactionSourceFilter.value"
            class="panel-filter"
            @change="workflow.transactionCurrentPage.value = 1; workflow.loadTransactions()"
          >
            <el-option label="全部来源" value="all" />
            <el-option label="点货入库" value="daily_intake" />
            <el-option label="手动出库" value="manual_outbound" />
            <el-option label="盘点修正" value="manual_adjust" />
          </el-select>
          <el-input
            v-model="workflow.transactionSearch.value"
            placeholder="搜索…"
            clearable
            :prefix-icon="Search"
            class="panel-search"
            @clear="workflow.transactionCurrentPage.value = 1; workflow.loadTransactions()"
            @keyup.enter="workflow.transactionCurrentPage.value = 1; workflow.loadTransactions()"
          />
          <el-button @click="workflow.transactionCurrentPage.value = 1; workflow.loadTransactions()">搜索</el-button>
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
          <el-table-column label="操作" width="140" fixed="right">
            <template #default="{ row }">
              <template v-if="row.source_type !== 'daily_intake'">
                <el-button
                  type="primary"
                  link
                  size="small"
                  @click="workflow.openEditTransaction(row)"
                >
                  编辑
                </el-button>
                <el-button
                  type="danger"
                  link
                  size="small"
                  :loading="workflow.deletingTransactionId.value === row.id"
                  @click="workflow.removeManualTransaction(row)"
                >
                  删除
                </el-button>
              </template>
            </template>
          </el-table-column>
        </el-table>

        <el-pagination
          v-model:current-page="workflow.transactionCurrentPage.value"
          v-model:page-size="workflow.transactionPageSize.value"
          :page-sizes="[10, 20, 50]"
          :total="workflow.transactionTotalCount.value"
          layout="total, sizes, prev, pager, next, jumper"
          class="transaction-pagination"
          @current-change="workflow.onTransactionPageChange"
          @size-change="workflow.onTransactionSizeChange"
        />
      </el-card>

    <el-dialog
      v-model="workflow.editDialogVisible.value"
      title="编辑库存流水"
      width="min(520px, calc(100vw - 24px))"
      append-to-body
      :close-on-click-modal="false"
    >
      <el-form :model="workflow.editDraft" label-position="top" class="field-grid">
        <el-form-item label="业务日期">
          <el-date-picker
            v-model="workflow.editDraft.businessDate"
            type="date"
            value-format="YYYY-MM-DD"
            :clearable="false"
          />
        </el-form-item>
        <el-form-item label="商品名称">
          <el-input v-model="workflow.editDraft.name" placeholder="例如：白菜" />
        </el-form-item>
        <el-form-item label="单位">
          <el-select v-model="workflow.editDraft.unit">
            <el-option
              v-for="unit in UNITS"
              :key="unit"
              :label="unit"
              :value="unit"
            />
          </el-select>
        </el-form-item>
        <el-form-item v-if="workflow.editDraft.direction === 'OUT'" label="出库数量">
          <el-input-number
            v-model="workflow.editDraft.quantity"
            :min="0"
            :step="1"
            :precision="1"
          />
        </el-form-item>
        <el-form-item v-else label="目标库存">
          <el-input-number
            v-model="workflow.editDraft.targetQuantity"
            :min="0"
            :step="1"
            :precision="1"
          />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="workflow.editDraft.note" placeholder="选填" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="workflow.editDialogVisible.value = false">取消</el-button>
        <el-button type="primary" :loading="workflow.editSaving.value" @click="workflow.saveEditTransaction()">
          保存
        </el-button>
      </template>
    </el-dialog>

    <StatusLog ref="statusLogRef" />
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { Search } from '@element-plus/icons-vue'
import PageHeader from '../components/PageHeader.vue'
import StatusLog from '../components/StatusLog.vue'
import { useInventoryWorkflow } from '../features/inventory/composables/useInventoryWorkflow'
import { DAILY_INTAKE_UNITS } from '../features/daily-intake/types'
import {
  INVENTORY_DIRECTION_LABELS as directionLabels,
  INVENTORY_SOURCE_LABELS as sourceLabels,
  type InventoryDirection,
  type InventorySourceType,
} from '../features/inventory/types'

const UNITS = DAILY_INTAKE_UNITS as readonly string[]

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

<style scoped>
.threshold-input {
  width: 140px;
}

.panel-search {
  width: 200px;
}

.panel-filter {
  width: 140px;
}

.balance--low {
  color: var(--color-warning);
  font-weight: 600;
}

.balance--negative {
  color: var(--color-danger);
  font-weight: 600;
}

.balance-toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 16px;
  align-items: center;
}

.balance-pagination {
  margin-top: 16px;
  justify-content: flex-end;
}

.transaction-pagination {
  margin-top: 16px;
  justify-content: flex-end;
}
</style>
