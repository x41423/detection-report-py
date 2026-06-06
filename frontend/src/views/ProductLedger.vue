<template>
  <div class="page-shell page page-shell--full">
    <PageHero title="商品台账" subtitle="按商品维度查看出入库流水，支持日期和商品筛选。" />
    <el-card shadow="never" class="fcard">
      <div class="frow wrap">
        <el-input-number v-model="productId" :min="0" size="small" placeholder="商品ID" controls-position="right" />
        <el-date-picker v-model="range" type="daterange" value-format="YYYY-MM-DD" :shortcuts="shortcuts" size="small" />
        <el-button type="primary" size="small" @click="load">查询</el-button>
        <el-button size="small" @click="loadSummary">汇总</el-button>
      </div>
    </el-card>
    <!-- KPI cards -->
    <div class="kpi-row" v-if="summary">
      <div class="kpi"><span class="kpi-label">入库量</span><span class="kpi-val in">{{ summary.in_qty.toFixed(1) }}</span></div>
      <div class="kpi"><span class="kpi-label">出库量</span><span class="kpi-val out">{{ Math.abs(summary.out_qty).toFixed(1) }}</span></div>
      <div class="kpi"><span class="kpi-label">净库存</span><span class="kpi-val" :class="summary.net_qty>=0?'in':'out'">{{ summary.net_qty.toFixed(1) }}</span></div>
      <div class="kpi"><span class="kpi-label">交易笔数</span><span class="kpi-val">{{ summary.transaction_count }}</span></div>
    </div>
    <!-- Ledger table -->
    <el-card shadow="never" class="fcard">
      <div class="trow"><span class="snote">共 {{ total }} 条记录</span></div>
      <el-table :data="items" stripe size="small" style="margin-top:8px">
        <el-table-column prop="business_date" label="日期" width="110" />
        <el-table-column prop="display_name" label="商品名称" min-width="140" />
        <el-table-column label="方向" width="70"><template #default="{row}">
          <el-tag :type="row.direction==='in'?'success':'danger'" size="small">{{row.direction==='in'?'入库':'出库'}}</el-tag></template></el-table-column>
        <el-table-column label="数量" width="90"><template #default="{row}"><span :style="{color:row.direction==='in'?'var(--el-color-success)':'var(--el-color-danger)'}">{{ row.quantity_delta }}</span></template></el-table-column>
        <el-table-column prop="unit_name" label="单位" width="60" />
        <el-table-column prop="source_type" label="来源" width="90" />
        <el-table-column prop="note" label="备注" min-width="120" show-overflow-tooltip />
      </el-table>
      <el-pagination v-if="total>50" v-model:current-page="page" :page-size="50" :total="total"
        layout="prev,next" small style="margin-top:12px;justify-content:flex-end" @current-change="loadPage" />
    </el-card>
  </div>
</template>
<script setup lang="ts">
import {ref,onMounted} from 'vue';import PageHero from '../components/PageHero.vue'
import {getLedger,getLedgerSummary,type LedgerEntry,type LedgerSummary} from '../api/product-ledger'
const shortcuts=[{text:'本周',value:()=>{const e=new Date();const s=new Date(e);s.setDate(e.getDate()-e.getDay()+1);return[s,e]}},{text:'本月',value:()=>{const e=new Date();const s=new Date(e.getFullYear(),e.getMonth(),1);return[s,e]}},{text:'上月',value:()=>{const e=new Date();const s=new Date(e.getFullYear(),e.getMonth()-1,1);const d=new Date(e.getFullYear(),e.getMonth(),0);return[s,d]}}]
const items=ref<LedgerEntry[]>([]);const summary=ref<LedgerSummary|null>(null)
const productId=ref(0);const range=ref<[string,string]|null>(null)
const total=ref(0);const page=ref(1)
async function load(){page.value=1;await loadPage()}
async function loadPage(){
  const[df,dt]=range.value||['','']
  const{data}=await getLedger({product_id:productId.value,date_from:df,date_to:dt,limit:50,offset:(page.value-1)*50})
  items.value=(data as any).items??[];total.value=(data as any).total??0
}
async function loadSummary(){
  const[df,dt]=range.value||['','']
  const{data}=await getLedgerSummary({product_id:productId.value,date_from:df,date_to:dt})
  summary.value=(data as any).summary
}
onMounted(load)
</script>
<style scoped>
.fcard{margin-bottom:12px}.trow{display:flex;justify-content:space-between;align-items:center}.snote{color:var(--el-text-color-secondary);font-size:13px}
.frow{display:flex;align-items:center;gap:10px}.wrap{flex-wrap:wrap}
.kpi-row{display:flex;gap:12px;margin-bottom:12px;flex-wrap:wrap}
.kpi{flex:1;min-width:120px;background:var(--el-bg-color-page);border-radius:8px;padding:12px 16px;display:flex;flex-direction:column;gap:4px}
.kpi-label{font-size:12px;color:var(--el-text-color-secondary)}.kpi-val{font-size:22px;font-weight:700}
.kpi-val.in{color:var(--el-color-success)}.kpi-val.out{color:var(--el-color-danger)}
</style>
