import { ref } from 'vue'

const isLoading = ref(false)

let hideTimer: ReturnType<typeof setTimeout> | null = null

export function useRouteLoadingBar() {
  function start() {
    if (hideTimer) {
      clearTimeout(hideTimer)
      hideTimer = null
    }
    isLoading.value = true
  }

  function done() {
    // 留 200ms 让动画收尾，避免闪一下就消失
    if (hideTimer) clearTimeout(hideTimer)
    hideTimer = setTimeout(() => {
      isLoading.value = false
      hideTimer = null
    }, 200)
  }

  return { isLoading, start, done }
}
