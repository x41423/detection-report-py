import { computed, ref, type Ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'

import {
  executeWeeklyPriceUpload,
  getApiErrorMessage,
  previewWeeklyPriceUpload,
  type WeeklyPriceMatchedItem,
  type WeeklyPricePreviewResponse,
  type WeeklyPriceSuggestedMatch,
  upsertWeeklyPriceAliases,
} from '../../../api'
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

function mergeSuggestionSelections(
  suggestions: WeeklyPriceSuggestedMatch[],
  previousSelections: Record<string, string>,
) {
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

function mergeIgnoredSuggestionSources(
  suggestions: WeeklyPriceSuggestedMatch[],
  previousIgnoredSources: string[],
) {
  const validSources = new Set(suggestions.map((item) => item.source_name))
  return Array.from(
    new Set(previousIgnoredSources.filter((sourceName) => validSources.has(sourceName))),
  )
}

export function useWeeklyPriceUpdateWorkflow(
  statusLogRef: Ref<StatusLogHandle | undefined>,
) {
  const router = useRouter()

  const updateFile = ref<File | null>(null)
  const referenceFile = ref<File | null>(null)
  const previewing = ref(false)
  const savingAliases = ref(false)
  const executing = ref(false)
  const activeDetailTab = ref<'matched' | 'unmatched'>('matched')
  const previewData = ref<WeeklyPricePreviewResponse | null>(null)
  const downloadedFileName = ref('')
  const suggestionSelections = ref<Record<string, string>>({})
  const ignoredSuggestionSources = ref<string[]>([])

  const previewReady = computed(() => Boolean(previewData.value))
  const previewWarnings = computed(() => previewData.value?.warnings || [])
  const outputPath = computed(() => downloadedFileName.value)
  const displayState = computed<WeeklyPriceDisplayState>(() => {
    if (previewData.value) return previewData.value
    return {
      matched_count: 0,
      updated_count: 0,
      matched_items: [],
      not_matched: [],
      not_matched_count: 0,
      not_matched_unique_count: 0,
      alias_hit_count: 0,
    }
  })
  const changedCount = computed(() =>
    displayState.value.matched_items.filter((item) => item.changed).length,
  )
  const unchangedCount = computed(
    () => displayState.value.matched_items.length - changedCount.value,
  )
  const suggestedRows = computed(() => previewData.value?.suggested_matches || [])
  const ignoredSourceSet = computed(() => new Set(ignoredSuggestionSources.value))
  const actionableSuggestionRows = computed(() =>
    suggestedRows.value.filter(
      (item) => item.candidates.length > 0 && !ignoredSourceSet.value.has(item.source_name),
    ),
  )
  const noCandidateRows = computed(() =>
    suggestedRows.value.filter((item) => item.candidates.length === 0),
  )
  const selectedSuggestionCount = computed(() =>
    actionableSuggestionRows.value.filter(
      (item) => Boolean(suggestionSelections.value[item.source_name]),
    ).length,
  )
  const unresolvedSuggestionCount = computed(
    () => actionableSuggestionRows.value.length - selectedSuggestionCount.value,
  )
  const hasSavableMappings = computed(() =>
    actionableSuggestionRows.value.some((item) =>
      Boolean(suggestionSelections.value[item.source_name]),
    ),
  )
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
        suggestionText: hasCandidates
          ? suggestion!.candidates
              .map((candidate) => `${candidate.target_name} (${formatScore(candidate.score)})`)
              .join(' / ')
          : '暂无建议，请人工排查',
      }
    })
  })
  const previewStatusNote = computed(() => {
    if (previewReady.value) return '当前上传文件已经完成预检，可以继续执行更新。'
    return '请先上传待更新表和参考表，再运行预检。'
  })

  function resetAnalysis() {
    previewData.value = null
    downloadedFileName.value = ''
    suggestionSelections.value = {}
    ignoredSuggestionSources.value = []
    activeDetailTab.value = 'matched'
  }

  function setUpdateFile(files: FileList | File[] | null | undefined) {
    updateFile.value = files ? Array.from(files)[0] || null : null
    resetAnalysis()
  }

  function setReferenceFile(files: FileList | File[] | null | undefined) {
    referenceFile.value = files ? Array.from(files)[0] || null : null
    resetAnalysis()
  }

  function formatPrice(price: number | null) {
    if (price === null || Number.isNaN(price)) return '-'
    return `${price}`
  }

  function formatScore(score: number) {
    return `${Math.round(score * 100)}%`
  }

  function isIgnored(sourceName: string) {
    return ignoredSourceSet.value.has(sourceName)
  }

  function updateSuggestionSelection(sourceName: string, targetName: string | undefined) {
    const nextSelections = { ...suggestionSelections.value }
    if (!targetName) delete nextSelections[sourceName]
    else nextSelections[sourceName] = targetName
    suggestionSelections.value = nextSelections
  }

  function toggleIgnore(sourceName: string) {
    if (isIgnored(sourceName)) {
      ignoredSuggestionSources.value = ignoredSuggestionSources.value.filter(
        (item) => item !== sourceName,
      )
      return
    }

    ignoredSuggestionSources.value = [...ignoredSuggestionSources.value, sourceName]
  }

  function openAliasLibrary(sourceName: string = '') {
    router.push({
      path: '/weekly-price-aliases',
      query: sourceName ? { source: sourceName } : undefined,
    })
  }

  function validateSourceInputs() {
    if (!updateFile.value) {
      ElMessage.warning('请先上传待更新报价表')
      return false
    }

    if (!referenceFile.value) {
      ElMessage.warning('请先上传参考报价表')
      return false
    }

    return true
  }

  async function runPreview() {
    if (!validateSourceInputs()) return

    previewing.value = true
    clearStatus(statusLogRef)
    appendStatus(statusLogRef, '开始预检每周报价...', 'info')

    try {
      const { data } = await previewWeeklyPriceUpload({
        updateFile: updateFile.value!,
        referenceFile: referenceFile.value!,
      })

      previewData.value = data
      downloadedFileName.value = ''
      suggestionSelections.value = mergeSuggestionSelections(
        data.suggested_matches || [],
        suggestionSelections.value,
      )
      ignoredSuggestionSources.value = mergeIgnoredSuggestionSources(
        data.suggested_matches || [],
        ignoredSuggestionSources.value,
      )
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
        .filter(([, targetName]) => Boolean(targetName)),
    )

    if (!Object.keys(mappings).length) {
      ElMessage.warning('请至少选择一条映射再保存')
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
    if (!validateSourceInputs()) return
    if (!previewReady.value) {
      ElMessage.warning('请先完成一次有效预检')
      return
    }

    const pendingCount = unresolvedSuggestionCount.value
    const hardUnmatchedCount = noCandidateRows.value.length
    if (pendingCount || hardUnmatchedCount) {
      try {
        await ElMessageBox.confirm(
          `还有 ${pendingCount} 个候选未确认，${hardUnmatchedCount} 个菜名无候选。继续执行时，未匹配项不会写入结果文件。`,
          '继续执行更新？',
          {
            confirmButtonText: '继续执行',
            cancelButtonText: '先处理未匹配项',
            type: 'warning',
          },
        )
      } catch {
        return
      }
    }

    executing.value = true
    appendStatus(statusLogRef, '开始执行每周报价更新...', 'info')

    try {
      const payload = await executeWeeklyPriceUpload({
        updateFile: updateFile.value!,
        referenceFile: referenceFile.value!,
      })
      triggerDownload(payload)
      downloadedFileName.value = payload.filename
      appendStatus(
        statusLogRef,
        payload.message || `已下载更新后的报价文件: ${payload.filename}`,
        'success',
      )
    } catch (error: any) {
      appendStatus(statusLogRef, '执行失败：' + getApiErrorMessage(error), 'error')
      ElMessage.error('执行失败')
    } finally {
      executing.value = false
    }
  }

  function resetForm() {
    updateFile.value = null
    referenceFile.value = null
    resetAnalysis()
    clearStatus(statusLogRef)
  }

  return {
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
    previewStatusNote,
    previewWarnings,
    previewing,
    referenceFile,
    resetForm,
    runPreview,
    runUpdate,
    saveSelectedAliasesAndRepreview,
    savingAliases,
    selectedSuggestionCount,
    setReferenceFile,
    setUpdateFile,
    suggestionSelections,
    suggestedRows,
    toggleIgnore,
    unmatchedDetailRows,
    unresolvedSuggestionCount,
    unchangedCount,
    updateFile,
    updateSuggestionSelection,
  }
}
