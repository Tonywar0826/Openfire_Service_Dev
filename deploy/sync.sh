#!/bin/bash
# =============================================================
# 协作平台「开发 → 线上」一键同步脚本
# 用法：
#   ./deploy/sync.sh            # 前端构建 + 后端镜像重建 + 全量同步
#   ./deploy/sync.sh frontend   # 只同步前端（dist 已构建或重新构建）
#   ./deploy/sync.sh backend    # 只同步后端（rsync 源码 + 重建容器）
#   ./deploy/sync.sh verify     # 只做线上健康检查
#
# 前置：本地已配置免密 SSH（~/.ssh/collab_deploy_ed25519），仓库根目录执行
# =============================================================
set -euo pipefail

# ---- 配置 ----
SERVER="root@47.121.201.246"
SSH_KEY="$HOME/.ssh/collab_deploy_ed25519"
KNOWN_HOSTS="/tmp/collab_known_hosts"
REMOTE_BACKEND="/opt/collaborate/backend"     # 后端源码（docker build 上下文）
REMOTE_DEPLOY="/opt/collaborate/deploy"       # compose / .env.prod / Dockerfile
REMOTE_WEB="/var/www/collab-web"              # 前端静态（nginx root）
COMPOSE="docker compose --env-file .env.prod -f docker-compose.prod.yml"

SSH_OPTS=(-i "$SSH_KEY" -o UserKnownHostsFile="$KNOWN_HOSTS" -o StrictHostKeyChecking=no)
RSYNC_SSH="ssh -i $SSH_KEY -o UserKnownHostsFile=$KNOWN_HOSTS"

# rsync 排除项：本地 .env* 一律不上传（服务器 .env.prod 为唯一事实来源，勿覆盖）
BACKEND_EXCLUDES=(--exclude '.venv' --exclude '__pycache__' --exclude '.pytest_cache'
                  --exclude '*.pyc' --exclude '.env' --exclude '.env.*' --exclude 'tests')

log() { printf '\033[1;36m[%s]\033[0m %s\n' "$(date +%H:%M:%S)" "$*"; }
die()  { printf '\033[1;31m[错误]\033[0m %s\n' "$*" >&2; exit 1; }

# ---------------- 前端 ----------------
sync_frontend() {
  log "① 构建前端 (npm run build) ..."
  (cd web && npm run build) || die "前端构建失败，请检查 web/src 类型错误"
  log "② 同步 dist → 服务器 ${REMOTE_WEB} ..."
  rsync -az --delete -e "$RSYNC_SSH" web/dist/ "${SERVER}:${REMOTE_WEB}/" \
    || die "前端 rsync 失败"
  log "✅ 前端已同步（nginx 即时生效，无需重启）"
}

# ---------------- 后端 ----------------
sync_backend() {
  log "① 同步后端源码 → ${REMOTE_BACKEND} ..."
  rsync -az "${BACKEND_EXCLUDES[@]}" -e "$RSYNC_SSH" backend/ "${SERVER}:${REMOTE_BACKEND}/" \
    || die "后端 rsync 失败"
  log "② 服务器重建后端镜像并滚动重启 ..."
  ssh "${SSH_OPTS[@]}" "$SERVER" "cd ${REMOTE_DEPLOY} && ${COMPOSE} up -d --build backend" \
    || die "后端容器重建失败"
  log "③ 等待就绪 ..."
  sleep 10
  ssh "${SSH_OPTS[@]}" "$SERVER" "docker ps --filter name=collab-backend --format '{{.Names}}: {{.Status}}'" \
    || die "后端状态检查失败"
  # 数据库迁移：容器 CMD 内置 alembic upgrade head，重启即自动应用新迁移
  log "✅ 后端已重建（新迁移已自动应用，若失败请查看 docker logs collab-backend）"
}

# ---------------- 健康检查 ----------------
verify() {
  log "线上健康检查 https://collab.tomes.cn ..."
  curl -sk -o /dev/null -w "  HTTPS        -> %{http_code}\n" https://collab.tomes.cn/
  curl -sk https://collab.tomes.cn/healthz && echo
  # 生产管理员密码从环境变量读取（勿硬编码入库）：未设置则跳过登录检查
  if [ -n "${PROD_ADMIN_PASSWORD:-}" ]; then
    curl -sk -o /dev/null -w "  login        -> %{http_code}\n" \
      -X POST https://collab.tomes.cn/api/v1/auth/login \
      -H "Content-Type: application/json" \
      -d "{\"username\":\"admin\",\"password\":\"${PROD_ADMIN_PASSWORD}\"}"
  else
    log "  login        -> 跳过（未设置 PROD_ADMIN_PASSWORD）"
  fi
  ssh "${SSH_OPTS[@]}" "$SERVER" "docker ps --format '{{.Names}}: {{.Status}}' | sort"
}

# ---------------- 入口 ----------------
case "${1:-all}" in
  frontend) sync_frontend ;;
  backend)  sync_backend ;;
  verify)   verify ;;
  all)
    sync_frontend
    sync_backend
    verify
    ;;
  *) die "用法: $0 [frontend|backend|verify|all]" ;;
esac

log "🎉 完成"
