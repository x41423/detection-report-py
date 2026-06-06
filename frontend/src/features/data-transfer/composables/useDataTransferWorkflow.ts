import { computed, onMounted, ref, type Ref } from 'vue'
import { ElMessage } from 'element-plus'

import {
  dedupVegNames,
  executeMonthlyTransferUpload,
  executeTransferFromPaths,
  executeTransferUpload,
  extractVarietiesFromPaths,
  extractVarietiesFromUploads,
  findTransferFiles,
  getApiErrorMessage,
  getConfig,
  getTransferTemplates,
  logPathRestore,
  previewMonthlyTransferUpload,
  uploadTransferTemplateFile,
  type MonthlyTransferGroup,
  type TransferTemplateInfo,
} from '../../../api'
import { appendStatus, clearStatus, persistConfig, type StatusLogHandle } from '../../shared/workflow'
import { useDirBrowserApi } from '../../shared/dirBrowser'
import { triggerDownload } from '../../../utils/download'
import { getFileName, parseVegNames } from '../../../utils/veg'

export const SMALL_TYPES = ['滨鲜', '1号', '5号', '6号', '7号', '8号', '顾家'] as const
export type SmallType = (typeof SMALL_TYPES)[number]

interface TransferResultState {
  processed_files: number
  matched_count: number
  written_count: number
  output_file: string
}

export type TransferWorkflowMode = 'single' | 'monthly'

function todayMonth(): string {
  return new Date().toISOString().slice(0, 7)
}

export function useDataTransferWorkflow(
  statusLogRef: Ref<StatusLogHandle | undefined>,
) {
  const { openDirectory, openFile } = useDirBrowserApi()
  const smallTypes = SMALL_TYPES
  const workflowMode = ref<TransferWorkflowMode>('single')

  const usePathMode = ref(false)
  const bigDir = ref('')
  const foundBigFiles = ref<string[]>([])
  const selectedBigFilePaths = ref<Set<string>>(new Set())
  const templatePath = ref('')
  const findingFiles = ref(false)
  const findFilesMessage = ref('')
  const useSavedTemplate = ref(true)

  const bigTableFiles = ref<File[]>([])
  const bigTablePaths = ref<string[]>([])
  const smallTemplateFile = ref<File | null>(null)
  const smallType = ref<SmallType>(SMALL_TYPES[0])
  const vegText = ref('')
  const vegStatus = ref('')
  const varieties = ref<string[]>([])
  const aliasesMap = ref<Record<string, string[]>>({})
  const executing = ref(false)
  const lastResult = ref<TransferResultState>({
    processed_files: 0,
    matched_count: 0,
    written_count: 0,
    output_file: '',
  })

  // Monthly transfer state
  const monthlyTableFiles = ref<File[]>([])
  const monthlyTablePaths = ref<string[]>([])
  const monthlyMonth = ref(todayMonth())
  const monthlyPreviewing = ref(false)
  const monthlyExecuting = ref(false)
  const monthlyGroups = ref<MonthlyTransferGroup[]>([])
  const monthlyUnrecognizedFiles = ref<string[]>([])

  // Saved templates state
  const savedTemplates = ref<Record<string, TransferTemplateInfo>>({})
  const uploadingTemplate = ref(false)

  // Output directory state (path-locking only)
  const outputDir = ref('')

  const selectedVegNames = computed(() => parseVegNames(vegText.value))
  const matchedSet = computed(() => new Set(selectedVegNames.value.map((name) => name.toLowerCase())))
  const detectedFiles = computed(() => {
    if (usePathMode.value) {
      return selectedBigFileList.value
    }
    return bigTableFiles.value.map((file) => file.name)
  })
  const bigTableSummary = computed(() => {
    if (usePathMode.value) {
      return detectedFiles.value.join(' / ')
    }
    return detectedFiles.value.join(' / ')
  })
  const smallTemplateName = computed(() => smallTemplateFile.value?.name || '')

  const monthlyTableSummary = computed(() => monthlyTableFiles.value.map((file) => file.name).join(' / '))

  const currentSavedTemplate = computed<TransferTemplateInfo | null>(
    () => savedTemplates.value[smallType.value] || null,
  )
  const currentSavedTemplateReady = computed(
    () => Boolean(currentSavedTemplate.value && currentSavedTemplate.value.configured),
  )

  async function loadConfig() {
    try {
      const { data } = await getConfig()
      const cfg = data.config
      if (cfg.last_used_small_type && (SMALL_TYPES as readonly string[]).includes(cfg.last_used_small_type)) {
        smallType.value = cfg.last_used_small_type as SmallType
      }
      aliasesMap.value = cfg.dish_name_aliases || {}
      bigDir.value = cfg.transfer_big_dir || ''
      templatePath.value = cfg.transfer_template_path || ''
      outputDir.value = cfg.transfer_output_dir || ''
      if (bigDir.value) {
        const restored = restorePathLockState()
        if (restored) {
          logPathRestore(bigDir.value)
          appendStatus(statusLogRef, `已从缓存恢复 ${foundBigFiles.value.length} 个大表文件`, 'info')
        }
      }
    } catch (error: any) {
      appendStatus(statusLogRef, '加载配置失败：' + getApiErrorMessage(error), 'error')
    }
  }

  async function loadSavedTemplates() {
    try {
      const { data } = await getTransferTemplates()
      savedTemplates.value = data.templates || {}
    } catch (error: any) {
      appendStatus(statusLogRef, '加载小表模板失败：' + getApiErrorMessage(error), 'error')
    }
  }

  function setBigTableFiles(files: FileList | File[] | null | undefined) {
    bigTableFiles.value = files ? Array.from(files) : []
    varieties.value = []
    resetLastResult()
  }

  function setSmallTemplateFile(files: FileList | File[] | null | undefined) {
    const nextFile = files ? Array.from(files)[0] || null : null
    smallTemplateFile.value = nextFile
    resetLastResult()
  }

  function setMonthlyTableFiles(files: FileList | File[] | null | undefined) {
    monthlyTableFiles.value = files ? Array.from(files) : []
    monthlyGroups.value = []
    monthlyUnrecognizedFiles.value = []
  }

  async function onDetect() {
    if (!bigTableFiles.value.length) {
      ElMessage.warning('请先选择大表文件')
      return
    }

    try {
      const { data } = await extractVarietiesFromUploads(bigTableFiles.value)
      varieties.value = data.varieties
      appendStatus(statusLogRef, `已识别 ${data.count} 个品种`, 'success')
    } catch (error: any) {
      appendStatus(statusLogRef, '品种分析失败：' + getApiErrorMessage(error), 'error')
    }
  }

  async function onDedup() {
    if (!vegText.value.trim()) {
      return
    }

    try {
      const { data } = await dedupVegNames(selectedVegNames.value)
      vegText.value = data.deduplicated.join(', ')
      onVegInput()
      appendStatus(
        statusLogRef,
        data.removed_count > 0
          ? `已去除 ${data.removed_count} 个重复菜名`
          : '没有检测到重复菜名',
        data.removed_count > 0 ? 'success' : 'info',
      )
    } catch (error: any) {
      ElMessage.error('菜名去重失败：' + getApiErrorMessage(error))
    }
  }

  function onVegInput() {
    const count = selectedVegNames.value.length
    vegStatus.value = count > 0 ? `准备写入 ${count} 个菜名` : ''
  }

  function clearVegInput() {
    vegText.value = ''
    vegStatus.value = ''
  }

  function resetLastResult() {
    lastResult.value = {
      processed_files: 0,
      matched_count: 0,
      written_count: 0,
      output_file: '',
    }
  }

  function resetActionArea() {
    resetLastResult()
    monthlyGroups.value = []
    monthlyUnrecognizedFiles.value = []
    clearPathLockState()
    clearStatus(statusLogRef)
  }

  async function onExecute() {
    if (usePathMode.value) {
      await onExecutePathMode()
      return
    }

    if (!bigTableFiles.value.length) {
      ElMessage.warning('请先选择大表文件')
      return
    }
    if (!smallTemplateFile.value && !currentSavedTemplateReady.value) {
      ElMessage.warning('请选择小表模板或先上传一个保存模板')
      return
    }
    if (!selectedVegNames.value.length) {
      ElMessage.warning('请输入待写入的菜名')
      return
    }

    executing.value = true
    clearStatus(statusLogRef)
    appendStatus(statusLogRef, '开始执行数据迁移...', 'info')

    try {
      const payload = await executeTransferUpload({
        tableFiles: bigTableFiles.value,
        smallTemplate: smallTemplateFile.value,
        vegNames: selectedVegNames.value,
        smallType: smallType.value,
      })

      triggerDownload(payload)
      lastResult.value = {
        processed_files: payload.processedFiles || bigTableFiles.value.length,
        matched_count: payload.matchedCount || 0,
        written_count: payload.writtenCount || 0,
        output_file: payload.filename,
      }

      appendStatus(
        statusLogRef,
        payload.message || `迁移完成，输出文件：${payload.filename}`,
        'success',
      )
    } catch (error: any) {
      appendStatus(statusLogRef, '执行失败：' + getApiErrorMessage(error), 'error')
    } finally {
      executing.value = false
    }
  }

  async function onSmallTypeChange(value: SmallType) {
    smallType.value = value
    await persistConfig({ last_used_small_type: value })
  }

  async function uploadTransferTemplate(files: FileList | File[] | null | undefined) {
    const file = files ? Array.from(files)[0] : null
    if (!file) return
    uploadingTemplate.value = true
    try {
      const { data } = await uploadTransferTemplateFile(smallType.value, file)
      savedTemplates.value = data.templates || {}
      appendStatus(statusLogRef, `已保存「${smallType.value}」小表模板`, 'success')
    } catch (error: any) {
      appendStatus(statusLogRef, '保存小表模板失败：' + getApiErrorMessage(error), 'error')
    } finally {
      uploadingTemplate.value = false
    }
  }

  async function onPreviewMonthlyTransfer() {
    if (!monthlyTableFiles.value.length) {
      ElMessage.warning('请先选择月度大表文件')
      return
    }
    monthlyPreviewing.value = true
    appendStatus(statusLogRef, '开始预览月度数据分组...', 'info')
    try {
      const { data } = await previewMonthlyTransferUpload({
        files: monthlyTableFiles.value,
        month: monthlyMonth.value,
      })
      monthlyGroups.value = data.groups || []
      monthlyUnrecognizedFiles.value = data.unrecognized_files || []
      appendStatus(
        statusLogRef,
        data.message || `预览完成：${data.groups.length} 个日期分组`,
        'success',
      )
    } catch (error: any) {
      appendStatus(statusLogRef, '预览失败：' + getApiErrorMessage(error), 'error')
    } finally {
      monthlyPreviewing.value = false
    }
  }

  async function onExecuteMonthlyTransfer() {
    if (!monthlyTableFiles.value.length) {
      ElMessage.warning('请先选择月度大表文件')
      return
    }
    if (!smallTemplateFile.value && !currentSavedTemplateReady.value) {
      ElMessage.warning('请选择小表模板或先上传保存模板')
      return
    }

    monthlyExecuting.value = true
    appendStatus(statusLogRef, `开始执行 ${monthlyMonth.value} 月度数据迁移...`, 'info')
    try {
      const payload = await executeMonthlyTransferUpload({
        files: monthlyTableFiles.value,
        month: monthlyMonth.value,
        smallType: smallType.value,
        smallTemplate: smallTemplateFile.value,
      })
      triggerDownload(payload)
      appendStatus(
        statusLogRef,
        payload.message || `月度迁移完成：${payload.filename}`,
        'success',
      )
    } catch (error: any) {
      appendStatus(statusLogRef, '月度迁移失败：' + getApiErrorMessage(error), 'error')
    } finally {
      monthlyExecuting.value = false
    }
  }

  // --- Path-locking mode functions ---

  function onSwitchMode(pathMode: boolean) {
    usePathMode.value = pathMode
    foundBigFiles.value = []
    selectedBigFilePaths.value = new Set()
    findFilesMessage.value = ''
    varieties.value = []
    vegText.value = ''
    vegStatus.value = ''
    clearPathLockState()
    resetLastResult()
  }

  async function onBrowseBigDir() {
    const selected = await openDirectory('transfer:big-dir', bigDir.value, {
      title: '选择大表文件所在目录',
    })
    if (selected) {
      bigDir.value = selected
      foundBigFiles.value = []
      selectedBigFilePaths.value = new Set()
      findFilesMessage.value = ''
      varieties.value = []
      vegText.value = ''
      vegStatus.value = ''
      clearPathLockState()
      persistConfig({ transfer_big_dir: bigDir.value })
    }
  }

  async function onFindTransferFiles() {
    if (!bigDir.value) {
      ElMessage.warning('请先浏览选择大表目录')
      return
    }
    findingFiles.value = true
    try {
      const { data } = await findTransferFiles(bigDir.value)
      foundBigFiles.value = data.files
      selectedBigFilePaths.value = new Set()
      findFilesMessage.value = `发现 ${data.files.length} 个大表文件`
      vegText.value = ''
      vegStatus.value = ''
      if (data.files.length > 0) savePathLockState()
      appendStatus(statusLogRef, findFilesMessage.value, 'success')
      ElMessage.success(findFilesMessage.value)
    } catch (error: any) {
      findFilesMessage.value = '查找失败: ' + getApiErrorMessage(error)
      appendStatus(statusLogRef, findFilesMessage.value, 'error')
      ElMessage.error('查找失败')
    } finally {
      findingFiles.value = false
    }
  }

  function toggleBigFileSelection(filePath: string) {
    const next = new Set(selectedBigFilePaths.value)
    if (next.has(filePath)) {
      next.delete(filePath)
    } else {
      next.add(filePath)
    }
    selectedBigFilePaths.value = next
    savePathLockState()
  }

  const selectedBigFileList = computed(() => [...selectedBigFilePaths.value])

  const allSelected = computed(() =>
    foundBigFiles.value.length > 0 &&
    selectedBigFilePaths.value.size === foundBigFiles.value.length
  )

  function toggleSelectAll() {
    if (allSelected.value) {
      selectedBigFilePaths.value = new Set()
    } else {
      selectedBigFilePaths.value = new Set(
        foundBigFiles.value.map((f) => bigDir.value + '/' + f)
      )
    }
    savePathLockState()
  }

  async function onAnalyzePathVarieties() {
    const paths = selectedBigFileList.value
    if (!paths.length) {
      ElMessage.warning('请先选择大表文件')
      return
    }
    try {
      const { data } = await extractVarietiesFromPaths(paths)
      varieties.value = data.varieties
      appendStatus(statusLogRef, `已识别 ${data.count} 个品种`, 'success')
    } catch (error: any) {
      appendStatus(statusLogRef, '品种分析失败：' + getApiErrorMessage(error), 'error')
    }
  }

  async function onBrowseTemplatePath() {
    const selected = await openFile('transfer:template-path', templatePath.value, {
      title: '选择小表模板文件',
      extensions: ['.docx'],
    })
    if (selected) {
      templatePath.value = selected
      useSavedTemplate.value = false
      persistConfig({ transfer_template_path: templatePath.value })
    }
  }

  function onUseSavedTemplate(useSaved: boolean = true) {
    useSavedTemplate.value = useSaved
    if (useSaved) {
      templatePath.value = ''
    }
  }

  async function onBrowseOutputDir() {
    const selected = await openDirectory('transfer:output', outputDir.value, {
      title: '选择输出目录',
    })
    if (selected) {
      outputDir.value = selected
      persistConfig({ transfer_output_dir: outputDir.value })
    }
  }

  async function onBrowseBigTableFiles() {
    const selected = await openFile('transfer:big-tables', '', {
      title: '选择大表文件',
      extensions: ['.doc', '.docx'],
    })
    if (selected) {
      bigTablePaths.value = [...(bigTablePaths.value || []), selected]
    }
  }

  async function onBrowseTemplateFile() {
    const selected = await openFile('transfer:template', templatePath.value, {
      title: '选择小表模板文件',
      extensions: ['.doc', '.docx'],
    })
    if (selected) {
      templatePath.value = selected
    }
  }

  async function onBrowseMonthlyTableFiles() {
    const selected = await openFile('transfer:monthly-tables', '', {
      title: '选择当月大表文件',
      extensions: ['.doc', '.docx'],
    })
    if (selected) {
      monthlyTablePaths.value = [...(monthlyTablePaths.value || []), selected]
    }
  }

  async function onBrowseSavedTemplateFile() {
    const selected = await openFile('transfer:saved-template', '', {
      title: '选择要保存的模板文件',
      extensions: ['.doc', '.docx'],
    })
    if (selected) {
      await uploadTransferTemplateFromPath(smallType.value, selected)
    }
  }

  // --- Path-lock state persistence (localStorage) ---

  const PATH_LOCK_STORAGE_KEY = 'transfer_path_lock_state'

  function savePathLockState() {
    const data = {
      bigDir: bigDir.value,
      foundFiles: foundBigFiles.value,
      selectedFileNames: selectedBigFileList.value.map((p) => getFileName(p)),
    }
    try {
      localStorage.setItem(PATH_LOCK_STORAGE_KEY, JSON.stringify(data))
    } catch { /* ignore quota errors */ }
  }

  function restorePathLockState() {
    try {
      const raw = localStorage.getItem(PATH_LOCK_STORAGE_KEY)
      if (!raw) return false
      const data = JSON.parse(raw)
      if (data.bigDir !== bigDir.value || !data.foundFiles?.length) return false
      foundBigFiles.value = data.foundFiles
      const selectedNames = new Set<string>(data.selectedFileNames || [])
      selectedBigFilePaths.value = new Set(
        data.foundFiles
          .filter((fn: string) => selectedNames.has(fn))
          .map((fn: string) => bigDir.value + '/' + fn),
      )
      return true
    } catch {
      return false
    }
  }

  function clearPathLockState() {
    try {
      localStorage.removeItem(PATH_LOCK_STORAGE_KEY)
    } catch { /* ignore */ }
  }

  async function onExecutePathMode() {
    const paths = selectedBigFileList.value
    if (!paths.length) {
      ElMessage.warning('请先选择大表文件')
      return
    }
    if (!selectedVegNames.value.length) {
      ElMessage.warning('请输入待写入的菜名')
      return
    }

    const template = useSavedTemplate.value
      ? currentSavedTemplate.value?.path
      : templatePath.value
    if (!template) {
      ElMessage.warning('请选择小表模板或先上传一个保存模板')
      return
    }

    const hasOutputDir = Boolean(outputDir.value)

    executing.value = true
    clearStatus(statusLogRef)
    appendStatus(statusLogRef, '开始执行数据迁移（路径模式）...', 'info')

    try {
      const payload = await executeTransferFromPaths({
        tablePaths: paths,
        smallTemplatePath: template,
        vegNames: selectedVegNames.value,
        smallType: smallType.value,
        outputDir: hasOutputDir ? outputDir.value : undefined,
      })

      if (hasOutputDir) {
        vegText.value = ''
        vegStatus.value = ''
        appendStatus(
          statusLogRef,
          payload.message || `迁移完成，已保存到：${outputDir.value}`,
          'success',
        )
        ElMessage.success(payload.message || '数据迁移已完成')
      } else {
        vegText.value = ''
        vegStatus.value = ''
        triggerDownload(payload)
        lastResult.value = {
          processed_files: payload.processedFiles || paths.length,
          matched_count: payload.matchedCount || 0,
          written_count: payload.writtenCount || 0,
          output_file: payload.filename,
        }
        appendStatus(
          statusLogRef,
          payload.message || `迁移完成，输出文件：${payload.filename}`,
          'success',
        )
      }
    } catch (error: any) {
      appendStatus(statusLogRef, '执行失败：' + getApiErrorMessage(error), 'error')
    } finally {
      executing.value = false
    }
  }

  onMounted(() => {
    void loadConfig()
    void loadSavedTemplates()
  })

  return {
    aliasesMap,
    allSelected,
    bigDir,
    bigTableSummary,
    bigTablePaths,
    clearVegInput,
    currentSavedTemplate,
    currentSavedTemplateReady,
    detectedFiles,
    executing,
    findFilesMessage,
    findingFiles,
    foundBigFiles,
    getFileName,
    lastResult,
    matchedSet,
    monthlyExecuting,
    monthlyGroups,
    monthlyMonth,
    monthlyPreviewing,
    monthlyTableFiles,
    monthlyTablePaths,
    monthlyTableSummary,
    monthlyUnrecognizedFiles,
    onAnalyzePathVarieties,
    onBrowseBigDir,
    onBrowseBigTableFiles,
    onBrowseMonthlyTableFiles,
    onBrowseOutputDir,
    onBrowseSavedTemplateFile,
    onBrowseTemplateFile,
    onBrowseTemplatePath,
    onDedup,
    onDetect,
    onExecute,
    onExecuteMonthlyTransfer,
    onFindTransferFiles,
    onPreviewMonthlyTransfer,
    onSmallTypeChange,
    onSwitchMode,
    onUseSavedTemplate,
    onVegInput,
    outputDir,
    resetActionArea,
    savedTemplates,
    selectedBigFileList,
    selectedBigFilePaths,
    selectedVegNames,
    setBigTableFiles,
    setMonthlyTableFiles,
    setSmallTemplateFile,
    smallTemplateName,
    smallType,
    smallTypes,
    templatePath,
    toggleBigFileSelection,
    toggleSelectAll,
    uploadTransferTemplate,
    uploadingTemplate,
    usePathMode,
    useSavedTemplate,
    varieties,
    vegStatus,
    vegText,
    workflowMode,
  }
}
