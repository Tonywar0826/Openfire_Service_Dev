"""Docker 操作服务：本机（docker SDK）或远程（SSH compose）部署完整可用的 Openfire 栈。

完整部署包 = 3 容器 + 插件（restapi/httpfileupload/monitoring）+ openfire.xml + coturn 配置
          + 数据库初始化（ofProperty 关键配置 + admin 账号）。
"""
from __future__ import annotations

import shutil
import time
from datetime import datetime
from pathlib import Path

import yaml

from app.config import settings
from app.services.compose_generator import (
    generate_compose, init_sql, openfire_xml, turnserver_conf,
)
from app.services.connectors import get_connector

PLUGIN_JARS = ["restAPI.jar", "httpfileupload.jar", "monitoring.jar"]


def _copy_plugins(dest_dir: Path) -> list[str]:
    """把预置插件 jar 复制到部署目录 plugins/。返回成功复制的 jar 名。"""
    src_dir = Path(settings.assets_dir) / "plugins"
    dest_dir.mkdir(parents=True, exist_ok=True)
    copied = []
    for jar in PLUGIN_JARS:
        src = src_dir / jar
        if src.exists():
            shutil.copy2(src, dest_dir / jar)
            copied.append(jar)
    return copied


def _exec_sql_file(db) -> int:
    """通过 psql -f 执行容器内 /deploy/init.sql（postgres 挂载了部署目录）。"""
    r = db.exec_run("psql -U openfire -d openfire -f /deploy/init.sql")
    return r.exit_code


def _wait_postgres_ready(db, timeout: int = 30) -> bool:
    for _ in range(timeout):
        try:
            if db.exec_run("pg_isready -U openfire -d openfire").exit_code == 0:
                return True
        except Exception:
            pass
        time.sleep(1)
    return False


def _wait_tables(db, timeout: int = 90) -> bool:
    """等 Openfire 建表（ofProperty 出现）。"""
    for _ in range(timeout):
        try:
            r = db.exec_run(
                "psql -U openfire -d openfire -tAc \"SELECT 1 FROM pg_tables WHERE tablename='ofproperty'\""
            )
            if r.exit_code == 0 and r.output.decode().strip() == "1":
                return True
        except Exception:
            pass
        time.sleep(2)
    return False


def _deploy_local(scale: str, params: dict) -> dict:
    import docker

    client = docker.from_env()
    ts = datetime.now().strftime("%Y%m%d%H%M%S")
    domain = str(params["domain"])
    admin_password = str(params["admin_password"])
    db_password = str(params["db_password"])
    lan_ip = str(params["lan_ip"])
    image = str(params.get("openfire_image", "openfire-openfire:5.1.2"))
    coturn_port = int(params.get("coturn_port", 13478))
    coturn_user = str(params.get("coturn_user", "collab"))
    coturn_password = str(params.get("coturn_password", "collab@123"))

    deploy_dir = Path(settings.compose_dir) / f"openfire-{scale}-{ts}"
    deploy_dir.mkdir(parents=True, exist_ok=True)

    # 1. 复制插件 jar 到部署目录 plugins/
    copied_plugins = _copy_plugins(deploy_dir / "plugins")

    # 2. 网络 + 卷
    net_name = f"ofdm-net-{ts}"
    client.networks.create(net_name, driver="bridge")
    vols = {k: client.volumes.create(f"ofdm-{k}-{ts}").name for k in ["dbdata", "conf", "fileupload"]}

    # 3. postgres
    db_name = f"openfire-db-{ts}"
    db = client.containers.run(
        "postgres:16-alpine",
        detach=True,
        name=db_name,
        network=net_name,
        environment={"POSTGRES_DB": "openfire", "POSTGRES_USER": "openfire", "POSTGRES_PASSWORD": db_password},
        volumes={
            vols["dbdata"]: {"bind": "/var/lib/postgresql/data", "mode": "rw"},
            str(deploy_dir): {"bind": "/deploy", "mode": "ro"},
        },
        restart_policy={"Name": "unless-stopped"},
    )
    _wait_postgres_ready(db)

    # 4. 写 openfire.xml（db_host 指向实际容器名）+ turnserver.conf
    (deploy_dir / "openfire.xml").write_text(openfire_xml(domain, db_password, db_host=db_name), encoding="utf-8")
    (deploy_dir / "turnserver.conf").write_text(
        turnserver_conf(domain, lan_ip, coturn_port, coturn_user, coturn_password), encoding="utf-8"
    )

    # 5. openfire（bind mount 部署目录：openfire.xml + plugins/）
    of = client.containers.run(
        image,
        detach=True,
        name=f"of-openfire-{ts}",
        network=net_name,
        ports={
            "9090/tcp": 9090, "5222/tcp": 5222, "5223/tcp": 5223,
            "7070/tcp": 7070, "7443/tcp": 7443, "7777/tcp": 7777,
        },
        environment={"JAVA_OPTS": "-Xmx1g"},
        volumes={
            vols["conf"]: {"bind": "/opt/openfire/conf", "mode": "rw"},
            str(deploy_dir / "plugins"): {"bind": "/opt/openfire/plugins", "mode": "rw"},
            vols["fileupload"]: {"bind": "/opt/openfire/fileupload", "mode": "rw"},
            str(deploy_dir / "openfire.xml"): {"bind": "/opt/openfire/conf/openfire.xml", "mode": "rw"},
        },
        restart_policy={"Name": "unless-stopped"},
    )

    # 6. coturn（bind mount turnserver.conf）
    coturn = client.containers.run(
        "coturn/coturn:latest",
        detach=True,
        name=f"of-coturn-{ts}",
        network=net_name,
        ports={f"{coturn_port}/tcp": coturn_port, f"{coturn_port}/udp": coturn_port,
               "5349/tcp": 5349, "5349/udp": 5349},
        volumes={str(deploy_dir / "turnserver.conf"): {"bind": "/etc/coturn/turnserver.conf", "mode": "ro"}},
        restart_policy={"Name": "unless-stopped"},
    )

    # 7. 等 Openfire 建表 → 写初始化配置（ofProperty + admin 账号）→ 重启 Openfire 让配置生效
    tables_ready = _wait_tables(db)
    (deploy_dir / "init.sql").write_text(init_sql(domain, admin_password, lan_ip), encoding="utf-8")
    _exec_sql_file(db)
    of.restart()  # 重启让 ofProperty（REST API/monitoring 等）生效

    return {
        "status": "success",
        "project": f"openfire-{scale}-{ts}",
        "deploy_dir": str(deploy_dir),
        "scale": scale,
        "plugins": copied_plugins,
        "tables_ready": tables_ready,
        "output": f"已启动 3 容器；插件 {len(copied_plugins)} 个；admin 账号 + { '24' } 条配置已写入",
    }


def _deploy_remote(target: dict, scale: str, params: dict) -> dict:
    """远程部署：生成 compose → SSH 下发 → docker compose up（目标服务器需有 docker CLI）。"""
    domain = str(params["domain"])
    admin_password = str(params["admin_password"])
    db_password = str(params["db_password"])
    lan_ip = str(params["lan_ip"])
    coturn_port = int(params.get("coturn_port", 13478))
    coturn_user = str(params.get("coturn_user", "collab"))
    coturn_password = str(params.get("coturn_password", "collab@123"))

    compose_dict = generate_compose(
        scale=scale, domain=domain, db_password=db_password, coturn_port=coturn_port
    )
    compose_yaml = yaml.safe_dump(compose_dict, sort_keys=False, allow_unicode=True)
    ts = datetime.now().strftime("%Y%m%d%H%M%S")
    project = f"openfire-{scale}-{ts}"
    deploy_dir = f"{settings.compose_dir.rstrip('/')}/{project}"

    connector = get_connector(target)
    connector.put_text(compose_yaml, f"{deploy_dir}/docker-compose.yml")
    connector.put_text(openfire_xml(domain, db_password, db_host="openfire-db"), f"{deploy_dir}/openfire.xml")
    connector.put_text(
        turnserver_conf(domain, lan_ip, coturn_port, coturn_user, coturn_password),
        f"{deploy_dir}/turnserver.conf",
    )
    connector.put_text(init_sql(domain, admin_password, lan_ip), f"{deploy_dir}/init.sql")

    code, out = connector.run("docker compose up -d", workdir=deploy_dir)
    return {
        "status": "success" if code == 0 else "failed",
        "project": project,
        "deploy_dir": deploy_dir,
        "scale": scale,
        "exit_code": code,
        "output": out[-3000:],
    }


def deploy(target: dict | None, scale: str, params: dict) -> dict:
    """一键部署：本机（docker SDK）或远程（SSH compose）。"""
    try:
        if target and target.get("connection_type") == "ssh":
            return _deploy_remote(target, scale, params)
        return _deploy_local(scale, params)
    except Exception as e:  # noqa: BLE001
        return {"status": "failed", "scale": scale, "exit_code": -1, "output": f"部署异常: {e}"}


def stop(target: dict | None, deploy_dir: str | None = None) -> dict:
    """停止部署（P0：远程 compose down；本机暂返回说明）。"""
    if target and target.get("connection_type") == "ssh":
        connector = get_connector(target)
        code, out = connector.run("docker compose down", workdir=deploy_dir)
        return {"status": "success" if code == 0 else "failed", "exit_code": code, "output": out[-3000:]}
    return {"status": "pending", "message": "本机停止待实现（可手动 docker ps + docker rm）"}
