import type { AxiosError, AxiosInstance, InternalAxiosRequestConfig } from 'axios'

import * as authApi from './auth'
import type { AuthTokenResponse } from './auth'

let isRefreshing = false
let refreshPromise: Promise<string> | null = null
let hasNotifiedSessionExpired = false

interface QueueEntry {
  resolve: (token: string) => void
  reject: (error: unknown) => void
}

let failedQueue: QueueEntry[] = []

function processQueue(error: unknown, token: string | null = null) {
  for (const entry of failedQueue) {
    if (error) {
      entry.reject(error)
    } else if (token) {
      entry.resolve(token)
    }
  }
  failedQueue = []
}

let onTokenRefreshed: ((payload: AuthTokenResponse) => void) | null = null
let onRefreshFailed: (() => void) | null = null
let onSessionExpired: (() => void) | null = null

export function setAuthCallbacks(
  onRefreshed: (payload: AuthTokenResponse) => void,
  onFailed: () => void,
) {
  onTokenRefreshed = onRefreshed
  onRefreshFailed = onFailed
}

export function setAuthSessionExpiredCallback(callback: (() => void) | null) {
  onSessionExpired = callback
}

export function installAuthInterceptors(api: AxiosInstance) {
  api.interceptors.response.use(
    (response) => {
      hasNotifiedSessionExpired = false
      return response
    },
    async (error: AxiosError) => {
      const config = error.config as (InternalAxiosRequestConfig & { _retry?: boolean }) | undefined

      if (!config || error.response?.status !== 401 || config._retry) {
        return Promise.reject(error)
      }

      // Don't intercept auth endpoints themselves (avoids refresh loops)
      if (config.url && /\/api\/auth\/(login|refresh|logout)/.test(config.url)) {
        return Promise.reject(error)
      }

      if (isRefreshing && refreshPromise) {
        return new Promise<string>((resolve, reject) => {
          failedQueue.push({ resolve, reject })
        }).then((token) => {
          config._retry = true
          config.headers.Authorization = `Bearer ${token}`
          return api.request(config)
        })
      }

      config._retry = true
      isRefreshing = true
      refreshPromise = authApi.refreshSession()
        .then((response) => {
          const newToken: string = response.data.access_token
          api.defaults.headers.common.Authorization = `Bearer ${newToken}`
          hasNotifiedSessionExpired = false
          onTokenRefreshed?.(response.data)
          processQueue(null, newToken)
          isRefreshing = false
          refreshPromise = null
          return newToken
        })
        .catch((refreshError) => {
          api.defaults.headers.common.Authorization = undefined
          delete api.defaults.headers.common.Authorization
          onRefreshFailed?.()
          if (!hasNotifiedSessionExpired) {
            hasNotifiedSessionExpired = true
            onSessionExpired?.()
          }
          processQueue(refreshError, null)
          isRefreshing = false
          refreshPromise = null
          return Promise.reject(refreshError)
        })

      try {
        const token = await refreshPromise
        config.headers.Authorization = `Bearer ${token}`
        return api.request(config)
      } catch (refreshError) {
        return Promise.reject(refreshError)
      }
    },
  )
}
