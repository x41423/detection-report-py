import { appNavigationItems } from '../navigation/appNavigation'

let preloadStarted = false

/**
 * 页面加载完成后，后台逐个预下载所有路由的 JS chunk。
 * 用户导航到任何页面时 chunk 已在缓存中，实现秒开。
 */
export function preloadAllRouteChunks() {
  if (preloadStarted) return
  preloadStarted = true

  // 延迟 2 秒，等首屏渲染完成后再开始预加载
  setTimeout(async () => {
    const delay = (ms: number) => new Promise<void>(r => setTimeout(r, ms))

    for (const item of appNavigationItems) {
      try {
        // 触发 Vite 的动态 import，浏览器开始下载 chunk
        await item.component()
        // 每个 chunk 之间隔 150ms，避免同时发起 20+ 个请求
        await delay(150)
      } catch {
        // 预加载失败不影响正常使用
      }
    }
  }, 2000)
}
