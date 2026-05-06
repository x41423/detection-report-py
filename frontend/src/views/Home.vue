<template>
  <div class="page-shell dashboard-page">
    <PageHero
      eyebrow="工作台总览"
      title="把高频业务收进一块可扩展的工作台"
      description="现在工作台已经按日常业务、数据与检测、报价中心重新归类。你可以先从左侧菜单定位模块，再在这里查看今天的工作节奏与重点入口。"
      tone="teal"
    >
      <template #actions>
        <el-button v-if="canOpenDailyIntake" type="primary" size="large" @click="$router.push('/daily-intake')">
          进入每日点货
        </el-button>
        <el-button v-if="canOpenInventory" size="large" @click="$router.push('/inventory')">
          打开库存管理
        </el-button>
        <el-tag v-if="!canOpenDailyIntake && !canOpenInventory" size="large" effect="plain">
          当前账号暂无常用业务入口
        </el-tag>
      </template>

      <template #aside>
        <div class="hero-metric-grid">
          <div class="hero-metric">
            <span class="hero-metric__label">主模块</span>
            <span class="hero-metric__value">{{ featuredModuleCount }}</span>
            <span class="hero-metric__note">点货、库存、迁移、农残、报价都已并入统一导航。</span>
          </div>
          <div class="hero-metric">
            <span class="hero-metric__label">业务分组</span>
            <span class="hero-metric__value">{{ homeSections.length }}</span>
            <span class="hero-metric__note">从“日常维护”到“报价规则”按工作节奏分区。</span>
          </div>
          <div class="hero-metric">
            <span class="hero-metric__label">导航策略</span>
            <span class="hero-metric__value">侧边栏</span>
            <span class="hero-metric__note">桌面端固定侧栏，移动端抽屉式菜单。</span>
          </div>
          <div class="hero-metric">
            <span class="hero-metric__label">界面状态</span>
            <span class="hero-metric__value">已收口</span>
            <span class="hero-metric__note">路由、侧边栏和首页入口共用同一份导航定义。</span>
          </div>
        </div>
      </template>
    </PageHero>

    <section class="dashboard-workspace">
      <el-card shadow="never" class="panel-card dashboard-sidebar">
        <div class="panel-heading">
          <div>
            <div class="panel-heading__eyebrow">开工前</div>
            <h2 class="panel-heading__title">开工前检查</h2>
            <p class="panel-heading__description">
              先确认日期、目标目录、输出位置和今天要处理的业务类型，这样能明显减少返工和误写文件。
            </p>
          </div>
        </div>

        <div class="dashboard-checks">
          <div v-for="item in checks" :key="item.title" class="dashboard-check">
            <div class="dashboard-check__icon">
              <el-icon><CircleCheckFilled /></el-icon>
            </div>
            <div>
              <div class="dashboard-check__title">{{ item.title }}</div>
              <div class="dashboard-check__description">{{ item.description }}</div>
            </div>
          </div>
        </div>

        <div class="dashboard-sidebar__footer">
          <div class="dashboard-sidebar__pulse" />
          <div>
            <div class="dashboard-sidebar__status">可以开始</div>
            <div class="dashboard-sidebar__note">
              左侧侧边栏负责稳定导航，首页负责给你今天的操作顺序和高频入口。
            </div>
          </div>
        </div>
      </el-card>

      <div class="dashboard-launchpad-sections">
        <section
          v-for="section in homeSections"
          :key="section.id"
          class="panel-card dashboard-launchpad-section"
        >
          <div class="dashboard-launchpad-section__header">
            <div class="dashboard-launchpad-section__lead">
              <div class="dashboard-launchpad-section__icon">
                <component :is="section.icon" />
              </div>

              <div class="dashboard-launchpad-section__copy">
                <div class="dashboard-launchpad-section__kicker">{{ section.kicker }}</div>
                <h2 class="dashboard-launchpad-section__title">{{ section.title }}</h2>
              </div>

              <div class="dashboard-launchpad-section__pills">
                <span class="dashboard-launchpad-section__pill">{{ countEntries(section) }} 个入口</span>
                <span class="dashboard-launchpad-section__pill dashboard-launchpad-section__pill--muted">
                  {{ section.spotlight }}
                </span>
              </div>
            </div>
            <p class="dashboard-launchpad-section__description">{{ section.description }}</p>
          </div>

          <div class="dashboard-launchpad">
            <el-card
              v-for="item in section.items"
              :key="item.path"
              shadow="never"
              class="panel-card launch-card"
              @click="$router.push(item.path)"
            >
              <div class="launch-card__mesh" :style="{ background: getCardGlow(item.accent) }" />
              <div class="launch-card__icon" :style="{ background: getCardIconBg(item.accent) }">
                <el-icon :size="28" :color="item.accent === 'orange' ? '#7c2d12' : '#0f172a'">
                  <component :is="item.icon" />
                </el-icon>
              </div>
              <div class="launch-card__eyebrow">{{ item.home?.eyebrow }}</div>
              <h2 class="launch-card__title">{{ item.title }}</h2>
              <p class="launch-card__description">{{ item.description }}</p>

              <div class="launch-card__tags">
                <span v-for="point in item.home?.points" :key="point" class="accent-tag muted-tag">
                  {{ point }}
                </span>
              </div>

              <div class="launch-card__footer">
                <span>{{ item.home?.tip }}</span>
                <span class="launch-card__link">
                  进入模块
                  <el-icon><ArrowRight /></el-icon>
                </span>
              </div>
            </el-card>
          </div>
        </section>

        <el-card v-if="homeSections.length === 0" shadow="never" class="panel-card dashboard-empty">
          <div class="dashboard-empty__mark">403</div>
          <h2>当前账号暂无可用业务入口</h2>
          <p>
            你已经登录，但当前账号只具备基础工作台权限。后续权限申请与审批上线后，可在系统内申请每日点货、库存、报价等业务模块权限。
          </p>
        </el-card>
      </div>
    </section>

    <section class="dashboard-foot">
      <el-card shadow="never" class="panel-card">
        <div class="panel-heading">
          <div>
            <div class="panel-heading__eyebrow">建议流程</div>
            <h2 class="panel-heading__title">今日建议流程</h2>
            <p class="panel-heading__description">
              每日点货适合先开单再全天持续追加，库存管理跟着当天业务同步维护，资料处理与检测适合集中执行，报价则放在最后收口。
            </p>
          </div>
        </div>

        <div class="dashboard-lanes">
          <div v-for="lane in lanes" :key="lane.step" class="dashboard-lane">
            <div class="dashboard-lane__step">{{ lane.step }}</div>
            <div class="dashboard-lane__title">{{ lane.title }}</div>
            <div class="dashboard-lane__description">{{ lane.description }}</div>
          </div>
        </div>
      </el-card>

      <el-card shadow="never" class="panel-card panel-card--emphasis">
        <div class="panel-heading">
          <div>
            <div class="panel-heading__eyebrow">准备清单</div>
            <h2 class="panel-heading__title">进入前要准备什么</h2>
          </div>
        </div>

        <div class="helper-list">
          <div v-for="tip in tips" :key="tip" class="helper-list__item">
            <div class="helper-list__dot" />
            <div class="helper-list__text">{{ tip }}</div>
          </div>
        </div>
      </el-card>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { ArrowRight, CircleCheckFilled } from '@element-plus/icons-vue'

import PageHero from '../components/PageHero.vue'
import { useAuth } from '../composables/useAuth'
import {
  countNavigationEntries,
  filterNavigationSectionsByPermissions,
  homeNavigationSections,
  type AppNavigationSection,
} from '../navigation/appNavigation'

const auth = useAuth()
const currentPermissions = computed(() => auth.currentUser.value?.permissions ?? [])
const homeSections = computed(() =>
  filterNavigationSectionsByPermissions(homeNavigationSections, currentPermissions.value, {
    isSuperAdmin: auth.isSuperAdmin.value,
  }),
)
const canOpenDailyIntake = computed(() => auth.hasPermission('daily_check:view'))
const canOpenInventory = computed(() => auth.hasPermission('inventory:view'))

const featuredModuleCount = computed(() =>
  homeSections.value.reduce((count, section) => count + section.items.length, 0),
)

const checks = [
  {
    title: '业务日期与目标目录已经确认',
    description: '避免把今天的记录写到错误日期，或把文件输出到不该使用的目录。',
  },
  {
    title: 'Excel 或 WPS 当前未占用目标工作簿',
    description: '防止覆盖写入或汇总导出时出现权限问题。',
  },
  {
    title: '今天优先处理的模块已经确定',
    description: '先明确是“持续录入型”还是“集中处理型”任务，会直接影响你的工作节奏。',
  },
  {
    title: '需要人工复核的名单已经知道',
    description: '尤其是语音草稿、未匹配报价项和可疑别名项。',
  },
]

const lanes = [
  {
    step: '01',
    title: '先开每日点货单',
    description: '如果今天会反复采购和补货，先进入每日点货，把当日单据建起来并随时追加。',
  },
  {
    step: '02',
    title: '同步维护库存管理',
    description: '点货新增、出库和盘点修正都集中收在库存页，适合当天边录边看当前库存与异常流水。',
  },
  {
    step: '03',
    title: '集中做数据迁移或农残检测',
    description: '等路径、模板和当天资料准备齐之后，再集中处理文档型工作流。',
  },
  {
    step: '04',
    title: '最后做每周报价',
    description: '报价更新和周汇总更依赖完整资料，放在一天后段集中核对更稳妥。',
  },
]

const tips = [
  '每日点货适合整天持续使用，建议固定在一个业务日期下维护同一张单。',
  '库存管理页已经正式并入主工作台，建议在当天业务处理过程中同步确认出入库和盘点修正。',
  '农残检测的关键不是录入本身，而是先锁定正确的大表、小表和日期。',
  '每周报价建议先预检查，再保存需要的别名映射，最后才做正式写回。',
]

function getCardGlow(accent: string) {
  switch (accent) {
    case 'orange':
      return 'radial-gradient(circle at top right, rgba(251, 146, 60, 0.24), rgba(255, 255, 255, 0))'
    case 'sun':
      return 'radial-gradient(circle at top right, rgba(250, 204, 21, 0.24), rgba(255, 255, 255, 0))'
    default:
      return 'radial-gradient(circle at top right, rgba(45, 212, 191, 0.22), rgba(255, 255, 255, 0))'
  }
}

function getCardIconBg(accent: string) {
  switch (accent) {
    case 'orange':
      return 'linear-gradient(135deg, rgba(251, 146, 60, 0.24), rgba(255, 255, 255, 0.18))'
    case 'sun':
      return 'linear-gradient(135deg, rgba(250, 204, 21, 0.24), rgba(255, 255, 255, 0.18))'
    default:
      return 'linear-gradient(135deg, rgba(45, 212, 191, 0.22), rgba(255, 255, 255, 0.18))'
  }
}

function countEntries(section: AppNavigationSection) {
  return countNavigationEntries(section)
}
</script>

<style scoped>
.dashboard-workspace {
  display: grid;
  grid-template-columns: 320px minmax(0, 1fr);
  gap: 18px;
}

.dashboard-sidebar {
  height: 100%;
}

.dashboard-checks {
  display: grid;
  gap: 12px;
}

.dashboard-check {
  display: grid;
  grid-template-columns: 40px minmax(0, 1fr);
  gap: 12px;
  padding: 14px 14px 16px;
  border-radius: 18px;
  border: 1px solid rgba(255, 255, 255, 0.48);
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.24), rgba(255, 255, 255, 0.12));
}

.dashboard-check__icon {
  display: grid;
  place-items: center;
  width: 40px;
  height: 40px;
  border-radius: 14px;
  background: rgba(16, 185, 129, 0.12);
  color: var(--color-success);
}

.dashboard-check__title {
  color: var(--color-text);
  font-weight: 700;
}

.dashboard-check__description {
  margin-top: 4px;
  color: var(--color-muted);
  font-size: 13px;
  line-height: 1.6;
}

.dashboard-sidebar__footer {
  display: grid;
  grid-template-columns: 14px minmax(0, 1fr);
  gap: 12px;
  align-items: start;
  margin-top: 18px;
  padding: 16px;
  border-radius: 18px;
  border: 1px solid rgba(255, 255, 255, 0.52);
  background: linear-gradient(135deg, rgba(16, 185, 129, 0.12), rgba(255, 255, 255, 0.18));
}

.dashboard-sidebar__pulse {
  width: 14px;
  height: 14px;
  margin-top: 4px;
  border-radius: 999px;
  background: var(--color-success);
  box-shadow: 0 0 0 8px rgba(16, 185, 129, 0.14);
}

.dashboard-sidebar__status {
  color: var(--color-text);
  font-family: var(--font-heading);
  font-size: 16px;
  font-weight: 700;
}

.dashboard-sidebar__note {
  margin-top: 4px;
  color: var(--color-muted);
  font-size: 13px;
  line-height: 1.6;
}

.dashboard-launchpad-sections {
  display: grid;
  gap: 18px;
}

.dashboard-empty {
  display: grid;
  justify-items: start;
  gap: 14px;
  padding: 28px;
  border-radius: 24px;
  background:
    radial-gradient(circle at top right, rgba(239, 68, 68, 0.12), transparent 32%),
    #ffffff;
}

.dashboard-empty__mark {
  display: grid;
  place-items: center;
  width: 58px;
  height: 58px;
  border-radius: 18px;
  background: #111111;
  color: #ffffff;
  font-family: var(--font-heading);
  font-weight: 800;
  letter-spacing: 0.08em;
}

.dashboard-empty h2 {
  margin: 0;
  color: var(--color-text);
  font-family: var(--font-heading);
  font-size: 24px;
}

.dashboard-empty p {
  max-width: 620px;
  margin: 0;
  color: var(--color-muted);
  line-height: 1.75;
}

.dashboard-launchpad-section {
  padding: 22px;
}

.dashboard-launchpad-section__header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 18px;
  margin-bottom: 18px;
}

.dashboard-launchpad-section__lead {
  display: flex;
  align-items: flex-start;
  gap: 14px;
  min-width: 0;
}

.dashboard-launchpad-section__icon {
  display: grid;
  place-items: center;
  width: 48px;
  height: 48px;
  border-radius: 16px;
  background: linear-gradient(135deg, rgba(45, 212, 191, 0.18), rgba(14, 165, 233, 0.12));
  color: var(--color-text);
  font-size: 22px;
}

.dashboard-launchpad-section__copy {
  display: grid;
  gap: 2px;
  min-width: 0;
}

.dashboard-launchpad-section__kicker {
  color: var(--color-muted-soft);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.18em;
  text-transform: uppercase;
}

.dashboard-launchpad-section__title {
  margin: 8px 0 0;
  color: var(--color-text);
  font-family: var(--font-heading);
  font-size: 24px;
  font-weight: 700;
  line-height: 1.08;
}

.dashboard-launchpad-section__description {
  max-width: 360px;
  margin: 0;
  color: var(--color-muted);
  font-size: 13px;
  line-height: 1.65;
}

.dashboard-launchpad-section__pills {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-left: 8px;
}

.dashboard-launchpad-section__pill {
  display: inline-flex;
  align-items: center;
  min-height: 28px;
  padding: 0 10px;
  border-radius: 999px;
  background: rgba(14, 165, 233, 0.12);
  color: var(--color-text);
  font-size: 11px;
  font-weight: 700;
}

.dashboard-launchpad-section__pill--muted {
  background: rgba(71, 85, 105, 0.1);
  color: var(--color-muted);
}

.dashboard-launchpad {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 18px;
}

.launch-card {
  position: relative;
  min-height: 246px;
  cursor: pointer;
  transition:
    transform 0.3s ease,
    box-shadow 0.3s ease,
    border-color 0.3s ease;
}

.launch-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 22px 42px rgba(15, 23, 42, 0.12);
}

.launch-card :deep(.el-card__body) {
  position: relative;
  display: grid;
  gap: 12px;
  min-height: 246px;
}

.launch-card__mesh {
  position: absolute;
  inset: 0;
  opacity: 0.9;
  pointer-events: none;
}

.launch-card__icon,
.launch-card__eyebrow,
.launch-card__title,
.launch-card__description,
.launch-card__tags,
.launch-card__footer {
  position: relative;
  z-index: 1;
}

.launch-card__icon {
  display: grid;
  place-items: center;
  width: 58px;
  height: 58px;
  border-radius: 18px;
  border: 1px solid rgba(255, 255, 255, 0.54);
}

.launch-card__eyebrow {
  color: var(--color-muted-soft);
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.18em;
  text-transform: uppercase;
}

.launch-card__title {
  margin: 0;
  color: var(--color-text);
  font-family: var(--font-heading);
  font-size: 26px;
  font-weight: 700;
  line-height: 1.08;
}

.launch-card__description {
  margin: 0;
  color: var(--color-muted);
  line-height: 1.7;
}

.launch-card__tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.launch-card__footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  margin-top: auto;
  color: var(--color-muted);
  font-size: 13px;
  line-height: 1.5;
}

.launch-card__link {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: var(--color-text);
  font-family: var(--font-heading);
  font-weight: 700;
}

.dashboard-foot {
  display: grid;
  grid-template-columns: minmax(0, 1.15fr) minmax(0, 0.85fr);
  gap: 18px;
}

.dashboard-lanes {
  display: grid;
  gap: 12px;
}

.dashboard-lane {
  padding: 16px 18px;
  border-radius: 18px;
  border: 1px solid rgba(255, 255, 255, 0.48);
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.24), rgba(255, 255, 255, 0.12));
}

.dashboard-lane__step {
  color: var(--color-muted-soft);
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.18em;
  text-transform: uppercase;
}

.dashboard-lane__title {
  margin-top: 8px;
  color: var(--color-text);
  font-family: var(--font-heading);
  font-size: 18px;
  font-weight: 700;
}

.dashboard-lane__description {
  margin-top: 8px;
  color: var(--color-muted);
  font-size: 14px;
  line-height: 1.65;
}

@media (max-width: 1240px) {
  .dashboard-workspace,
  .dashboard-foot,
  .dashboard-launchpad {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 1024px) {
  .dashboard-workspace {
    gap: 16px;
  }

  .launch-card {
    min-height: 220px;
  }

  .dashboard-launchpad-section__header {
    flex-direction: column;
  }

  .dashboard-launchpad-section__lead {
    flex-wrap: wrap;
  }
}

@media (max-width: 768px) {
  .dashboard-launchpad,
  .dashboard-foot {
    grid-template-columns: 1fr;
  }

  .dashboard-launchpad-section {
    padding: 18px;
  }

  .dashboard-launchpad-section__lead {
    flex-direction: column;
    align-items: flex-start;
  }

  .dashboard-launchpad-section__pills {
    margin-left: 0;
  }

  .dashboard-launchpad-section__description {
    max-width: none;
  }

  .launch-card__title {
    font-size: 22px;
  }

  .launch-card__footer {
    flex-direction: column;
    align-items: flex-start;
  }
}

@media (max-width: 430px) {
  .dashboard-check,
  .dashboard-sidebar__footer,
  .dashboard-lane {
    padding: 14px;
    border-radius: 16px;
  }

  .dashboard-launchpad-section {
    padding: 16px;
  }

  .dashboard-launchpad-section__icon,
  .launch-card__icon {
    width: 44px;
    height: 44px;
    border-radius: 14px;
  }
}
</style>
