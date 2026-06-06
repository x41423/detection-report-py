"""MySQL schema for the application database."""

from __future__ import annotations

from collections.abc import Callable

WEEKLY_QUOTE_DEFAULT_SUPPLIERS = (
    ("勾庄", 7, "highest", 1, 10),
    ("理想", 1, "average", 1, 20),
    ("刘慧", 1, "highest", 1, 30),
    ("酱菜", 7, "highest", 1, 40),
    ("豆制品", 7, "highest", 1, 50),
)
WEEKLY_QUOTE_DEFAULT_MEASURE_UNITS = (
    ("斤", 10),
    ("公斤", 20),
    ("千克", 30),
    ("克", 40),
    ("吨", 50),
    ("件", 60),
    ("箱", 70),
    ("袋", 80),
    ("瓶", 90),
    ("包", 100),
    ("桶", 110),
    ("盒", 120),
    ("条", 130),
    ("个", 140),
    ("把", 150),
    ("捆", 160),
    ("扎", 170),
    ("罐", 180),
    ("袋/件", 190),
    ("板", 200),
)


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
    CREATE TABLE IF NOT EXISTS WeeklyQuoteBatch (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        supplier VARCHAR(255) NOT NULL,
        quote_date VARCHAR(32) NOT NULL,
        source_label VARCHAR(255) DEFAULT '',
        source_path VARCHAR(1024) DEFAULT '',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE KEY uq_weekly_quote_batch (supplier, quote_date)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS WeeklyQuoteEntry (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        batch_id BIGINT NOT NULL,
        name VARCHAR(255) NOT NULL,
        unit VARCHAR(64) NOT NULL DEFAULT '斤',
        price DOUBLE NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        KEY idx_weekly_quote_entry_batch (batch_id),
        CONSTRAINT fk_weekly_quote_entry_batch FOREIGN KEY (batch_id) REFERENCES WeeklyQuoteBatch(id) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS WeeklyQuoteSupplierConfig (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        name VARCHAR(31) NOT NULL UNIQUE,
        weekly_batch_limit INT NOT NULL DEFAULT 7,
        summary_rule VARCHAR(16) NOT NULL DEFAULT 'highest',
        is_builtin TINYINT NOT NULL DEFAULT 0,
        sort_order INT NOT NULL DEFAULT 1000,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        CHECK (weekly_batch_limit >= 1 AND weekly_batch_limit <= 7),
        CHECK (summary_rule IN ('highest', 'average')),
        CHECK (is_builtin IN (0, 1)),
        KEY idx_weekly_quote_supplier_config_order (sort_order, id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS WeeklyQuoteMeasureUnitOption (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        name VARCHAR(64) NOT NULL UNIQUE,
        sort_order INT NOT NULL DEFAULT 1000,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        KEY idx_weekly_quote_measure_unit_order (sort_order, id)
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
    CREATE TABLE IF NOT EXISTS auth_refresh_token_grace (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        session_id BIGINT NOT NULL,
        refresh_token_hash VARCHAR(255) NOT NULL UNIQUE,
        valid_until VARCHAR(64) NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        KEY idx_auth_refresh_token_grace_session (session_id, valid_until),
        CONSTRAINT fk_auth_refresh_token_grace_session FOREIGN KEY (session_id) REFERENCES auth_sessions(id) ON DELETE CASCADE
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
    # ── P1.1 检测报告归档 ──
    """CREATE TABLE IF NOT EXISTS InspectionReport (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        report_no VARCHAR(50) NOT NULL UNIQUE,
        name VARCHAR(100) NOT NULL DEFAULT '',
        file_url VARCHAR(500) NOT NULL DEFAULT '',
        test_date VARCHAR(20) NOT NULL DEFAULT '',
        valid_from VARCHAR(20) NOT NULL DEFAULT '',
        valid_until VARCHAR(20) NOT NULL DEFAULT '',
        supplier_id BIGINT DEFAULT 0,
        submit_org VARCHAR(200) NOT NULL DEFAULT '',
        test_org VARCHAR(200) NOT NULL DEFAULT '',
        status VARCHAR(20) NOT NULL DEFAULT 'draft',
        source VARCHAR(20) NOT NULL DEFAULT 'manual',
        pesticide_task_id BIGINT DEFAULT 0,
        uploaded_by BIGINT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        KEY idx_ir_report_no (report_no),
        KEY idx_ir_supplier (supplier_id),
        KEY idx_ir_status (status),
        KEY idx_ir_test_date (test_date)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """CREATE TABLE IF NOT EXISTS InspectionReportProduct (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        report_id BIGINT NOT NULL,
        sku_id BIGINT NOT NULL DEFAULT 0,
        product_id BIGINT NOT NULL DEFAULT 0,
        batch VARCHAR(100) NOT NULL DEFAULT '',
        KEY idx_irp_report (report_id),
        KEY idx_irp_sku (sku_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """CREATE TABLE IF NOT EXISTS PriceMarkup (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        name VARCHAR(100) NOT NULL DEFAULT '',
        rate DOUBLE NOT NULL DEFAULT 0,
        scope VARCHAR(16) NOT NULL DEFAULT 'global',
        scope_id BIGINT DEFAULT 0,
        is_active TINYINT DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """CREATE TABLE IF NOT EXISTS SupplierProductPrice (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        supplier_id BIGINT NOT NULL,
        product_id BIGINT NOT NULL,
        price DOUBLE NOT NULL DEFAULT 0,
        unit_name VARCHAR(32) DEFAULT '',
        effective_from VARCHAR(16) DEFAULT '',
        effective_to VARCHAR(16) DEFAULT '',
        is_active TINYINT DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        KEY idx_spp_supplier (supplier_id),
        KEY idx_spp_product (product_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """CREATE TABLE IF NOT EXISTS LossReport (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        report_no VARCHAR(32) NOT NULL DEFAULT '',
        report_date VARCHAR(16) NOT NULL DEFAULT '',
        report_type VARCHAR(12) NOT NULL DEFAULT 'loss',
        warehouse_id BIGINT DEFAULT 0,
        notes TEXT,
        total_amount DOUBLE DEFAULT 0,
        status VARCHAR(12) DEFAULT 'draft',
        created_by VARCHAR(64) DEFAULT '',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """CREATE TABLE IF NOT EXISTS LossReportItem (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        report_id BIGINT NOT NULL,
        product_id BIGINT NOT NULL,
        quantity DOUBLE NOT NULL DEFAULT 0,
        unit_name VARCHAR(32) DEFAULT '',
        reason VARCHAR(255) DEFAULT '',
        unit_price DOUBLE DEFAULT 0,
        amount DOUBLE DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        KEY idx_lri_report (report_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """CREATE TABLE IF NOT EXISTS OrderModification (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        order_id BIGINT NOT NULL,
        order_no VARCHAR(32) NOT NULL DEFAULT '',
        modifier_name VARCHAR(64) DEFAULT '',
        summary TEXT,
        status VARCHAR(12) DEFAULT 'pending',
        reviewer_name VARCHAR(64) DEFAULT '',
        review_comment TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        KEY idx_om_order (order_id),
        KEY idx_om_status (status)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
]


def create_mysql_schema(cursor) -> None:
    for statement in MYSQL_SCHEMA_STATEMENTS:
        cursor.execute(statement)


def seed_weekly_quote_defaults(cursor) -> None:
    cursor.executemany(
        """
        INSERT INTO WeeklyQuoteSupplierConfig (
            name, weekly_batch_limit, summary_rule, is_builtin, sort_order
        )
        VALUES (?, ?, ?, ?, ?)
        ON DUPLICATE KEY UPDATE
            weekly_batch_limit = VALUES(weekly_batch_limit),
            summary_rule = VALUES(summary_rule),
            is_builtin = VALUES(is_builtin),
            sort_order = VALUES(sort_order)
        """,
        WEEKLY_QUOTE_DEFAULT_SUPPLIERS,
    )
    cursor.executemany(
        """
        INSERT INTO WeeklyQuoteMeasureUnitOption (name, sort_order)
        VALUES (?, ?)
        ON DUPLICATE KEY UPDATE
            sort_order = VALUES(sort_order)
        """,
        WEEKLY_QUOTE_DEFAULT_MEASURE_UNITS,
    )


def init_mysql_database(conn, seed_auth_defaults: Callable) -> None:
    cursor = conn.cursor()
    try:
        create_mysql_schema(cursor)
        seed_weekly_quote_defaults(cursor)
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
