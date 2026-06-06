import { computed, onMounted, ref, watch, type Ref } from 'vue'
import { ElMessage } from 'element-plus'

import {
  dedupJson,
  executePesticideMonthly,
  executePesticideMonthlyWithPaths,
  executePesticideTask,
  executePesticideTaskUpload,
  findFiles,
  formatJson,
  generateRates,
  getApiErrorMessage,
  getConfig,
  getPesticideTemplates,
  openLocalFile,
  parsePesticideMonthlyList,
  parsePesticideMonthlyListFromPath,
  savePesticideTemplateFromPath,
  uploadPesticideTemplate,
  type MonthlyListEntry,
  type MonthlyListParseError,
  type PesticideTemplateStatusResponse,
} from '../../../api'
import { triggerDownload } from '../../../utils/download'
import { getFileName, parseVegNames } from '../../../utils/veg'
import {
  appendStatus,
  clearStatus,
  persistConfig,
  type StatusLogHandle,
} from '../../shared/workflow'
import { useDirBrowserApi } from '../../shared/dirBrowser'

export function usePesticideWorkflow(
  statusLogRef: Ref<StatusLogHandle | undefined>,
) {
  const { openDirectory, openFile } = useDirBrowserApi()
  const bigFile = ref<File | null>(null)
  const smallFile = ref<File | null>(null)
  const detectDate = ref('')
  const inspectorName = ref('')
  const vegText = ref('')
  const vegStatus = ref('')
  const jsonText = ref('')
  const jsonStatus = ref('')
  const dataCount = ref(0)
  const executing = ref(false)
  const lastRunMessage = ref('')

  const usePathMode = ref(false)
  const bigPath = ref('')
  const smallPath = ref('')
  const pathLocked = ref(false)
  const foundFileBig = ref('')
  const foundFileSmall = ref('')
  const findingFiles = ref(false)
  const findFilesMessage = ref('')

  const outputDir = ref('')
  const monthlyOutputDir = ref('')

  const templateStatus = ref<PesticideTemplateStatusResponse | null>(null)
  const templateLoading = ref(false)
  const pendingTemplatePath = ref<{ big: string; small: string }>({ big: '', small: '' })
  const savingTemplate = ref('')

  const month = ref('')
  const monthListText = ref('')
  const monthListFile = ref<File | null>(null)
  const monthListPath = ref('')
  const monthEntries = ref<MonthlyListEntry[]>([])
  const monthSelectedDates = ref<Set<string>>(new Set())
  const monthParsing = ref(false)
  const monthListErrors = ref<MonthlyListParseError[]>([])
  const monthExecuting = ref(false)
  const monthResult = ref('')
  const monthUseSavedTemplates = ref(true)
  const monthBigTemplateFile = ref<File | null>(null)
  const monthSmallTemplateFile = ref<File | null>(null)

  const activeTab = ref<'single' | 'monthly-upload'>('single')
  const monthlyTemplateMode = ref<'upload' | 'path'>('upload')
  const monthlyBigPath = ref('')
  const monthlySmallPath = ref('')
  const monthlyPathLocked = ref(false)
  const monthlyFoundBig = ref('')
  const monthlyFoundSmall = ref('')
  const monthlyFindingFiles = ref(false)
  const monthlyFindFilesMessage = ref('')

  const fileInfo = computed(() => {
    if (usePathMode.value) {
      return {
        big_file: foundFileBig.value || bigPath.value || '',
        small_file: foundFileSmall.value || smallPath.value || '',
        big_exists: pathLocked.value || Boolean(foundFileBig.value),
        small_exists: pathLocked.value || Boolean(foundFileSmall.value),
      }
    }
    return {
      big_file: bigFile.value?.name || '',
      small_file: smallFile.value?.name || '',
      big_exists: Boolean(bigFile.value),
      small_exists: Boolean(smallFile.value),
    }
  })

  const fileReadyCount = computed(
    () => {
      if (usePathMode.value) {
        return Number(pathLocked.value) * 2
      }
      return Number(fileInfo.value.big_exists) + Number(fileInfo.value.small_exists)
    },
  )
  const formatHeroDate = computed(() => detectDate.value || '未设置')

  function parseDateParts() {
    if (!detectDate.value) {
      return null
    }
    const parts = detectDate.value.split('-')
    return parts.length === 3
      ? { year: parts[0], month: parts[1], day: parts[2] }
      : null
  }

  function formatDateLabel() {
    const parts = parseDateParts()
    if (!parts) {
      return ''
    }
    return `${parts.year}年${parseInt(parts.month, 10)}月${parseInt(parts.day, 10)}日`
  }

  async function loadConfig() {
    try {
      const { data } = await getConfig()
      const cfg = data.config
      inspectorName.value = cfg.inspector_name || ''
      detectDate.value = cfg.pesticide_last_date || new Date().toISOString().slice(0, 10)
      bigPath.value = cfg.big_path || ''
      smallPath.value = cfg.small_path || ''
      outputDir.value = cfg.pesticide_output_dir || ''
      monthlyOutputDir.value = cfg.pesticide_output_dir || ''
      monthListPath.value = cfg.month_list_path || ''
    } catch (error: any) {
      appendStatus(statusLogRef, '加载配置失败: ' + getApiErrorMessage(error), 'error')
    }
  }

  function setFile(type: 'big' | 'small', files: FileList | File[] | null | undefined) {
    const nextFile = files ? Array.from(files)[0] || null : null
    if (type === 'big') {
      bigFile.value = nextFile
    } else {
      smallFile.value = nextFile
    }
    lastRunMessage.value = ''
  }

  function onVegInput() {
    const count = parseVegNames(vegText.value).length
    vegStatus.value = count > 0 ? `有效品种 ${count} 个` : ''
  }

  function onJsonInput() {
    try {
      const parsed = JSON.parse(jsonText.value.trim() || '[]')
      if (Array.isArray(parsed)) {
        dataCount.value = parsed.length
        jsonStatus.value = `JSON 有效，共 ${parsed.length} 条记录`
      } else {
        jsonStatus.value = 'JSON 必须是数组结构'
      }
    } catch {
      jsonStatus.value = jsonText.value.trim() ? 'JSON 格式错误' : ''
      dataCount.value = 0
    }
  }

  function onSwitchMode(pathMode: boolean) {
    usePathMode.value = pathMode
    pathLocked.value = false
    foundFileBig.value = ''
    foundFileSmall.value = ''
    findFilesMessage.value = ''
    lastRunMessage.value = ''
  }

  async function onFindFiles() {
    if (!bigPath.value || !smallPath.value) {
      ElMessage.warning('请先浏览并锁定大表和小表目录')
      return
    }
    const parts = parseDateParts()
    if (!parts) {
      ElMessage.warning('请先选择检测日期')
      return
    }

    findingFiles.value = true
    clearStatus(statusLogRef)
    try {
      const { data } = await findFiles(bigPath.value, smallPath.value, parts.year, parts.month, parts.day)
      foundFileBig.value = data.big_file
      foundFileSmall.value = data.small_file
      pathLocked.value = Boolean(data.big_exists && data.small_exists)

      if (pathLocked.value) {
        findFilesMessage.value = '路径锁定成功：已找到大小表文件'
        appendStatus(statusLogRef, `大表: ${data.big_file}`, 'success')
        appendStatus(statusLogRef, `小表: ${data.small_file}`, 'success')
        ElMessage.success('路径锁定成功')
      } else {
        const missing: string[] = []
        if (!data.big_exists) missing.push('大表')
        if (!data.small_exists) missing.push('小表')
        findFilesMessage.value = `未找到: ${missing.join('、')}`
        appendStatus(statusLogRef, findFilesMessage.value, 'error')
        ElMessage.error(findFilesMessage.value)
      }
    } catch (error: any) {
      findFilesMessage.value = '查找失败: ' + getApiErrorMessage(error)
      pathLocked.value = false
      appendStatus(statusLogRef, findFilesMessage.value, 'error')
      ElMessage.error('查找失败')
    } finally {
      findingFiles.value = false
    }
  }

  async function onBrowsePath(kind: 'big' | 'small') {
    const initialPath = kind === 'big' ? bigPath.value : smallPath.value
    const selected = await openDirectory(`pest:single:${kind}-dir`, initialPath, {
      title: `选择${kind === 'big' ? '大表' : '小表'}目录`,
    })
    if (selected) {
      if (kind === 'big') {
        bigPath.value = selected
      } else {
        smallPath.value = selected
      }
      pathLocked.value = false
      foundFileBig.value = ''
      foundFileSmall.value = ''
      findFilesMessage.value = ''
      persistConfig({ big_path: bigPath.value, small_path: smallPath.value })
    }
  }

  async function onBrowseOutputDir() {
    const selected = await openDirectory('pest:output', outputDir.value, {
      title: '选择输出目录',
    })
    if (selected) {
      outputDir.value = selected
      monthlyOutputDir.value = selected
      persistConfig({ pesticide_output_dir: outputDir.value })
    }
  }

  async function onMonthlyBrowsePath(kind: 'big' | 'small') {
    const initialPath = kind === 'big' ? monthlyBigPath.value : monthlySmallPath.value
    const selected = await openFile(`pest:monthly:${kind}-template`, initialPath, {
      title: `选择月度${kind === 'big' ? '大表模板' : '小表模板'}文件`,
      extensions: ['.docx'],
    })
    if (selected) {
      if (kind === 'big') {
        monthlyBigPath.value = selected
      } else {
        monthlySmallPath.value = selected
      }
      monthlyPathLocked.value = false
      monthlyFoundBig.value = ''
      monthlyFoundSmall.value = ''
      monthlyFindFilesMessage.value = ''
    }
  }

  async function onMonthlyFindFiles() {
    if (!monthlyBigPath.value || !monthlySmallPath.value) {
      ElMessage.warning('请先浏览并选择大表和小表模板文件')
      return
    }

    monthlyFindingFiles.value = true

    try {
      monthlyFoundBig.value = monthlyBigPath.value
      monthlyFoundSmall.value = monthlySmallPath.value
      monthlyPathLocked.value = true
      monthlyFindFilesMessage.value = '模板路径已锁定'
      appendStatus(statusLogRef, `大表模板: ${monthlyBigPath.value}`, 'success')
      appendStatus(statusLogRef, `小表模板: ${monthlySmallPath.value}`, 'success')
      ElMessage.success('模板路径已锁定')
    } catch (error: any) {
      monthlyFindFilesMessage.value = '锁定失败: ' + getApiErrorMessage(error)
      monthlyPathLocked.value = false
      appendStatus(statusLogRef, monthlyFindFilesMessage.value, 'error')
      ElMessage.error('锁定失败')
    } finally {
      monthlyFindingFiles.value = false
    }
  }

  async function onGenerateRates() {
    if (!vegText.value.trim()) {
      ElMessage.warning('请先输入蔬菜品种')
      return
    }

    try {
      const { data } = await generateRates(vegText.value)
      jsonText.value = JSON.stringify(data.data, null, 2)
      dataCount.value = data.count
      jsonStatus.value = `已生成 ${data.count} 条记录`
      appendStatus(statusLogRef, `已生成 ${data.count} 条抑制率记录`, 'success')
    } catch (error: any) {
      ElMessage.error('生成失败: ' + getApiErrorMessage(error))
    }
  }

  async function onDedupJson() {
    if (!jsonText.value.trim()) {
      return
    }

    try {
      const { data } = await dedupJson(jsonText.value)
      jsonText.value = JSON.stringify(data.data, null, 2)
      dataCount.value = data.data.length
      appendStatus(
        statusLogRef,
        data.removed_count > 0 ? `已删除 ${data.removed_count} 条重复记录` : '没有检测到重复记录',
        data.removed_count > 0 ? 'success' : 'info',
      )
      onJsonInput()
    } catch (error: any) {
      ElMessage.error('JSON 去重失败: ' + getApiErrorMessage(error))
    }
  }

  async function onFormatJson() {
    if (!jsonText.value.trim()) {
      return
    }

    try {
      const { data } = await formatJson(jsonText.value)
      jsonText.value = data.json_text
      onJsonInput()
    } catch (error: any) {
      ElMessage.error('格式化失败: ' + getApiErrorMessage(error))
    }
  }

  async function onLoadTemplates() {
    templateLoading.value = true
    try {
      const { data } = await getPesticideTemplates()
      templateStatus.value = data
    } catch {
      // 静默失败，模板功能为可选
    } finally {
      templateLoading.value = false
    }
  }

  async function onUploadTemplate(kind: 'big' | 'small', file: File) {
    try {
      const { data } = await uploadPesticideTemplate(kind, file)
      templateStatus.value = data
      const label = kind === 'big' ? '大表' : '小表'
      appendStatus(statusLogRef, `${label}模板已更新: ${data[kind === 'big' ? 'big_template' : 'small_template'].filename}`, 'success')
      ElMessage.success(`${label}模板已保存`)
    } catch (error: any) {
      ElMessage.error('模板上传失败: ' + getApiErrorMessage(error))
    }
  }

  async function onBrowseTemplate(kind: 'big' | 'small') {
    const selected = await openFile(`pest:monthly:${kind}-upload`, pendingTemplatePath.value[kind], {
      title: `选择${kind === 'big' ? '大表' : '小表'}模板文件`,
      extensions: ['.docx'],
    })
    if (selected) {
      pendingTemplatePath.value[kind] = selected
    }
  }

  async function onSaveTemplatePath(kind: 'big' | 'small') {
    savingTemplate.value = kind
    try {
      const { data } = await savePesticideTemplateFromPath(kind, pendingTemplatePath.value[kind])
      templateStatus.value = data
      const label = kind === 'big' ? '大表' : '小表'
      appendStatus(statusLogRef, `${label}模板已更新: ${pendingTemplatePath.value[kind]}`, 'success')
      ElMessage.success(`${label}模板已保存`)
      pendingTemplatePath.value[kind] = ''
    } catch (error: any) {
      ElMessage.error('模板保存失败: ' + getApiErrorMessage(error))
    } finally {
      savingTemplate.value = ''
    }
  }

  async function onBrowseMonthListFile() {
    const selected = await openFile('pest:monthly:list', monthListPath.value, {
      title: '选择月度清单文件',
      extensions: ['.xlsx', '.xls', '.txt'],
    })
    if (selected) {
      monthListPath.value = selected
    }
  }

  async function onConfirmMonthListPath() {
    if (!monthListPath.value) {
      ElMessage.warning('请先浏览选择清单文件')
      return
    }
    try {
      await persistConfig({ month_list_path: monthListPath.value })
      ElMessage.success('清单路径已保存')
    } catch {
      ElMessage.error('保存失败')
    }
  }

  async function onOpenMonthListFile() {
    if (!monthListPath.value) {
      ElMessage.warning('请先浏览选择清单文件')
      return
    }
    try {
      await openLocalFile(monthListPath.value)
      ElMessage.success('已打开清单文件')
    } catch (error: any) {
      ElMessage.error('打开失败: ' + getApiErrorMessage(error))
    }
  }

  function onClearVeg() {
    vegText.value = ''
    vegStatus.value = ''
  }

  function onClearJson() {
    jsonText.value = ''
    jsonStatus.value = ''
    dataCount.value = 0
  }

  function onReset() {
    onClearVeg()
    onClearJson()
    lastRunMessage.value = ''
    clearStatus(statusLogRef)
  }

  function onSetTab(tab: 'single' | 'monthly-upload') {
    activeTab.value = tab
    monthEntries.value = []
    monthExecuting.value = false
    monthResult.value = ''
    monthListErrors.value = []
    monthListText.value = ''
    monthListFile.value = null
    monthParsing.value = false
  }

  async function onExecute() {
    if (usePathMode.value) {
      if (!pathLocked.value) {
        ElMessage.warning('请先通过路径锁定找到目标文件')
        return
      }
    } else {
      if (!bigFile.value || !smallFile.value) {
        ElMessage.warning('请先上传大表和小表模板')
        return
      }
    }
    if (!jsonText.value.trim()) {
      ElMessage.warning('JSON 数据为空')
      return
    }

    executing.value = true
    clearStatus(statusLogRef)
    appendStatus(statusLogRef, '开始生成农残检测报告...', 'info')

    try {
      await persistConfig({
        inspector_name: inspectorName.value,
        pesticide_last_date: detectDate.value,
      })

      if (usePathMode.value) {
        const effectiveOutputDir = outputDir.value || bigPath.value
        const { data } = await executePesticideTask({
          big_path: foundFileBig.value || bigPath.value,
          small_path: foundFileSmall.value || smallPath.value,
          json_text: jsonText.value,
          date_label: formatDateLabel(),
          output_dir: effectiveOutputDir,
          inspector_name: inspectorName.value,
        })
        lastRunMessage.value = data.message
        appendStatus(statusLogRef, data.message, 'success')
        appendStatus(statusLogRef, `输出目录: ${data.output_dir}`, 'info')
      } else {
        const payload = await executePesticideTaskUpload({
          bigFile: bigFile.value!,
          smallFile: smallFile.value!,
          jsonText: jsonText.value,
          dateLabel: formatDateLabel(),
          inspectorName: inspectorName.value,
        })

        triggerDownload(payload)
        lastRunMessage.value = payload.message || `已下载 ${payload.filename}`
        appendStatus(statusLogRef, lastRunMessage.value, 'success')
      }
    } catch (error: any) {
      const detail = getApiErrorMessage(error)
      appendStatus(statusLogRef, '执行失败: ' + detail, 'error')
    } finally {
      executing.value = false
    }
  }

  async function onParseMonthlyList() {
    if (!monthListText.value.trim() && !monthListPath.value) {
      ElMessage.warning('请输入清单文本或浏览选择清单文件')
      return
    }

    monthParsing.value = true
    try {
      const { data } = await parsePesticideMonthlyListFromPath({
        month: month.value,
        listText: monthListText.value,
        filePath: monthListPath.value,
      })
      monthEntries.value = data.entries
      monthListErrors.value = data.errors
      // 默认全选所有日期
      monthSelectedDates.value = new Set(data.entries.map(e => e.date))

      if (data.detected_month) {
        month.value = data.detected_month
      }

      const msg = `解析完成：${data.total_dates} 天，${data.total_names} 个品种`
      appendStatus(statusLogRef, msg, data.errors.length ? 'error' : 'success')
      if (data.errors.length > 0) {
        ElMessage.warning(`${msg}，${data.errors.length} 行有误`)
      } else {
        ElMessage.success(msg)
      }
    } catch (error: any) {
      monthEntries.value = []
      monthListErrors.value = []
      appendStatus(statusLogRef, '清单解析失败: ' + getApiErrorMessage(error), 'error')
      ElMessage.error('清单解析失败')
    } finally {
      monthParsing.value = false
    }
  }

  async function onExecuteMonthly() {
    // 筛选已选日期的条目
    const selectedEntries = monthEntries.value.filter(e => monthSelectedDates.value.has(e.date))
    if (selectedEntries.length === 0) {
      ElMessage.warning('请先解析清单并勾选要生成的日期')
      return
    }

    if (monthlyTemplateMode.value === 'path') {
      if (!monthlyPathLocked.value) {
        ElMessage.warning('请先锁定大表和小表模板路径')
        return
      }
    }

    monthExecuting.value = true
    clearStatus(statusLogRef)
    appendStatus(statusLogRef, `开始批量生成 ${month.value} 月度检测报告...`, 'info')

    try {
      if (monthlyTemplateMode.value === 'path') {
        const hasOutputDir = Boolean(monthlyOutputDir.value)
        const payload = await executePesticideMonthlyWithPaths({
          month: month.value,
          entries: selectedEntries,
          inspectorName: inspectorName.value,
          bigTemplatePath: monthlyFoundBig.value,
          smallTemplatePath: monthlyFoundSmall.value,
          outputDir: hasOutputDir ? monthlyOutputDir.value : undefined,
        })
        if (hasOutputDir) {
          monthResult.value = payload.message
          appendStatus(statusLogRef, payload.message, 'success')
          appendStatus(statusLogRef, `输出目录: ${monthlyOutputDir.value}`, 'info')
          ElMessage.success('月度批量报告已生成，已保存到输出目录')
        } else {
          triggerDownload(payload)
          monthResult.value = payload.message
          appendStatus(statusLogRef, payload.message, 'success')
          ElMessage.success('月度批量报告已生成')
        }
      } else {
        const hasOutputDir = Boolean(monthlyOutputDir.value)
        const payload = await executePesticideMonthly({
          month: month.value,
          entries: selectedEntries,
          inspectorName: inspectorName.value,
          bigTemplateFile: monthUseSavedTemplates.value ? null : monthBigTemplateFile.value,
          smallTemplateFile: monthUseSavedTemplates.value ? null : monthSmallTemplateFile.value,
          outputDir: hasOutputDir ? monthlyOutputDir.value : undefined,
        })
        if (hasOutputDir) {
          monthResult.value = payload.message
          appendStatus(statusLogRef, payload.message, 'success')
          appendStatus(statusLogRef, `输出目录: ${monthlyOutputDir.value}`, 'info')
          ElMessage.success('月度批量报告已生成，已保存到输出目录')
        } else {
          triggerDownload(payload)
          monthResult.value = payload.message
          appendStatus(statusLogRef, payload.message, 'success')
          ElMessage.success('月度批量报告已生成')
        }
      }
    } catch (error: any) {
      const detail = getApiErrorMessage(error)
      appendStatus(statusLogRef, '月度批量执行失败: ' + detail, 'error')
      ElMessage.error('月度批量执行失败')
    } finally {
      monthExecuting.value = false
    }
  }

  // 日期选择辅助
  function toggleDate(date: string) {
    const next = new Set(monthSelectedDates.value)
    if (next.has(date)) next.delete(date)
    else next.add(date)
    monthSelectedDates.value = next
  }

  function toggleAllDates() {
    if (monthSelectedDates.value.size === monthEntries.value.length) {
      monthSelectedDates.value = new Set()
    } else {
      monthSelectedDates.value = new Set(monthEntries.value.map(e => e.date))
    }
  }

  const allDatesSelected = computed(() =>
    monthEntries.value.length > 0 && monthSelectedDates.value.size === monthEntries.value.length,
  )

  const monthSelectedCount = computed(() =>
    monthEntries.value.filter(e => monthSelectedDates.value.has(e.date)).reduce((s, e) => s + e.names.length, 0),
  )

  watch(detectDate, async (value) => {
    if (value) {
      await persistConfig({ pesticide_last_date: value })
    }
  })

  onMounted(() => {
    loadConfig()
    onLoadTemplates()
  })

  return {
    activeTab,
    allDatesSelected,
    bigFile,
    bigPath,
    dataCount,
    detectDate,
    executing,
    fileInfo,
    fileReadyCount,
    findFilesMessage,
    findingFiles,
    formatHeroDate,
    foundFileBig,
    foundFileSmall,
    getFileName,
    inspectorName,
    jsonStatus,
    jsonText,
    lastRunMessage,
    month,
    monthBigTemplateFile,
    monthEntries,
    monthExecuting,
    monthListErrors,
    monthListFile,
    monthListPath,
    monthListText,
    monthParsing,
    monthResult,
    monthSelectedCount,
    monthSelectedDates,
    monthSmallTemplateFile,
    monthUseSavedTemplates,
    monthlyBigPath,
    monthlyFindFilesMessage,
    monthlyFindingFiles,
    monthlyFoundBig,
    monthlyFoundSmall,
    monthlyOutputDir,
    monthlyPathLocked,
    monthlySmallPath,
    monthlyTemplateMode,
    onBrowseOutputDir,
    onBrowsePath,
    onClearJson,
    onClearVeg,
    onDedupJson,
    onExecute,
    onExecuteMonthly,
    onFindFiles,
    onFormatJson,
    onGenerateRates,
    onJsonInput,
    onLoadTemplates,
    onBrowseMonthListFile,
    onConfirmMonthListPath,
    onOpenMonthListFile,
    onBrowseTemplate,
    onSaveTemplatePath,
    onMonthlyBrowsePath,
    onMonthlyFindFiles,
    onParseMonthlyList,
    onReset,
    onSetTab,
    onSwitchMode,
    onUploadTemplate,
    onVegInput,
    outputDir,
    parseVegNames,
    pathLocked,
    pendingTemplatePath,
    savingTemplate,
    setFile,
    smallFile,
    smallPath,
    templateLoading,
    templateStatus,
    toggleAllDates,
    toggleDate,
    usePathMode,
    vegStatus,
    vegText,
  }
}
