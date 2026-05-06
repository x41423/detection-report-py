<template>
  <div class="page-shell">
    <PageHeader
      eyebrow="报价别名库"
      title="把确认过的名称映射沉淀成长期规则"
      tone="orange"
    >
      <template #actions>
        <el-button type="primary" @click="router.push('/weekly-price')">返回每周报价</el-button>
        <el-button class="alias-page__ghost-button" @click="loadAliases()">刷新别名库</el-button>
      </template>

      <template #aside>
        <div class="hero-metric-grid">
          <div class="hero-metric">
            <span class="hero-metric__label">别名总数</span>
            <span class="hero-metric__value">{{ aliases.length }}</span>
            <span class="hero-metric__note">已保存到配置文件的长期映射</span>
          </div>
          <div class="hero-metric">
            <span class="hero-metric__label">筛选结果</span>
            <span class="hero-metric__value">{{ filteredAliases.length }}</span>
            <span class="hero-metric__note">按当前搜索条件命中的映射数</span>
          </div>
          <div class="hero-metric">
            <span class="hero-metric__label">当前模式</span>
            <span class="hero-metric__value">{{ editingSourceName ? '编辑中' : '新增中' }}</span>
            <span class="hero-metric__note">{{ editingSourceName || '可以直接录入一条新映射' }}</span>
          </div>
          <div class="hero-metric">
            <span class="hero-metric__label">搜索条件</span>
            <span class="hero-metric__value">{{ activeQueryLabel }}</span>
            <span class="hero-metric__note">支持分别按源名称和目标名称过滤</span>
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
              <h2 class="panel-heading__title">新增或编辑别名映射</h2>
              <p class="panel-heading__description">
                源名称来自待更新报价表，目标名称来自参考报价表。这里不校验目标名称是否存在于当前参考表，实际命中在预检查阶段确认。
              </p>
            </div>
          </div>

          <div class="field-grid two-up">
            <el-form label-position="top">
              <el-form-item label="待更新表菜名">
                <el-input
                  v-model="form.source_name"
                  placeholder="例如：沙葛/豆薯/凉薯"
                  clearable
                />
              </el-form-item>
            </el-form>

            <el-form label-position="top">
              <el-form-item label="参考表菜名">
                <el-input
                  v-model="form.target_name"
                  placeholder="例如：沙葛豆薯地瓜"
                  clearable
                />
              </el-form-item>
            </el-form>
          </div>

          <div class="action-cluster">
            <el-button type="primary" :loading="saving" @click="submitAlias">
              {{ editingSourceName ? '保存修改' : '新增映射' }}
            </el-button>
            <el-button class="alias-page__ghost-button" @click="resetForm">清空表单</el-button>
          </div>
        </el-card>

        <el-card shadow="never" class="panel-card">
          <div class="panel-heading">
            <div>
              <div class="panel-heading__eyebrow">步骤 02</div>
              <h2 class="panel-heading__title">搜索与管理别名库</h2>
              <p class="panel-heading__description">
                可以直接搜索源名称或目标名称。来自每周报价预检查页的跳转会把源名称预填到新增表单，但列表默认仍显示全部别名。
              </p>
            </div>
          </div>

          <el-alert
            v-if="incomingSourceName"
            :title="`当前来源菜名：${incomingSourceName}`"
            type="info"
            :closable="false"
            show-icon
            style="margin-bottom: 16px"
          >
            <template #default>
              已帮你把这个菜名带入上面的新增表单。下面列表默认显示全部已添加别名；如果要聚焦查找，再手动输入筛选条件。
            </template>
          </el-alert>

          <div class="field-grid two-up">
            <el-form label-position="top">
              <el-form-item label="搜索待更新表菜名">
                <el-input v-model="sourceQuery" placeholder="按源名称过滤" clearable />
              </el-form-item>
            </el-form>

            <el-form label-position="top">
              <el-form-item label="搜索参考表菜名">
                <el-input v-model="targetQuery" placeholder="按目标名称过滤" clearable />
              </el-form-item>
            </el-form>
          </div>

          <div class="table-toolbar">
            <h3 class="table-toolbar__title">报价别名映射</h3>
            <div class="table-toolbar__actions">
              <div class="table-toolbar__meta">共 {{ filteredAliases.length }} 条结果</div>
              <el-button
                v-if="sourceQuery || targetQuery"
                class="alias-page__ghost-button"
                @click="clearFilters"
              >
                查看全部别名
              </el-button>
            </div>
          </div>

          <div class="table-shell table-shell--wide">
            <el-table
              :data="filteredAliases"
              stripe
              size="small"
              max-height="520"
              v-loading="loading"
              empty-text="当前没有符合条件的报价别名映射"
            >
              <el-table-column prop="source_name" label="待更新表菜名" min-width="220" />
              <el-table-column prop="target_name" label="参考表菜名" min-width="220" />
              <el-table-column
                label="操作"
                :width="isCompactTable ? 170 : 220"
                :fixed="isCompactTable ? undefined : 'right'"
              >
                <template #default="{ row }">
                  <div class="row-actions">
                    <el-button
                      class="alias-row-actions__edit"
                      plain
                      type="primary"
                      size="small"
                      @click="startEdit(row)"
                    >
                      编辑
                    </el-button>
                    <el-button
                      class="alias-row-actions__delete"
                      plain
                      size="small"
                      @click="removeAlias(row.source_name)"
                    >
                      删除
                    </el-button>
                  </div>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </el-card>
      </div>

      <div class="panel-stack panel-stack--rail">
        <el-card shadow="never" class="panel-card">
          <div class="panel-heading">
            <div>
              <div class="panel-heading__eyebrow">使用指引</div>
              <h2 class="panel-heading__title">维护原则</h2>
            </div>
          </div>

          <div class="helper-list">
            <div class="helper-list__item">
              <div class="helper-list__dot" />
              <div class="helper-list__text">只保存人工确认过的同物名称，不要把模糊猜测直接沉淀进别名库。</div>
            </div>
            <div class="helper-list__item">
              <div class="helper-list__dot" />
              <div class="helper-list__text">如果参考表名称发生变化，旧别名不会自动纠错，预检查阶段会把失效映射作为警告提示出来。</div>
            </div>
            <div class="helper-list__item">
              <div class="helper-list__dot" />
              <div class="helper-list__text">建议优先从每周报价页保存建议映射，再在这里做长期清理和命名统一。</div>
            </div>
          </div>
        </el-card>

        <StatusLog ref="statusLogRef" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import PageHeader from '../components/PageHeader.vue'
import StatusLog from '../components/StatusLog.vue'
import { useMediaQuery } from '../composables/useMediaQuery'
import {
  deleteWeeklyPriceAlias,
  getApiErrorMessage,
  getWeeklyPriceAliases,
  upsertWeeklyPriceAliases,
  type WeeklyPriceAliasItem,
} from '../api'
import { markWeeklyPriceAliasRevisionChanged } from '../features/weekly-price/workflowSession'

const router = useRouter()
const route = useRoute()
const isCompactTable = useMediaQuery('(max-width: 768px)')

const aliases = ref<WeeklyPriceAliasItem[]>([])
const loading = ref(false)
const saving = ref(false)
const sourceQuery = ref('')
const targetQuery = ref('')
const editingSourceName = ref('')
const incomingSourceName = ref('')
const form = reactive({
  source_name: '',
  target_name: '',
})

const statusLogRef = ref<InstanceType<typeof StatusLog>>()

const filteredAliases = computed(() => {
  const sourceKeyword = sourceQuery.value.trim().toLowerCase()
  const targetKeyword = targetQuery.value.trim().toLowerCase()

  return aliases.value.filter((item) => {
    const sourceHit =
      !sourceKeyword || item.source_name.toLowerCase().includes(sourceKeyword)
    const targetHit =
      !targetKeyword || item.target_name.toLowerCase().includes(targetKeyword)

    return sourceHit && targetHit
  })
})

const activeQueryLabel = computed(() => {
  const sourceKeyword = sourceQuery.value.trim()
  const targetKeyword = targetQuery.value.trim()

  if (!sourceKeyword && !targetKeyword) {
    return '未筛选'
  }

  const parts = []
  if (sourceKeyword) {
    parts.push(`源:${sourceKeyword}`)
  }
  if (targetKeyword) {
    parts.push(`目标:${targetKeyword}`)
  }
  return parts.join(' / ')
})

async function loadAliases(appendLog: boolean = true) {
  loading.value = true

  try {
    const { data } = await getWeeklyPriceAliases()
    aliases.value = data.aliases || []

    if (appendLog) {
      statusLogRef.value?.append(`别名库已加载，共 ${data.total} 条映射`, 'info')
    }
  } catch (error: any) {
    const detail = getApiErrorMessage(error)
    statusLogRef.value?.append(`加载别名库失败：${detail}`, 'error')
    ElMessage.error('加载别名库失败')
  } finally {
    loading.value = false
  }
}

function applyRouteQuery() {
  const source = String(route.query.source || route.query.q || '').trim()
  incomingSourceName.value = source
  if (!source) return

  if (!editingSourceName.value && !form.source_name.trim()) {
    form.source_name = source
  }
}

function clearFilters() {
  sourceQuery.value = ''
  targetQuery.value = ''
}

function startEdit(item: WeeklyPriceAliasItem) {
  editingSourceName.value = item.source_name
  form.source_name = item.source_name
  form.target_name = item.target_name
  statusLogRef.value?.append(`已载入映射：${item.source_name} → ${item.target_name}`, 'info')
}

function resetForm() {
  editingSourceName.value = ''
  form.source_name = ''
  form.target_name = ''
}

async function submitAlias() {
  const sourceName = form.source_name.trim()
  const targetName = form.target_name.trim()
  if (!sourceName || !targetName) {
    ElMessage.warning('请完整填写源名称和目标名称')
    return
  }

  saving.value = true

  try {
    const renameSource =
      editingSourceName.value && editingSourceName.value !== sourceName

    const { data } = await upsertWeeklyPriceAliases({ [sourceName]: targetName })
    let nextAliases = data.aliases || []

    if (renameSource) {
      const deleted = await deleteWeeklyPriceAlias(editingSourceName.value)
      nextAliases = deleted.data.aliases || []
    }

    aliases.value = nextAliases
    markWeeklyPriceAliasRevisionChanged()
    statusLogRef.value?.append(`已保存映射：${sourceName} → ${targetName}`, 'success')
    ElMessage.success(editingSourceName.value ? '映射已更新' : '映射已新增')
    resetForm()
  } catch (error: any) {
    const detail = getApiErrorMessage(error)
    statusLogRef.value?.append(`保存映射失败：${detail}`, 'error')
    ElMessage.error('保存映射失败')
  } finally {
    saving.value = false
  }
}

async function removeAlias(sourceName: string) {
  try {
    await ElMessageBox.confirm(
      `将删除映射“${sourceName}”，后续预检查和执行将不再使用它。`,
      '确认删除',
      {
        confirmButtonText: '删除',
        cancelButtonText: '取消',
        type: 'warning',
      },
    )
  } catch {
    return
  }

  try {
    const { data } = await deleteWeeklyPriceAlias(sourceName)
    aliases.value = data.aliases || []

    if (editingSourceName.value === sourceName) {
      resetForm()
    }

    markWeeklyPriceAliasRevisionChanged()
    statusLogRef.value?.append(`已删除映射：${sourceName}`, 'success')
    ElMessage.success('映射已删除')
  } catch (error: any) {
    const detail = getApiErrorMessage(error)
    statusLogRef.value?.append(`删除映射失败：${detail}`, 'error')
    ElMessage.error('删除映射失败')
  }
}

watch(
  () => route.query,
  () => {
    applyRouteQuery()
  },
  { immediate: true },
)

onMounted(async () => {
  await loadAliases(false)
  applyRouteQuery()
})
</script>

<style scoped>
.alias-page__ghost-button {
  border-color: rgba(15, 23, 42, 0.12);
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.78), rgba(240, 249, 255, 0.68));
  box-shadow:
    inset 0 0 0 1px rgba(255, 255, 255, 0.62),
    0 10px 20px rgba(15, 23, 42, 0.04);
  color: var(--color-text);
}

.alias-page__ghost-button:hover,
.alias-page__ghost-button:focus {
  border-color: rgba(14, 165, 233, 0.4);
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.92), rgba(224, 242, 254, 0.88));
  box-shadow:
    inset 0 0 0 1px rgba(255, 255, 255, 0.74),
    0 12px 24px rgba(14, 165, 233, 0.08);
}

.table-toolbar__actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.row-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.row-actions :deep(.el-button) {
  min-height: 32px;
  padding: 0 10px;
}

.row-actions :deep(.alias-row-actions__edit) {
  border-color: rgba(14, 165, 233, 0.28);
  background: linear-gradient(135deg, rgba(14, 165, 233, 0.14), rgba(255, 255, 255, 0.48));
  color: var(--color-text);
}

.row-actions :deep(.alias-row-actions__edit:hover),
.row-actions :deep(.alias-row-actions__edit:focus) {
  border-color: rgba(14, 165, 233, 0.5);
  background: linear-gradient(135deg, rgba(14, 165, 233, 0.2), rgba(255, 255, 255, 0.68));
}

.row-actions :deep(.alias-row-actions__delete) {
  border-color: rgba(239, 68, 68, 0.26);
  background: linear-gradient(135deg, rgba(239, 68, 68, 0.12), rgba(255, 255, 255, 0.44));
  color: #991b1b;
}

.row-actions :deep(.alias-row-actions__delete:hover),
.row-actions :deep(.alias-row-actions__delete:focus) {
  border-color: rgba(239, 68, 68, 0.46);
  background: linear-gradient(135deg, rgba(239, 68, 68, 0.18), rgba(255, 255, 255, 0.64));
}

@media (max-width: 768px) {
  .table-toolbar__actions {
    align-items: stretch;
  }

  .row-actions :deep(.el-button) {
    min-height: 34px;
    padding: 0 10px;
  }
}
</style>
