-- KTV 数据分析数据库建表脚本
-- 数据库: ktv_analysis
-- 创建时间: 2026-04-24

CREATE DATABASE IF NOT EXISTS `ktv_analysis` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE `ktv_analysis`;

-- 门店信息表
CREATE TABLE IF NOT EXISTS `stores` (
    `id` INT AUTO_INCREMENT PRIMARY KEY COMMENT '门店ID',
    `store_name` VARCHAR(100) NOT NULL UNIQUE COMMENT '门店名称',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX `idx_store_name` (`store_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='门店信息表';

-- 日营业数据表
CREATE TABLE IF NOT EXISTS `store_daily` (
    `id` INT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    `store_id` INT NOT NULL COMMENT '门店ID',
    `data_date` DATE NOT NULL COMMENT '数据日期',
    `weekday` VARCHAR(20) DEFAULT '' COMMENT '星期几',
    `total_revenue` DECIMAL(12,2) DEFAULT 0 COMMENT '总计营业额',
    `actual_amount` DECIMAL(12,2) DEFAULT 0 COMMENT '实收金额',
    `supermarket_revenue` DECIMAL(12,2) DEFAULT 0 COMMENT '超市收入',
    `room_revenue` DECIMAL(12,2) DEFAULT 0 COMMENT '房费收入',
    `stored_card_sales` DECIMAL(12,2) DEFAULT 0 COMMENT '储值卡销售',
    `times_card_sales` DECIMAL(12,2) DEFAULT 0 COMMENT '次卡销售',
    `other_revenue` DECIMAL(12,2) DEFAULT 0 COMMENT '营业外收入',
    `transfer_fund` DECIMAL(12,2) DEFAULT 0 COMMENT '往来资金',
    `online_groupbuy` DECIMAL(12,2) DEFAULT 0 COMMENT '线上团购应收',
    `daily_batch_consumption` DECIMAL(12,2) DEFAULT 0 COMMENT '日单批消费',
    `customers_before_18` INT DEFAULT 0 COMMENT '18点前待客人数',
    `maintenance_before_18` INT DEFAULT 0 COMMENT '18点前维护人数',
    `customers_18_to_24` INT DEFAULT 0 COMMENT '18点-24点待客人数',
    `maintenance_18_to_24` INT DEFAULT 0 COMMENT '18点-24点维护人数',
    `customers_after_00` INT DEFAULT 0 COMMENT '00点后待客人数',
    `maintenance_after_00` INT DEFAULT 0 COMMENT '00点后维护人数',
    `peak_room_count` INT DEFAULT 0 COMMENT '晚场待客最高峰台数',
    `peak_time` VARCHAR(50) DEFAULT '' COMMENT '晚场待客最高峰时点',
    `revenue` DECIMAL(12,2) DEFAULT 0 COMMENT '营业额',
    `customers` INT DEFAULT 0 COMMENT '全天待客台数',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    UNIQUE KEY `uk_store_date` (`store_id`, `data_date`),
    INDEX `idx_data_date` (`data_date`),
    INDEX `idx_store_id` (`store_id`),
    CONSTRAINT `fk_store_daily_store` FOREIGN KEY (`store_id`) REFERENCES `stores`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='日营业数据表';

-- 储值订单表
CREATE TABLE IF NOT EXISTS `stored_value` (
    `id` INT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    `store_id` INT NOT NULL COMMENT '门店ID',
    `data_date` DATE DEFAULT NULL COMMENT '数据日期',
    `member_level` VARCHAR(50) DEFAULT '' COMMENT '会员等级',
    `stored_amount` DECIMAL(12,2) DEFAULT 0 COMMENT '储值金额',
    `stored_count` INT DEFAULT 1 COMMENT '储值次数',
    `recharge_source` VARCHAR(100) DEFAULT '' COMMENT '充值来源',
    `is_first_recharge` TINYINT(1) DEFAULT 0 COMMENT '是否首充',
    `marketing_manager` VARCHAR(100) DEFAULT '' COMMENT '营销经理',
    `member_name` VARCHAR(100) DEFAULT '' COMMENT '会员姓名',
    `member_phone` VARCHAR(20) DEFAULT '' COMMENT '会员电话',
    `room_principal` DECIMAL(12,2) DEFAULT 0 COMMENT '房费变动本金',
    `room_gift` DECIMAL(12,2) DEFAULT 0 COMMENT '房费变动赠金',
    `drink_principal` DECIMAL(12,2) DEFAULT 0 COMMENT '酒水变动本金',
    `drink_gift` DECIMAL(12,2) DEFAULT 0 COMMENT '酒水变动赠金',
    `payment_method` VARCHAR(50) DEFAULT '' COMMENT '支付方式',
    `payment_amount` DECIMAL(12,2) DEFAULT 0 COMMENT '支付金额',
    `points_change` INT DEFAULT 0 COMMENT '变动积分',
    `points_balance` INT DEFAULT 0 COMMENT '积分余额',
    `growth_change` INT DEFAULT 0 COMMENT '变动成长值',
    `growth_balance` INT DEFAULT 0 COMMENT '成长值余额',
    `total_balance` DECIMAL(12,2) DEFAULT 0 COMMENT '合计余额',
    `principal_balance` DECIMAL(12,2) DEFAULT 0 COMMENT '本金余额',
    `gift_balance` DECIMAL(12,2) DEFAULT 0 COMMENT '赠送余额',
    `recharge_time` DATETIME DEFAULT NULL COMMENT '充值时间',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX `idx_store_id` (`store_id`),
    INDEX `idx_data_date` (`data_date`),
    INDEX `idx_member_phone` (`member_phone`),
    CONSTRAINT `fk_stored_value_store` FOREIGN KEY (`store_id`) REFERENCES `stores`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='储值订单表';

-- 商品销售表
CREATE TABLE IF NOT EXISTS `product_sales` (
    `id` INT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    `store_id` INT NOT NULL COMMENT '门店ID',
    `data_date` DATE NOT NULL COMMENT '数据日期',
    `product_name` VARCHAR(200) DEFAULT '' COMMENT '商品名称',
    `category` VARCHAR(100) DEFAULT '' COMMENT '统计类别',
    `unit_price` DECIMAL(10,2) DEFAULT 0 COMMENT '单价',
    `quantity` INT DEFAULT 0 COMMENT '数量',
    `sales_amount` DECIMAL(12,2) DEFAULT 0 COMMENT '销售金额',
    `room_type` VARCHAR(50) DEFAULT '' COMMENT '单位/包厢类型',
    `big_category` VARCHAR(50) DEFAULT '其他' COMMENT '大类别',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX `idx_store_id` (`store_id`),
    INDEX `idx_data_date` (`data_date`),
    INDEX `idx_product_name` (`product_name`),
    INDEX `idx_big_category` (`big_category`),
    CONSTRAINT `fk_product_sales_store` FOREIGN KEY (`store_id`) REFERENCES `stores`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='商品销售表';

-- 视图：门店营业汇总
CREATE OR REPLACE VIEW `v_store_revenue_summary` AS
SELECT
    store_id,
    s.store_name,
    data_date,
    total_revenue,
    actual_amount,
    supermarket_revenue,
    room_revenue,
    stored_card_sales,
    times_card_sales
FROM store_daily sd
JOIN stores s ON sd.store_id = s.id;

-- 视图：商品销售汇总
CREATE OR REPLACE VIEW `v_product_sales_summary` AS
SELECT
    store_id,
    s.store_name,
    data_date,
    big_category,
    COUNT(DISTINCT product_name) as product_count,
    SUM(quantity) as total_quantity,
    SUM(sales_amount) as total_amount
FROM product_sales ps
JOIN stores s ON ps.store_id = s.id
GROUP BY store_id, s.store_name, data_date, big_category;

-- 订单明细表（时段客单价分析）
CREATE TABLE IF NOT EXISTS `order_detail` (
    `id` INT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    `store_id` INT NOT NULL COMMENT '门店ID',
    `data_date` DATE NOT NULL COMMENT '数据日期',
    `time_period` VARCHAR(50) DEFAULT '' COMMENT '开房时段',
    `room_type` VARCHAR(50) DEFAULT '' COMMENT '开房类型',
    `room_no` VARCHAR(50) DEFAULT '' COMMENT '包厢号',
    `open_time` DATETIME DEFAULT NULL COMMENT '开房时间',
    `close_time` DATETIME DEFAULT NULL COMMENT '关房时间',
    `customer_name` VARCHAR(100) DEFAULT '' COMMENT '开房人姓名',
    `customer_phone` VARCHAR(20) DEFAULT '' COMMENT '开房人手机号',
    `order_no` VARCHAR(100) DEFAULT '' COMMENT '开台单号',
    `should_amount` DECIMAL(12,2) DEFAULT 0 COMMENT '应收金额',
    `actual_amount` DECIMAL(12,2) DEFAULT 0 COMMENT '实收金额',
    `room_fee` DECIMAL(12,2) DEFAULT 0 COMMENT '房费收入',
    `product_fee` DECIMAL(12,2) DEFAULT 0 COMMENT '商品收入',
    `source_channel` VARCHAR(50) DEFAULT '' COMMENT '来源渠道',
    `scene` VARCHAR(50) DEFAULT '' COMMENT '场景',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX `idx_store_id` (`store_id`),
    INDEX `idx_data_date` (`data_date`),
    INDEX `idx_time_period` (`time_period`),
    INDEX `idx_room_no` (`room_no`),
    CONSTRAINT `fk_order_detail_store` FOREIGN KEY (`store_id`) REFERENCES `stores`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='订单明细表（时段客单价分析）';

-- 视图：时段客单价分析
CREATE OR REPLACE VIEW `v_time_period_analysis` AS
SELECT
    store_id,
    s.store_name,
    data_date,
    time_period,
    COUNT(*) as order_count,
    SUM(actual_amount) as total_amount,
    AVG(actual_amount) as avg_amount
FROM order_detail od
JOIN stores s ON od.store_id = s.id
GROUP BY store_id, s.store_name, data_date, time_period;