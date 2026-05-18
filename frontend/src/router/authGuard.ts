import type { Router } from 'vue-router'

import { useAuth } from '../composables/useAuth'

let hasTriedRestoreSession = false
let restoreSessionPromise: Promise<boolean> | null = null

export function resetRestoreSessionFlag() {
  hasTriedRestoreSession = false
}

export function markRestoreSessionAttempted() {
  hasTriedRestoreSession = true
}

export function installAuthGuard(router: Router) {
  router.beforeEach(async (to) => {
    const auth = useAuth()
    const requiresAuth = to.matched.some((route) => route.meta.requiresAuth === true)
    const guestOnly = to.matched.some((route) => route.meta.guestOnly === true)
    const requiredPermission = to.matched
      .map((route) => route.meta.requiredPermission)
      .find((permission): permission is string => typeof permission === 'string')

    if (auth.isAuthenticated.value) {
      if (guestOnly) {
        return typeof to.query.redirect === 'string' ? to.query.redirect : '/'
      }
      if (shouldRedirectSuperAdminPermissionRequest(to.name, auth.isSuperAdmin.value)) {
        return { name: 'permission-approvals', replace: true }
      }
      if (requiredPermission && !auth.hasPermission(requiredPermission)) {
        return forbiddenRoute(to.fullPath, requiredPermission)
      }
      return true
    }

    if (requiresAuth || guestOnly) {
      const restored = await restoreSession()
      if (restored) {
        if (guestOnly) {
          return typeof to.query.redirect === 'string' ? to.query.redirect : '/'
        }
        if (shouldRedirectSuperAdminPermissionRequest(to.name, auth.isSuperAdmin.value)) {
          return { name: 'permission-approvals', replace: true }
        }
        if (requiredPermission && !auth.hasPermission(requiredPermission)) {
          return forbiddenRoute(to.fullPath, requiredPermission)
        }
        return true
      }
    }

    if (!requiresAuth) {
      return true
    }

    return {
      path: '/login',
      query: {
        redirect: to.fullPath,
      },
    }
  })
}

function shouldRedirectSuperAdminPermissionRequest(
  routeName: string | symbol | null | undefined,
  isSuperAdmin: boolean,
) {
  return isSuperAdmin && routeName === 'permission-requests'
}

function forbiddenRoute(from: string, permission: string) {
  return {
    path: '/403',
    query: {
      from,
      permission,
    },
  }
}

async function restoreSession() {
  const auth = useAuth()
  if (auth.isAuthenticated.value) {
    return true
  }

  if (hasTriedRestoreSession) {
    return false
  }

  if (!restoreSessionPromise) {
    restoreSessionPromise = auth
      .refresh()
      .then(() => {
        hasTriedRestoreSession = true
        return true
      })
      .catch(() => {
        hasTriedRestoreSession = true
        auth.resetAuthState()
        return false
      })
      .finally(() => {
        restoreSessionPromise = null
      })
  }

  return restoreSessionPromise
}
