#!/bin/bash
# =============================================================
# M0-2 PostgreSQL 初始化 — collaboration 库专用应用账号（幂等）
# 仅首次初始化数据目录时由 docker-entrypoint 自动执行；
# 已初始化的实例可手动执行本脚本（见 M0_DEPLOYMENT_DESIGN.md §14）。
# 密码来自容器环境变量 COLLAB_APP_PASSWORD（.env → compose）。
# 约束：开发期密码建议使用字母数字（openssl rand -hex 16），
#       避免 SQL 字面量转义问题。
# =============================================================
set -euo pipefail

: "${COLLAB_APP_PASSWORD:?COLLAB_APP_PASSWORD 未设置，拒绝执行}"
: "${POSTGRES_USER:?POSTGRES_USER 未设置}"
: "${POSTGRES_DB:?POSTGRES_DB 未设置}"

# WAL 归档目录：卷根归 root，postgres 用户需可写（root 上下文创建；postgres 上下文运行则忽略，由运维一次性 chown）
mkdir -p /backups/wal 2>/dev/null || true
chown postgres:postgres /backups/wal 2>/dev/null || true

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
  -- 1) 专用应用账号（幂等：存在则仅重置密码；非超级用户）
  DO \$\$
  BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'collab_app') THEN
      CREATE ROLE collab_app LOGIN PASSWORD '${COLLAB_APP_PASSWORD}' NOSUPERUSER NOCREATEDB NOCREATEROLE;
    ELSE
      ALTER ROLE collab_app LOGIN PASSWORD '${COLLAB_APP_PASSWORD}';
    END IF;
  END
  \$\$;

  -- 2) 数据库归属应用账号（Alembic 迁移 / 运行时建表以 collab_app 身份）
  ALTER DATABASE "${POSTGRES_DB}" OWNER TO collab_app;

  -- 3) PG15+ public schema 默认收紧 CREATE，显式授予应用账号
  GRANT ALL ON SCHEMA public TO collab_app;
  GRANT ALL ON DATABASE "${POSTGRES_DB}" TO collab_app;
  GRANT TEMPORARY ON DATABASE "${POSTGRES_DB}" TO collab_app;

  -- 4) 监控只读角色（M0-18 postgres_exporter 使用，非超级用户可安全授予）
  GRANT pg_monitor TO collab_app;
EOSQL

echo "[init] collaboration 库应用账号初始化完成: collab_app (非超级用户 + pg_monitor)"
