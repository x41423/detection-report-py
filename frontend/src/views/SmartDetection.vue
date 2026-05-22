<template>
  <div class="smart-detection">
    <el-card class="header-card">
      <div class="header-row">
        <h2>智能检测工作台</h2>
        <div class="inspector">
          检查员:
          <el-input v-model="inspectorName" size="small" style="width:120px;margin-left:4px"
            @blur="saveInspectorName" />
        </div>
      </div>
      <div class="template-bar">
        <div class="template-item">
          <span class="template-label">大表</span>
          <el-tag v-if="bigTemplateInfo.configured" type="success" size="small">{{ bigTemplateInfo.filename }}</el-tag>
          <el-tag v-else type="danger" size="small">未上传</el-tag>
          <el-upload :show-file-list="false" :auto-upload="false" :accept="'.docx,.doc'" @change="(f:any) => uploadTemplate('big', f.raw)">
            <el-button size="small" text type="primary">更换</el-button>
          </el-upload>
        </div>
        <div class="template-item">
          <span class="template-label">小表</span>
          <el-tag v-if="smallTemplateInfo.configured" type="success" size="small">{{ smallTemplateInfo.filename }}</el-tag>
          <el-tag v-else type="danger" size="small">未上传</el-tag>
          <el-upload :show-file-list="false" :auto-upload="false" :accept="'.docx,.doc'" @change="(f:any) => uploadTemplate('small', f.raw)">
            <el-button size="small" text type="primary">更换</el-button>
          </el-upload>
        </div>
      </div>
      <div class="output-bar">
        <span class="template-label">输出路径</span>
        <el-input :model-value="outputDir" size="small" placeholder="点击右侧浏览选择输出目录" readonly style="flex:1;max-width:480px">
          <template #append>
            <el-button @click="onBrowseOutputDir">浏览</el-button>
          </template>
        </el-input>
      </div>
      <el-radio-group v-model="dataSource" class="source-switch">
        <el-radio-button value="auto">自动推荐</el-radio-button>
        <el-radio-button value="manual">完全手动</el-radio-button>
      </el-radio-group>
    </el-card>

    <el-alert v-if="gaps && gaps.total_missing > 0" type="warning" :closable="false" show-icon style="margin-bottom:12px">
      <template #title>
        发现 {{ gaps.total_missing }} 天遗漏检测:
        {{ gaps.missing_dates.slice(0, 3).join(', ') }}{{ gaps.missing_dates.length > 3 ? '...' : '' }}
        <el-button type="warning" size="small" @click="showBackfillDialog">批量补做</el-button>
      </template>
    </el-alert>

    <!-- Config warnings -->
    <el-alert v-if="!bigTemplate || !smallTemplate" type="error" :closable="false" show-icon style="margin-bottom:12px">
      <template #title>
        模板未配置 — 请在顶部上传大表/小表模板（.docx 格式）
      </template>
    </el-alert>
    <el-alert v-if="!outputDir" type="warning" :closable="false" show-icon style="margin-bottom:12px">
      <template #title>
        输出目录未配置 — 报告将保存到应用默认位置
      </template>
    </el-alert>

    <el-alert v-if="smartError" :title="smartError" type="error" show-icon style="margin-bottom:12px" closable />

    <el-skeleton v-if="loading" :rows="6" animated />

    <div v-else class="panels" :class="{ 'manual-mode': dataSource === 'manual' }">
      <div v-if="dataSource === 'auto'" class="panel">
        <div class="panel-header">
          <span>今日进货需检 ({{ todayIntakeItems.length }} 种)</span>
          <div class="panel-actions">
            <el-button size="small" text @click="selectAllToday">全选</el-button>
            <el-button size="small" text @click="deselectAllToday">反选</el-button>
          </div>
        </div>
        <div class="veg-list">
          <el-checkbox
            v-for="item in todayIntakeItems"
            :key="item.name"
            :model-value="selectedToday.has(item.name)"
            @change="toggleToday(item.name)"
          >
            {{ item.name }}
          </el-checkbox>
        </div>
        <div v-if="todayIntakeItems.length === 0" class="empty-hint">暂无今日点货数据</div>
      </div>

      <div v-if="dataSource === 'auto'" class="panel">
        <div class="panel-header">
          <span>昨日库存未检 ({{ yesterdayInventoryItems.length }} 种)</span>
          <div class="panel-actions">
            <el-button size="small" text @click="selectAllYesterday">全选</el-button>
            <el-button size="small" text @click="deselectAllYesterday">反选</el-button>
          </div>
        </div>
        <div class="veg-list">
          <el-checkbox
            v-for="item in yesterdayInventoryItems"
            :key="item.name"
            :model-value="selectedYesterday.has(item.name)"
            @change="toggleYesterday(item.name)"
          >
            {{ item.name }}
            <el-tag size="small" type="warning" style="margin-left:4px">未检</el-tag>
          </el-checkbox>
        </div>
        <div v-if="yesterdayInventoryItems.length === 0" class="empty-hint">昨日均已检测</div>
      </div>

      <div class="panel manual-panel">
        <div class="panel-header">
          <span>手动补充 ({{ manualAdditions.length }} 种)</span>
        </div>
        <div class="manual-input">
          <el-input v-model="newVegName" placeholder="输入蔬菜名称" size="small" @keyup.enter="addManualVeg">
            <template #append>
              <el-button @click="addManualVeg">添加</el-button>
            </template>
          </el-input>
        </div>
        <el-tag
          v-for="(name, idx) in manualAdditions"
          :key="idx"
          closable
          class="manual-tag"
          @close="removeManual(idx)"
        >
          {{ name }}
        </el-tag>
      </div>
    </div>

    <div v-if="!loading" class="action-bar">
      <div class="action-info">
        <span>检测日期: <strong>{{ detectionDate }}</strong></span>
        <span>已选 <strong :class="{ 'zero-count': selectedCount === 0 }">{{ selectedCount }}</strong> 种蔬菜</span>
        <span :class="{ 'warn-text': !bigTemplate || !smallTemplate }">模板: {{ bigTemplate && smallTemplate ? '已就绪' : '未配置' }}</span>
      </div>
      <div class="action-buttons">
        <el-button type="primary" size="large" :loading="executing"
          :disabled="selectedCount === 0 || !bigTemplate || !smallTemplate"
          @click="runDetection">
          一键生成报告
        </el-button>
        <el-button size="large" :loading="executing"
          :disabled="selectedCount === 0 || !bigTemplate || !smallTemplate"
          @click="runDetectionWithPdf">
          生成并导出 PDF
        </el-button>
      </div>
    </div>

    <el-card v-if="lastResult" class="result-card">
      <template #header>{{ lastResult.success ? '检测结果' : '检测失败' }}</template>
      <el-alert v-if="!lastResult.success && lastResult.error" :title="lastResult.error" type="error" show-icon style="margin-bottom:12px" />
      <el-descriptions v-if="lastResult.success" :column="2" border>
        <el-descriptions-item label="状态">
          <el-tag :type="lastResult.success ? 'success' : 'danger'">
            {{ lastResult.success ? '成功' : '失败' }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="检测日期">{{ detectionDate }}</el-descriptions-item>
        <el-descriptions-item label="蔬菜数量">{{ lastResult.summary?.total_varieties || 0 }} 种</el-descriptions-item>
        <el-descriptions-item label="检测员">{{ lastResult.summary?.inspector || inspectorName }}</el-descriptions-item>
      </el-descriptions>

      <el-alert
        v-if="lastResult.low_stock_alerts && lastResult.low_stock_alerts.length > 0"
        type="warning"
        :closable="false"
        show-icon
        style="margin-top: 12px"
      >
        <template #title>
          库存低量提醒:
          <el-tag
            v-for="a in lastResult.low_stock_alerts"
            :key="a.item_name"
            size="small"
            type="warning"
            style="margin-left: 4px"
          >
            {{ a.item_name }} ({{ a.balance }}{{ a.unit }})
          </el-tag>
        </template>
      </el-alert>
    </el-card>

    <el-alert v-if="smartError" :title="smartError" type="error" show-icon style="margin-top:12px" />

    <DirBrowser ref="dirBrowserRef" />

    <el-dialog v-model="backfillDialogVisible" title="批量补做遗漏检测" width="550px" append-to-body>
      <el-form label-width="100px">
        <el-form-item label="日期范围">
          <el-date-picker
            v-model="backfillDateRange"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            value-format="YYYY-MM-DD"
          />
        </el-form-item>
      </el-form>
      <div v-if="backfillResult" style="margin-top:12px">
        <el-divider />
        <div class="backfill-summary">
          <span>共 {{ backfillResult.results.length }} 天:
            <el-tag size="small" type="success">{{ backfillResult.results.filter(r => r.success).length }} 成功</el-tag>
            <el-tag v-if="backfillResult.results.filter(r => !r.success).length > 0" size="small" type="danger" style="margin-left:4px">
              {{ backfillResult.results.filter(r => !r.success).length }} 失败
            </el-tag>
          </span>
        </div>
        <ul v-if="backfillResult.results.filter(r => !r.success).length > 0" class="backfill-errors">
          <li v-for="r in backfillResult.results.filter(r => !r.success)" :key="r.date">
            {{ r.date }}: {{ r.error || '未知错误' }}
          </li>
        </ul>
      </div>
      <template #footer>
        <el-button @click="backfillDialogVisible = false">关闭</el-button>
        <el-button type="primary" :loading="backfilling" @click="runBackfill">开始补做</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import type { DirBrowserHandle } from '../features/shared/workflow'
import { openPath } from '../features/shared/workflow'

defineOptions({ name: 'SmartDetection' })
import { ElMessage } from 'element-plus'
import { useSmartDetection } from '../features/smart-detection/composables/useSmartDetection'
import { useGapDetection } from '../features/smart-detection/composables/useGapDetection'
import { getSmartPrepare, putSmartPrepare } from '../api/smart-detection'
import { getPesticideTemplates, uploadPesticideTemplate } from '../api/pesticide'

const dirBrowserRef = ref<DirBrowserHandle>()
const inspectorName = ref('检测员')
const bigTemplate = ref('')
const smallTemplate = ref('')
const outputDir = ref('')
const dataSource = ref<'auto' | 'manual'>('auto')
const detectionDate = ref(new Date().toISOString().split('T')[0])
const newVegName = ref('')

const {
  todayIntakeItems, yesterdayInventoryItems, manualAdditions,
  selectedToday, selectedYesterday,
  loading, executing, lastResult,
  selectedCount, error: smartError,
  loadRecommendations, toggleToday, toggleYesterday,
  selectAllToday, deselectAllToday, selectAllYesterday, deselectAllYesterday,
  addManual, removeManual, execute,
} = useSmartDetection()

const { gaps, backfilling, backfillResult, checkGaps, backfill } = useGapDetection()

const backfillDialogVisible = ref(false)
const backfillDateRange = ref<[string, string] | null>(null)

const bigTemplateInfo = ref<{ configured: boolean; filename: string }>({ configured: false, filename: '' })
const smallTemplateInfo = ref<{ configured: boolean; filename: string }>({ configured: false, filename: '' })

function addManualVeg() {
  if (newVegName.value.trim()) {
    addManual(newVegName.value.trim())
    newVegName.value = ''
  }
}

async function onBrowseOutputDir() {
  const selected = await openPath(dirBrowserRef, outputDir.value || '', {
    title: '选择报告输出目录',
    mode: 'directory',
  })
  if (selected) {
    outputDir.value = selected
    await putSmartPrepare(inspectorName.value.trim(), selected)
  }
}

async function saveInspectorName() {
  if (!inspectorName.value.trim()) return
  try {
    await putSmartPrepare(inspectorName.value.trim())
    ElMessage.success('检测员已保存')
  } catch {
    ElMessage.error('保存检测员失败')
  }
}

async function runDetection() {
  const result = await execute({
    date: detectionDate.value,
    big_template: bigTemplate.value,
    small_template: smallTemplate.value,
    output_dir: outputDir.value,
    inspector_name: inspectorName.value,
    export_format: 'docx',
  })
  if (result && !result.success) {
    ElMessage.error(result.error || '检测执行失败')
  }
}

async function runDetectionWithPdf() {
  const result = await execute({
    date: detectionDate.value,
    big_template: bigTemplate.value,
    small_template: smallTemplate.value,
    output_dir: outputDir.value,
    inspector_name: inspectorName.value,
    export_format: 'both',
  })
  if (result && !result.success) {
    ElMessage.error(result.error || '检测执行失败')
  }
}

function showBackfillDialog() {
  backfillDateRange.value = null
  backfillDialogVisible.value = true
}

async function runBackfill() {
  if (!backfillDateRange.value) {
    ElMessage.warning('请选择日期范围')
    return
  }
  await backfill(backfillDateRange.value[0], backfillDateRange.value[1], inspectorName.value)
  backfillDialogVisible.value = false
  ElMessage.success('补做完成')
}

async function refreshPrepare() {
  try {
    const prep = await getSmartPrepare()
    bigTemplate.value = prep.big_template
    smallTemplate.value = prep.small_template
    outputDir.value = prep.output_dir || outputDir.value
  } catch { /* ignore */ }
}

async function loadTemplateInfo() {
  try {
    const { data } = await getPesticideTemplates()
    bigTemplateInfo.value = { configured: data.big_template.configured, filename: data.big_template.filename }
    smallTemplateInfo.value = { configured: data.small_template.configured, filename: data.small_template.filename }
  } catch { /* ignore */ }
}

async function uploadTemplate(kind: 'big' | 'small', file: File | null) {
  if (!file) return
  try {
    await uploadPesticideTemplate(kind, file)
    ElMessage.success(`${kind === 'big' ? '大表' : '小表'}模板已更新`)
    await loadTemplateInfo()
    await refreshPrepare()
  } catch {
    ElMessage.error('模板上传失败')
  }
}

onMounted(async () => {
  try {
    const prep = await getSmartPrepare()
    bigTemplate.value = prep.big_template
    smallTemplate.value = prep.small_template
    outputDir.value = prep.output_dir
    inspectorName.value = prep.inspector_name || '检测员'
  } catch {
    console.warn('获取工作台配置失败，将使用默认值')
  }
  loadTemplateInfo()
  loadRecommendations(detectionDate.value)
  checkGaps(7)
})
</script>

<style scoped>
.smart-detection { padding: 16px; max-width: 1400px; margin: 0 auto; }
.header-card { margin-bottom: 12px; }
.header-row { display: flex; justify-content: space-between; align-items: center; }
.header-row h2 { margin: 0; font-size: 20px; }
.inspector { color: #909399; font-size: 14px; }
.template-bar { display: flex; gap: 24px; margin: 12px 0 4px; align-items: center; }
.template-item { display: flex; align-items: center; gap: 6px; }
.template-label { font-size: 13px; color: #606266; }
.output-bar { display: flex; align-items: center; gap: 8px; margin: 4px 0; }
.source-switch { margin-top: 8px; }

.panels { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 12px; margin: 16px 0; }
.panels.manual-mode { grid-template-columns: 1fr; }
.panel { background: #fff; border: 1px solid #ebeef5; border-radius: 8px; padding: 12px; }
.panel-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; font-weight: 600; }
.panel-actions { display: flex; gap: 4px; }
.veg-list { display: flex; flex-direction: column; gap: 6px; max-height: 400px; overflow-y: auto; }
.empty-hint { color: #c0c4cc; font-size: 13px; text-align: center; padding: 20px 0; }
.manual-input { margin-bottom: 8px; }
.manual-tag { margin: 2px; }

.action-bar { display: flex; justify-content: space-between; align-items: center; padding: 16px; background: #fff; border-radius: 8px; border: 1px solid #ebeef5; margin: 12px 0; }
.action-info { display: flex; gap: 20px; color: #606266; }
.action-buttons { display: flex; gap: 8px; }

.result-card { margin-top: 16px; }

.zero-count { color: var(--el-color-danger); }
.warn-text { color: var(--el-color-warning); }
.backfill-summary { margin-bottom: 8px; }
.backfill-errors { padding: 0; margin: 8px 0 0; list-style: none; }
.backfill-errors li { color: var(--el-color-danger); font-size: 13px; padding: 3px 0; }
</style>
