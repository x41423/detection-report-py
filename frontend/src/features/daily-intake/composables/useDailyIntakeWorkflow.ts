import { computed, onMounted, reactive, ref, type Ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'

import {
  createDailyIntakeItem,
  deleteDailyIntakeItem,
  getConfig,
  getApiErrorMessage,
  getDailyIntakeByDate,
  getDailyIntakeHistory,
  getTodayDailyIntake,
  transcribeDailyIntakeAudio,
  updateConfig,
  updateDailyIntakeItem,
} from '../../../api'
import {
  appendStatus,
  type StatusLogHandle,
} from '../../shared/workflow'
import type {
  DailyIntakeAsrProviderSelection,
  DailyIntakeCategory,
  DailyIntakeItem,
  DailyIntakeMergePreview,
  DailyIntakeParseResponse,
  DailyIntakeSheet,
  DailyIntakeSheetSummary,
  DailyIntakeSource,
} from '../types'

interface EntryDraftState {
  name: string
  category: DailyIntakeCategory
  quantity: number | null
  recognizedName: string
  rememberCorrection: boolean
  unit: string
  source: DailyIntakeSource
  transcript: string
}

interface EditDraftState
  extends Omit<EntryDraftState, 'recognizedName' | 'rememberCorrection'> {
  id: number | null
}

function formatLocalDate(target: Date) {
  const year = target.getFullYear()
  const month = `${target.getMonth() + 1}`.padStart(2, '0')
  const day = `${target.getDate()}`.padStart(2, '0')
  return `${year}-${month}-${day}`
}

function createEntryDraft(): EntryDraftState {
  return {
    name: '',
    category: 'vegetable',
    quantity: null,
    recognizedName: '',
    rememberCorrection: false,
    unit: '斤',
    source: 'manual',
    transcript: '',
  }
}

export function useDailyIntakeWorkflow(
  statusLogRef: Ref<StatusLogHandle | undefined>,
) {
  const selectedDate = ref(formatLocalDate(new Date()))
  const sheet = ref<DailyIntakeSheet | null>(null)
  const history = ref<DailyIntakeSheetSummary[]>([])
  const loadingSheet = ref(false)
  const loadingHistory = ref(false)
  const submitting = ref(false)
  const parsingVoice = ref(false)
  const deletingId = ref<number | null>(null)
  const editDialogVisible = ref(false)
  const editSaving = ref(false)
  const parseWarnings = ref<string[]>([])
  const parseMessage = ref('')
  const mergePreview = ref<DailyIntakeMergePreview | null>(null)

  const entryDraft = reactive<EntryDraftState>(createEntryDraft())
  const editDraft = reactive<EditDraftState>({
    ...createEntryDraft(),
    id: null,
  })

  interface VoiceConfirmDraftState {
    name: string
    quantity: number | null
    unit: string
    category: DailyIntakeCategory
    rememberCorrection: boolean
    recognizedName: string
    transcript: string
    asrProvider: string | null
    asrDurationMs: number | null
    asrFallbackUsed: boolean
  }

  const voiceConfirmVisible = ref(false)
  const voiceConfirmSubmitting = ref(false)
  const voiceConfirmWarnings = ref<string[]>([])
  const voiceConfirmDraft = reactive<VoiceConfirmDraftState>({
    name: '',
    quantity: null,
    unit: '斤',
    category: 'vegetable',
    rememberCorrection: false,
    recognizedName: '',
    transcript: '',
    asrProvider: null,
    asrDurationMs: null,
    asrFallbackUsed: false,
  })

  const sheetItems = computed(() => sheet.value?.items || [])
  const totalQuantity = computed(() => sheet.value?.total_quantity || 0)
  const quantityByUnit = computed<Record<string, number>>(() => sheet.value?.quantity_by_unit || {})
  const categoryCounts = computed(() => {
    const counts: Record<DailyIntakeCategory, number> = {
      vegetable: 0,
      frozen: 0,
      meat: 0,
    }
    for (const item of sheetItems.value) {
      counts[item.category] += 1
    }
    return counts
  })

  const recentHistory = computed(() => history.value.filter((entry) => entry.intake_date !== selectedDate.value))

  function resetDraft(source: DailyIntakeSource = 'manual') {
    Object.assign(entryDraft, createEntryDraft(), {
      source,
      rememberCorrection: source === 'voice',
    })
    parseWarnings.value = []
    parseMessage.value = ''
    mergePreview.value = null
  }

  function normalizeDishName(name: string) {
    return String(name || '')
      .trim()
      .replace(/^[,，、。；;]+|[,，、。；;]+$/g, '')
      .replace(/\s+/g, '')
  }

  function mergeDishNameAliases(
    currentAliases: Record<string, string[]>,
    canonicalName: string,
    aliasName: string,
  ) {
    const normalizedCanonical = normalizeDishName(canonicalName)
    const normalizedAlias = normalizeDishName(aliasName)

    if (!normalizedCanonical || !normalizedAlias || normalizedCanonical === normalizedAlias) {
      return currentAliases
    }

    let canonicalDisplayName = canonicalName.trim()
    const mergedAliasDisplays = new Map<string, string>()
    const nextAliases: Record<string, string[]> = {}

    for (const [rawCanonical, rawAliasList] of Object.entries(currentAliases || {})) {
      const currentCanonical = rawCanonical.trim()
      const normalizedCurrentCanonical = normalizeDishName(currentCanonical)
      const cleanedAliases = Array.from(
        new Map(
          (rawAliasList || [])
            .map((alias) => String(alias || '').trim())
            .filter(Boolean)
            .map((alias) => [normalizeDishName(alias), alias] as const),
        ).values(),
      ).filter(Boolean)

      if (
        normalizedCurrentCanonical === normalizedCanonical ||
        normalizedCurrentCanonical === normalizedAlias
      ) {
        if (normalizedCurrentCanonical === normalizedCanonical) {
          canonicalDisplayName = currentCanonical
        }
        for (const alias of cleanedAliases) {
          const normalized = normalizeDishName(alias)
          if (normalized && normalized !== normalizedCanonical && normalized !== normalizedAlias) {
            mergedAliasDisplays.set(normalized, alias)
          }
        }
        continue
      }

      const filteredAliases = cleanedAliases.filter((alias) => {
        const normalized = normalizeDishName(alias)
        return normalized !== normalizedCanonical && normalized !== normalizedAlias
      })

      nextAliases[currentCanonical] = filteredAliases
    }

    mergedAliasDisplays.set(normalizedAlias, aliasName.trim())
    nextAliases[canonicalDisplayName] = Array.from(mergedAliasDisplays.values())

    return Object.fromEntries(
      Object.entries(nextAliases)
        .filter(([canonical]) => Boolean(canonical.trim()))
        .sort(([left], [right]) => left.localeCompare(right, 'zh-CN')),
    )
  }

  async function rememberVoiceCorrectionIfNeeded(
    recognizedName: string,
    correctedName: string,
    enabled: boolean,
  ) {
    if (!enabled) {
      return false
    }

    const normalizedRecognized = normalizeDishName(recognizedName)
    const normalizedCorrected = normalizeDishName(correctedName)
    if (!normalizedRecognized || !normalizedCorrected || normalizedRecognized === normalizedCorrected) {
      return false
    }

    const { data } = await getConfig()
    const currentAliases = ((data as { config?: { dish_name_aliases?: Record<string, string[]> } }).config?.dish_name_aliases ||
      {}) as Record<string, string[]>
    const nextAliases = mergeDishNameAliases(currentAliases, correctedName, recognizedName)
    await updateConfig({
      dish_name_aliases: nextAliases,
    })
    return true
  }

  async function loadTodaySheet() {
    loadingSheet.value = true
    try {
      const { data } = await getTodayDailyIntake()
      sheet.value = data.sheet
      selectedDate.value = data.sheet.intake_date
    } catch (error: unknown) {
      const detail = getApiErrorMessage(error, '加载今日点货单失败')
      appendStatus(statusLogRef, detail, 'error')
      ElMessage.error(detail)
    } finally {
      loadingSheet.value = false
    }
  }

  async function loadSheetByDate(intakeDate: string) {
    loadingSheet.value = true
    try {
      const { data } = await getDailyIntakeByDate(intakeDate)
      sheet.value = data.sheet
      selectedDate.value = data.sheet.intake_date
      appendStatus(statusLogRef, `已切换到 ${data.sheet.intake_date} 的点货单`, 'info')
    } catch (error: unknown) {
      const detail = getApiErrorMessage(error, '加载点货单失败')
      appendStatus(statusLogRef, detail, 'error')
      ElMessage.error(detail)
    } finally {
      loadingSheet.value = false
    }
  }

  async function loadHistory() {
    loadingHistory.value = true
    try {
      const { data } = await getDailyIntakeHistory()
      history.value = data.sheets
    } catch (error: unknown) {
      const detail = getApiErrorMessage(error, '加载历史点货单失败')
      appendStatus(statusLogRef, detail, 'error')
    } finally {
      loadingHistory.value = false
    }
  }

  async function submitDraft() {
    if (!entryDraft.name.trim()) {
      ElMessage.warning('请先填写商品名')
      return
    }
    if (entryDraft.quantity === null || Number(entryDraft.quantity) <= 0) {
      ElMessage.warning('请填写大于 0 的数量')
      return
    }

    submitting.value = true
    try {
      const recognizedName = entryDraft.recognizedName
      const shouldRememberCorrection = entryDraft.source === 'voice' && entryDraft.rememberCorrection
      const { data } = await createDailyIntakeItem({
        intake_date: selectedDate.value,
        name: entryDraft.name.trim(),
        category: entryDraft.category,
        quantity: Number(entryDraft.quantity),
        unit: entryDraft.unit,
        source: entryDraft.source,
        transcript: entryDraft.transcript,
      })
      try {
        const correctedName = data.item?.raw_name || entryDraft.name.trim()
        const remembered = await rememberVoiceCorrectionIfNeeded(
          recognizedName,
          correctedName,
          shouldRememberCorrection,
        )
        if (remembered) {
          appendStatus(
            statusLogRef,
            `已记住语音修正：以后将“${recognizedName}”按“${correctedName}”处理。`,
            'info',
          )
        }
      } catch (error: unknown) {
        const detail = getApiErrorMessage(error, '保存条目成功，但记住修正失败')
        appendStatus(statusLogRef, detail, 'info')
      }
      sheet.value = data.sheet
      await loadHistory()
      appendStatus(statusLogRef, data.message, data.merged ? 'info' : 'success')
      ElMessage.success(data.merged ? '已累计到现有条目' : '条目已新增')
      resetDraft()
    } catch (error: unknown) {
      const detail = getApiErrorMessage(error, '保存条目失败')
      appendStatus(statusLogRef, detail, 'error')
      ElMessage.error(detail)
    } finally {
      submitting.value = false
    }
  }

  async function parseVoiceAudio(
    audioClip: { blob: Blob; filename: string },
    options: { asrProvider?: DailyIntakeAsrProviderSelection; fallbackEnabled?: boolean } = {},
  ) {
    if (!audioClip.blob || audioClip.blob.size <= 0) {
      ElMessage.warning('未获取到录音文件')
      return
    }

    parsingVoice.value = true
    try {
      const { data } = await transcribeDailyIntakeAudio({
        intake_date: selectedDate.value,
        audio: audioClip.blob,
        filename: audioClip.filename,
        asr_provider: options.asrProvider || 'auto',
        fallback_enabled: options.fallbackEnabled,
      })
      appendStatus(statusLogRef, data.message, data.parse_status === 'parsed' ? 'success' : 'info')
      if (data.raw_transcript) {
        appendStatus(statusLogRef, `录音转写：${data.raw_transcript}`, 'info')
      }
      if (data.asr_provider) {
        const durationText = data.asr_duration_ms ? `，耗时 ${data.asr_duration_ms} ms` : ''
        appendStatus(statusLogRef, `实际使用模型：${data.asr_provider}${durationText}`, 'info')
      }
      if (data.asr_fallback_used && data.asr_fallback_reason) {
        appendStatus(statusLogRef, `已使用备用模型：${data.asr_fallback_reason}`, 'info')
      }
      if (data.parse_status === 'parsed') {
        openVoiceConfirmDialog(data)
      } else {
        applyParseResult(data)
        ElMessage.warning(data.message)
      }
    } catch (error: unknown) {
      const detail = getApiErrorMessage(error, '录音转写失败')
      appendStatus(statusLogRef, detail, 'error')
      ElMessage.error(detail)
    } finally {
      parsingVoice.value = false
    }
  }

  function applyParseResult(result: DailyIntakeParseResponse) {
    entryDraft.name = result.draft_name || entryDraft.name
    entryDraft.quantity = result.quantity
    entryDraft.recognizedName = result.draft_name || ''
    entryDraft.rememberCorrection = true
    entryDraft.unit = result.unit || entryDraft.unit
    entryDraft.category = result.category_hint || entryDraft.category
    entryDraft.source = 'voice'
    entryDraft.transcript = result.raw_transcript
    parseWarnings.value = Array.from(new Set([...(result.warnings || []), ...(result.asr_warnings || [])]))
    parseMessage.value = result.message
    mergePreview.value = result.merge_preview
  }

  function openVoiceConfirmDialog(result: DailyIntakeParseResponse) {
    voiceConfirmDraft.name = result.draft_name || ''
    voiceConfirmDraft.quantity = result.quantity
    voiceConfirmDraft.unit = result.unit || '斤'
    voiceConfirmDraft.category = result.category_hint || 'vegetable'
    voiceConfirmDraft.recognizedName = result.draft_name || ''
    voiceConfirmDraft.rememberCorrection = true
    voiceConfirmDraft.transcript = result.raw_transcript || ''
    voiceConfirmDraft.asrProvider = result.asr_provider || null
    voiceConfirmDraft.asrDurationMs = result.asr_duration_ms || null
    voiceConfirmDraft.asrFallbackUsed = result.asr_fallback_used || false
    voiceConfirmWarnings.value = Array.from(
      new Set([...(result.warnings || []), ...(result.asr_warnings || [])]),
    )
    voiceConfirmVisible.value = true
  }

  function closeVoiceConfirmDialog() {
    voiceConfirmVisible.value = false
  }

  async function submitVoiceConfirm() {
    if (!voiceConfirmDraft.name.trim()) {
      ElMessage.warning('请检查品名')
      return
    }
    if (voiceConfirmDraft.quantity === null || Number(voiceConfirmDraft.quantity) <= 0) {
      ElMessage.warning('请检查数量（须大于 0）')
      return
    }

    voiceConfirmSubmitting.value = true
    try {
      const recognizedName = voiceConfirmDraft.recognizedName
      const { data } = await createDailyIntakeItem({
        intake_date: selectedDate.value,
        name: voiceConfirmDraft.name.trim(),
        category: voiceConfirmDraft.category,
        quantity: Number(voiceConfirmDraft.quantity),
        unit: voiceConfirmDraft.unit,
        source: 'voice',
        transcript: voiceConfirmDraft.transcript,
      })
      try {
        const correctedName = data.item?.raw_name || voiceConfirmDraft.name.trim()
        const remembered = await rememberVoiceCorrectionIfNeeded(
          recognizedName,
          correctedName,
          voiceConfirmDraft.rememberCorrection,
        )
        if (remembered) {
          appendStatus(
            statusLogRef,
            `已记住语音修正：以后将"${recognizedName}"按"${correctedName}"处理。`,
            'info',
          )
        }
      } catch {
        // ignore correction save errors silently
      }
      sheet.value = data.sheet
      await loadHistory()
      appendStatus(statusLogRef, data.message, data.merged ? 'info' : 'success')
      ElMessage.success(data.merged ? '已累计到现有条目' : '语音条目已入库')
      voiceConfirmVisible.value = false
    } catch (error: unknown) {
      const detail = getApiErrorMessage(error, '保存条目失败')
      appendStatus(statusLogRef, detail, 'error')
      ElMessage.error(detail)
    } finally {
      voiceConfirmSubmitting.value = false
    }
  }

  function openEditDialog(item: DailyIntakeItem) {
    editDraft.id = item.id
    editDraft.name = item.raw_name
    editDraft.category = item.category
    editDraft.quantity = item.quantity
    editDraft.unit = item.unit_name
    editDraft.source = item.last_source
    editDraft.transcript = item.last_transcript
    editDialogVisible.value = true
  }

  async function saveEdit() {
    if (!editDraft.id) {
      return
    }
    if (!editDraft.name.trim()) {
      ElMessage.warning('请填写商品名')
      return
    }
    if (editDraft.quantity === null || Number(editDraft.quantity) <= 0) {
      ElMessage.warning('请填写大于 0 的数量')
      return
    }

    editSaving.value = true
    try {
      const { data } = await updateDailyIntakeItem(editDraft.id, {
        name: editDraft.name.trim(),
        category: editDraft.category,
        quantity: Number(editDraft.quantity),
        unit: editDraft.unit,
        source: editDraft.source,
        transcript: editDraft.transcript,
      })
      sheet.value = data.sheet
      await loadHistory()
      editDialogVisible.value = false
      appendStatus(statusLogRef, data.message, data.merged ? 'info' : 'success')
      ElMessage.success(data.merged ? '编辑后已并入现有条目' : '条目已更新')
    } catch (error: unknown) {
      const detail = getApiErrorMessage(error, '更新条目失败')
      appendStatus(statusLogRef, detail, 'error')
      ElMessage.error(detail)
    } finally {
      editSaving.value = false
    }
  }

  async function removeItem(item: DailyIntakeItem) {
    try {
      await ElMessageBox.confirm(
        `将删除“${item.raw_name} ${item.quantity} ${item.unit_name}”这条记录。`,
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

    deletingId.value = item.id
    try {
      const { data } = await deleteDailyIntakeItem(item.id)
      sheet.value = data.sheet
      await loadHistory()
      appendStatus(statusLogRef, data.message, 'success')
      ElMessage.success('条目已删除')
    } catch (error: unknown) {
      const detail = getApiErrorMessage(error, '删除条目失败')
      appendStatus(statusLogRef, detail, 'error')
      ElMessage.error(detail)
    } finally {
      deletingId.value = null
    }
  }

  async function refreshCurrentSheet() {
    await loadSheetByDate(selectedDate.value)
  }

  onMounted(async () => {
    await loadTodaySheet()
    await loadHistory()
  })

  return {
    categoryCounts,
    deletingId,
    editDialogVisible,
    editDraft,
    editSaving,
    entryDraft,
    history,
    loadingHistory,
    loadingSheet,
    mergePreview,
    parseMessage,
    parseWarnings,
    parsingVoice,
    recentHistory,
    resetDraft,
    loadHistory,
    loadSheetByDate,
    loadTodaySheet,
    openEditDialog,
    parseVoiceAudio,
    refreshCurrentSheet,
    removeItem,
    saveEdit,
    selectedDate,
    sheet,
    sheetItems,
    submitDraft,
    submitting,
    totalQuantity,
    quantityByUnit,
    voiceConfirmDraft,
    voiceConfirmSubmitting,
    voiceConfirmVisible,
    voiceConfirmWarnings,
    closeVoiceConfirmDialog,
    submitVoiceConfirm,
  }
}
