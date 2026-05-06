<template>
  <div class="page-shell user-management-page">
    <PageHero
      eyebrow="用户管理"
      title="管理成员账号与角色"
      description="创建成员账号、调整显示名称和角色绑定，并在账号异常或离职时禁用账号。超级管理员账号受保护，普通管理员不能修改或禁用。"
      tone="teal"
    >
      <template #actions>
        <el-button type="primary" size="large" :loading="isLoading" @click="loadPageData">
          <el-icon><RefreshRight /></el-icon>
          刷新
        </el-button>
        <el-button v-if="canCreate" size="large" @click="openCreateUser">
          <el-icon><CirclePlus /></el-icon>
          新建用户
        </el-button>
      </template>

      <template #aside>
        <div class="user-hero-metrics">
          <div class="user-hero-metric">
            <span>用户总数</span>
            <strong>{{ users.length }}</strong>
          </div>
          <div class="user-hero-metric">
            <span>启用账号</span>
            <strong>{{ activeUserCount }}</strong>
          </div>
          <div class="user-hero-metric user-hero-metric--wide">
            <span>可分配角色</span>
            <strong>{{ assignableRoles.length }}</strong>
          </div>
        </div>
      </template>
    </PageHero>

    <el-card shadow="never" class="panel-card user-toolbar">
      <div>
        <div class="panel-heading__eyebrow">成员</div>
        <h2 class="panel-heading__title">用户列表</h2>
        <p class="panel-heading__description">
          角色绑定会影响用户可见导航和后端 API 权限。禁用账号会同步撤销该账号所有未失效会话。
        </p>
      </div>
      <el-tag v-if="!canUpdate || !canDisable" type="warning" effect="plain">
        当前账号只有部分用户管理权限
      </el-tag>
    </el-card>

    <div v-loading="isLoading" class="user-grid">
      <el-card
        v-for="user in users"
        :key="user.id"
        shadow="never"
        class="panel-card user-card"
        :class="{ 'user-card--disabled': !user.is_active, 'user-card--super': user.is_super_admin }"
      >
        <div class="user-card__topline">
          <div class="user-card__avatar">{{ initials(user.display_name || user.username) }}</div>
          <div class="user-card__badges">
            <el-tag v-if="user.is_super_admin" type="danger" effect="plain">超级管理员</el-tag>
            <el-tag :type="user.is_active ? 'success' : 'info'" effect="plain">
              {{ user.is_active ? '启用' : '禁用' }}
            </el-tag>
          </div>
        </div>

        <div class="user-card__main">
          <h2>{{ user.display_name || user.username }}</h2>
          <p>{{ user.username }}</p>
        </div>

        <div class="user-card__roles">
          <el-tag v-for="role in user.roles" :key="role" effect="plain">
            {{ roleLabel(role) }}
          </el-tag>
        </div>

        <div class="user-card__facts">
          <div>
            <span>有效会话</span>
            <strong>{{ user.active_session_count }}</strong>
          </div>
          <div>
            <span>最近登录</span>
            <strong>{{ formatDateTime(user.last_login_at) }}</strong>
          </div>
          <div>
            <span>创建时间</span>
            <strong>{{ formatDateTime(user.created_at) }}</strong>
          </div>
          <div>
            <span>权限数</span>
            <strong>{{ user.permissions.length }}</strong>
          </div>
        </div>

        <div class="user-card__actions">
          <el-button
            v-if="canUpdate"
            :disabled="isProtectedSuperAdmin(user)"
            @click="openEditUser(user)"
          >
            <el-icon><EditPen /></el-icon>
            编辑
          </el-button>
          <el-button
            v-if="canDisable"
            :type="user.is_active ? 'danger' : 'success'"
            plain
            :disabled="isProtectedSuperAdmin(user) || user.id === auth.currentUser.value?.id"
            :loading="mutatingUserId === user.id"
            @click="toggleUserActive(user)"
          >
            <el-icon>
              <Lock v-if="user.is_active" />
              <Unlock v-else />
            </el-icon>
            {{ user.is_active ? '禁用' : '启用' }}
          </el-button>
        </div>
      </el-card>

      <el-empty v-if="!isLoading && users.length === 0" description="暂无用户" />
    </div>

    <el-dialog v-model="userDialogOpen" :title="userDialogTitle" width="min(92vw, 520px)">
      <el-form label-position="top" class="user-form">
        <el-form-item v-if="userDialogMode === 'create'" label="账号">
          <el-input v-model.trim="userForm.username" placeholder="例如：buyer.team1" />
        </el-form-item>
        <el-form-item label="显示名称">
          <el-input v-model.trim="userForm.display_name" placeholder="例如：采购一组" />
        </el-form-item>
        <el-form-item v-if="userDialogMode === 'create'" label="初始密码">
          <el-input v-model="userForm.password" type="password" show-password placeholder="至少 8 位" />
        </el-form-item>
        <el-form-item label="角色">
          <el-select
            v-model="userForm.role_codes"
            multiple
            filterable
            :disabled="Boolean(editingUser?.is_super_admin)"
            placeholder="选择角色"
          >
            <el-option
              v-for="role in assignableRoles"
              :key="role.code"
              :label="role.name"
              :value="role.code"
            >
              <span>{{ role.name }}</span>
              <span class="user-form__role-code">{{ role.code }}</span>
            </el-option>
          </el-select>
        </el-form-item>
        <el-form-item v-if="userDialogMode === 'edit'" label="账号状态">
          <el-switch
            v-model="userForm.is_active"
            :disabled="editingUser?.id === auth.currentUser.value?.id || Boolean(editingUser?.is_super_admin)"
            active-text="启用"
            inactive-text="禁用"
          />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="userDialogOpen = false">取消</el-button>
        <el-button type="primary" :loading="isSavingUser" @click="saveUser">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { CirclePlus, EditPen, Lock, RefreshRight, Unlock } from '@element-plus/icons-vue'

import {
  createManagedUser,
  listManagedUsers,
  listRoles,
  updateManagedUser,
  type AuthManagedUser,
  type AuthRole,
} from '../api/auth'
import { getApiErrorMessage } from '../api/errors'
import PageHero from '../components/PageHero.vue'
import { useAuth } from '../composables/useAuth'

type UserDialogMode = 'create' | 'edit'

const auth = useAuth()
const users = ref<AuthManagedUser[]>([])
const roles = ref<AuthRole[]>([])
const isLoading = ref(false)
const isSavingUser = ref(false)
const mutatingUserId = ref<number | null>(null)
const userDialogOpen = ref(false)
const userDialogMode = ref<UserDialogMode>('create')
const editingUser = ref<AuthManagedUser | null>(null)
const userForm = reactive({
  username: '',
  password: '',
  display_name: '',
  role_codes: ['member'] as string[],
  is_active: true,
})

const canCreate = computed(() => auth.hasPermission('user:create'))
const canUpdate = computed(() => auth.hasPermission('user:update'))
const canDisable = computed(() => auth.hasPermission('user:disable'))
const activeUserCount = computed(() => users.value.filter((user) => user.is_active).length)
const assignableRoles = computed(() => roles.value.filter((role) => role.code !== 'super_admin'))
const userDialogTitle = computed(() => (userDialogMode.value === 'create' ? '新建用户' : '编辑用户'))
const roleNameMap = computed(() => new Map(roles.value.map((role) => [role.code, role.name])))

onMounted(() => {
  void loadPageData()
})

async function loadPageData() {
  isLoading.value = true
  try {
    const [usersResponse, rolesResponse] = await Promise.all([listManagedUsers(), listRoles()])
    users.value = usersResponse.data.users
    roles.value = rolesResponse.data.roles
  } catch (error) {
    ElMessage.error(getApiErrorMessage(error, '用户数据加载失败'))
  } finally {
    isLoading.value = false
  }
}

function openCreateUser() {
  userDialogMode.value = 'create'
  editingUser.value = null
  userForm.username = ''
  userForm.password = ''
  userForm.display_name = ''
  userForm.role_codes = ['member']
  userForm.is_active = true
  userDialogOpen.value = true
}

function openEditUser(user: AuthManagedUser) {
  userDialogMode.value = 'edit'
  editingUser.value = user
  userForm.username = user.username
  userForm.password = ''
  userForm.display_name = user.display_name
  userForm.role_codes = user.roles.filter((role) => role !== 'super_admin')
  userForm.is_active = user.is_active
  userDialogOpen.value = true
}

async function saveUser() {
  if (userDialogMode.value === 'create' && !userForm.username) {
    ElMessage.warning('请输入账号')
    return
  }
  if (userDialogMode.value === 'create' && userForm.password.length < 8) {
    ElMessage.warning('初始密码至少 8 位')
    return
  }
  if (userForm.role_codes.length === 0) {
    ElMessage.warning('至少选择一个角色')
    return
  }

  isSavingUser.value = true
  try {
    if (userDialogMode.value === 'create') {
      const response = await createManagedUser({
        username: userForm.username,
        password: userForm.password,
        display_name: userForm.display_name || undefined,
        role_codes: userForm.role_codes,
      })
      users.value = [response.data.user, ...users.value]
      ElMessage.success('用户已创建')
    } else if (editingUser.value) {
      const response = await updateManagedUser(editingUser.value.id, {
        display_name: userForm.display_name,
        role_codes: editingUser.value.is_super_admin ? undefined : userForm.role_codes,
        is_active: editingUser.value.is_super_admin ? undefined : userForm.is_active,
      })
      replaceUser(response.data.user)
      ElMessage.success('用户已更新')
    }
    userDialogOpen.value = false
  } catch (error) {
    ElMessage.error(getApiErrorMessage(error, '用户保存失败'))
  } finally {
    isSavingUser.value = false
  }
}

async function toggleUserActive(user: AuthManagedUser) {
  try {
    await ElMessageBox.confirm(
      user.is_active ? '禁用账号会立即撤销该用户的所有登录会话。' : '启用后该用户可以重新登录。',
      user.is_active ? '确认禁用账号' : '确认启用账号',
      {
        type: 'warning',
        confirmButtonText: user.is_active ? '禁用' : '启用',
        cancelButtonText: '取消',
      },
    )
    mutatingUserId.value = user.id
    const response = await updateManagedUser(user.id, { is_active: !user.is_active })
    replaceUser(response.data.user)
    ElMessage.success(user.is_active ? '账号已禁用' : '账号已启用')
  } catch (error) {
    if (!isMessageBoxCancel(error)) {
      ElMessage.error(getApiErrorMessage(error, '账号状态更新失败'))
    }
  } finally {
    mutatingUserId.value = null
  }
}

function replaceUser(nextUser: AuthManagedUser) {
  users.value = users.value.map((user) => (user.id === nextUser.id ? nextUser : user))
}

function roleLabel(roleCode: string) {
  return roleNameMap.value.get(roleCode) ?? roleCode
}

function isProtectedSuperAdmin(user: AuthManagedUser) {
  return user.is_super_admin && !auth.isSuperAdmin.value
}

function initials(value: string) {
  return value.trim().slice(0, 2).toUpperCase() || '用户'
}

function formatDateTime(value: string | null) {
  if (!value) {
    return '从未'
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

function isMessageBoxCancel(error: unknown) {
  return error === 'cancel' || error === 'close'
}
</script>

<style scoped>
.user-management-page {
  gap: 16px;
}

.user-hero-metrics {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
  width: 100%;
}

.user-hero-metric {
  display: grid;
  gap: 6px;
  padding: 14px;
  border-radius: var(--radius-md);
  background: #ffffff;
  box-shadow: var(--shadow-glass);
}

.user-hero-metric--wide {
  grid-column: 1 / -1;
}

.user-hero-metric span {
  color: var(--color-muted-soft);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}

.user-hero-metric strong {
  color: var(--color-text);
  font-family: var(--font-heading);
  font-size: clamp(22px, 3vw, 30px);
  font-weight: 600;
  line-height: 1.1;
}

.user-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  padding: 20px;
}

.user-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
  min-height: 240px;
}

.user-card {
  border-radius: var(--radius-lg);
  background: #ffffff;
}

.user-card :deep(.el-card__body) {
  display: grid;
  gap: 16px;
}

.user-card--super {
  box-shadow:
    inset 0 0 0 1px rgba(36, 36, 36, 0.28),
    var(--shadow-glass);
}

.user-card--disabled {
  opacity: 0.68;
}

.user-card__topline,
.user-card__actions {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
}

.user-card__actions {
  flex-wrap: wrap;
}

.user-card__avatar {
  display: grid;
  place-items: center;
  width: 42px;
  height: 42px;
  border-radius: var(--radius-md);
  background: #242424;
  color: #ffffff;
  font-family: var(--font-heading);
  font-weight: 600;
}

.user-card__badges,
.user-card__roles {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 8px;
}

.user-card__roles {
  justify-content: flex-start;
}

.user-card__main h2,
.user-card__main p {
  margin: 0;
}

.user-card__main h2 {
  color: var(--color-text);
  font-family: var(--font-heading);
  font-size: 22px;
  font-weight: 600;
}

.user-card__main p {
  margin-top: 4px;
  color: var(--color-muted);
  font-size: 13px;
}

.user-card__facts {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.user-card__facts div {
  display: grid;
  gap: 6px;
  min-width: 0;
  padding: 12px;
  border-radius: var(--radius-md);
  background: #fafafa;
  box-shadow: inset 0 0 0 1px rgba(34, 42, 53, 0.08);
}

.user-card__facts span {
  color: var(--color-muted-soft);
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.user-card__facts strong {
  color: var(--color-text);
  font-family: var(--font-body);
  font-weight: 600;
  font-size: 13px;
  overflow-wrap: anywhere;
}

.user-form {
  display: grid;
  gap: 2px;
}

.user-form :deep(.el-select) {
  width: 100%;
}

.user-form__role-code {
  float: right;
  color: var(--color-muted-soft);
  font-size: 12px;
}

@media (max-width: 1280px) {
  .user-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 860px) {
  .user-grid {
    grid-template-columns: 1fr;
  }

  .user-toolbar {
    align-items: flex-start;
    flex-direction: column;
  }
}

@media (max-width: 520px) {
  .user-hero-metrics,
  .user-card__facts {
    grid-template-columns: 1fr;
  }

  .user-card__actions .el-button {
    width: 100%;
  }
}
</style>
