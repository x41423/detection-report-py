<template>
  <div class="page-shell settlement-page page-shell--full">
    <PageHero eyebrow="采购入库" title="供应商结算" description="管理供应商结算单，支持手动创建或根据已确认入库自动生成。" tone="teal">
      <template #actions>
        <el-button type="primary" @click="openCreate">新增结算</el-button>
        <el-button @click="openAutoCreate">自动生成</el-button>
      </template>
    </PageHero>

    <el-card shadow="never" class="panel-card">
      <el-form :inline="true" @submit.prevent="load">
        <el-form-item><el-input v-model="periodFilter" placeholder="结算周期 YYYY-MM" clearable @clear="load" /></el-form-item>
        <el-form-item><el-button type="primary" @click="load">查询</el-button></el-form-item>
      </el-form>
    </el-card>

    <el-card shadow="never" class="panel-card" v-loading="loading">
      <el-table :data="items" stripe>
        <el-table-column prop="settlement_period" label="周期" width="120" />
        <el-table-column prop="supplier_name" label="供应商" />
        <el-table-column prop="payable_amount" label="应付" width="100" />
        <el-table-column prop="paid_amount" label="已付" width="100" />
        <el-table-column prop="balance_amount" label="余额" width="100" />
        <el-table-column prop="status" label="状态" width="90">
          <template #default="{row}"><el-tag :type="row.status==='settled'?'success':'warning'">{{ row.status }}</el-tag></template>
        </el-table-column>
        <el-table-column label="操作" width="120">
          <template #default="{row}">
            <el-button v-if="row.status!=='settled'" size="small" type="success" @click="handleConfirm(row)">确认</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-pagination v-model:current-page="page" :page-size="limit" :total="total" layout="prev,next" @current-change="load" />
    </el-card>

    <el-dialog v-model="dialogVisible" title="新增结算单" width="400px">
      <el-form :model="form" label-position="top">
        <el-form-item label="供应商ID" required><el-input-number v-model="form.supplier_id" :min="1" /></el-form-item>
        <el-form-item label="周期" required><el-input v-model="form.settlement_period" placeholder="YYYY-MM" /></el-form-item>
        <el-form-item label="应付金额"><el-input-number v-model="form.payable_amount" :min="0" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="dialogVisible=false">取消</el-button><el-button type="primary" @click="save" :loading="saving">保存</el-button></template>
    </el-dialog>

    <el-dialog v-model="autoDialogVisible" title="自动生成结算单" width="400px">
      <el-form :model="autoForm" label-position="top">
        <el-form-item label="供应商ID" required><el-input-number v-model="autoForm.supplier_id" :min="1" /></el-form-item>
        <el-form-item label="周期" required><el-input v-model="autoForm.period" placeholder="YYYY-MM" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="autoDialogVisible=false">取消</el-button><el-button type="primary" @click="autoSave" :loading="saving">生成</el-button></template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getSettlements, createSettlement, autoCreateSettlement, confirmSettlement, type Settlement } from '../api/settlement'

const items = ref<Settlement[]>([]); const total = ref(0); const loading = ref(false); const saving = ref(false)
const periodFilter = ref(''); const page = ref(1); const limit = 20
const dialogVisible = ref(false); const autoDialogVisible = ref(false)
const form = reactive({ supplier_id: 0, settlement_period: '', payable_amount: 0 })
const autoForm = reactive({ supplier_id: 0, period: '' })

async function load() {
  loading.value = true
  try { const { data } = await getSettlements({ period: periodFilter.value || undefined, limit, offset: (page.value-1)*limit }); items.value = data.items; total.value = data.total }
  catch (e: any) { ElMessage.error(e?.response?.data?.detail || '加载结算单失败') }
  finally { loading.value = false }
}
function openCreate() { form.supplier_id = 0; form.settlement_period = ''; form.payable_amount = 0; dialogVisible.value = true }
function openAutoCreate() { autoForm.supplier_id = 0; autoForm.period = ''; autoDialogVisible.value = true }
async function save() {
  saving.value = true
  try { await createSettlement({...form}); ElMessage.success('已创建'); dialogVisible.value = false; load() }
  catch (e: any) { ElMessage.error(e?.response?.data?.detail || '创建结算单失败') }
  finally { saving.value = false }
}
async function autoSave() {
  saving.value = true
  try { await autoCreateSettlement(autoForm.supplier_id, autoForm.period); ElMessage.success('已自动生成'); autoDialogVisible.value = false; load() }
  catch (e: any) { ElMessage.error(e?.response?.data?.detail || '自动生成失败') }
  finally { saving.value = false }
}
async function handleConfirm(row: Settlement) {
  try { await confirmSettlement(row.id); ElMessage.success('已确认'); load() }
  catch (e: any) { ElMessage.error(e?.response?.data?.detail || '确认结算失败') }
}

onMounted(load)
</script>
