# Openfire IM 服务 — 设计文档 + 部署实施包

> 本仓库是协作平台 **Openfire IM 服务**的完整交付物，面向**协作平台负责人**。
> 内容：设计文档、部署实施方法、部署文件包（含安装包与插件）。

---

## 一、这是什么

Openfire 是协作平台的 IM 引擎（开源 XMPP 协议，野火 IM 的替换方案），提供：

- **单聊 / 群聊**（MUC）
- **1v1 音视频通话**（Jingle 信令 + WebRTC 媒体 + coturn 中继）
- **文件上传**（HTTP File Upload）
- **历史消息归档**（MAM / XEP-0313）

Openfire 作为协作平台的**可插拔独立服务**，通过两条标准通道对接：

| 通道 | 协议 | 用途 |
|---|---|---|
| REST API | HTTP（`/plugins/restapi/v1`）| 账号增删改查、通讯录管理（后端调用）|
| XMPP | BOSH（`/http-bind/`）| 消息、群聊、通话、文件、在线状态（前端直连）|

**解耦边界**：Openfire 与协作平台不共享数据库（独立 postgres 实例）、不共享认证（两条独立认证链）、不直连数据库（账号同步全走 REST API）。详见 `docs/Design&Dev/02_概要设计_HLD.md` §1.5。

---

## 二、目录结构

| 目录 | 内容 |
|---|---|
| `docs/Design&Dev/` | **标准设计文档集**（00–08），从需求到缺陷跟踪 |
| `docs/Standard-Deployment/` | Openfire **标准化部署平台**（设计 + 代码，一键部署）|
| `deploy/` | **部署文件包**（见下方「安装 Openfire 服务」）|
| `Openfire-Integration/` | 集成脚本 + UI 设计稿 |

`deploy/` 下的关键文件：

| 文件 | 作用 |
|---|---|
| `docker-compose.yml` | **Openfire 服务编排**（openfire + openfire-db + coturn 三容器，安装用这个）|
| `docker-compose.collab-full.yml` | 协作平台**完整编排参考**（含 backend/web 等，源码由协作平台负责人维护）|
| `docker-compose.monitoring.yml` | 监控栈（Prometheus + Grafana + 探针）|
| `openfire.Dockerfile` + `openfire_5_1_2.tar.gz` | Openfire 5.1.2 镜像构建 |
| `openfire.xml` | Openfire 核心配置（数据库连接 + XMPP 域）|
| `coturn/turnserver.conf` | 音视频 TURN 中继配置 |
| `nginx/web.conf` | Web SPA + BOSH `/http-bind/` 反代配置 |
| `restAPI-1.12.0.jar` 等 | 插件（REST API / HTTP 上传 / monitoring 归档）|

---

## 三、设计文档阅读顺序

| 编号 | 文档 | 回答的问题 |
|---|---|---|
| 00 | 文档索引与变更历史 | 有哪些文档、怎么读 |
| 01 | 需求规格说明书（SRS）| 要做什么、验收标准 |
| 02 | 概要设计（HLD）| 整体怎么搭、解耦边界、能力映射 |
| 03 | 接口设计（API 规格）| 账号同步接口精确契约 |
| 03b | 服务集成设计 | Openfire 各组件如何被调用（REST API vs XMPP）|
| 04 | 安全设计 | 认证/加密/授权 |
| 05 | 服务验证与功能测试规格 | 怎么测、判定标准 |
| 06 | 测试报告 | 测出什么结果 |
| 07 | 缺陷跟踪表 | 缺陷的统一登记与跟踪 |
| 08 | 待办事项清单 | 还有哪些事要做 |

---

## 四、安装 Openfire 服务

> 前提：目标机器已安装 **Docker + Docker Compose**。

### 第 1 步：配置密码（两处改成同一个强密码）

```bash
cd deploy
cp .env.example .env
```

编辑两个文件，把数据库密码改成**同一个强密码**：

1. `.env` 里的 `OPENFIRE_DB_PASSWORD=...`
2. `openfire.xml` 里的 `<password>...</password>`

> 两处必须一致：`.env` 决定数据库（openfire-db）的密码，`openfire.xml` 决定 Openfire 连数据库用的密码。

### 第 2 步：构建 Openfire 镜像（一次性，约 1–2 分钟）

```bash
cd deploy
docker build -f openfire.Dockerfile -t openfire-openfire:5.1.2 .
```

### 第 3 步：启动服务（3 个容器）

```bash
cd deploy
docker compose up -d
```

启动三个容器：`openfire`（IM 引擎）、`openfire-db`（独立数据库）、`coturn`（音视频中继）。

### 第 4 步：验证

```bash
docker compose ps                          # 3 个容器都应 Up
curl -I http://localhost:19090/            # 管理台，返回 200
```

- **管理台**：http://localhost:19090 （首次默认账号 `admin` / 密码 `admin`，登录后立即修改）
- **REST API**：`curl -u admin:admin http://localhost:19090/plugins/restapi/v1/users`
- **插件**：需将 `restAPI.jar` 等插件放入 `openfire_plugins` 卷后重启（详见 03b 服务集成设计）

> **BOSH 说明**：Openfire 的 BOSH 端口（7070）不映射宿主机，前端接入需经 nginx `/http-bind/` 反代（配置见 `nginx/web.conf`，接入细节见 `docs/Design&Dev/03b_服务集成设计.md`）。

---

## 五、对接方式（给协作平台负责人）

1. **账号同步**：协作平台后端调用 Openfire REST API（`/plugins/restapi/v1/users`），建号/改密/禁用/删除时同步影子账号。接口契约见 `docs/Design&Dev/03_接口设计_API规格.md`。
2. **凭证签发**：用户登录后，前端通过 `GET /api/v1/im/credentials` 换取 IM 账号 + 密码，直连 Openfire。链路见 `docs/Design&Dev/03b_服务集成设计.md`。
3. **配置同步**：coturn 端口/账号/密码由协作平台负责人统一配置，Openfire 侧照着配保持一致。

---

## 六、安全提示

- **真实密码/密钥不在本仓库**（`.env` 已排除，`openfire.xml` 密码为占位符）。
- **数据库密码**：部署时 `.env` 与 `openfire.xml` 两处必须改成同一强密码。
- **管理台**：首次登录 `admin/admin`，立即改密码；生产环境建议启用 HTTPS（9091）与 Blowfish 密码加密（见 `docs/Design&Dev/04_安全设计.md`）。
- **coturn 默认密码 `collab@123` 仅供测试**，生产部署必须改强密码。
- 证书仅含**公钥**（`cert.crt`），私钥 `cert.key` 已排除。
