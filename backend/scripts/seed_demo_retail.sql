/*
 * demo_retail — 电商零售演示数据库
 * 用于 NL2SQL 归因平台的端到端功能演示
 */

CREATE DATABASE IF NOT EXISTS demo_retail DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE demo_retail;

-- ==================== 产品分类 ====================
DROP TABLE IF EXISTS categories;
CREATE TABLE categories (
    id          INT AUTO_INCREMENT PRIMARY KEY COMMENT '分类ID',
    name        VARCHAR(50)  NOT NULL COMMENT '分类名称',
    parent_id   INT          NULL COMMENT '父分类ID',
    level       TINYINT      NOT NULL DEFAULT 1 COMMENT '层级',
    sort_order  INT          NOT NULL DEFAULT 0 COMMENT '排序值',
    created_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间'
) COMMENT '产品分类表';

INSERT INTO categories (id, name, parent_id, level, sort_order) VALUES
(1, '电子产品',  NULL, 1, 1),
(2, '手机',      1,    2, 1),
(3, '电脑',      1,    2, 2),
(4, '配件',      1,    2, 3),
(5, '服装',      NULL, 1, 2),
(6, '男装',      5,    2, 1),
(7, '女装',      5,    2, 2),
(8, '食品饮料',  NULL, 1, 3),
(9, '零食',      8,    2, 1),
(10,'饮品',      8,    2, 2);

-- ==================== 产品 ====================
DROP TABLE IF EXISTS products;
CREATE TABLE products (
    id              INT AUTO_INCREMENT PRIMARY KEY COMMENT '产品ID',
    category_id     INT           NOT NULL COMMENT '分类ID',
    name            VARCHAR(200)  NOT NULL COMMENT '产品名称',
    sku             VARCHAR(50)   NOT NULL COMMENT 'SKU',
    unit_price      DECIMAL(12,2) NOT NULL COMMENT '单价',
    cost_price      DECIMAL(12,2) NOT NULL COMMENT '成本价',
    stock_qty       INT           NOT NULL DEFAULT 0 COMMENT '库存数量',
    status          TINYINT       NOT NULL DEFAULT 1 COMMENT '状态 1上架 0下架',
    created_at      DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    INDEX idx_category (category_id),
    INDEX idx_status (status)
) COMMENT '产品表';

INSERT INTO products (category_id, name, sku, unit_price, cost_price, stock_qty, status) VALUES
(2,  'iPhone 15 Pro Max',   'APP-IP15PM-256', 8999.00, 6500.00, 1200, 1),
(2,  '华为 Mate 60 Pro',   'HW-M60P-512',    6999.00, 5200.00, 800,  1),
(2,  '小米 14 Ultra',      'XM-14U-512',     5999.00, 4300.00, 1500, 1),
(3,  'MacBook Pro 14',     'APP-MBP14-M3',   14999.00, 11000.00, 500, 1),
(3,  'ThinkPad X1 Carbon', 'LN-TPX1-G12',    12999.00, 9500.00, 300,  1),
(4,  'AirPods Pro 2',      'APP-APP2-USB',   1899.00, 1200.00, 2000, 1),
(4,  '华为 FreeBuds 5',    'HW-FB5-WH',      999.00,  700.00,  2500, 1),
(6,  '男士商务衬衫',       'NS-CS-BW-M',     399.00,  180.00,  3000, 1),
(6,  '男士牛仔裤',         'NS-JEANS-BL',    499.00,  220.00,  2500, 1),
(7,  '女士连衣裙',         'NS-DRESS-RD',    599.00,  260.00,  1800, 1),
(9,  '三只松鼠坚果礼盒',   'FOOD-NUT-BX',    128.00,  75.00,   5000, 1),
(10, '元气森林气泡水',     'DRINK-QSL-12',   5.50,    3.20,   10000, 1),
(10, '农夫山泉矿泉水',     'DRINK-NFS-24',   2.00,    1.10,   20000, 1);

-- ==================== 客户 ====================
DROP TABLE IF EXISTS customers;
CREATE TABLE customers (
    id          INT AUTO_INCREMENT PRIMARY KEY COMMENT '客户ID',
    name        VARCHAR(100)  NOT NULL COMMENT '客户姓名',
    phone       VARCHAR(20)   NULL COMMENT '手机号',
    email       VARCHAR(100)  NULL COMMENT '邮箱',
    gender      TINYINT       NULL COMMENT '性别 1男 2女',
    city        VARCHAR(50)   NULL COMMENT '所在城市',
    level       VARCHAR(20)   NOT NULL DEFAULT '普通' COMMENT '会员等级',
    created_at  DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '注册时间',
    INDEX idx_city (city),
    INDEX idx_level (level)
) COMMENT '客户表';

INSERT INTO customers (id, name, phone, email, gender, city, level) VALUES
(1,  '张三', '13800138001', 'zhangsan@email.com',  1, '北京', '钻石'),
(2,  '李四', '13800138002', 'lisi@email.com',      1, '上海', '黄金'),
(3,  '王五', '13800138003', 'wangwu@email.com',    2, '广州', '白银'),
(4,  '赵六', '13800138004', 'zhaoliu@email.com',   2, '深圳', '黄金'),
(5,  '孙七', '13800138005', 'sunqi@email.com',     1, '杭州', '普通'),
(6,  '周八', '13800138006', 'zhouba@email.com',    1, '成都', '普通'),
(7,  '吴九', '13800138007', 'wujiu@email.com',     2, '北京', '钻石'),
(8,  '郑十', '13800138008', 'zhengshi@email.com',  1, '上海', '白银');

-- ==================== 订单 ====================
DROP TABLE IF EXISTS orders;
CREATE TABLE orders (
    id              INT AUTO_INCREMENT PRIMARY KEY COMMENT '订单ID',
    order_no        VARCHAR(30)   NOT NULL COMMENT '订单号',
    customer_id     INT           NOT NULL COMMENT '客户ID',
    order_date      DATETIME      NOT NULL COMMENT '下单时间',
    total_amount    DECIMAL(14,2) NOT NULL COMMENT '订单总额',
    discount_amount DECIMAL(12,2) NOT NULL DEFAULT 0 COMMENT '优惠金额',
    payment_method  VARCHAR(20)   NULL COMMENT '支付方式',
    status          TINYINT       NOT NULL DEFAULT 0 COMMENT '状态 0待支付 1已支付 2已发货 3已完成 4已取消',
    shipping_city   VARCHAR(50)   NULL COMMENT '收货城市',
    created_at      DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    INDEX idx_customer (customer_id),
    INDEX idx_date (order_date),
    INDEX idx_status (status)
) COMMENT '订单表';

INSERT INTO orders (id, order_no, customer_id, order_date, total_amount, discount_amount, payment_method, status, shipping_city) VALUES
(1,  'ORD-20260101-001', 1, '2026-01-01 10:30:00', 8999.00,  0.00,   '微信支付', 3, '北京'),
(2,  'ORD-20260103-002', 2, '2026-01-03 14:20:00', 14999.00, 200.00, '支付宝',   3, '上海'),
(3,  'ORD-20260105-003', 3, '2026-01-05 09:15:00', 399.00,   0.00,   '微信支付', 3, '广州'),
(4,  'ORD-20260110-004', 1, '2026-01-10 16:45:00', 1899.00,  50.00,  '银行卡',   3, '北京'),
(5,  'ORD-20260115-005', 4, '2026-01-15 11:00:00', 6999.00,  100.00, '支付宝',   3, '深圳'),
(6,  'ORD-20260120-006', 5, '2026-01-20 08:30:00', 128.00,   0.00,   '微信支付', 3, '杭州'),
(7,  'ORD-20260201-007', 6, '2026-02-01 13:00:00', 599.00,   0.00,   '微信支付', 3, '成都'),
(8,  'ORD-20260205-008', 2, '2026-02-05 10:10:00', 499.00,   0.00,   '支付宝',   3, '上海'),
(9,  'ORD-20260210-009', 7, '2026-02-10 15:30:00', 12999.00, 300.00, '银行卡',   3, '北京'),
(10, 'ORD-20260301-010', 3, '2026-03-01 09:00:00', 999.00,   0.00,   '微信支付', 3, '广州'),
(11, 'ORD-20260305-011', 8, '2026-03-05 14:20:00', 5999.00,  0.00,   '支付宝',   3, '上海'),
(12, 'ORD-20260310-012', 1, '2026-03-10 11:30:00', 399.00,   0.00,   '微信支付', 3, '北京'),
(13, 'ORD-20260315-013', 4, '2026-03-15 16:00:00', 1899.00,  0.00,   '支付宝',   3, '深圳'),
(14, 'ORD-20260320-014', 5, '2026-03-20 10:45:00', 5.50,     0.00,   '微信支付', 3, '杭州'),
(15, 'ORD-20260401-015', 6, '2026-04-01 08:00:00', 14999.00, 500.00, '银行卡',   3, '成都'),
(16, 'ORD-20260405-016', 2, '2026-04-05 17:30:00', 128.00,   0.00,   '微信支付', 3, '上海'),
(17, 'ORD-20260410-017', 7, '2026-04-10 12:00:00', 5999.00,  0.00,   '支付宝',   3, '北京'),
(18, 'ORD-20260501-018', 8, '2026-05-01 09:30:00', 8999.00,  100.00, '微信支付', 3, '上海'),
(19, 'ORD-20260510-019', 3, '2026-05-10 14:00:00', 399.00,   0.00,   '支付宝',   3, '广州'),
(20, 'ORD-20260601-020', 1, '2026-06-01 11:15:00', 5999.00,  0.00,   '微信支付', 3, '北京');

-- ==================== 订单明细 ====================
DROP TABLE IF EXISTS order_items;
CREATE TABLE order_items (
    id          INT AUTO_INCREMENT PRIMARY KEY COMMENT '明细ID',
    order_id    INT           NOT NULL COMMENT '订单ID',
    product_id  INT           NOT NULL COMMENT '产品ID',
    quantity    INT           NOT NULL COMMENT '数量',
    unit_price  DECIMAL(12,2) NOT NULL COMMENT '实际单价',
    subtotal    DECIMAL(14,2) NOT NULL COMMENT '小计金额',
    INDEX idx_order (order_id),
    INDEX idx_product (product_id)
) COMMENT '订单明细表';

INSERT INTO order_items (order_id, product_id, quantity, unit_price, subtotal) VALUES
(1,  1,  1, 8999.00, 8999.00),
(2,  4,  1, 14999.00, 14999.00),
(3,  8,  1, 399.00, 399.00),
(4,  6,  1, 1899.00, 1899.00),
(5,  2,  1, 6999.00, 6999.00),
(6,  11, 1, 128.00,  128.00),
(7,  10, 1, 599.00,  599.00),
(8,  9,  1, 499.00,  499.00),
(9,  5,  1, 12999.00, 12999.00),
(10, 7,  1, 999.00,  999.00),
(11, 3,  1, 5999.00, 5999.00),
(12, 8,  1, 399.00,  399.00),
(13, 6,  1, 1899.00, 1899.00),
(14, 12, 1, 5.50,    5.50),
(15, 4,  1, 14999.00, 14999.00),
(16, 11, 1, 128.00,  128.00),
(17, 3,  1, 5999.00, 5999.00),
(18, 1,  1, 8999.00, 8999.00),
(19, 8,  1, 399.00,  399.00),
(20, 3,  1, 5999.00, 5999.00);

-- ==================== 营销活动 ====================
DROP TABLE IF EXISTS campaigns;
CREATE TABLE campaigns (
    id              INT AUTO_INCREMENT PRIMARY KEY COMMENT '活动ID',
    name            VARCHAR(200)  NOT NULL COMMENT '活动名称',
    channel         VARCHAR(50)   NOT NULL COMMENT '渠道',
    start_date      DATE          NOT NULL COMMENT '开始日期',
    end_date        DATE          NOT NULL COMMENT '结束日期',
    budget          DECIMAL(14,2) NOT NULL COMMENT '预算金额',
    cost            DECIMAL(14,2) NOT NULL DEFAULT 0 COMMENT '实际花费',
    impressions     INT           NOT NULL DEFAULT 0 COMMENT '曝光量',
    clicks          INT           NOT NULL DEFAULT 0 COMMENT '点击量',
    conversions     INT           NOT NULL DEFAULT 0 COMMENT '转化数',
    revenue         DECIMAL(14,2) NOT NULL DEFAULT 0 COMMENT '归因收入',
    created_at      DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_channel (channel),
    INDEX idx_date (start_date, end_date)
) COMMENT '营销活动表';

INSERT INTO campaigns (name, channel, start_date, end_date, budget, cost, impressions, clicks, conversions, revenue) VALUES
('春节大促',       '抖音',   '2026-01-15', '2026-02-15', 500000.00, 480000.00, 2500000, 125000, 8500, 3200000.00),
('春季焕新',       '小红书', '2026-03-01', '2026-04-15', 300000.00, 285000.00, 1200000, 72000,  4200, 1800000.00),
('618预售',        '淘宝',   '2026-05-20', '2026-06-20', 800000.00, 790000.00, 3800000, 190000, 15000, 5800000.00),
('品牌日',         '京东',   '2026-04-01', '2026-04-30', 200000.00, 195000.00, 900000,  54000,  3200, 1200000.00),
('新品首发',       '抖音',   '2026-03-15', '2026-04-30', 350000.00, 340000.00, 1800000, 90000,  5600, 2100000.00),
('夏日狂欢',       '微信',   '2026-06-01', '2026-07-31', 400000.00, 380000.00, 1600000, 80000,  4800, 1900000.00),
('会员日',         '短信',   '2026-02-10', '2026-02-10', 50000.00,  48000.00,  200000,  8000,   1200, 450000.00),
('直播专场',       '抖音',   '2026-05-01', '2026-05-15', 250000.00, 240000.00, 1100000, 66000,  3800, 1500000.00);

-- ==================== 客服工单 ====================
DROP TABLE IF EXISTS support_tickets;
CREATE TABLE support_tickets (
    id              INT AUTO_INCREMENT PRIMARY KEY COMMENT '工单ID',
    order_id        INT           NULL COMMENT '关联订单ID',
    customer_id     INT           NOT NULL COMMENT '客户ID',
    category        VARCHAR(50)   NOT NULL COMMENT '工单类型',
    priority        TINYINT       NOT NULL DEFAULT 1 COMMENT '优先级 1低 2中 3高',
    status          TINYINT       NOT NULL DEFAULT 0 COMMENT '状态 0待处理 1处理中 2已解决 3已关闭',
    description     TEXT          NULL COMMENT '问题描述',
    created_at      DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    resolved_at     DATETIME      NULL COMMENT '解决时间',
    INDEX idx_customer (customer_id),
    INDEX idx_status (status)
) COMMENT '客服工单表';

INSERT INTO support_tickets (order_id, customer_id, category, priority, status, description, created_at, resolved_at) VALUES
(1,  1, '退换货',   2, 2, '手机屏幕有划痕',             '2026-01-05 09:00:00', '2026-01-06 14:00:00'),
(2,  2, '物流查询', 1, 2, '电脑发货后未更新物流信息',   '2026-01-06 10:30:00', '2026-01-06 16:00:00'),
(5,  4, '发票开具', 1, 2, '需要开具增值税专用发票',     '2026-01-18 11:00:00', '2026-01-19 10:00:00'),
(NULL, 3, '账号问题', 3, 1, '账号无法登录',             '2026-02-01 08:00:00', '2026-02-02 09:00:00'),
(9,  7, '退换货',   2, 2, '电脑开机蓝屏',               '2026-02-12 14:00:00', '2026-02-14 10:00:00'),
(15, 6, '退款咨询', 2, 0, '申请退款但未收到款项',       '2026-04-03 09:30:00', NULL),
(NULL, 5, '产品咨询', 1, 2, '坚果礼盒是否含过敏原',     '2026-03-22 15:00:00', '2026-03-23 10:00:00'),
(20, 1, '退换货',   2, 1, '手机颜色发错',               '2026-06-03 10:00:00', NULL);

SELECT 'demo_retail database seeded successfully!' AS result;