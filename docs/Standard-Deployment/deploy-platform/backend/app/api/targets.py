"""目标服务器 API：实施人员登记客户服务器 + 连接方式（三种可插拔）。

P0 骨架：内存存储（进程内），后续落库/SQLite。连接测试为占位（真实连接逻辑待实现）。
"""
from typing import Literal, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter()

# 进程内存储（P0 骨架；重启即清空，后续换 SQLite/文件）
_targets: dict[str, dict] = {}

# list 返回时脱敏的字段（密码/密钥/token 不出接口）
_SENSITIVE = {"agent_token", "ssh_password", "ssh_key", "docker_tls_cert"}


class TargetCreate(BaseModel):
    """添加目标服务器请求。connection_type 三选一：agent / ssh / docker_tls。"""

    name: str = Field(..., description="服务器名称（唯一标识）")
    host: str = Field(..., description="IP 或域名")
    connection_type: Literal["agent", "ssh", "docker_tls"] = "agent"

    # Agent 模式
    agent_url: Optional[str] = Field(None, description="Agent 地址，如 https://IP:9443")
    agent_token: Optional[str] = Field(None, description="Agent 令牌")

    # SSH 直连
    ssh_port: int = 22
    ssh_user: Optional[str] = None
    ssh_password: Optional[str] = None
    ssh_key: Optional[str] = None

    # Docker 远程端口
    docker_port: int = 2376
    docker_tls_cert: Optional[str] = None


def _sanitize(t: dict) -> dict:
    """脱敏：隐藏密码/密钥/token 字段。"""
    return {k: ("***" if k in _SENSITIVE and v else v) for k, v in t.items()}


@router.get("/targets", summary="目标服务器列表")
def list_targets() -> dict:
    """返回已登记的目标服务器（敏感字段脱敏）。"""
    return {"targets": [_sanitize(t) for t in _targets.values()]}


@router.post("/targets", summary="添加目标服务器")
def add_target(req: TargetCreate) -> dict:
    data = req.model_dump()
    data["id"] = req.name
    data["status"] = "unknown"
    _targets[req.name] = data
    return {"status": "created", "target": _sanitize(data)}


@router.delete("/targets/{name}", summary="删除目标服务器")
def delete_target(name: str) -> dict:
    if name in _targets:
        del _targets[name]
        return {"status": "deleted"}
    return {"status": "not_found"}


@router.post("/targets/{name}/test", summary="测试连接")
def test_connection(name: str) -> dict:
    """测试到目标服务器的连接（P0 占位：返回连通成功，真实连接逻辑待实现）。"""
    if name not in _targets:
        return {"status": "not_found"}
    t = _targets[name]
    return {
        "status": "ok",
        "message": f"目标服务器「{name}」连接正常（{t['connection_type']}，占位）",
    }


def count_targets() -> int:
    """返回已登记目标服务器数（供状态接口使用）。"""
    return len(_targets)
