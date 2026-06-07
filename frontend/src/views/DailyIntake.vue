<template>
  <div class="page-shell page-shell--full">
    <PageHeader eyebrow="每日点货" title="按业务日期维护点货单" tone="green">
      <template #aside>
        <div class="hero-metric-grid">
          <div class="hero-metric">
            <span class="hero-metric__label">业务日期</span>
            <span class="hero-metric__value">{{ workflow.selectedDate.value }}</span>
            <span class="hero-metric__note">点货以此日期为单</span>
          </div>
          <div class="hero-metric">
            <span class="hero-metric__label">条目数</span>
            <span class="hero-metric__value">{{ workflow.sheetItems.value.length }}</span>
            <span class="hero-metric__note">当前点货单总数</span>
          </div>
          <div class="hero-metric">
            <span class="hero-metric__label">总数量</span>
            <span class="hero-metric__value">{{ workflow.totalQuantity.value }}</span>
            <span class="hero-metric__note">所有单位累计</span>
          </div>
          <div class="hero-metric">
            <span class="hero-metric__label">状态</span>
            <span class="hero-metric__value">{{ workflow.loadingSheet.value ? '加载中' : '就绪' }}</span>
            <span class="hero-metric__note">{{ workflow.parseMessage.value || '可继续录入' }}</span>
          </div>
        </div>
        <router-link to="/smart-detection" style="margin-top:12px;display:inline-block">
          <el-button type="success">
            生成农残报告
          </el-button>
        </router-link>
      </template>
    </PageHeader>

    <el-card shadow="never" class="panel-card voice-card">
      <div class="panel-heading">
        <div>
          <div class="panel-heading__eyebrow">语音录入</div>
          <h2 class="panel-heading__title">说出商品与数量</h2>
          <p class="panel-heading__description">
            按下话筒后开始说话，例如「白菜 4.8 斤」。识别使用 Qwen3-ASR / faster-whisper 双模型自动回退。
          </p>
        </div>
      </div>

      <div class="voice-card__body">
        <div class="voice-card__selector">
          <span class="voice-card__selector-label">识别模型：</span>
          <el-radio-group v-model="asrProviderSelection" size="small">
            <el-radio-button value="auto">自动（千问优先）</el-radio-button>
            <el-radio-button value="qwen3-asr">仅千问 Qwen3-ASR</el-radio-button>
            <el-radio-button value="faster-whisper">仅 faster-whisper</el-radio-button>
          </el-radio-group>
          <el-tag :type="activeProviderTag.tone" size="small" effect="dark" round class="voice-card__active-tag">
            {{ activeProviderTag.label }}
          </el-tag>
        </div>

        <div class="voice-card__action">
          <el-button
            :type="recordButtonState.type"
            :loading="recordButtonState.loading"
            :disabled="recordButtonState.disabled"
            size="large"
            class="voice-card__primary"
            @click="onRecordButton"
          >
            {{ recordButtonState.label }}
          </el-button>
          <el-button
            v-if="speech.state.value === 'listening'"
            plain
            size="large"
            @click="onCancelRecording"
          >
            取消
          </el-button>

          <div class="voice-card__devices">
            <el-tooltip :content="qwenChip.tooltip" placement="top">
              <el-tag :type="qwenChip.tone" size="small" effect="plain" round>
                Qwen3-ASR · {{ qwenChip.label }}
              </el-tag>
            </el-tooltip>
            <el-tooltip :content="whisperChip.tooltip" placement="top">
              <el-tag :type="whisperChip.tone" size="small" effect="plain" round>
                faster-whisper · {{ whisperChip.label }}
              </el-tag>
            </el-tooltip>
            <el-button
              circle
              size="small"
              :loading="diagnosticsLoading"
              :icon="Refresh"
              title="刷新推理设备状态"
              @click="refreshDiagnostics"
            />
          </div>
        </div>

        <div
          v-if="speech.state.value === 'listening'"
          class="voice-card__bars"
          aria-hidden="true"
        >
          <span
            v-for="(level, idx) in speech.audioLevelBars.value"
            :key="idx"
            class="voice-card__bar"
            :style="{ height: `${Math.max(level, 0.04) * 100}%` }"
          />
        </div>

        <p v-if="voiceStatusHint" class="voice-card__hint">{{ voiceStatusHint }}</p>

        <el-alert
          v-if="voiceAlert"
          :type="voiceAlert.type"
          :title="voiceAlert.title"
          :closable="false"
          show-icon
          class="voice-card__alert"
        />
      </div>
    </el-card>

    <el-card shadow="never" class="panel-card">
      <div class="panel-heading">
        <div>
          <div class="panel-heading__eyebrow">手动录入</div>
          <h2 class="panel-heading__title">手填补充入口</h2>
          <p class="panel-heading__description">
            如果不方便录音，可以在这里直接填写品名与数量。合并预览与历史回看仍在恢复中。
          </p>
        </div>
      </div>

      <el-form :model="workflow.entryDraft" label-position="top">
        <div class="field-grid two-up">
          <el-form-item label="业务日期">
            <el-date-picker
              v-model="workflow.selectedDate.value"
              type="date"
              value-format="YYYY-MM-DD"
              :clearable="false"
              @change="onDateChange"
            />
          </el-form-item>
          <el-form-item label="分类">
            <el-select v-model="workflow.entryDraft.category">
              <el-option
                v-for="opt in categoryOptions"
                :key="opt.value"
                :label="opt.label"
                :value="opt.value"
              />
            </el-select>
          </el-form-item>
          <el-form-item label="商品名称">
            <el-input v-model="workflow.entryDraft.name" placeholder="例如：青椒" />
          </el-form-item>
          <el-form-item label="数量">
            <el-input-number v-model="workflow.entryDraft.quantity" :min="0" :precision="2" />
          </el-form-item>
          <el-form-item label="单位">
            <el-select v-model="workflow.entryDraft.unit">
              <el-option v-for="u in unitOptions" :key="u" :label="u" :value="u" />
            </el-select>
          </el-form-item>
        </div>

        <el-button
          type="primary"
          :loading="workflow.submitting.value"
          @click="onSubmit"
        >
          新增条目
        </el-button>
      </el-form>
    </el-card>

    <el-card shadow="never" class="panel-card">
      <div class="panel-heading">
        <div>
          <div class="panel-heading__eyebrow">条目列表</div>
          <h2 class="panel-heading__title">当前点货单</h2>
        </div>
      </div>
      <el-table :data="workflow.sheetItems.value" v-loading="workflow.loadingSheet.value" empty-text="今日还没有条目">
        <el-table-column prop="raw_name" label="名称" min-width="120" />
        <el-table-column prop="category" label="分类" width="80">
          <template #default="{ row }">{{ categoryLabel(row.category) }}</template>
        </el-table-column>
        <el-table-column prop="quantity" label="数量" width="100" />
        <el-table-column prop="unit_name" label="单位" width="80" />
        <el-table-column prop="merge_count" label="合并次数" width="100" />
        <el-table-column label="操作" width="100">
          <template #default="{ row }">
            <el-button size="small" link type="danger" :loading="workflow.deletingId.value === row.id" @click="workflow.removeItem(row.id)">
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog
      v-model="workflow.voiceConfirmVisible.value"
      title="确认语音条目"
      width="480px"
      :close-on-click-modal="false"
      append-to-body
      @close="onVoiceConfirmClose"
    >
      <p
        v-if="workflow.voiceConfirmDraft.transcript"
        class="voice-dialog__transcript"
      >
        原始转写：{{ workflow.voiceConfirmDraft.transcript }}
      </p>
      <p v-if="workflow.voiceConfirmDraft.asrProvider" class="voice-dialog__asr-info">
        识别模型：{{ PROVIDER_LABELS[workflow.voiceConfirmDraft.asrProvider] || workflow.voiceConfirmDraft.asrProvider }}
        <template v-if="workflow.voiceConfirmDraft.asrDurationMs">
          · 耗时 {{ workflow.voiceConfirmDraft.asrDurationMs }} ms
        </template>
        <template v-if="workflow.voiceConfirmDraft.asrFallbackUsed">
          · 已使用备用模型
        </template>
      </p>

      <el-form :model="workflow.voiceConfirmDraft" label-position="top">
        <div class="field-grid two-up">
          <el-form-item label="商品名称">
            <el-input v-model="workflow.voiceConfirmDraft.name" placeholder="例如：白菜" />
          </el-form-item>
          <el-form-item label="分类">
            <el-select v-model="workflow.voiceConfirmDraft.category">
              <el-option
                v-for="opt in categoryOptions"
                :key="opt.value"
                :label="opt.label"
                :value="opt.value"
              />
            </el-select>
          </el-form-item>
          <el-form-item label="数量">
            <el-input-number
              v-model="workflow.voiceConfirmDraft.quantity"
              :min="0"
              :precision="2"
            />
          </el-form-item>
          <el-form-item label="单位">
            <el-select v-model="workflow.voiceConfirmDraft.unit">
              <el-option v-for="u in unitOptions" :key="u" :label="u" :value="u" />
            </el-select>
          </el-form-item>
        </div>
        <el-form-item>
          <el-checkbox v-model="workflow.voiceConfirmDraft.rememberCorrection">
            记住对识别结果的修正（用于热词学习）
          </el-checkbox>
        </el-form-item>
      </el-form>

      <ul
        v-if="workflow.voiceConfirmWarnings.value.length"
        class="voice-dialog__warnings"
      >
        <li v-for="(warning, idx) in workflow.voiceConfirmWarnings.value" :key="idx">
          {{ warning }}
        </li>
      </ul>

      <template #footer>
        <el-button @click="onVoiceConfirmClose">取消</el-button>
        <el-button
          type="primary"
          :loading="workflow.voiceConfirmSubmitting.value"
          @click="onVoiceConfirmSubmit"
        >
          保存
        </el-button>
      </template>
    </el-dialog>

    <StatusLog ref="statusLogRef" />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'

defineOptions({ name: 'DailyIntake' })
import { Refresh } from '@element-plus/icons-vue'
import PageHeader from '../components/PageHeader.vue'
import StatusLog from '../components/StatusLog.vue'
import { trackAudit } from '../api/audit'
import {
  getDailyIntakeSpeechRuntimeDiagnostics,
  type DailyIntakeSpeechRuntimeDiagnosticsResponse,
} from '../api/daily-intake'
import { useDailyIntakeWorkflow } from '../features/daily-intake/composables/useDailyIntakeWorkflow'
import { useSpeechInput } from '../features/daily-intake/composables/useSpeechInput'
import {
  DAILY_INTAKE_CATEGORY_LABELS as categoryLabels,
  DAILY_INTAKE_CATEGORY_OPTIONS as categoryOptions,
  DAILY_INTAKE_UNITS,
  type DailyIntakeAsrProviderSelection,
  type DailyIntakeCategory,
} from '../features/daily-intake/types'

const statusLogRef = ref<InstanceType<typeof StatusLog>>()
const workflow = useDailyIntakeWorkflow(statusLogRef)
const speech = useSpeechInput()
const unitOptions = [...DAILY_INTAKE_UNITS]

function categoryLabel(category: string): string {
  return category in categoryLabels ? categoryLabels[category as DailyIntakeCategory] : category
}

// ---------------------------------------------------------------------------
// ASR provider selection (persisted in localStorage) + device chips
// ---------------------------------------------------------------------------
const ASR_PROVIDER_STORAGE_KEY = 'dailyIntake.asrProvider'
const VALID_PROVIDERS: DailyIntakeAsrProviderSelection[] = [
  'auto',
  'qwen3-asr',
  'faster-whisper',
]

function loadStoredAsrProvider(): DailyIntakeAsrProviderSelection {
  try {
    const stored = window.localStorage.getItem(ASR_PROVIDER_STORAGE_KEY)
    if (stored && (VALID_PROVIDERS as string[]).includes(stored)) {
      return stored as DailyIntakeAsrProviderSelection
    }
  } catch {
    // localStorage unavailable (private mode, etc.)
  }
  return 'auto'
}

const asrProviderSelection = ref<DailyIntakeAsrProviderSelection>(loadStoredAsrProvider())

watch(asrProviderSelection, (next, prev) => {
  try {
    window.localStorage.setItem(ASR_PROVIDER_STORAGE_KEY, next)
  } catch (e: any) { /* non-critical */ }
  if (prev !== undefined && next !== prev) {
    void trackAudit({
      module: 'daily_intake',
      action: 'asr_provider_change',
      description: next,
      metadata: { previous: prev },
    })
  }
})

const diagnostics = ref<DailyIntakeSpeechRuntimeDiagnosticsResponse | null>(null)
const diagnosticsLoading = ref(false)

async function refreshDiagnostics() {
  diagnosticsLoading.value = true
  try {
    const { data } = await getDailyIntakeSpeechRuntimeDiagnostics()
    diagnostics.value = data
  } catch {
    diagnostics.value = null
  } finally {
    diagnosticsLoading.value = false
  }
}

onMounted(() => {
  void refreshDiagnostics()
})

type ChipTone = 'success' | 'info' | 'warning'
interface ProviderChip {
  label: string
  tone: ChipTone
  tooltip: string
}

function providerInfo(providerName: 'qwen3-asr' | 'faster-whisper') {
  const list = (diagnostics.value?.providers ?? []) as Array<Record<string, unknown>>
  return list.find((p) => p?.provider === providerName)
}

function buildChip(providerName: 'qwen3-asr' | 'faster-whisper'): ProviderChip {
  const info = providerInfo(providerName)
  if (!diagnostics.value) {
    return { label: '探测中…', tone: 'warning', tooltip: '尚未获取到运行时诊断数据。' }
  }
  if (!info) {
    return { label: '未报告', tone: 'warning', tooltip: `诊断数据里找不到 ${providerName}。` }
  }
  const dependencyAvailable = Boolean(info.dependency_available)
  if (!dependencyAvailable) {
    return {
      label: '依赖未就绪',
      tone: 'warning',
      tooltip: String(info.message || '缺少依赖或未安装，请查看后端日志。'),
    }
  }
  const raw = String(info.effective_device || info.device || '').toLowerCase()
  const compute = String(info.compute_type || info.effective_compute_type || info.resolved_compute_type || '')
  const model = String(info.model || '')
  const cudaCount = Number(info.cuda_device_count || 0)
  const tooltipParts: string[] = []
  if (model) tooltipParts.push(`模型 ${model}`)
  if (compute) tooltipParts.push(`compute_type ${compute}`)
  if (raw.includes('cuda') || raw.includes('gpu')) tooltipParts.push(`CUDA 设备数 ${cudaCount}`)
  if (info.fallback_used) tooltipParts.push(`（回退：${info.fallback_reason || '未知原因'}）`)
  const tooltip = tooltipParts.join(' · ') || String(info.message || '已就绪')
  if (!raw) {
    return { label: '未探测', tone: 'warning', tooltip }
  }
  if (raw.includes('cuda') || raw.includes('gpu')) {
    return { label: 'GPU (CUDA)', tone: 'success', tooltip }
  }
  if (raw === 'cpu') {
    return { label: 'CPU', tone: 'info', tooltip }
  }
  return { label: raw.toUpperCase(), tone: 'info', tooltip }
}

const qwenChip = computed(() => buildChip('qwen3-asr'))
const whisperChip = computed(() => buildChip('faster-whisper'))

const PROVIDER_LABELS: Record<string, string> = {
  auto: '自动（千问优先）',
  'qwen3-asr': '仅千问 Qwen3-ASR',
  'faster-whisper': '仅 faster-whisper',
}
const activeProviderTag = computed<{ label: string; tone: 'success' | 'warning' | 'info' }>(() => {
  const selection = asrProviderSelection.value
  const label = PROVIDER_LABELS[selection] || selection
  if (selection === 'faster-whisper') {
    return { label: `当前：${label}`, tone: 'warning' }
  }
  if (selection === 'qwen3-asr') {
    return { label: `当前：${label}`, tone: 'success' }
  }
  return { label: `当前：${label}`, tone: 'info' }
})

type RecordButtonType = 'primary' | 'danger' | 'info'

const recordButtonState = computed<{
  label: string
  type: RecordButtonType
  loading: boolean
  disabled: boolean
}>(() => {
  if (workflow.parsingVoice.value) {
    return { label: '识别中…', type: 'primary', loading: true, disabled: true }
  }
  if (speech.state.value === 'authorizing') {
    return { label: '正在请求麦克风…', type: 'primary', loading: true, disabled: true }
  }
  if (speech.state.value === 'listening') {
    return { label: '停止并识别', type: 'danger', loading: false, disabled: false }
  }
  if (
    !speech.supported ||
    speech.state.value === 'unsupported' ||
    speech.state.value === 'blocked' ||
    speech.state.value === 'permission-denied'
  ) {
    return { label: '当前环境不可录音', type: 'info', loading: false, disabled: true }
  }
  return { label: '开始录音', type: 'primary', loading: false, disabled: false }
})

const voiceStatusHint = computed(() => {
  if (workflow.parsingVoice.value) return '正在调用 Qwen3-ASR / faster-whisper 转写，请稍候。'
  if (speech.state.value === 'listening') return '正在录音，说完后点击「停止并识别」。'
  if (speech.state.value === 'authorizing') return '请在浏览器弹窗中允许使用麦克风。'
  if (speech.state.value === 'idle' && speech.supported) return speech.compatibilityHint
  return ''
})

const voiceAlert = computed<{ type: 'warning' | 'error' | 'info'; title: string } | null>(() => {
  if (speech.errorMessage.value) {
    return { type: 'error', title: speech.errorMessage.value }
  }
  if (speech.state.value === 'unsupported' || !speech.supported) {
    return {
      type: 'warning',
      title: '当前浏览器不支持本地录音上传，请改用较新的 Chrome、Safari 或 Edge。',
    }
  }
  if (speech.state.value === 'blocked') {
    return {
      type: 'warning',
      title: '当前页面不是安全上下文，请改用 HTTPS 或本机 localhost 打开。',
    }
  }
  if (speech.state.value === 'permission-denied') {
    return {
      type: 'warning',
      title: '浏览器未授予麦克风权限，请在地址栏权限设置里允许后重试。',
    }
  }
  return null
})

async function onRecordButton() {
  if (speech.state.value === 'listening') {
    void trackAudit({ module: 'daily_intake', action: 'voice_record_stop' })
    speech.stopListening()
    return
  }
  void trackAudit({
    module: 'daily_intake',
    action: 'voice_record_start',
    description: workflow.selectedDate.value,
  })
  await speech.startListening()
}

function onCancelRecording() {
  void trackAudit({ module: 'daily_intake', action: 'voice_record_cancel' })
  speech.abortListening()
}

function onVoiceConfirmClose() {
  workflow.closeVoiceConfirmDialog()
}

// 录音停止 → MediaRecorder 在 onstop 里把 blob 写入 recordedAudio 并把 state 切回 idle，
// 这里捕获该迁移并触发后端转写。state→error/unsupported 路径下不会调用。
watch(
  () => speech.state.value,
  async (next, prev) => {
    if (prev !== 'listening' || next !== 'idle') return
    const clip = speech.consumeRecordedAudio()
    if (!clip) return
    speech.setParsing()
    try {
      await workflow.parseVoiceAudio(
        { blob: clip.blob, filename: clip.filename },
        { asrProvider: asrProviderSelection.value },
      )
    } finally {
      speech.markIdle()
    }
  },
)

async function onDateChange() {
  await workflow.loadSheetByDate(workflow.selectedDate.value)
}

async function onSubmit() {
  void trackAudit({
    module: 'daily_intake',
    action: 'manual_create',
    description: workflow.selectedDate.value,
    metadata: {
      category: workflow.entryDraft.category,
      unit: workflow.entryDraft.unit,
    },
  })
  await workflow.submitDraft()
}

async function onVoiceConfirmSubmit() {
  void trackAudit({
    module: 'daily_intake',
    action: 'voice_save',
    description: workflow.selectedDate.value,
    metadata: {
      category: workflow.voiceConfirmDraft.category,
      unit: workflow.voiceConfirmDraft.unit,
    },
  })
  await workflow.submitVoiceConfirm()
}
</script>

<style scoped>
.voice-card__body {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-top: 8px;
}

.voice-card__selector {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.voice-card__selector-label {
  color: var(--el-text-color-secondary);
  font-size: 13px;
}

.voice-card__action {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.voice-card__devices {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  margin-left: auto;
}

@media (max-width: 720px) {
  .voice-card__devices {
    margin-left: 0;
    width: 100%;
  }
}

.voice-card__primary {
  min-width: 160px;
}

.voice-card__bars {
  display: flex;
  align-items: flex-end;
  gap: 4px;
  height: 40px;
  padding: 4px 0;
}

.voice-card__bar {
  display: inline-block;
  width: 6px;
  border-radius: 3px;
  background: var(--el-color-primary);
  transition: height 80ms ease-out;
}

.voice-card__hint {
  margin: 0;
  color: var(--el-text-color-secondary);
  font-size: 13px;
}

.voice-card__alert {
  margin-top: 4px;
}

.voice-card__active-tag {
  flex-shrink: 0;
  margin-left: 4px;
}

.voice-dialog__transcript {
  margin: 0 0 12px;
  padding: 8px 12px;
  border-radius: 6px;
  background: var(--el-fill-color-light);
  color: var(--el-text-color-secondary);
  font-size: 13px;
  line-height: 1.5;
}

.voice-dialog__asr-info {
  margin: -8px 0 12px;
  font-size: 12px;
  color: var(--el-text-color-placeholder);
  line-height: 1.4;
}

.voice-dialog__warnings {
  margin: 12px 0 0;
  padding-left: 18px;
  color: var(--el-color-warning);
  font-size: 12px;
  line-height: 1.6;
}
</style>
