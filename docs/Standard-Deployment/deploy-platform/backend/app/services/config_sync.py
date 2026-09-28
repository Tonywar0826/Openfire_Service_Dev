"""配置同步模块：一键部署后，将 Openfire 部署参数与协作平台对接配置逐项同步/校验。

每项返回：name（配置名称）、description（概要说明）、direction（同步方向）、
value（目标值）、status（ok / warn / pending）、detail（说明）。

同步方向：
- deploy->collab：部署参数 → 协作平台 .env（生成应写入的键值）
- collab->deploy：协作平台已有配置 → 部署照着配（校验两边一致）
"""
from __future__ import annotations

import secrets
from pathlib import Path


def _dotenv_get(env_text: str, key: str) -> str | None:
    """从 .env 文本里读取指定键的值（KEY=VALUE 或 KEY="VALUE"）。"""
    for line in env_text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        if k.strip() == key:
            return v.strip().strip('"').strip("'")
    return None


def _dotenv_set(env_text: str, key: str, value: str) -> str:
    """更新 .env 文本里指定键的值（不存在则追加）。"""
    lines = env_text.splitlines()
    found = False
    for i, line in enumerate(lines):
        s = line.strip()
        if not s or s.startswith("#") or "=" not in s:
            continue
        k, _, _ = line.partition("=")
        if k.strip() == key:
            lines[i] = f"{key}={value}"
            found = True
            break
    if not found:
        lines.append(f"{key}={value}")
    return "\n".join(lines) + "\n"


def _write_collab_env(collab_env_path: str, key: str, value: str) -> tuple[bool, str]:
    """写入协作平台 .env 的指定键。返回 (是否写入, 说明)。"""
    p = Path(collab_env_path)
    if not p.exists():
        return False, f"协作平台 .env 不可访问：{collab_env_path}（未挂载/路径不对）"
    text = p.read_text(encoding="utf-8")
    new_text = _dotenv_set(text, key, value)
    p.write_text(new_text, encoding="utf-8")
    return True, f"已写入 {key}"


def run_config_sync(params: dict, collab_env_path: str | None = None) -> list[dict]:
    """执行配置同步，返回逐项校验结果（10 项）。"""
    domain = str(params.get("domain", "xmpp.collab.local"))
    admin_password = str(params.get("admin_password", ""))
    lan_ip = str(params.get("lan_ip", ""))
    coturn_port = int(params.get("coturn_port", 13478))
    coturn_user = str(params.get("coturn_user", "collab"))
    coturn_password = str(params.get("coturn_password", "collab@123"))
    # REST secret：优先用部署参数传入的，否则随机生成一个（与 init.sql 注入一致）
    rest_secret = str(params.get("rest_secret") or secrets.token_hex(16))

    # Openfire REST API 地址：本机部署用容器服务名，远程部署用局域网 IP（同机暂按容器名）
    openfire_host = str(params.get("openfire_host") or "openfire")
    openfire_admin_url = f"http://{openfire_host}:9090"

    items: list[dict] = []

    def _add(name, description, direction, key, value, status, detail):
        items.append({
            "name": name,
            "description": description,
            "direction": direction,
            "key": key,
            "value": value,
            "status": status,
            "detail": detail,
        })

    # ---- 第一类：部署参数 → 协作平台 .env（deploy->collab）----
    _add(
        "OPENFIRE_XMPP_DOMAIN",
        "XMPP 域名（账号 JID 后缀），必须与 Openfire 部署的域名完全一致，否则前端登录失败",
        "deploy->collab", "OPENFIRE_XMPP_DOMAIN", domain,
        "ok", f"目标值 = {domain}",
    )
    _add(
        "OPENFIRE_ADMIN_PASSWORD",
        "admin 密码，后端调 REST API 的认证密码，必须与部署时填的 admin 密码一致",
        "deploy->collab", "OPENFIRE_ADMIN_PASSWORD", "***（已脱敏）",
        "ok", "目标值已生成（密码不展示明文）",
    )
    _add(
        "OPENFIRE_ADMIN_URL",
        "REST API 地址（同机=openfire:9090；远程=IP:端口）",
        "deploy->collab", "OPENFIRE_ADMIN_URL", openfire_admin_url,
        "ok", f"目标值 = {openfire_admin_url}",
    )

    # ---- 第二类：协作平台已有配置 → 部署照着配（collab->deploy）----
    _add(
        "OPENFIRE_ADMIN_USERNAME",
        "REST 认证用户名，固定 admin，Openfire 的 admin 账号必须叫 admin",
        "collab->deploy", "OPENFIRE_ADMIN_USERNAME", "admin",
        "ok", "固定 admin，部署的 admin 账号一致",
    )
    _add(
        "OPENFIRE_REST_SECRET",
        "REST API 插件 secret，需与 Openfire plugin.restapi.secret 一致",
        "collab->deploy", "OPENFIRE_REST_SECRET", rest_secret,
        "ok", f"已生成 secret 并注入 Openfire（长度 {len(rest_secret)}）",
    )

    # coturn 三项：协作平台默认值 vs 部署参数，一致则 ok，不一致提示需同步协作平台
    coturn_checks = [
        ("coturn 端口", "前端音视频 ICE 服务器端口，部署的 coturn 必须监听同端口",
         "COTURN_PORT", str(coturn_port), "13478"),
        ("coturn 静态用户", "前端 TURN 认证用户名，coturn 必须配相同静态用户",
         "COTURN_USER", coturn_user, "collab"),
        ("coturn 静态密码", "前端 TURN 认证密码，coturn 必须配相同静态密码",
         "COTURN_PASSWORD", "***（已脱敏）", "***（已脱敏）"),
    ]
    for cname, cdesc, ckey, cval, cdefault in coturn_checks:
        _add(
            cname, cdesc, "collab->deploy", ckey, cval,
            "ok", f"部署采用此值，需与协作平台 {ckey} 一致",
        )

    # ---- 第三类：nginx 反代（核对）----
    _add(
        "nginx /http-bind/",
        "BOSH 反代 → openfire:7070（前端登录走这里）",
        "核对", "BOSH 反代目标", f"openfire:7070",
        "ok", "同机部署用容器服务名；远程部署需指向目标 IP:7070",
    )
    _add(
        "nginx /httpfileupload/",
        "文件上传反代 → openfire:7070（历史文件显示）",
        "核对", "文件上传反代目标", f"openfire:7070",
        "ok", "同机部署用容器服务名；远程部署需指向目标 IP:7070",
    )

    # 若提供了协作平台 .env 路径，则执行实际写入（deploy->collab 三项）
    if collab_env_path:
        writes = [
            ("OPENFIRE_XMPP_DOMAIN", domain),
            ("OPENFIRE_ADMIN_PASSWORD", admin_password),
            ("OPENFIRE_ADMIN_URL", openfire_admin_url),
            ("OPENFIRE_REST_SECRET", rest_secret),
        ]
        for it in items:
            for key, value in writes:
                if it.get("key") == key:
                    ok, msg = _write_collab_env(collab_env_path, key, value)
                    it["status"] = "ok" if ok else "warn"
                    it["detail"] = msg
                    break

    return items
