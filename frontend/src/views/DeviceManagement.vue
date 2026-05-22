<template>
  <div class="page-shell device-page">
    <PageHero
      eyebrow="账号安全"
      title="管理已登录设备"
      description="查看当前账号登记过的浏览器或平板，给设备改名便于识别；发现不再使用或异常的设备时，可以立即撤销它的登录会话。"
      tone="green"
    >
      <template #actions>
        <el-button type="primary" size="large" :loading="isLoading" @click="loadDevices">
          <el-icon><RefreshRight /></el-icon>
          刷新设备
        </el-button>
      </template>

      <template #aside>
        <div class="device-hero-metrics">
          <div class="device-hero-metric">
            <span>登记设备</span>
            <strong>{{ devices.length }}</strong>
          </div>
          <div class="device-hero-metric">
            <span>有效设备</span>
            <strong>{{ activeDeviceCount }}</strong>
          </div>
          <div class="device-hero-metric device-hero-metric--wide">
            <span>当前设备</span>
            <strong>{{ currentDeviceLabel }}</strong>
          </div>
        </div>
      </template>
    </PageHero>

    <el-card shadow="never" class="panel-card device-toolbar">
      <div>
        <div class="panel-heading__eyebrow">设备会话</div>
        <h2 class="panel-heading__title">设备列表</h2>
        <p class="panel-heading__description">
          撤销设备会同步撤销该设备下所有未过期会话；撤销当前设备会清除本机登录状态并返回登录页。
        </p>
      </div>

      <el-tag v-if="!canRename || !canRevoke" type="warning" effect="plain">
        当前账号只有部分设备管理权限
      </el-tag>
    </el-card>

    <div v-loading="isLoading" class="device-grid">
      <el-card
        v-for="device in devices"
        :key="device.id"
        shadow="never"
        class="panel-card device-card"
        :class="{
          'device-card--current': device.is_current,
          'device-card--revoked': device.is_revoked,
        }"
      >
        <div class="device-card__topline">
          <div class="device-card__icon">
            <el-icon><Monitor /></el-icon>
          </div>
          <div class="device-card__status">
            <el-tag v-if="device.is_current" type="success" effect="dark">当前设备</el-tag>
            <el-tag v-if="device.is_revoked" type="info" effect="plain">已撤销</el-tag>
          </div>
        </div>

        <div class="device-card__main">
          <h2>{{ displayDeviceName(device) }}</h2>
          <p>{{ summarizeUserAgent(device.user_agent) }}</p>
        </div>

        <div class="device-card__facts">
          <div>
            <span>IP 地址</span>
            <strong>{{ device.ip_address || '未知' }}</strong>
          </div>
          <div>
            <span>有效会话</span>
            <strong>{{ device.active_session_count }}</strong>
          </div>
          <div>
            <span>首次登录</span>
            <strong>{{ formatDateTime(device.first_login_at) }}</strong>
          </div>
          <div>
            <span>最近活跃</span>
            <strong>{{ formatDateTime(device.last_active_at) }}</strong>
          </div>
        </div>

        <div class="device-card__actions">
          <el-button
            v-if="canRename"
            :disabled="device.is_revoked"
            :loading="mutatingDeviceId === device.id"
            @click="handleRename(device)"
          >
            <el-icon><EditPen /></el-icon>
            重命名
          </el-button>
          <el-button
            v-if="canRevoke"
            type="danger"
            plain
            :disabled="device.is_revoked"
            :loading="mutatingDeviceId === device.id"
            @click="handleRevoke(device)"
          >
            <el-icon><SwitchButton /></el-icon>
            撤销设备
          </el-button>
        </div>
      </el-card>

      <el-card v-if="!isLoading && devices.length === 0" shadow="never" class="panel-card device-empty">
        <div class="device-empty__icon">
          <el-icon><Monitor /></el-icon>
        </div>
        <h2>暂无设备记录</h2>
        <p>登录成功后系统会自动登记当前浏览器或设备；如果这里为空，请刷新页面或重新登录。</p>
      </el-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { EditPen, Monitor, RefreshRight, SwitchButton } from '@element-plus/icons-vue'

import { listDevices, renameDevice, revokeDevice, type AuthDevice } from '../api/auth'
import PageHero from '../components/PageHero.vue'
import { useAuth } from '../composables/useAuth'

const router = useRouter()
const auth = useAuth()
const devices = ref<AuthDevice[]>([])
const isLoading = ref(false)
const mutatingDeviceId = ref<number | null>(null)

const canRename = computed(() => auth.hasPermission('device:rename'))
const canRevoke = computed(() => auth.hasPermission('device:revoke'))
const activeDeviceCount = computed(() => devices.value.filter((device) => !device.is_revoked).length)
const currentDevice = computed(() => devices.value.find((device) => device.is_current) ?? null)
const currentDeviceLabel = computed(() => (currentDevice.value ? displayDeviceName(currentDevice.value) : '未识别'))

onMounted(() => {
  void loadDevices()
})

async function loadDevices() {
  isLoading.value = true
  try {
    const response = await listDevices()
    devices.value = response.data.devices
  } catch {
    ElMessage.error('设备列表加载失败')
  } finally {
    isLoading.value = false
  }
}

async function handleRename(device: AuthDevice) {
  try {
    const result = await ElMessageBox.prompt('请输入便于识别的设备名称。', '重命名设备', {
      confirmButtonText: '保存',
      cancelButtonText: '取消',
      inputValue: displayDeviceName(device),
      inputValidator: (value: string) => {
        const cleanValue = value.trim()
        if (!cleanValue) {
          return '设备名称不能为空'
        }
        if (cleanValue.length > 64) {
          return '设备名称不能超过 64 个字符'
        }
        return true
      },
    })
    const nextName = String(result.value ?? '').trim()
    mutatingDeviceId.value = device.id
    const response = await renameDevice(device.id, { device_name: nextName })
    replaceDevice(response.data.device)
    ElMessage.success('设备名称已更新')
  } catch (error) {
    if (!isMessageBoxCancel(error)) {
      ElMessage.error('设备重命名失败')
    }
  } finally {
    mutatingDeviceId.value = null
  }
}

async function handleRevoke(device: AuthDevice) {
  try {
    await ElMessageBox.confirm(
      device.is_current
        ? '撤销当前设备会立即退出本机登录状态，需要重新登录后才能继续使用。'
        : '撤销后，该设备上的登录会话会立即失效。',
      '确认撤销设备',
      {
        type: 'warning',
        confirmButtonText: '撤销设备',
        cancelButtonText: '取消',
      },
    )
    mutatingDeviceId.value = device.id
    const response = await revokeDevice(device.id)
    replaceDevice(response.data.device)
    ElMessage.success('设备已撤销')
    if (response.data.device.is_current) {
      auth.resetAuthState()
      await router.replace('/login')
      return
    }
    await loadDevices()
  } catch (error) {
    if (!isMessageBoxCancel(error)) {
      ElMessage.error('设备撤销失败')
    }
  } finally {
    mutatingDeviceId.value = null
  }
}

function replaceDevice(nextDevice: AuthDevice) {
  devices.value = devices.value.map((device) => (device.id === nextDevice.id ? nextDevice : device))
}

function displayDeviceName(device: AuthDevice) {
  return device.device_name || (device.is_current ? '当前设备' : '未命名设备')
}

function summarizeUserAgent(userAgent: string) {
  const cleanValue = userAgent.trim()
  if (!cleanValue) {
    return '未提供 User-Agent'
  }
  return cleanValue.length > 120 ? `${cleanValue.slice(0, 120)}...` : cleanValue
}

function formatDateTime(value: string | null) {
  if (!value) {
    return '未知'
  }
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return value
  }
  return new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date)
}

function isMessageBoxCancel(error: unknown) {
  return error === 'cancel' || error === 'close'
}
</script>

<style scoped>
.device-page {
  gap: 16px;
}

.device-hero-metrics {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
  width: 100%;
}

.device-hero-metric {
  display: grid;
  gap: 6px;
  padding: 14px;
  border-radius: var(--radius-md);
  background: #ffffff;
  box-shadow: var(--shadow-glass);
}

.device-hero-metric--wide {
  grid-column: 1 / -1;
}

.device-hero-metric span {
  color: var(--color-muted-soft);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}

.device-hero-metric strong {
  color: var(--color-text);
  font-family: var(--font-heading);
  font-size: clamp(22px, 3vw, 30px);
  font-weight: 600;
  line-height: 1.1;
  overflow-wrap: anywhere;
}

.device-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  padding: 20px;
}

.device-toolbar h2,
.device-toolbar p {
  margin: 0;
}

.device-toolbar p {
  margin-top: 8px;
  max-width: 720px;
}

.device-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
  min-height: 240px;
}

.device-card {
  position: relative;
  overflow: hidden;
  border-radius: var(--radius-lg);
  background: #ffffff;
}

.device-card :deep(.el-card__body) {
  display: grid;
  gap: 18px;
}

.device-card--current {
  border-color: var(--color-primary);
}

.device-card--revoked {
  opacity: 0.72;
  background: var(--color-surface-card);
}

.device-card__topline {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
}

.device-card__icon {
  display: grid;
  place-items: center;
  width: 42px;
  height: 42px;
  border-radius: var(--radius-md);
  background: var(--color-primary);
  color: #ffffff;
  font-size: 20px;
}

.device-card__status {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 8px;
}

.device-card__main {
  display: grid;
  gap: 8px;
}

.device-card__main h2 {
  margin: 0;
  color: var(--color-text);
  font-family: var(--font-heading);
  font-size: 22px;
  font-weight: 600;
  line-height: 1.2;
}

.device-card__main p {
  margin: 0;
  color: var(--color-muted);
  font-size: 13px;
  line-height: 1.65;
  overflow-wrap: anywhere;
}

.device-card__facts {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.device-card__facts div {
  display: grid;
  gap: 6px;
  min-width: 0;
  padding: 12px;
  border-radius: var(--radius-md);
  background: var(--color-surface-card);
}

.device-card__facts span {
  color: var(--color-muted-soft);
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.device-card__facts strong {
  color: var(--color-text);
  font-family: var(--font-body);
  font-weight: 600;
  font-size: 14px;
  overflow-wrap: anywhere;
}

.device-card__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.device-empty {
  grid-column: 1 / -1;
  display: grid;
  justify-items: start;
  gap: 12px;
  padding: 30px;
  border-radius: var(--radius-lg);
}

.device-empty__icon {
  display: grid;
  place-items: center;
  width: 44px;
  height: 44px;
  border-radius: var(--radius-md);
  background: #242424;
  color: var(--color-text);
  color: #ffffff;
  font-size: 20px;
}

.device-empty h2,
.device-empty p {
  margin: 0;
}

.device-empty h2 {
  color: var(--color-text);
  font-family: var(--font-heading);
  font-size: 22px;
  font-weight: 600;
}

.device-empty p {
  color: var(--color-muted);
  line-height: 1.75;
}

@media (max-width: 1040px) {
  .device-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 720px) {
  .device-toolbar {
    align-items: flex-start;
    flex-direction: column;
    padding: 18px;
  }

  .device-card__facts {
    grid-template-columns: 1fr;
  }

  .device-card__actions .el-button {
    width: 100%;
  }
}

@media (max-width: 430px) {
  .device-hero-metrics,
  .device-card__actions {
    grid-template-columns: 1fr;
  }

  .device-hero-metric {
    padding: 14px;
    border-radius: var(--radius-md);
  }

  .device-card__main h2 {
    font-size: 24px;
  }
}
</style>
