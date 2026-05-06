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
      <!-- ====== Tab 1: 单次检测 ====== -->
      <el-tab-pane label="单次检测" name="single">
        <!-- 步骤 01 · 检测配置 -->
        <el-card shadow="never" class="panel-card">
          <div class="panel-heading">
            <div>
              <div class="panel-heading__eyebrow">步骤 01 · 检测配置</div>
              <h2 class="panel-heading__title">选择大表与小表</h2>
              <p class="panel-heading__description">
                通过文件上传或路径锁定两种方式选择当日大小表。
              </p>
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

            <el-form-item label="工作模式">
              <el-radio-group :model-value="workflow.usePathMode.value" @change="onModeChange">
                <el-radio-button :value="false">文件上传</el-radio-button>
                <el-radio-button :value="true">路径锁定</el-radio-button>
              </el-radio-group>
            </el-form-item>

            <!-- 文件上传模式 -->
            <div v-if="!workflow.usePathMode.value" class="field-grid two-up">
              <el-form-item label="大表（.docx）">
                <el-upload
                  :auto-upload="false"
                  :show-file-list="false"
                  :on-change="(f: UploadRawFile) => onFileChange('big', f)"
                >
                  <el-button>选择大表</el-button>
                  <template #tip>
                    <span class="soft-note">{{ workflow.fileInfo.value.big_file || '尚未选择' }}</span>
                  </template>
                </el-upload>
              </el-form-item>
              <el-form-item label="小表（.docx）">
                <el-upload
                  :auto-upload="false"
                  :show-file-list="false"
                  :on-change="(f: UploadRawFile) => onFileChange('small', f)"
                >
                  <el-button>选择小表</el-button>
                  <template #tip>
                    <span class="soft-note">{{ workflow.fileInfo.value.small_file || '尚未选择' }}</span>
                  </template>
                </el-upload>
              </el-form-item>
            </div>

            <!-- 路径锁定模式 -->
            <div v-else>
              <div class="field-grid two-up">
                <el-form-item label="大表目录">
                  <el-input :model-value="workflow.bigPath.value" placeholder="点击右侧浏览" readonly>
                    <template #append>
                      <el-button @click="workflow.onBrowsePath('big')">浏览</el-button>
                    </template>
                  </el-input>
                </el-form-item>
                <el-form-item label="小表目录">
                  <el-input :model-value="workflow.smallPath.value" placeholder="点击右侧浏览" readonly>
                    <template #append>
                      <el-button @click="workflow.onBrowsePath('small')">浏览</el-button>
                    </template>
                  </el-input>
                </el-form-item>
              </div>
              <el-button
                type="primary"
                :loading="workflow.findingFiles.value"
                :disabled="!workflow.bigPath.value || !workflow.smallPath.value"
                @click="workflow.onFindFiles"
              >
                查找目标文件
              </el-button>
              <span
                v-if="workflow.findFilesMessage.value"
                :class="workflow.pathLocked.value ? 'soft-note' : 'soft-note text--error'"
                style="margin-left: 12px"
              >
                {{ workflow.findFilesMessage.value }}
              </span>
              <div v-if="workflow.pathLocked.value" class="soft-note" style="margin-top: 8px">
                <div>大表: {{ workflow.foundFileBig.value }}</div>
                <div>小表: {{ workflow.foundFileSmall.value }}</div>
              </div>
            </div>
          </el-form>
        </el-card>

        <!-- 输出目录（仅路径锁定模式） -->
        <el-card v-if="workflow.usePathMode.value" shadow="never" class="panel-card">
          <div class="panel-heading">
            <div>
              <div class="panel-heading__eyebrow">输出目录</div>
              <h2 class="panel-heading__title">选择文件输出路径</h2>
              <p class="panel-heading__description">
                生成的文件将直接保存到选定的服务端目录，不再弹下载。
              </p>
            </div>
          </div>
          <el-form label-position="top">
            <el-form-item label="输出路径">
              <el-input :model-value="workflow.outputDir.value" placeholder="点击右侧浏览（留空则输出到大表目录）" readonly>
                <template #append>
                  <el-button @click="workflow.onBrowseOutputDir()">浏览</el-button>
                </template>
              </el-input>
            </el-form-item>
          </el-form>
        </el-card>

        <!-- 步骤 02 · 菜名 / JSON -->
        <el-card shadow="never" class="panel-card">
          <div class="panel-heading">
            <div>
              <div class="panel-heading__eyebrow">步骤 02 · 菜名 / JSON</div>
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
                :rows="8"
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

        <!-- 步骤 03 · 模板库（可选） -->
        <el-card shadow="never" class="panel-card">
          <div class="panel-heading">
            <div>
              <div class="panel-heading__eyebrow">步骤 03 · 模板库（可选）</div>
              <h2 class="panel-heading__title">保存常用模板</h2>
              <p class="panel-heading__description">
                上传后模板可供月度批量复用，无需每次选择。
              </p>
            </div>
          </div>

          <div class="field-grid two-up">
            <div style="display: flex; flex-direction: column; gap: 8px">
              <span style="font-weight: 600; font-size: 14px; color: var(--el-text-color-primary)">大表模板</span>
              <div style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap">
                <template v-if="workflow.templateStatus.value?.big_template.configured">
                  <el-tag type="success" size="small">已保存</el-tag>
                  <span style="font-size: 13px">{{ workflow.templateStatus.value.big_template.filename }}</span>
                </template>
                <span v-else class="soft-note">尚未保存</span>
              </div>
              <el-upload
                :auto-upload="false"
                :show-file-list="false"
                :on-change="(f: UploadRawFile) => onTemplateChange('big', f)"
              >
                <el-button size="small">上传 / 更换</el-button>
              </el-upload>
            </div>
            <div style="display: flex; flex-direction: column; gap: 8px">
              <span style="font-weight: 600; font-size: 14px; color: var(--el-text-color-primary)">小表模板</span>
              <div style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap">
                <template v-if="workflow.templateStatus.value?.small_template.configured">
                  <el-tag type="success" size="small">已保存</el-tag>
                  <span style="font-size: 13px">{{ workflow.templateStatus.value.small_template.filename }}</span>
                </template>
                <span v-else class="soft-note">尚未保存</span>
              </div>
              <el-upload
                :auto-upload="false"
                :show-file-list="false"
                :on-change="(f: UploadRawFile) => onTemplateChange('small', f)"
              >
                <el-button size="small">上传 / 更换</el-button>
              </el-upload>
            </div>
          </div>
        </el-card>

        <!-- 步骤 04 · 执行 -->
        <el-card shadow="never" class="panel-card">
          <div class="panel-heading">
            <div>
              <div class="panel-heading__eyebrow">步骤 04 · 执行</div>
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
      </el-tab-pane>

      <!-- ====== Tab 2: 月度批量·上传模式 ====== -->
      <el-tab-pane label="月度批量·上传" name="monthly-upload">
        <el-card shadow="never" class="panel-card">
          <div class="panel-heading">
            <div>
              <div class="panel-heading__eyebrow">上传模式</div>
              <h2 class="panel-heading__title">批量生成全月检测报告</h2>
              <p class="panel-heading__description">
                上传大表/小表模板，输入或上传每日蔬菜清单，批量生成该月所有检测报告并打包下载。
              </p>
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

            <el-form-item label="模板来源">
              <el-radio-group :model-value="workflow.monthUseSavedTemplates.value" @change="onMonthTemplateModeChange">
                <el-radio :value="true">使用已保存模板</el-radio>
                <el-radio :value="false">上传临时模板</el-radio>
              </el-radio-group>
            </el-form-item>

            <div v-if="!workflow.monthUseSavedTemplates.value" class="field-grid two-up">
              <el-form-item label="大表模板">
                <el-upload
                  :auto-upload="false"
                  :show-file-list="false"
                  :on-change="(f: UploadRawFile) => onMonthTemplateChange('big', f)"
                >
                  <el-button size="small">选择文件</el-button>
                  <template #tip>
                    <span class="soft-note">{{ monthTemplateNames.big || '未选择' }}</span>
                  </template>
                </el-upload>
              </el-form-item>
              <el-form-item label="小表模板">
                <el-upload
                  :auto-upload="false"
                  :show-file-list="false"
                  :on-change="(f: UploadRawFile) => onMonthTemplateChange('small', f)"
                >
                  <el-button size="small">选择文件</el-button>
                  <template #tip>
                    <span class="soft-note">{{ monthTemplateNames.small || '未选择' }}</span>
                  </template>
                </el-upload>
              </el-form-item>
            </div>

            <el-form-item label="每日清单（文本或上传 Excel / TXT）">
              <el-input
                v-model="workflow.monthListText.value"
                type="textarea"
                :rows="6"
                placeholder="格式：每行一条，日期在前，品种用逗号或空格分隔&#10;示例：&#10;4月1日 青椒 蘑菇 番茄&#10;4月2日 黄瓜 白菜 萝卜&#10;&#10;或直接上传 Excel 文件（第一行为日期，每列一天）"
              />
              <div class="action-cluster">
                <el-upload
                  :auto-upload="false"
                  :show-file-list="false"
                  :on-change="(f: UploadRawFile) => onMonthFileChange(f)"
                  accept=".xlsx,.xls,.txt"
                >
                  <el-button>上传清单文件</el-button>
                </el-upload>
                <span v-if="workflow.monthListFile.value" class="soft-note">
                  {{ workflow.monthListFile.value.name }}
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

            <el-form-item v-if="workflow.monthEntries.value.length > 0" label="解析结果预览">
              <el-table :data="workflow.monthEntries.value" size="small" max-height="300" stripe>
                <el-table-column type="index" label="#" width="50" />
                <el-table-column prop="date" label="日期" width="120" />
                <el-table-column label="品种列表">
                  <template #default="{ row }">
                    {{ (row as { names: string[] }).names.join('、') }}
                  </template>
                </el-table-column>
                <el-table-column label="品种数" width="80" align="center">
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

            <el-form-item>
              <el-button
                type="primary"
                size="large"
                :loading="workflow.monthExecuting.value"
                :disabled="workflow.monthEntries.value.length === 0"
                @click="workflow.onExecuteMonthly"
              >
                批量执行并下载
              </el-button>
              <div v-if="workflow.monthResult.value" class="soft-note" style="margin-top: 12px">
                {{ workflow.monthResult.value }}
              </div>
            </el-form-item>
          </el-form>
        </el-card>
      </el-tab-pane>

      <!-- ====== Tab 3: 月度批量·路径锁定 ====== -->
      <el-tab-pane label="月度批量·路径" name="monthly-path">
        <el-card shadow="never" class="panel-card">
          <div class="panel-heading">
            <div>
              <div class="panel-heading__eyebrow">路径锁定模式</div>
              <h2 class="panel-heading__title">批量生成全月检测报告（路径）</h2>
              <p class="panel-heading__description">
                浏览服务器目录锁定大表/小表模板文件，输入或上传每日蔬菜清单，批量生成该月所有检测报告并打包下载。
              </p>
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

            <div class="field-grid two-up">
              <el-form-item label="大表模板">
                <el-input :model-value="workflow.monthlyBigPath.value" placeholder="点击右侧浏览" readonly>
                  <template #append>
                    <el-button @click="workflow.onMonthlyBrowsePath('big')">浏览</el-button>
                  </template>
                </el-input>
              </el-form-item>
              <el-form-item label="小表模板">
                <el-input :model-value="workflow.monthlySmallPath.value" placeholder="点击右侧浏览" readonly>
                  <template #append>
                    <el-button @click="workflow.onMonthlyBrowsePath('small')">浏览</el-button>
                  </template>
                </el-input>
              </el-form-item>
            </div>
            <el-button
              type="primary"
              :loading="workflow.monthlyFindingFiles.value"
              :disabled="!workflow.monthlyBigPath.value || !workflow.monthlySmallPath.value"
              @click="workflow.onMonthlyFindFiles"
            >
              锁定模板路径
            </el-button>
            <span
              v-if="workflow.monthlyFindFilesMessage.value"
              :class="workflow.monthlyPathLocked.value ? 'soft-note' : 'soft-note text--error'"
              style="margin-left: 12px"
            >
              {{ workflow.monthlyFindFilesMessage.value }}
            </span>

            <el-divider />

            <el-form-item label="每日清单（文本或上传 Excel / TXT）">
              <el-input
                v-model="workflow.monthListText.value"
                type="textarea"
                :rows="6"
                placeholder="格式：每行一条，日期在前，品种用逗号或空格分隔&#10;示例：&#10;4月1日 青椒 蘑菇 番茄&#10;4月2日 黄瓜 白菜 萝卜&#10;&#10;或直接上传 Excel 文件（第一行为日期，每列一天）"
              />
              <div class="action-cluster">
                <el-upload
                  :auto-upload="false"
                  :show-file-list="false"
                  :on-change="(f: UploadRawFile) => onMonthFileChange(f)"
                  accept=".xlsx,.xls,.txt"
                >
                  <el-button>上传清单文件</el-button>
                </el-upload>
                <span v-if="workflow.monthListFile.value" class="soft-note">
                  {{ workflow.monthListFile.value.name }}
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

            <el-form-item v-if="workflow.monthEntries.value.length > 0" label="解析结果预览">
              <el-table :data="workflow.monthEntries.value" size="small" max-height="300" stripe>
                <el-table-column type="index" label="#" width="50" />
                <el-table-column prop="date" label="日期" width="120" />
                <el-table-column label="品种列表">
                  <template #default="{ row }">
                    {{ (row as { names: string[] }).names.join('、') }}
                  </template>
                </el-table-column>
                <el-table-column label="品种数" width="80" align="center">
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

            <el-form-item label="输出目录（留空则弹下载）">
              <el-input :model-value="workflow.monthlyOutputDir.value" placeholder="点击右侧浏览选择输出目录" readonly>
                <template #append>
                  <el-button @click="workflow.onBrowseOutputDir()">浏览</el-button>
                </template>
              </el-input>
            </el-form-item>

            <el-form-item>
              <el-button
                type="primary"
                size="large"
                :loading="workflow.monthExecuting.value"
                :disabled="workflow.monthEntries.value.length === 0"
                @click="workflow.onExecuteMonthly"
              >
                批量执行并下载
              </el-button>
              <div v-if="workflow.monthResult.value" class="soft-note" style="margin-top: 12px">
                {{ workflow.monthResult.value }}
              </div>
            </el-form-item>
          </el-form>
        </el-card>
      </el-tab-pane>
    </el-tabs>

    <DirBrowser ref="dirBrowserRef" />
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
import type { DirBrowserHandle } from '../features/shared/workflow'

const statusLogRef = ref<InstanceType<typeof StatusLog>>()
const dirBrowserRef = ref<DirBrowserHandle>()
const workflow = usePesticideWorkflow(statusLogRef, dirBrowserRef)
const monthTemplateNames = ref<{ big: string; small: string }>({ big: '', small: '' })

const canExecute = computed(() => {
  if (workflow.usePathMode.value) {
    return workflow.pathLocked.value && workflow.dataCount.value > 0
  }
  return workflow.fileReadyCount.value >= 2 && workflow.dataCount.value > 0
})

function onTabChange(val: string) {
  workflow.onSetTab(val as 'single' | 'monthly-upload' | 'monthly-path')
}

function onModeChange(val: string | number | boolean) {
  workflow.onSwitchMode(Boolean(val))
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
