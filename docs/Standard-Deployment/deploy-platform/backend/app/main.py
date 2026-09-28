"""Openfire 部署管理平台 - 后端入口。

P0 骨架：提供 /health 健康检查 + 部署/备份/状态三类 API 路由（占位）。
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import backup, deploy, status, targets

app = FastAPI(
    title="Openfire 部署管理平台",
    description="Openfire 标准化部署与扩展管理平台后端 API",
    version="0.1.0",
)

# 允许前端跨域访问（开发阶段）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(deploy.router, prefix="/api", tags=["部署"])
app.include_router(backup.router, prefix="/api", tags=["备份"])
app.include_router(status.router, prefix="/api", tags=["状态"])
app.include_router(targets.router, prefix="/api", tags=["目标服务器"])


@app.get("/health", tags=["健康检查"])
def health() -> dict:
    """健康检查端点。"""
    return {"status": "ok", "service": "deploy-platform"}
