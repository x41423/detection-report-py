import { computed, reactive, ref, watch, type Ref } from 'vue'

import type { StatusLogHandle } from '../../shared/workflow'

import {
  saveQuoteBatch,
  listQuoteBatches,
  deleteQuoteBatch,
  getWeeklyQuoteSummary,
  listSuppliers,
  importWeeklyQuoteBatch,
  exportWeeklyQuoteSummary,
} from '../../../api/weekly-price'

/**
 * Weekly-quote summary workflow composable.
 *
 * The original rich implementation was wiped during a prior incident and is
 * being rebuilt incrementally. This revision focuses on two things:
 *
 * 1. Expose the *exact* shape consumed by `WeeklyQuoteSummaryWorkflow.vue` so
 *    the page mounts, renders all panels and reacts to clicks without any
 *    runtime "undefined" / "is not iterable" errors.
 * 2. Gate every mutation behind a clearly-labelled "feature is being rebuilt"
 *    notice via the status log.  Navigation-only actions (supplier switch,
 *    date picker, week expansion) continue to work locally so the layout can
 *    be reviewed end-to-end.
 *
 * The shapes below intentionally mirror what the Vue template accesses:
 *
 *   LIMITS[supplier]                    -> number
 *   savedRecordsByWeek[i].monday        -> string
 *   savedRecordsByWeek[i].records[j]... -> WeeklyQuoteSavedRecord
 *   daysForSelectedWeek[i].dayLabel     -> string
 *   weeksForSelectedMonth[i].monday     -> string
 *   currentSummary.summary_items[k]...  -> summary row
 *
 * Keep any future refactor compatible with these shapes – the template does
 * not tolerate the generic `string[]` / `Record<string, …>` forms we used in
 * the very first recovery stub.
 */

const suppliers = ref<string[]>(['勾庄', '理想', '刘慧', '酱菜', '豆制品'])

const LIMITS: Record<string, number> = {
  勾庄: 7,
  理想: 7,
  刘慧: 7,
  酱菜: 7,
  豆制品: 7,
}

const DAY_LABELS = ['周一', '周二', '周三', '周四', '周五', '周六', '周日'] as const

interface WeeklyQuoteEntry {
  id: string
  name: string
  unit: string
  price: number
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

interface WeeklyQuoteSummaryItem {
  name: string
  unit: string
  summary_price: number
}

interface WeeklyQuoteSummary {
  batch_count: number
  entry_count: number
  summary_items: WeeklyQuoteSummaryItem[]
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
  hasRecord: boolean
}

interface WeeklyQuoteWeekCell {
  monday: string
  label: string
}

function pad(n: number): string {
  return n < 10 ? `0${n}` : String(n)
}

function formatDate(date: Date): string {
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`
}

function parseDate(value: string): Date | null {
  if (!value) return null
  const [y, m, d] = value.split('-').map((part) => Number.parseInt(part, 10))
  if (!y || !m || !d) return null
  const dt = new Date(y, m - 1, d)
  return Number.isNaN(dt.getTime()) ? null : dt
}

function mondayOf(date: Date): Date {
  const result = new Date(date)
  const day = (result.getDay() + 6) % 7 // Mon=0..Sun=6
  result.setDate(result.getDate() - day)
  result.setHours(0, 0, 0, 0)
  return result
}

function addDays(date: Date, days: number): Date {
  const result = new Date(date)
  result.setDate(result.getDate() + days)
  return result
}

export function useWeeklyQuoteSummaryWorkflow(
  statusLogRef: Ref<StatusLogHandle | undefined>,
) {
  const today = new Date()

  const activeSupplier = ref<string>(suppliers.value[0])
  const selectedMonth = ref(`${today.getFullYear()}-${pad(today.getMonth() + 1)}`)
  const selectedWeekMonday = ref(formatDate(mondayOf(today)))
  const selectedRecordDate = ref(formatDate(today))

  const importDialogVisible = ref(false)
  const pasteDialogVisible = ref(false)
  const importing = ref(false)
  const pasteParsing = ref(false)
  const previewing = ref(false)
  const exporting = ref(false)

  const workbookPath = ref('')

  const importForm = reactive({
    quote_date: formatDate(today),
    source_path: '',
  })
  const pasteForm = reactive<{
    mode: 'columns' | 'lines'
    names: string
    prices: string
    text: string
  }>({
    mode: 'columns',
    names: '',
    prices: '',
    text: '',
  })

  const rawRows = ref<WeeklyQuoteRawRow[]>([])
  let _nextEntryCounter = 0

  const previewData = ref<WeeklyQuotePreview | null>(null)
  const previewIssues = ref<string[]>([])

  const currentRecord = ref<WeeklyQuoteSavedRecord | null>(null)
  const currentSummary = ref<WeeklyQuoteSummary | null>(null)

  // Keyed by supplier, then by quote_date.  Persistence (localStorage /
  // backend) is deferred until the full workflow is rebuilt.
  const savedRecords = ref<Record<string, Record<string, WeeklyQuoteSavedRecord>>>({})

  const expandedWeeks = ref<Record<string, boolean>>({})

  const savedRecordCounts = computed<Record<string, number>>(() => {
    const result = {} as Record<string, number>
    for (const supplier of suppliers.value) {
      result[supplier] = Object.keys(savedRecords.value[supplier] || {}).length
    }
    return result
  })

  const activeSupplierCount = computed(() => savedRecordCounts.value[activeSupplier.value] || 0)
  const currentLimit = computed(() => LIMITS[activeSupplier.value] ?? 0)

  const currentRecordEntryCount = computed(() => rawRows.value.length)

  const currentRecordSourceLabel = computed(() => {
    if (!currentRecord.value) return '尚未保存'
    return currentRecord.value.source_label || '手动录入'
  })

  const weeksForSelectedMonth = computed<WeeklyQuoteWeekCell[]>(() => {
    const [yearStr, monthStr] = selectedMonth.value.split('-')
    const year = Number.parseInt(yearStr, 10)
    const month = Number.parseInt(monthStr, 10)
    if (!year || !month) return []
    const firstDay = new Date(year, month - 1, 1)
    const lastDay = new Date(year, month, 0)
    const mondays: WeeklyQuoteWeekCell[] = []
    let cursor = mondayOf(firstDay)
    while (cursor <= lastDay) {
      const sunday = addDays(cursor, 6)
      const label = `${pad(cursor.getMonth() + 1)}/${pad(cursor.getDate())} – ${pad(sunday.getMonth() + 1)}/${pad(sunday.getDate())}`
      mondays.push({ monday: formatDate(cursor), label })
      cursor = addDays(cursor, 7)
    }
    return mondays
  })

  const daysForSelectedWeek = computed<WeeklyQuoteDayCell[]>(() => {
    const monday = parseDate(selectedWeekMonday.value)
    if (!monday) return []
    const supplierRecords = savedRecords.value[activeSupplier.value] || {}
    return Array.from({ length: 7 }, (_, offset) => {
      const day = addDays(monday, offset)
      const dateStr = formatDate(day)
      const record = supplierRecords[dateStr]
      return {
        date: dateStr,
        dayLabel: DAY_LABELS[offset],
        dateLabel: `${pad(day.getMonth() + 1)}/${pad(day.getDate())}`,
        entryCount: record ? record.entries.length : 0,
        hasRecord: Boolean(record),
      }
    })
  })

  const savedRecordsByWeek = computed<WeeklyQuoteWeekGroup[]>(() => {
    const supplierRecords = savedRecords.value[activeSupplier.value] || {}
    const groups = new Map<string, WeeklyQuoteWeekGroup>()
    for (const record of Object.values(supplierRecords)) {
      const date = parseDate(record.quote_date)
      if (!date) continue
      const monday = formatDate(mondayOf(date))
      let group = groups.get(monday)
      if (!group) {
        const mondayDate = parseDate(monday)!
        const sunday = addDays(mondayDate, 6)
        group = {
          monday,
          label: `${pad(mondayDate.getMonth() + 1)}/${pad(mondayDate.getDate())} – ${pad(sunday.getMonth() + 1)}/${pad(sunday.getDate())}`,
          records: [],
          totalEntries: 0,
        }
        groups.set(monday, group)
      }
      group.records.push(record)
      group.totalEntries += record.entries.length
    }
    const result = Array.from(groups.values())
    result.sort((a, b) => (a.monday < b.monday ? 1 : -1))
    for (const group of result) {
      group.records.sort((a, b) => (a.quote_date < b.quote_date ? 1 : -1))
    }
    return result
  })

  // ------------------------------------------------------------------
  // Navigation handlers (fully functional – no backend required)
  // ------------------------------------------------------------------
  function isWeekExpanded(weekMonday: string) {
    return Boolean(expandedWeeks.value[weekMonday])
  }
  function toggleWeekExpanded(weekMonday: string) {
    expandedWeeks.value = {
      ...expandedWeeks.value,
      [weekMonday]: !expandedWeeks.value[weekMonday],
    }
  }
  function selectRecordDate(date: string) {
    selectedRecordDate.value = date
    const record = savedRecords.value[activeSupplier.value]?.[date] || null
    currentRecord.value = record
    rawRows.value = record
      ? record.entries.map((entry) => ({ entry: { ...entry } }))
      : []
    refreshWeeklySummary()
  }
  function selectWeek(weekMonday: string) {
    selectedWeekMonday.value = weekMonday
  }
  function onMonthChange(value: string) {
    selectedMonth.value = value
    const weeks = weeksForSelectedMonth.value
    if (weeks.length) {
      selectedWeekMonday.value = weeks[0].monday
    }
  }

  // ------------------------------------------------------------------
  // Display helpers consumed by the template
  // ------------------------------------------------------------------
  function getFileName(path: string | null | undefined): string {
    const text = (path || '').toString().trim()
    if (!text) return ''
    const normalized = text.replace(/\\/g, '/')
    const idx = normalized.lastIndexOf('/')
    return idx >= 0 ? normalized.slice(idx + 1) : normalized
  }
  function countEntries(record: WeeklyQuoteSavedRecord | null | undefined): number {
    return record?.entries?.length ?? 0
  }
  function getRecordSourceLabel(record: WeeklyQuoteSavedRecord | null | undefined): string {
    return record?.source_label || '手动录入'
  }

  // ------------------------------------------------------------------
  // Mutating actions
  // ------------------------------------------------------------------
  function applyRememberedUnit(_entry?: WeeklyQuoteEntry) {
    /* no-op while feature is offline */
  }
  function setImportSourceFile(files: FileList | null | undefined) {
    const file = files?.[0]
    if (file) {
      importForm.source_path = (file as File & { path?: string }).path || file.name
    }
  }
  function setWorkbookTemplateFile(files: FileList | null | undefined) {
    const file = files?.[0]
    if (file) {
      workbookPath.value = (file as File & { path?: string }).path || file.name
    }
  }
  function openImportDialog() {
    importForm.quote_date = selectedRecordDate.value
    importDialogVisible.value = true
  }
  function openPasteDialog() {
    pasteDialogVisible.value = true
  }
  async function confirmImport() {
    if (!importForm.source_path) {
      statusLogRef.value?.append?.('请先选择要导入的 Excel 文件', 'error')
      return
    }
    importing.value = true
    try {
      const res = await importWeeklyQuoteBatch({
        supplier: activeSupplier.value,
        quote_date: importForm.quote_date,
        source_path: importForm.source_path,
      })
      await loadRecords(activeSupplier.value)
      selectRecordDate(importForm.quote_date)
      importDialogVisible.value = false
      importForm.source_path = ''
      statusLogRef.value?.append?.(
        `导入成功：${res.data.message || '已完成'}`,
        'success',
      )
    } catch (e: any) {
      statusLogRef.value?.append?.(
        `导入失败: ${e.response?.data?.detail || e.message || e}`,
        'error',
      )
    } finally {
      importing.value = false
    }
  }
  function confirmPaste() {
    pasteParsing.value = true
    try {
      const lines =
        pasteForm.mode === 'lines'
          ? pasteForm.text.split('\n').filter((l) => l.trim())
          : []
      const names =
        pasteForm.mode === 'columns'
          ? pasteForm.names.split('\n').filter((l) => l.trim())
          : []
      const prices =
        pasteForm.mode === 'columns'
          ? pasteForm.prices.split('\n').filter((l) => l.trim())
          : []

      if (pasteForm.mode === 'lines') {
        for (const line of lines) {
          const parts = line.trim().split(/\s+/)
          if (parts.length >= 2) {
            _nextEntryCounter++
            const name = parts[0]
            const price = parseFloat(parts[parts.length - 1])
            const unit = parts.length >= 3 ? parts[parts.length - 2] : '斤'
            if (!Number.isNaN(price) && name) {
              rawRows.value.push({
                entry: {
                  id: `paste-${Date.now()}-${_nextEntryCounter}`,
                  name,
                  unit: /^[\u4e00-\u9fa5a-zA-Z]+$/.test(unit) ? unit : '斤',
                  price,
                },
              })
            }
          }
        }
      } else {
        const maxLen = Math.max(names.length, prices.length)
        for (let i = 0; i < maxLen; i++) {
          const name = (names[i] || '').trim()
          const price = parseFloat((prices[i] || '').trim())
          if (name && !Number.isNaN(price)) {
            _nextEntryCounter++
            rawRows.value.push({
              entry: {
                id: `paste-${Date.now()}-${_nextEntryCounter}`,
                name,
                unit: '斤',
                price,
              },
            })
          }
        }
      }
      statusLogRef.value?.append?.(
        `识别完成：新增记录`,
        'success',
      )
      pasteDialogVisible.value = false
      pasteForm.names = ''
      pasteForm.prices = ''
      pasteForm.text = ''
    } catch (e: any) {
      statusLogRef.value?.append?.(
        `识别失败: ${e.message || e}`,
        'error',
      )
    } finally {
      pasteParsing.value = false
    }
  }
  function addEntryToCurrentRecord() {
    _nextEntryCounter++
    rawRows.value.push({
      entry: {
        id: `new-${Date.now()}-${_nextEntryCounter}`,
        name: '',
        unit: '斤',
        price: 0,
      },
    })
  }
  function removeEntry(entryId: string) {
    rawRows.value = rawRows.value.filter((r) => r.entry.id !== entryId)
  }

  async function loadSuppliersList() {
    try {
      const res = await listSuppliers()
      if (res.data.suppliers?.length) {
        suppliers.value = res.data.suppliers
        if (!suppliers.value.includes(activeSupplier.value)) {
          activeSupplier.value = suppliers.value[0]
        }
      }
    } catch (e) {
      console.error('Failed to load suppliers', e)
    }
  }

  async function loadRecords(supplier: string) {
    try {
      const res = await listQuoteBatches(supplier)
      const records: Record<string, WeeklyQuoteSavedRecord> = {}
      for (const batch of res.data.batches || []) {
        records[batch.quote_date] = {
          id: String(batch.id),
          supplier: batch.supplier,
          quote_date: batch.quote_date,
          entries: (batch.entries || []).map((e: any, i: number) => ({
            id: `${batch.id}-${i}`,
            name: e.name,
            unit: e.unit || '斤',
            price: e.price,
          })),
          source_label: batch.source_label || '',
          source_path: batch.source_path || '',
          updated_at: batch.created_at || '',
        }
      }
      savedRecords.value[supplier] = records
    } catch (e) {
      console.error('Failed to load records', e)
    }
  }

  async function refreshWeeklySummary() {
    if (!activeSupplier.value || !selectedRecordDate.value) return
    try {
      const res = await getWeeklyQuoteSummary(activeSupplier.value, selectedRecordDate.value)
      currentSummary.value = {
        batch_count: 0,
        entry_count: 0,
        summary_items: (res.data.summary_items || []).map((item: any) => ({
          name: item.name,
          unit: item.unit,
          summary_price: item.summary_price,
        })),
      }
    } catch (e) {
      console.error('Failed to load weekly summary', e)
    }
  }

  async function saveCurrentRecord() {
    if (!rawRows.value.length) {
      statusLogRef.value?.append?.('当前日期还没有录入记录，请先通过「新增一条报价」「Excel导入」或「批量粘贴识别」添加记录后再保存。', 'error')
      return
    }
    const invalid = rawRows.value.filter(r => !r.entry.name.trim() || r.entry.price <= 0)
    if (invalid.length) {
      statusLogRef.value?.append?.(`有 ${invalid.length} 条记录缺少菜名或有效单价，请完善后重新保存。`, 'error')
      return
    }
    try {
      await saveQuoteBatch({
        supplier: activeSupplier.value,
        quote_date: selectedRecordDate.value,
        entries: rawRows.value.map(r => ({
          name: r.entry.name,
          unit: r.entry.unit,
          price: r.entry.price,
        })),
        source_label: '手动录入',
      })
      await loadRecords(activeSupplier.value)
      rawRows.value = []
      statusLogRef.value?.append?.('保存成功', 'success')
    } catch (e: any) {
      statusLogRef.value?.append?.(`保存失败: ${e.response?.data?.detail || e.message || e}`, 'error')
    }
  }

  async function removeSavedRecord(date: string) {
    try {
      await deleteQuoteBatch(activeSupplier.value, date)
      await loadRecords(activeSupplier.value)
      if (selectedRecordDate.value === date) {
        rawRows.value = []
      }
      statusLogRef.value?.append?.('删除成功', 'success')
    } catch (e: any) {
      statusLogRef.value?.append?.(`删除失败: ${e.response?.data?.detail || e.message || e}`, 'error')
    }
  }

  function openSavedRecord(quoteDate: string) {
    selectRecordDate(quoteDate)
  }
  function openTodayRecord() {
    const todayStr = formatDate(new Date())
    selectedRecordDate.value = todayStr
    const monday = formatDate(mondayOf(new Date()))
    selectedWeekMonday.value = monday
    selectedMonth.value = todayStr.slice(0, 7)
    selectRecordDate(todayStr)
  }
  async function exportWorkbook() {
    if (!workbookPath.value) {
      statusLogRef.value?.append?.('请先选择导出模板文件', 'error')
      return
    }
    exporting.value = true
    try {
      const batches: Array<{ supplier: string; quote_date: string; entries: Array<{ name: string; unit: string; price: number }> }> = []
      for (const supplier of Object.keys(savedRecords.value)) {
        const records = savedRecords.value[supplier] || {}
        for (const date of Object.keys(records)) {
          batches.push({
            supplier,
            quote_date: date,
            entries: records[date].entries.map((e) => ({
              name: e.name,
              unit: e.unit,
              price: e.price,
            })),
          })
        }
      }
      const res = await exportWeeklyQuoteSummary({
        workbook_path: workbookPath.value,
        batches,
      })
      statusLogRef.value?.append?.(
        `导出成功：${res.data.message || '已完成'}`,
        'success',
      )
    } catch (e: any) {
      statusLogRef.value?.append?.(
        `导出失败: ${e.response?.data?.detail || e.message || e}`,
        'error',
      )
    } finally {
      exporting.value = false
    }
  }

  watch(activeSupplier, (newVal) => {
    if (newVal && !savedRecords.value[newVal]) {
      loadRecords(newVal)
    }
  })

  loadSuppliersList().then(() => {
    if (suppliers.value.length > 0) {
      activeSupplier.value = suppliers.value[0]
      loadRecords(activeSupplier.value)
    }
  })

  return {
    suppliers,
    LIMITS,
    activeSupplier,
    activeSupplierCount,
    addEntryToCurrentRecord,
    applyRememberedUnit,
    confirmImport,
    confirmPaste,
    countEntries,
    currentLimit,
    currentRecord,
    currentRecordEntryCount,
    currentRecordSourceLabel,
    currentSummary,
    daysForSelectedWeek,
    exportWorkbook,
    exporting,
    getFileName,
    getRecordSourceLabel,
    importDialogVisible,
    importForm,
    importing,
    isWeekExpanded,
    onMonthChange,
    openImportDialog,
    openPasteDialog,
    openSavedRecord,
    openTodayRecord,
    pasteDialogVisible,
    pasteForm,
    pasteParsing,
    previewData,
    previewIssues,
    previewing,
    rawRows,
    removeEntry,
    removeSavedRecord,
    saveCurrentRecord,
    savedRecordCounts,
    savedRecordsByWeek,
    selectedMonth,
    selectedRecordDate,
    selectedWeekMonday,
    selectRecordDate,
    selectWeek,
    setImportSourceFile,
    setWorkbookTemplateFile,
    toggleWeekExpanded,
    weeksForSelectedMonth,
    workbookPath,
  }
}
