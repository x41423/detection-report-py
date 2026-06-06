<template>
  <div class="page-shell audit-page page-shell--full">
    <PageHero
      eyebrow="审计追踪"
      title="查看关键账号与权限操作"
      description="集中查看登录、设备、权限申请、用户和角色变更记录。审计日志只展示必要上下文，不展示密码、token 或其它认证密钥。"
      tone="sun"
    >
      <template #actions>
        <el-button type="primary" size="large" :loading="isLoading" @click="loadAuditLogs">
          <el-icon><RefreshRight /></el-icon>
          刷新日志
        </el-button>
      </template>

      <template #aside>
        <div class="audit-hero-metrics">
          <div class="audit-hero-metric">
            <span>本次返回</span>
            <strong>{{ logs.length }}</strong>
          </div>
          <div class="audit-hero-metric">
            <span>失败事件</span>
            <strong>{{ failureCount }}</strong>
          </div>
          <div class="audit-hero-metric audit-hero-metric--wide">
            <span>涉及模块</span>
            <strong>{{ moduleCount }}</strong>
          </div>
        </div>
      </template>
    </PageHero>

    <el-card shadow="never" class="panel-card audit-filter-card">
      <div>
        <div class="panel-heading__eyebrow">筛选</div>
        <h2 class="panel-heading__title">筛选审计记录</h2>
        <p class="panel-heading__description">
          默认返回最近 100 条记录。需要定位问题时，优先按模块和结果过滤，再用动作关键字缩小范围。
        </p>
      </div>

      <el-form class="audit-filters" label-position="top" @submit.prevent>
        <el-form-item label="模块">
          <el-select v-model="filters.module" clearable placeholder="全部模块">
            <el-option label="认证" value="auth" />
            <el-option label="设备" value="device" />
            <el-option label="权限申请" value="permission_request" />
            <el-option label="用户" value="user" />
            <el-option label="角色" value="role" />
          </el-select>
        </el-form-item>
        <el-form-item label="结果">
          <el-select v-model="filters.result" clearable placeholder="全部结果">
            <el-option label="成功" value="success" />
            <el-option label="失败" value="failure" />
            <el-option label="待处理" value="pending" />
          </el-select>
        </el-form-item>
        <el-form-item label="动作">
          <el-input v-model.trim="filters.action" clearable placeholder="例如：login / user_update" />
        </el-form-item>
        <el-form-item label="数量">
          <el-input-number v-model="filters.limit" :min="1" :max="200" controls-position="right" />
        </el-form-item>
        <el-form-item class="audit-filters__actions">
          <el-button type="primary" :loading="isLoading" @click="loadAuditLogs">查询</el-button>
          <el-button @click="resetFilters">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card shadow="never" class="panel-card audit-list-card">
      <div class="audit-list-card__header">
        <div>
          <div class="panel-heading__eyebrow">时间线</div>
          <h2 class="panel-heading__title">最近审计日志</h2>
        </div>
        <el-tag effect="plain">{{ responseTotal }} 条</el-tag>
      </div>

      <div v-loading="isLoading" class="audit-list">
        <article v-for="log in logs" :key="log.id" class="audit-item" :class="`audit-item--${log.result}`">
          <div class="audit-item__marker" />
          <div class="audit-item__content">
            <div class="audit-item__topline">
              <div>
                <span>{{ moduleLabel(log.module) }}</span>
                <h3>{{ actionLabel(log.action) }}</h3>
              </div>
              <el-tag :type="resultTagType(log.result)" effect="plain">
                {{ resultLabel(log.result) }}
              </el-tag>
            </div>

            <p>{{ log.description || '无描述' }}</p>

            <div class="audit-item__meta">
              <span>操作者：{{ userLabel(log.actor_display_name, log.actor_username) }}</span>
              <span>目标：{{ userLabel(log.target_display_name, log.target_username) }}</span>
              <span>IP：{{ log.ip_address || '未知' }}</span>
              <span>{{ formatDateTime(log.created_at) }}</span>
            </div>

            <div v-if="log.user_agent" class="audit-item__agent">
              {{ summarizeUserAgent(log.user_agent) }}
            </div>
          </div>
        </article>

        <el-empty v-if="!isLoading && logs.length === 0" description="暂无审计记录" />
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { RefreshRight } from '@element-plus/icons-vue'

import { listAuditLogs, type AuthAuditLog, type AuditLogFilters } from '../api/auth'
import { getApiErrorMessage } from '../api/errors'
import PageHero from '../components/PageHero.vue'

const DEFAULT_FILTERS: Required<Pick<AuditLogFilters, 'limit'>> & Omit<AuditLogFilters, 'limit'> = {
  limit: 100,
  module: '',
  action: '',
  result: '',
}

const logs = ref<AuthAuditLog[]>([])
const responseTotal = ref(0)
const isLoading = ref(false)
const filters = reactive<AuditLogFilters>({ ...DEFAULT_FILTERS })

const failureCount = computed(() => logs.value.filter((log) => log.result === 'failure').length)
const moduleCount = computed(() => new Set(logs.value.map((log) => log.module)).size)

onMounted(() => {
  void loadAuditLogs()
})

async function loadAuditLogs() {
  isLoading.value = true
  try {
    const response = await listAuditLogs(cleanFilters())
    logs.value = response.data.logs
    responseTotal.value = response.data.total
  } catch (error) {
    ElMessage.error(getApiErrorMessage(error, '审计日志加载失败'))
  } finally {
    isLoading.value = false
  }
}

function resetFilters() {
  Object.assign(filters, DEFAULT_FILTERS)
  void loadAuditLogs()
}

function cleanFilters(): AuditLogFilters {
  return {
    limit: filters.limit || 100,
    module: filters.module || undefined,
    action: filters.action || undefined,
    result: filters.result || undefined,
  }
}

function moduleLabel(module: string) {
  const labels: Record<string, string> = {
    auth: '认证',
    device: '设备',
    permission_request: '权限申请',
    user: '用户',
    role: '角色',
    audit: '审计',
  }
  return labels[module] ?? module
}

function actionLabel(action: string) {
  const labels: Record<string, string> = {
    register: '注册',
    login: '登录',
    login_device_limit: '设备上限登录',
    device_replace_login: '替换设备登录',
    refresh: '刷新会话',
    logout: '退出登录',
    device_rename: '重命名设备',
    device_revoke: '撤销设备',
    permission_request_create: '提交权限申请',
    permission_request_review: '审批权限申请',
    user_create: '创建用户',
    user_update: '更新用户',
    role_create: '创建角色',
    role_update: '更新角色',
    role_delete: '删除角色',
  }
  return labels[action] ?? action
}

function resultLabel(result: AuthAuditLog['result']) {
  if (result === 'failure') {
    return '失败'
  }
  if (result === 'pending') {
    return '待处理'
  }
  return '成功'
}

function resultTagType(result: AuthAuditLog['result']) {
  if (result === 'failure') {
    return 'danger'
  }
  if (result === 'pending') {
    return 'warning'
  }
  return 'success'
}

function userLabel(displayName: string | null, username: string | null) {
  return displayName || username || '系统'
}

function summarizeUserAgent(userAgent: string) {
  return userAgent.length > 180 ? `${userAgent.slice(0, 180)}...` : userAgent
}

function formatDateTime(value: string | null) {
  if (!value) {
    return '未知'
  }
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return value
  }
  return new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date)
}
</script>

<style scoped>
.audit-page {
  gap: 16px;
}

.audit-hero-metrics {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
  width: 100%;
}

.audit-hero-metric {
  display: grid;
  gap: 6px;
  padding: 14px;
  border-radius: var(--radius-md);
  background: #ffffff;
  box-shadow: var(--shadow-glass);
}

.audit-hero-metric--wide {
  grid-column: 1 / -1;
}

.audit-hero-metric span {
  color: var(--color-muted-soft);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}

.audit-hero-metric strong {
  color: var(--color-text);
  font-family: var(--font-heading);
  font-size: clamp(22px, 3vw, 30px);
  font-weight: 600;
  line-height: 1.1;
}

.audit-filter-card {
  display: grid;
  gap: 16px;
  padding: 20px;
}

.audit-filters {
  display: grid;
  grid-template-columns: minmax(150px, 0.8fr) minmax(130px, 0.7fr) minmax(180px, 1fr) 132px auto;
  gap: 12px;
  align-items: end;
}

.audit-filters :deep(.el-select),
.audit-filters :deep(.el-input-number) {
  width: 100%;
}

.audit-filters__actions :deep(.el-form-item__content) {
  display: flex;
  flex-wrap: nowrap;
  gap: 10px;
}

.audit-list-card {
  border-radius: var(--radius-lg);
}

.audit-list-card :deep(.el-card__body) {
  display: grid;
  gap: 16px;
}

.audit-list-card__header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
}

.audit-list {
  display: grid;
  gap: 10px;
  min-height: 240px;
}

.audit-item {
  display: grid;
  grid-template-columns: 8px minmax(0, 1fr);
  gap: 14px;
  padding: 16px;
  border-radius: var(--radius-md);
  background: #ffffff;
  box-shadow: var(--shadow-glass);
}

.audit-item__marker {
  width: 8px;
  min-height: 100%;
  border-radius: var(--radius-sm);
  background: #10b981;
}

.audit-item--failure .audit-item__marker {
  background: #ef4444;
}

.audit-item--pending .audit-item__marker {
  background: #f59e0b;
}

.audit-item__content {
  display: grid;
  gap: 10px;
  min-width: 0;
}

.audit-item__topline {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
}

.audit-item__topline span {
  color: var(--color-muted-soft);
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.audit-item h3,
.audit-item p {
  margin: 0;
}

.audit-item h3 {
  margin-top: 4px;
  color: var(--color-text);
  font-family: var(--font-heading);
  font-size: 18px;
  font-weight: 600;
}

.audit-item p {
  color: var(--color-muted);
  font-size: 13px;
  line-height: 1.7;
}

.audit-item__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 10px 14px;
  color: var(--color-muted-soft);
  font-size: 12px;
}

.audit-item__agent {
  padding: 10px 12px;
  border-radius: var(--radius-md);
  background: var(--color-surface-card);
  color: var(--color-muted);
  font-size: 12px;
  line-height: 1.6;
  overflow-wrap: anywhere;
}

@media (max-width: 1120px) {
  .audit-filters {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 680px) {
  .audit-filters,
  .audit-hero-metrics {
    grid-template-columns: 1fr;
  }

.audit-filter-card {
    padding: 18px;
  }

  .audit-item {
    grid-template-columns: 1fr;
  }

  .audit-item__marker {
    width: 100%;
    height: 8px;
    min-height: 8px;
  }

  .audit-item__topline,
  .audit-list-card__header {
    flex-direction: column;
  }

  .audit-filters__actions :deep(.el-form-item__content),
  .audit-filters__actions .el-button {
    width: 100%;
  }
}
</style>
