#!/bin/bash
# =============================================================
# Openfire 首次 setup 自动化（一次性）
# 前置：Openfire 容器已启动（admin console 监听 127.0.0.1:19090）
# 作用：跳过 setup 向导的浏览器操作，自动完成语言/主机/数据库/admin 设置。
# 用法：bash setup-openfire.sh <admin密码>
#   （默认 admin 密码 openfire@collab2026，可传参覆盖）
# =============================================================
set -euo pipefail

BASE="${OPENFIRE_BASE:-http://127.0.0.1:19090}"
ADMIN_PASSWORD="${1:-openfire@collab2026}"
XMPP_DOMAIN="${XMPP_DOMAIN:-xmpp.collab.local}"
COOKIE="$(mktemp)"

echo "==> Openfire setup @ $BASE (domain=$XMPP_DOMAIN)"

# 1) 语言选择（zh_CN）
curl -s -c "$COOKIE" -b "$COOKIE" -X POST "$BASE/setup/index.jsp" \
  -d "locale=zh_CN" -o /dev/null

# 2) 主机设置（XMPP 域；端口用默认）
curl -s -c "$COOKIE" -b "$COOKIE" -X POST "$BASE/setup/setup-host-settings.jsp" \
  -d "domain=$XMPP_DOMAIN" \
  -d "xmpp.domain=$XMPP_DOMAIN" \
  -o /dev/null

# 3) 数据库设置（openfire.xml 已预填 PostgreSQL 连接，此处确认标准模式）
#    Openfire 4.x 数据库类型枚举：postgresql
curl -s -c "$COOKIE" -b "$COOKIE" -X POST "$BASE/setup/setup-datasource-settings.jsp" \
  -d "databaseType=postgresql" \
  -o /dev/null

# 4) 管理员设置（邮箱 + 密码）
curl -s -c "$COOKIE" -b "$COOKIE" -X POST "$BASE/setup/setup-admin-settings.jsp" \
  --data-urlencode "email=admin@$XMPP_DOMAIN" \
  --data-urlencode "newPassword=$ADMIN_PASSWORD" \
  --data-urlencode "newPasswordConfirm=$ADMIN_PASSWORD" \
  -o /dev/null

rm -f "$COOKIE"
echo "==> setup 完成。admin 密码: $ADMIN_PASSWORD"
echo "    请在 backend/.env 设置 OPENFIRE_ADMIN_PASSWORD=$ADMIN_PASSWORD"
