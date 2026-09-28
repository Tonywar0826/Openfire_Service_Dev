#!/usr/bin/env python3
"""IM 黑盒探针：BOSH 登录测试 + 推结果到 pushgateway。

用法：/usr/local/bin/python3.11 im_probe.py
产出的指标：im_login_success（0/1）、im_login_latency_seconds
"""
import base64, re, sys, time, urllib.request

DOMAIN = "xmpp.collab.local"
BOSH = "http://localhost:8080/http-bind/"
PUSHGATEWAY = "http://localhost:19091"
USER = "yuzhouxiang"
PASSWORD = "admin123"


def bosh_login(user, pwd):
    rid = 0

    def post(inner, sid=None):
        nonlocal rid
        rid += 1
        a = (f'xmlns="http://jabber.org/protocol/httpbind" rid="{rid}" to="{DOMAIN}" '
             f'wait="60" hold="1" content="text/xml; charset=utf-8" ver="1.6" '
             f'xmpp:version="1.0" xmlns:xmpp="urn:xmpp:xbosh"')
        if sid:
            a += f' sid="{sid}"'
        req = urllib.request.Request(
            BOSH, data=f"<body {a}>{inner}</body>".encode(),
            headers={"Content-Type": "text/xml; charset=utf-8"})
        return urllib.request.urlopen(req, timeout=10).read().decode(errors="replace")

    r1 = post("")  # session create
    m = re.search(r'sid="([^"]+)"', r1)
    if not m:
        return False, "no sid"
    sid = m.group(1)
    auth = base64.b64encode(b"\x00" + user.encode() + b"\x00" + pwd.encode()).decode()
    r2 = post(f'<auth xmlns="urn:ietf:params:xml:ns:xmpp-sasl" mechanism="PLAIN">{auth}</auth>', sid)
    return "<success" in r2, r2[:200]


def push_metric(name, value):
    body = f"{name} {value}\n".encode()
    req = urllib.request.Request(
        f"{PUSHGATEWAY}/metrics/job/im_probe", data=body, method="POST")
    urllib.request.urlopen(req, timeout=10)


def main():
    t0 = time.time()
    ok, detail = bosh_login(USER, PASSWORD)
    latency = time.time() - t0
    push_metric("im_login_success", 1 if ok else 0)
    push_metric("im_login_latency_seconds", round(latency, 3))
    if not ok:
        # 成功静默（不刷屏），失败才输出告警
        print(f"❌ IM 登录失败 latency={latency:.2f}s detail={detail}")


if __name__ == "__main__":
    main()
