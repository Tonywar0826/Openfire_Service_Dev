"""备份服务：pg_dump + 卷备份 + 恢复（P0 占位）。"""
from __future__ import annotations


class BackupService:
    """备份与恢复。"""

    def backup(self, backup_dir: str) -> dict:
        """备份 DB + 配置 + 卷。"""
        raise NotImplementedError("备份逻辑待实现（P0）")

    def restore(self, backup_id: str) -> dict:
        """从备份恢复。"""
        raise NotImplementedError("恢复逻辑待实现（P0）")

    def list_backups(self, backup_dir: str) -> list[dict]:
        """列出历史备份。"""
        raise NotImplementedError("备份列表待实现（P0）")
