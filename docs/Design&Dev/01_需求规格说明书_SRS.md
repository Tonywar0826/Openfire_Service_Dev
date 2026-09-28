# 01 需求规格说明书（SRS）— Openfire IM 服务端

> 版本：v1.0 · 2026-09-20 · 读者：Openfire 开发人员
> 安全红线：所有密码/密钥/连接串一律 `<占位符>`，不写明文。

---

## 1. 引言

### 1.1 目的
本文定义协作平台集成 Openfire 作为 IM 引擎的**功能需求、非功能需求、约束与验收标准**，是后续概要设计、接口设计、安全设计的依据。

### 1.2 范围
- **在范围内**：Openfire 作为 IM 引擎的账号同步、IM 登录认证、单聊/群聊、通讯录、1v1 音视频、消息附件。
- **不在范围内**：多方音视频会议、会议录制、移动离线推送（这三项 Openfire 社区版无内置能力，见 02 概要设计 §能力缺口）。

### 1.3 背景
PRD（mindful-collaboration）原指定「野火 IM 商业版」作 IM 引擎，现已**统一替换为 Openfire 5.1.2**（社区版）。Openfire 是标准 XMPP 服务器，作为协作平台的「能力引擎」，只执行消息/音视频能力，不维护企业主数据与权限。

---

## 2. 需求背景与目标

### 2.1 目标
让协作平台的用户能用一套账号（平台账号）完成 IM 能力：登录后即自动连上 IM，能单聊、建群、看通讯录、打 1v1 音视频，且离职/停用后**立即失去 IM 登录能力**。

### 2.2 核心原则（架构性需求，不可违背）
1. **平台是账号主数据**，Openfire 是影子账号（跟着平台同步，不反向）。
2. **只通过 REST API 对接 Openfire，禁止直连 Openfire 数据库**（PRD 约束 1）。
3. **同步失败不阻塞平台主流程**（建号/登录不能因 Openfire 不可用而失败），失败仅告警 + 可重试。

---

## 3. 功能需求（FR）

| 编号 | 需求 | 说明 | 优先级 |
|---|---|---|---|
| FR-1 | 账号同步 | 平台建号/改密/改资料/禁用/删除/恢复时，同步到 Openfire 影子账号 | P0 |
| FR-2 | IM 登录认证 | 前端经 BOSH + SASL SCRAM-SHA-1 登录 Openfire，用平台账号密码 | P0 |
| FR-3 | 单聊 | 用户间一对一消息（文本/图片/文件/表情） | P0 |
| FR-4 | 群聊 MUC | 建群/拉人/退群/群设置，域 `conference.xmpp.collab.local` | P0 |
| FR-5 | 全员通讯录 | 所有在职用户互为双向好友（roster，sub=3） | P0 |
| FR-6 | 1v1 音视频 | Jingle 信令 + WebRTC 媒体 + coturn 中转 | P0 |
| FR-7 | 消息附件 | XEP-0363 HTTP 文件上传 | P1 |
| FR-8 | 账号生命周期 | 离职/停用用户**立即**失去 IM 登录能力（删影子账号） | P0 |
| FR-9 | 消息归档（历史记录同步） | 消息内容服务端归档（MAM/XEP-0313），换设备登录自动拉取历史 | P1 |

### FR 详述（关键两条）

**FR-1 账号同步**：平台后端在以下事件触发时调用 Openfire REST API：
- 建号 → `POST /users`
- 改密/重置密码 → `PUT /users/{username}`
- 改姓名/邮箱 → `PUT /users/{username}`
- 停用/离职 → `DELETE /users/{username}`（删影子账号）
- 恢复在职 → `POST /users`（重建影子账号）

**FR-8 账号生命周期**：离职（status=2）删影子账号 + 清 Redis 密码缓存；停用（status=0）删影子账号但保留缓存密码（便于恢复）；恢复在职（status=1）从缓存取回密码重建影子账号。缓存过期（24h 无密码）则需管理员重置密码后重建。

---

## 4. 非功能需求（NFR）

| 编号 | 类别 | 需求 | 指标 |
|---|---|---|---|
| NFR-1 | 性能 | IM 登录 | BOSH 登录延迟 < 1s（探针实测 29ms） |
| NFR-2 | 性能 | 消息吞吐 | 支持平台全部在线用户（初期 < 200 并发） |
| NFR-3 | 安全 | 密码存储 | ofUser 用 encryptedPassword（Blowfish 可逆），Redis 加 requirepass |
| NFR-4 | 安全 | 传输加密 | 明文端口全关，仅 TLS/HTTPS；SASL 用 SCRAM-SHA-1 |
| NFR-5 | 可用性 | 故障隔离 | Openfire 用独立 postgres 实例，维护/故障不影响平台主库 |
| NFR-6 | 可用性 | 高可用 | 数据层 HA（postgres 主从）；IM 节点可横向扩展（P1） |
| NFR-7 | 可维护性 | 可观测 | 全链路监控（容器/DB/探针）+ 结构化日志 |
| NFR-8 | 可维护性 | 可追溯 | 账号操作留痕（平台审计日志 + Openfire 安全审计） |

---

## 5. 约束

| 约束 | 内容 |
|---|---|
| C-1 | **禁止直接读写 Openfire 数据库**（PRD 约束 1），一切账号操作走 REST API |
| C-2 | Openfire 为社区版，**无** 多方会议/录制/离线推送/官方 SDK 能力 |
| C-3 | 平台不存 IM 消息内容；消息归档（历史记录跨设备同步）由 Openfire **monitoring 插件**负责（MAM/XEP-0313） |
| C-4 | XMPP 域固定 `xmpp.collab.local`，JID = `<用户名小写>@xmpp.collab.local` |
| C-5 | Openfire 5.1.2 用 REST API 插件 **1.12.0**（minServerVersion 5.0.0） |

---

## 6. 验收标准

| 编号 | 验收项 | 通过标准 |
|---|---|---|
| AC-1 | 账号同步 | 平台建号 → Openfire ofUser 出现对应账号（encryptedPassword 非空） |
| AC-2 | IM 登录 | 平台账号密码能经 BOSH SASL 登录成功（`<success/>`） |
| AC-3 | 消息收发 | 两账号互发消息，对方实时收到 |
| AC-4 | 通讯录 | 新账号与所有在职用户双向好友（ofRoster sub=3） |
| AC-5 | 离职断 IM | 停用/离职后，该账号 BOSH 登录返回 `<not-authorized/>` |
| AC-6 | 恢复在职 | 恢复后（24h 内）影子账号重建，BOSH 登录恢复成功 |
| AC-7 | 音视频 | 1v1 通话信令（Jingle）与媒体（WebRTC+coturn）建立成功 |
| AC-8 | 消息归档 | 消息落 `ofMessageArchive` 表；换设备登录 converse 自动拉取历史记录 |
