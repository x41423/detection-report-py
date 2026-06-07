<template>
  <div class="page-shell pricelock-page page-shell--full">
    <PageHero eyebrow="营销工具" title="限时锁价" description="创建和管理限时锁价规则，锁定特定菜单下的商品价格。" tone="teal">
      <template #actions>
        <el-button type="primary" @click="openCreate">新增规则</el-button>
      </template>
    </PageHero>

    <el-card shadow="never" class="panel-card">
      <el-form :inline="true" @submit.prevent="load">
        <el-form-item><el-input v-model="search" placeholder="搜索规则名称" clearable @clear="load" /></el-form-item>
        <el-form-item><el-button type="primary" @click="load">查询</el-button></el-form-item>
      </el-form>
    </el-card>

    <el-card shadow="never" class="panel-card" v-loading="loading">
      <el-table :data="items" stripe>
        <el-table-column prop="rule_code" label="规则编码" width="160" />
        <el-table-column prop="rule_name" label="名称" />
        <el-table-column prop="category_count" label="品类数" width="80" />
        <el-table-column prop="start_time" label="开始" width="120" />
        <el-table-column prop="end_time" label="结束" width="120" />
        <el-table-column prop="status" label="状态" width="80">
          <template #default="{row}"><el-tag :type="row.status==='active'?'success':'info'">{{ row.status }}</el-tag></template>
        </el-table-column>
        <el-table-column label="操作" width="120">
          <template #default="{row}">
            <el-button v-if="row.status==='active'" size="small" type="danger" @click="handleDeactivate(row)">停用</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-pagination v-model:current-page="page" :page-size="limit" :total="total" layout="prev,next" @current-change="load" />
    </el-card>

    <el-dialog v-model="dialogVisible" title="新增锁价规则" width="600px">
      <el-form :model="form" label-position="top">
        <el-form-item label="规则名称" required><el-input v-model="form.rule_name" /></el-form-item>
        <el-form-item label="菜单名称"><el-input v-model="form.salemenu_name" /></el-form-item>
        <el-form-item label="开始日期"><el-input v-model="form.start_time" placeholder="YYYY-MM-DD" /></el-form-item>
        <el-form-item label="结束日期"><el-input v-model="form.end_time" placeholder="YYYY-MM-DD" /></el-form-item>
        <el-form-item label="商品"><el-input v-model="newItem.veg_name" placeholder="品名" @keyup.enter="addItem" /></el-form-item>
        <el-form-item><el-input-number v-model="newItem.locked_price" :min="0" placeholder="锁定价" /> <el-button @click="addItem">添加</el-button></el-form-item>
        <el-table :data="form.items" size="small">
          <el-table-column prop="veg_name" label="品名" /><el-table-column prop="locked_price" label="锁定价" />
          <el-table-column label="操作" width="60"><template #default="{$index}"><el-button size="small" @click="form.items.splice($index,1)">删</el-button></template></el-table-column>
        </el-table>
      </el-form>
      <template #footer><el-button @click="dialogVisible=false">取消</el-button><el-button type="primary" @click="save" :loading="saving">保存</el-button></template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getPriceLockRules, createPriceLockRule, deactivatePriceLockRule, type PriceLockRule } from '../api/price-lock'

const items = ref<PriceLockRule[]>([]); const total = ref(0); const loading = ref(false); const saving = ref(false)
const search = ref(''); const page = ref(1); const limit = 20
const dialogVisible = ref(false)
const form = reactive<{ rule_name: string; salemenu_name: string; start_time: string; end_time: string; items: any[] }>({ rule_name: '', salemenu_name: '', start_time: '', end_time: '', items: [] })
const newItem = reactive({ veg_name: '', locked_price: 0 })

async function load() {
  loading.value = true
  try { const { data } = await getPriceLockRules({ search: search.value, limit, offset: (page.value-1)*limit }); items.value = data.items; total.value = data.total }
  catch (e: any) { ElMessage.error(e?.response?.data?.detail || '加载锁价规则失败') }
  finally { loading.value = false }
}
function openCreate() { form.rule_name = ''; form.salemenu_name = ''; form.start_time = ''; form.end_time = ''; form.items = []; dialogVisible.value = true }
function addItem() { if (newItem.veg_name) { form.items.push({...newItem}); newItem.veg_name = ''; newItem.locked_price = 0 } }
async function save() {
  saving.value = true
  try { await createPriceLockRule({...form}); ElMessage.success('已创建'); dialogVisible.value = false; load() }
  catch (e: any) { ElMessage.error(e?.response?.data?.detail || '创建锁价规则失败') }
  finally { saving.value = false }
}
async function handleDeactivate(row: PriceLockRule) {
  try {
    await ElMessageBox.confirm(`确定停用规则「${row.rule_name}」？`)
    await deactivatePriceLockRule(row.id); ElMessage.success('已停用'); load()
  } catch (e: any) {
    if (e !== 'cancel') ElMessage.error(e?.response?.data?.detail || '停用失败')
  }
}

onMounted(load)
</script>
