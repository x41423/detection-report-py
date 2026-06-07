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
  OfficeBuilding,
  PriceTag,
  ShoppingCart,
  Stamp,
  TakeawayBox,
  Tickets,
  TrendCharts,
  User,
} from '@element-plus/icons-vue'

type AppNavigationGroupId = 'workspace' | 'commodity' | 'operations' | 'purchase' | 'processing' | 'quality' | 'pricing' | 'report' | 'extension' | 'account'
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
    id: 'commodity',
    title: '商品中心',
    kicker: '商品',
    description: '商品主数据、分类管理、报价规则等基础资料。',
    spotlight: '主数据',
    icon: CollectionTag,
    order: 2,
  },
  {
    id: 'operations',
    title: '日常业务',
    kicker: '日常',
    description: '当天持续维护的点货与库存链路。',
    spotlight: '持续录入',
    icon: TakeawayBox,
    order: 3,
  },
  {
    id: 'purchase',
    title: '采购入库',
    kicker: '采购',
    description: '供应商管理、采购入库与退货、结算对账。',
    spotlight: '采购链路',
    icon: ShoppingCart,
    order: 4,
  },
  {
    id: 'processing',
    title: '数据与检测',
    kicker: '处理',
    description: '资料处理、检测执行与结果整理。',
    spotlight: '集中处理',
    icon: Files,
    order: 5,
  },
  {
    id: 'quality',
    title: '质量管理',
    kicker: '质量',
    description: '检测报告归档与质量追溯。',
    spotlight: '质量追溯',
    icon: DocumentChecked,
    order: 6,
  },
  {
    id: 'pricing',
    title: '报价中心',
    kicker: '报价',
    description: '每周报价主流程与别名规则维护。',
    spotlight: '规则与汇总',
    icon: Tickets,
    order: 7,
  },
  {
    id: 'report',
    title: '数据报表',
    kicker: '报表',
    description: '销售驾驶舱、出入库汇总和货值成本分析。',
    spotlight: '经营分析',
    icon: DataAnalysis,
    order: 8,
  },
  {
    id: 'extension',
    title: '扩展功能',
    kicker: '扩展',
    description: '配送管理、营销工具、系统设置等远期规划功能。',
    spotlight: '规划中',
    icon: MagicStick,
    order: 9,
  },
  {
    id: 'account',
    title: '账号安全',
    kicker: '账号',
    description: '登录设备、账号安全和后续权限管理入口。',
    spotlight: '设备会话',
    icon: Monitor,
    order: 10,
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
    name: 'products',
    path: '/products',
    title: '商品库',
    shortTitle: '商品',
    description: '管理销售商品主数据，支持分类筛选、SKU规格配置。',
    accent: 'teal',
    group: 'commodity',
    order: 1,
    icon: ShoppingCart,
    component: () => import('../views/ProductManagement.vue'),
    requiredPermission: 'product:view',
    home: {
      eyebrow: '商品库',
      points: ['分类筛选', 'SKU管理', '报价关联'],
      tip: '先建立商品主数据，再用于采购和报价流程。',
    },
  },
  {
    name: 'categories',
    path: '/categories',
    title: '分类管理',
    shortTitle: '分类',
    description: '维护商品分类树，支持三级结构的新增、编辑、删除。',
    accent: 'teal',
    group: 'commodity',
    order: 2,
    icon: CollectionTag,
    component: () => import('../views/CategoryManagement.vue'),
    requiredPermission: 'category:view',
  },
  {
    name: 'quotations',
    path: '/quotations',
    title: '报价单管理',
    shortTitle: '报价单',
    description: '管理客户报价单，为不同客户群配置差异化商品定价。',
    accent: 'orange',
    group: 'commodity',
    order: 3,
    icon: PriceTag,
    component: () => import('../views/QuotationManagement.vue'),
    requiredPermission: 'quotation:view',
    home: {
      eyebrow: '报价单',
      points: ['客户定价', '商品关联', '批量调价'],
      tip: '为不同客户建立独立报价单，灵活配置商品价格。',
    },
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
    name: 'inventory-transactions',
    path: '/inventory-transactions',
    title: '库存流水明细',
    shortTitle: '流水',
    description: '按商品、日期、方向筛选库存变动记录，支持检测批次追溯。',
    accent: 'green',
    group: 'operations',
    order: 3,
    icon: TrendCharts,
    component: () => import('../views/InventoryTransactions.vue'),
    requiredPermission: 'inventory:view',
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
    requiredPermission: 'pesticide:view',
    home: {
      eyebrow: '智能检测',
      points: ['自动推荐', '遗漏补做', '一键报告'],
      tip: '基于当天点货和昨日库存自动匹配检测项。',
    },
  },
  // ── 质量管理 ──
  {
    name: 'inspection-reports',
    path: '/inspection-reports',
    title: '检测报告',
    shortTitle: '检测报告',
    description: '管理检测报告归档，支持上传、查询、关联商品。',
    accent: 'teal',
    group: 'quality',
    order: 1,
    icon: DocumentChecked,
    component: () => import('../views/InspectionReportManagement.vue'),
    requiredPermission: 'inspection_report:view',
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
  // ── Step 1-7 新增模块 ──
  {
    name: 'suppliers',
    path: '/suppliers',
    title: '供应商管理',
    shortTitle: '供应商',
    description: '维护供应商基础信息，支持新增、编辑、停用。',
    accent: 'teal',
    group: 'purchase',
    order: 1,
    icon: OfficeBuilding,
    component: () => import('../views/SupplierManagement.vue'),
    requiredPermission: 'supplier:view',
  },
  {
    name: 'supplier-detail',
    path: '/suppliers/:id',
    component: () => import('../views/SupplierDetail.vue'),
    meta: { hidden: true },
  },
  {
    name: 'purchase',
    path: '/purchase',
    title: '采购入库 & 退货',
    shortTitle: '采购',
    description: '管理采购入库与退货单据，确认后自动同步库存。',
    accent: 'teal',
    group: 'purchase',
    order: 2,
    icon: ShoppingCart,
    component: () => import('../views/PurchaseManagement.vue'),
    requiredPermission: 'inventory:view',
  },
  {
    name: 'orders',
    path: '/orders',
    title: '订单管理',
    shortTitle: '订单',
    description: '管理客户订单，确认出库后自动扣减库存。',
    accent: 'teal',
    group: 'purchase',
    order: 3,
    icon: Tickets,
    component: () => import('../views/OrderManagement.vue'),
    requiredPermission: 'inventory:view',
  },
  {
    name: 'settlement',
    path: '/settlement',
    title: '供应商结算',
    shortTitle: '结算',
    description: '管理供应商结算单，支持手动创建或根据已确认入库自动生成。',
    accent: 'teal',
    group: 'purchase',
    order: 4,
    icon: PriceTag,
    component: () => import('../views/SettlementManagement.vue'),
    requiredPermission: 'supplier:view',
  },
  {
    name: 'dashboard',
    path: '/dashboard',
    title: '数据驾驶舱',
    shortTitle: '驾驶舱',
    description: '跨模块经营概览：供应商、采购、订单、库存、结算一站汇总。',
    accent: 'sun',
    group: 'report',
    order: 1,
    icon: TrendCharts,
    component: () => import('../views/Dashboard.vue'),
    requiredPermission: 'inventory:view',
  },
  {
    name: 'product-sales',
    path: '/product-sales',
    title: '商品销售分析',
    shortTitle: '销售分析',
    description: '按商品和分类维度查看销售额排行与销售趋势。',
    accent: 'sun',
    group: 'report',
    order: 2,
    icon: TrendCharts,
    component: () => import('../views/ProductSalesAnalysis.vue'),
    requiredPermission: 'inventory:view',
  },
  {
    name: 'sales-report',
    path: '/sales-report',
    title: '销售总表',
    shortTitle: '销售总表',
    description: '按日期范围查看所有订单明细，支持导出 CSV。',
    accent: 'sun',
    group: 'report',
    order: 3,
    icon: Notebook,
    component: () => import('../views/SalesReport.vue'),
    requiredPermission: 'inventory:view',
  },
  {
    name: 'customer-analysis',
    path: '/customer-analysis',
    title: '客户购买分析',
    shortTitle: '客户分析',
    description: '按商户维度查看销售额排行、订单数和客单价。',
    accent: 'sun',
    group: 'report',
    order: 4,
    icon: TrendCharts,
    component: () => import('../views/CustomerAnalysis.vue'),
    requiredPermission: 'inventory:view',
  },
  {
    name: 'inventory-summary',
    path: '/inventory-summary',
    title: '出入库汇总',
    shortTitle: '出入库',
    description: '按日期范围查看入库/出库总量与来源分布。',
    accent: 'sun',
    group: 'report',
    order: 5,
    icon: DataAnalysis,
    component: () => import('../views/InventorySummary.vue'),
    requiredPermission: 'inventory:view',
  },
  {
    name: 'payables',
    path: '/payables',
    title: '应付总账',
    shortTitle: '应付',
    description: '按供应商查看应付金额、已付金额和余额。',
    accent: 'orange',
    group: 'report',
    order: 6,
    icon: PriceTag,
    component: () => import('../views/PayablesReport.vue'),
    requiredPermission: 'inventory:view',
  },
  {
    name: 'inactive-merchants',
    path: '/inactive-merchants',
    title: '未下单商户',
    shortTitle: '未下单',
    description: '监控近期未下单的商户，及时跟进。',
    accent: 'orange',
    group: 'report',
    order: 7,
    icon: CollectionTag,
    component: () => import('../views/InactiveMerchants.vue'),
    requiredPermission: 'inventory:view',
  },
  {
    name: 'price-lock',
    path: '/price-lock',
    title: '限时锁价',
    shortTitle: '锁价',
    description: '创建和管理限时锁价规则，锁定特定菜单下的商品价格。',
    accent: 'teal',
    group: 'extension',
    order: 1,
    icon: CollectionTag,
    component: () => import('../views/PriceLockManagement.vue'),
    requiredPermission: 'supplier:view',
  },
  {
    name: 'price-markup',
    path: '/price-markup',
    title: '上浮定价',
    shortTitle: '上浮',
    description: '设置全局或分类的商品价格上浮比例，灵活调控终端售价。',
    accent: 'amber',
    group: 'extension',
    order: 2,
    icon: TrendCharts,
    component: () => import('../views/PriceMarkupManagement.vue'),
    requiredPermission: 'supplier:view',
  },
  {
    name: 'agreement-price',
    path: '/agreement-price',
    title: '协议价管理',
    shortTitle: '协议价',
    description: '维护供应商协议价格，入库采购时按协议价自动填入。',
    accent: 'indigo',
    group: 'pricing',
    order: 3,
    icon: PriceTag,
    component: () => import('../views/AgreementPriceManagement.vue'),
    requiredPermission: 'supplier:view',
  },
  {
    name: 'loss-report',
    path: '/loss-report',
    title: '报损报溢',
    shortTitle: '损耗',
    description: '记录商品损耗与溢余，支持主子表明细录入。',
    accent: 'rose',
    group: 'quality',
    order: 4,
    icon: DocumentChecked,
    component: () => import('../views/LossReportManagement.vue'),
    requiredPermission: 'inventory:view',
  },
  {
    name: 'order-modification',
    path: '/order-modification',
    title: '改单审核',
    shortTitle: '改审',
    description: '订单修改审核工作流：提交→审核→通过/驳回。',
    accent: 'amber',
    group: 'operations',
    order: 10,
    icon: DocumentChecked,
    component: () => import('../views/OrderModificationManagement.vue'),
    requiredPermission: 'order:view',
  },
  {
    name: 'product-ledger',
    path: '/product-ledger',
    title: '商品台账',
    shortTitle: '台账',
    description: '按商品查看出入库流水，含出入汇总和明细下钻。',
    accent: 'slate',
    group: 'report',
    order: 10,
    icon: Notebook,
    component: () => import('../views/ProductLedger.vue'),
    requiredPermission: 'inventory:view',
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
  {
    path: '/orders/:id',
    name: 'order-detail',
    component: () => import('../views/OrderDetail.vue'),
    meta: {
      requiresAuth: true,
      title: '订单详情',
      description: '查看订单详情',
      requiredPermission: 'order:view',
    },
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'not-found',
    component: () => import('../views/NotFound.vue'),
    meta: {
      requiresAuth: true,
      title: '404 页面不存在',
    },
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
