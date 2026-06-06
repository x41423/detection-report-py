<template>
  <div class="page-shell sales-page page-shell--full">
    <PageHero title="商品销售分析" subtitle="按商品和分类维度分析销售额、销量和订单数。" />

    <!-- Date filter -->
    <el-card shadow="never" class="filter-card">
      <div class="filter-row">
        <el-date-picker
          v-model="dateRange"
          type="daterange"
          range-separator="~"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          value-format="YYYY-MM-DD"
          style="width: 260px"
        />
        <el-button type="primary" @click="loadAll">搜索</el-button>
        <el-button @click="resetDates">近30天</el-button>
      </div>
    </el-card>

    <!-- KPI Cards -->
    <div class="kpi-row">
      <div class="kpi-card">
        <div class="kpi-value">{{ summary.total_sales?.toFixed(0) || 0 }}</div>
        <div class="kpi-label">销售额(元)</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-value">{{ summary.order_count || 0 }}</div>
        <div class="kpi-label">订单数</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-value">{{ summary.merchant_count || 0 }}</div>
        <div class="kpi-label">下单商户</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-value">{{ (summary.total_sales / Math.max(summary.order_count, 1)).toFixed(0) }}</div>
        <div class="kpi-label">客单价(元)</div>
      </div>
    </div>

    <el-row :gutter="16">
      <!-- Top Products -->
      <el-col :span="14">
        <el-card shadow="never">
          <template #header><span class="card-title">商品销售额排行 Top {{ topProducts.length }}</span></template>
          <div v-if="topProducts.length" class="bar-list">
            <div v-for="(p, i) in topProducts" :key="i" class="bar-row">
              <span class="bar-rank">{{ i + 1 }}</span>
              <span class="bar-name">{{ p.product_name }}</span>
              <span class="bar-track">
                <span class="bar-fill" :style="{ width: barPct(p.total_amount, topMax) }" />
              </span>
              <span class="bar-val">{{ p.total_amount?.toFixed(0) }}</span>
            </div>
          </div>
          <div v-else class="empty-hint">暂无数据</div>
        </el-card>
      </el-col>

      <!-- By Category -->
      <el-col :span="10">
        <el-card shadow="never">
          <template #header><span class="card-title">分类销售额</span></template>
          <div v-if="categories.length" class="bar-list">
            <div v-for="(c, i) in categories" :key="i" class="bar-row">
              <span class="bar-name" style="width:90px">{{ c.category }}</span>
              <span class="bar-track">
                <span class="bar-fill cat-fill" :style="{ width: barPct(c.total_amount, catMax) }" />
              </span>
              <span class="bar-val">{{ c.total_amount?.toFixed(0) }}</span>
            </div>
          </div>
          <div v-else class="empty-hint">暂无数据</div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import PageHero from '../components/PageHero.vue'
import {
  getProductSalesSummary, getProductSalesTop, getProductSalesByCategory,
  type SalesSummary, type TopProduct, type CategorySales,
} from '../api/product-sales'

const summary = ref<SalesSummary>({ order_count: 0, total_amount: 0, total_sales: 0, merchant_count: 0 })
const topProducts = ref<TopProduct[]>([])
const categories = ref<CategorySales[]>([])
const dateRange = ref<[string, string] | null>(null)

const topMax = ref(1)
const catMax = ref(1)

function barPct(v: number, max: number) { return max > 0 ? `${(v / max) * 100}%` : '0%' }

function defaultDates(): [string, string] {
  const end = new Date()
  const start = new Date(); start.setDate(start.getDate() - 30)
  return [start.toISOString().slice(0, 10), end.toISOString().slice(0, 10)]
}

async function loadAll() {
  const [df, dt] = dateRange.value || defaultDates()
  const params = { date_from: df, date_to: dt }

  const [s, t, c] = await Promise.all([
    getProductSalesSummary(params),
    getProductSalesTop({ ...params, limit: 20 }),
    getProductSalesByCategory(params),
  ])
  summary.value = (s.data as any).data ?? s.data
  topProducts.value = (t.data as any).items ?? []
  categories.value = (c.data as any).items ?? []
  topMax.value = Math.max(...topProducts.value.map(p => p.total_amount), 1)
  catMax.value = Math.max(...categories.value.map(c => c.total_amount), 1)
}

function resetDates() {
  dateRange.value = null
  loadAll()
}

onMounted(loadAll)
</script>

<style scoped>
.filter-row { display: flex; align-items: center; gap: 12px; margin-bottom: 0; }
.filter-card { margin-bottom: 16px; }
.kpi-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 16px; }
.kpi-card {
  background: var(--el-fill-color-light); border-radius: 8px;
  padding: 16px; text-align: center;
}
.kpi-value { font-size: 28px; font-weight: 700; color: var(--el-color-primary); }
.kpi-label { font-size: 13px; color: var(--el-text-color-secondary); margin-top: 4px; }
.card-title { font-weight: 600; }
.bar-list { max-height: 520px; overflow-y: auto; }
.bar-row {
  display: flex; align-items: center; gap: 8px; padding: 4px 0;
  border-bottom: 1px solid var(--el-border-color-lighter);
}
.bar-rank { width: 24px; text-align: center; font-weight: 600; color: var(--el-text-color-secondary); }
.bar-name { width: 130px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 13px; }
.bar-track {
  flex: 1; height: 18px; background: var(--el-fill-color);
  border-radius: 4px; overflow: hidden;
}
.bar-fill {
  height: 100%; background: var(--el-color-primary); border-radius: 4px;
  min-width: 2px; transition: width 0.3s;
}
.cat-fill { background: var(--el-color-success); }
.bar-val { width: 80px; text-align: right; font-size: 13px; font-weight: 500; color: var(--el-text-color-regular); }
.empty-hint { text-align: center; color: var(--el-text-color-secondary); padding: 40px 0; }
</style>
