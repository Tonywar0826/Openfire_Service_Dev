"""配置管理：从环境变量 / .env 读取部署参数。"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """部署管理平台配置。"""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # 部署目录（存放生成的 docker-compose 文件；本机部署模式与宿主机同名 bind mount）
    compose_dir: str = "/Users/yuzhouxiang/ofdm-deploy"

    # 插件资产目录（预置 restapi/httpfileupload/monitoring jar）
    assets_dir: str = "/app/assets"

    # 默认规模：small / medium / large / custom
    scale: str = "small"

    # Openfire
    openfire_image: str = "openfire-openfire:5.1.2"
    openfire_domain: str = "xmpp.collab.local"
    openfire_memory: str = "1g"

    # 端口
    openfire_admin_port: int = 19090
    openfire_c2s_tls_port: int = 15223
    openfire_ws_port: int = 17443

    # 数据库
    openfire_db_password: str = "change-me"

    # 备份目录
    backup_dir: str = "/opt/backup"

    # 协作平台对接配置路径（可选）：设置后配置同步会实际写入/读取协作平台 .env
    # 本机部署：挂载协作平台 backend/.env 的宿主机路径到容器；远程部署经 SSH 由 connector 处理
    collab_env_path: str = ""  # 协作平台 backend/.env 路径（空=不写入，仅生成同步清单）
    collab_nginx_path: str = ""  # 协作平台 nginx web.conf 路径（空=仅核对）


settings = Settings()
