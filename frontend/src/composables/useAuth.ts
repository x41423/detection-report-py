import { computed, readonly, ref } from 'vue'

import api from '../api/client'
import * as authApi from '../api/auth'
import type { AuthUser, LoginPayload, RegisterPayload, ReplaceDeviceLoginPayload } from '../api/auth'

const accessToken = ref('')
const expiresAt = ref('')
const currentUser = ref<AuthUser | null>(null)
const isLoading = ref(false)

function applyAccessToken(token: string) {
  accessToken.value = token
  if (token) {
    api.defaults.headers.common.Authorization = `Bearer ${token}`
    return
  }
  delete api.defaults.headers.common.Authorization
}

function applyTokenResponse(payload: authApi.AuthTokenResponse) {
  applyAccessToken(payload.access_token)
  expiresAt.value = payload.expires_at
  currentUser.value = payload.user
  import('../router/authGuard').then((m) => m.resetRestoreSessionFlag()).catch(() => {})
  return payload
}

function resetAuthState() {
  applyAccessToken('')
  expiresAt.value = ''
  currentUser.value = null
  import('../router/authGuard').then((m) => m.markRestoreSessionAttempted()).catch(() => {})
}

// Exported for use by the auth interceptor (which runs outside the composable tree)
export { applyTokenResponse as applyAuthTokenResponse, resetAuthState as resetAuthState }

export function useAuth() {
  const isAuthenticated = computed(() => {
    if (!accessToken.value || !currentUser.value) return false
    if (expiresAt.value) {
      return new Date(expiresAt.value).getTime() > Date.now()
    }
    return true
  })
  const isSuperAdmin = computed(() => Boolean(currentUser.value?.is_super_admin))
  const permissions = computed(() => currentUser.value?.permissions ?? [])

  function hasPermission(permissionCode: string) {
    return isSuperAdmin.value || permissions.value.includes(permissionCode)
  }

  function hasAnyPermission(permissionCodes: string[]) {
    return isSuperAdmin.value || permissionCodes.some((permissionCode) => permissions.value.includes(permissionCode))
  }

  async function login(payload: LoginPayload) {
    isLoading.value = true
    try {
      const response = await authApi.login(payload)
      if (authApi.isPendingLoginResponse(response.data)) {
        return response.data
      }
      return applyTokenResponse(response.data)
    } finally {
      isLoading.value = false
    }
  }

  async function register(payload: RegisterPayload) {
    isLoading.value = true
    try {
      const response = await authApi.register(payload)
      return response.data
    } finally {
      isLoading.value = false
    }
  }

  async function refresh() {
    isLoading.value = true
    try {
      const response = await authApi.refreshSession()
      return applyTokenResponse(response.data)
    } finally {
      isLoading.value = false
    }
  }

  async function loadMe() {
    if (!accessToken.value) {
      return null
    }

    const response = await authApi.getCurrentUser()
    currentUser.value = response.data.user
    return currentUser.value
  }

  async function logout() {
    try {
      if (accessToken.value) {
        await authApi.logout()
      }
    } finally {
      resetAuthState()
    }
  }

  async function replaceDeviceLogin(payload: ReplaceDeviceLoginPayload) {
    isLoading.value = true
    try {
      const response = await authApi.replaceDeviceLogin(payload)
      return applyTokenResponse(response.data)
    } finally {
      isLoading.value = false
    }
  }

  return {
    accessToken: readonly(accessToken),
    currentUser: readonly(currentUser),
    expiresAt: readonly(expiresAt),
    hasAnyPermission,
    hasPermission,
    isAuthenticated,
    isLoading: readonly(isLoading),
    isSuperAdmin,
    loadMe,
    login,
    logout,
    replaceDeviceLogin,
    refresh,
    register,
    resetAuthState,
  }
}

// Register callbacks so the 401 interceptor can sync composable state
// without creating a circular dependency.
import { setAuthCallbacks } from '../api/authInterceptors'
setAuthCallbacks(applyTokenResponse, resetAuthState)
