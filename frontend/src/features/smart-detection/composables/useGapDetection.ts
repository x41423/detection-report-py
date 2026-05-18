import { ref } from 'vue'
import { getSmartGaps, postSmartBackfill, type GapResponse, type BackfillResponse } from '@/api/smart-detection'

export function useGapDetection() {
  const gaps = ref<GapResponse | null>(null)
  const loading = ref(false)
  const backfilling = ref(false)
  const backfillResult = ref<BackfillResponse | null>(null)
  const error = ref<string | null>(null)

  async function checkGaps(days = 7) {
    loading.value = true
    error.value = null
    try {
      gaps.value = await getSmartGaps(days)
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : '检查遗漏失败'
    } finally {
      loading.value = false
    }
  }

  async function backfill(startDate: string, endDate: string, inspectorName: string) {
    backfilling.value = true
    error.value = null
    try {
      backfillResult.value = await postSmartBackfill({
        start_date: startDate,
        end_date: endDate,
        inspector_name: inspectorName,
      })
      return backfillResult.value
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : '补做失败'
      return null
    } finally {
      backfilling.value = false
    }
  }

  return { gaps, loading, backfilling, backfillResult, error, checkGaps, backfill }
}
