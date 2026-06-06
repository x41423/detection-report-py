<template>
  <div class="page-shell order-page page-shell--full">
    <PageHero eyebrow="采购入库" title="订单管理" description="管理客户订单，确认出库后自动扣减库存。支持售后记录。" tone="teal">
      <template #actions>
        <el-button type="primary" @click="openCreate">新建订单</el-button>
      </template>
    </PageHero>

    <!-- 筛选栏 -->
    <el-card shadow="never" class="panel-card">
      <FilterBar
        :filters="filterConfigs"
        v-model="filterValues"
        :show-reset="true"
        @search="load"
        @reset="resetFilters"
      />
    </el-card>

    <!-- 列选择器 + 表格 -->
    <el-card shadow="never" class="panel-card">
      <div class="table-toolbar">
        <el-popover placement="bottom-start" :width="400" trigger="click">
          <template #reference>
            <el-button size="small">
              <el-icon><Setting /></el-icon>
              列设置
            </el-button>
          </template>
          <div class="column-selector">
            <div class="column-selector__header">
              <el-checkbox
                :model-value="allColumnsSelected"
                :indeterminate="isIndeterminate"
                @change="toggleAllColumns"
              >全选</el-checkbox>
            </div>
            <el-divider style="margin: 8px 0" />
            <el-checkbox-group v-model="visibleColumnKeys" @change="onColumnChange">
              <div v-for="col in allColumnDefs" :key="col.key" class="column-selector__item">
                <el-checkbox :label="col.key" :disabled="mandatoryKeys.includes(col.key)">
                  {{ col.label }}
                </el-checkbox>
              </div>
            </el-checkbox-group>
          </div>
        </el-popover>
      </div>

      <el-table :data="items" stripe v-loading="loading" @row-click="showDetail" style="width: 100%">
        <!-- 动态列 -->
        <el-table-column
          v-for="col in activeColumns"
          :key="col.key"
          :prop="col.key"
          :label="col.label"
          :width="col.width"
          :min-width="col.minWidth"
          show-overflow-tooltip
        >
          <template #default="{ row }">
            <!-- 订单状态标签 -->
            <template v-if="col.key === 'order_status'">
              <el-tag :type="orderStatusType(row.order_status)" size="small">
                {{ orderStatusLabel(row.order_status) }}
              </el-tag>
            </template>
            <!-- 支付状态标签 -->
            <template v-else-if="col.key === 'payment_status'">
              <el-tag :type="paymentStatusType(row.payment_status)" size="small">
                {{ paymentStatusLabel(row.payment_status) }}
              </el-tag>
            </template>
            <!-- 金额格式化 -->
            <template v-else-if="col.key === 'order_amount' || col.key === 'sales_amount_incl_freight' || col.key === 'freight' || col.key === 'discount_amount'">
              ¥{{ (row[col.key] || 0).toFixed(2) }}
            </template>
            <!-- 默认显示 -->
            <template v-else>
              {{ row[col.key] ?? '-' }}
            </template>
          </template>
        </el-table-column>

        <!-- 操作列（固定右侧） -->
        <el-table-column label="操作" width="240" fixed="right">
          <template #default="{ row }">
            <el-button size="small" type="primary" link @click.stop="showDetail(row)">详情</el-button>
            <el-button size="small" type="primary" link @click.stop="openEdit(row)">编辑</el-button>
            <el-button size="small" type="danger" link @click.stop="handleDelete(row)">删除</el-button>
            <el-dropdown trigger="click" @command="(cmd: string) => handleCopyCommand(row, cmd)">
              <el-button size="small" type="success" link @click.stop>复制</el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="order">复制到订单</el-dropdown-item>
                  <el-dropdown-item command="supplement">复制到补单</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        v-model:current-page="page"
        v-model:page-size="limit"
        :page-sizes="[10, 20, 50, 100]"
        :total="total"
        layout="total, sizes, prev, pager, next, jumper"
        background
        style="margin-top: 12px; justify-content: flex-end"
        @current-change="load"
        @size-change="load"
      />
    </el-card>

    <!-- 新建/编辑订单对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="isEditMode ? '编辑订单' : '新建订单'"
      width="780px"
      top="3vh"
    >
      <el-form :model="form" label-position="top" label-width="auto">
        <!-- 客户信息 -->
        <el-divider content-position="left">客户信息</el-divider>
        <el-row :gutter="16">
          <el-col :span="8">
            <el-form-item label="商户">
              <el-input v-model="form.merchant_name" placeholder="输入商户名" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="商户标签">
              <el-input v-model="form.merchant_tag" placeholder="输入商户标签" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="订单号">
              <el-input :model-value="isEditMode ? editingOrder?.order_no : '-'" disabled />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="关联出库单号">
              <el-input v-model="form.related_outbound_no" placeholder="-" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="第三方订单号">
              <el-input v-model="form.third_party_order_no" placeholder="-" />
            </el-form-item>
          </el-col>
        </el-row>

        <!-- 时间信息 -->
        <el-divider content-position="left">时间信息</el-divider>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="下单日期" required>
              <el-date-picker v-model="form.order_date" type="date" value-format="YYYY-MM-DD" placeholder="选择日期" style="width:100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="运营时间">
              <el-select v-model="form.operation_time" placeholder="请选择运营时间" clearable style="width:100%">
                <el-option label="早餐" value="breakfast" />
                <el-option label="午餐" value="lunch" />
                <el-option label="晚餐" value="dinner" />
                <el-option label="全天" value="all_day" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="收货时间">
          <el-row :gutter="12" style="width: 100%">
            <el-col :span="11">
              <el-date-picker v-model="form.receive_start_date" type="date" value-format="YYYY-MM-DD" placeholder="开始日期" style="width:100%" />
            </el-col>
            <el-col :span="2" style="text-align:center;line-height:32px">~</el-col>
            <el-col :span="11">
              <el-date-picker v-model="form.receive_end_date" type="date" value-format="YYYY-MM-DD" placeholder="结束日期" style="width:100%" />
            </el-col>
          </el-row>
        </el-form-item>

        <!-- 配送信息 -->
        <el-divider content-position="left">配送信息</el-divider>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="收货方式">
              <el-select v-model="form.delivery_method" placeholder="请选择收货方式" clearable style="width:100%">
                <el-option label="自提" value="pickup" />
                <el-option label="配送" value="delivery" />
                <el-option label="快递" value="express" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="收货人">
              <el-input v-model="form.receiver" placeholder="-" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="签收方式">
              <el-select v-model="form.sign_method" placeholder="请选择" clearable style="width:100%">
                <el-option label="扫码签收" value="scan" />
                <el-option label="手动签收" value="manual" />
                <el-option label="无需签收" value="none" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="收货地址">
              <el-input v-model="form.delivery_address" placeholder="输入收货地址" />
            </el-form-item>
          </el-col>
        </el-row>

        <!-- 订单信息 -->
        <el-divider content-position="left">订单信息</el-divider>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="订单类型">
              <el-select v-model="form.order_type" placeholder="请选择订单类型" clearable style="width:100%">
                <el-option label="普通订单" value="normal" />
                <el-option label="加急订单" value="urgent" />
                <el-option label="补单" value="supplement" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="订单备注">
          <el-input v-model="form.remark" type="textarea" :rows="2" maxlength="128" show-word-limit placeholder="输入商家对订单的特殊要求（128个字以内）" />
        </el-form-item>

        <!-- 商户自定义字段 -->
        <el-row :gutter="16">
          <el-col :span="8">
            <el-form-item label="商户定义字段1">
              <el-input v-model="form.custom_field_1" placeholder="-" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="商户定义字段2">
              <el-input v-model="form.custom_field_2" placeholder="-" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="商户定义字段3">
              <el-input v-model="form.custom_field_3" placeholder="-" />
            </el-form-item>
          </el-col>
        </el-row>

        <!-- 商品清单 -->
        <el-divider content-position="left">商品清单</el-divider>
        <el-row :gutter="12">
          <el-col :span="8">
            <el-input v-model="newItem.product_name" placeholder="品名" @keyup.enter="addItem" />
          </el-col>
          <el-col :span="4">
            <el-input-number v-model="newItem.quantity" :min="0" placeholder="数量" controls-position="right" style="width:100%" />
          </el-col>
          <el-col :span="4">
            <el-input-number v-model="newItem.unit_price" :min="0" placeholder="单价" controls-position="right" style="width:100%" />
          </el-col>
          <el-col :span="4">
            <el-select v-model="newItem.unit" placeholder="单位" style="width:100%">
              <el-option label="斤" value="斤" />
              <el-option label="kg" value="kg" />
              <el-option label="个" value="个" />
              <el-option label="箱" value="箱" />
            </el-select>
          </el-col>
          <el-col :span="4">
            <el-button type="primary" @click="addItem">添加</el-button>
          </el-col>
        </el-row>
        <el-table :data="form.items" size="small" style="margin-top:8px">
          <el-table-column prop="product_name" label="品名" />
          <el-table-column prop="quantity" label="数量" width="80" />
          <el-table-column prop="unit_price" label="单价" width="80" />
          <el-table-column prop="unit" label="单位" width="60" />
          <el-table-column label="金额" width="80">
            <template #default="{ row }">{{ (row.quantity * row.unit_price).toFixed(2) }}</template>
          </el-table-column>
          <el-table-column label="操作" width="60">
            <template #default="{ $index }">
              <el-button size="small" type="danger" @click="form.items.splice($index, 1)">删</el-button>
            </template>
          </el-table-column>
        </el-table>

        <!-- 金额汇总 -->
        <el-row :gutter="16" style="margin-top:12px">
          <el-col :span="8">
            <el-form-item label="运费">
              <el-input-number v-model="form.freight" :min="0" controls-position="right" style="width:100%" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="折扣">
              <el-input-number v-model="form.discount_amount" :min="0" controls-position="right" style="width:100%" />
            </el-form-item>
          </el-col>
          <el-col :span="8" style="text-align:right;line-height:32px">
            商品合计: ¥{{ itemsTotal.toFixed(2) }}
          </el-col>
        </el-row>
      </el-form>

      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveOrder" :loading="saving">保存</el-button>
        <el-button v-if="!isEditMode" type="success" @click="saveAndNew" :loading="saving">保存并新建</el-button>
      </template>
    </el-dialog>

    <!-- 复制订单弹窗 -->
    <el-dialog v-model="copyDialogVisible" title="复制订单" width="420px">
      <el-form :model="copyForm" label-width="160px">
        <el-form-item label="复制订单类型">
          <el-select v-model="copyForm.copy_type" style="width: 100%">
            <el-option label="常规" value="normal" />
            <el-option label="是" value="yes" />
            <el-option label="否" value="no" />
          </el-select>
        </el-form-item>
        <el-form-item label="是否同步商品单价">
          <el-select v-model="copyForm.sync_unit_price" style="width: 100%">
            <el-option label="是" value="yes" />
            <el-option label="否" value="no" />
          </el-select>
        </el-form-item>
        <el-form-item label="是否同步单价变化率">
          <el-select v-model="copyForm.sync_price_change_rate" style="width: 100%">
            <el-option label="是" value="yes" />
            <el-option label="否" value="no" />
          </el-select>
        </el-form-item>
        <el-form-item label="是否复制出库数">
          <el-select v-model="copyForm.copy_outbound_quantity" style="width: 100%">
            <el-option label="是" value="yes" />
            <el-option label="否" value="no" />
          </el-select>
        </el-form-item>
        <el-alert
          v-if="copyForm.copy_outbound_quantity === 'yes'"
          title="同步出库数订单状态会变为分拣中"
          type="warning"
          :closable="false"
          show-icon
          style="margin-bottom: 12px"
        />
      </el-form>
      <template #footer>
        <el-button @click="copyDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmCopy" :loading="copying">确认</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Setting } from '@element-plus/icons-vue'
import FilterBar from '../components/FilterBar.vue'
import {
  getOrders, createOrder, updateOrder, deleteOrder, copyOrder,
  saveColumnPreference, getColumnPreference,
  type Order, type OrderCreateForm, type OrderCopyOptions,
} from '../api/order'

// ====================================================================
// 列定义（49 个可选字段）
// ====================================================================

interface ColumnDef {
  key: string
  label: string
  width?: number
  minWidth?: number
  mandatory?: boolean
}

const allColumnDefs: ColumnDef[] = [
  { key: 'order_no', label: '订单号', width: 180, mandatory: true },
  { key: 'merchant_tag', label: '商户标签', width: 120, mandatory: true },
  { key: 'order_status', label: '订单状态', width: 100, mandatory: true },
  { key: 'payment_status', label: '支付状态', width: 100, mandatory: true },
  // 基础字段
  { key: 'receive_start_date', label: '收货日期', width: 120 },
  { key: 'related_outbound_no', label: '关联出库单', width: 140 },
  { key: 'sorting_status', label: '分拣状态', width: 100 },
  { key: 'inspection_status', label: '验货状态', width: 100 },
  { key: 'cabinet_status', label: '投柜状态', width: 100 },
  { key: 'route_name', label: '线路', width: 100 },
  { key: 'merchant_name', label: '商户名/ID', width: 140 },
  { key: 'merchant_custom_code', label: '商户自定义编码', width: 140 },
  { key: 'custom_field_1', label: '商户定义字段1', width: 120 },
  { key: 'custom_field_2', label: '商户定义字段2', width: 120 },
  { key: 'custom_field_3', label: '商户定义字段3', width: 120 },
  { key: 'delivery_method', label: '收货方式', width: 100 },
  { key: 'pickup_point', label: '自提点', width: 100 },
  { key: 'order_type', label: '订单类型', width: 100 },
  // 金额字段
  { key: 'order_amount', label: '下单金额', width: 110 },
  { key: 'total_order_quantity', label: '总下单数', width: 100 },
  { key: 'accounting_quantity_sale', label: '记账数(销售)', width: 120 },
  { key: 'accounting_quantity_base', label: '记账数(基本)', width: 120 },
  { key: 'product_category_count', label: '商品种类数', width: 110 },
  { key: 'after_sale_amount', label: '订单售后', width: 100 },
  { key: 'should_refund_amount', label: '应退金额', width: 100 },
  { key: 'discount_amount', label: '优惠金额', width: 100 },
  { key: 'freight', label: '运费', width: 80 },
  { key: 'sales_amount_incl_freight', label: '销售额(含运费)', width: 130 },
  // 状态字段
  { key: 'edit_status', label: '编辑状态', width: 100 },
  { key: 'loading_status', label: '装车状态', width: 100 },
  { key: 'vehicle_status', label: '装车状态', width: 100 },
  { key: 'driver_name', label: '司机', width: 80 },
  { key: 'order_source', label: '订单来源', width: 100 },
  { key: 'print_status', label: '打印状态', width: 100 },
  { key: 'outbound_status', label: '出库状态', width: 100 },
  { key: 'remark', label: '订单备注', width: 150 },
  { key: 'batch_status', label: '集包状态', width: 100 },
  { key: 'operator', label: '下单员', width: 80 },
  { key: 'print_time', label: '打印时间', width: 140 },
  // 其他
  { key: 'batch_merchant_name', label: '分仓原始商户名', width: 140 },
  { key: 'main_sorting_category', label: '主分拣品类', width: 120 },
  { key: 'main_sorting_category_count', label: '主分拣品类数', width: 120 },
  { key: 'third_party_order_no', label: '第三方订单号', width: 140 },
]

const mandatoryKeys = allColumnDefs.filter(c => c.mandatory).map(c => c.key)
const defaultVisibleKeys = [...mandatoryKeys]

// ====================================================================
// 列选择器状态
// ====================================================================

const visibleColumnKeys = ref<string[]>([...defaultVisibleKeys])

const allColumnsSelected = computed(() => visibleColumnKeys.value.length === allColumnDefs.length)
const isIndeterminate = computed(() => {
  const count = visibleColumnKeys.value.length
  return count > 0 && count < allColumnDefs.length
})

function toggleAllColumns(checked: boolean) {
  visibleColumnKeys.value = checked ? allColumnDefs.map(c => c.key) : [...mandatoryKeys]
  persistColumnPreference()
}

function onColumnChange() {
  // 确保必选列始终包含
  for (const key of mandatoryKeys) {
    if (!visibleColumnKeys.value.includes(key)) {
      visibleColumnKeys.value.push(key)
    }
  }
  persistColumnPreference()
}

const activeColumns = computed(() =>
  allColumnDefs.filter(c => visibleColumnKeys.value.includes(c.key))
)

// ====================================================================
// 列偏好持久化（后端）
// ====================================================================

async function loadColumnPreference() {
  try {
    const { data } = await getColumnPreference('order_list')
    if (data.visible_columns && data.visible_columns.length > 0) {
      // 确保必选列始终包含
      const loaded = new Set(data.visible_columns)
      for (const key of mandatoryKeys) loaded.add(key)
      visibleColumnKeys.value = allColumnDefs.filter(c => loaded.has(c.key)).map(c => c.key)
    }
  } catch {
    // 首次使用，用默认值
  }
}

let persistTimer: ReturnType<typeof setTimeout> | null = null
function persistColumnPreference() {
  if (persistTimer) clearTimeout(persistTimer)
  persistTimer = setTimeout(() => {
    saveColumnPreference('order_list', visibleColumnKeys.value).catch(() => {})
  }, 500)
}

// ====================================================================
// 筛选栏配置
// ====================================================================

const filterConfigs = [
  { key: 'search', label: '', type: 'search' as const, placeholder: '搜索单号/商户名', width: '200px' },
  {
    key: 'order_status', label: '', type: 'select' as const, placeholder: '订单状态', width: '130px',
    options: [
      { value: 'pending', label: '待处理' },
      { value: 'sorting', label: '分拣中' },
      { value: 'delivered', label: '已出库' },
      { value: 'cancelled', label: '已取消' },
    ],
  },
  {
    key: 'payment_status', label: '', type: 'select' as const, placeholder: '支付状态', width: '130px',
    options: [
      { value: 'unpaid', label: '未支付' },
      { value: 'paid', label: '已支付' },
      { value: 'partial', label: '部分支付' },
    ],
  },
]

const filterValues = ref<Record<string, any>>({ search: '', order_status: '', payment_status: '' })

function resetFilters() {
  filterValues.value = { search: '', order_status: '', payment_status: '' }
  load()
}

// ====================================================================
// 数据加载
// ====================================================================

const router = useRouter()
const items = ref<Order[]>([])
const total = ref(0)
const loading = ref(false)
const page = ref(1)
const limit = ref(20)

async function load() {
  loading.value = true
  try {
    const { data } = await getOrders({
      search: filterValues.value.search,
      order_status: filterValues.value.order_status || undefined,
      limit: limit.value,
      offset: (page.value - 1) * limit.value,
    })
    items.value = data.items
    total.value = data.total
  } finally {
    loading.value = false
  }
}

// ====================================================================
// 状态显示
// ====================================================================

function orderStatusLabel(status: string) {
  const map: Record<string, string> = {
    pending: '待处理', sorting: '分拣中', delivered: '已出库', cancelled: '已取消',
  }
  return map[status] || status
}

function orderStatusType(status: string) {
  const map: Record<string, string> = {
    pending: 'info', sorting: 'warning', delivered: 'success', cancelled: 'danger',
  }
  return (map[status] || 'info') as any
}

function paymentStatusLabel(status: string) {
  const map: Record<string, string> = {
    unpaid: '未支付', paid: '已支付', partial: '部分支付',
  }
  return map[status] || status || '-'
}

function paymentStatusType(status: string) {
  const map: Record<string, string> = {
    unpaid: 'danger', paid: 'success', partial: 'warning',
  }
  return (map[status] || 'info') as any
}

// ====================================================================
// 新建/编辑订单
// ====================================================================

const dialogVisible = ref(false)
const saving = ref(false)
const isEditMode = ref(false)
const editingOrder = ref<Order | null>(null)

const emptyForm = (): OrderCreateForm => ({
  merchant_name: '', merchant_id: '', merchant_tag: '',
  order_date: new Date().toISOString().slice(0, 10),
  receive_start_date: '', receive_end_date: '', receive_start_time: '', receive_end_time: '',
  operation_time: '', delivery_method: '', receiver: '', delivery_address: '', sign_method: '',
  order_type: '', freight: 0, discount_amount: 0, remark: '',
  related_outbound_no: '', third_party_order_no: '',
  custom_field_1: '', custom_field_2: '', custom_field_3: '',
  items: [],
})

const form = reactive<OrderCreateForm>(emptyForm())
const newItem = reactive({ product_name: '', quantity: 0, unit_price: 0, unit: '斤' })

const itemsTotal = computed(() =>
  form.items.reduce((sum, it) => sum + it.quantity * it.unit_price, 0)
)

function openCreate() {
  isEditMode.value = false
  editingOrder.value = null
  Object.assign(form, emptyForm())
  dialogVisible.value = true
}

function openEdit(row: Order) {
  isEditMode.value = true
  editingOrder.value = row
  Object.assign(form, {
    merchant_name: row.merchant_name || '',
    merchant_id: row.merchant_id || '',
    merchant_tag: row.merchant_tag || '',
    order_date: row.order_date,
    receive_start_date: row.receive_start_date || '',
    receive_end_date: row.receive_end_date || '',
    receive_start_time: row.receive_start_time || '',
    receive_end_time: row.receive_end_time || '',
    operation_time: row.operation_time || '',
    delivery_method: row.delivery_method || '',
    receiver: row.receiver || '',
    delivery_address: row.delivery_address || '',
    sign_method: row.sign_method || '',
    order_type: row.order_type || '',
    freight: row.freight || 0,
    discount_amount: row.discount_amount || 0,
    remark: row.remark || '',
    related_outbound_no: row.related_outbound_no || '',
    third_party_order_no: row.third_party_order_no || '',
    custom_field_1: row.custom_field_1 || '',
    custom_field_2: row.custom_field_2 || '',
    custom_field_3: row.custom_field_3 || '',
    items: (row.items || []).map(it => ({
      product_name: it.product_name,
      quantity: it.quantity,
      unit_price: it.unit_price,
      unit: it.unit,
    })),
  })
  dialogVisible.value = true
}

function addItem() {
  if (!newItem.product_name) return
  form.items.push({ ...newItem })
  newItem.product_name = ''; newItem.quantity = 0; newItem.unit_price = 0; newItem.unit = '斤'
}

async function saveOrder() {
  if (!form.order_date) { ElMessage.warning('请选择下单日期'); return }
  if (form.items.length === 0) { ElMessage.warning('请添加至少一个商品'); return }
  saving.value = true
  try {
    if (isEditMode.value && editingOrder.value) {
      await updateOrder(editingOrder.value.id, { ...form })
      ElMessage.success('订单已更新')
    } else {
      await createOrder({ ...form })
      ElMessage.success('订单已创建')
    }
    dialogVisible.value = false
    load()
  } finally {
    saving.value = false
  }
}

async function saveAndNew() {
  await saveOrder()
  if (!saving.value) {
    Object.assign(form, emptyForm())
    dialogVisible.value = true
  }
}

// ====================================================================
// 删除订单
// ====================================================================

async function handleDelete(row: Order) {
  try {
    await ElMessageBox.confirm(
      `确定要删除订单 ${row.order_no} 吗？此操作不可撤销。`,
      '删除确认',
      { type: 'warning', confirmButtonText: '确定删除', cancelButtonText: '取消' }
    )
    await deleteOrder(row.id)
    ElMessage.success('订单已删除')
    load()
  } catch {
    // 用户取消
  }
}

// ====================================================================
// 复制订单
// ====================================================================

const copyDialogVisible = ref(false)
const copying = ref(false)
const copyingOrderId = ref(0)
const copyTargetType = ref<'order' | 'supplement'>('order')

const copyForm = reactive<OrderCopyOptions>({
  copy_type: 'normal',
  sync_unit_price: 'yes',
  sync_price_change_rate: 'yes',
  copy_outbound_quantity: 'no',
})

function handleCopyCommand(row: Order, command: string) {
  copyingOrderId.value = row.id
  copyTargetType.value = command as 'order' | 'supplement'
  // 重置表单
  copyForm.copy_type = 'normal'
  copyForm.sync_unit_price = 'yes'
  copyForm.sync_price_change_rate = 'yes'
  copyForm.copy_outbound_quantity = 'no'
  copyDialogVisible.value = true
}

async function confirmCopy() {
  copying.value = true
  try {
    const options: OrderCopyOptions = { ...copyForm }
    if (copyTargetType.value === 'supplement') {
      options.copy_type = 'no'
    }
    const { data } = await copyOrder(copyingOrderId.value, options)
    ElMessage.success(`订单已复制为 ${data.new_order_no}`)
    copyDialogVisible.value = false
    load()
  } finally {
    copying.value = false
  }
}

// ====================================================================
// 其他
// ====================================================================

function showDetail(row: Order) {
  router.push(`/orders/${row.id}`)
}

onMounted(() => {
  loadColumnPreference()
  load()
})
</script>

<style scoped>
.table-toolbar {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 8px;
}

.column-selector {
  max-height: 400px;
  overflow-y: auto;
}

.column-selector__header {
  padding: 4px 0;
}

.column-selector__item {
  padding: 2px 0;
}
</style>
