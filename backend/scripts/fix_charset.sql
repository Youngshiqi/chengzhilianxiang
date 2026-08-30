-- ============================================================
-- 城市公共设施智能报修与派单系统 - 字符集修复脚本
-- 问题：数据库/表可能使用 latin1 默认字符集，导致中文乱码
-- 解决：将数据库、所有表、所有文本列统一改为 utf8mb4
-- 运行方式：mysql -u city_repair -p city_repair < fix_charset.sql
-- 注意：已损毁的数据（latin1 存入的 UTF-8 中文）无法自动恢复，
--       需重新导入或由业务操作重新生成
-- ============================================================

-- 1. 修改数据库默认字符集
ALTER DATABASE city_repair CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 2. 修改 tickets 表及列
ALTER TABLE tickets CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
ALTER TABLE tickets MODIFY ticket_id VARCHAR(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL;
ALTER TABLE tickets MODIFY user_id VARCHAR(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL;
ALTER TABLE tickets MODIFY facility_code VARCHAR(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL;
ALTER TABLE tickets MODIFY facility_type VARCHAR(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL;
ALTER TABLE tickets MODIFY district VARCHAR(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
ALTER TABLE tickets MODIFY description TEXT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
ALTER TABLE tickets MODIFY address VARCHAR(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL;
ALTER TABLE tickets MODIFY assigned_worker_id VARCHAR(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
ALTER TABLE tickets MODIFY ai_category VARCHAR(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 3. 修改 users 表及列
ALTER TABLE users CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
ALTER TABLE users MODIFY user_id VARCHAR(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL;
ALTER TABLE users MODIFY username VARCHAR(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL;
ALTER TABLE users MODIFY nickname VARCHAR(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
ALTER TABLE users MODIFY phone VARCHAR(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
ALTER TABLE users MODIFY avatar_url VARCHAR(512) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
ALTER TABLE users MODIFY password_hash VARCHAR(128) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL;
ALTER TABLE users MODIFY role VARCHAR(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL;

-- 4. 修改 workers 表及列
ALTER TABLE workers CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
ALTER TABLE workers MODIFY worker_id VARCHAR(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL;
ALTER TABLE workers MODIFY name VARCHAR(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL;
ALTER TABLE workers MODIFY phone VARCHAR(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
ALTER TABLE workers MODIFY district VARCHAR(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
ALTER TABLE workers MODIFY skill_tags VARCHAR(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 5. 修改 facilities 表及列
ALTER TABLE facilities CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
ALTER TABLE facilities MODIFY facility_code VARCHAR(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL;
ALTER TABLE facilities MODIFY name VARCHAR(128) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL;
ALTER TABLE facilities MODIFY type VARCHAR(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL;
ALTER TABLE facilities MODIFY address VARCHAR(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
ALTER TABLE facilities MODIFY district VARCHAR(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 6. 修改 settlements 表及列
ALTER TABLE settlements CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
ALTER TABLE settlements MODIFY settlement_id VARCHAR(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL;
ALTER TABLE settlements MODIFY ticket_id VARCHAR(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL;
ALTER TABLE settlements MODIFY worker_id VARCHAR(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL;

-- 7. 修改 evaluations 表及列
ALTER TABLE evaluations CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
ALTER TABLE evaluations MODIFY eval_id VARCHAR(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL;
ALTER TABLE evaluations MODIFY ticket_id VARCHAR(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL;
ALTER TABLE evaluations MODIFY user_id VARCHAR(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL;
ALTER TABLE evaluations MODIFY comment TEXT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 8. 修改 audit_rules 表及列
ALTER TABLE audit_rules CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
ALTER TABLE audit_rules MODIFY rule_id VARCHAR(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL;
ALTER TABLE audit_rules MODIFY rule_name VARCHAR(128) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL;

-- 验证修复结果
SELECT TABLE_NAME, TABLE_COLLATION
FROM information_schema.TABLES
WHERE TABLE_SCHEMA = 'city_repair';
