import { computed, onMounted, reactive, ref, type Ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'

import {
  createInventoryAdjustment,
  createInventoryOutbound,
  deleteInventoryAdjustment,
  deleteInventoryOutbound,
  exportInventoryBalances,
  getApiErrorMessage,
  getConfig,
  getDailyIntakeByDate,
  getInventoryBalances,
  getInventoryTransactions,
  updateConfig,
  updateInventoryAdjustment,
  updateInventoryOutbound,
} from '../../../api'
import { appendStatus, type StatusLogHandle } from '../../shared/workflow'
import { DAILY_INTAKE_UNITS, type DailyIntakeSheet } from '../../daily-intake/types'
import type {
  InventoryBalance,
  InventoryDirection,
  InventoryTransaction,
} from '../types'

interface OutboundDraftState {
  name: string
  unit: string
  quantity: number | null
  note: string
}

interface AdjustmentDraftState {
  name: string
  unit: string
  targetQuantity: number | null
  note: string
}

interface EditDraftState {
  id: number | null
  direction: InventoryDirection
  name: string
  unit: string
  quantity: number | null
  targetQuantity: number | null
  note: string
  businessDate: string
}

function formatLocalDate(target: Date) {
  const year = target.getFullYear()
  const month = `${target.getMonth() + 1}`.padStart(2, '0')
  const day = `${target.getDate()}`.padStart(2, '0')
  return `${year}-${month}-${day}`
}

function createOutboundDraft(): OutboundDraftState {
  return {
    name: '',
    unit: DAILY_INTAKE_UNITS[0],
    quantity: null,
    note: '',
  }
}

function createAdjustmentDraft(): AdjustmentDraftState {
  return {
    name: '',
    unit: DAILY_INTAKE_UNITS[0],
    targetQuantity: null,
    note: '',
  }
}

function createEditDraft(businessDate: string): EditDraftState {
  return {
    id: null,
    direction: 'OUT',
    name: '',
    unit: DAILY_INTAKE_UNITS[0],
    quantity: null,
    targetQuantity: null,
    note: '',
    businessDate,
  }
}

export function useInventoryWorkflow(statusLogRef: Ref<StatusLogHandle | undefined>) {
  const selectedDate = ref(formatLocalDate(new Date()))
  const inboundSheet = ref<DailyIntakeSheet | null>(null)
  const balances = ref<InventoryBalance[]>([])
  const transactions = ref<InventoryTransaction[]>([])

  const balanceSearch = ref('')
  const transactionSearch = ref('')
  const transactionSourceFilter = ref<'all' | 'daily_intake' | 'manual_outbound' | 'manual_adjust'>('all')
  const lowStockThreshold = ref(3)

  const loadingInbound = ref(false)
  const loadingBalances = ref(false)
  const loadingTransactions = ref(false)
  const submittingOutbound = ref(false)
  const submittingAdjustment = ref(false)
  const savingThreshold = ref(false)
  const exportingBalances = ref(false)
  const editDialogVisible = ref(false)
  const editSaving = ref(false)
  const deletingTransactionId = ref<number | null>(null)

  const outboundDraft = reactive<OutboundDraftState>(createOutboundDraft())
  const adjustmentDraft = reactive<AdjustmentDraftState>(createAdjustmentDraft())
  const editDraft = reactive<EditDraftState>(createEditDraft(selectedDate.value))

  const positiveBalanceCount = computed(() => balances.value.filter((item) => item.available_quantity > 0).length)
  const lowStockCount = computed(
    () =>
      balances.value.filter(
        (item) =>
          item.available_quantity > 0 &&
          item.available_quantity <= Number(lowStockThreshold.value || 0),
      ).length,
  )
  const negativeStockCount = computed(() => balances.value.filter((item) => item.available_quantity < 0).length)
  const inboundItems = computed(() => inboundSheet.value?.items || [])

  function resetOutboundDraft() {
    Object.assign(outboundDraft, createOutboundDraft(), {
      unit: outboundDraft.unit || DAILY_INTAKE_UNITS[0],
    })
  }

  function resetAdjustmentDraft() {
    Object.assign(adjustmentDraft, createAdjustmentDraft(), {
      unit: adjustmentDraft.unit || DAILY_INTAKE_UNITS[0],
    })
  }

  function prefillFromBalance(balance: InventoryBalance) {
    outboundDraft.name = balance.display_name || balance.normalized_name
    outboundDraft.unit = balance.unit_name
    adjustmentDraft.name = balance.display_name || balance.normalized_name
    adjustmentDraft.unit = balance.unit_name
    adjustmentDraft.targetQuantity = balance.available_quantity
    appendStatus(statusLogRef, `已将 ${balance.display_name} / ${balance.unit_name} 填入出库与盘点表单`, 'info')
  }

  async function loadInboundSheet(intakeDate = selectedDate.value) {
    loadingInbound.value = true
    try {
      const { data } = await getDailyIntakeByDate(intakeDate)
      inboundSheet.value = data.sheet
      selectedDate.value = data.sheet.intake_date
      editDraft.businessDate = data.sheet.intake_date
    } catch (error: unknown) {
      const detail = getApiErrorMessage(error, '加载点货入库来源失败')
      appendStatus(statusLogRef, detail, 'error')
      ElMessage.error(detail)
    } finally {
      loadingInbound.value = false
    }
  }

  async function loadSettings() {
    try {
      const { data } = await getConfig()
      const threshold = Number(
        (data as { config?: { inventory_low_stock_threshold?: unknown } }).config?.inventory_low_stock_threshold ?? 3,
      )
      if (Number.isFinite(threshold) && threshold >= 0) {
        lowStockThreshold.value = threshold
      }
    } catch (error: unknown) {
      const detail = getApiErrorMessage(error, '加载库存阈值配置失败')
      appendStatus(statusLogRef, detail, 'error')
    }
  }

  async function loadBalances() {
    loadingBalances.value = true
    try {
      const { data } = await getInventoryBalances({
        search: balanceSearch.value.trim(),
        limit: 200,
      })
      balances.value = data.items
    } catch (error: unknown) {
      const detail = getApiErrorMessage(error, '加载库存列表失败')
      appendStatus(statusLogRef, detail, 'error')
      ElMessage.error(detail)
    } finally {
      loadingBalances.value = false
    }
  }

  async function loadTransactions() {
    loadingTransactions.value = true
    try {
      const { data } = await getInventoryTransactions({
        search: transactionSearch.value.trim(),
        limit: 100,
        source_type: transactionSourceFilter.value === 'all' ? undefined : transactionSourceFilter.value,
      })
      transactions.value = data.items
    } catch (error: unknown) {
      const detail = getApiErrorMessage(error, '加载库存流水失败')
      appendStatus(statusLogRef, detail, 'error')
      ElMessage.error(detail)
    } finally {
      loadingTransactions.value = false
    }
  }

  async function refreshAll() {
    await Promise.all([loadInboundSheet(selectedDate.value), loadBalances(), loadTransactions()])
  }

  async function saveLowStockThreshold() {
    const normalizedThreshold = Number(lowStockThreshold.value)
    if (!Number.isFinite(normalizedThreshold) || normalizedThreshold < 0) {
      ElMessage.warning('低库存阈值必须大于等于 0')
      return
    }

    savingThreshold.value = true
    try {
      await updateConfig({
        inventory_low_stock_threshold: normalizedThreshold,
      })
      appendStatus(statusLogRef, `已保存低库存阈值：${normalizedThreshold}`, 'success')
      ElMessage.success('低库存阈值已保存')
    } catch (error: unknown) {
      const detail = getApiErrorMessage(error, '保存低库存阈值失败')
      appendStatus(statusLogRef, detail, 'error')
      ElMessage.error(detail)
    } finally {
      savingThreshold.value = false
    }
  }

  async function downloadBalanceExport() {
    exportingBalances.value = true
    try {
      const response = await exportInventoryBalances({
        search: balanceSearch.value.trim(),
      })
      const contentDisposition = response.headers['content-disposition'] || ''
      const matched = contentDisposition.match(/filename="?([^"]+)"?/)
      const filename = matched?.[1] || 'inventory-balances.csv'
      const blobUrl = window.URL.createObjectURL(response.data)
      const link = document.createElement('a')
      link.href = blobUrl
      link.download = filename
      document.body.appendChild(link)
      link.click()
      link.remove()
      window.URL.revokeObjectURL(blobUrl)
      appendStatus(statusLogRef, `已导出库存 CSV：${filename}`, 'success')
      ElMessage.success('库存 CSV 已导出')
    } catch (error: unknown) {
      const detail = getApiErrorMessage(error, '导出库存失败')
      appendStatus(statusLogRef, detail, 'error')
      ElMessage.error(detail)
    } finally {
      exportingBalances.value = false
    }
  }

  async function submitOutbound() {
    if (!outboundDraft.name.trim()) {
      ElMessage.warning('请先填写出库商品')
      return
    }
    if (outboundDraft.quantity === null || Number(outboundDraft.quantity) <= 0) {
      ElMessage.warning('请填写大于 0 的出库数量')
      return
    }

    submittingOutbound.value = true
    try {
      const { data } = await createInventoryOutbound({
        business_date: selectedDate.value,
        name: outboundDraft.name.trim(),
        unit: outboundDraft.unit,
        quantity: Number(outboundDraft.quantity),
        note: outboundDraft.note.trim(),
      })
      appendStatus(statusLogRef, data.message, 'success')
      ElMessage.success(data.message)
      resetOutboundDraft()
      await Promise.all([loadBalances(), loadTransactions()])
    } catch (error: unknown) {
      const detail = getApiErrorMessage(error, '保存出库记录失败')
      appendStatus(statusLogRef, detail, 'error')
      ElMessage.error(detail)
    } finally {
      submittingOutbound.value = false
    }
  }

  async function submitAdjustment() {
    if (!adjustmentDraft.name.trim()) {
      ElMessage.warning('请先填写盘点商品')
      return
    }
    if (adjustmentDraft.targetQuantity === null || Number(adjustmentDraft.targetQuantity) < 0) {
      ElMessage.warning('请填写大于等于 0 的目标库存')
      return
    }

    submittingAdjustment.value = true
    try {
      const { data } = await createInventoryAdjustment({
        business_date: selectedDate.value,
        name: adjustmentDraft.name.trim(),
        unit: adjustmentDraft.unit,
        target_quantity: Number(adjustmentDraft.targetQuantity),
        note: adjustmentDraft.note.trim(),
      })
      appendStatus(statusLogRef, data.message, 'success')
      ElMessage.success(data.message)
      resetAdjustmentDraft()
      await Promise.all([loadBalances(), loadTransactions()])
    } catch (error: unknown) {
      const detail = getApiErrorMessage(error, '保存盘点修正失败')
      appendStatus(statusLogRef, detail, 'error')
      ElMessage.error(detail)
    } finally {
      submittingAdjustment.value = false
    }
  }

  function openEditTransaction(transaction: InventoryTransaction) {
    if (transaction.source_type === 'daily_intake') {
      return
    }

    editDraft.id = transaction.id
    editDraft.direction = transaction.direction
    editDraft.name = transaction.display_name
    editDraft.unit = transaction.unit_name
    editDraft.quantity = transaction.direction === 'OUT' ? transaction.quantity : null
    editDraft.targetQuantity = transaction.direction === 'ADJUST' ? transaction.target_quantity : null
    editDraft.note = transaction.note || ''
    editDraft.businessDate = transaction.business_date
    editDialogVisible.value = true
  }

  async function saveEditTransaction() {
    if (!editDraft.id) {
      return
    }
    if (!editDraft.name.trim()) {
      ElMessage.warning('请先填写商品名')
      return
    }

    editSaving.value = true
    try {
      if (editDraft.direction === 'OUT') {
        if (editDraft.quantity === null || Number(editDraft.quantity) <= 0) {
          ElMessage.warning('请填写大于 0 的出库数量')
          return
        }
        const { data } = await updateInventoryOutbound(editDraft.id, {
          business_date: editDraft.businessDate,
          name: editDraft.name.trim(),
          unit: editDraft.unit,
          quantity: Number(editDraft.quantity),
          note: editDraft.note.trim(),
        })
        appendStatus(statusLogRef, data.message, 'success')
        ElMessage.success(data.message)
      } else {
        if (editDraft.targetQuantity === null || Number(editDraft.targetQuantity) < 0) {
          ElMessage.warning('请填写大于等于 0 的目标库存')
          return
        }
        const { data } = await updateInventoryAdjustment(editDraft.id, {
          business_date: editDraft.businessDate,
          name: editDraft.name.trim(),
          unit: editDraft.unit,
          target_quantity: Number(editDraft.targetQuantity),
          note: editDraft.note.trim(),
        })
        appendStatus(statusLogRef, data.message, 'success')
        ElMessage.success(data.message)
      }

      editDialogVisible.value = false
      await Promise.all([loadBalances(), loadTransactions()])
    } catch (error: unknown) {
      const detail = getApiErrorMessage(error, '更新库存流水失败')
      appendStatus(statusLogRef, detail, 'error')
      ElMessage.error(detail)
    } finally {
      editSaving.value = false
    }
  }

  async function removeManualTransaction(transaction: InventoryTransaction) {
    if (transaction.source_type === 'daily_intake') {
      return
    }

    try {
      await ElMessageBox.confirm(
        `将删除“${transaction.display_name}”的${transaction.direction === 'OUT' ? '出库' : '盘点修正'}记录。`,
        '确认删除',
        {
          confirmButtonText: '删除',
          cancelButtonText: '取消',
          type: 'warning',
        },
      )
    } catch {
      return
    }

    deletingTransactionId.value = transaction.id
    try {
      if (transaction.source_type === 'manual_outbound') {
        const { data } = await deleteInventoryOutbound(transaction.id)
        appendStatus(statusLogRef, data.message, 'success')
        ElMessage.success(data.message)
      } else {
        const { data } = await deleteInventoryAdjustment(transaction.id)
        appendStatus(statusLogRef, data.message, 'success')
        ElMessage.success(data.message)
      }
      await Promise.all([loadBalances(), loadTransactions()])
    } catch (error: unknown) {
      const detail = getApiErrorMessage(error, '删除库存流水失败')
      appendStatus(statusLogRef, detail, 'error')
      ElMessage.error(detail)
    } finally {
      deletingTransactionId.value = null
    }
  }

  function getBalanceRowClassName({ row }: { row: InventoryBalance }) {
    if (row.available_quantity < 0) {
      return 'inventory-balance-row--negative'
    }
    if (row.available_quantity > 0 && row.available_quantity <= Number(lowStockThreshold.value || 0)) {
      return 'inventory-balance-row--low'
    }
    return ''
  }

  onMounted(async () => {
    await loadSettings()
    await refreshAll()
  })

  return {
    adjustmentDraft,
    balanceSearch,
    balances,
    deletingTransactionId,
    editDialogVisible,
    editDraft,
    editSaving,
    exportingBalances,
    getBalanceRowClassName,
    inboundItems,
    inboundSheet,
    loadBalances,
    loadInboundSheet,
    loadSettings,
    loadTransactions,
    lowStockThreshold,
    loadingBalances,
    loadingInbound,
    loadingTransactions,
    lowStockCount,
    negativeStockCount,
    openEditTransaction,
    outboundDraft,
    positiveBalanceCount,
    prefillFromBalance,
    refreshAll,
    removeManualTransaction,
    saveLowStockThreshold,
    saveEditTransaction,
    savingThreshold,
    selectedDate,
    submitAdjustment,
    submitOutbound,
    submittingAdjustment,
    submittingOutbound,
    transactionSourceFilter,
    transactionSearch,
    transactions,
    downloadBalanceExport,
  }
}
