<template>
  <div v-if="isAuthLayout" class="auth-layout">
    <router-view />
  </div>
  <div v-else class="app-layout">
    <aside class="app-layout__sidebar" :class="{ 'is-collapsed': isCollapsed }">
      <div class="app-layout__brand">
        <div class="app-layout__brand-mark">滨</div>
        <div v-if="!isCollapsed" class="app-layout__brand-meta">
          <div class="app-layout__brand-title">滨鲜检测工具</div>
          <div class="app-layout__brand-sub">业务工作台</div>
        </div>
      </div>

      <nav class="app-layout__nav">
        <template v-for="section in visibleSections" :key="section.id">
          <div v-if="!isCollapsed" class="app-layout__nav-group">{{ section.title }}</div>
          <ul class="app-layout__nav-list">
            <li v-for="item in section.items" :key="item.path">
              <router-link :to="item.path" class="app-layout__nav-link" active-class="is-active">
                <el-icon class="app-layout__nav-icon">
                  <component :is="item.icon" />
                </el-icon>
                <span v-if="!isCollapsed" class="app-layout__nav-label">{{ item.shortTitle || item.title }}</span>
              </router-link>
              <ul v-if="!isCollapsed && item.children?.length" class="app-layout__sub-list">
                <li v-for="child in item.children" :key="child.path">
                  <router-link :to="child.path" class="app-layout__sub-link" active-class="is-active">
                    {{ child.shortTitle || child.title }}
                  </router-link>
                </li>
              </ul>
            </li>
          </ul>
        </template>
      </nav>

      <button type="button" class="app-layout__collapse" @click="toggleCollapsed">
        <el-icon>
          <component :is="isCollapsed ? 'Expand' : 'Fold'" />
        </el-icon>
      </button>
    </aside>

    <div class="app-layout__main">
      <header class="app-layout__topbar">
        <div class="app-layout__topbar-left">
          <h1 class="app-layout__page-title">{{ currentTitle }}</h1>
          <p v-if="currentDescription" class="app-layout__page-desc">{{ currentDescription }}</p>
        </div>
        <div class="app-layout__topbar-right">
          <template v-if="auth.isAuthenticated.value">
            <el-dropdown trigger="click" @command="onUserCommand">
              <span class="app-layout__user">
                <el-avatar :size="32">{{ userInitial }}</el-avatar>
                <span class="app-layout__user-name">{{ auth.currentUser.value?.display_name || auth.currentUser.value?.username }}</span>
                <el-icon><CaretBottom /></el-icon>
              </span>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item v-if="auth.isSuperAdmin.value" disabled>超级管理员</el-dropdown-item>
                  <el-dropdown-item command="devices">登录设备</el-dropdown-item>
                  <el-dropdown-item command="logout" divided>退出登录</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </template>
        </div>
      </header>

      <main class="app-layout__content">
        <router-view />
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { CaretBottom } from '@element-plus/icons-vue'

import { useAuth } from '../composables/useAuth'
import {
  filterNavigationSectionsByPermissions,
  sidebarNavigationSections,
} from '../navigation/appNavigation'

const auth = useAuth()
const route = useRoute()
const router = useRouter()

const isCollapsed = ref(false)

const isAuthLayout = computed(() => route.meta?.layout === 'auth')

const visibleSections = computed(() =>
  filterNavigationSectionsByPermissions(
    sidebarNavigationSections,
    auth.currentUser.value?.permissions ?? [],
    { isSuperAdmin: auth.isSuperAdmin.value },
  ),
)

const currentTitle = computed(() => {
  const meta = route.meta as { title?: string }
  return meta?.title || ''
})

const currentDescription = computed(() => {
  const meta = route.meta as { description?: string }
  return meta?.description || ''
})

const userInitial = computed(() => {
  const name = auth.currentUser.value?.display_name || auth.currentUser.value?.username || ''
  return name.slice(0, 1).toUpperCase()
})

function toggleCollapsed() {
  isCollapsed.value = !isCollapsed.value
}

async function onUserCommand(command: string) {
  if (command === 'logout') {
    try {
      await auth.logout()
      ElMessage.success('已退出登录')
      await router.push('/login')
    } catch {
      ElMessage.error('退出失败，请重试')
    }
  } else if (command === 'devices') {
    await router.push('/devices')
  }
}
</script>

<style scoped>
.auth-layout {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f5f5f5;
}

.app-layout {
  display: flex;
  min-height: 100vh;
  background: #f7f7f8;
}

.app-layout__sidebar {
  flex-shrink: 0;
  width: 232px;
  background: #ffffff;
  border-right: 1px solid var(--color-border);
  display: flex;
  flex-direction: column;
  position: sticky;
  top: 0;
  height: 100vh;
  overflow: hidden;
  transition: width 0.22s ease;
}

.app-layout__sidebar.is-collapsed {
  width: 64px;
}

.app-layout__brand {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 18px 16px 14px;
  border-bottom: 1px solid var(--color-border);
}

.app-layout__brand-mark {
  flex-shrink: 0;
  width: 32px;
  height: 32px;
  border-radius: 8px;
  background: var(--color-primary);
  color: #ffffff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 16px;
  font-family: var(--font-heading);
}

.app-layout__brand-meta {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.app-layout__brand-title {
  font-family: var(--font-heading);
  font-size: 14px;
  font-weight: 700;
  color: var(--color-text);
  line-height: 1.2;
}

.app-layout__brand-sub {
  font-size: 11px;
  color: var(--color-muted-soft);
  letter-spacing: 0.1em;
  text-transform: uppercase;
}

.app-layout__nav {
  flex: 1;
  overflow-y: auto;
  padding: 12px 8px 24px;
}

.app-layout__nav-group {
  margin: 14px 12px 6px;
  font-size: 11px;
  color: var(--color-muted-soft);
  letter-spacing: 0.14em;
  text-transform: uppercase;
  font-weight: 600;
}

.app-layout__nav-list,
.app-layout__sub-list {
  list-style: none;
  margin: 0;
  padding: 0;
}

.app-layout__nav-link {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 12px;
  margin: 2px 4px;
  border-radius: 8px;
  color: var(--color-muted);
  font-size: 13px;
  text-decoration: none;
  transition: background 0.18s ease, color 0.18s ease;
}

.app-layout__nav-link:hover {
  background: rgba(34, 42, 53, 0.05);
  color: var(--color-text);
}

.app-layout__nav-link.is-active {
  background: var(--color-primary);
  color: #ffffff;
}

.app-layout__nav-icon {
  font-size: 16px;
  flex-shrink: 0;
}

.app-layout__nav-label {
  flex: 1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.app-layout__sub-list {
  padding-left: 32px;
}

.app-layout__sub-link {
  display: block;
  padding: 6px 10px;
  margin: 1px 0;
  border-radius: 6px;
  color: var(--color-muted-soft);
  font-size: 12px;
  text-decoration: none;
  transition: color 0.18s ease;
}

.app-layout__sub-link:hover,
.app-layout__sub-link.is-active {
  color: var(--color-text);
  background: rgba(34, 42, 53, 0.04);
}

.app-layout__collapse {
  margin: 8px 12px 16px;
  height: 32px;
  border-radius: 6px;
  border: 1px solid var(--color-border);
  background: #ffffff;
  color: var(--color-muted);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
}

.app-layout__collapse:hover {
  background: rgba(34, 42, 53, 0.04);
}

.app-layout__main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.app-layout__topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 14px 28px;
  background: #ffffff;
  border-bottom: 1px solid var(--color-border);
  position: sticky;
  top: 0;
  z-index: 10;
}

.app-layout__topbar-left {
  min-width: 0;
}

.app-layout__page-title {
  margin: 0;
  font-family: var(--font-heading);
  font-size: 18px;
  font-weight: 700;
  color: var(--color-text);
}

.app-layout__page-desc {
  margin: 4px 0 0;
  font-size: 12px;
  color: var(--color-muted);
}

.app-layout__user {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  padding: 4px 10px 4px 4px;
  border-radius: 999px;
  transition: background 0.18s ease;
}

.app-layout__user:hover {
  background: rgba(34, 42, 53, 0.05);
}

.app-layout__user-name {
  font-size: 13px;
  color: var(--color-text);
  font-weight: 500;
}

.app-layout__content {
  flex: 1;
  min-width: 0;
  overflow-x: hidden;
}

@media (max-width: 900px) {
  .app-layout__sidebar {
    width: 64px;
  }

  .app-layout__brand-meta,
  .app-layout__nav-group,
  .app-layout__nav-label,
  .app-layout__sub-list {
    display: none;
  }

  .app-layout__topbar {
    padding: 12px 16px;
  }
}
</style>
