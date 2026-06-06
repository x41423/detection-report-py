import { computed, ref, watch, type Ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'

import {
  executeWeeklyPricePaste,
  getApiErrorMessage,
  previewWeeklyPricePaste,
  type WeeklyPriceMatchedItem,
  type WeeklyPricePreviewResponse,
  type WeeklyPriceSuggestedMatch,
  upsertWeeklyPriceAliases,
} from '../../../api'
import api from '../../../api'
import { triggerDownload } from '../../../utils/download'
import { appendStatus, clearStatus, type StatusLogHandle } from '../../shared/workflow'

interface WeeklyPriceDisplayState {
  matched_count: number
  updated_count: number
  matched_items: WeeklyPriceMatchedItem[]
  not_matched: string[]
  not_matched_count: number
  not_matched_unique_count: number
  alias_hit_count: number
}

export interface ParsedRow {
  id: string
  originalIndex: number
  name: string
  price: string
  status: 'valid' | 'missing-name' | 'missing-price' | 'invalid-price' | 'merged-note'
  isSelected: boolean
  mergedWith?: string[]
  warning?: string
}

const CATEGORY_HEADER_RE = /^(蔬菜类|豆制品|肉类|水产|水果|根茎|叶菜|【|】|\d+[、])/

let rowIdCounter = 0
function generateRowId(): string {
  return `row-${++rowIdCounter}`
}

function parsePrice(text: string): { value: number | null; warning?: string } {
  const trimmed = text.trim()
  if (!trimmed) return { value: null }
  const cleaned = trimmed.replace(/[元块\/\\斤公斤千克][\s]*$/, '')
  const rangeMatch = cleaned.match(/^(\d+\.?\d*)\s*[-~～]\s*(\d+\.?\d*)/)
  if (rangeMatch) {
    return { value: parseFloat(rangeMatch[1]), warning: `疑似区间价格，已取低值 ${rangeMatch[1]}` }
  }
  const numbers = cleaned.match(/\d+\.?\d*/g)
  if (numbers && numbers.length > 1) {
    return { value: parseFloat(numbers[0]), warning: `包含多个数值，已取第一个 ${numbers[0]}` }
  }
  const num = parseFloat(cleaned)
  if (isNaN(num)) return { value: null, warning: '不是有效数字' }
  if (num < 0) return { value: num, warning: '价格为负数' }
  if (num === 0) return { value: 0, warning: '价格为 0' }
  return { value: num }
}

function mergeQuotedLines(lines: string[]): string[] {
  const result: string[] = []
  let i = 0
  while (i < lines.length) {
    const line = lines[i]
    const trimmed = line.trim()
    if (trimmed.startsWith('"') && !trimmed.endsWith('"')) {
      const collected: string[] = [trimmed.substring(1)]
      i++
      while (i < lines.length) {
        const nextLine = lines[i]
        const nextTrimmed = nextLine.trim()
        if (nextTrimmed.endsWith('"')) {
          collected.push(nextTrimmed.substring(0, nextTrimmed.length - 1))
          i++
          break
        } else {
          collected.push(nextTrimmed)
          i++
        }
      }
      result.push(collected.join(' '))
    } else if (trimmed.startsWith('"') && trimmed.endsWith('"') && trimmed.length > 2) {
      result.push(trimmed.substring(1, trimmed.length - 1))
      i++
    } else {
      result.push(line)
      i++
    }
  }
  return result
}

function parseLines(text: string): { rows: ParsedRow[]; skippedHeaders: string[]; emptyCount: number } {
  const rawLines = text.split('\n')
  const rows: ParsedRow[] = []
  const skippedHeaders: string[] = []
  let emptyCount = 0
  const mergedLines = mergeQuotedLines(rawLines)
  for (let i = 0; i < mergedLines.length; i++) {
    const trimmed = mergedLines[i].trim()
    if (!trimmed) {
      emptyCount++
      continue
    }
    if (CATEGORY_HEADER_RE.test(trimmed)) {
      skippedHeaders.push(trimmed)
      continue
    }
    const cleaned = trimmed.replace(/\s+/g, ' ')
    rows.push({
      id: generateRowId(),
      originalIndex: i + 1,
      name: cleaned,
      price: '',
      status: 'missing-price',
      isSelected: false,
    })
  }
  return { rows, skippedHeaders, emptyCount }
}

function getCellText(cell: Element): string {
  const clone = cell.cloneNode(true) as Element
  const brs = clone.querySelectorAll('br')
  brs.forEach(br => {
    br.replaceWith('\n')
  })
  return clone.textContent || ''
}

function parseExcelHtml(html: string): { names: string[]; prices: string[]; columnCount: number } | null {
  try {
    const parser = new DOMParser()
    const doc = parser.parseFromString(html, 'text/html')
    const table = doc.querySelector('table')
    if (!table) return null
    const rows = table.querySelectorAll('tr')
    if (rows.length === 0) return null
    const names: string[] = []
    const prices: string[] = []
    let maxColumnCount = 0
    for (const row of rows) {
      const cells = row.querySelectorAll('td')
      if (cells.length === 0) continue
      maxColumnCount = Math.max(maxColumnCount, cells.length)
      const nameCell = cells[0]
      const priceCell = cells.length > 1 ? cells[1] : null
      const nameText = getCellText(nameCell)
      const priceText = priceCell ? getCellText(priceCell) : ''
      if (nameText.trim()) {
        names.push(nameText.trim())
      }
      if (priceText.trim()) {
        prices.push(priceText.trim())
      }
    }
    if (names.length === 0) return null
    return { names, prices, columnCount: maxColumnCount }
  } catch {
    return null
  }
}

function pairNamesAndPrices(nameRows: ParsedRow[], priceRows: ParsedRow[]): ParsedRow[] {
  const maxLen = Math.max(nameRows.length, priceRows.length)
  const result: ParsedRow[] = []
  for (let i = 0; i < maxLen; i++) {
    const nameRow = nameRows[i]
    const priceRow = priceRows[i]
    if (!nameRow) {
      result.push({
        id: generateRowId(),
        originalIndex: i + 1,
        name: '',
        price: priceRow.price,
        status: 'missing-name',
        isSelected: false,
      })
    } else if (!priceRow) {
      result.push({ ...nameRow, status: 'missing-price' })
    } else {
      const { value, warning } = parsePrice(priceRow.name)
      if (value === null) {
        result.push({ ...nameRow, price: priceRow.name, status: 'invalid-price', warning: warning || '不是有效数字' })
      } else {
        result.push({ ...nameRow, price: String(value), status: 'valid', ...(warning ? { warning } : {}) })
      }
    }
  }
  return result
}

function mergeSuggestionSelections(suggestions: WeeklyPriceSuggestedMatch[], previousSelections: Record<string, string>) {
  const nextSelections: Record<string, string> = {}
  suggestions.forEach((item) => {
    const candidateTargets = new Set(item.candidates.map((candidate) => candidate.target_name))
    const previousTarget = previousSelections[item.source_name]
    if (previousTarget && candidateTargets.has(previousTarget)) {
      nextSelections[item.source_name] = previousTarget
      return
    }
    if (item.preselected_target_name && candidateTargets.has(item.preselected_target_name)) {
      nextSelections[item.source_name] = item.preselected_target_name
    }
  })
  return nextSelections
}

function mergeIgnoredSuggestionSources(suggestions: WeeklyPriceSuggestedMatch[], previousIgnoredSources: string[]) {
  const validSources = new Set(suggestions.map((item) => item.source_name))
  return Array.from(new Set(previousIgnoredSources.filter((sourceName) => validSources.has(sourceName))))
}

export function useWeeklyPriceUpdateWorkflow(statusLogRef: Ref<StatusLogHandle | undefined>) {
  const router = useRouter()

  const pasteNames = ref('')
  const pastePrices = ref('')
  const previewing = ref(false)
  const savingAliases = ref(false)
  const executing = ref(false)
  const activeDetailTab = ref<'matched' | 'unmatched'>('matched')
  const previewData = ref<WeeklyPricePreviewResponse | null>(null)
  const downloadedFileName = ref('')
  const suggestionSelections = ref<Record<string, string>>({})
  const ignoredSuggestionSources = ref<string[]>([])
  const parsedNames = computed(() => parseLines(pasteNames.value))
  const parsedPrices = computed(() => parseLines(pastePrices.value))
  const pairingRows = ref<ParsedRow[]>([])
  const selectedRowIds = ref<Set<string>>(new Set())

  watch([parsedNames, parsedPrices], () => {
    pairingRows.value = pairNamesAndPrices(parsedNames.value.rows, parsedPrices.value.rows)
    selectedRowIds.value = new Set()
  }, { immediate: true })

  const validPairCount = computed(() => pairingRows.value.filter(p => p.status === 'valid').length)
  const hasMismatch = computed(() => parsedNames.value.rows.length !== parsedPrices.value.rows.length)
  const mismatchMessage = computed(() => {
    if (!hasMismatch.value) return ''
    return `菜名 ${parsedNames.value.rows.length} 条，价格 ${parsedPrices.value.rows.length} 条，数量不对应，请检查粘贴内容`
  })

  const validationMessages = computed(() => {
    const msgs: { type: 'warning' | 'info' | 'success'; text: string }[] = []
    const emptyTotal = parsedNames.value.emptyCount + parsedPrices.value.emptyCount
    if (emptyTotal > 0) {
      msgs.push({ type: 'info', text: `已自动跳过 ${emptyTotal} 个空行` })
    }
    const headerTotal = parsedNames.value.skippedHeaders.length + parsedPrices.value.skippedHeaders.length
    if (headerTotal > 0) {
      const headers = [...new Set([...parsedNames.value.skippedHeaders, ...parsedPrices.value.skippedHeaders])]
      msgs.push({ type: 'info', text: `已自动跳过 ${headerTotal} 行疑似分类标题：${headers.slice(0, 3).join('、')}${headers.length > 3 ? '…' : ''}` })
    }
    if (mismatchMessage.value) {
      msgs.push({ type: 'warning', text: mismatchMessage.value })
    }
    const invalidPrices = pairingRows.value.filter(p => p.status === 'invalid-price')
    for (const row of invalidPrices) {
      msgs.push({ type: 'warning', text: `第 ${row.originalIndex} 行"${row.name}"的价格"${row.price}"${row.warning || '不是有效数字'}` })
    }
    return msgs
  })

  const hasValidData = computed(() => validPairCount.value > 0)

  // merge / split
  function mergeSelectedRows() {
    const selectedIds = Array.from(selectedRowIds.value)
    if (selectedIds.length < 2) {
      ElMessage.warning('请至少选择 2 行再合并')
      return
    }
    const selected = pairingRows.value.filter(r => selectedIds.includes(r.id))
    const others = pairingRows.value.filter(r => !selectedIds.includes(r.id))
    const mergedNames = selected.map(r => r.name).filter(Boolean).join(' ')
    const mergedPrice = selected.find(r => r.price)?.price || ''
    const merged: ParsedRow = {
      id: generateRowId(),
      originalIndex: selected[0].originalIndex,
      name: mergedNames,
      price: mergedPrice,
      status: mergedPrice ? 'valid' : 'missing-price',
      isSelected: false,
      mergedWith: selected.map(r => r.id),
    }
    const result = [...others, merged]
    result.sort((a, b) => a.originalIndex - b.originalIndex)
    pairingRows.value = result
    selectedRowIds.value = new Set()
    ElMessage.success(`已合并 ${selected.length} 行为 1 行`)
  }

  function splitSelectedRows() {
    const selectedIds = Array.from(selectedRowIds.value)
    if (selectedIds.length !== 1) {
      ElMessage.warning('请选择 1 个合并行再拆分')
      return
    }
    const row = pairingRows.value.find(r => selectedIds.includes(r.id))
    if (!row || !row.mergedWith) {
      ElMessage.warning('该行不是合并行，无法拆分')
      return
    }
    const nameParts = row.name.split(' ')
    const originalRows: ParsedRow[] = []
    for (let i = 0; i < row.mergedWith.length; i++) {
      originalRows.push({
        id: row.mergedWith[i],
        originalIndex: row.originalIndex + i,
        name: nameParts[i] || '',
        price: i === 0 ? row.price : '',
        status: i === 0 ? (row.price ? 'valid' : 'missing-price') : 'missing-price',
        isSelected: false,
      })
    }
    const result = pairingRows.value.filter(r => r.id !== row.id).concat(originalRows)
    result.sort((a, b) => a.originalIndex - b.originalIndex)
    pairingRows.value = result
    selectedRowIds.value = new Set()
    ElMessage.success('已拆分选中行')
  }

  // clipboard HTML parse
  function handlePaste(event: ClipboardEvent, target: 'names' | 'prices') {
    const clipboardData = event.clipboardData
    if (!clipboardData) return
    const html = clipboardData.getData('text/html')
    if (html) {
      const parsed = parseExcelHtml(html)
      if (parsed) {
        event.preventDefault()
        if (parsed.columnCount >= 2) {
          pasteNames.value = parsed.names.join('\n')
          pastePrices.value = parsed.prices.join('\n')
        } else {
          if (target === 'names') {
            pasteNames.value = parsed.names.join('\n')
          } else {
            pastePrices.value = parsed.names.join('\n')
          }
        }
        return
      }
    }
  }

  // Excel file import
  const isImporting = ref(false)
  async function importExcelFile(file: File) {
    isImporting.value = true
    try {
      const formData = new FormData()
      formData.append('file', file)
      const response = await api.post('/api/weekly-price/import-reference', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      const data = response.data
      if (data.names && data.prices) {
        pasteNames.value = data.names.join('\n')
        pastePrices.value = data.prices.join('\n')
        ElMessage.success(`已导入 ${data.names.length} 条数据`)
      }
    } catch (error: any) {
      ElMessage.error('导入失败：' + (error.response?.data?.detail || error.message || '未知错误'))
    } finally {
      isImporting.value = false
    }
  }

  function handleFileChange(event: Event) {
    const input = event.target as HTMLInputElement
    const file = input.files?.[0]
    if (file) {
      importExcelFile(file)
    }
    input.value = ''
  }

  // preview / execute
  const previewReady = computed(() => Boolean(previewData.value))
  const previewWarnings = computed(() => previewData.value?.warnings || [])
  const outputPath = computed(() => downloadedFileName.value)
  const displayState = computed<WeeklyPriceDisplayState>(() => {
    if (previewData.value) return previewData.value
    return { matched_count: 0, updated_count: 0, matched_items: [], not_matched: [], not_matched_count: 0, not_matched_unique_count: 0, alias_hit_count: 0 }
  })
  const changedCount = computed(() => displayState.value.matched_items.filter((item) => item.changed).length)
  const suggestedRows = computed(() => previewData.value?.suggested_matches || [])
  const ignoredSourceSet = computed(() => new Set(ignoredSuggestionSources.value))
  const actionableSuggestionRows = computed(() =>
    suggestedRows.value.filter((item) => item.candidates.length > 0 && !ignoredSourceSet.value.has(item.source_name)))
  const noCandidateRows = computed(() => suggestedRows.value.filter((item) => item.candidates.length === 0))
  const selectedSuggestionCount = computed(() =>
    actionableSuggestionRows.value.filter((item) => Boolean(suggestionSelections.value[item.source_name])).length)
  const unresolvedSuggestionCount = computed(() => actionableSuggestionRows.value.length - selectedSuggestionCount.value)
  const hasSavableMappings = computed(() =>
    actionableSuggestionRows.value.some((item) => Boolean(suggestionSelections.value[item.source_name])))
  const unmatchedDetailRows = computed(() => {
    const suggestionMap = new Map<string, WeeklyPriceSuggestedMatch>()
    suggestedRows.value.forEach((item) => suggestionMap.set(item.source_name, item))
    return displayState.value.not_matched.map((name) => {
      const suggestion = suggestionMap.get(name)
      const hasCandidates = Boolean(suggestion?.candidates.length)
      return {
        name,
        statusLabel: hasCandidates ? '待确认候选' : '无候选',
        statusType: hasCandidates ? 'warning' : 'info',
        suggestionText: hasCandidates ? suggestion!.candidates.map((c) => `${c.target_name} (${formatScore(c.score)})`).join(' / ') : '暂无建议，请人工排查',
      }
    })
  })

  function formatPrice(price: number | null) {
    if (price === null || Number.isNaN(price)) return '-'
    return `${price}`
  }

  function formatScore(score: number) {
    return `${Math.round(score * 100)}%`
  }

  function isIgnored(sourceName: string) { return ignoredSourceSet.value.has(sourceName) }

  function updateSuggestionSelection(sourceName: string, targetName: string | undefined) {
    const nextSelections = { ...suggestionSelections.value }
    if (!targetName) delete nextSelections[sourceName]
    else nextSelections[sourceName] = targetName
    suggestionSelections.value = nextSelections
  }

  function toggleIgnore(sourceName: string) {
    if (isIgnored(sourceName)) {
      ignoredSuggestionSources.value = ignoredSuggestionSources.value.filter((item) => item !== sourceName)
      return
    }
    ignoredSuggestionSources.value = [...ignoredSuggestionSources.value, sourceName]
  }

  function openAliasLibrary(sourceName: string = '') {
    router.push({ path: '/weekly-price-aliases', query: sourceName ? { source: sourceName } : undefined })
  }

  function resetAnalysis() {
    previewData.value = null
    downloadedFileName.value = ''
    suggestionSelections.value = {}
    ignoredSuggestionSources.value = []
    activeDetailTab.value = 'matched'
  }

  function resetForm() {
    pasteNames.value = ''
    pastePrices.value = ''
    pairingRows.value = []
    selectedRowIds.value = new Set()
    resetAnalysis()
    clearStatus(statusLogRef)
  }

  async function runPreview() {
    if (!hasValidData.value) {
      ElMessage.warning('请在菜名框和价格框中粘贴数据后再运行预检')
      return
    }
    previewing.value = true
    clearStatus(statusLogRef)
    appendStatus(statusLogRef, '开始预检每周报价...', 'info')
    const validRows = pairingRows.value.filter(r => r.status === 'valid')
    const names = validRows.map(r => r.name)
    const prices = validRows.map(r => r.price)
    try {
      const { data } = await previewWeeklyPricePaste({ names, prices })
      previewData.value = data
      downloadedFileName.value = ''
      suggestionSelections.value = mergeSuggestionSelections(data.suggested_matches || [], suggestionSelections.value)
      ignoredSuggestionSources.value = mergeIgnoredSuggestionSources(data.suggested_matches || [], ignoredSuggestionSources.value)
      activeDetailTab.value = data.not_matched_unique_count ? 'unmatched' : 'matched'
      appendStatus(statusLogRef, data.message, 'success')
    } catch (error: any) {
      appendStatus(statusLogRef, '预检失败：' + getApiErrorMessage(error), 'error')
      ElMessage.error('预检失败')
    } finally {
      previewing.value = false
    }
  }

  async function saveSelectedAliasesAndRepreview() {
    const mappings = Object.fromEntries(
      actionableSuggestionRows.value
        .map((item) => [item.source_name, suggestionSelections.value[item.source_name] || ''])
        .filter(([, targetName]) => Boolean(targetName)))
    if (!Object.keys(mappings).length) {
      ElMessage.warning('请至少选择一条映射后再保存')
      return
    }
    savingAliases.value = true
    try {
      await upsertWeeklyPriceAliases(mappings)
      appendStatus(statusLogRef, `已保存 ${Object.keys(mappings).length} 条别名映射`, 'success')
      await runPreview()
    } catch (error: any) {
      appendStatus(statusLogRef, '保存别名失败：' + getApiErrorMessage(error), 'error')
      ElMessage.error('保存别名失败')
    } finally {
      savingAliases.value = false
    }
  }

  async function runUpdate() {
    if (!hasValidData.value) {
      ElMessage.warning('请在菜名框和价格框中粘贴数据后再运行预检')
      return
    }
    if (!previewReady.value) {
      ElMessage.warning('请先完成一次有效预检')
      return
    }
    const pendingCount = unresolvedSuggestionCount.value
    const hardUnmatchedCount = noCandidateRows.value.length
    if (pendingCount || hardUnmatchedCount) {
      try {
        await ElMessageBox.confirm(
          `还有 ${pendingCount} 个候选未确认，${hardUnmatchedCount} 个菜名无候选。继续执行时，未匹配行将在 G 列留空。是否继续？`,
          '继续执行更新？',
          { confirmButtonText: '继续执行', cancelButtonText: '先处理未匹配项', type: 'warning' })
      } catch { return }
    }
    executing.value = true
    appendStatus(statusLogRef, '开始执行每周报价更新...', 'info')
    const validRows = pairingRows.value.filter(r => r.status === 'valid')
    const names = validRows.map(r => r.name)
    const prices = validRows.map(r => r.price)
    try {
      const payload = await executeWeeklyPricePaste({ names, prices })
      triggerDownload(payload)
      downloadedFileName.value = payload.filename
      appendStatus(statusLogRef, payload.message || `已下载更新后的报价文件: ${payload.filename}`, 'success')
    } catch (error: any) {
      appendStatus(statusLogRef, '执行失败：' + getApiErrorMessage(error), 'error')
      ElMessage.error('执行失败')
    } finally {
      executing.value = false
    }
  }

  return {
    pasteNames,
    pastePrices,
    parsedNames,
    parsedPrices,
    pairingRows,
    selectedRowIds,
    mergeSelectedRows,
    splitSelectedRows,
    validPairCount,
    hasMismatch,
    mismatchMessage,
    validationMessages,
    hasValidData,
    activeDetailTab,
    actionableSuggestionRows,
    changedCount,
    displayState,
    downloadedFileName,
    executing,
    formatPrice,
    formatScore,
    hasSavableMappings,
    isIgnored,
    noCandidateRows,
    openAliasLibrary,
    outputPath,
    previewData,
    previewReady,
    previewStatusNote: computed(() => {
      if (previewReady.value) return '当前数据已完成预检，可以继续执行更新。'
      return '请先粘贴菜名和价格，再运行预检。'
    }),
    previewWarnings,
    previewing,
    resetForm,
    handlePaste,
    isImporting,
    importExcelFile,
    handleFileChange,
    runPreview,
    runUpdate,
    saveSelectedAliasesAndRepreview,
    savingAliases,
    selectedSuggestionCount,
    suggestionSelections,
    suggestedRows,
    toggleIgnore,
    unmatchedDetailRows,
    unresolvedSuggestionCount,
    unchangedCount: computed(() => displayState.value.matched_items.length - changedCount.value),
    updateSuggestionSelection,
  }
}

