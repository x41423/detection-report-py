<template>
  <div class="auth-access">
    <div class="auth-card">
      <div class="auth-card__header">
        <div class="auth-card__brand">滨</div>
        <h1 class="auth-card__title">{{ isRegister ? '注册账号' : '欢迎回来' }}</h1>
        <p class="auth-card__subtitle">
          {{ isRegister ? '创建账号后请联系管理员开通业务权限。' : '请使用账号密码登录滨鲜检测工具集。' }}
        </p>
      </div>

      <el-form
        ref="formRef"
        :model="form"
        :rules="formRules"
        label-position="top"
        @keydown.enter.prevent="onSubmit"
      >
        <el-form-item label="用户名" prop="username">
          <el-input v-model="form.username" placeholder="请输入用户名" autocomplete="username" />
        </el-form-item>

        <el-form-item v-if="isRegister" label="显示名称" prop="display_name">
          <el-input v-model="form.display_name" placeholder="可选，留空则使用用户名" />
        </el-form-item>

        <el-form-item label="密码" prop="password">
          <el-input
            v-model="form.password"
            type="password"
            show-password
            :placeholder="isRegister ? '至少 8 位，建议混合字母数字' : '请输入密码'"
            :autocomplete="isRegister ? 'new-password' : 'current-password'"
          />
        </el-form-item>

        <el-form-item v-if="!isRegister" label="设备名称">
          <el-input v-model="form.device_name" :placeholder="defaultDeviceName" />
          <div class="auth-form__hint">设备名将记录到登录设备列表，方便随时撤销。</div>
        </el-form-item>

        <el-button
          type="primary"
          size="large"
          :loading="auth.isLoading.value"
          class="auth-form__submit"
          @click="onSubmit"
        >
          {{ isRegister ? '注册账号' : '登录' }}
        </el-button>
      </el-form>

      <div class="auth-card__switch">
        <template v-if="isRegister">
          <span>已有账号？</span>
          <router-link :to="{ name: 'login', query: route.query }">前往登录</router-link>
        </template>
        <template v-else>
          <span>还没有账号？</span>
          <router-link :to="{ name: 'register', query: route.query }">立即注册</router-link>
        </template>
      </div>
    </div>

    <el-dialog v-model="deviceDialog.visible" title="该账号已达设备上限" width="480px" append-to-body>
      <p class="auth-dialog__desc">{{ deviceDialog.message }}</p>
      <el-radio-group v-model="deviceDialog.selectedId" class="auth-dialog__list">
        <el-radio
          v-for="device in deviceDialog.devices"
          :key="device.id"
          :label="device.id"
          class="auth-dialog__item"
        >
          <div class="auth-dialog__item-name">{{ device.device_name || '未命名设备' }}</div>
          <div class="auth-dialog__item-meta">{{ device.user_agent || '未知客户端' }} · 最近活跃 {{ device.last_active_at || '—' }}</div>
        </el-radio>
      </el-radio-group>
      <template #footer>
        <el-button @click="cancelDeviceReplacement">取消</el-button>
        <el-button type="primary" :loading="auth.isLoading.value" @click="confirmDeviceReplacement">
          替换并登录
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'

import { isPendingLoginResponse, type AuthDevice, type AuthPendingLoginResponse } from '../api/auth'
import { useAuth } from '../composables/useAuth'

const auth = useAuth()
const route = useRoute()
const router = useRouter()

const formRef = ref<FormInstance>()

const isRegister = computed(() => route.name === 'register')

const defaultDeviceName = computed(() => {
  if (typeof navigator === 'undefined') {
    return '当前浏览器'
  }
  return `${navigator.platform || 'Web'} · ${navigator.userAgent.split(' ').slice(-1)[0] || ''}`.trim()
})

const form = reactive({
  username: '',
  password: '',
  display_name: '',
  device_name: '',
})

const formRules = computed<FormRules>(() => ({
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, message: '用户名至少 3 个字符', trigger: 'blur' },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: isRegister.value ? 8 : 1, message: '密码至少 8 位', trigger: 'blur' },
  ],
}))

const deviceDialog = reactive<{
  visible: boolean
  message: string
  devices: AuthDevice[]
  pendingToken: string
  selectedId: number | null
}>({
  visible: false,
  message: '',
  devices: [],
  pendingToken: '',
  selectedId: null,
})

watch(
  () => route.name,
  () => {
    form.password = ''
  },
)

async function onSubmit() {
  if (!formRef.value) return
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  if (isRegister.value) {
    try {
      const response = await auth.register({
        username: form.username.trim(),
        password: form.password,
        display_name: form.display_name.trim() || undefined,
      })
      ElMessage.success(response.message || '注册成功，请登录')
      await router.push({ name: 'login', query: route.query })
    } catch (error: unknown) {
      ElMessage.error(extractErrorMessage(error, '注册失败'))
    }
    return
  }

  try {
    const result = await auth.login({
      username: form.username.trim(),
      password: form.password,
      device_name: form.device_name.trim() || defaultDeviceName.value,
    })
    if (isPendingLoginResponse(result)) {
      openDeviceDialog(result)
      return
    }
    ElMessage.success('登录成功')
    await redirectAfterLogin()
  } catch (error: unknown) {
    ElMessage.error(extractErrorMessage(error, '登录失败'))
  }
}

function openDeviceDialog(payload: AuthPendingLoginResponse) {
  deviceDialog.visible = true
  deviceDialog.message = payload.message
  deviceDialog.devices = payload.devices
  deviceDialog.pendingToken = payload.pending_token
  deviceDialog.selectedId = payload.devices[0]?.id ?? null
}

async function confirmDeviceReplacement() {
  if (!deviceDialog.selectedId) {
    ElMessage.warning('请选择一台要替换的设备')
    return
  }
  try {
    await auth.replaceDeviceLogin({
      pending_token: deviceDialog.pendingToken,
      replace_device_id: deviceDialog.selectedId,
    })
    ElMessage.success('登录成功')
    deviceDialog.visible = false
    await redirectAfterLogin()
  } catch (error: unknown) {
    ElMessage.error(extractErrorMessage(error, '设备替换失败'))
  }
}

function cancelDeviceReplacement() {
  deviceDialog.visible = false
  deviceDialog.pendingToken = ''
  deviceDialog.selectedId = null
}

async function redirectAfterLogin() {
  const target = typeof route.query.redirect === 'string' ? route.query.redirect : '/'
  await router.push(target)
}

function extractErrorMessage(error: unknown, fallback: string): string {
  if (error && typeof error === 'object' && 'response' in error) {
    const response = (error as { response?: { data?: { detail?: string; message?: string } } }).response
    return response?.data?.detail || response?.data?.message || fallback
  }
  if (error instanceof Error) {
    return error.message || fallback
  }
  return fallback
}
</script>

<style scoped>
.auth-access {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  min-height: 100vh;
  padding: 32px 16px;
  background: #f8f9fa;
}

.auth-card {
  width: 100%;
  max-width: 420px;
  padding: 32px 28px;
  border-radius: var(--radius-lg);
  background: var(--color-surface);
  box-shadow: var(--shadow-card);
  border: 1px solid var(--color-border);
}

.auth-card__header {
  text-align: center;
  margin-bottom: 24px;
}

.auth-card__brand {
  width: 48px;
  height: 48px;
  margin: 0 auto 16px;
  border-radius: var(--radius-md);
  background: var(--color-primary);
  color: #ffffff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: var(--font-heading);
  font-size: 22px;
  font-weight: 600;
}

.auth-card__title {
  margin: 0 0 8px;
  font-family: var(--font-heading);
  font-size: 22px;
  font-weight: 600;
  color: var(--color-text);
}

.auth-card__subtitle {
  margin: 0;
  color: var(--color-muted);
  font-size: 13px;
  line-height: 1.6;
}

.auth-form__submit {
  width: 100%;
  margin-top: 8px;
}

.auth-form__hint {
  margin-top: 6px;
  color: var(--color-muted);
  font-size: 11px;
}

.auth-card__switch {
  margin-top: 20px;
  text-align: center;
  font-size: 13px;
  color: var(--color-muted);
}

.auth-card__switch a {
  margin-left: 6px;
  color: var(--color-primary);
  font-weight: 600;
}

.auth-dialog__desc {
  margin: 0 0 16px;
  color: var(--color-muted);
  font-size: 13px;
  line-height: 1.6;
}

.auth-dialog__list {
  display: grid;
  gap: 8px;
  width: 100%;
}

.auth-dialog__item {
  width: 100%;
  margin: 0 !important;
  padding: 10px 12px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  align-items: flex-start;
}

.auth-dialog__item-name {
  font-weight: 600;
  color: var(--color-text);
  font-size: 13px;
}

.auth-dialog__item-meta {
  margin-top: 2px;
  color: var(--color-muted-soft);
  font-size: 11px;
}
</style>
