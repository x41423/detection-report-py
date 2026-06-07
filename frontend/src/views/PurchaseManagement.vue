<template>
  <div class="page-shell purchase-page page-shell--full">
    <PageHero eyebrow="采购入库" title="采购入库 & 退货" description="管理采购入库与退货单据，确认后自动同步库存。" tone="teal">
      <template #actions>
        <el-button type="primary" @click="openCreateIn">新增入库</el-button>
        <el-button @click="openCreateReturn">新增退货</el-button>
      </template>
    </PageHero>

    <el-card shadow="never" class="panel-card">
      <el-tabs v-model="activeTab" @tab-change="load">
        <el-tab-pane label="入库单" name="in" />
        <el-tab-pane label="退货单" name="return" />
      </el-tabs>
      <el-form :inline="true" @submit.prevent="load">
        <el-form-item><el-input v-model="search" placeholder="搜索单号" clearable @clear="load" /></el-form-item>
        <el-form-item>
          <el-select v-model="statusFilter" clearable placeholder="状态" @change="load">
            <el-option label="待确认" value="pending" /><el-option label="已确认" value="confirmed" />
          </el-select>
        </el-form-item>
        <el-form-item><el-button type="primary" @click="load">查询</el-button></el-form-item>
      </el-form>
    </el-card>

    <el-card shadow="never" class="panel-card" v-loading="loading">
      <el-table :data="items" stripe>
        <el-table-column prop="order_no" label="单号" width="200" />
        <el-table-column prop="supplier_name" label="供应商" />
        <el-table-column :prop="activeTab === 'in' ? 'inbound_date' : 'return_date'" label="日期" width="120" />
        <el-table-column prop="total_amount" label="金额" width="100" />
        <el-table-column prop="status" label="状态" width="90">
          <template #default="{row}"><el-tag :type="row.status==='confirmed'?'success':'warning'">{{ row.status }}</el-tag></template>
        </el-table-column>
        <el-table-column label="操作" width="150">
          <template #default="{row}">
            <el-button v-if="row.status !== 'confirmed'" size="small" type="success" @click="handleConfirm(row)">确认</el-button>
            <el-tag v-else type="success">已确认</el-tag>
          </template>
        </el-table-column>
      </el-table>
      <el-pagination v-model:current-page="page" :page-size="limit" :total="total" layout="prev,next" @current-change="load" />
    </el-card>

    <!-- Create In Dialog -->
    <el-dialog v-model="inDialogVisible" title="新增入库单" width="600px">
      <el-form :model="inForm" label-position="top">
        <el-form-item label="供应商ID" required><el-input-number v-model="inForm.supplier_id" :min="1" /></el-form-item>
        <el-form-item label="入库日期" required><el-input v-model="inForm.inbound_date" placeholder="YYYY-MM-DD" /></el-form-item>
        <el-form-item label="商品"><el-input v-model="inNewItem.veg_name" placeholder="品名" @keyup.enter="addInItem" /></el-form-item>
        <el-form-item><el-input-number v-model="inNewItem.quantity" :min="0" placeholder="数量" /> <el-input-number v-model="inNewItem.unit_price" :min="0" placeholder="单价" /> <el-button @click="addInItem">添加</el-button></el-form-item>
        <el-table :data="inForm.items" size="small">
          <el-table-column prop="veg_name" label="品名" /><el-table-column prop="quantity" label="数量" /><el-table-column prop="unit_price" label="单价" />
          <el-table-column label="操作" width="60"><template #default="{$index}"><el-button size="small" @click="inForm.items.splice($index,1)">删</el-button></template></el-table-column>
        </el-table>
      </el-form>
      <template #footer><el-button @click="inDialogVisible=false">取消</el-button><el-button type="primary" @click="saveIn" :loading="saving">保存</el-button></template>
    </el-dialog>

    <!-- Create Return Dialog -->
    <el-dialog v-model="retDialogVisible" title="新增退货单" width="600px">
      <el-form :model="retForm" label-position="top">
        <el-form-item label="供应商ID" required><el-input-number v-model="retForm.supplier_id" :min="1" /></el-form-item>
        <el-form-item label="退货日期" required><el-input v-model="retForm.return_date" placeholder="YYYY-MM-DD" /></el-form-item>
        <el-form-item label="商品"><el-input v-model="retNewItem.veg_name" placeholder="品名" @keyup.enter="addRetItem" /></el-form-item>
        <el-form-item><el-input-number v-model="retNewItem.quantity" :min="0" /> <el-input-number v-model="retNewItem.unit_price" :min="0" /> <el-button @click="addRetItem">添加</el-button></el-form-item>
        <el-table :data="retForm.items" size="small">
          <el-table-column prop="veg_name" label="品名" /><el-table-column prop="quantity" label="数量" /><el-table-column prop="unit_price" label="单价" />
          <el-table-column label="操作" width="60"><template #default="{$index}"><el-button size="small" @click="retForm.items.splice($index,1)">删</el-button></template></el-table-column>
        </el-table>
      </el-form>
      <template #footer><el-button @click="retDialogVisible=false">取消</el-button><el-button type="primary" @click="saveRet" :loading="saving">保存</el-button></template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { ElMessage } from 'element-plus'
import { getPurchaseIns, createPurchaseIn, confirmPurchaseIn, getPurchaseReturns, createPurchaseReturn, confirmPurchaseReturn, type PurchaseIn, type PurchaseReturn } from '../api/purchase'

const activeTab = ref('in')
const items = ref<(PurchaseIn | PurchaseReturn)[]>([])
const total = ref(0)
const loading = ref(false)
const saving = ref(false)
const search = ref(''); const statusFilter = ref(''); const page = ref(1); const limit = 20

const inDialogVisible = ref(false); const retDialogVisible = ref(false)
const inForm = reactive<{ supplier_id: number; inbound_date: string; items: any[] }>({ supplier_id: 0, inbound_date: new Date().toISOString().slice(0,10), items: [] })
const retForm = reactive<{ supplier_id: number; return_date: string; items: any[] }>({ supplier_id: 0, return_date: new Date().toISOString().slice(0,10), items: [] })
const inNewItem = reactive({ veg_name: '', quantity: 0, unit_price: 0 })
const retNewItem = reactive({ veg_name: '', quantity: 0, unit_price: 0 })

async function load() {
  loading.value = true
  try {
    const fn = activeTab.value === 'in' ? getPurchaseIns : getPurchaseReturns
    const { data } = await fn({ search: search.value, status: statusFilter.value || undefined, limit, offset: (page.value-1)*limit })
    items.value = data.items; total.value = data.total
  } catch (e: any) { ElMessage.error(e?.response?.data?.detail || '操作失败') } finally { loading.value = false }
}

function openCreateIn() { inForm.supplier_id = 0; inForm.inbound_date = new Date().toISOString().slice(0,10); inForm.items = []; inDialogVisible.value = true }
function openCreateReturn() { retForm.supplier_id = 0; retForm.return_date = new Date().toISOString().slice(0,10); retForm.items = []; retDialogVisible.value = true }

function addInItem() { if (inNewItem.veg_name) { inForm.items.push({...inNewItem}); inNewItem.veg_name = ''; inNewItem.quantity = 0; inNewItem.unit_price = 0 } }
function addRetItem() { if (retNewItem.veg_name) { retForm.items.push({...retNewItem}); retNewItem.veg_name = ''; retNewItem.quantity = 0; retNewItem.unit_price = 0 } }

async function saveIn() {
  saving.value = true
  try { await createPurchaseIn({...inForm}); ElMessage.success('入库单已创建'); inDialogVisible.value = false; load()  } catch (e: any) { ElMessage.error(e?.response?.data?.detail || '操作失败') } finally { saving.value = false }
}
async function saveRet() {
  saving.value = true
  try { await createPurchaseReturn({...retForm}); ElMessage.success('退货单已创建'); retDialogVisible.value = false; load()  } catch (e: any) { ElMessage.error(e?.response?.data?.detail || '操作失败') } finally { saving.value = false }
}

async function handleConfirm(row: any) {
  try {
    const fn = activeTab.value === 'in' ? confirmPurchaseIn : confirmPurchaseReturn
    await fn(row.id); ElMessage.success('已确认，库存已同步'); load()
  } catch (e: any) { ElMessage.error(e?.response?.data?.detail || '确认失败') }
}

import { onMounted } from 'vue'; onMounted(load)
</script>
