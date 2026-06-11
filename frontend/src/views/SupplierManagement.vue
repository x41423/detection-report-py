<template>
  <div class="page-shell supplier-page page-shell--full">
    <PageHero title="供应商管理" subtitle="管理上游供货商，支持基本信息、可供商品、联系人、合同管理。" />

    <!-- 搜索栏 -->
    <el-card shadow="never" class="filter-card">
      <div class="filter-row">
        <el-input
          v-model="search"
          placeholder="搜索供应商编号/名称"
          clearable
          style="width: 260px"
          @clear="load"
          @keyup.enter="load"
        />
        <el-select v-model="filterStatus" placeholder="全部状态" clearable style="width: 130px" @change="load">
          <el-option label="活跃" value="active" />
          <el-option label="已停用" value="inactive" />
        </el-select>
        <el-button type="primary" @click="load">搜索</el-button>
        <el-button @click="reset">重置</el-button>
      </div>
    </el-card>

    <!-- 操作栏 -->
    <el-card shadow="never" class="toolbar-card">
      <div class="toolbar-row">
        <span class="soft-note">共 {{ total }} 条</span>
        <el-button type="primary" @click="openCreate">
          <el-icon><Plus /></el-icon>新建供应商
        </el-button>
      </div>
    </el-card>

    <!-- 表格 -->
    <el-card shadow="never" class="table-card">
      <el-table :data="items" v-loading="loading" stripe size="small">
        <el-table-column prop="supplier_code" label="编号" width="100" />
        <el-table-column prop="name" label="供应商名称" min-width="160" show-overflow-tooltip>
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="openDetail(row.id)">
              {{ row.name }}
            </el-button>
          </template>
        </el-table-column>
        <el-table-column prop="settlement_cycle" label="结款周期" width="100" />
        <el-table-column prop="invoice_type" label="开票类型" width="130" />
        <el-table-column prop="default_purchaser" label="默认采购员" width="110" />
        <el-table-column prop="supplier_nature" label="性质" width="90">
          <template #default="{ row }">
            <el-tag size="small" :type="row.supplier_nature === '普通' ? 'info' : 'success'">
              {{ row.supplier_nature }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="row.status === 'active' ? 'success' : 'info'" size="small">
              {{ row.status === 'active' ? '活跃' : '停用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="160" />
        <el-table-column label="操作" width="140" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="openEdit(row)">编辑</el-button>
            <el-popconfirm
              :title="row.status === 'active' ? '确定停用？' : '确定恢复？'"
              @confirm="toggleStatus(row)"
            >
              <template #reference>
                <el-button link :type="row.status === 'active' ? 'warning' : 'success'" size="small">
                  {{ row.status === 'active' ? '停用' : '启用' }}
                </el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
      <div class="pagination-row">
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          :total="total"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next"
          @change="load"
        />
      </div>
    </el-card>

    <!-- 新建/编辑弹窗 -->
    <el-dialog
      v-model="dialogVisible"
      :title="editingId ? '编辑供应商' : '新建供应商'"
      width="700px"
      destroy-on-close
      @closed="resetForm"
    >
      <el-form ref="formRef" :model="form" label-width="100px">
        <el-divider content-position="left">基本资料</el-divider>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="供应商编号" required>
              <el-input v-model="form.supplier_code" placeholder="如 GX-001" maxlength="20" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="供应商名称" required>
              <el-input v-model="form.name" placeholder="输入供应商名称" maxlength="50" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="公司地址">
          <el-input v-model="form.contact_address" placeholder="详细地址" maxlength="200" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.remark" placeholder="备注信息" maxlength="200" />
        </el-form-item>

        <el-divider content-position="left">业务信息</el-divider>
        <el-form-item label="默认采购员">
          <el-input v-model="form.default_purchaser" placeholder="采购员姓名" maxlength="20" />
        </el-form-item>

        <el-divider content-position="left">结算信息</el-divider>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="结款周期">
              <el-select v-model="form.settlement_cycle" style="width:100%">
                <el-option label="日结" value="日结" />
                <el-option label="周结" value="周结" />
                <el-option label="半月结" value="半月结" />
                <el-option label="月结" value="月结" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="开票类型">
              <el-select v-model="form.invoice_type" style="width:100%">
                <el-option label="一般纳税人" value="一般纳税人" />
                <el-option label="小规模纳税人" value="小规模纳税人" />
                <el-option label="普票或无票" value="普票或无票" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>

        <el-divider content-position="left">工商信息</el-divider>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="公司名称">
              <el-input v-model="form.company_name" placeholder="工商注册名" maxlength="100" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="营业执照号">
              <el-input v-model="form.business_license" placeholder="统一社会信用代码" maxlength="30" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="开户名">
              <el-input v-model="form.bank_account_name" maxlength="50" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="开户银行">
              <el-input v-model="form.bank_name" maxlength="50" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="银行账号">
              <el-input v-model="form.bank_account" maxlength="30" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="供应商性质">
              <el-select v-model="form.supplier_nature" style="width:100%">
                <el-option label="普通" value="普通" />
                <el-option label="基地" value="基地" />
                <el-option label="批发商" value="批发商" />
                <el-option label="厂家" value="厂家" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import PageHero from '../components/PageHero.vue'
import {
  getSuppliers,
  createSupplier,
  updateSupplier,
  deleteSupplier,
  type Supplier,
  type SupplierForm,
} from '../api/supplier-api'

// Table
const items = ref<Supplier[]>([])
const total = ref(0)
const loading = ref(false)
const page = ref(1)
const pageSize = ref(20)
const search = ref('')
const filterStatus = ref('')

async function load() {
  loading.value = true
  try {
    const { data } = await getSuppliers({
      search: search.value || undefined,
      status: filterStatus.value || undefined,
      limit: pageSize.value,
      offset: (page.value - 1) * pageSize.value,
    })
    items.value = data.items ?? []
    total.value = data.total ?? 0
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '加载失败')
  } finally {
    loading.value = false
  }
}

function reset() { search.value = ''; filterStatus.value = ''; page.value = 1; load() }

// Form
const dialogVisible = ref(false)
const editingId = ref<number | null>(null)
const submitting = ref(false)
const form = reactive<SupplierForm>({
  supplier_code: '', name: '',
  settlement_cycle: '日结', invoice_type: '普票或无票',
  supplier_nature: '普通',
})

function openCreate() { editingId.value = null; Object.assign(form, { supplier_code: '', name: '', settlement_cycle: '日结', invoice_type: '普票或无票', supplier_nature: '普通' }); dialogVisible.value = true }
function openEdit(row: Supplier) { editingId.value = row.id; Object.assign(form, row); dialogVisible.value = true }
function resetForm() { editingId.value = null }

async function submit() {
  if (!form.supplier_code.trim() || !form.name.trim()) {
    ElMessage.warning('供应商编号和名称为必填'); return
  }
  submitting.value = true
  try {
    if (editingId.value) {
      await updateSupplier(editingId.value, { ...form })
      ElMessage.success('已更新')
    } else {
      await createSupplier({ ...form })
      ElMessage.success('已创建')
    }
    dialogVisible.value = false
    await load()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '操作失败')
  } finally {
    submitting.value = false
  }
}

async function toggleStatus(row: Supplier) {
  try {
    if (row.status === 'active') {
      await deleteSupplier(row.id)
      ElMessage.success('已停用')
    } else {
      await updateSupplier(row.id, { status: 'active' })
      ElMessage.success('已启用')
    }
    await load()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '操作失败')
  }
}

function openDetail(id: number) {
  // Navigate to detail page
  window.open(`/suppliers/${id}`, '_self')
}

onMounted(load)
</script>

<style scoped>
.filter-row { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
.toolbar-row { display: flex; align-items: center; justify-content: space-between; }
.pagination-row { margin-top: 12px; display: flex; justify-content: flex-end; }
.filter-card, .toolbar-card { margin-bottom: 12px; }
.soft-note { color: var(--el-text-color-secondary); font-size: 13px; }
</style>
