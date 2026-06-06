/**
 * DirBrowser 函数式 API — 单例模式（composable 版本）
 *
 * App.vue 层 provide 一个 DirBrowserV2 单例（1 个 DOM）。
 * 各页面在 setup() 中调用 useDirBrowserApi() 获取绑定的 API。
 *
 * 用法：
 *   import { useDirBrowserApi } from '@/features/shared/dirBrowser'
 *   const { openFile, openDirectory } = useDirBrowserApi()
 *   const path = await openFile('pest:big', '', { extensions: ['.docx'] })
 */

import { inject, type Ref } from 'vue'

import type { DirBrowserV2OpenOptions } from '../../components/DirBrowserV2.vue'

/** 注入 key */
export const DIR_BROWSER_KEY = Symbol('dir-browser-v2')

interface DirBrowserV2Handle {
  open(initialPath?: string, options?: DirBrowserV2OpenOptions): Promise<string | string[]>
}

/**
 * 在 setup() 阶段调用，获取绑定到单例 DirBrowserV2 的函数式 API。
 */
export function useDirBrowserApi() {
  const handle = inject<Ref<DirBrowserV2Handle | undefined>>(DIR_BROWSER_KEY)
  if (!handle) {
    console.error('[DirBrowser] 单例未初始化 — 确保 App.vue 已 provide DIR_BROWSER_KEY')
  }

  async function openFile(
    scope: string,
    initialPath: string = '',
    options: Omit<DirBrowserV2OpenOptions, 'mode' | 'scope'> = {},
  ): Promise<string> {
    if (!handle?.value) return ''
    const result = await handle.value.open(initialPath, { ...options, mode: 'file', scope })
    return typeof result === 'string' ? result : (result[0] || '')
  }

  async function openDirectory(
    scope: string,
    initialPath: string = '',
    options: Omit<DirBrowserV2OpenOptions, 'mode' | 'scope'> = {},
  ): Promise<string> {
    if (!handle?.value) return ''
    const result = await handle.value.open(initialPath, { ...options, mode: 'directory', scope })
    return typeof result === 'string' ? result : ''
  }

  async function openMultiFile(
    scope: string,
    initialPath: string = '',
    options: Omit<DirBrowserV2OpenOptions, 'mode' | 'scope'> = {},
  ): Promise<string[]> {
    if (!handle?.value) return []
    const result = await handle.value.open(initialPath, { ...options, mode: 'multi-file', scope })
    return Array.isArray(result) ? result : (result ? [result] : [])
  }

  async function openSaveAs(
    scope: string,
    initialPath: string = '',
    options: Omit<DirBrowserV2OpenOptions, 'mode' | 'scope'> = {},
  ): Promise<string> {
    if (!handle?.value) return ''
    const result = await handle.value.open(initialPath, { ...options, mode: 'save-as', scope })
    return typeof result === 'string' ? result : ''
  }

  return { openFile, openDirectory, openMultiFile, openSaveAs }
}
