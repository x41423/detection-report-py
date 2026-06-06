<template>
  <div class="page-shell">
    <PageHeader eyebrow="农残检测" title="生成检测报告" tone="green">
      <template #aside>
        <div class="hero-metric-grid">
          <div class="hero-metric">
            <span class="hero-metric__label">检测日期</span>
            <span class="hero-metric__value">{{ workflow.formatHeroDate.value }}</span>
            <span class="hero-metric__note">需在执行前确认</span>
          </div>
          <div class="hero-metric">
            <span class="hero-metric__label">已就绪</span>
            <span class="hero-metric__value">{{ workflow.fileReadyCount.value }} / 2</span>
            <span class="hero-metric__note">大表与小表</span>
          </div>
          <div class="hero-metric">
            <span class="hero-metric__label">JSON 条目</span>
            <span class="hero-metric__value">{{ workflow.dataCount.value }}</span>
            <span class="hero-metric__note">将写入检测结果</span>
          </div>
          <div class="hero-metric">
            <span class="hero-metric__label">最近结果</span>
            <span class="hero-metric__value">{{ workflow.lastRunMessage.value ? '已完成' : '—' }}</span>
            <span class="hero-metric__note">{{ workflow.lastRunMessage.value || '尚未执行' }}</span>
          </div>
        </div>
      </template>
    </PageHeader>

    <el-tabs :model-value="workflow.activeTab.value" @update:model-value="onTabChange">
      <!-- ====== Tab 1: 单次检测（两栏布局） ====== -->
      <el-tab-pane label="单次检测" name="single">
        <div class="workbench-grid">
          <!-- 左栏：检测参数 + 文件来源 -->
          <div class="panel-stack panel-stack--rail">
            <!-- 检测参数 -->
            <el-card shadow="never" class="panel-card">
              <div class="panel-heading">
                <div>
                  <div class="panel-heading__eyebrow">检测配置</div>
                  <h2 class="panel-heading__title">检测参数</h2>
                </div>
              </div>
              <el-form label-position="top">
                <div class="field-grid two-up">
                  <el-form-item label="检测日期">
                    <el-date-picker
                      v-model="workflow.detectDate.value"
                      type="date"
                      value-format="YYYY-MM-DD"
                      :clearable="false"
                    />
                  </el-form-item>
                  <el-form-item label="执行人">
                    <el-input v-model="workflow.inspectorName.value" placeholder="输入执行人姓名" />
                  </el-form-item>
                </div>
              </el-form>
            </el-card>

            <!-- 文件来源（统一面板） -->
            <FileSourcePanel
              :modes="singleModes"
              :model-value="workflow.usePathMode.value ? 'path-lock' : 'upload'"
              path-lock-value="path-lock"
              :slots="singleFileSlots"
              :paths="singleFilePaths"
              :locked-files="singleLockedFiles"
              :path-locked="workflow.pathLocked.value"
              :locking="workflow.findingFiles.value"
              :lock-message="workflow.findFilesMessage.value"
              :lock-label="'查找目标文件'"
              :can-lock="!!workflow.bigPath.value && !!workflow.smallPath.value"
              :show-output-dir="workflow.usePathMode.value"
              :output-dir="workflow.outputDir.value"
              @update:model-value="onSingleModeChange"
              @browse="onSingleBrowse"
              @lock="workflow.onFindFiles"
              @browse-output="workflow.onBrowseOutputDir()"
            >
              <template #template-actions>
                <el-divider />
                <el-collapse>
                  <el-collapse-item title="模板管理（保存常用模板，可选）">
                    <div class="field-grid two-up">
                      <div style="display: flex; flex-direction: column; gap: 8px">
                        <span class="soft-note" style="font-weight: 600">大表模板</span>
                        <template v-if="workflow.templateStatus.value?.big_template.configured">
                          <el-tag type="success" size="small">已保存</el-tag>
                          <span style="font-size: 13px">{{ workflow.templateStatus.value.big_template.filename }}</span>
                        </template>
                        <span v-else class="soft-note">尚未保存</span>
                        <div style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap">
                          <el-button size="small" @click="workflow.onBrowseTemplate('big')">浏览</el-button>
                          <el-button size="small" type="primary" :loading="workflow.savingTemplate.value === 'big'" :disabled="!workflow.pendingTemplatePath.value.big" @click="workflow.onSaveTemplatePath('big')">保存模板</el-button>
                          <span v-if="workflow.pendingTemplatePath.value.big" class="soft-note" style="font-size: 12px">{{ workflow.pendingTemplatePath.value.big }}</span>
                        </div>
                      </div>
                      <div style="display: flex; flex-direction: column; gap: 8px">
                        <span class="soft-note" style="font-weight: 600">小表模板</span>
                        <template v-if="workflow.templateStatus.value?.small_template.configured">
                          <el-tag type="success" size="small">已保存</el-tag>
                          <span style="font-size: 13px">{{ workflow.templateStatus.value.small_template.filename }}</span>
                        </template>
                        <span v-else class="soft-note">尚未保存</span>
                        <div style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap">
                          <el-button size="small" @click="workflow.onBrowseTemplate('small')">浏览</el-button>
                          <el-button size="small" type="primary" :loading="workflow.savingTemplate.value === 'small'" :disabled="!workflow.pendingTemplatePath.value.small" @click="workflow.onSaveTemplatePath('small')">保存模板</el-button>
                          <span v-if="workflow.pendingTemplatePath.value.small" class="soft-note" style="font-size: 12px">{{ workflow.pendingTemplatePath.value.small }}</span>
                        </div>
                      </div>
                    </div>
                  </el-collapse-item>
                </el-collapse>
              </template>
            </FileSourcePanel>
          </div>

          <!-- 右栏：JSON编辑器 + 执行 -->
          <div class="panel-stack">
            <!-- 菜名 / JSON 编辑器 -->
            <el-card shadow="never" class="panel-card">
              <div class="panel-heading">
                <div>
                  <div class="panel-heading__eyebrow">菜名 / JSON</div>
                  <h2 class="panel-heading__title">生成抑制率 JSON</h2>
                </div>
              </div>

              <el-form label-position="top">
                <el-form-item label="菜名（一行一个，或用逗号分隔）">
                  <el-input
                    v-model="workflow.vegText.value"
                    type="textarea"
                    :rows="4"
                    placeholder="青椒&#10;蘑菇&#10;..."
                  />
                  <div class="action-cluster">
                    <el-button type="primary" :icon="Setting" @click="workflow.onGenerateRates">
                      生成抑制率
                    </el-button>
                    <el-button @click="workflow.onClearVeg">清空</el-button>
                    <span class="soft-note">{{ workflow.vegStatus.value }}</span>
                  </div>
                </el-form-item>

                <el-form-item label="JSON（可手动编辑）">
                  <el-input
                    v-model="workflow.jsonText.value"
                    type="textarea"
                    :rows="6"
                    placeholder="生成后的 JSON 会显示在这里"
                  />
                  <div class="action-cluster">
                    <el-button @click="workflow.onFormatJson">格式化</el-button>
                    <el-button @click="workflow.onDedupJson">去重</el-button>
                    <el-button @click="workflow.onClearJson">清空</el-button>
                    <span class="soft-note">{{ workflow.jsonStatus.value }}</span>
                  </div>
                </el-form-item>
              </el-form>
            </el-card>

            <!-- 执行 -->
            <el-card shadow="never" class="panel-card">
              <div class="panel-heading">
                <div>
                  <div class="panel-heading__eyebrow">执行</div>
                  <h2 class="panel-heading__title">生成检测报告并下载</h2>
                </div>
              </div>
              <el-button
                type="primary"
                size="large"
                :loading="workflow.executing.value"
                :disabled="!canExecute"
                @click="workflow.onExecute"
              >
                执行并下载
              </el-button>
              <div v-if="workflow.lastRunMessage.value" class="soft-note" style="margin-top: 12px">
                {{ workflow.lastRunMessage.value }}
              </div>
            </el-card>
          </div>
        </div>
      </el-tab-pane>

      <!-- ====== Tab 2: 月度批量 ====== -->
      <el-tab-pane label="月度批量" name="monthly-upload">
        <!-- 选择参数 -->
        <el-card shadow="never" class="panel-card">
          <div class="panel-heading">
            <div>
              <div class="panel-heading__eyebrow">月度批量</div>
              <h2 class="panel-heading__title">批量生成全月检测报告</h2>
            </div>
          </div>
          <el-form label-position="top">
            <div class="field-grid two-up">
              <el-form-item label="目标月份">
                <el-date-picker
                  v-model="workflow.month.value"
                  type="month"
                  value-format="YYYY-MM"
                  :clearable="false"
                  placeholder="选择月份"
                />
              </el-form-item>
              <el-form-item label="执行人">
                <el-input v-model="workflow.inspectorName.value" placeholder="输入执行人姓名" />
              </el-form-item>
            </div>
          </el-form>
        </el-card>

        <!-- 文件来源（统一面板） -->
        <FileSourcePanel
          heading="模板来源"
          :modes="monthlyModes"
          :model-value="workflow.monthlyTemplateMode.value"
          path-lock-value="path"
          :slots="monthlySlots"
          :paths="monthlyPaths"
          :locked-files="monthlyLockedFiles"
          :path-locked="workflow.monthlyPathLocked.value"
          :locking="workflow.monthlyFindingFiles.value"
          :lock-message="workflow.monthlyFindFilesMessage.value"
          :lock-label="'锁定模板路径'"
          :can-lock="!!workflow.monthlyBigPath.value && !!workflow.monthlySmallPath.value"
          :show-output-dir="true"
          :output-dir="workflow.monthlyOutputDir.value"
          @update:model-value="(v: string) => workflow.monthlyTemplateMode.value = v as 'upload' | 'path'"
          @browse="onMonthlyBrowse"
          @lock="workflow.onMonthlyFindFiles"
          @browse-output="workflow.onBrowseOutputDir()"
        >
          <template #before-slots>
            <el-form-item v-if="workflow.monthlyTemplateMode.value === 'upload'" label="模板方式">
              <el-radio-group :model-value="workflow.monthUseSavedTemplates.value" @change="onMonthTemplateModeChange">
                <el-radio :value="true">使用已保存模板</el-radio>
                <el-radio :value="false">浏览临时模板</el-radio>
              </el-radio-group>
            </el-form-item>
          </template>
        </FileSourcePanel>

        <!-- 每日清单 + 解析 + 执行 -->
        <el-card shadow="never" class="panel-card">
          <el-form label-position="top">
            <el-form-item label="每日清单（文本或上传 Excel / TXT）">
              <el-input
                v-model="workflow.monthListText.value"
                type="textarea"
                :rows="6"
                placeholder="格式：每行一条，日期在前，品种用逗号或空格分隔&#10;示例：&#10;4月1日 青椒 蘑菇 番茄&#10;4月2日 黄瓜 白菜 萝卜&#10;&#10;或直接上传 Excel 文件（第一行为日期，每列一天）"
              />
              <div class="action-cluster">
                <el-button @click="workflow.onBrowseMonthListFile()">浏览清单文件</el-button>
                <el-button v-if="workflow.monthListPath.value" type="success" @click="workflow.onConfirmMonthListPath()">确定路径</el-button>
                <el-button v-if="workflow.monthListPath.value" @click="workflow.onOpenMonthListFile()">打开文件</el-button>
                <span v-if="workflow.monthListPath.value" class="soft-note">
                  {{ workflow.monthListPath.value }}
                </span>
              </div>
            </el-form-item>

            <el-form-item>
              <el-button
                type="primary"
                :loading="workflow.monthParsing.value"
                @click="workflow.onParseMonthlyList"
              >
                解析清单
              </el-button>
            </el-form-item>

            <!-- 共享：解析结果预览（带日期选择） -->
            <el-form-item v-if="workflow.monthEntries.value.length > 0" label="解析结果预览">
              <div style="margin-bottom: 8px; display: flex; align-items: center; gap: 12px">
                <el-button size="small" @click="workflow.toggleAllDates">
                  {{ workflow.allDatesSelected.value ? '取消全选' : '全选' }}
                </el-button>
                <span class="soft-note">已选 {{ workflow.monthSelectedDates.value.size }} / {{ workflow.monthEntries.value.length }} 天，共 {{ workflow.monthSelectedCount.value }} 个品种</span>
              </div>
              <el-table :data="workflow.monthEntries.value" size="small" max-height="300" stripe>
                <el-table-column width="40">
                  <template #default="{ row }">
                    <el-checkbox
                      :model-value="workflow.monthSelectedDates.value.has((row as { date: string }).date)"
                      @change="workflow.toggleDate((row as { date: string }).date)"
                    />
                  </template>
                </el-table-column>
                <el-table-column type="index" label="#" width="45" />
                <el-table-column prop="date" label="日期" width="120" />
                <el-table-column label="品种列表">
                  <template #default="{ row }">
                    {{ (row as { names: string[] }).names.join('、') }}
                  </template>
                </el-table-column>
                <el-table-column label="品种数" width="70" align="center">
                  <template #default="{ row }">
                    {{ (row as { names: string[] }).names.length }}
                  </template>
                </el-table-column>
              </el-table>
              <div v-if="workflow.monthListErrors.value.length > 0" style="margin-top: 8px">
                <el-alert
                  v-for="(err, i) in workflow.monthListErrors.value"
                  :key="i"
                  type="warning"
                  :title="`第 ${err.line} 行: ${err.message}`"
                  :closable="false"
                  style="margin-bottom: 4px"
                />
              </div>
            </el-form-item>

            <!-- 执行按钮 -->
            <el-form-item>
              <el-button
                type="primary"
                size="large"
                :loading="workflow.monthExecuting.value"
                :disabled="workflow.monthSelectedDates.value.size === 0"
                @click="workflow.onExecuteMonthly"
              >
                批量执行
              </el-button>
              <div v-if="workflow.monthResult.value" class="soft-note" style="margin-top: 12px">
                {{ workflow.monthResult.value }}
              </div>
            </el-form-item>
          </el-form>
        </el-card>
      </el-tab-pane>
    </el-tabs>

    <StatusLog ref="statusLogRef" />
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { Setting } from '@element-plus/icons-vue'
import type { UploadRawFile } from 'element-plus'
import PageHeader from '../components/PageHeader.vue'
import StatusLog from '../components/StatusLog.vue'
import { usePesticideWorkflow } from '../features/pesticide/composables/usePesticideWorkflow'
import { useDirBrowserApi } from '../features/shared/dirBrowser'
import FileSourcePanel from '../components/FileSourcePanel.vue'

const statusLogRef = ref<InstanceType<typeof StatusLog>>()
const { openFile } = useDirBrowserApi()
const workflow = usePesticideWorkflow(statusLogRef)
const monthTemplateNames = ref<{ big: string; small: string }>({ big: '', small: '' })

const canExecute = computed(() => {
  if (workflow.usePathMode.value) {
    return workflow.pathLocked.value && workflow.dataCount.value > 0
  }
  return workflow.fileReadyCount.value >= 2 && workflow.dataCount.value > 0
})

// FileSourcePanel integration
const singleModes = [
  { value: 'upload', label: '文件选择' },
  { value: 'path-lock', label: '路径锁定' },
]
const singleFileSlots = [
  { key: 'big', label: '大表 (.docx)' },
  { key: 'small', label: '小表 (.docx)' },
]
const singleFilePaths = computed<Record<string, string>>(() => ({
  big: workflow.bigPath.value || '',
  small: workflow.smallPath.value || '',
}))
const singleLockedFiles = computed(() => [
  { key: 'big', label: '大表', path: workflow.foundFileBig.value },
  { key: 'small', label: '小表', path: workflow.foundFileSmall.value },
])

function onSingleModeChange(v: string) {
  workflow.onSwitchMode(v === 'path-lock')
}

async function onSingleBrowse(key: string) {
  if (workflow.usePathMode.value) {
    workflow.onBrowsePath(key as 'big' | 'small')
  } else {
    await onBrowseFile(key as 'big' | 'small')
  }
}

// Monthly FileSourcePanel integration
const monthlyModes = [
  { value: 'upload', label: '使用已保存 / 临时模板' },
  { value: 'path', label: '路径锁定' },
]
const monthlyFileSlots = [
  { key: 'big', label: '大表模板' },
  { key: 'small', label: '小表模板' },
]
const monthlySlots = computed(() => {
  if (workflow.monthlyTemplateMode.value !== 'upload') return monthlyFileSlots
  if (workflow.monthUseSavedTemplates.value) return []
  return monthlyFileSlots
})
const monthlyPaths = computed<Record<string, string>>(() => ({
  big: workflow.monthlyTemplateMode.value === 'path'
    ? workflow.monthlyBigPath.value || ''
    : workflow.pendingTemplatePath.value.big || '',
  small: workflow.monthlyTemplateMode.value === 'path'
    ? workflow.monthlySmallPath.value || ''
    : workflow.pendingTemplatePath.value.small || '',
}))
const monthlyLockedFiles = computed(() => [
  { key: 'big', label: '大表模板', path: workflow.monthlyFoundBig.value },
  { key: 'small', label: '小表模板', path: workflow.monthlyFoundSmall.value },
])

function onMonthlyBrowse(key: string) {
  if (workflow.monthlyTemplateMode.value === 'path') {
    workflow.onMonthlyBrowsePath(key as 'big' | 'small')
  } else {
    workflow.onBrowseTemplate(key as 'big' | 'small')
  }
}

function onTabChange(val: string) {
  workflow.onSetTab(val as 'single' | 'monthly-upload')
}

function onMonthTemplateModeChange(val: string | number | boolean) {
  workflow.monthUseSavedTemplates.value = Boolean(val)
  if (workflow.monthUseSavedTemplates.value) {
    workflow.monthBigTemplateFile.value = null
    workflow.monthSmallTemplateFile.value = null
    monthTemplateNames.value = { big: '', small: '' }
  }
}

function onFileChange(kind: 'big' | 'small', file: UploadRawFile) {
  const raw = (file as unknown as { raw?: File }).raw ?? (file as unknown as File)
  workflow.setFile(kind, [raw])
}

async function onBrowseFile(kind: 'big' | 'small') {
  const initialPath = kind === 'big' ? workflow.bigPath.value : workflow.smallPath.value
  const selected = await openFile(`pest:single:${kind}-file`, initialPath, {
    title: `选择${kind === 'big' ? '大表' : '小表'}文件`,
    extensions: ['.docx', '.doc'],
  })
  if (selected) {
    if (kind === 'big') {
      workflow.bigPath.value = selected
    } else {
      workflow.smallPath.value = selected
    }
    workflow.pathLocked.value = false
    workflow.foundFileBig.value = ''
    workflow.foundFileSmall.value = ''
    workflow.findFilesMessage.value = ''
    // Auto-switch to path mode when browsing files
    if (!workflow.usePathMode.value) {
      workflow.onSwitchMode(true)
    }
  }
}

function onTemplateChange(kind: 'big' | 'small', file: UploadRawFile) {
  const raw = (file as unknown as { raw?: File }).raw ?? (file as unknown as File)
  workflow.onUploadTemplate(kind, raw)
}

function onMonthFileChange(file: UploadRawFile) {
  const raw = (file as unknown as { raw?: File }).raw ?? (file as unknown as File)
  workflow.monthListFile.value = raw
}

function onMonthTemplateChange(kind: 'big' | 'small', file: UploadRawFile) {
  const raw = (file as unknown as { raw?: File }).raw ?? (file as unknown as File)
  if (kind === 'big') {
    workflow.monthBigTemplateFile.value = raw
    monthTemplateNames.value.big = raw.name
  } else {
    workflow.monthSmallTemplateFile.value = raw
    monthTemplateNames.value.small = raw.name
  }
}
</script>
