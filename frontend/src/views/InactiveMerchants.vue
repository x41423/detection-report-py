<template>
  <div class="page-shell page page-shell--full">
    <PageHero title="未下单商户" subtitle="监控近期未下单的商户，及时跟进。" />
    <el-card shadow="never" class="fcard"><div class="frow">
      <span>近</span><el-input-number v-model="days" :min="1" :max="90" @change="load" /><span>天未下单</span>
      <span class="snote">共 {{ items.length }} 个商户</span>
    </div></el-card>
    <el-card shadow="never">
      <el-table :data="items" stripe size="small">
        <el-table-column prop="merchant_name" label="商户" min-width="150" />
        <el-table-column prop="last_order" label="最后下单" width="120" />
        <el-table-column prop="total_orders" label="历史订单" width="90" align="center" />
        <el-table-column prop="total_amount" label="历史消费" width="120" align="right" />
      </el-table>
    </el-card>
  </div>
</template>
<script setup lang="ts">import {onMounted,ref} from 'vue';import PageHero from '../components/PageHero.vue';import api from '../api/client'
const items=ref<any[]>([]);const days=ref(7)
async function load(){const{data}=await api.get('/api/dashboard/inactive-merchants',{params:{days:days.value}});items.value=(data as any).items??[]}
onMounted(load)</script>
<style scoped>.fcard{margin-bottom:12px}.frow{display:flex;align-items:center;gap:8px}.snote{color:var(--el-text-color-secondary);font-size:13px;margin-left:auto}</style>
