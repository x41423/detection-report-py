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
        "description": "拥有系统全部权限的内置角色",
    },
    {
        "code": "admin",
        "name": "管理员",
        "description": "管理普通用户、设备和权限申请",
    },
    {
        "code": "member",
        "name": "成员",
        "description": "默认注册角色，可查看基础入口并申请更多权限",
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
    ("role:view", "查看角色", "role", "查看角色列表和权限"),
    ("role:create", "新增角色", "role", "新增角色"),
    ("role:update", "修改角色", "role", "修改角色资料和权限"),
    ("role:delete", "删除角色", "role", "删除非系统角色"),
    ("audit:view", "查看审计日志", "audit", "查看认证、设备、用户和权限变更日志"),
]

ROLE_PERMISSION_CODES = {
    "super_admin": [permission[0] for permission in DEFAULT_PERMISSIONS],
    "admin": [
        "dashboard:view",
        "device:view",
        "device:rename",
        "device:revoke",
        "permission_request:view",
        "permission_request:approve",
        "permission_request:reject",
        "user:view",
        "user:update",
        "user:disable",
        "role:view",
        "audit:view",
    ],
    "member": [
        "dashboard:view",
        "device:view",
        "device:rename",
        "device:revoke",
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
