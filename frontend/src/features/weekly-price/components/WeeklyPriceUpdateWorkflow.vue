<template>
  <div class="weekly-price-update">
    <PageHeader
      eyebrow="每周报价 / 更新"
      title="每周报价更新"
      description="上传待更新的报价表与参考报价表，预检后再写入新价格，全程不改原文件。"
      tone="teal"
    />

    <el-card shadow="never" class="panel-card">
      <div class="panel-heading">
        <div>
          <div class="panel-heading__eyebrow">第 1 步</div>
          <h2 class="panel-heading__title">选择待更新报价表</h2>
          <p class="panel-heading__description">
            上传客户最新报价表（待更新）和参考报价表（带新价格），系统会自动匹配菜名后写入新价格。
          </p>
        </div>
      </div>

      <div class="upload-row">
        <div class="upload-tile">
          <div class="upload-tile__label">待更新报价表</div>
          <el-button @click="triggerUpdatePicker">
            选择文件
          </el-button>
          <span class="upload-tile__filename">{{ updateFile?.name || '尚未选择' }}</span>
          <input
            ref="updateInputRef"
            type="file"
            accept=".xlsx,.xlsm,.xls"
            style="display: none"
            @change="handleUpdateFileChange"
          />
        </div>

        <div class="upload-tile">
          <div class="upload-tile__label">参考报价表</div>
          <el-button @click="triggerReferencePicker">
            选择文件
          </el-button>
          <span class="upload-tile__filename">{{ referenceFile?.name || '尚未选择' }}</span>
          <input
            ref="referenceInputRef"
            type="file"
            accept=".xlsx,.xlsm,.xls"
            style="display: none"
            @change="handleReferenceFileChange"
          />
        </div>
      </div>

      <p class="status-note">{{ previewStatusNote }}</p>

      <div class="action-cluster">
        <el-button :loading="previewing" type="primary" @click="runPreview">
          运行预检
        </el-button>
        <el-button @click="resetForm">重置</el-button>
      </div>
    </el-card>

    <el-card v-if="previewReady" shadow="never" class="panel-card">
      <div class="panel-heading">
        <div>
          <div class="panel-heading__eyebrow">预检结果</div>
          <h2 class="panel-heading__title">{{ displayState.matched_count }} 条匹配 / {{ changedCount }} 条价格变化</h2>
          <p class="panel-heading__description">
            待写入更新数：{{ displayState.updated_count }}；未匹配：{{ displayState.not_matched_unique_count }} 条；
            别名命中：{{ displayState.alias_hit_count }} 条。
          </p>
        </div>
      </div>

      <el-tabs v-model="activeDetailTab" class="weekly-price-tabs">
        <el-tab-pane label="匹配明细" name="matched">
          <el-table :data="displayState.matched_items" stripe size="small" max-height="320">
            <el-table-column prop="name" label="菜名" />
            <el-table-column prop="old_price" label="旧价" width="100" :formatter="(row: any) => formatPrice(row.old_price)" />
            <el-table-column prop="new_price" label="新价" width="100" :formatter="(row: any) => formatPrice(row.new_price)" />
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
                    <el-option
                      v-for="candidate in row.candidates"
                      :key="candidate.target_name"
                      :label="`${candidate.target_name}（${formatScore(candidate.score)}）`"
                      :value="candidate.target_name"
                    />
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
              <el-button
                type="success"
                :disabled="!hasSavableMappings"
                :loading="savingAliases"
                @click="saveSelectedAliasesAndRepreview"
              >
                保存映射并重新预检
              </el-button>
              <el-button text @click="openAliasLibrary()">
                打开别名库
              </el-button>
            </div>
          </div>
        </el-tab-pane>
      </el-tabs>

      <div v-if="previewWarnings.length" class="warning-bar">
        <el-alert
          v-for="(warning, idx) in previewWarnings"
          :key="idx"
          :title="warning"
          type="warning"
          show-icon
          :closable="false"
        />
      </div>

      <div class="action-cluster">
        <el-button
          type="primary"
          size="large"
          :loading="executing"
          :disabled="!previewReady"
          @click="runUpdate"
        >
          执行更新并下载结果
        </el-button>
        <el-button v-if="outputPath" text @click="copyOutputPath">
          已下载：{{ outputPath }}
        </el-button>
      </div>
    </el-card>

    <StatusLog ref="statusLogRef" />
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'

import PageHeader from '../../../components/PageHeader.vue'
import StatusLog from '../../../components/StatusLog.vue'
import { useWeeklyPriceUpdateWorkflow } from '../composables/useWeeklyPriceUpdateWorkflow'
import type { StatusLogHandle } from '../../shared/workflow'

const statusLogRef = ref<StatusLogHandle>()
const updateInputRef = ref<HTMLInputElement>()
const referenceInputRef = ref<HTMLInputElement>()

const {
  actionableSuggestionRows,
  activeDetailTab,
  changedCount,
  displayState,
  executing,
  formatPrice,
  formatScore,
  hasSavableMappings,
  isIgnored,
  openAliasLibrary,
  outputPath,
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
  toggleIgnore,
  unmatchedDetailRows,
  updateFile,
  updateSuggestionSelection,
} = useWeeklyPriceUpdateWorkflow(statusLogRef)

function triggerUpdatePicker() {
  updateInputRef.value?.click()
}

function triggerReferencePicker() {
  referenceInputRef.value?.click()
}

function handleUpdateFileChange(event: Event) {
  const input = event.target as HTMLInputElement
  setUpdateFile(input.files)
  input.value = ''
}

function handleReferenceFileChange(event: Event) {
  const input = event.target as HTMLInputElement
  setReferenceFile(input.files)
  input.value = ''
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
.weekly-price-update {
  display: grid;
  gap: 22px;
}

.panel-card {
  border-radius: 22px;
  padding: 22px 24px;
  background: rgba(255, 255, 255, 0.78);
  border: 1px solid rgba(255, 255, 255, 0.6);
  backdrop-filter: blur(20px) saturate(155%);
}

.panel-heading {
  margin-bottom: 14px;
}

.panel-heading__eyebrow {
  font-size: 12px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--el-color-primary);
}

.panel-heading__title {
  margin: 4px 0 6px;
  font-size: 20px;
  font-weight: 600;
}

.panel-heading__description {
  margin: 0;
  font-size: 13px;
  opacity: 0.8;
}

.upload-row {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
  margin-bottom: 14px;
}

@media (max-width: 720px) {
  .upload-row {
    grid-template-columns: minmax(0, 1fr);
  }
}

.upload-tile {
  display: grid;
  gap: 8px;
  padding: 16px 18px;
  border-radius: 18px;
  border: 1px dashed rgba(56, 189, 248, 0.45);
  background: rgba(255, 255, 255, 0.55);
}

.upload-tile__label {
  font-size: 13px;
  font-weight: 600;
}

.upload-tile__filename {
  font-size: 12px;
  opacity: 0.72;
  word-break: break-all;
}

.status-note {
  margin: 0 0 14px;
  font-size: 13px;
  opacity: 0.78;
}

.action-cluster {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 14px;
}

.weekly-price-tabs {
  margin-top: 6px;
}

.suggestion-board {
  margin-top: 18px;
  padding: 14px 16px;
  border-radius: 16px;
  background: rgba(56, 189, 248, 0.08);
  border: 1px solid rgba(56, 189, 248, 0.32);
}

.suggestion-board h3 {
  margin: 0 0 4px;
  font-size: 16px;
  font-weight: 600;
}

.suggestion-board p {
  margin: 0 0 10px;
  font-size: 13px;
  opacity: 0.78;
}

.warning-bar {
  display: grid;
  gap: 8px;
  margin-top: 16px;
}
</style>
