#!/bin/bash
# =============================================================
# PostgreSQL 初始化 — openfire 库专用账号（幂等）
# Openfire 复用协作平台 PostgreSQL，独立 database + 非超级用户。
# 密码来自容器环境变量 OPENFIRE_DB_PASSWORD（.env → compose）。
# =============================================================
set -euo pipefail

: "${OPENFIRE_DB_PASSWORD:?OPENFIRE_DB_PASSWORD 未设置，拒绝执行}"
: "${POSTGRES_USER:?POSTGRES_USER 未设置}"

OPENFIRE_DB="${OPENFIRE_DB:-openfire}"
OPENFIRE_USER="${OPENFIRE_USER:-openfire}"

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname postgres <<-EOSQL
  -- 1) 专用账号（幂等：存在则仅重置密码；非超级用户）
  DO \$\$
  BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '${OPENFIRE_USER}') THEN
      CREATE ROLE ${OPENFIRE_USER} LOGIN PASSWORD '${OPENFIRE_DB_PASSWORD}' NOSUPERUSER NOCREATEDB NOCREATEROLE;
    ELSE
      ALTER ROLE ${OPENFIRE_USER} LOGIN PASSWORD '${OPENFIRE_DB_PASSWORD}';
    END IF;
  END
  \$\$;

  -- 2) 数据库（幂等：存在则跳过；owner 归 openfire 用户）
  SELECT 'CREATE DATABASE ${OPENFIRE_DB} OWNER ${OPENFIRE_USER} ENCODING ''UTF8'''
  WHERE NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = '${OPENFIRE_DB}')\gexec

  -- 3) 权限
  ALTER DATABASE ${OPENFIRE_DB} OWNER TO ${OPENFIRE_USER};
  GRANT ALL ON DATABASE ${OPENFIRE_DB} TO ${OPENFIRE_USER};
EOSQL

echo "[init] openfire 库初始化完成: ${OPENFIRE_DB} (owner=${OPENFIRE_USER}, 非超级用户)"
