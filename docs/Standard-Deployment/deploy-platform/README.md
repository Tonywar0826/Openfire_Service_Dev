# Openfire 部署管理平台（deploy-platform）

标准化部署与扩展管理平台。P0 阶段骨架：完全可视化 Web 控制台，一键部署/备份/恢复。

## 目录结构

```
deploy-platform/
├── backend/            # 后端 FastAPI
│   ├── app/
│   │   ├── main.py     # 入口（/health + 路由注册）
│   │   ├── config.py   # 配置（.env 驱动）
│   │   ├── api/        # 路由层：deploy / targets / status / backup
│   │   └── services/   # 业务层：docker_service / compose_generator /
│   │                   #        connectors / config_sync / selfcheck
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
└── frontend/           # 前端 Vue3 + Vite + TS
    ├── src/
    │   ├── App.vue     # 三栏布局
    │   ├── components/Sidebar.vue
    │   ├── router/     # 8 个路由
    │   ├── api/        # 后端 API 客户端
    │   └── views/      # 8 个页面（概览/目标服务器/部署/拓扑/回退/备份/监控/设置）
    ├── package.json
    └── vite.config.ts
```

## 本地运行

**后端**（需 Python 3.11+）：
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

**前端**（需 Node 18+）：
```bash
cd frontend
npm install
npm run dev        # http://localhost:5173（代理 /api 到 8000）
```

## P0 状态

- [x] 项目骨架（后端分层 + 前端布局）
- [x] 参数化 compose + 一键部署（3 容器 + 插件 + 数据库初始化）
- [x] 部署参数（域名/admin 密码/数据库密码/局域网 IP + 可选 coturn 端口/用户/密码）
- [x] 配置同步（10 项逐项校验：部署参数 ↔ 协作平台 .env/nginx）
- [x] 自检校验（4 层：容器→服务→功能→Bug 回归，逐项状态）
- [ ] 一键备份 / 恢复
- [ ] 监控看板
