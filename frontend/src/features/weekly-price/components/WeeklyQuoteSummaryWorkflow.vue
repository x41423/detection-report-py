<template>
  <div class="page-shell page-shell--wide-rail page-shell--full">
    <PageHeader
      eyebrow="新报价汇总"
      title="维护供应商日记录，并按模板导出周汇总"
      tone="orange"
    >
      <template #actions>
        <span class="accent-tag">批次 {{ previewData?.total_batches || 0 }}</span>
        <span class="accent-tag warning-tag">原始记录 {{ previewData?.total_entries || 0 }}</span>
        <span class="accent-tag muted-tag">汇总 {{ previewData?.total_summary_items || 0 }}</span>
      </template>

      <template #aside>
        <div class="hero-metric-grid">
          <div class="hero-metric">
            <span class="hero-metric__label">当前单位</span>
            <span class="hero-metric__value">{{ activeSupplier }}</span>
            <span class="hero-metric__note">记录上限 {{ currentLimit }}</span>
          </div>
          <div class="hero-metric">
            <span class="hero-metric__label">当前日期</span>
            <span class="hero-metric__value">{{ selectedRecordDate }}</span>
            <span class="hero-metric__note">{{ currentRecordEntryCount }} 条当日记录</span>
          </div>
          <div class="hero-metric">
            <span class="hero-metric__label">导出模板</span>
            <span class="hero-metric__value">{{ workbookPath ? '已选择' : '未选择' }}</span>
            <span class="hero-metric__note">{{ getFileName(workbookPath) || '导出前需要先上传模板工作簿' }}</span>
          </div>
          <div class="hero-metric">
            <span class="hero-metric__label">汇总状态</span>
            <span class="hero-metric__value">{{ previewing ? '更新中' : previewIssues.length ? '需修正' : previewData ? '已同步' : '待录入' }}</span>
            <span class="hero-metric__note">{{ previewIssues[0] || '日期记录变化后会自动重新计算' }}</span>
          </div>
        </div>
      </template>
    </PageHeader>

    <div class="workbench-grid">
      <div class="panel-stack">
        <el-card shadow="never" class="panel-card panel-card--warm">
          <div class="panel-heading">
            <div>
              <div class="panel-heading__eyebrow">步骤 01</div>
              <h2 class="panel-heading__title">单位与日期记录</h2>
              <p class="panel-heading__description">
                先选单位，再打开今天或历史日期记录。导入和粘贴识别都写入当前单位的当前日期。
              </p>
            </div>
          </div>

          <div class="supplier-switch">
            <button
              v-for="supplier in suppliers"
              :key="supplier"
              type="button"
              class="supplier-switch__item"
              :class="{ 'is-active': activeSupplier === supplier }"
              @click="selectSupplier(supplier)"
            >
              <span class="supplier-switch__name">{{ supplier }}</span>
              <span class="supplier-switch__meta">{{ savedRecordCounts[supplier] }} / {{ LIMITS[supplier] }}</span>
            </button>
          </div>

          <div class="supplier-tools">
            <el-button plain @click="openSupplierDialog">新增报价单位</el-button>
          </div>

          <div class="date-nav">
            <div class="date-nav__row">
              <el-date-picker
                v-model="selectedMonth"
                type="month"
                value-format="YYYY-MM"
                placeholder="年月"
                style="width: 148px"
                @change="(v: string) => onMonthChange(v)"
              />
              <span class="date-nav__source">{{ currentRecordSourceLabel }}</span>
            </div>

            <div class="week-picker">
              <button
                v-for="week in weeksForSelectedMonth"
                :key="week.monday"
                type="button"
                class="week-picker__item"
                :class="{ 'is-active': selectedWeekMonday === week.monday }"
                @click="selectWeek(week.monday)"
              >
                {{ week.label }}
              </button>
            </div>

            <div class="day-picker">
              <button
                v-for="day in daysForSelectedWeek"
                :key="day.date"
                type="button"
                class="day-picker__item"
                :class="{ 'is-active': selectedRecordDate === day.date, 'has-record': day.hasRecord, 'has-draft': day.hasDraft }"
                @click="selectRecordDate(day.date)"
              >
                <span class="day-picker__label">{{ day.dayLabel }}</span>
                <span class="day-picker__date">{{ day.dateLabel }}</span>
                <span v-if="day.entryCount > 0" class="day-picker__badge">{{ day.entryCount }}</span>
                <span v-else-if="day.draftCount > 0" class="day-picker__badge draft">{{ day.draftCount }}</span>
              </button>
            </div>
          </div>

          <div class="action-cluster summary-actions">
            <el-button type="primary" @click="openTodayRecord">打开今天记录</el-button>
            <el-button class="summary-ghost-button" @click="openImportDialog">导入 Excel 记录</el-button>
            <el-button class="summary-ghost-button" @click="openPasteDialog">批量粘贴识别</el-button>
            <el-button class="summary-ghost-button" @click="saveCurrentRecord">保存当前日期记录</el-button>
          </div>
        </el-card>

        <el-card shadow="never" class="panel-card">
          <div class="panel-heading">
            <div>
              <div class="panel-heading__eyebrow">步骤 02</div>
              <h2 class="panel-heading__title">原始记录审核</h2>
              <p class="panel-heading__description">
                这里只显示 {{ selectedRecordDate }} 的记录。改菜名后会尝试回填上次记住的单位，减少重复录入。
              </p>
            </div>
          </div>

          <div v-if="currentRecord || rawRows.length || hasCurrentDraft" class="field-grid">
            <div class="path-display">
              当前来源：{{ currentRecordSourceLabel }}
            </div>

            <div class="action-cluster summary-actions">
              <el-button type="primary" @click="addEntryToCurrentRecord">为当前日期新增一条报价</el-button>
              <el-button class="summary-ghost-button" @click="openPasteDialog">继续粘贴识别</el-button>
              <el-button class="summary-ghost-button" @click="saveCurrentRecord">保存当前日期记录</el-button>
              <el-button
                v-if="currentRecord"
                type="danger"
                plain
                @click="deleteCurrentRecord"
              >
                删除当前日期记录
              </el-button>
            </div>
          </div>

          <div class="table-shell table-shell--wide" style="margin-top: 18px">
            <el-table
              :data="rawRows"
              stripe
              size="small"
              max-height="380"
              empty-text="当前日期还没有原始记录，可以先新增一条或试试批量粘贴识别"
            >
              <el-table-column label="菜名" min-width="220">
                <template #default="{ row }">
                  <el-input
                    v-model="row.entry.name"
                    placeholder="菜名"
                    clearable
                    @blur="applyRememberedUnit(row.entry)"
                  />
                </template>
              </el-table-column>
              <el-table-column label="单位" width="140">
                <template #default="{ row }">
                  <el-select
                    v-model="row.entry.unit"
                    filterable
                    allow-create
                    default-first-option
                    clearable
                    placeholder="单位"
                    style="width: 100%"
                    @change="(value: string) => ensureMeasureUnitOption(value)"
                  >
                    <el-option
                      v-for="unit in measureUnitNames"
                      :key="unit"
                      :label="unit"
                      :value="unit"
                    />
                  </el-select>
                </template>
              </el-table-column>
              <el-table-column label="单价" width="160">
                <template #default="{ row }">
                  <el-input-number
                    v-model="row.entry.price"
                    :min="0"
                    :precision="2"
                    :step="0.1"
                    controls-position="right"
                    style="width: 100%"
                  />
                </template>
              </el-table-column>
              <el-table-column label="操作" width="140">
                <template #default="{ row }">
                  <div class="row-actions">
                    <el-button plain size="small" @click="removeEntry(row.entry.id)">
                      删除
                    </el-button>
                  </div>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </el-card>

        <el-card shadow="never" class="panel-card panel-card--emphasis">
          <div class="panel-heading">
            <div>
              <div class="panel-heading__eyebrow">步骤 03</div>
              <h2 class="panel-heading__title">汇总预览</h2>
              <p class="panel-heading__description">
                同一种菜若单位不同会拆成两条。预览会随记录变化自动刷新。
              </p>
            </div>
          </div>

          <el-alert v-if="previewIssues.length" :title="previewIssues[0]" type="warning" :closable="false" show-icon />

          <div class="summary-grid" style="margin-top: 18px">
            <div class="summary-card">
              <span class="summary-card__label">{{ activeSupplier }} 记录</span>
              <span class="summary-card__value">{{ currentSummary?.batch_count || 0 }}</span>
              <span class="summary-card__note">已参与汇总的日期记录数</span>
            </div>
            <div class="summary-card">
              <span class="summary-card__label">{{ activeSupplier }} 原始条目</span>
              <span class="summary-card__value">{{ currentSummary?.entry_count || 0 }}</span>
              <span class="summary-card__note">已参与汇总的原始记录数</span>
            </div>
            <div class="summary-card">
              <span class="summary-card__label">{{ activeSupplier }} 汇总</span>
              <span class="summary-card__value">{{ currentSummary?.summary_items.length || 0 }}</span>
              <span class="summary-card__note">聚合后的最终报价条数</span>
            </div>
            <div class="summary-card">
              <span class="summary-card__label">活跃单位</span>
              <span class="summary-card__value">{{ activeSupplierCount }}</span>
              <span class="summary-card__note">当前有有效记录的单位数</span>
            </div>
          </div>

          <div class="table-shell table-shell--wide" style="margin-top: 18px">
            <el-table
              :data="currentSummary?.summary_items || []"
              stripe
              size="small"
              max-height="340"
              empty-text="当前单位还没有可汇总记录"
            >
              <el-table-column prop="name" label="菜名" min-width="180" />
              <el-table-column prop="unit" label="单位" width="120" />
              <el-table-column label="汇总价" width="120">
                <template #default="{ row }">
                  {{ row.summary_price }}
                </template>
              </el-table-column>
            </el-table>
          </div>
        </el-card>
      </div>

      <div class="panel-stack panel-stack--rail">
        <el-card shadow="never" class="panel-card panel-card--warm">
          <div class="panel-heading">
            <div>
              <div class="panel-heading__eyebrow">本周记录</div>
              <h2 class="panel-heading__title">本周已保存记录</h2>
            </div>
          </div>

          <div v-if="savedRecordsByWeek.length" class="week-group-list">
            <div v-for="weekGroup in savedRecordsByWeek" :key="weekGroup.monday" class="week-group">
              <button
                type="button"
                class="week-group__header"
                :class="{ 'is-expanded': isWeekExpanded(weekGroup.monday) }"
                @click="toggleWeekExpanded(weekGroup.monday)"
              >
                <span class="week-group__label">{{ weekGroup.label }}</span>
                <span class="week-group__stats">{{ weekGroup.records.length }} 天 · {{ weekGroup.totalEntries }} 条</span>
                <span class="week-group__chevron">▾</span>
              </button>
              <div v-if="isWeekExpanded(weekGroup.monday)" class="week-group__records">
                <article
                  v-for="record in weekGroup.records"
                  :key="record.id"
                  class="saved-record-item"
                  :class="{ 'is-active': record.quote_date === selectedRecordDate }"
                >
                  <button
                    type="button"
                    class="saved-record-item__main"
                    @click="openSavedRecord(record.quote_date)"
                  >
                    <span class="saved-record-item__date">{{ record.quote_date }}</span>
                    <span class="saved-record-item__meta">
                      {{ countEntries(record) }} 条 / {{ getRecordSourceLabel(record) }}
                    </span>
                  </button>
                  <div class="saved-record-item__actions">
                    <el-button plain size="small" @click="openSavedRecord(record.quote_date)">查看</el-button>
                    <el-button plain size="small" @click="removeSavedRecord(record.quote_date)">删除</el-button>
                  </div>
                </article>
              </div>
            </div>
          </div>
          <div v-else class="panel-empty">当前单位本周还没有已保存记录。</div>
        </el-card>

        <el-card shadow="never" class="panel-card panel-card--warm">
          <div class="panel-heading">
            <div>
              <div class="panel-heading__eyebrow">导出</div>
              <h2 class="panel-heading__title">按模板导出汇总文件</h2>
            </div>
          </div>

          <el-form label-position="top">
            <el-form-item label="汇总模板工作簿">
              <el-input v-model="workbookPath" placeholder="请选择模板工作簿" readonly>
                <template #append>
                  <el-button @click="onBrowseWorkbookFile">选择文件</el-button>
                </template>
              </el-input>
            </el-form-item>
          </el-form>

          <div class="action-cluster stretch">
            <el-button type="primary" :icon="Download" :loading="exporting" @click="exportWorkbook">
              导出选中周汇总表
            </el-button>
          </div>
        </el-card>

        <el-card shadow="never" class="panel-card">
          <div class="panel-heading">
            <div>
              <div class="panel-heading__eyebrow">快照</div>
              <h2 class="panel-heading__title">总体概览</h2>
            </div>
          </div>

          <div class="summary-grid">
            <div class="summary-card">
              <span class="summary-card__label">总记录天数</span>
              <span class="summary-card__value">{{ previewData?.total_batches || 0 }}</span>
              <span class="summary-card__note">全部单位的有效日期记录数</span>
            </div>
            <div class="summary-card">
              <span class="summary-card__label">总原始记录</span>
              <span class="summary-card__value">{{ previewData?.total_entries || 0 }}</span>
              <span class="summary-card__note">全部单位参与汇总的记录数</span>
            </div>
            <div class="summary-card">
              <span class="summary-card__label">总汇总条数</span>
              <span class="summary-card__value">{{ previewData?.total_summary_items || 0 }}</span>
              <span class="summary-card__note">五个单位合计输出条数</span>
            </div>
            <div class="summary-card">
              <span class="summary-card__label">模板</span>
              <span class="summary-card__value">{{ workbookPath ? '已锁定' : '未锁定' }}</span>
              <span class="summary-card__note">{{ getFileName(workbookPath) || '导出前需要先上传模板工作簿' }}</span>
            </div>
          </div>
        </el-card>

        <StatusLog ref="statusLogRef" />
      </div>
    </div>

    <el-dialog
      v-model="supplierDialog.visible"
      title="新增报价单位"
      width="min(520px, calc(100vw - 24px))"
      :close-on-click-modal="false"
      append-to-body
    >
      <el-form label-position="top">
        <el-form-item label="报价单位名称">
          <el-input v-model="supplierDialog.name" placeholder="例如：自采、临时供应商" clearable />
        </el-form-item>
        <el-form-item label="每周记录上限">
          <el-input-number
            v-model="supplierDialog.weekly_batch_limit"
            :min="1"
            :max="7"
            :step="1"
            step-strictly
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="汇总规则">
          <el-radio-group v-model="supplierDialog.summary_rule">
            <el-radio-button value="highest">取最高价</el-radio-button>
            <el-radio-button value="average">取平均价</el-radio-button>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <div class="summary-dialog__footer">
          <el-button @click="supplierDialog.visible = false">取消</el-button>
          <el-button type="primary" :loading="supplierSaving" @click="confirmCreateSupplier">添加</el-button>
        </div>
      </template>
    </el-dialog>

    <el-dialog
      v-model="importDialogVisible"
      title="导入日期记录"
      width="min(620px, calc(100vw - 24px))"
      :close-on-click-modal="false"
      append-to-body
    >
      <div class="field-grid">
        <el-form label-position="top">
          <el-form-item label="当前单位">
            <el-input :model-value="activeSupplier" readonly />
          </el-form-item>
        </el-form>
        <el-form label-position="top">
          <el-form-item label="记录日期">
            <el-date-picker v-model="importForm.quote_date" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
          </el-form-item>
        </el-form>
        <el-form label-position="top">
          <el-form-item label="导入文件">
            <el-input v-model="importForm.source_path" placeholder="请选择统一模板 Excel 文件" readonly>
              <template #append>
                <el-button @click="onBrowseImportFile">选择文件</el-button>
              </template>
            </el-input>
          </el-form-item>
        </el-form>
      </div>
      <template #footer>
        <div class="summary-dialog__footer">
          <el-button @click="importDialogVisible = false">取消</el-button>
          <el-button type="primary" :loading="importing" @click="confirmImport">导入到当前日期</el-button>
        </div>
      </template>
    </el-dialog>

    <el-dialog
      v-model="pasteDialogVisible"
      title="批量粘贴识别"
      width="min(680px, calc(100vw - 24px))"
      :close-on-click-modal="false"
      append-to-body
    >
      <div class="field-grid">
        <div class="path-display">
          当前单位：{{ activeSupplier }} / 当前日期：{{ selectedRecordDate }}
        </div>

        <el-form label-position="top">
          <el-form-item label="粘贴方式">
            <el-radio-group v-model="pasteForm.mode" class="paste-mode-switch">
              <el-radio-button value="columns">分列粘贴</el-radio-button>
              <el-radio-button value="table">表格粘贴</el-radio-button>
              <el-radio-button value="lines">完整行粘贴</el-radio-button>
            </el-radio-group>
          </el-form-item>

          <template v-if="pasteForm.mode === 'columns'">
            <p class="paste-tip">
              从 Excel 分别复制菜名列和价格列。也可以先粘菜名，下一次只粘价格列，系统会按当前表格顺序补齐缺价行。
            </p>
            <div class="paste-column-grid">
              <el-form-item label="菜名列">
                <el-input
                  v-model="pasteForm.names"
                  type="textarea"
                  :rows="10"
                  placeholder="从 Excel 复制一列菜名，例如：&#10;白菜&#10;土豆&#10;黄瓜"
                />
              </el-form-item>
              <el-form-item label="价格列">
                <el-input
                  v-model="pasteForm.prices"
                  type="textarea"
                  :rows="10"
                  placeholder="从 Excel 复制对应价格，例如：&#10;2.5&#10;1.8&#10;3"
                />
              </el-form-item>
            </div>
          </template>

          <el-form-item v-else-if="pasteForm.mode === 'table'" label="Excel 表格区域">
            <el-input
              v-model="pasteForm.text"
              type="textarea"
              :rows="10"
              placeholder="可直接从 Excel 复制带表头区域，例如：&#10;菜名&#9;单位&#9;单价&#10;白菜&#9;斤&#9;2.5&#10;土豆&#9;斤&#9;1.8"
            />
          </el-form-item>

          <el-form-item v-else label="完整行内容">
            <el-input
              v-model="pasteForm.text"
              type="textarea"
              :rows="10"
              placeholder="每行一条，例如：&#10;白菜&#10;白菜 2.5&#10;白菜 2.5 斤"
            />
          </el-form-item>
        </el-form>
      </div>
      <template #footer>
        <div class="summary-dialog__footer">
          <el-button @click="pasteDialogVisible = false">取消</el-button>
          <el-button type="primary" :loading="pasteParsing" @click="confirmPaste">写入/补齐当前日期</el-button>
        </div>
      </template>
    </el-dialog>

  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { Download } from '@element-plus/icons-vue'

import PageHeader from '../../../components/PageHeader.vue'
import StatusLog from '../../../components/StatusLog.vue'
import { useWeeklyQuoteSummaryWorkflow } from '../composables/useWeeklyQuoteSummaryWorkflow'
import type { StatusLogHandle } from '../../shared/workflow'
import { useDirBrowserApi } from '../../shared/dirBrowser'

const { openFile } = useDirBrowserApi()
const statusLogRef = ref<StatusLogHandle>()
const importFileInputRef = ref<HTMLInputElement>()
const workbookInputRef = ref<HTMLInputElement>()

const {
  suppliers,
  LIMITS,
  activeSupplier,
  activeSupplierCount,
  addEntryToCurrentRecord,
  applyRememberedUnit,
  confirmCreateSupplier,
  confirmImport,
  confirmImportFromPath,
  confirmPaste,
  countEntries,
  currentLimit,
  currentRecord,
  currentRecordEntryCount,
  currentRecordSourceLabel,
  currentSummary,
  daysForSelectedWeek,
  deleteCurrentRecord,
  exportWorkbook,
  exporting,
  ensureMeasureUnitOption,
  getFileName,
  getRecordSourceLabel,
  importDialogVisible,
  importForm,
  importing,
  isWeekExpanded,
  measureUnitNames,
  onMonthChange,
  openImportDialog,
  openPasteDialog,
  openSupplierDialog,
  openSavedRecord,
  openTodayRecord,
  pasteDialogVisible,
  pasteForm,
  pasteParsing,
  previewData,
  previewIssues,
  previewing,
  rawRows,
  removeEntry,
  removeSavedRecord,
  saveCurrentRecord,
  savedRecordCounts,
  savedRecordsByWeek,
  selectedMonth,
  selectedRecordDate,
  selectedWeekMonday,
  selectRecordDate,
  selectSupplier,
  selectWeek,
  toggleWeekExpanded,
  setImportSourceFile,
  setWorkbookTemplateFile,
  setWorkbookTemplateFromPath,
  supplierDialog,
  supplierSaving,
  weeksForSelectedMonth,
  workbookPath,
  hasCurrentDraft,
} = useWeeklyQuoteSummaryWorkflow(statusLogRef)

function triggerImportPicker() {
  importFileInputRef.value?.click()
}

function triggerWorkbookPicker() {
  workbookInputRef.value?.click()
}

async function onBrowseImportFile() {
  const selected = await openFile('wqs:import', '', {
    title: '选择导入文件',
    extensions: ['.xlsx', '.xls', '.xlsm'],
  })
  if (selected) {
    try {
      await confirmImportFromPath(selected)
    } catch { /* handled in composable */ }
  }
}

async function onBrowseWorkbookFile() {
  const selected = await openFile('wqs:workbook', '', {
    title: '选择工作簿模板',
    extensions: ['.xlsx', '.xlsm'],
  })
  if (selected) {
    try {
      await setWorkbookTemplateFromPath(selected)
    } catch { /* handled in composable */ }
  }
}

function handleImportFileChange(event: Event) {
  const input = event.target as HTMLInputElement
  setImportSourceFile(input.files)
  input.value = ''
}

function handleWorkbookFileChange(event: Event) {
  const input = event.target as HTMLInputElement
  setWorkbookTemplateFile(input.files)
  input.value = ''
}
</script>

<style scoped>
.supplier-switch {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 10px;
}

.supplier-switch__item {
  display: grid;
  gap: 6px;
  padding: 15px 16px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-surface-card);
  cursor: pointer;
  text-align: left;
}

.supplier-switch__item.is-active {
  border-color: var(--color-primary);
  background: var(--color-primary-soft);
}

.supplier-switch__name {
  font-family: var(--font-heading);
  font-size: 15px;
  font-weight: 600;
  color: var(--color-text);
}

.supplier-switch__meta {
  font-size: 12px;
  color: var(--color-muted);
}

.supplier-tools {
  display: flex;
  justify-content: flex-end;
  margin-top: 10px;
}

.date-nav {
  display: grid;
  gap: 10px;
  margin-top: 18px;
}

.date-nav__row {
  display: flex;
  align-items: center;
  gap: 10px;
}

.date-nav__source {
  font-size: 12px;
  color: var(--color-muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.week-picker {
  display: flex;
  flex-wrap: wrap;
  gap: 7px;
}

.week-picker__item {
  padding: 6px 13px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface-card);
  color: var(--color-text);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: border-color 0.16s, background 0.16s;
}

.week-picker__item:hover {
  border-color: var(--color-border-highlight);
  background: var(--color-surface);
}

.week-picker__item.is-active {
  border-color: var(--color-primary);
  background: var(--color-surface);
}

.day-picker {
  display: grid;
  grid-template-columns: repeat(7, minmax(0, 1fr));
  gap: 5px;
}

.day-picker__item {
  position: relative;
  display: grid;
  gap: 2px;
  padding: 9px 5px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface-card);
  cursor: pointer;
  text-align: center;
  transition: border-color 0.16s, background 0.16s;
}

.day-picker__item:hover {
  border-color: var(--color-border-highlight);
  background: var(--color-surface);
}

.day-picker__item.has-record {
  border-color: #fb923c;
  background: rgba(251, 146, 60, 0.08);
}

.day-picker__item.has-draft:not(.has-record) {
  border-color: var(--color-brand-accent);
  background: rgba(59, 130, 246, 0.06);
}

.day-picker__item.is-active {
  border-color: var(--color-primary);
  background: var(--color-surface);
}

.day-picker__label {
  display: block;
  font-size: 10px;
  font-weight: 700;
  color: var(--color-muted);
  letter-spacing: 0.04em;
}

.day-picker__date {
  display: block;
  font-family: var(--font-heading);
  font-size: 12px;
  font-weight: 700;
  color: var(--color-text);
}

.day-picker__badge {
  position: absolute;
  top: 3px;
  right: 3px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 15px;
  height: 15px;
  padding: 0 3px;
  border-radius: 999px;
  background: #fb923c;
  color: #fff;
  font-size: 9px;
  font-weight: 700;
  line-height: 1;
}

.day-picker__badge.draft {
  background: #0ea5e9;
}

.day-picker__item.is-active .day-picker__label {
  color: var(--color-text);
}

.week-group-list {
  display: grid;
  gap: 7px;
}

.week-group {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  overflow: hidden;
  background: var(--color-surface-card);
}

.week-group__header {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 11px 15px;
  border: none;
  background: transparent;
  cursor: pointer;
  text-align: left;
  transition: background 0.16s;
}

.week-group__header:hover {
  background: var(--color-surface);
}

.week-group__label {
  font-family: var(--font-heading);
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text);
}

.week-group__stats {
  flex: 1;
  font-size: 11px;
  color: var(--color-muted);
}

.week-group__chevron {
  font-size: 13px;
  color: var(--color-muted);
  transition: transform 0.2s ease;
}

.week-group__header.is-expanded .week-group__chevron {
  transform: rotate(180deg);
}

.week-group__records {
  padding: 4px 10px 10px;
  display: grid;
  gap: 7px;
}

.week-group__records .saved-record-item {
  border-radius: 10px;
}

.summary-actions {
  margin-top: 8px;
}

.summary-ghost-button {
  border-color: var(--color-border);
  background: var(--color-surface);
  color: var(--color-text);
}

.row-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.saved-record-list {
  display: grid;
  gap: 10px;
}

.saved-record-item {
  display: grid;
  gap: 10px;
  padding: 14px 16px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-surface-card);
}

.saved-record-item.is-active {
  border-color: var(--color-primary);
}

.saved-record-item__main {
  display: grid;
  gap: 6px;
  padding: 0;
  border: none;
  background: transparent;
  color: inherit;
  text-align: left;
  cursor: pointer;
}

.saved-record-item__date {
  font-family: var(--font-heading);
  font-size: 16px;
  font-weight: 600;
  color: var(--color-text);
}

.saved-record-item__meta {
  color: var(--color-muted);
  font-size: 13px;
  line-height: 1.55;
}

.saved-record-item__actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.panel-empty {
  padding: 22px 18px;
  border-radius: var(--radius-lg);
  border: 1px dashed var(--color-border);
  background: var(--color-surface-card);
  color: var(--color-muted);
  text-align: center;
}

.paste-mode-switch {
  width: 100%;
}

.paste-tip {
  margin: -4px 0 14px;
  color: var(--color-muted);
  font-size: 13px;
  line-height: 1.6;
}

.paste-column-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.summary-dialog__footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

@media (max-width: 1180px) {
  .supplier-switch {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .day-picker {
    grid-template-columns: repeat(4, minmax(0, 1fr));
  }
}

@media (max-width: 720px) {
  .supplier-switch {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .date-nav__row {
    flex-wrap: wrap;
    align-items: flex-start;
  }

  .day-picker {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .paste-column-grid {
    grid-template-columns: 1fr;
  }

  .summary-dialog__footer {
    flex-direction: column-reverse;
  }

  .summary-dialog__footer :deep(.el-button) {
    width: 100%;
  }
}

@media (max-width: 430px) {
  .supplier-switch {
    grid-template-columns: 1fr;
  }

  .day-picker {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
