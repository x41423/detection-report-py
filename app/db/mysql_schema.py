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
    CREATE TABLE IF NOT EXISTS Category (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        name TEXT,
        parent_id BIGINT,
        level BIGINT DEFAULT 1,
        sort_order BIGINT DEFAULT 0,
        is_active BIGINT DEFAULT 1,
        KEY idx_category_parent (parent_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS Config (
        `key` TEXT,
        value TEXT,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS Coupon (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        code TEXT,
        name TEXT,
        coupon_type TEXT,
        discount_value DOUBLE DEFAULT 0,
        min_order_amount DOUBLE DEFAULT 0,
        total_quantity BIGINT DEFAULT 0,
        used_quantity BIGINT DEFAULT 0,
        start_time TEXT,
        end_time TEXT,
        status TEXT,
        operator TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE KEY sqlite_autoindex_Coupon_1 (code(200))
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS DailyIntakeItem (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        sheet_id BIGINT,
        veg_id BIGINT,
        raw_name TEXT,
        normalized_name TEXT,
        category TEXT,
        unit_id BIGINT,
        quantity DOUBLE,
        source TEXT,
        transcript TEXT,
        last_source TEXT,
        last_transcript TEXT,
        merge_count BIGINT DEFAULT 1,
        last_confirmed_at TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        KEY idx_daily_intake_item_sheet (sheet_id, updated_at),
        UNIQUE KEY idx_daily_intake_item_merge_key (sheet_id, normalized_name, unit_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS DailyIntakeSheet (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        intake_date TEXT,
        status TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE KEY idx_daily_intake_sheet_date (intake_date),
        UNIQUE KEY sqlite_autoindex_DailyIntakeSheet_1 (intake_date)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS DeliveryRoute (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        code TEXT,
        name TEXT,
        driver_id BIGINT,
        status TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE KEY sqlite_autoindex_DeliveryRoute_1 (code(200))
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS DeliveryTask (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        route_id BIGINT,
        order_id BIGINT,
        delivery_date TEXT,
        delivery_status TEXT,
        driver_name TEXT,
        operator TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS FreightTemplate (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        name TEXT,
        base_freight DOUBLE DEFAULT 0,
        free_threshold DOUBLE DEFAULT 0,
        status TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS InspectionReport (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        report_no TEXT,
        name TEXT,
        file_url TEXT,
        test_date TEXT,
        valid_from TEXT,
        valid_until TEXT,
        supplier_id BIGINT DEFAULT 0,
        submit_org TEXT,
        test_org TEXT,
        status TEXT,
        source TEXT,
        pesticide_task_id BIGINT DEFAULT 0,
        uploaded_by BIGINT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        KEY idx_ir_test_date (test_date),
        KEY idx_ir_status (status),
        KEY idx_ir_merchant (supplier_id),
        KEY idx_ir_report_no (report_no),
        UNIQUE KEY sqlite_autoindex_InspectionReport_1 (report_no(200))
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS InspectionReportProduct (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        report_id BIGINT,
        sku_id BIGINT DEFAULT 0,
        product_id BIGINT DEFAULT 0,
        batch TEXT,
        KEY idx_irp_sku (sku_id),
        KEY idx_irp_report (report_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS InventoryTransaction (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        veg_id BIGINT,
        display_name TEXT,
        normalized_name TEXT,
        unit_id BIGINT,
        direction TEXT,
        quantity_delta DOUBLE,
        business_date TEXT,
        source_type TEXT,
        source_ref_id BIGINT,
        note TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE KEY idx_inventory_transaction_source_ref (source_type, source_ref_id),
        KEY idx_inventory_transaction_business_date (business_date, id),
        KEY idx_inventory_transaction_item (normalized_name, unit_id, updated_at)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS LossReport (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        report_no TEXT,
        report_date TEXT,
        report_type TEXT,
        warehouse_id BIGINT DEFAULT 0,
        notes TEXT,
        total_amount DOUBLE DEFAULT 0,
        status TEXT,
        created_by TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE KEY sqlite_autoindex_LossReport_1 (report_no(200))
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS LossReportItem (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        report_id BIGINT,
        product_id BIGINT,
        quantity DOUBLE DEFAULT 0,
        unit_name TEXT,
        reason TEXT,
        unit_price DOUBLE DEFAULT 0,
        amount DOUBLE DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        KEY idx_lri_report (report_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS MigrationVersion (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        version BIGINT,
        description TEXT,
        applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS OperationTimeConfig (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        day_type TEXT,
        order_start_time TEXT,
        order_end_time TEXT,
        delivery_time_range TEXT,
        status TEXT,
        operator TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS OrderAfterSale (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        order_id BIGINT,
        product_id TEXT,
        product_name TEXT,
        after_sale_type TEXT,
        return_quantity DOUBLE DEFAULT 0,
        return_amount DOUBLE DEFAULT 0,
        accounting_quantity DOUBLE DEFAULT 0,
        total_abnormal DOUBLE DEFAULT 0,
        total_return DOUBLE DEFAULT 0,
        status TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS OrderItem (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        order_id BIGINT,
        product_id TEXT,
        product_name TEXT,
        category TEXT,
        unit TEXT,
        quantity DOUBLE DEFAULT 0,
        unit_price DOUBLE DEFAULT 0,
        amount DOUBLE DEFAULT 0,
        original_price DOUBLE DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        KEY idx_order_item_order (order_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS OrderModification (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        order_id BIGINT,
        order_no TEXT,
        modifier_name TEXT,
        summary TEXT,
        status TEXT,
        reviewer_name TEXT,
        review_comment TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        KEY idx_om_status (status),
        KEY idx_om_order (order_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS OrderRecord (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        order_no TEXT,
        merchant_name TEXT,
        merchant_id TEXT,
        order_date TEXT,
        delivery_method TEXT,
        order_type TEXT,
        original_amount DOUBLE DEFAULT 0,
        order_amount DOUBLE DEFAULT 0,
        outbound_amount DOUBLE DEFAULT 0,
        sales_amount_excl_freight DOUBLE DEFAULT 0,
        freight DOUBLE DEFAULT 0,
        sales_amount_incl_freight DOUBLE DEFAULT 0,
        discount_amount DOUBLE DEFAULT 0,
        abnormal_amount DOUBLE DEFAULT 0,
        refund_amount DOUBLE DEFAULT 0,
        actual_refund DOUBLE DEFAULT 0,
        order_status TEXT,
        payment_status TEXT,
        loading_status TEXT,
        print_status TEXT,
        outbound_status TEXT,
        driver_name TEXT,
        order_source TEXT,
        remark TEXT,
        operator TEXT,
        print_time TEXT,
        last_operate_time TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        receive_start_date TEXT,
        receive_end_date TEXT,
        receive_start_time TEXT,
        receive_end_time TEXT,
        operation_time TEXT,
        receiver TEXT,
        delivery_address TEXT,
        sign_method TEXT,
        related_outbound_no TEXT,
        third_party_order_no TEXT,
        custom_field_1 TEXT,
        custom_field_2 TEXT,
        custom_field_3 TEXT,
        merchant_tag TEXT,
        sorting_status TEXT,
        inspection_status TEXT,
        cabinet_status TEXT,
        route_name TEXT,
        pickup_point TEXT,
        total_order_quantity DOUBLE DEFAULT 0,
        accounting_quantity_sale DOUBLE DEFAULT 0,
        accounting_quantity_base DOUBLE DEFAULT 0,
        product_category_count BIGINT DEFAULT 0,
        merchant_custom_code TEXT,
        after_sale_amount DOUBLE DEFAULT 0,
        should_refund_amount DOUBLE DEFAULT 0,
        edit_status TEXT,
        vehicle_status TEXT,
        batch_status TEXT,
        batch_merchant_name TEXT,
        main_sorting_category TEXT,
        main_sorting_category_count BIGINT DEFAULT 0,
        KEY idx_order_record_status (order_status),
        KEY idx_order_record_merchant (merchant_name),
        KEY idx_order_record_date (order_date),
        UNIQUE KEY sqlite_autoindex_OrderRecord_1 (order_no)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS PointsRecord (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        merchant_name TEXT,
        merchant_id TEXT,
        points_change BIGINT DEFAULT 0,
        change_type TEXT,
        description TEXT,
        operator TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS PriceHistory (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        vegetable_id BIGINT,
        unit_id BIGINT,
        price DOUBLE,
        date TEXT,
        source TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        KEY idx_price_veg_unit_date (vegetable_id, unit_id, date)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS PriceLockRule (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        rule_code TEXT,
        rule_name TEXT,
        salemenu_id TEXT,
        salemenu_name TEXT,
        target_count BIGINT DEFAULT 0,
        category_count BIGINT DEFAULT 0,
        start_time TEXT,
        end_time TEXT,
        status TEXT,
        operator TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE KEY sqlite_autoindex_PriceLockRule_1 (rule_code)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS PriceLockRuleItem (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        rule_id BIGINT,
        veg_name TEXT,
        locked_price DOUBLE DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS PriceMarkup (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        name TEXT,
        rate DOUBLE DEFAULT 0,
        scope TEXT,
        scope_id BIGINT DEFAULT 0,
        is_active BIGINT DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS ProcessingPlan (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        plan_code TEXT,
        plan_date TEXT,
        status TEXT,
        operator TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE KEY sqlite_autoindex_ProcessingPlan_1 (plan_code)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS Product (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        code TEXT,
        name TEXT,
        alias TEXT,
        category_id BIGINT,
        product_type TEXT,
        custom_code TEXT,
        delivery_method TEXT,
        purchase_type TEXT,
        base_unit TEXT,
        image_url TEXT,
        shelf_life_days BIGINT DEFAULT 0,
        purchase_mode TEXT,
        default_supplier_id BIGINT,
        description TEXT,
        tax_category_code TEXT,
        tax_rate DOUBLE DEFAULT 0,
        custom_field_1 TEXT,
        custom_field_2 TEXT,
        custom_field_3 TEXT,
        has_inspection_report BIGINT DEFAULT 0,
        is_active BIGINT DEFAULT 1,
        performance_method TEXT,
        suggested_min_cost DOUBLE DEFAULT 0,
        product_tags TEXT,
        fixed_url TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        KEY idx_product_name (name(100)),
        KEY idx_product_is_active (is_active),
        KEY idx_product_category (category_id),
        KEY idx_product_code (code),
        UNIQUE KEY sqlite_autoindex_Product_1 (code)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS ProductSku (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        product_id BIGINT,
        sku_code TEXT,
        spec_name TEXT,
        sku_type TEXT,
        is_listed BIGINT DEFAULT 1,
        price DOUBLE DEFAULT 0,
        stock DOUBLE DEFAULT 0,
        pricing_method TEXT,
        min_order_qty DOUBLE DEFAULT 1,
        sale_spec_value DOUBLE DEFAULT 1,
        sale_spec_unit TEXT,
        reference_cost DOUBLE DEFAULT 0,
        purchase_spec TEXT,
        stock_setting TEXT,
        stock_limit_value DOUBLE DEFAULT 0,
        pricing_rule TEXT,
        is_spot BIGINT DEFAULT 0,
        default_stock_slot TEXT,
        waste_ratio DOUBLE DEFAULT 0,
        box_type TEXT,
        order_round_up BIGINT DEFAULT 0,
        is_cycle_item BIGINT DEFAULT 0,
        KEY idx_product_sku_product (product_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS PurchaseInItem (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        record_id BIGINT,
        veg_name TEXT,
        category TEXT,
        unit TEXT,
        quantity DOUBLE DEFAULT 0,
        unit_price DOUBLE DEFAULT 0,
        amount DOUBLE DEFAULT 0,
        tax_rate DOUBLE DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        KEY idx_purchase_in_item_record (record_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS PurchaseInRecord (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        order_no TEXT,
        supplier_id BIGINT,
        inbound_date TEXT,
        total_amount DOUBLE DEFAULT 0,
        status TEXT,
        operator TEXT,
        remark TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        KEY idx_purchase_in_record_date (inbound_date),
        KEY idx_purchase_in_record_merchant (supplier_id),
        UNIQUE KEY sqlite_autoindex_PurchaseInRecord_1 (order_no)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS PurchaseReturnItem (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        record_id BIGINT,
        veg_name TEXT,
        category TEXT,
        unit TEXT,
        quantity DOUBLE DEFAULT 0,
        unit_price DOUBLE DEFAULT 0,
        amount DOUBLE DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS PurchaseReturnRecord (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        order_no TEXT,
        supplier_id BIGINT,
        return_date TEXT,
        total_amount DOUBLE DEFAULT 0,
        status TEXT,
        operator TEXT,
        remark TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        KEY idx_purchase_return_record_date (return_date),
        KEY idx_purchase_return_record_merchant (supplier_id),
        UNIQUE KEY sqlite_autoindex_PurchaseReturnRecord_1 (order_no)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS Quotation (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        code TEXT,
        name TEXT,
        external_name TEXT,
        currency TEXT,
        operation_time TEXT,
        tags TEXT,
        status TEXT,
        pricing_start_date TEXT,
        pricing_end_date TEXT,
        auto_pricing BIGINT DEFAULT 0,
        description TEXT,
        created_at TEXT,
        updated_at TEXT,
        KEY idx_quotation_name (name(100)),
        KEY idx_quotation_status (status),
        UNIQUE KEY sqlite_autoindex_Quotation_1 (code)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS QuotationProduct (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        quotation_id BIGINT,
        product_id BIGINT,
        sku_id BIGINT DEFAULT 0,
        price DOUBLE DEFAULT 0,
        is_active BIGINT DEFAULT 1,
        KEY idx_qp_product (product_id),
        KEY idx_qp_quotation (quotation_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS SortingPerformance (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        sorter_name TEXT,
        sorter_username TEXT,
        performance_date TEXT,
        total_performance DOUBLE DEFAULT 0,
        base_salary DOUBLE DEFAULT 0,
        piece_performance DOUBLE DEFAULT 0,
        weight_performance DOUBLE DEFAULT 0,
        operator TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS SortingTask (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        task_date TEXT,
        category TEXT,
        product_count BIGINT DEFAULT 0,
        status TEXT,
        operator TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS Merchant (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        code TEXT,
        name TEXT,
        contact_person TEXT,
        contact_phone TEXT,
        contact_address TEXT,
        settlement_method TEXT,
        status TEXT,
        remark TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        supplier_type TEXT,
        business_license TEXT,
        tax_number TEXT,
        bank_name TEXT,
        bank_account TEXT,
        payment_terms TEXT,
        credit_limit DOUBLE DEFAULT 0,
        level TEXT,
        settlement_person TEXT,
        settlement_phone TEXT,
        date_dimension TEXT,
        period_start_day BIGINT DEFAULT 1,
        settlement_day BIGINT DEFAULT 1,
        freeze_status BIGINT DEFAULT 0,
        approval_status BIGINT DEFAULT 1,
        sorting_priority BIGINT DEFAULT 0,
        KEY idx_merchant_name (name(100)),
        KEY idx_merchant_status (status(20)),
        UNIQUE KEY sqlite_autoindex_Merchant_1 (code(200))
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS MerchantProductPrice (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        supplier_id BIGINT,
        product_id BIGINT,
        price DOUBLE DEFAULT 0,
        unit_name TEXT,
        effective_from TEXT,
        effective_to TEXT,
        is_active BIGINT DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        KEY idx_spp_product (product_id),
        KEY idx_spp_merchant (supplier_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS MerchantSettlement (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        supplier_id BIGINT,
        settlement_period TEXT,
        payable_amount DOUBLE DEFAULT 0,
        paid_amount DOUBLE DEFAULT 0,
        fee_amount DOUBLE DEFAULT 0,
        discount_amount DOUBLE DEFAULT 0,
        balance_amount DOUBLE DEFAULT 0,
        reconciliation_status TEXT,
        status TEXT,
        remark TEXT,
        operator TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        KEY idx_merchant_settlement_period (settlement_period(50)),
        KEY idx_merchant_settlement_merchant (supplier_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS Supplier (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        supplier_code VARCHAR(50) NOT NULL,
        name VARCHAR(100) NOT NULL,
        company_name VARCHAR(200),
        contact_address VARCHAR(300),
        remark VARCHAR(500),
        default_purchaser VARCHAR(50),
        linked_station VARCHAR(100),
        settlement_cycle VARCHAR(20) DEFAULT '日结',
        invoice_type VARCHAR(30) DEFAULT '普票或无票',
        sales_purchase_settlement BIGINT DEFAULT 0,
        business_license VARCHAR(50),
        bank_account_name VARCHAR(100),
        bank_name VARCHAR(100),
        bank_account VARCHAR(50),
        supplier_nature VARCHAR(20) DEFAULT '普通',
        purchase_auto_sync BIGINT DEFAULT 0,
        geo_location VARCHAR(500),
        qualification_images TEXT DEFAULT ('[]'),
        payment_qr TEXT,
        status VARCHAR(20) DEFAULT 'active',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE KEY idx_supplier_code (supplier_code(50))
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS SupplierCategory (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        supplier_id BIGINT NOT NULL,
        category_id BIGINT NOT NULL,
        UNIQUE KEY idx_sc_unique (supplier_id, category_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS SupplierProduct (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        supplier_id BIGINT NOT NULL,
        product_id BIGINT NOT NULL,
        UNIQUE KEY idx_sp_unique (supplier_id, product_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS SupplierContact (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        supplier_id BIGINT NOT NULL,
        name TEXT NOT NULL,
        phone TEXT NOT NULL,
        role TEXT,
        is_default BIGINT DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS SupplierContract (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        supplier_id BIGINT NOT NULL,
        contract_no TEXT NOT NULL,
        start_date TEXT NOT NULL,
        end_date TEXT NOT NULL,
        file_url TEXT,
        status VARCHAR(20) DEFAULT 'active',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS Unit (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        name TEXT,
        description TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE KEY sqlite_autoindex_Unit_1 (name(100))
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS UserColumnPreference (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        user_id BIGINT,
        page_key TEXT,
        visible_columns TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        KEY idx_ucp_user_page (user_id, page_key),
        UNIQUE KEY sqlite_autoindex_UserColumnPreference_1 (user_id, page_key)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS Veg (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        name TEXT,
        category TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE KEY sqlite_autoindex_Veg_1 (name(100))
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS WeeklyPriceEntry (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        week_start TEXT,
        vegetable_id BIGINT,
        unit_id BIGINT,
        price DOUBLE,
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        KEY idx_weekly_veg_unit_week (vegetable_id, unit_id, week_start)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS WeeklyQuoteBatch (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        supplier TEXT,
        quote_date TEXT,
        source_label TEXT,
        source_path TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE KEY sqlite_autoindex_WeeklyQuoteBatch_1 (supplier, quote_date)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS WeeklyQuoteEntry (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        batch_id BIGINT,
        name TEXT,
        unit TEXT,
        price DOUBLE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS WeeklyQuoteMeasureUnitOption (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        name TEXT,
        sort_order BIGINT DEFAULT 1000,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        KEY idx_weekly_quote_measure_unit_order (sort_order, id),
        UNIQUE KEY sqlite_autoindex_WeeklyQuoteMeasureUnitOption_1 (name(100))
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS WeeklyQuoteMerchantConfig (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        name TEXT,
        weekly_batch_limit BIGINT DEFAULT 7,
        summary_rule TEXT,
        is_builtin BIGINT DEFAULT 0,
        sort_order BIGINT DEFAULT 1000,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        KEY idx_weekly_quote_supplier_config_order (sort_order, id),
        UNIQUE KEY sqlite_autoindex_WeeklyQuoteMerchantConfig_1 (name(100))
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS auth_audit_logs (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        actor_user_id BIGINT,
        target_user_id BIGINT,
        action TEXT,
        module TEXT,
        description TEXT,
        ip_address TEXT,
        user_agent TEXT,
        result TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        KEY idx_auth_audit_module_action_created (module, action, created_at),
        KEY idx_auth_audit_target_created (target_user_id, created_at),
        KEY idx_auth_audit_actor_created (actor_user_id, created_at)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS auth_devices (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        user_id BIGINT,
        device_name TEXT,
        device_fingerprint TEXT,
        user_agent TEXT,
        browser TEXT,
        os TEXT,
        ip_address TEXT,
        first_login_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_active_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        is_revoked BIGINT DEFAULT 0,
        revoked_at TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        KEY idx_auth_devices_user_active (user_id, is_revoked, last_active_at),
        UNIQUE KEY sqlite_autoindex_auth_devices_1 (user_id, device_fingerprint)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS auth_pending_logins (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        user_id BIGINT,
        pending_token_hash TEXT,
        ip_address TEXT,
        user_agent TEXT,
        expires_at TEXT,
        used_at TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        device_name TEXT,
        KEY idx_auth_pending_logins_user_expires (user_id, expires_at),
        UNIQUE KEY sqlite_autoindex_auth_pending_logins_1 (pending_token_hash)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS auth_permission_requests (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        user_id BIGINT,
        permission_id BIGINT,
        permission_code TEXT,
        reason TEXT,
        status TEXT,
        reviewer_id BIGINT,
        review_comment TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        reviewed_at TEXT,
        UNIQUE KEY idx_auth_permission_requests_pending (user_id, permission_code),
        KEY idx_auth_permission_requests_user_status (user_id, status, created_at)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS auth_permissions (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        code TEXT,
        name TEXT,
        module TEXT,
        description TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE KEY sqlite_autoindex_auth_permissions_1 (code)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS auth_refresh_token_grace (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        session_id BIGINT,
        refresh_token_hash TEXT,
        valid_until TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        KEY idx_auth_refresh_token_grace_session (session_id, valid_until),
        UNIQUE KEY sqlite_autoindex_auth_refresh_token_grace_1 (refresh_token_hash)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS auth_role_permissions (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        role_id BIGINT,
        permission_id BIGINT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        KEY idx_auth_role_permissions_role (role_id),
        UNIQUE KEY sqlite_autoindex_auth_role_permissions_1 (role_id, permission_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS auth_roles (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        code TEXT,
        name TEXT,
        description TEXT,
        is_system BIGINT DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE KEY sqlite_autoindex_auth_roles_1 (code)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS auth_sessions (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        user_id BIGINT,
        device_id BIGINT,
        access_token_hash TEXT,
        refresh_token_hash TEXT,
        access_expires_at TEXT,
        refresh_expires_at TEXT,
        revoked_at TEXT,
        revoke_reason TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_active_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        ip_address TEXT,
        user_agent TEXT,
        KEY idx_auth_sessions_active_refresh (refresh_token_hash, refresh_expires_at),
        KEY idx_auth_sessions_active_access (access_token_hash, access_expires_at),
        KEY idx_auth_sessions_user_device (user_id, device_id, revoked_at),
        UNIQUE KEY sqlite_autoindex_auth_sessions_2 (refresh_token_hash),
        UNIQUE KEY sqlite_autoindex_auth_sessions_1 (access_token_hash)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS auth_user_permission_overrides (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        user_id BIGINT,
        permission_id BIGINT,
        effect TEXT,
        reason TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        KEY idx_auth_permission_overrides_user (user_id),
        UNIQUE KEY sqlite_autoindex_auth_user_permission_overrides_1 (user_id, permission_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS auth_user_roles (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        user_id BIGINT,
        role_id BIGINT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        KEY idx_auth_user_roles_user (user_id),
        UNIQUE KEY sqlite_autoindex_auth_user_roles_1 (user_id, role_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS auth_users (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        username TEXT,
        display_name TEXT,
        password_hash TEXT,
        password_salt TEXT,
        is_active BIGINT DEFAULT 1,
        is_super_admin BIGINT DEFAULT 0,
        must_change_password BIGINT DEFAULT 0,
        failed_login_count BIGINT DEFAULT 0,
        locked_until TEXT,
        last_failed_login_at TEXT,
        last_login_at TEXT,
        password_changed_at TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE KEY sqlite_autoindex_auth_users_1 (username)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS schema_migrations (
        version BIGINT,
        name TEXT,
        applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
