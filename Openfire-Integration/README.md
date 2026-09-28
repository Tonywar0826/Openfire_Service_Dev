# Openfire ↔ Collaboration 集成 — 设计与部署

> 目录：`collaboration/Openfire Integration/`
> 目标：将 Openfire（XMPP）作为协作平台的 IM 能力引擎集成，功能栏「消息」入口驱动真实 IM。
> 状态：设计中 → 实施中（2026-09-02）

---

## 1. 目标与范围

| 项 | 内容 |
|---|---|
| 集成目标 | 协作平台「消息」功能由 Openfire 承载（单聊、群聊、消息回执），替代原规划的野火 IM |
| 数据边界 | Openfire 仅作 XMPP 引擎；用户主数据、组织、权限仍由协作平台（PostgreSQL `collaboration` 库）维护 |
| 中间件复用 | 复用协作平台已有 PostgreSQL；不再新建 MySQL（原 OpenFire 测试栈的 MySQL 仅作对照，不参与本次集成） |
| 前端 | `/messages` 路由从占位页替换为真实 IM 界面（converse.js 嵌入），功能栏图标沿用 `MessageSquare`（lucide，与其他菜单一致） |

## 2. 架构

```
┌───────────────────────── collaboration 平台 ─────────────────────────┐
│  Web (Vue3, :8080) ── /messages 页面嵌入 converse.js                │
│        │ /api/v1 (nginx 反代)                                        │
│  Backend (FastAPI, :8000)                                            │
│        │  IM 凭证接口 + 用户同步（REST API）                          │
│        ├── PostgreSQL (collaboration 库)  ← 用户主数据                │
│        └── Openfire (XMPP, :9090/:7070/:5222)                        │
│                └── PostgreSQL (openfire 库)  ← XMPP 用户/花名册       │
└──────────────────────────────────────────────────────────────────────┘
```

- **账号模型**：协作平台用户（`collaboration.users`）为主；Openfire 用户（`openfire.ofUser`）为影子账号。
- **JID 规则**：`<username>@xmpp.collab.local`（`username` = 协作平台用户名）。
- **凭证策略**：Openfire 影子账号密码由后端统一生成并加密托管，前端经鉴权后凭平台 JWT 拉取，用户无感登录。

## 3. 组件清单

| 组件 | 来源 | 说明 |
|---|---|---|
| Openfire 4.9.2 | 复用 `openfire-openfire:latest` 镜像（基于 `eclipse-temurin:17-jre` + 官方 tar.gz） | 内置 `postgresql-42.7.2.jar`，可直接连 PostgreSQL |
| PostgreSQL | 复用协作平台 `collab-postgres` | 新增 `openfire` 库 + `openfire` 用户（非超级） |
| converse.js | npm/CDN | 前端 XMPP 客户端，嵌入 `/messages` |
| Openfire REST API 插件 | Openfire Admin Console 安装 | 后端同步用户的通道 |

> 不复用：Redis/RabbitMQ/MinIO（Openfire 不自带这些依赖，XMPP 连接由 Openfire 自管）。

## 4. 数据库（复用 PostgreSQL）

在协作平台 PostgreSQL 上新增独立 schema 归属：

```
database: openfire   (owner: openfire 用户)
user:     openfire   (LOGIN, 密码见 deploy/.env，非超级用户)
```

由 `deploy/postgres/init/02-openfire-user.sh` 幂等创建（与 01-collaboration-app-user.sh 同风格）。

## 5. Openfire 配置（预置 openfire.xml）

- 数据库：`org.postgresql.Driver` → `jdbc:postgresql://postgres:5432/openfire`
- `testSQL=select 1`
- XMPP 域：`xmpp.collab.local`
- 首次启动跳过 setup 向导（`<setup>true</setup>`），admin 账号通过 setup/脚本创建

## 6. 后端集成

### 6.1 新增接口

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/v1/im/credentials` | 返回当前用户 XMPP JID + 密码（无账号则自动创建影子账号） |
| POST | `/api/v1/im/users/sync` | （管理）全量/增量同步协作平台用户到 Openfire |

### 6.2 同步策略

- **创建账号时同步**（`user_service.create_user`）：直接写 Openfire 库 `ofUser` 表创建影子账号（绕过 REST API 插件，不依赖网络），幂等 upsert。
- **懒同步兜底**：请求 IM 凭证时后台再同步一次（`im_service.sync_user_to_openfire`）。
- 同步通道优先级：配置 `OPENFIRE_DATABASE_URL` → 直接写库；否则回退 REST API。
- 密码采用统一派生（`hmac(jwt_secret, username)` 截断 24 位），前端凭证接口与影子账号密码一致，用户无感登录。
- `ofUser.creationDate/modificationDate` 沿用 Openfire 官方初始值 `'0'`（真实时间戳格式 Openfire 解析器无法识别会导致用户加载失败）。
- 用户停用/删除时同步停用 Openfire 账号（事件钩子，后置）。

## 7. 前端集成

- 路由 `/messages`：`PlaceholderView` → `MessagesView.vue`（嵌入 converse.js）。
- converse.js 连接方式：BOSH `/http-bind/`（nginx 同源反代到 `openfire:7070`），避免 CORS。
- 自动登录：页面加载 → `GET /api/v1/im/credentials` → converse.js `login(jid, password)`。
- 功能栏：沿用现有 `menu.messages`（`MessageSquare` 图标 + i18n 键），风格与其他菜单一致。

## 8. 部署

Openfire 已作为主栈服务并入 `deploy/docker-compose.yml`（`openfire` service），一条命令统一编排：

```bash
cd deploy && docker compose up -d --build
```

Openfire 组件划分：应用容器 `collab-openfire`（无法复用，独立）+ 复用主栈 `collab-postgres` 的 `openfire` 库（SQL 复用，不新建）；配置挂载 `Openfire Integration/deploy/openfire.xml`。

暴露端口（宿主机偏移 +10000，避免与既有 OpenFire 测试栈冲突）：`19090`(admin console)、`19091`(secure)、`15222`(c2s)、`15223`(ssl)、`17070`(http-bind)、`17443`(ws)、`17777`(file transfer)。

### 8.1 Openfire 首次 setup（已自动化）

`openfire.xml` 已预置 PostgreSQL 连接与 XMPP 域；首次 setup 由脚本自动完成：

```bash
cd "Openfire Integration/scripts" && python3 setup_openfire.py
```

脚本处理 CSRF + 多步表单（语言→主机→数据库模式→连接→admin）。运行后：
- XMPP 域 `xmpp.collab.local`，数据库复用 `postgres` 的 `openfire` 库（33 张表）
- 影子账号密码 = 后端确定性派生 `HMAC(jwt_secret, username)`（见 `im_service.py`），
  admin 影子账号密码即 `/api/v1/im/credentials` 返回的派生值
- admin console 登录：`admin` / 派生密码（或先在 ofUser 表查 `plainPassword`）

> 已知：脚本设的自定义 admin 密码未生效（Openfire 落库为默认 `admin`），
> 故集成时手动将 `ofUser.admin.plainPassword` 同步为派生密码以对齐 IM 登录。

### 8.2 安装 REST API 插件

Admin Console（`http://localhost:19090`）→ 插件 → 可用插件 → 安装 **REST API**；或手动上传 `.jar`。
安装后在「服务器 → 服务器设置 → REST API」配置 shared secret（对应 `backend/.env` 的 `OPENFIRE_REST_SECRET`）。

## 9. 目录结构

```
Openfire Integration/
├── README.md            # 本文件（设计总览 + 实施记录）
└── deploy/
    └── openfire.xml     # 预置数据库/XMPP 域配置（主栈 openfire service 挂载）
```

> Openfire 服务编排已并入主栈 `deploy/docker-compose.yml`（`openfire` service），不再独立 stack。

> 集成代码直接改在协作平台主仓库（单一事实来源），不在本目录复制副本：

| 改动 | 位置 |
|---|---|
| Openfire 服务编排（openfire service + 卷 + 端口） | `deploy/docker-compose.yml` |
| Openfire 配置（连接串/域/密钥） | `backend/app/core/config.py`（openfire_* 字段） |
| IM 服务（凭证派生 + 影子账号同步） | `backend/app/services/im_service.py` |
| IM 接口（GET /api/v1/im/credentials） | `backend/app/api/routes/im.py`（已注册进 router.py） |
| 前端凭证 API 封装 | `web/src/api/im.ts` |
| IM 界面（converse.js 嵌入） | `web/src/views/messages/MessagesView.vue`（替换 PlaceholderView） |
| 路由改造 | `web/src/router/index.ts`（/messages → MessagesView） |
| converse.js 静态资源（本地化，不依赖 CDN） | `web/public/converse/converse.min.{js,css}` |
| nginx 反代（BOSH/WS → openfire） | `deploy/nginx/web.conf` |
| PostgreSQL openfire 库初始化 | `deploy/postgres/init/02-openfire-user.sh` |

## 10. 待确认 / 风险

- Openfire 首次启动的 admin 账号自动化（setup 向导 vs 预置数据库记录）。
- REST API 插件的安装与 secret 配置。
- 与既有 `openfire` 测试栈（MySQL）并存时的端口冲突（本集成用独立容器名 + 端口偏移 +10000）。
