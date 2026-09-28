# Openfire 对接设计与架构（含 API 详细清单）

> 版本：2026-09-19 · 适用：Openfire 5.1.2 + REST API 插件 1.12.0
> 读者：协作平台负责人（对接方）+ Openfire IM 测试/部署负责人
> 安全红线：所有密码/密钥用 `<占位符>` 表示，不写明文。

---

## 一、对接架构

### 1.1 整体架构

```
协作平台后端 (FastAPI)
   │  建号/改密/禁用/删除/重置密码
   │  HTTP 调用 REST API
   ▼
Openfire REST API 插件
   │  (/plugins/restapi/v1/...)
   ▼
Openfire 用户库 (ofUser) + 通讯录 (ofRoster)
```

### 1.2 角色边界

| 角色 | 职责 |
|---|---|
| 协作平台 | 账号**主数据**，权限/ACL 的唯一权威；对用户做增删改时同步到 Openfire |
| Openfire | IM **影子账号**，只做消息收发能力执行，不维护主数据、不维护权限 |

### 1.3 核心原则

1. **只通过 REST API 调 Openfire，禁止直连 Openfire 数据库**（遵循 PRD 约束 1）。
2. 平台是账号主数据，Openfire 是影子账号（跟着同步）。
3. 同步失败**不阻塞平台主流程**，只告警 + 重试/对账补同步。

---

## 二、API 详细清单

### 2.1 接口总览

> 完整路径前缀：`http://<Openfire地址>:<管理台端口>/plugins/restapi/v1`（本文简称 `/users` 等）。

| # | 方法 + 路径 | 用途 | 平台触发时机 |
|---|---|---|---|
| 1 | `POST /users` | 创建 IM 账号 | 平台建新用户 |
| 2 | `GET /users/{username}` | 查询账号是否存在 | 校验/对账 |
| 3 | `PUT /users/{username}` | 修改密码/资料 | 改密、重置密码、改姓名邮箱 |
| 4 | `DELETE /users/{username}` | 删除账号 | 用户离职/注销 |
| 5 | `POST /users/{username}/roster` | 加联系人（通讯录） | 建双向通讯录关系 |
| 6 | `GET /users/{username}/roster` | 查询联系人 | 对账/排障 |
| 7 | `GET /sessions` | 查询在线会话 | 排障/监控（可选） |

### 2.2 认证方式（两种，二选一）

| 方式 | 怎么传 | 适用 |
|---|---|---|
| HTTP Basic Auth | 请求头 `Authorization: Basic <base64(admin:密码)>`，即 `curl -u "admin:密码"` | 简单，管理台账号 |
| Secret Key（推荐） | 请求头 `Authorization: <secretKey>`，secretKey 在插件配置 `plugin.restapi.secretKey` 设置 | 避免暴露 admin 弱口令 |

### 2.3 接口详细定义

#### 接口 1：创建用户

- **请求**：`POST /users`
- **请求体**（JSON）：

```json
{
  "username": "zhangsan",          // 必填，唯一，建议全小写、无空格
  "name": "张三",                   // 可选，显示名
  "email": "zs@example.com",        // 可选
  "password": "<明文密码>"          // 必填，Openfire 内部加密存储
}
```

- **成功响应**：`HTTP 201 Created`
- **失败响应**：`409`（用户名已存在）、`400`（缺字段/格式错）、`401`（认证失败）
- **curl 示例**：

```bash
curl -u "admin:<ADMIN_PWD>" -H "Content-Type: application/json" \
  -X POST http://localhost:19090/plugins/restapi/v1/users \
  -d '{"username":"zhangsan","name":"张三","email":"zs@example.com","password":"<测试密码>"}'
```

> ⚠️ `username` 必须全小写、无空格：Openfire 认证会 `trim().toLowerCase()` 后精确查库，大写或空格会导致「密码正确却登录失败」。

#### 接口 2：查询用户

- **请求**：`GET /users/{username}`
- **成功响应**：`200`，返回该用户信息 JSON
- **失败响应**：`404`（不存在）、`401`
- **curl**：`curl -u "admin:<ADMIN_PWD>" http://localhost:19090/plugins/restapi/v1/users/zhangsan`

#### 接口 3：修改用户

- **请求**：`PUT /users/{username}`，请求体只传要改的字段：

```json
{ "password": "<新密码>" }                          // 改密
{ "name": "张三丰", "email": "zsf@example.com" }    // 改资料
```

- **成功响应**：`200`；**失败**：`404`（不存在）、`401`
- **curl**：`curl -u "admin:<ADMIN_PWD>" -H "Content-Type: application/json" -X PUT http://localhost:19090/plugins/restapi/v1/users/zhangsan -d '{"password":"<新密码>"}'`

#### 接口 4：删除用户

- **请求**：`DELETE /users/{username}`
- **成功响应**：`200`；**失败**：`404`、`401`
- **curl**：`curl -u "admin:<ADMIN_PWD>" -X DELETE http://localhost:19090/plugins/restapi/v1/users/zhangsan`

#### 接口 5：加联系人（roster）

- **请求**：`POST /users/{username}/roster`

```json
{
  "jid": "lisi@test.xmpp.collab.local",  // 对方的 JID（用户名@域）
  "nickname": "李四",                     // 显示昵称
  "subscriptionType": "3"                // 3=双向(both)，见下表
}
```

- **subscriptionType 取值**：

| 值 | 含义 |
|---|---|
| -1 | 移除该联系人 |
| 0 | 无订阅 |
| 1 | 对方订阅我 |
| 2 | 我订阅对方 |
| 3 | **双向订阅（both）** ← 全员通讯录用这个 |

- **成功响应**：`201`；**失败**：`404`（用户不存在）、`401`
- **curl**：`curl -u "admin:<ADMIN_PWD>" -H "Content-Type: application/json" -X POST http://localhost:19090/plugins/restapi/v1/users/zhangsan/roster -d '{"jid":"lisi@test.xmpp.collab.local","nickname":"李四","subscriptionType":"3"}'`

> 双向通讯录 = 对 A 加 B（subscriptionType=3）+ 对 B 加 A（subscriptionType=3），各调一次。

#### 接口 6：查询联系人

- **请求**：`GET /users/{username}/roster` → `200` + roster 列表 JSON
- **curl**：`curl -u "admin:<ADMIN_PWD>" http://localhost:19090/plugins/restapi/v1/users/zhangsan/roster`

#### 接口 7：在线会话（可选）

- **请求**：`GET /sessions` → `200` + 在线会话列表 JSON
- **curl**：`curl -u "admin:<ADMIN_PWD>" http://localhost:19090/plugins/restapi/v1/sessions`

---

## 三、账号同步逻辑（平台后端实现的触发规则）

| 平台事件 | 调用的接口 | 说明 |
|---|---|---|
| 创建用户 | `POST /users` | 同步用户名（小写）+姓名+邮箱+密码（落 encryptedPassword） |
| 修改密码 / 重置密码 | `PUT /users/{username}` | 传新密码 |
| 修改姓名/邮箱 | `PUT /users/{username}` | 传 name/email |
| 停用 / 离职 | `DELETE /users/{username}` | 删影子账号，立即失去 IM 登录 |
| 恢复在职 | `POST /users` | 重建影子账号 |
| 建通讯录关系 | `POST /users/{a}/roster` + `POST /users/{b}/roster` | 双向各一次 |

---

## 四、错误处理约定

| HTTP 码 | 含义 | 平台处理 |
|---|---|---|
| 201 / 200 | 成功 | 继续 |
| 401 | 认证失败 | 检查 admin 账号/secretKey，告警 |
| 404 | 目标不存在 | 按幂等处理（删除已删的→忽略） |
| 409 | 冲突（重复建号） | 改为调用 `PUT` 更新 |
| 400 | 参数错 | 检查字段格式，告警 |

---

## 五、部署架构

### 5.1 正式环境

| 组件 | 容器 | 端口 | 说明 |
|---|---|---|---|
| Openfire 本体 | `collab-openfire` | 19090(管理台·仅本机)/15223(c2s-TLS)/17443(WS) | 明文端口已关（+10000 偏移） |
| 数据库 | `collab-openfire-db` | 25432 | `openfire` 库（ofUser/ofRoster，独立实例） |
| 媒体中转 | `collab-coturn` | 13478 + 59160-59200 | 音视频媒体 |
| REST API 插件 | 装在 Openfire 内 | — | 对接必需 |

### 5.2 隔离测试环境（不影响正式）

单独起一套测试 Openfire，四维隔离：

| 维度 | 正式环境 | 测试环境 | 隔离手段 |
|---|---|---|---|
| 容器 | `collab-openfire` | `test-openfire` | 不同容器名 |
| 端口 | 19090 等（+10000） | **29090 等（+20000）** | 端口偏移 |
| 数据库 | `openfire` 库 | **`openfire_test` 库** | 独立库 |
| XMPP 域 | `xmpp.collab.local` | **`test.xmpp.collab.local`** | 独立域 |

**部署步骤**：

1. postgres 建独立库：`CREATE DATABASE openfire_test OWNER openfire;`
2. 复制 `openfire.xml`，改 `<fqdn>test.xmpp.collab.local</fqdn>` + 库名 `openfire_test`
3. 起测试容器（独立 compose 文件：容器名/端口/卷名全改）
4. 装 REST API 插件（restAPI.jar 放入测试容器 plugins 目录）
5. 重启 → 登录测试管理台确认插件加载
6. 验证：`curl -u "admin:<ADMIN_PWD>" http://localhost:29090/plugins/restapi/v1/users` 返回 200
