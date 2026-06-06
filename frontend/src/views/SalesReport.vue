<template>
  <div class="page-shell report-page page-shell--full">
    <PageHero title="销售总表" subtitle="按日期范围查看所有订单明细，支持导出 CSV。" />

    <el-card shadow="never" class="filter-card">
      <div class="filter-row">
        <el-date-picker v-model="dateRange" type="daterange" range-separator="~"
          start-placeholder="开始" end-placeholder="结束" value-format="YYYY-MM-DD" style="width:260px" />
        <el-button type="primary" @click="load">查询</el-button>
        <el-button @click="resetDates">近30天</el-button>
        <span class="soft-note">共 {{ total }} 条</span>
        <el-button type="success" @click="exportCsv" style="margin-left:auto">导出 CSV</el-button>
      </div>
    </el-card>

    <el-card shadow="never">
      <el-table :data="items" v-loading="loading" stripe size="small" max-height="600">
        <el-table-column prop="order_no" label="订单号" width="170" />
        <el-table-column prop="order_date" label="日期" width="110" />
        <el-table-column prop="merchant_name" label="商户" min-width="130" />
        <el-table-column prop="order_amount" label="下单金额" width="110" align="right" />
        <el-table-column prop="sales_amount_incl_freight" label="销售额(含运费)" width="130" align="right" />
        <el-table-column prop="freight" label="运费" width="80" align="right" />
        <el-table-column prop="discount_amount" label="优惠" width="90" align="right" />
        <el-table-column prop="order_status" label="状态" width="90">
          <template #default="{ row }">
            <el-tag size="small">{{ row.order_status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="payment_status" label="支付" width="90" />
      </el-table>
      <div class="pagination-row">
        <el-pagination v-model:current-page="page" v-model:page-size="pageSize"
          :total="total" :page-sizes="[50,100,200]" layout="total,sizes,prev,pager,next" @change="load" />
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import PageHero from '../components/PageHero.vue'
import api from '../api/client'

interface OrderRow { order_no: string; order_date: string; merchant_name: string; order_amount: number; sales_amount_incl_freight: number; freight: number; discount_amount: number; order_status: string; payment_status: string }

const items = ref<OrderRow[]>([])
const total = ref(0)
const loading = ref(false)
const page = ref(1)
const pageSize = ref(100)
const dateRange = ref<[string, string] | null>(null)

async function load() {
  loading.value = true
  try {
    const [df, dt] = dateRange.value || defaultDates()
    const { data } = await api.get('/api/dashboard/sales-report/orders', {
      params: { date_from: df, date_to: dt, limit: pageSize.value, offset: (page.value - 1) * pageSize.value }
    })
    items.value = (data as any).items ?? []
    total.value = (data as any).total ?? 0
  } finally { loading.value = false }
}

function resetDates() { dateRange.value = null; page.value = 1; load() }
function defaultDates(): [string, string] {
  const e = new Date(); const s = new Date(); s.setDate(s.getDate() - 30)
  return [s.toISOString().slice(0,10), e.toISOString().slice(0,10)]
}

function exportCsv() {
  const [df, dt] = dateRange.value || defaultDates()
  window.open(`/api/dashboard/sales-report/export?date_from=${df}&date_to=${dt}`, '_blank')
}

onMounted(load)
</script>

<style scoped>
.filter-row { display: flex; align-items: center; gap: 12px; }
.filter-card { margin-bottom: 12px; }
.pagination-row { margin-top: 12px; display: flex; justify-content: flex-end; }
.soft-note { color: var(--el-text-color-secondary); font-size: 13px; }
</style>
