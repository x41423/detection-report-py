<template>
  <div class="page-shell order-detail-page page-shell--full">
    <PageHero eyebrow="订单管理" title="订单详情" :description="`订单号: ${order.order_no || '-'}`" tone="teal">
      <template #actions>
        <el-button @click="goBack">返回列表</el-button>
        <el-button type="primary" @click="handleEdit">追加修改</el-button>
        <el-button @click="handlePrint">打印</el-button>
        <el-dropdown trigger="click" @command="handleMoreCommand">
          <el-button>更多功能</el-button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="copy-order">复制到订单</el-dropdown-item>
              <el-dropdown-item command="copy-supplement">复制到补单</el-dropdown-item>
              <el-dropdown-item command="delete" divided>删除订单</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </template>
    </PageHero>

    <!-- 订单头部信息 -->
    <el-card shadow="never" class="panel-card order-header-card">
      <el-row :gutter="24">
        <!-- 左侧：财务汇总 -->
        <el-col :span="8">
          <div class="finance-summary">
            <div class="finance-item">
              <span class="finance-label">下单金额</span>
              <span class="finance-value primary">¥{{ formatMoney(order.order_amount) }}</span>
            </div>
            <div class="finance-item">
              <span class="finance-label">出库金额</span>
              <span class="finance-value">¥{{ formatMoney(order.order_amount) }}</span>
            </div>
            <div class="finance-item">
              <span class="finance-label">订单销售额 (含税、运)</span>
              <span class="finance-value">¥{{ formatMoney(order.sales_amount_incl_freight) }}</span>
            </div>
            <div class="finance-item">
              <span class="finance-label">订单销售额 (不含税、运)</span>
              <span class="finance-value">¥{{ formatMoney(order.sales_amount_incl_freight) }}</span>
            </div>
            <div class="finance-item">
              <span class="finance-label">订单税额</span>
              <span class="finance-value">¥0.00</span>
            </div>
          </div>
        </el-col>

        <!-- 右侧：订单信息 -->
        <el-col :span="16">
          <el-descriptions :column="2" border size="small">
            <el-descriptions-item label="订单号">
              <span class="order-no">{{ order.order_no }}</span>
              <el-tag :type="orderStatusType(order.order_status)" size="small" style="margin-left: 8px">
                {{ orderStatusLabel(order.order_status) }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="商户">
              <span class="merchant-link">{{ order.merchant_name || '-' }}/{{ order.merchant_id || '-' }}</span>
            </el-descriptions-item>
            <el-descriptions-item label="关联出库单号">
              {{ order.related_outbound_no || '-' }}
            </el-descriptions-item>
            <el-descriptions-item label="运营时间">
              {{ order.operation_time || '默认运营时间' }}
            </el-descriptions-item>
            <el-descriptions-item label="收货时间">
              {{ formatReceiveTime() }}
            </el-descriptions-item>
            <el-descriptions-item label="订单备注">
              {{ order.remark || '-' }}
            </el-descriptions-item>
            <el-descriptions-item label="订单类型">
              {{ orderTypeLabel(order.order_type) }}
            </el-descriptions-item>
            <el-descriptions-item label="下单时间">
              {{ order.created_at || '-' }}
            </el-descriptions-item>
            <el-descriptions-item label="收货方式">
              {{ deliveryMethodLabel(order.delivery_method) }}
            </el-descriptions-item>
            <el-descriptions-item label="收货人">
              {{ order.receiver || '-' }}
            </el-descriptions-item>
            <el-descriptions-item label="收货地址" :span="2">
              {{ order.delivery_address || '-' }}
            </el-descriptions-item>
            <el-descriptions-item label="最后操作">
              {{ order.updated_at || '-' }}
            </el-descriptions-item>
            <el-descriptions-item label="签收方式">
              {{ signMethodLabel(order.sign_method) }}
            </el-descriptions-item>
          </el-descriptions>
        </el-col>
      </el-row>
    </el-card>

    <!-- 订单明细 Tab -->
    <el-card shadow="never" class="panel-card">
      <el-tabs v-model="activeTab">
        <el-tab-pane label="订单明细" name="detail">
          <template #label>
            订单明细
            <el-badge :value="order.items?.length || 0" :max="99" class="tab-badge" />
          </template>
        </el-tab-pane>
        <el-tab-pane label="商品列表" name="products" />
        <el-tab-pane label="运费" name="freight">
          <template #label>
            运费: ¥{{ formatMoney(order.freight) }}
          </template>
        </el-tab-pane>
        <el-tab-pane label="分类统计" name="category-stats" />
      </el-tabs>

      <!-- 订单明细表格 -->
      <div v-if="activeTab === 'detail'">
        <div class="table-toolbar">
          <el-button size="small" @click="handleModifyOrder">修改顺序</el-button>
          <el-dropdown trigger="click">
            <el-button size="small">更多功能</el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item>批量修改</el-dropdown-item>
                <el-dropdown-item>导出明细</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>

        <el-table :data="order.items" stripe border style="width: 100%" size="small">
          <el-table-column label="商品图" width="80">
            <template #default>
              <el-avatar shape="square" :size="40" :icon="PictureFilled" />
            </template>
          </el-table-column>
          <el-table-column type="index" label="序号" width="60" />
          <el-table-column prop="product_id" label="规格ID" width="120" />
          <el-table-column prop="product_name" label="规格名" min-width="120" />
          <el-table-column prop="unit" label="规格" width="80" />
          <el-table-column prop="category" label="分类" width="100" />
          <el-table-column label="报价单简称" width="120">
            <template #default>-</template>
          </el-table-column>
          <el-table-column label="下单数" width="100">
            <template #default="{ row }">{{ row.quantity }}{{ row.unit }}</template>
          </el-table-column>
          <el-table-column label="单价(销售单位)" width="130">
            <template #default="{ row }">{{ row.unit_price }}元/{{ row.unit }}</template>
          </el-table-column>
          <el-table-column label="不含税单价" width="110">
            <template #default>-</template>
          </el-table-column>
          <el-table-column label="下单金额" width="100">
            <template #default="{ row }">{{ formatMoney(row.amount) }}元</template>
          </el-table-column>
          <el-table-column label="最近销售单价(基本)" width="160">
            <template #default>-</template>
          </el-table-column>
          <el-table-column label="最近销售单价(销售)" width="160">
            <template #default>-</template>
          </el-table-column>
          <el-table-column label="实收照片" width="100">
            <template #default>-</template>
          </el-table-column>
          <el-table-column label="出库数" width="100">
            <template #default="{ row }">
              <span v-if="order.order_status === 'delivered'">{{ row.quantity }}{{ row.unit }}</span>
              <span v-else>-</span>
            </template>
          </el-table-column>
          <el-table-column label="异常数" width="80">
            <template #default>-</template>
          </el-table-column>
          <el-table-column label="备注" width="120">
            <template #default>-</template>
          </el-table-column>
          <el-table-column label="对公转账" width="100">
            <template #default>-</template>
          </el-table-column>
          <el-table-column label="商品保质期" width="110">
            <template #default>-</template>
          </el-table-column>
          <el-table-column label="操作" width="80" fixed="right">
            <template #default>
              <el-button size="small" type="primary" link>编辑</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <!-- 商品列表 Tab -->
      <div v-if="activeTab === 'products'">
        <el-table :data="order.items" stripe border style="width: 100%" size="small">
          <el-table-column type="index" label="序号" width="60" />
          <el-table-column prop="product_name" label="商品名称" min-width="150" />
          <el-table-column prop="category" label="分类" width="120" />
          <el-table-column prop="unit" label="单位" width="80" />
          <el-table-column label="下单数" width="100">
            <template #default="{ row }">{{ row.quantity }}{{ row.unit }}</template>
          </el-table-column>
          <el-table-column label="单价" width="100">
            <template #default="{ row }">{{ row.unit_price }}元/{{ row.unit }}</template>
          </el-table-column>
          <el-table-column label="金额" width="100">
            <template #default="{ row }">{{ formatMoney(row.amount) }}元</template>
          </el-table-column>
        </el-table>
      </div>

      <!-- 运费 Tab -->
      <div v-if="activeTab === 'freight'">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="运费金额">¥{{ formatMoney(order.freight) }}</el-descriptions-item>
          <el-descriptions-item label="运费类型">-</el-descriptions-item>
          <el-descriptions-item label="运费备注">-</el-descriptions-item>
        </el-descriptions>
      </div>

      <!-- 分类统计 Tab -->
      <div v-if="activeTab === 'category-stats'">
        <el-table :data="categoryStats" stripe border style="width: 100%" size="small">
          <el-table-column prop="category" label="分类" min-width="150" />
          <el-table-column prop="count" label="商品种类" width="100" />
          <el-table-column prop="quantity" label="总数量" width="100" />
          <el-table-column prop="amount" label="总金额" width="120">
            <template #default="{ row }">¥{{ formatMoney(row.amount) }}</template>
          </el-table-column>
        </el-table>
      </div>
    </el-card>

    <!-- 操作日志（占位） -->
    <el-card shadow="never" class="panel-card">
      <template #header>
        <div class="log-header" @click="logExpanded = !logExpanded">
          <span>操作日志</span>
          <el-icon><ArrowDown v-if="!logExpanded" /><ArrowUp v-else /></el-icon>
        </div>
      </template>
      <div v-if="logExpanded" class="log-content">
        <el-empty description="暂无操作日志" />
      </div>
    </el-card>

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
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { PictureFilled, ArrowDown, ArrowUp } from '@element-plus/icons-vue'
import PageHero from '../components/PageHero.vue'
import {
  getOrder, deleteOrder, copyOrder,
  type Order, type OrderCopyOptions,
} from '../api/order'

const route = useRoute()
const router = useRouter()

// ====================================================================
// 数据
// ====================================================================

const order = ref<Order>({} as Order)
const loading = ref(false)
const activeTab = ref('detail')
const logExpanded = ref(false)

// ====================================================================
// 加载订单
// ====================================================================

async function loadOrder() {
  const id = Number(route.params.id)
  if (!id) { ElMessage.error('订单ID无效'); return }
  loading.value = true
  try {
    const { data } = await getOrder(id)
    order.value = (data as any).item ?? data
  } catch {
    ElMessage.error('加载订单失败')
  } finally {
    loading.value = false
  }
}

// ====================================================================
// 分类统计
// ====================================================================

const categoryStats = computed(() => {
  const stats: Record<string, { category: string; count: number; quantity: number; amount: number }> = {}
  for (const item of order.value.items || []) {
    const cat = item.category || '未分类'
    if (!stats[cat]) stats[cat] = { category: cat, count: 0, quantity: 0, amount: 0 }
    stats[cat].count++
    stats[cat].quantity += item.quantity
    stats[cat].amount += item.amount
  }
  return Object.values(stats)
})

// ====================================================================
// 状态显示
// ====================================================================

function orderStatusLabel(status: string) {
  const map: Record<string, string> = {
    pending: '待处理', sorting: '分拣中', delivered: '已出库', cancelled: '已取消',
  }
  return map[status] || status || '-'
}

function orderStatusType(status: string) {
  const map: Record<string, string> = {
    pending: 'info', sorting: 'warning', delivered: 'success', cancelled: 'danger',
  }
  return (map[status] || 'info') as any
}

function orderTypeLabel(type: string) {
  const map: Record<string, string> = {
    normal: '常规-后台下单', urgent: '加急订单', supplement: '补单',
  }
  return map[type] || type || '-'
}

function deliveryMethodLabel(method: string) {
  const map: Record<string, string> = {
    pickup: '自提', delivery: '配送', express: '快递',
  }
  return map[method] || method || '-'
}

function signMethodLabel(method: string) {
  const map: Record<string, string> = {
    scan: '扫码签收', manual: '手动签收', none: '无需签收',
  }
  return map[method] || method || '-'
}

function formatReceiveTime() {
  const start = order.value.receive_start_date
  const end = order.value.receive_end_date
  if (!start && !end) return '-'
  if (start === end) return start
  return `${start || '-'} ~ ${end || '-'}`
}

function formatMoney(amount: number | undefined) {
  return (amount || 0).toFixed(2)
}

// ====================================================================
// 操作
// ====================================================================

function goBack() {
  router.push('/orders')
}

function handleEdit() {
  // TODO: 打开编辑弹窗
  ElMessage.info('编辑功能开发中')
}

function handlePrint() {
  window.print()
}

function handleModifyOrder() {
  ElMessage.info('修改顺序功能开发中')
}

async function handleMoreCommand(command: string) {
  if (command === 'delete') {
    try {
      await ElMessageBox.confirm(
        `确定要删除订单 ${order.value.order_no} 吗？`,
        '删除确认',
        { type: 'warning' }
      )
      await deleteOrder(order.value.id)
      ElMessage.success('订单已删除')
      router.push('/orders')
    } catch (e: any) { ElMessage.error(e?.response?.data?.detail || \'操作失败\') }
  } else if (command === 'copy-order' || command === 'copy-supplement') {
    copyTargetType.value = command === 'copy-supplement' ? 'supplement' : 'order'
    copyForm.copy_type = 'normal'
    copyForm.sync_unit_price = 'yes'
    copyForm.sync_price_change_rate = 'yes'
    copyForm.copy_outbound_quantity = 'no'
    copyDialogVisible.value = true
  }
}

// ====================================================================
// 复制订单
// ====================================================================

const copyDialogVisible = ref(false)
const copying = ref(false)
const copyTargetType = ref<'order' | 'supplement'>('order')

const copyForm = reactive<OrderCopyOptions>({
  copy_type: 'normal',
  sync_unit_price: 'yes',
  sync_price_change_rate: 'yes',
  copy_outbound_quantity: 'no',
})

async function confirmCopy() {
  copying.value = true
  try {
    const options: OrderCopyOptions = { ...copyForm }
    if (copyTargetType.value === 'supplement') {
      options.copy_type = 'no'
    }
    const { data } = await copyOrder(order.value.id, options)
    ElMessage.success(`订单已复制为 ${data.new_order_no}`)
    copyDialogVisible.value = false
    router.push(`/orders/${data.new_order_id}`)
  } finally {
    copying.value = false
  }
}

// ====================================================================
// 初始化
// ====================================================================

onMounted(loadOrder)
</script>

<style scoped>
.order-header-card {
  margin-bottom: 16px;
}

.finance-summary {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.finance-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 0;
  border-bottom: 1px solid var(--el-border-color-lighter);
}

.finance-label {
  font-size: 13px;
  color: var(--el-text-color-regular);
}

.finance-value {
  font-size: 14px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.finance-value.primary {
  color: var(--el-color-primary);
  font-size: 16px;
}

.order-no {
  font-weight: 600;
  color: var(--el-color-primary);
}

.merchant-link {
  color: var(--el-color-primary);
  cursor: pointer;
}

.table-toolbar {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-bottom: 12px;
}

.tab-badge {
  margin-left: 4px;
}

.log-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  cursor: pointer;
}

.log-content {
  min-height: 100px;
}

/* 打印样式 */
@media print {
  .page-hero,
  .table-toolbar,
  .el-button,
  .el-dropdown {
    display: none !important;
  }
}
</style>
