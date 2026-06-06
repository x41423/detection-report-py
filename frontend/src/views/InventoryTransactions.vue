<template>
  <div class="page-shell transaction-page page-shell--full">
    <PageHero title="库存流水明细" subtitle="按商品名、日期、方向筛选库存变动记录，支持追溯检测批次。" />

    <el-card shadow="never" class="filter-card">
      <div class="filter-row">
        <el-input
          v-model="searchText"
          placeholder="搜索商品名称"
          clearable
          style="width: 200px"
          @clear="load"
          @keyup.enter="load"
        />
        <el-select v-model="filterDirection" placeholder="全部方向" clearable style="width: 130px" @change="load">
          <el-option label="入库" value="in" />
          <el-option label="出库" value="out" />
          <el-option label="盘点调整" value="adjustment" />
        </el-select>
        <el-select v-model="filterSource" placeholder="全部来源" clearable style="width: 150px" @change="load">
          <el-option label="点货入库" value="daily_intake" />
          <el-option label="采购入库" value="purchase_in" />
          <el-option label="销售出库" value="order_outbound" />
          <el-option label="退货入库" value="purchase_return" />
          <el-option label="盘点调整" value="stock_check" />
          <el-option label="手动调整" value="manual" />
        </el-select>
        <el-date-picker
          v-model="dateRange"
          type="daterange"
          range-separator="~"
          start-placeholder="日期起"
          end-placeholder="日期止"
          value-format="YYYY-MM-DD"
          style="width: 260px"
          @change="load"
        />
        <el-button type="primary" @click="load">搜索</el-button>
        <el-button @click="resetFilters">重置</el-button>
      </div>
    </el-card>

    <el-card shadow="never">
      <div class="toolbar-row">
        <span class="soft-note">共 {{ total }} 条记录</span>
      </div>
      <el-table :data="items" v-loading="loading" stripe size="small" style="margin-top: 8px">
        <el-table-column prop="business_date" label="日期" width="110" sortable />
        <el-table-column prop="display_name" label="商品名称" min-width="140" show-overflow-tooltip />
        <el-table-column label="方向" width="90">
          <template #default="{ row }">
            <el-tag :type="directionTag(row.direction)" size="small">{{ directionLabel(row.direction) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="quantity_delta" label="变动量" width="100" align="right">
          <template #default="{ row }">
            <span :class="row.direction === 'in' ? 'text-green' : 'text-red'">
              {{ row.quantity_delta >= 0 ? '+' : '' }}{{ row.quantity_delta }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="unit_name" label="单位" width="70" align="center" />
        <el-table-column label="来源" width="110">
          <template #default="{ row }">
            <el-tag type="info" size="small">{{ sourceLabel(row.source_type) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="note" label="备注" min-width="160" show-overflow-tooltip />
        <el-table-column prop="created_at" label="操作时间" width="160" />
      </el-table>
      <div class="pagination-row">
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          :total="total"
          :page-sizes="[20, 50, 100]"
          layout="total, sizes, prev, pager, next"
          @change="load"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import PageHero from '../components/PageHero.vue'
import { getInventoryTransactions, type InventoryTransaction } from '../api/inventory'

const items = ref<InventoryTransaction[]>([])
const total = ref(0)
const loading = ref(false)
const page = ref(1)
const pageSize = ref(50)

const searchText = ref('')
const filterDirection = ref('')
const filterSource = ref('')
const dateRange = ref<[string, string] | null>(null)

async function load() {
  loading.value = true
  try {
    const { data } = await getInventoryTransactions({
      search: searchText.value || undefined,
      direction: filterDirection.value || undefined,
      source_type: filterSource.value || undefined,
      date_from: dateRange.value?.[0] || undefined,
      date_to: dateRange.value?.[1] || undefined,
      limit: pageSize.value,
      offset: (page.value - 1) * pageSize.value,
    })
    items.value = data.items
    total.value = data.total
  } finally {
    loading.value = false
  }
}

function resetFilters() {
  searchText.value = ''
  filterDirection.value = ''
  filterSource.value = ''
  dateRange.value = null
  page.value = 1
  load()
}

function directionTag(d: string) { return d === 'in' ? 'success' : d === 'out' ? 'danger' : 'warning' }
function directionLabel(d: string) { return d === 'in' ? '入库' : d === 'out' ? '出库' : '调整' }

function sourceLabel(s: string) {
  const map: Record<string, string> = {
    daily_intake: '点货入库', purchase_in: '采购入库', order_outbound: '销售出库',
    purchase_return: '退货入库', stock_check: '盘点调整', manual: '手动调整',
  }
  return map[s] || s
}

onMounted(load)
</script>

<style scoped>
.filter-row { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
.toolbar-row { display: flex; align-items: center; justify-content: space-between; }
.pagination-row { margin-top: 12px; display: flex; justify-content: flex-end; }
.filter-card { margin-bottom: 12px; }
.soft-note { color: var(--el-text-color-secondary); font-size: 13px; }
.text-green { color: var(--el-color-success); font-weight: 500; }
.text-red { color: var(--el-color-danger); font-weight: 500; }
</style>
