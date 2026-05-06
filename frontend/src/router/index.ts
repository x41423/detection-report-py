import { createRouter, createWebHistory } from 'vue-router'

import { trackAudit } from '../api/audit'
import { useAuth } from '../composables/useAuth'
import { appRoutes } from '../navigation/appNavigation'
import { installAuthGuard } from './authGuard'

const router = createRouter({
  history: createWebHistory(),
  routes: appRoutes,
})

installAuthGuard(router)

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
