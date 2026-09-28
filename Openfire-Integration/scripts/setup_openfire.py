#!/usr/bin/env python3
"""Openfire 4.9 首次 setup 自动化（处理 CSRF + cookie + 多步表单）。

流程：语言 → 主机(XMPP域/端口/加密) → 数据库模式(standard) →
      数据库连接(已从 openfire.xml 预填 PostgreSQL) → admin 账号。
用法：python3 setup_openfire.py [admin密码]  （默认 openfire@collab2026）
"""
import re
import sys
import urllib.parse
import urllib.request
import urllib.error
import http.cookiejar

BASE = "http://127.0.0.1:19090"
ADMIN_PASSWORD = sys.argv[1] if len(sys.argv) > 1 else "openfire@collab2026"
XMPP_DOMAIN = "xmpp.collab.local"
ADMIN_EMAIL = f"admin@{XMPP_DOMAIN}"

# openfire.xml 已预填的 PostgreSQL 连接（与 deploy/openfire.xml 一致）
DB = {
    "driver": "org.postgresql.Driver",
    "serverURL": "jdbc:postgresql://postgres:5432/openfire",
    "username": "openfire",
    "password": "openfireCollab2026",
    "minConnections": "5",
    "maxConnections": "25",
    "connectionTimeout": "1.0",
}

cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
opener.addheaders = [("User-Agent", "Mozilla/5.0 (Macintosh) setup-automation")]

CSRF_RE = re.compile(r'name="csrf"\s+value="([^"]+)"')


def get(url: str) -> str:
    return opener.open(url, timeout=20).read().decode("utf-8", "replace")


def post(url: str, data: dict) -> str:
    body = urllib.parse.urlencode(data).encode()
    return opener.open(urllib.request.Request(url, data=body, method="POST"),
                       timeout=30).read().decode("utf-8", "replace")


def csrf_of(html: str) -> str:
    m = CSRF_RE.search(html)
    if not m:
        raise RuntimeError("未找到 csrf token")
    return m.group(1)


try:
    # Step 0: 语言
    print("==> 语言 zh_CN")
    html = get(f"{BASE}/setup/index.jsp")
    post(f"{BASE}/setup/index.jsp",
         {"csrf": csrf_of(html), "localeCode": "zh_CN", "save": "继续"})

    # Step 1: 主机设置（必须带 continue 提交）
    print("==> 主机设置 (XMPP 域/端口/加密)")
    html = get(f"{BASE}/setup/setup-host-settings.jsp")
    post(f"{BASE}/setup/setup-host-settings.jsp", {
        "csrf": csrf_of(html), "domain": XMPP_DOMAIN, "fqdn": XMPP_DOMAIN,
        "embeddedPort": "9090", "securePort": "9091",
        "restrictAdminLocalhost": "true",
        "encryptionAlgorithm": "Blowfish", "encryptionKey": "",
        "continue": "继续",
    })

    # Step 2a: 数据库模式（standard = 外部数据库）
    print("==> 数据库模式 standard")
    html = get(f"{BASE}/setup/setup-datasource-settings.jsp")
    html = post(f"{BASE}/setup/setup-datasource-settings.jsp",
                {"csrf": csrf_of(html), "mode": "standard", "next": "true"})

    # Step 2b: 数据库连接（字段已由 openfire.xml 预填，原样提交）
    print("==> 数据库连接 (PostgreSQL)")
    data = dict(DB)
    data["csrf"] = csrf_of(html)
    data["continue"] = "继续"
    post(f"{BASE}/setup/setup-datasource-settings.jsp", data)

    # Step 3: admin 账号（password 留空 = 首次设置）
    print("==> 管理员账号")
    html = get(f"{BASE}/setup/setup-admin-settings.jsp")
    post(f"{BASE}/setup/setup-admin-settings.jsp", {
        "csrf": csrf_of(html), "password": "", "email": ADMIN_EMAIL,
        "newPassword": ADMIN_PASSWORD, "newPasswordConfirm": ADMIN_PASSWORD,
        "continue": "继续",
    })

    print(f"\n✓ setup 完成。admin 密码 = {ADMIN_PASSWORD}")
    print(f"  请在 backend/.env 设置 OPENFIRE_ADMIN_PASSWORD={ADMIN_PASSWORD}")
except urllib.error.HTTPError as e:
    print(f"✗ HTTP {e.code}: {e.read().decode('utf-8', 'replace')[:400]}")
    sys.exit(1)
except Exception as e:
    print(f"✗ 失败: {e}")
    sys.exit(1)
