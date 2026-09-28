"""状态 API：查询平台/目标服务器/部署状态。"""
from fastapi import APIRouter

from app.api.targets import count_targets

router = APIRouter()


@router.get("/status", summary="平台状态")
def status() -> dict:
    """返回平台整体状态（目标服务器数、部署状态等）。"""
    return {
        "health": "ok",
        "version": "0.1.0",
        "targets": count_targets(),
        "deployed": False,
        "instances": 0,
        "online_users": 0,
        "database": "未部署",
    }
