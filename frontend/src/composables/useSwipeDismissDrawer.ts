import { nextTick, onBeforeUnmount, type Ref, watch } from 'vue'

interface UseSwipeDismissDrawerOptions {
  drawerSelector?: string
  dismissDistanceRatio?: number
  dismissDurationMs?: number
  dismissVelocity?: number
  isEnabled: Ref<boolean>
  isOpen: Ref<boolean>
  onDismiss: () => void
}

const DRAGGING_CLASS = 'is-swipe-dragging'
const DEFAULT_SELECTOR = '.shell-navigation-drawer'
const DEFAULT_DISMISS_DISTANCE_RATIO = 0.25
const DEFAULT_DISMISS_DURATION_MS = 220
const DEFAULT_DISMISS_VELOCITY = 0.35
const MIN_LOCK_DISTANCE = 12
const MIN_AXIS_DISTANCE = 8
const AXIS_RATIO = 1.25

export function useSwipeDismissDrawer({
  drawerSelector = DEFAULT_SELECTOR,
  dismissDistanceRatio = DEFAULT_DISMISS_DISTANCE_RATIO,
  dismissDurationMs = DEFAULT_DISMISS_DURATION_MS,
  dismissVelocity = DEFAULT_DISMISS_VELOCITY,
  isEnabled,
  isOpen,
  onDismiss,
}: UseSwipeDismissDrawerOptions) {
  let drawerPanel: HTMLElement | null = null
  let dismissTimer: number | null = null
  let panelWidth = 0
  let startX = 0
  let startY = 0
  let startTime = 0
  let currentOffset = 0
  let axis: 'idle' | 'undetermined' | 'horizontal' | 'vertical' = 'idle'
  let dismissing = false
  let tracking = false
  let finalTouchTime = 0

  function clearDismissTimer() {
    if (dismissTimer !== null) {
      window.clearTimeout(dismissTimer)
      dismissTimer = null
    }
  }

  function resetGestureState() {
    panelWidth = 0
    startX = 0
    startY = 0
    startTime = 0
    currentOffset = 0
    finalTouchTime = 0
    axis = 'idle'
    tracking = false
  }

  function removeDraggingState() {
    drawerPanel?.classList.remove(DRAGGING_CLASS)
  }

  function resetPanelStyles(target?: HTMLElement | null) {
    const panel = target ?? drawerPanel
    panel?.classList.remove(DRAGGING_CLASS)
    if (!panel) {
      return
    }

    panel.style.transform = ''
  }

  function teardownPanel() {
    clearDismissTimer()

    if (drawerPanel) {
      drawerPanel.removeEventListener('touchstart', handleTouchStart)
      drawerPanel.removeEventListener('touchmove', handleTouchMove)
      drawerPanel.removeEventListener('touchend', handleTouchEnd)
      drawerPanel.removeEventListener('touchcancel', handleTouchCancel)
      if (!dismissing) {
        resetPanelStyles()
      } else {
        removeDraggingState()
      }
      drawerPanel = null
    }

    panelWidth = 0
    startX = 0
    startY = 0
    startTime = 0
    currentOffset = 0
    finalTouchTime = 0
    axis = 'idle'
    tracking = false
  }

  function getPanelWidth() {
    return drawerPanel?.getBoundingClientRect().width ?? 0
  }

  function applyOffset(offset: number) {
    if (!drawerPanel) {
      return
    }

    currentOffset = Math.max(offset, -panelWidth)
    drawerPanel.style.transform = `translate3d(${currentOffset}px, 0, 0)`
  }

  function animateBack() {
    removeDraggingState()
    if (drawerPanel) {
      drawerPanel.style.transform = ''
    }
    resetGestureState()
  }

  function animateDismiss() {
    if (!drawerPanel) {
      resetGestureState()
      return
    }

    dismissing = true
    removeDraggingState()
    drawerPanel.style.transform = `translate3d(-${panelWidth}px, 0, 0)`
    clearDismissTimer()
    dismissTimer = window.setTimeout(() => {
      dismissTimer = null
      onDismiss()
    }, dismissDurationMs)
    resetGestureState()
  }

  function handleTouchStart(event: TouchEvent) {
    if (!drawerPanel || event.touches.length !== 1 || dismissTimer !== null) {
      return
    }

    const touch = event.touches[0]
    panelWidth = getPanelWidth()
    startX = touch.clientX
    startY = touch.clientY
    startTime = performance.now()
    finalTouchTime = startTime
    currentOffset = 0
    axis = 'undetermined'
    tracking = true
    removeDraggingState()
  }

  function handleTouchMove(event: TouchEvent) {
    if (!drawerPanel || !tracking || event.touches.length !== 1) {
      return
    }

    const touch = event.touches[0]
    const deltaX = touch.clientX - startX
    const deltaY = touch.clientY - startY
    const absDeltaX = Math.abs(deltaX)
    const absDeltaY = Math.abs(deltaY)

    finalTouchTime = performance.now()

    if (axis === 'vertical') {
      return
    }

    if (axis === 'undetermined') {
      if (absDeltaX < MIN_AXIS_DISTANCE && absDeltaY < MIN_AXIS_DISTANCE) {
        return
      }

      if (deltaX <= -MIN_LOCK_DISTANCE && absDeltaX > absDeltaY * AXIS_RATIO) {
        axis = 'horizontal'
      } else if (absDeltaY > absDeltaX || deltaX > 0) {
        axis = 'vertical'
        return
      } else {
        return
      }
    }

    if (axis !== 'horizontal') {
      return
    }

    event.preventDefault()
    drawerPanel.classList.add(DRAGGING_CLASS)
    applyOffset(deltaX)
  }

  function handleTouchEnd(event: TouchEvent) {
    if (!drawerPanel || !tracking) {
      resetGestureState()
      return
    }

    if (event.changedTouches.length === 1) {
      finalTouchTime = performance.now()
    }

    if (axis !== 'horizontal') {
      resetGestureState()
      return
    }

    const distance = Math.abs(currentOffset)
    const elapsed = Math.max(finalTouchTime - startTime, 1)
    const velocity = distance / elapsed

    if (distance >= panelWidth * dismissDistanceRatio || velocity >= dismissVelocity) {
      animateDismiss()
      return
    }

    animateBack()
  }

  function handleTouchCancel() {
    if (axis === 'horizontal') {
      animateBack()
      return
    }

    resetGestureState()
  }

  async function findDrawerPanel() {
    for (let attempt = 0; attempt < 6; attempt += 1) {
      await nextTick()
      const panel = document.querySelector(drawerSelector)
      if (panel instanceof HTMLElement) {
        return panel
      }
      await new Promise<void>((resolve) => window.requestAnimationFrame(() => resolve()))
    }

    return null
  }

  async function setupPanel() {
    teardownPanel()

    if (!isEnabled.value || !isOpen.value) {
      return
    }

    drawerPanel = await findDrawerPanel()
    if (!drawerPanel) {
      return
    }

    drawerPanel.addEventListener('touchstart', handleTouchStart, { passive: true })
    drawerPanel.addEventListener('touchmove', handleTouchMove, { passive: false })
    drawerPanel.addEventListener('touchend', handleTouchEnd, { passive: true })
    drawerPanel.addEventListener('touchcancel', handleTouchCancel, { passive: true })
  }

  watch([isEnabled, isOpen], () => {
    void setupPanel()
  })

  onBeforeUnmount(() => {
    teardownPanel()
  })

  function resetDrawerSwipe() {
    clearDismissTimer()
    dismissing = false
    const fallbackPanel = document.querySelector(drawerSelector)
    if (fallbackPanel instanceof HTMLElement) {
      resetPanelStyles(fallbackPanel)
    } else {
      resetPanelStyles()
    }
    resetGestureState()
  }

  return {
    resetDrawerSwipe,
  }
}
