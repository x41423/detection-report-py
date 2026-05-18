import { ref, computed } from 'vue'
import {
  getSmartRecommend,
  postSmartExecute,
  type SmartRecommendItem,
  type SmartExecuteRequest,
  type SmartExecuteResponse,
} from '@/api/smart-detection'

export function useSmartDetection() {
  const todayIntakeItems = ref<SmartRecommendItem[]>([])
  const yesterdayInventoryItems = ref<SmartRecommendItem[]>([])
  const manualAdditions = ref<string[]>([])
  const missingDates = ref<string[]>([])

  const selectedToday = ref<Set<string>>(new Set())
  const selectedYesterday = ref<Set<string>>(new Set())

  const loading = ref(false)
  const executing = ref(false)
  const lastResult = ref<SmartExecuteResponse | null>(null)

  const allSelected = computed(() =>
    [...selectedToday.value, ...selectedYesterday.value, ...manualAdditions.value]
  )

  const totalRecommended = computed(() =>
    todayIntakeItems.value.length + yesterdayInventoryItems.value.length
  )

  const selectedCount = computed(() =>
    selectedToday.value.size + selectedYesterday.value.size + manualAdditions.value.length
  )

  const error = ref<string | null>(null)

  async function loadRecommendations(date?: string) {
    loading.value = true
    error.value = null
    try {
      const result = await getSmartRecommend(date)
      todayIntakeItems.value = result.today_intake
      yesterdayInventoryItems.value = result.yesterday_inventory
      missingDates.value = result.missing_dates

      selectedToday.value = new Set(result.today_intake.map(i => i.name))
      selectedYesterday.value = new Set(result.yesterday_inventory.map(i => i.name))
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : '加载推荐清单失败'
    } finally {
      loading.value = false
    }
  }

  function toggleToday(name: string) {
    const s = new Set(selectedToday.value)
    if (s.has(name)) s.delete(name)
    else s.add(name)
    selectedToday.value = s
  }

  function toggleYesterday(name: string) {
    const s = new Set(selectedYesterday.value)
    if (s.has(name)) s.delete(name)
    else s.add(name)
    selectedYesterday.value = s
  }

  function selectAllToday() {
    selectedToday.value = new Set(todayIntakeItems.value.map(i => i.name))
  }

  function deselectAllToday() {
    selectedToday.value = new Set()
  }

  function selectAllYesterday() {
    selectedYesterday.value = new Set(yesterdayInventoryItems.value.map(i => i.name))
  }

  function deselectAllYesterday() {
    selectedYesterday.value = new Set()
  }

  function addManual(name: string) {
    if (name && !manualAdditions.value.includes(name)) {
      manualAdditions.value.push(name)
    }
  }

  function removeManual(index: number) {
    manualAdditions.value.splice(index, 1)
  }

  async function execute(options: Omit<SmartExecuteRequest, 'selected_varieties' | 'manual_additions'>) {
    executing.value = true
    error.value = null
    try {
      const result = await postSmartExecute({
        ...options,
        selected_varieties: [...selectedToday.value, ...selectedYesterday.value],
        manual_additions: manualAdditions.value,
      })
      lastResult.value = result
      return result
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : '执行检测失败'
      return null
    } finally {
      executing.value = false
    }
  }

  function reset() {
    todayIntakeItems.value = []
    yesterdayInventoryItems.value = []
    manualAdditions.value = []
    selectedToday.value = new Set()
    selectedYesterday.value = new Set()
    lastResult.value = null
    error.value = null
  }

  return {
    todayIntakeItems, yesterdayInventoryItems, manualAdditions, missingDates,
    selectedToday, selectedYesterday,
    loading, executing, lastResult, error,
    allSelected, totalRecommended, selectedCount,
    loadRecommendations, toggleToday, toggleYesterday,
    selectAllToday, deselectAllToday, selectAllYesterday, deselectAllYesterday,
    addManual, removeManual, execute, reset,
  }
}
