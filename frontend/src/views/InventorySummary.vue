<template>
  <div class="page-shell page page-shell--full">
    <PageHero title="出入库汇总" subtitle="按日期范围查看入库/出库总量与来源分布。" />
    <el-card shadow="never" class="fcard"><div class="frow">
      <el-date-picker v-model="range" type="daterange" range-separator="~" value-format="YYYY-MM-DD" style="width:260px" />
      <el-button type="primary" @click="load">查询</el-button>
    </div></el-card>
    <div class="krow">
      <div class="kc"><div class="kv">{{ s.total_in?.toFixed(0) }}</div><div class="kl">入库总量</div></div>
      <div class="kc"><div class="kv">{{ s.total_out?.toFixed(0) }}</div><div class="kl">出库总量</div></div>
      <div class="kc"><div class="kv">{{ s.total_txns }}</div><div class="kl">流水条数</div></div>
    </div>
    <el-card shadow="never">
      <el-table :data="items" stripe size="small">
        <el-table-column prop="source_type" label="来源" width="140" />
        <el-table-column prop="direction" label="方向" width="80"><template #default="{row}"><el-tag :type="row.direction==='in'?'success':'danger'" size="small">{{row.direction==='in'?'入库':'出库'}}</el-tag></template></el-table-column>
        <el-table-column prop="txn_count" label="次数" width="80" align="center" />
        <el-table-column prop="total_qty" label="数量" width="100" align="right" />
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import {onMounted,ref} from 'vue';import PageHero from '../components/PageHero.vue';import api from '../api/client'
const items=ref<any[]>([]);const s=ref<any>({});const range=ref<[string,string]|null>(null)
async function load(){const[p,q]=range.value||['',''];const r=await Promise.all([api.get('/api/dashboard/inventory/summary',{params:{date_from:p,date_to:q}}),api.get('/api/dashboard/inventory/by-source',{params:{date_from:p,date_to:q}})]);
s.value=(r[0].data as any).data??{};items.value=(r[1].data as any).items??[]}
onMounted(load)
</script>

<style scoped>
.fcard{margin-bottom:12px}.frow{display:flex;align-items:center;gap:12px}
.krow{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-bottom:16px}
.kc{background:var(--el-fill-color-light);border-radius:8px;padding:16px;text-align:center}
.kv{font-size:28px;font-weight:700;color:var(--el-color-primary)}.kl{font-size:13px;color:var(--el-text-color-secondary);margin-top:4px}
</style>
