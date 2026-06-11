from __future__ import annotations

import logging
import os
import sqlite3

from backend.auth.passwords import generate_password_salt, hash_password

DEFAULT_SUPER_ADMIN_USERNAME = "lina1124"
SUPER_ADMIN_ENV_USERNAME = "SEED_SUPER_ADMIN_USERNAME"
SUPER_ADMIN_ENV_PASSWORD = "SEED_SUPER_ADMIN_PASSWORD"
SUPER_ADMIN_ENV_FORCE_CHANGE = "SEED_SUPER_ADMIN_FORCE_CHANGE_PASSWORD"

DEFAULT_ROLES = [
    {
        "code": "super_admin",
        "name": "超级管理员",
        "description": "拥有系统全部权限，可管理所有功能和用户",
    },
    {
        "code": "admin",
        "name": "管理员",
        "description": "管理员——除不能编辑超级管理员、不能删除管理员账号、不能删除自己外，权限等同超级管理员",
    },
    {
        "code": "purchaser",
        "name": "采购员",
        "description": "管理供应商、采购入库与退货、查看应付结算",
    },
    {
        "code": "order_clerk",
        "name": "下单员",
        "description": "管理客户订单、改单审核、每日点货录入",
    },
    {
        "code": "warehouse",
        "name": "库管员",
        "description": "管理库存出入库、报损报溢、每日点货",
    },
    {
        "code": "inspector",
        "name": "检测员",
        "description": "执行农残检测、智能检测、管理检测报告归档",
    },
    {
        "code": "pricer",
        "name": "报价员",
        "description": "管理每周报价、别名库、协议价、锁价和上浮定价",
    },
    {
        "code": "qc",
        "name": "品控员",
        "description": "管理检测报告、报损报溢、数据迁移",
    },
    {
        "code": "finance",
        "name": "财务",
        "description": "管理供应商结算、查看经营报表和采购数据",
    },
    {
        "code": "staff",
        "name": "普通员工",
        "description": "每日点货录入、查看基础商品与库存数据",
    },
]

DEFAULT_PERMISSIONS = [
    ("dashboard:view", "查看工作台", "dashboard", "查看首页和基础工作台入口"),
    ("daily_check:view", "查看每日点货", "daily_check", "查看每日点货数据"),
    ("daily_check:create", "新增每日点货", "daily_check", "新增每日点货记录"),
    ("daily_check:update", "修改每日点货", "daily_check", "修改每日点货记录"),
    ("daily_check:delete", "删除每日点货", "daily_check", "删除每日点货记录"),
    ("daily_check:export", "导出每日点货", "daily_check", "导出每日点货数据"),
    ("inventory:view", "查看库存", "inventory", "查看库存余额和流水"),
    ("inventory:create", "新增库存记录", "inventory", "新增库存出入库或调整记录"),
    ("inventory:update", "修改库存记录", "inventory", "修改库存记录"),
    ("inventory:delete", "删除库存记录", "inventory", "删除库存记录"),
    ("inventory:export", "导出库存", "inventory", "导出库存数据"),
    ("transfer:view", "查看数据迁移", "transfer", "查看数据迁移模块"),
    ("transfer:execute", "执行数据迁移", "transfer", "执行数据迁移任务"),
    ("pesticide:view", "查看农残检测", "pesticide", "查看农残检测模块"),
    ("pesticide:execute", "执行农残检测", "pesticide", "执行农残检测任务"),
    ("weekly_quote:view", "查看每周报价", "weekly_quote", "查看每周报价模块"),
    ("weekly_quote:create", "新增每周报价", "weekly_quote", "新增每周报价数据"),
    ("weekly_quote:update", "修改每周报价", "weekly_quote", "修改每周报价数据"),
    ("weekly_quote:delete", "删除每周报价", "weekly_quote", "删除每周报价数据"),
    ("weekly_quote:approve", "审批每周报价", "weekly_quote", "审批每周报价流程"),
    ("weekly_quote:export", "导出每周报价", "weekly_quote", "导出每周报价文件"),
    ("weekly_quote:aliases", "维护报价别名", "weekly_quote", "维护报价别名库"),
    ("device:view", "查看设备", "device", "查看登录设备"),
    ("device:rename", "重命名设备", "device", "重命名自己的登录设备"),
    ("device:revoke", "撤销设备", "device", "撤销登录设备"),
    ("permission_request:view", "查看权限申请", "permission_request", "查看权限申请列表"),
    ("permission_request:create", "提交权限申请", "permission_request", "提交自己的权限申请"),
    ("permission_request:approve", "批准权限申请", "permission_request", "批准成员权限申请"),
    ("permission_request:reject", "拒绝权限申请", "permission_request", "拒绝成员权限申请"),
    ("user:view", "查看用户", "user", "查看用户列表和详情"),
    ("user:create", "新增用户", "user", "新增用户"),
    ("user:update", "修改用户", "user", "修改用户资料、角色和权限"),
    ("user:disable", "禁用用户", "user", "禁用用户账号"),
    ("user:delete", "删除用户", "user", "删除用户账号"),
    ("role:view", "查看角色", "role", "查看角色列表和权限"),
    ("role:create", "新增角色", "role", "新增角色"),
    ("role:update", "修改角色", "role", "修改角色资料和权限"),
    ("role:delete", "删除角色", "role", "删除非系统角色"),
    ("audit:view", "查看审计日志", "audit", "查看认证、设备、用户和权限变更日志"),
    ("supplier:view", "查看供应商", "supplier", "查看供应商列表和详情"),
    ("supplier:create", "新增供应商", "supplier", "新增供应商"),
    ("supplier:edit", "修改供应商", "supplier", "修改供应商信息"),
    ("supplier:update", "更新供应商", "supplier", "更新供应商信息"),
    ("supplier:delete", "删除供应商", "supplier", "停用供应商"),
    ("product:view", "查看商品库", "product", "查看商品列表和详情"),
    ("product:create", "新建商品", "product", "新建销售商品及其规格"),
    ("product:update", "编辑商品", "product", "修改商品信息和规格"),
    ("product:delete", "删除商品", "product", "下架/删除商品"),
    ("category:view", "查看分类", "product", "查看商品分类树"),
    ("quotation:view", "查看报价单", "quotation", "查看报价单列表和详情"),
    ("quotation:create", "新建报价单", "quotation", "新建报价单及其商品"),
    ("quotation:update", "编辑报价单", "quotation", "修改报价单信息和商品价格"),
    ("order:view", "查看订单", "order", "查看订单列表和详情"),
    ("order:create", "创建订单", "order", "新建订单"),
    ("order:update", "编辑订单", "order", "修改订单信息"),
    ("order:delete", "删除订单", "order", "删除订单"),
    ("order:copy", "复制订单", "order", "复制订单到新订单或补单"),
    ("inspection_report:view", "查看检测报告", "inspection_report", "查看检测报告归档列表和详情"),
    ("inspection_report:create", "新增检测报告", "inspection_report", "上传检测报告文件"),
    ("inspection_report:update", "修改检测报告", "inspection_report", "修改检测报告信息"),
    ("inspection_report:delete", "删除检测报告", "inspection_report", "删除检测报告"),
    ("config:view", "查看系统配置", "config", "查看系统配置"),
    ("config:update", "修改系统配置", "config", "修改系统配置"),
    ("transfer:execute", "执行数据迁移", "transfer", "执行数据迁移任务"),
    ("purchase:view", "查看采购入库", "purchase", "查看采购入库与退货"),
    ("purchase:create", "新增采购记录", "purchase", "新增采购入库或退货"),
    ("purchase:update", "修改采购记录", "purchase", "修改采购记录"),
    ("purchase:delete", "删除采购记录", "purchase", "删除采购记录"),
    ("loss_report:view", "查看报损报溢", "loss_report", "查看报损报溢记录"),
    ("loss_report:create", "新增报损报溢", "loss_report", "新增报损报溢记录"),
    ("loss_report:update", "修改报损报溢", "loss_report", "修改报损报溢记录"),
    ("loss_report:delete", "删除报损报溢", "loss_report", "删除报损报溢记录"),
    ("agreement_price:view", "查看协议价", "agreement_price", "查看协议价格"),
    ("agreement_price:create", "新增协议价", "agreement_price", "新增协议价格"),
    ("agreement_price:update", "修改协议价", "agreement_price", "修改协议价格"),
    ("agreement_price:delete", "删除协议价", "agreement_price", "删除协议价格"),
    ("price_lock:view", "查看锁价规则", "price_lock", "查看限时锁价规则"),
    ("price_lock:create", "新增锁价规则", "price_lock", "新增限时锁价规则"),
    ("price_lock:update", "修改锁价规则", "price_lock", "修改限时锁价规则"),
    ("price_lock:delete", "删除锁价规则", "price_lock", "删除限时锁价规则"),
    ("price_markup:view", "查看上浮定价", "price_markup", "查看上浮定价规则"),
    ("price_markup:create", "新增上浮定价", "price_markup", "新增上浮定价规则"),
    ("price_markup:update", "修改上浮定价", "price_markup", "修改上浮定价规则"),
    ("price_markup:delete", "删除上浮定价", "price_markup", "删除上浮定价规则"),
    ("settlement:view", "查看供应商结算", "settlement", "查看供应商结算单"),
    ("settlement:create", "新增结算单", "settlement", "新增供应商结算单"),
    ("settlement:update", "修改结算单", "settlement", "修改供应商结算单"),
    ("settlement:delete", "删除结算单", "settlement", "删除供应商结算单"),
    ("storage:view", "查看存储文件", "storage", "查看 MinIO 存储文件"),
    ("system:view", "查看中控台", "system", "查看系统运行状态、资源监控和日志"),
]

# ── 角色权限分配 ──
# 设计原则：
#   - 每个角色只获得自己职责范围内的操作权限 + 必要的查看权限
#   - super_admin 自动获得全部权限（不在此列表中重复）
#   - "查看"类权限尽可能开放，保证信息透明
#   - "操作"类权限严格限定，防止越权

ROLE_PERMISSION_CODES = {
    # ── 超级管理员（全部）──
    "super_admin": [permission[0] for permission in DEFAULT_PERMISSIONS],

    # ── 管理员：除三条红线外，权限等同超级管理员 ──
    "admin": [permission[0] for permission in DEFAULT_PERMISSIONS],

    # ── 采购员 ──
    "purchaser": [
        "dashboard:view",
        # 供应商管理（全权）
        "supplier:view", "supplier:create", "supplier:edit", "supplier:update", "supplier:delete",
        # 采购入库退货（全权）
        "purchase:view", "purchase:create", "purchase:update", "purchase:delete",
        # 结算查看
        "settlement:view",
        # 查看辅助
        "product:view",
        "inventory:view",
        "order:view",
        "daily_check:view",
        # 个人
        "device:view", "device:rename", "device:revoke",
        "permission_request:create",
    ],

    # ── 下单员 ──
    "order_clerk": [
        "dashboard:view",
        # 订单管理（全权）
        "order:view", "order:create", "order:update", "order:delete", "order:copy",
        # 每日点货
        "daily_check:view", "daily_check:create", "daily_check:update",
        # 查看辅助
        "product:view", "category:view",
        "quotation:view",
        "inventory:view",
        # 个人
        "device:view", "device:rename", "device:revoke",
        "permission_request:create",
    ],

    # ── 库管员 ──
    "warehouse": [
        "dashboard:view",
        # 库存（全权）
        "inventory:view", "inventory:create", "inventory:update", "inventory:delete", "inventory:export",
        # 报损报溢（全权）
        "loss_report:view", "loss_report:create", "loss_report:update", "loss_report:delete",
        # 每日点货
        "daily_check:view", "daily_check:create", "daily_check:update",
        # 查看辅助
        "purchase:view",
        "product:view",
        # 个人
        "device:view", "device:rename", "device:revoke",
        "permission_request:create",
    ],

    # ── 检测员 ──
    "inspector": [
        "dashboard:view",
        # 农残检测
        "pesticide:view", "pesticide:execute",
        # 检测报告
        "inspection_report:view", "inspection_report:create", "inspection_report:update",
        # 查看辅助
        "transfer:view",
        "daily_check:view",
        "inventory:view",
        "product:view",
        # 个人
        "device:view", "device:rename", "device:revoke",
        "permission_request:create",
    ],

    # ── 报价员 ──
    "pricer": [
        "dashboard:view",
        # 每周报价（全权）
        "weekly_quote:view", "weekly_quote:create", "weekly_quote:update",
        "weekly_quote:delete", "weekly_quote:approve", "weekly_quote:export",
        "weekly_quote:aliases",
        # 协议价（全权）
        "agreement_price:view", "agreement_price:create", "agreement_price:update", "agreement_price:delete",
        # 锁价（全权）
        "price_lock:view", "price_lock:create", "price_lock:update", "price_lock:delete",
        # 上浮定价（全权）
        "price_markup:view", "price_markup:create", "price_markup:update", "price_markup:delete",
        # 报价单
        "quotation:view", "quotation:create", "quotation:update",
        # 查看辅助
        "product:view", "category:view",
        "supplier:view",
        # 个人
        "device:view", "device:rename", "device:revoke",
        "permission_request:create",
    ],

    # ── 品控员 ──
    "qc": [
        "dashboard:view",
        # 检测报告（全权）
        "inspection_report:view", "inspection_report:create",
        "inspection_report:update", "inspection_report:delete",
        # 报损报溢（全权）
        "loss_report:view", "loss_report:create", "loss_report:update", "loss_report:delete",
        # 数据迁移
        "transfer:view", "transfer:execute",
        # 查看辅助
        "pesticide:view",
        "daily_check:view",
        "inventory:view",
        "product:view",
        # 个人
        "device:view", "device:rename", "device:revoke",
        "permission_request:create",
    ],

    # ── 财务 ──
    "finance": [
        "dashboard:view",
        # 结算管理（全权）
        "settlement:view", "settlement:create", "settlement:update", "settlement:delete",
        # 经营报表（使用 inventory:view 作为报表权限 — product_analysis 路由暂用此码）
        "inventory:view",
        # 查看辅助
        "order:view",
        "purchase:view",
        "supplier:view",
        "product:view",
        "daily_check:view",
        # 个人
        "device:view", "device:rename", "device:revoke",
        "permission_request:create",
    ],

    # ── 普通员工 ──
    "staff": [
        "dashboard:view",
        # 每日点货录入
        "daily_check:view", "daily_check:create",
        # 查看基础数据
        "product:view",
        "inventory:view",
        "order:view",
        # 个人
        "device:view", "device:rename", "device:revoke",
        "permission_request:create",
    ],
}


def seed_auth_defaults(cursor: sqlite3.Cursor) -> None:
    """Seed system roles, permissions, role bindings, and optional super admin."""
    _seed_roles(cursor)
    _seed_permissions(cursor)
    _seed_role_permissions(cursor)
    _seed_super_admin(cursor)


def _seed_roles(cursor: sqlite3.Cursor) -> None:
    for role in DEFAULT_ROLES:
        cursor.execute(
            """
            INSERT INTO auth_roles (code, name, description, is_system)
            VALUES (?, ?, ?, 1)
            ON CONFLICT(code) DO UPDATE SET
                name = excluded.name,
                description = excluded.description,
                is_system = 1,
                updated_at = CURRENT_TIMESTAMP
            """,
            (role["code"], role["name"], role["description"]),
        )


def _seed_permissions(cursor: sqlite3.Cursor) -> None:
    for code, name, module, description in DEFAULT_PERMISSIONS:
        cursor.execute(
            """
            INSERT INTO auth_permissions (code, name, module, description)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(code) DO UPDATE SET
                name = excluded.name,
                module = excluded.module,
                description = excluded.description,
                updated_at = CURRENT_TIMESTAMP
            """,
            (code, name, module, description),
        )


def _seed_role_permissions(cursor: sqlite3.Cursor) -> None:
    for role_code, permission_codes in ROLE_PERMISSION_CODES.items():
        cursor.execute("SELECT id FROM auth_roles WHERE code = ?", (role_code,))
        role = cursor.fetchone()
        if role is None:
            continue

        for permission_code in permission_codes:
            cursor.execute("SELECT id FROM auth_permissions WHERE code = ?", (permission_code,))
            permission = cursor.fetchone()
            if permission is None:
                continue
            cursor.execute(
                """
                INSERT OR IGNORE INTO auth_role_permissions (role_id, permission_id)
                VALUES (?, ?)
                """,
                (role["id"], permission["id"]),
            )


def _seed_super_admin(cursor: sqlite3.Cursor) -> None:
    initial_password = os.getenv(SUPER_ADMIN_ENV_PASSWORD, "").strip()
    if not initial_password:
        logging.warning(
            "%s is not set; skipping default super admin seed.",
            SUPER_ADMIN_ENV_PASSWORD,
        )
        return

    username = os.getenv(SUPER_ADMIN_ENV_USERNAME, DEFAULT_SUPER_ADMIN_USERNAME).strip() or DEFAULT_SUPER_ADMIN_USERNAME
    must_change_password = _env_flag(SUPER_ADMIN_ENV_FORCE_CHANGE, default=True)

    cursor.execute("SELECT id FROM auth_users WHERE username = ?", (username,))
    existing_user = cursor.fetchone()
    if existing_user is None:
        salt = generate_password_salt()
        cursor.execute(
            """
            INSERT INTO auth_users (
                username,
                display_name,
                password_hash,
                password_salt,
                is_active,
                is_super_admin,
                must_change_password,
                password_changed_at
            )
            VALUES (?, ?, ?, ?, 1, 1, ?, CURRENT_TIMESTAMP)
            """,
            (
                username,
                username,
                hash_password(initial_password, salt),
                salt,
                1 if must_change_password else 0,
            ),
        )
        user_id = cursor.lastrowid
    else:
        user_id = existing_user["id"]
        cursor.execute(
            """
            UPDATE auth_users
            SET is_active = 1,
                is_super_admin = 1,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (user_id,),
        )

    cursor.execute("SELECT id FROM auth_roles WHERE code = 'super_admin'")
    super_admin_role = cursor.fetchone()
    if super_admin_role is not None:
        cursor.execute(
            """
            INSERT OR IGNORE INTO auth_user_roles (user_id, role_id)
            VALUES (?, ?)
            """,
            (user_id, super_admin_role["id"]),
        )


def _env_flag(name: str, *, default: bool) -> bool:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    return raw_value.strip().lower() in {"1", "true", "yes", "on"}
