<template>
  <div class="page-shell inspection-report-page page-shell--full">
    <PageHero title="检测报告" subtitle="管理检测报告归档，支持上传、查询、关联商品。" />

    <!-- Filter bar -->
    <el-card shadow="never" class="filter-card">
      <div class="filter-row">
        <el-input
          v-model="searchText"
          placeholder="搜索报告名/编号/送检机构/检测机构"
          clearable
          style="width: 320px"
          @clear="load"
          @keyup.enter="load"
        />
        <el-select v-model="filterStatus" placeholder="全部状态" clearable style="width: 140px" @change="load">
          <el-option label="草稿" value="draft" />
          <el-option label="已通过" value="approved" />
          <el-option label="已驳回" value="rejected" />
        </el-select>
        <el-date-picker
          v-model="dateRange"
          type="daterange"
          range-separator="~"
          start-placeholder="检测日期起"
          end-placeholder="检测日期止"
          value-format="YYYY-MM-DD"
          style="width: 260px"
          @change="load"
        />
        <el-button type="primary" @click="load">搜索</el-button>
        <el-button @click="resetFilters">重置</el-button>
      </div>
    </el-card>

    <!-- Toolbar -->
    <el-card shadow="never" class="toolbar-card">
      <div class="toolbar-row">
        <span class="soft-note">共 {{ total }} 条记录</span>
        <el-button type="primary" @click="openCreate">
          <el-icon><Plus /></el-icon>
          新增检测报告
        </el-button>
      </div>
    </el-card>

    <!-- Table -->
    <el-card shadow="never" class="table-card">
      <el-table :data="items" v-loading="loading" stripe size="small" @row-click="openDetail">
        <el-table-column prop="report_no" label="报告编号" width="170" />
        <el-table-column prop="name" label="报告名称" min-width="180" show-overflow-tooltip />
        <el-table-column prop="test_date" label="检测日期" width="110" />
        <el-table-column label="有效期" width="200">
          <template #default="{ row }">
            {{ row.valid_from }} ~ {{ row.valid_until }}
          </template>
        </el-table-column>
        <el-table-column prop="supplier_name" label="供应商" width="120" />
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="statusTag(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="来源" width="80">
          <template #default="{ row }">
            <el-tag v-if="row.source === 'generated'" type="success" size="small">系统生成</el-tag>
            <el-tag v-else type="info" size="small">手动</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="product_count" label="关联商品" width="90" align="center" />
        <el-table-column prop="uploader_name" label="上传人" width="100" />
        <el-table-column prop="created_at" label="上传时间" width="160" />
        <el-table-column label="操作" width="140" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click.stop="openEdit(row)">编辑</el-button>
            <el-popconfirm title="确定删除？" @confirm="handleDelete(row.id)">
              <template #reference>
                <el-button link type="danger" size="small">删除</el-button>
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

    <!-- Create / Edit Dialog -->
    <el-dialog
      v-model="dialogVisible"
      :title="editingId ? '编辑检测报告' : '新增检测报告'"
      width="720px"
      destroy-on-close
      @closed="resetForm"
    >
      <el-form ref="formRef" :model="form" label-width="100px">
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="报告名称">
              <el-input v-model="form.name" maxlength="50" placeholder="输入报告名称" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="检测日期">
              <el-date-picker v-model="form.test_date" type="date" value-format="YYYY-MM-DD" style="width:100%" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="送检机构">
              <el-input v-model="form.submit_org" placeholder="输入送检机构" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="检测机构">
              <el-input v-model="form.test_org" placeholder="输入检测机构" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="供应商">
              <el-select v-model="form.supplier_id" placeholder="选择供应商" clearable style="width:100%">
                <el-option v-for="s in suppliers" :key="s.id" :label="s.name" :value="s.id" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="状态">
              <el-select v-model="form.status" style="width:100%">
                <el-option label="草稿" value="draft" />
                <el-option label="已通过" value="approved" />
                <el-option label="已驳回" value="rejected" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="有效期起">
              <el-date-picker v-model="form.valid_from" type="date" value-format="YYYY-MM-DD" style="width:100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="有效期止">
              <el-date-picker v-model="form.valid_until" type="date" value-format="YYYY-MM-DD" style="width:100%" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="检测报告文件">
          <el-upload
            :action="'/api/inspection-report/upload'"
            :headers="uploadHeaders"
            :before-upload="beforeFileUpload"
            :on-success="onFileSuccess"
            :on-error="onFileError"
            :file-list="fileList"
            :limit="1"
            accept=".pdf,.docx,.doc,.jpg,.jpeg,.png,.zip"
            name="file"
          >
            <el-button size="small">上传附件</el-button>
            <template #tip>
              <span class="soft-note">支持 PDF / DOCX / JPG / PNG / ZIP，5M以内</span>
            </template>
          </el-upload>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submit">保存</el-button>
      </template>
    </el-dialog>

    <!-- Detail Dialog -->
    <el-dialog v-model="detailVisible" title="报告详情" width="720px" destroy-on-close>
      <template v-if="detail">
        <el-descriptions :column="2" border size="small">
          <el-descriptions-item label="报告编号">{{ detail.report_no }}</el-descriptions-item>
          <el-descriptions-item label="报告名称">{{ detail.name }}</el-descriptions-item>
          <el-descriptions-item label="检测日期">{{ detail.test_date }}</el-descriptions-item>
          <el-descriptions-item label="有效期">{{ detail.valid_from }} ~ {{ detail.valid_until }}</el-descriptions-item>
          <el-descriptions-item label="送检机构">{{ detail.submit_org }}</el-descriptions-item>
          <el-descriptions-item label="检测机构">{{ detail.test_org }}</el-descriptions-item>
          <el-descriptions-item label="供应商">{{ detail.supplier_name }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="statusTag(detail.status)" size="small">{{ statusLabel(detail.status) }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="上传人">{{ detail.uploader_name }}</el-descriptions-item>
          <el-descriptions-item label="上传时间">{{ detail.created_at }}</el-descriptions-item>
        </el-descriptions>

        <div v-if="detail.file_url" style="margin-top:12px">
          <el-button link type="primary" @click="window.open(detail.file_url, '_blank')">
            查看/下载报告文件
          </el-button>
        </div>

        <div v-if="detail.products && detail.products.length" style="margin-top:16px">
          <h4>关联检测商品</h4>
          <el-table :data="detail.products" size="small" stripe>
            <el-table-column prop="product_code" label="商品编码" width="140" />
            <el-table-column prop="product_name" label="商品名称" min-width="150" />
            <el-table-column prop="sku_name" label="规格" width="120" />
            <el-table-column prop="batch" label="批次" width="120" />
          </el-table>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import type { UploadFile, UploadRawFile } from 'element-plus'
import PageHero from '../components/PageHero.vue'
import { useAuth } from '../composables/useAuth'
import {
  getReports,
  getReport,
  createReport,
  updateReport,
  deleteReport,
  uploadReportFile,
  type InspectionReport,
  type InspectionReportForm,
} from '../api/inspection-report'

const { accessToken } = useAuth()

// ── Table state ──
const items = ref<InspectionReport[]>([])
const total = ref(0)
const loading = ref(false)
const page = ref(1)
const pageSize = ref(20)

// ── Filters ──
const searchText = ref('')
const filterStatus = ref('')
const dateRange = ref<[string, string] | null>(null)

async function load() {
  loading.value = true
  try {
    const { data } = await getReports({
      search: searchText.value || undefined,
      status: filterStatus.value || undefined,
      test_date_from: dateRange.value?.[0] || undefined,
      test_date_to: dateRange.value?.[1] || undefined,
      limit: pageSize.value,
      offset: (page.value - 1) * pageSize.value,
    })
    items.value = data.items
    total.value = data.total
  } finally {
    loading.value = false
  }
}

function resetFilters() {
  searchText.value = ''
  filterStatus.value = ''
  dateRange.value = null
  page.value = 1
  load()
}

// ── Status helpers ──
function statusTag(s: string) { return s === 'approved' ? 'success' : s === 'rejected' ? 'danger' : 'info' }
function statusLabel(s: string) { return s === 'approved' ? '已通过' : s === 'rejected' ? '已驳回' : '草稿' }

// ── Suppliers (for select) ──
const suppliers = ref<{ id: number; name: string }[]>([])
async function loadSuppliers() {
  try {
    const { default: api } = await import('../api/supplier')
    const { data } = await api.getSuppliers({ limit: 200 })
    suppliers.value = (data as any).items ?? []
  } catch { /* ignore */ }
}

// ── Form ──
const dialogVisible = ref(false)
const editingId = ref<number | null>(null)
const formRef = ref()
const form = reactive<InspectionReportForm>(emptyForm())

function emptyForm(): InspectionReportForm {
  return {
    name: '', test_date: '', valid_from: '', valid_until: '',
    supplier_id: 0, submit_org: '', test_org: '', file_url: '',
    status: 'draft', products: [],
  }
}

function resetForm() {
  editingId.value = null
  Object.assign(form, emptyForm())
  fileList.value = []
}

function openCreate() {
  resetForm()
  dialogVisible.value = true
}

async function openEdit(row: InspectionReport) {
  editingId.value = row.id
  Object.assign(form, {
    name: row.name, test_date: row.test_date,
    valid_from: row.valid_from, valid_until: row.valid_until,
    supplier_id: row.supplier_id, submit_org: row.submit_org,
    test_org: row.test_org, file_url: row.file_url,
    status: row.status, products: [],
  })
  if (row.file_url) {
    fileList.value = [{ name: row.file_url.split('/').pop() || 'report', url: row.file_url, uid: Date.now() }]
  } else {
    fileList.value = []
  }
  dialogVisible.value = true
}

async function submit() {
  const payload = { ...form }
  try {
    if (editingId.value) {
      await updateReport(editingId.value, payload)
      ElMessage.success('已更新')
    } else {
      await createReport(payload)
      ElMessage.success('已创建')
    }
    dialogVisible.value = false
    // Pitfall #30: update locally, don't reload
    await load()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '操作失败')
  }
}

// ⚠️ Pitfall #30: after delete, update local state, then reload
async function handleDelete(id: number) {
  try {
    await deleteReport(id)
    items.value = items.value.filter(item => item.id !== id)
    total.value = Math.max(0, total.value - 1)
    ElMessage.success('已删除')
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '删除失败')
  }
}

// ── File upload ──
// ⚠️ Pitfall #15: el-upload uses own XHR, must pass token explicitly
const fileList = ref<UploadFile[]>([])
const uploadHeaders = computed(() => {
  const token = accessToken.value
  return token ? { Authorization: `Bearer ${token}` } : {}
})

function beforeFileUpload(raw: UploadRawFile) {
  if (raw.size / 1024 / 1024 > 5) { ElMessage.error('文件不能超过 5MB'); return false }
  return true
}

function onFileSuccess(res: { success: boolean; url: string }) {
  if (res.success) form.file_url = res.url
}

function onFileError() {
  ElMessage.error('文件上传失败')
}

// ── Detail ──
const detailVisible = ref(false)
const detail = ref<InspectionReport | null>(null)

async function openDetail(row: InspectionReport) {
  try {
    const { data } = await getReport(row.id)
    detail.value = (data as any).item ?? data
    detailVisible.value = true
  } catch { /* ignore */ }
}

onMounted(() => {
  load()
  loadSuppliers()
})
</script>

<style scoped>
.filter-row {
  display: flex; align-items: center; gap: 12px; flex-wrap: wrap;
}
.toolbar-row {
  display: flex; align-items: center; justify-content: space-between;
}
.pagination-row {
  margin-top: 12px; display: flex; justify-content: flex-end;
}
.filter-card, .toolbar-card { margin-bottom: 12px; }
.soft-note { color: var(--el-text-color-secondary); font-size: 13px; }
</style>
