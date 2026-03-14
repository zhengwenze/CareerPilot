-- 临时本地引导脚本（仅供手动调试）
-- 正式开发请使用 apps/api/alembic/ 下的迁移文件作为数据库结构唯一来源。
-- docker-compose.middleware.yml 已经会创建 career_pilot 数据库，通常无需手动执行本文件。

SELECT 'CREATE DATABASE career_pilot'
WHERE NOT EXISTS (
  SELECT FROM pg_database WHERE datname = 'career_pilot'
)\gexec

\c career_pilot

-- 数据库创建完后，请在 apps/api 目录执行：
-- uv run alembic upgrade head
