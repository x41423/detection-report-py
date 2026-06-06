<template>
  <div class="weekly-price-update">
    <PageHeader
      eyebrow="每周报价 / 更新"
      title="每周报价更新"
      description="粘贴客户执行价数据，系统自动匹配报价模板并填入 G 列「江东执行价」。"
      tone="teal"
    />

    <!-- 模板管理（折叠面板） -->
    <el-card shadow="never" class="panel-card">
      <el-collapse v-model="templateCollapse">
        <el-collapse-item title="模板管理" name="template">
          <div class="template-section">
            <div class="template-info">
              <span class="template-label">当前模板：</span>
              <span v-if="templateName" class="template-name">{{ templateName }}</span>
              <span v-else class="template-missing">未上传</span>
            </div>
            <div class="template-actions">
              <el-button size="small" @click="onBrowseTemplate">更换模板</el-button>
              <span v-if="templateName" class="template-status">已上传 ✓</span>
            </div>
          </div>
        </el-collapse-item>
      </el-collapse>
    </el-card>

    <!-- 粘贴输入区 -->
    <el-card shadow="never" class="panel-card">
      <div class="panel-heading">
        <div>
          <div class="panel-heading__eyebrow">第 1 步</div>
          <h2 class="panel-heading__title">导入客户执行价</h2>
        </div>
      </div>

      <!-- Excel 文件导入 -->
      <div class="import-section">
        <el-button type="primary" :loading="workflow.isImporting.value" @click="triggerFileInput">
          选择 Excel 文件
        </el-button>
        <span class="import-hint">支持 .xlsx 格式，A 列菜名、B 列价格</span>
        <input
          ref="fileInputRef"
          type="file"
          accept=".xlsx,.xls,.xlsm"
          style="display: none"
          @change="handleFileSelect"
        />
      </div>

      <el-divider>或手动粘贴</el-divider>

      <div class="paste-row">
        <!-- 菜名输入框 -->
        <div class="paste-col">
          <label class="paste-label">菜名（每行一个）</label>
          <el-input
            v-model="workflow.pasteNames.value"
            type="textarea"
            :rows="8"
            placeholder="土豆&#10;白菜&#10;黄瓜&#10;茄子"
            class="paste-textarea"
            @paste="(e: ClipboardEvent) => workflow.handlePaste(e, 'names')"
          />
        </div>

        <!-- 价格输入框 -->
        <div class="paste-col">
          <label class="paste-label">价格（每行一个）</label>
          <el-input
            v-model="workflow.pastePrices.value"
            type="textarea"
            :rows="8"
            placeholder="2.5&#10;1.8&#10;3.0&#10;4.2"
            class="paste-textarea"
            @paste="(e: ClipboardEvent) => workflow.handlePaste(e, 'prices')"
          />
        </div>
      </div>

      <!-- 校验消息 -->
      <div class="validation-messages">
        <template v-for="(msg, idx) in workflow.validationMessages.value" :key="idx">
          <el-alert
            :title="msg.text"
            :type="msg.type === 'warning' ? 'warning' : msg.type === 'success' ? 'success' : 'info'"
            show-icon
            :closable="false"
            size="small"
            style="margin-bottom: 8px"
          />
        </template>
      </div>

      <!-- 配对状态提示 -->
      <div v-if="workflow.hasValidData.value" class="pairing-status">
        <el-tag :type="workflow.hasMismatch.value ? 'warning' : 'success'" size="small">
          已识别 {{ workflow.validPairCount.value }} 条有效配对
        </el-tag>
        <span v-if="workflow.hasMismatch.value" class="mismatch-hint">
          {{ workflow.mismatchMessage.value }}
        </span>
      </div>

      <!-- 配对预览（可折叠） -->
      <el-collapse v-if="workflow.hasValidData.value" v-model="previewCollapse" class="preview-collapse">
        <el-collapse-item :title="`配对预览（${workflow.validPairCount.value} 条）`" name="preview">
          <!-- 操作按钮 -->
          <div class="preview-actions">
            <el-button 
              size="small" 
              :disabled="workflow.selectedRowIds.value.size < 2"
              @click="workflow.mergeSelectedRows()"
            >
              合并选中行
            </el-button>
            <el-button 
              size="small" 
              :disabled="workflow.selectedRowIds.value.size !== 1"
              @click="workflow.splitSelectedRows()"
            >
              拆分选中行
            </el-button>
            <span class="selection-hint">
              已选择 {{ workflow.selectedRowIds.value.size }} 行
            </span>
          </div>

          <el-table
            :data="workflow.pairingRows.value"
            stripe
            size="small"
            max-height="500"
            class="preview-table"
            @selection-change="handleSelectionChange"
          >
            <el-table-column type="selection" width="40" />
            <el-table-column prop="originalIndex" label="#" width="50" />
            <el-table-column prop="name" label="菜名">
              <template #default="{ row }">
                <span :class="{ 'merged-row': row.mergedWith }">{{ row.name }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="price" label="价格" width="100" />
            <el-table-column label="状态" width="100">
              <template #default="{ row }">
                <el-tag
                  :type="row.status === 'valid' ? 'success' : row.status === 'invalid-price' ? 'danger' : row.status === 'merged-note' ? 'info' : 'warning'"
                  size="small"
                >
                  {{ row.status === 'valid' ? '有效' : row.status === 'invalid-price' ? '格式异常' : row.status === 'merged-note' ? '已合并' : row.status === 'missing-name' ? '缺菜名' : '缺价格' }}
                </el-tag>
              </template>
            </el-table-column>
          </el-table>
        </el-collapse-item>
      </el-collapse>

      <div class="action-cluster">
        <el-button
          :loading="workflow.previewing.value"
          type="primary"
          :disabled="!workflow.hasValidData.value"
          @click="workflow.runPreview()"
        >
          运行预检匹配
        </el-button>
        <el-button @click="workflow.resetForm()">重置</el-button>
      </div>
    </el-card>

    <!-- 预检结果 -->
    <el-card v-if="workflow.previewReady.value" shadow="never" class="panel-card">
      <div class="panel-heading">
        <div>
          <div class="panel-heading__eyebrow">预检结果</div>
          <h2 class="panel-heading__title">{{ workflow.displayState.value.matched_count }} 条匹配 / {{ changedCount }} 条价格变化</h2>
          <p class="panel-heading__description">
            待写入更新数：{{ workflow.displayState.value.updated_count }}；未匹配：{{ workflow.displayState.value.not_matched_unique_count }} 条；
            别名命中：{{ workflow.displayState.value.alias_hit_count }} 条。
          </p>
        </div>
      </div>

      <el-tabs v-model="workflow.activeDetailTab.value" class="weekly-price-tabs">
        <el-tab-pane label="匹配明细" name="matched">
          <el-table :data="workflow.displayState.value.matched_items" stripe size="small" max-height="320">
            <el-table-column prop="name" label="菜名" />
            <el-table-column prop="old_price" label="旧价" width="100" :formatter="(row: any) => workflow.formatPrice(row.old_price)" />
            <el-table-column prop="new_price" label="新价" width="100" :formatter="(row: any) => workflow.formatPrice(row.new_price)" />
            <el-table-column label="变化" width="80">
              <template #default="{ row }">
                <el-tag v-if="row.changed" type="warning" size="small">变化</el-tag>
                <el-tag v-else type="info" size="small">不变</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="match_type" label="匹配方式" width="100" />
          </el-table>
        </el-tab-pane>

        <el-tab-pane :label="`未匹配 (${unmatchedDetailRows.length})`" name="unmatched">
          <el-table :data="unmatchedDetailRows" stripe size="small" max-height="320">
            <el-table-column prop="name" label="菜名" />
            <el-table-column label="状态" width="120">
              <template #default="{ row }">
                <el-tag :type="row.statusType" size="small">{{ row.statusLabel }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="suggestionText" label="建议候选" />
          </el-table>

          <div v-if="actionableSuggestionRows.length" class="suggestion-board">
            <h3>候选确认 ({{ selectedSuggestionCount }} / {{ actionableSuggestionRows.length }})</h3>
            <p>已选择 {{ selectedSuggestionCount }} 条映射。保存后会写入别名库并自动重新预检。</p>
            <el-table :data="actionableSuggestionRows" stripe size="small" max-height="280">
              <el-table-column prop="source_name" label="客户菜名" />
              <el-table-column label="选择参考菜名" width="240">
                <template #default="{ row }">
                  <el-select
                    :model-value="suggestionSelections[row.source_name]"
                    placeholder="忽略"
                    clearable
                    size="small"
                    @update:model-value="updateSuggestionSelection(row.source_name, $event)"
                  >
                    <el-option v-for="candidate in row.candidates" :key="candidate.target_name" :label="`${candidate.target_name}（${workflow.formatScore(candidate.score)}）`" :value="candidate.target_name" />
                  </el-select>
                </template>
              </el-table-column>
              <el-table-column label="忽略" width="90">
                <template #default="{ row }">
                  <el-switch :model-value="isIgnored(row.source_name)" @change="toggleIgnore(row.source_name)" />
                </template>
              </el-table-column>
            </el-table>
            <div class="action-cluster">
              <el-button type="success" :disabled="!hasSavableMappings" :loading="savingAliases" @click="saveSelectedAliasesAndRepreview">保存映射并重新预检</el-button>
              <el-button text @click="openAliasLibrary()">打开别名库</el-button>
            </div>
          </div>
        </el-tab-pane>
      </el-tabs>

      <div v-if="previewWarnings.length" class="warning-bar">
        <el-alert v-for="(warning, idx) in previewWarnings" :key="idx" :title="warning" type="warning" show-icon :closable="false" />
      </div>

      <div class="action-cluster">
        <el-button type="primary" size="large" :loading="executing" :disabled="!previewReady" @click="runUpdate">执行更新并下载结果</el-button>
        <el-button v-if="outputPath" text @click="copyOutputPath">已下载：{{ outputPath }}</el-button>
      </div>
    </el-card>

    <StatusLog ref="statusLogRef" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import PageHeader from '../../../components/PageHeader.vue'
import StatusLog from '../../../components/StatusLog.vue'
import { useWeeklyPriceUpdateWorkflow } from '../composables/useWeeklyPriceUpdateWorkflow'
import { listTemplates, uploadTemplateFromPath } from '../../../api/weekly-price'
import type { StatusLogHandle } from '../../shared/workflow'
import { useDirBrowserApi } from '../../shared/dirBrowser'

const { openFile } = useDirBrowserApi()
const statusLogRef = ref<StatusLogHandle>()

const workflow = useWeeklyPriceUpdateWorkflow(statusLogRef)

// 模板状态
const templateName = ref('')
const templateCollapse = ref<string[]>([])
const previewCollapse = ref<string[]>([])

// 从 workflow 中解构需要的属性
const { 
  previewReady, 
  previewWarnings, 
  outputPath, 
  executing, 
  savingAliases,
  selectedSuggestionCount,
  hasSavableMappings,
  previewing,
  activeDetailTab,
  suggestionSelections,
  previewData,
  displayState,
} = workflow

// 计算属性
const changedCount = computed(() => displayState.value.matched_items.filter((item: any) => item.changed).length)
const unmatchedDetailRows = computed(() => workflow.unmatchedDetailRows.value)
const actionableSuggestionRows = computed(() => workflow.actionableSuggestionRows.value)

// 模板管理
onMounted(async () => {
  try {
    const { data } = await listTemplates()
    if (data.templates.update) {
      templateName.value = data.templates.update.name
    }
  } catch { /* ignore */ }
})

async function onBrowseTemplate() {
  const selected = await openFile('wp:template', '', {
    title: '选择报价模板',
    extensions: ['.xlsx', '.xlsm', '.xls'],
  })
  if (selected) {
    try {
      await uploadTemplateFromPath('update', selected)
      const name = selected.split(/[/\\]/).pop() || selected
      templateName.value = name
      ElMessage.success('模板已上传')
    } catch {
      ElMessage.error('模板上传失败')
    }
  }
}

// Excel 文件导入
const fileInputRef = ref<HTMLInputElement>()

function triggerFileInput() {
  fileInputRef.value?.click()
}

function handleFileSelect(event: Event) {
  workflow.handleFileChange(event)
}

// 处理表格选择变化
function handleSelectionChange(selection: any[]) {
  const newSet = new Set(selection.map((row: any) => row.id));
  workflow.selectedRowIds.value = newSet;
}

// 预检结果操作
function updateSuggestionSelection(sourceName: string, targetName: string | undefined) {
  workflow.updateSuggestionSelection(sourceName, targetName)
}

function isIgnored(sourceName: string) {
  return workflow.isIgnored(sourceName)
}

function toggleIgnore(sourceName: string) {
  workflow.toggleIgnore(sourceName)
}

function openAliasLibrary() {
  workflow.openAliasLibrary()
}

async function saveSelectedAliasesAndRepreview() {
  await workflow.saveSelectedAliasesAndRepreview()
}

async function runUpdate() {
  await workflow.runUpdate()
}

async function copyOutputPath() {
  try {
    await navigator.clipboard.writeText(outputPath.value)
    ElMessage.success('已复制到剪贴板')
  } catch {
    ElMessage.info('请手动复制：' + outputPath.value)
  }
}
</script>

<style scoped>
.weekly-price-update { display: grid; gap: 22px; }
.panel-card { border-radius: 22px; padding: 22px 24px; background: rgba(255,255,255,0.78); border: 1px solid rgba(255,255,255,0.6); backdrop-filter: blur(20px) saturate(155%); }
.panel-heading { margin-bottom: 14px; }
.panel-heading__eyebrow { font-size: 12px; letter-spacing: 0.12em; text-transform: uppercase; color: var(--el-color-primary); }
.panel-heading__title { margin: 4px 0 6px; font-size: 20px; font-weight: 600; }
.panel-heading__description { margin: 0; font-size: 13px; opacity: 0.8; }

/* 模板管理 */
.template-section { display: flex; align-items: center; justify-content: space-between; padding: 12px 0; }
.template-info { display: flex; align-items: center; gap: 8px; }
.template-label { font-size: 13px; color: var(--el-text-color-secondary); }
.template-name { font-weight: 600; color: var(--el-text-color-primary); }
.template-missing { color: var(--el-color-warning); font-style: italic; }
.template-actions { display: flex; align-items: center; gap: 8px; }
.template-status { font-size: 12px; color: var(--el-color-success); }

/* 粘贴输入区 */
.import-section { display: flex; align-items: center; gap: 12px; margin-bottom: 16px; }
.import-hint { font-size: 12px; color: var(--el-text-color-secondary); }
.paste-row { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px; margin-bottom: 14px; }
.paste-col { display: flex; flex-direction: column; gap: 6px; }
.paste-label { font-size: 13px; font-weight: 600; color: var(--el-text-color-regular); }
.paste-textarea :deep(textarea) { font-family: 'Courier New', monospace; font-size: 14px; line-height: 1.6; resize: vertical; }

/* 校验消息 */
.validation-messages { margin-bottom: 12px; }

/* 配对状态 */
.pairing-status { display: flex; align-items: center; gap: 12px; margin-bottom: 14px; }
.mismatch-hint { font-size: 12px; color: var(--el-color-warning); }

/* 配对预览 */
.preview-collapse { margin-bottom: 14px; }
.preview-table { margin-top: 8px; }
.preview-more { text-align: center; padding: 8px; font-size: 12px; color: var(--el-text-color-secondary); }
.preview-actions { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
.selection-hint { font-size: 12px; color: var(--el-text-color-secondary); }
.merged-row { font-weight: 600; color: var(--el-color-primary); }

/* 操作按钮 */
.action-cluster { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 14px; }

/* 预检结果 */
.weekly-price-tabs { margin-top: 6px; }
.suggestion-board { margin-top: 18px; padding: 14px 16px; border-radius: 16px; background: rgba(56,189,248,0.08); border: 1px solid rgba(56,189,248,0.32); }
.suggestion-board h3 { margin: 0 0 4px; font-size: 16px; font-weight: 600; }
.suggestion-board p { margin: 0 0 10px; font-size: 13px; opacity: 0.78; }
.warning-bar { display: grid; gap: 8px; margin-top: 16px; }

@media (max-width: 720px) { .paste-row { grid-template-columns: minmax(0, 1fr); } }
</style>
