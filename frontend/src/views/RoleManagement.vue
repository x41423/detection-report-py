<template>
  <div class="page-shell role-management-page">
    <PageHero
      eyebrow="角色权限"
      title="维护角色与权限组合"
      description="创建自定义角色、调整角色名称和权限清单，再把角色分配给用户。系统角色保留基础边界，超级管理员角色不能在页面中修改。"
      tone="orange"
    >
      <template #actions>
        <el-button type="primary" size="large" :loading="isLoading" @click="loadPageData">
          <el-icon><RefreshRight /></el-icon>
          刷新
        </el-button>
        <el-button v-if="canCreate" size="large" @click="openCreateRole">
          <el-icon><CirclePlus /></el-icon>
          新建角色
        </el-button>
      </template>

      <template #aside>
        <div class="role-hero-metrics">
          <div class="role-hero-metric">
            <span>角色总数</span>
            <strong>{{ roles.length }}</strong>
          </div>
          <div class="role-hero-metric">
            <span>自定义角色</span>
            <strong>{{ customRoleCount }}</strong>
          </div>
          <div class="role-hero-metric role-hero-metric--wide">
            <span>权限目录</span>
            <strong>{{ permissions.length }}</strong>
          </div>
        </div>
      </template>
    </PageHero>

    <el-card shadow="never" class="panel-card role-toolbar">
      <div>
        <div class="panel-heading__eyebrow">角色</div>
        <h2 class="panel-heading__title">角色列表</h2>
        <p class="panel-heading__description">
          角色变更会影响后续用户权限计算。删除角色前需要先从所有用户身上移除该角色，系统角色只能调整可编辑项，不能删除。
        </p>
      </div>
      <el-tag v-if="!canUpdate || !canDelete" type="warning" effect="plain">
        当前账号只有部分角色管理权限
      </el-tag>
    </el-card>

    <div v-loading="isLoading" class="role-grid">
      <el-card
        v-for="role in roles"
        :key="role.id"
        shadow="never"
        class="panel-card role-card"
        :class="{ 'role-card--system': role.is_system, 'role-card--locked': isSuperAdminRole(role) }"
      >
        <div class="role-card__topline">
          <div>
            <span class="role-card__code">{{ role.code }}</span>
            <h2>{{ role.name }}</h2>
          </div>
          <div class="role-card__badges">
            <el-tag v-if="isSuperAdminRole(role)" type="danger" effect="plain">受保护</el-tag>
            <el-tag :type="role.is_system ? 'info' : 'success'" effect="plain">
              {{ role.is_system ? '系统角色' : '自定义角色' }}
            </el-tag>
          </div>
        </div>

        <p class="role-card__description">
          {{ role.description || '未填写角色说明' }}
        </p>

        <div class="role-card__facts">
          <div>
            <span>绑定用户</span>
            <strong>{{ role.user_count }}</strong>
          </div>
          <div>
            <span>权限数量</span>
            <strong>{{ role.permission_codes.length }}</strong>
          </div>
          <div>
            <span>创建时间</span>
            <strong>{{ formatDateTime(role.created_at) }}</strong>
          </div>
          <div>
            <span>更新时间</span>
            <strong>{{ formatDateTime(role.updated_at) }}</strong>
          </div>
        </div>

        <div class="role-card__permissions">
          <el-tag
            v-for="permissionCode in visiblePermissionCodes(role)"
            :key="permissionCode"
            effect="plain"
            round
          >
            {{ permissionLabel(permissionCode) }}
          </el-tag>
          <el-tag v-if="role.permission_codes.length > 8" type="info" effect="plain" round>
            +{{ role.permission_codes.length - 8 }}
          </el-tag>
          <span v-if="role.permission_codes.length === 0" class="role-card__empty">未绑定权限</span>
        </div>

        <div class="role-card__actions">
          <el-button
            v-if="canUpdate"
            :disabled="isSuperAdminRole(role)"
            @click="openEditRole(role)"
          >
            <el-icon><EditPen /></el-icon>
            编辑
          </el-button>
          <el-button
            v-if="canDelete"
            type="danger"
            plain
            :disabled="role.is_system || role.user_count > 0"
            :loading="deletingRoleId === role.id"
            @click="confirmDeleteRole(role)"
          >
            <el-icon><Delete /></el-icon>
            删除
          </el-button>
        </div>
      </el-card>

      <el-empty v-if="!isLoading && roles.length === 0" description="暂无角色" />
    </div>

    <el-dialog v-model="roleDialogOpen" :title="roleDialogTitle" width="min(92vw, 720px)" append-to-body>
      <el-form label-position="top" class="role-form">
        <el-form-item v-if="roleDialogMode === 'create'" label="角色编码">
          <el-input
            v-model.trim="roleForm.code"
            maxlength="48"
            placeholder="例如：buyer_lead，仅允许小写字母、数字、点、下划线和短横线"
          />
        </el-form-item>
        <el-form-item v-else label="角色编码">
          <el-input v-model="roleForm.code" disabled />
        </el-form-item>
        <el-form-item label="角色名称">
          <el-input v-model.trim="roleForm.name" maxlength="64" placeholder="例如：采购负责人" />
        </el-form-item>
        <el-form-item label="角色说明">
          <el-input
            v-model.trim="roleForm.description"
            type="textarea"
            :rows="3"
            maxlength="300"
            show-word-limit
            placeholder="说明这个角色适合哪些成员使用"
          />
        </el-form-item>
        <el-form-item label="权限清单">
          <el-select
            v-model="roleForm.permission_codes"
            multiple
            filterable
            collapse-tags
            collapse-tags-tooltip
            placeholder="选择角色拥有的权限"
          >
            <el-option-group
              v-for="group in permissionGroups"
              :key="group.module"
              :label="moduleLabel(group.module)"
            >
              <el-option
                v-for="permission in group.permissions"
                :key="permission.code"
                :label="permission.name"
                :value="permission.code"
              >
                <div class="role-permission-option">
                  <strong>{{ permission.name }}</strong>
                  <span>{{ permission.code }}</span>
                </div>
              </el-option>
            </el-option-group>
          </el-select>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="roleDialogOpen = false">取消</el-button>
        <el-button type="primary" :loading="isSavingRole" @click="saveRole">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { CirclePlus, Delete, EditPen, RefreshRight } from '@element-plus/icons-vue'

import {
  createRole,
  deleteRole,
  listPermissions,
  listRoles,
  updateRole,
  type AuthPermission,
  type AuthRole,
} from '../api/auth'
import { getApiErrorMessage } from '../api/errors'
import PageHero from '../components/PageHero.vue'
import { useAuth } from '../composables/useAuth'

type RoleDialogMode = 'create' | 'edit'

const ROLE_CODE_PATTERN = /^[a-z0-9_.-]{2,48}$/

const auth = useAuth()
const roles = ref<AuthRole[]>([])
const permissions = ref<AuthPermission[]>([])
const isLoading = ref(false)
const isSavingRole = ref(false)
const deletingRoleId = ref<number | null>(null)
const roleDialogOpen = ref(false)
const roleDialogMode = ref<RoleDialogMode>('create')
const editingRole = ref<AuthRole | null>(null)
const roleForm = reactive({
  code: '',
  name: '',
  description: '',
  permission_codes: [] as string[],
})

const canCreate = computed(() => auth.hasPermission('role:create'))
const canUpdate = computed(() => auth.hasPermission('role:update'))
const canDelete = computed(() => auth.hasPermission('role:delete'))
const customRoleCount = computed(() => roles.value.filter((role) => !role.is_system).length)
const roleDialogTitle = computed(() => (roleDialogMode.value === 'create' ? '新建角色' : '编辑角色'))
const permissionNameMap = computed(() => new Map(permissions.value.map((permission) => [permission.code, permission.name])))
const permissionGroups = computed(() => {
  const groups = new Map<string, AuthPermission[]>()
  for (const permission of permissions.value) {
    const module = permission.module || 'other'
    groups.set(module, [...(groups.get(module) ?? []), permission])
  }
  return [...groups.entries()]
    .map(([module, groupedPermissions]) => ({
      module,
      permissions: groupedPermissions.slice().sort((left, right) => left.code.localeCompare(right.code)),
    }))
    .sort((left, right) => moduleLabel(left.module).localeCompare(moduleLabel(right.module), 'zh-CN'))
})

onMounted(() => {
  void loadPageData()
})

async function loadPageData() {
  isLoading.value = true
  try {
    const [rolesResponse, permissionsResponse] = await Promise.all([listRoles(), listPermissions()])
    roles.value = rolesResponse.data.roles
    permissions.value = permissionsResponse.data.permissions
  } catch (error) {
    ElMessage.error(getApiErrorMessage(error, '角色数据加载失败'))
  } finally {
    isLoading.value = false
  }
}

function openCreateRole() {
  roleDialogMode.value = 'create'
  editingRole.value = null
  roleForm.code = ''
  roleForm.name = ''
  roleForm.description = ''
  roleForm.permission_codes = []
  roleDialogOpen.value = true
}

function openEditRole(role: AuthRole) {
  roleDialogMode.value = 'edit'
  editingRole.value = role
  roleForm.code = role.code
  roleForm.name = role.name
  roleForm.description = role.description
  roleForm.permission_codes = [...role.permission_codes]
  roleDialogOpen.value = true
}

async function saveRole() {
  if (roleDialogMode.value === 'create' && !ROLE_CODE_PATTERN.test(roleForm.code)) {
    ElMessage.warning('角色编码需要 2-48 位，仅允许小写字母、数字、点、下划线和短横线')
    return
  }
  if (!roleForm.name.trim()) {
    ElMessage.warning('请输入角色名称')
    return
  }

  isSavingRole.value = true
  try {
    if (roleDialogMode.value === 'create') {
      const response = await createRole({
        code: roleForm.code,
        name: roleForm.name,
        description: roleForm.description,
        permission_codes: roleForm.permission_codes,
      })
      roles.value = [...roles.value, response.data.role].sort(compareRole)
      ElMessage.success('角色已创建')
    } else if (editingRole.value) {
      const response = await updateRole(editingRole.value.id, {
        name: roleForm.name,
        description: roleForm.description,
        permission_codes: roleForm.permission_codes,
      })
      replaceRole(response.data.role)
      ElMessage.success('角色已更新')
    }
    roleDialogOpen.value = false
  } catch (error) {
    ElMessage.error(getApiErrorMessage(error, '角色保存失败'))
  } finally {
    isSavingRole.value = false
  }
}

async function confirmDeleteRole(role: AuthRole) {
  try {
    await ElMessageBox.confirm(
      `确认删除角色“${role.name}”？删除前请确保没有用户绑定该角色。`,
      '删除角色',
      {
        type: 'warning',
        confirmButtonText: '删除',
        cancelButtonText: '取消',
      },
    )
    deletingRoleId.value = role.id
    await deleteRole(role.id)
    roles.value = roles.value.filter((candidate) => candidate.id !== role.id)
    ElMessage.success('角色已删除')
  } catch (error) {
    if (!isMessageBoxCancel(error)) {
      ElMessage.error(getApiErrorMessage(error, '角色删除失败'))
    }
  } finally {
    deletingRoleId.value = null
  }
}

function replaceRole(nextRole: AuthRole) {
  roles.value = roles.value.map((role) => (role.id === nextRole.id ? nextRole : role)).sort(compareRole)
}

function compareRole(left: AuthRole, right: AuthRole) {
  if (left.is_system !== right.is_system) {
    return left.is_system ? -1 : 1
  }
  return left.code.localeCompare(right.code)
}

function visiblePermissionCodes(role: AuthRole) {
  return role.permission_codes.slice(0, 8)
}

function permissionLabel(permissionCode: string) {
  return permissionNameMap.value.get(permissionCode) ?? permissionCode
}

function moduleLabel(module: string) {
  const labels: Record<string, string> = {
    dashboard: '工作台',
    daily_check: '每日点货',
    inventory: '库存管理',
    transfer: '数据迁移',
    pesticide: '农残检测',
    weekly_quote: '每周报价',
    device: '设备管理',
    permission_request: '权限申请',
    user: '用户管理',
    role: '角色管理',
  }
  return labels[module] ?? module
}

function isSuperAdminRole(role: AuthRole) {
  return role.code === 'super_admin'
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

function isMessageBoxCancel(error: unknown) {
  return error === 'cancel' || error === 'close'
}
</script>

<style scoped>
.role-management-page {
  gap: 16px;
}

.role-hero-metrics {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
  width: 100%;
}

.role-hero-metric {
  display: grid;
  gap: 6px;
  padding: 14px;
  border-radius: var(--radius-md);
  background: #ffffff;
  box-shadow: var(--shadow-glass);
}

.role-hero-metric--wide {
  grid-column: 1 / -1;
}

.role-hero-metric span {
  color: var(--color-muted-soft);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}

.role-hero-metric strong {
  color: var(--color-text);
  font-family: var(--font-heading);
  font-size: clamp(22px, 3vw, 30px);
  font-weight: 600;
  line-height: 1.1;
}

.role-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  padding: 20px;
}

.role-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
  min-height: 260px;
}

.role-card {
  border-radius: var(--radius-lg);
  background: #ffffff;
}

.role-card :deep(.el-card__body) {
  display: grid;
  gap: 16px;
}

.role-card--system {
  border-color: var(--color-border);
}

.role-card--locked {
  border-color: var(--color-primary);
}

.role-card__topline,
.role-card__actions {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
}

.role-card__actions {
  flex-wrap: wrap;
}

.role-card__code {
  color: var(--color-muted-soft);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.role-card h2,
.role-card__description {
  margin: 0;
}

.role-card h2 {
  margin-top: 4px;
  color: var(--color-text);
  font-family: var(--font-heading);
  font-size: 22px;
  font-weight: 600;
}

.role-card__badges,
.role-card__permissions {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 8px;
}

.role-card__permissions {
  justify-content: flex-start;
}

.role-card__description {
  min-height: 46px;
  color: var(--color-muted);
  font-size: 13px;
  line-height: 1.7;
}

.role-card__facts {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.role-card__facts div {
  display: grid;
  gap: 6px;
  min-width: 0;
  padding: 12px;
  border-radius: var(--radius-md);
  background: var(--color-surface-card);
}

.role-card__facts span {
  color: var(--color-muted-soft);
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.role-card__facts strong {
  color: var(--color-text);
  font-family: var(--font-body);
  font-weight: 600;
  font-size: 13px;
  overflow-wrap: anywhere;
}

.role-card__empty {
  color: var(--color-muted);
  font-size: 13px;
}

.role-form {
  display: grid;
  gap: 2px;
}

.role-form :deep(.el-select) {
  width: 100%;
}

.role-permission-option {
  display: grid;
  gap: 2px;
  min-width: 0;
}

.role-permission-option strong {
  color: var(--color-text);
  font-size: 13px;
}

.role-permission-option span {
  color: var(--color-muted);
  font-size: 12px;
}

@media (max-width: 1280px) {
  .role-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 860px) {
  .role-grid {
    grid-template-columns: 1fr;
  }

  .role-toolbar {
    align-items: flex-start;
    flex-direction: column;
  }
}

@media (max-width: 520px) {
  .role-hero-metrics,
  .role-card__facts {
    grid-template-columns: 1fr;
  }

  .role-card__actions .el-button {
    width: 100%;
  }
}
</style>
