import type { Component } from 'vue'
import type { RouteRecordRaw } from 'vue-router'
import {
  CollectionTag,
  DataAnalysis,
  DocumentChecked,
  Files,
  HomeFilled,
  Key,
  MagicStick,
  Management,
  Monitor,
  Notebook,
  PriceTag,
  ShoppingCart,
  Stamp,
  TakeawayBox,
  Tickets,
  User,
} from '@element-plus/icons-vue'

type AppNavigationGroupId = 'workspace' | 'operations' | 'processing' | 'pricing' | 'account'
type LazyRouteComponent = () => Promise<unknown>

export interface AppNavigationGroup {
  id: AppNavigationGroupId
  title: string
  kicker: string
  description: string
  spotlight: string
  icon: Component
  order: number
}

export interface AppHomeCardMeta {
  eyebrow: string
  points: string[]
  tip: string
}

export interface AppNavigationItem {
  name: string
  path: string
  title: string
  shortTitle: string
  description: string
  accent: string
  group: AppNavigationGroupId
  order: number
  icon: Component
  component: LazyRouteComponent
  requiredPermission: string
  parentName?: string
  home?: AppHomeCardMeta
  hideForSuperAdmin?: boolean
}

export interface AppNavigationNode extends AppNavigationItem {
  children: AppNavigationItem[]
}

export interface AppNavigationSection extends AppNavigationGroup {
  items: AppNavigationNode[]
}

export const appNavigationGroups: AppNavigationGroup[] = [
  {
    id: 'workspace',
    title: '工作台',
    kicker: '总览',
    description: '总览入口和当前页面定位。',
    spotlight: '总览入口',
    icon: HomeFilled,
    order: 1,
  },
  {
    id: 'operations',
    title: '日常业务',
    kicker: '日常',
    description: '当天持续维护的点货与库存链路。',
    spotlight: '持续录入',
    icon: TakeawayBox,
    order: 2,
  },
  {
    id: 'processing',
    title: '数据与检测',
    kicker: '处理',
    description: '资料处理、检测执行与结果整理。',
    spotlight: '集中处理',
    icon: Files,
    order: 3,
  },
  {
    id: 'pricing',
    title: '报价中心',
    kicker: '报价',
    description: '每周报价主流程与别名规则维护。',
    spotlight: '规则与汇总',
    icon: Tickets,
    order: 4,
  },
  {
    id: 'account',
    title: '账号安全',
    kicker: '账号',
    description: '登录设备、账号安全和后续权限管理入口。',
    spotlight: '设备会话',
    icon: Monitor,
    order: 5,
  },
]

export const appNavigationItems: AppNavigationItem[] = [
  {
    name: 'home',
    path: '/',
    title: '工作台首页',
    shortTitle: '首页',
    description: '查看今日工作分组、建议流程和各模块入口。',
    accent: 'teal',
    group: 'workspace',
    order: 1,
    icon: HomeFilled,
    component: () => import('../views/Home.vue'),
    requiredPermission: 'dashboard:view',
  },
  {
    name: 'daily-intake',
    path: '/daily-intake',
    title: '每日点货',
    shortTitle: '点货',
    description: '按业务日期维护点货单，支持手动录入、语音录入、历史回看和自动累计。',
    accent: 'green',
    group: 'operations',
    order: 1,
    icon: ShoppingCart,
    component: () => import('../views/DailyIntake.vue'),
    requiredPermission: 'daily_check:view',
    home: {
      eyebrow: '每日点货',
      points: ['按天开单', '语音草稿', '自动累计'],
      tip: '适合全天持续追加采购与点货记录。',
    },
  },
  {
    name: 'inventory',
    path: '/inventory',
    title: '库存管理',
    shortTitle: '库存',
    description: '统一处理点货入库、商品出库、盘点修正、库存流水和低库存提示。',
    accent: 'green',
    group: 'operations',
    order: 2,
    icon: TakeawayBox,
    component: () => import('../views/Inventory.vue'),
    requiredPermission: 'inventory:view',
    home: {
      eyebrow: '库存管理',
      points: ['点货入库', '商品出库', '盘点修正'],
      tip: '适合跟随每日点货同步维护库存变化与异常项。',
    },
  },
  {
    name: 'transfer',
    path: '/transfer',
    title: '数据迁移',
    shortTitle: '迁移',
    description: '从大表抽取指定菜名并写入模板，适合批量整理历史供应链文档。',
    accent: 'sun',
    group: 'processing',
    order: 1,
    icon: DataAnalysis,
    component: () => import('../views/DataTransfer.vue'),
    requiredPermission: 'transfer:view',
    home: {
      eyebrow: '数据迁移',
      points: ['大表定位', '模板选择', '菜名核对'],
      tip: '先确认目标目录、模板与输出位置。',
    },
  },
  {
    name: 'pesticide',
    path: '/pesticide',
    title: '农残检测',
    shortTitle: '农残',
    description: '围绕目标文件、JSON 结果和执行动作组织检测流程。',
    accent: 'green',
    group: 'processing',
    order: 2,
    icon: DocumentChecked,
    component: () => import('../views/Pesticide.vue'),
    requiredPermission: 'pesticide:view',
    home: {
      eyebrow: '农残检测',
      points: ['路径锁定', 'JSON 生成', '结果执行'],
      tip: '重点核对日期、执行人和命中文件。',
    },
  },
  {
    name: 'smart-detection',
    path: '/smart-detection',
    title: '智能检测工作台',
    shortTitle: '智能检测',
    description: '根据点货与库存数据自动推荐检测清单，一键生成农残检测报告。',
    accent: 'sun',
    group: 'processing',
    order: 3,
    icon: MagicStick,
    component: () => import('../views/SmartDetection.vue'),
    requiredPermission: 'smart_detection:view',
    home: {
      eyebrow: '智能检测',
      points: ['自动推荐', '遗漏补做', '一键报告'],
      tip: '基于当天点货和昨日库存自动匹配检测项。',
    },
  },
  {
    name: 'weekly-price',
    path: '/weekly-price',
    title: '每周报价',
    shortTitle: '报价',
    description: '更新参考价、预检报价项，并导出一周新报价总结。',
    accent: 'orange',
    group: 'pricing',
    order: 1,
    icon: PriceTag,
    component: () => import('../views/WeeklyPrice.vue'),
    requiredPermission: 'weekly_quote:view',
    home: {
      eyebrow: '每周报价',
      points: ['参考价更新', '别名确认', '周报价汇总'],
      tip: '执行前先跑预检查，确认未匹配项。',
    },
  },
  {
    name: 'weekly-price-aliases',
    path: '/weekly-price-aliases',
    title: '报价别名库',
    shortTitle: '别名库',
    description: '维护待更新表名称到参考表名称的长期映射，供每周报价工作流复用。',
    accent: 'orange',
    group: 'pricing',
    order: 2,
    icon: CollectionTag,
    component: () => import('../views/WeeklyPriceAliases.vue'),
    requiredPermission: 'weekly_quote:aliases',
    parentName: 'weekly-price',
  },
  {
    name: 'devices',
    path: '/devices',
    title: '设备管理',
    shortTitle: '设备',
    description: '查看、重命名并撤销当前账号的登录设备。',
    accent: 'green',
    group: 'account',
    order: 1,
    icon: Monitor,
    component: () => import('../views/DeviceManagement.vue'),
    requiredPermission: 'device:view',
  },
  {
    name: 'permission-requests',
    path: '/permission-requests',
    title: '权限申请',
    shortTitle: '申请',
    description: '提交业务权限申请并查看自己的申请进度。',
    accent: 'sun',
    group: 'account',
    order: 2,
    icon: Key,
    component: () => import('../views/PermissionRequests.vue'),
    requiredPermission: 'permission_request:create',
    hideForSuperAdmin: true,
  },
  {
    name: 'permission-approvals',
    path: '/permission-approvals',
    title: '权限审批',
    shortTitle: '审批',
    description: '查看并审批成员提交的权限申请。',
    accent: 'orange',
    group: 'account',
    order: 3,
    icon: Stamp,
    component: () => import('../views/PermissionRequests.vue'),
    requiredPermission: 'permission_request:view',
  },
  {
    name: 'users',
    path: '/users',
    title: '用户管理',
    shortTitle: '用户',
    description: '创建成员账号、调整显示名称、绑定角色并处理账号启停。',
    accent: 'teal',
    group: 'account',
    order: 4,
    icon: User,
    component: () => import('../views/UserManagement.vue'),
    requiredPermission: 'user:view',
  },
  {
    name: 'roles',
    path: '/roles',
    title: '角色管理',
    shortTitle: '角色',
    description: '维护自定义角色和权限组合，配合用户管理完成授权。',
    accent: 'orange',
    group: 'account',
    order: 5,
    icon: Management,
    component: () => import('../views/RoleManagement.vue'),
    requiredPermission: 'role:view',
  },
  {
    name: 'audit-logs',
    path: '/audit-logs',
    title: '审计日志',
    shortTitle: '审计',
    description: '查看登录、设备、用户、角色和权限申请等关键操作记录。',
    accent: 'sun',
    group: 'account',
    order: 6,
    icon: Notebook,
    component: () => import('../views/AuditLogs.vue'),
    requiredPermission: 'audit:view',
  },
]

const authRoutes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'login',
    component: () => import('../views/AuthAccess.vue'),
    meta: {
      layout: 'auth',
      guestOnly: true,
      title: '登录',
      description: '账号登录入口',
    },
  },
  {
    path: '/register',
    name: 'register',
    component: () => import('../views/AuthAccess.vue'),
    meta: {
      layout: 'auth',
      guestOnly: true,
      title: '注册',
      description: '账号注册入口',
    },
  },
]

export const appRoutes: RouteRecordRaw[] = [
  ...authRoutes,
  ...appNavigationItems.map((item) => ({
    path: item.path,
    name: item.name,
    component: item.component,
    meta: {
      requiresAuth: true,
      title: item.title,
      description: item.description,
      accent: item.accent,
      group: item.group,
      parentName: item.parentName ?? null,
      requiredPermission: item.requiredPermission,
    },
  })),
  {
    path: '/403',
    name: 'forbidden',
    component: () => import('../views/Forbidden.vue'),
    meta: {
      requiresAuth: true,
      title: '权限不足',
      description: '当前账号没有访问该页面所需的权限',
    },
  },
  {
    path: '/inventory-lab',
    redirect: '/inventory',
  },
]

export function findNavigationItemByName(name: string | symbol | null | undefined) {
  if (!name) {
    return null
  }

  return appNavigationItems.find((item) => item.name === String(name)) ?? null
}

function buildSectionItems(groupId: AppNavigationGroupId): AppNavigationNode[] {
  const topLevelItems = appNavigationItems
    .filter((item) => item.group === groupId && !item.parentName)
    .sort((left, right) => left.order - right.order)

  return topLevelItems.map((item) => ({
    ...item,
    children: appNavigationItems
      .filter((candidate) => candidate.parentName === item.name)
      .sort((left, right) => left.order - right.order),
  }))
}

export function countNavigationEntries(section: Pick<AppNavigationSection, 'items'>) {
  return section.items.reduce((count, item) => count + 1 + item.children.length, 0)
}

export const sidebarNavigationSections: AppNavigationSection[] = appNavigationGroups
  .slice()
  .sort((left, right) => left.order - right.order)
  .map((group) => ({
    ...group,
    items: buildSectionItems(group.id),
  }))

export const homeNavigationSections: AppNavigationSection[] = sidebarNavigationSections
  .filter((section) => section.id !== 'workspace')
  .map((section) => ({
    ...section,
    items: section.items.filter((item) => Boolean(item.home)),
  }))
  .filter((section) => section.items.length > 0)

export interface NavigationFilterOptions {
  isSuperAdmin?: boolean
}

export function hasPermission(
  permissions: readonly string[],
  permissionCode: string,
  options: NavigationFilterOptions = {},
) {
  return options.isSuperAdmin === true || permissions.includes(permissionCode)
}

export function filterNavigationSectionsByPermissions(
  sections: AppNavigationSection[],
  permissions: readonly string[],
  options: NavigationFilterOptions = {},
): AppNavigationSection[] {
  const canShowItem = (item: AppNavigationItem) =>
    hasPermission(permissions, item.requiredPermission, options) &&
    !(options.isSuperAdmin === true && item.hideForSuperAdmin === true)

  return sections
    .map((section) => ({
      ...section,
      items: section.items
        .filter((item) => canShowItem(item))
        .map((item) => ({
          ...item,
          children: item.children.filter((child) => canShowItem(child)),
        })),
    }))
    .filter((section) => section.items.length > 0)
}
