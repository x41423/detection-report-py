<template>
  <div class="page-shell product-page page-shell--full">
    <PageHero eyebrow="商品中心" title="商品库" description="管理销售商品主数据，支持分类筛选、SKU规格配置。" tone="teal">
      <template #actions>
        <el-button type="primary" @click="openCreate">新建销售商品</el-button>
      </template>
    </PageHero>

    <!-- 筛选栏 -->
    <el-card shadow="never" class="panel-card">
      <el-form :inline="true" @submit.prevent="load">
        <el-form-item>
          <el-input v-model="search" placeholder="搜索商品名称/编码" clearable @clear="load" style="width:240px" />
        </el-form-item>
        <el-form-item>
          <el-cascader
            v-model="selectedCategoryPath"
            :options="categoryTree"
            :props="{ value: 'id', label: 'name', children: 'children', checkStrictly: true, emitPath: false }"
            placeholder="全部分类"
            clearable
            style="width:200px"
            @change="onCategoryChange"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="load">查询</el-button>
        </el-form-item>
        <el-form-item>
          <el-button @click="resetFilters">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 数据表格 -->
    <el-card shadow="never" class="panel-card" v-loading="loading">
      <el-table :data="items" stripe @row-click="showDetail" highlight-current-row>
        <el-table-column label="图片" width="100">
          <template #default="{ row }">
            <el-avatar v-if="row.image_url" :src="row.image_url" shape="square" :size="54" />
            <el-avatar v-else shape="square" :size="54" :icon="PictureFilled" />
          </template>
        </el-table-column>
        <el-table-column label="商品(名称+编码)" min-width="180">
          <template #default="{ row }">
            <div class="product-cell">
              <span class="product-name">{{ row.name }}</span>
              <span class="product-code">{{ row.code }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="category_name" label="分类" width="120" />
        <el-table-column label="规格" width="80">
          <template #default="{ row }">
            {{ row.skus?.length || 0 }}
          </template>
        </el-table-column>
        <el-table-column prop="base_unit" label="单位" width="60" />
        <el-table-column label="价格区间" width="120">
          <template #default="{ row }">
            <span v-if="row.skus && row.skus.length">
              ¥{{ minSkuPrice(row).toFixed(2) }} ~ ¥{{ maxSkuPrice(row).toFixed(2) }}
            </span>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column prop="delivery_method" label="投框方式" width="110" />
        <el-table-column label="状态" width="70">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'info'" size="small">
              {{ row.is_active ? '上架' : '下架' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click.stop="openEdit(row)">编辑</el-button>
            <el-button v-if="row.is_active" size="small" type="danger" @click.stop="handleDelete(row)">下架</el-button>
            <el-button v-else size="small" type="success" @click.stop="handleActivate(row)">上架</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-pagination
        v-model:current-page="page"
        :page-size="limit"
        :total="total"
        layout="total, prev, pager, next"
        @current-change="load"
        style="margin-top:12px"
      />
    </el-card>

    <!-- 新建/编辑弹窗 -->
    <el-dialog
      v-model="dialogVisible"
      :title="editingId ? '编辑商品' : '新建销售商品'"
      width="780px"
      top="3vh"
      @closed="resetForm"
    >
      <el-form :model="form" label-position="top" label-width="auto">
        <!-- ===== 基本信息 ===== -->
        <el-divider content-position="left">基本信息</el-divider>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="商品名称" required>
              <el-input v-model="form.name" placeholder="输入商品名称" maxlength="200" show-word-limit />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="别名">
              <el-input v-model="form.alias" placeholder="商品别称" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="商品分类">
              <el-cascader
                v-model="form.category_id"
                :options="categoryTree"
                :props="{ value: 'id', label: 'name', children: 'children', checkStrictly: true, emitPath: false }"
                placeholder="选择分类"
                clearable
                style="width:100%"
              />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="商品类型">
              <el-select v-model="form.product_type" placeholder="选择类型" style="width:100%">
                <el-option label="通用" value="通用" />
                <el-option label="标品" value="标品" />
                <el-option label="非标品" value="非标品" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="自定义编码">
              <el-input v-model="form.custom_code" placeholder="自定义商品编码" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="基本单位">
              <el-select v-model="form.base_unit" placeholder="选择单位" style="width:100%">
                <el-option label="斤" value="斤" />
                <el-option label="kg" value="kg" />
                <el-option label="个" value="个" />
                <el-option label="箱" value="箱" />
                <el-option label="包" value="包" />
                <el-option label="瓶" value="瓶" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>

        <!-- ===== 采购与配送 ===== -->
        <el-divider content-position="left">采购与配送</el-divider>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="投框方式">
              <el-select v-model="form.delivery_method" placeholder="选择投框方式" style="width:100%">
                <el-option label="按订单投框" value="按订单投框" />
                <el-option label="按司机投框" value="按司机投框" />
                <el-option label="按线路投框" value="按线路投框" />
                <el-option label="不分框" value="不分框" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="采购方式">
              <el-select v-model="form.purchase_type" placeholder="选择采购方式" style="width:100%">
                <el-option label="临采" value="临采" />
                <el-option label="订单采购" value="订单采购" />
                <el-option label="长期合同" value="长期合同" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="采购模式">
              <el-select v-model="form.purchase_mode" placeholder="选择采购模式" style="width:100%">
                <el-option label="订单采购" value="订单采购" />
                <el-option label="自主采购" value="自主采购" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="默认供应商ID">
              <el-input-number v-model="form.default_supplier_id" :min="0" placeholder="可选" controls-position="right" style="width:100%" />
            </el-form-item>
          </el-col>
        </el-row>

        <!-- ===== 图片与保质期 ===== -->
        <el-divider content-position="left">图片与保质期</el-divider>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="商品图片">
              <el-upload
                :action="'/api/product/upload-image'"
                :headers="uploadHeaders"
                :before-upload="beforeImageUpload"
                :on-success="onImageUploadSuccess"
                :on-error="onImageUploadError"
                :on-remove="onImageRemove"
                :file-list="imageFileList"
                :limit="1"
                list-type="picture-card"
                accept="image/*"
                name="file"
              >
                <el-icon><Plus /></el-icon>
              </el-upload>
              <div v-if="form.image_url" style="margin-top:4px;font-size:12px;color:var(--el-text-color-secondary)">
                当前: {{ form.image_url }}
              </div>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="保质期(天)">
              <el-input-number v-model="form.shelf_life_days" :min="0" controls-position="right" style="width:100%" />
            </el-form-item>
          </el-col>
        </el-row>

        <!-- ===== 税务与检测 ===== -->
        <el-divider content-position="left">税务与检测</el-divider>
        <el-row :gutter="16">
          <el-col :span="8">
            <el-form-item label="税收分类编码">
              <el-input v-model="form.tax_category_code" placeholder="税收编码" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="税率(%)">
              <el-input-number v-model="form.tax_rate" :min="0" :max="100" :precision="1" controls-position="right" style="width:100%" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="检测报告">
              <el-switch v-model="form.has_inspection_report" active-text="需要" inactive-text="不需" />
            </el-form-item>
          </el-col>
        </el-row>

        <!-- ===== 自定义字段 ===== -->
        <el-divider content-position="left">自定义字段</el-divider>
        <el-row :gutter="16">
          <el-col :span="8">
            <el-form-item label="自定义字段1">
              <el-input v-model="form.custom_field_1" placeholder="-" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="自定义字段2">
              <el-input v-model="form.custom_field_2" placeholder="-" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="自定义字段3">
              <el-input v-model="form.custom_field_3" placeholder="-" />
            </el-form-item>
          </el-col>
        </el-row>

        <!-- ===== 备注 ===== -->
        <el-form-item label="商品描述">
          <el-input v-model="form.description" type="textarea" :rows="2" maxlength="256" show-word-limit placeholder="输入商品描述信息" />
        </el-form-item>
        <el-form-item label="内部备注">
          <el-input v-model="form.notes" type="textarea" :rows="2" maxlength="500" show-word-limit placeholder="内部使用的备注信息（如检测状态、供应商注意事项等）" />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="save" :loading="saving">
          {{ editingId ? '保存修改' : '新建商品' }}
        </el-button>
      </template>
    </el-dialog>

    <!-- 详情弹窗 -->
    <el-dialog v-model="detailVisible" title="商品详情" width="700px" top="5vh">
      <template v-if="detail">
        <el-descriptions :column="2" border size="small">
          <el-descriptions-item label="商品编码">{{ detail.code }}</el-descriptions-item>
          <el-descriptions-item label="商品名称">{{ detail.name }}</el-descriptions-item>
          <el-descriptions-item label="别名">{{ detail.alias || '-' }}</el-descriptions-item>
          <el-descriptions-item label="分类">{{ detail.category_name || '-' }}</el-descriptions-item>
          <el-descriptions-item label="商品类型">{{ detail.product_type }}</el-descriptions-item>
          <el-descriptions-item label="基本单位">{{ detail.base_unit }}</el-descriptions-item>
          <el-descriptions-item label="投框方式">{{ detail.delivery_method }}</el-descriptions-item>
          <el-descriptions-item label="采购方式">{{ detail.purchase_type }}</el-descriptions-item>
          <el-descriptions-item label="采购模式">{{ detail.purchase_mode }}</el-descriptions-item>
          <el-descriptions-item label="保质期">{{ detail.shelf_life_days }}天</el-descriptions-item>
          <el-descriptions-item label="税率">{{ detail.tax_rate }}%</el-descriptions-item>
          <el-descriptions-item label="税收编码">{{ detail.tax_category_code || '-' }}</el-descriptions-item>
          <el-descriptions-item label="检测报告">{{ detail.has_inspection_report ? '需要' : '不需' }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="detail.is_active ? 'success' : 'info'" size="small">
              {{ detail.is_active ? '上架' : '下架' }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="创建时间" :span="2">{{ detail.created_at }}</el-descriptions-item>
        </el-descriptions>

        <el-divider content-position="left">SKU规格列表 ({{ detail.skus?.length || 0 }})</el-divider>
        <el-table :data="detail.skus || []" size="small" max-height="240">
          <el-table-column prop="sku_code" label="SKU编码" width="130" />
          <el-table-column prop="spec_name" label="规格名称" />
          <el-table-column prop="sku_type" label="类型" width="90" />
          <el-table-column prop="price" label="售价" width="80" />
          <el-table-column prop="reference_cost" label="参考成本" width="80" />
          <el-table-column prop="pricing_method" label="定价方式" width="90">
            <template #default="{ row: sku }">
              {{ sku.pricing_method === 'manual' ? '手动' : '自动' }}
            </template>
          </el-table-column>
          <el-table-column prop="min_order_qty" label="最小下单" width="80" />
          <el-table-column prop="stock" label="库存" width="80" />
          <el-table-column label="上架" width="60">
            <template #default="{ row: sku }">
              <el-tag :type="sku.is_listed ? 'success' : 'info'" size="small">{{ sku.is_listed ? '是' : '否' }}</el-tag>
            </template>
          </el-table-column>
        </el-table>

        <el-descriptions v-if="detail.description" :column="1" border size="small" style="margin-top:12px">
          <el-descriptions-item label="描述">{{ detail.description }}</el-descriptions-item>
        </el-descriptions>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { PictureFilled, Plus } from '@element-plus/icons-vue'
import { useAuth } from '../composables/useAuth'
import type { UploadFile, UploadRawFile } from 'element-plus'
import {
  getProducts, getCategories, getProduct,
  createProduct, updateProduct, deleteProduct, activateProduct,
  uploadProductImage,
  type Product, type ProductCreateForm, type Category,
} from '../api/product'

// ── 列表状态 ──
const items = ref<Product[]>([])
const total = ref(0)
const loading = ref(false)
const search = ref('')
const page = ref(1)
const limit = 20
const selectedCategoryPath = ref<number[]>([])
const filterCategoryId = ref<number | null>(null)

// ── 分类树 ──
const categoryTree = ref<Category[]>([])

function buildCategoryTree(flat: Category[]): Category[] {
  const map = new Map<number, Category>()
  const roots: Category[] = []
  for (const cat of flat) {
    map.set(cat.id, { ...cat, children: [] })
  }
  for (const cat of map.values()) {
    if (cat.parent_id && map.has(cat.parent_id)) {
      map.get(cat.parent_id)!.children!.push(cat)
    } else {
      roots.push(cat)
    }
  }
  return roots
}

async function loadCategories() {
  try {
    const { data } = await getCategories()
    categoryTree.value = buildCategoryTree(data.items || [])
  } catch { /* ignore */ }
}

function onCategoryChange(value: number | null) {
  filterCategoryId.value = value
  page.value = 1
  load()
}

// ── 加载列表 ──
async function load() {
  loading.value = true
  try {
    const { data } = await getProducts({
      search: search.value || undefined,
      category_id: filterCategoryId.value ?? undefined,
      limit,
      offset: (page.value - 1) * limit,
      include_inactive: true,
    })
    items.value = data.items
    total.value = data.total
  } finally {
    loading.value = false
  }
}

function resetFilters() {
  search.value = ''
  selectedCategoryPath.value = []
  filterCategoryId.value = null
  page.value = 1
  load()
}

// ── SKU 价格计算 ──
function minSkuPrice(row: Product) {
  if (!row.skus?.length) return 0
  return Math.min(...row.skus.map(s => s.price))
}
function maxSkuPrice(row: Product) {
  if (!row.skus?.length) return 0
  return Math.max(...row.skus.map(s => s.price))
}

// ── 新建/编辑弹窗 ──
const dialogVisible = ref(false)
const editingId = ref<number | null>(null)
const saving = ref(false)

// ── 图片上传 ──

const { accessToken } = useAuth()

const imageFileList = ref<UploadFile[]>([])
const uploadHeaders = computed(() => {
  const token = accessToken.value
  return token ? { Authorization: `Bearer ${token}` } : {}
})

function beforeImageUpload(rawFile: UploadRawFile) {
  const isImage = rawFile.type.startsWith('image/')
  if (!isImage) {
    ElMessage.error('只能上传图片文件')
    return false
  }
  const isLt2M = rawFile.size / 1024 / 1024 < 2
  if (!isLt2M) {
    ElMessage.error('图片大小不能超过 2MB')
    return false
  }
  return true
}

function onImageUploadSuccess(response: { success: boolean; url: string }, uploadFile: any) {
  console.log('[UPLOAD] onSuccess called:', response, uploadFile)
  if (response.success) {
    form.image_url = response.url
    ElMessage.success('图片上传成功')
  } else {
    ElMessage.error(response.message || '上传失败')
  }
}

function onImageUploadError(error: any, uploadFile: any) {
  console.error('[UPLOAD] onError called:', error, uploadFile)
  ElMessage.error('图片上传失败，请检查网络或服务器')
}

function onImageRemove() {
  form.image_url = ''
}

const emptyForm = (): ProductCreateForm => ({
  name: '',
  alias: '',
  category_id: null,
  product_type: '通用',
  custom_code: '',
  delivery_method: '按订单投框',
  purchase_type: '临采',
  base_unit: '斤',
  image_url: '',
  shelf_life_days: 0,
  purchase_mode: '订单采购',
  default_supplier_id: null,
  description: '',
  notes: '',
  tax_category_code: '',
  tax_rate: 0,
  custom_field_1: '',
  custom_field_2: '',
  custom_field_3: '',
  has_inspection_report: false,
})

const form = reactive<ProductCreateForm>(emptyForm())

function resetForm() {
  editingId.value = null
  Object.assign(form, emptyForm())
  imageFileList.value = []
}

function openCreate() {
  resetForm()
  dialogVisible.value = true
}

function openEdit(row: Product) {
  editingId.value = row.id
  Object.assign(form, {
    name: row.name,
    alias: row.alias,
    category_id: row.category_id,
    product_type: row.product_type,
    custom_code: row.custom_code,
    delivery_method: row.delivery_method,
    purchase_type: row.purchase_type,
    base_unit: row.base_unit,
    image_url: row.image_url,
    shelf_life_days: row.shelf_life_days,
    purchase_mode: row.purchase_mode,
    default_supplier_id: row.default_supplier_id,
    description: row.description,
    notes: (row as any).notes || '',
    tax_category_code: row.tax_category_code,
    tax_rate: row.tax_rate,
    custom_field_1: row.custom_field_1,
    custom_field_2: row.custom_field_2,
    custom_field_3: row.custom_field_3,
    has_inspection_report: !!row.has_inspection_report,
  })
  // 初始化图片文件列表
  if (row.image_url) {
    imageFileList.value = [{
      name: row.image_url.split('/').pop() || 'product.jpg',
      url: row.image_url,
      uid: Date.now(),
    }]
  } else {
    imageFileList.value = []
  }
  dialogVisible.value = true
}

async function save() {
  if (!form.name.trim()) {
    ElMessage.warning('请输入商品名称')
    return
  }
  saving.value = true
  try {
    if (editingId.value) {
      await updateProduct(editingId.value, { ...form })
      ElMessage.success('商品已更新')
    } else {
      await createProduct({ ...form })
      ElMessage.success('商品已创建')
    }
    dialogVisible.value = false
    load()
  } finally {
    saving.value = false
  }
}

async function handleDelete(row: Product) {
  try {
    await ElMessageBox.confirm(`确定下架商品「${row.name}」吗？`, '确认下架', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning',
    })
    await deleteProduct(row.id)
    row.is_active = 0
    ElMessage.success('商品已下架')
  } catch { /* cancelled */ }
}

async function handleActivate(row: Product) {
  try {
    await activateProduct(row.id)
    row.is_active = 1
    ElMessage.success('商品已上架')
  } catch { /* ignore */ }
}

// ── 详情弹窗 ──
const detailVisible = ref(false)
const detail = ref<Product | null>(null)

async function showDetail(row: Product) {
  try {
    const { data } = await getProduct(row.id)
    detail.value = (data as any).item ?? data
    detailVisible.value = true
  } catch {
    ElMessage.error('加载商品详情失败')
  }
}

// ── 生命周期 ──
onMounted(async () => {
  await loadCategories()
  load()
})
</script>

<style scoped>
.product-cell {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.product-name {
  font-weight: 500;
}
.product-code {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
</style>
