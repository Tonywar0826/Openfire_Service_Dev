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
| `docs/archive/` | 历史设计文档（过程稿，供回溯）|
| `deploy/` | **部署文件包**（Dockerfile、compose、配置、插件、安装包）|
| `Openfire-Integration/` | 集成脚本 + `openfire.xml` 配置 |

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

## 四、部署实施方法

部署文件全部在 `deploy/`，核心文件：

| 文件 | 作用 |
|---|---|
| `openfire.Dockerfile` | Openfire 5.1.2 镜像构建（base eclipse-temurin:17-jre）|
| `openfire_5_1_2.tar.gz` | Openfire 5.1.2 官方安装包（Dockerfile 构建时解压）|
| `docker-compose.yml` | 主编排（含 openfire + openfire-db 独立实例 + coturn 等服务）|
| `docker-compose.monitoring.yml` | 监控栈（Prometheus + Grafana + 探针）|
| `coturn/turnserver.conf` | 音视频 TURN 中继配置 |
| `nginx/web.conf` | Web SPA + BOSH `/http-bind/` 反代 |
| `restAPI-1.12.0.jar` 等 | 插件（REST API / HTTP 上传 / monitoring 归档）|
| `postgres/init/02-openfire-user.sh` | Openfire 独立库初始化 |

**部署前提**：Openfire 依赖一个独立的 PostgreSQL 实例（`openfire-db`），账号同步依赖 REST API 插件，音视频依赖 coturn。

> ⚠️ 环境变量（`.env`）含真实密码，**不在本仓库**。部署时参考 `deploy/.env.example` 自行填写。

---

## 五、对接方式（给协作平台负责人）

1. **账号同步**：协作平台后端调用 Openfire REST API（`/plugins/restapi/v1/users`），建号/改密/禁用/删除时同步影子账号。接口契约见 `docs/Design&Dev/03_接口设计_API规格.md`。
2. **凭证签发**：用户登录后，前端通过 `GET /api/v1/im/credentials` 换取 IM 账号 + 密码，直连 Openfire。链路见 `docs/Design&Dev/03b_服务集成设计.md`。
3. **配置同步**：coturn 端口/账号/密码由协作平台负责人统一配置，Openfire 侧照着配保持一致。

---

## 六、安全提示

- **真实密码/密钥不在本仓库**（`.env` 已排除）。
- **coturn 默认密码 `collab@123` 仅供测试**，生产部署必须改强密码。
- **`openfire.xml` 数据库密码为密文**（Blowfish 加密），解密密钥在 `security.xml`（部署时生成，不在本仓库）。
- 证书仅含**公钥**（`cert.crt`），私钥 `cert.key` 已排除。
