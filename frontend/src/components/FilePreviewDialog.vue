<template>
  <el-dialog
    :model-value="visible"
    :title="title"
    width="90vw"
    top="3vh"
    :close-on-click-modal="false"
    :destroy-on-close="true"
    @update:model-value="$emit('update:visible', $event)"
  >
    <div class="file-preview-container">
      <!-- 加载中 -->
      <div v-if="loading" class="file-preview-status">
        <el-icon class="is-loading" :size="32"><Loading /></el-icon>
        <span>正在加载文件...</span>
      </div>

      <!-- 错误 -->
      <div v-else-if="error" class="file-preview-status file-preview-status--error">
        <el-icon :size="32"><WarningFilled /></el-icon>
        <span>{{ error }}</span>
        <el-button size="small" style="margin-top: 12px" @click="retry">重试</el-button>
      </div>

      <!-- 图片预览 -->
      <div v-else-if="viewerType === 'image'" class="file-preview-image">
        <img :src="effectiveSrc" :alt="fileName" />
      </div>

      <!-- PDF 预览 -->
      <VueOfficePdf
        v-else-if="viewerType === 'pdf'"
        :src="effectiveSrc"
        style="min-height: 70vh"
        @rendered="onRendered"
        @error="onError"
      />

      <!-- Word 预览 -->
      <VueOfficeDocx
        v-else-if="viewerType === 'docx'"
        :src="effectiveSrc"
        style="min-height: 70vh"
        @rendered="onRendered"
        @error="onError"
      />

      <!-- Excel 预览 -->
      <VueOfficeExcel
        v-else-if="viewerType === 'xlsx'"
        :src="effectiveSrc"
        style="min-height: 70vh"
        @rendered="onRendered"
        @error="onError"
      />

      <!-- CSV 预览 -->
      <div v-else-if="viewerType === 'csv'" class="file-preview-csv">
        <el-table
          :data="csvData"
          border
          stripe
          max-height="60vh"
          style="width: 100%"
        >
          <el-table-column
            v-for="col in csvColumns"
            :key="col"
            :prop="col"
            :label="col"
            min-width="120"
            show-overflow-tooltip
          />
        </el-table>
      </div>

      <!-- 纯文本预览 -->
      <div v-else-if="viewerType === 'text'" class="file-preview-text">
        <pre>{{ textContent }}</pre>
      </div>

      <!-- 不支持的类型 -->
      <div v-else class="file-preview-status">
        <el-icon :size="32"><Document /></el-icon>
        <span>暂不支持预览 {{ fileExtension }} 格式，请下载后查看</span>
        <el-button size="small" type="primary" style="margin-top: 12px" @click="downloadFile">
          下载文件
        </el-button>
      </div>
    </div>

    <template #footer>
      <div class="file-preview-footer">
        <span class="file-preview-footer__name">{{ fileName }}</span>
        <div>
          <el-button size="small" @click="downloadFile">下载</el-button>
          <el-button @click="$emit('update:visible', false)">关闭</el-button>
        </div>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { Loading, WarningFilled, Document } from '@element-plus/icons-vue'
import VueOfficeDocx from '@vue-office/docx'
import VueOfficeExcel from '@vue-office/excel'
import VueOfficePdf from '@vue-office/pdf'
import '@vue-office/docx/lib/index.css'
import '@vue-office/excel/lib/index.css'

// ---------- Props ----------

const props = withDefaults(defineProps<{
  visible: boolean
  src: string            // 文件 URL（支持 http/https、blob、data URL）
  fileName?: string
  /** 强制指定预览类型，不传则根据文件名后缀自动推断 */
  viewerType?: 'image' | 'pdf' | 'docx' | 'xlsx' | 'csv' | 'text'
}>(), {
  fileName: '未命名文件',
})

const emit = defineEmits<{
  'update:visible': [value: boolean]
}>()

// ---------- 类型推断 ----------

type ViewerType = 'image' | 'pdf' | 'docx' | 'xlsx' | 'csv' | 'text'

const FILE_TYPE_MAP: Record<string, ViewerType> = {
  // 图片
  jpg: 'image', jpeg: 'image', png: 'image', gif: 'image',
  webp: 'image', svg: 'image', bmp: 'image', ico: 'image',
  // 文档
  pdf: 'pdf',
  docx: 'docx', doc: 'docx',
  xlsx: 'xlsx', xls: 'xlsx',
  // 表格
  csv: 'csv',
  // 文本
  txt: 'text', log: 'text', md: 'text', json: 'text',
  xml: 'text', yaml: 'text', yml: 'text', toml: 'text',
  ini: 'text', cfg: 'text', conf: 'text',
}

const fileExtension = computed(() => {
  const name = props.fileName || props.src.split('/').pop()?.split('?')[0] || ''
  const parts = name.split('.')
  return parts.length > 1 ? parts[parts.length - 1].toLowerCase() : ''
})

const resolvedType = computed<ViewerType | null>(() => {
  if (props.viewerType) return props.viewerType
  return FILE_TYPE_MAP[fileExtension.value] ?? null
})

const title = computed(() => {
  const typeLabels: Record<string, string> = {
    image: '图片预览', pdf: 'PDF预览', docx: 'Word预览',
    xlsx: 'Excel预览', csv: 'CSV预览', text: '文本预览',
  }
  const label = typeLabels[resolvedType.value ?? ''] || '文件预览'
  return `${label} — ${props.fileName}`
})

// ---------- 数据 ----------

const loading = ref(true)
const error = ref('')
const csvData = ref<Record<string, string>[]>([])
const csvColumns = ref<string[]>([])
const textContent = ref('')
const effectiveSrc = ref<string | ArrayBuffer>('')

// ---------- 初始化 ----------

watch(() => [props.visible, props.src], async ([vis, src]) => {
  if (!vis || !src) return
  loading.value = true
  error.value = ''
  csvData.value = []
  textContent.value = ''

  const type = resolvedType.value

  try {
    // PDF/Word/Excel 组件直接使用 src URL，无需预加载
    if (type === 'pdf' || type === 'docx' || type === 'xlsx') {
      effectiveSrc.value = src as string
      loading.value = false // 子组件自己管理加载状态
      return
    }

    // 图片：设置 src 后等加载事件
    if (type === 'image') {
      effectiveSrc.value = src as string
      // 预加载检测
      const img = new Image()
      img.onload = () => { loading.value = false }
      img.onerror = () => {
        error.value = '图片加载失败，请检查文件格式或网络连接'
        loading.value = false
      }
      img.src = src as string
      return
    }

    // CSV / 文本：fetch 并解析
    const response = await fetch(src as string)
    if (!response.ok) throw new Error(`HTTP ${response.status}`)
    const raw = await response.text()

    if (type === 'csv') {
      parseCSV(raw)
    } else if (type === 'text') {
      textContent.value = raw
    }

    loading.value = false
  } catch (e: any) {
    error.value = e?.message || '文件加载失败'
    loading.value = false
  }
}, { immediate: true })

// ---------- CSV 解析 ----------

function parseCSV(raw: string) {
  const lines = raw.trim().split(/\r?\n/).filter(Boolean)
  if (lines.length === 0) {
    csvData.value = []
    csvColumns.value = []
    return
  }

  // 用第一行当表头
  const headers = parseCSVLine(lines[0])
  csvColumns.value = headers

  const rows: Record<string, string>[] = []
  for (let i = 1; i < lines.length; i++) {
    const cells = parseCSVLine(lines[i])
    const row: Record<string, string> = {}
    headers.forEach((h, idx) => {
      row[h] = cells[idx] ?? ''
    })
    rows.push(row)
  }
  csvData.value = rows
}

function parseCSVLine(line: string): string[] {
  const result: string[] = []
  let current = ''
  let inQuotes = false

  for (const ch of line) {
    if (inQuotes) {
      if (ch === '"') {
        inQuotes = false
      } else {
        current += ch
      }
    } else if (ch === '"') {
      inQuotes = true
    } else if (ch === ',') {
      result.push(current.trim())
      current = ''
    } else {
      current += ch
    }
  }
  result.push(current.trim())
  return result
}

// ---------- 事件 ----------

function onRendered() {
  loading.value = false
}

function onError(err: any) {
  error.value = err?.message || '文档渲染失败'
  loading.value = false
}

function retry() {
  if (props.src) {
    loading.value = true
    error.value = ''
    effectiveSrc.value = props.src as string
  }
}

function downloadFile() {
  if (props.src) {
    const a = document.createElement('a')
    a.href = props.src as string
    a.download = props.fileName || 'download'
    a.target = '_blank'
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
  }
}
</script>

<style scoped>
.file-preview-container {
  min-height: 50vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f5f7fa;
  border-radius: 4px;
  overflow: auto;
}

.file-preview-status {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  color: #909399;
  font-size: 14px;
  padding: 40px;
  text-align: center;
}
.file-preview-status--error {
  color: #f56c6c;
}

.file-preview-image {
  max-width: 100%;
  max-height: 75vh;
  overflow: auto;
  display: flex;
  align-items: center;
  justify-content: center;
}
.file-preview-image img {
  max-width: 100%;
  max-height: 75vh;
  object-fit: contain;
  display: block;
}

.file-preview-text {
  width: 100%;
  max-height: 70vh;
  overflow: auto;
  background: #1e1e1e;
  color: #d4d4d4;
  padding: 16px;
  border-radius: 4px;
  white-space: pre-wrap;
  word-break: break-all;
  font-family: 'Consolas', 'Courier New', monospace;
  font-size: 13px;
  line-height: 1.6;
}

.file-preview-csv {
  width: 100%;
  padding: 8px;
}

.file-preview-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}
.file-preview-footer__name {
  color: #909399;
  font-size: 13px;
  max-width: 60%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
