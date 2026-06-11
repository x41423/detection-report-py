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

    <!-- 批量操作栏 -->
    <el-card shadow="never" class="panel-card batch-bar" v-if="selectedOrders.length > 0">
      <div style="display:flex;align-items:center;gap:12px">
        <span>已选 <strong>{{ selectedOrders.length }}</strong> 个订单</span>
        <el-button
          v-if="canBatchSorting"
          type="primary" size="small"
          @click="batchOperate('set_sorting')"
        >批量改为分拣中</el-button>
        <el-button
          v-if="canBatchInDelivery"
          type="warning" size="small"
          @click="batchOperate('set_in_delivery')"
        >批量改为配送中</el-button>
        <el-button
          v-if="canBatchConfirm"
          type="success" size="small"
          @click="batchOperate('confirm_outbound')"
        >批量确认出库</el-button>
        <el-button
          v-if="canBatchArrived"
          type="primary" size="small"
          @click="batchOperate('set_arrived')"
        >批量改为已送达</el-button>
        <el-button
          v-if="canBatchCancel"
          type="warning" size="small"
          @click="batchOperate('cancel')"
        >批量取消</el-button>
        <el-button
          v-if="canBatchUndo"
          type="info" size="small"
          @click="batchOperate('undo_outbound')"
        >批量撤销出库</el-button>
        <el-button
          v-if="canBatchDelete"
          type="danger" size="small"
          @click="batchOperate('delete')"
        >批量删除</el-button>
        <el-button size="small" @click="clearSelection">取消选择</el-button>
      </div>
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
                <el-checkbox :value="col.key" :disabled="mandatoryKeys.includes(col.key)">
                  {{ col.label }}
                </el-checkbox>
              </div>
            </el-checkbox-group>
          </div>
        </el-popover>
      </div>

      <el-table :data="items" stripe v-loading="loading" @row-click="showDetail" @selection-change="onSelectionChange" ref="tableRef" :row-class-name="rowClassName" style="width: 100%">
                <!-- 勾选列 -->
        <el-table-column type="selection" width="40" fixed="left" />
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
              <el-tag :type="row.edit_status === 'frozen' ? 'info' : orderStatusType(row.order_status)" size="small">
                {{ row.edit_status === 'frozen' ? '❄️ 已冻结' : orderStatusLabel(row.order_status) }}
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
        <el-table-column label="操作" width="280" fixed="right">
          <template #default="{ row }">
            <el-button size="small" type="primary" link @click.stop="showDetail(row)">详情</el-button>

            <!-- 冻结态：只显示解冻 -->
            <template v-if="row.edit_status === 'frozen'">
              <el-button size="small" type="warning" link @click.stop="handleUnfreeze(row)">解冻</el-button>
            </template>

            <!-- 已取消：只显示删除（需退款后才能删） -->
            <template v-else-if="row.order_status === 'cancelled'">
              <el-button v-if="row.payment_status !== 'paid'" size="small" type="danger" link @click.stop="handleDelete(row)">删除</el-button>
            </template>

            <!-- 已出库 -->
            <template v-else-if="row.order_status === 'delivered'">
              <el-button size="small" type="warning" link @click.stop="handleUndoOutbound(row)">撤销出库</el-button>
              <el-button size="small" type="info" link @click.stop="handleFreeze(row)">冻结</el-button>
            </template>

            <!-- 待处理 / 分拣中 -->
            <template v-else>
              <el-button size="small" type="primary" link @click.stop="openEdit(row)">编辑</el-button>
              <el-button v-if="row.payment_status === 'paid' || row.payment_status === 'partial'" size="small" type="warning" link @click.stop="handleRefund(row)">退款</el-button>
              <el-button v-else size="small" type="danger" link @click.stop="handleCancel(row)">取消</el-button>
              <el-button size="small" type="info" link @click.stop="handleFreeze(row)">冻结</el-button>
            </template>

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
          <el-col :span="16">
            <el-form-item label="商户" required>
              <el-autocomplete
                v-model="merchantQuery"
                :fetch-suggestions="fetchMerchantSuggestions"
                placeholder="输入商户名称搜索..."
                :trigger-on-focus="false"
                clearable
                style="width:100%"
                @select="onMerchantSelect"
                @clear="onMerchantClear"
              >
                <template #default="{ item }">
                  <div v-if="item.action === 'create'" class="merchant-option merchant-option--create">
                    <el-icon style="margin-right:4px"><Plus /></el-icon> 新建商户「{{ merchantQuery }}」
                  </div>
                  <div v-else class="merchant-option">
                    <span class="merchant-option__name">{{ item.value }}</span>
                    <el-tag v-if="item.tag" size="small" type="info" style="margin-left:8px">{{ item.tag }}</el-tag>
                  </div>
                </template>
              </el-autocomplete>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="订单号">
              <el-input :model-value="isEditMode ? editingOrder?.order_no : '-'" disabled />
            </el-form-item>
          </el-col>
        </el-row>

        <!-- 阶段 2：商户选定后解锁 -->
        <template v-if="form.merchant_name">
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
            <el-autocomplete
              v-model="productQuery"
              :fetch-suggestions="fetchProductSuggestions"
              placeholder="搜索商品名称..."
              :trigger-on-focus="false"
              clearable
              style="width:100%"
              @select="onProductSelect"
            />
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
        </template>
        <!-- end v-if form.merchant_name -->
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
import api from '../api/client'
import { Setting } from '@element-plus/icons-vue'
import { Plus } from '@element-plus/icons-vue'
import FilterBar from '../components/FilterBar.vue'
import {
  getOrders, createOrder, updateOrder, deleteOrder, copyOrder,
  saveColumnPreference, getColumnPreference, undoOrderOutbound,
  type Order, type OrderCreateForm, type OrderCopyOptions,
} from '../api/order'
import { getSuppliers, type Supplier } from '../api/supplier'
import { getProducts, type Product } from '../api/product'

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
  { key: 'receive_start_date', label: '收货日期', minWidth: 120 },
  { key: 'related_outbound_no', label: '关联出库单', minWidth: 140 },
  { key: 'sorting_status', label: '分拣状态', minWidth: 100 },
  { key: 'inspection_status', label: '验货状态', minWidth: 100 },
  { key: 'cabinet_status', label: '投柜状态', minWidth: 100 },
  { key: 'route_name', label: '线路', minWidth: 100 },
  { key: 'merchant_name', label: '商户名/ID', minWidth: 140 },
  { key: 'merchant_custom_code', label: '商户自定义编码', minWidth: 140 },
  { key: 'custom_field_1', label: '商户定义字段1', minWidth: 120 },
  { key: 'custom_field_2', label: '商户定义字段2', minWidth: 120 },
  { key: 'custom_field_3', label: '商户定义字段3', minWidth: 120 },
  { key: 'delivery_method', label: '收货方式', minWidth: 100 },
  { key: 'pickup_point', label: '自提点', minWidth: 100 },
  { key: 'order_type', label: '订单类型', minWidth: 100 },
  // 金额字段
  { key: 'order_amount', label: '下单金额', minWidth: 110 },
  { key: 'total_order_quantity', label: '总下单数', minWidth: 100 },
  { key: 'accounting_quantity_sale', label: '记账数(销售)', minWidth: 120 },
  { key: 'accounting_quantity_base', label: '记账数(基本)', minWidth: 120 },
  { key: 'product_category_count', label: '商品种类数', minWidth: 110 },
  { key: 'after_sale_amount', label: '订单售后', minWidth: 100 },
  { key: 'should_refund_amount', label: '应退金额', minWidth: 100 },
  { key: 'discount_amount', label: '优惠金额', minWidth: 100 },
  { key: 'freight', label: '运费', minWidth: 80 },
  { key: 'sales_amount_incl_freight', label: '销售额(含运费)', minWidth: 130 },
  // 状态字段
  { key: 'edit_status', label: '编辑状态', minWidth: 100 },
  { key: 'loading_status', label: '装车状态', minWidth: 100 },
  { key: 'vehicle_status', label: '装车状态', minWidth: 100 },
  { key: 'driver_name', label: '司机', minWidth: 80 },
  { key: 'order_source', label: '订单来源', minWidth: 100 },
  { key: 'print_status', label: '打印状态', minWidth: 100 },
  { key: 'outbound_status', label: '出库状态', minWidth: 100 },
  { key: 'remark', label: '订单备注', minWidth: 150 },
  { key: 'batch_status', label: '集包状态', minWidth: 100 },
  { key: 'operator', label: '下单员', minWidth: 80 },
  { key: 'print_time', label: '打印时间', minWidth: 140 },
  // 其他
  { key: 'batch_merchant_name', label: '分仓原始商户名', minWidth: 140 },
  { key: 'main_sorting_category', label: '主分拣品类', minWidth: 120 },
  { key: 'main_sorting_category_count', label: '主分拣品类数', minWidth: 120 },
  { key: 'third_party_order_no', label: '第三方订单号', minWidth: 140 },
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
  {
    key: 'date_mode', label: '', type: 'select' as const, placeholder: '日期筛选方式', width: '150px',
    options: [
      { value: 'order_date', label: '按下单日期' },
      { value: 'receipt_date', label: '按收货日期' },
    ],
  },
  {
    key: 'date_range', label: '', type: 'date-range' as const,
    startPlaceholder: '开始日期', endPlaceholder: '结束日期', width: '260px',
  },
]

const todayStr = new Date().toISOString().slice(0, 10)

const filterValues = ref<Record<string, any>>({
  search: '', order_status: '', payment_status: '',
  date_mode: 'receipt_date',  // 默认按收货日期
  date_range: [todayStr, todayStr],  // 默认锁定今天
})

function resetFilters() {
  filterValues.value = {
    search: '', order_status: '', payment_status: '',
    date_mode: 'receipt_date',
    date_range: [todayStr, todayStr],
  }
  load()
}

// ====================================================================
// 数据加载
// ====================================================================

const router = useRouter()
const items = ref<Order[]>([])
const total = ref(0)
const loading = ref(false)
const selectedOrders = ref<Order[]>([])
const tableRef = ref()
const page = ref(1)
const limit = ref(20)

async function load() {
  loading.value = true
  try {
    const range = (filterValues.value.date_range as string[]) || []
    const { data } = await getOrders({
      search: filterValues.value.search,
      order_status: filterValues.value.order_status || undefined,
      date_mode: filterValues.value.date_mode || undefined,
      date_from: range[0] || undefined,
      date_to: range[1] || undefined,
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
    pending: '待处理', sorting: '分拣中', in_delivery: '配送中',
    delivered: '已出库', arrived: '已送达', cancelled: '已取消',
  }
  return map[status] || status
}

function orderStatusType(status: string) {
  const map: Record<string, string> = {
    pending: 'info', sorting: 'warning', in_delivery: '',
    delivered: 'success', arrived: '', cancelled: 'danger',
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

// ── 商户自动完成 ──
const merchantQuery = ref('')
let merchantSuggestionsTimer: ReturnType<typeof setTimeout> | null = null

async function fetchMerchantSuggestions(keyword: string, cb: (results: { value: string; tag?: string; supplier?: Supplier; action?: string }[]) => void) {
  if (!keyword || keyword.length < 1) { cb([]); return }
  if (merchantSuggestionsTimer) clearTimeout(merchantSuggestionsTimer)
  merchantSuggestionsTimer = setTimeout(async () => {
    try {
      const { data } = await getSuppliers({ search: keyword, limit: 10, status: 'active' })
      const results = (data.items || []).map((s: Supplier) => ({
        value: s.name,
        tag: s.supplier_type || undefined,
        supplier: s,
      }))
      // 追加"新建商户"选项
      if (results.length === 0 || keyword.length >= 2) {
        results.push({ value: keyword, tag: undefined, supplier: undefined, action: 'create' })
      }
      cb(results)
    } catch { cb([]) }
  }, 200)
}

function onMerchantSelect(item: { value: string; tag?: string; supplier?: Supplier; action?: string }) {
  if (item.action === 'create') {
    window.open('/merchants', '_blank')
    return
  }
  const s = item.supplier
  form.merchant_name = item.value
  form.merchant_tag = s?.supplier_type || ''
  form.receiver = s?.contact_person || s?.settlement_person || ''
  form.delivery_address = s?.contact_address || ''
}

function onMerchantClear() {
  form.merchant_name = ''
  form.merchant_tag = ''
  form.receiver = ''
  form.delivery_address = ''
}

// ── 商品自动完成 ──
const productQuery = ref('')
let productSuggestionsTimer: ReturnType<typeof setTimeout> | null = null

async function fetchProductSuggestions(keyword: string, cb: (results: { value: string; unit?: string; price?: number }[]) => void) {
  if (!keyword || keyword.length < 1) { cb([]); return }
  if (productSuggestionsTimer) clearTimeout(productSuggestionsTimer)
  productSuggestionsTimer = setTimeout(async () => {
    try {
      const { data } = await getProducts({ search: keyword, limit: 10, include_inactive: false })
      cb((data.items || []).map((p: Product) => ({
        value: p.name,
        unit: p.base_unit || undefined,
        price: p.suggested_min_cost || undefined,
      })))
    } catch { cb([]) }
  }, 200)
}

function onProductSelect(item: { value: string; unit?: string; price?: number }) {
  newItem.product_name = item.value
  if (item.unit) newItem.unit = item.unit
  if (item.price && item.price > 0) newItem.unit_price = item.price
  productQuery.value = ''
}

const itemsTotal = computed(() =>
  form.items.reduce((sum, it) => sum + it.quantity * it.unit_price, 0)
)

function openCreate() {
  isEditMode.value = false
  editingOrder.value = null
  Object.assign(form, emptyForm())
  // 默认收货日期：明天 5:00 - 17:00
  const tomorrow = new Date()
  tomorrow.setDate(tomorrow.getDate() + 1)
  const dateStr = tomorrow.toISOString().slice(0, 10)
  form.receive_start_date = dateStr
  form.receive_end_date = dateStr
  form.receive_start_time = '05:00'
  form.receive_end_time = '17:00'
  merchantQuery.value = ''
  productQuery.value = ''
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
  merchantQuery.value = row.merchant_name || ''
  dialogVisible.value = true
}

function addItem() {
  if (productQuery.value && !newItem.product_name) {
    newItem.product_name = productQuery.value
  }
  if (!newItem.product_name) return
  form.items.push({ ...newItem })
  newItem.product_name = ''; newItem.quantity = 0; newItem.unit_price = 0; newItem.unit = '斤'
  productQuery.value = ''
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
  } catch (e: any) {
    if (e !== 'cancel') ElMessage.error(e?.response?.data?.detail || '删除失败')
  }
}

async function handleUndoOutbound(row: Order) {
  try {
    await ElMessageBox.confirm(
      `确定要撤销订单 ${row.order_no} 的出库吗？库存将恢复，订单状态退回待处理。`,
      '撤销出库确认',
      { type: 'warning', confirmButtonText: '确定撤销', cancelButtonText: '取消' }
    )
    await undoOrderOutbound(row.id)
    ElMessage.success('出库已撤销，库存已恢复')
    load()
  } catch (e: any) {
    if (e !== 'cancel') ElMessage.error(e?.response?.data?.detail || '撤销失败')
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
  } catch (e: any) { ElMessage.error(e?.response?.data?.detail || '复制订单失败') } finally {
    copying.value = false
  }
}

// ====================================================================
// 其他
// ====================================================================

function showDetail(row: Order) {
  router.push(`/orders/${row.id}`)
}

// ====================================================================
// 批量操作
// ====================================================================

function onSelectionChange(rows: Order[]) {
  selectedOrders.value = rows
}

function rowClassName({ row }: { row: Order }) {
  if (row.edit_status === 'frozen') return 'row-frozen'
  return ''
}

function clearSelection() {
  tableRef.value?.clearSelection()
}

const canBatchSorting = computed(() =>
  selectedOrders.value.length > 0 &&
  selectedOrders.value.every(o => o.order_status === 'pending')
)

const canBatchInDelivery = computed(() =>
  selectedOrders.value.length > 0 &&
  selectedOrders.value.every(o => o.order_status === 'sorting')
)

const canBatchConfirm = computed(() =>
  selectedOrders.value.length > 0 &&
  selectedOrders.value.every(o => o.order_status === 'in_delivery')
)

const canBatchArrived = computed(() =>
  selectedOrders.value.length > 0 &&
  selectedOrders.value.every(o => o.order_status === 'delivered')
)

const canBatchCancel = computed(() =>
  selectedOrders.value.length > 0 &&
  selectedOrders.value.every(o => ['pending', 'sorting'].includes(o.order_status))
)

const canBatchUndo = computed(() =>
  selectedOrders.value.length > 0 &&
  selectedOrders.value.every(o => o.order_status === 'delivered')
)

const canBatchDelete = computed(() =>
  selectedOrders.value.length > 0 &&
  selectedOrders.value.every(o => o.order_status === 'cancelled')
)

async function handleCancel(row: Order) {
  try {
    await ElMessageBox.confirm(
      row.order_status === 'sorting'
        ? `订单 ${row.order_no} 正在分拣中，确定取消？`
        : `确定取消订单 ${row.order_no}？`,
      '取消订单',
      { type: 'warning' }
    )
  } catch { return }
  try {
    await api.delete(`/api/order/${row.id}`)
    ElMessage.success('订单已取消')
    await load()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || e?.message || '取消失败')
  }
}

async function handleRefund(row: Order) {
  try {
    await ElMessageBox.confirm(`确定标记订单 ${row.order_no} 已退款？`, '退款确认', { type: 'warning' })
  } catch { return }
  try {
    await api.post(`/api/order/${row.id}/refund`)
    ElMessage.success('已退款')
    await load()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || e?.message || '退款失败')
  }
}

async function handleFreeze(row: Order) {
  try {
    await ElMessageBox.confirm(`确定冻结订单 ${row.order_no}？冻结后不可编辑/取消/出库。`, '冻结确认', { type: 'warning' })
  } catch { return }
  try {
    await api.post(`/api/order/${row.id}/freeze`)
    ElMessage.success('已冻结')
    await load()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || e?.message || '冻结失败')
  }
}

async function handleUnfreeze(row: Order) {
  try {
    await api.post(`/api/order/${row.id}/unfreeze`)
    ElMessage.success('已解冻')
    await load()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || e?.message || '解冻失败')
  }
}

async function batchOperate(action: string) {
  const labels: Record<string, string> = {
    confirm_outbound: '确认出库',
    cancel: '取消',
    undo_outbound: '撤销出库',
    delete: '删除',
  }
  const label = labels[action] || action
  try {
    await ElMessageBox.confirm(
      `确定要对 ${selectedOrders.value.length} 个订单执行「${label}」吗？`,
      '批量操作确认',
      { type: 'warning' }
    )
  } catch {
    return
  }
  try {
    const ids = selectedOrders.value.map(o => o.id)
    await api.post('/api/order/batch', { order_ids: ids, action })
    ElMessage.success(`${label}成功，共 ${ids.length} 个订单`)
    clearSelection()
    await load()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || e?.message || '批量操作失败')
  }
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
.merchant-option--create {
  color: var(--el-color-primary);
  font-weight: 500;
}

.row-frozen {
  background-color: #e6f0fa !important;
}
.row-frozen .el-table__cell {
  background-color: #e6f0fa !important;
}

<style scoped>
.order-page {
  max-width: none !important;
  width: 100%;
}
.row-frozen {
  background-color: #e6f0fa !important;
}
.row-frozen .el-table__cell {
  background-color: #e6f0fa !important;
}
</style>
