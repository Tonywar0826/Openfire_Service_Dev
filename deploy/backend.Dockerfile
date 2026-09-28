# =============================================================
# collaboration-backend 生产镜像
# 构建：docker build -f deploy/backend.Dockerfile -t collaboration-backend:prod backend/
# 启动：uvicorn app.main:app（容器内由 compose command 控制，先跑 alembic upgrade head）
# =============================================================
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /srv/app

# 依赖安装（利用缓存分层：pyproject 不变则不重装；
# 阿里云服务器访问 files.pythonhosted.org 常超时，改用阿里云 PyPI 镜像 + 超时/重试）
# 注意：阿里云 PyPI 为国内源，直连更快；清空 daemon 继承的代理环境变量，避免绕行 mihomo 代理失败
ARG PIP_INDEX=https://mirrors.aliyun.com/pypi/simple/
# 容器直连外网 TLS 会被宿主机 Clash TUN 干扰（SSLError UNEXPECTED_EOF），
# 默认经宿主 Clash 代理 host.docker.internal:7890 下载；无需代理时构建传 --build-arg HTTP_PROXY= 清空。
ARG HTTP_PROXY=http://host.docker.internal:7890
ARG HTTPS_PROXY=http://host.docker.internal:7890
ARG http_proxy=http://host.docker.internal:7890
ARG https_proxy=http://host.docker.internal:7890
ARG ALL_PROXY=http://host.docker.internal:7890
ARG NO_PROXY=localhost,127.0.0.1
ENV HTTP_PROXY=$HTTP_PROXY \
    HTTPS_PROXY=$HTTPS_PROXY \
    http_proxy=$http_proxy \
    https_proxy=$https_proxy \
    ALL_PROXY=$ALL_PROXY \
    NO_PROXY=$NO_PROXY \
    no_proxy=$NO_PROXY
COPY pyproject.toml README.md ./
RUN pip install --no-cache-dir --timeout 120 --retries 6 -i "$PIP_INDEX" --upgrade pip && \
    pip install --no-cache-dir --timeout 120 --retries 6 -i "$PIP_INDEX" .

# 应用代码（含 Alembic 迁移脚本）
COPY alembic.ini ./
COPY alembic ./alembic
COPY app ./app

# 非 root 运行
RUN useradd -m -u 10001 appuser && chown -R appuser:appuser /srv/app
USER appuser

EXPOSE 8000

# 生产入口：先迁移再启动（compose 中可用 command 覆盖，如加 --workers）
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
