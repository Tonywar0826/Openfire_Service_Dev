"""备份/恢复 API（P0 占位）。"""
from fastapi import APIRouter

router = APIRouter()


@router.post("/backup", summary="立即备份")
def backup() -> dict:
    """一键备份（DB + 配置 + 卷）（P0：待实现）。"""
    return {"status": "pending", "message": "备份功能待实现（P0 骨架）"}


@router.get("/backups", summary="备份列表")
def list_backups() -> dict:
    """列出历史备份（P0：待实现）。"""
    return {"backups": []}


@router.post("/restore", summary="一键恢复")
def restore(backup_id: str = "") -> dict:
    """从指定备份恢复（P0：待实现）。"""
    return {"status": "pending", "message": "恢复功能待实现", "backup_id": backup_id}
