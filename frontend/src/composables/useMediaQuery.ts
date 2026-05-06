import { onBeforeUnmount, onMounted, ref } from 'vue'

export function useMediaQuery(query: string) {
  const matches = ref(false)
  let mediaQueryList: MediaQueryList | null = null

  const updateMatches = (event?: MediaQueryListEvent) => {
    matches.value = event?.matches ?? mediaQueryList?.matches ?? false
  }

  onMounted(() => {
    if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') {
      return
    }

    mediaQueryList = window.matchMedia(query)
    updateMatches()

    if (typeof mediaQueryList.addEventListener === 'function') {
      mediaQueryList.addEventListener('change', updateMatches)
      return
    }

    mediaQueryList.addListener(updateMatches)
  })

  onBeforeUnmount(() => {
    if (!mediaQueryList) {
      return
    }

    if (typeof mediaQueryList.removeEventListener === 'function') {
      mediaQueryList.removeEventListener('change', updateMatches)
      return
    }

    mediaQueryList.removeListener(updateMatches)
  })

  return matches
}
