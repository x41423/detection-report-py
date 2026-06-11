import api from './client'

export interface ServiceStatus {
  status: string
  port: number
  host: string
}

export interface SystemStatusResponse {
  success: boolean
  data: {
    timestamp: string
    uptime_seconds: number
    services: {
      backend: ServiceStatus
      nginx: ServiceStatus
      mysql: ServiceStatus
      minio: ServiceStatus
    }
    cpu: {
      percent: number
      cores: number
      process_percent: number
    }
    memory: {
      total_gb: number
      used_gb: number
      available_gb: number
      percent: number
      process_percent: number
    }
    process: {
      pid: number
      rss_mb: number
      vms_mb: number
      threads: number
    }
    disk: {
      total_gb: number
      used_gb: number
      percent: number
      project_gb: number
    }
    memory_trend: Array<{ time: string; rss_mb: number }>
    alerts: Array<{
      level: string
      message: string
      current_mb: number
      consecutive_growth: number
      time: string
    }>
    perf_stats: Record<string, {
      path: string
      count: number
      avg_ms: number
      p50_ms: number
      p95_ms: number | null
      max_ms: number
    }>
  }
}

export interface LogTailResponse {
  success: boolean
  lines: string[]
  file: string
  total_lines_in_file: number
}

export function fetchSystemStatus(): Promise<SystemStatusResponse> {
  return api.get('/api/system/status').then(r => r.data)
}

export function fetchLogTail(
  lines = 20,
  file: 'app' | 'error' | 'access' = 'app'
): Promise<LogTailResponse> {
  return api
    .get('/api/system/logs/tail', { params: { lines, file } })
    .then(r => r.data)
}
