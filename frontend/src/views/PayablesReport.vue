<template>
  <div class="page-shell page page-shell--full">
    <PageHero title="应付总账" subtitle="按供应商查看应付金额、已付金额和余额。" />
    <el-card shadow="never">
      <el-table :data="items" stripe size="small" max-height="550">
        <el-table-column prop="supplier_name" label="供应商" min-width="140" />
        <el-table-column prop="settlement_period" label="结算周期" width="130" />
        <el-table-column prop="payable_amount" label="应付" width="110" align="right" />
        <el-table-column prop="paid_amount" label="已付" width="110" align="right" />
        <el-table-column prop="balance_amount" label="余额" width="110" align="right"><template #default="{row}"><span :style="{color:row.balance_amount>0?'var(--el-color-danger)':'var(--el-color-success)'}">{{row.balance_amount}}</span></template></el-table-column>
        <el-table-column prop="status" label="状态" width="80"><template #default="{row}"><el-tag size="small">{{row.status}}</el-tag></template></el-table-column>
      </el-table>
    </el-card>
  </div>
</template>
<script setup lang="ts">import {onMounted,ref} from 'vue';import PageHero from '../components/PageHero.vue';import api from '../api/client'
const items=ref<any[]>([]);onMounted(async()=>{const{data}=await api.get('/api/dashboard/payables');items.value=(data as any).items??[]})</script>
