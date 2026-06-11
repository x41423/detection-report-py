<template>
  <div class="page-shell page-shell--full system-monitor-page">
    <PageHero
      eyebrow="系统监控"
      title="中控台"
      description="实时查看服务器运行状态、资源使用、日志和告警。"
      tone="sun"
    />

    <!-- 服务状态 -->
    <el-row :gutter="16" class="status-row">
      <el-col v-for="svc in serviceList" :key="svc.key" :span="6">
        <el-card shadow="never" class="status-card">
          <div class="svc-label">{{ svc.label }}</div>
          <el-tag
            :type="svc.status === 'up' ? 'success' : 'danger'"
            size="small"
            effect="dark"
          >
            {{ svc.status === 'up' ? '● 运行中' : '● 已停止' }}
          </el-tag>
          <div class="svc-port">{{ svc.host }}:{{ svc.port }}</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 资源指标 -->
    <el-row :gutter="16" style="margin-top: 16px">
      <el-col :span="8">
        <el-card shadow="never">
          <template #header>CPU</template>
          <div class="metric-value">{{ status.cpu.percent }}%</div>
          <div class="segmented-bar">
            <div class="seg-binxian" :style="{ width: status.cpu.process_percent + '%' }" />
            <div class="seg-other" :style="{ width: (status.cpu.percent - status.cpu.process_percent) + '%' }" />
          </div>
          <div class="seg-legend">
            <span class="seg-legend-dot seg-legend-dot--binxian"></span>滨鲜 {{ status.cpu.process_percent }}%
            <span class="seg-legend-dot seg-legend-dot--other"></span>其他 {{ (status.cpu.percent - status.cpu.process_percent).toFixed(1) }}%
          </div>
          <div class="metric-sub">{{ status.cpu.cores }} 核</div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="never">
          <template #header>内存</template>
          <div class="metric-value">{{ status.memory.percent }}%</div>
          <div class="segmented-bar">
            <div class="seg-binxian" :style="{ width: status.memory.process_percent + '%' }" />
            <div class="seg-other" :style="{ width: (status.memory.percent - status.memory.process_percent) + '%' }" />
          </div>
          <div class="seg-legend">
            <span class="seg-legend-dot seg-legend-dot--binxian"></span>滨鲜 {{ status.memory.process_percent }}%
            <span class="seg-legend-dot seg-legend-dot--other"></span>其他 {{ (status.memory.percent - status.memory.process_percent).toFixed(1) }}%
          </div>
          <div class="metric-sub">
            {{ status.memory.used_gb }} / {{ status.memory.total_gb }} GB
          </div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="never">
          <template #header>磁盘</template>
          <div class="metric-value">{{ status.disk.percent }}%</div>
          <div class="segmented-bar">
            <div class="seg-binxian" :style="{ width: diskBinxianPercent + '%' }" />
            <div class="seg-other" :style="{ width: (status.disk.percent - diskBinxianPercent) + '%' }" />
          </div>
          <div class="seg-legend">
            <span class="seg-legend-dot seg-legend-dot--binxian"></span>滨鲜 {{ status.disk.project_gb }} GB
            <span class="seg-legend-dot seg-legend-dot--other"></span>其他 {{ (status.disk.used_gb - status.disk.project_gb).toFixed(1) }} GB
          </div>
          <div class="metric-sub">
            {{ status.disk.used_gb }} / {{ status.disk.total_gb }} GB
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 进程 + 趋势 -->
    <el-row :gutter="16" style="margin-top: 16px">
      <el-col :span="8">
        <el-card shadow="never">
          <template #header>Python 进程</template>
          <el-descriptions :column="1" size="small" border>
            <el-descriptions-item label="PID">{{ status.process.pid }}</el-descriptions-item>
            <el-descriptions-item label="RSS">{{ status.process.rss_mb }} MB</el-descriptions-item>
            <el-descriptions-item label="VMS">{{ status.process.vms_mb }} MB</el-descriptions-item>
            <el-descriptions-item label="线程">{{ status.process.threads }}</el-descriptions-item>
            <el-descriptions-item label="运行时间">{{ uptimeStr }}</el-descriptions-item>
          </el-descriptions>
        </el-card>
      </el-col>
      <el-col :span="16">
        <el-card shadow="never">
          <template #header>内存趋势（最近 1 小时 · RSS MB）</template>
          <div class="trend-bar">
            <div
              v-for="(pt, i) in status.memory_trend"
              :key="i"
              class="trend-bar-item"
              :style="{ height: trendHeight(pt.rss_mb) + '%' }"
              :title="pt.time + ' — ' + pt.rss_mb + ' MB'"
            />
            <div v-if="!status.memory_trend.length" class="trend-empty">
              采集数据中，请稍后...
            </div>
          </div>
          <div class="trend-range">
            <span>{{ trendMin }} MB</span>
            <span>{{ trendMax }} MB</span>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 性能统计 -->
    <el-row :gutter="16" style="margin-top: 16px">
      <el-col :span="24">
        <el-card shadow="never">
          <template #header>API 性能统计（最近 1000 次请求）</template>
          <el-table :data="perfRows" size="small" v-if="perfRows.length">
            <el-table-column prop="path" label="端点" width="220" />
            <el-table-column prop="count" label="请求数" width="100" />
            <el-table-column prop="avg_ms" label="平均(ms)" width="100" />
            <el-table-column prop="p50_ms" label="P50(ms)" width="100" />
            <el-table-column prop="p95_ms" label="P95(ms)" width="100" />
            <el-table-column prop="max_ms" label="最大(ms)" width="100" />
          </el-table>
          <div v-else class="text-muted">暂无数据</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 告警 -->
    <el-row :gutter="16" style="margin-top: 16px" v-if="status.alerts.length">
      <el-col :span="24">
        <el-card shadow="never">
          <template #header>⚠️ 告警（{{ status.alerts.length }}）</template>
          <el-alert
            v-for="(alert, i) in status.alerts"
            :key="i"
            :title="alert.time + ' — ' + alert.message"
            :type="alert.level === 'critical' ? 'error' : 'warning'"
            :closable="false"
            show-icon
            style="margin-bottom: 8px"
          />
        </el-card>
      </el-col>
    </el-row>

    <!-- 日志流 -->
    <el-row :gutter="16" style="margin-top: 16px">
      <el-col :span="24">
        <el-card shadow="never">
          <template #header>
            <span>📋 最近日志</span>
            <el-radio-group
              v-model="logFile"
              size="small"
              style="margin-left: 16px"
              @change="fetchLogs"
            >
              <el-radio-button value="app">应用</el-radio-button>
              <el-radio-button value="error">错误</el-radio-button>
              <el-radio-button value="access">请求</el-radio-button>
            </el-radio-group>
          </template>
          <pre class="log-tail"><code><div
  v-for="(line, i) in logLines"
  :key="i"
          :class="{ 'log-error': isLogError(line) }"
>{{ line }}</div></code></pre>
        </el-card>
      </el-col>
    </el-row>

    <!-- 刷新状态 -->
    <div class="refresh-bar">
      🔄 自动刷新（每 5 秒）&nbsp;·&nbsp;最后更新：{{ lastRefresh }}
      &nbsp;·&nbsp;{{ errorMsg }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { fetchSystemStatus, fetchLogTail } from '../api/system-monitor'
import type { SystemStatusResponse } from '../api/system-monitor'

const REFRESH_INTERVAL = 5000

const status = ref<SystemStatusResponse['data']>({
  timestamp: '',
  uptime_seconds: 0,
  services: { backend: { status: 'unknown', port: 0, host: '' }, nginx: { status: 'unknown', port: 0, host: '' }, mysql: { status: 'unknown', port: 0, host: '' }, minio: { status: 'unknown', port: 0, host: '' } },
  cpu: { percent: 0, cores: 0, process_percent: 0 },
  memory: { total_gb: 0, used_gb: 0, available_gb: 0, percent: 0, process_percent: 0 },
  process: { pid: 0, rss_mb: 0, vms_mb: 0, threads: 0 },
  disk: { total_gb: 0, used_gb: 0, percent: 0, project_gb: 0 },
  memory_trend: [],
  alerts: [],
  perf_stats: {},
})

const logLines = ref<string[]>([])
const logFile = ref<'app' | 'error' | 'access'>('app')
const lastRefresh = ref('--')
const errorMsg = ref('')
let timer: ReturnType<typeof setInterval>

const serviceList = computed(() => [
  { key: 'backend', label: '后端 API', ...status.value.services.backend },
  { key: 'nginx', label: 'Nginx', ...status.value.services.nginx },
  { key: 'mysql', label: 'MySQL', ...status.value.services.mysql },
  { key: 'minio', label: 'MinIO', ...status.value.services.minio },
])

const uptimeStr = computed(() => {
  const s = status.value.uptime_seconds
  if (s < 60) return s + ' 秒'
  if (s < 3600) return Math.floor(s / 60) + ' 分'
  return Math.floor(s / 3600) + ' 小时 ' + Math.floor((s % 3600) / 60) + ' 分'
})

const trendMin = computed(() => {
  const vals = status.value.memory_trend.map(p => p.rss_mb)
  return vals.length ? Math.min(...vals).toFixed(0) : '0'
})

const trendMax = computed(() => {
  const vals = status.value.memory_trend.map(p => p.rss_mb)
  return vals.length ? Math.max(...vals).toFixed(0) : '0'
})

const trendHeight = (mb: number) => {
  const max = Math.max(...status.value.memory_trend.map(p => p.rss_mb), 1)
  return Math.round((mb / max) * 100)
}

const cpuColor = computed(() => {
  if (status.value.cpu.percent > 80) return '#F56C6C'
  if (status.value.cpu.percent > 50) return '#E6A23C'
  return '#67C23A'
})

const memColor = computed(() => {
  if (status.value.memory.percent > 90) return '#F56C6C'
  if (status.value.memory.percent > 75) return '#E6A23C'
  return '#67C23A'
})

const diskColor = computed(() => {
  if (status.value.disk.percent > 90) return '#F56C6C'
  if (status.value.disk.percent > 75) return '#E6A23C'
  return '#67C23A'
})

const diskBinxianPercent = computed(() => {
  if (!status.value.disk.total_gb) return 0
  return Number(((status.value.disk.project_gb / status.value.disk.total_gb) * 100).toFixed(1))
})

const perfRows = computed(() =>
  Object.values(status.value.perf_stats)
)

async function fetchStatus() {
  try {
    const resp = await fetchSystemStatus()
    if (resp && resp.success && resp.data) {
      status.value = resp.data
      errorMsg.value = ''
    } else {
      errorMsg.value = '状态数据格式异常'
    }
  } catch (e: any) {
    errorMsg.value = '获取状态失败: ' + (e?.message || '网络错误')
  }
  lastRefresh.value = new Date().toLocaleTimeString()
}

async function fetchLogs() {
  try {
    const resp = await fetchLogTail(15, logFile.value)
    logLines.value = resp.lines
  } catch {
    // silently ignore log fetch errors
  }
}

function isLogError(line: string): boolean {
  return line.includes('"level": "ERROR"') || line.includes('"level": "WARNING"')
}

onMounted(() => {
  fetchStatus()
  fetchLogs()
  timer = setInterval(() => {
    fetchStatus()
    fetchLogs()
  }, REFRESH_INTERVAL)
})

onUnmounted(() => clearInterval(timer))
</script>

<style scoped>
.status-row {
  margin-bottom: 0;
}
.status-card {
  text-align: center;
}
.svc-label {
  font-size: 14px;
  color: #606266;
  margin-bottom: 8px;
}
.svc-port {
  font-size: 12px;
  color: #909399;
  margin-top: 6px;
}
.metric-value {
  font-size: 32px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 8px;
}
.bar-label {
  font-size: 12px;
  color: #909399;
  margin-bottom: 2px;
}
/* ---- 分段进度条 ---- */
.segmented-bar {
  display: flex;
  height: 14px;
  border-radius: 7px;
  overflow: hidden;
  background: #F2F3F5;
  margin: 8px 0 6px;
}
.seg-binxian {
  background: #67C23A;
  min-width: 0;
  transition: width 0.4s ease;
  flex-shrink: 0;
}
.seg-other {
  background: #C0C4CC;
  min-width: 0;
  transition: width 0.4s ease;
  flex-shrink: 0;
}
.seg-legend {
  font-size: 12px;
  color: #606266;
  display: flex;
  gap: 12px;
  align-items: center;
}
.seg-legend-dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  margin-right: 2px;
}
.seg-legend-dot--binxian {
  background: #67C23A;
}
.seg-legend-dot--other {
  background: #C0C4CC;
}
.metric-sub {
  font-size: 13px;
  color: #909399;
  margin-top: 8px;
}
.trend-bar {
  display: flex;
  align-items: flex-end;
  height: 120px;
  gap: 2px;
  padding: 4px 0;
}
.trend-bar-item {
  flex: 1;
  background: #409EFF;
  border-radius: 2px 2px 0 0;
  min-height: 2px;
  opacity: 0.85;
  transition: height 0.3s ease;
}
.trend-bar-item:hover {
  opacity: 1;
  background: #337ECC;
}
.trend-empty {
  color: #909399;
  font-size: 14px;
  align-self: center;
  width: 100%;
  text-align: center;
}
.trend-range {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}
.log-tail {
  background: #1e1e1e;
  color: #d4d4d4;
  padding: 12px;
  border-radius: 6px;
  font-size: 12px;
  line-height: 1.6;
  max-height: 300px;
  overflow-y: auto;
  margin: 0;
}
.log-tail code {
  font-family: 'Cascadia Code', 'Fira Code', 'Consolas', monospace;
}
.log-error {
  color: #F56C6C;
}
.refresh-bar {
  text-align: center;
  color: #909399;
  font-size: 12px;
  margin-top: 24px;
  padding-bottom: 16px;
}
.text-muted {
  color: #909399;
  text-align: center;
  padding: 24px;
}
</style>
