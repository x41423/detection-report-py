<template>
  <div class="page-shell permission-page">
    <PageHero
      :eyebrow="pageHero.eyebrow"
      :title="pageHero.title"
      :description="pageHero.description"
      tone="sun"
    >
      <template #actions>
        <el-button type="primary" size="large" :loading="isLoading" @click="loadPageData">
          <el-icon><RefreshRight /></el-icon>
          刷新
        </el-button>
      </template>

      <template #aside>
        <div class="permission-hero-metrics">
          <div
            v-for="metric in heroMetrics"
            :key="metric.label"
            class="permission-hero-metric"
            :class="{ 'permission-hero-metric--wide': metric.wide }"
          >
            <span>{{ metric.label }}</span>
            <strong>{{ metric.value }}</strong>
          </div>
        </div>
      </template>
    </PageHero>

    <div v-if="isRequestMode" class="permission-layout">
      <el-card v-if="canCreate" shadow="never" class="panel-card permission-card permission-card--request">
        <div class="panel-heading">
          <div>
            <div class="panel-heading__eyebrow">申请</div>
            <h2 class="panel-heading__title">提交权限申请</h2>
            <p class="panel-heading__description">
              选择需要开通的业务权限并填写使用原因，提交后由管理员审批。
            </p>
          </div>
        </div>

        <el-form label-position="top" class="permission-form" @submit.prevent>
          <el-form-item label="申请权限">
            <el-select
              v-model="selectedPermissionCode"
              filterable
              placeholder="选择一个未开通的业务权限"
              :disabled="requestablePermissions.length === 0"
            >
              <el-option
                v-for="permission in requestablePermissions"
                :key="permission.code"
                :label="`${permission.name}（${permission.code}）`"
                :value="permission.code"
              >
                <div class="permission-option">
                  <strong>{{ permission.name }}</strong>
                  <span>{{ permission.module }} · {{ permission.code }}</span>
                </div>
              </el-option>
            </el-select>
          </el-form-item>

          <el-form-item label="申请原因">
            <el-input
              v-model="requestReason"
              type="textarea"
              :rows="4"
              maxlength="500"
              show-word-limit
              placeholder="例如：需要查看库存余额以完成每日采购核对。"
            />
          </el-form-item>

          <div v-if="selectedPermission" class="permission-selected">
            <span>{{ selectedPermission.module }}</span>
            <strong>{{ selectedPermission.name }}</strong>
            <p>{{ selectedPermission.description || selectedPermission.code }}</p>
          </div>

          <el-button
            type="primary"
            size="large"
            :loading="isSubmitting"
            :disabled="!selectedPermissionCode"
            @click="submitPermissionRequest"
          >
            提交申请
          </el-button>
        </el-form>
      </el-card>

      <el-card shadow="never" class="panel-card permission-card">
        <div class="panel-heading">
          <div>
            <div class="panel-heading__eyebrow">我的申请</div>
            <h2 class="panel-heading__title">申请记录</h2>
            <p class="panel-heading__description">
              这里保留你的权限申请进度。审批通过后刷新账号状态即可看到新增权限。
            </p>
          </div>
        </div>

        <div v-loading="isLoading" class="permission-request-list">
          <article v-for="request in myRequests" :key="request.id" class="permission-request">
            <div class="permission-request__header">
              <div>
                <span>{{ request.permission_module || 'permission' }}</span>
                <h3>{{ request.permission_name }}</h3>
              </div>
              <el-tag :type="statusTagType(request.status)" effect="plain">
                {{ statusLabel(request.status) }}
              </el-tag>
            </div>
            <p>{{ request.reason || '未填写申请原因' }}</p>
            <div class="permission-request__meta">
              <span>{{ request.permission_code }}</span>
              <span>{{ formatDateTime(request.created_at) }}</span>
            </div>
            <div v-if="request.review_comment" class="permission-request__review">
              审批备注：{{ request.review_comment }}
            </div>
          </article>

          <el-empty v-if="!isLoading && myRequests.length === 0" description="暂无权限申请" />
        </div>
      </el-card>
    </div>

    <el-card v-else-if="canReview" shadow="never" class="panel-card permission-card permission-review">
      <div class="permission-review__toolbar">
        <div>
          <div class="panel-heading__eyebrow">审批</div>
          <h2 class="panel-heading__title">审批队列</h2>
          <p class="panel-heading__description">批准后会立即给目标用户写入权限覆盖；拒绝只关闭本次申请。</p>
        </div>

        <el-select v-model="reviewStatusFilter" class="permission-review__filter" @change="loadReviewRequests">
          <el-option label="待审批" value="pending" />
          <el-option label="全部" value="" />
          <el-option label="已批准" value="approved" />
          <el-option label="已拒绝" value="rejected" />
          <el-option label="已取消" value="cancelled" />
        </el-select>
      </div>

      <div v-loading="isReviewLoading" class="permission-review-list">
        <article v-for="request in reviewRequests" :key="request.id" class="permission-review-item">
          <div class="permission-review-item__main">
            <div class="permission-review-item__avatar">
              {{ initials(request.display_name || request.username) }}
            </div>
            <div class="permission-review-item__copy">
              <div class="permission-review-item__topline">
                <strong>{{ request.display_name || request.username }}</strong>
                <el-tag :type="statusTagType(request.status)" effect="plain">
                  {{ statusLabel(request.status) }}
                </el-tag>
              </div>
              <h3>{{ request.permission_name }}</h3>
              <p>{{ request.reason || '未填写申请原因' }}</p>
              <div class="permission-request__meta">
                <span>{{ request.permission_code }}</span>
                <span>{{ formatDateTime(request.created_at) }}</span>
              </div>
            </div>
          </div>

          <div v-if="request.status === 'pending'" class="permission-review-item__actions">
            <el-button
              type="success"
              :loading="reviewingRequestId === request.id"
              @click="handleReview(request, 'approved')"
            >
              批准
            </el-button>
            <el-button
              type="danger"
              plain
              :loading="reviewingRequestId === request.id"
              @click="handleReview(request, 'rejected')"
            >
              拒绝
            </el-button>
          </div>
          <div v-else class="permission-review-item__reviewed">
            <span>{{ request.reviewer_display_name || request.reviewer_username || '未知审批人' }}</span>
            <span>{{ request.reviewed_at ? formatDateTime(request.reviewed_at) : '未记录时间' }}</span>
          </div>
        </article>

        <el-empty v-if="!isReviewLoading && reviewRequests.length === 0" description="暂无审批记录" />
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { RefreshRight } from '@element-plus/icons-vue'

import {
  createPermissionRequest,
  listMyPermissionRequests,
  listPermissionRequests,
  listPermissions,
  reviewPermissionRequest,
  type AuthPermission,
  type AuthPermissionRequest,
} from '../api'
import PageHero from '../components/PageHero.vue'
import { useAuth } from '../composables/useAuth'

const route = useRoute()
const auth = useAuth()

const isLoading = ref(false)
const isReviewLoading = ref(false)
const isSubmitting = ref(false)
const reviewingRequestId = ref<number | null>(null)

const permissions = ref<AuthPermission[]>([])
const myRequests = ref<AuthPermissionRequest[]>([])
const reviewRequests = ref<AuthPermissionRequest[]>([])

const selectedPermissionCode = ref('')
const requestReason = ref('')
const reviewStatusFilter = ref<'pending' | 'approved' | 'rejected' | 'cancelled' | ''>('pending')

const isRequestMode = computed(() => route.name !== 'permission-approvals')
const canCreate = computed(() => auth.hasPermission('permission_request:create'))
const canReview = computed(
  () => auth.isSuperAdmin.value || auth.hasPermission('permission_request:view'),
)

const requestablePermissions = computed(() =>
  permissions.value.filter((permission) => !permission.has_permission),
)
const selectedPermission = computed(() =>
  permissions.value.find((permission) => permission.code === selectedPermissionCode.value) || null,
)

const pageHero = computed(() => {
  if (isRequestMode.value) {
    return {
      eyebrow: '账号 / 权限申请',
      title: '权限申请中心',
      description: '挑选业务权限并写明用途，等待管理员审批后即可生效。',
    }
  }
  return {
    eyebrow: '账号 / 审批',
    title: '权限审批工作台',
    description: '审阅成员发起的权限申请，按状态过滤并完成批准或拒绝。',
  }
})

const heroMetrics = computed(() => {
  if (isRequestMode.value) {
    return [
      { label: '可申请权限', value: requestablePermissions.value.length, wide: false },
      {
        label: '待审批',
        value: myRequests.value.filter((req) => req.status === 'pending').length,
        wide: false,
      },
      { label: '历史申请', value: myRequests.value.length, wide: false },
    ]
  }
  const pending = reviewRequests.value.filter((req) => req.status === 'pending').length
  return [
    { label: '当前列表', value: reviewRequests.value.length, wide: false },
    { label: '待处理', value: pending, wide: false },
    { label: '过滤状态', value: reviewStatusFilter.value || '全部', wide: true },
  ]
})

function statusLabel(status: AuthPermissionRequest['status']) {
  switch (status) {
    case 'approved':
      return '已批准'
    case 'rejected':
      return '已拒绝'
    case 'cancelled':
      return '已取消'
    case 'pending':
    default:
      return '待审批'
  }
}

function statusTagType(status: AuthPermissionRequest['status']) {
  switch (status) {
    case 'approved':
      return 'success'
    case 'rejected':
      return 'danger'
    case 'cancelled':
      return 'info'
    case 'pending':
    default:
      return 'warning'
  }
}

function initials(name: string): string {
  const trimmed = (name || '').trim()
  if (!trimmed) return '?'
  return trimmed.slice(0, 2).toUpperCase()
}

function formatDateTime(value: string | null | undefined) {
  if (!value) return '-'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString('zh-CN', { hour12: false })
}

async function loadPermissions() {
  try {
    const { data } = await listPermissions()
    permissions.value = data.permissions
  } catch (error) {
    console.error('Failed to load permissions catalog', error)
    ElMessage.error('加载权限目录失败')
  }
}

async function loadMyRequests() {
  try {
    const { data } = await listMyPermissionRequests()
    myRequests.value = data.requests
  } catch (error) {
    console.error('Failed to load my permission requests', error)
    ElMessage.error('加载申请记录失败')
  }
}

async function loadReviewRequests() {
  if (!canReview.value) return
  isReviewLoading.value = true
  try {
    const { data } = await listPermissionRequests(reviewStatusFilter.value || undefined)
    reviewRequests.value = data.requests
  } catch (error) {
    console.error('Failed to load review queue', error)
    ElMessage.error('加载审批队列失败')
  } finally {
    isReviewLoading.value = false
  }
}

async function loadPageData() {
  isLoading.value = true
  try {
    if (isRequestMode.value) {
      await Promise.all([loadPermissions(), loadMyRequests()])
    } else {
      await loadReviewRequests()
    }
  } finally {
    isLoading.value = false
  }
}

async function submitPermissionRequest() {
  if (!selectedPermissionCode.value) return
  isSubmitting.value = true
  try {
    await createPermissionRequest({
      permission_code: selectedPermissionCode.value,
      reason: requestReason.value.trim(),
    })
    ElMessage.success('权限申请已提交，等待审批')
    selectedPermissionCode.value = ''
    requestReason.value = ''
    await loadMyRequests()
  } catch (error: any) {
    const detail = error?.response?.data?.detail
    const message = (detail && (detail.message || detail)) || error?.message || '申请提交失败'
    ElMessage.error(typeof message === 'string' ? message : '申请提交失败')
  } finally {
    isSubmitting.value = false
  }
}

async function handleReview(
  request: AuthPermissionRequest,
  status: 'approved' | 'rejected',
) {
  const verb = status === 'approved' ? '批准' : '拒绝'
  let comment = ''
  try {
    const result = await ElMessageBox.prompt(
      `请填写${verb}备注（可留空）`,
      `${verb}权限申请`,
      {
        confirmButtonText: verb,
        cancelButtonText: '取消',
        inputType: 'textarea',
        inputPlaceholder: '可写入审批意见，留空也可以',
        inputValue: '',
      },
    )
    comment = (result.value || '').trim()
  } catch {
    return
  }

  reviewingRequestId.value = request.id
  try {
    await reviewPermissionRequest(request.id, { status, review_comment: comment })
    ElMessage.success(`已${verb}权限申请`)
    await loadReviewRequests()
  } catch (error: any) {
    const detail = error?.response?.data?.detail
    const message = (detail && (detail.message || detail)) || error?.message || `${verb}失败`
    ElMessage.error(typeof message === 'string' ? message : `${verb}失败`)
  } finally {
    reviewingRequestId.value = null
  }
}

watch(
  () => route.name,
  () => {
    void loadPageData()
  },
)

onMounted(() => {
  void loadPageData()
})
</script>

<style scoped>
.permission-page {
  display: grid;
  gap: 22px;
}

.permission-hero-metrics {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.permission-hero-metric {
  display: grid;
  gap: 4px;
  padding: 14px 18px;
  border-radius: var(--radius-lg);
  background: var(--color-surface-card);
  border: 1px solid var(--color-border);
}

.permission-hero-metric span {
  font-size: 12px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  opacity: 0.78;
}

.permission-hero-metric strong {
  font-size: 22px;
  font-weight: 600;
}

.permission-hero-metric--wide {
  grid-column: span 2;
}

.permission-layout {
  display: grid;
  grid-template-columns: minmax(0, 1.05fr) minmax(0, 1fr);
  gap: 22px;
}

@media (max-width: 1100px) {
  .permission-layout {
    grid-template-columns: minmax(0, 1fr);
  }
}

.permission-card {
  border-radius: var(--radius-lg);
  padding: 22px 24px;
  background: var(--color-surface-card);
  border: 1px solid var(--color-border);
}

.panel-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
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

.permission-form {
  display: grid;
  gap: 18px;
}

.permission-option {
  display: grid;
  gap: 2px;
  padding: 4px 0;
}

.permission-option span {
  font-size: 12px;
  opacity: 0.65;
}

.permission-selected {
  padding: 12px 14px;
  border-radius: var(--radius-md);
  background: var(--color-primary-soft);
  border: 1px dashed var(--color-border-highlight);
  display: grid;
  gap: 4px;
}

.permission-selected span {
  font-size: 12px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  opacity: 0.7;
}

.permission-selected p {
  margin: 0;
  font-size: 13px;
  opacity: 0.8;
}

.permission-request-list,
.permission-review-list {
  display: grid;
  gap: 14px;
}

.permission-request,
.permission-review-item {
  padding: 16px 18px;
  border-radius: var(--radius-lg);
  background: var(--color-surface-card);
  border: 1px solid var(--color-border);
  display: grid;
  gap: 10px;
}

.permission-request__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
}

.permission-request__header span {
  font-size: 12px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  opacity: 0.65;
}

.permission-request__header h3,
.permission-review-item__copy h3 {
  margin: 4px 0 0;
  font-size: 16px;
  font-weight: 600;
}

.permission-request p,
.permission-review-item__copy p {
  margin: 0;
  font-size: 13px;
  opacity: 0.86;
}

.permission-request__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  font-size: 12px;
  opacity: 0.72;
}

.permission-request__review {
  font-size: 12px;
  padding: 8px 10px;
  border-radius: var(--radius-md);
  background: var(--color-surface-card);
}

.permission-review-item__avatar {
  width: 44px;
  height: 44px;
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  background: var(--color-primary-soft);
  border: 1px solid var(--color-border);
  color: var(--color-text);
  flex-shrink: 0;
}

.permission-review__toolbar {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
}

.permission-review__filter {
  width: 160px;
}

.permission-review-item__main {
  display: flex;
  gap: 14px;
}

.permission-review-item__avatar {
  width: 44px;
  height: 44px;
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.2), rgba(56, 189, 248, 0.18));
  border: 1px solid rgba(99, 102, 241, 0.32);
  color: rgba(15, 23, 42, 0.78);
  flex-shrink: 0;
}

.permission-review-item__copy {
  display: grid;
  gap: 4px;
  flex: 1;
  min-width: 0;
}

.permission-review-item__topline {
  display: flex;
  align-items: center;
  gap: 10px;
}

.permission-review-item__actions {
  display: flex;
  gap: 10px;
  margin-top: 4px;
}

.permission-review-item__reviewed {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  font-size: 12px;
  opacity: 0.74;
}
</style>
