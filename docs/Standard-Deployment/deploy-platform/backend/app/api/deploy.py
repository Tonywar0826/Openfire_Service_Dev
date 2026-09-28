"""部署 API：一键部署 / 停止。域名/admin 密码/db 密码/局域网 IP 由部署人员填写。"""
from typing import Literal, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.services import docker_service

router = APIRouter()


class DeployRequest(BaseModel):
    """部署请求参数。四个必填参数由部署人员按客户环境填写。"""

    scale: Literal["small", "medium", "large", "custom"] = "small"
    target_name: Optional[str] = Field(None, description="目标服务器名称（不填则本机）")

    # 必填：客户环境相关
    domain: str = Field(..., description="XMPP 域名（客户提供，如 im.example.com）")
    admin_password: str = Field(..., description="Openfire admin 密码")
    db_password: str = Field(..., description="Openfire 数据库密码")
    lan_ip: str = Field(..., description="局域网 IP（文件上传/coturn 转发地址，按 ipconfig 填）")

    # 可选：coturn（音视频 ICE/TURN），默认值与协作平台前端一致，一般无需改
    coturn_port: int = Field(13478, ge=1024, le=65535, description="coturn STUN/TURN 端口")
    coturn_user: str = Field("collab", description="coturn TURN 静态用户名")
    coturn_password: str = Field("collab@123", description="coturn TURN 静态密码")

    # 可选：custom 模式
    openfire_instances: Optional[int] = Field(None, ge=1, le=50, description="Openfire 实例数（custom）")
    coturn_instances: Optional[int] = Field(None, ge=1, le=50, description="coturn 实例数（custom）")
    database: Optional[Literal["single", "replica", "patroni"]] = None


@router.post("/deploy", summary="一键部署")
def deploy(req: DeployRequest) -> dict:
    """按规模一键部署完整可用的 Openfire 栈到目标服务器（或本机）。

    部署成功后自动执行：①配置同步（Openfire 部署参数 ↔ 协作平台 .env/nginx 逐项校验）
    ②自检校验（容器→服务→功能→Bug 回归逐项状态）。
    """
    from app.api.targets import _targets

    target = _targets.get(req.target_name) if req.target_name else None

    params: dict[str, object] = {
        "openfire_image": "openfire-openfire:5.1.2",
        "domain": req.domain,
        "admin_password": req.admin_password,
        "db_password": req.db_password,
        "lan_ip": req.lan_ip,
        "coturn_port": req.coturn_port,
        "coturn_user": req.coturn_user,
        "coturn_password": req.coturn_password,
    }
    if req.scale == "custom":
        params["openfire_instances"] = req.openfire_instances or 1
        params["coturn_instances"] = req.coturn_instances or 1

    result = docker_service.deploy(target, req.scale, params)

    # 部署成功后：配置同步 + 自检校验
    if result.get("status") == "success":
        from app.config import settings as app_settings
        from app.services.config_sync import run_config_sync
        from app.services.selfcheck import run_selfcheck, summarize

        result["config_sync"] = run_config_sync(
            params, collab_env_path=app_settings.collab_env_path or None
        )
        result["selfcheck"] = run_selfcheck(
            domain=req.domain,
            admin_password=req.admin_password,
            lan_ip=req.lan_ip,
        )
        result["selfcheck_summary"] = summarize(result["selfcheck"])

    return result


@router.post("/deploy/stop", summary="停止服务")
def stop() -> dict:
    """停止最近一次部署（P0 简化：本机）。"""
    return docker_service.stop(None)
