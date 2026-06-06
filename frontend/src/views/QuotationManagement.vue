<template>
  <div class="page-shell quotation-page page-shell--full">
    <PageHero eyebrow="商品中心" title="报价单管理" description="管理客户报价单，为不同客户配置商品定价。" tone="orange">
      <template #actions>
        <el-button type="primary" @click="openCreate">新建报价单</el-button>
      </template>
    </PageHero>

    <!-- 筛选栏 -->
    <el-card shadow="never" class="panel-card">
      <el-form :inline="true" @submit.prevent="load">
        <el-form-item>
          <el-input v-model="search" placeholder="输入报价单ID或名称" clearable @clear="load" style="width:260px" />
        </el-form-item>
        <el-form-item>
          <el-select v-model="statusFilter" placeholder="状态筛选" clearable style="width:140px" @change="load">
            <el-option label="已激活" value="active" />
            <el-option label="已停用" value="inactive" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="load">搜索</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 报价单卡片列表 -->
    <div class="quotation-grid" v-loading="loading">
      <el-card
        v-for="q in items"
        :key="q.id"
        shadow="hover"
        class="quotation-card"
        @click="showDetail(q)"
      >
        <template #header>
          <div class="card-header">
            <el-tag :type="q.status === 'active' ? 'success' : 'info'" size="small" effect="dark">
              {{ q.status === 'active' ? '已激活' : '已停用' }}
            </el-tag>
            <span class="card-title">{{ q.name }}</span>
          </div>
        </template>
        <div class="card-body">
          <div class="card-field">
            <span class="field-label">报价单ID</span>
            <span class="field-value">{{ q.code }}</span>
          </div>
          <div class="card-field">
            <span class="field-label">对外简称</span>
            <span class="field-value">{{ q.external_name || '-' }}</span>
          </div>
          <div class="card-field">
            <span class="field-label">在售商品数</span>
            <span class="field-value">{{ q.product_count }}</span>
          </div>
          <div class="card-field">
            <span class="field-label">标签</span>
            <span class="field-value">{{ q.tags || '-' }}</span>
          </div>
          <div class="card-field">
            <span class="field-label">运营时间</span>
            <span class="field-value">{{ q.operation_time || '-' }}</span>
          </div>
          <div class="card-field">
            <span class="field-label">定价周期</span>
            <span class="field-value">
              <template v-if="q.pricing_start_date">{{ q.pricing_start_date }} ~ {{ q.pricing_end_date }}</template>
              <template v-else>-</template>
            </span>
          </div>
        </div>
        <div class="card-actions">
          <el-button size="small" @click.stop="openEdit(q)">编辑</el-button>
          <el-button
            size="small"
            :type="q.status === 'active' ? 'warning' : 'success'"
            @click.stop="handleToggle(q)"
          >
            {{ q.status === 'active' ? '停用' : '激活' }}
          </el-button>
        </div>
      </el-card>

      <el-empty v-if="!loading && items.length === 0" description="暂无报价单" />
    </div>

    <el-pagination
      v-if="total > limit"
      v-model:current-page="page"
      :page-size="limit"
      :total="total"
      layout="total, prev, pager, next"
      @current-change="load"
      style="margin-top:16px;justify-content:center"
    />

    <!-- 新建/编辑弹窗 -->
    <el-dialog
      v-model="dialogVisible"
      :title="editingId ? '编辑报价单' : '新建报价单'"
      width="600px"
      top="5vh"
      @closed="resetForm"
    >
      <el-form :model="form" label-position="top" label-width="auto">
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="报价单名称" required>
              <el-input v-model="form.name" placeholder="输入报价单名称" maxlength="200" show-word-limit />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="对外简称" required>
              <el-input v-model="form.external_name" placeholder="下单商城展现，≤20字符" maxlength="20" show-word-limit />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="货币类型">
              <el-select v-model="form.currency" style="width:100%">
                <el-option label="人民币" value="人民币" />
                <el-option label="美元" value="美元" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="运营时间">
              <el-select v-model="form.operation_time" style="width:100%">
                <el-option label="默认运营时间" value="默认运营时间" />
                <el-option label="早餐" value="早餐" />
                <el-option label="午餐" value="午餐" />
                <el-option label="晚餐" value="晚餐" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="报价单标签">
          <el-input v-model="form.tags" placeholder="输入标签（可选）" />
        </el-form-item>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="定价开始日期">
              <el-date-picker v-model="form.pricing_start_date" type="date" value-format="YYYY-MM-DD" placeholder="选择日期" style="width:100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="定价结束日期">
              <el-date-picker v-model="form.pricing_end_date" type="date" value-format="YYYY-MM-DD" placeholder="选择日期" style="width:100%" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="激活状态">
          <el-switch v-model="form.status" active-value="active" inactive-value="inactive" active-text="激活" inactive-text="停用" />
          <span class="form-hint">激活后客户可正常下单</span>
        </el-form-item>
        <el-form-item label="自动定价">
          <el-switch v-model="form.auto_pricing" disabled active-text="开" inactive-text="关" />
          <span class="form-hint">需设置定价周期后可用（规划中）</span>
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="2" maxlength="256" show-word-limit placeholder="输入报价单描述" />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="save" :loading="saving">
          {{ editingId ? '保存修改' : '新建报价单' }}
        </el-button>
      </template>
    </el-dialog>

    <!-- 详情弹窗 -->
    <el-dialog v-model="detailVisible" title="报价单详情" width="750px" top="5vh">
      <template v-if="detail">
        <el-descriptions :column="2" border size="small">
          <el-descriptions-item label="报价单ID">{{ detail.code }}</el-descriptions-item>
          <el-descriptions-item label="名称">{{ detail.name }}</el-descriptions-item>
          <el-descriptions-item label="对外简称">{{ detail.external_name || '-' }}</el-descriptions-item>
          <el-descriptions-item label="货币">{{ detail.currency }}</el-descriptions-item>
          <el-descriptions-item label="运营时间">{{ detail.operation_time }}</el-descriptions-item>
          <el-descriptions-item label="标签">{{ detail.tags || '-' }}</el-descriptions-item>
          <el-descriptions-item label="定价周期">
            {{ detail.pricing_start_date ? `${detail.pricing_start_date} ~ ${detail.pricing_end_date}` : '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="detail.status === 'active' ? 'success' : 'info'" size="small">
              {{ detail.status === 'active' ? '已激活' : '已停用' }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="创建时间" :span="2">{{ detail.created_at }}</el-descriptions-item>
        </el-descriptions>

        <el-divider content-position="left">
          关联商品 ({{ detail.products?.length || 0 }})
        </el-divider>

        <div class="add-product-row">
          <el-select
            v-model="newProductId"
            filterable
            remote
            :remote-method="searchProducts"
            :loading="searchingProducts"
            placeholder="搜索并添加商品"
            style="width:280px"
            value-key="id"
          >
            <el-option
              v-for="p in productOptions"
              :key="p.id"
              :label="`${p.name} (${p.code})`"
              :value="p.id"
            />
          </el-select>
          <el-input-number v-model="newProductPrice" :min="0" :precision="2" placeholder="价格" style="width:120px;margin-left:8px" />
          <el-button type="primary" size="small" @click="addProductToQuotation" style="margin-left:8px">添加</el-button>
        </div>

        <el-table :data="detail.products || []" size="small" style="margin-top:8px" max-height="300">
          <el-table-column prop="product_code" label="商品编码" width="120" />
          <el-table-column prop="product_name" label="商品名称" min-width="150" />
          <el-table-column prop="base_unit" label="单位" width="60" />
          <el-table-column prop="price" label="报价" width="100">
            <template #default="{ row: qp }">
              <el-input-number
                v-model="qp.price"
                :min="0"
                :precision="2"
                size="small"
                controls-position="right"
                style="width:90px"
                @change="(v: number) => updateQpPrice(qp, v)"
              />
            </template>
          </el-table-column>
          <el-table-column label="操作" width="60">
            <template #default="{ row: qp }">
              <el-button size="small" type="danger" @click="removeQp(qp)">移除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  getQuotations, getQuotation, createQuotation, updateQuotation,
  toggleQuotationStatus,
  addQuotationProduct, updateQuotationProduct, removeQuotationProduct,
  type Quotation, type QuotationCreateForm,
} from '../api/quotation'
import { getProducts, type Product } from '../api/product'

// ── 列表状态 ──
const items = ref<Quotation[]>([])
const total = ref(0)
const loading = ref(false)
const search = ref('')
const statusFilter = ref('')
const page = ref(1)
const limit = 20

async function load() {
  loading.value = true
  try {
    const { data } = await getQuotations({
      search: search.value || undefined,
      status: statusFilter.value || undefined,
      limit,
      offset: (page.value - 1) * limit,
    })
    items.value = data.items
    total.value = data.total
  } finally {
    loading.value = false
  }
}

// ── 新建/编辑弹窗 ──
const dialogVisible = ref(false)
const editingId = ref<number | null>(null)
const saving = ref(false)

const emptyForm = (): QuotationCreateForm => ({
  name: '',
  external_name: '',
  currency: '人民币',
  operation_time: '默认运营时间',
  tags: '',
  status: 'active',
  pricing_start_date: '',
  pricing_end_date: '',
  auto_pricing: false,
  description: '',
})

const form = reactive<QuotationCreateForm>(emptyForm())

function resetForm() {
  editingId.value = null
  Object.assign(form, emptyForm())
}

function openCreate() {
  resetForm()
  dialogVisible.value = true
}

function openEdit(q: Quotation) {
  editingId.value = q.id
  Object.assign(form, {
    name: q.name,
    external_name: q.external_name,
    currency: q.currency,
    operation_time: q.operation_time,
    tags: q.tags,
    status: q.status,
    pricing_start_date: q.pricing_start_date,
    pricing_end_date: q.pricing_end_date,
    auto_pricing: !!q.auto_pricing,
    description: q.description,
  })
  dialogVisible.value = true
}

async function save() {
  if (!form.name.trim()) { ElMessage.warning('请输入报价单名称'); return }
  if (!form.external_name.trim()) { ElMessage.warning('请输入对外简称'); return }
  saving.value = true
  try {
    if (editingId.value) {
      await updateQuotation(editingId.value, { ...form })
      ElMessage.success('报价单已更新')
    } else {
      await createQuotation({ ...form })
      ElMessage.success('报价单已创建')
    }
    dialogVisible.value = false
    load()
  } finally {
    saving.value = false
  }
}

async function handleToggle(q: Quotation) {
  const newStatus = q.status === 'active' ? 'inactive' : 'active'
  const action = newStatus === 'active' ? '激活' : '停用'
  try {
    await ElMessageBox.confirm(`确定${action}报价单「${q.name}」吗？`, `确认${action}`, {
      confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning',
    })
    await toggleQuotationStatus(q.id, newStatus)
    ElMessage.success(`报价单已${action}`)
    load()
  } catch { /* cancelled */ }
}

// ── 详情弹窗 ──
const detailVisible = ref(false)
const detail = ref<Quotation | null>(null)

async function showDetail(q: Quotation) {
  try {
    const { data } = await getQuotation(q.id)
    detail.value = data.item as unknown as Quotation
    detailVisible.value = true
  } catch {
    ElMessage.error('加载报价单详情失败')
  }
}

// ── 添加商品到报价单 ──
const newProductId = ref<number | null>(null)
const newProductPrice = ref(0)
const productOptions = ref<Product[]>([])
const searchingProducts = ref(false)

async function searchProducts(query: string) {
  if (!query) { productOptions.value = []; return }
  searchingProducts.value = true
  try {
    const { data } = await getProducts({ search: query, limit: 20 })
    productOptions.value = data.items
  } finally {
    searchingProducts.value = false
  }
}

async function addProductToQuotation() {
  if (!newProductId.value || !detail.value) return
  try {
    await addQuotationProduct(detail.value.id, {
      product_id: newProductId.value,
      price: newProductPrice.value,
    })
    ElMessage.success('商品已添加')
    newProductId.value = null
    newProductPrice.value = 0
    // Refresh detail
    const { data } = await getQuotation(detail.value.id)
    detail.value = data.item as unknown as Quotation
    load()
  } catch {
    ElMessage.error('添加商品失败')
  }
}

async function updateQpPrice(qp: any, price: number) {
  try {
    await updateQuotationProduct(qp.id, { price })
  } catch {
    ElMessage.error('更新价格失败')
  }
}

async function removeQp(qp: any) {
  try {
    await ElMessageBox.confirm('确定移除该商品吗？', '确认移除', {
      confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning',
    })
    await removeQuotationProduct(qp.id)
    ElMessage.success('商品已移除')
    if (detail.value) {
      const { data } = await getQuotation(detail.value.id)
      detail.value = data.item as unknown as Quotation
      load()
    }
  } catch { /* cancelled */ }
}

// ── 生命周期 ──
onMounted(load)
</script>

<style scoped>
.quotation-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: 16px;
  margin-top: 12px;
}
.quotation-card {
  cursor: pointer;
  transition: transform 0.15s;
}
.quotation-card:hover {
  transform: translateY(-2px);
}
.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
}
.card-title {
  font-weight: 600;
  font-size: 15px;
}
.card-body {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.card-field {
  display: flex;
  justify-content: space-between;
  font-size: 13px;
}
.field-label {
  color: var(--el-text-color-secondary);
}
.field-value {
  font-weight: 500;
}
.card-actions {
  margin-top: 12px;
  display: flex;
  gap: 8px;
  justify-content: flex-end;
}
.add-product-row {
  display: flex;
  align-items: center;
}
.form-hint {
  margin-left: 8px;
  color: var(--el-text-color-secondary);
  font-size: 12px;
}
</style>
