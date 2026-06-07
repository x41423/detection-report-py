<template>
  <div class="page-shell supplier-detail-page page-shell--full">
    <!-- 顶部 -->
    <div class="detail-header">
      <el-button @click="$router.push('/suppliers')" text>
        <el-icon><ArrowLeft /></el-icon> 返回列表
      </el-button>
      <div class="detail-header__title">
        <h2>{{ supplier.name || '加载中...' }}</h2>
        <el-tag :type="supplier.status === 'active' ? 'success' : 'info'" size="small">
          {{ supplier.status === 'active' ? '活跃' : '停用' }}
        </el-tag>
        <el-tag v-if="supplier.freeze_status" type="danger" size="small">已冻结</el-tag>
      </div>
      <div class="detail-header__actions">
        <el-button type="primary" @click="$router.push(`/suppliers?edit=${supplier.id}`)">编辑</el-button>
      </div>
    </div>

    <!-- 标签页 -->
    <el-card shadow="never" class="panel-card" v-loading="loading">
      <el-tabs v-model="activeTab">
        <!-- Tab 1: 基本信息 -->
        <el-tab-pane label="基本信息" name="basic">
          <el-descriptions :column="2" border size="small">
            <el-descriptions-item label="编码">{{ supplier.code }}</el-descriptions-item>
            <el-descriptions-item label="名称">{{ supplier.name }}</el-descriptions-item>
            <el-descriptions-item label="联系人">{{ supplier.contact_person || '-' }}</el-descriptions-item>
            <el-descriptions-item label="电话">{{ supplier.contact_phone || '-' }}</el-descriptions-item>
            <el-descriptions-item label="地址" :span="2">{{ supplier.contact_address || '-' }}</el-descriptions-item>
            <el-descriptions-item label="类型">
              <el-tag :type="typeTag(supplier.supplier_type)" size="small">{{ supplierTypeLabel(supplier.supplier_type) }}</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="等级">
              <el-tag :type="levelTag(supplier.level)" size="small">{{ levelLabel(supplier.level) }}</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="营业执照">{{ supplier.business_license || '-' }}</el-descriptions-item>
            <el-descriptions-item label="税号">{{ supplier.tax_number || '-' }}</el-descriptions-item>
            <el-descriptions-item label="银行名称">{{ supplier.bank_name || '-' }}</el-descriptions-item>
            <el-descriptions-item label="银行账号">{{ supplier.bank_account || '-' }}</el-descriptions-item>
            <el-descriptions-item label="信用额度">¥{{ (supplier.credit_limit || 0).toFixed(2) }}</el-descriptions-item>
            <el-descriptions-item label="审核状态">
              <el-tag :type="supplier.approval_status ? 'success' : 'warning'" size="small">
                {{ supplier.approval_status ? '已审核' : '待审核' }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="备注" :span="2">{{ supplier.remark || '-' }}</el-descriptions-item>
            <el-descriptions-item label="创建时间">{{ supplier.created_at }}</el-descriptions-item>
            <el-descriptions-item label="更新时间">{{ supplier.updated_at }}</el-descriptions-item>
          </el-descriptions>
        </el-tab-pane>

        <!-- Tab 2: 结算配置 -->
        <el-tab-pane label="结算配置" name="settlement">
          <el-descriptions :column="2" border size="small">
            <el-descriptions-item label="结算人">{{ supplier.settlement_person || supplier.contact_person || '-' }}</el-descriptions-item>
            <el-descriptions-item label="结算人电话">{{ supplier.settlement_phone || supplier.contact_phone || '-' }}</el-descriptions-item>
            <el-descriptions-item label="结算方式">{{ settlementMethodLabel(supplier.settlement_method) }}</el-descriptions-item>
            <el-descriptions-item label="结款周期">{{ settlementPeriodLabel(supplier.settlement_method) }}</el-descriptions-item>
            <el-descriptions-item label="日期维度">{{ supplier.date_dimension === 'receipt_date' ? '按收货日期' : '按下单日期' }}</el-descriptions-item>
            <el-descriptions-item label="账期起始日">每月 {{ supplier.period_start_day || 1 }} 日</el-descriptions-item>
            <el-descriptions-item label="结算日">每月 {{ supplier.settlement_day || 1 }} 日</el-descriptions-item>
            <el-descriptions-item label="分拣优先级">{{ supplier.sorting_priority || 0 }}</el-descriptions-item>
            <el-descriptions-item label="冻结状态">
              <el-tag :type="supplier.freeze_status ? 'danger' : 'success'" size="small">
                {{ supplier.freeze_status ? '已冻结' : '正常' }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="支付条款">{{ supplier.payment_terms || '-' }}</el-descriptions-item>
          </el-descriptions>
        </el-tab-pane>

        <!-- Tab 3: 交易概况 -->
        <el-tab-pane label="交易概况" name="transaction">
          <div class="transaction-filter">
            <el-date-picker
              v-model="txDateRange"
              type="daterange"
              range-separator="~"
              start-placeholder="开始日期"
              end-placeholder="结束日期"
              value-format="YYYY-MM-DD"
              style="width: 280px"
              @change="loadTransaction"
            />
            <el-button type="primary" @click="loadTransaction" style="margin-left: 8px">查询</el-button>
          </div>
          <el-row :gutter="16" style="margin-top: 16px" v-loading="txLoading">
            <el-col :span="6">
              <el-statistic title="销售额（含运）" :value="txSummary.total_sales_amount" prefix="¥" :precision="2" />
            </el-col>
            <el-col :span="6">
              <el-statistic title="销售额（不含运）" :value="txSummary.total_sales_amount_excl_freight" prefix="¥" :precision="2" />
            </el-col>
            <el-col :span="6">
              <el-statistic title="毛利" :value="txSummary.total_gross_margin" prefix="¥" :precision="2" />
            </el-col>
            <el-col :span="6">
              <el-statistic title="毛利率" :value="txSummary.gross_margin_rate" suffix="%" :precision="2" />
            </el-col>
          </el-row>
          <el-row :gutter="16" style="margin-top: 16px">
            <el-col :span="6">
              <el-statistic title="折扣金额" :value="txSummary.total_discount" prefix="¥" :precision="2" />
            </el-col>
            <el-col :span="6">
              <el-statistic title="订单数" :value="txSummary.order_count" />
            </el-col>
            <el-col :span="6">
              <el-statistic title="售后订单" :value="txSummary.after_sale_count" />
            </el-col>
            <el-col :span="6">
              <el-statistic title="异常金额" :value="txSummary.abnormal_amount" prefix="¥" :precision="2" />
            </el-col>
          </el-row>
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ArrowLeft } from '@element-plus/icons-vue'
import { getSupplier } from '../api/supplier'
import api from '../api/client'
import type { Supplier } from '../api/supplier'

const route = useRoute()
const supplierId = Number(route.params.id)
const loading = ref(true)
const activeTab = ref('basic')

const supplier = ref<Supplier>({} as Supplier)

// ── Transaction summary ──
const txLoading = ref(false)
const txDateRange = ref<string[]>([])
const txSummary = ref({
  total_sales_amount: 0, total_sales_amount_excl_freight: 0,
  total_gross_margin: 0, gross_margin_rate: 0,
  total_discount: 0, order_count: 0,
  after_sale_count: 0, abnormal_amount: 0,
  should_refund: 0, actual_refund: 0,
})

async function loadSupplier() {
  loading.value = true
  try {
    const { data } = await getSupplier(supplierId)
    supplier.value = data as Supplier
  } finally {
    loading.value = false
  }
}

async function loadTransaction() {
  txLoading.value = true
  try {
    const params: Record<string, string> = {}
    if (txDateRange.value?.[0]) params.date_from = txDateRange.value[0]
    if (txDateRange.value?.[1]) params.date_to = txDateRange.value[1]
    const { data } = await api.get(`/api/supplier/${supplierId}/transaction-summary`, { params })
    txSummary.value = data
  } finally {
    txLoading.value = false
  }
}

// ── Helpers ──
function supplierTypeLabel(t: string) {
  return { enterprise: '企业', individual: '个人', cooperative: '合作社' }[t] || t
}
function typeTag(t: string) {
  return { enterprise: 'primary', cooperative: 'success', individual: 'info' }[t] || 'info'
}
function levelLabel(l: string) {
  return { vip: 'VIP', normal: '普通', temporary: '临时' }[l] || l
}
function levelTag(l: string) {
  return { vip: 'danger', normal: 'primary', temporary: 'info' }[l] || 'info'
}
function settlementMethodLabel(m: string) {
  return { cash: '现金', prepaid: '先款后货', credit: '先货后款' }[m] || m
}
function settlementPeriodLabel(m: string) {
  return { daily: '日结', weekly: '周结', monthly: '月结' }[m] || m
}

onMounted(() => {
  loadSupplier()
})
</script>

<style scoped>
.detail-header {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 12px 0;
  flex-wrap: wrap;
}
.detail-header__title {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
}
.detail-header__title h2 {
  margin: 0;
  font-size: 20px;
}
.transaction-filter {
  display: flex;
  align-items: center;
}
</style>
