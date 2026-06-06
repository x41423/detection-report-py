<template>
  <div class="page-shell dashboard-page">
    <PageHero eyebrow="数据报表" title="数据驾驶舱" description="跨模块经营概览：供应商、采购、订单、库存、结算一站汇总。" tone="sun" />

    <div v-loading="loading">
      <el-row :gutter="16" class="dashboard-kpi-row">
        <el-col :span="4" v-for="kpi in kpis" :key="kpi.label">
          <el-card shadow="never" class="kpi-card">
            <div class="kpi-label">{{ kpi.label }}</div>
            <div class="kpi-value">{{ kpi.value }}</div>
          </el-card>
        </el-col>
      </el-row>

      <el-row :gutter="16" style="margin-top:16px">
        <el-col :span="12">
          <el-card shadow="never"><h3>采购趋势（近6月）</h3>
            <el-table :data="dashboard.purchase_trend" size="small">
              <el-table-column prop="period" label="月份" /><el-table-column prop="amount" label="金额" /><el-table-column prop="count" label="单数" />
            </el-table>
          </el-card>
        </el-col>
        <el-col :span="12">
          <el-card shadow="never"><h3>订单趋势（近6月）</h3>
            <el-table :data="dashboard.order_trend" size="small">
              <el-table-column prop="period" label="月份" /><el-table-column prop="amount" label="金额" /><el-table-column prop="count" label="单数" />
            </el-table>
          </el-card>
        </el-col>
      </el-row>

      <el-card shadow="never" style="margin-top:16px"><h3>Top 供应商</h3>
        <el-table :data="dashboard.top_suppliers" size="small">
          <el-table-column prop="supplier_name" label="供应商" /><el-table-column prop="total_amount" label="采购总额" /><el-table-column prop="order_count" label="入库单数" />
        </el-table>
      </el-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { getDashboard, type Dashboard } from '../api/dashboard'

const loading = ref(false)
const dashboard = ref<Dashboard>({ success: true, overview: { total_suppliers:0, active_suppliers:0, purchase_this_month:0, orders_this_month:0, pending_settlements:0, low_stock_items:0 }, purchase_trend: [], order_trend: [], top_suppliers: [] })

const kpis = computed(() => {
  const o = dashboard.value.overview
  return [
    { label: '供应商', value: `${o.active_suppliers}/${o.total_suppliers}` },
    { label: '本月采购', value: `¥${o.purchase_this_month.toLocaleString()}` },
    { label: '本月订单', value: `¥${o.orders_this_month.toLocaleString()}` },
    { label: '待结算', value: o.pending_settlements },
    { label: '低库存', value: o.low_stock_items },
  ]
})

async function load() {
  loading.value = true
  try { const { data } = await getDashboard(); dashboard.value = data } finally { loading.value = false }
}

onMounted(load)
</script>

<style scoped>
.dashboard-kpi-row { margin-bottom: 0; }
.kpi-card { text-align: center; }
.kpi-label { font-size: 12px; color: #909399; }
.kpi-value { font-size: 24px; font-weight: 700; margin-top: 4px; }
</style>
