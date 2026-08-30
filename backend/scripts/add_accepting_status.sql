-- ============================================================
-- 城市公共设施智能报修与派单系统 - 添加 accepting 工单状态
-- 问题：数据库枚举 ticket_status 缺少 'accepting' 值
-- 解决：修改枚举类型添加新状态
-- 运行方式：mysql -u city_repair -p city_repair < add_accepting_status.sql
-- ============================================================

-- 修改 tickets 表的 status 列枚举，添加 'accepting'
ALTER TABLE tickets
MODIFY COLUMN status ENUM(
    'pending',
    'accepting',
    'dispatching',
    'repairing',
    'verifying',
    'closed'
) DEFAULT 'pending'
COMMENT '工单状态';

-- 验证修改结果
SHOW COLUMNS FROM tickets LIKE 'status';
