<template>
  <div class="page-shell supplier-page page-shell--full">
    <PageHero eyebrow="采购入库" title="商户管理" description="维护商户基础信息，支持搜索、筛选、新增、编辑和停用。" tone="teal">
      <template #actions>
        <el-button type="primary" @click="openCreate">新增商户</el-button>
      </template>
      <template #aside>
        <div class="hero-metrics">
          <div class="hero-metric"><span>商户总数</span><strong>{{ total }}</strong></div>
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
          <el-select v-model="typeFilter" clearable placeholder="商户类型" @change="load">
            <el-option label="企业" value="enterprise" /><el-option label="个人" value="individual" /><el-option label="合作社" value="cooperative" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-select v-model="levelFilter" clearable placeholder="商户等级" @change="load">
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
        <el-table-column label="添加时间" width="130">
          <template #default="{row}">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="80"><template #default="{row}"><el-tag :type="row.status==='active'?'success':'info'">{{ row.status }}</el-tag></template></el-table-column>
        <el-table-column label="操作" width="240">
          <template #default="{row}">
            <el-button size="small" type="primary" link @click="$router.push(`/merchants/${row.id}`)">详情</el-button>
            <el-button size="small" type="primary" link @click="openEdit(row)">编辑</el-button>
            <template v-if="row.status === 'active'">
              <el-button size="small" type="warning" link @click="handleDeactivate(row)">停用</el-button>
            </template>
            <template v-else>
              <el-button size="small" type="success" link @click="handleActivate(row)">启用</el-button>
              <el-button size="small" type="danger" link @click="handleDelete(row)">删除</el-button>
            </template>
          </template>
        </el-table-column>
      </el-table>
      <div class="pagination-wrap" style="margin-top: 16px">
        <el-pagination
          v-model:current-page="page"
          :page-size="limit"
          :total="total"
          layout="total, prev, pager, next"
          @current-change="load"
        />
      </div>
    </el-card>

    <!-- Create/Edit Dialog -->
    <el-dialog
      v-model="dialogVisible"
      :title="editingId ? '编辑商户' : '新增商户'"
      width="700px"
      @close="resetForm"
    >
      <el-form ref="formRef" :model="form" :rules="formRules" label-width="100px">
        <el-divider content-position="left">基本信息</el-divider>
        <el-row :gutter="16">
          <el-col :span="8">
            <el-form-item label="商户名称" required><el-input v-model="form.name" /></el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="联系人"><el-input v-model="form.contact_person" /></el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="联系电话"><el-input v-model="form.contact_phone" /></el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="24">
            <el-form-item label="联系地址"><el-input v-model="form.contact_address" /></el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="8">
            <el-form-item label="商户类型">
              <el-select v-model="form.supplier_type">
                <el-option label="企业" value="enterprise" />
                <el-option label="个人" value="individual" />
                <el-option label="合作社" value="cooperative" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="商户等级">
              <el-select v-model="form.level">
                <el-option label="VIP" value="vip" />
                <el-option label="普通" value="normal" />
                <el-option label="临时" value="temporary" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="状态">
              <el-select v-model="form.status">
                <el-option label="活跃" value="active" />
                <el-option label="停用" value="inactive" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-divider content-position="left">经营信息</el-divider>
        <el-row :gutter="16">
          <el-col :span="8"><el-form-item label="营业执照"><el-input v-model="form.business_license" /></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="税号"><el-input v-model="form.tax_number" /></el-form-item></el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="8"><el-form-item label="开户行"><el-input v-model="form.bank_name" /></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="银行账号"><el-input v-model="form.bank_account" /></el-form-item></el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="8">
            <el-form-item label="结算方式">
              <el-select v-model="form.settlement_method">
                <el-option label="月结" value="monthly" /><el-option label="周结" value="weekly" /><el-option label="现结" value="daily" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="8"><el-form-item label="结算周期"><el-input v-model="form.payment_terms" /></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="信用额度"><el-input-number v-model="form.credit_limit" :min="0" /></el-form-item></el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="24">
            <el-form-item label="备注"><el-input v-model="form.remark" type="textarea" /></el-form-item>
          </el-col>
        </el-row>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSubmit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'

import { getSuppliers, createSupplier, updateSupplier, deleteSupplier, activateSupplier, hardDeleteSupplier, type Supplier, type SupplierCreateForm } from '../api/supplier'
import { ElMessage, ElMessageBox } from 'element-plus'

function formatDate(dateStr: string): string {
  if (!dateStr) return '-'
  const d = new Date(dateStr)
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  const h = String(d.getHours()).padStart(2, '0')
  const min = String(d.getMinutes()).padStart(2, '0')
  return m + '-' + day + ' ' + h + ':' + min
}

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
  status: 'active',
  remark: '',
})

const form = reactive<SupplierCreateForm>(emptyForm())
const formRef = ref()
const formRules = {
  name: [{ required: true, message: '请输入商户名称', trigger: 'blur' }],
}

async function load() {
  loading.value = true
  try {
    const res = await getSuppliers({
      search: search.value,
      status: statusFilter.value || undefined,
      supplier_type: typeFilter.value || undefined,
      level: levelFilter.value || undefined,
      limit,
      offset: (page.value - 1) * limit,
    })
    items.value = res.data.items
    total.value = res.data.total
  } catch (e: any) {
    ElMessage.error('加载失败: ' + (e?.message || '未知错误'))
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
    contact_person: row.contact_person ?? '',
    contact_phone: row.contact_phone ?? '',
    contact_address: row.contact_address ?? '',
    supplier_type: row.supplier_type,
    business_license: row.business_license ?? '',
    tax_number: row.tax_number ?? '',
    bank_name: row.bank_name ?? '',
    bank_account: row.bank_account ?? '',
    settlement_method: row.settlement_method,
    payment_terms: row.payment_terms ?? '',
    credit_limit: row.credit_limit ?? 0,
    level: row.level,
    status: row.status,
    remark: row.remark ?? '',
  })
  dialogVisible.value = true
}

function resetForm() {
  editingId.value = null
  Object.assign(form, emptyForm())
  formRef.value?.resetFields()
}

async function handleSubmit() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  saving.value = true
  try {
    const payload = { ...form }
    if (editingId.value) {
      await updateSupplier(editingId.value, payload)
      ElMessage.success('商户已更新')
    } else {
      await createSupplier(payload)
      ElMessage.success('商户创建成功')
    }
    dialogVisible.value = false
    await load()
  } catch (e: any) {
    const msg = e?.response?.data?.detail || e?.message || '操作失败'
    ElMessage.error(msg)
  } finally {
    saving.value = false
  }
}

async function handleDeactivate(row: Supplier) {
  await ElMessageBox.confirm(`确定停用商户「${row.name}」？`, '确认', { type: 'warning' })
  await deleteSupplier(row.id)
  ElMessage.success('商户已停用')
  await load()
}

async function handleActivate(row: Supplier) {
  await ElMessageBox.confirm(`确定启用商户「${row.name}」？`, '确认')
  await activateSupplier(row.id)
  ElMessage.success('商户已启用')
  await load()
}

async function handleDelete(row: Supplier) {
  await ElMessageBox.confirm(`确定永久删除商户「${row.name}」？此操作不可撤销！`, '危险操作', { type: 'error' })
  await hardDeleteSupplier(row.id)
  ElMessage.success('商户已删除')
  await load()
}

onMounted(load)
</script>
