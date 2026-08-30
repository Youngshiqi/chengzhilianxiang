-- ============================================================
-- 城市公共设施智能报修与派单系统 - 时间迁移脚本
-- 问题：历史数据使用 UTC 时间存储，需要 +8 小时转为北京时间
-- 运行方式：mysql -u city_repair -p city_repair < fix_timezone.sql
-- 注意：每个表只执行一次，重复执行会导致时间偏移 16 小时！
-- ============================================================

-- tickets 工单主表
UPDATE tickets SET created_at = DATE_ADD(created_at, INTERVAL 8 HOUR) WHERE created_at IS NOT NULL;
UPDATE tickets SET accepted_at = DATE_ADD(accepted_at, INTERVAL 8 HOUR) WHERE accepted_at IS NOT NULL;
UPDATE tickets SET started_at = DATE_ADD(started_at, INTERVAL 8 HOUR) WHERE started_at IS NOT NULL;
UPDATE tickets SET completed_at = DATE_ADD(completed_at, INTERVAL 8 HOUR) WHERE completed_at IS NOT NULL;
UPDATE tickets SET closed_at = DATE_ADD(closed_at, INTERVAL 8 HOUR) WHERE closed_at IS NOT NULL;

-- users 用户表
UPDATE users SET created_at = DATE_ADD(created_at, INTERVAL 8 HOUR) WHERE created_at IS NOT NULL;

-- settlements 结算表
UPDATE settlements SET created_at = DATE_ADD(created_at, INTERVAL 8 HOUR) WHERE created_at IS NOT NULL;

-- evaluations 评价表
UPDATE evaluations SET created_at = DATE_ADD(created_at, INTERVAL 8 HOUR) WHERE created_at IS NOT NULL;

-- 验证修复结果
SELECT 'tickets' AS tbl, created_at FROM tickets ORDER BY created_at DESC LIMIT 3;
SELECT 'users' AS tbl, created_at FROM users ORDER BY created_at DESC LIMIT 3;
