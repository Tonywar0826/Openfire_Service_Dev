"""compose 生成器：按规模生成 Openfire 部署栈的配置（openfire.xml / coturn / 初始化 SQL）。"""
from __future__ import annotations

import secrets

import yaml


def openfire_xml(domain: str, db_password: str, db_host: str = "openfire-db") -> str:
    """生成 openfire.xml（连 postgres、跳过安装向导）。db_host 为 postgres 容器名。

    参照已验证的协作平台 openfire.xml：含 connectionProvider/adminConsole/locale/testSQL，
    保证 Openfire 能正确初始化数据库连接池 + 首次自动建表。密码 P0 用明文（P1 改 Blowfish 加密）。
    """
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<jive>
  <adminConsole>
    <port>9090</port>
    <securePort>9091</securePort>
  </adminConsole>
  <locale>zh_CN</locale>
  <connectionProvider>
    <className>org.jivesoftware.database.DefaultConnectionProvider</className>
  </connectionProvider>
  <database>
    <defaultProvider>
      <driver>org.postgresql.Driver</driver>
      <serverURL>jdbc:postgresql://{db_host}:5432/openfire</serverURL>
      <username>openfire</username>
      <password>{db_password}</password>
      <testSQL>select 1</testSQL>
      <testBeforeUse>false</testBeforeUse>
      <testAfterUse>false</testAfterUse>
      <minConnections>5</minConnections>
      <maxConnections>25</maxConnections>
      <connectionTimeout>1.0</connectionTimeout>
    </defaultProvider>
  </database>
  <setup>true</setup>
  <fqdn>{domain}</fqdn>
</jive>
'''


def turnserver_conf(
    domain: str,
    lan_ip: str,
    port: int = 13478,
    user: str = "collab",
    password: str = "collab@123",
) -> str:
    """生成 coturn 配置：realm + external-ip + 静态用户，端口/用户/密码与协作平台前端一致。

    端口/用户/密码由部署参数提供（默认与协作平台 .env 的 coturn_* 一致），
    保证前端 iceServers 能连通此 coturn 中继。
    """
    return f'''listening-port={port}
tls-listening-port=5349
fingerprint
realm={domain}
external-ip={lan_ip}
listening-ip=0.0.0.0
min-port=59160
max-port=59200
user={user}:{password}
'''


def init_sql(domain: str, admin_password: str, lan_ip: str, restapi_secret: str | None = None) -> str:
    """生成 Openfire 初始化 SQL：ofProperty 关键配置 + admin 账号（只保留 admin）。

    参照协作平台已验证的 ofProperty 清单（26 条中的关键 24 条）。
    secret / masterkey / passwordKey 等运行时密钥：secret 用随机值注入，其余由 Openfire 自动生成。
    """
    secret = restapi_secret or secrets.token_hex(16)
    # MUC cache 的 name 含单引号，SQL 里转义为 ''
    return f'''-- Openfire 一键部署初始化（自动写入）
-- 注：cache.* 系列由 Openfire/插件启动时自动生成，此处不预置（避免 duplicate key）
INSERT INTO ofproperty (name, propvalue) VALUES
('admin.authorizedJIDs', 'admin@{domain}'),
('adminConsole.access.allow-wildcards-in-excludes', 'true'),
('conversation.database.jid-columns-have-been-migrated', 'true'),
('conversation.messageArchiving', 'true'),
('conversation.metadataArchiving', 'true'),
('conversation.roomArchiving', 'true'),
('conversation.roomArchivingStanzas', 'true'),
('locale', 'zh_CN'),
('plugin.restapi.enabled', 'true'),
('plugin.restapi.httpAuth', 'basic'),
('plugin.restapi.secret', '{secret}'),
('plugin.restapi.serviceLoggingEnabled', 'false'),
('setup', 'true'),
('xmpp.domain', '{domain}'),
('xmpp.fqdn', '{domain}'),
('xmpp.httpbind.client.idle', '1800')
ON CONFLICT (name) DO NOTHING;

-- admin 账号（只保留 admin）
INSERT INTO ofuser (username, plainpassword, encryptedpassword, name, email, creationdate, modificationdate)
VALUES ('admin', '{admin_password}', NULL, 'Administrator', 'admin@{domain}', '0', '0')
ON CONFLICT (username) DO NOTHING;
'''


def generate_compose(
    scale: str = "small",
    openfire_image: str = "openfire-openfire:5.1.2",
    domain: str = "xmpp.collab.local",
    db_password: str = "openfire",
    openfire_instances: int = 1,
    coturn_instances: int = 1,
    coturn_port: int = 13478,
) -> dict:
    """生成 Openfire 部署栈 compose 结构（dict，由调用方 dump 成 YAML）。

    远程 SSH 部署用：目标服务器有 docker CLI 时，下发 compose 文件 + docker compose up。
    """
    return {
        "services": {
            "openfire-db": {
                "image": "postgres:16-alpine",
                "container_name": "openfire-db",
                "environment": {
                    "POSTGRES_DB": "openfire",
                    "POSTGRES_USER": "openfire",
                    "POSTGRES_PASSWORD": db_password,
                },
                "volumes": ["openfire_dbdata:/var/lib/postgresql/data"],
                "healthcheck": {
                    "test": ["CMD-SHELL", "pg_isready -U openfire -d openfire"],
                    "interval": "10s",
                    "timeout": "5s",
                    "retries": 5,
                },
                "restart": "unless-stopped",
                "networks": ["openfire-net"],
            },
            "openfire": {
                "image": openfire_image,
                "container_name": "openfire",
                "ports": [
                    "9090:9090", "5222:5222", "5223:5223",
                    "7070:7070", "7443:7443", "7777:7777",
                ],
                "volumes": [
                    "openfire_conf:/opt/openfire/conf",
                    "openfire_plugins:/opt/openfire/plugins",
                    "openfire_fileupload:/opt/openfire/fileupload",
                    "./openfire.xml:/opt/openfire/conf/openfire.xml",
                ],
                "environment": {"JAVA_OPTS": "-Xmx1g"},
                "depends_on": {"openfire-db": {"condition": "service_healthy"}},
                "restart": "unless-stopped",
                "networks": ["openfire-net"],
            },
            "coturn": {
                "image": "coturn/coturn:latest",
                "container_name": "coturn",
                "ports": [
                    f"{coturn_port}:{coturn_port}", f"{coturn_port}:{coturn_port}/udp",
                    "5349:5349", "5349:5349/udp",
                    "59160-59200:59160-59200/udp",
                ],
                "volumes": ["./turnserver.conf:/etc/coturn/turnserver.conf"],
                "restart": "unless-stopped",
                "networks": ["openfire-net"],
            },
        },
        "volumes": {
            "openfire_dbdata": {},
            "openfire_conf": {},
            "openfire_plugins": {},
            "openfire_fileupload": {},
        },
        "networks": {"openfire-net": {"driver": "bridge"}},
    }
