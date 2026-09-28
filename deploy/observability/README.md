# 可观测性栈（M0-18 最小监控 + M0-19 日志集中采集）

> 依赖：`deploy/docker-compose.yml` 的 `collab-net` 网络与 4 中间件容器。
> 验收：Grafana 面板展示主机与中间件指标；Loki 可集中检索容器日志。

## 组成

| 服务 | 镜像 | 用途 |
| --- | --- | --- |
| prometheus | prom/prometheus | 指标采集（15s），6 个 job：node/cadvisor/postgres/redis/rabbitmq/minio |
| grafana | grafana/grafana | 面板（provisioned：数据源 Prometheus+Loki + 仪表盘「M0 基础设施总览」） |
| node-exporter | prom/node-exporter | 主机指标（CPU/内存/磁盘） |
| cadvisor | gcr.io/cadvisor/cadvisor | 容器指标（CPU/内存） |
| postgres-exporter | prometheuscommunity/postgres-exporter | PG 指标（collab_app + pg_monitor 角色） |
| redis-exporter | oliver006/redis_exporter | Redis 指标 |
| loki | grafana/loki | 日志集中存储与检索（单实例，retention 7d） |
| promtail | grafana/promtail | docker_sd 采集全部容器日志 → Loki |

## 操作

```bash
# 首次：生成 .env（从 deploy/.env 取 COLLAB_APP_PASSWORD）
grep '^COLLAB_APP_PASSWORD=' ../.env > .env

docker compose up -d
docker compose ps

# 验证
curl -s http://127.0.0.1:9090/api/v1/targets | python3 -m json.tool | grep -c '"health": "up"'
curl -s http://127.0.0.1:3000/api/health          # Grafana（admin/admin）
curl -s -G http://127.0.0.1:3100/loki/api/v1/query_range \
  --data-urlencode 'query={container="collab-postgres"}' --data-urlencode 'limit=5'
```

## 入口

- Grafana：http://10.211.55.4:3000（admin/admin，本机 dev）
- Prometheus：http://10.211.55.4:9090
- Loki API：http://10.211.55.4:3100

## 已知限制 / 后续

- 镜像均 `latest`，预生产前固定版本（M0_DEPLOYMENT_DESIGN.md §3 原则）
- MinIO 指标 `MINIO_PROMETHEUS_AUTH_TYPE=public`（NAT 内网 dev；生产改 basic_auth）
- Alertmanager 告警、ES 全文本检索（M6）后置；Loki retention 7d 可调
- cadvisor 需 privileged（容器指标）；仅 NAT 网络可达
