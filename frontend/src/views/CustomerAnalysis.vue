<template>
  <div class="page-shell page page-shell--full">
    <PageHero title="客户购买分析" subtitle="客户销售额排行、客单价与复购率分析。" />
    <el-card shadow="never" class="fcard"><div class="frow">
      <el-date-picker v-model="range" type="daterange" range-separator="~" value-format="YYYY-MM-DD" style="width:260px" />
      <el-button type="primary" @click="load">查询</el-button>
      <span class="snote">客户: {{ s.customer_count }} | 订单: {{ s.order_count }} | 总额: {{ s.total_amount?.toFixed(0) }}</span>
    </div></el-card>
    <el-card shadow="never">
      <el-table :data="items" stripe size="small" max-height="550">
        <el-table-column type="index" width="50" />
        <el-table-column prop="merchant_name" label="商户" min-width="150" />
        <el-table-column prop="order_count" label="订单数" width="90" align="center" />
        <el-table-column prop="total_amount" label="消费总额" width="120" align="right" />
        <el-table-column prop="avg_amount" label="客单价" width="100" align="right" />
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'; import PageHero from '../components/PageHero.vue'; import api from '../api/client'
const items=ref<any[]>([]); const s=ref<any>({}); const range=ref<[string,string]|null>(null)
async function load(){const[p,q]=range.value||['',''];const r=await Promise.all([api.get('/api/dashboard/customer/summary',{params:{date_from:p,date_to:q}}),api.get('/api/dashboard/customer/ranking',{params:{date_from:p,date_to:q,limit:30}})]);
s.value=(r[0].data as any).data??{};items.value=(r[1].data as any).items??[]}
onMounted(load)
</script>

<style scoped>
.fcard{margin-bottom:12px}.frow{display:flex;align-items:center;gap:12px}.snote{color:var(--el-text-color-secondary);font-size:13px;margin-left:auto}
</style>
