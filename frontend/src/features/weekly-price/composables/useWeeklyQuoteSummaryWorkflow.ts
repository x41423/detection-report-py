import { computed, nextTick, reactive, ref, type Ref } from 'vue'
import { ElMessageBox } from 'element-plus'

import { getApiErrorMessage } from '../../../api/errors'
import {
  createWeeklyQuoteMeasureUnit,
  createWeeklyQuoteSupplier,
  deleteQuoteBatch,
  exportWeeklyQuoteSummaryWeekUpload,
  getWeeklyQuoteSummaryOptions,
  getWeeklyQuoteWeekOverview,
  importWeeklyQuoteBatchFromPath,
  importWeeklyQuoteBatchUpload,
  saveQuoteBatch,
  type WeeklyQuoteEntryInput,
  type WeeklyQuoteMeasureUnitOption,
  type WeeklyQuoteSavedBatch,
  type WeeklyQuoteSummaryRule,
  type WeeklyQuoteSupplierOption,
  type WeeklyQuoteSupplierWeekOverview,
} from '../../../api/weekly-price'
import { useAuth } from '../../../composables/useAuth'
import { triggerDownload } from '../../../utils/download'
import type { StatusLogHandle } from '../../shared/workflow'
import {
  WEEKLY_QUOTE_DAY_LABELS,
  WEEKLY_QUOTE_LIMITS,
  WEEKLY_QUOTE_SUPPLIERS,
  addDays,
  buildEntryId,
  formatDate,
  getFileName,
  mondayOf,
  normalizeEntrySnapshot,
  parseDate,
  parseWeeklyQuotePaste,
  pad,
  type WeeklyQuoteEntryDraft,
  type WeeklyQuotePasteMode,
} from './weeklyQuoteSummaryUtils'

const DRAFT_STORAGE_KEY = 'weekly-quote-summary-drafts-v1'
const UNIT_MEMORY_KEY = 'weekly-quote-unit-memory-v1'

interface WeeklyQuoteEntry extends WeeklyQuoteEntryDraft {
  id: string
}

interface WeeklyQuoteRawRow {
  entry: WeeklyQuoteEntry
}

interface WeeklyQuoteSavedRecord {
  id: string
  supplier: string
  quote_date: string
  entries: WeeklyQuoteEntry[]
  source_label: string
  source_path: string
  updated_at: string
}

interface WeeklyQuoteWeekGroup {
  monday: string
  label: string
  records: WeeklyQuoteSavedRecord[]
  totalEntries: number
}

interface WeeklyQuotePreview {
  total_batches: number
  total_entries: number
  total_summary_items: number
}

interface WeeklyQuoteDayCell {
  date: string
  dayLabel: string
  dateLabel: string
  entryCount: number
  draftCount: number
  hasRecord: boolean
  hasDraft: boolean
}

interface WeeklyQuoteWeekCell {
  monday: string
  label: string
}

interface WeeklyQuoteDraft {
  supplier: string
  quote_date: string
  entries: WeeklyQuoteEntryInput[]
  updated_at: string
}

type DraftStore = Record<string, WeeklyQuoteDraft>
type EditorSource = 'empty' | 'saved' | 'draft' | 'import'

function emptySupplierOverview(
  supplier: string,
  limit = WEEKLY_QUOTE_LIMITS[supplier] ?? 0,
  summaryRule: WeeklyQuoteSummaryRule = 'highest',
): WeeklyQuoteSupplierWeekOverview {
  return {
    supplier,
    limit,
    summary_rule: summaryRule,
    batches: [],
    batch_count: 0,
    entry_count: 0,
    summary_items: [],
  }
}

function toEntryInputs(rows: WeeklyQuoteRawRow[]): WeeklyQuoteEntryInput[] {
  return rows.map((row) => ({
    name: row.entry.name.trim(),
    unit: (row.entry.unit || '').trim(),
    price: Number(row.entry.price),
  }))
}

function toRows(entries: WeeklyQuoteEntryInput[], prefix: string): WeeklyQuoteRawRow[] {
  return entries.map((entry, index) => ({
    entry: {
      id: buildEntryId(prefix, index + 1),
      name: entry.name,
      unit: entry.unit || '斤',
      price: Number(entry.price),
    },
  }))
}

function savedBatchToRecord(batch: WeeklyQuoteSavedBatch): WeeklyQuoteSavedRecord {
  return {
    id: String(batch.id),
    supplier: batch.supplier,
    quote_date: batch.quote_date,
    entries: toRows(batch.entries || [], `saved-${batch.id}`).map((row) => row.entry),
    source_label: batch.source_label || '',
    source_path: batch.source_path || '',
    updated_at: batch.created_at || '',
  }
}

function weeksForMonth(monthValue: string): WeeklyQuoteWeekCell[] {
  const [yearStr, monthStr] = monthValue.split('-')
  const year = Number.parseInt(yearStr, 10)
  const month = Number.parseInt(monthStr, 10)
  if (!year || !month) return []
  const firstDay = new Date(year, month - 1, 1)
  const lastDay = new Date(year, month, 0)
  const mondays: WeeklyQuoteWeekCell[] = []
  let cursor = mondayOf(firstDay)
  while (cursor <= lastDay) {
    const sunday = addDays(cursor, 6)
    mondays.push({
      monday: formatDate(cursor),
      label: `${pad(cursor.getMonth() + 1)}/${pad(cursor.getDate())} – ${pad(sunday.getMonth() + 1)}/${pad(sunday.getDate())}`,
    })
    cursor = addDays(cursor, 7)
  }
  return mondays
}

function draftKey(supplier: string, quoteDate: string): string {
  return `${supplier}::${quoteDate}`
}

function loadDraftStore(): DraftStore {
  if (typeof localStorage === 'undefined') return {}
  try {
    const parsed = JSON.parse(localStorage.getItem(DRAFT_STORAGE_KEY) || '{}')
    return parsed && typeof parsed === 'object' ? parsed : {}
  } catch {
    return {}
  }
}

function persistDraftStore(drafts: DraftStore) {
  if (typeof localStorage === 'undefined') return
  localStorage.setItem(DRAFT_STORAGE_KEY, JSON.stringify(drafts))
}

function loadUnitMemory(): Record<string, string> {
  if (typeof localStorage === 'undefined') return {}
  try {
    const parsed = JSON.parse(localStorage.getItem(UNIT_MEMORY_KEY) || '{}')
    return parsed && typeof parsed === 'object' ? parsed : {}
  } catch {
    return {}
  }
}

function persistUnitMemory(memory: Record<string, string>) {
  if (typeof localStorage === 'undefined') return
  // Keep only the last 200 entries to avoid localStorage bloat
  const entries = Object.entries(memory)
  if (entries.length > 200) {
    const trimmed: Record<string, string> = {}
    for (const [key, value] of entries.slice(-200)) {
      trimmed[key] = value
    }
    localStorage.setItem(UNIT_MEMORY_KEY, JSON.stringify(trimmed))
    return
  }
  localStorage.setItem(UNIT_MEMORY_KEY, JSON.stringify(memory))
}

function isAuthFailure(error: any): boolean {
  return error?.response?.status === 401
}

export function useWeeklyQuoteSummaryWorkflow(
  statusLogRef: Ref<StatusLogHandle | undefined>,
) {
  const auth = useAuth()
  const today = new Date()

  const weekState = reactive({
    loading: false,
    selectedMonth: `${today.getFullYear()}-${pad(today.getMonth() + 1)}`,
    selectedWeekMonday: formatDate(mondayOf(today)),
    selectedRecordDate: formatDate(today),
    committedMonth: `${today.getFullYear()}-${pad(today.getMonth() + 1)}`,
    overview: null as Awaited<ReturnType<typeof getWeeklyQuoteWeekOverview>>['data'] | null,
  })

  const optionsState = reactive({
    loading: false,
    suppliers: [] as WeeklyQuoteSupplierOption[],
    measureUnits: [] as WeeklyQuoteMeasureUnitOption[],
    addingSupplier: false,
  })

  const editorState = reactive({
    activeSupplier: WEEKLY_QUOTE_SUPPLIERS[0] as string,
    source: 'empty' as EditorSource,
    sourceLabel: '',
    baselineSnapshot: normalizeEntrySnapshot([]),
  })

  const importExportState = reactive({
    importDialogVisible: false,
    pasteDialogVisible: false,
    importing: false,
    pasteParsing: false,
    exporting: false,
    importSourceFile: null as File | null,
    workbookTemplateFile: null as File | null,
    workbookPath: '',
  })

  const importForm = reactive({
    quote_date: formatDate(today),
    source_path: '',
  })

  const pasteForm = reactive<{
    mode: WeeklyQuotePasteMode
    names: string
    prices: string
    text: string
  }>({
    mode: 'columns',
    names: '',
    prices: '',
    text: '',
  })

  const supplierDialog = reactive({
    visible: false,
    name: '',
    weekly_batch_limit: 7,
    summary_rule: 'highest' as WeeklyQuoteSummaryRule,
  })

  const rawRows = ref<WeeklyQuoteRawRow[]>([])
  const currentRecord = ref<WeeklyQuoteSavedRecord | null>(null)
  const drafts = ref<DraftStore>(loadDraftStore())
  const unitMemory = ref<Record<string, string>>(loadUnitMemory())
  const statusIssues = ref<string[]>([])
  let nextEntryCounter = 0

  function appendStatus(message: string, type: 'info' | 'success' | 'error' = 'info') {
    statusLogRef.value?.append?.(message, type)
  }

  function canUseAuthenticatedApi() {
    return Boolean(auth.accessToken.value)
  }

  const supplierOptions = computed<WeeklyQuoteSupplierOption[]>(() => {
    if (optionsState.suppliers.length) return optionsState.suppliers
    return WEEKLY_QUOTE_SUPPLIERS.map((supplier, index) => ({
      name: supplier,
      weekly_batch_limit: WEEKLY_QUOTE_LIMITS[supplier] ?? 7,
      summary_rule: supplier === '理想' ? 'average' : 'highest',
      is_builtin: true,
      sort_order: (index + 1) * 10,
    }))
  })

  const supplierSummaries = computed<WeeklyQuoteSupplierWeekOverview[]>(() => {
    const bySupplier = new Map((weekState.overview?.suppliers || []).map((item) => [item.supplier, item]))
    return supplierOptions.value.map((supplier) => bySupplier.get(supplier.name) || emptySupplierOverview(
      supplier.name,
      supplier.weekly_batch_limit,
      supplier.summary_rule,
    ))
  })

  const suppliers = computed(() => supplierSummaries.value.map((item) => item.supplier))
  const LIMITS = computed(() =>
    Object.fromEntries(supplierSummaries.value.map((item) => [item.supplier, item.limit])),
  )
  const activeSupplierOverview = computed(
    () => supplierSummaries.value.find((item) => item.supplier === editorState.activeSupplier)
      || emptySupplierOverview(editorState.activeSupplier),
  )
  const currentLimit = computed(() => activeSupplierOverview.value.limit)
  const currentSummary = computed(() => ({
    batch_count: activeSupplierOverview.value.batch_count,
    entry_count: activeSupplierOverview.value.entry_count,
    summary_items: activeSupplierOverview.value.summary_items,
  }))
  const previewData = computed<WeeklyQuotePreview>(() => ({
    total_batches: weekState.overview?.total_batches || 0,
    total_entries: weekState.overview?.total_entries || 0,
    total_summary_items: weekState.overview?.total_summary_items || 0,
  }))
  const previewIssues = computed(() => statusIssues.value.length ? statusIssues.value : (weekState.overview?.issue_messages || []))
  const savedRecordCounts = computed<Record<string, number>>(() =>
    Object.fromEntries(supplierSummaries.value.map((item) => [item.supplier, item.batch_count])),
  )
  const activeSupplierCount = computed(() =>
    supplierSummaries.value.filter((item) => item.batch_count > 0).length,
  )
  const currentRecordEntryCount = computed(() => rawRows.value.length)
  const measureUnitNames = computed(() => optionsState.measureUnits.map((unit) => unit.name))
  const currentDraftKey = computed(() => draftKey(editorState.activeSupplier, weekState.selectedRecordDate))
  const hasCurrentDraft = computed(() => Boolean(drafts.value[currentDraftKey.value]))
  const editorSnapshot = computed(() => normalizeEntrySnapshot(toEntryInputs(rawRows.value)))
  const editorDirty = computed(() => editorSnapshot.value !== editorState.baselineSnapshot)
  const savedRecordEmptied = computed(() => Boolean(currentRecord.value) && !rawRows.value.length && editorDirty.value)
  const currentRecordSourceLabel = computed(() => {
    if (savedRecordEmptied.value) return '待删除已保存记录'
    if (editorState.source === 'draft') return '本地草稿'
    if (editorState.source === 'import') return editorState.sourceLabel || 'Excel 导入待保存'
    if (currentRecord.value) return currentRecord.value.source_label || '手动录入'
    return hasCurrentDraft.value ? '本地草稿' : '尚未保存'
  })

  const weeksForSelectedMonth = computed(() => weeksForMonth(weekState.selectedMonth))

  const daysForSelectedWeek = computed<WeeklyQuoteDayCell[]>(() => {
    const monday = parseDate(weekState.selectedWeekMonday)
    if (!monday) return []
    const records = new Map(activeSupplierOverview.value.batches.map((record) => [record.quote_date, record]))
    return Array.from({ length: 7 }, (_, offset) => {
      const day = addDays(monday, offset)
      const dateStr = formatDate(day)
      const record = records.get(dateStr)
      const draft = drafts.value[draftKey(editorState.activeSupplier, dateStr)]
      return {
        date: dateStr,
        dayLabel: WEEKLY_QUOTE_DAY_LABELS[offset],
        dateLabel: `${pad(day.getMonth() + 1)}/${pad(day.getDate())}`,
        entryCount: record?.entry_count || 0,
        draftCount: draft?.entries.length || 0,
        hasRecord: Boolean(record),
        hasDraft: Boolean(draft),
      }
    })
  })

  const savedRecordsByWeek = computed<WeeklyQuoteWeekGroup[]>(() => {
    const monday = weekState.selectedWeekMonday
    const mondayDate = parseDate(monday)
    if (!mondayDate) return []
    const records = activeSupplierOverview.value.batches.map(savedBatchToRecord)
    if (!records.length) return []
    const sunday = addDays(mondayDate, 6)
    return [{
      monday,
      label: `${pad(mondayDate.getMonth() + 1)}/${pad(mondayDate.getDate())} – ${pad(sunday.getMonth() + 1)}/${pad(sunday.getDate())}`,
      records: records.sort((a, b) => (a.quote_date < b.quote_date ? 1 : -1)),
      totalEntries: records.reduce((total, record) => total + record.entries.length, 0),
    }]
  })

  function findSavedBatch(supplier: string, quoteDate: string) {
    return supplierSummaries.value
      .find((item) => item.supplier === supplier)
      ?.batches.find((batch) => batch.quote_date === quoteDate) || null
  }

  function openRecordFromState(supplier = editorState.activeSupplier, quoteDate = weekState.selectedRecordDate) {
    const draft = drafts.value[draftKey(supplier, quoteDate)]
    const savedBatch = findSavedBatch(supplier, quoteDate)
    currentRecord.value = savedBatch ? savedBatchToRecord(savedBatch) : null

    if (draft) {
      rawRows.value = toRows(draft.entries, 'draft')
      editorState.source = 'draft'
      editorState.sourceLabel = '本地草稿'
      editorState.baselineSnapshot = normalizeEntrySnapshot(draft.entries)
      return
    }

    if (savedBatch) {
      rawRows.value = toRows(savedBatch.entries || [], `saved-${savedBatch.id}`)
      editorState.source = 'saved'
      editorState.sourceLabel = savedBatch.source_label || '手动录入'
      editorState.baselineSnapshot = normalizeEntrySnapshot(savedBatch.entries || [])
      return
    }

    rawRows.value = []
    editorState.source = 'empty'
    editorState.sourceLabel = ''
    editorState.baselineSnapshot = normalizeEntrySnapshot([])
  }

  function saveCurrentDraft() {
    const entries = toEntryInputs(rawRows.value)
    const key = currentDraftKey.value
    const nextDrafts = { ...drafts.value }
    if (entries.length) {
      nextDrafts[key] = {
        supplier: editorState.activeSupplier,
        quote_date: weekState.selectedRecordDate,
        entries,
        updated_at: new Date().toISOString(),
      }
      appendStatus(`${editorState.activeSupplier} ${weekState.selectedRecordDate} 已保存为本地草稿`, 'success')
    } else {
      delete nextDrafts[key]
    }
    drafts.value = nextDrafts
    persistDraftStore(nextDrafts)
    _updateUnitMemory(entries)
    editorState.source = entries.length ? 'draft' : 'empty'
    editorState.sourceLabel = entries.length ? '本地草稿' : ''
    editorState.baselineSnapshot = normalizeEntrySnapshot(entries)
  }

  function removeCurrentDraft() {
    const nextDrafts = { ...drafts.value }
    delete nextDrafts[currentDraftKey.value]
    drafts.value = nextDrafts
    persistDraftStore(nextDrafts)
  }

  function clearEmptyUnsavedEditor() {
    if (rawRows.value.length || currentRecord.value) return
    removeCurrentDraft()
    editorState.source = 'empty'
    editorState.sourceLabel = ''
    editorState.baselineSnapshot = normalizeEntrySnapshot([])
  }

  async function loadOptions() {
    if (!canUseAuthenticatedApi()) return false
    optionsState.loading = true
    try {
      const { data } = await getWeeklyQuoteSummaryOptions()
      optionsState.suppliers = data.suppliers || []
      optionsState.measureUnits = data.measure_units || []
      if (optionsState.suppliers.length && !optionsState.suppliers.some((item) => item.name === editorState.activeSupplier)) {
        editorState.activeSupplier = optionsState.suppliers[0].name
      }
      return true
    } catch (error: any) {
      if (!isAuthFailure(error)) {
        appendStatus('加载报价单位配置失败：' + getApiErrorMessage(error), 'error')
      }
      return false
    } finally {
      optionsState.loading = false
    }
  }

  async function confirmLeaveEditor() {
    if (!editorDirty.value) return true
    if (!rawRows.value.length && !currentRecord.value) {
      clearEmptyUnsavedEditor()
      return true
    }
    if (savedRecordEmptied.value) {
      return deleteCurrentSavedRecord({
        title: '删除已保存记录',
        message: `当前 ${editorState.activeSupplier} ${weekState.selectedRecordDate} 的记录已被删空。确认删除该日已保存记录并切换？`,
        successMessage: '已删除当前日期记录，继续切换',
        reopenCurrentRecord: false,
      })
    }
    try {
      await ElMessageBox.confirm(
        '当前编辑区有未保存内容。保存为本地草稿后不会参与预览和导出，正式保存后才会入库。',
        '切换前处理编辑内容',
        {
          confirmButtonText: '保存草稿并切换',
          cancelButtonText: '不保存并切换',
          distinguishCancelAndClose: true,
          closeOnClickModal: false,
          type: 'warning',
        },
      )
      saveCurrentDraft()
      return true
    } catch (action) {
      return action === 'cancel'
    }
  }

  async function deleteCurrentSavedRecord(options?: {
    title?: string
    message?: string
    successMessage?: string
    reopenCurrentRecord?: boolean
  }) {
    if (!currentRecord.value) return false
    const supplier = editorState.activeSupplier
    const quoteDate = weekState.selectedRecordDate
    try {
      await ElMessageBox.confirm(
        options?.message || `确认删除 ${supplier} ${quoteDate} 的已保存记录？`,
        options?.title || '删除已保存记录',
        {
          confirmButtonText: '删除',
          cancelButtonText: '取消',
          type: 'warning',
        },
      )
    } catch {
      return false
    }

    try {
      const { data } = await deleteQuoteBatch(supplier, quoteDate)
      removeCurrentDraft()
      await loadWeekOverview(quoteDate)
      if (options?.reopenCurrentRecord !== false) {
        openRecordFromState()
      } else {
        currentRecord.value = null
        rawRows.value = []
        editorState.source = 'empty'
        editorState.sourceLabel = ''
        editorState.baselineSnapshot = normalizeEntrySnapshot([])
      }
      appendStatus(
        data.success ? (options?.successMessage || '已删除当前日期记录，当前周预览已刷新') : '未找到可删除的记录',
        data.success ? 'success' : 'info',
      )
      return true
    } catch (error: any) {
      appendStatus('删除失败：' + getApiErrorMessage(error), 'error')
      return false
    }
  }

  async function deleteCurrentRecord() {
    await deleteCurrentSavedRecord({
      title: '删除当前日期记录',
      message: `确认删除 ${editorState.activeSupplier} ${weekState.selectedRecordDate} 的已保存记录？`,
      successMessage: '已删除当前日期记录，当前周预览已刷新',
    })
  }

  async function loadWeekOverview(date = weekState.selectedWeekMonday) {
    if (!canUseAuthenticatedApi()) return false
    weekState.loading = true
    statusIssues.value = []
    try {
      const { data } = await getWeeklyQuoteWeekOverview(date)
      weekState.overview = data
      weekState.selectedWeekMonday = data.week_start
      return true
    } catch (error: any) {
      if (!isAuthFailure(error)) {
        statusIssues.value = [getApiErrorMessage(error, '加载周汇总失败')]
        appendStatus('加载周汇总失败：' + getApiErrorMessage(error), 'error')
      }
      return false
    } finally {
      weekState.loading = false
    }
  }

  async function selectSupplier(supplier: string) {
    if (supplier === editorState.activeSupplier) return
    if (!(await confirmLeaveEditor())) return
    editorState.activeSupplier = supplier
    openRecordFromState()
  }

  async function selectRecordDate(date: string) {
    if (date === weekState.selectedRecordDate) return
    if (!(await confirmLeaveEditor())) return
    weekState.selectedRecordDate = date
    openRecordFromState()
  }

  async function selectWeek(weekMonday: string) {
    if (weekMonday === weekState.selectedWeekMonday) return
    if (!(await confirmLeaveEditor())) return
    weekState.selectedWeekMonday = weekMonday
    weekState.selectedRecordDate = weekMonday
    weekState.selectedMonth = weekMonday.slice(0, 7)
    weekState.committedMonth = weekState.selectedMonth
    await loadWeekOverview(weekMonday)
    openRecordFromState()
  }

  async function onMonthChange(value: string) {
    if (!value) return
    if (!(await confirmLeaveEditor())) {
      weekState.selectedMonth = weekState.committedMonth
      return
    }
    const weeks = weeksForMonth(value)
    weekState.selectedMonth = value
    weekState.committedMonth = value
    if (weeks.length) {
      weekState.selectedWeekMonday = weeks[0].monday
      weekState.selectedRecordDate = weeks[0].monday
      await loadWeekOverview(weeks[0].monday)
      openRecordFromState()
    }
  }

  function isWeekExpanded(_weekMonday: string) {
    return true
  }

  function toggleWeekExpanded(_weekMonday: string) {
    // Current week overview only returns one visible week group.
  }

  function countEntries(record: WeeklyQuoteSavedRecord | null | undefined): number {
    return record?.entries?.length ?? 0
  }

  function getRecordSourceLabel(record: WeeklyQuoteSavedRecord | null | undefined): string {
    return record?.source_label || '手动录入'
  }

  async function applyRememberedUnit(entry?: WeeklyQuoteEntry) {
    if (!entry) return
    const name = (entry.name || '').trim()
    if (!name) return
    const remembered = unitMemory.value[name]
    if (!remembered) return
    const current = (entry.unit || '').trim()
    if (current && current !== '斤') return
    entry.unit = remembered
    await nextTick()
  }

  function _updateUnitMemory(entries: WeeklyQuoteEntryInput[]) {
    const next = { ...unitMemory.value }
    let changed = false
    for (const entry of entries) {
      const name = (entry.name || '').trim()
      const unit = (entry.unit || '').trim()
      if (!name || !unit) continue
      if (next[name] === unit) continue
      next[name] = unit
      changed = true
    }
    if (!changed) return
    unitMemory.value = next
    persistUnitMemory(next)
  }

  function setImportSourceFile(files: FileList | null | undefined) {
    const file = files?.[0]
    if (file) {
      importExportState.importSourceFile = file
      importForm.source_path = file.name
    }
  }

  function setWorkbookTemplateFile(files: FileList | null | undefined) {
    const file = files?.[0]
    if (file) {
      importExportState.workbookTemplateFile = file
      importExportState.workbookPath = file.name
    }
  }

  function setWorkbookTemplateFromPath(path: string) {
    importExportState.workbookPath = path
    // Store path for later use - the actual file will be read by backend
    importExportState.workbookTemplateFile = null
  }

  async function confirmImportFromPath(sourcePath: string) {
    if (!sourcePath) {
      appendStatus('请先选择要导入的 Excel 文件', 'error')
      return
    }
    if (!importForm.quote_date) {
      appendStatus('请选择报价日期', 'error')
      return
    }
    if (!(await confirmLeaveEditor())) return

    importExportState.importing = true
    try {
      const { data } = await importWeeklyQuoteBatchFromPath({
        supplier: editorState.activeSupplier,
        quoteDate: importForm.quote_date,
        sourcePath: sourcePath,
      })
      const targetDate = data.batch.quote_date
      const targetMonday = formatDate(mondayOf(parseDate(targetDate) || new Date()))
      weekState.selectedRecordDate = targetDate
      weekState.selectedWeekMonday = targetMonday
      weekState.selectedMonth = targetDate.slice(0, 7)
      weekState.committedMonth = weekState.selectedMonth
      await loadWeekOverview(targetMonday)
      currentRecord.value = findSavedBatch(editorState.activeSupplier, targetDate)
        ? savedBatchToRecord(findSavedBatch(editorState.activeSupplier, targetDate)!)
        : null
      rawRows.value = toRows(data.batch.entries, 'import')
      
      // Auto-fill units from memory for imported entries
      for (const row of rawRows.value) {
        const name = (row.entry.name || '').trim()
        if (!name) continue
        const remembered = unitMemory.value[name]
        if (!remembered) continue
        const current = (row.entry.unit || '').trim()
        if (!current || current === '斤') {
          row.entry.unit = remembered
        }
      }
      
      importExportState.importDialogVisible = false
      appendStatus(`导入完成：${data.batch.entries.length} 条记录`, 'success')
      ElMessage.success('导入完成')
    } catch (error: any) {
      appendStatus('导入失败: ' + getApiErrorMessage(error), 'error')
      ElMessage.error('导入失败')
    } finally {
      importExportState.importing = false
    }
  }

  function openImportDialog() {
    importForm.quote_date = weekState.selectedRecordDate
    importExportState.importDialogVisible = true
  }

  function openPasteDialog() {
    importExportState.pasteDialogVisible = true
  }

  function openSupplierDialog() {
    supplierDialog.visible = true
    supplierDialog.name = ''
    supplierDialog.weekly_batch_limit = 7
    supplierDialog.summary_rule = 'highest'
  }

  async function confirmCreateSupplier() {
    const name = supplierDialog.name.trim()
    if (!name) {
      appendStatus('请输入报价单位名称', 'error')
      return
    }
    optionsState.addingSupplier = true
    try {
      const { data } = await createWeeklyQuoteSupplier({
        name,
        weekly_batch_limit: Number(supplierDialog.weekly_batch_limit),
        summary_rule: supplierDialog.summary_rule,
      })
      await loadOptions()
      await loadWeekOverview(weekState.selectedWeekMonday)
      if (await confirmLeaveEditor()) {
        editorState.activeSupplier = data.supplier.name
        openRecordFromState()
      }
      supplierDialog.visible = false
      appendStatus(data.message || '报价单位已添加', 'success')
    } catch (error: any) {
      appendStatus('新增报价单位失败：' + getApiErrorMessage(error), 'error')
    } finally {
      optionsState.addingSupplier = false
    }
  }

  async function ensureMeasureUnitOption(value: string) {
    const name = String(value || '').trim()
    if (!name || measureUnitNames.value.includes(name)) return
    try {
      const { data } = await createWeeklyQuoteMeasureUnit({ name })
      optionsState.measureUnits = [...optionsState.measureUnits, data.measure_unit]
      appendStatus(data.message || `计量单位“${name}”已添加`, 'success')
    } catch (error: any) {
      const message = getApiErrorMessage(error)
      if (message.includes('已存在')) {
        await loadOptions()
        return
      }
      appendStatus('新增计量单位失败：' + message, 'error')
    }
  }

  async function confirmImport() {
    if (!importExportState.importSourceFile) {
      appendStatus('请先选择要导入的 Excel 文件', 'error')
      return
    }
    if (!importForm.quote_date) {
      appendStatus('请选择报价日期', 'error')
      return
    }
    if (!(await confirmLeaveEditor())) return

    importExportState.importing = true
    try {
      const { data } = await importWeeklyQuoteBatchUpload({
        supplier: editorState.activeSupplier,
        quoteDate: importForm.quote_date,
        sourceFile: importExportState.importSourceFile,
      })
      const targetDate = data.batch.quote_date
      const targetMonday = formatDate(mondayOf(parseDate(targetDate) || new Date()))
      weekState.selectedRecordDate = targetDate
      weekState.selectedWeekMonday = targetMonday
      weekState.selectedMonth = targetDate.slice(0, 7)
      weekState.committedMonth = weekState.selectedMonth
      await loadWeekOverview(targetMonday)
      currentRecord.value = findSavedBatch(editorState.activeSupplier, targetDate)
        ? savedBatchToRecord(findSavedBatch(editorState.activeSupplier, targetDate)!)
        : null
      rawRows.value = toRows(data.batch.entries, 'import')
      
      // Auto-fill units from memory for imported entries
      for (const row of rawRows.value) {
        const name = (row.entry.name || '').trim()
        if (!name) continue
        const remembered = unitMemory.value[name]
        if (!remembered) continue
        const current = (row.entry.unit || '').trim()
        if (!current || current === '斤') {
          row.entry.unit = remembered
        }
      }

      editorState.source = 'import'
      editorState.sourceLabel = `Excel 导入：${importExportState.importSourceFile.name}`
      editorState.baselineSnapshot = normalizeEntrySnapshot(currentRecord.value?.entries || [])
      importExportState.importDialogVisible = false
      importExportState.importSourceFile = null
      importForm.source_path = ''
      appendStatus(`导入成功：${data.message || '已完成'}，请审核后点击“保存当前日期记录”`, 'success')
    } catch (error: any) {
      appendStatus('导入失败：' + getApiErrorMessage(error), 'error')
    } finally {
      importExportState.importing = false
    }
  }

  function confirmPaste() {
    importExportState.pasteParsing = true
    try {
      const result = parseWeeklyQuotePaste(pasteForm)
      let updatedCount = 0
      if (result.pricesOnly.length) {
        rawRows.value = rawRows.value.map((row, index) => {
          const price = result.pricesOnly[index]
          if (price === undefined) return row
          updatedCount++
          return { entry: { ...row.entry, price } }
        })
      }

      for (const entry of result.entries) {
        nextEntryCounter++
        rawRows.value.push({
          entry: {
            id: buildEntryId('paste', nextEntryCounter),
            ...entry,
          },
        })
      }

      // Auto-fill units from memory for paste entries
      for (const row of rawRows.value) {
        const name = (row.entry.name || '').trim()
        if (!name) continue
        const remembered = unitMemory.value[name]
        if (!remembered) continue
        const current = (row.entry.unit || '').trim()
        if (!current || current === '斤') {
          row.entry.unit = remembered
        }
      }

      const addedCount = result.entries.length
      if (!addedCount && !updatedCount) {
        appendStatus('没有识别到可写入的报价记录', 'info')
        return
      }
      appendStatus(`识别完成：新增 ${addedCount} 条，补齐 ${updatedCount} 条，保存后参与汇总`, 'success')
      importExportState.pasteDialogVisible = false
      pasteForm.names = ''
      pasteForm.prices = ''
      pasteForm.text = ''
    } catch (error: any) {
      appendStatus(`识别失败：${error.message || error}`, 'error')
    } finally {
      importExportState.pasteParsing = false
    }
  }

  function addEntryToCurrentRecord() {
    nextEntryCounter++
    rawRows.value.push({
      entry: {
        id: buildEntryId('new', nextEntryCounter),
        name: '',
        unit: '斤',
        price: 0,
      },
    })
  }

  function removeEntry(entryId: string) {
    rawRows.value = rawRows.value.filter((row) => row.entry.id !== entryId)
  }

  async function saveCurrentRecord() {
    if (!rawRows.value.length) {
      if (currentRecord.value) {
        await deleteCurrentSavedRecord({
          title: '删除当前日期记录',
          message: `当前 ${editorState.activeSupplier} ${weekState.selectedRecordDate} 的记录已被删空。确认删除该日已保存记录？`,
          successMessage: '已删除当前日期记录，当前周预览已刷新',
        })
        return
      }
      clearEmptyUnsavedEditor()
      appendStatus('当前日期还没有录入记录，请先新增、导入或粘贴报价后再保存。', 'error')
      return
    }

    const entries = toEntryInputs(rawRows.value)
    const invalid = entries.filter((entry) => !entry.name || !entry.unit || entry.price <= 0)
    if (invalid.length) {
      appendStatus(`有 ${invalid.length} 条记录缺少菜名、单位或有效单价，请完善后重新保存。`, 'error')
      return
    }

    const isUpdatingExistingDate = Boolean(findSavedBatch(editorState.activeSupplier, weekState.selectedRecordDate))
    if (!isUpdatingExistingDate && activeSupplierOverview.value.batch_count >= currentLimit.value) {
      appendStatus(`${editorState.activeSupplier} 当前周最多只允许 ${currentLimit.value} 个日期记录`, 'error')
      return
    }

    try {
      await saveQuoteBatch({
        supplier: editorState.activeSupplier,
        quote_date: weekState.selectedRecordDate,
        entries,
        source_label: editorState.source === 'import' ? 'Excel 导入' : '手动录入',
      })
      removeCurrentDraft()
      _updateUnitMemory(entries)
      await loadOptions()
      await loadWeekOverview(weekState.selectedRecordDate)
      openRecordFromState()
      appendStatus('保存成功，当前周预览已刷新', 'success')
    } catch (error: any) {
      appendStatus('保存失败：' + getApiErrorMessage(error), 'error')
    }
  }

  async function removeSavedRecord(date: string) {
    try {
      await ElMessageBox.confirm(`确认删除 ${editorState.activeSupplier} ${date} 的已保存记录？`, '删除已保存记录', {
        confirmButtonText: '删除',
        cancelButtonText: '取消',
        type: 'warning',
      })
    } catch {
      return
    }

    try {
      const { data } = await deleteQuoteBatch(editorState.activeSupplier, date)
      await loadWeekOverview(weekState.selectedRecordDate)
      if (weekState.selectedRecordDate === date) {
        openRecordFromState()
      }
      appendStatus(data.success ? '删除成功，当前周预览已刷新' : '未找到可删除的记录', data.success ? 'success' : 'info')
    } catch (error: any) {
      appendStatus('删除失败：' + getApiErrorMessage(error), 'error')
    }
  }

  function openSavedRecord(quoteDate: string) {
    void selectRecordDate(quoteDate)
  }

  async function openTodayRecord() {
    if (!(await confirmLeaveEditor())) return
    const todayStr = formatDate(new Date())
    const todayMonday = formatDate(mondayOf(new Date()))
    weekState.selectedRecordDate = todayStr
    weekState.selectedWeekMonday = todayMonday
    weekState.selectedMonth = todayStr.slice(0, 7)
    weekState.committedMonth = weekState.selectedMonth
    await loadWeekOverview(todayMonday)
    openRecordFromState()
  }

  async function exportWorkbook() {
    if (!importExportState.workbookTemplateFile) {
      appendStatus('请先选择导出模板文件', 'error')
      return
    }
    if (!previewData.value.total_batches) {
      appendStatus('当前选中周没有可导出的已保存记录', 'error')
      return
    }
    importExportState.exporting = true
    try {
      const payload = await exportWeeklyQuoteSummaryWeekUpload({
        workbookFile: importExportState.workbookTemplateFile,
        date: weekState.selectedWeekMonday,
      })
      triggerDownload(payload)
      appendStatus(`导出成功：${payload.message || payload.filename}`, 'success')
    } catch (error: any) {
      appendStatus('导出失败：' + getApiErrorMessage(error), 'error')
    } finally {
      importExportState.exporting = false
    }
  }

  void (async () => {
    await loadOptions()
    await loadWeekOverview(weekState.selectedWeekMonday)
    openRecordFromState()
  })()

  return {
    suppliers,
    LIMITS,
    activeSupplier: computed({
      get: () => editorState.activeSupplier,
      set: (value: string) => {
        void selectSupplier(value)
      },
    }),
    activeSupplierCount,
    addEntryToCurrentRecord,
    applyRememberedUnit,
    confirmImport,
    confirmImportFromPath,
    confirmCreateSupplier,
    confirmPaste,
    countEntries,
    currentLimit,
    currentRecord,
    currentRecordEntryCount,
    currentRecordSourceLabel,
    currentSummary,
    daysForSelectedWeek,
    deleteCurrentRecord,
    exportWorkbook,
    exporting: computed(() => importExportState.exporting),
    ensureMeasureUnitOption,
    getFileName,
    getRecordSourceLabel,
    hasCurrentDraft,
    importDialogVisible: computed({
      get: () => importExportState.importDialogVisible,
      set: (value: boolean) => { importExportState.importDialogVisible = value },
    }),
    importForm,
    importing: computed(() => importExportState.importing),
    isWeekExpanded,
    measureUnitNames,
    onMonthChange,
    openImportDialog,
    openPasteDialog,
    openSupplierDialog,
    openSavedRecord,
    openTodayRecord,
    pasteDialogVisible: computed({
      get: () => importExportState.pasteDialogVisible,
      set: (value: boolean) => { importExportState.pasteDialogVisible = value },
    }),
    pasteForm,
    pasteParsing: computed(() => importExportState.pasteParsing),
    previewData,
    previewIssues,
    previewing: computed(() => weekState.loading),
    rawRows,
    removeEntry,
    removeSavedRecord,
    saveCurrentDraft,
    saveCurrentRecord,
    savedRecordCounts,
    savedRecordsByWeek,
    selectedMonth: computed({
      get: () => weekState.selectedMonth,
      set: (value: string) => { weekState.selectedMonth = value },
    }),
    selectedRecordDate: computed(() => weekState.selectedRecordDate),
    selectedWeekMonday: computed(() => weekState.selectedWeekMonday),
    selectRecordDate,
    selectSupplier,
    selectWeek,
    setImportSourceFile,
    setWorkbookTemplateFile,
    setWorkbookTemplateFromPath,
    supplierDialog,
    supplierSaving: computed(() => optionsState.addingSupplier),
    toggleWeekExpanded,
    weeksForSelectedMonth,
    workbookPath: computed({
      get: () => importExportState.workbookPath,
      set: (value: string) => { importExportState.workbookPath = value },
    }),
  }
}
