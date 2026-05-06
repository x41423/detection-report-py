# Pesticide.vue 完整重建实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在已恢复的 usePesticideWorkflow composable 和后端 API 基础上，重建完整的农残检测页面 UI，包含路径锁定/文件上传双模式、模板管理、月度批量等完整流程。

**Architecture:** 扩展 `usePesticideWorkflow` composable 增加路径锁定、模板管理、月度批量三组状态/动作；重写 `Pesticide.vue` 移除重建警告，按条件渲染各功能卡片。遵循项目现有的 View→Composable 模式，所有逻辑下沉到 composable，view 只负责渲染。

**Tech Stack:** Vue 3 Composition API + TypeScript + Element Plus + Axios

---

### Task 1: 扩展 usePesticideWorkflow（路径锁定 + 模板 + 月度批量）

**Files:**
- Modify: `frontend/src/features/pesticide/composables/usePesticideWorkflow.ts`

**路径锁定 state：**
```ts
// 新增 refs
const usePathMode = ref(false)
const bigPath = ref('')
const smallPath = ref('')
const pathLocked = ref(false)
const foundFileBig = ref('')
const foundFileSmall = ref('')
const findingFiles = ref(false)
const findFilesMessage = ref('')

// 新增 computed
const activeFileInfo = computed(() => ({
  big_file: usePathMode.value
    ? foundFileBig.value || bigPath.value
    : bigFile.value?.name || '',
  small_file: usePathMode.value
    ? foundFileSmall.value || smallPath.value
    : smallFile.value?.name || '',
  big_exists: usePathMode.value ? Boolean(foundFileBig.value) : Boolean(bigFile.value),
  small_exists: usePathMode.value ? Boolean(foundFileSmall.value) : Boolean(smallFile.value),
}))
```

**路径锁定 actions：**
```ts
// 切换模式时清空另一边
function onSwitchMode(pathMode: boolean) {
  usePathMode.value = pathMode
  pathLocked.value = false
  foundFileBig.value = ''
  foundFileSmall.value = ''
  findFilesMessage.value = ''
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
  try {
    const { data } = await findFiles(bigPath.value, smallPath.value, parts.year, parts.month, parts.day)
    foundFileBig.value = data.big_file || ''
    foundFileSmall.value = data.small_file || ''
    pathLocked.value = Boolean(data.big_file && data.small_file)
    findFilesMessage.value = data.message || (pathLocked.value ? '路径锁定成功' : '未找到匹配文件')
    appendStatus(statusLogRef, findFilesMessage.value, pathLocked.value ? 'success' : 'error')
  } catch (error: any) {
    findFilesMessage.value = '查找失败: ' + getApiErrorMessage(error)
    appendStatus(statusLogRef, findFilesMessage.value, 'error')
  } finally {
    findingFiles.value = false
  }
}
```

**模板管理 state + actions：**
```ts
// 在 loadConfig() 中添加模板状态加载
// 新增
const templateStatus = ref<PesticideTemplateStatusResponse | null>(null)
const templateLoading = ref(false)

async function onLoadTemplates() {
  templateLoading.value = true
  try {
    const { data } = await getPesticideTemplates()
    templateStatus.value = data
  } catch (error: any) {
    // 静默失败，不影响主流程
  } finally {
    templateLoading.value = false
  }
}

async function onUploadTemplate(kind: 'big' | 'small', file: File) {
  try {
    const { data } = await uploadPesticideTemplate(kind, file)
    templateStatus.value = data
    appendStatus(statusLogRef, `${kind === 'big' ? '大表' : '小表'}模板已更新`, 'success')
    ElMessage.success(`${kind === 'big' ? '大表' : '小表'}模板已保存`)
  } catch (error: any) {
    ElMessage.error('模板上传失败: ' + getApiErrorMessage(error))
  }
}
```

**月度批量 state + actions：**
```ts
const month = ref('')
const monthListText = ref('')
const monthListFile = ref<File | null>(null)
const monthEntries = ref<MonthlyListEntry[]>([])
const monthParsing = ref(false)
const monthListErrors = ref<MonthlyListParseError[]>([])
const monthExecuting = ref(false)
const monthResult = ref('')
const monthUseSavedTemplates = ref(true)
const monthBigTemplateFile = ref<File | null>(null)
const monthSmallTemplateFile = ref<File | null>(null)

async function onParseMonthlyList() {
  if (!month.value) {
    ElMessage.warning('请选择月份')
    return
  }
  if (!monthListText.value.trim() && !monthListFile.value) {
    ElMessage.warning('请输入清单文本或上传清单文件')
    return
  }
  monthParsing.value = true
  try {
    const { data } = await parsePesticideMonthlyList({
      month: month.value,
      listText: monthListText.value,
      listFile: monthListFile.value,
    })
    monthEntries.value = data.entries
    monthListErrors.value = data.errors
    const msg = `解析完成：${data.total_dates} 天，${data.total_names} 个品种`
    appendStatus(statusLogRef, msg, data.errors.length ? 'error' : 'success')
    if (data.errors.length > 0) {
      ElMessage.warning(`${msg}，${data.errors.length} 行有误`)
    } else {
      ElMessage.success(msg)
    }
  } catch (error: any) {
    monthEntries.value = []
    appendStatus(statusLogRef, '清单解析失败: ' + getApiErrorMessage(error), 'error')
  } finally {
    monthParsing.value = false
  }
}

async function onExecuteMonthly() {
  if (monthEntries.value.length === 0) {
    ElMessage.warning('请先解析月度清单')
    return
  }
  monthExecuting.value = true
  clearStatus(statusLogRef)
  try {
    const payload = await executePesticideMonthly({
      month: month.value,
      entries: monthEntries.value,
      inspectorName: inspectorName.value,
      bigTemplateFile: monthUseSavedTemplates.value ? null : monthBigTemplateFile.value,
      smallTemplateFile: monthUseSavedTemplates.value ? null : monthSmallTemplateFile.value,
    })
    triggerDownload(payload)
    monthResult.value = payload.message
    appendStatus(statusLogRef, payload.message, 'success')
  } catch (error: any) {
    appendStatus(statusLogRef, '月度批量执行失败: ' + getApiErrorMessage(error), 'error')
  } finally {
    monthExecuting.value = false
  }
}
```

**修改 onExecute：** 路径模式使用 `/execute` + JSON 响应（提示输出目录），文件模式使用 `/execute/upload` + ZIP 下载。

**修改 loadConfig：** 加载模板状态、big_path/small_path 路径配置。

---

### Task 2: 重写 Pesticide.vue

**Files:**
- Modify: `frontend/src/views/Pesticide.vue`

完整模板结构：

```vue
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

    <!-- 步骤 01 · 检测配置 -->
    <el-card shadow="never" class="panel-card">
      <div class="panel-heading">
        <div>
          <div class="panel-heading__eyebrow">步骤 01 · 检测配置</div>
          <h2 class="panel-heading__title">选择大表与小表</h2>
          <p class="panel-heading__description">通过文件上传或路径锁定选择当日大小表。</p>
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
          <el-radio-group v-model="workflow.usePathMode.value" @change="onModeChange">
            <el-radio-button :value="false">文件上传</el-radio-button>
            <el-radio-button :value="true">路径锁定</el-radio-button>
          </el-radio-group>
        </el-form-item>

        <!-- 文件上传模式 -->
        <div v-if="!workflow.usePathMode.value" class="field-grid two-up">
          <el-form-item label="大表（.docx）">
            <el-upload :auto-upload="false" :show-file-list="false" :on-change="(f: UploadRawFile) => onFileChange('big', f)">
              <el-button>选择大表</el-button>
              <template #tip>
                <span class="soft-note">{{ workflow.fileInfo.value.big_file || '尚未选择' }}</span>
              </template>
            </el-upload>
          </el-form-item>
          <el-form-item label="小表（.docx）">
            <el-upload :auto-upload="false" :show-file-list="false" :on-change="(f: UploadRawFile) => onFileChange('small', f)">
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
              <el-input v-model="workflow.bigPath.value" placeholder="点击右侧浏览" readonly>
                <template #append>
                  <el-button @click="onBrowsePath('big')">浏览</el-button>
                </template>
              </el-input>
            </el-form-item>
            <el-form-item label="小表目录">
              <el-input v-model="workflow.smallPath.value" placeholder="点击右侧浏览" readonly>
                <template #append>
                  <el-button @click="onBrowsePath('small')">浏览</el-button>
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
          <span v-if="workflow.findFilesMessage.value" :class="workflow.pathLocked.value ? 'soft-note' : 'soft-note text--error'" style="margin-left: 12px">
            {{ workflow.findFilesMessage.value }}
          </span>
          <div v-if="workflow.pathLocked.value" class="soft-note" style="margin-top: 8px">
            大表: {{ workflow.foundFileBig.value }}<br />
            小表: {{ workflow.foundFileSmall.value }}
          </div>
        </div>
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
          <el-input v-model="workflow.vegText.value" type="textarea" :rows="4" placeholder="青椒&#10;蘑菇&#10;..." />
          <div class="action-cluster">
            <el-button type="primary" :icon="Setting" @click="workflow.onGenerateRates">生成抑制率</el-button>
            <el-button @click="workflow.onClearVeg">清空</el-button>
            <span class="soft-note">{{ workflow.vegStatus.value }}</span>
          </div>
        </el-form-item>

        <el-form-item label="JSON（可手动编辑）">
          <el-input v-model="workflow.jsonText.value" type="textarea" :rows="8" placeholder="生成后的 JSON 会显示在这里" />
          <div class="action-cluster">
            <el-button @click="workflow.onFormatJson">格式化</el-button>
            <el-button @click="workflow.onDedupJson">去重</el-button>
            <el-button @click="workflow.onClearJson">清空</el-button>
            <span class="soft-note">{{ workflow.jsonStatus.value }}</span>
          </div>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 步骤 03 · 模板库 -->
    <el-card shadow="never" class="panel-card">
      <div class="panel-heading">
        <div>
          <div class="panel-heading__eyebrow">步骤 03 · 模板库（可选）</div>
          <h2 class="panel-heading__title">保存常用模板</h2>
          <p class="panel-heading__description">上传后的模板可供月度批量复用，无需每次选择。</p>
        </div>
      </div>

      <div class="field-grid two-up">
        <div class="template-item">
          <div class="template-item__label">大表模板</div>
          <div class="template-item__info">
            <template v-if="workflow.templateStatus.value?.big_template.configured">
              <el-tag type="success" size="small">已保存</el-tag>
              <span>{{ workflow.templateStatus.value.big_template.filename }}</span>
              <span class="soft-note">{{ workflow.templateStatus.value.big_template.updated_at }}</span>
            </template>
            <span v-else class="soft-note">尚未保存</span>
          </div>
          <el-upload :auto-upload="false" :show-file-list="false" :on-change="(f: UploadRawFile) => onTemplateChange('big', f)">
            <el-button size="small">重新上传</el-button>
          </el-upload>
        </div>
        <div class="template-item">
          <div class="template-item__label">小表模板</div>
          <div class="template-item__info">
            <template v-if="workflow.templateStatus.value?.small_template.configured">
              <el-tag type="success" size="small">已保存</el-tag>
              <span>{{ workflow.templateStatus.value.small_template.filename }}</span>
              <span class="soft-note">{{ workflow.templateStatus.value.small_template.updated_at }}</span>
            </template>
            <span v-else class="soft-note">尚未保存</span>
          </div>
          <el-upload :auto-upload="false" :show-file-list="false" :on-change="(f: UploadRawFile) => onTemplateChange('small', f)">
            <el-button size="small">重新上传</el-button>
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

    <!-- 月度批量 -->
    <el-card shadow="never" class="panel-card">
      <div class="panel-heading">
        <div>
          <div class="panel-heading__eyebrow">月度批量</div>
          <h2 class="panel-heading__title">批量生成全月检测报告</h2>
          <p class="panel-heading__description">输入月份和每日蔬菜清单，解析后批量生成该月所有检测报告。</p>
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

        <el-form-item label="每日清单（文本或上传文件）">
          <el-input
            v-model="workflow.monthListText.value"
            type="textarea"
            :rows="6"
            placeholder="格式：每行一条，日期在前，品种用逗号或空格分隔&#10;示例：&#10;4月1日 青椒 蘑菇 番茄&#10;4月2日 黄瓜 白菜 萝卜&#10;或直接上传 Excel / TXT 文件"
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

        <!-- 解析结果预览 -->
        <el-form-item v-if="workflow.monthEntries.value.length > 0" label="解析结果预览">
          <el-table :data="workflow.monthEntries.value" size="small" max-height="300" stripe>
            <el-table-column prop="date" label="日期" width="120" />
            <el-table-column prop="names" label="品种列表">
              <template #default="{ row }">{{ (row.names as string[]).join(', ') }}</template>
            </el-table-column>
            <el-table-column label="品种数" width="80">
              <template #default="{ row }">{{ (row.names as string[]).length }}</template>
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

        <!-- 模板选择 -->
        <el-form-item label="模板来源">
          <el-radio-group v-model="workflow.monthUseSavedTemplates.value">
            <el-radio :value="true">使用已保存模板</el-radio>
            <el-radio :value="false">上传临时模板</el-radio>
          </el-radio-group>
        </el-form-item>

        <div v-if="!workflow.monthUseSavedTemplates.value" class="field-grid two-up">
          <el-form-item label="大表模板">
            <el-upload :auto-upload="false" :show-file-list="false" :on-change="(f: UploadRawFile) => onMonthTemplateChange('big', f)">
              <el-button size="small">选择文件</el-button>
              <template #tip>
                <span class="soft-note">{{ monthTemplateNames.big || '未选择' }}</span>
              </template>
            </el-upload>
          </el-form-item>
          <el-form-item label="小表模板">
            <el-upload :auto-upload="false" :show-file-list="false" :on-change="(f: UploadRawFile) => onMonthTemplateChange('small', f)">
              <el-button size="small">选择文件</el-button>
              <template #tip>
                <span class="soft-note">{{ monthTemplateNames.small || '未选择' }}</span>
              </template>
            </el-upload>
          </el-form-item>
        </div>

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

    <StatusLog ref="statusLogRef" />
  </div>
</template>
```

**Script 部分：**
```ts
import { computed, ref } from 'vue'
import { Setting } from '@element-plus/icons-vue'
import type { UploadRawFile } from 'element-plus'
import PageHeader from '../components/PageHeader.vue'
import StatusLog from '../components/StatusLog.vue'
import { usePesticideWorkflow } from '../features/pesticide/composables/usePesticideWorkflow'
import { openPath } from '../features/shared/workflow'
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

function onModeChange(val: boolean) {
  workflow.onSwitchMode(val)
}

async function onBrowsePath(kind: 'big' | 'small') {
  const initialPath = kind === 'big' ? workflow.bigPath.value : workflow.smallPath.value
  const selected = await openPath(dirBrowserRef, initialPath, {
    title: `选择${kind === 'big' ? '大表' : '小表'}目录`,
    mode: 'directory',
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
  }
}

function onFileChange(kind: 'big' | 'small', file: UploadRawFile) {
  const raw = (file as unknown as { raw?: File }).raw ?? (file as unknown as File)
  workflow.setFile(kind, raw)
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
```

**移除：** `el-alert` 重建警告

---

### Task 3: 注册 DirBrowser 全局组件引用

**Files:**
- Modify: `frontend/src/views/Pesticide.vue` (在模板末尾添加 DirBrowser 引用)

模板末尾添加：
```html
<DirBrowser ref="dirBrowserRef" />
```

无需另外注册（components.d.ts 已自动全局注册 DirBrowser）。

---

### Task 4: 验证

运行前端类型检查和编译：
```bash
cd frontend && npx vue-tsc --noEmit
```

修复任何类型错误后提交。
