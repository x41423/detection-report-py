import { createRouter, createWebHistory } from 'vue-router'

import { trackAudit } from '../api/audit'
import { useAuth } from '../composables/useAuth'
import { useRouteLoadingBar } from '../composables/useLoadingBar'
import { appRoutes } from '../navigation/appNavigation'
import { installAuthGuard } from './authGuard'

const router = createRouter({
  history: createWebHistory(),
  routes: appRoutes,
})

installAuthGuard(router)

// ── 全局 loading 条 ──
const loadingBar = useRouteLoadingBar()

router.beforeEach((_to, _from) => {
  loadingBar.start()
})

// 用 afterEach 而非 beforeResolve，确保 chunk 加载 + 组件渲染都完成
router.afterEach(() => {
  loadingBar.done()
})

// Page-view audit: fire-and-forget after each authenticated navigation.
router.afterEach((to, from) => {
  if (to.path === from.path) return
  const auth = useAuth()
  if (!auth.isAuthenticated.value) return
  void trackAudit({
    module: 'navigation',
    action: 'page_view',
    description: to.fullPath,
    metadata: {
      name: typeof to.name === 'string' ? to.name : undefined,
      from: from.fullPath || undefined,
    },
  })
})

export default router
