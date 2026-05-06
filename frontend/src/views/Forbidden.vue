<template>
  <div class="page-shell forbidden-page">
    <section class="forbidden-card panel-card">
      <div class="forbidden-card__halo" />
      <div class="forbidden-card__status">403</div>
      <div class="forbidden-card__copy">
        <p class="forbidden-card__eyebrow">访问受限</p>
        <h1>当前账号没有访问权限</h1>
        <p>
          你已登录，但当前账号缺少进入该页面所需的权限。请联系管理员开通权限，或返回工作台查看当前可用入口。
        </p>
      </div>

      <div class="forbidden-card__facts">
        <div>
          <span>账号</span>
          <strong>{{ auth.currentUser.value?.display_name || auth.currentUser.value?.username || '未知账号' }}</strong>
        </div>
        <div>
          <span>缺少权限</span>
          <strong>{{ missingPermission }}</strong>
        </div>
      </div>

      <div class="forbidden-card__actions">
        <el-button type="primary" size="large" @click="router.push('/')">返回工作台</el-button>
        <el-button size="large" @click="router.back()">返回上一页</el-button>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { useAuth } from '../composables/useAuth'

const route = useRoute()
const router = useRouter()
const auth = useAuth()

const missingPermission = computed(() =>
  typeof route.query.permission === 'string' && route.query.permission ? route.query.permission : '未声明权限',
)
</script>

<style scoped>
.forbidden-page {
  min-height: calc(100vh - 48px);
  min-height: calc(100dvh - 48px);
  place-items: center;
}

.forbidden-card {
  position: relative;
  display: grid;
  gap: 20px;
  width: min(100%, 760px);
  padding: clamp(26px, 4vw, 44px);
  overflow: hidden;
  border-radius: var(--radius-lg);
  background: #ffffff;
}

.forbidden-card__halo {
  display: none;
}

.forbidden-card__status {
  position: relative;
  display: inline-grid;
  place-items: center;
  width: 64px;
  height: 64px;
  border-radius: var(--radius-md);
  background: #242424;
  color: #ffffff;
  font-family: var(--font-heading);
  font-size: 18px;
  font-weight: 600;
  letter-spacing: 0;
}

.forbidden-card__copy {
  position: relative;
  max-width: 620px;
}

.forbidden-card__eyebrow {
  margin: 0 0 10px;
  color: var(--color-muted-soft);
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.16em;
  text-transform: uppercase;
}

.forbidden-card h1 {
  margin: 0;
  color: var(--color-text);
  font-family: var(--font-heading);
  font-size: clamp(30px, 5vw, 46px);
  font-weight: 600;
  line-height: 1.12;
}

.forbidden-card p {
  margin: 14px 0 0;
  color: var(--color-muted);
  font-size: 15px;
  line-height: 1.8;
}

.forbidden-card__facts {
  position: relative;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.forbidden-card__facts div {
  display: grid;
  gap: 6px;
  padding: 14px;
  border-radius: var(--radius-md);
  background: #fafafa;
  box-shadow: inset 0 0 0 1px rgba(34, 42, 53, 0.08);
}

.forbidden-card__facts span {
  color: var(--color-muted-soft);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.forbidden-card__facts strong {
  color: var(--color-text);
  font-family: var(--font-body);
  font-weight: 600;
  font-size: 16px;
  overflow-wrap: anywhere;
}

.forbidden-card__actions {
  position: relative;
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

@media (max-width: 720px) {
  .forbidden-page {
    place-items: start stretch;
  }

  .forbidden-card {
    border-radius: var(--radius-lg);
  }

  .forbidden-card__facts {
    grid-template-columns: 1fr;
  }

  .forbidden-card__actions .el-button {
    width: 100%;
  }
}
</style>
