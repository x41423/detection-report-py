<template>
  <div class="page-shell">
    <PageHeader
      eyebrow="数据迁移"
      title="上传大表，生成并下载小表"
      tone="sun"
    >
      <template #actions>
        <el-radio-group v-model="workflowMode" size="small">
          <el-radio-button value="single">单次处理</el-radio-button>
          <el-radio-button value="monthly">月度批量</el-radio-button>
        </el-radio-group>
        <span class="accent-tag">大表 {{ detectedFiles.length }} 份</span>
        <span class="accent-tag muted-tag">待写入 {{ selectedVegNames.length }} 个菜名</span>
      </template>

      <template #aside>
        <div class="hero-metric-grid">
          <div class="hero-metric">
            <span class="hero-metric__label">模板类型</span>
            <span class="hero-metric__value">{{ smallType }}</span>
            <span class="hero-metric__note">当前输出模板分类</span>
          </div>
          <div class="hero-metric">
            <span class="hero-metric__label">品种预览</span>
            <span class="hero-metric__value">{{ varieties.length }}</span>
            <span class="hero-metric__note">上传大表后可提取的品种数量</span>
          </div>
          <div class="hero-metric">
            <span class="hero-metric__label">模板文件</span>
            <span class="hero-metric__value">{{ smallTemplateName ? '已选择' : '未选择' }}</span>
            <span class="hero-metric__note">{{ smallTemplateName || '执行前需要先上传模板' }}</span>
          </div>
          <div class="hero-metric">
            <span class="hero-metric__label">最近结果</span>
            <span class="hero-metric__value">{{ lastResult.matched_count }}</span>
            <span class="hero-metric__note">最近一次命中的菜名条数</span>
          </div>
        </div>
      </template>
    </PageHeader>

    <div v-if="workflowMode === 'single'" class="workbench-grid">
      <div class="panel-stack panel-stack--rail">
        <el-card shadow="never" class="panel-card panel-card--emphasis">
          <div class="panel-heading">
            <div>
              <div class="panel-heading__eyebrow">工作模式</div>
              <h2 class="panel-heading__title">上传 / 路径锁定</h2>
            </div>
          </div>
          <el-radio-group :model-value="usePathMode" @change="onSwitchMode">
            <el-radio-button :value="false">文件上传</el-radio-button>
            <el-radio-button :value="true">路径锁定</el-radio-button>
          </el-radio-group>
        </el-card>

        <!-- ===== 上传模式 ===== -->
        <template v-if="!usePathMode">
        <el-card shadow="never" class="panel-card panel-card--emphasis">
          <div class="panel-heading">
            <div>
              <div class="panel-heading__eyebrow">步骤 01</div>
              <h2 class="panel-heading__title">上传大表并分析品种</h2>
              <p class="panel-heading__description">
                支持一次上传多份大表文档。分析完成后，右侧会刷新品种匹配预览，便于继续整理菜名。
              </p>
            </div>
          </div>

          <el-form label-position="top">
            <el-form-item label="大表文件（可多选）">
              <el-input v-model="bigTableSummary" placeholder="请选择大表文件" readonly>
                <template #append>
                  <el-button @click="triggerBigTablePicker">选择文件</el-button>
                </template>
              </el-input>
            </el-form-item>
          </el-form>

          <div class="action-cluster stretch">
            <el-button type="primary" :icon="Search" @click="onDetect">
              分析已上传大表
            </el-button>
            <span class="soft-note">分析不会写文件，只提取品种用于后续预览。</span>
          </div>

          <div class="status-strip">
            <span>已上传文件数：{{ detectedFiles.length }}</span>
            <span>可预览品种：{{ varieties.length }}</span>
          </div>

          <div class="pill-list">
            <el-tag
              v-for="file in detectedFiles"
              :key="file"
              type="success"
              effect="plain"
              round
            >
              {{ getFileName(file) }}
            </el-tag>
            <span v-if="detectedFiles.length === 0" class="soft-note">
              还没有上传大表文件。
            </span>
          </div>
        </el-card>

        <el-card shadow="never" class="panel-card">
          <div class="panel-heading">
            <div>
              <div class="panel-heading__eyebrow">步骤 02</div>
              <h2 class="panel-heading__title">上传模板并确认类型</h2>
              <p class="panel-heading__description">
                模板类型会参与输出文件命名。模板文件改为直接上传，不再依赖服务端磁盘路径。
              </p>
            </div>
          </div>

          <div class="field-grid two-up">
            <el-form label-position="top">
              <el-form-item label="小表类型">
                <el-select v-model="smallType" placeholder="选择小表类型" @change="onSmallTypeChange">
                  <el-option v-for="type in smallTypes" :key="type" :label="type" :value="type" />
                </el-select>
              </el-form-item>
            </el-form>

            <el-form label-position="top">
              <el-form-item label="模板文件">
                <el-input v-model="smallTemplateName" placeholder="请选择模板文件" readonly>
                  <template #append>
                    <el-button @click="triggerTemplatePicker">选择文件</el-button>
                  </template>
                </el-input>
              </el-form-item>
            </el-form>
          </div>
        </el-card>
        </template>

        <!-- ===== 路径锁定模式 ===== -->
        <template v-else>
        <el-card shadow="never" class="panel-card panel-card--emphasis">
          <div class="panel-heading">
            <div>
              <div class="panel-heading__eyebrow">步骤 01 · 路径锁定</div>
              <h2 class="panel-heading__title">浏览目录，发现大表文件</h2>
              <p class="panel-heading__description">
                浏览服务端目录，自动发现其中的 .doc / .docx 大表文件，勾选需要处理的项目。
              </p>
            </div>
          </div>

          <div class="field-grid two-up">
            <el-form label-position="top">
              <el-form-item label="大表目录">
                <el-input :model-value="bigDir" placeholder="点击右侧浏览" readonly>
                  <template #append>
                    <el-button @click="onBrowseBigDir">浏览</el-button>
                  </template>
                </el-input>
              </el-form-item>
            </el-form>
            <div class="summary-card">
              <span class="summary-card__label">已发现</span>
              <span class="summary-card__value">{{ foundBigFiles.length }}</span>
              <span class="summary-card__note">{{ foundBigFiles.length ? '已勾选 ' + selectedBigFileList.length + ' 个' : '等待发现' }}</span>
            </div>
          </div>

          <div class="action-cluster stretch">
            <el-button
              type="primary"
              :loading="findingFiles"
              @click="onFindTransferFiles"
            >
              发现大表文件
            </el-button>
            <el-button
              :disabled="selectedBigFileList.length === 0"
              @click="onAnalyzePathVarieties"
            >
              分析已选大表品种
            </el-button>
          </div>

          <div
            v-if="foundBigFiles.length > 0"
            class="pill-list"
            style="margin-top: 12px; max-height: 200px; overflow-y: auto"
          >
            <div style="margin-bottom: 6px">
              <el-button size="small" @click="toggleSelectAll">
                {{ allSelected ? '取消全选' : '全选' }}
              </el-button>
              <span class="soft-note" style="margin-left: 8px">
                ({{ selectedBigFileList.length }} / {{ foundBigFiles.length }})
              </span>
            </div>
            <el-checkbox
              v-for="file in foundBigFiles"
              :key="file"
              :model-value="selectedBigFilePaths.has(bigDir + '/' + file)"
              :label="file"
              size="small"
              @change="toggleBigFileSelection(bigDir + '/' + file)"
            />
            <div v-if="foundBigFiles.length === 0" class="soft-note">
              还没有发现大表文件。
            </div>
          </div>

          <div class="status-strip">
            <span>已发现：{{ foundBigFiles.length }} 个</span>
            <span>已勾选：{{ selectedBigFileList.length }} 个</span>
            <span>品种：{{ varieties.length }}</span>
          </div>
        </el-card>

        <el-card shadow="never" class="panel-card">
          <div class="panel-heading">
            <div>
              <div class="panel-heading__eyebrow">步骤 02 · 路径锁定</div>
              <h2 class="panel-heading__title">选择小表模板</h2>
              <p class="panel-heading__description">
                通过目录浏览器选择服务端小表模板文件，或使用已保存模板。
              </p>
            </div>
          </div>

          <div class="field-grid two-up">
            <el-form label-position="top">
              <el-form-item label="小表类型">
                <el-select v-model="smallType" placeholder="选择小表类型" @change="onSmallTypeChange">
                  <el-option v-for="type in smallTypes" :key="type" :label="type" :value="type" />
                </el-select>
              </el-form-item>
            </el-form>
            <div class="summary-card">
              <span class="summary-card__label">已保存模板</span>
              <span class="summary-card__value">{{ currentSavedTemplateReady ? '已配置' : '未保存' }}</span>
              <span class="summary-card__note">{{ currentSavedTemplate?.filename || '请先保存' }}</span>
            </div>
          </div>

          <el-radio-group :model-value="useSavedTemplate" @change="onUseSavedTemplate" style="margin-bottom: 12px">
            <el-radio-button :value="true">使用已保存模板</el-radio-button>
            <el-radio-button :value="false">浏览选择模板文件</el-radio-button>
          </el-radio-group>

          <div v-if="!useSavedTemplate" style="display: flex; align-items: center; gap: 8px; margin-bottom: 10px">
            <el-input :model-value="templatePath" placeholder="点击右侧浏览" readonly style="flex: 1">
              <template #append>
                <el-button @click="onBrowseTemplatePath">浏览</el-button>
              </template>
            </el-input>
          </div>

          <div class="action-cluster">
            <el-button :loading="uploadingTemplate" @click="triggerSavedTemplatePicker">
              保存当前类型模板
            </el-button>
            <span v-if="templatePath" class="soft-note">已选：{{ getFileName(templatePath) }}</span>
            <span v-else-if="useSavedTemplate && currentSavedTemplateReady" class="soft-note">将使用已保存模板</span>
          </div>
        </el-card>
        </template>

        <el-card v-if="usePathMode" shadow="never" class="panel-card">
          <div class="panel-heading">
            <div>
              <div class="panel-heading__eyebrow">步骤 03 · 路径锁定</div>
              <h2 class="panel-heading__title">输出目录</h2>
              <p class="panel-heading__description">
                文件将直接保存到选定的服务端目录，不再弹下载。
              </p>
            </div>
          </div>
          <el-form label-position="top">
            <el-form-item label="输出路径">
              <el-input :model-value="outputDir" placeholder="点击右侧浏览选择输出目录" readonly>
                <template #append>
                  <el-button @click="onBrowseOutputDir">浏览</el-button>
                </template>
              </el-input>
            </el-form-item>
          </el-form>
          <div v-if="outputDir" class="soft-note">
            输出文件将保存到：{{ outputDir }}
          </div>
        </el-card>

        <el-card shadow="never" class="panel-card">
          <div class="panel-heading">
            <div>
              <div class="panel-heading__eyebrow">步骤 {{ usePathMode ? '04' : '03' }}</div>
              <h2 class="panel-heading__title">整理待写入菜名</h2>
              <p class="panel-heading__description">
                支持逗号或换行分隔。去重后会同步更新匹配预览，方便确认覆盖范围。
              </p>
            </div>
          </div>

          <div class="textarea-shell">
            <el-input
              v-model="vegText"
              type="textarea"
              :rows="6"
              placeholder="输入菜名，支持逗号或换行分隔"
              @input="onVegInput"
            />
          </div>

          <div class="action-cluster" style="margin-top: 14px">
            <el-button :icon="CircleCheck" @click="onDedup">菜名去重</el-button>
            <el-button @click="clearVegInput">清空菜名</el-button>
          </div>

          <div class="status-strip">
            <span>{{ vegStatus || '输入后会显示待写入数量。' }}</span>
            <span>当前输入：{{ selectedVegNames.length }} 个</span>
          </div>
        </el-card>
      </div>

      <div class="panel-stack">
        <el-card shadow="never" class="panel-card">
          <div class="panel-heading">
            <div>
              <div class="panel-heading__eyebrow">输出</div>
              <h2 class="panel-heading__title">执行并下载</h2>
              <p class="panel-heading__description">
                执行后会直接下载生成的小表文档，不再先写到服务端指定目录。
              </p>
            </div>
          </div>

          <div class="action-cluster stretch">
            <el-button type="primary" :icon="VideoPlay" :loading="executing" @click="onExecute">
              开始提取并写入
            </el-button>
            <el-button @click="resetActionArea">重置执行区</el-button>
          </div>

          <div class="helper-list" style="margin-top: 16px">
            <div class="helper-list__item">
              <div class="helper-list__dot" />
              <div class="helper-list__text">先确认模板和菜名，再执行写入，避免把内容写进错误模板。</div>
            </div>
            <div class="helper-list__item">
              <div class="helper-list__dot" />
              <div class="helper-list__text">如果大表刚更新，建议先重新分析一次，再看品种预览和下载结果。</div>
            </div>
          </div>
        </el-card>

        <el-card shadow="never" class="panel-card">
          <div class="panel-heading">
            <div>
              <div class="panel-heading__eyebrow">快照</div>
              <h2 class="panel-heading__title">当前摘要</h2>
            </div>
          </div>

          <div class="summary-grid">
            <div class="summary-card">
              <span class="summary-card__label">大表文件</span>
              <span class="summary-card__value">{{ detectedFiles.length }}</span>
              <span class="summary-card__note">当前已上传的大表文档数</span>
            </div>
            <div class="summary-card">
              <span class="summary-card__label">菜名输入</span>
              <span class="summary-card__value">{{ selectedVegNames.length }}</span>
              <span class="summary-card__note">准备写入模板的菜名数量</span>
            </div>
            <div class="summary-card">
              <span class="summary-card__label">预览品种</span>
              <span class="summary-card__value">{{ varieties.length }}</span>
              <span class="summary-card__note">从大表提取出的可比对品种</span>
            </div>
            <div class="summary-card">
              <span class="summary-card__label">最近写入</span>
              <span class="summary-card__value">{{ lastResult.written_count }}</span>
              <span class="summary-card__note">最近一次输出写入的记录数</span>
            </div>
          </div>

          <div v-if="lastResult.output_file" class="path-display" style="margin-top: 14px">
            最近下载文件：{{ lastResult.output_file }}
          </div>
        </el-card>

        <el-card shadow="never" class="panel-card">
          <div class="panel-heading">
            <div>
              <div class="panel-heading__eyebrow">预览</div>
              <h2 class="panel-heading__title">品种匹配预览</h2>
            </div>
          </div>
          <VarietyPreview
            :varieties="varieties"
            :matched-set="matchedSet"
            :aliases-map="aliasesMap"
          />
        </el-card>

        <StatusLog ref="statusLogRef" />
      </div>
    </div>

    <div v-else class="workbench-grid">
      <div class="panel-stack panel-stack--rail">
        <el-card shadow="never" class="panel-card panel-card--emphasis">
          <div class="panel-heading">
            <div>
              <div class="panel-heading__eyebrow">模板库</div>
              <h2 class="panel-heading__title">保存小表模板</h2>
              <p class="panel-heading__description">
                月度批量会按当前小表类型复用已保存模板，后续只需上传当月大表。
              </p>
            </div>
          </div>

          <div class="field-grid two-up">
            <el-form label-position="top">
              <el-form-item label="小表类型">
                <el-select v-model="smallType" placeholder="选择小表类型" @change="onSmallTypeChange">
                  <el-option v-for="type in smallTypes" :key="type" :label="type" :value="type" />
                </el-select>
              </el-form-item>
            </el-form>
            <div class="summary-card">
              <span class="summary-card__label">当前模板</span>
              <span class="summary-card__value">{{ currentSavedTemplateReady ? '已保存' : '未保存' }}</span>
              <span class="summary-card__note">{{ currentSavedTemplate?.filename || '请保存该类型模板' }}</span>
            </div>
          </div>

          <div class="action-cluster" style="margin-top: 16px">
            <el-button :loading="uploadingTemplate" @click="triggerSavedTemplatePicker">
              保存当前类型模板
            </el-button>
          </div>
        </el-card>

        <el-card shadow="never" class="panel-card">
          <div class="panel-heading">
            <div>
              <div class="panel-heading__eyebrow">月度大表</div>
              <h2 class="panel-heading__title">上传当月全部大表</h2>
              <p class="panel-heading__description">
                系统会按文件名日期自动分组，支持同一天多个分页大表。
              </p>
            </div>
          </div>

          <div class="field-grid two-up">
            <el-form label-position="top">
              <el-form-item label="处理月份">
                <el-date-picker
                  v-model="monthlyMonth"
                  type="month"
                  value-format="YYYY-MM"
                  placeholder="选择月份"
                  style="width: 100%"
                />
              </el-form-item>
            </el-form>
            <el-form label-position="top">
              <el-form-item label="当月大表文件">
                <el-input v-model="monthlyTableSummary" placeholder="请选择当月大表文件" readonly>
                  <template #append>
                    <el-button @click="triggerMonthlyTablePicker">选择文件</el-button>
                  </template>
                </el-input>
              </el-form-item>
            </el-form>
          </div>

          <div class="textarea-shell" style="margin-top: 12px">
            <el-input
              v-model="vegText"
              type="textarea"
              :rows="6"
              placeholder="输入本月需要写入小表的菜名，支持逗号或换行分隔"
              @input="onVegInput"
            />
          </div>

          <div class="action-cluster" style="margin-top: 14px">
            <el-button :icon="CircleCheck" @click="onDedup">菜名去重</el-button>
            <el-button type="primary" :loading="monthlyPreviewing" @click="onPreviewMonthlyTransfer">预览日期分组</el-button>
          </div>

          <div class="status-strip">
            <span>大表 {{ monthlyTableFiles.length }} 份</span>
            <span>已识别 {{ monthlyGroups.length }} 天</span>
            <span>待写入 {{ selectedVegNames.length }} 个菜名</span>
          </div>
        </el-card>
      </div>

      <div class="panel-stack">
        <el-card shadow="never" class="panel-card">
          <div class="panel-heading">
            <div>
              <div class="panel-heading__eyebrow">预览</div>
              <h2 class="panel-heading__title">按日期分组</h2>
            </div>
          </div>

          <div v-if="monthlyGroups.length" class="monthly-preview-list">
            <article v-for="group in monthlyGroups" :key="group.date" class="monthly-preview-item">
              <strong>{{ group.date }}</strong>
              <span>{{ group.count }} 份大表</span>
              <small>{{ group.files.map(getFileName).join(' / ') }}</small>
            </article>
          </div>
          <el-empty v-else description="还没有预览月度大表分组" />

          <div v-if="monthlyUnrecognizedFiles.length" class="monthly-error-list">
            <div>未识别或不属于所选月份：</div>
            <div v-for="file in monthlyUnrecognizedFiles.slice(0, 6)" :key="file">{{ getFileName(file) }}</div>
          </div>
        </el-card>

        <el-card shadow="never" class="panel-card">
          <div class="panel-heading">
            <div>
              <div class="panel-heading__eyebrow">输出</div>
              <h2 class="panel-heading__title">生成月度小表压缩包</h2>
              <p class="panel-heading__description">
                zip 会平铺包含每天生成的小表和处理结果清单。
              </p>
            </div>
          </div>

          <div class="action-cluster stretch">
            <el-button type="primary" :icon="VideoPlay" :loading="monthlyExecuting" @click="onExecuteMonthlyTransfer">
              开始月度数据迁移
            </el-button>
            <el-button @click="resetActionArea">重置执行区</el-button>
          </div>

          <div class="summary-grid" style="margin-top: 16px">
            <div class="summary-card">
              <span class="summary-card__label">模板类型</span>
              <span class="summary-card__value">{{ smallType }}</span>
              <span class="summary-card__note">{{ currentSavedTemplateReady ? '已可用于批量输出' : '还未保存模板' }}</span>
            </div>
            <div class="summary-card">
              <span class="summary-card__label">最近输出</span>
              <span class="summary-card__value">{{ lastResult.output_file ? '已下载' : '未执行' }}</span>
              <span class="summary-card__note">{{ lastResult.output_file || '执行后会显示下载文件名' }}</span>
            </div>
          </div>
        </el-card>

        <StatusLog ref="statusLogRef" />
      </div>
    </div>

    <DirBrowser ref="dirBrowserRef" />

    <input
      ref="bigTableInputRef"
      type="file"
      accept=".doc,.docx"
      multiple
      style="display: none"
      @change="handleBigTableChange"
    />
    <input
      ref="templateInputRef"
      type="file"
      accept=".doc,.docx"
      style="display: none"
      @change="handleTemplateChange"
    />
    <input
      ref="monthlyTableInputRef"
      type="file"
      accept=".doc,.docx"
      multiple
      style="display: none"
      @change="handleMonthlyTableChange"
    />
    <input
      ref="savedTemplateInputRef"
      type="file"
      accept=".doc,.docx"
      style="display: none"
      @change="handleSavedTemplateChange"
    />
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { CircleCheck, Search, VideoPlay } from '@element-plus/icons-vue'

import PageHeader from '../components/PageHeader.vue'
import StatusLog from '../components/StatusLog.vue'
import VarietyPreview from '../components/VarietyPreview.vue'
import DirBrowser from '../components/DirBrowser.vue'
import { useDataTransferWorkflow } from '../features/data-transfer/composables/useDataTransferWorkflow'
import type { DirBrowserHandle } from '../features/shared/workflow'

const statusLogRef = ref<InstanceType<typeof StatusLog>>()
const dirBrowserRef = ref<DirBrowserHandle>()
const bigTableInputRef = ref<HTMLInputElement>()
const templateInputRef = ref<HTMLInputElement>()
const monthlyTableInputRef = ref<HTMLInputElement>()
const savedTemplateInputRef = ref<HTMLInputElement>()

const {
  aliasesMap,
  allSelected,
  bigDir,
  bigTableSummary,
  clearVegInput,
  currentSavedTemplate,
  currentSavedTemplateReady,
  detectedFiles,
  executing,
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
  monthlyTableSummary,
  monthlyUnrecognizedFiles,
  onAnalyzePathVarieties,
  onBrowseBigDir,
  onBrowseOutputDir,
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
} = useDataTransferWorkflow(statusLogRef, dirBrowserRef)

function triggerBigTablePicker() {
  bigTableInputRef.value?.click()
}

function triggerTemplatePicker() {
  templateInputRef.value?.click()
}

function triggerMonthlyTablePicker() {
  monthlyTableInputRef.value?.click()
}

function triggerSavedTemplatePicker() {
  savedTemplateInputRef.value?.click()
}

function handleBigTableChange(event: Event) {
  const input = event.target as HTMLInputElement
  setBigTableFiles(input.files)
  input.value = ''
}

function handleTemplateChange(event: Event) {
  const input = event.target as HTMLInputElement
  setSmallTemplateFile(input.files)
  input.value = ''
}

function handleMonthlyTableChange(event: Event) {
  const input = event.target as HTMLInputElement
  setMonthlyTableFiles(input.files)
  input.value = ''
}

function handleSavedTemplateChange(event: Event) {
  const input = event.target as HTMLInputElement
  void uploadTransferTemplate(input.files)
  input.value = ''
}
</script>

<style scoped>
.monthly-preview-list,
.monthly-error-list {
  display: grid;
  gap: 10px;
}

.monthly-preview-item {
  display: grid;
  gap: 4px;
  padding: 12px 14px;
  border-radius: 16px;
  border: 1px solid var(--line-soft);
  background: rgba(255, 255, 255, 0.72);
}

.monthly-preview-item small {
  color: var(--text-muted);
}

.monthly-error-list {
  margin-top: 14px;
  color: #b42318;
  font-size: 13px;
}
</style>
