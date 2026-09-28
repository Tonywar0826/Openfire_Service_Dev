# =============================================================
# collaboration-web — 前端镜像
# 用法（在仓库根目录）：
#   1) 先本地构建：cd web && npm ci && npm run build   （生成 web/dist）
#   2) docker build -f deploy/web.Dockerfile -t collaboration-web:dev .
# 说明：dist 为 Vite 构建产物（含 public/converse 本地化 XMPP 客户端资源），
#       由 nginx 托管并反代 /api、/http-bind（Openfire BOSH）、OnlyOffice。
# =============================================================
FROM nginx:1.27-alpine
COPY web/dist /usr/share/nginx/html
COPY deploy/nginx/web.conf /etc/nginx/conf.d/default.conf
COPY deploy/nginx/certs /etc/nginx/certs
EXPOSE 80 443
