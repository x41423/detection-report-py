"""MySQL schema for the application database."""

from __future__ import annotations

from collections.abc import Callable


MYSQL_SCHEMA_STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS Veg (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        name VARCHAR(255) NOT NULL UNIQUE,
        category VARCHAR(64) DEFAULT 'other',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS Unit (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        name VARCHAR(64) NOT NULL UNIQUE,
        description VARCHAR(255),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS PriceHistory (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        vegetable_id BIGINT NOT NULL,
        unit_id BIGINT NOT NULL,
        price DOUBLE NOT NULL,
        date VARCHAR(32) NOT NULL,
        source VARCHAR(255),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        CONSTRAINT fk_price_history_veg FOREIGN KEY (vegetable_id) REFERENCES Veg(id) ON DELETE CASCADE,
        CONSTRAINT fk_price_history_unit FOREIGN KEY (unit_id) REFERENCES Unit(id) ON DELETE CASCADE,
        KEY idx_price_veg_unit_date (vegetable_id, unit_id, date DESC)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS WeeklyPriceEntry (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        week_start VARCHAR(32) NOT NULL,
        vegetable_id BIGINT NOT NULL,
        unit_id BIGINT NOT NULL,
        price DOUBLE NOT NULL,
        notes VARCHAR(1024),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        CONSTRAINT fk_weekly_price_veg FOREIGN KEY (vegetable_id) REFERENCES Veg(id) ON DELETE CASCADE,
        CONSTRAINT fk_weekly_price_unit FOREIGN KEY (unit_id) REFERENCES Unit(id) ON DELETE CASCADE,
        KEY idx_weekly_veg_unit_week (vegetable_id, unit_id, week_start DESC)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS DailyIntakeSheet (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        intake_date VARCHAR(32) NOT NULL UNIQUE,
        status VARCHAR(32) NOT NULL DEFAULT 'open',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE KEY idx_daily_intake_sheet_date (intake_date)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS DailyIntakeItem (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        sheet_id BIGINT NOT NULL,
        veg_id BIGINT,
        raw_name VARCHAR(255) NOT NULL,
        normalized_name VARCHAR(255) NOT NULL,
        category VARCHAR(64) NOT NULL,
        unit_id BIGINT NOT NULL,
        quantity DOUBLE NOT NULL,
        source VARCHAR(64) NOT NULL DEFAULT 'manual',
        transcript LONGTEXT,
        last_source VARCHAR(64) NOT NULL DEFAULT 'manual',
        last_transcript LONGTEXT,
        merge_count INT NOT NULL DEFAULT 1,
        last_confirmed_at VARCHAR(64),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        CONSTRAINT fk_daily_intake_item_sheet FOREIGN KEY (sheet_id) REFERENCES DailyIntakeSheet(id) ON DELETE CASCADE,
        CONSTRAINT fk_daily_intake_item_veg FOREIGN KEY (veg_id) REFERENCES Veg(id) ON DELETE SET NULL,
        CONSTRAINT fk_daily_intake_item_unit FOREIGN KEY (unit_id) REFERENCES Unit(id) ON DELETE CASCADE,
        UNIQUE KEY idx_daily_intake_item_merge_key (sheet_id, normalized_name, unit_id),
        KEY idx_daily_intake_item_sheet (sheet_id, updated_at DESC)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS InventoryTransaction (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        veg_id BIGINT,
        display_name VARCHAR(255) NOT NULL,
        normalized_name VARCHAR(255) NOT NULL,
        unit_id BIGINT NOT NULL,
        direction VARCHAR(32) NOT NULL,
        quantity_delta DOUBLE NOT NULL,
        business_date VARCHAR(32) NOT NULL,
        source_type VARCHAR(64) NOT NULL,
        source_ref_id BIGINT,
        note VARCHAR(2048) DEFAULT '',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        CONSTRAINT fk_inventory_transaction_veg FOREIGN KEY (veg_id) REFERENCES Veg(id) ON DELETE SET NULL,
        CONSTRAINT fk_inventory_transaction_unit FOREIGN KEY (unit_id) REFERENCES Unit(id) ON DELETE CASCADE,
        KEY idx_inventory_transaction_item (normalized_name, unit_id, updated_at DESC),
        KEY idx_inventory_transaction_business_date (business_date DESC, id DESC),
        UNIQUE KEY idx_inventory_transaction_source_ref (source_type, source_ref_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS Config (
        `key` VARCHAR(255) PRIMARY KEY,
        value LONGTEXT,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS MigrationVersion (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        version INT NOT NULL,
        description VARCHAR(1024),
        applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS schema_migrations (
        version INT PRIMARY KEY,
        name VARCHAR(255) NOT NULL,
        applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS auth_users (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        username VARCHAR(64) NOT NULL UNIQUE,
        display_name VARCHAR(255) NOT NULL DEFAULT '',
        password_hash VARCHAR(255) NOT NULL,
        password_salt VARCHAR(255) NOT NULL,
        is_active TINYINT NOT NULL DEFAULT 1,
        is_super_admin TINYINT NOT NULL DEFAULT 0,
        must_change_password TINYINT NOT NULL DEFAULT 0,
        failed_login_count INT NOT NULL DEFAULT 0,
        locked_until VARCHAR(64),
        last_failed_login_at VARCHAR(64),
        last_login_at VARCHAR(64),
        password_changed_at VARCHAR(64),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        CHECK (is_active IN (0, 1)),
        CHECK (is_super_admin IN (0, 1)),
        CHECK (must_change_password IN (0, 1))
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS auth_roles (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        code VARCHAR(64) NOT NULL UNIQUE,
        name VARCHAR(255) NOT NULL,
        description VARCHAR(1024) NOT NULL DEFAULT '',
        is_system TINYINT NOT NULL DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        CHECK (is_system IN (0, 1))
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS auth_permissions (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        code VARCHAR(128) NOT NULL UNIQUE,
        name VARCHAR(255) NOT NULL,
        module VARCHAR(64) NOT NULL,
        description VARCHAR(1024) NOT NULL DEFAULT '',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS auth_user_roles (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        user_id BIGINT NOT NULL,
        role_id BIGINT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE KEY uq_auth_user_roles_user_role (user_id, role_id),
        KEY idx_auth_user_roles_user (user_id),
        CONSTRAINT fk_auth_user_roles_user FOREIGN KEY (user_id) REFERENCES auth_users(id) ON DELETE CASCADE,
        CONSTRAINT fk_auth_user_roles_role FOREIGN KEY (role_id) REFERENCES auth_roles(id) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS auth_role_permissions (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        role_id BIGINT NOT NULL,
        permission_id BIGINT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE KEY uq_auth_role_permissions_role_permission (role_id, permission_id),
        KEY idx_auth_role_permissions_role (role_id),
        CONSTRAINT fk_auth_role_permissions_role FOREIGN KEY (role_id) REFERENCES auth_roles(id) ON DELETE CASCADE,
        CONSTRAINT fk_auth_role_permissions_permission FOREIGN KEY (permission_id) REFERENCES auth_permissions(id) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS auth_user_permission_overrides (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        user_id BIGINT NOT NULL,
        permission_id BIGINT NOT NULL,
        effect VARCHAR(16) NOT NULL,
        reason VARCHAR(2048) NOT NULL DEFAULT '',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE KEY uq_auth_user_permission_overrides_user_permission (user_id, permission_id),
        KEY idx_auth_permission_overrides_user (user_id),
        CHECK (effect IN ('allow', 'deny')),
        CONSTRAINT fk_auth_permission_overrides_user FOREIGN KEY (user_id) REFERENCES auth_users(id) ON DELETE CASCADE,
        CONSTRAINT fk_auth_permission_overrides_permission FOREIGN KEY (permission_id) REFERENCES auth_permissions(id) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS auth_permission_requests (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        user_id BIGINT NOT NULL,
        permission_id BIGINT,
        permission_code VARCHAR(128) NOT NULL,
        reason VARCHAR(2048) NOT NULL DEFAULT '',
        status VARCHAR(32) NOT NULL DEFAULT 'pending',
        reviewer_id BIGINT,
        review_comment VARCHAR(2048) NOT NULL DEFAULT '',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        reviewed_at VARCHAR(64),
        pending_permission_code VARCHAR(128)
            GENERATED ALWAYS AS (CASE WHEN status = 'pending' THEN permission_code ELSE NULL END) STORED,
        CHECK (status IN ('pending', 'approved', 'rejected', 'cancelled')),
        KEY idx_auth_permission_requests_user_status (user_id, status, created_at DESC),
        UNIQUE KEY idx_auth_permission_requests_pending (user_id, pending_permission_code),
        CONSTRAINT fk_auth_permission_requests_user FOREIGN KEY (user_id) REFERENCES auth_users(id) ON DELETE CASCADE,
        CONSTRAINT fk_auth_permission_requests_permission FOREIGN KEY (permission_id) REFERENCES auth_permissions(id) ON DELETE SET NULL,
        CONSTRAINT fk_auth_permission_requests_reviewer FOREIGN KEY (reviewer_id) REFERENCES auth_users(id) ON DELETE SET NULL
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS auth_devices (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        user_id BIGINT NOT NULL,
        device_name VARCHAR(255) NOT NULL DEFAULT '',
        device_fingerprint VARCHAR(255) NOT NULL,
        user_agent TEXT NOT NULL,
        browser VARCHAR(255) NOT NULL DEFAULT '',
        os VARCHAR(255) NOT NULL DEFAULT '',
        ip_address VARCHAR(64) NOT NULL DEFAULT '',
        first_login_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_active_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        is_revoked TINYINT NOT NULL DEFAULT 0,
        revoked_at VARCHAR(64),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE KEY uq_auth_devices_user_fingerprint (user_id, device_fingerprint),
        KEY idx_auth_devices_user_active (user_id, is_revoked, last_active_at DESC),
        CHECK (is_revoked IN (0, 1)),
        CONSTRAINT fk_auth_devices_user FOREIGN KEY (user_id) REFERENCES auth_users(id) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS auth_sessions (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        user_id BIGINT NOT NULL,
        device_id BIGINT NOT NULL,
        access_token_hash VARCHAR(255) NOT NULL UNIQUE,
        refresh_token_hash VARCHAR(255) UNIQUE,
        access_expires_at VARCHAR(64) NOT NULL,
        refresh_expires_at VARCHAR(64),
        revoked_at VARCHAR(64),
        revoke_reason VARCHAR(255) NOT NULL DEFAULT '',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_active_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        ip_address VARCHAR(64) NOT NULL DEFAULT '',
        user_agent TEXT NOT NULL,
        KEY idx_auth_sessions_user_device (user_id, device_id, revoked_at),
        KEY idx_auth_sessions_active_access (access_token_hash, revoked_at, access_expires_at),
        KEY idx_auth_sessions_active_refresh (refresh_token_hash, revoked_at, refresh_expires_at),
        CONSTRAINT fk_auth_sessions_user FOREIGN KEY (user_id) REFERENCES auth_users(id) ON DELETE CASCADE,
        CONSTRAINT fk_auth_sessions_device FOREIGN KEY (device_id) REFERENCES auth_devices(id) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS auth_pending_logins (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        user_id BIGINT NOT NULL,
        pending_token_hash VARCHAR(255) NOT NULL UNIQUE,
        ip_address VARCHAR(64) NOT NULL DEFAULT '',
        user_agent TEXT NOT NULL,
        device_name VARCHAR(255) NOT NULL DEFAULT '',
        expires_at VARCHAR(64) NOT NULL,
        used_at VARCHAR(64),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        KEY idx_auth_pending_logins_user_expires (user_id, expires_at),
        CONSTRAINT fk_auth_pending_logins_user FOREIGN KEY (user_id) REFERENCES auth_users(id) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS auth_audit_logs (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        actor_user_id BIGINT,
        target_user_id BIGINT,
        action VARCHAR(128) NOT NULL,
        module VARCHAR(64) NOT NULL DEFAULT 'auth',
        description VARCHAR(2048) NOT NULL DEFAULT '',
        ip_address VARCHAR(64) NOT NULL DEFAULT '',
        user_agent TEXT NOT NULL,
        result VARCHAR(64) NOT NULL DEFAULT 'success',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        KEY idx_auth_audit_actor_created (actor_user_id, created_at DESC),
        KEY idx_auth_audit_target_created (target_user_id, created_at DESC),
        KEY idx_auth_audit_module_action_created (module, action, created_at DESC),
        CONSTRAINT fk_auth_audit_actor FOREIGN KEY (actor_user_id) REFERENCES auth_users(id) ON DELETE SET NULL,
        CONSTRAINT fk_auth_audit_target FOREIGN KEY (target_user_id) REFERENCES auth_users(id) ON DELETE SET NULL
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
]


def create_mysql_schema(cursor) -> None:
    for statement in MYSQL_SCHEMA_STATEMENTS:
        cursor.execute(statement)


def init_mysql_database(conn, seed_auth_defaults: Callable) -> None:
    cursor = conn.cursor()
    try:
        create_mysql_schema(cursor)
        cursor.execute(
            """
            INSERT IGNORE INTO schema_migrations (version, name)
            VALUES (1, 'auth_core_schema')
            """
        )
        seed_auth_defaults(cursor)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
