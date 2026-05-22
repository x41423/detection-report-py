<template>
  <footer class="app-footer">
    <div class="app-footer__inner">
      <div class="app-footer__brand">
        <div class="app-footer__logo">滨</div>
        <div class="app-footer__title">滨鲜检测工具</div>
        <p class="app-footer__tagline">农药残留检测 · 每日点货 · 库存管理 · 每周报价</p>
      </div>

      <div class="app-footer__columns">
        <div v-for="col in columns" :key="col.heading" class="app-footer__column">
          <div class="app-footer__heading">{{ col.heading }}</div>
          <ul class="app-footer__links">
            <li v-for="link in col.links" :key="link.label">
              <router-link v-if="link.to" :to="link.to">{{ link.label }}</router-link>
              <span v-else>{{ link.label }}</span>
            </li>
          </ul>
        </div>
      </div>
    </div>

    <div class="app-footer__bottom">
      <span>滨鲜检测工具 &copy; {{ currentYear }}</span>
      <span class="app-footer__dot">·</span>
      <span>基于 Cal.com 设计系统</span>
    </div>
  </footer>
</template>

<script setup lang="ts">
const currentYear = new Date().getFullYear()

const columns = [
  {
    heading: '日常业务',
    links: [
      { label: '每日点货', to: '/daily-intake' },
      { label: '库存管理', to: '/inventory' },
    ],
  },
  {
    heading: '数据与检测',
    links: [
      { label: '数据迁移', to: '/transfer' },
      { label: '农残检测', to: '/pesticide' },
      { label: '智能检测', to: '/smart-detection' },
    ],
  },
  {
    heading: '报价中心',
    links: [
      { label: '每周报价', to: '/weekly-price' },
      { label: '别名库', to: '/weekly-price-aliases' },
    ],
  },
  {
    heading: '系统',
    links: [
      { label: '首页', to: '/' },
      { label: '设备管理', to: '/devices' },
      { label: '用户管理', to: '/users' },
    ],
  },
]
</script>

<style scoped>
.app-footer {
  background: #101010;
  color: #a1a1aa;
  margin-top: auto;
}

.app-footer__inner {
  max-width: 1200px;
  margin: 0 auto;
  padding: 64px 32px 48px;
  display: grid;
  grid-template-columns: 240px 1fr;
  gap: 48px;
}

.app-footer__brand {
  min-width: 0;
}

.app-footer__logo {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  background: #ffffff;
  color: #101010;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-family: var(--font-heading);
  font-size: 18px;
  font-weight: 700;
  margin-bottom: 12px;
}

.app-footer__title {
  font-family: var(--font-heading);
  font-size: 16px;
  font-weight: 600;
  color: #ffffff;
  margin-bottom: 6px;
}

.app-footer__tagline {
  margin: 0;
  font-size: 13px;
  line-height: 1.6;
  color: #a1a1aa;
}

.app-footer__columns {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 24px;
}

.app-footer__heading {
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: #71717a;
  margin-bottom: 14px;
}

.app-footer__links {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 8px;
}

.app-footer__links a,
.app-footer__links span {
  font-size: 13px;
  color: #a1a1aa;
  text-decoration: none;
  transition: color 0.18s ease;
}

.app-footer__links a:hover {
  color: #ffffff;
}

.app-footer__bottom {
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px 32px 24px;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
  font-size: 12px;
  color: #71717a;
  display: flex;
  gap: 6px;
}

.app-footer__dot {
  color: #3f3f46;
}

@media (max-width: 900px) {
  .app-footer__inner {
    grid-template-columns: 1fr;
    gap: 32px;
    padding: 48px 24px 36px;
  }

  .app-footer__columns {
    grid-template-columns: repeat(2, 1fr);
    gap: 24px;
  }

  .app-footer__bottom {
    padding: 16px 24px 20px;
  }
}

@media (max-width: 600px) {
  .app-footer__inner {
    padding: 40px 20px 28px;
  }

  .app-footer__columns {
    grid-template-columns: 1fr;
    gap: 20px;
  }

  .app-footer__bottom {
    padding: 14px 20px 18px;
    flex-direction: column;
    gap: 4px;
  }

  .app-footer__dot {
    display: none;
  }
}
</style>
