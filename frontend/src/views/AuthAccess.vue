<template>
  <div class="auth-page">
    <AnimatedCharacters
      ref="charactersRef"
      :typing="formState.isTyping"
      :password-focused="formState.passwordFocused"
      :show-password="formState.showPassword"
      :login-error="formState.loginError"
      :is-register="isRegister"
    />
    <div class="right-panel">
      <div class="form-container">
        <div class="sparkle-icon">
          <svg viewBox="0 0 24 24" fill="none">
            <path d="M12 2L13.5 9H10.5L12 2Z" fill="#1a1a2e" />
            <path d="M12 22L10.5 15H13.5L12 22Z" fill="#1a1a2e" />
            <path d="M2 12L9 10.5V13.5L2 12Z" fill="#1a1a2e" />
            <path d="M22 12L15 13.5V10.5L22 12Z" fill="#1a1a2e" />
          </svg>
        </div>
        <div class="form-header">
          <h1>{{ isRegister ? '创建账号' : '欢迎回来' }}</h1>
          <p>{{ isRegister ? '加入滨鲜工作台，开始高效检测管理' : '请登录滨鲜工作台' }}</p>
        </div>

        <div class="error-msg" v-if="formState.errorText" style="display:block;">{{ formState.errorText }}</div>

        <form @submit.prevent="onSubmit">
          <div class="form-group">
            <label :class="{ 'error-label': formState.fieldErrors.username }" for="username">用户名</label>
            <div class="input-wrapper">
              <input
                id="username"
                v-model="form.username"
                type="text"
                placeholder="请输入用户名"
                autocomplete="username"
                :class="{ error: formState.fieldErrors.username }"
                @focus="onFieldFocus('username')"
                @blur="onFieldBlur"
                @input="onInput"
              />
            </div>
          </div>

          <div class="form-group" v-if="isRegister">
            <label for="display_name">显示名称</label>
            <div class="input-wrapper">
              <input
                id="display_name"
                v-model="form.display_name"
                type="text"
                placeholder="可选，留空则使用用户名"
                autocomplete="off"
                @focus="onFieldFocus('display_name')"
                @blur="onFieldBlur"
                @input="onInput"
              />
            </div>
          </div>

          <div class="form-group">
            <label :class="{ 'error-label': formState.fieldErrors.password }" for="password">密码</label>
            <div class="input-wrapper">
              <input
                id="password"
                v-model="form.password"
                :type="formState.showPassword ? 'text' : 'password'"
                :placeholder="isRegister ? '至少 8 位，建议混合字母数字' : '••••••••'"
                :autocomplete="isRegister ? 'new-password' : 'current-password'"
                :class="{ error: formState.fieldErrors.password }"
                @focus="onPasswordFocus"
                @blur="onPasswordBlur"
                @input="onInput"
              />
              <button type="button" class="toggle-password" @click="togglePassword" tabindex="-1">
                <svg v-if="!formState.showPassword" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
                  <circle cx="12" cy="12" r="3"></circle>
                </svg>
                <svg v-else width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path>
                  <line x1="1" y1="1" x2="23" y2="23"></line>
                </svg>
              </button>
            </div>
          </div>

          <div class="form-group" v-if="!isRegister">
            <label for="device_name">设备名称</label>
            <div class="input-wrapper">
              <input
                id="device_name"
                v-model="form.device_name"
                type="text"
                :placeholder="defaultDeviceName"
                autocomplete="off"
                @focus="onFieldFocus('device_name')"
                @blur="onFieldBlur"
                @input="onInput"
              />
            </div>
            <div class="form-hint">设备名将记录到登录设备列表，方便随时撤销。</div>
          </div>

          <button type="submit" class="btn-submit" :disabled="formState.loading">
            <span class="btn-text">{{ formState.loading ? '处理中...' : (isRegister ? '创建账号' : 'Log In') }}</span>
            <div class="btn-hover-content">
              <span>{{ isRegister ? '创建账号' : 'Log In' }}</span>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                <line x1="5" y1="12" x2="19" y2="12" />
                <polyline points="12 5 19 12 12 19" />
              </svg>
            </div>
          </button>
        </form>

        <div class="switch-link">
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
          <div class="auth-dialog__item-meta">{{ shortUA(device.user_agent) }} · 最近活跃 {{ device.last_active_at || '—' }}</div>
        </el-radio>
      </el-radio-group>
      <template #footer>
        <el-button @click="cancelDeviceReplacement">取消</el-button>
        <el-button type="primary" :loading="formState.loading" @click="confirmDeviceReplacement">
          替换并登录
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

import { getApiErrorMessage } from '../api/errors'
import AnimatedCharacters from '../components/AnimatedCharacters.vue'
import { isPendingLoginResponse, type AuthDevice, type AuthPendingLoginResponse } from '../api/auth'
import { useAuth } from '../composables/useAuth'

const auth = useAuth()
const route = useRoute()
const router = useRouter()

const charactersRef = ref<InstanceType<typeof AnimatedCharacters> | null>(null)

const isRegister = computed(() => route.name === 'register')

const defaultDeviceName = computed(() => {
  if (typeof navigator === 'undefined') return '当前浏览器'
  return `${navigator.platform || 'Web'} · ${(navigator.userAgent.split(' ').slice(-1)[0] || '')}`.trim()
})

const form = reactive({
  username: '',
  password: '',
  display_name: '',
  device_name: '',
})

const formState = reactive({
  isTyping: false,
  passwordFocused: false,
  showPassword: false,
  loginError: false,
  loading: false,
  errorText: '',
  fieldErrors: { username: false, password: false },
})

watch(() => route.name, () => {
  form.password = ''
  formState.errorText = ''
  formState.fieldErrors = { username: false, password: false }
  formState.loginError = false
})

function onFieldFocus(_field: string) {
  formState.isTyping = true
  formState.errorText = ''
}

function onFieldBlur() {
  formState.isTyping = false
}

/** 把 User Agent 精简为「浏览器 · OS」短格式 */
function shortUA(ua: string | null | undefined): string {
  if (!ua) return '未知客户端'
  let browser = ''
  if (ua.includes('Edg/')) browser = 'Edge ' + (ua.match(/Edg\/(\d+)/)?.[1] || '')
  else if (ua.includes('Chrome/')) browser = 'Chrome ' + (ua.match(/Chrome\/(\d+)/)?.[1] || '')
  else if (ua.includes('Firefox/')) browser = 'Firefox ' + (ua.match(/Firefox\/(\d+)/)?.[1] || '')
  else if (ua.includes('Safari/') && !ua.includes('Chrome')) browser = 'Safari'
  else browser = '浏览器'
  let os = ''
  if (ua.includes('Windows NT 10')) os = 'Win10'
  else if (ua.includes('Windows NT')) os = 'Win'
  else if (ua.includes('Mac OS X')) os = 'Mac'
  else if (ua.includes('Android')) os = 'Android'
  else if (ua.includes('iPhone') || ua.includes('iPad')) os = 'iOS'
  else if (ua.includes('Linux')) os = 'Linux'
  return [browser, os].filter(Boolean).join(' · ') || ua.slice(0, 30)
}

function onInput() {
  formState.isTyping = true
}

function onPasswordFocus() {
  formState.passwordFocused = true
  formState.isTyping = true
}

function onPasswordBlur() {
  formState.passwordFocused = false
  formState.isTyping = false
}

function togglePassword() {
  formState.showPassword = !formState.showPassword
}

function validate() {
  formState.fieldErrors = { username: false, password: false }
  formState.errorText = ''

  const username = form.username.trim()
  const pwd = form.password

  if (!username || username.length < 3) {
    formState.fieldErrors.username = true
    formState.errorText = '用户名至少 3 个字符'
    return false
  }

  if (!pwd || (isRegister.value && pwd.length < 8)) {
    formState.fieldErrors.password = true
    formState.errorText = isRegister.value ? '密码至少 8 位' : '请输入密码'
    return false
  }

  if (!isRegister.value && !pwd) {
    formState.fieldErrors.password = true
    formState.errorText = '请输入密码'
    return false
  }

  return true
}

async function onSubmit() {
  if (formState.loading) return
  if (!validate()) {
    charactersRef.value?.triggerError()
    return
  }

  formState.loading = true
  formState.loginError = false

  if (isRegister.value) {
    try {
      const response = await auth.register({
        username: form.username.trim(),
        password: form.password,
        display_name: form.display_name.trim() || undefined,
      })
      ElMessage.success(response.message || '注册成功，请登录')
      charactersRef.value?.triggerSuccess()
      await new Promise(r => setTimeout(r, 1500))
      await router.push({ name: 'login', query: route.query })
    } catch (error: unknown) {
      formState.errorText = getApiErrorMessage(error, '注册失败')
      formState.loginError = true
      charactersRef.value?.triggerError()
    } finally {
      formState.loading = false
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
      formState.loading = false
      return
    }
    ElMessage.success('登录成功')
    charactersRef.value?.triggerSuccess()
    await new Promise(r => setTimeout(r, 1500))
    await redirectAfterLogin()
  } catch (error: unknown) {
     formState.errorText = getApiErrorMessage(error, '登录失败')
    formState.loginError = true
    charactersRef.value?.triggerError()
  } finally {
    formState.loading = false
  }
}

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
     ElMessage.error(getApiErrorMessage(error, '设备替换失败'))
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

</script>

<style scoped>
.auth-page {
  display: grid;
  grid-template-columns: 1fr 1fr;
  height: 100vh;
}

.right-panel {
  display: flex;
  align-items: center;
  justify-content: center;
  background: #fff;
  padding: 40px;
}

.form-container {
  width: 100%;
  max-width: 400px;
}

.sparkle-icon {
  display: flex;
  justify-content: center;
  margin-bottom: 24px;
}

.sparkle-icon svg {
  width: 32px;
  height: 32px;
}

.form-header {
  text-align: center;
  margin-bottom: 36px;
}

.form-header h1 {
  font-size: 28px;
  font-weight: 700;
  color: #1a1a2e;
  letter-spacing: -0.5px;
  margin: 0 0 6px;
}

.form-header p {
  margin: 0;
  font-size: 14px;
  color: #888;
}

.error-msg {
  display: none;
  padding: 10px 14px;
  font-size: 13px;
  color: #dc2626;
  background: rgba(220, 38, 38, 0.08);
  border: 1px solid rgba(220, 38, 38, 0.2);
  border-radius: 10px;
  margin-bottom: 16px;
}

.form-group {
  margin-bottom: 20px;
}

.form-group label {
  display: block;
  font-size: 13px;
  font-weight: 500;
  color: #333;
  margin-bottom: 8px;
}

.form-group label.error-label {
  color: #dc2626;
}

.input-wrapper {
  position: relative;
}

.form-group input {
  width: 100%;
  height: 48px;
  border: none;
  border-bottom: 1.5px solid #e0e0e0;
  padding: 0 40px 0 0;
  font-size: 15px;
  font-family: inherit;
  color: #1a1a2e;
  background: transparent;
  outline: none;
  transition: border-color 0.3s;
  box-sizing: border-box;
}

.form-group input:focus {
  border-bottom-color: #5b21b6;
}

.form-group input.error {
  border-bottom-color: #dc2626;
}

.form-group input::placeholder {
  color: #ccc;
}

.form-group input[type="password"]:not(:placeholder-shown) {
  font-family: inherit;
  letter-spacing: 2px;
}

.form-group input[type="password"]::-ms-reveal,
.form-group input[type="password"]::-ms-clear {
  display: none;
}

.form-hint {
  margin-top: 6px;
  font-size: 11px;
  color: #999;
}

.toggle-password {
  position: absolute;
  right: 0;
  top: 50%;
  transform: translateY(-50%);
  background: none;
  border: none;
  cursor: pointer;
  color: #666;
  padding: 6px;
  transition: color 0.2s;
}

.toggle-password:hover {
  color: #333;
}

.btn-submit {
  position: relative;
  width: 100%;
  height: 50px;
  border-radius: 25px;
  border: 1.5px solid #1a1a2e;
  background: #1a1a2e;
  color: #fff;
  font-size: 15px;
  font-weight: 600;
  font-family: inherit;
  cursor: pointer;
  overflow: hidden;
  margin-top: 8px;
  transition: all 0.3s;
}

.btn-submit:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-submit .btn-text {
  display: inline-block;
  transition: all 0.3s;
}

.btn-submit .btn-hover-content {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  background: #5b21b6;
  color: #fff;
  opacity: 0;
  transition: all 0.3s;
  border-radius: 25px;
}

.btn-submit:hover:not(:disabled) .btn-text {
  transform: translateX(40px);
  opacity: 0;
}

.btn-submit:hover:not(:disabled) .btn-hover-content {
  opacity: 1;
}

.switch-link {
  text-align: center;
  font-size: 13px;
  color: #888;
  margin-top: 32px;
}

.switch-link a {
  color: #1a1a2e;
  font-weight: 600;
  text-decoration: none;
  margin-left: 4px;
}

.switch-link a:hover {
  text-decoration: underline;
}

.auth-dialog__desc {
  margin: 0 0 16px;
  color: var(--color-muted, #666);
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
  border: 1px solid var(--color-border, #e0e0e0);
  border-radius: 8px;
  align-items: flex-start;
}

.auth-dialog__item-name {
  font-weight: 600;
  color: var(--color-text, #1a1a2e);
  font-size: 13px;
}

.auth-dialog__item-meta {
  margin-top: 2px;
  color: #999;
  font-size: 11px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 100%;
}

@media (max-width: 900px) {
  .auth-page {
    grid-template-columns: 1fr;
  }
}
</style>
