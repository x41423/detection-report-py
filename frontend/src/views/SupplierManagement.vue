<template>
  <div class="page-shell supplier-page page-shell--full">
    <PageHero eyebrow="采购入库" title="供应商管理" description="维护供应商基础信息，支持搜索、筛选、新增、编辑和停用。" tone="teal">
      <template #actions>
        <el-button type="primary" @click="openCreate">新增供应商</el-button>
      </template>
      <template #aside>
        <div class="hero-metrics">
          <div class="hero-metric"><span>供应商总数</span><strong>{{ total }}</strong></div>
        </div>
      </template>
    </PageHero>

    <el-card shadow="never" class="panel-card">
      <el-form :inline="true" @submit.prevent="load">
        <el-form-item><el-input v-model="search" placeholder="搜索名称/编码" clearable @clear="load" /></el-form-item>
        <el-form-item>
          <el-select v-model="statusFilter" clearable placeholder="状态" @change="load">
            <el-option label="活跃" value="active" /><el-option label="停用" value="inactive" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-select v-model="typeFilter" clearable placeholder="供应商类型" @change="load">
            <el-option label="企业" value="enterprise" /><el-option label="个人" value="individual" /><el-option label="合作社" value="cooperative" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-select v-model="levelFilter" clearable placeholder="供应商等级" @change="load">
            <el-option label="VIP" value="vip" /><el-option label="普通" value="normal" /><el-option label="临时" value="temporary" />
          </el-select>
        </el-form-item>
        <el-form-item><el-button type="primary" @click="load">查询</el-button></el-form-item>
      </el-form>
    </el-card>

    <el-card shadow="never" class="panel-card" v-loading="loading">
      <el-table :data="items" stripe>
        <el-table-column prop="code" label="编码" width="180" />
        <el-table-column prop="name" label="名称" />
        <el-table-column prop="contact_person" label="联系人" />
        <el-table-column prop="contact_phone" label="电话" />
        <el-table-column prop="supplier_type" label="类型" width="100">
          <template #default="{row}">
            <el-tag :type="row.supplier_type==='enterprise'?'primary':row.supplier_type==='cooperative'?'success':'info'">
              {{ supplierTypeMap[row.supplier_type] || row.supplier_type }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="level" label="等级" width="100">
          <template #default="{row}">
            <el-tag :type="row.level==='vip'?'danger':row.level==='normal'?'primary':'info'">
              {{ levelMap[row.level] || row.level }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="settlement_method" label="结算方式" width="100">
          <template #default="{row}">
            {{ settlementMap[row.settlement_method] || row.settlement_method }}
          </template>
        </el-table-column>
        <el-table-column prop="credit_limit" label="信用额度" width="100" />
        <el-table-column prop="status" label="状态" width="80"><template #default="{row}"><el-tag :type="row.status==='active'?'success':'info'">{{ row.status }}</el-tag></template></el-table-column>
        <el-table-column label="操作" width="240">
          <template #default="{row}">
            <el-button size="small" type="primary" link @click="$router.push(`/suppliers/${row.id}`)">详情</el-button>
            <el-button size="small" type="primary" link @click="openEdit(row)">编辑</el-button>
            <template v-if="row.status === 'active'">
              <el-button size="small" type="warning" link @click="handleDeactivate(row)">停用</el-button>
            </template>
            <template v-else>
              <el-button size="small" type="success" link @click="handleActivate(row)">启用</el-button>
              <el-button size="small" type="danger" link @click="handleHardDelete(row)">删除</el-button>
            </template>
          </template>
        </el-table-column>
      </el-table>
      <el-pagination v-model:current-page="page" :page-size="limit" :total="total" layout="prev,next" @current-change="load" />
    </el-card>

    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑供应商' : '新增供应商'" width="800px">
      <el-form :model="form" label-position="top">
        <!-- 基本信息 -->
        <el-divider content-position="left">基本信息</el-divider>
        <el-row :gutter="16">
          <el-col :span="8">
            <el-form-item label="供应商名称" required><el-input v-model="form.name" /></el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="联系人"><el-input v-model="form.contact_person" /></el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="联系电话"><el-input v-model="form.contact_phone" /></el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="16">
            <el-form-item label="地址"><el-input v-model="form.contact_address" /></el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="供应商类型">
              <el-select v-model="form.supplier_type" style="width:100%">
                <el-option label="企业" value="enterprise" /><el-option label="个人" value="individual" /><el-option label="合作社" value="cooperative" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>

        <!-- 业务信息 -->
        <el-divider content-position="left">业务信息</el-divider>
        <el-row :gutter="16">
          <el-col :span="8">
            <el-form-item label="营业执照号"><el-input v-model="form.business_license" /></el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="税号"><el-input v-model="form.tax_number" /></el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="供应商等级">
              <el-select v-model="form.level" style="width:100%">
                <el-option label="VIP" value="vip" /><el-option label="普通" value="normal" /><el-option label="临时" value="temporary" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="8">
            <el-form-item label="开户银行"><el-input v-model="form.bank_name" /></el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="银行账号"><el-input v-model="form.bank_account" /></el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="信用额度"><el-input-number v-model="form.credit_limit" :min="0" :precision="2" style="width:100%" /></el-form-item>
          </el-col>
        </el-row>

        <!-- 合作信息 -->
        <el-divider content-position="left">合作信息</el-divider>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="结算方式">
              <el-select v-model="form.settlement_method" style="width:100%">
                <el-option label="月结" value="monthly" /><el-option label="周结" value="weekly" /><el-option label="现结" value="daily" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="付款条件"><el-input v-model="form.payment_terms" placeholder="如：货到付款、预付30%" /></el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="24">
            <el-form-item label="备注"><el-input v-model="form.remark" type="textarea" :rows="2" /></el-form-item>
          </el-col>
        </el-row>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible=false">取消</el-button>
        <el-button type="primary" @click="handleSave" :loading="saving">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { getSuppliers, createSupplier, updateSupplier, deleteSupplier, activateSupplier, hardDeleteSupplier, type Supplier, type SupplierCreateForm } from '../api/supplier'
import { ElMessage, ElMessageBox } from 'element-plus'

const supplierTypeMap: Record<string, string> = { enterprise: '企业', individual: '个人', cooperative: '合作社' }
const levelMap: Record<string, string> = { vip: 'VIP', normal: '普通', temporary: '临时' }
const settlementMap: Record<string, string> = { monthly: '月结', weekly: '周结', daily: '现结' }

const items = ref<Supplier[]>([])
const total = ref(0)
const loading = ref(false)
const saving = ref(false)
const search = ref('')
const statusFilter = ref('')
const typeFilter = ref('')
const levelFilter = ref('')
const page = ref(1)
const limit = 20
const dialogVisible = ref(false)
const editingId = ref<number | null>(null)

const emptyForm = (): SupplierCreateForm => ({
  name: '',
  contact_person: '',
  contact_phone: '',
  contact_address: '',
  supplier_type: 'enterprise',
  business_license: '',
  tax_number: '',
  bank_name: '',
  bank_account: '',
  settlement_method: 'monthly',
  payment_terms: '',
  credit_limit: 0,
  level: 'normal',
  remark: '',
})

const form = reactive<SupplierCreateForm>(emptyForm())

function resetForm() {
  editingId.value = null
  Object.assign(form, emptyForm())
}

async function load() {
  loading.value = true
  try {
    const { data } = await getSuppliers({
      search: search.value,
      status: statusFilter.value || undefined,
      supplier_type: typeFilter.value || undefined,
      level: levelFilter.value || undefined,
      limit,
      offset: (page.value - 1) * limit,
    })
    items.value = data.items
    total.value = data.total
  } finally {
    loading.value = false
  }
}

function openCreate() {
  resetForm()
  dialogVisible.value = true
}

function openEdit(row: Supplier) {
  editingId.value = row.id
  Object.assign(form, {
    name: row.name,
    contact_person: row.contact_person || '',
    contact_phone: row.contact_phone || '',
    contact_address: row.contact_address || '',
    supplier_type: row.supplier_type || 'enterprise',
    business_license: row.business_license || '',
    tax_number: row.tax_number || '',
    bank_name: row.bank_name || '',
    bank_account: row.bank_account || '',
    settlement_method: row.settlement_method || 'monthly',
    payment_terms: row.payment_terms || '',
    credit_limit: row.credit_limit || 0,
    level: row.level || 'normal',
    remark: row.remark || '',
  })
  dialogVisible.value = true
}

async function handleSave() {
  if (!form.name) {
    ElMessage.warning('名称不能为空')
    return
  }
  saving.value = true
  try {
    if (editingId.value) {
      await updateSupplier(editingId.value, { ...form })
    } else {
      await createSupplier({ ...form })
    }
    ElMessage.success(editingId.value ? '已更新' : '已创建')
    dialogVisible.value = false
    load()
  } finally {
    saving.value = false
  }
}

async function handleDeactivate(row: Supplier) {
  try {
    await ElMessageBox.confirm(`确定停用供应商「${row.name}」？`)
    await deleteSupplier(row.id)
    ElMessage.success('已停用')
    load()
  } catch (e: any) {
    if (e !== 'cancel') {
      ElMessage.error(e?.response?.data?.detail || '操作失败')
    }
  }
}

async function handleActivate(row: Supplier) {
  try {
    await ElMessageBox.confirm(`确定重新启用供应商「${row.name}」？`)
    await activateSupplier(row.id)
    ElMessage.success('已启用')
    load()
  } catch (e: any) {
    if (e !== 'cancel') {
      ElMessage.error(e?.response?.data?.detail || '操作失败')
    }
  }
}

async function handleHardDelete(row: Supplier) {
  try {
    await ElMessageBox.confirm(
      `确定永久删除供应商「${row.name}」？此操作不可撤销！`,
      '删除确认',
      { type: 'error', confirmButtonText: '确定删除', cancelButtonText: '取消' },
    )
    await hardDeleteSupplier(row.id)
    ElMessage.success('已永久删除')
    load()
  } catch (e: any) {
    if (e !== 'cancel') {
      ElMessage.error(e?.response?.data?.detail || '操作失败')
    }
  }
}

onMounted(load)
</script>
